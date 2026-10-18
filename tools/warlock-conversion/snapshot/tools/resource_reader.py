"""Read resident resource controls and local compressed pages without asset copies."""
import struct,zlib,xml.etree.ElementTree as E
from pathlib import Path
class Resource:
 def __init__(self,c,datum):
  self.c=c;z=next(t['offset'] for t in c.tags.values() if t['group']=='zone');r=c.block(z+(100 if c.mcc else 88),64)[datum&65535]
  schema=E.parse(Path(__file__).resolve().parents[1]/'reference'/('mcc' if c.mcc else 'plugins')/'zone.xml').getroot();co=int(next(x for x in schema if x.attrib.get('name')=='Native Resource Control Data').attrib['offset'],0);cp=c.pointer(c.u(z+co+12));off,n=c.unpack('II',r+20)
  self.data=c.data[cp+off:cp+off+n];self.root=c.u(r+36)&0x1fffffff;self.fix={c.u(x):c.u(x+4) for x in c.block(r+40,8)}
  if c.mcc:table=z;lo=88;po=52
  else:table=next(t['offset'] for t in c.tags.values() if t['group']=='play');lo=48;po=24
  li=c.unpack('h',r+34)[0];self.raw=[]
  if li<0:return
  l=c.block(table+lo,16)[li];pages=c.block(table+po,88);indices=c.unpack('hh',l);offsets=c.unpack('II',l+4)
  for index,offset in zip(indices,offsets):
   if index<0:self.raw.append(b'');continue
   p=pages[index];shared=c.unpack('h',p+4)[0];assert shared==-1
   block,compressed,size,crc=c.unpack('IIII',p+8);base=0 if c.mcc else (c.u(0x484)+c.u(0x470))&0xffffffff;raw=c.data[base+block:base+block+compressed]
   if c.data[p+3]==0:raw=zlib.decompress(raw,-15)
   else:assert c.data[p+3]==255
   assert len(raw)==size, (index,len(raw),size)
   if crc:assert zlib.crc32(raw)^0xffffffff==crc,(index,hex(zlib.crc32(raw)^0xffffffff),hex(crc))
   self.raw.append(raw[offset:])
 def unpack(self,fmt,at):return struct.unpack_from(self.c.endian+fmt,self.data,at)
 def ptr(self,at):return self.fix[at]&0x1fffffff
 def buffers(self,which):
  at=self.root+(24 if which=='vertex' else 36);n=self.unpack('I',at)[0];table=self.ptr(at+4)
  return [self.ptr(table+i*12) for i in range(n)]
