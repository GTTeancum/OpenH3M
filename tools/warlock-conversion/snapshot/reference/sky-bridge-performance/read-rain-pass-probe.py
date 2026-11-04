"""Attribute paired numeric rain observations to exact CPU texture payload witnesses."""
import argparse
import array
from collections import Counter, defaultdict
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys

ref = Path(__file__).resolve().parent
repo = ref.parents[4]
sys.path.insert(0, str(repo / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
spec = importlib.util.spec_from_file_location('stage', ref / 'read-stage-probe.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('run', type=Path)
args = parser.parse_args()
run = args.run.resolve()
run.relative_to(repo / 'work/sky-bridge')
cache = Cache(repo / 'work/sky-bridge/payload-32/sky_bridge.map')
cache.decoded_pages = {}
cache.shared_paths = {'maps\\shared.map': Path('C:/X360/ISOs/H3M/maps/shared.map')}
textures = []
for tag in (10703, 10705):
    row, = cache.block(cache.tags[tag]['offset'] + 0x60, 48)
    hw, = cache.block(cache.tags[tag]['offset'] + 0x8c, 8)
    resource = Resource(cache, cache.u(hw))
    # Resource residency may omit the highest mip: keep both native streams
    # and identify the captured one instead of assuming the high stream is used.
    for field in (12, 32):
        if field not in resource.fix:
            continue
        pointer = resource.fix[field]
        raw_index, start = (pointer >> 29) - 2, pointer & 0x1fffffff
        length = resource.unpack('I', field - 12)[0]
        payload = resource.raw[raw_index][start:start + length]
        assert len(payload) == length and length >= 512
        textures.append({'tag': tag, 'dimensions': list(cache.unpack('HH', row + 4)),
            'format': cache.unpack('H', row + 12)[0], 'resource_stream': raw_index,
            'prefix_sha256': hashlib.sha256(payload[:512]).hexdigest()})
cache.close()
prefixes = defaultdict(set)
with (run / 'draws.bin').open('rb') as stream:
    while header := stream.read(8):
        kind, size = struct.unpack('<II', header)
        data = stream.read(size)
        assert len(data) == size
        if kind == 6:
            sequence, address, length, prefix_length = struct.unpack('<4Q', data)
        elif kind == 7:
            assert len(data) == prefix_length
            prefixes[address].add(hashlib.sha256(data).hexdigest())
calls = {}
regs = array.array('I', [0]) * 0x5003
stop = []
with (run / 'draws.bin').open('rb') as stream:
    while header := stream.read(8):
        kind, size = struct.unpack('<II', header)
        data = stream.read(size)
        assert len(data) == size
        if kind == 1:
            draw = struct.unpack('<11Q', data)
            assert draw[4] == 13459420923560293274
        elif kind == 2:
            for i, value in struct.iter_unpack('<II', data):
                regs[i] = value
        elif kind == 5:
            assert struct.unpack('<QQ', data) == draw[:2]
            words = list(regs[0x4800:0x4806])
            address = words[1] & 0xfffff000
            dimensions = [1 + (words[2] & 8191), 1 + (words[2] >> 13 & 8191)]
            matches = [t for t in textures if t['dimensions'] == dimensions
                and prefixes[address] == {t['prefix_sha256']}]
            assert len(matches) == 1, (hex(address), dimensions, prefixes[address], textures)
            calls[draw[0]] = {'frame': draw[1], 'index_count': draw[6],
                'texture': matches[0]['tag'], 'resource_stream': matches[0]['resource_stream'],
                'min_lod': words[4] >> 2 & 15, 'max_lod': words[4] >> 6 & 15, 'fetch_words': [hex(w) for w in words], 'phases': {}}
        elif kind == 9:
            stop.append(struct.unpack('<Q', data)[0])
events = Counter()
for row in csv.DictReader((run / 'stages.csv').open()):
    events[row['event']] += 1
    if row['event'] != 'sample':
        continue
    row = {k: int(v) for k, v in row.items() if k != 'event'}
    call = calls[row['sequence']]
    assert row['shader'] == 13459420923560293274 and row['frame'] == call['frame']
    assert row['index_count'] == call['index_count'] and row['phase'] in (0, 1)
    key = (row['x'], row['y'])
    phase = call['phases'].setdefault(row['phase'], {})
    assert key not in phase
    phase[key] = {'rgba': stage.rgba(row),
        'target': [row[k] for k in ('resource', 'format', 'width', 'height')]}
    assert all(math.isfinite(v) for v in phase[key]['rgba'])
summary = {t['tag']: {'draws': 0, 'complete_pairs': 0, 'changed_draws': 0,
    'changed_samples': 0, 'max_abs_rgb_delta': 0, 'changed_frames': set(), 'residency': Counter(), 'examples': []} for t in textures}
incomplete = []
for sequence, call in calls.items():
    result = summary[call['texture']]
    result['draws'] += 1
    result['residency'][str((call['resource_stream'], call['min_lod'], call['max_lod']))] += 1
    if set(call['phases']) != {0, 1} or any(len(p) != 16 for p in call['phases'].values()):
        incomplete.append(sequence)
        continue
    before, after = call['phases'][0], call['phases'][1]
    assert before.keys() == after.keys()
    result['complete_pairs'] += 1
    changed = False
    for point in before:
        a, b = before[point], after[point]
        assert a['target'] == b['target']
        delta = max(abs(x-y) for x,y in zip(a['rgba'][:3], b['rgba'][:3]))
        if delta:
            changed = True
            result['changed_samples'] += 1
            result['max_abs_rgb_delta'] = max(result['max_abs_rgb_delta'], delta)
            result['changed_frames'].add(call['frame'])
            if len(result['examples']) < 4:
                result['examples'].append({'frame': call['frame'], 'sequence': sequence,
                    'point': point, 'before': a['rgba'], 'after': b['rgba']})
    result['changed_draws'] += changed
for item in summary.values():
    item['changed_frames'] = sorted(item['changed_frames'])
report = {'textures': textures, 'events': dict(events), 'draws': len(calls),
    'frames': len({c['frame'] for c in calls.values()}), 'stop_reasons': stop,
    'incomplete_pairs': incomplete, 'by_texture': summary,
    'limitations': ['Sixteen isolated points per draw, not a screenshot or full visibility assessment.',
        'A 512-byte CPU payload prefix plus texture dimensions identifies the asset; it does not validate every GPU texel.',
        'Paired color changes demonstrate rendered contribution at measured points, not correct rain density or appearance.',
        'Probe synchronization overhead excludes this run from performance acceptance.'],
    'credit': json.loads((ref / 'sky-pixel-probe-build.json').read_text())['credit']}
(run / 'rain-pass-analysis.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'events': dict(events), 'incomplete_pairs': len(incomplete),
    'by_texture': {k: {n:v for n,v in t.items() if n not in ('examples', 'changed_frames')}
        for k,t in summary.items()}}))
