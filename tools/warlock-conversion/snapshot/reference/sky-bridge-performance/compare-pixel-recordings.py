"""Compare same-coordinate sample distributions without aligning simulation time."""
import argparse
import collections
import csv
import importlib.util
import json
from pathlib import Path
import statistics

ref = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pixel_probe', ref/'read-pixel-probe.py')
pixel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pixel)


def read(path):
    points = collections.defaultdict(list)
    seen = set()
    with path.open(newline='') as stream:
        for row in csv.DictReader(stream):
            if row['event'] != 'sample':
                continue
            key = tuple(int(row[k]) for k in ('width', 'height', 'x', 'y'))
            identity = (int(row['frame']), key)
            if identity in seen:
                raise ValueError('Duplicate sample')
            seen.add(identity)
            points[key].append(pixel.channels(int(row['packed_pixel']),
                int(row['format']), int(row['swizzle']))[:3])
    return points


def describe(values):
    return {name: [fn(v[i] for v in values) for i in range(3)]
            for name, fn in [('median', statistics.median), ('min', min), ('max', max)]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('human_csv', type=Path)
    parser.add_argument('replay_csv', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.resolve().relative_to(ref.parents[4])
    human, replay = read(args.human_csv), read(args.replay_csv)
    if human.keys() != replay.keys() or not human:
        raise ValueError('Sample coordinate grids do not match')
    rows = []
    for key in sorted(human):
        a, b = describe(human[key]), describe(replay[key])
        rows.append({'width': key[0], 'height': key[1], 'x': key[2], 'y': key[3],
            'human_samples': len(human[key]), 'replay_samples': len(replay[key]),
            'human': a, 'replay': b,
            'max_median_channel_difference': max(abs(x-y) for x, y in zip(a['median'], b['median'])),
            'channel_range_overlap': [max(a['min'][i], b['min'][i]) <= min(a['max'][i], b['max'][i]) for i in range(3)]})
    upper_right = [v for v in rows if 756 <= v['x'] <= 1044 and 128 <= v['y'] <= 256]
    report = {'human_csv': str(args.human_csv), 'replay_csv': str(args.replay_csv),
        'matched_points': len(rows), 'upper_right_points': upper_right,
        'largest_median_differences': sorted(rows, key=lambda v: v['max_median_channel_difference'], reverse=True)[:20],
        'points': rows,
        'limitation': 'Compares distributions at identical coordinates and decoded component mappings. Does not align simulation phase or prove complete visual equivalence. Both inputs must measure the same rendering stage.',
        'credit': json.loads((ref/'sky-pixel-probe-build.json').read_text())['credit']}
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'matched_points': len(rows), 'upper_right_points': len(upper_right),
        'upper_right_max_median_difference': max(v['max_median_channel_difference'] for v in upper_right) if upper_right else None}))
