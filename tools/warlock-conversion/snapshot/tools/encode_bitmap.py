import struct
import numpy as np
from xbox_bitmap import tile_base

SUPPORTED_FORMATS=(0,1,10,11,14,15,16,22,33)

def texture_gpu_format(fmt,curve):
 """Preserve color sampling: MCC sRGB uses the retail gamma fetch format.

 Retail Cold Storage uses AS16 formats plus RGB gamma signs for color,
 but plain formats for linear data. Gamma2 is shader-managed in retail.
 Normal maps must retain their signed/linear fetch interpretation.
 """
 linear=0x18280186 if fmt==11 else 0x2d20ab4a if fmt==22 else 0x1a215571 if fmt==33 else 0x1a200100+{14:0x52,15:0x53,16:0x54}[fmt]
 if curve in (1,5) and fmt in (11,14,15,16):
  return (linear & ~0x3f) | {11:50,14:51,15:52,16:53}[fmt] | 0x7e00
 return linear

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
 if fmt==22:return width*height*2
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

def clear_bc3_blue(payload):
 """Zero an unused blend channel without changing BC3 red, green or alpha."""
 if len(payload)%16:raise ValueError('BC3 payload is not whole blocks')
 blocks=np.frombuffer(payload,dtype='<u2').reshape(-1,8).copy()
 # BC3 color endpoints are RGB565 at bytes 8/10. Its color block always
 # uses four-color interpolation, including when endpoints become equal.
 blocks[:,4:6]&=np.uint16(0xffe0)
 return blocks.tobytes()


def mcc_dxn_to_retail(payload):
 """Translate signed MCC BC5 endpoints into retail biased-unsigned DXN.

 TagTool BitmapConverterGen3.ConvertDXGIFormats adds 128 and swaps XY for
 MCC -> PC ATI2; its original-Xbox -> ATI2 path only swaps XY. Thus this
 direct MCC -> Xbox path biases endpoints without swapping the two blocks.
 Selector bits stay unchanged. Native DXN uses GPUSIGN_BIAS on all channels.
 """
 if len(payload)%16:raise ValueError('DXN payload is not whole blocks')
 blocks=np.frombuffer(payload,dtype=np.uint8).reshape(-1,16).copy()
 endpoints=(0,1,8,9)
 blocks[:,endpoints]^=np.uint8(128)
 return blocks.tobytes()


