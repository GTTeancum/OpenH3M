"""Measure the current private simplified candidate at the three required views."""
import hashlib,json,os,shutil,subprocess,sys,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/video-options'))
from single_instance import acquire
acquire()
work=ROOT/'work/map-review-20261105'
stage=work/'powerhouse-cache-native-01'
is_baseline='--baseline' in sys.argv
candidate=work/('powerhouse-cache-order.map' if is_baseline else 'powerhouse-simplified.map')
metadata=(dict(sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),reduction_percent=0) if is_baseline
          else json.loads((work/'powerhouse-simplification.json').read_text()))
assert hashlib.sha256(candidate.read_bytes()).hexdigest()==metadata['sha256']
assert is_baseline or 15 <= metadata['reduction_percent'] <= 20
baseline=work/'powerhouse-cache-order.map'
target=stage/'game/maps/zanzibar.map'
assert hashlib.sha256(target.read_bytes()).digest()==hashlib.sha256(baseline.read_bytes()).digest()
config=stage/'bin/OpenH3M.toml';original=config.read_bytes()
settings=tomllib.loads(original.decode());assert settings.get('dxbc_switch',True)
label='powerhouse-reduction-baseline' if is_baseline else 'powerhouse-reduction-20'
out=ROOT/'.local/map-benchmarks'/label
out.mkdir(exist_ok=True)
shutil.copyfile(ROOT/'.local/map-benchmarks/powerhouse-current-load/points.txt',out/'points.txt')
args=json.loads((stage/'draw-cost-ready-lobby-launch.json').read_text())['args']
args[args.index('--seconds')+1]='210'
i=args.index('--capture-times-ms');del args[i:i+2];args.remove('--capture')
before=set((ROOT/'.local/loading-traces').iterdir())
try:
    config.write_bytes(original.decode().replace('\r\n','\n').replace('powerhouse-current-load/points.txt',label+'/points.txt').encode())
    assert tomllib.loads(config.read_text())['halo3mp_benchmark_seconds']==30
    shutil.copy2(candidate,target)
    env=dict(os.environ,TEMP=str(ROOT/'work/build-temp'),TMP=str(ROOT/'work/build-temp'))
    env.pop('OPENH3M_DRAW_GPU_DIR',None)
    with (stage/(label+'-runner.log')).open('w') as log:
        result=subprocess.run(args,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    traces=sorted(str(p) for p in set((ROOT/'.local/loading-traces').iterdir())-before)
    report=dict(args=args,traces=traces,exit=result.returncode,candidate_sha256=metadata['sha256'],reduction_percent=metadata['reduction_percent'])
    (work/(label+'-launch.json')).write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)
finally:
    config.write_bytes(original)
    shutil.copy2(baseline,target)
    assert hashlib.sha256(target.read_bytes()).digest()==hashlib.sha256(baseline.read_bytes()).digest()
    print('Private map and configuration restored',flush=True)
