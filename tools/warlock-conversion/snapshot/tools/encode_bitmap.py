import struct
import numpy as np
from xbox_bitmap import tile_base

SUPPORTED_FORMATS=(0,1,10,11,14,15,16,33)

def encode_lightmap_array(source, tag):
 """Encode single-mip BC3 lightmap arrays at authored resolution."""
 infos=source.info(tag)
 if len(infos)!=1:raise ValueError('Expected one lightmap array bitmap')
 info=infos[0];c=source.c;row=c.block(c.tags[tag]['offset']+0x60,0x38)[0]
 depth=c.data[row+8];kind=c.unpack('H',row+10)[0]
 w,h,fmt=info['width'],info['height'],info['format']
 if kind!=3 or fmt!=16 or info['mips']!=1 or not depth or not w or not h:
  raise ValueError('Lightmap array requires single-mip BC3 array data')
 pixels=source.pixels(tag);slice_size=mip_size(w,h,fmt)
 if len(pixels)!=slice_size*depth:raise ValueError('Lightmap array payload size mismatch')
 tiled=b''.join(tile_base(pixels[i*slice_size:(i+1)*slice_size],w,h,fmt) for i in range(depth))
 record=bytearray(48);record[:4]=b'bitm'
 struct.pack_into('>HHBBHHH',record,4,w,h,depth,0x0e,3,fmt,3)
 record[0x15]=c.data[row+0x15]
 struct.pack_into('>I',record,0x1c,len(tiled));struct.pack_into('>I',record,0x28,0xffffffff)
 control=bytearray(64);struct.pack_into('>I',control,0,len(tiled))
 struct.pack_into('>HHBBBBI',control,0x28,w,h,depth,1,3,0,0x1a200154)
 return bytes(record),bytes(control),tiled

def mip_size(width,height,fmt):
 if fmt in (0,1):return width*height
 if fmt in (10,11):return width*height*4
 if fmt in (14,15,16,33):return ((width+3)//4)*((height+3)//4)*(8 if fmt==14 else 16)
 raise ValueError(f'Unsupported format {fmt}')

def expand_argb(payload,width,height,fmt):
 """Expand A8/Y8/XRGB into little-endian ARGB32 without quantization."""
 size=mip_size(width,height,fmt)
 if len(payload)<size:raise ValueError('Base mip truncated')
 if fmt==11:return payload[:size]
 out=np.full((width*height,4),255,dtype=np.uint8)
 src=np.frombuffer(payload[:size],dtype=np.uint8)
 if fmt==0:out[:,3]=src
 elif fmt==1:out[:,:3]=src[:,None]
 elif fmt==10:out[:,:3]=src.reshape(-1,4)[:,:3]
 else:raise ValueError(f'Cannot expand format {fmt}')
 return out.tobytes()

def encode_bitmap_base(source,tag,index=0,max_dimension=512):
 """Return retail bitmap record, resource control bytes and tiled base mip.
 Mip levels are intentionally limited to one in both metadata records.
 """
 info=source.info(tag)[index];fmt=info['format'];w=info['width'];h=info['height']
 if fmt not in SUPPORTED_FORMATS:raise ValueError(f'Format {fmt} needs a dedicated encoder')
 row=source.c.block(source.c.tags[tag]['offset']+0x60,0x38)[index]
 if source.c.unpack('H',row+10)[0]!=0:raise ValueError('Only 2D bitmap conversion is supported')
 if max_dimension<1:raise ValueError('max_dimension must be positive')
 pixels=source.pixels(tag,index)
 level=0
 while max(w,h)>max_dimension:
  level+=1
  if level>=info['mips']:raise ValueError('Source has no mip at the requested size')
  pixels=pixels[mip_size(w,h,fmt):];w=max(1,w//2);h=max(1,h//2)
 if fmt in (0,1,10,11):pixels=expand_argb(pixels,w,h,fmt);fmt=11
 tiled=tile_base(pixels,w,h,fmt)
 bitmap=bytearray(48);bitmap[:4]=b'bitm'
 struct.pack_into('>HHBBHHH',bitmap,4,w,h,1,0x0e,0,fmt,3)
 bitmap[0x15]=source.c.data[source.c.block(source.c.tags[tag]['offset']+0x60,0x38)[index]+0x15]
 struct.pack_into('>I',bitmap,0x1c,len(tiled));struct.pack_into('>I',bitmap,0x28,0xffffffff)
 control=bytearray(64);struct.pack_into('>I',control,0,len(tiled))
 gpu_format=0x18280186 if fmt==11 else 0x1a200100+{14:0x52,15:0x53,16:0x54,33:0x71}[fmt]
 struct.pack_into('>HHBBBBI',control,0x28,w,h,1,1,0,1,gpu_format)
 # Resource fixups use control+0x0C -> raw+0 and control+0x34 -> control+0.
 return bytes(bitmap),bytes(control),tiled
