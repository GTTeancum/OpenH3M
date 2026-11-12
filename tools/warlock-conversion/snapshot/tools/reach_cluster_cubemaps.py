"""Convert single-point Reach cluster cubemaps to original H3 metadata.

Source: TagTool ScenarioStructureBsp.Cluster.StructureClusterCubemap at commit
ce2dc6ac13072b160752af618ea1dc143e2727ac. Reference-point arrays replace H3's
inline position in Reach. Index remapping belongs to the scenario/bitmap caller.
"""
import math
import struct


def install_scenario_cubemaps(cache, scenario, root, bsp_offsets, allocate):
    """Retain the complete Reach scenario table, including unreferenced entries.

    MCC Reach U13's table is at 0x7b8, with 32-byte records. Field layout:
    TagTool Scenario.ScenarioCubemapBlock at the pinned revision above. Native
    H3 keeps position/resolution, while cluster metadata stores the sample point.
    Reject multiple reference points rather than silently collapsing them.
    """
    if len(root) != 0x7b8 or any(root[0x788:0x794]):
        raise ValueError('Expected empty native scenario cubemap table')
    rows = cache.block(scenario + 0x7b8, 32)
    records = bytearray()
    positions = []
    for at in rows:
        position = cache.unpack('3f', at + 4)
        resolution, manual = cache.unpack('hh', at + 16)
        references = cache.block(at + 20, 16)
        if (not all(math.isfinite(v) for v in position)
                or resolution not in range(5) or len(references) > 1):
            raise ValueError('Unsupported scenario cubemap position/resolution/points')
        # Manual BSP assignment is authoring metadata; all compiled cluster
        # memberships are retained and checked below.
        sample = position
        if references:
            sample = cache.unpack('3f', references[0])
            if (not all(math.isfinite(v) for v in sample)
                    or cache.unpack('i', references[0] + 12)[0] != 0):
                raise ValueError('Unsupported scenario cubemap reference-point index')
        positions.append(sample)
        records.extend(struct.pack('>3fhh', *position, resolution, 0))
    referenced = set()
    memberships = 0
    for bsp in bsp_offsets:
        for cluster in cache.block(bsp + 0x138, 140):
            for at in cache.block(cluster + 128, 16):
                index, bitmap = cache.unpack('hh', at)
                points = cache.block(at + 4, 16)
                if not 0 <= index < len(rows) or len(points) != 1:
                    raise ValueError('Cluster references absent scenario cubemap')
                if (cache.unpack('3f', points[0]) != positions[index]
                        or cache.unpack('i', points[0] + 12)[0] != 0):
                    raise ValueError('Cluster/scenario cubemap sample mismatch')
                referenced.add(index)
                memberships += 1
    pointer = allocate(records) if records else 0
    struct.pack_into('>III', root, 0x788, len(rows), pointer, 0)
    return dict(entries=len(rows), referenced_entries=len(referenced),
                cluster_memberships=memberships, ordinals_preserved=True,
                unreferenced_entries_preserved=len(rows)-len(referenced),
                runtime_verified=False)


def import_cubemap_group(source, datum, registry):
    """Retain every authored image/mip and ordinal in one native bitmap tag."""
    from encode_bitmap import encode_cubemap_base
    cache=source.c;tag=cache.tags[datum&65535]
    if tag['group']!='bitm' or tag['salt']!=datum>>16:
        raise ValueError('Invalid source cubemap bitmap datum')
    images=source.info(datum&65535)
    if not images or any(i['kind']!=2 for i in images):
        raise ValueError('Expected a nonempty cubemap-only bitmap group')
    root=bytearray(0xa4);struct.pack_into('>H',root,4,0x50)
    owner,address=registry.newtag('bitm',root)
    records=bytearray();resources=bytearray();raw_bytes=0
    for index,info in enumerate(images):
        record,control,raw=encode_cubemap_base(source,datum&65535,index,
            max_dimension=info['width'],preserve_mips=True)
        resource=registry.add_resource(owner,'bitmap_texture_interop_resource',
            dict(control=control,raw=raw,root=52,fixups=[(12,0x40000000),(52,0x20000000)],
                 interops=[(0x20000034,2)]))
        records.extend(record);resources.extend(struct.pack('>II',resource,0));raw_bytes+=len(raw)
    b=registry.builder
    b.put(address+0x60,'III',len(images),b.alloc(records),0)
    b.put(address+0x8c,'III',len(images),b.alloc(resources),0)
    return owner,dict(images=len(images),raw_bytes=raw_bytes,source_datum=datum,
                      native_address=address,authored_mips_preserved=True,runtime_verified=False)


def instance_cubemap_samples(resource,instances,bitmap_remap):
    """Reach's cached image index -> native single-image sample, without blending.

Cluster/point locators are source lookup metadata; native instances store image
indices directly. Preserve the cached index even for an empty source locator.
"""
    result=[]
    for p in instances:
        image=resource.unpack('h',p['source_offset']+154)[0]
        if image==-1:result.append((-1,-1,0.));continue
        if image not in bitmap_remap or not 0<=bitmap_remap[image]<=32767:
            raise ValueError('Instance cubemap image was not imported')
        target=bitmap_remap[image]
        result.append((target,target,0.))
    return result


def convert_cluster_cubemaps(cache,cluster_offset,index_remap=None):
    output=bytearray();source_points=[]
    for at in cache.block(cluster_offset+128,16):
        scenario,bitmap=cache.unpack('hh',at)
        points=cache.block(at+4,16)
        if len(points)!=1:
            raise ValueError('Reach cubemap requires explicit multiple/empty-point adaptation')
        position=cache.unpack('3f',points[0]);point_index=cache.unpack('i',points[0]+12)[0]
        if not all(math.isfinite(v) for v in position):raise ValueError('Nonfinite cubemap position')
        if index_remap is not None:scenario,bitmap=index_remap(scenario,bitmap)
        output.extend(struct.pack('>3fhh',*position,scenario,bitmap))
        source_points.append(point_index)
    return bytes(output),source_points
