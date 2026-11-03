"""Check emitted Sky Bridge window constants, samplers and shader routes."""
import sys,json,struct
from pathlib import Path
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
from string_ids import StringTable
s=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map',True)
c=Cache('work/sky-bridge/zanzibar-29.map');ss,cs=StringTable(s),StringTable(c)
a=s.block(s.tags[10471]['offset']+208,36);bsp,=[v for v in c.tags.values() if v['group']=='sbsp' and c.u(v['offset']+192)==len(a)]
b=c.block(bsp['offset']+192,36)
id,={c.u(y+12)&65535 for x,y in zip(a,b) if s.u(x+12)&65535==12142}
sp,=s.block(s.tags[12142]['offset']+40,140);tp,=c.block(c.tags[id]['offset']+40,132)
st=s.tags[s.u(sp+12)&65535]['offset'];tt=c.tags[c.u(tp+12)&65535]['offset']
names=lambda cache,strings,t,o:[strings.text(cache.u(x)) for x in cache.block(t+o,4)]
sn=names(s,ss,st,72);tn=names(c,cs,tt,72)
assert tn==sn+['use_material_texture']
sc=s.block(sp+28,16);tc=c.block(tp+28,16)
assert all(s.unpack('4f',x)==c.unpack('4f',y) for x,y in zip(sc,tc))
assert c.unpack('4f',tc[-1])==(1.,)*4
assert names(s,ss,st,96)==names(c,cs,tt,96)
assert s.u(sp+52)==c.u(tp+52)==3
assert c.u(tp+92)==s.u(sp+92)==0 and c.u(tp+104)==3
assert names(c,cs,tt,108)==names(s,ss,st,108)
textures=[]
for name,x,y in zip(names(s,ss,st,108),s.block(sp+16,28),c.block(tp+16,24)):
 image,address,filtering,comparison,external,transform,pad,animation,pad2=s.unpack('h4BbBhH',x+16)
 assert c.unpack('hBBB',y+16)==(image,address,filtering,external)
 assert c.unpack('b',y+21)[0]==tn.index(name)
 assert c.unpack('H',y+22)[0]==animation
 assert c.u(y+12)!=0xffffffff
 textures.append(dict(name=name,source=s.name(s.u(x+12)&65535),target=c.u(y+12)&65535))
plan=json.loads(Path('work/sky-bridge/window-native-01/route-plan.json').read_text())
passes=c.block(tt+48,28);entries=c.block(tt+36,2);routes=c.block(tt+60,4)
for program in plan['programs']:
 packed=c.unpack('H',entries[program['entry']])[0];assert packed>>10==1
 pass_row=passes[packed&1023]
 for usage,expected in enumerate(program['usages']):
  packed=c.unpack('H',pass_row+usage*2)[0]
  actual=[list(c.unpack('HBB',x)) for x in routes[packed&1023:(packed&1023)+(packed>>10)]]
  assert actual==expected
report=dict(target_material=id,source_float_constants_exact=True,source_booleans_exact=True,
 material_texture_float_enabled=True,sampler_controls_exact=True,no_bump_sampler=True,
 blend_mode=3,native_program_route_checks=12,textures=textures,
 limitation='No visual or runtime verification; no performance claim')
Path('work/sky-bridge/candidate-29-window-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));s.close();c.close()
