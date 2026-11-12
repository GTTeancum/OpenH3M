"""Convert Reach geometry auxiliary tables for a native H3 lighting BSP.

Layouts: pinned TagTool RenderGeometry/RenderGeometryCompression and retained
Reach/H3 plugins. Water bounds are returned for separate BSP/water adaptation.
"""
import math
import struct


def install_geometry_tables(cache, geometry, root, resource, allocate):
    if not isinstance(root, bytearray) or len(root) != 0x1b4:
        raise ValueError('Expected native lighting BSP record')
    offsets = (0x140, 0x14c, 0x158, 0x1a0)
    if any(any(root[o:o+12]) for o in offsets):
        raise ValueError('Geometry auxiliary tables already populated')
    # These need their own adapters when present; do not silently discard them.
    for offset in (0x34, 0x40, 0x4c, 0x58, 0x64, 0x70):
        if any(cache.data[geometry+offset:geometry+offset+12]):
            raise ValueError(f'Unsupported nonempty geometry auxiliary block {offset:#x}')
    compression = bytearray()
    for at in cache.block(geometry+0x10, 52):
        flags, padding = cache.unpack('HH', at)
        bounds = cache.unpack('10f', at+4)
        if flags & ~7 or padding or any(cache.data[at+44:at+52]):
            raise ValueError('Unsupported Reach compression fields')
        if not all(math.isfinite(v) for v in bounds) or any(bounds[i] > bounds[i+1] for i in range(0,10,2)):
            raise ValueError('Invalid geometry compression bounds')
        compression.extend(struct.pack('>HH10f', flags, 0, *bounds))
    spheres = bytearray()
    for at in cache.block(geometry+0x1c, 48):
        spheres.extend(struct.pack('>8f4b3f', *cache.unpack('8f4b3f', at)))
    user_rows = []
    for at in cache.block(geometry+0x28, 24):
        if cache.unpack('BBH', at) != (0,1,20):
            raise ValueError('Unsupported geometry user data')
        size, flags, unknown, pointer, tail = cache.unpack('5I', at+4)
        if (size,flags,unknown,tail) != (20,0,0,0):
            raise ValueError('Unsupported PRT descriptor')
        address = cache.pointer(pointer)
        if address < 0 or address+20 > len(cache.data):
            raise ValueError('PRT descriptor outside source cache')
        user_rows.append(struct.pack('>5I', *cache.unpack('5I', address)))
    per_pixel = bytearray();bound = 0
    fixups = dict(resource['fixups'])
    table = fixups[28] & 0x1fffffff
    for at in cache.block(geometry+0x7c, 2):
        index = cache.unpack('h', at)[0]
        if index != -1:
            if not 0 <= index < resource['vertex_buffers']:
                raise ValueError('Per-instance lightmap buffer missing')
            descriptor = fixups[table+index*12] & 0x1fffffff
            count, fmt, stride, size = struct.unpack_from('>IHHI',resource['control'],descriptor)
            if fmt != 4 or stride != 4 or size != count*stride:
                raise ValueError('Per-instance lightmap requires native coordinate buffer')
            bound += 1
        per_pixel.extend(bytes(12)+struct.pack('>hh',index,0))
    water = [cache.unpack('hh6f',at) for at in cache.block(geometry+0x88,28)]
    users = bytearray();shared = {}
    for payload in user_rows:
        if payload not in shared: shared[payload] = allocate(payload)
        users.extend(struct.pack('>BBH5I',0,1,20,20,0,0,shared[payload],0))
    for offset,payload,stride in zip(offsets,(compression,spheres,users,per_pixel),(44,48,24,16)):
        struct.pack_into('>III',root,offset,len(payload)//stride,allocate(payload) if payload else 0,0)
    return dict(compression_count=len(compression)//44,sorting_spheres=len(spheres)//48,
                user_data_count=len(user_rows),unique_prt_descriptors=len(shared),
                instance_count=len(per_pixel)//16,lightmapped_instances=bound,
                water_bounds=water,water_bounds_adapted=False)
