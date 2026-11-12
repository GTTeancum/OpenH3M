"""Exercise original H4 marker curves; this does not simulate particle lifetime."""
import csv
import hashlib
import json
import math
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'work/h4-forge-research/isolated'
fields = json.loads((WORK / 'marker-effect-fields.json').read_text())
curves = []
for tag in ('16658', '16660'):
    for offset, name in (('88', 'aspect'), ('A8', 'color'), ('C8', 'intensity'),
                         ('E8', 'alpha'), ('110', 'frame'), ('130', 'animation_rate'),
                         ('150', 'palette')):
        curves.append((f'{tag}/{name}', bytes.fromhex(fields[tag]['fields'][f'Unknown@0x{offset}'])))
systems = fields['16657']['fields']['Events@0x34'][0]['Particle Systems@0x38']
for index, system in enumerate(systems):
    for key, value in system['Emitters@0x68'][0].items():
        if key.startswith('Function@'):
            curves.append((f'emitter{index}/{key}', bytes.fromhex(value)))

fixture = WORK / 'marker-curves.bin'
fixture.write_bytes(struct.pack('<4sI', b'H4CF', len(curves)) + b''.join(
    struct.pack('<I', len(data)) + data for _, data in curves))
output = WORK / 'marker-curves.csv'
subprocess.run([str(WORK / 'check_marker_curves.exe'),
                str(ROOT / 'work/h4-forge-research/h4-image.bin'), str(fixture), str(output)],
               cwd=ROOT, check=True, timeout=60)
rows = list(csv.DictReader(output.open()))
assert len(rows) == len(curves)*645
summaries = []
for index, (name, data) in enumerate(curves):
    samples = [r for r in rows if int(r['curve']) == index]
    assert len(samples) == 645
    colors = [[float(r[c]) for c in ('r', 'g', 'b')] for r in samples]
    assert all(math.isfinite(v) for rgb in colors for v in rgb)
    # Independent endpoint expectations: constant/identity scalar functions
    # store their authored range at +4/+8. Other curves are reported rather
    # than falsely validated by an invented replacement spline evaluator.
    verified = 0
    if data[2] == 0 and data[0] in (0, 1):
        lo, hi = struct.unpack_from('>2f', data, 4)
        for row, rgb in zip(samples, colors):
            fraction = float(row['input']) if data[0] == 0 else (
                float(row['range']) if data[1] & 1 else 0)
            expected = lo+(hi-lo)*fraction
            assert abs(rgb[0]-expected) < 2e-6, (name, row, expected)
            verified += 1
    if data[2] == 1 and data[0] == 1:
        expected = [b/255 for b in data[5:8]]
        assert all(abs(rgb[i]-expected[i]) < 1e-6 for rgb in colors for i in range(3))
        verified = len(samples)
    summaries.append(dict(name=name, function_sha256=hashlib.sha256(data).hexdigest(),
        minimum=[min(rgb[i] for rgb in colors) for i in range(3)],
        maximum=[max(rgb[i] for rgb in colors) for i in range(3)],
        independently_checked_samples=verified))
report = dict(sample_count=len(rows),
    original_code=json.loads((WORK/'extraction.json').read_text())['functions'],
    fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
    output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(), curves=summaries,
    limitations='Supplied normalized input/range values; particle input selection, emission, lifetime, fades and vertex interpolation remain to be integrated. Complex curves have original execution and finite-output evidence, not an independent numerical oracle.')
(WORK/'marker-curves-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(f'PASS: {len(rows)} finite samples; {sum(r["independently_checked_samples"] for r in summaries)} constant/identity samples independently checked')
for row in summaries:
    if '/intensity' in row['name'] or '/color' in row['name'] or '0x298' in row['name']:
        print(row['name'], row['minimum'], row['maximum'])
