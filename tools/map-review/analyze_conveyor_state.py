"""Summarize bounded native conveyor observations without changing the process."""
import argparse
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument('trace', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
trace, output = a.trace.resolve(), a.output.resolve()
assert trace.is_relative_to(ROOT) and output.is_relative_to(ROOT)
rows = [json.loads(line) for line in (trace/'loading-trace.jsonl').read_text().splitlines()]
observers = [r for r in rows if r['event'] == 'observer_position' and 110 <= r['seconds'] <= 189]
segments = []
for x,y in zip(observers, observers[1:]):
    dt = y['seconds'] - x['seconds']
    segments.append(dict(start=x['seconds'], end=y['seconds'], speed=(y['position'][0]-x['position'][0])/dt))
snapshots = []
previous = {}
phase_errors = []
for row in rows:
    if row['event'] != 'machine_crate_snapshot': continue
    machines = []
    for obj in row['objects']:
        if obj['tag'] != '0x900024f9': continue
        data = bytes.fromhex(obj['body'])
        if len(data) < 0x2d4: continue
        f = lambda off: struct.unpack_from('>f',data,off)[0]
        size, off = struct.unpack_from('>HH',data,0x13a)
        assert size == 156 and off == 0x238 and off+size <= len(data)
        origin = struct.unpack_from('>3f',data,0x54)
        position,velocity,frame,phase = [f(i) for i in (0x174,0x178,0x1d8,0x1dc)]
        phase_errors.append(max(abs(frame-phase*15), abs(position+phase-1)))
        node_x = f(off+52+40)
        item = dict(handle=obj['handle'], origin=origin, position=position, velocity=velocity,
                    animation_frame=frame, animation_phase=phase, support_node_x=node_x)
        old = previous.get(obj['handle'])
        if old:
            dt = row['seconds']-old['seconds']
            item['support_speed'] = (node_x-old['node_x'])/dt
        previous[obj['handle']] = dict(seconds=row['seconds'],node_x=node_x)
        machines.append(item)
    snapshots.append(dict(seconds=row['seconds'], machines=machines))
near_zero = [s for s in segments if abs(s['speed']) < .005]
report = dict(trace=str(trace.relative_to(ROOT)), observer_samples=len(observers),
    first=observers[0]['position'], last=observers[-1]['position'],
    near_zero_intervals=near_zero, segments=segments, snapshots=snapshots,
    max_phase_relation_error=max(phase_errors, default=None),
    semantics='Device position/velocity and animation frame/phase are inferred from layout and verified numeric relations. Node matrix block header validates three 52-byte transforms. A support node speed is not proof of the player contacting that particular shape.',
    completion='Telemetry only; visual captures must be inspected independently.')
output.write_text(json.dumps(report,indent=2))
print(json.dumps({k:report[k] for k in ('observer_samples','first','last','max_phase_relation_error')}))
print('Near-zero intervals:',len(near_zero))
