import sys,json,re,subprocess
from pathlib import Path
import os
os.environ["TEMP"]=str(Path.cwd()/".local/build-temp")
os.environ["TMP"]=os.environ["TEMP"]
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
out=Path('work/sky-bridge/lamp-native-01');compiled={x['entry']:x for x in json.loads((out/'compilation.json').read_text())['programs']};refs=json.loads((out/'native-reflection.json').read_text());c=Cache('C:/X360/ISOs/H3M/maps/sandbox.map');t=next(t for i,t in c.tags.items() if t['group']=='rmt2' and c.name(i)==r'shaders\halogram_templates\_2_8_0_0_0_1_0');pix=c.tags[c.u(t['offset']+28)&65535]['offset'];shaders=c.block(pix+20,80);audit=[]
fixed={'camera_position_ps','hdr_gamma2','ldr_gamma2','g_exposure','dynamic_environment_blend','p_lightmap_compress_constant_0','p_lightmap_compress_constant_1','p_tiling_vpos_offset','simple_light_count_int','simple_lights','no_dynamic_lights','albedo_texture','normal_texture','lightprobe_texture_array','dominant_light_intensity_map','scene_ldr_texture','depth_buffer'}
for row in refs:
 entry=row['entry'];name=compiled[entry]['name'];r=shaders[row['shader']];p=c.pointer(c.u(r+76));ds,ms=c.unpack('II',p+44);at=c.pointer(c.u(p+16));binary=out/f'native-{name}.bin';binary.write_bytes(c.data[p+40:p+40+ds]+c.data[at:at+ms]);assembly=out/f'native-{name}.asm';subprocess.run([str(Path('work/powerhouse/shader-toolchain/disassemble.exe')),str(binary),str(assembly)],check=True,timeout=30)
 old=assembly.read_text().rstrip('\0');new=(out/f'{name}.asm').read_text();decl=lambda a:re.findall(r'^dcl_.*$',a,re.M)
 newregs={n.lower():(k,int(i),int(count)) for n,k,i,count in re.findall(r'^//\s+(\w+)\s+([cbis])(\d+)\s+(\d+)\s*$',new,re.M)};checks=[]
 for v in row['registers']:
  n=v['name'].lower()
  if n in fixed and n in newregs:
   expected=({0:'b',1:'i',2:'c',3:'s'}[v['set']],v['register'],v['count']);actual=newregs[n];checks.append(dict(name=n,expected=expected,actual=actual,equal=expected==actual))
 audit.append(dict(entry=entry,name=name,native_inputs=decl(old),compiled_inputs=decl(new),inputs_match=decl(old)==decl(new),fixed_register_checks=checks,native_gprs=row['gprs'],native_max_reg=int(re.search(r'PsMaxReg=(\d+)',old).group(1)) if 'PsMaxReg=' in old else 0))
(out/'native-interface-audit.json').write_text(json.dumps(audit,indent=2));print('Input declarations:',sum(x['inputs_match'] for x in audit),'/',len(audit));print('fixed register mismatches',[(x['name'],v) for x in audit for v in x['fixed_register_checks'] if not v['equal']]);print('input differences',[(x['name'],x['native_inputs'],x['compiled_inputs']) for x in audit if not x['inputs_match']]);c.close()
