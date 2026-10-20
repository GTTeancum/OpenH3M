"""Summarize native frame-counter timing; flag lost samples instead of hiding them."""
import argparse
import csv
import json
from pathlib import Path
import statistics


def summarize(run):
    rows = [r for r in csv.DictReader((run / 'guest-frames.csv').open()) if float(r['seconds']) >= 125]
    if not rows or all(abs(float(r['seconds']) * 1000 - round(float(r['seconds']) * 1000)) < .001 for r in rows):
        raise ValueError('Missing or quantized timestamps; require high-resolution counter capture')
    intervals, skipped = [], 0
    for a, b in zip(rows, rows[1:]):
        delta = int(b['guest_frame_count']) - int(a['guest_frame_count'])
        if delta != 1:
            skipped += max(1, delta - 1)
            continue
        intervals.append(1000 * (float(b['seconds']) - float(a['seconds'])))
    if len(intervals) < 100:
        raise ValueError('Insufficient native frame samples')
    ordered = sorted(intervals)
    def percentile(q): return round(ordered[round((len(ordered) - 1) * q)], 3)
    state = json.loads((run / 'run.json').read_text())
    return {'run': str(run), 'mode': state['mode'], 'stock': state.get('stock', False),
            'map_sha256': state['map_sha256'], 'metric': 'new guest-output frames, not host presents',
            'settled_gameplay_start_seconds': 125,
            'intervals': len(intervals), 'skipped_frames': skipped,
            'mean_ms': round(statistics.mean(intervals), 3),
            'stdev_ms': round(statistics.pstdev(intervals), 3),
            'p05_ms': percentile(.05), 'p50_ms': percentile(.5),
            'p95_ms': percentile(.95), 'p99_ms': percentile(.99),
            'under_25_ms': sum(x < 25 for x in intervals),
            'over_41_667_ms': sum(x > 41.667 for x in intervals),
            'max_observation_poll_gap_ms': round(max(float(r['poll_gap_ms']) for r in rows), 3),
            'caution': 'Polling introduces up to the observation gap in timing uncertainty. Display cadence is separate.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    report = summarize(args.run)
    (args.run / 'native-summary.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
