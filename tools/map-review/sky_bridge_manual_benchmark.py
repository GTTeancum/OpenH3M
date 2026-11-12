"""User-controlled map launch; native benchmark and read-only GPU sampling."""
import json, os, subprocess, sys, time, tomllib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/video-options'))
from single_instance import acquire
acquire()
second = '--second' in sys.argv
out = ROOT / ('.local/map-benchmarks/sky-bridge-manual-20261111-second' if second else '.local/map-benchmarks/sky-bridge-manual-20261111')
out.mkdir(exist_ok=False)
points = json.loads((ROOT / '.local/map-benchmarks/sky-bridge-five-20261111-final/locations.json').read_text())['points']
(out / 'all-five-points.json').write_text(json.dumps(points))
selected = points[:3]
if second:
    # First authored start is above the floor: measured settled camera Z=.18719625,
    # standing eye height=.612. Retry the same X/Y/yaw at the actual floor height.
    retry = list(points[0]); retry[2] = .18719625 - .612
    selected = [retry] + points[3:]
(out / 'points.txt').write_text(''.join(' '.join(map(str,p))+'\n' for p in selected))
settings = tomllib.loads(Path('C:/X360/ISOs/H3M/OpenH3M.bootstrap.toml').read_text())
settings.update(log_file=str(out/'runtime.log'), log_max_file_size_mb=50,
    halo3mp_benchmark_map='sky_bridge', halo3mp_benchmark_points=str(out/'points.txt'),
    halo3mp_benchmark_seconds=30, input_script='', input_state_replay='',
    halo3mp_log_fps=True)
command = ['C:/X360/ISOs/H3M/OpenH3M.exe', '--fpsunlock'] + [f'--{k}={str(v).lower() if isinstance(v,bool) else v}' for k,v in settings.items()]
env = dict(os.environ, TEMP=str(ROOT/'work/build-temp'), TMP=str(ROOT/'work/build-temp'))
with (out/'console.log').open('w') as console:
    game = subprocess.Popen(command,cwd=ROOT,env=env,stdout=console,stderr=console)
(out/'launch.json').write_text(json.dumps(dict(pid=game.pid,command=command),indent=2))
print(f'Launched one user-controlled instance: {game.pid}',flush=True)
with (out/'gpu-usage.jsonl').open('w') as log:
    while game.poll() is None:
        sample = subprocess.run(['powershell','-NoProfile','-Command',(ROOT/'tools/map-review/sample_gpu_usage.ps1').read_text()],cwd=ROOT,env=env,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
        log.write(json.dumps(dict(wall_time=time.time(),sample=sample.stdout.strip()))+'\n');log.flush()
        if (out/'runtime.log').exists() and '[map-benchmark] COMPLETE map=sky_bridge' in (out/'runtime.log').read_text(errors='replace'):
            print('Three points complete; game left open.',flush=True)
            break
        time.sleep(7)
