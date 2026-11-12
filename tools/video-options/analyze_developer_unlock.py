"""Summarize actual guest outputs and observed simulation ticks by toggle phase."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re

p = argparse.ArgumentParser()
p.add_argument('run', type=Path)
a = p.parse_args()
phases = [{'mode': 'OFF-before', 'fps': [], 'simulation': []}]
for line in (a.run / 'runtime.log').read_text(errors='replace').splitlines():
    if 'Developer framerate unlock ON:' in line:
        phases.append({'mode': 'ON', 'fps': [], 'simulation': []})
    elif 'Developer framerate unlock OFF:' in line:
        phases.append({'mode': 'OFF-after', 'fps': [], 'simulation': []})
    stamp = re.match(r'\[([^]]+)\]', line)
    if not stamp:
        continue
    timestamp = datetime.fromisoformat(stamp[1]).timestamp()
    m = re.search(r'guest-output FPS [\d.]+ \((\d+) frames / ([\d.]+)s\)', line)
    if m:
        phases[-1]['fps'].append([timestamp, int(m[1]), float(m[2])])
    m = re.search(r'\[dev-simulation\].*wall_ms=(\d+) initialized=1 rate=30 ticks=(\d+) speed=1(?:\s|$)', line)
    if m:
        phases[-1]['simulation'].append([int(m[1]), int(m[2])])
result = []
for phase in phases:
    # Use the final 10 samples of each phase, avoiding toggle/load transitions.
    frames = phase['fps'][-10:]
    simulation = phase['simulation'][-10:]
    row = dict(mode=phase['mode'], frame_samples=len(frames), simulation_samples=len(simulation))
    if frames:
        row['guest_output_fps'] = sum(x[1] for x in frames) / sum(x[2] for x in frames)
    if len(simulation) >= 2:
        wall = (simulation[-1][0] - simulation[0][0]) / 1000
        ticks = simulation[-1][1] - simulation[0][1]
        row.update(wall_seconds=wall, ticks=ticks, ticks_per_second=ticks / wall)
    result.append(row)
report = {'phases': result, 'scope': 'Final 10 samples per phase; inspect captures and loading state separately. Not a network compatibility test.'}
(a.run / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
