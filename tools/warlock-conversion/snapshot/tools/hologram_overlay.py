"""Powerhouse computer overlay bake; native illumination/edge fade stay live.

Source math: HaloShaderGenerator 5af3671, overlays.fx and self_illumination.fx.
The static overlay multiplies illumination before edge fade. Bake only its RGB
sample/tint, fold intensity into illumination intensity, preserve color animation.
"""
import io
import numpy as np
from PIL import Image
from encode_bitmap import encode_bitmap_base, expand_argb, mip_size


def decode(source, tag):
    info = source.info(tag)
    if len(info) != 1:
        raise ValueError('Overlay bake requires one image')
    info = info[0]
    w, h, fmt = info['width'], info['height'], info['format']
    data = source.pixels(tag)
    if fmt in (0, 1, 3, 10, 11):
        rgba = np.frombuffer(expand_argb(data, w, h, fmt), np.uint8).reshape(h, w, 4)[:, :, [2, 1, 0, 3]]
    elif fmt in (14, 15, 16):
        rgba = np.asarray(Image.frombytes('RGBA', (w,h), data[:mip_size(w,h,fmt)], 'bcn', {14:1,15:2,16:3}[fmt]))
    else:
        raise ValueError('Unsupported overlay bitmap encoding')
    row = source.c.block(source.c.tags[tag]['offset']+0x60, 56)[0]
    if source.c.unpack('H', row+10)[0] != 0:
        raise ValueError('Overlay bake needs a 2D image')
    curve = source.c.data[row+21]
    rgb = rgba[:,:,:3].astype(np.float32)/255
    if curve in (1,5):
        rgb = np.where(rgb <= .04045, rgb/12.92, ((rgb+.055)/1.055)**2.4)
    elif curve != 3:
        raise ValueError('Unverified overlay texture sampling curve')
    return rgb


def sample(rgb, width, height):
    # Bilinear wrap sampling at output texel centers, in linear color space.
    h,w = rgb.shape[:2]
    x=(np.arange(width)+.5)*w/width-.5
    y=(np.arange(height)+.5)*h/height-.5
    ix,iy=np.floor(x).astype(int),np.floor(y).astype(int)
    fx,fy=(x-ix)[None,:,None],(y-iy)[:,None,None]
    return ((rgb[iy[:,None]%h,ix%w]*(1-fx)+rgb[iy[:,None]%h,(ix+1)%w]*fx)*(1-fy)
          +(rgb[(iy[:,None]+1)%h,ix%w]*(1-fx)+rgb[(iy[:,None]+1)%h,(ix+1)%w]*fx)*fy)


def bake(materials, post):
    s=materials.source
    textures,names=materials.parameters(s,materials.source_strings,post)
    rows=s.block(post+28,16)
    values={name:s.unpack('4f',row) for name,row in zip(names,rows)}
    samplers=s.block(post+16,28)
    if values['albedo_color'][:3] != (0.,0.,0.):
        raise ValueError('Hologram bake requires zero albedo contribution')
    for name in ('self_illum_map','overlay_map'):
        if values[name] != (1.,1.,0.,0.):
            raise ValueError('Hologram bake requires identical identity UVs')
        row=samplers[textures.index(name)]
        if s.unpack('h4BbBhH',row+16) != (0,0,0,0,0,names.index(name),0,0,0):
            raise ValueError('Hologram bake sampler differs from audited bilinear wrap')
    for row in s.block(post+80,4):
        register,function,constant=s.unpack('HBB',row)
        if constant != names.index('self_illum_color'):
            raise ValueError('Hologram bake would consume an animated parameter')
    tint=np.array(values['overlay_tint'][:3],dtype=np.float32)
    intensity=values['overlay_intensity']
    if np.any(tint<0) or np.any(tint>1) or len(set(intensity))!=1 or not 0<intensity[0]<=32:
        raise ValueError('Hologram overlay constants outside bake limits')
    base=s.u(samplers[textures.index('self_illum_map')]+12)&65535
    overlay=s.u(samplers[textures.index('overlay_map')]+12)&65535
    # Stock native dither is available even when the MCC shared page is not.
    # Keep the authored linear curve, bilinear wrap and UV contract above.
    from native_dither_overlay import read_overlay
    overlay_rgb = read_overlay(materials, overlay)
    rgb=sample(decode(materials.bitmaps,base),512,512)*sample(overlay_rgb,512,512)*tint
    blocks=[]
    while True:
        encoded=np.where(rgb<=.0031308,rgb*12.92,1.055*np.maximum(rgb,0)**(1/2.4)-.055)
        rgba=np.full((*rgb.shape[:2],4),255,np.uint8)
        rgba[:,:,:3]=np.rint(np.clip(encoded,0,1)*255).astype(np.uint8)
        stream=io.BytesIO();Image.fromarray(rgba).save(stream,format='DDS',pixel_format='DXT5')
        data=stream.getvalue()
        if data[84:88]!=b'DXT5' or len(data)-128!=mip_size(rgb.shape[1],rgb.shape[0],16):
            raise ValueError('Unexpected DDS encoder output')
        blocks.append(data[128:])
        if rgb.shape[0]==1:break
        rgb=rgb.reshape(rgb.shape[0]//2,2,rgb.shape[1]//2,2,3).mean(axis=(1,3))
    class Baked:
        c=s
        def info(self,tag):return [dict(width=512,height=512,format=16,mips=10,kind=0,curve=1)]
        def pixels(self,tag,index=0):return b''.join(blocks)
    bitmap=materials.bitmap_resource(*encode_bitmap_base(Baked(),base,preserve_bc_mips=True))
    return bitmap,intensity[0]
