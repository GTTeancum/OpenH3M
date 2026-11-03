import sys,json,subprocess,os,re,shutil
from pathlib import Path
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
from string_ids import StringTable
out=Path('work/sky-bridge/particle-smoke-01');out.mkdir(exist_ok=True)
c=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map',True);st=StringTable(c);root=next(t['offset'] for i,t in c.tags.items() if t['group']=='rmdf' and c.name(i)==r'shaders\particle');opts=[5,10,0,0,0,1,0,1,0,0]
defines=['/DPIXEL_SHADER=1','/DDX_VERSION=9','/DSHADER_30=1','/Dvertex_type=s_particle_vertex']
for j,row in enumerate(c.block(root+16,24)):
 cat=st.text(c.u(row));defines.append('/Dcategory_'+cat+'='+str(opts[j]))
 for k,x in enumerate(c.block(row+4,28)):defines.append('/Dcategory_'+cat+'_option_'+st.text(c.u(x))+'='+str(k))
c.close()
known={x.split('=')[0] for x in defines}
for file in Path('work/sky-bridge/lamp-native-01/xenos-source').glob('*'):
 if file.suffix not in ('.fx','.hlsl'):continue
 for cat,opt in re.findall(r'(?:TEST_CATEGORY_OPTION|IF_CATEGORY_OPTION|IF_NOT_CATEGORY_OPTION)\(\s*(\w+)\s*,\s*(\w+)\s*\)',file.read_text(errors='replace')):
  name='/Dcategory_'+cat+'_option_'+opt
  if name not in known:defines.append(name+'=1000');known.add(name)
shutil.copytree('work/sky-bridge/lamp-native-01/xenos-source',out/'xenos-source',dirs_exist_ok=True)
p=out/'xenos-source/particle_render.hlsl';p.write_text(p.read_text().replace('PARAM(float4, base_map_xform);','static const float4 base_map_xform=float4(1,1,0,0);').replace('PARAM(float, depth_fade_range);','uniform float depth_fade_range : register(c100);').replace('distorted_pixel.ssr_color= float4(0.0f, 0.0f, 0.0f, 0.0f);','').replace('PARAM(float4, alpha_map_xform);','static const float4 alpha_map_xform=float4(1,1,0,0);').replace('CONVERT_TO_RENDER_TARGET_FOR_BLEND(blended, false, false, 0.0f)','CONVERT_TO_RENDER_TARGET_FOR_BLEND(blended, false, false)'))
q=out/'xenos-source/particle.fx';q.write_text(q.read_text().replace('PARAM(float, depth_fade_range);','uniform float depth_fade_range : register(c100);'))
wrapper=out/'particle.fx';wrapper.write_text('#define BUMP_GET_CHANNELS(BM) ((BM).rg)\n#include "'+(out/'xenos-source/particle.fx').resolve().as_posix()+'"\n')
env=dict(os.environ,TEMP=str(Path('.local/build-temp').resolve()),TMP=str(Path('.local/build-temp').resolve()))
r=subprocess.run([r'C:\Program Files (x86)\Microsoft Xbox 360 SDK\bin\win32\fxc.exe','/T','ps_3_0','/E','default_ps','/Fo',str(out/'default.bin'),'/Fc',str(out/'default.asm'),*defines,str(wrapper)],env=env,capture_output=True,text=True,timeout=60)
(out/'compile.log').write_text(r.stdout+r.stderr);(out/'recipe.json').write_text(json.dumps(dict(defines=defines,success=r.returncode==0),indent=2));print(r.returncode,r.stdout,r.stderr)
