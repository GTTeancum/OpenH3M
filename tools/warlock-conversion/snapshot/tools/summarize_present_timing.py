"""Summarize host-observed guest frame changes, retaining long stalls."""
import argparse
import json
import re
import statistics
from pathlib import Path


def summarize(path, start_ms, captures, end_ms=float('inf')):
    samples = []
    for line in path.open(errors='replace'):
        if '[host-present]' not in line:
            continue
        values = dict(re.findall(r'(\w+)=([\w.]+)', line))
        time = float(values['elapsed_ms'])
        frame = int(values['guest_painted'])
        if not samples or frame != samples[-1][1]:
            samples.append((time, frame))
    gaps, capture_intervals, frame_jumps = [], 0, 0
    for before, after in zip(samples, samples[1:]):
        if before[0] < start_ms or after[0] > end_ms or after[1] <= before[1]:
            continue
        # Exclude intervals intersecting a capture, not just endpoint samples.
        if any(before[0] <= capture + 1000 and after[0] >= capture - 1000
               for capture in captures):
            capture_intervals += 1
            continue
        gaps.append(after[0] - before[0])
        frame_jumps += max(0, after[1] - before[1] - 1)
    if not gaps:
        raise ValueError('No guest frame-change intervals in selected window')
    ordered = sorted(gaps)
    return dict(run=str(path.parent), start_ms=start_ms, samples=len(gaps),
                scope='Host-observed guest image changes; does not establish traversal or console performance',
                median_ms=statistics.median(gaps),
                p95_ms=ordered[int(.95 * (len(ordered) - 1))],
                p99_ms=ordered[int(.99 * (len(ordered) - 1))],
                max_ms=max(gaps), over_50_ms=sum(x > 50 for x in gaps),
                over_100_ms=sum(x > 100 for x in gaps),
                over_1000_ms=sum(x > 1000 for x in gaps),
                unobserved_guest_frames=frame_jumps,
                capture_intervals_excluded=capture_intervals)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--start-ms', type=float, default=110000)
    parser.add_argument('--end-ms', type=float, default=float('inf'))
    parser.add_argument('--captures', type=float, nargs='*', default=[])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.run / 'trace-runtime.log', args.start_ms, args.captures, args.end_ms)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
