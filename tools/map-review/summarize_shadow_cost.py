"""Measure GPU frames within the existing process-local shadow diagnostic phases."""
import collections
import datetime
import json
import re
import statistics
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
run = Path(sys.argv[1]).resolve()
assert run.is_relative_to(root)
paths = sorted(run.glob('trace-runtime.*.log'), key=lambda p: int(p.name.split('.')[-2]), reverse=True)
paths += [run / 'trace-runtime.log']
gpu = collections.defaultdict(float)
closed = {}
phases = []
observations = []
for path in paths:
    for line in path.open(errors='replace'):
        if not any(k in line for k in ('[gpu-execution]', '[video-shadow-probe]', '[video-visual] observed=', '[video-visual-render]')):
            continue
        stamp = datetime.datetime.fromisoformat(line[1:24]).timestamp()
        values = dict(re.findall(r'([\w]+)=([^ ]+)', line.strip()))
        if '[gpu-execution]' in line:
            frame = int(values['frame'])
            gpu[frame] += float(values['elapsed_ms'])
            if values['closes_frame'] == 'true':
                closed[frame] = stamp
        elif '[video-shadow-probe]' in line:
            phases.append(dict(phase=int(values['phase']), start=stamp, disabled=values['diagnostic_shadows_disabled']=='true'))
        else:
            observations.append(dict(time=stamp, values=values))
assert [p['phase'] for p in phases] == list(range(7)), 'Incomplete diagnostic sweep'
for index, phase in enumerate(phases):
    end = phases[index+1]['start'] if index+1<len(phases) else phase['start']+10
    selected = [f for f,t in closed.items() if phase['start']+3<t<end-0.25]
    selected.sort(key=closed.get)
    values = [gpu[f] for f in selected]
    phase.update(samples=len(values), gpu_mean_ms=statistics.mean(values) if values else None,
                 observed_fps=(len(selected)-1)/(closed[selected[-1]]-closed[selected[0]]) if len(selected)>1 else None)
report = dict(run=str(run), phases=phases, observations=observations,
              scope='Diagnostic only; excludes first three seconds of each phase. GPU timestamps can include contention. Verify matching observed positions before comparing phases.')
out = root / 'work/map-review-20261105/powerhouse-shadow-cost.json'
out.write_text(json.dumps(report, indent=2))
print(json.dumps(phases, indent=2))
