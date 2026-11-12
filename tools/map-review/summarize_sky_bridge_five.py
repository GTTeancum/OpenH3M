"""Join five native uncapped measurements with concurrent GPU counter samples."""
import datetime,hashlib,json,re,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
out=ROOT/'.local/map-benchmarks/sky-bridge-five-20261111-ready'
runs=json.loads((out/'runs.json').read_text());assert len(runs)==2
rows=[]
for run in runs:
    trace=Path(run['traces'][0]);assert trace.is_relative_to(ROOT)
    paths=sorted(trace.glob('trace-runtime.*.log'),key=lambda x:int(x.name.split('.')[-2]),reverse=True)+[trace/'trace-runtime.log']
    text='\n'.join(p.read_text(errors='replace') for p in paths)
    command=json.loads((trace/'launch-command.json').read_text());assert '--fpsunlock' in command
    assert 'Developer FPS unlock command line: true' in text
    folder=out/f"batch-{run['batch']}"
    samples=[json.loads(line) for line in (folder/'gpu-usage.jsonl').read_text().splitlines()]
    pattern=r'^\[([^\]]+)\].*?\[map-benchmark\] RESULT map=sky_bridge point=(\d+) frames=(\d+) seconds=([\d.]+) fps=([\d.]+) valid=(\w+) camera=([^\r\n]+)'
    found=list(re.finditer(pattern,text,re.M));assert len(found)==run['points']
    for match in found:
        stamp,point,frames,seconds,fps,valid,camera=match.groups();assert valid=='true'
        end=datetime.datetime.fromisoformat(stamp).timestamp();start=end-float(seconds)
        usage=[];processes={}
        for sample in samples:
            if sample['returncode']!=0:continue
            when=datetime.datetime.fromisoformat(sample['sample']['utc'].replace('Z','+00:00')).timestamp()
            if not start<=when<=end:continue
            engines=[x for x in sample['sample']['engines'] if x['instance'].lower().endswith('engtype_3d')]
            usage.append(sum(x['percent'] for x in engines))
            for x in engines:processes.setdefault(x['process'] or str(x['process_id']),[]).append(x['percent'])
        image=folder/f'spawn-{point}.png';assert image.is_file()
        rows.append(dict(point=run['first_point']+int(point)-1,fps=float(fps),frames=int(frames),seconds=float(seconds),camera=camera,
            screenshot=str(image),screenshot_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),trace=str(trace),
            gpu_3d_percent_mean=statistics.mean(usage) if usage else None,gpu_samples=len(usage),
            gpu_process_active_sample_means={k:statistics.mean(v) for k,v in processes.items()}))
assert [x['point'] for x in rows]==[1,2,3,4,5]
report=dict(map='Sky Bridge',map_sha256=json.loads((out/'locations.json').read_text())['map_sha256'],points=rows,
    method='Five distinct points;30seconds each; --fpsunlock; unchanged timing and original private720p settings. One game instance at a time. Native captures precede sample windows.',
    limits='GPU usage is sampled Windows3D-engine utilization during each window, including other applications. No isolated-load or Xbox360 performance claim. Visual classification must be completed separately.')
(out/'results.json').write_text(json.dumps(report,indent=2))
print(json.dumps(rows,indent=2))
