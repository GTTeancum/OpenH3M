"""Verify serialized split geometry and native scenario soft-ceiling bindings."""
import argparse
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
                    if set(vertices[:, 2]) != {-40., 160.}:
                        raise ValueError('Split vertical extent differs')
                codes = c.block(tag['offset']+4, 64)
                if len(codes) != 1 or not c.u(codes[0]+48):
                    raise ValueError('Split has no compiled native acceleration tree')
                results.append({'name': name, 'boundary_triangles': len(rows)-442,
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
