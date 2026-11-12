"""Exercise every native video spinner via process-local controller replay."""
from pathlib import Path
import sys,json,shutil,os,subprocess,argparse
from single_instance import acquire
acquire()
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from script_input_replay import encode
parser=argparse.ArgumentParser();parser.add_argument('--resolution-check',action='store_true');args_cli=parser.parse_args()
run=ROOT/('work/video-options/validation-20261105/menu-resolution-final' if args_cli.resolution_check else 'work/video-options/validation-20261105/menu-values');run.mkdir(exist_ok=False);binary=run/'bin';binary.mkdir()
source=ROOT/'work/rexglue-sdk/out/win-amd64'
for f in ['halo3mp.exe','rexruntime.dll','rexgpu-xenos.dll','halo3mp_l360.dll','halo3mp_q10.dll','halo3mp_waveshell-xbox.dll','halo3mp_waveslibdll.dll']:shutil.copy2(source/f,binary/f)
for d in ['temp','profile','cache']:(run/d).mkdir()
steps=['45000:START+100','47500:RIGHT+100','50000:DOWN+100','51500:DOWN+100','53000:DOWN+100','55000:A+100']
t=58000;captures=[];expected=[]
# Native brightness, preset, then the 11 PC options. Cancel leaves each baseline intact.
rows=[('brightness',5,2),('preset',3,2),('resolution',5,0),('fullscreen',2,0),('textures',3,0),('filtering',6,3),('shadows',3,0),('objects',3,0),('decorations',3,0),('effects',3,0),('water',3,0),('aa',3,0),('scale',3,0)]
for row,(name,count,initial) in enumerate(rows):
 steps.append(f'{t}:A+100');t+=700
 for _ in range(initial):steps.append(f'{t}:LEFT+100');t+=350
 for choice in range(count):
  captures.append(t+800);expected.append(dict(time=t+800,row=row,name=name,choice=choice))
  t+=1800
  if choice<count-1:steps.append(f'{t}:RIGHT+100');t+=700
 steps.append(f'{t}:B+100');t+=700;steps.append(f'{t}:DOWN+100');t+=700
# Sidebar is now Apply. Navigate back to display mode, choose fullscreen, Apply,
# return to Windowed and Apply again. These writes come from the actual menu.
for _ in range(10):steps.append(f'{t}:UP+100');t+=350
steps += [f'{t}:A+100',f'{t+800}:RIGHT+100',f'{t+1600}:A+100'];t+=2400
for _ in range(10):steps.append(f'{t}:DOWN+100');t+=350
steps.append(f'{t}:A+100');t+=3500;captures.append(t);expected.append(dict(time=t,name='applied-fullscreen'));t+=1500
for _ in range(10):steps.append(f'{t}:UP+100');t+=350
steps += [f'{t}:A+100',f'{t+800}:LEFT+100',f'{t+1600}:A+100'];t+=2400
for _ in range(10):steps.append(f'{t}:DOWN+100');t+=350
steps.append(f'{t}:A+100');t+=3500;captures.append(t);expected.append(dict(time=t,name='restored-windowed'))
if args_cli.resolution_check:
 # Focus resolution help, then apply fullscreen and return using the actual menu.
 (binary/'OpenH3M.toml').write_text('resolution = "4k"\n')
 steps=['45000:START+100','47500:RIGHT+100','50000:DOWN+100','51500:DOWN+100','53000:DOWN+100','55000:A+100','58000:DOWN+100','59000:DOWN+100','61000:A+100','65000:B+100','67000:DOWN+100','68000:A+100','69000:RIGHT+100','70000:A+100']
 for n in range(10):steps.append(f'{72000+n*350}:DOWN+100')
 steps.append('77000:A+100')
 for n in range(10):steps.append(f'{83000+n*350}:UP+100')
 steps+=['88000:A+100','89000:LEFT+100','90000:A+100']
 for n in range(10):steps.append(f'{92000+n*350}:DOWN+100')
 steps.append('97000:A+100')
 captures=[63000,81000,101000];t=101000
 expected=[dict(time=at,name=name) for at,name in zip(captures,['resolution-help','fullscreen','windowed-fit'])]
(run/'input.h3ir').write_bytes(encode(steps));(run/'expected.json').write_text(json.dumps(expected,indent=2))
validation=run/'validation.tsv';validation.write_text(''.join(f'{at} -1 0\n' for at in captures))
args=[str(binary/'halo3mp.exe'),'--game_data_root=C:/X360/ISOs/H3M',f'--user_data_root={run/"profile"}',f'--cache_root={run/"cache"}',f'--log_file={run/"runtime.log"}','--log_level=info','--log_max_file_size_mb=100','--log_max_files=2','--keyboard_controller=false',f'--input_state_replay={run/"input.h3ir"}','--show_settings_on_startup=false',f'--halo3mp_video_validation={validation}',f'--halo3mp_capture_guest_output_path={run/"menu.png"}','--halo3mp_capture_guest_output_times_ms='+','.join(map(str,captures)),'--host_guest_output_fps=30']
env=os.environ.copy();env.update(TEMP=str(run/'temp'),TMP=str(run/'temp'),APPDATA=str(run/'profile'),LOCALAPPDATA=str(run/'profile'))
(run/'launch.json').write_text(json.dumps(dict(args=args,steps=steps),indent=2))
print('START menu-values',len(captures),'captures',t/1000,'seconds',flush=True)
with (run/'stdout.log').open('w') as out:
 child=subprocess.Popen(args,cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT)
 try:child.wait(timeout=t/1000+15);watchdog=False
 except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10);watchdog=True
(run/'result.json').write_text(json.dumps(dict(exit_code=child.returncode,watchdog=watchdog)));print('END menu-values',child.returncode,watchdog,flush=True)
