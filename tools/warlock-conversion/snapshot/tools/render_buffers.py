"""Convert MCC primary world/rigid geometry payloads to retail Xbox streams.

No metadata or resource table is written here. Unsupported formats fail rather
than preserving a PC-only stride. Resource assembly is a separate stage.
"""
import numpy as np


def pack_basis(components):
    """Convert MCC signed-normalized 16-bit XYZ to retail signed 10:11:11."""
    unit = np.maximum(components.astype(np.float64) / 32767.0, -1.0)
    packed = np.zeros(len(unit), dtype=np.uint32)
    for axis, (shift, bits) in enumerate(((0, 10), (10, 11), (21, 11))):
        limit = (1 << (bits - 1)) - 1
        quantized = np.rint(np.clip(unit[:, axis], -1, 1) * limit).astype(np.int32)
        packed |= (quantized.astype(np.uint32) & ((1 << bits) - 1)) << shift
    return packed.astype('>u4').view('u1').reshape(-1, 4)


def convert_vertices(payload, count, fmt, stride):
    expected = {1: (44, 32, 20, 4), 2: (36, 24, 12, 2)}
    if fmt not in expected:
        raise ValueError(f'Vertex format {fmt} needs a dedicated converter')
    source_stride, target_stride, prefix, unit = expected[fmt]
    if count < 0 or stride != source_stride or len(payload) != count * stride:
        raise ValueError('Vertex count, stride or payload size mismatch')
    raw = np.frombuffer(payload, dtype=np.uint8).reshape(count, stride)
    out = np.zeros((count, target_stride), dtype=np.uint8)
    # Preserve source positions and UV bit patterns; only reverse endian units.
    out[:, :prefix] = raw[:, :prefix].reshape(count, prefix // unit, unit)[:, :, ::-1].reshape(count, prefix)
    for channel in range(3):
        at = prefix + channel * 8
        xyz = np.ndarray((count, 3), dtype='<i2', buffer=payload, offset=at,
                         strides=(stride, 2)) if count else np.empty((0, 3), dtype='<i2')
        out[:, prefix + channel * 4:prefix + channel * 4 + 4] = pack_basis(xyz)
    return out.tobytes(), target_stride


def convert_indices(payload):
    if len(payload) % 2:
        raise ValueError('16-bit index payload has an odd byte count')
    return np.frombuffer(payload, dtype='<u2').astype('>u2').tobytes()
