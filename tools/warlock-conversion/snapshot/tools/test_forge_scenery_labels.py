"""Authored Forge text is distinct from string IDs; no guessed display labels."""
import struct,unittest
from types import SimpleNamespace
from unittest.mock import patch
from forge_scenery_labels import source_label_text,plan_labels,stage_labels,stage_label_text,resolve_derived_labels

class LabelsTests(unittest.TestCase):
 def source(self,entries):
  data=bytearray(1024);text=bytearray();refs=128;start=512
  for j,(sid,value) in enumerate(entries):
   struct.pack_into('<II',data,refs+j*8,sid,len(text));text.extend(value)
  data[start:start+len(text)]=text;struct.pack_into('<4I',data,24,len(entries),len(text),refs,start)
  return SimpleNamespace(tags={0:dict(group='matg',offset=0)},data=data,unpack=lambda f,o:struct.unpack_from('<'+f,data,o))
 def test_real_source_text_bounds_empty_ambiguity(self):
  self.assertEqual(source_label_text(self.source([(1,b'Actual Name\0'),(2,b'\0')]),{1,2}),{1:b'Actual Name\0'})
  with self.assertRaisesRegex(ValueError,'Ambiguous'):source_label_text(self.source([(1,b'A\0'),(1,b'B\0')]),{1})
  source=self.source([(1,b'abc')])
  with self.assertRaisesRegex(ValueError,'Unterminated'):source_label_text(source,{1})
 def test_stock_precedence_and_unresolved_not_titlecased(self):
  source=self.source([(1,b'Source Changed\0'),(2,b'Authored Name\0')])
  with patch('forge_scenery_labels.native_label_text',return_value={10:b'Stock Name\0'}):
   resolved,missing=plan_labels(source,SimpleNamespace(cache=None),{1:10,2:20,3:30})
  self.assertEqual(resolved,{20:b'Authored Name\0'});self.assertEqual(missing,[3])
 def test_conflicting_translated_ids_rejected(self):
  with patch('forge_scenery_labels.native_label_text',return_value={}):
   with self.assertRaisesRegex(ValueError,'collide'):
    plan_labels(self.source([(1,b'A\0'),(2,b'B\0')]),SimpleNamespace(cache=None),{1:10,2:10})
 def test_actual_resuscitation_staged_locale_when_available(self):
  from pathlib import Path
  import json,hashlib
  from cache_reader import Cache
  from map_builder import MapBuilder
  from cache_registry import CacheRegistry
  from string_ids import StringTable
  root=Path(__file__).resolve().parents[4]
  evidence=root/'work/mcc-ten-conversion/resuscitation-selected-forge-palette.json'
  original=root/'.local/mcc-five-conversion/resuscitation.map'
  sourcepath=root.parent/'references/halo3/mcc-second-two/extracted/resuscitation.map'
  if not all(p.exists() for p in (evidence,original,sourcepath)):self.skipTest('Actual inputs not installed')
  source=Cache(sourcepath,True);builder=MapBuilder(original,0x10000)
  try:
   registry=CacheRegistry(builder,bytes(34));strings=StringTable(source)
   rows=json.loads(evidence.read_text())['missing_english_display_rows']
   labels={strings.id_for_text(row['display_key']):row['target_string_id'] for row in rows}
   # The audit stores display IDs as hex for readable evidence.
   labels={k:int(v,16) if isinstance(v,str) else v for k,v in labels.items()}
   resolved,missing=plan_labels(source,registry,labels)
   self.assertEqual(len(resolved),84)
   self.assertEqual({strings.text(k) for k in missing},{'spectre','sniper_rifle_ammo','map_credits'})
   with patch('forge_scenery_labels.resolve_derived_labels',return_value=({},[])):
    with self.assertRaisesRegex(ValueError,'Missing authored English Forge names'):stage_labels(source,registry,labels)
   self.assertFalse(builder.locale,'Unresolved publication must fail atomically')
   derived,provenance=resolve_derived_labels(source,labels,missing)
   self.assertEqual(set(derived.values()),{b'Spectre\0',b'Sniper Rifle Ammo\0',b'Map Credits\0'})
   self.assertEqual(len(provenance),3)
   with patch('forge_scenery_labels.RESUSCITATION_SOURCE_SHA256','wrong'):
    with self.assertRaisesRegex(ValueError,'source changed'):resolve_derived_labels(source,labels,missing)
   self.assertEqual(stage_labels(source,registry,labels),87)
   self.assertEqual(registry.forge_label_publication['authored_labels_added'],84)
   self.assertEqual(registry.forge_label_publication['derived_labels_added'],3)
   resolved.update(derived)
   c=builder.cache;matg=next(t['offset'] for t in c.tags.values() if t['group']=='matg');unic=next(t['offset'] for k,t in c.tags.items() if t['group']=='unic' and c.name(k)==r'ui\halox\sandbox_ui\strings')
   count,size,refs,data=struct.unpack('>4I',builder.read(registry.address(matg+0x1c4),16))
   start=c.u(0x494)+c.u(0x498);refs-=start;data-=start
   first,length=struct.unpack('>HH',builder.read(registry.address(unic+32),4))
   table={}
   for n in range(first,first+length):
    sid,off=struct.unpack_from('>II',builder.locale,refs+n*8);end=builder.locale.find(b'\0',data+off,data+size)
    self.assertGreaterEqual(end,data+off);table[sid]=bytes(builder.locale[data+off:end+1])
   for sid,text in resolved.items():self.assertEqual(table[sid],text)
   # Every originally missing row now resolves, including repeated ammo IDs.
   for row in rows:
    sid=row['target_string_id'];sid=int(sid,16) if isinstance(sid,str) else sid
    self.assertTrue(table[sid][:-1])
   # The retained native scenario has all 180 actual Forge rows. Validate
   # display IDs directly from those rows, not a synthetic inventory.
   from source_schema import load_schema
   from assemble_scenario import field
   schema=load_schema(c,'scnr');scnr=next(t['offset'] for t in c.tags.values() if t['group']=='scnr');total=0
   for category in ('Vehicle','Weapon','Equipment','Scenery','Teleporter','Goal','Spawner'):
    f=field(schema,'Map Variant '+category+' Palette')
    for row in c.block(scnr+int(f.get('offset'),0),int(f.get('elementSize'),0)):
     self.assertTrue(table[c.u(row+16)][:-1]);total+=1
   self.assertEqual(total,180)
   for off,payload in ((0x1d4,builder.locale[refs:refs+count*8]),(0x1e8,builder.locale[data:data+size])):
    self.assertEqual(builder.read(registry.address(matg+off),20),hashlib.sha1(payload).digest())
  finally:source.close();builder.close()

if __name__=='__main__':unittest.main()
