"""Private stock-H3 visual fixture: reposition stock placements, no asset edits."""
from pathlib import Path
import sys, os, struct, json, hashlib
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from map_builder import MapBuilder
from build_scenario_checkpoint import resource_salt

source=Path(sys.argv[1]).resolve(strict=True)
target=(ROOT/'work/video-options/remaining'/('shadow-fixture' if '--shadows' in sys.argv else 'water-fixture' if '--water' in sys.argv else 'beach-fixture-objects' if '--objects' in sys.argv else 'beach-fixture')).resolve()
target.relative_to(ROOT)
if target.exists(): raise SystemExit('Fixture already exists; refusing to overwrite')
target.mkdir(parents=True)
for folder in ('maps','bink','waves'):
 for src in (source/folder).rglob('*'):
  if not src.is_file() or src.name=='zanzibar.map':continue
  dest=target/src.relative_to(source)
  dest.parent.mkdir(parents=True,exist_ok=True)
  os.link(src,dest)
for name in ('default.xex','WaveShell-Xbox.dll','WavesLibDLL.dll'):
 if (source/name).exists():os.link(source/name,target/name)
b=MapBuilder(str(source/'maps/zanzibar.map'),reserve=0)
c=b.cache
scnr=next(t['offset'] for t in c.tags.values() if t['group']=='scnr')
schema=ET.parse(ROOT/'tools/warlock-conversion/snapshot/reference/plugins/scnr.xml').getroot()
scenery=next(x for x in schema if x.get('name')=='Scenery')
palette=next(x for x in schema if x.get('name')=='Scenery Palette')
names=[c.name(c.u(at+12)&65535) for at in c.block(scnr+int(palette.get('offset'),0),int(palette.get('elementSize'),0))]
rows=c.block(scnr+int(scenery.get('offset'),0),int(scenery.get('elementSize'),0))
# Original beach respawn 5 is authored on solid sand and overlooks the stock
# Mongoose/Warthog/Ghost placements, with the shoreline to the left.
position=(14.362690925598145,24.83962059020996,-.98987877368927)
yaw=2.7
if '--shadows' in sys.argv:
 yaw=3.35
if '--water' in sys.argv:
 position=(6.3,29.0,-2.14)
 yaw=1.57079632679
changed=[]
for i,at in enumerate(rows):
 name=names[c.unpack('h',at)[0]]
 if 'initial_spawn_point' not in name and 'respawn_point' not in name:continue
 address=at-c.start+c.base
 b.put(address+8,'3f',*position)
 b.put(address+20,'3f',yaw,0,0)
 changed.append({'index':i,'name':name})
fallback=next(x for x in schema if x.get('name')=='Player Starting Locations')
for at in c.block(scnr+int(fallback.get('offset'),0),int(fallback.get('elementSize'),0)):
 address=at-c.start+c.base
 b.put(address,'3f',*position)
 b.put(address+12,'2f',yaw,0)
object_changes=[]
if '--shadows' in sys.argv:
 vehicles=next(x for x in schema if x.get('name')=='Vehicles')
 vr=c.block(scnr+int(vehicles.get('offset'),0),int(vehicles.get('elementSize'),0))
 placements=((5.5,16,-1.7),(5.5,20,-1.7),(5.5,24,-1.7),(5.5,28,-2.14),(9,19,-1.7),(9,27,-1.7))
 for i,pos in enumerate(placements):
  at=vr[i];address=at-c.start+c.base
  b.put(address,'h',0) # Original stock Warthog palette entry.
  b.put(address+8,'3f',*pos)
  b.put(address+20,'3f',1.57079632679,0,0)
  object_changes.append({'vehicle_index':i,'stock_object':'warthog','position':pos})
if '--objects' in sys.argv:
 # Keep stock meshes and LOD thresholds. The native Mongoose has no alternate
 # LOD model; use stock rifles at distances straddling their authored thresholds.
 weapons=next(x for x in schema if x.get('name')=='Weapons')
 wp=next(x for x in schema if x.get('name')=='Weapon Palette')
 wn=[c.name(c.u(at+12)&65535) for at in c.block(scnr+int(wp.get('offset'),0),int(wp.get('elementSize'),0))]
 rifle=next(i for i,n in enumerate(wn) if n.endswith('battle_rifle'))
 wr=c.block(scnr+int(weapons.get('offset'),0),int(weapons.get('elementSize'),0))
 for i,at in enumerate(wr[:4]):
  address=at-c.start+c.base
  pos=(8.0-i*.7,25.5+i*.9,-.4+i*.2)
  b.put(address,'h',rifle)
  b.put(address+8,'3f',*pos)
  b.put(address+20,'3f',1.1,0,0)
  b.put(address+0x70,'I',1) # Authored "initially at rest" placement flag.
  object_changes.append({'weapon_index':i,'stock_object':wn[rifle],'position':pos})
 vehicles=next(x for x in schema if x.get('name')=='Vehicles')
 vr=c.block(scnr+int(vehicles.get('offset'),0),int(vehicles.get('elementSize'),0))
 for i,(x,y) in enumerate(((8,26),(8,28),(10,28),(10,26))):
  at=vr[i];address=at-c.start+c.base
  b.put(address,'h',2) # Existing stock Mongoose palette entry.
  b.put(address+8,'3f',x,y,-1.4)
  b.put(address+20,'3f',2.7,0,0)
  object_changes.append({'vehicle_index':i,'stock_object':'mongoose','position':(x,y,-1.4)})
payload=b.finish(resource_salt(source/'default.xex'))
(target/'maps/zanzibar.map').write_bytes(payload)
report={'original_map':'Last Resort / Halo 3 ODST Multiplayer Disc','position':position,'yaw':yaw,
 'changed_spawn_markers':changed,'output_sha256':hashlib.sha256(payload).hexdigest(),
 'source_sha256':hashlib.sha256(c.data).hexdigest(),'assets':'Original stock assets; no asset settings changed'}
report['test_object_placements']=object_changes
b.close()
(target/'fixture.json').write_text(json.dumps(report,indent=2))
print(target)
