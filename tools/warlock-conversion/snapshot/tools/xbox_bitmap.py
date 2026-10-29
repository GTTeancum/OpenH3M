"""Encode a base mip as Xbox 360 tiled ARGB, V8U8 or BC1/BC2/BC3/BC5.
Address bit layout: xenia-project/xenia src/xenia/gpu/texture_address.h (BSD).
Only base-mip output is supported; callers must set mip count to one.
"""
import numpy as np

def addresses(width_blocks,height_blocks,bytes_per_block):
 assert bytes_per_block in (2,4,8,16)
 y,x=np.indices((height_blocks,width_blocks),dtype=np.uint32)
 pitch=(width_blocks+31)&~31
 outer=((y>>5)*(pitch>>5)+(x>>5))<<6
 inner=((y&14)<<2)+(x&7)
 v=(outer+inner)*(bytes_per_block)
 bank=(y>>4)&1;pipe=((x>>3)&3)^((y>>2)&2)
 return ((v&~255)<<4)|((v&224)<<3)|(bank<<11)|(pipe<<6)|((v&16)<<1)|((y&1)<<4)|(v&15)

def tile_base(payload,width,height,fmt):
 if fmt not in (11,14,15,16,22,33):raise ValueError(f'Unsupported block format {fmt}')
 wb=width if fmt in (11,22) else (width+3)//4;hb=height if fmt in (11,22) else (height+3)//4;bpb=4 if fmt==11 else 2 if fmt==22 else (8 if fmt==14 else 16)
 n=wb*hb*bpb
 if len(payload)<n:raise ValueError('Base mip truncated')
 pos=addresses(wb,hb,bpb).reshape(-1)
 assert len(np.unique(pos))==len(pos)
 size=(int(pos.max())+bpb+4095)&~4095
 out=np.zeros(size,dtype=np.uint8)
 # ARGB32 uses 8-in-32; V8U8 and Xenos DXT formats use 8-in-16.
 swap=4 if fmt==11 else 2
 blocks=np.frombuffer(payload[:n],dtype=np.uint8).reshape(-1,bpb).reshape(-1,bpb//swap,swap)[:,:,::-1].reshape(-1,bpb)
 out[pos[:,None]+np.arange(bpb)]=blocks
 return out.tobytes()

def untile_base(payload,width,height,fmt):
 if fmt not in (11,14,15,16,22,33):raise ValueError(f'Unsupported block format {fmt}')
 wb=width if fmt in (11,22) else (width+3)//4;hb=height if fmt in (11,22) else (height+3)//4;bpb=4 if fmt==11 else 2 if fmt==22 else (8 if fmt==14 else 16)
 pos=addresses(wb,hb,bpb).reshape(-1)
 data=np.frombuffer(payload,dtype=np.uint8)[pos[:,None]+np.arange(bpb)]
 swap=4 if fmt==11 else 2
 return data.reshape(-1,bpb//swap,swap)[:,:,::-1].tobytes()
