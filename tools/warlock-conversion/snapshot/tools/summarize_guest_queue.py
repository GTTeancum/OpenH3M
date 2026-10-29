"""Summarize observed D3D queue deadlines; does not verify scene or physical flips."""
import argparse
import collections
import csv
import json
from pathlib import Path


def summarize(path):
    with path.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    entries = {}
    conflicts = set()
    completions = []
    previous = None
    inconsistent = 0
    for row in rows:
        if float(row['seconds']) < 125:
            continue
        head, tail = int(row['head']), int(row['tail'])
        if head > tail or tail - head > 16:
            # Cross-thread snapshots are not atomic. Never reinterpret a torn
            # snapshot as a huge backlog (or silently mask it modulo 16).
            inconsistent += 1
            continue
        for ordinal in range(max(0, tail - 16), tail):
            slot = ordinal % 16
            target = int(row[f'slot_{slot}_target_vblank'])
            if ordinal in entries and entries[ordinal] != target:
                conflicts.add(ordinal)
            entries[ordinal] = target
        completed = int(row['completed'])
        if previous is not None and completed != previous['completed']:
            completions.append({'vblank_delta': int(row['vblank']) - previous['vblank'],
                                'completed_delta': completed - previous['completed']})
        if previous is None or completed != previous['completed']:
            previous = {'completed': completed, 'vblank': int(row['vblank'])}
    deltas = collections.Counter()
    for ordinal in sorted(entries):
        if ordinal in conflicts or ordinal - 1 in conflicts:
            continue
        if ordinal - 1 in entries:
            deltas[entries[ordinal] - entries[ordinal - 1]] += 1
    return {'scene_verified_by_this_tool': False,
            'snapshot_caveat': 'Read-only cross-thread snapshots; not atomic; not physical flips.',
            'distinct_queue_entries': len(entries), 'conflicting_entries': len(conflicts),
            'inconsistent_snapshots': inconsistent,
            'requested_target_spacing_vblanks': dict(sorted(deltas.items())),
            'observed_completion_spacing_vblanks': dict(sorted(collections.Counter(
                x['vblank_delta'] for x in completions if x['completed_delta'] == 1).items())),
            'multi_completion_observations': sum(x['completed_delta'] != 1 for x in completions)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    result = summarize(args.run / 'guest-queue.csv')
    content = json.dumps(result, indent=2)
    (args.run / 'guest-queue-summary.json').write_text(content + '\n')
    print(content)
