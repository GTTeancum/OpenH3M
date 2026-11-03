"""Attribute slow replay batches without treating wall time as CPU time."""
import collections
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
names = json.loads(Path(__file__).with_name('deferred-command-ids.json').read_text())
lines = sorted(line for path in root.glob('*runtime*.log')
               for line in path.read_text(errors='replace').splitlines())
rows = []
last_present_ms = None
for line in lines:
    values = dict(re.findall(r'(\w+)=([\w.\-]+)', line))
    if '[host-present]' in line:
        last_present_ms = float(values['elapsed_ms'])
    if '[deferred-replay]' not in line:
        continue
    rows.append(dict(log_timestamp=line[1:24], preceding_present_ms=last_present_ms,
                     commands=int(values['commands']), bytes=int(values['bytes']),
                     batch_ms=float(values['batch_ms']), calls_ms=float(values['calls_ms']),
                     max_call_ms=float(values['max_call_ms']),
                     slowest_command=names.get(values['slowest_command'], 'unknown')))
active = [r for r in rows if r['preceding_present_ms'] is not None
          and 115000 <= r['preceding_present_ms'] < 155000]
report = dict(source_directory=str(root), slow_batch_count=len(rows),
              later_slow_batch_count=len(active),
              later_slowest_command_counts=dict(collections.Counter(r['slowest_command'] for r in active)),
              later_batches=sorted(active, key=lambda r: r['batch_ms'], reverse=True),
              all_slow_batches=rows,
              limitations=['Only batches of at least 5 ms are logged.',
                           'Window association uses the preceding host present, not a GPU frame ID.',
                           'Wall time includes scheduling delays and instrumentation; it does not prove driver CPU cost.',
                           'Batch and individual-call times overlap and must not be added.'])
(root / 'deferred-replay-summary.json').write_text(json.dumps(report, indent=2))
print(json.dumps({k: v for k, v in report.items() if k not in ('all_slow_batches', 'later_batches')}, indent=2))
print(json.dumps(report['later_batches'][:8], indent=2))
