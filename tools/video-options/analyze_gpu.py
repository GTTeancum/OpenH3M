"""Bounded native CPU-wait/GPU execution summary. Never treats CPU waits as GPU time."""
import argparse,collections,datetime,itertools,json,re,statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--start',type=float,default=140);p.add_argument('--end',type=float,default=193);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
launch=json.loads((a.run/'launch-clock.json').read_text())['wall_time'];frames=collections.defaultdict(float);counts=collections.Counter();closed=set();waits=collections.defaultdict(list)
paths=sorted(a.run.glob('trace-runtime.*.log'),key=lambda p:int(p.name.split('.')[-2]),reverse=True)+[a.run/'trace-runtime.log']
for l in itertools.chain.from_iterable(p.open(errors='replace') for p in paths):
 if not any(x in l for x in ('[gpu-execution]','[queue-wait]','[host-phase]')):continue
 t=datetime.datetime.fromisoformat(l[1:24]).timestamp()-launch
 if not a.start<t<a.end:continue
 v=dict(re.findall(r'([\w]+)=([^ ]+)',l.strip()))
 if '[gpu-execution]' in l:
  frame=int(v['frame']);frames[frame]+=float(v['elapsed_ms']);counts[frame]+=1
  if v['closes_frame']=='true':closed.add(frame)
 else:waits[v['kind']].append(float(v['elapsed_ms']))
def stats(v):
 v=sorted(v)
 return dict(count=len(v),mean_ms=statistics.mean(v),median_ms=statistics.median(v),p95_ms=v[int(.95*(len(v)-1))],max_ms=max(v)) if v else None
valid=sorted(closed)[1:-1]
r=dict(gpu_execution=stats([frames[f] for f in valid]),submissions_per_frame=statistics.mean([counts[f] for f in valid]) if valid else None,cpu_waits_over_5ms={k:stats(v) for k,v in waits.items()},scope='GPU timestamps sum command-list execution per frame; excludes CPU idle and gaps between submissions. CPU wait spans may overlap GPU execution.')
a.output.write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
