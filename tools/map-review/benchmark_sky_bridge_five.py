"""Five Sky Bridge views in two sequential native benchmark runs; no OS input."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/video-options'))
from single_instance import acquire,ensure_no_game
from benchmark_maps import spawn_points
acquire()
stage=ROOT/'work/map-review-20261105/sky-weather-native-02'
installed=next((ROOT/'work/dlc/installed-corrections').rglob('sky_bridge.map'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(installed)==sha(stage/'payload/sky_bridge.map')
assert sha(stage/'bin/OpenH3M.exe')==sha(Path('C:/X360/ISOs/H3M/OpenH3M.exe'))
out=ROOT/'.local/map-benchmarks/sky-bridge-five-20261111-final'
out.mkdir(exist_ok=True)
if (out/'runs.json').exists():
    assert all(not x['traces'] for x in json.loads((out/'runs.json').read_text())), 'Existing runtime evidence; do not overwrite'
selected,_=spawn_points(installed)
extra=[[16.4107,79.9909,-.414,1.3337],[16.4107,67.9909,-.414,1.3337]]
points=[list(p['position'])+[p['yaw']] for p in selected]+extra
(out/'locations.json').write_text(json.dumps(dict(points=points,map_sha256=sha(installed),seconds_per_point=30,scope='First3spatially separated authored starts plus2previously validated weather-review positions. Indoor/outdoor labels require native image inspection.'),indent=2))
config=stage/'bin/OpenH3M.toml';original=config.read_bytes()
env=dict(os.environ,TEMP=str(ROOT/'work/build-temp'),TMP=str(ROOT/'work/build-temp'))
base=json.loads((stage/'launch.json').read_text())['args']
base[base.index('--seconds')+1]='240'
i=base.index('--capture-times-ms');del base[i:i+2];base.remove('--capture')
base+=['--fpsunlock','--menu-press-ms','50','--menu-delay-ms','10000','--capture','--capture-times-ms','80000']
runs=[]
try:
    for batch,group in enumerate([points[:3],points[3:]],1):
        ensure_no_game()
        folder=out/f'batch-{batch}';folder.mkdir(exist_ok=True)
        pointfile=folder/'points.txt';pointfile.write_text(''.join(' '.join(map(str,p))+'\n' for p in group))
        text=original.decode().replace('\r\n','\n').replace('halo3mp_benchmark_seconds = 5','halo3mp_benchmark_seconds = 30')
        text=text.replace('C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/map-benchmarks/sky-weather-review-02/points.txt',pointfile.as_posix())
        config.write_bytes(text.encode())
        before=set((ROOT/'.local/loading-traces').iterdir())
        print(f'Starting batch{batch}, {len(group)}points',flush=True)
        with (folder/'runner.log').open('w') as log,(folder/'gpu-usage.jsonl').open('w') as gpu:
            process=subprocess.Popen(base,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            while process.poll() is None:
                sample=subprocess.run(['powershell','-NoProfile','-Command',(ROOT/'tools/map-review/sample_gpu_usage.ps1').read_text()],cwd=ROOT,env=env,capture_output=True,text=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
                gpu.write(json.dumps(dict(wall_time=time.time(),returncode=sample.returncode,sample=json.loads(sample.stdout) if sample.returncode==0 and sample.stdout.strip() else sample.stderr.strip()))+'\n');gpu.flush()
                time.sleep(7)
        traces=sorted(str(p) for p in set((ROOT/'.local/loading-traces').iterdir())-before)
        row=dict(batch=batch,first_point=1 if batch==1 else 4,points=len(group),traces=traces,runner_exit=process.returncode,args=base)
        runs.append(row);(out/'runs.json').write_text(json.dumps(runs,indent=2));print(json.dumps(row),flush=True)
        assert len(traces)==1
        logs='\n'.join(p.read_text(errors='replace') for p in Path(traces[0]).glob('trace-runtime*.log'))
        if '[map-benchmark] COMPLETE map=sky_bridge' not in logs:
            raise RuntimeError('Batch did not finish all native points; inspect before continuing')
finally:
    config.write_bytes(original)
    print('Private configuration restored',flush=True)
