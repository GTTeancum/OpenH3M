"""Compare a recorded observer path with source/native main-BSP surfaces.

Camera points are not vehicle centers. Instance collision and swept vehicle
shapes are excluded, so this cannot certify gameplay collision/containment.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

import numpy as np
from cache_reader import Cache
from forge_collision_mesh import read_mesh, surface_loops, positions
from resource_reader import Resource


def retail_mesh(cache):
    root = next(t['offset'] for t in cache.tags.values() if t['group'] == 'sbsp')
    r = Resource(cache, cache.u(root+0x37c))
    if r.unpack('I', r.root)[0] != 1:
        raise ValueError('Expected one retail main collision BSP')
    header = r.ptr(r.root+4)
    arrays = [[] for _ in range(8)]
    for slot, fmt in ((5, '5H2B'), (6, '6H'), (7, '3f2H')):
        at = header+slot*12
        count = r.unpack('I', at)[0]
        ptr = r.fix[at+4]
        segment, offset = ptr >> 29, ptr & 0x1fffffff
        data = r.data if segment == 1 else r.raw[segment-2]
        arrays[slot] = list(struct.iter_unpack('>'+fmt, data[offset:offset+count*struct.calcsize('>'+fmt)]))
    arrays[6] = [tuple(-1 if v == 65535 else v for v in row) for row in arrays[6]]
    return arrays


def corridor_triangles(arrays, low, high):
    xyz, triangles, owners = positions(arrays), [], []
    for index, loop in enumerate(surface_loops(arrays)):
        polygon = xyz[loop]
        if np.any(polygon.min(axis=0) > high) or np.any(polygon.max(axis=0) < low):
            continue
        for j in range(1, len(loop)-1):
            triangles.append(xyz[[loop[0], loop[j], loop[j+1]]])
            owners.append(index)
    return np.asarray(triangles).reshape(-1, 3, 3), owners


def crossings(triangles, owners, track):
    v0, e1, e2 = triangles[:, 0], triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0]
    result = []
    for p, q in zip(track, track[1:]):
        start = np.array(p['position'])
        direction = np.array(q['position'])-start
        h = np.cross(np.broadcast_to(direction, e2.shape), e2)
        determinant = (e1*h).sum(axis=1)
        valid = abs(determinant) > 1e-9
        inverse = np.divide(1, determinant, out=np.zeros_like(determinant), where=valid)
        s = start-v0
        u = inverse*(s*h).sum(axis=1)
        cross = np.cross(s, e1)
        v, t = inverse*(cross*direction).sum(axis=1), inverse*(e2*cross).sum(axis=1)
        for index in np.where(valid & (u >= -1e-6) & (v >= -1e-6) & (u+v <= 1.000001) & (t > 1e-6) & (t <= 1))[0]:
            result.append({'seconds': p['seconds']+float(t[index])*(q['seconds']-p['seconds']),
                           'position': (start+t[index]*direction).tolist(), 'surface': owners[index]})
    return result


def audit(source_path, candidate_path, trace_path, start_seconds):
    trace = [json.loads(v) for v in Path(trace_path).read_text().splitlines()]
    track = [v for v in trace if v['event'] == 'observer_position' and v['seconds'] >= start_seconds]
    if len(track) < 2:
        raise ValueError('Insufficient observer samples')
    points = np.asarray([v['position'] for v in track])
    low, high = points.min(axis=0)-1, points.max(axis=0)+1
    source, target = Cache(source_path, True), Cache(candidate_path)
    try:
        meshes = {'source': read_mesh(source)[1], 'candidate': retail_mesh(target)}
        report = {'scope': __doc__, 'start_seconds': start_seconds, 'samples': len(track),
                  'source_sha256': hashlib.sha256(source.data).hexdigest(),
                  'candidate_sha256': hashlib.sha256(target.data).hexdigest(),
                  'trace_sha256': hashlib.sha256(Path(trace_path).read_bytes()).hexdigest(), 'runs': {}}
        canonical = {}
        for name, arrays in meshes.items():
            triangles, owners = corridor_triangles(arrays, low, high)
            canonical[name] = Counter(tuple(sorted(tuple(v) for v in triangle)) for triangle in triangles)
            report['runs'][name] = {'triangles_in_corridor': len(triangles), 'hits': crossings(triangles, owners, track)}
        report['corridor_triangle_positions_exact'] = canonical['source'] == canonical['candidate']
        return report
    finally:
        source.close()
        target.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'candidate', 'trace', 'report'):
        p.add_argument('--'+name, required=True, type=Path)
    p.add_argument('--start-seconds', type=float, default=140)
    args = p.parse_args()
    result = audit(args.source, args.candidate, args.trace, args.start_seconds)
    args.report.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
