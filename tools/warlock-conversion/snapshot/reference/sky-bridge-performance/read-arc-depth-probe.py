"""Compare non-writing native/depth/stencil/cull variants of attributed arc draws."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

REF=Path(__file__).resolve().parent;REPO=REF.parents[4]
spec=importlib.util.spec_from_file_location('arc',REF/'read-arc-pass-probe.py')
arc=importlib.util.module_from_spec(spec);spec.loader.exec_module(arc)
p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path)
run=p.parse_args().run.resolve();run.relative_to(REPO/'work/sky-bridge')
calls={}
for kind,data in arc.packets(run/'draws.bin'):
    if kind==1:draw=struct.unpack('<11Q',data)
    elif kind==5:
        assert draw[4]==arc.PS
        calls[draw[0]]=draw
attribution=json.loads((run/'arc-pass-analysis.json').read_text())
assert not attribution['unassigned_draws']
events=Counter();variants=defaultdict(dict);outside=0;states=set();queries=set()
for row in csv.DictReader((run/'depth-tests.csv').open()):
    events[row['event']]+=1
    if row['event']!='sample':continue
    r={k:int(v) for k,v in row.items() if k!='event'}
    assert r['query'] not in queries;queries.add(r['query'])
    if r['sequence'] not in calls:
        outside+=1;continue
    d=calls[r['sequence']]
    assert (r['frame'],r['shader'],r['index_count'])==(d[1],d[4],d[6])
    assert r['variant'] not in variants[r['sequence']]
    variants[r['sequence']][r['variant']]=r['samples']
    states.add(tuple(r[k] for k in ('variant','depth_enabled','depth_func','stencil_enabled','cull','sample_mask')))
count=max((max(v) for v in variants.values()),default=-1)+1
assert count in (4,6)
complete={s:v for s,v in variants.items() if set(v)==set(range(count))}
actual={int(r['sequence']):int(r['samples']) for r in csv.DictReader((run/'coverage.csv').open()) if r['event']=='sample'}
summary={i:{'draws':len(complete),'nonzero_draws':sum(v[i]>0 for v in complete.values()),
    'total_samples':sum(v[i] for v in complete.values()),'maximum_samples':max((v[i] for v in complete.values()),default=0)} for i in range(count)}
report={'events':dict(events),'attributed_draws':len(calls),'complete_comparisons':len(complete),
    'frames':len({calls[s][1] for s in complete}),'incomplete_comparisons':len(variants)-len(complete),
    'records_outside_flushed_draw_trace':outside,'variants':summary,
    'actual_matches_readonly_native':sum(actual.get(s)==v[0] for s,v in complete.items()),
    'variant_order':['native tests and culling','depth ALWAYS','stencil disabled','depth/stencil bypassed',
        'depth/stencil bypassed and culling disabled','native depth/stencil, culling disabled'][:count],
    'host_states':[dict(zip(('variant','original_depth_enabled','original_depth_func','original_stencil_enabled','effective_cull','sample_mask'),s)) for s in sorted(states)],
    'evidence_sha256':{n:hashlib.sha256((run/n).read_bytes()).hexdigest() for n in ('draws.bin','coverage.csv','depth-tests.csv')},
    'limitations':['All variant draws disable color/depth/stencil writes and restore the native pipeline.',
        'Fragment counts prove rasterization and rejection, not visible particle color or correct shape.',
        'Bounded watchdog may stop a probe before its own frame limit; only joined complete comparisons are reported.'],
    'credit':json.loads((REF/'sky-pixel-probe-build.json').read_text())['credit']}
(run/'arc-depth-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k in ('events','attributed_draws','complete_comparisons','frames','incomplete_comparisons','variants','actual_matches_readonly_native')}))
