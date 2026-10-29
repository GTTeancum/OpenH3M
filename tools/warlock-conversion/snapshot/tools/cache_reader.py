"""Read-only mapped Halo 3 retail/MCC cache access; no extracted asset copies."""
import mmap,struct
from pathlib import Path
class Cache:
 def __init__(self,path,mcc=False):
  self.file=Path(path).open('rb');self.data=mmap.mmap(self.file.fileno(),0,access=mmap.ACCESS_READ);self.mcc=mcc;self.endian='<' if mcc else '>'
  if mcc:
   self.base,idx=self.unpack('QQ',0x2e0);self.start=self.u(0x10);ng,ga,nt,ta=self.unpack('QQQQ',self.offset(idx))
   self.names_base,self.names_size,self.names_index=self.unpack('III',0x24)
  else:
   self.base=self.u(0x2e8);self.start=(self.u(0x48c)+self.u(0x474))&0xffffffff;ng,ga,nt,ta=self.unpack('IIII',self.offset(self.u(0x10)))
   self.names_base=(self.u(0x2b8)+self.u(0x46c))&0xffffffff
   self.names_size=self.u(0x2bc);self.names_index=(self.u(0x2c0)+self.u(0x46c))&0xffffffff
  self.groups=[]
  for i in range(ng):
   raw=self.data[self.offset(ga)+i*16:self.offset(ga)+i*16+4];self.groups.append((raw[::-1] if mcc else raw).decode('ascii'))
  self.tags={}
  for i in range(nt):
   g,s,p=self.unpack('HHI',self.offset(ta)+i*8)
   if g!=65535 and p not in (0,0xffffffff):self.tags[i]={'group':self.groups[g],'salt':s,'offset':self.pointer(p)}
 def unpack(self,fmt,off):return struct.unpack_from(self.endian+fmt,self.data,off)
 def u(self,off):return self.unpack('I',off)[0]
 def offset(self,address):
  off=address-self.base+self.start
  if not 0<=off<len(self.data):raise ValueError(f'Address outside cache: {address:#x}')
  return off
 def pointer(self,p):return self.offset(p*4 if self.mcc else p)
 def block(self,off,stride):
  n,p=self.unpack('II',off)
  if not n:return []
  at=self.pointer(p);assert at+n*stride<=len(self.data)
  return [at+i*stride for i in range(n)]
 def name(self,i):
  if not self.mcc and i>=self.u(0x2b4):return None
  rel=self.u(self.names_index+i*4)
  if rel==0xffffffff:return None
  assert rel<self.names_size
  at=self.names_base+rel;return self.data[at:self.data.find(b'\0',at)].decode('utf-8',errors='replace')
 def close(self):self.data.close();self.file.close()
