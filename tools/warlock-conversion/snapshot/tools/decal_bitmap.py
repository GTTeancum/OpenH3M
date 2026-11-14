"""Bake the separate, untiled decal mask into tiled diffuse alpha for retail.

Authored full-resolution chains. No sprite atlases or generated tail levels.
The mask's alpha replaces diffuse alpha; it is not multiplied by diffuse alpha.
"""
import numpy as np
from PIL import Image
from encode_bitmap import encode_bitmap_base, expand_argb, mip_size


def _chain(source, tag):
    """Validate the entire authored chain before any composition or decoding."""
    infos=source.info(tag)
    if len(infos)!=1 or source.c.u(source.c.tags[tag]['offset']+84):
        raise ValueError('Decal requires a single nonsprite image')
    info=infos[0];w,h,count=info['width'],info['height'],info['mips']
    if not all(isinstance(v,int) and not isinstance(v,bool) for v in (w,h,count)) or not (1<=w<=8192 and 1<=h<=8192 and 1<=count<=max(w,h).bit_length()):
        raise ValueError('Invalid authored decal dimensions or count')
    if info.get('kind',0)!=0:raise ValueError('Decal must be 2D')
    raw=source.pixels(tag)
    sizes=[mip_size(max(1,w>>n),max(1,h>>n),info['format']) for n in range(count)]
    if len(raw)!=sum(sizes):raise ValueError('Authored decal payload length mismatch')
    parts=[];offset=0
    for size in sizes:parts.append(raw[offset:offset+size]);offset+=size
    return info,parts


def _rgba(payload,w,h,fmt):
    if fmt in (0,1,10,11):
        return np.frombuffer(expand_argb(payload,w,h,fmt),np.uint8).reshape(h,w,4)[:,:,[2,1,0,3]]
    if fmt in (14,16):return np.asarray(Image.frombytes('RGBA',(w,h),payload,'bcn',1 if fmt==14 else 3))
    raise ValueError('Unsupported decal pixel format')


