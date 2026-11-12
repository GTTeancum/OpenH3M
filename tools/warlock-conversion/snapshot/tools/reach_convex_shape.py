"""Reach MCC BSP convex hull -> original H3 phmo shape payload.

This does not turn BSP instances into scenario objects. The caller supplies the
phmo shape's self-offset and builds its material, rigid-body and placement data.
Layouts: TagTool HkConvexVerticesShape and paired Assembly phmo schemas. Native
shape type/radius/refcount corroborated against Sandbox sand_wall.phmo.
"""
import math
import struct


def convert_definition_hulls(reader, definition):
    """Consume each definition's complete concatenated hull arrays in order."""
    count,headers=reader.block(definition+260,160)
    nv,vectors=reader.block(definition+272,48)
    np,planes=reader.block(definition+284,16)
    va=pa=0;result=[]
    for index in range(count):
        header=headers[index*160:(index+1)*160]
        nvec=struct.unpack_from('<I',header,88)[0]
        nplane=struct.unpack_from('<I',header,120)[0]
        if va+nvec>nv or pa+nplane>np:
            raise ValueError('Definition hull span exceeds concatenated arrays')
        result.append(convert_bsp_hull(header,vectors[va*48:(va+nvec)*48],
                                      planes[pa*16:(pa+nplane)*16],user_data=32+index*128))
        va+=nvec;pa+=nplane
    if va!=nv or pa!=np:
        raise ValueError('Unowned hull vectors or planes')
    return result


def convert_bsp_hull(header, vectors, planes, *, user_data):
    header=bytes(header)
    if len(header)!=160 or len(vectors)%48 or len(planes)%16:
        raise ValueError('Malformed Reach MCC hull buffers')
    if not 0<=user_data<=0xffffffff:
        raise ValueError('Native shape self-offset exceeds pointer width')
    if any(struct.unpack_from('<Q',header,x)[0] for x in (0,80,104,112,128)):
        raise ValueError('Serialized hull contains runtime pointers')
    if struct.unpack_from('<Q',header,16)[0]!=0x706f6f70:
        raise ValueError('Expected Reach BSP hull ownership marker')
    if struct.unpack_from('<I',header,24)[0]!=6:
        raise ValueError('Expected Reach convex vertex shape')
    # Reject unexpected state rather than silently losing new Havok fields.
    if any(header[12:16]+header[28:32]+header[36:48]+header[100:104]+header[136:144]+header[148:160]):
        raise ValueError('Unrepresented Reach convex metadata')
    nv,vc,nverts=struct.unpack_from('<III',header,88)
    np,pc=struct.unpack_from('<II',header,120)
    if nv!=(nverts+3)//4 or nv*48!=len(vectors) or np*16!=len(planes):
        raise ValueError('Hull array counts disagree')
    if not nverts or not np or (vc&0x7fffffff)<nv or (pc&0x7fffffff)<np:
        raise ValueError('Invalid hull allocation')
    if any(not math.isfinite(x) for data in (vectors,planes) for (x,) in struct.iter_unpack('<f',data)):
        raise ValueError('Nonfinite hull geometry')
    radius=struct.unpack_from('<f',header,32)[0]
    if not math.isfinite(radius) or radius<0:raise ValueError('Invalid convex radius')
    native=bytearray(96)
    struct.pack_into('>HHII',native,4,*struct.unpack_from('<HH',header,8),user_data,8)
    # Copy IEEE bits, including both AABB homogeneous coordinates.
    for source,target,fmt in ((32,16,'I'),(48,32,'8I'),(88,68,'3I'),(120,84,'2I')):
        struct.pack_into('>'+fmt,native,target,*struct.unpack_from('<'+fmt,header,source))
    def swap(data):return b''.join(struct.pack('>I',x) for (x,) in struct.iter_unpack('<I',data))
    return dict(shape=bytes(native),vectors=swap(vectors),planes=swap(planes),
                source_material=struct.unpack_from('<i',header,144)[0])
