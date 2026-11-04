"""Attribute sparse depth changes to emitted draws; retain gaps and probe limits."""
import argparse
import array
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import struct

REF = Path(__file__).resolve().parent
REPO = REF.parents[4]
ALBEDO = {8562590739555380577, 6159915361788144154}
STATIC = {12021865740332317413, 17893540736724855907}
POINTS = {(501, 175), (503, 173), (497, 178), (711, 197)}


def packets(path):
    with path.open('rb') as stream:
        while header := stream.read(8):
            assert len(header) == 8
            kind, size = struct.unpack('<II', header)
            assert size <= 1024 * 1024
            data = stream.read(size)
            assert len(data) == size
            yield kind, data


def depth(bits):
    return struct.unpack('<f', struct.pack('<I', bits))[0]


def analyze(run):
    run = run.resolve()
    run.relative_to(REPO / 'work/sky-bridge')
    calls = {c['sequence']: c for c in json.loads((run / 'model-draw-calls.json').read_text())['calls']}
    pose = json.loads((REF / 'candidate32-flicker-reproduction-view.json').read_text())
    expected_cameras = {bytes.fromhex(c)[:128].hex() for c in pose['recorded_vertex_constants_0_18']}
    assert len(expected_cameras) == 1
    programs = json.loads((run / 'program-slice-matches.json').read_text())
    materials = {p['shader']: {m['id'] for s in p['matches'] for program in s['programs']
        for t in program['templates'] for m in t['materials']} for p in programs}
    geometry = defaultdict(dict)
    for prefix in json.loads((run / 'geometry-prefix-matches.json').read_text())['matches']:
        for candidate in prefix['matches']:
            if candidate['index_count'] * 2 == prefix['length']:
                key = candidate['owner'], candidate['mesh'], candidate['part']
                geometry[prefix['address']][key] = candidate
    prefixes = defaultdict(set)
    for kind, raw in packets(run / 'draws.bin'):
        if kind == 6:
            _, address, _, _ = struct.unpack('<4Q', raw)
        elif kind == 7:
            prefixes[address].add(hashlib.sha256(raw).hexdigest())
    regs = array.array('I', [0]) * 0x5003
    states = {}
    for kind, raw in packets(run / 'draws.bin'):
        if kind == 1:
            seq, frame, _, vs, ps, primitive, count, address, length, fmt, endian = struct.unpack('<11Q', raw)
        elif kind == 2:
            for index, value in struct.iter_unpack('<II', raw):
                regs[index] = value
        elif kind == 5:
            assert struct.unpack('<2Q', raw) == (seq, frame)
            c = calls[seq]
            assert (c['frame'], c['vs'], c['ps'], c['index_count']) == (frame, vs, ps, count)
            vertex_address = regs[0x48be] & ~3
            matches = [g for g in geometry[address].values() if g['index_count'] == count
                and g['target_material'] in materials.get(ps, set())
                and prefixes.get(vertex_address) == {g['vertex_prefix_sha256']}]
            camera = regs[0x4000:0x4020].tobytes().hex()
            states[seq] = dict(**c, geometry_candidates=matches, index_address=address,
                vertex_address=vertex_address, index_prefix_sha256=sorted(prefixes.get(address, [])),
                vertex_prefix_sha256=sorted(prefixes.get(vertex_address, [])),
                camera_exact=camera in expected_cameras, camera_constants_0_7=camera,
                model_constants_16_18=regs[0x4040:0x404c].tobytes().hex(),
                registers={hex(i): hex(regs[i]) for i in
                    [0x2000, 0x2002, 0x2104, 0x2200, 0x2208, *range(0x2080, 0x2083),
                     *range(0x2100, 0x2104), *range(0x210f, 0x2115)]})
    records = {}
    events = Counter()
    excluded = []
    with (run / 'depth-values.csv').open(newline='') as stream:
        for row in csv.DictReader(stream):
            event = row.pop('event')
            events[event] += 1
            row = {k: int(v) for k, v in row.items()}
            if event != 'sample':
                excluded.append(dict(event=event, **row))
                continue
            c = calls[row['sequence']]
            assert (c['frame'], c['ps'], c['index_count']) == (row['frame'], row['shader'], row['index_count'])
            assert row['phase'] in (0, 1) and row['samples'] in (1, 2, 4)
            assert 0 <= row['sample'] < row['samples'] and math.isfinite(depth(row['depth_bits']))
            metadata = {k: v for k, v in row.items() if k not in ('x', 'y', 'sample', 'depth_bits')}
            record = records.setdefault(row['record'], dict(metadata=metadata, points={}))
            assert record['metadata'] == metadata
            point = row['x'], row['y'], row['sample']
            assert point not in record['points']
            record['points'][point] = row['depth_bits']
    assert records
    assert set(records) == set(range(len(records)))
    paired = defaultdict(dict)
    for record in records.values():
        m = record['metadata']
        assert record['points'].keys() == {(x, y, s) for x, y in POINTS for s in range(m['samples'])}
        assert m['phase'] not in paired[m['sequence']]
        paired[m['sequence']][m['phase']] = record
    intervals, missing = [], []
    for frame in sorted({c['frame'] for c in calls.values()}):
        model_calls = [c for c in calls.values() if c['frame'] == frame
            and any(p['owner'] == 10122 for p in c['candidates'])]
        albedo = [c for c in model_calls if c['ps'] in ALBEDO]
        static = [c for c in model_calls if c['ps'] in STATIC]
        if not albedo or not static:
            missing.append(dict(frame=frame, reason='Searchlight interval endpoints absent from CPU trace'))
            continue
        start = max(c['sequence'] for c in albedo)
        end = min(c['sequence'] for c in static)
        assert start < end
        first, last = paired[start].get(1), paired[end].get(0)
        if first is None or last is None:
            missing.append(dict(frame=frame, albedo_sequence=start, static_sequence=end,
                reason='Depth recording limit or skipped endpoint',
                has_albedo_after=first is not None, has_static_before=last is not None))
            continue
        rows = [r for number, r in sorted(records.items())
            if first['metadata']['record'] <= number <= last['metadata']['record']]
        transitions = []
        for previous, current in zip(rows, rows[1:]):
            a, b = previous['metadata'], current['metadata']
            same_resource = all(a[k] == b[k] for k in ('resource', 'format', 'width', 'height', 'samples'))
            changes = []
            if previous['points'].keys() == current['points'].keys():
                for p, old in previous['points'].items():
                    new = current['points'][p]
                    if old != new:
                        changes.append(dict(x=p[0], y=p[1], sample=p[2], before_bits=old,
                            after_bits=new, before=depth(old), after=depth(new)))
            if not changes and same_resource:
                continue
            is_draw = a['sequence'] == b['sequence'] and a['phase'] == 0 and b['phase'] == 1
            transitions.append(dict(kind='actual_draw' if is_draw else 'between_samples',
                from_sequence=a['sequence'], from_phase=a['phase'], to_sequence=b['sequence'],
                to_phase=b['phase'], same_resource=same_resource, changes=changes,
                writer=states[b['sequence']] if is_draw else None))
        endpoints = [dict(x=p[0], y=p[1], sample=p[2], before_bits=v,
            after_bits=last['points'][p], before=depth(v), after=depth(last['points'][p]))
            for p, v in sorted(first['points'].items())]
        intervals.append(dict(frame=frame, albedo_sequence=start, static_sequence=end,
            records=len(rows), resource=first['metadata']['resource'], points=endpoints,
            transitions=transitions,
            excluded_sequences=sorted({p['sequence'] for p in excluded if start < p['sequence'] < end})))
    report = dict(run=str(run.relative_to(REPO)), events=dict(events), records=len(records),
        cpu_draws=len(calls), cpu_frames=len({c['frame'] for c in calls.values()}),
        depth_frames=sorted({r['metadata']['frame'] for r in records.values()}),
        complete_pairs=sum(set(p) == {0, 1} for p in paired.values()),
        incomplete_pairs=[s for s, p in paired.items() if p and set(p) != {0, 1}],
        intervals=intervals, missing_intervals=missing,
        recording_configuration_correction={
            'original_pixel_probe_field': json.loads((run / 'recording-configuration.json').read_text())['pixel_probe'],
            'actual_pixel_probe': False, 'pixel_files_present': [p.name for p in run.glob('pixels*')],
            'reason': 'Writer mode explicitly removes OPENH3M_SKY_PIXEL_PROBE_DIR; original configuration field omitted this mode.'},
        evidence_sha256={name: hashlib.sha256((run / name).read_bytes()).hexdigest() for name in
            ('draws.bin', 'depth-values.csv', 'model-draw-calls.json', 'geometry-prefix-matches.json',
             'program-slice-matches.json', 'recording-configuration.json', 'experiment.json')},
        limitations=[
            'Four fixed locations are sparse stored-depth evidence, not a complete image or fragment output.',
            'Actual-draw attribution requires the same resource and paired before/after samples.',
            'Between-sample changes may include unsampled draws, render-target transfers or clears.',
            'Skipped scopes and depth-record limits remain explicit; CPU frame count is not depth coverage.',
            'A closer metal surface is consistent with occlusion; this does not prove authored geometry or visual correctness.',
            'The measured searchlight is not conclusively identified as the protrusion in the human report.',
            'Replay matches the saved view, not full simulation or animation phase.'], credit=pose['credit'])
    (run / 'depth-writer-analysis.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('events', 'records', 'cpu_draws', 'cpu_frames', 'depth_frames',
        'complete_pairs', 'incomplete_pairs', 'missing_intervals')}))
    for interval in intervals:
        print(json.dumps(dict(frame=interval['frame'], records=interval['records'],
            transitions=[dict(kind=t['kind'], sequence=t['to_sequence'], same_resource=t['same_resource'],
                points=len(t['changes']), geometry=t['writer']['geometry_candidates'] if t['writer'] else [],
                camera_exact=t['writer']['camera_exact'] if t['writer'] else None) for t in interval['transitions']])) )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    analyze(parser.parse_args().run)
