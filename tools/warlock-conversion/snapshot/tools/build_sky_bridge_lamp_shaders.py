import sys,json,subprocess,os,hashlib,shutil
from pathlib import Path
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from lightmap_register_reservations import reserve_shared_source
from cache_reader import Cache
from string_ids import StringTable
repository=Path(__file__).resolve().parents[4]
os.chdir(repository)
reference=repository/'tools/warlock-conversion/snapshot/reference/sky-bridge-lamp-shaders'
for name,expected in json.loads((reference/'input-hashes.json').read_text()).items():
 if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=expected:
  raise ValueError('Lamp shader source changed: '+name)
out=Path('work/sky-bridge/lamp-native-01')
out.mkdir(parents=True,exist_ok=True)
shutil.copytree('work/powerhouse/native-window-shaders/xenos-source',out/'xenos-source',dirs_exist_ok=True)
for name in ('halogram.fx','self_illumination_halogram.fx','overlays.fx','warp.fx'):
 shutil.copyfile(Path('work/powerhouse/shader-toolchain/reference/halo_online_shaders')/name,out/'xenos-source'/name)
p=out/'xenos-source/self_illumination_halogram.fx'
p.write_text(p.read_text().replace('PARAM(int, layers_of_4);','PARAM(float, layers_of_4);'))
(out/'lamp-xenos.fx').write_text('float4 v_squish_params;\nbool v_mesh_squished;\n#define BUMP_GET_CHANNELS(BM) ((BM).rg)\n#include "xenos-source/halogram.fx"\n')
p=out/'xenos-source/hlsl_constant_persist.fx'
p.write_text(reserve_shared_source(p.read_text()))
# This specialization is valid only for the three static authored four-group lamps.
lamps=json.loads(Path('work/sky-bridge/opaque-multilayer-lamps.json').read_text())
assert len(lamps)==3 and all(x['animations']==0 and x['constants']['layers_of_4']==[4.0]*4 for x in lamps)
p=out/'xenos-source/self_illumination_halogram.fx'
s=p.read_text();s=s.replace('for (int x= 0; x < layers_of_4; x++)','[unroll] for (int x= 0; x < 4; x++)');p.write_text(s)
c=Cache('C:/X360/ISOs/H3M/maps/sandbox.map');st=StringTable(c)
t=next(t for i,t in c.tags.items() if t['group']=='rmt2' and c.name(i)==r'shaders\halogram_templates\_2_8_0_0_0_1_0')
pix=c.tags[c.u(t['offset']+28)&65535]['offset'];pr=c.block(pix+20,80);entries=c.block(pix+4,2);refs=[]
for n,e in enumerate(entries):
 start,count=c.unpack('BB',e)
 for idx in range(start,start+count):
  p=pr[idx];refs.append(dict(entry=n,shader=idx,registers=[dict(name=st.text(c.u(r)),register=c.unpack('H',r+4)[0],count=c.data[r+6],set=c.data[r+7]) for r in c.block(p+40,8)],gprs=c.u(p+72)))
(out/'native-reflection.json').write_text(json.dumps(refs,indent=2));c.close()
recipe=json.loads((reference/'recipe.json').read_text());names={x['entry']:x['name'] for x in json.loads(Path('tools/warlock-conversion/snapshot/reference/powerhouse-water-shaders/recipe.json').read_text())['programs']}
env=dict(os.environ,TEMP=str(Path('.local/build-temp').resolve()),TMP=str(Path('.local/build-temp').resolve()))
programs=[]
for ref in refs:
 name=names[ref['entry']];base=out/name
 args=[r'C:\Program Files (x86)\Microsoft Xbox 360 SDK\bin\win32\fxc.exe','/T','ps_3_0','/E',('static_prt_ps' if name.startswith('static_prt_') else 'dynamic_light_cine_ps' if name=='dynamic_light_cinematic' else name+'_ps'),'/Fo',str(base.with_suffix('.bin')),'/Fc',str(base.with_suffix('.asm')),*recipe['defines'],'/Dentry_point='+name,str(out/'lamp-xenos.fx')]
 result=subprocess.run(args,env=env,capture_output=True,text=True,timeout=60)
 base.with_suffix('.log').write_text(result.stdout+result.stderr)
 programs.append(dict(entry=ref['entry'],name=name,success=result.returncode==0,sha256=hashlib.sha256(base.with_suffix('.bin').read_bytes()).hexdigest() if result.returncode==0 else None))
 print(name,result.returncode,(result.stdout+result.stderr)[-400:])
recipe['programs']=programs;recipe['specialization']={'layers_of_4':4,'static_materials':[x['name'] for x in lamps]}
(out/'compilation.json').write_text(json.dumps(recipe,indent=2))

assert all(p['success'] for p in programs), 'Lamp shader compilation failed'
