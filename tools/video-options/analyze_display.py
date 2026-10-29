"""Join submitted image identity to successful DXGI displayed-present reports."""
import argparse,collections,itertools,json,re,statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--rotation',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
w=json.loads(a.rotation.read_text());paths=sorted(a.run.glob('trace-runtime.*.log'),key=lambda p:int(p.name.split('.')[-2]),reverse=True)+[a.run/'trace-runtime.log'];records=[];submitted={};invalid=0
for l in itertools.chain.from_iterable(p.open(errors='replace') for p in paths):
 if '[host-present]' not in l:continue
 v=dict(re.findall(r'(\w+)=([\w.]+)',l))
 if any(v[k]!='00000000' for k in ('present_hr','stats_hr','count_hr')):invalid+=1;continue
 v={k:(float(x) if k in ('elapsed_ms','call_ms') else int(x,16) if k.endswith('_hr') else int(x)) for k,x in v.items()};records.append(v);submitted[v['submitted']]=v['guest_painted']
clock=[(y['sync_qpc']-x['sync_qpc'])/x['frequency']/(y['sync_refresh']-x['sync_refresh']) for x,y in zip(records,records[1:]) if y['sync_refresh']>x['sync_refresh'] and y['sync_qpc']>x['sync_qpc']];refresh_s=statistics.median(clock);images=[];unmatched=0
for v in records:
 identity=submitted.get(v['displayed'])
 if identity is None:unmatched+=1;continue
 if not images or identity!=images[-1]['image']:images.append(dict(image=identity,refresh=v['refresh'],time=v['elapsed_ms']))
gaps=[];missing=0
for x,y in zip(images,images[1:]):
 if x['time']<w['start_ms'] or y['time']>w['end_ms']:continue
 if any(x['time']<=t+1000 and y['time']>=t-1000 for t in w['capture_elapsed_ms']):continue
 if y['refresh']<=x['refresh'] or y['image']<=x['image']:continue
 gaps.append(y['refresh']-x['refresh']);missing+=max(0,y['image']-x['image']-1)
ms=sorted(g*refresh_s*1000 for g in gaps)
r=dict(refresh_hz=1/refresh_s,displayed_fps=len(gaps)/(sum(gaps)*refresh_s),intervals=len(gaps),refresh_interval_counts=dict(collections.Counter(gaps)),median_ms=statistics.median(ms),p95_ms=ms[int(.95*(len(ms)-1))],max_ms=max(ms),missing_images=missing,invalid_reports=invalid,unmatched_reports=unmatched,scope='Identified game images joined to DXGI displayed-present refresh counts; capture windows excluded.')
a.output.write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
