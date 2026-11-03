"""Summarize bounded text-only timing logs and attribute waits by caller."""
import sys,re,json,statistics,collections
from pathlib import Path

def stats(values):
 values=sorted(values)
 return dict(n=len(values),median=statistics.median(values),p95=values[int(.95*(len(values)-1))],maximum=max(values)) if values else {}

def analyze(root):
 lines=[]
 for path in root.glob('runtime*.log'):lines.extend(path.read_text(errors='replace').splitlines())
 lines.sort()
 presents=[];gpu={};waits=[];evidence=[]
 for line in lines:
  v=dict(re.findall(r'(\w+)=([\w.\-]+)',line))
  if '[host-present]' in line:
   elapsed=float(v['elapsed_ms']);frame=int(v['guest_painted'])
   if 110000<=elapsed<=165000 and (not presents or frame!=presents[-1][1]):presents.append((elapsed,frame))
  elif '[gpu-execution]' in line:
   submission=int(v['submission'])
   assert submission not in gpu
   gpu[submission]=dict(frame=int(v['frame']),ms=float(v['elapsed_ms']),closes=v['closes_frame']=='true')
  elif '[queue-wait]' in line:waits.append(v)
  if 'asq_sky_bri' in line or ('sky_bridge.map' in line and ('Read' in line or 'Open' in line or 'map' in line)):
   evidence.append(line)
 active={frame for _,frame in presents};frames=collections.defaultdict(list);reasons=collections.defaultdict(list)
 for row in gpu.values():
  if row['frame'] in active:frames[row['frame']].append(row)
 for row in waits:
  if int(row.get('frame',-1)) in active:reasons[row.get('reason','unknown')].append(float(row['elapsed_ms']))
 complete={f:rows for f,rows in frames.items() if any(x['closes'] for x in rows)}
 gaps=[b[0]-a[0] for a,b in zip(presents,presents[1:]) if b[1]==a[1]+1]
 report=dict(scope='Stationary process-local menu route, 110-165 seconds, host observations only; no visual/traversal/console verification.',
  present_interval_ms=stats(gaps),nonconsecutive_frame_transitions=sum(b[1]!=a[1]+1 for a,b in zip(presents,presents[1:])),
  gpu_ms_per_observed_frame=stats([sum(r['ms'] for r in rows) for rows in complete.values()]),
  submissions_per_observed_frame=stats([len(rows) for rows in complete.values()]),
  wait_ms_by_caller={key:stats(values) for key,values in reasons.items()},
  wait_total_ms_by_caller={key:sum(values) for key,values in reasons.items()},
  first_sample=presents[0] if presents else None,last_sample=presents[-1] if presents else None,
  map_log_evidence=evidence[-12:],
  caveats=['Waits under 5ms are not logged.','GPU timings and CPU waits overlap; do not add them.','Map/autosave log records alone do not verify visible gameplay.'])
 (root/'attributed-timing-summary.json').write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':print(json.dumps(analyze(Path(sys.argv[1])),indent=2))
