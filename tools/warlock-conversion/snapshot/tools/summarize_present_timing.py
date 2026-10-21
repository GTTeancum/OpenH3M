"""Summarize process-local DXGI statistics without equating Present calls to display delivery."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import statistics


def summarize(path):
    rows=[]
    for line in path.read_text().splitlines():
        if '[host-present] ' not in line:
            continue
        pairs=dict(re.findall(r'(\w+)=([^ ]+)', line.split('[host-present] ',1)[1]))
        row={k: (float(v) if k in ('elapsed_ms','call_ms') else int(v,16 if k.endswith('_hr') else 10)) for k,v in pairs.items()}
        rows.append(row)
    result={'samples':len(rows),'source':'DXGI swap-chain frame statistics',
            'caution':'Successful Present calls are submissions, not proof of display. SyncQPCTime is a scheduler synchronization sample, not the presentation timestamp. guest_observed is sampled output progress, not a displayed-image identifier.'}
    if not rows:
        return dict(result,status='missing')
    result['statistics_hresult_counts']=dict(Counter(f"{r['stats_hr']:08X}" for r in rows))
    result['present_hresult_counts']=dict(Counter(f"{r['present_hr']:08X}" for r in rows))
    result['present_call_ms']={'median':statistics.median(r['call_ms'] for r in rows),'max':max(r['call_ms'] for r in rows)}
    intervals=[(b['qpc']-a['qpc'])*1000/a['frequency'] for a,b in zip(rows,rows[1:]) if a['frequency']==b['frequency'] and b['qpc']>a['qpc']]
    result['submission_intervals_ms']={'mean':statistics.mean(intervals),'max':max(intervals)} if intervals else None
    good=[r for r in rows if r['stats_hr']==0]
    result['status']='available' if good else 'unavailable'
    histogram=Counter(); skipped=0; resets=0; repeats=0
    for a,b in zip(rows,rows[1:]):
        if a['stats_hr'] or b['stats_hr']:
            continue
        delta=b['displayed']-a['displayed']; refresh=b['refresh']-a['refresh']
        if delta<0 or refresh<0:
            resets+=1
        elif delta==0:
            repeats+=1
        elif delta==1:
            histogram[refresh]+=1
        else:
            skipped+=1
    result.update(refresh_deltas_when_present_count_advances_by_one=dict(sorted(histogram.items())),
                  present_count_advances_greater_than_one=skipped, counter_resets=resets,
                  repeated_display_statistics=repeats,
                  first_successful_statistics=good[0] if good else None,
                  last_successful_statistics=good[-1] if good else None)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    args=parser.parse_args()
    report=summarize(args.run/'runtime.log')
    (args.run/'presentation-summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
