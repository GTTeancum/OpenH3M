"""Join sparse stored-depth samples to actual byte-attributed searchlight draws."""
import argparse
from collections import Counter,defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import struct

REF=Path(__file__).resolve().parent
REPO=REF.parents[4]
ALBEDO={8562590739555380577,6159915361788144154}
STATIC={12021865740332317413,17893540736724855907}
POINTS={(501,175),(503,173),(497,178),(711,197)}


def value(bits):
    return struct.unpack('<f',struct.pack('<I',bits))[0]


def analyze(run):
    run=run.resolve();run.relative_to(REPO/'work/sky-bridge')
    calls={c['sequence']:c for c in json.loads((run/'model-draw-calls.json').read_text())['calls']}
    coverage={c['sequence']:c for c in json.loads((run/'coverage-draws.json').read_text())}
    events=Counter();records={}
    for row in csv.DictReader((run/'depth-values.csv').open()):
        events[row['event']]+=1
        if row['event']!='sample':continue
        row={k:int(v) for k,v in row.items() if k!='event'}
        seq=row['sequence'];c=calls[seq];owner,=c['candidates']
        assert owner['owner']==10122 and owner['part'] in (0,1)
        assert (c['frame'],c['ps'],c['index_count'])==(row['frame'],row['shader'],row['index_count'])
        assert row['phase'] in (0,1) and row['samples'] in (1,2,4) and 0<=row['sample']<row['samples']
        assert (row['x'],row['y']) in POINTS and math.isfinite(value(row['depth_bits']))
        record=records.setdefault(row['record'],dict(metadata={k:v for k,v in row.items() if k not in ('x','y','sample','depth_bits')},points={}))
        assert record['metadata']=={k:v for k,v in row.items() if k not in ('x','y','sample','depth_bits')}
        point=(row['x'],row['y'],row['sample']);assert point not in record['points']
        record['points'][point]=row['depth_bits']
    assert records,'No recorded depth values'
    assert set(events)<={'sample','limit','end'},dict(events)
    paired=defaultdict(dict)
    for number,record in records.items():
        m=record['metadata']
        assert set(record['points'])=={(x,y,s) for x,y in POINTS for s in range(m['samples'])}
        assert m['phase'] not in paired[m['sequence']]
        paired[m['sequence']][m['phase']]=record
    missing=[s for s,p in paired.items() if set(p)!={0,1}]
    result_rows=[];groups={};by_frame=defaultdict(list)
    for seq,pair in sorted(paired.items()):
        if set(pair)!={0,1}:continue
        c=calls[seq];identity,=c['candidates'];a,b=pair[0],pair[1]
        assert all(a['metadata'][k]==b['metadata'][k] for k in ('resource','format','width','height','samples'))
        assert a['points'].keys()==b['points'].keys()
        key=(identity['part'],c['vs'],c['ps'])
        group=groups.setdefault(key,dict(part=key[0],vs=key[1],ps=key[2],draws=0,depth_changed_draws=0,
            depth_changed_samples=0,zero_coverage_draws=0,resource_shapes=set(),depth_min=math.inf,depth_max=-math.inf))
        points=[]
        for point in sorted(a['points']):
            before,after=a['points'][point],b['points'][point]
            points.append(dict(x=point[0],y=point[1],sample=point[2],before_bits=before,after_bits=after,
                before=value(before),after=value(after)))
        changed=sum(p['before_bits']!=p['after_bits'] for p in points)
        group['draws']+=1;group['depth_changed_draws']+=bool(changed);group['depth_changed_samples']+=changed
        group['zero_coverage_draws']+=coverage[seq]['samples']==0
        group['resource_shapes'].add(tuple(a['metadata'][k] for k in ('format','width','height','samples')))
        group['depth_min']=min(group['depth_min'],*(p['before'] for p in points),*(p['after'] for p in points))
        group['depth_max']=max(group['depth_max'],*(p['before'] for p in points),*(p['after'] for p in points))
        row=dict(sequence=seq,frame=c['frame'],part=identity['part'],vs=c['vs'],ps=c['ps'],
            resource=a['metadata']['resource'],actual_coverage=coverage[seq]['samples'],points=points)
        result_rows.append(row);by_frame[c['frame']].append(row)
    intervals=[]
    for frame,rows in sorted(by_frame.items()):
        albedo=[r for r in rows if r['ps'] in ALBEDO]
        static=[r for r in rows if r['ps'] in STATIC]
        if not albedo or not static:continue
        before=max(albedo,key=lambda r:r['sequence']);after=min(static,key=lambda r:r['sequence'])
        assert after['sequence']>before['sequence']
        old={(p['x'],p['y'],p['sample']):p for p in before['points']}
        comparisons=[]
        for p in after['points']:
            a=old[p['x'],p['y'],p['sample']]
            comparisons.append(dict(x=p['x'],y=p['y'],sample=p['sample'],albedo_after_bits=a['after_bits'],
                static_before_bits=p['before_bits'],delta=p['before']-a['after'],bit_delta=p['before_bits']-a['after_bits']))
        intervals.append(dict(frame=frame,albedo_sequence=before['sequence'],static_sequence=after['sequence'],
            same_resource=before['resource']==after['resource'],points=comparisons))
    interval_summary=[]
    for point in sorted({(p['x'],p['y'],p['sample']) for r in intervals for p in r['points']}):
        rows=[p for r in intervals for p in r['points'] if (p['x'],p['y'],p['sample'])==point]
        interval_summary.append(dict(x=point[0],y=point[1],sample=point[2],frames=len(rows),
            equal=sum(p['bit_delta']==0 for p in rows),larger=sum(p['delta']>0 for p in rows),smaller=sum(p['delta']<0 for p in rows),
            delta_range=[min(p['delta'] for p in rows),max(p['delta'] for p in rows)],
            bit_delta_range=[min(p['bit_delta'] for p in rows),max(p['bit_delta'] for p in rows)]))
    for group in groups.values():group['resource_shapes']=sorted(group['resource_shapes'])
    report=dict(run=str(run.relative_to(REPO)),events=dict(events),records=len(records),paired_draws=len(result_rows),
        frames=len(by_frame),missing_pairs=missing,groups=list(groups.values()),
        albedo_to_static_interval_frames=len(intervals),interval_summary=interval_summary,
        same_resource_intervals=sum(r['same_resource'] for r in intervals),
        evidence_sha256={name:hashlib.sha256((run/name).read_bytes()).hexdigest()
            for name in ('depth-values.csv','draws.bin','model-draw-calls.json','coverage-draws.json')},
        limitations=['These are stored depth values, not captured fragment or vertex outputs.',
            'Four fixed locations cannot establish a full image, complete coverage or correct visual appearance.',
            'A change between albedo and static passes identifies an interval; it does not identify its writer.',
            'Same host resource identity does not prove the resource contents were never transferred or cleared.',
            'All samples are from the private replay, which restores the camera but not the full simulation state.'],
        credit=json.loads((REF/'sky-pixel-probe-build.json').read_text())['credit'])
    (run/'depth-value-draws.json').write_text(json.dumps(dict(draws=result_rows,intervals=intervals),indent=2)+'\n')
    (run/'depth-value-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('events','records','paired_draws','frames','missing_pairs','interval_summary','same_resource_intervals')}))
    print(json.dumps(report['groups']))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path)
    analyze(parser.parse_args().run)
