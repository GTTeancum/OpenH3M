from pathlib import Path
import json,os,shutil,subprocess,hashlib,sys
sys.path.insert(0,"tools/warlock-conversion/snapshot/tools")
from lightmap_register_reservations import reserve_shared_source
from cache_reader import Cache
root=Path.cwd();out=root/'work/sky-bridge/window-color-distort-native-01';out.mkdir(exist_ok=True)
source=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map',True)
try:
 for tid,count in ((12412, 1),):
  tag=source.tags[tid];post,=source.block(tag['offset']+40,140)
  assert source.name(source.u(post+12)&65535)==r'shaders\shader_templates\_8_2_0_2_1_2_0_3_0_0_1_0_0'
  assert source.u(post+104)==3 and source.u(post+92)==count
finally:source.close()
src=root/'work/powerhouse/native-concrete-shaders/xenos-source';shutil.copytree(src,out/'xenos-source',dirs_exist_ok=True)
# XDK fxc needs explicit vector operands in the otherwise-unused distortion body.
ep=out/'xenos-source/entry_points.fx'
text=ep.read_text().replace('(sfx_distort * vsout.distortion) * 0.5f + 0.50195998f', '(sfx_distort * float2(vsout.distortion, vsout.distortion)) * float2(0.5f, 0.5f) + float2(0.50195998f, 0.50195998f)').replace('dot(abs(distort_raw * 10.0f), 1.0f)', 'dot(abs(distort_raw * float2(10.0f, 10.0f)), float2(1.0f, 1.0f))')
ep.write_text(text)
persist=out/'xenos-source/hlsl_constant_persist.fx';persist.write_text(reserve_shared_source(persist.read_text()))
recipe=json.loads((root/'tools/warlock-conversion/snapshot/reference/powerhouse-concrete-shaders/recipe.json').read_text())
changes=dict(calc_albedo_ps='calc_albedo_color_mask_ps',calc_albedo_vs='calc_albedo_color_mask_vs',calc_bumpmap_ps='calc_bumpmap_detail_ps',calc_bumpmap_vs='calc_bumpmap_detail_vs',calc_specular_mask_ps='calc_specular_mask_texture_ps',calc_self_illumination_ps='calc_self_illumination_none_ps',material_type='cook_torrance',envmap_type='dynamic',blend_type='alpha_blend',distort_proc_ps='distort_on_ps')
defines=['/Dmaybe_calc_albedo=1']+[('/D'+x[2:].split('=')[0]+'='+changes[x[2:].split('=')[0]]) if x[2:].split('=')[0] in changes else x for x in recipe['defines']]
wrapper=out/'window-color-distort.fx';wrapper.write_text('float4 v_squish_params;\nbool v_mesh_squished;\n#define BUMP_GET_CHANNELS(BM) ((BM).rg)\n#include "xenos-source/shader.fx"\n')
env=dict(os.environ,TEMP=str(root/'.local/build-temp'),TMP=str(root/'.local/build-temp'));result=[]
for p in recipe['programs']:
 n=p['name'];entry='static_prt_ps' if n.startswith('static_prt_') else 'dynamic_light_cine_ps' if p['entry']==17 else n+'_ps'
 b=out/(n+'-ps.bin');a=out/(n+'-ps.asm');r=subprocess.run([r'C:\Program Files (x86)\Microsoft Xbox 360 SDK\bin\win32\fxc.exe','/T','ps_3_0','/E',entry,'/Fo',str(b),'/Fc',str(a),*defines,'/Dentry_point='+n,str(wrapper)],cwd=root,env=env,capture_output=True,text=True,timeout=60)
 (out/(n+'.log')).write_text(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError(n+' '+r.stdout+r.stderr)
 result.append(dict(entry=p['entry'],name=n,stage='ps',success=True,sha256=hashlib.sha256(b.read_bytes()).hexdigest()))
(out/'compilation.json').write_text(json.dumps(dict(defines=defines,programs=result,source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (out/'xenos-source').iterdir() if p.is_file()}),indent=2));print('Compiled',len(result),'original-Xbox-360 pixel programs')
