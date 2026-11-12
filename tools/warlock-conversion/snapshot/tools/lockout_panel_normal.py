"""Fold Lockout's two static, unit-UV normals into one native normal chain.

Keeps single-lobe lighting and animated illumination using a stock Chillout
shader. This is a filtered texture approximation, not shader-equivalence proof.
"""
import numpy as np
from encode_bitmap import mip_size
from normal_strength import decode_blocks, valid_pixels
from fused_ridge_normal import sample, normal


def bake(source, base_tag, detail_tag):
    def decode(tag, dimensions):
        info=source.info(tag)
        if len(info)!=1 or (info[0]['width'],info[0]['height'],info[0]['format'])!=(*dimensions,33):
            raise ValueError('Lockout panel normal dimensions/format changed')
        row=source.c.block(source.c.tags[tag]['offset']+96,56)[0]
        if source.c.unpack('H',row+10)[0]!=0 or source.c.data[row+21]!=3:
            raise ValueError('Lockout panel normals must be linear 2D images')
        raw=source.pixels(tag);offset=0;levels=[]
        for level in range(info[0]['mips']):
            w,h=max(1,dimensions[0]>>level),max(1,dimensions[1]>>level)
            size=mip_size(w,h,33)
            blocks=np.frombuffer(raw[offset:offset+size],np.uint8).reshape(-1,2,8)
            levels.append(valid_pixels(decode_blocks(blocks),w,h));offset+=size
        if offset!=len(raw):raise ValueError('Unexpected Lockout normal mip payload')
        return levels
    base=decode(base_tag,(512,1024));detail=decode(detail_tag,(512,512))
    result=bytearray()
    for level in range(11):
        w,h=max(1,512>>level),max(1,1024>>level)
        yy,xx=np.indices((h,w));uv=np.stack(((xx+.5)/w,(yy+.5)/h),axis=-1)
        value=normal(sample(base[min(level,len(base)-1)],uv))
        layer=normal(sample(detail[min(level,len(detail)-1)],uv))
        value[...,:2]+=layer[...,:2]
        value/=np.linalg.norm(value,axis=-1,keepdims=True)
        if not np.isfinite(value).all():raise ValueError('Nonfinite composed Lockout normal')
        result.extend(np.rint(value[...,:2]*127).astype(np.int8).tobytes())
    class Baked:
        c=source.c
        def info(self,unused):
            return [dict(width=512,height=1024,format=22,mips=11,kind=0,curve=3)]
        def pixels(self,unused,index=0):return bytes(result)
    return Baked()
