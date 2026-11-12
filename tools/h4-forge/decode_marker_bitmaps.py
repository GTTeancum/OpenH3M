"""Decode the original H4 marker base images from checksum-verified Xbox pages."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from xbox_bitmap import addresses
research=ROOT/'work/h4-forge-research/isolated'
effects=json.loads((research/'marker-effect-fields.json').read_text())
resources={r['index']:r for r in json.loads((research/'marker-resource-pages.json').read_text())}
verified={p['page']:p for p in json.loads((research/'marker-pages/extraction.json').read_text())['verified_pages']}
out=research/'marker-bitmaps';out.mkdir(exist_ok=True)

def bc4(blocks):
    # DXT5 alpha-style unsigned endpoints and 48-bit, three-bit selectors.
    a,b=blocks[:,0].astype(np.uint16),blocks[:,1].astype(np.uint16)
    palette=np.empty((len(blocks),8),dtype=np.uint16);palette[:,0]=a;palette[:,1]=b
    for i in range(1,7):
        palette[:,i+1]=np.where(a>b,((7-i)*a+i*b)//7,
            ((5-i)*a+i*b)//5 if i<=4 else (0 if i==5 else 255))
    selectors=np.zeros(len(blocks),dtype=np.uint64)
    for i in range(6):selectors|=blocks[:,2+i].astype(np.uint64)<<(8*i)
    codes=((selectors[:,None]>>(3*np.arange(16,dtype=np.uint64)))&7).astype(np.intp)
    return np.take_along_axis(palette,codes,axis=1).astype(np.uint8)

report=[]
for index,channels in [(7748,2),(16661,1)]:
    info=effects[str(index)]['fields']['Bitmap Data@0x7C'][0]
    width,height=info['Width@0x0'],info['Height@0x2']
    if info['Mipmap Count@0x10'] or info['Format@0x8']['value']!={1:43,2:44}[channels]:raise ValueError('Unexpected glow format')
    part,=resources[index]['parts']
    raw=(research/f"marker-pages/{part['page']}.bin").read_bytes()
    if hashlib.sha256(raw).hexdigest()!=verified[part['page']]['sha256']:raise ValueError('Unverified resource page')
    raw=raw[part['offset']:part['offset']+info['Pixels Count@0x18']]
    wb,hb=width//4,height//4;stride=channels*8
    positions=addresses(wb,hb,stride).reshape(-1)
    if int(positions.max())+stride>len(raw):raise ValueError('Tiled pixels outside image data')
    blocks=np.frombuffer(raw,dtype=np.uint8)[positions[:,None]+np.arange(stride)]
    blocks=blocks.reshape(-1,stride//2,2)[:,:,::-1].reshape(-1,stride)
    planes=[]
    for channel in range(channels):
        pixels=bc4(blocks[:,channel*8:channel*8+8]).reshape(hb,wb,4,4).transpose(0,2,1,3).reshape(height,width)
        planes.append(pixels)
        Image.fromarray(pixels).save(out/f'{index}-channel-{channel}.png')
    rgba=np.stack([planes[0]]*3+[planes[1] if channels==2 else np.full_like(planes[0],255)],axis=2)
    (out/f'{index}.rgba').write_bytes(rgba.tobytes())
    report.append(dict(index=index,width=width,height=height,format=info['Format@0x8']['label'],
        source_sha256=hashlib.sha256(raw).hexdigest(),rgba_sha256=hashlib.sha256(rgba.tobytes()).hexdigest()))

for index in [16659,419,341]:
    info=effects[str(index)]['fields']['Bitmap Data@0x7C'][0]
    width,height=info['Width@0x0'],info['Height@0x2']
    # The two plasma resources place their full-resolution 128x128 mip in the
    # optional page; their required-page range starts with the smaller mips.
    part=next(p for p in resources[index]['parts'] if p['part']==(0 if index==16659 else 1))
    page=(research/f"marker-pages/{part['page']}.bin").read_bytes()
    if hashlib.sha256(page).hexdigest()!=verified[part['page']]['sha256']:
        raise ValueError('Unverified resource page')
    if index==16659:
        assert (width,height,info['Format@0x8']['value'])==(256,1,14)
        assert not info['Format Flags@0x5']&8  # Original gradient is linear DXT1.
        # With the short dimension <=16, mip 0 is already in the packed tail.
        # ReXGlue GetPackedMipOffset places a wide texture at texel y=16:
        # four BC1 block rows, each 64 blocks * 8 bytes = 512 bytes.
        assert info['Mipmap Count@0x10']==8
        base_offset=4*(width//4*8)
        raw=page[part['offset']+base_offset:part['offset']+base_offset+width//4*8]
        blocks=np.frombuffer(raw,dtype=np.uint8).reshape(-1,4,2)[:,:,::-1].reshape(-1,8)
        words=blocks[:,0:4].copy().view('<u2').reshape(-1,2).astype(np.uint32)
        red=(words>>11)&31;green=(words>>5)&63;blue=words&31
        colors=np.stack([(red<<3)|(red>>2),(green<<2)|(green>>4),(blue<<3)|(blue>>2)],axis=2)
        pal=np.zeros((len(blocks),4,4),dtype=np.uint32)
        pal[:,:2,:3]=colors;pal[:,:3,3]=255
        four=words[:,0]>words[:,1]
        pal[:,2,:3]=np.where(four[:,None],(2*colors[:,0]+colors[:,1])//3,(colors[:,0]+colors[:,1])//2)
        pal[:,3,:3]=np.where(four[:,None],(colors[:,0]+2*colors[:,1])//3,0)
        pal[:,3,3]=np.where(four,255,0)
        codes=blocks[:,4:8].copy().view('<u4').reshape(-1)
        # Only the first texel row belongs to this 256x1 source bitmap.
        selectors=((codes[:,None]>>(2*np.arange(4,dtype=np.uint32)))&3).astype(np.intp)
        rgba=pal[np.arange(len(blocks))[:,None],selectors].astype(np.uint8).reshape(1,width,4)
    else:
        base_offset=0
        assert (width,height,info['Format@0x8']['value'])==(128,128,2)
        assert info['Format Flags@0x5']&8
        raw=page[part['offset']:part['offset']+width*height]
        # ReXGlue texture_util::GetTiledOffset2D with log2(bytes/block)=0.
        y,x=np.indices((height,width),dtype=np.uint32)
        macro=((x>>5)+(y>>5)*(width>>5))<<7
        micro=(x&7)+((y&14)<<2)
        offset=macro+((micro&~np.uint32(15))<<1)+(micro&15)+((y&1)<<4)
        pos=((offset&~np.uint32(511))<<3)+((y&16)<<7)+((offset&448)<<2)+(((((y&8)>>2)+(x>>3))&3)<<6)+(offset&63)
        assert len(raw)==width*height and len(np.unique(pos))==width*height and pos.max()<len(raw)
        pixels=np.frombuffer(raw,dtype=np.uint8)[pos]
        rgba=np.stack([pixels]*4,axis=2)  # AY8 uses one byte for luminance and alpha.
    (out/f'{index}.rgba').write_bytes(rgba.tobytes())
    Image.fromarray(rgba).save(out/f'{index}.png')
    report.append(dict(index=index,width=width,height=height,format=info['Format@0x8']['label'],
        source_page=part['page'],source_offset=part['offset']+base_offset,source_sha256=hashlib.sha256(raw).hexdigest(),
        rgba_sha256=hashlib.sha256(rgba.tobytes()).hexdigest()))
(out/'decoded.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