def encode_bitmap_base(source,tag,index=0,max_dimension=512,resize_blend=False,zero_blue=False,preserve_normal_mips=False,preserve_bc_mips=False,opaque_alpha=False):
 """Return retail bitmap record, resource control bytes and tiled payload.
 Default is one mip; opted-in BC textures retain their authored mip chain.
 """
 info=source.info(tag)[index];fmt=info['format'];w=info['width'];h=info['height']
 if fmt not in SUPPORTED_FORMATS:raise ValueError(f'Format {fmt} needs a dedicated encoder')
 row=source.c.block(source.c.tags[tag]['offset']+0x60,0x38)[index]
 if source.c.unpack('H',row+10)[0]!=0:raise ValueError('Only 2D bitmap conversion is supported')
 if max_dimension<1:raise ValueError('max_dimension must be positive')
 pixels=source.pixels(tag,index)
 if fmt==33:pixels=mcc_dxn_to_retail(pixels)
 if zero_blue:
  if fmt!=16:raise ValueError('Unused blue blend channel requires BC3 source')
  pixels=clear_bc3_blue(pixels)
 level=0
 while max(w,h)>max_dimension:
  level+=1
  if level>=info['mips']:
   if not resize_blend or fmt!=16:raise ValueError('Source has no mip at the requested size')
   from PIL import Image
   image=Image.frombytes('RGBA',(w,h),pixels[:mip_size(w,h,fmt)],'bcn',3)
   nw,nh=w,h
   while max(nw,nh)>max_dimension:nw=max(1,nw//2);nh=max(1,nh//2)
   # Terrain blend channels are independent linear weights, not sRGB color
   # or opacity. Resize each independently, without premultiplying alpha.
   channels=[ch.resize((nw,nh),Image.Resampling.BOX) for ch in image.split()]
   pixels=Image.merge('RGBA',channels).tobytes('raw','BGRA');w,h,fmt=nw,nh,11
   break
  pixels=pixels[mip_size(w,h,fmt):];w=max(1,w//2);h=max(1,h//2)
 if fmt in (0,1,10,11):pixels=expand_argb(pixels,w,h,fmt);fmt=11
 if opaque_alpha:
  if fmt!=11:raise ValueError('Opaque-alpha material adapter requires uncompressed color')
  pixels=bytearray(pixels)
  pixels[3::4]=bytes([255])*(len(pixels)//4)
 mip_count=1
 if ((preserve_normal_mips and fmt==33) or (preserve_bc_mips and fmt in (14,15,16))) and info['mips']-level>1 and min(w,h)>=32 and not (w&(w-1) or h&(h-1)):
  from xbox_mip_chain import tile_chain
  mip_count=info['mips']-level
  tiled=tile_chain(pixels,w,h,mip_count,fmt)
 else:tiled=tile_base(pixels,w,h,fmt)
 bitmap=bytearray(48);bitmap[:4]=b'bitm'
 struct.pack_into('>HHBBHHH',bitmap,4,w,h,1,0x0e,0,fmt,3)
 bitmap[0x15]=source.c.data[source.c.block(source.c.tags[tag]['offset']+0x60,0x38)[index]+0x15]
 bitmap[0x14]=mip_count-1
 struct.pack_into('>I',bitmap,0x1c,len(tiled));struct.pack_into('>I',bitmap,0x28,0xffffffff)
 control=bytearray(64);struct.pack_into('>I',control,0,len(tiled))
 gpu_format=texture_gpu_format(fmt,bitmap[0x15])
 struct.pack_into('>HHBBBBI',control,0x28,w,h,1,mip_count,0,0 if mip_count>1 else 1,gpu_format)
 # Resource fixups use control+0x0C -> raw+0 and control+0x34 -> control+0.
 return bytes(bitmap),bytes(control),tiled


def encode_cubemap_base(source, tag, index=0, max_dimension=64):
 """Encode six face-major DDS mip chains as a native, single-mip cube."""
 info=source.info(tag)[index];c=source.c
 row=c.block(c.tags[tag]['offset']+0x60,0x38)[index]
 w,h,fmt=info['width'],info['height'],info['format']
 if c.unpack('H',row+10)[0]!=2 or w!=h or fmt not in (11,14,15,16):
  raise ValueError('Cubemap requires square ARGB32/BC1/BC2/BC3 faces')
 levels=[];fw,fh=w,h
 for level in range(info['mips']):
  levels.append((fw,fh,mip_size(fw,fh,fmt)));fw=max(1,fw//2);fh=max(1,fh//2)
 from resource_reader import Resource
 resource=Resource(c,info['resource'])
 if info['high_size'] or resource.unpack('I',0)[0]!=info['size'] or resource.fix.get(12)!=0x40000000:
  raise ValueError('Unsupported cubemap resource segmentation')
 pixels=resource.raw[0][:info['size']];chain=sum(v[2] for v in levels)
 if len(pixels)!=6*chain:raise ValueError('Cubemap face/mip payload size mismatch')
 chosen=next((j for j,v in enumerate(levels) if v[0]<=max_dimension),None)
 if chosen is None:raise ValueError('Cubemap has no mip within the size budget')
 w,h,size=levels[chosen];offset=sum(v[2] for v in levels[:chosen])
 raw=b''.join(tile_base(pixels[f*chain+offset:f*chain+offset+size],w,h,fmt) for f in range(6))
 record=bytearray(48);record[:4]=b'bitm'
 struct.pack_into('>HHBBHHH',record,4,w,h,1,0x1e,2,fmt,3)
 record[21]=c.data[row+21]
 struct.pack_into('>I',record,28,len(raw));struct.pack_into('>I',record,40,0xffffffff)
 control=bytearray(64);struct.pack_into('>I',control,0,len(raw))
 struct.pack_into('>HHBBBBI',control,40,w,h,1,1,2,0,texture_gpu_format(fmt,record[21]))
 return bytes(record),bytes(control),raw
