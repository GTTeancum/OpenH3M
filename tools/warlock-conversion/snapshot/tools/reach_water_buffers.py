"""Build native H3 water topology with explicit, caller-reviewed depth values.

Reach bump water has no geometric wave displacement. Keep displacement scale
zero; shading still belongs to the separately selected native H3 material.
No depth defaults are supplied. Depth is keyed by geometry vertex, not UV index.
"""
import math
import struct
from reach_water_parameters import recover_water_uvs


def validate_water_bounds(cache, lighting_offset, resource):
    """Account for Reach-only water AABBs before native topology conversion.

    Reflection stores interleaved min/max axes, not two XYZ vectors. Its
    boxes equal rendered-part bounds with a .15 vertical margin. Native H3
    has no RenderGeometry water-box table; this verifies these records do
    not encode extra surfaces. Native visibility still needs runtime checks.
    """
    meshes=cache.block(lighting_offset+0x7c,92)
    vb=resource.buffers('vertex');ib=resource.buffers('index')
    expected={(mi,pi) for mi,m in enumerate(meshes)
              for pi,p in enumerate(cache.block(m,24)) if cache.unpack('H',p+18)[0]&1}
    seen=set();report=[]
    def payload(at,size):
        address=resource.fix[at]
        segment={0x40000000:0,0x60000000:1}[address&0xe0000000]
        offset=address&0x1fffffff
        data=resource.raw[segment][offset:offset+size]
        if len(data)!=size:raise ValueError('Water bound geometry exceeds resource')
        return data
    for at in cache.block(lighting_offset+0x100,28):
        mi,pi,*bounds=cache.unpack('hh6f',at)
        if (mi,pi) not in expected or (mi,pi) in seen:
            raise ValueError('Water bound does not uniquely identify a water part')
        seen.add((mi,pi));mesh=meshes[mi];part=cache.block(mesh,24)[pi]
        vertex,index=cache.unpack('h',mesh+24)[0],cache.unpack('h',mesh+40)[0]
        if not 0<=vertex<len(vb) or not 0<=index<len(ib):
            raise ValueError('Water bound references absent geometry buffers')
        count,fmt,stride=resource.unpack('IHH',vb[vertex])
        if (fmt,stride)!=(1,36):raise ValueError('Unreviewed water bound vertex format')
        vertices=payload(vb[vertex]+20,count*stride)
        indices=payload(ib[index]+20,resource.unpack('I',ib[index]+8)[0])
        first,n=cache.unpack('II',part+4)
        if not n or first*2+n*2>len(indices):raise ValueError('Invalid water bound triangle span')
        ids=struct.unpack_from('<'+'H'*n,indices,first*2)
        if max(ids)>=count:raise ValueError('Water bound vertex outside buffer')
        points=[struct.unpack_from('<3f',vertices,i*stride) for i in ids]
        actual=[value for axis in range(3) for value in
                (min(p[axis] for p in points),max(p[axis] for p in points))]
        padded=actual[:4]+[actual[4]-.15,actual[5]+.15]
        if not all(math.isfinite(x) for x in bounds+actual) or any(abs(x-y)>2e-5 for x,y in zip(bounds,padded)):
            raise ValueError('Water bound differs from reviewed rendered-part bounds')
        report.append(dict(mesh=mi,part=pi,bounds=bounds,rendered_bounds=actual,vertical_margin=.15))
    if seen!=expected:raise ValueError('Water geometry has missing bounds')
    return report


def rebuild_water_buffers(cache, lighting_offset, resource, depths_by_mesh):
    vb=resource.buffers('vertex');ib=resource.buffers('index');out={};reports=[];used=set()
    def payload(at,size):
        address=resource.fix[at];segment={0x40000000:0,0x60000000:1}[address&0xe0000000]
        start=address&0x1fffffff;data=bytes(resource.raw[segment][start:start+size])
        if len(data)!=size:raise ValueError('Truncated Reach water data')
        return data
    for mi,mesh in enumerate(cache.block(lighting_offset+0x7c,92)):
        parts=[p for p in cache.block(mesh,24) if cache.unpack('H',p+18)[0]&1]
        if not parts:continue
        slots=cache.unpack('8h',mesh+24);ps=slots[7];ts=ps-1;expanded=slots[6]
        if not all(0<=slot<len(vb) for slot in (ps,ts,expanded,slots[0])):
            raise ValueError('Invalid Reach water stream slots')
        if (resource.unpack('IHH',vb[ps])[1:]!=(27,24) or
            resource.unpack('IHH',vb[ts])[1:]!=(26,12) or
            resource.unpack('IHH',vb[expanded])[1:]!=(28,128)):
            raise ValueError('Unreviewed Reach water stream format')
        triangles=payload(vb[ts]+20,resource.unpack('I',vb[ts]+8)[0])
        pairs=list(struct.iter_unpack('<HH',triangles))
        corners=[i for p in parts for i in range(cache.u(p+4),cache.u(p+4)+cache.u(p+8))]
        uv=recover_water_uvs(payload(vb[ps]+20,resource.unpack('I',vb[ps]+8)[0]),
                             resource.unpack('I',vb[ps])[0],corners,triangles)
        index_slot=cache.unpack('h',mesh+40)[0]
        if not 0<=index_slot<len(ib):raise ValueError('Invalid water index buffer')
        ia=ib[index_slot]
        if resource.unpack('I',ia)[0]!=3:raise ValueError('Water must use triangle lists')
        indices=payload(ia+20,resource.unpack('I',ia+8)[0])
        if any(i*2+2>len(indices) for i in corners):raise ValueError('Water index outside buffer')
        if [struct.unpack_from('<H',indices,i*2)[0] for i in corners]!=[v for v,_ in pairs]:
            raise ValueError('Water triangle pairs disagree with visible geometry')
        depths=depths_by_mesh[mi];used.add(mi)
        if set(depths)!={v for v,_ in pairs}:raise ValueError('Water depth vertex set mismatch')
        if any(not math.isfinite(v) or v<0 for v in depths.values()):
            raise ValueError('Invalid reviewed water depth')
        if len(pairs)>65536:raise ValueError('Water parameter indices exceed H3 width')
        parameters=bytearray();native_triangles=bytearray()
        vertex_count=resource.unpack('I',vb[slots[0]])[0]
        for corner,(vertex,water_index) in enumerate(pairs):
            if vertex>=vertex_count:raise ValueError('Water geometry vertex out of bounds')
            u,v=struct.unpack_from('<2f',uv,water_index*8)
            parameters.extend(struct.pack('>9f',0,depths[vertex],0,0,0,0,u,v,0))
            native_triangles.extend(struct.pack('>HH',vertex,corner))
        for slot,record in ((ps,(len(pairs),27,36,bytes(parameters))),
                            (expanded,(len(pairs)//3,26,12,bytes(native_triangles)))):
            if slot in out and out[slot]!=record:raise ValueError('Conflicting shared water buffer')
            out[slot]=record
        reports.append(dict(mesh=mi,corners=len(pairs),parameter_slot=ps,triangle_slot=expanded,
                            geometric_displacement_scale=0,requires_native_material=True))
    if used!=set(depths_by_mesh):raise ValueError('Depth data references a non-water mesh')
    return out,reports
