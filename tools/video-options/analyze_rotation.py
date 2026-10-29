import json, math, re, datetime, statistics, argparse, itertools
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--exclude-phase-ms',type=float,nargs='*',default=[]);a=p.parse_args()
events=[json.loads(x) for x in (a.run/'loading-trace.jsonl').read_text().splitlines()]
obs=[x for x in events if x.get('event')=='observer_position' and x['seconds']>132]
turn=[];total=0
for prev,cur in zip(obs,obs[1:]):
 y0=math.degrees(math.atan2(prev['forward'][1],prev['forward'][0]));y1=math.degrees(math.atan2(cur['forward'][1],cur['forward'][0]));d=(y1-y0+180)%360-180
 if not turn and abs(d)>1:turn=[prev]
 if turn:
  total+=d;turn.append(cur)
  if abs(total)>=360:break
if abs(total)<360:raise RuntimeError(f'Only {total} degrees; no complete sweep')
launch=json.loads((a.run/'launch-clock.json').read_text())['wall_time'];samples=[];captures=[];origin=None
logs=sorted(a.run.glob('trace-runtime.*.log'),key=lambda p:int(p.name.split('.')[-2]),reverse=True)+[a.run/'trace-runtime.log']
for line in itertools.chain.from_iterable(p.open(errors='replace') for p in logs):
 if '[host-present]' in line:
  v=dict(re.findall(r'(\w+)=([\w.]+)',line));t=float(v['elapsed_ms']);f=int(v['guest_painted'])
  if origin is None:origin=datetime.datetime.fromisoformat(line[1:24]).timestamp()-t/1000
  if not samples or samples[-1][1]!=f:samples.append((t,f))
 if 'guest-output capture at' in line and 'wrote' in line:captures.append(datetime.datetime.fromisoformat(line[1:24]).timestamp())
start=(launch+turn[0]['seconds']-origin)*1000;end=(launch+turn[-1]['seconds']-origin)*1000
caps=[(c-origin)*1000 for c in captures];caps += [start+t for t in a.exclude_phase_ms];gaps=[];skips=0;excluded=0
for b,c in zip(samples,samples[1:]):
 if b[0]<start or c[0]>end or c[1]<=b[1]:continue
 if any(b[0]<=t+1000 and c[0]>=t-1000 for t in caps):excluded+=1;continue
 gaps.append(c[0]-b[0]);skips+=max(0,c[1]-b[1]-1)
sortedg=sorted(gaps)
r=dict(run=str(a.run),degrees=total,rotation_seconds=turn[-1]['seconds']-turn[0]['seconds'],position_ranges=[max(o['position'][i] for o in turn)-min(o['position'][i] for o in turn) for i in range(3)],start_ms=start,end_ms=end,delivered_fps=1000*len(gaps)/sum(gaps),median_ms=statistics.median(gaps),p95_ms=sortedg[int(.95*(len(gaps)-1))],p99_ms=sortedg[int(.99*(len(gaps)-1))],max_ms=max(gaps),over_50_ms=sum(g>50 for g in gaps),over_100_ms=sum(g>100 for g in gaps),unobserved_guest_frames=skips,intervals=len(gaps),capture_intervals_excluded=excluded,capture_elapsed_ms=caps)
a.output.write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
