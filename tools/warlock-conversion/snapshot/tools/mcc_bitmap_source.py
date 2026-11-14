"""Read MCC bitmap mip payloads in memory for map-side conversion."""
import zlib
class BitmapSource:
 def __init__(self,cache):
  assert cache.mcc
  self.c=cache;z=next(t['offset'] for t in cache.tags.values() if t['group']=='zone')
  self.resources=cache.block(z+0x64,0x40);self.locations=cache.block(z+0x58,16);self.pages=cache.block(z+0x34,0x58)
 def page(self,index):
  if index<0:return b''
  c=self.c;p=self.pages[index];salt,flags,codec,shared,unused,off,compressed,raw,crc=c.unpack('hBBhhIIII',p)
  if shared!=-1:raise ValueError(f'External page {index} requires shared cache {shared}')
  payload=c.data[off:off+compressed]
  if codec==0:payload=zlib.decompress(payload,-15)
  elif codec!=255:raise ValueError(f'Unsupported codec {codec}')
  assert len(payload)==raw
  assert (zlib.crc32(payload)^0xffffffff)==crc, f'Page {index} CRC mismatch'
  return payload
 def info(self,tag):
  c=self.c;t=c.tags[tag];assert t['group']=='bitm';a=t['offset'];rows=c.block(a+0x60,0x38);hw=c.block(a+0x8c,8)
  result=[]
  for i,b in enumerate(rows):
   w,h=c.unpack('HH',b+4);fmt=c.unpack('H',b+12)[0];size=c.u(b+0x1c);high=c.u(b+0x24)
   resource=c.u(hw[i]) if i<len(hw) else None
   result.append({'width':w,'height':h,'format':fmt,'mips':c.data[b+0x14]+1,'size':size,'high_size':high,'pixel_offset':c.u(b+0x18),'high_offset':c.u(b+0x20),'resource':resource})
  return result
 def pixels(self,tag,index=0):
  from resource_reader import Resource
  info=self.info(tag)[index];resource=Resource(self.c,info['resource'])
  high=info['high_size'];size=info['size'];low=size-high
  # BitmapData offsets index the editor's aggregate image payload. Runtime
  # resources are per image (for example the three truck-logo images), and
  # their dataref fixups, not cumulative editor offsets, locate the bytes.
  if low<0 or resource.unpack('I',0)[0]!=low or resource.unpack('I',20)[0]!=high:
   raise ValueError('Bitmap image/resource payload lengths disagree')
  def piece(field,length,segment):
   if not length:return b''
   pointer=resource.fix.get(field)
   if pointer is None or pointer>>29!=segment:
    raise ValueError('Bitmap payload has an unsupported resource segment')
   offset=pointer&0x1fffffff;raw=resource.raw[segment-2]
   if offset+length>len(raw):raise ValueError('Bitmap resource payload truncated')
   return bytes(raw[offset:offset+length])
  result=piece(32,high,3)+piece(12,low,2)
  if len(result)!=size:raise ValueError('Bitmap payload size mismatch')
  return result
