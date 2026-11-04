"""Attribute paired billboard color measurements using index, vertex and shader evidence."""
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

ref = Path(__file__).resolve().parent
repo = ref.parents[4]
spec = importlib.util.spec_from_file_location('stage', ref / 'read-stage-probe.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('run', type=Path)
args = parser.parse_args()
run = args.run.resolve()
run.relative_to(repo / 'work/sky-bridge')
prefixes = json.loads((run / 'geometry-prefix-matches.json').read_text())['matches']
by_address = {p['address']: p['matches'] for p in prefixes}
programs = json.loads((run / 'program-slice-matches.json').read_text())
materials = {p['shader']: {m['id'] for match in p['matches'] for entry in match['programs']
    for template in entry['templates'] for m in template['materials']} for p in programs}
vertex_hashes = defaultdict(set)
with (run / 'draws.bin').open('rb') as stream:
    while header := stream.read(8):
        kind, size = struct.unpack('<II', header)
        data = stream.read(size)
        assert len(data) == size
        if kind == 6:
            prefix_address = struct.unpack('<4Q', data)[1]
        elif kind == 7:
            vertex_hashes[prefix_address].add(hashlib.sha256(data).hexdigest())
regs = array.array('I', [0]) * 0x5003
calls, stops = {}, []
with (run / 'draws.bin').open('rb') as stream:
    while header := stream.read(8):
        kind, size = struct.unpack('<II', header)
        data = stream.read(size)
        assert len(data) == size
        if kind == 1:
            draw = struct.unpack('<11Q', data)
            assert draw[4] in (3413622546942440597, 10494309294728871449, 8658708157452486949)
        elif kind == 2:
            for i, value in struct.iter_unpack('<II', data):
                regs[i] = value
        elif kind == 5:
            assert struct.unpack('<QQ', data) == draw[:2]
            matches = [g for g in by_address[draw[7]] if g['index_count'] == draw[6]
                and g['target_material'] in materials[draw[4]]
                and vertex_hashes[regs[0x48be] & 0xfffffffc] == {g['vertex_prefix_sha256']}]
            assert len(matches) == 1 and matches[0]['mesh'] == 144
            calls[draw[0]] = {'frame': draw[1], 'shader': draw[4], 'index_count': draw[6],
                'geometry': matches[0], 'phases': {},
                'pixel_booleans_128_159': hex(regs[0x4904])}
        elif kind == 9:
            stops.append(struct.unpack('<Q', data)[0])
events, formats = Counter(), Counter()
for row in csv.DictReader((run / 'stages.csv').open()):
    events[row['event']] += 1
    if row['event'] != 'sample':
        continue
    row = {k: int(v) for k, v in row.items() if k != 'event'}
    call = calls[row['sequence']]
    assert row['frame'] == call['frame'] and row['shader'] == call['shader']
    assert row['index_count'] == call['index_count'] and row['phase'] in (0, 1)
    point = (row['x'], row['y'])
    phase = call['phases'].setdefault(row['phase'], {})
    assert point not in phase
    phase[point] = {'rgba': stage.rgba(row),
        'target': [row[k] for k in ('resource', 'format', 'width', 'height')]}
    assert all(math.isfinite(v) for v in phase[point]['rgba'])
    formats[row['format']] += 1
layers, incomplete = {}, []
per_frame = defaultdict(list)
for sequence, call in calls.items():
    geometry = call['geometry']
    layer = layers.setdefault(geometry['part'], {'geometry': geometry, 'draws': 0,
        'complete_pairs': 0, 'changed_draws': 0, 'changed_points': 0, 'positive_rgb_sum': 0.,
        'negative_rgb_sum': 0., 'max_abs_rgb_delta': 0., 'newly_saturated_channels': 0,
        'after_saturated_channels': 0, 'sampled_channels': 0, 'examples': []})
    layer['draws'] += 1
    if set(call['phases']) != {0, 1} or any(len(p) != 16 for p in call['phases'].values()):
        incomplete.append(sequence)
        continue
    before, after = call['phases'][0], call['phases'][1]
    assert before.keys() == after.keys()
    layer['complete_pairs'] += 1
    changed = False
    for point in before:
        a, b = before[point], after[point]
        assert a['target'] == b['target']
        delta = [y-x for x,y in zip(a['rgba'][:3], b['rgba'][:3])]
        maximum = max(map(abs, delta))
        layer['positive_rgb_sum'] += sum(max(0, v) for v in delta)
        layer['negative_rgb_sum'] += sum(min(0, v) for v in delta)
        layer['sampled_channels'] += 3
        # Only normalized eight-bit color targets have the saturation bound used here.
        assert a['target'][1] == 28
        layer['after_saturated_channels'] += sum(v == 1 for v in b['rgba'][:3])
        layer['newly_saturated_channels'] += sum(x < 1 and y == 1 for x,y in zip(a['rgba'][:3], b['rgba'][:3]))
        if maximum:
            changed = True
            layer['changed_points'] += 1
            layer['max_abs_rgb_delta'] = max(layer['max_abs_rgb_delta'], maximum)
            if len(layer['examples']) < 4:
                layer['examples'].append({'frame': call['frame'], 'sequence': sequence,
                    'point': point, 'before': a['rgba'], 'after': b['rgba']})
    layer['changed_draws'] += changed
    point = (392, 210)
    per_frame[call['frame']].append({'sequence': sequence, 'part': geometry['part'],
        'before': before[point]['rgba'], 'after': after[point]['rgba']})
total = sum(layer['positive_rgb_sum'] for layer in layers.values())
for layer in layers.values():
    layer['share_of_measured_positive_rgb'] = layer['positive_rgb_sum'] / total if total else None
report = {'draws': len(calls), 'frames': len(per_frame), 'events': dict(events),
    'formats': dict(formats), 'stop_reasons': stops, 'incomplete_pairs': incomplete,
    'layers': layers, 'central_point': [392, 210], 'central_point_layers_by_frame': dict(per_frame),
    'limitations': ['Sixteen points within the saved-view billboard; not a full image or perceptual readability measurement.',
        'Measured RGB shares are normalized color-target differences, not linear-light energy or complete shader output.',
        'Other shader outputs and later composition are outside these paired color-0 samples.',
        'Source fidelity and visual correctness require separate evidence; probe timing is not performance acceptance.'],
    'credit': json.loads((ref / 'sky-pixel-probe-build.json').read_text())['credit']}
(run / 'screen-pass-analysis.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'draws': len(calls), 'frames': len(per_frame), 'events': dict(events),
    'formats': dict(formats), 'incomplete_pairs': len(incomplete), 'layers': {
        k: {n:v for n,v in layer.items() if n not in ('geometry', 'examples')}
        for k,layer in layers.items()}}))
