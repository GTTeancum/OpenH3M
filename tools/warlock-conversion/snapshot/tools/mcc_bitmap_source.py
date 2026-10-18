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
  c=self.c;info=self.info(tag)[index];r=self.resources[info['resource']&65535];loc=c.unpack('h',r+0x22)[0];required,optional,roff,ooff,_,_=c.unpack('hhIIhh',self.locations[loc])
  # Optional data is the highest mip; required data holds the remaining chain.
  high=info['high_size'];size=info['size'];low=size-high
  req=self.page(required) if low else b'';opt=self.page(optional) if high else b''
  assert roff+info['pixel_offset']+low<=len(req)
  assert ooff+info['high_offset']+high<=len(opt)
  result=opt[ooff+info['high_offset']:ooff+info['high_offset']+high]+req[roff+info['pixel_offset']:roff+info['pixel_offset']+low]
  assert len(result)==size
  return result
