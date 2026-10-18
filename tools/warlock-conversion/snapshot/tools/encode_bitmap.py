import struct
from xbox_bitmap import tile_base

def encode_bitmap_base(source,tag,index=0,max_dimension=512):
 """Return retail bitmap record, resource control bytes and tiled base mip.
 Mip levels are intentionally limited to one in both metadata records.
 """
 info=source.info(tag)[index];fmt=info['format'];w=info['width'];h=info['height']
 if fmt not in (14,16,33):raise ValueError(f'Format {fmt} needs a dedicated encoder')
 pixels=source.pixels(tag,index)
 while max(w,h)>max_dimension:
  pixels=pixels[((w+3)//4)*((h+3)//4)*(8 if fmt==14 else 16):];w=max(1,w//2);h=max(1,h//2)
 tiled=tile_base(pixels,w,h,fmt)
 bitmap=bytearray(48);bitmap[:4]=b'bitm'
 struct.pack_into('>HHBBHHH',bitmap,4,w,h,1,0x0e,0,fmt,3)
 bitmap[0x15]=source.c.data[source.c.block(source.c.tags[tag]['offset']+0x60,0x38)[index]+0x15]
 struct.pack_into('>I',bitmap,0x1c,len(tiled));struct.pack_into('>I',bitmap,0x28,0xffffffff)
 control=bytearray(64);struct.pack_into('>I',control,0,len(tiled))
 struct.pack_into('>HHBBBBI',control,0x28,w,h,1,1,0,1,0x1a200100+{14:0x52,16:0x54,33:0x71}[fmt])
 # Resource fixups use control+0x0C -> raw+0 and control+0x34 -> control+0.
 return bytes(bitmap),bytes(control),tiled
