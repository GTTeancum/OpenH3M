"""Restore exact-source mip chains without changing base images or resource IDs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import xml.etree.ElementTree as ET
from audit_missing_mips import audit
from cache_reader import Cache
from cache_registry import CacheRegistry
from map_builder import MapBuilder
from build_scenario_checkpoint import resource_salt
from resource_reader import Resource
from mcc_bitmap_source import BitmapSource
from encode_bitmap import encode_bitmap_base, mip_size, mcc_dxn_to_retail, texture_gpu_format

ROOT = Path(__file__).resolve().parents[4]


def compact_pages(r):
    """Discard only unreferenced whole local pages; preserve shared references."""
    b, c = r.builder, r.cache
    used = set()
    for at in range(0, len(r.resources), 64):
        li = struct.unpack_from('>h', r.resources, at+34)[0]
        if li >= 0:
            used.update(p for p in struct.unpack_from('>hh', r.locations, li*16) if p >= 0)
    start = (c.u(0x484)+c.u(0x470)) & 0xffffffff
    original = c.data[start:start+c.u(0x488)] + b.raw
    packed, moved = bytearray(), {}
    for i in range(len(r.pages)//88):
        at = i*88
        if struct.unpack_from('>h', r.pages, at+4)[0] != -1:
            continue
        offset, size = struct.unpack_from('>II', r.pages, at+8)
        if i not in used:
            struct.pack_into('>III', r.pages, at+8, 0, 0, 0)
            continue
        if offset+size > len(original):
            raise ValueError('Page outside raw section')
        key = offset, size
        if key not in moved:
            packed.extend(bytes((-len(packed)) % 4096))
            moved[key] = len(packed)
            packed.extend(original[offset:offset+size])
        struct.pack_into('>I', r.pages, at+8, moved[key])
    packed.extend(bytes((-len(packed)) % 4096))
    b.compacted_raw = packed


def restore(source, basis, xex, output, report):
    if any(not p.resolve().is_relative_to(ROOT) or p.exists() for p in (output, report)):
        raise ValueError('Outputs must be new repository-local paths')
    matching = audit(source, basis)
    s, b = Cache(source, True), MapBuilder(basis, 0x200000)
    r = CacheRegistry(b, resource_salt(xex))
    c, bitmaps = b.cache, BitmapSource(s)
    changes, deltas, skipped = [], {}, []
    temp = ROOT/'work/forge-world/temp'
    temp.mkdir(parents=True, exist_ok=True)
    scratch = temp/'restored-mip-check.bin'
    validator = ROOT/'work/forge-world/tools/mip-validator/Validate.dll'
    if hashlib.sha256((validator.parent/'TagTool.dll').read_bytes()).hexdigest() != '0080eb49cc22dae4d0854c33db42863539b784776aea2124543fc90c96f68623':
        raise ValueError('Independent mip decoder does not match pinned dependency')
    env = dict(os.environ, TEMP=str(temp), TMP=str(temp), DOTNET_CLI_HOME=str(ROOT/'.local/dotnet'),
               NUGET_PACKAGES=str(ROOT/'.local/nuget'), DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
    try:
        for item in matching['matches']:
            if item.get('ambiguous') or any(v & (v-1) for v in (item['width'],item['height'])):
                skipped.append(dict(item,reason='Ambiguous source chain' if item.get('ambiguous') else 'Non-power-of-two mip layout requires a separate encoder'))
                continue
            target, src = item['target'], item['source']
            tag = c.tags[target]
            row = c.block(tag['offset']+96, 48)[0]
            hw = c.block(tag['offset']+140, 8)[0]
            old = Resource(c, c.u(hw), shared_paths={'maps\\shared.map': Path('C:/X360/ISOs/H3M/maps/shared.map')})
            record, control, raw = encode_bitmap_base(bitmaps, src,
                max_dimension=max(item['width'], item['height']), preserve_normal_mips=True, preserve_bc_mips=True)
            # Preserve the accepted map's color curve, sampler metadata and base image.
            control = bytearray(control)
            gpu = texture_gpu_format(item['format'], c.data[row+21])
            struct.pack_into('>I', control, 48, gpu)
            pixels = bitmaps.pixels(src)
            if item['format'] == 33:
                pixels = mcc_dxn_to_retail(pixels)
            info = bitmaps.info(src)[0]
            expected, offset = [], 0
            for level in range(info['mips']):
                size = mip_size(max(1, info['width']>>level), max(1, info['height']>>level), item['format'])
                if level >= item['level']:
                    expected.append(hashlib.sha256(pixels[offset:offset+size]).hexdigest())
                offset += size
            scratch.write_bytes(raw)
            checked = subprocess.run(['C:/Program Files/dotnet/dotnet.exe', str(validator), str(scratch),
                str(item['width']), str(item['height']), str(record[20]+1), f'{gpu:x}'],
                cwd=ROOT, env=env, capture_output=True, text=True, check=True, timeout=30)
            if json.loads(checked.stdout) != expected:
                raise ValueError('Independent mip decode differs from source: '+item['name'])
            rid = c.u(hw) & 65535
            if rid in deltas:
                raise ValueError('Unexpected shared resource between converted bitmap tags')
            old_salt = bytes(r.resources[rid*64+16:rid*64+18])
            r.add_resource((tag['salt']<<16)|target, 'bitmap_texture_interop_resource',
                dict(control=bytes(control), raw=raw, root=52, fixups=[(12,0x40000000),(52,0x20000000)], interops=[(0x20000034,2)]))
            replacement = r.resources[-64:]
            replacement[16:18] = old_salt
            del r.resources[-64:]
            r.resources[rid*64:(rid+1)*64] = replacement
            b.put(r.address(row+20), 'B', record[20])
            b.put(r.address(row+28), 'I', len(raw))
            deltas[rid] = len(raw)-old.unpack('I',0)[0]
            changes.append(dict(item, mips=record[20]+1, bytes_added=deltas[rid], sha256_per_mip=expected))
        if not changes:
            raise ValueError('No unambiguous supported mip chains found; refusing an unnecessary map copy')
        # Existing IDs retain all residency bits; adjust each manifest's size by
        # only the resources actually present in that manifest/category.
        r.added_bytes = 0
        schema = ET.parse(Path(__file__).resolve().parents[1]/'reference/plugins/zone.xml').getroot()
        updates = []
        for field in schema:
            if field.tag.lower() != 'tagblock' or 'Manifest' not in field.get('name',''):
                continue
            for manifest in c.block(r.zone+int(field.get('offset'),0),120):
                for category in range(4):
                    words = [c.u(a) for a in c.block(manifest+category*12,4)]
                    delta = sum(size for rid,size in deltas.items() if rid//32 < len(words) and words[rid//32] & (1<<(rid%32)))
                    updates.append((r.address(manifest+48+category*4), c.u(manifest+48+category*4)+delta))
        compact_pages(r)
        r.finalize()
        for address, size in updates:
            b.put(address,'I',size)
        payload = b.finish(r.salt)
        output.write_bytes(payload)
        report.write_text(json.dumps(dict(basis=str(basis), source=str(source), matching=matching,
            restored=changes, skipped=skipped, bytes=len(payload), bytes_difference=len(payload)-len(b.original),
            resident_bytes_added=sum(deltas.values()), metadata_used=b.used,
            sha256=hashlib.sha256(payload).hexdigest(), native_visual_check='pending'),indent=2)+'\n')
        print(f'{output.name}: restored {len(changes)} textures; resource delta {sum(deltas.values())} bytes; file {len(payload)} bytes')
    finally:
        scratch.unlink(missing_ok=True)
        s.close();b.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source','basis','xex','output','report'):
        p.add_argument('--'+name, type=Path, required=True)
    restore(**vars(p.parse_args()))
