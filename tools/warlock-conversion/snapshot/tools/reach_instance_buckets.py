"""Validate Reach placements for Halo 3's original version-2 bucket lookup.

Original H3 sub_8229C388 selects buckets when sbsp.ImportVersion < 3,
otherwise cluster MOPPs. Both call sub_820C0B00 with a global placement index.
Reach cluster trees instead cover instance groups; they cannot be wired into
that direct-index consumer unchanged. See the retained native consumer trace.
"""
import struct
from collections import Counter


def validate_instance_buckets(cache, bsp, geometry, instances):
    clusters = cache.block(bsp + 0x138, 140)
    groups = cache.block(bsp + 0x234, 16)
    subgroups = cache.block(bsp + 0x240, 40)
    meshes = cache.block(geometry + 4, 92)
    if len(groups) != len(clusters):
        raise ValueError('Reach cluster/group counts differ')
    result = []
    for index, cluster in enumerate(clusters):
        mesh = cache.unpack('h', cluster + 64)[0]
        if not 0 <= mesh < len(meshes):
            raise ValueError('Cluster references absent mesh')
        expected = set()
        group_ids = [cache.unpack('h', p)[0] for p in cache.block(groups[index] + 4, 2)]
        for group in group_ids:
            if not 0 <= group < len(subgroups):
                raise ValueError('Cluster references absent instance group')
            expected.update(cache.unpack('h', p)[0]
                            for p in cache.block(subgroups[group] + 28, 2))
        actual = set(); references = []
        for bucket in cache.block(meshes[mesh] + 52, 16):
            bucket_mesh, definition = cache.unpack('hh', bucket)
            for p in cache.block(bucket + 4, 2):
                instance = cache.unpack('h', p)[0]
                if not 0 <= instance < len(instances):
                    raise ValueError('Bucket placement index out of bounds')
                placement = instances[instance]
                if placement['definition'] != definition or placement['mesh'] != bucket_mesh:
                    raise ValueError('Bucket does not match its placement definition/mesh')
                actual.add(instance)
                references.append((bucket_mesh, definition, instance))
        if any(not 0 <= i < len(instances) for i in expected) or expected - actual:
            raise ValueError('Native buckets omit source group placements')
        # Existing authored buckets may contain more instances than the imposter
        # groups. Preserve those; group membership is not a deletion criterion.
        result.append(dict(cluster=index, mesh=mesh, groups=len(group_ids),
                           references=references,
                           group_instances=len(expected), bucket_instances=len(actual),
                           additional_bucket_instances=sorted(actual - expected)))
    return dict(required_native_import_version=2,
                lookup='original_h3_instance_buckets', clusters=result,
                source_group_coverage_verified=True, runtime_verified=False)


def install_native_bsp_geometry(root, lighting, lookup, cluster_bindings, read):
    """Share verified native render geometry with its BSP and select H3 lookup.

cluster_bindings is (source cluster, destination mesh) per destination cluster;
split children must each retain their source cluster's authored buckets.
Other BSP sections, including the cluster records themselves, remain caller-owned.
"""
    if len(root) != 0x388 or len(lighting) != 0x1b4:
        raise ValueError('Expected native BSP and lighting BSP roots')
    if any(root[4:8]) or any(root[0x2e0:0x364]):
        raise ValueError('BSP lookup/geometry already installed')
    if lookup.get('required_native_import_version') != 2 or not lookup.get('source_group_coverage_verified'):
        raise ValueError('Missing validated instance lookup')
    mesh_count, mesh_pointer, padding = struct.unpack_from('>III', lighting, 0x134)
    if not mesh_count or not mesh_pointer or padding:
        raise ValueError('Missing native mesh array')
    covered = set(); references = 0
    for source, destination in cluster_bindings:
        if not 0 <= source < len(lookup['clusters']) or not 0 <= destination < mesh_count:
            raise ValueError('Invalid native cluster mesh binding')
        mesh = read(mesh_pointer + destination * 76, 76)
        count, pointer, padding = struct.unpack_from('>III', mesh, 52)
        if padding or (count and not pointer):
            raise ValueError('Invalid native bucket block')
        actual = []
        for i in range(count):
            bucket = read(pointer + i * 16, 16)
            mesh_id, definition, n, p, pad = struct.unpack('>hhIII', bucket)
            if pad or (n and not p):
                raise ValueError('Invalid native bucket placements')
            actual.extend((mesh_id, definition, item[0])
                          for item in struct.iter_unpack('>h', read(p, n * 2)))
        expected = lookup['clusters'][source]['references']
        if Counter(actual) != Counter(map(tuple, expected)):
            raise ValueError('Native cluster lost or changed authored placement references')
        covered.add(source); references += len(actual)
    if covered != set(range(len(lookup['clusters']))):
        raise ValueError('Native cluster bindings omit source clusters')
    root[0x2e0:0x364] = lighting[0x130:0x1b4]
    struct.pack_into('>I', root, 4, 2)
    return dict(native_import_version=2, cluster_bindings=len(cluster_bindings),
                placement_references_verified=references,
                shared_bsp_geometry_installed=True, runtime_verified=False)
