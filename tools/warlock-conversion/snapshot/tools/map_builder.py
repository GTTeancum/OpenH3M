"""Map-side staging allocator. Virtual addresses are preserved for existing tags.
No filesystem writes until save(); original cache is opened read-only.
"""
import struct,hashlib
import numpy as np
from cache_reader import Cache
class MapBuilder:
 def __init__(self,path,reserve=0x200000):
  self.cache=Cache(path);self.original=self.cache.data[:];self.reserve=reserve
  assert reserve%0x10000==0
  self.base=self.cache.base-reserve;self.meta=bytearray(reserve)+bytearray(self.original[self.cache.start:self.cache.start+self.cache.u(0x490)])
  self.used=0;self.raw=bytearray();self.debug=bytearray();self.header_updates={}
 def append_debug(self,payload,align=4):
  self.debug.extend(bytes((-len(self.debug))%align));at=len(self.debug);self.debug.extend(payload)
  return (self.cache.u(0x47c)+self.cache.u(0x480)+at)&0xffffffff
 def alloc(self,payload,align=16):
  at=(self.used+align-1)&~(align-1)
  if at+len(payload)>self.reserve:raise ValueError('Metadata reserve exhausted')
  self.meta[at:at+len(payload)]=payload;self.used=at+len(payload);return self.base+at
 def put(self,address,fmt,*values):struct.pack_into('>'+fmt,self.meta,address-self.base,*values)
 def read(self,address,size):return bytes(self.meta[address-self.base:address-self.base+size])
 def append_raw(self,payload):
  pad=(-len(self.raw))%0x1000;self.raw.extend(bytes(pad));off=self.cache.u(0x488)+len(self.raw);self.raw.extend(payload);return off
 def finish(self,salt):
  self.raw.extend(bytes((-len(self.raw))%0x1000));growth=len(self.raw);c=self.cache;h=bytearray(self.original[:c.start]);tail=self.original[c.start+c.u(0x490):]
  self.debug.extend(bytes((-len(self.debug))%0x1000));debug_growth=len(self.debug)
  debug_end=((c.u(0x47c)+c.u(0x46c))&0xffffffff)+c.u(0x480)
  if debug_growth:
   if debug_end>((c.u(0x484)+c.u(0x470))&0xffffffff) or debug_end>c.start:raise ValueError('Unsupported overlapping debug section')
   h[debug_end:debug_end]=self.debug
  out=h+self.raw+self.meta+tail
  def put(o,v):struct.pack_into('>I',out,o,v)
  put(8,len(out));put(0x18,c.u(0x18)+self.reserve);put(0x2e8,self.base);put(0x2f0,self.base);put(0x2f4,c.u(0x2f4)+self.reserve)
  put(0x480,c.u(0x480)+debug_growth);put(0x470,c.u(0x470)+debug_growth)
  # Section address adjustments are signed 32-bit displacements serialized
  # as words. Original Lockout starts with a negative tag-section adjustment.
  put(0x488,c.u(0x488)+growth);put(0x474,(c.u(0x474)+growth+debug_growth)&0xffffffff);put(0x490,c.u(0x490)+self.reserve);put(0x478,c.u(0x478)+growth+self.reserve+debug_growth)
  for at,value in self.header_updates.items():put(at,value)
  assert self.base+c.u(0x18)+self.reserve==0xbfc00000
  put(0x2c4,int(np.bitwise_xor.reduce(np.frombuffer(out,dtype='>u4',offset=0x3000))))
  header=bytearray(out[:0x3000])
  for start,size in ((0x320,4),(0x328,8),(0x330,0x13c),(0x1c,0x100),(0x144,8),(0x16c,0x20),(0x49c,0x10)):header[start:start+size]=bytes(size)
  out[0x330:0x344]=hashlib.sha1(salt+header).digest();return out
 def close(self):self.cache.close()
