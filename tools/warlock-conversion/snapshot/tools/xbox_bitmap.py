"""Encode a base mip as Xbox 360 tiled BC1/BC3/BC5 blocks.
Address bit layout: xenia-project/xenia src/xenia/gpu/texture_address.h (BSD).
Only base-mip output is supported; callers must set mip count to one.
"""
import numpy as np

def addresses(width_blocks,height_blocks,bytes_per_block):
 assert bytes_per_block in (8,16)
 y,x=np.indices((height_blocks,width_blocks),dtype=np.uint32)
 pitch=(width_blocks+31)&~31
 outer=((y>>5)*(pitch>>5)+(x>>5))<<6
 inner=((y&14)<<2)+(x&7)
 v=(outer+inner)*(bytes_per_block)
 bank=(y>>4)&1;pipe=((x>>3)&3)^((y>>2)&2)
 return ((v&~255)<<4)|((v&224)<<3)|(bank<<11)|(pipe<<6)|((v&16)<<1)|((y&1)<<4)|(v&15)

def tile_base(payload,width,height,fmt):
 if fmt not in (14,16,33):raise ValueError(f'Unsupported block format {fmt}')
 wb=(width+3)//4;hb=(height+3)//4;bpb=8 if fmt==14 else 16
 n=wb*hb*bpb
 if len(payload)<n:raise ValueError('Base mip truncated')
 pos=addresses(wb,hb,bpb).reshape(-1)
 assert len(np.unique(pos))==len(pos)
 size=(int(pos.max())+bpb+4095)&~4095
 out=np.zeros(size,dtype=np.uint8)
 # Xenos DXT formats use 8-in-16 endian swapping.
 blocks=np.frombuffer(payload[:n],dtype=np.uint8).reshape(-1,bpb).reshape(-1,bpb//2,2)[:,:,::-1].reshape(-1,bpb)
 out[pos[:,None]+np.arange(bpb)]=blocks
 return out.tobytes()

def untile_base(payload,width,height,fmt):
 wb=(width+3)//4;hb=(height+3)//4;bpb=8 if fmt==14 else 16
 pos=addresses(wb,hb,bpb).reshape(-1)
 data=np.frombuffer(payload,dtype=np.uint8)[pos[:,None]+np.arange(bpb)]
 return data.reshape(-1,bpb//2,2)[:,:,::-1].tobytes()
