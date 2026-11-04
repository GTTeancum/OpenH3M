"""Extract numeric native observer inputs without restoring pointers or handles."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('run_directory', type=Path)
args = parser.parse_args()
ref = Path(__file__).resolve().parent
repo = ref.parents[4]
run = args.run_directory.resolve(strict=True)
run.relative_to(repo / 'work/sky-bridge')
source = repo / 'work/sky-bridge/pixel-probe-20261103-203123/reproduction-view-full/guest-snapshot.json'
snapshot = json.loads(source.read_text())
tls = bytes.fromhex(snapshot['blobs']['tls']['bytes'])
observer_address = struct.unpack_from('>I', tls, 0x2cc)[0]
blob = snapshot['blobs']['observer']
offset = observer_address - int(blob['guest_address'], 16)
raw = bytes.fromhex(blob['bytes'])
if offset < 0 or offset + 448 > len(raw):
    raise ValueError('Native observer command outside captured allocation')
command = raw[offset+384:offset+448]
if raw[offset+16:offset+80] != command:
    raise ValueError('Saved observer target has not settled to its current command')
values = struct.unpack('>16f', command)
if not all(math.isfinite(x) for x in values):
    raise ValueError('Non-finite observer command')
pose = json.loads((ref/'candidate32-flicker-reproduction-view.json').read_text())
if list(values[10:13]) != pose['camera']['forward'] or list(values[13:16]) != pose['camera']['up']:
    raise ValueError('Saved native command basis differs from recorded view')
if values[9] != pose['camera']['horizontal_fov_radians']:
    raise ValueError('Saved native command FOV differs from recorded view')
destination = run/'observer-command.bin'
if destination.exists() and destination.read_bytes() != command:
    raise ValueError('Existing command differs; use a fresh run directory')
destination.write_bytes(command)
report = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'observer_address': hex(observer_address), 'captured_blob_offset': offset,
          'captured_current_user_offset': 380, 'captured_current_global_offset': 384,
          'target_user_offset': 12, 'target_global_offset': 16,
          'values': values, 'bytes': len(command),
          'sha256': hashlib.sha256(command).hexdigest(),
          'consumer': 'sub_82214930, before native interpolation and sub_82214BC0',
          'limitation': 'Numeric camera command from the later saved human snapshot, not a complete savestate.'}
(run/'observer-command.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
