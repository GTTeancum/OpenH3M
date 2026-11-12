"""Bake the separate, untiled decal mask into tiled diffuse alpha for retail.

POC: nearest sampling, one mip, maximum 512 pixels. No sprite atlases.
The mask's alpha replaces diffuse alpha; it is not multiplied by diffuse alpha.
"""
import numpy as np
from PIL import Image
from encode_bitmap import encode_bitmap_base, expand_argb, mip_size


def combine_resampled_alpha(source, base_tag, mask_tag, color_scale=(1.,1.,1.)):
    """Combine differently sized static images, preserving a full output mip chain.

    RGB is filtered in linear space; alpha remains linear. Output uses ARGB8 to
    avoid another lossy BC encode. Native sampler addressing is checked by caller.
    """
    scale=np.asarray(color_scale,dtype=np.float32)
    if scale.shape!=(3,) or not np.all(np.isfinite(scale)) or np.any(scale<0) or np.any(scale>1):
        raise ValueError('Decal color scale must fit the normalized texture range')
    images=[]
    for tag in (base_tag,mask_tag):
        info=source.info(tag)
        if len(info)!=1 or source.c.u(source.c.tags[tag]['offset']+84):
            raise ValueError('Resampled decal requires a single nonsprite image')
        info=info[0]; raw=source.pixels(tag); levels=[]; offset=0
        w,h=info['width'],info['height']; fmt=info['format']
        row=source.c.block(source.c.tags[tag]['offset']+96,56)[0]
        curve=source.c.data[row+21]
        if curve not in (1,3,5):raise ValueError('Unsupported decal color curve')
        for level in range(info['mips']):
            size=mip_size(w,h,fmt); payload=raw[offset:offset+size]
            if fmt in (14,16):
                rgba=np.asarray(Image.frombytes('RGBA',(w,h),payload,'bcn',1 if fmt==14 else 3))
            elif fmt in (0,1,10,11):
                rgba=np.frombuffer(expand_argb(payload,w,h,fmt),np.uint8).reshape(h,w,4)[:,:,[2,1,0,3]]
            else:raise ValueError('Unsupported resampled decal format')
            values=rgba.astype(np.float32)/255
            if curve in (1,5):
                rgb=values[:,:,:3];values[:,:,:3]=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
            levels.append(values);offset+=size;w,h=max(1,w//2),max(1,h//2)
        if not levels:raise ValueError('Decal has no authored mips')
        images.append(levels)
    w=min(512,max(a[0].shape[1] for a in images));h=min(512,max(a[0].shape[0] for a in images))
    width,height=w,h;blocks=[]
    def sample(levels,w,h):
        # Pick the finest authored level no larger than the requested footprint.
        index=0
        while index+1<len(levels) and (levels[index].shape[1]>w or levels[index].shape[0]>h):index+=1
        values=levels[index]
        return np.stack([np.asarray(Image.fromarray(values[:,:,j]).resize((w,h),Image.Resampling.BILINEAR)) for j in range(4)],axis=2)
    while True:
        rgb=sample(images[0],w,h)[:,:,:3]*scale;alpha=sample(images[1],w,h)[:,:,3]
        encoded=np.where(rgb<=.0031308,rgb*12.92,1.055*np.maximum(rgb,0)**(1/2.4)-.055)
        rgba=np.rint(np.clip(np.dstack((encoded,alpha)),0,1)*255).astype(np.uint8)
        blocks.append(rgba[:,:,[2,1,0,3]].tobytes())
        if w==h==1:break
        w,h=max(1,w//2),max(1,h//2)
    class Combined:
        c=source.c
        def info(self,tag):return [dict(width=width,height=height,format=11,mips=len(blocks),kind=0,curve=1)]
        def pixels(self,tag,index=0):return b''.join(blocks)
    return encode_bitmap_base(Combined(),base_tag,preserve_color_mips=True)


def combine_bc_alpha(source, base_tag, mask_tag):
    """Join authored BC color/alpha blocks without recompressing either channel."""
    infos = [source.info(tag) for tag in (base_tag, mask_tag)]
    if any(len(info) != 1 for info in infos):
        raise ValueError('Combined decal requires single-image bitmaps')
    base, mask = (info[0] for info in infos)
    w, h = base['width'], base['height']
    if (w, h) != (mask['width'], mask['height']) or max(w,h)>512:
        raise ValueError('Combined decal requires matching dimensions within 512 pixels')
    if base['format'] not in (14,16) or mask['format'] != 16:
        raise ValueError('Combined decal requires BC1/BC3 color and BC3 alpha')
    data = [source.pixels(tag) for tag in (base_tag,mask_tag)]
    offsets = [0,0]; blocks = []
    count = min(base['mips'],mask['mips'])
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
    return encode_bitmap_base(Combined(),base_tag,preserve_bc_mips=True)


def decode(source, tag):
    info = source.info(tag)[0]
    w, h, fmt = info['width'], info['height'], info['format']
    data = source.pixels(tag)
    level = 0
    while max(w, h) > 512:
        level += 1
        if level >= info['mips']:
            raise ValueError('Decal bitmap has no mip within the POC size limit')
        data = data[mip_size(w, h, fmt):]
        w, h = max(1, w // 2), max(1, h // 2)
    if fmt in (0, 1, 10, 11):
        bgra = np.frombuffer(expand_argb(data, w, h, fmt), dtype=np.uint8).reshape(h, w, 4)
        return bgra[:, :, [2, 1, 0, 3]]
    if fmt not in (14, 16):
        raise ValueError(f'Unsupported decal diffuse/mask format {fmt}')
    return np.array(Image.frombytes('RGBA', (w, h), data[:mip_size(w, h, fmt)],
                                   'bcn', 1 if fmt == 14 else 3))


def bake(source, base_tag, mask_tag, tiles):
    if not all(np.isfinite(value) and 0 < value <= 32 for value in tiles):
        raise ValueError('Unsupported decal tile scale')
    for tag in (base_tag, mask_tag):
        root = source.c.tags[tag]['offset']
        if len(source.info(tag)) != 1 or source.c.u(root + 0x54):
            raise ValueError('Decal mask baking does not support sprite/multi-image bitmaps')
    base, mask = decode(source, base_tag), decode(source, mask_tag)
    h, w = min(512, max(base.shape[0], mask.shape[0])), min(512, max(base.shape[1], mask.shape[1]))
    u, v = (np.arange(w) + .5) / w, (np.arange(h) + .5) / h
    bx = ((u * tiles[0] % 1) * base.shape[1]).astype(int)
    by = ((v * tiles[1] % 1) * base.shape[0]).astype(int)
    mx, my = (u * mask.shape[1]).astype(int), (v * mask.shape[0]).astype(int)
    rgba = base[by[:, None], bx].copy()
    rgba[:, :, 3] = mask[my[:, None], mx, 3]
    payload = rgba[:, :, [2, 1, 0, 3]].tobytes()

    class BakedSource:
        c = source.c

        def info(self, tag):
            return [{'width': w, 'height': h, 'format': 11, 'mips': 1}]

        def pixels(self, tag, index=0):
            return payload

    return encode_bitmap_base(BakedSource(), base_tag)
