"""Remove explicitly unwanted rain-card draws and electrical light pulses.
Builds a private map from the accepted Sky Bridge baseline; never installs it.
"""
from pathlib import Path
import hashlib,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from map_builder import MapBuilder
from build_scenario_checkpoint import resource_salt
run=ROOT/'work/map-review-20261105'
record=json.loads((ROOT/'tools/warlock-conversion/snapshot/reference/sky-bridge-performance/candidate36-install-result.json').read_text())
source=Path(record['target']);output=run/'sky-bridge-no-rain-flash.map'
assert not output.exists()
b=MapBuilder(source,0);c=b.cache
assert hashlib.sha256(b.original).hexdigest()==record['sha256']=='39873291ea89a3225a53ecda3f9811f7429ab46c8760ebc07a9938fcf8dd0245'
changes=[];removed=[]
def zero(offset,fmt,before,reason):
 assert c.unpack(fmt,offset)[0]==before
 b.put(offset-c.start+c.base,fmt,0)
 changes.append(dict(offset=offset,size=2 if fmt=='H' else 4,before=before,after=0,reason=reason))
bsp=next(t['offset'] for t in c.tags.values() if t['group']=='sbsp')
materials=c.block(bsp+0xc0,36)
rain_slots={19:9415,20:9415,21:9418}
for slot,tag in rain_slots.items():assert c.u(materials[slot]+12)&65535==tag
for mi,mesh in enumerate(c.block(bsp+0x2e4,76)):
 subparts=c.block(mesh+12,8)
 for pi,part in enumerate(c.block(mesh,16)):
  slot=c.unpack('h',part)[0]
  if slot not in rain_slots:continue
  count=c.unpack('H',part+6)[0];first,n=c.unpack('2H',part+8)
  zero(part+6,'H',count,'rain-card part index count')
  for sub in subparts[first:first+n]:zero(sub+2,'H',c.unpack('H',sub+2)[0],'rain-card subpart index count')
  removed.append(dict(mesh=mi,part=pi,material_slot=slot,indices=count))
assert removed
lights=[]
# Source/target identities were matched through authored effect placements.
for effect in (10416,10419):
 assert c.tags[effect]['group']=='effe'
 for ei,event in enumerate(c.block(c.tags[effect]['offset']+0x2c,68)):
  parts=c.block(event+0x20,96)
  groups=[c.tags[c.u(p+0x1c)&65535]['group'] for p in parts]
  if 'ligh' not in groups:continue
  assert all(g=='ligh' for g in groups),'Do not suppress unrelated effect parts'
  zero(event+0x20,'I',len(parts),'electrical geometry light creation')
  lights.append(dict(effect=effect,event=ei,light_parts=len(parts)))
assert len(lights)==2
result=b.finish(resource_salt('C:/X360/ISOs/H3M/default.xex'))
allowed={i for row in changes for i in range(row['offset'],row['offset']+row['size'])}|set(range(0x2c4,0x2c8))|set(range(0x330,0x344))
diff=np.flatnonzero(np.frombuffer(result,dtype=np.uint8)!=np.frombuffer(b.original,dtype=np.uint8)).tolist()
assert set(diff)<=allowed
output.write_bytes(result)
report=dict(source=str(source),source_sha256=record['sha256'],output=str(output),output_sha256=hashlib.sha256(result).hexdigest(),rain_parts=removed,light_events=lights,changes=changes,changed_byte_count=len(diff),status='Candidate only; native visual validation pending',preserved='Collision, gameplay, material programs, electrical particles, other geometry and outdoor particle weather',credit='Sky Bridge, Halo Online; GeneralHeed / Priception Halo Online Map Pack for Halo 3, https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190; Xbox 360/OpenH3M adaptation by this project')
(run/'sky-bridge-no-rain-flash.json').write_text(json.dumps(report,indent=2));b.close()
print(json.dumps(dict(rain_parts=len(removed),rain_indices=sum(x['indices'] for x in removed),light_events=len(lights),changed_bytes=len(diff))))
