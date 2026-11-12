"""Move Reach cache-file surface/seam arrays to original H3 BSP metadata.

Original H3 sbsp offsets follow the retained retail plugin and bsp_metadata.py.
Reach pathfinding must be explicitly supported before nonempty data is accepted.
Instance/physics sections of the Reach resource belong to separate adapters.
"""
import struct
import math
from reach_bsp_collision_source import ReachBspCollisionSource
from reach_collision_geometry import convert_surface_mappings


def surface_sections(resource,cluster_triangle_remaps=None):
    reader=ReachBspCollisionSource(resource)
    if resource.unpack('I',resource.root+36)[0]:
        raise ValueError('Nonempty Reach pathfinding requires native metadata conversion')
    surfaces,ranges=reader.block(resource.root,8)
    references,triangles=reader.block(resource.root+12,4)
    edges,seams=reader.block(resource.root+24,4)
    native_ranges,native_triangles=convert_surface_mappings(ranges,triangles,cluster_triangle_remaps)
    native_seams=b''.join(struct.pack('>HH',*row) for row in struct.iter_unpack('<HH',seams))
    return {0x18:(edges,native_seams),0x54:(surfaces,native_ranges),0x60:(references,native_triangles)}


def install_surface_sections(root,sections,allocate):
    """Populate a caller-owned H3 root; refuse competing authored arrays."""
    if len(root)<0x6c or set(sections)!={0x18,0x54,0x60}:
        raise ValueError('Invalid native BSP root or surface section set')
    for offset,(count,data) in sections.items():
        if len(data)!=count*4 or any(root[offset:offset+12]):
            raise ValueError('Invalid payload or competing native BSP surface array')
    result=bytearray(root)
    for offset,(count,data) in sections.items():
        struct.pack_into('>III',result,offset,count,allocate(data) if count else 0,0)
    return bytes(result)


def install_collision_resource(cache, source_bsp, root, registry, owner, resource,
                               leaf_clusters, cluster_count):
    """Bind the converted collision resource and matching leaf lookup to a BSP.

The caller supplies the post-split leaf table/count when geometry was split.
Instance physics and all other BSP blocks remain caller-owned.
"""
    if not isinstance(root, bytearray) or len(root) != 0x388:
        raise ValueError('Expected native BSP root')
    if any(root[:4]) or any(root[0x30:0x54]) or any(root[0x37c:0x388]):
        raise ValueError('Native collision metadata already populated')
    if not 0 < cluster_count <= 128 or any(x != 255 and x >= cluster_count for x in leaf_clusters):
        raise ValueError('Leaf cluster outside native cluster range')
    control=resource['control'];resource_root=resource['root'];fix=dict(resource['fixups'])
    if struct.unpack_from('>I',control,resource_root)[0] != 1:
        raise ValueError('Expected one native main collision geometry')
    main=fix[resource_root+4]
    if main >> 29 != 1:
        raise ValueError('Main collision header must be resident')
    main &= 0x1fffffff
    leaf_count=struct.unpack_from('>I',control,main+24)[0]
    if leaf_count != len(leaf_clusters):
        raise ValueError('Collision and cluster leaf counts disagree')
    bounds=cache.unpack('6f',source_bsp+0xf0)
    if any(not math.isfinite(x) for x in bounds) or any(bounds[i]>bounds[i+1] for i in (0,2,4)):
        raise ValueError('Invalid source BSP world bounds')
    datum=registry.add_resource(owner,'structure_bsp_tag_resources',resource)
    struct.pack_into('>I',root,0,cache.u(source_bsp+0x30))
    struct.pack_into('>III',root,0x30,len(leaf_clusters),
                     registry.builder.alloc(leaf_clusters) if leaf_clusters else 0,0)
    struct.pack_into('>6f',root,0x3c,*bounds)
    struct.pack_into('>III',root,0x37c,datum,0,1)
    return dict(resource_datum=datum,leaf_count=leaf_count,cluster_count=cluster_count,
                collision_resource_installed=True,instance_physics_installed=False,
                runtime_verified=False)
