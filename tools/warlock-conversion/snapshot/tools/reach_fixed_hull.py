"""Stage a native fixed phmo from a converted BSP convex hull.

Use only the base cache's verified single-body Sandbox wall wrapper. Existing
node/region tables remain valid because MapBuilder preserves base addresses.
Inactive mass/inertia defaults stay stock; this adapter must never be used for
dynamic bodies. Scenery/model linkage is deliberately the caller's job.
"""
import math
import struct
import xml.etree.ElementTree as ET
from pathlib import Path


def stage_fixed_hull(builder,hull,material):
    c=builder.cache
    donor=r'objects\levels\dlc\sandbox\sand_wall\sand_wall'
    matches=[t for i,t in c.tags.items() if t['group']=='phmo' and c.name(i)==donor]
    if len(matches)!=1:raise ValueError('Native fixed-hull donor missing or ambiguous')
    at=matches[0]['offset']
    schema=ET.parse(Path(__file__).resolve().parents[1]/'reference/plugins/phmo.xml').getroot()
    allowed={'Rigid Bodies','Materials','Polyhedra','Polyhedron Four Vectors',
             'Polyhedron Plane Equations','Regions','Nodes'}
    for field in schema:
        if field.tag in ('tagblock','dataref') and c.u(at+int(field.get('offset'),0)):
            if field.get('name') not in allowed:raise ValueError('Donor has unrelated physics state')
    body_rows=c.block(at+88,176);poly_rows=c.block(at+172,128)
    if len(body_rows)!=1 or len(poly_rows)!=1 or c.u(at+100)!=1:
        raise ValueError('Expected one fixed convex body and material')
    body=bytearray(c.data[body_rows[0]:body_rows[0]+176])
    if struct.unpack_from('>h',body,26)[0]!=5 or struct.unpack_from('>hh',body,88)!=(4,0):
        raise ValueError('Donor is not a fixed convex body')
    shape=hull['shape'];vectors=hull['vectors'];planes=hull['planes']
    if len(shape)!=96 or struct.unpack_from('>II',shape,8)!=(32,8):
        raise ValueError('Hull must be a native phmo shape at self-offset 32')
    nv,_,nverts=struct.unpack_from('>III',shape,68)
    np=struct.unpack_from('>I',shape,84)[0]
    if len(vectors)!=nv*48 or len(planes)!=np*16:raise ValueError('Native hull array sizes differ')
    center=struct.unpack_from('>3f',shape,48);skin=struct.unpack_from('>f',shape,16)[0]
    points=[]
    for values in struct.iter_unpack('>12f',vectors):
        points.extend(tuple(values[axis*4+k] for axis in range(3)) for k in range(4))
    points=points[:nverts]
    radius=max(math.dist(p,center) for p in points)+skin
    # Round the enclosing radius outward, not inward, when narrowing to f32.
    bits=struct.unpack('>I',struct.pack('>f',radius))[0]
    if struct.unpack('>f',struct.pack('>I',bits))[0]<radius:bits+=1
    struct.pack_into('>3fI',body,8,*center,bits)
    struct.pack_into('>3f',body,96,*center)
    poly=bytearray(c.data[poly_rows[0]:poly_rows[0]+32])+shape
    struct.pack_into('>IhH',poly,0,material['string_id'],0,material['index'])
    struct.pack_into('>2f',poly,12,material['friction'],material['restitution'])
    material_row=struct.pack('>IIhBB',material['string_id'],material['string_id'],-1,0,0)
    root=bytearray(c.data[at:at+408])
    for offset,payload,count in ((88,body,1),(100,material_row,1),(172,poly,1),
                                 (184,vectors,nv),(196,planes,np)):
        struct.pack_into('>III',root,offset,count,builder.alloc(payload),0)
    return bytes(root)
