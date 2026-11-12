"""Verify the native Bank1x1 pitch-cancel/delete regression's retained evidence."""
import argparse
import csv
import json
import math
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('run', type=Path)
args = parser.parse_args()
run = args.run.resolve(strict=True)
run.relative_to(ROOT)
log = (run / 'trace-runtime.log').read_text(errors='replace')
cancelled = re.findall(r'Advanced Forge numeric preview cancelled: ([0-9A-F]+)', log)
if len(cancelled) != 1:
    raise ValueError(f'Expected one cancelled numeric preview, got {cancelled}')
datum = int(cancelled[0], 16)
previews = [(int(d, 16), int(row), int(choice)) for d, row, choice in re.findall(
    r'Advanced Forge numeric preview: ([0-9A-F]+) row (\d+) choice (\d+)', log)]
if previews != [(datum, 5, 181), (datum, 5, 182)]:
    raise ValueError(f'Expected pitch1 then2 previews on the same object: {previews}')
if re.search(r'Advanced Forge (?:numeric preview|native coordinates) (?:accepted|selected):', log):
    raise ValueError('The cancellation route unexpectedly committed an edit')
if re.search(r'(?:Original scenery|Advanced Forge)[^\n]*(?:failed:|disabled:)', log):
    raise ValueError('Runtime reported an editor failure')
poses = []
with (run / 'forge-scene.bin.native.csv').open(newline='') as stream:
    for row in csv.reader(stream):
        if int(row[1]) == datum:
            poses.append(tuple(map(float, row[3:12])))
if not poses:
    raise ValueError('No native serialized transform after cancellation')
restored = poses[-1]
before_preview = log.split('Advanced Forge numeric preview:', 1)[0]
prior_positions = re.findall(
    rf'Forge held flow: tick \d+ held {datum:08X} [^\n]* pose ([^ ]+) candidates', before_preview)
if not prior_positions:
    raise ValueError('Missing pre-preview held position')
original_position = tuple(map(float, prior_positions[-1].split(',')))
if len(original_position) != 3 or any(abs(a-b) > 0.0001
        for a, b in zip(restored[:3], original_position)):
    raise ValueError('Cancellation did not retain the pre-preview position')
expected_axes = (1., 0., 0., 0., 0., 1.)
if not all(math.isfinite(v) for v in restored) or any(
        abs(a-b) > 0.0001 for a, b in zip(restored[3:], expected_axes)):
    raise ValueError(f'Cancelled pitch did not restore the original basis: {restored}')
data = (run / 'native-variant.bin').read_bytes()
if len(data) != 0xe090 or struct.unpack_from('>H', data, 0xf8)[0] != 12:
    raise ValueError('Not an ordinary native H3 version12 variant')
remaining = []
for slot in range(640):
    offset = 0x130 + slot * 0x54
    if not struct.unpack_from('>H', data, offset)[0] & 1:
        continue
    identity = struct.unpack_from('>I', data, offset+4)[0]
    quota = struct.unpack_from('>i', data, offset+12)[0]
    if quota < -1 or quota >= 256:
        raise ValueError('Invalid native quota index')
    tag = struct.unpack_from('>I', data, 0xd34c+quota*12)[0] if quota >= 0 else None
    if identity == datum or tag == 0x90002937:
        remaining.append(slot)
if remaining:
    raise ValueError(f'Deleted Bank1x1 still occupies native slots: {remaining}')
report = dict(result='NATIVE_RECORDS_PASS', visual_status='REQUIRES_SEPARATE_INSPECTION', datum=f'{datum:08X}', previews=previews,
              restored_pose=restored, deleted_from_native_variant=True,
              limitation='Native menu/record evidence; inspect captures separately. This does not prove every cancellation or deletion path.')
(run / 'cancel-delete-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
