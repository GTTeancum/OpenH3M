"""Verify emitted water-card material structurally, without importing images."""
import sys,json,struct,hashlib
from pathlib import Path
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
from string_ids import StringTable
from tag_functions import convert_function
s=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map',True)
c=Cache('work/sky-bridge/zanzibar-30.map')
tag_id=int(sys.argv[1]);assert tag_id in (12310,12318)
ss,cs=StringTable(s),StringTable(c)
a=s.block(s.tags[10471]['offset']+208,36)
bsp,=[v for v in c.tags.values() if v['group']=='sbsp' and c.u(v['offset']+192)==len(a)]
b=c.block(bsp['offset']+192,36)
ids={c.u(y+12)&65535 for x,y in zip(a,b) if s.u(x+12)&65535==tag_id}
id,=ids
sp,=s.block(s.tags[tag_id]['offset']+40,140);tp,=c.block(c.tags[id]['offset']+40,132)
st=s.tags[s.u(sp+12)&65535]['offset'];tt=c.tags[c.u(tp+12)&65535]['offset']
for offset in (72,84,96,108):
 assert [ss.text(s.u(x)) for x in s.block(st+offset,4)]==[cs.text(c.u(x)) for x in c.block(tt+offset,4)]
assert [s.unpack('4f',x) for x in s.block(sp+28,16)]==[c.unpack('4f',x) for x in c.block(tp+28,16)]
assert s.u(sp+52)==c.u(tp+52)
assert c.unpack('i',tp+104)[0]==1
sf=s.block(sp+92,36);tf=c.block(tp+92,36);assert len(sf)==len(tf)==(5 if tag_id==12310 else 10)
for x,y in zip(sf,tf):
 assert s.u(x)==c.u(y) and s.unpack('f',x+12)==c.unpack('f',y+12)
 assert ss.text(s.u(x+4))==cs.text(c.u(y+4)) and ss.text(s.u(x+8))==cs.text(c.u(y+8))
 size=s.u(x+16);assert size==c.u(y+16)
 sa=s.pointer(s.u(x+28));ta=c.pointer(c.u(y+28))
 assert convert_function(bytes(s.data[sa:sa+size]))==bytes(c.data[ta:ta+size])
textures=[]
for x,y in zip(s.block(sp+16,28),c.block(tp+16,24)):
 image,address,filtering,comparison,external,transform,pad,animation,pad2=s.unpack('h4BbBhH',x+16)
 assert c.unpack('hBBB',y+16)==(image,address,filtering,external)
 assert c.unpack('H',y+22)[0]==animation
 assert c.u(y+12)!=0xffffffff
 textures.append(dict(source=s.name(s.u(x+12)&65535),target=c.u(y+12)&65535))
assert c.u(tp+80)==s.u(sp+80)
from audit_sky_water_card_animation import audit
source_audit=audit(s,tag_id)
entries=c.block(tp+56,2);passes=c.block(tp+68,6);routes=c.block(tp+80,4)
tentries=c.block(tt+36,2);tpasses=c.block(tt+48,28);troutes=c.block(tt+60,4)
def span(packed,rows):
 start,count=packed&1023,packed>>10
 assert start+count<=len(rows)
 return range(start,start+count)
actual=[]
for entry,(ep,tep) in enumerate(zip(entries,tentries)):
 for pi,ti in zip(span(c.unpack('H',ep)[0],passes),span(c.unpack('H',tep)[0],tpasses)):
  for usage,tu in enumerate((0,1,4)):
   names=[cs.text(c.u(x)) for x in c.block(tt+(108 if usage==0 else 72),4)]
   for ri in span(c.unpack('H',passes[pi]+usage*2)[0],routes):
    reg,func,const=c.unpack('HBB',routes[ri])
    matches=[c.unpack('HBB',troutes[r]) for r in span(c.unpack('H',tpasses[ti]+tu*2)[0],troutes)
             if c.unpack('HBB',troutes[r])[:2]==(reg,const)]
    assert len(matches)==1
    actual.append((entry,usage,func,names[const],matches[0][2]))
expected=[(x['entry'],x['usage'],x['function'],x['name'],x['flags']) for x in source_audit['consumers']]
assert sorted(actual)==sorted(expected)
report=dict(target_material=id,animations=len(sf),animation_routes=c.u(tp+80),source_constants_exact=True,animation_consumers_exact=True,
 source_function_payloads_endian_exact=True,sampler_controls_exact=True,blend_mode=1,textures=textures,
 limitation='Structural evidence only; runtime appearance and performance unverified')
Path(f'work/sky-bridge/candidate-30-water-card-{tag_id}-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
s.close();c.close()
