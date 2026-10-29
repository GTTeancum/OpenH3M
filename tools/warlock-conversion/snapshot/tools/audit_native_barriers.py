"""Inspect original H3 unrendered collision surfaces and their physics keys.

This is serialized-data evidence, not a runtime barrier acceptance test.
In particular the Invisible surface flag is not used to identify a boundary.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from audit_forge_camera_collision import retail_mesh
from cache_reader import Cache
from forge_collision_mesh import positions, surface_loops
from forge_mopp import terminals


def audit(path):
    c = Cache(path)
    try:
        root = next(t['offset'] for t in c.tags.values() if t['group'] == 'sbsp')
        arrays = retail_mesh(c)
        xyz, loops = positions(arrays), surface_loops(arrays)
        mappings = c.block(root+0x54, 4)
        if len(mappings) != len(arrays[5]):
            raise ValueError('Surface/render-mapping counts differ')
        surface_keys = defaultdict(set)
        instance_keys = set()
        for row in c.block(root+0x288, 64):
            size, pointer = c.unpack('II', row+48)
            offset = c.pointer(pointer)
            for _, _, key in terminals(c.data[offset:offset+size]):
                kind, subshape, index = key >> 29, (key >> 16) & 7, key & 65535
                if key & 0x1ff80000:
                    raise ValueError('Unexpected retail shape-key bits')
                if kind == 1:
                    if index >= len(arrays[5]):
                        raise ValueError('Physics key outside surface table')
                    surface_keys[index].add(subshape)
                elif kind == 2:
                    if index >= c.u(root+0x1b0):
                        raise ValueError('Physics key outside instance table')
                    instance_keys.add(index)
                else:
                    raise ValueError('Unknown main BSP physics shape class')
        unrendered = [i for i, row in enumerate(mappings)
                      if c.unpack('H', row+2)[0] == 0]
        null_material = [i for i in unrendered if arrays[5][i][2] == 65535]
        largest = sorted(null_material, key=lambda i: float(
            ((xyz[loops[i]].max(0)-xyz[loops[i]].min(0))**2).sum()), reverse=True)[:8]
        return {
            'map': str(Path(path).resolve()),
            'sha256': hashlib.file_digest(c.file, 'sha256').hexdigest(),
            'main_surface_count': len(arrays[5]),
            'zero_render_mapping_count': len(unrendered),
            'zero_mapping_null_material_count': len(null_material),
            'null_material_physics_subshape_patterns': dict(Counter(
                ','.join(map(str, sorted(surface_keys[i]))) or 'none' for i in null_material)),
            'instance_keys_referenced': len(instance_keys),
            'largest_unrendered_null_material_surfaces': [
                {'surface': i, 'flags': arrays[5][i][5],
                 'vertex_count': len(loops[i]), 'physics_subshapes': sorted(surface_keys[i]),
                 'bounds': [xyz[loops[i]].min(0).tolist(), xyz[loops[i]].max(0).tolist()]}
                for i in largest],
            'runtime_containment_verified': False,
        }
    finally:
        c.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--maps', type=Path, nargs='+', required=True)
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    result = [audit(path) for path in args.maps]
    args.report.write_text(json.dumps(result, indent=2)+'\n')
    for entry in result:
        print(Path(entry['map']).name, entry['zero_mapping_null_material_count'],
              entry['null_material_physics_subshape_patterns'])
