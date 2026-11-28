"""Per-map colour balance of a finished native Halo 3 cache's baked lighting.

Use: rebalance a converted map whose baked light colour is off (e.g. Chiron's
yellow cast) when its source package is no longer available for a rebuild.

The native per-pixel lightmap stores each SH coefficient as two BC3 layers:
    colour = ((rgb_a + rgb_b) * 2 - 2) * (alpha_a * alpha_b * range)
(lightmap_sampling.fx, decode_bpp16_luvw). Scaling one colour channel of the
decoded light by k therefore means  sum' - 1 = k * (sum - 1)  per texel.
Layer A's endpoints get the exact affine map; layer B is refitted with its own
original indices to absorb A's rounding/clipping. Alpha (luminance), indices,
other channels whose gain is 1, sizes, formats and tiling are unchanged.
Scenery-probe SH and dominant-light colour get the same channel gains.

Only a page used solely by the lightmap bitmap is rewritten, in its existing
slot (it must still fit); page CRC/salted hashes and the cache's body XOR and
metadata digests are then refreshed. The RSA signature is not regenerated.
"""
import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path

import numpy as np

from cache_reader import Cache
from cache_integrity import refresh_cache_hashes
from build_scenario_checkpoint import resource_salt
from xbox_bitmap import addresses

LBSP_STRIDE = 0x1B4
PROBE_STRIDE = 0x50


