"""Encode the portable pose for the opt-in native reproduction harness."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('run_directory', type=Path)
args = parser.parse_args()
reference = Path(__file__).resolve().parent
repo = reference.parents[4]
run = args.run_directory.resolve(strict=True)
run.relative_to(repo / 'work/sky-bridge')
pose = json.loads((reference / 'candidate32-flicker-reproduction-view.json').read_text())
player, vehicle = pose['player_and_parent_chain']
if vehicle['position_space'] != 'world' or player['parent_handle'] != vehicle['recorded_handle']:
    raise ValueError('Unexpected attachment chain')
if hashlib.sha256((repo / 'work/sky-bridge/payload-32/sky_bridge.map').read_bytes()).hexdigest() != pose['map_sha256']:
    raise ValueError('Reproduction map changed')
observer = bytes.fromhex(pose['camera']['raw_observer_result'])
if len(observer) != 112:
    raise ValueError('Unexpected observer result size')
data = struct.pack('<5I', 0x52594b53, 1, pose['map_id'],
                   int(vehicle['tag_datum'], 16), int(player['tag_datum'], 16))
data += observer
data += struct.pack('<9f', *(vehicle['position'] + vehicle['forward'] + vehicle['up']))
destination = run / 'pose.bin'
if destination.exists() and destination.read_bytes() != data:
    raise ValueError('Existing pose differs; use a fresh run directory')
destination.write_bytes(data)
print(json.dumps({'path': str(destination), 'bytes': len(data),
                  'sha256': hashlib.sha256(data).hexdigest()}))