def combine_resampled_alpha(source, base_tag, mask_tag, color_scale=(1.,1.,1.)):
    """Combine static images at full dimensions with the authored level count.

    The result is a derived composite, not a byte-exact source copy. The
    output count is the larger authored count; no synthetic tail is added.
    RGB is filtered in linear space; alpha remains linear. Output uses ARGB8 to
    avoid another lossy BC encode. Native sampler addressing is checked by caller.
    """
    scale=np.asarray(color_scale,dtype=np.float32)
    if scale.shape!=(3,) or not np.all(np.isfinite(scale)) or np.any(scale<0) or np.any(scale>1):
        raise ValueError('Decal color scale must fit the normalized texture range')
    images=[]
    for tag in (base_tag,mask_tag):
        info,parts=_chain(source,tag)
        levels=[]
        w,h=info['width'],info['height']; fmt=info['format']
        row=source.c.block(source.c.tags[tag]['offset']+96,56)[0]
        curve=source.c.data[row+21]
        if curve not in (1,3,5):raise ValueError('Unsupported decal color curve')
        for level in range(info['mips']):
            rgba=_rgba(parts[level],w,h,fmt)
            values=rgba.astype(np.float32)/255
            if curve in (1,5):
                rgb=values[:,:,:3];values[:,:,:3]=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
            levels.append(values);w,h=max(1,w//2),max(1,h//2)
        if not levels:raise ValueError('Decal has no authored mips')
        images.append(levels)
    w=max(a[0].shape[1] for a in images);h=max(a[0].shape[0] for a in images)
    width,height=w,h;blocks=[]
    def sample(levels,w,h):
        # Pick the finest authored level no larger than the requested footprint.
        index=0
        while index+1<len(levels) and (levels[index].shape[1]>w or levels[index].shape[0]>h):index+=1
        values=levels[index]
        return np.stack([np.asarray(Image.fromarray(values[:,:,j]).resize((w,h),Image.Resampling.BILINEAR)) for j in range(4)],axis=2)
    for level in range(max(map(len,images))):
        rgb=sample(images[0],w,h)[:,:,:3]*scale;alpha=sample(images[1],w,h)[:,:,3]
        encoded=np.where(rgb<=.0031308,rgb*12.92,1.055*np.maximum(rgb,0)**(1/2.4)-.055)
        rgba=np.rint(np.clip(np.dstack((encoded,alpha)),0,1)*255).astype(np.uint8)
        blocks.append(rgba[:,:,[2,1,0,3]].tobytes())
        w,h=max(1,w//2),max(1,h//2)
    class Combined:
        c=source.c
        def info(self,tag):return [dict(width=width,height=height,format=11,mips=len(blocks),kind=0,curve=1)]
        def pixels(self,tag,index=0):return b''.join(blocks)
    return encode_bitmap_base(Combined(),base_tag,max_dimension=8192,preserve_authored_mips=True)


def combine_bc_alpha(source, base_tag, mask_tag):
    """Join authored BC color/alpha blocks without recompressing either channel."""
    chains=[_chain(source,tag) for tag in (base_tag,mask_tag)]
    base,mask=(x[0] for x in chains)
    w,h=base['width'],base['height']
    if (w,h)!=(mask['width'],mask['height']) or base['mips']!=mask['mips']:
        raise ValueError('Combined decal requires matching dimensions and mip counts')
    if base['format'] not in (14,16) or mask['format']!=16:
        raise ValueError('Combined decal requires BC1/BC3 color and BC3 alpha')
    data=[b''.join(x[1]) for x in chains]
    offsets = [0,0]; blocks = []
    count = base['mips']
    for level in range(count):
        bw,bh=max(1,w>>level),max(1,h>>level)
        sizes=[mip_size(bw,bh,info['format']) for info in (base,mask)]
        parts=[raw[off:off+size] for raw,off,size in zip(data,offsets,sizes)]
        color=np.frombuffer(parts[0],np.uint8).reshape(-1,8 if base['format']==14 else 16)[:,-8:]
        alpha=np.frombuffer(parts[1],np.uint8).reshape(-1,16)[:,:8]
        joined=np.concatenate((alpha,color),axis=1).tobytes()
        before=np.asarray(Image.frombytes('RGBA',(bw,bh),parts[0],'bcn',1 if base['format']==14 else 3))
        mask_pixels=np.asarray(Image.frombytes('RGBA',(bw,bh),parts[1],'bcn',3))
        after=np.asarray(Image.frombytes('RGBA',(bw,bh),joined,'bcn',3))
        # BC1 three-color blocks cannot always be reinterpreted as BC3.
        if not np.array_equal(before[:,:,:3],after[:,:,:3]) or not np.array_equal(mask_pixels[:,:,3],after[:,:,3]):
            raise ValueError('Combined decal changed decoded color or alpha')
        blocks.append(joined); offsets=[off+size for off,size in zip(offsets,sizes)]
    row=source.c.block(source.c.tags[base_tag]['offset']+96,56)[0]
    curve=source.c.data[row+21]
    class Combined:
        c=source.c
        def info(self, tag):return [dict(width=w,height=h,format=16,mips=count,kind=0,curve=curve)]
        def pixels(self, tag,index=0):return b''.join(blocks)
    return encode_bitmap_base(Combined(),base_tag,max_dimension=8192,preserve_authored_mips=True)


def decode(source, tag, level=0):
    info,parts=_chain(source,tag)
    if not 0<=level<len(parts):raise ValueError('Missing authored decal level')
    return _rgba(parts[level],max(1,info['width']>>level),max(1,info['height']>>level),info['format'])


def bake(source, base_tag, mask_tag, tiles):
    """Derived nearest-sampled composition at every authored output level.

    No new source mip is generated: when counts differ the shorter chain's
    final authored image remains the input. Output is not a lossless copy of
    both source textures; it retains the historical mask replacement/tiling.
    """
    if len(tiles)!=2 or not all(np.isfinite(v) and 0<v<=32 for v in tiles):
        raise ValueError('Unsupported decal tile scale')
    chains=[_chain(source,tag) for tag in (base_tag,mask_tag)]
    width=max(x[0]['width'] for x in chains);height=max(x[0]['height'] for x in chains)
    count=max(x[0]['mips'] for x in chains);blocks=[]
    # Nearest sampling preserves the diffuse's encoded RGB values, so retain
    # its authored color curve. The separate mask contributes linear alpha.
    row=source.c.block(source.c.tags[base_tag]['offset']+96,56)[0]
    curve=source.c.data[row+21]
    for level in range(count):
        images=[]
        for info,parts in chains:
            n=min(level,len(parts)-1)
            images.append(_rgba(parts[n],max(1,info['width']>>n),max(1,info['height']>>n),info['format']))
        base,mask=images;w,h=max(1,width>>level),max(1,height>>level)
        u,v=(np.arange(w)+.5)/w,(np.arange(h)+.5)/h
        bx=((u*tiles[0]%1)*base.shape[1]).astype(int)
        by=((v*tiles[1]%1)*base.shape[0]).astype(int)
        mx,my=(u*mask.shape[1]).astype(int),(v*mask.shape[0]).astype(int)
        rgba=base[by[:,None],bx].copy();rgba[:,:,3]=mask[my[:,None],mx,3]
        blocks.append(rgba[:,:,[2,1,0,3]].tobytes())
    class BakedSource:
        c=source.c
        def info(self,tag):return [dict(width=width,height=height,format=11,mips=count,kind=0,curve=curve)]
        def pixels(self,tag,index=0):return b''.join(blocks)
    return encode_bitmap_base(BakedSource(),base_tag,max_dimension=8192,preserve_authored_mips=True)
