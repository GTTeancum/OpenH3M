import struct,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unused_shader_bitmaps import prune_unused_shader_bitmaps
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent);self.addCleanup(self.tmp.cleanup)
  self.ref=Path(self.tmp.name);(self.ref/'plugins').mkdir()
  (self.ref/'plugins/bitm.xml').write_text('<plugin/>')
  (self.ref/'plugins/rmsh.xml').write_text('<plugin><tagref name="texture" offset="0"/></plugin>')
 def fixture(self):
  meta=bytearray(256);struct.pack_into('>I',meta,108,0xffffffff)
  tags=bytearray().join(struct.pack('>HHI',g,0x9000,0x1000+n*32) for n,g in enumerate((0,0,0,1)))
  resource=bytearray(64);struct.pack_into('>I',resource,12,0x90000001)
  page=bytearray(88);struct.pack_into('>h',page,4,-1);struct.pack_into('>III',page,8,0,100,200)
  locations=bytearray(16);struct.pack_into('>hh',locations,0,0,-1)
  r=NS(cache=NS(groups=['bitm','rmsh']),tags=tags,resources=resource,locations=locations,pages=page,first_tag=1,first_resource=0)
  added=[dict(group='bitm',datum=hex(0x90000000+n),native_shader_donor=True,native_shader_donor_file='donor.map',source='texture'+str(n)) for n in (0,1)]
  added.append(dict(group='bitm',datum='0x90000002',source='authored'))
  return NS(registry=r,builder=NS(base=0x1000,meta=meta),reference=self.ref,added=added)
 def test_unreferenced_new_donor_only(self):
  i=self.fixture();out=prune_unused_shader_bitmaps(i)
  self.assertEqual(out['retired_tags'],1);self.assertEqual(i.registry.retired_tags,{1})
  self.assertEqual(len(i.added),2);self.assertTrue(out['retired'][0]['provenance']['native_shader_donor'])
  self.assertEqual(struct.unpack_from('>h',i.registry.resources,34)[0],-1)
  for pos in (0,16):self.assertEqual(struct.unpack_from('>H',i.registry.tags,pos)[0],0)
  self.assertEqual(struct.unpack_from('>h',i.registry.locations,0)[0],0)
 def test_semantic_reference_retained(self):
  i=self.fixture();struct.pack_into('>I',i.builder.meta,108,0x90000001)
  out=prune_unused_shader_bitmaps(i);self.assertEqual(out['retired_tags'],0)
  self.assertEqual(out['retained_candidates'][0]['semantic_incoming'],1)
 def test_opaque_unaligned_reference_retained(self):
  i=self.fixture();i.builder.meta[193:197]=struct.pack('>I',0x90000001)
  self.assertEqual(prune_unused_shader_bitmaps(i)['retired_tags'],0)
 def test_prior_retirements_preserved(self):
  i=self.fixture();i.registry.retired_tags={99};i.registry.retired_resources={77}
  prune_unused_shader_bitmaps(i)
  self.assertEqual(i.registry.retired_tags,{1,99});self.assertEqual(i.registry.retired_resources,{0,77})
 def test_exact_ledger_not_compressed_or_page_estimate(self):
  i=self.fixture();i.registry.added_bytes=999;i.registry.added_resource_bytes={0:237,9:762}
  report=prune_unused_shader_bitmaps(i)
  self.assertEqual(report['retired_added_raw_bytes'],237)
  self.assertEqual((report['added_bytes_before'],report['added_bytes_after']),(999,762))
  self.assertEqual(i.registry.added_bytes,762);self.assertEqual(i.registry.added_resource_bytes,{9:762})
 def test_untracked_resource_has_no_guessed_decrement(self):
  i=self.fixture();i.registry.added_bytes=999;i.registry.added_resource_bytes={9:999}
  self.assertEqual(prune_unused_shader_bitmaps(i)['retired_added_raw_bytes'],0)
  self.assertEqual(i.registry.added_bytes,999)
 def ledger_fixture(self):
  i=self.fixture();i.builder.used=160;i.builder.reserve=192
  i.builder.allocations=[(0x1000+n*32,32) for n in range(5)]
  struct.pack_into('>I',i.builder.meta,140,0x90000001)
  return i
 def test_orphan_only_handle_can_retire(self):
  i=self.ledger_fixture();out=prune_unused_shader_bitmaps(i)
  self.assertEqual(out['retired_tags'],1)
  self.assertFalse(out['retired'][0]['unreachable_handle_allocations'][0]['live_or_unmapped'])
 def test_live_root_interior_pointer_retains(self):
  i=self.ledger_fixture();struct.pack_into('>I',i.builder.meta,97,0x1084)
  self.assertEqual(prune_unused_shader_bitmaps(i)['retired_tags'],0)
 def test_original_opaque_pointer_retains(self):
  i=self.ledger_fixture();struct.pack_into('>I',i.builder.meta,201,0x1081)
  self.assertEqual(prune_unused_shader_bitmaps(i)['retired_tags'],0)
 def test_unmapped_handle_retains_despite_orphan_match(self):
  i=self.ledger_fixture();struct.pack_into('>I',i.builder.meta,171,0x90000001)
  self.assertEqual(prune_unused_shader_bitmaps(i)['retired_tags'],0)
 def test_orphan_handle_crossing_boundary_retains(self):
  i=self.ledger_fixture();struct.pack_into('>I',i.builder.meta,158,0x90000001)
  self.assertEqual(prune_unused_shader_bitmaps(i)['retired_tags'],0)
 def test_bad_layout_fails_before_mutation(self):
  i=self.fixture();(self.ref/'plugins/rmsh.xml').write_text('<plugin><tagblock offset="0" elementSize="16"><tagref offset="0"/></tagblock></plugin>')
  struct.pack_into('>II',i.builder.meta,96,1,0x12345678);before=bytes(i.registry.tags)
  with self.assertRaises(ValueError):prune_unused_shader_bitmaps(i)
  self.assertEqual(bytes(i.registry.tags),before)
if __name__=='__main__':unittest.main()
