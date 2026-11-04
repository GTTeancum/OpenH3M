"""Validate full-region numeric aggregates and locate temporal darkening."""
import argparse
import collections
import csv
import json
import math
from pathlib import Path


def analyze(path):
    frames = collections.defaultdict(dict)
    events = collections.Counter()
    exceptions = []
    with path.open(newline='') as stream:
        for row in csv.DictReader(stream):
            events[row['event']] += 1
            if row['event'] != 'sample':
                exceptions.append(row)
                continue
            integers = ('frame', 'pulse_frame', 'tile', 'x', 'y', 'width', 'height',
                        'count', 'dark_count', 'fall_count', 'pulse_count',
                        'black_pulse_count', 'worst_x', 'worst_y')
            value = {k: int(row[k]) for k in integers}
            if 'recorded_ns' in row:
                value.update({k: int(row[k]) for k in ('recorded_ns', 'format', 'viewport_width', 'viewport_height')})
            for key in ('mean_max', 'min_max', 'max_max', 'worst_pulse_drop',
                        'worst_before', 'worst_current', 'worst_after'):
                value[key] = float(row[key])
                if not math.isfinite(value[key]) or not 0 <= value[key] <= 1:
                    raise ValueError('Invalid aggregate color statistic')
            frame, tile = value['frame'], value['tile']
            if tile not in range(32) or tile in frames[frame]:
                raise ValueError('Invalid or duplicate tile')
            if value['count'] != value['width'] * value['height'] or value['count'] <= 0:
                raise ValueError('Tile dimensions do not match contribution count')
            for key in ('dark_count', 'fall_count', 'pulse_count', 'black_pulse_count'):
                if not 0 <= value[key] <= value['count']:
                    raise ValueError('Invalid event pixel count')
            frames[frame][tile] = value
    incomplete = {f: len(v) for f, v in frames.items() if len(v) != 32}
    summaries = []
    shapes = set()
    metadata = []
    for frame, tiles in sorted(frames.items()):
        if len(tiles) != 32:
            continue
        left = min(v['x'] for v in tiles.values())
        top = min(v['y'] for v in tiles.values())
        right = max(v['x'] + v['width'] for v in tiles.values())
        bottom = max(v['y'] + v['height'] for v in tiles.values())
        width, height = right-left, bottom-top
        for tile, value in tiles.items():
            tx, ty = tile % 8, tile // 8
            x0, x1 = (tx*width+7)//8, ((tx+1)*width+7)//8
            y0, y1 = (ty*height+3)//4, ((ty+1)*height+3)//4
            if (value['x'], value['y'], value['width'], value['height']) != (left+x0, top+y0, x1-x0, y1-y0):
                raise ValueError('Tiles do not partition the complete region')
        shapes.add((left, top, right, bottom))
        pulses = {v['pulse_frame'] for v in tiles.values()}
        if len(pulses) != 1 or next(iter(pulses)) not in (-1, frame-1):
            raise ValueError('Inconsistent pulse frame association')
        count = sum(v['count'] for v in tiles.values())
        if count != width*height:
            raise ValueError('Incomplete region contribution count')
        if 'recorded_ns' in next(iter(tiles.values())):
            frame_metadata = {tuple(v[k] for k in ('recorded_ns', 'format', 'viewport_width', 'viewport_height')) for v in tiles.values()}
            if len(frame_metadata) != 1:
                raise ValueError('Inconsistent frame metadata')
            ns, fmt, vw, vh = frame_metadata.pop()
            if fmt not in (24, 28, 87) or not 0 <= left < right <= vw or not 0 <= top < bottom <= vh:
                raise ValueError('Invalid format or viewport')
            if metadata and ns <= metadata[-1]['recorded_ns']:
                raise ValueError('Non-monotonic recording timestamps')
            metadata.append({'frame': frame, 'recorded_ns': ns, 'format': fmt, 'viewport_width': vw, 'viewport_height': vh})
        worst = max(tiles.values(), key=lambda v: v['worst_pulse_drop'])
        summaries.append({'frame': frame, 'pulse_frame': next(iter(pulses)),
            'pixel_count': count,
            'mean_max': sum(v['mean_max']*v['count'] for v in tiles.values())/count,
            **{k: sum(v[k] for v in tiles.values()) for k in
               ('dark_count', 'fall_count', 'pulse_count', 'black_pulse_count')},
            'worst': {k: worst[k] for k in ('tile', 'worst_pulse_drop', 'worst_x',
                      'worst_y', 'worst_before', 'worst_current', 'worst_after')}})
    order = sorted(frames)
    return {'events': dict(events), 'events_other_than_samples': exceptions,
        'frame_count': len(order), 'frame_range': [order[0], order[-1]] if order else [],
        'missing_frame_ids': sorted(set(range(order[0], order[-1]+1))-set(order)) if order else [],
        'incomplete_frames': incomplete, 'region_bounds': sorted(shapes),
        'frame_metadata': metadata,
        'total_pixel_contributions': sum(v['pixel_count'] for v in summaries),
        'black_pulse_frames': [v for v in summaries if v['black_pulse_count']],
        'largest_pulse_frames': sorted(summaries, key=lambda v: v['pulse_count'], reverse=True)[:30],
        'largest_falls': sorted(summaries, key=lambda v: v['fall_count'], reverse=True)[:30],
        'frames': summaries,
        'limitation': 'Every texel in the stated region contributes to numeric statistics after host gamma/FXAA. No pixel image is saved. A temporal darkening or black pulse may be authored animation or occlusion; it is not proof of a defect or its cause. Presenter scaling and desktop composition are outside this measurement.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace_directory', type=Path)
    parser.add_argument('--swapchain', action='store_true')
    args = parser.parse_args()
    ref = Path(__file__).resolve().parent
    args.trace_directory.resolve().relative_to(ref.parents[4])
    report = analyze(args.trace_directory/('swapchain-region.csv' if args.swapchain else 'region.csv'))
    report['measurement_stage'] = 'application_swapchain' if args.swapchain else 'guest_output_after_host_effects'
    if args.swapchain:
        report['limitation'] = 'Every texel in the stated application-owned swapchain region contributes after presenter scaling/sharpening and UI composition, before DXGI Present and desktop composition. Frame IDs are paint submissions, not guest frames. Numeric darkening alone does not establish a rendering defect or its cause. No image is saved.'
    report['credit'] = json.loads((ref/'sky-pixel-probe-build.json').read_text())['credit']
    (args.trace_directory/('swapchain-region-analysis.json' if args.swapchain else 'region-analysis.json')).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('events', 'frame_count', 'frame_range',
        'missing_frame_ids', 'incomplete_frames', 'region_bounds', 'total_pixel_contributions')}))
    print('Frames with isolated near-black pixel transitions:', len(report['black_pulse_frames']))
