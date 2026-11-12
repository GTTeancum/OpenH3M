"""Bind an authored cube to both native dynamic-environment samplers.

The two samples then cancel the probe blend. Caller forces LOD0 and divides
environment tint by 256, undoing the native dynamic-probe radiance scale.
Only routing metadata changes; native vertex/pixel programs stay untouched.
Reference: HaloShaderGenerator 5af3671c919e93b802dd6aa0899f6725de70992c,
halo_online_shaders/environment_mapping.fx (xenon dynamic and per_pixel paths).
Native armory routing independently confirms cube samplers s1/s2, externs22/23.
"""
import struct


def bind_static_cube(materials, post, names):
    b, registry = materials.builder, materials.registry
    post = bytearray(post)
    datum = struct.unpack_from('>I', post, 12)[0]
    address = struct.unpack_from('>I', registry.tags, (datum & 65535) * 8 + 4)[0]
    root = bytearray(b.read(address, 132))
    if struct.unpack_from('>I', root, 120)[0]:
        raise ValueError('Static cube adapter does not support platform subtemplates')
    def rows(offset, stride):
        count, pointer = struct.unpack_from('>II', root, offset)
        return [bytes(b.read(pointer + j * stride, stride)) for j in range(count)]
    texture_names, constant_names = names
    if 'environment_map' in texture_names or len(texture_names) >= 255:
        raise ValueError('Unexpected native environment texture table')
    texture_index = len(texture_names)
    old_routes = rows(60, 4)
    routes, passes, converted = bytearray(), bytearray(), 0
    for original in rows(48, 28):
        p = bytearray(original)
        usages = []
        for usage in range(12):
            packed = struct.unpack_from('>H', p, usage * 2)[0]
            start, count = packed & 1023, packed >> 10
            if start + count > len(old_routes):
                raise ValueError('Native routing range outside table')
            usages.append(list(old_routes[start:start + count]))
        retained, moved = [], []
        for row in usages[7]:
            register, source, flags = struct.unpack('>HBB', row)
            if source in (22, 23):
                if (register, source, flags) not in ((1, 22, 0), (2, 23, 0)):
                    raise ValueError('Native dynamic cube register layout changed')
                moved.append(struct.pack('>HBB', register, texture_index, flags))
            else:
                retained.append(row)
        if moved and len(moved) != 2:
            raise ValueError('Native pass has only one dynamic cube sampler')
        converted += len(moved)
        usages[0].extend(moved)
        usages[7] = retained
        for usage, entries in enumerate(usages):
            start = len(routes) // 4
            if start > 1023 or len(entries) > 63:
                raise ValueError('Static cube routing exceeds native packed limits')
            struct.pack_into('>H', p, usage * 2, start | len(entries) << 10)
            routes.extend(b''.join(entries))
        passes.extend(p)
    if not converted:
        raise ValueError('Native template has no dynamic cube routes')
    textures = b''.join(rows(108, 4)) + struct.pack('>I', materials.target_strings.id_for_text('environment_map'))
    for offset, count, payload in ((48, len(passes)//28, passes),
                                   (60, len(routes)//4, routes),
                                   (108, texture_index+1, textures)):
        struct.pack_into('>III', root, offset, count, b.alloc(payload), 0)
    new_datum, _ = registry.newtag('rmt2', root)
    struct.pack_into('>I', post, 12, new_datum)
    count, pointer = struct.unpack_from('>II', post, 16)
    if count != texture_index:
        raise ValueError('Native material texture count differs from its template')
    payload = bytes(b.read(pointer, count*24)) + b'bitm' + bytes(8) + struct.pack('>IhBBBbH', 0xffffffff, 0, 0, 0, 0, -1, 0)
    struct.pack_into('>III', post, 16, count+1, b.alloc(payload), 0)
    return post, (list(texture_names)+['environment_map'], constant_names), converted
