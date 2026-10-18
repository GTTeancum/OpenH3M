"""Convert MCC primary world/rigid/skinned payloads to retail Xbox streams.

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
    if fmt == 24:
        if count < 0 or stride != 20 or len(payload) != count * 20:
            raise ValueError('Decorator mesh payload size mismatch')
        raw = np.frombuffer(payload, dtype=np.uint8).reshape(count, 20)
        out = np.zeros((count, 16), dtype=np.uint8)
        out[:, :12] = raw[:, :12].reshape(count, 6, 2)[:, :, ::-1].reshape(count, 12)
        xyz = np.frombuffer(payload, dtype='<i2').reshape(count, 10)[:, 6:9]
        out[:, 12:16] = pack_basis(xyz)
        return out.tobytes(), 16
    if fmt == 20:
        # TinyPosition: ushort3 position, ushort model/scale, biased/reversed
        # byte4 orientation, packed color. Model selection stays in variant.
        if count < 0 or stride != 16 or len(payload) != count * 16:
            raise ValueError('Decorator instance payload size mismatch')
        raw = np.frombuffer(payload, dtype=np.uint8).reshape(count, 16)
        out = np.empty_like(raw)
        out[:, :8] = raw[:, :8].reshape(count, 4, 2)[:, :, ::-1].reshape(count, 8)
        normal = raw[:, 8:12][:, ::-1].astype(np.int16) - 127
        if np.any(normal > 127):
            raise ValueError('Decorator orientation exceeds signed-normalized range')
        out[:, 8:12] = normal.astype(np.int8).view(np.uint8)
        out[:, 12:16] = raw[:, 12:16][:, ::-1]
        return out.tobytes(), 16
    auxiliary = {4: (4, 2), 6: (20, 4), 9: (4, None), 10: (4, None), 11: (24, None),
                 14: (12, 4)}
    # Water formats 27/28 require mesh context. MCC's format-27 allocation
    # advertises 36-byte vertices but packs meaningful corner data at 24 bytes;
    # see water_buffers.py. Neither water allocation can be copied directly.
    if fmt in auxiliary:
        source_stride, unit = auxiliary[fmt]
        if count < 0 or stride != source_stride or len(payload) != count * stride:
            raise ValueError('Auxiliary vertex payload size mismatch')
        raw = np.frombuffer(payload, dtype=np.uint8).reshape(count, stride)
        if unit:
            return raw.reshape(count, stride // unit, unit)[:, :, ::-1].tobytes(), stride
        if fmt == 9:
            # MCC stores one float; retail stores an unsigned-normalized byte
            # in a four-byte vertex slot (remaining components are padding).
            values = np.frombuffer(payload, dtype='<f4')
            if not np.all(np.isfinite(values)) or np.any((values < 0) | (values > 1)):
                raise ValueError('Ambient PRT coefficient outside normalized range')
            out = np.zeros((count, 4), dtype=np.uint8)
            out[:, 0] = np.rint(values * 255).astype(np.uint8)
            return out.tobytes(), 4
        if fmt == 10:
            # MCC TinyNormal reverses the component order and biases by 127;
            # retail reads four signed-normalized bytes directly.
            values = raw[:, ::-1].astype(np.int16) - 127
            if np.any(values > 127):
                raise ValueError('Linear PRT coefficient exceeds signed-normalized range')
            return values.astype(np.int8).tobytes(), 4
        # Quadratic PRT uses three signed 10:10:10 vectors, not the primary
        # normal stream's 10:11:11 format. Drop each MCC short4 padding component.
        values = np.frombuffer(payload, dtype='<i2').reshape(count, 3, 4)[:, :, :3]
        quantized = np.rint(np.clip(values.astype(float) / 32767, -1, 1) * 511).astype(np.int32)
        packed = np.zeros((count, 3), dtype=np.uint32)
        for axis in range(3):
            packed |= (quantized[:, :, axis].astype(np.uint32) & 1023) << (axis * 10)
        return packed.astype('>u4').tobytes(), 12
    expected = {1: (44, 32, 20, 4), 2: (36, 24, 12, 2), 3: (44, 32, 12, 2)}
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
    if fmt == 3:
        # Four byte-sized bone indices followed by four byte-sized weights.
        # These are not packed integers and must not be endian-reversed.
        out[:, 24:32] = raw[:, 36:44]
    return out.tobytes(), target_stride


def convert_indices(payload):
    if len(payload) % 2:
        raise ValueError('16-bit index payload has an odd byte count')
    return np.frombuffer(payload, dtype='<u2').astype('>u2').tobytes()
