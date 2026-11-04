"""Join per-draw numeric colors to byte-attributed animated model submissions.

Measures contribution at selected points; no claim of complete surface coverage,
correct animation, or reproduction of the human-reported black flash.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path

REF = Path(__file__).resolve().parent
REPO = REF.parents[4]
spec = importlib.util.spec_from_file_location('stage', REF/'read-stage-probe.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)
POINTS = {(192,172),(353,162),(574,184),(566,190),(701,190),(711,197),
          (501,175),(753,228),(755,234),(585,212),(614,219),(341,216),
          (347,222),(408,184),(614,187),(966,224)}


def analyze(run):
    run = run.resolve()
    run.relative_to(REPO/'work/sky-bridge')
    attribution = json.loads((run/'model-draw-calls.json').read_text())
    calls = {c['sequence']: c for c in attribution['calls']}
    assert len(calls) == len(attribution['calls'])
    metadata = json.loads((run/'model-draw-analysis.json').read_text())
    parts = {(p['owner'],p['mesh'],p['part']): p for p in metadata['parts']}
    events, formats = Counter(), Counter()
    phases, non_samples = {}, []
    with (run/'stages.csv').open(newline='') as stream:
        for row in csv.DictReader(stream):
            event = row.pop('event')
            events[event] += 1
            row = {k: int(v) for k,v in row.items()}
            if event != 'sample':
                non_samples.append(dict(event=event, **row))
                continue
            call = calls[row['sequence']]
            assert (row['frame'],row['shader'],row['index_count']) == (
                call['frame'],call['ps'],call['index_count'])
            assert row['phase'] in (0,1)
            point = row['x'],row['y']
            assert point in POINTS
            phase = phases.setdefault(row['sequence'], {}).setdefault(row['phase'], {})
            assert point not in phase
            color = stage.rgba(row)
            assert all(math.isfinite(v) for v in color), 'Non-finite sampled color'
            target = tuple(row[k] for k in ('resource','format','resource_format','width','height','bytes'))
            phase[point] = color,target
            formats[row['format']] += 1
    groups, incomplete, unmatched = {}, [], []
    temporal = defaultdict(dict)
    complete = 0
    for sequence, call in calls.items():
        sampled = phases.get(sequence, {})
        full = set(sampled) == {0,1} and all(set(p) == POINTS for p in sampled.values())
        if not full:
            incomplete.append(dict(sequence=sequence, frame=call['frame'], ps=call['ps'],
                phase_counts={str(k):len(v) for k,v in sampled.items()},
                guest_color0_write_mask=call['color_mask'] & 15,
                candidates=call['candidates']))
        else:
            complete += 1
        if len(call['candidates']) != 1:
            unmatched.append(sequence)
            continue
        candidate = call['candidates'][0]
        geometry_key = tuple(candidate[k] for k in ('owner','mesh','part'))
        key = (*geometry_key,call['vs'],call['ps'])
        group = groups.setdefault(key, dict(geometry=parts[geometry_key], vs=call['vs'],ps=call['ps'],
            draws=0,complete_pairs=0,changed_draws=0,changed_points=0,max_abs_rgb_delta=0.,
            color0_write_masks=Counter(),points={}))
        group['draws'] += 1
        group['color0_write_masks'][call['color_mask'] & 15] += 1
        if not full:
            continue
        group['complete_pairs'] += 1
        changed = False
        for point in sorted(POINTS):
            (before, before_target),(after,after_target) = sampled[0][point],sampled[1][point]
            assert before_target == after_target, 'Target changed inside a draw'
            delta = max(abs(a-b) for a,b in zip(before[:3],after[:3]))
            any_change = before != after
            changed |= any_change
            group['changed_points'] += any_change
            group['max_abs_rgb_delta'] = max(group['max_abs_rgb_delta'],delta)
            label = ','.join(map(str,point))
            item = group['points'].setdefault(label,dict(point=point,pairs=0,changed_pairs=0,
                rgb_changed_pairs=0,after_min_rgb=[math.inf]*3,after_max_rgb=[-math.inf]*3,
                max_abs_rgb_delta=0.,examples=[]))
            item['pairs'] += 1
            item['changed_pairs'] += any_change
            item['rgb_changed_pairs'] += delta != 0
            item['max_abs_rgb_delta'] = max(item['max_abs_rgb_delta'],delta)
            for i,v in enumerate(after[:3]):
                item['after_min_rgb'][i] = min(item['after_min_rgb'][i],v)
                item['after_max_rgb'][i] = max(item['after_max_rgb'][i],v)
            if any_change and len(item['examples']) < 2:
                item['examples'].append(dict(frame=call['frame'],sequence=sequence,before=before,after=after))
            frame_values = temporal[(*key,*point)]
            previous = frame_values.get(call['frame'])
            if previous is None or sequence > previous[0]:
                frame_values[call['frame']] = sequence,before,after,delta
        group['changed_draws'] += changed
    drops = []
    for key, frames in temporal.items():
        for frame,(sequence,before,after,delta) in frames.items():
            if frame-1 not in frames or frame+1 not in frames:
                continue
            previous,following = frames[frame-1][2],frames[frame+1][2]
            baseline,current = min(max(previous[:3]),max(following[:3])),max(after[:3])
            if baseline > 0 and current < baseline:
                drops.append(dict(frame=frame,sequence=sequence,owner=key[0],mesh=key[1],part=key[2],
                    vs=key[3],ps=key[4],point=key[5:],drop=baseline-current,ratio=current/baseline,
                    previous_rgb=previous[:3],before_rgb=before[:3],after_rgb=after[:3],
                    next_rgb=following[:3],draw_max_abs_rgb_delta=delta))
    report = dict(trace=str(run.relative_to(REPO)),draws=len(calls),
        frames=len({c['frame'] for c in calls.values()}),events=dict(events),formats=dict(formats),
        stop_reasons=attribution['stop_reasons'],complete_pairs=complete,
        unmatched_or_ambiguous_sequences=unmatched,incomplete_pairs=incomplete,
        other_events=non_samples,groups=list(groups.values()),
        largest_single_frame_decreases=sorted(drops,key=lambda d:d['drop'],reverse=True)[:50],
        lowest_single_frame_ratios=sorted(drops,key=lambda d:d['ratio'])[:50],
        input_sha256={name:hashlib.sha256((run/name).read_bytes()).hexdigest() for name in
            ('draws.bin','stages.csv','model-draw-analysis.json','model-draw-calls.json')},
        limitations=[
            'Sixteen fixed numeric points, not a complete image or complete triangle coverage.',
            'A changed value proves contribution at that point; unchanged values do not prove invisibility.',
            'Color-0 values may be intermediate buffers and are not final presented colors.',
            'Temporal metrics compare the last matching pass per frame, including pixels unchanged by that draw.',
            'Missing pairs are explicit. A zero guest color-0 write mask may explain them but does not establish the normalized host binding.',
            'The saved pose is not a complete simulation savestate; probe barriers can affect timing.'],
        credit=json.loads((REF/'sky-pixel-probe-build.json').read_text())['credit'])
    (run/'model-pass-analysis.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ('draws','frames','events','formats','complete_pairs','stop_reasons')}))
    print(json.dumps(dict(unmatched=len(unmatched),incomplete=len(incomplete),groups=len(groups),
        contributing_groups=sum(g['changed_draws']>0 for g in groups.values()))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    analyze(parser.parse_args().run)
