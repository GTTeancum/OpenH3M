"""Report fixed startup-inclusive and later windows without hiding outliers."""
import collections
import json
import re
import statistics
import sys
from pathlib import Path


def analyze(root):
    lines = sorted(line for path in root.glob('*runtime*.log')
                   for line in path.read_text(errors='replace').splitlines())
    points = []
    for index, line in enumerate(lines):
        if '[host-present]' not in line:
            continue
        values = dict(re.findall(r'(\w+)=([\w.\-]+)', line))
        elapsed, frame = float(values['elapsed_ms']), int(values['guest_painted'])
        if not points or frame != points[-1][2]:
            points.append((index, elapsed, frame))
    windows = []
    for start, end in [(110, 155), (115, 155), (120, 150)]:
        selected = [p for p in points if start * 1000 <= p[1] <= end * 1000]
        gaps = sorted(b[1] - a[1] for a, b in zip(selected, selected[1:])
                      if b[2] == a[2] + 1)
        if not gaps:
            windows.append(dict(start=start, end=end, status='insufficient samples'))
            continue
        windows.append(dict(start=start, end=end, frames=len(selected),
                            actual_start_ms=selected[0][1], actual_end_ms=selected[-1][1],
                            fps=(selected[-1][2] - selected[0][2]) * 1000 /
                            (selected[-1][1] - selected[0][1]),
                            median_ms=statistics.median(gaps),
                            p95_ms=gaps[int(.95 * (len(gaps) - 1))],
                            maximum_ms=max(gaps), over_50ms=sum(g > 50 for g in gaps)))
    hitches = []
    for a, b in zip(points, points[1:]):
        if a[1] < 115000 or b[1] > 155000 or b[1] - a[1] <= 45:
            continue
        between = lines[a[0]:b[0] + 1]
        hitches.append(dict(start_ms=a[1], interval_ms=b[1] - a[1],
                            events=[line for line in between if any(key in line for key in
                                    ('[host-phase]', '[queue-wait]', '[draw-phase]', '[preparation]'))],
                            query_log_lines=sum('viz query ID' in line for line in between)))
    return dict(run=str(root), windows=windows, hitches=hitches,
                line_counts=dict(collections.Counter('query' if 'viz query ID' in line
                                                     else 'other' for line in lines)),
                limitation='Host diagnostic timing only. Later windows supplement the full window; '
                           'they do not establish full-map traversal or visual acceptance.')


if __name__ == '__main__':
    root = Path(sys.argv[1])
    report = analyze(root)
    (root / 'pacing-windows.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != 'hitches'}, indent=2))
