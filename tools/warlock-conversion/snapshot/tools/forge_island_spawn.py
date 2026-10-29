"""Relocate the authored Forge start onto verified terrain on the island."""
import struct
import math
import numpy as np
from forge_collision_mesh import read_mesh, surface_loops, positions
from forge_gulch_boundary import boundary_y

START_XY = (50., 50.)
# Face the open coast toward Sanctuary, rather than the adjacent island cliff.
FACING = math.atan2(200. - START_XY[1], 65. - START_XY[0])
MARKER = ('scen', r'objects\multi\spawning\initial_spawn_point')


def starting_position(source):
    _, arrays = read_mesh(source)
    xyz = positions(arrays)
    hits = []
    for index, loop in enumerate(surface_loops(arrays)):
        points = xyz[loop]
        if np.any(points[:, :2].min(0) > START_XY) or np.any(points[:, :2].max(0) < START_XY):
            continue
        surface = arrays[5][index]
        plane = np.array(arrays[1][surface[0] & 0x7fffffff])
        if surface[0] < 0:
            plane = -plane
        if plane[2] < 0.8:
            continue
        for i in range(1, len(points)-1):
            p, q, r = points[[0, i, i+1]]
            matrix = np.column_stack((q[:2]-p[:2], r[:2]-p[:2]))
            if abs(np.linalg.det(matrix)) < 1e-8:
                continue
            u, v = np.linalg.solve(matrix, np.array(START_XY)-p[:2])
            if min(u, v) >= -1e-6 and u+v <= 1+1e-6:
                z = (plane[3] - plane[0]*START_XY[0] - plane[1]*START_XY[1])/plane[2]
                hits.append((index, float(z)))
                break
    if len(hits) != 1 or not 14 < hits[0][1] < 16 or START_XY[1] <= boundary_y(START_XY[0]):
        raise ValueError(f'Island starting terrain changed: {hits}')
    return (*START_XY, hits[0][1] + 0.35)


def relocate_marker(importer, prepared, schema):
    from assemble_scenario import field
    position = starting_position(importer.source)
    importer.forge_island_start = position
    datum = importer.resolved[MARKER][1]
    count, original = prepared['arrays']['Scenery']
    payload = bytearray(original)
    palette = prepared['arrays']['Scenery Palette'][1]
    definition = field(schema, 'Scenery')
    stride = int(definition.get('elementSize'), 0)
    changed = []
    for index in range(count):
        at = index*stride
        pi = struct.unpack_from('>h', payload, at)[0]
        if struct.unpack_from('>I', palette, pi*48+12)[0] != datum:
            continue
        pos = at + int(field(definition, 'Position').get('offset'), 0)
        old = struct.unpack_from('>3f', payload, pos)
        struct.pack_into('>3f', payload, pos, *position)
        struct.pack_into('>3f', payload, at+int(field(definition, 'Rotation').get('offset'), 0), FACING, 0., 0.)
        changed.append({'original': old, 'position': position, 'clearance': 0.35})
    if len(changed) != 1:
        raise ValueError('Expected exactly one authored initial spawn marker')
    prepared['arrays']['Scenery'] = count, bytes(payload)
    return changed
