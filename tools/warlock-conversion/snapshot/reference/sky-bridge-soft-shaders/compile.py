import json,shutil,subprocess,os
from pathlib import Path
out=Path('work/sky-bridge/soft-native-01');out.mkdir(exist_ok=True);shutil.copytree('work/sky-bridge/lamp-native-01/xenos-source',out/'xenos-source',dirs_exist_ok=True)
(out/'soft-xenos.fx').write_text('float4 v_squish_params;\nbool v_mesh_squished;\n#define BUMP_GET_CHANNELS(BM) ((BM).rg)\n#include "xenos-source/halogram.fx"\n')
p=out/'xenos-source/deform.fx'
p.write_text(p.read_text().replace('#ifndef APPLY_FIXES','#if 0'))
p=out/'xenos-source/common.fx'
s=p.read_text().replace('PARAM_SAMPLER_2D(depth_map);', 'PARAM_SAMPLER_2D(depth_map);\nstatic float2 sky_bridge_depth_projection;')
s=s.replace('get_softness(z_to_w(sample2D(depth_map, frag_coord).r), linearDepth, soft_z_range)', 'get_softness(sky_bridge_depth_projection.y / (sample2D(depth_map, frag_coord).r - sky_bridge_depth_projection.x), linearDepth, soft_z_range)')
p.write_text(s)
p=out/'xenos-source/entry_points.fx'
s=p.read_text().replace('APPLY_FIXES','SKY_BRIDGE_SOFT_DEPTH')
for structure in ('static_per_vertex_color_vsout','dynamic_light_vsout'):
 s=s.replace('struct '+structure+'\n{','struct '+structure+'\n{\n float2 soft_depth_projection : TEXCOORD7;')
for declaration in ('static_per_vertex_color_vsout vsout;','dynamic_light_vsout vsout;'):
 s=s.replace(declaration, declaration+\
  '\n float3 projection_z=View_Projection._m02_m12_m22;\n float3 projection_w=View_Projection._m03_m13_m23;\n float scale=dot(projection_z,projection_w)/dot(projection_w,projection_w);\n vsout.soft_depth_projection=float2(scale,View_Projection._m32-scale*View_Projection._m33);')
for signature in ('accum_pixel static_per_vertex_color_ps(\n\tin static_per_vertex_color_vsout vsout)\n{','accum_pixel default_dynamic_light_ps(\n\tin dynamic_light_vsout vsout,\n\tbool cinematic)\n{'):
 assert signature in s,signature
 s=s.replace(signature,signature+'\n sky_bridge_depth_projection=vsout.soft_depth_projection;')
p.write_text(s)
defines=json.loads(Path('work/sky-bridge/lamp-native-01/compilation.json').read_text())['defines']
defines=[x.replace('calc_self_illumination_multilayer_ps','calc_self_illumination_simple_ps').replace('blend_type=opaque','blend_type=additive').replace('calc_overlay_multiply_ps','calc_overlay_additive_ps').replace('calc_edge_fade_none_ps','calc_edge_fade_simple_ps') for x in defines]
defines+=['/DSKY_BRIDGE_SOFT_DEPTH=1','/Dapply_soft_fade=apply_soft_fade_on','/Dmaybe_calc_albedo=1']
env=dict(os.environ,TEMP=str(Path('.local/build-temp').resolve()),TMP=str(Path('.local/build-temp').resolve()));results=[]
for stage in ('ps','vs-world','vs-rigid','vs-skinned'):
 for name in (('albedo','static_per_pixel','static_per_vertex','static_sh','static_prt_ambient','static_prt_linear','static_prt_quadratic','static_per_vertex_color','dynamic_light','dynamic_light_cinematic') if stage=='ps' else ('static_per_vertex_color','dynamic_light','dynamic_light_cinematic')):
  shader_stage=stage.split('-')[0]
  entry=('static_prt' if name.startswith('static_prt_') else name)+'_'+shader_stage
  if name=='dynamic_light_cinematic':entry='dynamic_light_cine_'+shader_stage
  if name=='dynamic_light' and shader_stage=='vs':entry='default_dynamic_light_vs'
  ds=defines if stage=='ps' else [x for x in defines if x!='/DPIXEL_SHADER=1']+['/DVERTEX_SHADER=1']
  if name not in ('static_per_vertex_color','dynamic_light','dynamic_light_cinematic'):
   ds=[x for x in ds if x not in ('/DSKY_BRIDGE_SOFT_DEPTH=1','/Dapply_soft_fade=apply_soft_fade_on')]
  if shader_stage=='vs':
   kind=stage.split('-')[1];ds=[x.replace('vertex_type=s_world_vertex','vertex_type=s_'+kind+'_vertex').replace('deform=deform_world','deform=deform_'+kind) for x in ds]
  base=out/(name+'-'+stage)
  result=subprocess.run([r'C:\Program Files (x86)\Microsoft Xbox 360 SDK\bin\win32\fxc.exe','/T',shader_stage+'_3_0','/E',entry,'/Fo',str(base.with_suffix('.bin')),'/Fc',str(base.with_suffix('.asm')),*ds,'/Dentry_point='+name,str(out/'soft-xenos.fx')],env=env,capture_output=True,text=True,timeout=60)
  base.with_suffix('.log').write_text(result.stdout+result.stderr);results.append(dict(stage=stage,name=name,success=result.returncode==0));print(name,stage,result.returncode,(result.stdout+result.stderr)[-500:])
(out/'compilation.json').write_text(json.dumps(dict(defines=defines,programs=results),indent=2))
