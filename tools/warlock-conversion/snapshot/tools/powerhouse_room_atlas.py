"""Spatial C0-only atlas fill; preserve every nonambient compressed slice."""
import io
import numpy as np
from PIL import Image
from scipy.ndimage import maximum_filter
from encode_bitmap import encode_lightmap_pixels, mip_size
from powerhouse_room_lighting import weights


def raster_mask(geometry, width, height):
    high = np.zeros((height,width),np.float32)
    low = np.ones_like(high)
    covered = np.zeros_like(high,dtype=bool)
    for xyz,uv,triangles,owner in geometry:
        pixel = uv*np.array([width,height])-.5
        for indices in triangles:
            p = pixel[indices]
            a,b,c = p
            det = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(det)<1e-8:
                continue
            lo = np.maximum(np.ceil(p.min(axis=0)).astype(int),0)
            hi = np.minimum(np.floor(p.max(axis=0)).astype(int),[width-1,height-1])
            if np.any(hi<lo):
                continue
            x,y = np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1))
            u = ((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/det
            v = ((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/det
            w = 1-u-v
            inside = (u>=-1e-6)&(v>=-1e-6)&(w>=-1e-6)
            if not np.any(inside):
                continue
            point = u[inside,None]*xyz[indices[0]]+v[inside,None]*xyz[indices[1]]+w[inside,None]*xyz[indices[2]]
            value = weights(point)
            xx,yy = x[inside],y[inside]
            high[yy,xx] = np.maximum(high[yy,xx],value)
            low[yy,xx] = np.minimum(low[yy,xx],value)
            covered[yy,xx] = True
    if np.any((high-low>.02)&covered):
        raise ValueError('Shared atlas texels span different room weights')
    # Extend into unoccupied atlas gutters only; never overwrite another island.
    padding = maximum_filter(high,size=5,mode='constant')
    high[~covered] = padding[~covered]
    return high


def decode_bc3(data,width,height):
    return np.asarray(Image.frombytes('RGBA',(width,height),data,'bcn',3),dtype=np.float64)/255.


def decode_c0(a,b,scale):
    return ((a[:,:,:3]+b[:,:,:3])*2-2)*(a[:,:,3]*b[:,:,3]*scale)[:,:,None]


def encode_c0(values,scale):
    magnitude=np.max(abs(values),axis=2)
    if not np.isfinite(values).all() or np.any(magnitude>scale):
        raise ValueError('Room atlas C0 exceeds its native compression range')
    rgba=np.zeros((*magnitude.shape,4),np.float64)
    rgba[:,:,:3]=.5+np.divide(values,magnitude[:,:,None],out=np.zeros_like(values),where=magnitude[:,:,None]>0)*.25
    product=magnitude/scale*255**2
    lower=np.maximum(1,np.floor(np.sqrt(product)))
    upper=np.maximum(1,np.ceil(np.sqrt(product)))
    partner_lower=np.rint(product/lower).clip(0,255)
    partner_upper=np.rint(product/upper).clip(0,255)
    choose_lower=abs(lower*partner_lower-product)<=abs(upper*partner_upper-product)
    first=np.rint(rgba*255).clip(0,255).astype(np.uint8)
    second=first.copy()
    first[:,:,3]=np.where(choose_lower,lower,upper).astype(np.uint8)
    second[:,:,3]=np.where(choose_lower,partner_lower,partner_upper).astype(np.uint8)
    return first,second


def bake(cache,lighting,bitmaps,tag,amount,quarter_stops):
    geometry=cache.powerhouse_room_atlas_geometry[lighting]
    info=bitmaps.info(tag)
    if len(info)!=1 or info[0]['format']!=16 or info[0]['mips']!=1:
        raise ValueError('Room atlas requires a single BC3 array')
    row=cache.block(cache.tags[tag]['offset']+96,56)[0]
    depth=cache.data[row+8]
    if depth!=8 or cache.unpack('H',row+10)[0]!=3:
        raise ValueError('Room atlas requires eight SH slices')
    width,height=info[0]['width'],info[0]['height']
    mask=raster_mask(geometry,width,height)
    if not np.any(mask):
        raise ValueError('Room atlas mask is empty')
    size=mip_size(width,height,16)
    original=bitmaps.pixels(tag)
    if len(original)!=size*depth:
        raise ValueError('Unexpected room atlas data size')
    scale=cache.unpack('f',lighting+8)[0]*2**(quarter_stops/4)
    if not np.isfinite(scale) or scale<=0:
        raise ValueError('Invalid C0 compression scale')
    first=decode_bc3(original[:size],width,height)
    second=decode_bc3(original[size:2*size],width,height)
    before=decode_c0(first,second,scale)
    # Preserve highlight blocks exactly. A single replacement palette cannot
    # represent their wide HDR range accurately alongside a small shadow fill.
    brightness=np.max(abs(before),axis=2)
    dark_blocks=brightness.reshape(height//4,4,width//4,4).max(axis=(1,3))<.5
    fully_inside=mask.reshape(height//4,4,width//4,4).min(axis=(1,3))>0
    eligible=np.repeat(np.repeat(dark_blocks&fully_inside,4,axis=0),4,axis=1)
    taper=np.clip(1-brightness/.5,0,1)
    mask=mask*eligible*taper*taper
    if not np.any(mask):
        raise ValueError('No eligible dark interior atlas blocks')
    desired=before+mask[:,:,None]*amount*np.array([1.,.96,.88])
    encoded=encode_c0(desired,scale)
    # Reuse untouched source blocks and all directional coefficients verbatim.
    active=mask.reshape(height//4,4,width//4,4).max(axis=(1,3)).reshape(-1)>0
    parts=[]
    for index in (0,1):
        stream=io.BytesIO()
        Image.fromarray(encoded[index]).save(stream,format='DDS',pixel_format='DXT5')
        dds=stream.getvalue()
        if dds[84:88]!=b'DXT5' or len(dds)!=128+size:
            raise ValueError('Unexpected room atlas DDS encoding')
        replacement=np.frombuffer(dds[128:],np.uint8).reshape(-1,16)
        blocks=np.frombuffer(original[index*size:(index+1)*size],np.uint8).reshape(-1,16).copy()
        blocks[active]=replacement[active]
        parts.append(blocks.tobytes())
    after=decode_c0(decode_bc3(parts[0],width,height),decode_bc3(parts[1],width,height),scale)
    error=abs(after-desired)
    # Leave blocks with an inaccurate compressed fit authored, rather than
    # accepting a bright speck or a hue shift from the replacement palette.
    rejected=error.max(axis=2).reshape(height//4,4,width//4,4).max(axis=(1,3)).reshape(-1)>.1
    rejected &= active
    for index in (0,1):
        blocks=np.frombuffer(parts[index],np.uint8).reshape(-1,16).copy()
        source=np.frombuffer(original[index*size:(index+1)*size],np.uint8).reshape(-1,16)
        blocks[rejected]=source[rejected]
        parts[index]=blocks.tobytes()
    rejected_pixels=np.repeat(np.repeat(rejected.reshape(height//4,width//4),4,axis=0),4,axis=1)
    mask[rejected_pixels]=0
    active &= ~rejected
    if not np.any(active):
        raise ValueError('No atlas fill blocks survived compression limits')
    desired=before+mask[:,:,None]*amount*np.array([1.,.96,.88])
    after=decode_c0(decode_bc3(parts[0],width,height),decode_bc3(parts[1],width,height),scale)
    error=abs(after-desired)
    if float(error.max())>.1 or float(error[mask>0].mean())>.025:
        raise ValueError(f'Room atlas compression error exceeds limits: {error.max()}, {error[mask>0].mean()}')
    raw=b''.join(parts)+original[2*size:]
    return encode_lightmap_pixels(raw,width,height,depth,cache.data[row+21]),dict(
        masked_texels=int(np.count_nonzero(mask)),changed_blocks_per_slice=int(active.sum()),
        rejected_blocks_preserved=int(rejected.sum()),
        maximum_C0_error=float(error.max()),mean_masked_C0_error=float(error[mask>0].mean()),
        directional_slices_bit_exact=True,source_scale=scale,amount=amount)
