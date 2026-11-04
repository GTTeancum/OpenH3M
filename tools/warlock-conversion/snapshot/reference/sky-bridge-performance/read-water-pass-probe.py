"""Correlate paired water-sheet draw measurements with final output pulses."""
import argparse
import array
import collections
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct

ref = Path(__file__).resolve().parent
def load(name):
    spec = importlib.util.spec_from_file_location(name, ref / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
stage, pixel = load('read-stage-probe'), load('read-pixel-probe')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('run', type=Path)
args = parser.parse_args()
args.run.resolve().relative_to(ref.parents[4] / 'work/sky-bridge')
root = args.run
shader = 11015601269670120444
geometry_prefixes = json.loads((root / 'geometry-prefix-matches.json').read_text())['matches']
by_address = {p['address']: p['matches'] for p in geometry_prefixes}
vertex_hashes = collections.defaultdict(set)
with (root / 'draws.bin').open('rb') as stream:
    while header := stream.read(8):
        kind, size = struct.unpack('<II', header)
        data = stream.read(size)
        if len(data) != size:
            raise ValueError('Truncated prefix packet')
        if kind == 6:
            prefix_sequence, prefix_address, prefix_length, prefix_size = struct.unpack('<4Q', data)
        elif kind == 7:
            vertex_hashes[prefix_address].add(hashlib.sha256(data).hexdigest())
calls, events = {}, collections.Counter()
for row in csv.DictReader((root / 'stages.csv').open()):
    events[row['event']] += 1
    if row['event'] != 'sample':
        continue
    row = {k: int(v) for k, v in row.items() if k != 'event'}
    if row['shader'] != shader or (row['x'], row['y']) != (714, 210):
        raise ValueError('Unexpected water probe sample')
    value = stage.rgba(row)
    if not all(math.isfinite(v) for v in value):
        raise ValueError('Nonfinite water probe sample')
    call = calls.setdefault(row['sequence'], {'phases': {}})
    phase = row['phase']
    if phase not in (0, 1) or phase in call['phases']:
        raise ValueError('Duplicate or unexpected phase')
    call['phases'][phase] = {**row, 'rgba': value}

regs = array.array('I', [0]) * 0x5003
states, stop, counts = {}, [], collections.Counter()
with (root / 'draws.bin').open('rb') as stream:
    while header := stream.read(8):
        kind, size = struct.unpack('<II', header)
        data = stream.read(size)
        if len(data) != size:
            raise ValueError('Truncated draw packet')
        if kind == 1:
            draw = struct.unpack('<11Q', data)
        elif kind == 2:
            for i, value in struct.iter_unpack('<II', data):
                regs[i] = value
        elif kind == 5:
            sequence, frame = struct.unpack('<QQ', data)
            if draw[:2] != (sequence, frame) or draw[4] != shader:
                raise ValueError('Unexpected emitted draw')
            counts[draw[6]] += 1
            if sequence in calls:
                call = calls[sequence]
                call['draw'] = dict(zip(('sequence','frame','ns','vs','ps','primitive',
                    'index_count','index_address','index_length','index_format','index_endian'), draw))
                candidates = [g for g in by_address.get(draw[7], [])
                    if g['index_count'] == draw[6] and g['target_material'] in (9415, 9418)
                    and vertex_hashes.get(regs[0x48be] & 0xfffffffc) == {g['vertex_prefix_sha256']}]
                if len(candidates) != 1:
                    raise ValueError('Water geometry not uniquely identified by index and vertex bytes')
                call['geometry'] = candidates[0]
                if draw[6] == 84:
                    states[sequence] = regs[:]
        elif kind == 9:
            stop.append(struct.unpack('<Q', data)[0])

by_frame = collections.defaultdict(list)
incomplete = []
for sequence, call in sorted(calls.items()):
    if set(call['phases']) != {0, 1} or 'draw' not in call:
        incomplete.append(sequence)
        continue
    before, after = call.pop('phases').values()
    # CSV readback completion order must not determine phase identity.
    if before['phase'] == 1:
        before, after = after, before
    for key in ('frame','sequence','shader','index_count','resource','format','width','height'):
        if before[key] != after[key]:
            raise ValueError('Draw/target changed between paired observations')
    if before['frame'] != call['draw']['frame'] or before['index_count'] != call['draw']['index_count']:
        raise ValueError('CPU/GPU draw identity mismatch')
    call.update({k: before[k] for k in ('frame','sequence','resource','format','width','height')})
    call['before'], call['after'] = before['rgba'], after['rgba']
    call['changed_rgb'] = call['before'][:3] != call['after'][:3]
    by_frame[call['frame']].append(call)

def final(name):
    values = {}
    for row in csv.DictReader((root / name).open()):
        if row['event'] == 'sample' and (int(row['x']), int(row['y'])) == (714, 210):
            values[int(row['frame'])] = pixel.channels(int(row['packed_pixel']),
                int(row['format']), int(row['swizzle']))
    return values
source, presented = final('pixels.csv'), final('presented.csv')
decreases = []
for frame, value in sorted(presented.items()):
    if frame - 1 not in presented or frame + 1 not in presented:
        continue
    baseline = min(max(presented[frame - 1][:3]), max(presented[frame + 1][:3]))
    if baseline - max(value[:3]) <= .05 or max(value[:3]) > .7 * baseline:
        continue
    window = range(frame - 1, frame + 2)
    event = {'frame': frame, 'drop': baseline - max(value[:3]),
        'ratio': max(value[:3]) / baseline,
        'complete_stage_window': all(f in by_frame for f in window),
        'source': {str(f): source.get(f) for f in window},
        'presented': {str(f): presented[f] for f in window},
        'draws': {str(f): by_frame.get(f, []) for f in window}}
    event['register_comparisons'] = []
    identities = {(c['geometry']['mesh'],c['geometry']['part'])
        for f in window for c in by_frame.get(f, []) if c['draw']['index_count'] == 84}
    for mesh, part in sorted(identities):
        selected = [[c for c in by_frame.get(f, [])
            if (c['geometry']['mesh'],c['geometry']['part']) == (mesh,part)] for f in window]
        if all(len(s) == 1 for s in selected):
            snapshots = [states[s[0]['sequence']] for s in selected]
            event['register_comparisons'].append({'mesh':mesh,'part':part,
                'changed_registers':{hex(i):[hex(s[i]) for s in snapshots]
                    for i in range(len(regs)) if len({s[i] for s in snapshots}) != 1}})
    decreases.append(event)
report = {'point': [714,210], 'events': dict(events), 'incomplete_pairs': incomplete,
    'stage_frames': len(by_frame), 'source_frames': len(source), 'presented_frames': len(presented),
    'emitted_counts': dict(counts), 'stop_reasons': stop,
    'changed_draws': sum(c['changed_rgb'] for v in by_frame.values() for c in v),
    'relative_decreases': decreases,
    'limitations': ['Exact before/after measurements attribute pixel contribution to the draw, not why its shader inputs differ.',
        'The measured pulse is not yet established as the human-reported black flash.',
        'Probe barriers may alter timing; this run is not performance acceptance.']}
(root / 'water-pass-analysis.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('relative_decreases','limitations')}))
print('Decreases:', [(e['frame'], round(e['ratio'], 4)) for e in decreases])
