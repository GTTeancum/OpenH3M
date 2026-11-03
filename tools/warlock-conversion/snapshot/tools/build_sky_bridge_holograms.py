"""Build source-parameter-preserving Sky Bridge halogram profiles with the installed XDK."""
import hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
from cache_reader import Cache
from string_ids import StringTable

REPO=Path(__file__).resolve().parents[4]
def build():
 os.chdir(REPO)
 outroot=REPO/'work/sky-bridge/holograms-01';outroot.mkdir(exist_ok=True)
 src=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map',True);strings=StringTable(src)
 profiles={}
 for i,t in src.tags.items():
  if t['group']!='rmhg' or not (src.name(i).startswith('levels\\multi\\s3d_sky_bridgenew\\') or src.name(i) in (r'levels\solo\s3d_tutorial\shaders\lighting\tut_device_04_glow',r'levels\multi\s3d_turf\shaders\turf_banners_01')):continue
  post=src.block(t['offset']+40,140)[0];template=src.tags[src.u(post+12)&65535]['offset'];variant=src.name(src.u(post+12)&65535).rsplit('\\',1)[-1];options=list(map(int,variant.split('_')[1:]))
  names={str(usage):[strings.text(src.u(r)) for r in src.block(template+offset,4)] for usage,offset in ((0,108),(4,72),(5,84),(6,96))}
  profile=profiles.setdefault(variant,dict(options=options,names=names,materials=[]))
  assert names==profile['names'];profile['materials'].append(src.name(i))
  if options[1]==8:
   values=src.unpack('4f',src.block(post+28,16)[names['4'].index('layers_of_4')]);assert values in ((2.,)*4,(4.,)*4)
   assert all(src.unpack('HBB',r)[2]!=names['4'].index('layers_of_4') for r in src.block(post+80,4))
   count=int(values[0]);assert profile.get('layer_groups',count)==count;profile['layer_groups']=count

 src.close()
 refs=REPO/'tools/warlock-conversion/snapshot/reference/sky-bridge-soft-shaders'
 recipe=json.loads((REPO/'work/sky-bridge/lamp-native-01/compilation.json').read_text())
 stages=json.loads((refs/'compilation.json').read_text())['programs'];stages=[x for x in stages if x['stage']=='ps']
 env=dict(os.environ,TEMP=str(REPO/'.local/build-temp'),TMP=str(REPO/'.local/build-temp'))
 requested=sys.argv[1:]
 for variant,profile in profiles.items():
  if requested and variant not in requested:continue
  opt=profile['options'];names=profile['names']
  exact='shaders\\halogram_templates\\_'+'_'.join(map(str,opt[:7]))
  stock=json.loads((REPO/'work/sky-bridge/halogram-donor-audit.json').read_text())['native_templates']
  if not requested and not any(opt[7:]) and exact in stock:continue
  if opt[0]!=0 or (opt[3] not in (0,1,2,4) or opt[4]!=0) or opt[1] not in (1,4,8):continue
  if opt[7] and profile['materials']!=[r'levels\multi\s3d_sky_bridgenew\sky\shaders\night_city_wall']:continue
  soft=bool(opt[8] and 'use_soft_z' in names['6'])
  directory=outroot/variant;directory.mkdir(exist_ok=True)
  source=REPO/('work/sky-bridge/soft-native-01' if soft else 'work/sky-bridge/lamp-native-01')
  if opt[1]==8:
   shutil.copytree(source/'xenos-source',directory/'xenos-source',dirs_exist_ok=True)
   source=directory
   layer=directory/'xenos-source/self_illumination_halogram.fx'
   layer.write_text(layer.read_text().replace('x < 4;', 'x < '+str(profile['layer_groups'])+';'))
  wrapper=directory/'profile.fx';wrapper.write_text('#define BUMP_GET_CHANNELS(BM) ((BM).rg)\nfloat4 v_squish_params;\nbool v_mesh_squished;\n#include "'+(source/'xenos-source/halogram.fx').as_posix()+'"\n')
  defines=[x for x in recipe['defines'] if not any(x.startswith('/D'+k+'=') for k in ('calc_self_illumination_ps','blend_type','calc_overlay_ps','calc_edge_fade_ps'))]
  defines += ['/Dcalc_self_illumination_ps=calc_self_illumination_'+{1:'simple',4:'from_albedo',5:'detail',8:'multilayer'}[opt[1]]+'_ps','/Dblend_type='+{0:'opaque',1:'additive',3:'alpha_blend'}[opt[2]],'/Dcalc_overlay_ps=calc_overlay_'+{0:'none',1:'additive',2:'additive_detail',3:'multiply',4:'multiply_and_additive_detail'}[opt[5]]+'_ps','/Dcalc_edge_fade_ps=calc_edge_fade_'+{0:'none',1:'simple'}[opt[6]]+'_ps','/Dmaybe_calc_albedo=1']
  if opt[2]==0 and opt[3]==0:defines.remove('/Dmaybe_calc_albedo=1')
  if opt[3]==4:defines.append('/Dalways_calc_albedo=1')
  programs=[]
  for p in stages:
   name=p['name'];entry=('static_prt' if name.startswith('static_prt_') else 'dynamic_light_cine' if name=='dynamic_light_cinematic' else name)+'_ps'
   ds=defines+(['/DSKY_BRIDGE_SOFT_DEPTH=1','/Dapply_soft_fade=apply_soft_fade_on'] if soft and p['entry'] in (9,14,17) else [])
   base=directory/(name+'-ps');r=subprocess.run([r'C:\Program Files (x86)\Microsoft Xbox 360 SDK\bin\win32\fxc.exe','/T','ps_3_0','/E',entry,'/Fo',str(base.with_suffix('.bin')),'/Fc',str(base.with_suffix('.asm')),*ds,'/Dentry_point='+name,str(wrapper)],env=env,capture_output=True,text=True,timeout=60)
   base.with_suffix('.log').write_text(r.stdout+r.stderr)
   if r.returncode:raise RuntimeError(variant+' '+name+' '+r.stderr)
   programs.append(dict(entry=p['entry'],name=name,stage='ps',success=True,sha256=hashlib.sha256(base.with_suffix('.bin').read_bytes()).hexdigest()))
  (directory/'compilation.json').write_text(json.dumps(dict(programs=programs),indent=2))
  profile['soft']=soft;(directory/'profile.json').write_text(json.dumps(profile,indent=2))
  shutil.copyfile(REPO/'work/sky-bridge/soft-native-01/native-reflection.json',directory/'native-reflection.json')
  script=(refs/'plan-routes.py').read_text();a=script.index('names={usage:');b=script.index('passes=c.block',a)
  script=script[:a]+'names='+repr({int(k):v for k,v in names.items()})+'\n'+script[b:]
  script=script.replace("out=Path('work/sky-bridge/soft-native-01')",'out=Path('+repr(str(directory))+')')
  exec(compile(script,str(refs/'plan-routes.py'),'exec'),{})
  script=(refs/'audit-interface.py').read_text().replace("out=Path('work/sky-bridge/soft-native-01')",'out=Path('+repr(str(directory))+')')
  exec(compile(script,str(refs/'audit-interface.py'),'exec'),{})
  audit=json.loads((directory/'native-interface-audit.json').read_text())
  def semantics(lines):return [re.sub(r' [ro]\d+','',x).replace('_centroid','') for x in lines]
  for a in audit:
   old,new=semantics(a['native_inputs']),semantics(a['compiled_inputs'])
   if soft and a['entry'] in (9,14,17):
    assert 'dcl_texcoord7.xy' in new;new.remove('dcl_texcoord7.xy');new=[x.replace('dcl_texcoord.xyz','dcl_texcoord.xy') for x in new]
   a['soft_depth_extension_matches']=old==new
   if not a['soft_depth_extension_matches']:raise ValueError((variant,a['name'],old,new))
  (directory/'native-interface-audit.json').write_text(json.dumps(audit,indent=2))
  if json.loads((directory/'route-plan.json').read_text())['unresolved']:raise ValueError('Unresolved hologram routes')
  if any(not check['equal'] for a in audit for check in a['fixed_register_checks']):raise ValueError('Hologram fixed register mismatch')
  print('Ready:',variant,len(profile['materials']),flush=True)
if __name__=='__main__':build()
