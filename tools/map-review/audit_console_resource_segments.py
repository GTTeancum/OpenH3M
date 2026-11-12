"""Estimate lossless segment repacking; never edits or publishes cache files."""
import collections
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from string_ids import StringTable

KNOWN = {'bitmap_texture_interop_resource', 'render_geometry_api_resource_definition',
         'model_animation_tag_resource'}


def audit(path):
    c = Cache(path)
    zone = next(t['offset'] for t in c.tags.values() if t['group']=='zone')
    play = next(t['offset'] for t in c.tags.values() if t['group']=='play')
    strings = StringTable(c)
    types = [strings.text(c.u(p+24)) for p in c.block(zone+4,28)]
    control = c.pointer(c.u(zone+0x13c+12))
    locations, pages = c.block(play+48,16), c.block(play+24,88)
    segments = collections.defaultdict(list)
    opaque = set()
    counts = collections.Counter()
    for ri,r in enumerate(c.block(zone+88,64)):
        li = c.unpack('h',r+34)[0]
        if li < 0:
            continue
        loc = locations[li]
        ids, offsets = c.unpack('2h',loc), c.unpack('2I',loc+4)
        kind = types[c.data[r+18]]
        counts[kind] += 1
        if kind not in KNOWN:
            opaque.update(p for p in ids if p >= 0)
            continue
        co, size = c.unpack('II',r+20)
        ends = [0,0]
        for fix in c.block(r+40,8):
            pointer,target = c.unpack('II',fix)
            slot = {0x40000000:0,0x60000000:1}.get(target&0xe0000000)
            if slot is None:
                continue
            if pointer < 12 or pointer > size-4:
                raise ValueError('Dataref outside resource control')
            n = c.u(control+co+pointer-12)
            ends[slot] = max(ends[slot],(target&0x1fffffff)+n)
        for slot,pi in enumerate(ids):
            if pi >= 0:
                segments[pi].append((offsets[slot],ends[slot],ri,kind))
    raw_base = (c.u(0x484)+c.u(0x470))&0xffffffff
    unique = {}
    kept = {}
    totals = collections.Counter()
    for pi in sorted(set(segments)|opaque):
        p = pages[pi]
        if c.unpack('h',p+4)[0] != -1:
            continue
        offset,compressed,decoded_size = c.unpack('III',p+8)
        if pi in opaque:
            kept[(offset,compressed)] = (compressed+4095)&~4095
            continue
        raw = c.data[raw_base+offset:raw_base+offset+compressed]
        data = zlib.decompress(raw,-15) if c.data[p+3]==0 else raw
        if len(data)!=decoded_size:
            raise ValueError('Wrong page size')
        for start,size,ri,kind in segments[pi]:
            if not size:
                continue
            if start+size > len(data):
                raise ValueError(f'{path.name} resource {ri} segment outside page')
            fragment = data[start:start+size]
            key = hashlib.sha256(fragment).hexdigest()
            totals['segment_count'] += 1
            totals['segment_decoded_bytes'] += size
            if key not in unique:
                encoded = zlib.compress(fragment)[2:-4]
                unique[key] = (len(encoded)+4095)&~4095
                totals['unique_segment_decoded_bytes'] += size
    raw_estimate = sum(kept.values())+sum(unique.values())
    result = dict(map=path.name,bytes=len(c.data),original_raw_bytes=c.u(0x488),
                  preserved_opaque_pages=len(kept),unique_segments=len(unique),
                  repacked_raw_bytes=raw_estimate,
                  estimated_file_bytes=len(c.data)-c.u(0x488)+raw_estimate,
                  counts=dict(counts),totals=dict(totals),
                  scope='Planning estimate only. Requires complete fixup/streaming verification and page-table allocation before use.')
    c.close()
    return result


if __name__ == '__main__':
    manifest = json.loads((ROOT/'.local/releases/current-live/manifest.json').read_text())
    reports = []
    for bundle in manifest['packages']:
        for name in bundle['maps']:
            path = Path(bundle['installed_source'])/(name+'.map')
            if path.stat().st_size <= 157286400:
                continue
            report = audit(path)
            reports.append(report)
            print(json.dumps(report),flush=True)
            (ROOT/'work/elongation-console-diagnostic/resource-segment-repack-audit.json').write_text(json.dumps(reports,indent=2)+'\n')
