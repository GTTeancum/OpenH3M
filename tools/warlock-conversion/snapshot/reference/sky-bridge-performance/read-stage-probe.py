"""Analyze numeric color-0 values immediately around identified material draws."""
import argparse
import collections
import csv
import json
import math
from pathlib import Path
import struct

PASSES = {8562590739555380577: 'albedo', 14617156369365479079: 'static',
          14007674117786981017: 'dynamic'}

def unsigned_float(value, mantissa_bits):
    fraction = value & ((1 << mantissa_bits) - 1)
    exponent = value >> mantissa_bits
    if exponent == 31:
        return math.nan if fraction else math.inf
    if exponent == 0:
        return math.ldexp(fraction, -14-mantissa_bits)
    return math.ldexp(1+fraction/(1 << mantissa_bits), exponent-15)

def rgba(row):
    raw = struct.pack('<4I', *(int(row[f'w{i}']) for i in range(4)))
    fmt = int(row['format'])
    if fmt == 2:
        return struct.unpack('<4f', raw)
    if fmt == 10:
        return struct.unpack('<4e', raw[:8])
    if fmt == 11:
        return tuple(v/65535 for v in struct.unpack('<4H', raw[:8]))
    if fmt == 13:
        return tuple(max(-1, v/32767) for v in struct.unpack('<4h', raw[:8]))
    if fmt == 24:
        word, = struct.unpack('<I', raw[:4])
        return tuple((word >> shift & 1023)/1023 for shift in (0,10,20)) + ((word >> 30)/3,)
    if fmt == 26:
        word, = struct.unpack('<I', raw[:4])
        return (unsigned_float(word & 2047,6), unsigned_float(word >> 11 & 2047,6),
                unsigned_float(word >> 22,5), 1.0)
    if fmt in (28,29,87):
        result = tuple(v/255 for v in raw[:4])
        return (result[2],result[1],result[0],result[3]) if fmt == 87 else result
    raise ValueError(f'Unsupported sampled format {fmt}')

def analyze(path):
    pairs = {}; events = collections.Counter(); non_samples = []; nonfinite = []
    with path.open(newline='') as stream:
        for row in csv.DictReader(stream):
            events[row['event']] += 1
            if row['event'] != 'sample':
                non_samples.append(row); continue
            key = tuple(int(row[n]) for n in ('frame','sequence','x','y'))
            phase = int(row['phase'])
            if phase not in (0,1) or phase in pairs.setdefault(key,{}):
                raise ValueError('Unexpected or duplicate phase')
            row['rgba'] = rgba(row)
            if not all(math.isfinite(v) for v in row['rgba']):
                nonfinite.append({k:row[k] for k in ('frame','sequence','phase','shader','x','y','w0','w1','w2','w3')})
            pairs[key][phase] = row
    incomplete = []; groups = {}; draws = collections.defaultdict(set)
    temporal = collections.defaultdict(dict)
    for key, phases in pairs.items():
        frame, sequence, x, y = key
        if len(phases) != 2:
            incomplete.append(key); continue
        before, after = phases[0], phases[1]
        fields = ('shader','index_count','resource','format','resource_format','width','height','bytes')
        if any(before[n] != after[n] for n in fields):
            raise ValueError('Resource or draw identity changed inside a sample pair')
        mesh = {28632:183,21858:184}[int(after['index_count'])]
        name = PASSES[int(after['shader'])]
        group_key = (mesh,name,x,y)
        group = groups.setdefault(group_key,{'mesh':mesh,'pass':name,'x':x,'y':y,'pairs':0,
            'changed_pairs':0,'formats':set(),'after_min_rgb':[math.inf]*3,'after_max_rgb':[-math.inf]*3})
        group['pairs'] += 1
        group['changed_pairs'] += any(before[f'w{i}'] != after[f'w{i}'] for i in range(4))
        group['formats'].add(int(after['format']))
        for i,value in enumerate(after['rgba'][:3]):
            if math.isfinite(value):
                group['after_min_rgb'][i] = min(group['after_min_rgb'][i],value)
                group['after_max_rgb'][i] = max(group['after_max_rgb'][i],value)
        draws[(frame,sequence)].add((x,y))
        previous = temporal[group_key].get(frame)
        if previous is None or sequence > previous[0]:
            temporal[group_key][frame] = (sequence,after['rgba'])
    drops = []
    for (mesh,name,x,y),frames in temporal.items():
        for frame,(sequence,value) in frames.items():
            if frame-1 not in frames or frame+1 not in frames:
                continue
            previous, following = frames[frame-1][1], frames[frame+1][1]
            if not all(math.isfinite(v) for values in (previous,value,following) for v in values):
                continue
            baseline = min(max(previous[:3]),max(following[:3])); current = max(value[:3])
            if baseline > 0 and current < baseline:
                drops.append({'frame':frame,'sequence':sequence,'mesh':mesh,'pass':name,'x':x,'y':y,
                    'drop':baseline-current,'ratio':current/baseline,'rgb':value[:3],
                    'previous_rgb':previous[:3],'next_rgb':following[:3]})
    for group in groups.values():
        group['formats'] = sorted(group['formats'])
        for field in ('after_min_rgb','after_max_rgb'):
            group[field] = [v if math.isfinite(v) else None for v in group[field]]
    return {'events':dict(events),'events_other_than_samples':non_samples,
        'complete_draws':len(draws),'frame_count':len({frame for frame,_ in draws}),
        'incomplete_pairs':incomplete,'incomplete_draw_point_sets':[
            {'frame':key[0],'sequence':key[1],'points':len(value)} for key,value in draws.items() if len(value)!=16],
        'nonfinite_samples':nonfinite,'groups':list(groups.values()),
        'largest_single_frame_decreases':sorted(drops,key=lambda r:r['drop'],reverse=True)[:50],
        'lowest_single_frame_ratios':sorted(drops,key=lambda r:r['ratio'])[:50],
        'limitation':'Color-0 values around specific draws only. Unchanged values do not prove a draw was invisible. Copy barriers may affect timing; raw render-target values are not final presented colors. Temporal comparisons use the last matching draw per pass/frame.'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace_directory',type=Path)
    args = parser.parse_args()
    args.trace_directory.resolve().relative_to(Path(__file__).resolve().parents[5])
    report = analyze(args.trace_directory/'stages.csv')
    report['credit'] = json.loads((Path(__file__).parent/'sky-pixel-probe-build.json').read_text())['credit']
    (args.trace_directory/'stage-analysis.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ('events','complete_draws','frame_count','incomplete_pairs','incomplete_draw_point_sets','nonfinite_samples')}))
    print('Changed point/pass groups:',sum(g['changed_pairs']>0 for g in report['groups']))
