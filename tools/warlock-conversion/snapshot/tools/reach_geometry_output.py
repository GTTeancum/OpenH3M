"""Attach converted Reach render geometry to an original H3 lighting BSP.

The caller owns BSP/tag allocation, mesh partitioning and material remapping.
All nested mesh allocations must use this registry's builder. This does not
adapt analytical lighting, water bounds or scenario visibility.
"""
import struct
from reach_geometry_tables import install_geometry_tables


def install_native_geometry(cache, geometry, root, registry, owner, resource,
                            build_meshes):
    if not isinstance(root, bytearray) or len(root) != 0x1b4:
        raise ValueError('Expected native lighting BSP record')
    if any(root[0x130:]):
        raise ValueError('Native geometry fields already populated')
    flags = cache.u(geometry)
    if flags & ~7:
        raise ValueError('Unmapped geometry runtime flags')
    builder = registry.builder
    meshes = build_meshes(builder.alloc)
    if not meshes or len(meshes) % 76:
        raise ValueError('Expected complete native mesh records')
    for at in range(0, len(meshes), 76):
        for offset, count in ((0, 8), (16, 2)):
            indices = struct.unpack_from('>' + 'h'*count, meshes, at+24+offset)
            limit = resource['vertex_buffers'] if offset == 0 else resource['index_buffers']
            if any(i != -1 and not 0 <= i < limit for i in indices):
                raise ValueError('Native mesh references absent resource buffer')
    report = install_geometry_tables(cache, geometry, root, resource, builder.alloc)
    datum = registry.add_resource(owner, 'render_geometry_api_resource_definition', resource)
    struct.pack_into('>I',root,0x130,flags)
    struct.pack_into('>III',root,0x134,len(meshes)//76,builder.alloc(meshes),0)
    struct.pack_into('>II',root,0x1ac,datum,0)
    report.update(resource_datum=datum,mesh_count=len(meshes)//76,
                  raw_bytes=len(resource['raw']),geometry_runtime_flags=flags)
    return report
