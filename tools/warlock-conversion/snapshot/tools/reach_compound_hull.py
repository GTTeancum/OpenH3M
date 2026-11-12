"""Native fixed compound hull: one body/list per Reach definition.

Uses Sandbox's half-door list structure instead of creating one scenario object
per component. Runtime acceptance remains required before production deployment.
"""
import math
import struct
import numpy as np
from pathlib import Path
import xml.etree.ElementTree as ET
from reach_fixed_hull import stage_fixed_hull


def stage_compound_hull(builder,hulls,materials):
    if not hulls or len(hulls)>32767 or len(hulls)!=len(materials):
        raise ValueError('Invalid compound hull/material count')
    if len(hulls)==1:
        return stage_fixed_hull(builder,hulls[0],materials[0])
    c=builder.cache
    donor=r'objects\levels\dlc\sandbox\sand_wall_halfdoor\sand_wall_halfdoor'
    matches=[t['offset'] for i,t in c.tags.items() if t['group']=='phmo' and c.name(i)==donor]
    if len(matches)!=1:raise ValueError('Native compound donor missing/ambiguous')
    at=matches[0];bs=c.block(at+88,176);ls=c.block(at+220,80)
    schema=ET.parse(Path(__file__).resolve().parents[1]/'reference/plugins/phmo.xml').getroot()
    allowed={'Rigid Bodies','Materials','Polyhedra','Polyhedron Four Vectors',
             'Polyhedron Plane Equations','Lists','List Shapes','Regions','Nodes'}
    for field in schema:
        if field.tag in ('tagblock','dataref') and c.u(at+int(field.get('offset'),0)):
            if field.get('name') not in allowed:raise ValueError('Compound donor has unrelated physics state')
    polys=c.block(at+172,128);children=c.block(at+232,16)
    if len(bs)!=1 or len(ls)!=1 or len(polys)!=3 or len(children)!=3:
        raise ValueError('Unexpected half-door compound layout')
    body=bytearray(c.data[bs[0]:bs[0]+176]);lst=bytearray(c.data[ls[0]:ls[0]+80])
    if c.unpack('h',bs[0]+26)[0]!=5 or c.unpack('hh',bs[0]+88)!=(14,0):
        raise ValueError('Compound donor is not one fixed list body')
    for i,ch in enumerate(children):
        if c.unpack('hh',ch)!=(4,i) or c.u(ch+12)!=3:
            raise ValueError('Compound donor has non-polyhedron children')
    if c.u(ls[0]+12)!=10 or c.u(ls[0]+28)!=3:
        raise ValueError('Unexpected native list shape')
    points=[];skins=[];polydata=bytearray();vectors=bytearray();planes=bytearray()
    material_rows=bytearray();shape_rows=bytearray()
    prefix=bytes(c.data[polys[0]:polys[0]+32])
    for index,(h,m) in enumerate(zip(hulls,materials)):
        shape=h['shape']
        if len(shape)!=96 or struct.unpack_from('>II',shape,8)!=(32+index*128,8):
            raise ValueError('Compound shape self-offset/type mismatch')
        nv,_,nverts=struct.unpack_from('>III',shape,68);np_=struct.unpack_from('>I',shape,84)[0]
        if len(h['vectors'])!=nv*48 or len(h['planes'])!=np_*16:
            raise ValueError('Compound hull allocation mismatch')
        local=[tuple(v[a*4+k] for a in range(3)) for v in struct.iter_unpack('>12f',h['vectors']) for k in range(4)][:nverts]
        if not local:raise ValueError('Empty compound hull')
        skin=struct.unpack_from('>f',shape,16)[0]
        points.extend(local);skins.extend([skin]*len(local))
        poly=bytearray(prefix)+shape
        struct.pack_into('>IhH',poly,0,m['string_id'],index,m['index'])
        struct.pack_into('>2f',poly,12,m['friction'],m['restitution'])
        polydata.extend(poly);vectors.extend(h['vectors']);planes.extend(h['planes'])
        material_rows.extend(struct.pack('>IIhBB',m['string_id'],m['string_id'],-1,0,0))
        child=bytearray(c.data[children[0]:children[0]+16])
        struct.pack_into('>hh',child,0,4,index);struct.pack_into('>I',child,12,len(hulls))
        shape_rows.extend(child)
    points=np.asarray(points,dtype=np.float64);skins=np.asarray(skins)
    if not np.isfinite(points).all() or not np.isfinite(skins).all() or np.any(skins<0):
        raise ValueError('Nonfinite compound dimensions')
    low=(points-skins[:,None]).min(axis=0);high=(points+skins[:,None]).max(axis=0)
    center=((low+high)*.5).astype(np.float32)
    half=np.maximum(high-center.astype(float),center.astype(float)-low)
    rounded=half.astype(np.float32)
    rounded=np.where(rounded.astype(float)<half,np.nextafter(rounded,np.float32(np.inf)),rounded)
    radius=max(math.dist(v,center)+s for v,s in zip(points,skins))
    radius32=np.float32(radius)
    if float(radius32)<radius:radius32=np.nextafter(radius32,np.float32(np.inf))
    struct.pack_into('>3ff',body,8,*center,float(radius32))
    struct.pack_into('>3f',body,96,*center)
    struct.pack_into('>II',lst,28,len(hulls),0x80000000|len(hulls))
    struct.pack_into('>3f',lst,48,*rounded);struct.pack_into('>3f',lst,64,*center)
    root=bytearray(c.data[at:at+408])
    # Retain the donor's fixed body and one-node region linkage; replace all
    # variable compound arrays rather than inheriting its three wall pieces.
    for offset,data,count in ((88,body,1),(100,material_rows,len(hulls)),(172,polydata,len(hulls)),
                              (184,vectors,len(vectors)//48),(196,planes,len(planes)//16),
                              (220,lst,1),(232,shape_rows,len(hulls))):
        struct.pack_into('>III',root,offset,count,builder.alloc(data),0)
    return bytes(root)
