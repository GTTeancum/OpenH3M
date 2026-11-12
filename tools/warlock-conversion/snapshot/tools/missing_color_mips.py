"""Generate missing color mips for explicitly audited opaque diffuse images."""
import io
import numpy as np
from PIL import Image
from encode_bitmap import encode_bitmap_base

PREFIX = 'levels\\solo\\s3d_tutorial\\bitmaps\\'
NAMES = {PREFIX+n: size for n,size in (
    ('unsc_ship_12_diff',(1024,1024)), ('unsc_ship_14_diff',(512,1024)),
    ('unsc_panel_indus_06_diff',(1024,1024)), ('unsc_metal_trim_01_diff',(1024,512)))}


def encode(source, tag):
    info = source.info(tag)
    if len(info)!=1 or info[0]['format']!=14 or info[0]['mips']!=1:
        raise ValueError('Audited single-level diffuse format changed')
    w,h=info[0]['width'],info[0]['height']
    if (w,h)!=NAMES[source.c.name(tag)]:
        raise ValueError('Audited diffuse dimensions changed')
    rgba=np.asarray(Image.frombytes('RGBA',(w,h),source.pixels(tag),'bcn',1))
    if not np.all(rgba[:,:,3]==255):
        raise ValueError('Diffuse mip generation requires opaque color')
    row=source.c.block(source.c.tags[tag]['offset']+96,56)[0]
    curve=source.c.data[row+21]
    values=rgba[:,:,:3].astype(np.float32)/255
    if curve in (1,5):
        values=np.where(values<=.04045,values/12.92,((values+.055)/1.055)**2.4)
    elif curve!=3:
        raise ValueError('Unaudited color curve')
    width,height=w//2,h//2
    values=values.reshape(height,2,width,2,3).mean(axis=(1,3))
    blocks=[]
    while True:
        colors=values if curve==3 else np.where(values<=.0031308,values*12.92,1.055*np.maximum(values,0)**(1/2.4)-.055)
        pixels=np.rint(np.clip(colors,0,1)*255).astype(np.uint8)
        stream=io.BytesIO()
        Image.fromarray(pixels).save(stream,format='DDS',pixel_format='DXT1')
        dds=stream.getvalue()
        if dds[:4]!=b'DDS ' or dds[84:88]!=b'DXT1':
            raise ValueError('BC1 encoder returned unexpected format')
        blocks.append(dds[128:])
        h,w=values.shape[:2]
        if h==w==1:break
        fh,fw=2 if h>1 else 1,2 if w>1 else 1
        values=values.reshape(h//fh,fh,w//fw,fw,3).mean(axis=(1,3))
    class Generated:
        c=source.c
        def info(self, tag):return [dict(width=width,height=height,format=14,mips=len(blocks),kind=0,curve=curve)]
        def pixels(self, tag, index=0):return b''.join(blocks)
    return encode_bitmap_base(Generated(),tag,preserve_bc_mips=True)
