"""Isolated application-native video validation. No desktop input/capture."""
import argparse,hashlib,json,os,shutil,subprocess,sys,time
from single_instance import acquire,ensure_no_game
acquire()
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from script_input_replay import encode
p=argparse.ArgumentParser();p.add_argument('cases',nargs='+');p.add_argument('--suffix',default='');a=p.parse_args()
BASE=ROOT/'work/video-options/validation-20261105';BASE.mkdir(exist_ok=True)
source=ROOT/'work/rexglue-sdk/out/win-amd64'
cases={
 'surface':('beach-fixture-objects',{},[(-1,0)]+[(i,j) for i,n in [(2,3),(3,6),(5,3)] for j in range(n)]+[(-1,0)]),
 'shadows':('shadow-fixture',{},[(4,j) for j in [0,1,2,0]]+[(-2,j) for j in range(3)]+[(-3,0)]),
 'water':('water-fixture',{},[(8,j) for j in [0,1,2,0]]+[(1,j) for j in [1,0]]),
 'distance':('distance-fixture',{},[(i,j) for i in [6,7] for j in [0,1,2,0]]),
 'water-witness':('water-fixture',{},[(8,j) for j in [0,1,2,0]]),
 'pause':('beach-fixture-objects',{},[(-1,0)]*6),
 'effects-curve':('distance-fixture',{},[(7,j) for j in [0,1,2,0]])}
for name,res in [('default',''),('720','720p'),('1080','1080p'),('1440','1440p'),('2160','4k')]:cases['res-'+name]=('beach-fixture-objects',{'resolution':res},[(-1,0)])
for scale in [2,3]:cases['scale-'+str(scale)]=('beach-fixture-objects',{'resolution_scale':scale,'draw_resolution_scale_x':scale,'draw_resolution_scale_y':scale},[(-1,0)])
for mode in ['fxaa','fxaa_extreme']:cases[mode]=('beach-fixture-objects',{'swap_post_effect':mode},[(-1,0)])
for name in a.cases:
 ensure_no_game()
 fixture,settings,actions=cases[name];run=BASE/(name+a.suffix);run.mkdir(exist_ok=False);binary=run/'bin';binary.mkdir()
 for f in ['halo3mp.exe','rexruntime.dll','rexgpu-xenos.dll','halo3mp_l360.dll','halo3mp_q10.dll','halo3mp_waveshell-xbox.dll','halo3mp_waveslibdll.dll']:shutil.copy2(source/f,binary/f)
 for d in ['temp','profile','cache']:(run/d).mkdir()
 config={'resolution':'720p','resolution_scale':1,'draw_resolution_scale_x':1,'draw_resolution_scale_y':1,'swap_post_effect':'none','fullscreen':False,**settings}
 (binary/'OpenH3M.toml').write_text(''.join(k+' = '+json.dumps(v)+'\n' for k,v in config.items()))
 steps=['45000:DOWN+220','46000:A+250','55000:UP+220','56000:A+250','70000:A+250','72000:A+250','74000:DOWN+220','95000:A+250']
 if name=='shadows':steps+=['108000:RSDOWN+400']
 if name=='water':steps+=['108000:RSDOWN+250']+[f'{128000+i*9000}:RT+1000' for i in range(len(actions))]+[f'{132000+i*18000}:X+200' for i in range(3)]
 if name=='water-witness':steps+=['108000:RSDOWN+650']+[f'{129700+i*9000}:RT+150' for i in range(len(actions))]
 if name=='distance':steps+=['108000:RSDOWN+180']+[f'{129700+i*9000}:RT+150' for i in range(len(actions))]
 if name=='effects-curve':steps+=['108000:RSDOWN+180']+[f'{129700+i*9000}:RT+150' for i in range(len(actions))]
 times=[130000+i*9000 for i in range(len(actions))]
 if name=='pause':
  steps+=['110000:START+100','114000:RIGHT+100','117000:DOWN+100','118000:DOWN+100','119000:DOWN+100','121000:A+100','132000:B+100','134000:B+100','137000:LSUP+900','140000:RT+150']
  times=[112000,115000,123000,131000,136000,142000]
 script=run/'validation.tsv';script.write_text(''.join(f'{t} {i} {j}\n' for t,(i,j) in zip(times,actions)))
 (run/'input.h3ir').write_bytes(encode(steps))
 args=[str(binary/'halo3mp.exe'),f'--game_data_root={ROOT/"work/video-options/remaining"/fixture}',f'--user_data_root={run/"profile"}',f'--cache_root={run/"cache"}',f'--log_file={run/"runtime.log"}','--log_level=info','--log_max_file_size_mb=100','--log_max_files=2','--keyboard_controller=false',f'--input_state_replay={run/"input.h3ir"}','--show_settings_on_startup=false',f'--halo3mp_video_validation={script}',f'--halo3mp_capture_guest_output_path={run/"scene.png"}','--halo3mp_capture_guest_output_times_ms='+','.join(map(str,times)),f'--d3d12_host_capture_path={run/"output.bmp"}','--d3d12_host_capture_after_ms=125000','--host_guest_output_fps=30','--host_present_from_non_ui_thread=false','--d3d12_host_sync_interval=1','--d3d12_host_waitable_presentation=true','--d3d12_host_maximum_frame_latency=2','--host_output_display_phase=true']
 env=os.environ.copy();env.update(TEMP=str(run/'temp'),TMP=str(run/'temp'),APPDATA=str(run/'profile'),LOCALAPPDATA=str(run/'profile'))
 record=dict(name=name,args=args,actions=actions,settings=settings,steps=steps,exe_sha256=hashlib.sha256((binary/'halo3mp.exe').read_bytes()).hexdigest())
 (run/'launch.json').write_text(json.dumps(record,indent=2));print('START',name,flush=True)
 with (run/'stdout.log').open('w') as out:
  child=subprocess.Popen(args,cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT)
  (run/'pid.txt').write_text(str(child.pid))
  try:child.wait(timeout=times[-1]/1000+15);record['watchdog']=False
  except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10);record['watchdog']=True
 record['exit_code']=child.returncode
 (run/'result.json').write_text(json.dumps(record,indent=2));print('END',name,child.returncode,'watchdog',record['watchdog'],flush=True)
