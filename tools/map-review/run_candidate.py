"""Run one private map candidate using process-local replay and native captures."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/video-options'))
from single_instance import acquire
p=argparse.ArgumentParser();p.add_argument('map');p.add_argument('--name',required=True);p.add_argument('--input',default='');p.add_argument('--captures',default='120000,130000');p.add_argument('--seconds',default='150');p.add_argument('--points',type=Path);p.add_argument('--point-seconds',type=int,default=5);p.add_argument('--sample-objects',action='store_true');p.add_argument('--shader-cache-seed',type=Path);p.add_argument('--fpsunlock',action='store_true');p.add_argument('--timing-diagnostics',action='store_true');p.add_argument('--resolution',default='720p',choices=['480p','720p']);p.add_argument('--expanded-object-samples',action='store_true');a=p.parse_args()
if not 5 <= a.point_seconds <= 60:p.error('--point-seconds must be 5–60')
acquire()
entries={'chiron':('chillout','chiron-06.map'),'rodentia':('zanzibar','rodentia-original-lighting-dlc.map'),'resuscitation':('zanzibar','resuscitation-07.map'),'elongation':('zanzibar','../elongation/zanzibar-06.map'),'sky_bridge':('zanzibar','sky-bridge-no-rain-flash.map')}
# Experimental brightness candidates retired: preserve original Rodentia source lighting.
entries['powerhouse-cache']=('zanzibar','powerhouse-cache-order.map')
entries['powerhouse']=('zanzibar','../powerhouse/zanzibar-139.map')
entries['elongation-clearance']=('zanzibar','elongation-support-clearance-control.map')
entries['elongation-gear']=('zanzibar','elongation-gear-control.map')
entries['elongation-local-physics']=('zanzibar','elongation-local-physics-control.map')
entries['elongation-linear']=('zanzibar','elongation-linear-control.map')
entries['elongation-platform']=('zanzibar','elongation-platform-control.map')
slot,file=entries[a.map];installed=Path('C:/X360/ISOs/H3M');run=ROOT/'work/map-review-20261105'/a.name;run.mkdir(exist_ok=False)
dlc = a.map in ('sky_bridge','rodentia')
game=run/'game';(game/'maps').mkdir(parents=True);binary=run/'bin';binary.mkdir()
for folder in ['maps','bink','waves']:
 for src in (installed/folder).rglob('*'):
  if not src.is_file():continue
  dest=game/src.relative_to(installed);dest.parent.mkdir(parents=True,exist_ok=True)
  if not dlc and folder=='maps' and src.name==slot+'.map':shutil.copy2(ROOT/'work/map-review-20261105'/file,dest)
  else:os.link(src,dest)
for name in ['default.xex','WaveShell-Xbox.dll','WavesLibDLL.dll']:os.link(installed/name,game/name)
for name in ['OpenH3M.exe','rexruntime.dll','rexgpu-xenos.dll','halo3mp_l360.dll','halo3mp_q10.dll','halo3mp_waveshell-xbox.dll','halo3mp_waveslibdll.dll']:shutil.copy2(installed/name,binary/name)
(binary/'OpenH3M.toml').write_text('resolution = "720p"\nfullscreen = false\nhost_guest_output_fps = 30\nhost_present_from_non_ui_thread = false\nd3d12_host_sync_interval = 1\nd3d12_host_waitable_presentation = true\nd3d12_host_maximum_frame_latency = 2\nhost_output_display_phase = true\n')
if a.resolution != '720p':
 config=binary/'OpenH3M.toml'
 config.write_text(config.read_text().replace('resolution = "720p"',f'resolution = "{a.resolution}"'))
if a.points:
 points=a.points.resolve()
 assert points.is_relative_to(ROOT/'.local/map-benchmarks') and points.is_file()
 with (binary/'OpenH3M.toml').open('a') as config:
  config.write(f'halo3mp_benchmark_map = "{a.map if dlc else slot}"\nhalo3mp_benchmark_points = "{points.as_posix()}"\nhalo3mp_benchmark_seconds = {a.point_seconds}\n')
exe=binary/'OpenH3M.exe';digest=hashlib.sha256(exe.read_bytes()).hexdigest()
args=[sys.executable,'-B',str(ROOT/'tools/warlock-conversion/snapshot/tools/trace_loading.py'),'--project',str(installed),'--exe',str(exe),'--expected-exe-sha256',digest,'--game',str(game),'--slot',slot,'--seconds',a.seconds,'--capture','--capture-times-ms',a.captures,'--exclusive-input','--quiet-timing','--sample-observer']
if a.input:args+=['--inspection-input',a.input]
if a.fpsunlock:args+=['--fpsunlock']
if a.fpsunlock or a.timing_diagnostics:args+=['--timing-diagnostics']
if a.sample_objects:args+=['--sample-object-map',str(game/'maps'/(slot+'.map')),'--sample-player-objects']
if a.expanded_object_samples:
 assert a.sample_objects
 args+=['--sample-object-body-bytes','1024','--sample-object-interval','1']
if a.shader_cache_seed:
 seed=a.shader_cache_seed.resolve()
 assert seed.is_relative_to(ROOT) and seed.is_dir()
 args+=['--shader-cache-seed',str(seed)]
if dlc:
 targets=list((ROOT/'work/dlc/installed-corrections').rglob(a.map+'.map'));assert len(targets)==1
 payload=run/'payload';payload.mkdir()
 for src in targets[0].parent.iterdir():
  if src.name==a.map+'.map':shutil.copy2(ROOT/'work/map-review-20261105'/file,payload/src.name)
  elif src.is_file() and (src.name==a.map+'.mapinfo' or src.name.startswith('dlc_'+a.map)):os.link(src,payload/src.name)
 args+=['--dlc-payload',str(payload),'--dlc-map',a.map]
(run/'launch.json').write_text(json.dumps({'args':args,'candidate':file},indent=2))
with (run/'runner.log').open('w') as log:
 result=subprocess.run(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
print(a.name,'exit',result.returncode,flush=True)
sys.exit(result.returncode)
