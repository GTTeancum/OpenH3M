"""Three-view private trial of existing DXBC control-flow generation."""
import json, os, shutil, subprocess, sys, tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/video-options'))
from single_instance import acquire
acquire()
stage=ROOT/'work/map-review-20261105/powerhouse-cache-native-01'
config=stage/'bin/OpenH3M.toml'
original=config.read_bytes()
args=json.loads((stage/'draw-cost-ready-lobby-launch.json').read_text())['args']
args[args.index('--seconds')+1]='180'
args[args.index('--capture-times-ms')+1]='85000,120000,155000'
before=set((ROOT/'.local/loading-traces').iterdir())
evidence=ROOT/'.local/map-benchmarks/powerhouse-controlflow'
evidence.mkdir(exist_ok=True)
shutil.copyfile(ROOT/'.local/map-benchmarks/powerhouse-current-load/points.txt',evidence/'points.txt')
try:
    settings=original.decode().replace('\r\n','\n').replace('powerhouse-current-load/points.txt','powerhouse-controlflow/points.txt')+'\ndxbc_switch = false\n'
    config.write_bytes(settings.encode())
    assert tomllib.loads(config.read_text())['dxbc_switch'] is False
    env=dict(os.environ,TEMP=str(ROOT/'work/build-temp'),TMP=str(ROOT/'work/build-temp'))
    env.pop('OPENH3M_DRAW_GPU_DIR',None)
    with (stage/'shader-controlflow-runner.log').open('w') as log:
        result=subprocess.run(args,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    traces=sorted(str(p) for p in set((ROOT/'.local/loading-traces').iterdir())-before)
    report=dict(args=args,traces=traces,exit=result.returncode,setting='dxbc_switch=false',map_changed=False)
    (ROOT/'work/map-review-20261105/shader-controlflow-launch.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)
finally:
    config.write_bytes(original)
    print('Private configuration restored',flush=True)
