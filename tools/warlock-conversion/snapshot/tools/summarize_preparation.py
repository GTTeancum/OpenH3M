"""Correlate native output gaps with thresholded host preparation log intervals.

Overlap is evidence of concurrency, not proof that the preparation blocked
rendering: pipeline creation can run on worker threads.
"""
import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import re


def summarize(run):
    state = json.loads((run / 'run.json').read_text())
    start = state.get('started_unix_seconds')
    if start is None:
        start = json.loads((run / 'process-start.json').read_text())['started_unix_seconds']
    pattern = re.compile(r'^\[([^]]+)\].*\[preparation\] kind=(\w+) shader=(\w+) elapsed_ms=([\d.]+)')
    events = []
    for line in (run / 'runtime.log').read_text().splitlines():
        match = pattern.search(line)
        if not match:
            continue
        wall, kind, shader, duration = match.groups()
        end = datetime.fromisoformat(wall).timestamp() - start
        events.append({'kind': kind, 'shader': shader, 'elapsed_ms': float(duration),
                       'start_seconds': end - float(duration) / 1000, 'end_seconds': end})
    with (run / 'guest-frames.csv').open() as source:
        rows = list(csv.DictReader(source))
    hitches = []
    for a, b in zip(rows, rows[1:]):
        lo, hi = float(a['seconds']), float(b['seconds'])
        if hi - lo <= .060:
            continue
        hitches.append({'start_seconds': lo, 'end_seconds': hi,
                        'interval_ms': (hi - lo) * 1000,
                        'counter_delta': int(b['guest_frame_count']) - int(a['guest_frame_count']),
                        'overlapping_preparation': [e for e in events
                            if e['start_seconds'] <= hi and e['end_seconds'] >= lo]})
    return {'events': events, 'hitches': hitches,
            'caution': 'Log timestamps use the local Windows time zone. Clock alignment is approximate; overlapping worker-thread compilation does not prove a rendering dependency.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    report = summarize(args.run)
    (args.run / 'preparation-summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'logged_preparation_events': len(report['events']),
                      'hitches': report['hitches']}, indent=2))
