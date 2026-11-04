"""Decode sparse numeric GPU samples; flag temporal changes, not rendering causes."""
import argparse
import collections
import csv
import json
from pathlib import Path


def channels(value, fmt, swizzle):
    if fmt == 24:  # DXGI_FORMAT_R10G10B10A2_UNORM
        source = [(value >> shift & 1023) / 1023 for shift in (0, 10, 20)]
        source.append((value >> 30 & 3) / 3)
    elif fmt in (28, 87):  # R8G8B8A8_UNORM / B8G8R8A8_UNORM
        source = [(value >> shift & 255) / 255 for shift in (0, 8, 16, 24)]
        if fmt == 87:
            source[0], source[2] = source[2], source[0]
    else:
        raise ValueError(f'Unsupported DXGI format {fmt}')
    source.extend((0.0, 1.0))
    mapping = [(swizzle >> (3*i)) & 7 for i in range(4)]
    if any(i > 5 for i in mapping):
        raise ValueError('Invalid component mapping')
    return tuple(source[i] for i in mapping)


def analyze(rows):
    frames = collections.defaultdict(dict)
    events = collections.Counter()
    exceptions = []
    for row in rows:
        events[row['event']] += 1
        if row['event'] != 'sample':
            exceptions.append(row)
            continue
        frame, x, y = (int(row[k]) for k in ('frame', 'x', 'y'))
        width, height = (int(row[k]) for k in ('width', 'height'))
        if not 0 <= x < width or not 0 <= y < height:
            raise ValueError('Sample outside active viewport')
        key = (width, height, x, y)
        if key in frames[frame]:
            raise ValueError('Duplicate sample coordinate in one frame')
        frames[frame][key] = channels(int(row['packed_pixel']), int(row['format']), int(row['swizzle']))
    ordered = sorted(frames)
    holes = sorted(set(range(ordered[0], ordered[-1]+1)) - set(ordered)) if ordered else []
    dark_pulses = []
    decreases = []
    for frame in ordered:
        # Never bridge dropped frames or compare different viewport dimensions.
        if frame-1 not in frames or frame+1 not in frames:
            continue
        for key, rgba in frames[frame].items():
            before, after = frames[frame-1].get(key), frames[frame+1].get(key)
            if before is None or after is None:
                continue
            current = max(rgba[:3])
            baseline = min(max(before[:3]), max(after[:3]))
            if baseline > current:
                width, height, x, y = key
                decreases.append({'frame':frame,'x':x,'y':y,'u':x/width,'v':y/height,
                    'drop':baseline-current,'ratio':current/baseline,
                    'rgb':rgba[:3],'previous_rgb':before[:3],'next_rgb':after[:3]})
            if baseline >= 0.03 and current <= 0.01 and current <= baseline * 0.15:
                width, height, x, y = key
                dark_pulses.append({'frame': frame, 'x': x, 'y': y,
                    'u': x/width, 'v': y/height, 'rgb': rgba[:3],
                    'previous_rgb': before[:3], 'next_rgb': after[:3]})
    return {'events': dict(events), 'frame_count': len(ordered),
        'first_frame': ordered[0] if ordered else None,
        'last_frame': ordered[-1] if ordered else None,
        'missing_frame_ids': holes,
        'incomplete_sample_grids': {f: len(points) for f, points in frames.items() if len(points) != 144},
        'dark_pulses': dark_pulses,
        'largest_single_frame_decreases':sorted(decreases,key=lambda row:row['drop'],reverse=True)[:50],
        'events_other_than_samples': exceptions,
        'limitation': '144 isolated pre-presentation-gamma/FXAA texels per sampled frame. Sparse sampling can miss small or brief artifacts. A dark pulse is a numerical observation, not proof of a rendering defect or its cause.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--stage',choices=('before_host_effects','after_host_effects'),default='before_host_effects')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[5]
    args.output.resolve().relative_to(repo)
    with args.csv.open(newline='') as stream:
        report = analyze(csv.DictReader(stream))
    report['measurement_stage']=args.stage
    if args.stage=='after_host_effects':
        report['limitation']='144 isolated native guest-output texels after host gamma/FXAA, before presenter scaling and desktop composition. Sparse samples can miss artifacts; dark values do not establish a defect or its cause.'
    report['credit'] = json.loads((Path(__file__).parent/'sky-pixel-probe-build.json').read_text())['credit']
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('events','frame_count','first_frame','last_frame','missing_frame_ids','incomplete_sample_grids')}))
    print('Isolated dark sample pulses:', len(report['dark_pulses']))
