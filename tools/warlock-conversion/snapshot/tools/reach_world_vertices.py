"""Reach MCC world vertices to original H3 Xbox world vertices.

Reach's 36-byte MCC layout: float4 position/handedness, half2 UV,
short4 normal, short4 tangent, matching the retained Reclaimer schema at
work/forge-world/variants/reference/MccHaloReachVertexBuffer.xml. Console Reach's corresponding semantic layout
is documented by TagTool VertexStreamReach.ReadWorldVertex (ce2dc6ac).
The resource converter uses this helper for world streams; Reach
lighting and water streams still require their own conversions.
"""
import numpy as np
from render_buffers import pack_unit_basis


def convert_world_vertices(payload, count):
    if count < 0 or len(payload) != count * 36:
        raise ValueError('Reach world vertex payload size mismatch')
    position = np.ndarray((count, 4), dtype='<f4', buffer=payload, strides=(36, 4))
    uv = np.ndarray((count, 2), dtype='<f2', buffer=payload, offset=16, strides=(36, 2))
    normal = np.ndarray((count, 3), dtype='<i2', buffer=payload, offset=20, strides=(36, 2)).astype(float)
    tangent = np.ndarray((count, 3), dtype='<i2', buffer=payload, offset=28, strides=(36, 2)).astype(float)
    if not np.all(np.isfinite(position)) or not np.all(np.isfinite(uv)):
        raise ValueError('Nonfinite Reach world position or UV')
    if np.any((position[:, 3] != 0) & (position[:, 3] != 1)):
        raise ValueError('Unsupported Reach tangent handedness')
    normal = np.clip(normal / 32767, -1, 1)
    tangent = np.clip(tangent / 32767, -1, 1)
    binormal = np.cross(normal, tangent) * (position[:, 3:4] * 2 - 1)
    result = np.zeros((count, 32), dtype=np.uint8)
    result[:, :12] = position[:, :3].astype('>f4').view(np.uint8).reshape(count, 12)
    result[:, 12:20] = uv.astype('>f4').view(np.uint8).reshape(count, 8)
    for offset, basis in ((20, normal), (24, tangent), (28, binormal)):
        result[:, offset:offset+4] = pack_unit_basis(basis)
    return result.tobytes()


