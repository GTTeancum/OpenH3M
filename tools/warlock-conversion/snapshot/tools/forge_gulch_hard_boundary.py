"""Unrendered retail collision divider, independent of soft-ceiling forces."""
import struct
import numpy as np
from forge_gulch_boundary import BOUNDARY

BOTTOM, TOP = -152., 190.


def append_surfaces(arrays):
    """Append two-sided triangles; preserve all retained surface/edge indices."""
    start, edge_start = len(arrays[5]), len(arrays[6])
    for p, q in zip(BOUNDARY, BOUNDARY[1:]):
        a, b = np.array([*p, BOTTOM]), np.array([*q, BOTTOM])
        c, d = b+[0, 0, TOP-BOTTOM], a+[0, 0, TOP-BOTTOM]
        for triangle in ((a, c, d), (a, b, c)):
            normal = np.cross(triangle[1]-triangle[0], triangle[2]-triangle[0])
            normal /= np.linalg.norm(normal)
            plane = len(arrays[1])
            arrays[1].append(tuple(float(v) for v in np.asarray(
                [*normal, float(normal @ triangle[0])], dtype=np.float32)))
            face, edge, vertex = len(arrays[5]), len(arrays[6]), len(arrays[7])
            # Native flags: TwoSided=1. No render or physical-material binding.
            arrays[5].append((plane, edge, -1, -1, -1, 1, 0))
            for j, position in enumerate(triangle):
                arrays[7].append((*position, edge+j, -1))
                arrays[6].append((vertex+j, vertex+(j+1)%3,
                                  edge+(j+1)%3, edge+(j+2)%3, face, 65535))
    if any(len(arrays[i]) >= limit for i, limit in ((1,32768),(5,32767),(6,65535),(7,65535))):
        raise ValueError('Hard divider exceeds retail collision index limits')
    return {'surface_first': start, 'surface_count': len(arrays[5])-start,
            'edge_first': edge_start, 'edge_count': len(arrays[6])-edge_start,
            'bottom': BOTTOM, 'top': TOP, 'native_behavior_verified': False}


def extend_mopp(code, info, world_z, divider):
    """Conservative 16-surface branch; retain the authored tree byte-for-byte.

    MOPP's initial byte-coordinate domain is Info.xyz + [0, 2**24/Info.w].
    Overlapping SPLIT_Z tests cover both paths across the complete BSP Z bounds.
    Divider triangles become extra candidates, then normal native collision
    performs the exact test. This trades 16 candidates/query for avoiding a
    rebuild of the authored terrain/instance acceleration tree.
    """
    from forge_mopp import terminals
    from collections import Counter
    z0, scale = info[2], info[3]
    if not scale > 0 or not z0 < world_z[0] <= world_z[1] < z0+255*65536/scale:
        raise ValueError('BSP Z bounds outside conservative MOPP branch domain')
    keys = [(13 << 26) | i for i in range(divider['surface_first'],
                                          divider['surface_first']+divider['surface_count'])]
    # Each terminal has its own absolute key base. Branch-local state leaves
    # the original subtree's initial base and coordinate scale untouched.
    extra = b''
    for key in reversed(keys):
        terminal = b'\x0b'+struct.pack('>I', key)+b'\x30'
        extra = b'\x12\xff\x00\x06'+terminal+extra if extra else terminal
    # First branch jumps over added terminals; second branch visits them.
    out = b'\x12\xff\x00\x04\x07'+len(extra).to_bytes(3,'big')+extra+code
    expected = Counter(key for _, _, key in terminals(code)) + Counter(keys)
    if Counter(key for _, _, key in terminals(out)) != expected:
        raise ValueError('Divider MOPP changed original reachable physics keys')
    return out
