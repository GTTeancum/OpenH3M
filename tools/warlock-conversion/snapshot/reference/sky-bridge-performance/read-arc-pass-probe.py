"""Attribute electrical-arc draws and measure their paired numeric GPU contribution."""
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

REF = Path(__file__).resolve().parent
REPO = REF.parents[4]
PS = 16104069050768599808
OFFSETS = (0x3800, 0x25800, 0x72e00)
sys.path.insert(0, str(REPO / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
spec = importlib.util.spec_from_file_location('stage', REF / 'read-stage-probe.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


def packets(path):
    with path.open('rb') as stream:
        while header := stream.read(8):
            kind, size = struct.unpack('<II', header)
            data = stream.read(size)
            assert len(data) == size
            yield kind, data


def analyze(run):
    cache = Cache(REPO / 'work/sky-bridge/payload-36/sky_bridge.map')
    cache.decoded_pages = {}
    cache.shared_paths = {'maps\\shared.map': Path('C:/X360/ISOs/H3M/maps/shared.map')}
    row, = cache.block(cache.tags[10422]['offset'] + 0x60, 48)
    hw, = cache.block(cache.tags[10422]['offset'] + 0x8c, 8)
    resource = Resource(cache, cache.u(hw))
    pointer = resource.fix[12]
    start = pointer & 0x1fffffff
    size = resource.unpack('I', 0)[0]
    payload = resource.raw[(pointer >> 29) - 2][start:start + size]
    assert len(payload) == 1048576
    witnesses = {offset: hashlib.sha256(payload[offset:offset+512]).hexdigest() for offset in OFFSETS}
    texture = {'tag': 10422, 'name': cache.name(10422),
        'dimensions': list(cache.unpack('HH', row + 4)),
        'format': cache.unpack('H', row + 12)[0], 'witnesses': witnesses}
    cache.close()
    calls = {}
    regs = array.array('I', [0]) * 0x5003
    stops = []
    # Recorder deduplicates address/content witnesses. Require a single exact
    # value over the entire run, rather than assuming every draw repeats it.
    prefixes = defaultdict(set)
    for kind, data in packets(run / 'draws.bin'):
        if kind == 6:
            _, address, _, prefix_length = struct.unpack('<4Q', data)
        elif kind == 7:
            assert len(data) == prefix_length
            prefixes[address].add(hashlib.sha256(data).hexdigest())
    for kind, data in packets(run / 'draws.bin'):
        if kind == 1:
            draw = struct.unpack('<11Q', data)
            assert draw[4] == PS
        elif kind == 2:
            for i, value in struct.iter_unpack('<II', data):
                regs[i] = value
        elif kind == 5:
            assert struct.unpack('<QQ', data) == draw[:2]
            bindings = {}
            for sampler in (0, 2):
                words = list(regs[0x4800+sampler*6:0x4806+sampler*6])
                base = words[1] & 0xfffff000
                dimensions = [1+(words[2]&8191), 1+(words[2]>>13&8191)]
                match = dimensions == texture['dimensions'] and all(
                    prefixes[base+offset] == {digest} for offset,digest in witnesses.items())
                bindings[sampler] = {'base': hex(base), 'dimensions': dimensions,
                    'exact_three_witness_match': match, 'fetch_words': [hex(w) for w in words]}
            calls[draw[0]] = {'frame': draw[1], 'index_count': draw[6],
                'bindings': bindings, 'matched': all(x['exact_three_witness_match'] for x in bindings.values()),
                'phases': {}}
        elif kind == 9:
            stops.append(struct.unpack('<Q', data)[0])
    events = Counter()
    for row in csv.DictReader((run / 'stages.csv').open()):
        events[row['event']] += 1
        if row['event'] != 'sample':
            continue
        row = {k:int(v) for k,v in row.items() if k != 'event'}
        call = calls[row['sequence']]
        assert row['shader'] == PS and row['frame'] == call['frame']
        assert row['index_count'] == call['index_count'] and row['phase'] in (0,1)
        point = (row['x'],row['y'])
        phase = call['phases'].setdefault(row['phase'], {})
        assert point not in phase
        phase[point] = {'rgba': stage.rgba(row),
            'target': [row[k] for k in ('resource','format','width','height')]}
        assert all(math.isfinite(v) for v in phase[point]['rgba'])
    changed_frames = set()
    changed_points = Counter()
    examples = []
    complete = changed_draws = 0
    maximum = 0
    incomplete = []
    unassigned = []
    for sequence, call in calls.items():
        if not call['matched']:
            unassigned.append(sequence)
        if set(call['phases']) != {0,1} or any(len(p) != 16 for p in call['phases'].values()):
            incomplete.append(sequence)
            continue
        complete += 1
        before, after = call['phases'][0], call['phases'][1]
        assert before.keys() == after.keys()
        changed = False
        for point in before:
            a,b = before[point],after[point]
            assert a['target'] == b['target']
            delta = max(abs(x-y) for x,y in zip(a['rgba'][:3],b['rgba'][:3]))
            if delta and call['matched']:
                changed = True
                maximum = max(maximum,delta)
                changed_frames.add(call['frame'])
                changed_points[str(point)] += 1
                if len(examples) < 12:
                    examples.append({'sequence':sequence,'frame':call['frame'],
                        'point':point,'before':a['rgba'],'after':b['rgba']})
        changed_draws += changed
    report = {'texture':texture, 'shader':PS, 'events':dict(events),
        'draws':len(calls),'frames':len({c['frame'] for c in calls.values()}),
        'stop_reasons':stops,'complete_pairs':complete,'incomplete_pairs':incomplete,
        'unassigned_draws':unassigned, 'changed_draws':changed_draws,
        'changed_frames':sorted(changed_frames),'changed_points':dict(changed_points),
        'max_abs_rgb_delta':maximum,'examples':examples,
        'binding_variants':[json.loads(s) for s in sorted({json.dumps(c['bindings'],sort_keys=True) for c in calls.values()})],
        'limitations':['Sixteen isolated points per draw, not an image or a full particle-shape assessment.',
            'Exact dimensions and three nonzero texture witnesses identify the asset; they do not validate every GPU texel.',
            'No measured change would not prove absence outside the sampled points.',
            'Diagnostic synchronization overhead excludes this run from performance acceptance.'],
        'credit':json.loads((REF/'sky-pixel-probe-build.json').read_text())['credit']}
    (run/'arc-pass-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:(len(v) if k in ('incomplete_pairs','unassigned_draws','changed_frames') else v)
        for k,v in report.items() if k in ('draws','frames','events','complete_pairs','changed_frames',
        'incomplete_pairs','unassigned_draws','changed_draws','changed_points','max_abs_rgb_delta')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    run.relative_to(REPO/'work/sky-bridge')
    analyze(run)
