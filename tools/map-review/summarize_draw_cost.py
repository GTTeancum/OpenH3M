"""Rank bounded GPU timestamp draws; timings are diagnostic, not acceptance FPS."""
import collections
import csv
import json
import sys
from pathlib import Path
import xxhash

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache

path = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT / '.local/map-benchmarks/powerhouse-draw-cost/draw-gpu.csv'
assert path.is_relative_to(ROOT / '.local/map-benchmarks')
lines = path.read_text().splitlines()
assert any(l.startswith('# capture_complete=1') and 'capacity_hit=0' in l for l in lines), 'Capture not confirmed complete'
records = list(csv.DictReader(line for line in lines if not line.startswith('#')))
assert records, 'No GPU samples'
frames = sorted({int(r['frame']) for r in records})
assert len(frames) == 3, 'Expected three frames; do not analyze a partial capture'
# Arming may occur in the middle of frame one. Frames two and three are full.
selected = [r for r in records if int(r['frame']) != frames[0]]
cost = collections.defaultdict(lambda: dict(ms=0., draws=0, indices=0))
vertex_cost = collections.defaultdict(lambda: dict(ms=0., draws=0, indices=0))
for r in selected:
    ms = float(r['milliseconds']); assert ms >= 0
    row = cost[int(r['shader'])]
    row['ms'] += ms; row['draws'] += 1; row['indices'] += int(r['index_count'])
    if 'vertex_shader' in r:
        row = vertex_cost[int(r['vertex_shader'])]
        row['ms'] += ms; row['draws'] += 1; row['indices'] += int(r['index_count'])
c = Cache(ROOT / 'work/map-review-20261105/powerhouse-cache-order.map')
names = collections.defaultdict(list)
for index, tag in c.tags.items():
    if tag['group'] not in ('pixl', 'glps', 'vtsh', 'glvs'):
        continue
    offset = 20 if tag['group'] in ('pixl', 'vtsh') else 16
    for number, program in enumerate(c.block(tag['offset']+offset, 80)):
        pointer = c.u(program+76)
        if not pointer: continue
        header = c.pointer(pointer)
        debug = header + (0x368 if tag['group'] in ('vtsh', 'glvs') else 40)
        info = debug + c.u(debug+24)
        constants_size, size = c.unpack('II', info)
        start = c.pointer(c.u(header+16)) + constants_size
        assert size % 4 == 0 and 0 < size < 65536
        binary = bytes(c.data[start:start+size])
        for order, payload in [('stored', binary), ('word-swapped', b''.join(binary[i:i+4][::-1] for i in range(0,size,4)))]:
            key = xxhash.xxh3_64_intdigest(payload)
            if key in cost or key in vertex_cost:
                names[key].append(dict(tag=index, group=tag['group'], name=c.name(index), program=number, byte_order=order))
c.close()
ranking = [dict(shader=str(k), mean_ms_per_frame=v['ms']/2, draws_per_frame=v['draws']/2,
                indices_per_frame=v['indices']/2, programs=names[k]) for k,v in cost.items()]
ranking.sort(key=lambda r:r['mean_ms_per_frame'],reverse=True)
report = dict(frames=frames, discarded_partial_frame=frames[0], full_frames=frames[1:], ranking=ranking,
              footer=[l for l in lines if l.startswith('#')],
              scope='Two full instrumented frames. Query overhead/serialization and concurrent GPU workload affect these numbers; use for localization, not production FPS.')
report['vertex_ranking'] = sorted([dict(shader=str(k), mean_ms_per_frame=v['ms']/2, draws_per_frame=v['draws']/2,
    indices_per_frame=v['indices']/2, programs=names[k]) for k,v in vertex_cost.items()], key=lambda r:-r['mean_ms_per_frame'])
(ROOT / 'work/map-review-20261105' / (path.parent.name+'-summary.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(dict(pixel=ranking[:5],vertex=report['vertex_ranking'][:5]),indent=2))
