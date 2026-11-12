"""Reach render meshes -> native H3 records, with explicit semantic audit.

Flag mapping follows TagTool RenderGeometryConverter.ConvertHaloReach's lexical
mapping. Reach-only flags/analytical fields are reported, not claimed equivalent.
This serializer requires already-converted buffers; it does not convert shaders.
"""
import struct
from collections import Counter
from reach_mesh_parts import pack_part


def serialize_meshes(cache, geometry, allocate, vertex_buffers, index_buffers, mesh_ranges=None,water_meshes=(),without_static_lighting=()):
    rows = cache.block(geometry+4,92)
    output = bytearray()
    dropped_mesh, dropped_part, analytical, policies = Counter(), Counter(), Counter(), Counter()
    part_count = subpart_count = bucket_count = 0
    mesh_ranges=mesh_ranges or {};water_meshes=set(water_meshes);used_water=set()
    without_static_lighting=set(without_static_lighting)
    if any(not 0<=i<len(rows) for i in without_static_lighting):
        raise ValueError('Static-lighting exemption references absent mesh')
    if any(not 0<=i<len(rows) for i in mesh_ranges):raise ValueError('Range override references absent mesh')
    def block(payload,count):
        return struct.pack('>III',count,allocate(payload) if payload else 0,0)
    for mesh_index, at in enumerate(rows):
        record = bytearray(76)
        parts = cache.block(at,24)
        subs = cache.block(at+12,16)
        native_parts = bytearray()
        native_subs = bytearray()
        for part_index,p in enumerate(parts):
            flags = cache.unpack('H',p+18)[0]
            if flags & ~0x3fff:
                raise ValueError('Unknown Reach part flags')
            if flags & 2 and mesh_index not in without_static_lighting:
                raise ValueError('Per-vertex part needs original H3 lighting adaptation')
            if flags & 2 and cache.unpack('2h',at+26)!=(-1,-1):
                raise ValueError('Static-lighting exemption has bound lighting streams')
            native_flags = (8 if flags&1 else 0) | (16 if flags&64 else 0)
            dropped_part[hex(flags & ~(1|64))] += 1
            part_bytes=bytearray(cache.data[p:p+24])
            if mesh_index in mesh_ranges:
                replacement=mesh_ranges[mesh_index]['parts'][part_index]
                if replacement['count']!=cache.u(p+8):raise ValueError('Range relocation changed part size')
                struct.pack_into('<I',part_bytes,4,replacement['first'])
            native_parts.extend(pack_part(bytes(part_bytes),native_flags))
            first,count,start,n = cache.unpack('IIhH',p+4)
            if start < 0 or start+n > len(subs):
                raise ValueError('Part subrange outside mesh')
            for sub in subs[start:start+n]:
                sf,sc,owner = cache.unpack('IIh',sub)
                if owner != part_index or sf < first or sf+sc > first+count:
                    raise ValueError('Subpart not contained in owning part')
        for sub_index,p in enumerate(subs):
            first,count,owner,vertices,light = cache.unpack('IIhHI',p)
            if mesh_index in mesh_ranges:
                replacement=mesh_ranges[mesh_index]['subparts'][sub_index]
                if replacement['count']!=count or replacement['part']!=owner:raise ValueError('Relocation changed subpart identity')
                first=replacement['first']
            if max(first,count)>65535 or not 0<=owner<len(parts):
                raise ValueError('Subpart requires splitting or has invalid owner')
            native_subs.extend(struct.pack('>HHhH',first,count,owner,vertices))
            analytical[hex(light)]+=1
        record[:12] = block(native_parts,len(parts))
        record[12:24] = block(native_subs,len(subs))
        vb = cache.unpack('8h',at+24)
        ib = cache.unpack('2h',at+40)
        if any(v != -1 and not 0<=v<vertex_buffers for v in vb):
            raise ValueError('Mesh vertex buffer outside converted resource')
        if any(v != -1 and not 0<=v<index_buffers for v in ib):
            raise ValueError('Mesh index buffer outside converted resource')
        struct.pack_into('>8h2h',record,24,*vb,*ib)
        flags,node,kind,prt,policy,primitive,padding = cache.unpack('HbBBBBB',at+44)
        if flags & ~0x13f or kind not in (0,1) or prt not in (0,1) or primitive!=3 or padding:
            raise ValueError('Mesh requires a dedicated Reach layout adapter')
        dropped_mesh[hex(flags & ~31)]+=1
        policies[policy]+=1
        struct.pack_into('>BbBBB',record,44,flags&31,node,kind,prt,primitive)
        buckets=cache.block(at+52,16)
        packed_buckets=bytearray()
        for p in buckets:
            mesh,definition=cache.unpack('hh',p)
            if mesh != -1 and not 0<=mesh<len(rows):
                raise ValueError('Instance bucket references absent mesh')
            instances=cache.block(p+4,2)
            packed_buckets.extend(struct.pack('>hh',mesh,definition))
            packed_buckets.extend(block(b''.join(struct.pack('>h',cache.unpack('h',v)[0]) for v in instances),len(instances)))
        record[52:64]=block(packed_buckets,len(buckets))
        if cache.u(at+64):
            if mesh_index not in water_meshes:raise ValueError('Water mesh requires dedicated conversion')
            starts=[cache.unpack('H',p)[0] for p in cache.block(at+64,2)]
            expected=[];corner=0
            for p in parts:
                if cache.unpack('H',p+18)[0]&1:
                    expected.append(corner);corner+=cache.u(p+8)
            if starts!=expected:raise ValueError('Water start table disagrees with rebuilt corner order')
            record[64:76]=block(b''.join(struct.pack('>H',v) for v in starts),len(starts))
            used_water.add(mesh_index)
        output.extend(record)
        part_count+=len(parts);subpart_count+=len(subs);bucket_count+=len(buckets)
    if used_water!=water_meshes:raise ValueError('Converted water mesh set differs from metadata')
    return bytes(output),dict(meshes=len(rows),parts=part_count,subparts=subpart_count,
        instance_buckets=bucket_count,unmapped_mesh_flags=dict(dropped_mesh),
        unmapped_part_flags=dict(dropped_part),subpart_analytical_fields=dict(analytical),
        source_lighting_policies=dict(policies),
        meshes_without_static_lighting=sorted(without_static_lighting),
        scope='Native metadata serialization; shader/lighting semantic and runtime validation remain')
