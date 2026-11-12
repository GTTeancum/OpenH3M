"""Join GPU execution samples to each native map-benchmark measurement window."""
import argparse,collections,datetime,json,re,statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
root=Path(__file__).resolve().parents[2];assert a.output.resolve().is_relative_to(root)
paths=sorted(a.run.glob('trace-runtime.*.log'),key=lambda x:int(x.name.split('.')[-2]),reverse=True)+[a.run/'trace-runtime.log']
frames=collections.defaultdict(float);times={};closed=set();results=[]
for path in paths:
 for line in path.open(errors='replace'):
  if '[gpu-execution]' not in line and '[map-benchmark] RESULT' not in line:continue
  stamp=datetime.datetime.fromisoformat(line[1:24]).timestamp();v=dict(re.findall(r'([\w]+)=([^ ]+)',line.strip()))
  if '[gpu-execution]' in line:
   frame=int(v['frame']);frames[frame]+=float(v['elapsed_ms'])
   if v['closes_frame']=='true':closed.add(frame);times[frame]=stamp
  else:results.append(dict(point=int(v['point']),seconds=float(v['seconds']),displayed_fps=float(v['fps']),valid=v['valid']=='true',end=stamp,camera=v['camera']))
for row in results:
 start=row['end']-row['seconds'];selected=sorted(f for f in closed if start<times[f]<row['end'])[1:-1];vals=sorted(frames[f] for f in selected)
 row['gpu_execution_ms']=dict(count=len(vals),mean=statistics.mean(vals),median=statistics.median(vals),p95=vals[int(.95*(len(vals)-1))]) if vals else None
report=dict(scope='GPU command-list execution per frame during exact native benchmark windows. Locked displayed FPS is not an uncapped performance estimate. Images require separate inspection.',run=str(a.run),points=results)
a.output.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
