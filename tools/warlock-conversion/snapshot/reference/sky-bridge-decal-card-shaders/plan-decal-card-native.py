import sys,json
from pathlib import Path
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
from string_ids import StringTable
out=Path('work/sky-bridge/decal-card-native-01')
s=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map',True);ss=StringTable(s)
p,=s.block(s.tags[12453]['offset']+40,140);t=s.tags[s.u(p+12)&65535]['offset']
names={u:[ss.text(s.u(x)) for x in s.block(t+off,4)] for u,off in ((0,108),(4,72),(5,84),(6,96))}
assert not s.u(p+92) and not s.u(p+40)
source_names={k:list(v) for k,v in names.items()}
names[4].append('use_material_texture')
(out/'profile.json').write_text(json.dumps(dict(names={str(k):v for k,v in names.items()},source_names=source_names,material=s.name(12453)),indent=2));s.close()
ref=Path('tools/warlock-conversion/snapshot/reference/sky-bridge-soft-shaders')
text=(ref/'plan-routes.py').read_text();a=text.index('names={usage:');b=text.index('passes=c.block',a);text=text[:a]+'names='+repr(names)+'\n'+text[b:]
text=text.replace('soft-native-01','decal-card-native-01').replace('maps/sandbox.map','maps/armory.map').replace('halogram_templates','shader_templates').replace('_0_1_1_0_0_0_1','_0_0_1_1_1_2_0_0_0_0')
text=text.replace('result=[];unresolved=[]',"\n# A stock transparent Armory shader supplies the shared albedo switch absent\n# from the opaque decal donor. Prove both reflection and absence of routes.\nsupplement = c.tags[9401]['offset']\nassert c.name(9401) == r'shaders\\shader_templates\\_0_2_0_1_1_2_0_3_0_0'\nspp = c.tags[c.u(supplement+28)&65535]['offset']\nsp_programs = c.block(spp+20,80)\nsp_entries = c.block(spp+4,2)\nst_entries = c.block(supplement+36,2)\nst_passes = c.block(supplement+48,28)\nst_routes = c.block(supplement+60,4)\nproof = []\nfor entry,(pe,te) in enumerate(zip(sp_entries,st_entries)):\n start,count=c.unpack('BB',pe); packed=c.unpack('H',te)[0]\n if count != 1 or packed>>10 != 1: continue\n regs=[c.unpack('HBB',r+4) for r in c.block(sp_programs[start]+40,8) if strings.text(c.u(r)).lower()=='actually_calc_albedo']\n if not regs: continue\n assert regs == [(0,1,0)],regs\n row=st_passes[packed&1023]\n for usage,regset in sets.items():\n  if regset != 0: continue\n  span=c.unpack('H',row+usage*2)[0]\n  assert all(c.unpack('H',r)[0] != 0 for r in st_routes[span&1023:(span&1023)+(span>>10)])\n proof.append(dict(entry=entry,donor_map='armory.map',donor_template=9401,name='actually_calc_albedo',register=0,register_set=0))\nassert proof\npersistent['actually_calc_albedo']=(0,0,1)\n(out/'shared-register-proof.json').write_text(json.dumps(proof,indent=2))\nresult=[];unresolved=[]\n")
(out/'plan-routes.py').write_text(text);exec(compile(text,'window-routes','exec'),{})
text=(ref/'audit-interface.py').read_text().replace('soft-native-01','decal-card-native-01').replace('maps/sandbox.map','maps/armory.map').replace('halogram_templates','shader_templates').replace('_0_1_1_0_0_0_1','_0_0_1_1_1_2_0_0_0_0')
(out/'audit-interface.py').write_text(text);exec(compile(text,'window-interface','exec'),{})
