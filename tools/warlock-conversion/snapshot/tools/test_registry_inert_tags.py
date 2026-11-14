import struct,unittest
from types import SimpleNamespace as NS
from cache_registry import CacheRegistry
class Builder:
 def __init__(self):self.blocks={};self.writes={};self.next=10000
 def alloc(self,data):
  at=self.next;self.next+=len(data)+16;self.blocks[at]=bytes(data);return at
 def put(self,address,fmt,*values):self.writes[address]=(fmt,values)
class Tests(unittest.TestCase):
 def fixture(self):
  r=CacheRegistry.__new__(CacheRegistry);r.builder=Builder()
  r.cache=NS(groups=['scen','bitm'],tags={0:dict(group='scnr',offset=100)},block=lambda a,s:[1000],u=lambda a:0)
  r.tags=bytearray(b''.join((struct.pack('>HHI',0,0x9000,100),struct.pack('>HHI',65535,65535,0),struct.pack('>HHI',0,0x9000,200),struct.pack('>HHI',1,0x9000,300))))
  r.first_tag=1;r.first_resource=0;r.address=lambda x:x
  return r
 def test_inert_not_simulated_live_unchanged(self):
  r=self.fixture();r.table=lambda a,s:b''
  r.stage_simulation_definitions()
  self.assertEqual(r.simulation_added,[0x90000002])
  self.assertEqual(list(r.builder.blocks.values()),[struct.pack('>I',0x90000002)])
 def test_inert_not_resident_original_and_live_preserved(self):
  r=self.fixture();r.table=lambda a,s:bytearray(struct.pack('>I',3))
  r.stage_simulation_definitions=lambda:None;r.closed=False
  r.manifest_field=0;r.zone=10;r.play=20;r.control_field=30;r.index=40;r.added_bytes=0
  for field in ('resources','pages','streaming','locations','control'):setattr(r,field,bytearray())
  r.finalize()
  for field in (0x54,0x60):
   _,values=r.builder.writes[1000+field];data=r.builder.blocks[values[1]]
   self.assertEqual(struct.unpack('>I',data)[0],13) # basis0 + live2/3, inert1clear
if __name__=='__main__':unittest.main()
