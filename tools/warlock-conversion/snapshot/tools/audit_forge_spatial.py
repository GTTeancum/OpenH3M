"""Independent spatial probes of rebuilt and visibility-overlaid collision."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from cache_reader import Cache
from forge_collision_mesh import read_mesh
from rebuild_forge_collision import read_result


def retail_leaf(arrays, point):
    node = 0
    while node < 0x800000:
        packed = arrays[0][node][0]
        plane_index = packed & 65535
        if plane_index >= 32768:
            raise ValueError('Node plane would sign-extend negative on original H3')
        plane = arrays[1][plane_index]
        side = sum(point[k]*plane[k] for k in range(3)) >= plane[3]
        node = (packed >> (40 if side else 16)) & 0xffffff
    return None if node == 0xffffff else node & 0x7fffff


def audit(source_path, work):
    cache = Cache(source_path, True)
    try:
        tag, source = read_mesh(cache)
        source_clusters = bytes(cache.data[row] for row in cache.block(tag['offset']+0x34, 1))
        base_path, output_path = work/'collision.output', work/'collision-overlaid.output'
        base, output = read_result(base_path), read_result(output_path)
        clusters = (work/'collision-clusters.bin').read_bytes()
        if len(clusters) != len(output[2]):
            raise ValueError('Leaf/cluster table mismatch')
        points = []
        for index, surface in enumerate(output[5]):
            edge, seen, vertices = surface[1], set(), []
            while edge not in seen:
                seen.add(edge)
                row = output[6][edge]
                vertices.append(output[7][row[0] if row[4] == index else row[1]][:3])
                edge = row[2] if row[4] == index else row[3]
            plane = output[1][surface[0] & 32767]
            normal = np.asarray(plane[:3]) * (-1 if surface[0] & 32768 else 1)
            points.append(np.mean(vertices, axis=0) + normal*.05)
        points.extend(np.random.default_rng(20261021).uniform([-150, -300, 0], [50, -60, 40], (5000, 3)))
        solid_errors, cluster_errors, checked = 0, 0, 0
        examples = []
        for point in points:
            old, new = retail_leaf(base, point), retail_leaf(output, point)
            solid_errors += (old is None) != (new is None)
            node = 0
            while node >= 0:
                pi, back, front = source[0][node]
                plane = source[1][pi]
                node = front if sum(point[k]*plane[k] for k in range(3)) >= plane[3] else back
            if node != -1 and new is not None:
                checked += 1
                expected = source_clusters[node & 0x7fffffff]
                if clusters[new] != expected:
                    cluster_errors += 1
                    if len(examples) < 10:
                        examples.append({'point': list(point), 'expected': expected, 'actual': clusters[new]})
        return {'samples': len(points), 'nonsolid_cluster_checks': checked,
                'solid_mismatches': int(solid_errors), 'cluster_mismatches': cluster_errors,
                'examples': examples, 'output_sha256': hashlib.sha256(output_path.read_bytes()).hexdigest(),
                'scope': 'Polygon-offset and deterministic random probes, not exhaustive space or native behavior'}
    finally:
        cache.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--work', type=Path, default=Path('work/forge-world/temp'))
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.source, args.work)
    args.report.write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
    raise SystemExit(bool(result['solid_mismatches'] or result['cluster_mismatches']))
