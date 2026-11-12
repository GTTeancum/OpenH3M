"""Preserve BSP-owned Reach geometry when its lighting tag is a placeholder.

No lightmap is invented: the temporary lighting-sized record is only an adapter
for the shared geometry serializer. It is never registered as a lighting tag.
"""
import struct
import zlib
from reach_bsp_source import convert_bsp_geometry
from reach_geometry_output import install_native_geometry
from reach_mesh_metadata import serialize_meshes
from reach_instance_buckets import install_native_bsp_geometry
from reach_bsp_metadata_sections import install_collision_resource, install_surface_sections, surface_sections
from reach_resource import ReachResource
from reach_bsp_instances import serialize_instances
from reach_cluster_cubemaps import instance_cubemap_samples
from string_ids import StringTable


def install_placeholder_bsp(cache, binding, registry, strings, shared_paths,
                            collision, cubemap_source_bsp, cubemap_image_count):
    if not binding['lighting_placeholder']:
        raise ValueError('Expected placeholder lighting with BSP-owned geometry')
    builder = registry.builder
    bsp = binding['bsp']['offset']
    geometry = bsp + 0x44c
    light = binding['lighting']['offset']
    # The placeholder must actually have no static lighting tables/resources.
    # TagTool VmfConversion documents Reach part bit 1 as disabling static
    # per-vertex lighting for that part. With no such stream it is redundant;
    # it must not be copied numerically into H3's unrelated flags.
    if (any(cache.u(light+offset) for offset in (0x48,0x54,0x60,0x6c,0x7c))
            or any(cache.u(light+offset)!=0xffffffff for offset in (0x28,0x38,0x10c))):
        raise ValueError('Placeholder unexpectedly contains static lighting data')
    no_static = [i for i,at in enumerate(cache.block(geometry+4,92))
                 if cache.unpack('2h',at+26)==(-1,-1)]
    resource, provenance = convert_bsp_geometry(cache, binding['bsp_index'], shared_paths)
    owner, address = registry.newtag('sbsp', bytes(0x388))
    temporary = bytearray(0x1b4)
    def meshes(allocate):
        records, _ = serialize_meshes(cache, geometry, allocate,
                                      resource['vertex_buffers'], resource['index_buffers'],
                                      without_static_lighting=no_static)
        return records
    report = install_native_geometry(cache, geometry, temporary, registry, owner, resource, meshes)
    root = bytearray(0x388)
    lookup = resource['collision_lookup']
    report['collision_lookup'] = install_native_bsp_geometry(root, temporary, lookup,
        [(row['cluster'], row['mesh']) for row in lookup['clusters']], builder.read)
    report['collision_resource'] = install_collision_resource(cache, bsp, root, registry, owner,
        collision['resource'], collision['leaf_clusters'], collision['cluster_count'])
    placements = ReachResource(cache, cache.u(bsp+0x520), shared_paths, {})
    root = bytearray(install_surface_sections(root, surface_sections(placements), builder.alloc))
    source_strings = StringTable(cache)
    names = [source_strings.translate(cache.u(p), strings) for p in cache.block(bsp+0x258, 4)]
    instances = collision['instances']
    if cache.u(geometry+0x7c):
        raise ValueError('Placeholder has texcoord bindings requiring explicit lighting adaptation')
    for instance in instances:
        source_bsp, cluster, cube, point, image = placements.unpack('BBhhh', instance['source_offset']+148)
        if image != -1 and source_bsp != cubemap_source_bsp:
            raise ValueError('Placeholder samples a different BSP cubemap group')
    samples = instance_cubemap_samples(placements, instances, {i:i for i in range(cubemap_image_count)})
    data, report['placements'] = serialize_instances(instances, names, [-1]*len(instances),
        collision['physics'], collision['external_physics'], samples, builder.alloc)
    pointer = builder.alloc(data)
    struct.pack_into('>III', root, 0x1b0, len(instances), pointer, 0)
    for offset in range(0, len(root), 4):
        builder.put(address+offset, 'I', struct.unpack_from('>I', root, offset)[0])
    for i, instance in enumerate(instances):
        row = builder.read(pointer+i*120, 120)
        assert struct.unpack_from('>13f', row) == (instance['scale'], *instance['matrix'])
        assert struct.unpack_from('>h', row, 56)[0] == -1
        assert struct.unpack_from('>hhf', row, 112) == samples[i]
    assert builder.read(address, 4) == struct.pack('>I', cache.u(bsp+0x30))
    assert builder.read(address+0x2e0, 0x84) == temporary[0x130:0x1b4]
    rid = (report['resource_datum'] & 65535)*64
    assert struct.unpack_from('>I',registry.resources,rid+12)[0] == owner
    location = struct.unpack_from('>h',registry.resources,rid+34)[0]
    page = struct.unpack_from('>h',registry.locations,location*16)[0]
    file_offset, size, raw_size = struct.unpack_from('>III',registry.pages,page*88+8)
    start = file_offset-builder.cache.u(0x488)
    assert raw_size == len(resource['raw'])
    assert zlib.decompress(builder.raw[start:start+size],-15) == resource['raw']
    report.update(provenance=provenance, placeholder_lightmap_preserved=True,
                  invented_lightmap=False, placement_records_read_back=True,
                  geometry_page_read_back=True, cubemap_source_bsp=cubemap_source_bsp,
                  meshes_without_static_lighting=no_static, runtime_verified=False)
    return dict(datum=owner, address=address, lighting=None,
                geometry_record=bytes(temporary), report=report)
