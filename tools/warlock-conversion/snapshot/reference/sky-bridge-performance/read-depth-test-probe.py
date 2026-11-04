"""Join read-only depth/stencil comparison queries to actual model draws.

Variant0 preserves the original tests, variant1 forces depth ALWAYS,
variant2 disables stencil, and variant3 bypasses both. Every variant has
zero color/depth/stencil writes. A bypass result is diagnostic, not a fix.
"""
import argparse,collections,csv,hashlib,json
from pathlib import Path
REF=Path(__file__).resolve().parent;REPO=REF.parents[4]

def analyze(run):
    run=run.resolve();run.relative_to(REPO/'work/sky-bridge')
    calls={x['sequence']:x for x in json.loads((run/'model-draw-calls.json').read_text())['calls']}
    coverage={x['sequence']:x for x in json.loads((run/'coverage-draws.json').read_text())}
    phases=collections.defaultdict(dict);events=collections.Counter();queries=set()
    with (run/'depth-tests.csv').open(newline='') as stream:
        for raw in csv.DictReader(stream):
            event=raw.pop('event');events[event]+=1
            if event!='sample':continue
            row={k:int(v) for k,v in raw.items()};seq=row['sequence'];c=calls[seq]
            assert (row['frame'],row['shader'],row['index_count'])==(c['frame'],c['ps'],c['index_count'])
            assert row['query'] not in queries;queries.add(row['query'])
            assert row['variant'] in range(4) and row['variant'] not in phases[seq]
            assert len(c['candidates'])==1 and c['candidates'][0]['owner']==10122
            assert c['candidates'][0]['part'] in (0,1)
            phases[seq][row['variant']]=row
    assert not set(events)-{'sample','end'},events
    groups={};rows=[]
    for seq,variants in sorted(phases.items()):
        assert set(variants)==set(range(4))
        c=calls[seq];part=c['candidates'][0]['part'];key=(part,c['vs'],c['ps'])
        samples=[variants[i]['samples'] for i in range(4)]
        row=dict(sequence=seq,frame=c['frame'],part=part,vs=c['vs'],ps=c['ps'],samples=samples,
            actual_samples=coverage[seq]['samples'],position_inputs_sha256=coverage[seq]['position_inputs_sha256'])
        rows.append(row)
        state_keys=('depth_enabled','depth_func','stencil_enabled','stencil_front_func','stencil_read_mask','cull','sample_mask')
        states=[{k:variants[i][k] for k in state_keys} for i in range(4)];assert all(x==states[0] for x in states)
        group=groups.setdefault(key,dict(part=part,vs=c['vs'],ps=c['ps'],draws=0,
            host_state=states[0],actual_matches_readonly_original=0,
            zero_original_depth_restores=0,zero_original_stencil_restores=0,
            both_equals_depth=0,variant_min=[2**64-1]*4,variant_max=[0]*4,combinations=collections.Counter()))
        assert group['host_state']==states[0]
        group['draws']+=1;group['actual_matches_readonly_original']+=samples[0]==row['actual_samples']
        group['zero_original_depth_restores']+=samples[0]==0 and samples[1]>0 and samples[2]==0
        group['zero_original_stencil_restores']+=samples[0]==0 and samples[2]>0 and samples[1]==0
        group['both_equals_depth']+=samples[3]==samples[1]
        for i,n in enumerate(samples):group['variant_min'][i]=min(group['variant_min'][i],n);group['variant_max'][i]=max(group['variant_max'][i],n)
        group['combinations'][tuple(samples)]+=1
    for group in groups.values():group['combinations']=[dict(samples=k,draws=v) for k,v in sorted(group['combinations'].items())]
    expected={seq for seq,c in calls.items() if c['candidates']==[dict(owner=10122,mesh=0,part=0)] or c['candidates']==[dict(owner=10122,mesh=0,part=1)]}
    assert set(phases)==expected,(len(phases),len(expected))
    report=dict(run=str(run.relative_to(REPO)),events=dict(events),draws=len(phases),groups=list(groups.values()),
        variant_order=['original tests, all writes disabled','depth comparison ALWAYS','stencil disabled','depth ALWAYS and stencil disabled'],
        inputs_sha256={n:hashlib.sha256((run/n).read_bytes()).hexdigest() for n in ('depth-tests.csv','coverage-draws.json','model-draw-calls.json')},
        limitations=['Extra read-only draws diagnose rejection paths; they do not propose disabling tests in the game.',
            'Disabling depth writes can change self-occlusion counts in an albedo draw; actual/read-only equality must be checked per pass.',
            'Depth rejection does not distinguish correct occlusion from numerical or transformed-position errors.',
            'Aggregate counts are not a complete coverage mask or full visual acceptance.'],
        credit=json.loads((REF/'sky-pixel-probe-build.json').read_text())['credit'])
    (run/'depth-test-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    (run/'depth-test-draws.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(dict(events=dict(events),draws=len(phases),groups=[{k:v for k,v in g.items() if k!='combinations'} for g in groups.values()])))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path);analyze(parser.parse_args().run)
