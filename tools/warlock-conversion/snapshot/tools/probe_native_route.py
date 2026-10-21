"""Short native menu-route probe; process-local input, no host input/capture."""
import argparse, csv, hashlib, json, os, subprocess, time
from pathlib import Path
from build_scenario_checkpoint import output_path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--project',type=Path,required=True)
p.add_argument('--exe',type=Path,required=True)
p.add_argument('--script',required=True)
p.add_argument('--captures',default='40000,52000')
p.add_argument('--seconds',type=int,default=60)
p.add_argument('--no-vsync',action='store_true')
a=p.parse_args()
root=a.project.resolve(strict=True)
if not 1 <= a.seconds <= 180: p.error('Watchdog must be 1-180 seconds')
if any(not 0<int(t)<a.seconds*1000 for t in a.captures.split(',')): p.error('Captures must precede watchdog')
exe=a.exe.resolve(strict=True)
if hashlib.sha256(exe.read_bytes()).hexdigest()!='ec4d57ee4f654095bd5e512ffe650d65ac514b0fb8f21d5c7b09e61e689c3406': raise SystemExit('Unexpected runtime')
listing=subprocess.run(['tasklist','/FI','IMAGENAME eq OpenH3M.exe','/FO','CSV','/NH'],capture_output=True,text=True,check=True)
if any(r and r[0].lower()=='openh3m.exe' for r in csv.reader(listing.stdout.splitlines())): raise SystemExit('Game already running')
repository=Path(__file__).resolve().parents[4]
run=output_path(repository/'.local/native-probes'/ (time.strftime('%Y%m%d-%H%M%S')+'-route-probe'),repository)
for name in ('temp','profile'): (run/name).mkdir(parents=True)
env=dict(os.environ,TEMP=str(run/'temp'),TMP=str(run/'temp'),APPDATA=str(run/'profile'),LOCALAPPDATA=str(run/'profile'))
cmd=[str(exe),f'--game_data_root={root / ".local/custom-maps-play"}',f'--user_data_root={run}',f'--cache_root={root / ".local/custom-maps-play/cache"}',f'--log_file={run / "runtime.log"}','--keyboard_controller=false',f'--input_script={a.script}','--input_script_button_state=true','--input_script_keystrokes=false',f'--halo3mp_capture_guest_output_times_ms={a.captures}',f'--halo3mp_capture_guest_output_path={run / "native.png"}']
if a.no_vsync: cmd+=['--vsync=false']
print(run,flush=True)
with (run/'console.log').open('wb') as out:
 child=subprocess.Popen(cmd,cwd=run,env=env,stdout=out,stderr=out,creationflags=subprocess.CREATE_NO_WINDOW)
 (run/'run.json').write_text(json.dumps({'command':cmd,'pid':child.pid,'watchdog_seconds':a.seconds},indent=2))
 try: child.wait(timeout=a.seconds)
 except subprocess.TimeoutExpired: pass
 finally:
  if child.poll() is None: child.kill(); child.wait(timeout=10)
