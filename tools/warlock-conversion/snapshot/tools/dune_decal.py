"""Exact Dune pride decal: native combined shader, all authored BC3 levels retained."""
import hashlib
import numpy as np
from dune_flare import SCENARIO, BUILD
from encode_bitmap import encode_bitmap_base, mip_size

NAME = r'fx\decals\pride_flags\pride_flags'
TEMPLATE = r'shaders\decal_templates\_3_3_0_1_0_0'
NAMES = [r'fx\decals\pride_flags\bitmaps\pride', r'fx\decals\pride_flags\bitmaps\alpha map']
HASHES = ['739b6af97b0b66449715015db9a73c2db14150afe626b8682189068fdd5f467b',
          '38e6fb53f21db89227598dadb93e27e65c703ca4303918cd8d887c4eba69883c']
NOTE = ('Dune pride decal uses the native combined-alpha shader with exact authored 768x384 BC3 base '
        'and all ten authored mip levels. Each level retains source pride RGB and mask alpha losslessly; '
        'no resizing, mip generation or mip omission. Source retained.')


def join_bc3_chains(base, mask, width, height, count):
    """Join independent BC3 RGB/alpha blocks and decode-verify every authored mip."""
    from PIL import Image
    sizes=[mip_size(max(1,width>>n),max(1,height>>n),16) for n in range(count)]
    if not 0<count<=max(width,height).bit_length() or min(width,height)<1:
        raise ValueError('Invalid decal authored mip dimensions/count')
    if len(base)!=sum(sizes) or len(mask)!=sum(sizes):
        raise ValueError('Decal authored mip payload length mismatch')
    joined=[];offset=0
    for n,size in enumerate(sizes):
        w,h=max(1,width>>n),max(1,height>>n)
        rgb,alpha=base[offset:offset+size],mask[offset:offset+size];offset+=size
        level=np.concatenate((np.frombuffer(alpha,np.uint8).reshape(-1,16)[:,:8],
                              np.frombuffer(rgb,np.uint8).reshape(-1,16)[:,8:]),axis=1).tobytes()
        decoded=[np.asarray(Image.frombytes('RGBA',(w,h),p,'bcn',3)) for p in (rgb,alpha,level)]
        if not np.array_equal(decoded[0][:,:,:3],decoded[2][:,:,:3]) or not np.array_equal(decoded[1][:,:,3],decoded[2][:,:,3]):
            raise ValueError(f'Dune decal RGB/alpha changed at mip {n}')
        joined.append(level)
    return b''.join(joined)



def matches(source, post, group, template):
    if group != 'decs' or template != TEMPLATE:
        return False
    if [source.name(k) for k,t in source.tags.items() if t['group']=='scnr'] != [SCENARIO]:
        return False
    for k,t in source.tags.items():
        if t['group']=='decs' and source.name(k)==NAME:
            if any(post in source.block(row+48,140) for row in source.block(t['offset']+20,116)):
                if bytes(source.data[0xa0:0xc0]).split(b'\0',1)[0] != BUILD.encode():
                    raise ValueError('Dune decal build changed')
                return True
    return False


def encode(bitmaps, base_tag, mask_tag):
    source=bitmaps.c
    tags=[base_tag,mask_tag]
    if [source.name(k) for k in tags] != NAMES:
        raise ValueError('Dune decal bitmap binding changed')
    raw=[]
    for tag,digest in zip(tags,HASHES):
        infos=bitmaps.info(tag)
        if len(infos)!=1 or tuple(infos[0][k] for k in ('width','height','format','mips'))!=(768,384,16,10):
            raise ValueError('Dune decal bitmap layout changed')
        pixels=bitmaps.pixels(tag)
        if hashlib.sha256(pixels).hexdigest()!=digest:
            raise ValueError('Dune decal bitmap data changed')
        raw.append(pixels)
    joined=join_bc3_chains(raw[0],raw[1],768,384,10)
    rows=[source.block(source.tags[tag]['offset']+96,56)[0] for tag in tags]
    curves=[source.data[row+21] for row in rows]
    if curves[0] != curves[1]:
        raise ValueError('Dune decal bitmap curves differ')
    class Combined:
        c=source
        def info(self,tag):return [dict(width=768,height=384,format=16,mips=10,kind=0,curve=curves[0])]
        def pixels(self,tag,index=0):return joined
    return encode_bitmap_base(Combined(),base_tag,max_dimension=768,preserve_authored_mips=True)
