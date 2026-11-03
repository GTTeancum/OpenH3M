"""Analyze existing text logs; sums are not a decomposition of wall time."""
import re,json,statistics,collections
from pathlib import Path

def stats(values):
 values=sorted(values)
 return dict(n=len(values),median=statistics.median(values),p95=values[int(.95*(len(values)-1))],maximum=max(values)) if values else {}
results={}
for run in ('performance-baseline-01','performance-async-02'):
 root=Path('work/sky-bridge')/run
 records=[]
 for path in root.glob('runtime*.log'):
  for line in path.read_text(errors='replace').splitlines():
   if any(marker in line for marker in ('[gpu-execution]','[queue-wait]','[host-present]')):
    records.append((line[:25],dict(re.findall(r'(\w+)=([\w.]+)',line)),line))
 records.sort(key=lambda row:row[0])
 gpu={};waits=[];active=set();present=[]
 for stamp,v,line in records:
  if '[gpu-execution]' in line:
   sub=int(v['submission']);assert sub not in gpu
   gpu[sub]=dict(frame=int(v['frame']),ms=float(v['elapsed_ms']),closes=v['closes_frame']=='true')
  elif '[queue-wait]' in line:waits.append((int(v['target']),float(v['elapsed_ms'])))
  else:
   elapsed=float(v['elapsed_ms'])
   if 110000<=elapsed<=178000 and not 144137<=elapsed<=146137:
    active.add(int(v['guest_painted']));present.append((elapsed,int(v['guest_painted'])))
 frames=collections.defaultdict(list);fw=collections.defaultdict(list)
 for sub,row in gpu.items():
  if row['frame'] in active:frames[row['frame']].append(row)
 unmatched=0
 for sub,ms in waits:
  if sub not in gpu:unmatched+=1
  elif gpu[sub]['frame'] in active:fw[gpu[sub]['frame']].append(ms)
 complete={f:rows for f,rows in frames.items() if sum(r['closes'] for r in rows)==1}
 results[run]=dict(scope='Existing stationary-spawn host logs, 110-178 seconds; capture interval excluded by painted frame ID. No traversal or console evidence.',
  submissions_per_frame=stats([len(rows) for rows in complete.values()]),
  gpu_ms_per_frame=stats([sum(r['ms'] for r in rows) for rows in complete.values()]),
  logged_wait_ms_per_frame=stats([sum(fw[f]) for f in complete]),
  logged_wait_count_per_frame=stats([len(fw[f]) for f in complete]),
  submission_ms=stats([r['ms'] for rows in complete.values() for r in rows]),
  small_submissions=sum(r['ms']<.1 for rows in complete.values() for r in rows),
  missing_target_submissions=unmatched,
  caveats=['Waits shorter than 5 ms are not logged.','Frame-close marker does not prove all timestamp samples were retained.','GPU work and CPU waits overlap; do not add them.','Logs do not identify the caller of CheckSubmissionFence.'])
Path('work/sky-bridge/submission-analysis.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
