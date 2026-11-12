"""Read Reach MCC's resource-resident placements without losing transforms.

TagTool StructureBspCacheFileTagResources puts InstancedGeometryInstances at
root+72; Reach (not Reach11883) records occupy 156 bytes. Nested physics remains
explicitly referenced for separate conversion, not silently discarded.
"""
import math
import struct
from collections import Counter
from reach_bsp_collision_source import ReachBspCollisionSource


def read_instances(resource, definition_count):
    reader=ReachBspCollisionSource(resource)
    result=[]
    for index,at in enumerate(reader.headers(resource.root+72,156)):
        transform=resource.unpack('13f',at)
        if any(not math.isfinite(v) for v in transform) or transform[0]<=0:
            raise ValueError('Invalid Reach instance transform')
        definition,flags,mesh,compression=resource.unpack('hHhh',at+52)
        if not 0<=definition<definition_count:
            raise ValueError('Reach instance definition out of bounds')
        bounds=resource.unpack('6f',at+76)
        sphere=resource.unpack('5f',at+100)
        if any(not math.isfinite(v) for v in bounds+sphere):
            raise ValueError('Nonfinite Reach instance bounds')
        physics_count=resource.unpack('I',at+136)[0]
        physics_pointer=resource.fix.get(at+140)
        if physics_count and physics_pointer is None:
            raise ValueError('Reach instance physics pointer missing')
        result.append(dict(index=index,definition=definition,flags=flags,mesh=mesh,
            compression=compression,scale=transform[0],matrix=list(transform[1:]),
            seams=list(resource.unpack('4I',at+60)),bounds=list(bounds),sphere=list(sphere),
            checksum=resource.unpack('I',at+120)[0],policies=list(resource.unpack('4b',at+124)),
            lightmap_resolution=resource.unpack('f',at+128)[0],
            physics_count=physics_count,physics_pointer=physics_pointer,source_offset=at))
    return result


def serialize_instances(instances, names, texcoord_slots, physics, external_physics,
                        cubemap_samples, allocate):
    """Pack native placements without changing IDs; callers remap dependencies.

external_physics names placements handed to the separate convex-object path.
This function does not establish that those scenario objects are installed.
Cubemap samples must already be native (bitmap0, bitmap1, blend) tuples.
"""
    count=len(instances)
    if any(len(v)!=count for v in (names,texcoord_slots,cubemap_samples)):
        raise ValueError('Placement dependency table counts disagree')
    external_physics=set(external_physics)
    required={p['index'] for p in instances if p['physics_count']}
    if set(physics)&external_physics or set(physics)|external_physics != required:
        raise ValueError('Physics handoffs must cover every source physics placement exactly once')
    output=bytearray();unmapped=Counter()
    for i,p in enumerate(instances):
        if p['index']!=i or any(p['seams'][1:]):
            raise ValueError('Placement ordering or seam width requires adaptation')
        if p['flags']&~0x3ff:
            raise ValueError('Unknown Reach placement flags')
        pathfinding,lighting,imposter,streaming=p['policies']
        if pathfinding not in (0,1,2) or lighting not in (0,1,2):
            raise ValueError('Unsupported native placement policy')
        if not -1<=texcoord_slots[i]<=32767:
            raise ValueError('Native texcoord slot outside short range')
        record=bytearray(120)
        struct.pack_into('>13f',record,0,p['scale'],*p['matrix'])
        struct.pack_into('>hHh',record,52,p['definition'],p['flags']&31,texcoord_slots[i])
        struct.pack_into('>I',record,60,p['seams'][0])
        struct.pack_into('>4fIIhhf',record,64,*p['sphere'][:4],p['checksum'],names[i],
                         pathfinding,{0:3,1:1,2:2}[lighting],p['lightmap_resolution'])
        payload=physics.get(i,b'')
        if payload and len(payload)!=112:
            raise ValueError('Native placement requires one 112-byte physics wrapper')
        struct.pack_into('>III',record,96,int(bool(payload)),allocate(payload) if payload else 0,0)
        bitmap0,bitmap1,blend=cubemap_samples[i]
        if not math.isfinite(blend) or not 0<=blend<=1:
            raise ValueError('Invalid native cubemap blend')
        struct.pack_into('>hhf',record,112,bitmap0,bitmap1,blend)
        output.extend(record)
        unmapped[hex(p['flags']&~31)]+=1
    return bytes(output),dict(placements=count,geometry_physics=len(physics),
        external_convex_placements=sorted(external_physics),source_only_flags=dict(unmapped),
        fade_policy='Zero instance overrides; native scenario/default fade applies',runtime_verified=False)
