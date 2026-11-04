"""Restore two audited billboard mip chains in a private copy of candidate32.

No source pixels are resampled. No material, shader, animation or geometry is
changed. This incremental builder avoids unrelated pending converter changes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import numpy as np

REF = Path(__file__).resolve().parent
REPO = REF.parents[4]
sys.path.insert(0, str(REPO / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from cache_registry import CacheRegistry
from map_builder import MapBuilder
from build_scenario_checkpoint import resource_salt
from mcc_bitmap_source import BitmapSource
from encode_bitmap import encode_bitmap_base, mip_size
from xbox_bitmap import addresses
from xbox_mip_chain import layout
from resource_reader import Resource

BASIS_SHA = '311ad88580c5e099546c029f07f93976c346a8bb9bf9b12c1d48f72f5e0c3e5d'
SOURCE = Path('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map')
ASSETS = (
    (12513, 9767, r'levels\shared\bitmaps\human\crop_01', (256, 256, 11, 9),
     'e0d4c49e9abb36e5afd23b68e8fe20797afa6120aa3a99839c9ae9b3a161095d'),
    (12519, 9772, r'objects\bitmaps\screen_maps\screen_line_01', (128, 16, 14, 8),
     '2d7a8477335935dfb5f3a035212edd99c256b2060e4eaa81ad86d0c6392008ee'))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def scanline_layout():
    # Native GetPackedMipOffset (texture/util.cpp): shortest dimension 16
    # puts level zero in the packed tail. Coordinates below are BC1 blocks,
    # with a 32-block pitch. TagTool GetXboxBitmapLevelOffset returns zero
    # for every level: the base and mip resource offsets share this tail.
    offsets = ((0, 4), (0, 2), (0, 1), (16, 0), (8, 0), (4, 0), (2, 0), (1, 0))
    tiled = addresses(32, 32, 8)
    rows = []
    for level, (x, y) in enumerate(offsets):
        wb = (max(1, 128 >> level) + 3) // 4
        hb = (max(1, 16 >> level) + 3) // 4
        rows.append((tiled[y:y+hb, x:x+wb], wb * hb * 8))
    used = np.concatenate([p.ravel() for p, _ in rows])
    assert len(set(map(int, used))) == len(used)
    return rows, (int(used.max()) + 8 + 4095) & ~4095


def encode(source, tag):
    info, = source.info(tag)
    if tag == 12513:
        return encode_bitmap_base(source, tag, preserve_color_mips=True)
    assert tag == 12519
    record, control, _ = encode_bitmap_base(source, tag)
    pixels = source.pixels(tag)
    rows, size = scanline_layout()
    assert len(pixels) == sum(n for _, n in rows)
    raw = np.zeros(size, dtype=np.uint8)
    at = 0
    for positions, length in rows:
        blocks = np.frombuffer(pixels[at:at+length], dtype=np.uint8)
        blocks = blocks.reshape(-1, 2)[:, ::-1].reshape(-1, 8)
        raw[positions.reshape(-1, 1) + np.arange(8)] = blocks
        at += length
    record, control = bytearray(record), bytearray(control)
    record[20] = info['mips'] - 1
    struct.pack_into('>I', record, 28, size)
    struct.pack_into('>I', control, 0, size)
    control[45], control[47] = info['mips'], 0
    return bytes(record), bytes(control), raw.tobytes()


def verify_levels(pixels, raw, width, height, fmt, count):
    bpb, endian = (4, 4) if fmt == 11 else (8, 2)
    rows, size = layout(width, height, count, bpb, 1) if fmt == 11 else scanline_layout()
    assert len(raw) == size
    result, at = [], 0
    for level, (positions, length) in enumerate(rows):
        blocks = np.frombuffer(raw, dtype=np.uint8)[positions.reshape(-1, 1) + np.arange(bpb)]
        actual = blocks.reshape(-1, endian)[:, ::-1].tobytes()
        expected = pixels[at:at+length]
        assert actual == expected
        assert length == mip_size(max(1, width >> level), max(1, height >> level), fmt)
        result.append({'level': level, 'bytes': length, 'sha256': digest(actual)})
        at += length
    assert at == len(pixels)
    return result


def build(output):
    output = output.resolve()
    output.relative_to(REPO / 'work/sky-bridge')
    if output.exists() or not output.parent.is_dir():
        raise ValueError('Use a new map in an existing private Sky Bridge directory')
    basis = REPO / 'work/sky-bridge/payload-32/sky_bridge.map'
    assert digest(basis.read_bytes()) == BASIS_SHA
    stock = json.loads((REPO / 'work/sky-bridge/screen-pass-build/screen-stock-texture-audit.json').read_text())
    assert not stock['matches'] and len(stock['checked']) == 25
    s = Cache(SOURCE, True)
    bs = BitmapSource(s)
    b = MapBuilder(basis, 0x200000)
    r = CacheRegistry(b, resource_salt('C:/X360/ISOs/H3M/default.xex'))
    c = b.cache
    report = {'basis_sha256': BASIS_SHA, 'stock_audit': stock, 'textures': []}
    try:
        assert len(c.block(r.manifest_field, 120)) == 1
        for src, dst, name, expected, source_hash in ASSETS:
            info, = bs.info(src)
            assert s.name(src) == name
            assert tuple(info[k] for k in ('width', 'height', 'format', 'mips')) == expected
            pixels = bs.pixels(src)
            assert digest(pixels) == source_hash
            t = c.tags[dst]
            assert t['group'] == 'bitm' and t['salt'] == 0x9000
            row, = c.block(t['offset'] + 96, 48)
            handle, = c.block(t['offset'] + 140, 8)
            assert c.data[row+20] == 0
            assert (*c.unpack('HH', row+4), c.unpack('H', row+12)[0]) == expected[:3]
            record, control, raw = encode(bs, src)
            # The original base pixels remain unchanged after endian/tiling.
            old_resource = Resource(c, c.u(handle))
            from xbox_bitmap import tile_base
            old_raw = tile_base(pixels, expected[0], expected[1], expected[2])
            assert old_resource.raw[0] == old_raw
            levels = verify_levels(pixels, raw, *expected)
            owner = (t['salt'] << 16) | dst
            resource = r.add_resource(owner, 'bitmap_texture_interop_resource',
                {'control': control, 'raw': raw, 'root': 52,
                 'fixups': [(12, 0x40000000), (52, 0x20000000)], 'interops': [(0x20000034, 2)]})
            start = r.address(row) - b.base
            b.meta[start:start+48] = record
            b.put(r.address(handle), 'I', resource)
            report['textures'].append({'source': src, 'target': dst, 'name': name,
                'source_sha256': source_hash, 'before_mips': 1, 'after_mips': expected[3],
                'old_resource': c.u(handle), 'new_resource': resource,
                'old_raw_bytes': len(old_raw), 'raw_bytes': len(raw), 'raw_sha256': digest(raw),
                'levels': levels})
        r.finalize()
        assert not r.simulation_added and len(r.tags)//8 == r.first_tag
        payload = b.finish(r.salt)
        output.write_bytes(payload)
        report.update(map=str(output.relative_to(REPO)), sha256=digest(payload), bytes=len(payload),
            added_resource_bytes=r.added_bytes, native_runtime_verified=False,
            limitation='Mip byte retention and map structure only; native bindings, filtering and visual readability require runtime verification.',
            credit=json.loads((REF/'sky-pixel-probe-build.json').read_text())['credit'])
        output.with_suffix('.mips.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({k: v for k, v in report.items() if k not in ('textures', 'stock_audit')}))
    finally:
        b.close()
        s.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    build(parser.parse_args().output)
