import sys,json
from pathlib import Path
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
from string_ids import StringTable
out=Path('work/sky-bridge/water-card-native-01')
s=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map',True);ss=StringTable(s)
p,=s.block(s.tags[12310]['offset']+40,140);t=s.tags[s.u(p+12)&65535]['offset']
names={u:[ss.text(s.u(x)) for x in s.block(t+off,4)] for u,off in ((0,108),(4,72),(5,84),(6,96))}
assert s.u(p+92)==5 and not s.u(p+40)
source_names={k:list(v) for k,v in names.items()}
# Two-lobe Phong uses the original source names without Cook-Torrance additions.
(out/'profile.json').write_text(json.dumps(dict(names={str(k):v for k,v in names.items()},source_names=source_names,material=s.name(12310)),indent=2));s.close()
ref=Path('tools/warlock-conversion/snapshot/reference/sky-bridge-soft-shaders')
text=(ref/'plan-routes.py').read_text();a=text.index('names={usage:');b=text.index('passes=c.block',a);text=text[:a]+'names='+repr(names)+'\n'+text[b:]
text=text.replace('soft-native-01','water-card-native-01').replace('maps/sandbox.map','maps/salvation.map').replace('halogram_templates','shader_templates').replace('_0_1_1_0_0_0_1','_6_2_0_1_2_2_0_0_0_0')
text=text.replace('result=[];unresolved=[]',"\n# Confirm newly required shared registers against a native transparent/emissive\n# donor from the same stock map, rather than assigning unverified externs.\nsupplement=c.tags[74]['offset']\nassert c.name(74)==r'shaders\\shader_templates\\_0_0_0_0_0_0_2_3_0_0'\nsuppixel=c.tags[c.u(supplement+28)&65535]['offset']\nsupshaders=c.block(suppixel+20,80);supe=c.block(suppixel+4,2)\nsupt=c.block(supplement+36,2);suppasses=c.block(supplement+48,28);suproutes=c.block(supplement+60,4)\nshared_proof=[]\nfor desired,expected in {'actually_calc_albedo':(0,0,1),'g_alt_exposure':(2,12,1)}.items():\n for entry,(pe,te) in enumerate(zip(supe,supt)):\n  start,count=c.unpack('BB',pe);packed=c.unpack('H',te)[0]\n  if count!=1 or packed>>10!=1:continue\n  shader=supshaders[start];passrow=suppasses[packed&1023]\n  found=[c.unpack('HBB',r+4) for r in c.block(shader+40,8) if strings.text(c.u(r)).lower()==desired]\n  if not found:continue\n  register,size,register_set=found[0];assert (register_set,register,size)==expected\n  for usage,rs in sets.items():\n   if rs!=register_set:continue\n   span=c.unpack('H',passrow+usage*2)[0]\n   assert all(not register<=c.unpack('H',r)[0]<register+size for r in suproutes[span&1023:(span&1023)+(span>>10)])\n  shared_proof.append(dict(name=desired,entry=entry,binding=expected,donor=74))\n assert any(x['name']==desired for x in shared_proof),desired\n persistent[desired]=expected\n(out/'shared-register-proof.json').write_text(json.dumps(shared_proof,indent=2))\n\nresult=[];unresolved=[]")
(out/'plan-routes.py').write_text(text);exec(compile(text,'window-routes','exec'),{})
text=(ref/'audit-interface.py').read_text().replace('soft-native-01','water-card-native-01').replace('maps/sandbox.map','maps/salvation.map').replace('halogram_templates','shader_templates').replace('_0_1_1_0_0_0_1','_6_2_0_1_2_2_0_0_0_0')
(out/'audit-interface.py').write_text(text);exec(compile(text,'window-interface','exec'),{})
