"""Bake Reach's multiplied diffuse/specular mask for native H3 texture masking.

The authored default-albedo alpha is base * detail * albedo tint alpha. Reach's
multiplied mask multiplies that by the specular texture alpha. H3 can consume
the result using its stock texture-mask program, without changing the engine.
The periodic bake is capped at 512 square and includes filtered mip levels.
"""
import math
from fractions import Fraction
from functools import reduce
import numpy as np
from PIL import Image
from encode_bitmap import mip_size


def encode_alpha_bc3(alpha):
    """BC3 blocks with white RGB and fitted alpha endpoints/selectors."""
    height, width = alpha.shape
    padded = np.pad(alpha, ((0, (-height) % 4), (0, (-width) % 4)), mode='edge')
    blocks = padded.reshape(padded.shape[0]//4, 4, padded.shape[1]//4, 4).transpose(0, 2, 1, 3).reshape(-1, 16)
    maximum, minimum = blocks.max(axis=1).astype(np.int32), blocks.min(axis=1).astype(np.int32)
    table = np.stack([maximum, minimum] + [((7-j)*maximum+j*minimum)//7 for j in range(1,7)], axis=1)
    indices = abs(blocks.astype(np.int32)[:, :, None]-table[:, None, :]).argmin(axis=2).astype(np.uint64)
    packed = np.zeros(len(blocks), dtype=np.uint64)
    for j in range(16):
        packed |= indices[:, j] << np.uint64(j*3)
    result = np.zeros((len(blocks), 16), dtype=np.uint8)
    result[:, 0], result[:, 1] = maximum, minimum
    for j in range(6):
        result[:, j+2] = ((packed >> np.uint64(j*8)) & 255).astype(np.uint8)
    result[:, 8:12] = 255  # Both RGB565 color endpoints are white.
    return result.tobytes()


def alpha_plane(source, datum, scale, size):
    info = source.info(datum & 65535)[0]
    pixels = source.pixels(datum & 65535)
    width, height, fmt = info['width'], info['height'], info['format']
    level = max(0, math.ceil(math.log2(max(abs(scale[0])*width, abs(scale[1])*height)/size)))
    level = min(level, info['mips']-1)
    for _ in range(level):
        pixels = pixels[mip_size(width,height,fmt):]
        width, height = max(1,width//2), max(1,height//2)
    if fmt == 11:
        alpha = np.frombuffer(pixels[:width*height*4],dtype=np.uint8).reshape(height,width,4)[:,:,3]
    elif fmt in (14,15,16):
        decoded = Image.frombytes('RGBA',(width,height),pixels[:mip_size(width,height,fmt)],'bcn',{14:1,15:2,16:3}[fmt])
        alpha = np.asarray(decoded)[:,:,3]
    else:
        raise ValueError('Unsupported specular-mask source format')
    return alpha.astype(np.float64)/255


def bake_mask(material, source, size=512):
    if material['options']['albedo'] != 'default' or material['options']['specular_mask'] != 'specular_mask_mult_diffuse':
        raise ValueError('Only reviewed default-albedo multiplied specular masks can be baked')
    if material.get('animated'):
        raise ValueError('Animated multiplied masks require a time-dependent conversion, not a static bake')
    names = ('base_map','detail_map','specular_mask_texture')
    transforms = [material['constants'][name] for name in names]
    periods = []
    for axis in range(2):
        frequencies = [Fraction(abs(t[axis])).limit_denominator(1000) for t in transforms if t[axis]]
        denominator = math.lcm(*(f.denominator for f in frequencies))
        numerator = reduce(math.gcd, (f.numerator*(denominator//f.denominator) for f in frequencies))
        period = denominator/numerator
        if any(abs(t[axis]*period-round(t[axis]*period)) > 1e-4 for t in transforms):
            raise ValueError('Cannot preserve mask repetition within tolerance')
        periods.append(period)
    x,y = np.meshgrid((np.arange(size)+.5)/size*periods[0],(np.arange(size)+.5)/size*periods[1])
    result = np.full((size,size),material['constants']['albedo_color'][3],dtype=np.float64)
    for name, transform in zip(names,transforms):
        texture = material['textures'][name]
        if texture['address_mode'] != 0 or texture['bitmap_index'] or texture['external_mode']:
            raise ValueError('Baked mask requires ordinary repeating 2D textures')
        try:
            plane = alpha_plane(source,texture['datum'],(transform[0]*periods[0],transform[1]*periods[1]),size)
        finally:
            source.clear()
        height,width = plane.shape
        tx=(x*transform[0]+transform[2])*width-.5
        ty=(y*transform[1]+transform[3])*height-.5
        ix,iy=np.floor(tx).astype(np.int64),np.floor(ty).astype(np.int64)
        fx,fy=tx-ix,ty-iy
        result *= ((1-fy)*((1-fx)*plane[iy%height,ix%width]+fx*plane[iy%height,(ix+1)%width])+
                   fy*((1-fx)*plane[(iy+1)%height,ix%width]+fx*plane[(iy+1)%height,(ix+1)%width]))
    levels=[]
    while True:
        levels.append(encode_alpha_bc3(np.rint(np.clip(result,0,1)*255).astype(np.uint8)))
        if result.shape == (1,1):
            break
        h,w=result.shape
        result=result.reshape(h//2,2,w//2,2).mean(axis=(1,3))
    return dict(pixels=b''.join(levels),width=size,height=size,format=16,mips=len(levels),kind=0,curve=3), (1/periods[0],1/periods[1],0.,0.)
