"""Verify serialized split geometry and native scenario soft-ceiling bindings."""
import argparse
from collections import Counter
import json
from pathlib import Path
import numpy as np
from cache_reader import Cache
from string_ids import StringTable
from forge_gulch_boundary import BOUNDARY


def audit(path):
    c = Cache(path)
    try:
        strings = StringTable(c)
        scenario = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
        flags = {strings.text(c.u(r+4)): c.unpack('HH', r) for r in c.block(scenario+0x23c, 12)}
        results = []
        for tag in c.tags.values():
            if tag['group'] != 'sddt':
                continue
            for ceiling in c.block(tag['offset']+16, 20):
                rows = c.block(ceiling+8, 68)
                if len(rows) != 442+2*(len(BOUNDARY)-1):
                    continue
                name = strings.text(c.u(ceiling))
                if flags[name] != (0, 0) or c.unpack('hh', ceiling+4) != (0, 0):
                    raise ValueError('Split must use acceleration and ignore no object categories')
                original = np.array([c.unpack('17f', r) for r in rows[:442]])
                shell = original[:, 8:].reshape(-1, 3, 3)
                edges = Counter()
                for triangle in shell:
                    vertices = [tuple(np.round(v, 4)) for v in triangle]
                    for a, b in zip(vertices, vertices[1:]+vertices[:1]):
                        edges[tuple(sorted((a, b)))] += 1
                if any(count != 2 for count in edges.values()):
                    raise ValueError('Outer containment shell is not closed')
                mins, maxs = shell.reshape(-1, 3).min(0), shell.reshape(-1, 3).max(0)
                if not BOUNDARY[0][0] < mins[0]-4 < maxs[0]+4 < BOUNDARY[-1][0]:
                    raise ValueError('Split endpoints do not overlap the outer shell')
                for index, row in enumerate(rows[442:]):
                    values = c.unpack('17f', row)
                    normal, distance = np.array(values[:3]), values[3]
                    vertices = np.array(values[8:]).reshape(3, 3)
                    derived = np.cross(vertices[1]-vertices[0], vertices[2]-vertices[0])
                    derived /= np.linalg.norm(derived)
                    if normal[1] >= 0 or not np.allclose(normal, derived, atol=1e-6):
                        raise ValueError('Split triangle winding/normal mismatch')
                    if max(abs(vertices @ normal-distance)) > 1e-4:
                        raise ValueError('Split triangle plane does not contain its vertices')
                    start, end = BOUNDARY[index//2:index//2+2]
                    if any(not any(np.allclose(v[:2], p) for p in (start, end)) for v in vertices):
                        raise ValueError('Split triangle deviates from authorized curved boundary')
                    if vertices[:, 2].min() > mins[2]-4 or vertices[:, 2].max() < maxs[2]+4:
                        raise ValueError('Split does not overlap the outer shell vertically')
                codes = c.block(tag['offset']+4, 64)
                if len(codes) != 1 or not c.u(codes[0]+48):
                    raise ValueError('Split has no compiled native acceleration tree')
                results.append({'name': name, 'boundary_triangles': len(rows)-442,
                                'outer_shell_closed': True, 'outer_bounds': [mins.tolist(), maxs.tolist()],
                                'ignore_flags': flags[name], 'mopp_bytes': c.u(codes[0]+48)})
        if len(results) != 1:
            raise ValueError('Expected exactly one Gulch containment design')
        return {'serialized_geometry': results, 'native_behavior_verified': False}
    finally:
        c.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate', required=True)
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    result = audit(args.candidate)
    args.report.write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
