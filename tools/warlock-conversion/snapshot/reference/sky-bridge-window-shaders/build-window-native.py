from pathlib import Path
import json,os,shutil,subprocess,hashlib,sys
sys.path.insert(0,"tools/warlock-conversion/snapshot/tools")
from lightmap_register_reservations import reserve_shared_source
from cache_reader import Cache
root=Path.cwd();out=root/'work/sky-bridge/window-native-01';out.mkdir(exist_ok=True)
src=root/'work/powerhouse/native-concrete-shaders/xenos-source';shutil.copytree(src,out/'xenos-source',dirs_exist_ok=True)
persist=out/'xenos-source/hlsl_constant_persist.fx';persist.write_text(reserve_shared_source(persist.read_text()))
recipe=json.loads((root/'tools/warlock-conversion/snapshot/reference/powerhouse-concrete-shaders/recipe.json').read_text())
changes=dict(calc_albedo_ps='calc_albedo_default_ps',calc_albedo_vs='calc_albedo_default_vs',calc_bumpmap_ps='calc_bumpmap_off_ps',calc_bumpmap_vs='calc_bumpmap_off_vs',calc_specular_mask_ps='calc_specular_mask_no_specular_mask_ps',calc_self_illumination_ps='calc_self_illumination_none_ps',material_type='cook_torrance',envmap_type='dynamic',blend_type='alpha_blend')
defines=['/Dmaybe_calc_albedo=1']+[('/D'+x[2:].split('=')[0]+'='+changes[x[2:].split('=')[0]]) if x[2:].split('=')[0] in changes else x for x in recipe['defines']]
wrapper=out/'window.fx';wrapper.write_text('float4 v_squish_params;\nbool v_mesh_squished;\n#define BUMP_GET_CHANNELS(BM) ((BM).rg)\n#include "xenos-source/shader.fx"\n')
env=dict(os.environ,TEMP=str(root/'.local/build-temp'),TMP=str(root/'.local/build-temp'));result=[]
for p in recipe['programs']:
 n=p['name'];entry='static_prt_ps' if n.startswith('static_prt_') else 'dynamic_light_cine_ps' if p['entry']==17 else n+'_ps'
 b=out/(n+'-ps.bin');a=out/(n+'-ps.asm');r=subprocess.run([r'C:\Program Files (x86)\Microsoft Xbox 360 SDK\bin\win32\fxc.exe','/T','ps_3_0','/E',entry,'/Fo',str(b),'/Fc',str(a),*defines,'/Dentry_point='+n,str(wrapper)],cwd=root,env=env,capture_output=True,text=True,timeout=60)
 (out/(n+'.log')).write_text(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(n+' '+r.stdout+r.stderr)
 result.append(dict(entry=p['entry'],name=n,stage='ps',success=True,sha256=hashlib.sha256(b.read_bytes()).hexdigest()))
(out/'compilation.json').write_text(json.dumps(dict(defines=defines,programs=result,source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (out/'xenos-source').iterdir() if p.is_file()}),indent=2));print('Compiled',len(result),'original-Xbox-360 pixel programs')
