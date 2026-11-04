import sys,json
from pathlib import Path
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
from string_ids import StringTable
out=Path('work/sky-bridge/puddle-native-01')
s=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map',True);ss=StringTable(s)
p,=s.block(s.tags[12294]['offset']+40,140);t=s.tags[s.u(p+12)&65535]['offset']
names={u:[ss.text(s.u(x)) for x in s.block(t+off,4)] for u,off in ((0,108),(4,72),(5,84),(6,96))}
assert s.u(p+92)==4 and not s.u(p+40)
source_names={k:list(v) for k,v in names.items()}
names[4].append('use_material_texture')
(out/'profile.json').write_text(json.dumps(dict(names={str(k):v for k,v in names.items()},source_names=source_names,material=s.name(12294)),indent=2));s.close()
ref=Path('tools/warlock-conversion/snapshot/reference/sky-bridge-soft-shaders')
text=(ref/'plan-routes.py').read_text();a=text.index('names={usage:');b=text.index('passes=c.block',a);text=text[:a]+'names='+repr(names)+'\n'+text[b:]
text=text.replace('soft-native-01','puddle-native-01').replace('maps/sandbox.map','maps/armory.map').replace('halogram_templates','shader_templates').replace('_0_1_1_0_0_0_1','_0_2_0_1_1_2_0_3_0_0')
(out/'plan-routes.py').write_text(text);exec(compile(text,'window-routes','exec'),{})
text=(ref/'audit-interface.py').read_text().replace('soft-native-01','puddle-native-01').replace('maps/sandbox.map','maps/armory.map').replace('halogram_templates','shader_templates').replace('_0_1_1_0_0_0_1','_0_2_0_1_1_2_0_3_0_0')
(out/'audit-interface.py').write_text(text);exec(compile(text,'window-interface','exec'),{})
