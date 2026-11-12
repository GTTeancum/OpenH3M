"""Recover Reach MCC water UVs without fabricating Halo 3 local-info fields.

Reflection's format-27 allocation advertises 24 bytes per corner, but its
meaningful payload is float2 UVs packed at eight-byte corner offsets. Original
format-26 pairs retain the mapping from triangle corners to water vertices.
This helper validates that equivalence before returning an indexed UV table.
It is deliberately not a complete native H3 water-parameter converter.
"""
import math
import struct


def recover_water_uvs(payload, allocated_count, corner_indices, triangle_payload):
    if allocated_count < 0 or len(payload) != allocated_count * 24:
        raise ValueError('Unexpected Reach MCC water parameter allocation')
    if len(triangle_payload) % 12:
        raise ValueError('Water triangle payload is not complete triangles')
    pairs = list(struct.iter_unpack('<HH', triangle_payload))
    if len(corner_indices) != len(pairs) or not pairs:
        raise ValueError('Water corners and original triangle pairs disagree')
    uv_by_index = {}
    occupied = bytearray(len(payload))
    for corner, (_, water_index) in zip(corner_indices, pairs):
        if not 0 <= corner < allocated_count:
            raise ValueError('Water corner exceeds parameter allocation')
        start = corner * 8
        uv_bytes = bytes(payload[start:start + 8])
        if not all(math.isfinite(v) for v in struct.unpack('<2f', uv_bytes)):
            raise ValueError('Nonfinite water UV')
        if water_index in uv_by_index and uv_by_index[water_index] != uv_bytes:
            raise ValueError('Conflicting UVs for the same original water index')
        uv_by_index[water_index] = uv_bytes
        occupied[start:start + 8] = b'\1' * 8
    if any(value and not used for value, used in zip(payload, occupied)):
        raise ValueError('Unexplained nonzero water data outside packed UV corners')
    if set(uv_by_index) != set(range(max(uv_by_index) + 1)):
        raise ValueError('Sparse original water indices require explicit handling')
    return b''.join(uv_by_index[i] for i in range(len(uv_by_index)))
