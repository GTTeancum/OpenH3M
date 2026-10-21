"""Correlate thresholded CPU fence waits with native guest-output gaps."""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re
from summarize_preparation import summarize

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('run',type=Path)
a=p.parse_args()
state=json.loads((a.run/'run.json').read_text())
start=state['started_unix_seconds']
events=[]
pattern=re.compile(r'^\[([^]]+)\].*\[queue-wait\] kind=(\S+) elapsed_ms=([\d.]+) target=(\d+) result=(\d+) queue=(\w+)')
for line in (a.run/'runtime.log').read_text().splitlines():
 m=pattern.search(line)
 if not m: continue
 wall,kind,ms,target,result,queue=m.groups()
 end=datetime.fromisoformat(wall).timestamp()-start
 events.append(dict(kind=kind,elapsed_ms=float(ms),target=int(target),result=int(result),queue=queue,start_seconds=end-float(ms)/1000,end_seconds=end))
hitches=summarize(a.run)['hitches']
for h in hitches:
 h.pop('overlapping_preparation',None)
 matches=[e for e in events if e['start_seconds']<=h['end_seconds'] and e['end_seconds']>=h['start_seconds']]
 h['wait_counts']=dict(Counter(e['kind'] for e in matches))
 h['overlapping_waits_ms']=round(sum(max(0,min(e['end_seconds'],h['end_seconds'])-max(e['start_seconds'],h['start_seconds']))*1000 for e in matches),3)
 h['maximum_wait_ms']=max((e['elapsed_ms'] for e in matches),default=0)
report={'counts':dict(Counter(e['kind'] for e in events)), 'hitches':hitches,
        'caution':'Only waits >=5ms are logged. Wall-clock alignment is approximate; sums across threads can overlap. Does not identify which caller requested a guest submission fence.'}
(a.run/'queue-wait-summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
