"""Prepare an isolated text-only run; --run requires the user's resumed-test instruction."""
import argparse,hashlib,json,os,shutil,subprocess,time
from pathlib import Path

def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');parser.add_argument('--async-occlusion',action='store_true');parser.add_argument('--warm-cache',action='store_true');parser.add_argument('--binary-manifest',type=Path,default=Path('work/sky-bridge/wait-attribution-build/after-hashes.json'));parser.add_argument('--run-name',default='performance-candidate29-01');args=parser.parse_args()
 if not __import__('re').fullmatch(r'performance-candidate29-[a-z0-9-]+',args.run_name):raise ValueError('Invalid run name')
 root=Path.cwd().resolve()
 assert root==Path('C:/X360/ISOs/H3M/.local/OpenH3M-source').resolve()
 run=root/'work/sky-bridge'/args.run_name;run.mkdir(exist_ok=True)
 for name in ('temp','profile','cache','game'):(run/name).mkdir(exist_ok=True)
 source=Path('C:/X360/ISOs/H3M/.local/custom-maps-play')
 game=run/'game'
 if not (run/'prepared.json').exists():
  for name in ('maps','bink','waves'):
   shutil.copytree(source/name,game/name,dirs_exist_ok=True,symlinks=False)
  for name in ('default.xex','WaveShell-Xbox.dll','WavesLibDLL.dll'):shutil.copyfile(source/name,game/name)
  payload=root/'work/sky-bridge/payload-29'
  content=run/'user/0000000000000000/4D5307E6/00000002/SkyBridge';content.mkdir(parents=True,exist_ok=True)
  for p in payload.iterdir():shutil.copyfile(p,content/p.name)
  (run/'prepared.json').write_text(json.dumps(dict(game=str(game),payload_sha256=digest(content/'sky_bridge.map'),cache='fresh private cache; cold run'),indent=2))
 cache=(root/'work/sky-bridge/performance-candidate29-01/cache') if args.warm_cache else run/'cache'
 manifest=args.binary_manifest.resolve();manifest.relative_to(root)
 expected=json.loads(manifest.read_text())
 bindir=root/'work/rexglue-sdk/out/win-amd64'
 for name,value in expected.items():
  if digest(bindir/name)!=value:raise ValueError('Timing binary changed: '+name)
 old=json.loads((root/'work/sky-bridge/performance-baseline-01/launch.json').read_text())['command']
 steps=next(x for x in old if x.startswith('--input_script='))
 cmd=[str(bindir/'halo3mp.exe'),f'--game_data_root={game}',f'--user_data_root={run/"user"}',
      f'--cache_root={cache}',f'--log_file={run/"runtime.log"}','--log_level=info',
      '--log_max_file_size_mb=20','--log_max_files=6','--d3d12_log_present_timing=true',
      '--d3d12_present_timing_end_ms=165000','--d3d12_async_occlusion_readback='+str(args.async_occlusion).lower(),
      steps,'--input_script_button_state=true','--input_script_keystrokes=false']
 assert not any('capture' in arg for arg in cmd)
 (run/'prepared-command.json').write_text(json.dumps(dict(command=cmd,binary_hashes=expected,cache_reused=args.warm_cache,
  controls='Process-local menu input only. No captures. 170-second watchdog, then terminate/kill.'),indent=2))
 if not args.run:
  print('Prepared only; no process launched.');return
 if (run/'launch.json').exists():raise ValueError('Run already exists; do not overwrite evidence')
 prepared=json.loads((run/'prepared.json').read_text())
 installed=run/'user/0000000000000000/4D5307E6/00000002/SkyBridge/sky_bridge.map'
 if digest(installed)!=prepared['payload_sha256']:raise ValueError('Prepared payload changed')
 check=subprocess.run(['powershell','-NoProfile','-Command',
  "if (Get-Process halo3mp -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }"],
  cwd=root,creationflags=subprocess.CREATE_NO_WINDOW,timeout=15)
 if check.returncode:raise ValueError('Existing game process detected; no launch')
 env=dict(os.environ,TEMP=str(run/'temp'),TMP=str(run/'temp'),LOCALAPPDATA=str(run/'profile'),APPDATA=str(run/'profile'))
 startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
 started=time.monotonic()
 with (run/'console.log').open('wb') as log:
  process=subprocess.Popen(cmd,cwd=root,env=env,stdout=log,stderr=log,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW)
  (run/'launch.json').write_text(json.dumps(dict(pid=process.pid,command=cmd,binary_hashes=expected),indent=2))
  try:
   process.wait(timeout=170)
  except subprocess.TimeoutExpired:
   pass  # Expected watchdog expiry; cleanup below still enforces the limit.
  finally:
   if process.poll() is None:
    process.terminate()
    try:process.wait(timeout=5)
    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
   (run/'completion.json').write_text(json.dumps(dict(exit_code=process.returncode,seconds=time.monotonic()-started),indent=2))
 print('Bounded run ended',process.returncode)

if __name__=='__main__':main()
