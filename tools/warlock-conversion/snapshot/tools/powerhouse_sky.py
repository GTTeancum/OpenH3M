"""Repair the authored far-storm quad's collapsed UV triangle, not its shape."""
import struct

MODEL = r'levels\multi\s3d_powerhouse\sky_settlement\sky_settlement'
STORM = r'levels\multi\s3d_powerhouse\sky_settlement\shaders\s3d_lighting_bolt'


def missing_corner(a, c, d):
    return tuple(a[i] + c[i] - d[i] for i in range(len(a)))


def repair_storm_uv(cache, model, source, converted):
    materials = [cache.name(cache.u(row + 12) & 65535)
                 for row in cache.block(model + 72, 36)]
    material = materials.index(STORM)
    parts = [(mesh, part) for mesh in cache.block(model + 104, 76)
             for part in cache.block(mesh, 16) if cache.unpack('h', part)[0] == material]
    if len(parts) != 1:
        raise ValueError('Powerhouse storm quad part changed')
    mesh, part = parts[0]
    first, count = cache.unpack('HH', part + 4)
    if (first, count) != (0, 8):
        raise ValueError('Powerhouse storm quad index range changed')

    def read_pointer(at, size):
        p = source.fix[at]
        segment = {0x40000000: 0, 0x60000000: 1}[p & 0xe0000000]
        start = p & 0x1fffffff
        return source.raw[segment][start:start + size]

    ib = source.buffers('index')[cache.unpack('h', mesh + 40)[0]]
    if struct.unpack('<8H', read_pointer(ib + 16, 16)) != (0, 1, 2, 2, 3, 3, 4, 5):
        raise ValueError('Powerhouse storm quad topology changed')
    slot = cache.unpack('h', mesh + 24)[0]
    vb = source.buffers('vertex')[slot]
    count, fmt, stride = source.unpack('IHH', vb)
    if (fmt, stride) != (2, 36) or count < 6:
        raise ValueError('Powerhouse storm vertex layout changed')
    raw = read_pointer(vb + 20, count * stride)
    rows = [struct.unpack_from('<6H', raw, j * stride) for j in range(6)]
    a, b, c, d = (rows[j] for j in (0, 1, 2, 5))
    if rows[2] != rows[3] or rows[0] != rows[4]:
        raise ValueError('Storm strip degenerates no longer share vertices')
    predicted = missing_corner(a[:3], c[:3], d[:3])
    if any(abs(x-y) > 2 for x, y in zip(predicted, b[:3])):
        raise ValueError('Storm geometry is no longer an affine quad')
    uv = missing_corner(a[4:6], c[4:6], d[4:6])
    if b[4:6] == uv:
        return None  # An upstream fix must not be applied twice.
    if b[4:6] != c[4:6] or not all(0 <= v <= 65535 for v in uv):
        raise ValueError('Storm UV defect differs from the isolated source defect')
    control = converted['control']
    fix = dict(converted['fixups'])
    table = fix[28] & 0x1fffffff
    descriptor = fix[table + slot * 12] & 0x1fffffff
    if struct.unpack_from('>IHH', control, descriptor) != (count, 2, 24):
        raise ValueError('Native storm vertex layout differs')
    start = fix[descriptor + 20] & 0x1fffffff
    target = bytearray(converted['raw'])
    struct.pack_into('>2H', target, start + 24 + 8, *uv)
    converted['raw'] = bytes(target)
    return {'vertex': 1, 'before_uv_packed': list(b[4:6]), 'after_uv_packed': list(uv),
            'equation': 'UV(B) = UV(A) + UV(C) - UV(D)', 'positions_unchanged': True}