def _tiled_block_order(width, height):
    pos = addresses(width // 4, height // 4, 16).reshape(-1)
    n = len(pos)
    if len(np.unique(pos)) != n or pos.max() + 16 != n * 16 or np.any(pos % 16):
        raise ValueError('Lightmap slice is not a dense block permutation')
    return n


def _decode(blocks):
    """blocks: (n,16) uint8 in little-endian BC3 order -> endpoints, weights."""
    c0 = blocks[:, 8].astype(np.uint16) | (blocks[:, 9].astype(np.uint16) << 8)
    c1 = blocks[:, 10].astype(np.uint16) | (blocks[:, 11].astype(np.uint16) << 8)
    unpack = lambda v: np.stack([(v >> 11) & 31, (v >> 5) & 63, v & 31], -1).astype(np.float64) / [31, 63, 31]
    bits = (blocks[:, 12].astype(np.uint32) | (blocks[:, 13].astype(np.uint32) << 8)
            | (blocks[:, 14].astype(np.uint32) << 16) | (blocks[:, 15].astype(np.uint32) << 24))
    index = np.stack([(bits >> (2 * j)) & 3 for j in range(16)], 1)
    # BC3 colour blocks always use four-colour interpolation.
    weight = np.array([0., 1., 1 / 3, 2 / 3])[index]
    return unpack(c0), unpack(c1), weight


def _texels(e0, e1, w):
    return e0[:, None, :] * (1 - w[..., None]) + e1[:, None, :] * w[..., None]


def _quantize(endpoint):
    q = np.clip(np.rint(endpoint * [31, 63, 31]), 0, [31, 63, 31]).astype(np.uint16)
    return (q[:, 0] << 11) | (q[:, 1] << 5) | q[:, 2], q / [31, 63, 31]


def _fit(target, w):
    """Least-squares endpoints for fixed indices; target (n,16,3), w (n,16)."""
    a = ((1 - w) ** 2).sum(1); b = ((1 - w) * w).sum(1); d = (w ** 2).sum(1)
    det = a * d - b * b
    r0 = ((1 - w)[..., None] * target).sum(1); r1 = (w[..., None] * target).sum(1)
    ok = np.abs(det) > 1e-9
    safe = np.where(ok, det, 1.)[:, None]
    e0 = (d[:, None] * r0 - b[:, None] * r1) / safe
    e1 = (a[:, None] * r1 - b[:, None] * r0) / safe
    mean = target.mean(1)
    e0 = np.where(ok[:, None], e0, mean); e1 = np.where(ok[:, None], e1, mean)
    return np.clip(e0, 0, 1), np.clip(e1, 0, 1)


def _swap16(raw):
    return raw.reshape(-1, 2)[:, ::-1].reshape(raw.shape)


def balance_pair(slice_a, slice_b, gains):
    """Return rebalanced tiled slices A and B plus error statistics."""
    a = _swap16(np.frombuffer(slice_a, np.uint8).copy()).reshape(-1, 16)
    b = _swap16(np.frombuffer(slice_b, np.uint8).copy()).reshape(-1, 16)
    a0, a1, aw = _decode(a); b0, b1, bw = _decode(b)
    gains = np.asarray(gains, dtype=np.float64)
    target = 1 + gains * (_texels(a0, a1, aw) + _texels(b0, b1, bw) - 1)
    q0, f0 = _quantize(0.5 + gains * (a0 - 0.5))
    q1, f1 = _quantize(0.5 + gains * (a1 - 0.5))
    n0, n1 = _fit(target - _texels(f0, f1, aw), bw)
    p0, g0 = _quantize(n0); p1, g1 = _quantize(n1)
    result = _texels(f0, f1, aw) + _texels(g0, g1, bw)
    keep = gains == 1
    # Channels with unit gain must stay bit-identical: restore their bits.
    masks = np.array([0xF800, 0x07E0, 0x001F], dtype=np.uint16)
    unit = np.uint16(sum(int(m) for m, k in zip(masks, keep) if k))
    def merge(new, old_lo, old_hi):
        old = old_lo.astype(np.uint16) | (old_hi.astype(np.uint16) << 8)
        return (new & ~unit) | (old & unit)
    for blocks, e0, e1 in ((a, q0, q1), (b, p0, p1)):
        v0 = merge(e0, blocks[:, 8], blocks[:, 9]); v1 = merge(e1, blocks[:, 10], blocks[:, 11])
        blocks[:, 8] = v0 & 255; blocks[:, 9] = v0 >> 8
        blocks[:, 10] = v1 & 255; blocks[:, 11] = v1 >> 8
    error = np.abs(result - target)[..., ~keep] if (~keep).any() else np.zeros(1)
    clipped = float(np.mean((target < 0) | (target > 2)))
    stats = dict(max_sum_error=float(error.max()), mean_sum_error=float(error.mean()),
                 target_outside_range_fraction=clipped)
    return _swap16(a.reshape(-1)).tobytes(), _swap16(b.reshape(-1)).tobytes(), stats


def rebalance_lights(c, data, chroma):
    """Recolour placed lights' constant colour functions (ARGB8 at function+4).

    The new colour has the requested linear balance and the old colour's
    luminance (Rec.709 weights, 2.2 transfer). Intensity, falloff, shape and
    placements are unchanged. Named (stock/shared) light tags are refused.
    """
    scnr = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
    chroma = np.asarray(chroma, dtype=np.float64)
    weights = np.array([0.2126, 0.7152, 0.0722])
    out = []
    for row in c.block(scnr + 0x1DC, 0x30):
        datum = c.u(row + 12)
        if c.data[row:row + 4] != b'ligh' or datum == 0xFFFFFFFF:
            continue
        index = datum & 65535
        if c.name(index) is not None:
            raise SystemExit(f'Light tag {c.name(index)} is named (stock/shared); refusing to recolour')
        tag = c.tags[index]['offset']
        size, pointer = c.u(tag + 0x28), c.u(tag + 0x28 + 12)
        at = c.pointer(pointer)
        function = bytes(c.data[at:at + size])
        if size != 32 or function[:4] != bytes.fromhex('01340100'):
            raise SystemExit(f'Light {datum:#x}: unsupported colour function {function.hex()}')
        old = np.frombuffer(function[5:8], np.uint8) / 255.
        linear = old ** 2.2
        new = chroma * (linear @ weights) / (chroma @ weights)
        if new.max() > 1:
            new /= new.max()
        argb = bytes([function[4]]) + bytes(np.clip(np.rint(new ** (1 / 2.2) * 255), 0, 255).astype(np.uint8))
        data[at + 4:at + 8] = argb
        out.append(dict(light=hex(datum), before='#' + function[5:8].hex(), after='#' + argb[1:].hex()))
    return out


def rebalance_atmosphere(c, data, chroma):
    """Recolour the scenario's skya Atmosphere Settings sun colour (linear RGB floats at +0x10)."""
    scnr = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
    datum = c.u(scnr + 0x6D0 + 12)
    if c.data[scnr + 0x6D0:scnr + 0x6D4] != b'skya' or datum == 0xFFFFFFFF:
        raise SystemExit('Scenario has no sky-atmosphere tag')
    if c.name(datum & 65535) is not None:
        raise SystemExit(f'Atmosphere tag {c.name(datum & 65535)} is named (stock/shared); refusing')
    chroma = np.asarray(chroma, dtype=np.float64)
    weights = np.array([0.2126, 0.7152, 0.0722])
    out = []
    for row in c.block(c.tags[datum & 65535]['offset'] + 0x34, 0xA4):
        old = np.array(c.unpack('3f', row + 0x10))
        new = chroma * (old @ weights) / (chroma @ weights)
        struct.pack_into('>3f', data, row + 0x10, *new)
        out.append(dict(before=[round(x, 4) for x in old], after=[round(x, 4) for x in new],
                        intensity=c.unpack('f', row + 0x1C)[0]))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--xex', type=Path, required=True, help='retail default.xex (resource hash salt)')
    p.add_argument('--gains', type=float, nargs=3, required=True, metavar=('R', 'G', 'B'))
    p.add_argument('--light-chroma', type=float, nargs=3, metavar=('R', 'G', 'B'),
                   help='also give every placed light (scenario light volumes) this linear colour '
                        'balance, keeping each light\'s luminance; only map-private light tags')
    p.add_argument('--atmosphere-chroma', type=float, nargs=3, metavar=('R', 'G', 'B'),
                   help='give the scenario sky-atmosphere sun colour this linear balance, keeping '
                        'its luminance; density, intensity and heights unchanged; map-private tag only')
    p.add_argument('--leave-vertex-lighting', action='store_true',
                   help='proceed although per-vertex-lit meshes exist; they keep their old colour '
                        '(recorded in the report)')
    p.add_argument('--brightness', type=float, default=1.0,
                   help='uniform baked-light brightness factor (lightmap ranges and scenery probes)')
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists() or a.report.exists():
        raise SystemExit('Output or report exists; use a fresh numbered path')
    gains = tuple(a.gains)
    if not all(0.25 <= g <= 4 for g in gains):
        raise SystemExit('Gains outside 0.25..4')
    salt = resource_salt(a.xex)
    c = Cache(a.input)
    data = bytearray(c.data)
    # Salt check: the untouched input's body XOR and salted header digest must
    # reproduce. Its two metadata digests are recorded; they are refreshed anyway.
    probe = bytearray(data); refresh_cache_hashes(probe, salt)
    if probe[0x2C4:0x2C8] != data[0x2C4:0x2C8] or probe[0x330:0x344] != data[0x330:0x344]:
        raise SystemExit('Input header digest does not reproduce with this xex salt; refusing to edit')
    input_metadata_digests_current = probe[0x344:0x36C] == data[0x344:0x36C]
    del probe
    sldt = next(t['offset'] for t in c.tags.values() if t['group'] == 'sLdT')
    zone = next(t['offset'] for t in c.tags.values() if t['group'] == 'zone')
    play = next(t['offset'] for t in c.tags.values() if t['group'] == 'play')
    pages = c.block(play + 24, 88); locations = c.block(play + 48, 16)
    users = {}
    for row in locations:
        for index in c.unpack('hh', row):
            if index >= 0:
                users[index] = users.get(index, 0) + 1
    resource_base = (c.u(0x484) + c.u(0x470)) & 0xFFFFFFFF
    page_starts = sorted({c.u(pg + 8) for pg in pages if c.unpack('h', pg + 4)[0] == -1 and c.u(pg + 12)})
    report = dict(input=str(a.input), input_sha256=hashlib.sha256(c.data).hexdigest(), gains=gains,
                  input_metadata_digests_current=input_metadata_digests_current,
                  method=__doc__.strip().splitlines()[0], textures=[], probes={})
    for bsp_row in (c.block(sldt + 4, LBSP_STRIDE) if gains != (1.0, 1.0, 1.0) else []):
        # Per-coefficient luminance ranges are 0x18 apart (Compression Vectors 0,2,4,6,8 x):
        # SH terms 0..3, then dominant-light intensity. Verified on Chiron: 161,186,201,203,341.
        ranges = c.unpack('54f', bsp_row + 8)[0:30:6]
        for ref, layer_count, range_index in ((0xE0, 8, (0, 1, 2, 3)), (0xF0, 2, (4,))):
            bitmap = c.tags[c.u(bsp_row + ref + 12) & 65535]['offset']
            info = c.block(bitmap + 0x60, 0x30)
            if len(info) != 1:
                raise SystemExit('Expected one lightmap bitmap entry')
            width, height, depth = c.unpack('HH', info[0] + 4) + (c.data[info[0] + 8],)
            fmt = c.unpack('H', info[0] + 12)[0]
            if depth != layer_count or fmt != 16:
                raise SystemExit(f'Unexpected lightmap layout {width}x{height}x{depth} format {fmt}')
            pairs = [(2 * k, 2 * k + 1) for k, r in zip(range(layer_count // 2), range_index) if ranges[r] > 0]
            entry = dict(role='lightprobe' if ref == 0xE0 else 'dominant_intensity', width=width, height=height,
                         layers=depth, ranges=[ranges[r] for r in range_index], pairs_rebalanced=pairs)
            report['textures'].append(entry)
            if not pairs:
                entry['note'] = 'all ranges zero: no visible contribution, left unchanged'
                continue
            datum = c.u(c.block(bitmap + 0x8C, 8)[0])
            resource = c.block(zone + 88, 64)[datum & 65535]
            if c.unpack('H', resource + 16)[0] != datum >> 16:
                raise SystemExit('Lightmap resource salt mismatch')
            location = locations[c.unpack('h', resource + 34)[0]]
            page_index, second = c.unpack('hh', location)
            if second != -1 or c.unpack('II', location + 4) != (0, 0) or users.get(page_index) != 1:
                raise SystemExit('Lightmap page is shared or segmented; refusing in-place edit')
            page = pages[page_index]
            if c.unpack('h', page + 4)[0] != -1:
                raise SystemExit('Lightmap page lives in a shared cache')
            block, compressed, size, crc = c.unpack('IIII', page + 8)
            codec = c.data[page + 3]
            raw = bytes(c.data[resource_base + block:resource_base + block + compressed])
            raw = zlib.decompress(raw, -15) if codec == 0 else raw
            if codec not in (0, 255) or len(raw) != size or zlib.crc32(raw) ^ 0xFFFFFFFF != crc:
                raise SystemExit('Lightmap page failed its own integrity check')
            slice_size = _tiled_block_order(width, height) * 16
            if size != slice_size * depth:
                raise SystemExit('Lightmap page size differs from its layers')
            raw = bytearray(raw)
            stats = []
            for la, lb in pairs:
                sa = raw[la * slice_size:(la + 1) * slice_size]; sb = raw[lb * slice_size:(lb + 1) * slice_size]
                na, nb, st = balance_pair(bytes(sa), bytes(sb), gains)
                raw[la * slice_size:(la + 1) * slice_size] = na; raw[lb * slice_size:(lb + 1) * slice_size] = nb
                stats.append(dict(layers=[la, lb], **st))
            raw = bytes(raw)
            later = [s for s in page_starts if s > block]
            slot = (later[0] if later else None)
            payload = zlib.compress(raw, 9)[2:-4] if codec == 0 else raw
            if slot is None or len(payload) > slot - block:
                raise SystemExit(f'Rebalanced page ({len(payload)} bytes) does not fit its slot')
            start = resource_base + block
            data[start:slot + resource_base] = payload + bytes(slot - block - len(payload))
            struct.pack_into('>II', data, page + 12, len(payload), size)
            struct.pack_into('>I', data, page + 20, zlib.crc32(raw) ^ 0xFFFFFFFF)
            data[page + 24:page + 84] = b''.join(hashlib.sha1(salt + part).digest()
                                                 for part in (raw, raw[:1024], raw[-1024:]))
            entry.update(page=page_index, compressed_before=compressed, compressed_after=len(payload),
                         slot_bytes=slot - block, pair_stats=stats)
    # Scenery probes: big-endian half floats, 9 SH terms per channel plus the
    # dominant-light colour (the plugin labels them int16; values are binary16).
    def scale(at, g):
        value = float(np.frombuffer(bytes(data[at:at + 2]), '>f2')[0])
        scaled = np.array([value * g], '>f2')
        if not np.isfinite(scaled[0]):
            raise SystemExit('Probe value overflow')
        data[at:at + 2] = scaled.tobytes()
    # Lighting stores this tool does not rebalance must be empty when the
    # baked colour changes (otherwise objects/geometry would keep the old colour).
    unit_gains = gains == (1.0, 1.0, 1.0)
    if not unit_gains and (c.u(sldt + 0x28) or c.u(sldt + 0x40)):
        raise SystemExit('Airprobes or device/machine probes present; extend this tool first')
    for bsp_row in ([] if unit_gains else c.block(sldt + 4, LBSP_STRIDE)):
        if c.u(bsp_row + 0x124):
            raise SystemExit('Per-BSP probe lighting present; extend this tool first')
        if c.u(bsp_row + 0x100):
            if not a.leave_vertex_lighting:
                raise SystemExit('Per-vertex lighting present; extend this tool or pass --leave-vertex-lighting')
            report['vertex_lit_buffers_unchanged'] = report.get('vertex_lit_buffers_unchanged', 0) + c.u(bsp_row + 0x100)
    if a.brightness != 1:
        # Uniform brightness: the decode is linear in each SH/dominant range, so
        # multiplying the five ranges scales baked light exactly, with no requantization.
        if not 0.25 <= a.brightness <= 4:
            raise SystemExit('Brightness outside 0.25..4')
        if c.u(sldt + 0x28) or c.u(sldt + 0x40):
            raise SystemExit('Airprobes or device/machine probes present; extend this tool first')
        scaled_ranges = []
        for bsp_row in c.block(sldt + 4, LBSP_STRIDE):
            if c.u(bsp_row + 0x124):
                raise SystemExit('Per-BSP probe lighting present; extend this tool first')
            if c.u(bsp_row + 0x100):
                if not a.leave_vertex_lighting:
                    raise SystemExit('Per-vertex lighting present; extend this tool or pass --leave-vertex-lighting')
                report['vertex_lit_buffers_unchanged'] = c.u(bsp_row + 0x100)
            for n in range(5):
                at = bsp_row + 8 + 0x18 * n
                old = c.unpack('f', at)[0]
                struct.pack_into('>f', data, at, old * a.brightness)
                scaled_ranges.append([old, old * a.brightness])
        report['brightness'] = dict(factor=a.brightness, ranges=scaled_ranges)
    probe_gains = tuple(g * a.brightness for g in gains)
    for name, offset in (('scenery', 0x34),):
        rows = c.block(sldt + offset, PROBE_STRIDE)
        for row in rows:
            for channel, g in enumerate(probe_gains):
                if g == 1:
                    continue
                scale(row + 0x10 + 2 * channel, g)
                for k in range(9):
                    scale(row + 0x18 + 18 * channel + 2 * k, g)
        report['probes'][name] = len(rows)
    if a.light_chroma:
        report['lights'] = rebalance_lights(c, data, a.light_chroma)
    if a.atmosphere_chroma:
        report['atmosphere'] = rebalance_atmosphere(c, data, a.atmosphere_chroma)
    c.close()
    report["finalization"] = refresh_cache_hashes(data, salt)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_bytes(data)
    report['output'] = str(a.output); report['output_sha256'] = hashlib.sha256(data).hexdigest()
    a.report.write_text(json.dumps(report, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'finalization'}, indent=1))


if __name__ == '__main__':
    main()
