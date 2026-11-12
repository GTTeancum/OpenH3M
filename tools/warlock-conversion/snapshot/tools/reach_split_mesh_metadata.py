"""Emit a spatial subset of a converted mesh without renumbering vertices.

The caller owns cluster, visibility and collision-reference remapping. Bounds
and instance buckets remain conservative source values until that integration.
Water subsets use explicitly remapped corner offsets when they are noncontiguous.
"""
import struct
from reach_mesh_parts import pack_part


def partition_water_corners(cache,source_mesh,partitions,triangle_payload):
    parts=cache.block(source_mesh,24);source_corners={};cursor=0
    for pi,at in enumerate(parts):
        if not cache.unpack('H',at+18)[0]&1:continue
        first,count=cache.unpack('II',at+4)
        for i in range(first,first+count):source_corners[i]=cursor;cursor+=1
    if len(triangle_payload)!=cursor*4:raise ValueError('Water corner payload size mismatch')
    output=bytearray();offsets=[];seen=[]
    for partition in partitions:
        inverse={new:old for old,new in partition['old_to_new_triangle'].items()};starts={}
        for p in partition['parts']:
            if p['source_part'] not in [i for i,at in enumerate(parts) if cache.unpack('H',at+18)[0]&1]:continue
            starts[p['source_part']]=len(output)//4
            for index in range(p['first'],p['first']+p['count']):
                source_index=inverse[index//3]*3+index%3
                corner=source_corners[source_index];seen.append(corner)
                pair=triangle_payload[corner*4:corner*4+4]
                if struct.unpack_from('>H',pair)[0]!=partition['indices'][index]:
                    raise ValueError('Water corner references different geometry')
                output.extend(pair)
        offsets.append(starts)
    if sorted(seen)!=list(range(cursor)):
        raise ValueError('Split must preserve every water corner exactly once')
    return bytes(output),offsets


def serialize_split_mesh(cache, source_mesh, native_record, partition, index_slot, allocate,water_offsets=None,secondary_index_slot=None):
    if len(native_record)!=76 or not 0<=index_slot<32768:
        raise ValueError('Invalid native split mesh record or index slot')
    record=bytearray(native_record)
    parts=cache.block(source_mesh,24)
    subs=cache.block(source_mesh+12,16)
    water_starts=[cache.unpack('H',p)[0] for p in cache.block(source_mesh+64,2)]
    water_parts=[i for i,p in enumerate(parts) if cache.unpack('H',p+18)[0]&1]
    if len(water_starts)!=len(water_parts):
        raise ValueError('Water corner table differs from source part count')
    water_by_part=dict(zip(water_parts,water_starts))
    packed_parts=bytearray();packed_subs=bytearray();selected_water=[]
    for part in partition['parts']:
        at=parts[part['source_part']]
        data=bytearray(cache.data[at:at+24]);flags=cache.unpack('H',at+18)[0]
        if flags&2:raise ValueError('Unsupported per-vertex lighting part')
        struct.pack_into('<IIhH',data,4,part['first'],part['count'],part['subpart_start'],part['subpart_count'])
        packed_parts.extend(pack_part(data,(8 if flags&1 else 0)|(16 if flags&64 else 0)))
        if flags&1:
            if water_offsets is not None:
                selected_water.append(water_offsets[part['source_part']])
                continue
            source_first,source_count=cache.unpack('II',at+4)
            actual=partition['indices'][part['first']:part['first']+part['count']]
            selected=[triangle for triangle,new in partition['old_to_new_triangle'].items()
                      if part['first']<=new*3<part['first']+part['count']]
            selected.sort()
            if not selected or selected!=list(range(selected[0],selected[-1]+1)):
                raise ValueError('Noncontiguous water subset needs its own corner stream')
            if selected[0]*3<source_first or (selected[-1]+1)*3>source_first+source_count:
                raise ValueError('Water subset outside original part')
            for i,triangle in enumerate(selected):
                if partition['old_to_new_triangle'][triangle]*3!=part['first']+i*3:
                    raise ValueError('Water corner order changed')
            if len(actual)!=len(selected)*3:raise ValueError('Truncated water part')
            selected_water.append(water_by_part[part['source_part']]+selected[0]*3-source_first)
    for sub in partition['subparts']:
        vertices=cache.unpack('H',subs[sub['source_subpart']]+10)[0]
        packed_subs.extend(struct.pack('>HHhH',sub['first'],sub['count'],sub['part'],vertices))
    def block(payload,count):
        return struct.pack('>III',count,allocate(payload) if payload else 0,0)
    record[:12]=block(packed_parts,len(partition['parts']))
    record[12:24]=block(packed_subs,len(partition['subparts']))
    # This conversion supports triangle-list meshes with no secondary index stream.
    primary,secondary=struct.unpack_from('>2h',record,40)
    if secondary_index_slot is not None:
        if not 0<=secondary_index_slot<32768:raise ValueError('Invalid secondary index slot')
        struct.pack_into('>h',record,42,secondary_index_slot)
    elif secondary not in (-1,primary):
        raise ValueError(f'Split mesh has independent secondary index stream {primary}/{secondary}')
    elif secondary==primary:struct.pack_into('>h',record,42,index_slot)
    struct.pack_into('>h',record,40,index_slot)
    record[64:76]=block(b''.join(struct.pack('>H',v) for v in selected_water),len(selected_water))
    return bytes(record)
