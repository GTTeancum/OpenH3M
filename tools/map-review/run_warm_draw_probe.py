"""Private, bounded native capture with ten seconds of settled benchmark view."""
import json, os, shutil, subprocess, sys, time, tomllib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/video-options'))
from single_instance import acquire
acquire()
stage = ROOT / 'work/map-review-20261105/powerhouse-cache-native-01'
out = ROOT / '.local/map-benchmarks/powerhouse-draw-cost-warm'
out.mkdir(exist_ok=True)
assert not (out/'draw-gpu.csv').exists(), 'Preserve existing evidence'
traces = ROOT / '.local/loading-traces'
before = set(traces.iterdir())
config = stage/'bin/OpenH3M.toml'
original = config.read_bytes()
args = json.loads((stage/'draw-cost-ready-lobby-launch.json').read_text())['args']
env = dict(os.environ, OPENH3M_DRAW_GPU_DIR=str(out), TEMP=str(ROOT/'work/build-temp'), TMP=str(ROOT/'work/build-temp'))
try:
    candidate = original.decode().replace('\r\n','\n').replace('powerhouse-current-load/points.txt','powerhouse-shadow-cost/points.txt').replace('halo3mp_benchmark_seconds = 30','halo3mp_benchmark_seconds = 60')
    config.write_bytes(candidate.encode())
    assert tomllib.loads(config.read_text())['halo3mp_benchmark_seconds'] == 60
    shutil.copy2(ROOT/'work/rexglue-sdk/out/win-amd64/rexgpu-xenos.dll', stage/'bin/rexgpu-xenos.dll')
    with (stage/'draw-cost-warm-runner.log').open('w') as log:
        p = subprocess.Popen(args, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        first = None
        trace = None
        while p.poll() is None:
            if trace is None:
                found = set(traces.iterdir())-before
                if found:
                    trace = max(found, key=lambda x:x.stat().st_mtime)
                    print('Trace:', trace, flush=True)
            if trace:
                runtime = trace/'trace-runtime.log'
                if first is None and runtime.exists() and '[map-benchmark] view map=zanzibar point=1' in runtime.read_text(errors='replace'):
                    first = time.monotonic()
                    print('Native benchmark view ready; settling ten seconds', flush=True)
                if first is not None and time.monotonic()-first >= 10 and not (out/'arm').exists():
                    (out/'arm').write_text('Settled native view for ten seconds\n')
                    print('GPU trace armed', flush=True)
            time.sleep(1)
        print('Runner exit:',p.returncode, flush=True)
finally:
    config.write_bytes(original)
    shutil.copy2(Path('C:/X360/ISOs/H3M/rexgpu-xenos.dll'),stage/'bin/rexgpu-xenos.dll')
    print('Private runtime and configuration restored',flush=True)
