"""Extract numeric in-process controller states from an existing runtime trace."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import statistics
import struct

from build_scenario_checkpoint import output_path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--project', type=Path, required=True)
parser.add_argument('--log', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
project = args.project.resolve(strict=True)
source = args.log.resolve(strict=True)
source.relative_to(project)
dest = output_path(args.output, project)
lines = source.read_text().splitlines()
anchors, states = [], []
for line in lines:
    match = re.match(r'^\[([^]]+)\].*\[input-script\] t=(\d+)ms', line)
    if match:
        anchors.append(datetime.fromisoformat(match[1]).timestamp() - int(match[2]) / 1000)
    match = re.match(r'^\[([^]]+)\].*\[input-script\] returned result=(0x[\da-fA-F]+) packet=(\d+) buttons=(0x[\da-fA-F]+) lx=(-?\d+) ly=(-?\d+) rx=(-?\d+) ry=(-?\d+) lt=(\d+) rt=(\d+)', line)
    if match:
        if int(match[2], 16) != 0:
            raise ValueError('Disconnected/failed controller record cannot be replayed as connected')
        states.append(match.groups())
if len(anchors) < 2 or not states:
    raise ValueError('Missing time anchors or states')
spread = (max(anchors) - min(anchors)) * 1000
if spread > 5:
    raise ValueError(f'Clock anchors disagree by {spread:.3f}ms')
origin = statistics.median(anchors)
frames = []
previous_packet = None
for stamp, result, packet, buttons, lx, ly, rx, ry, lt, rt in states:
    packet = int(packet)
    if previous_packet is not None and packet != previous_packet + 1:
        raise ValueError('Missing, reordered or interleaved controller packets')
    previous_packet = packet
    ms = round((datetime.fromisoformat(stamp).timestamp() - origin) * 1000)
    if ms < 0 or ms > 3600000 or (frames and ms < frames[-1][0]):
        raise ValueError('Invalid or nonmonotonic replay time')
    frames.append((ms, int(buttons, 16), *(int(x) for x in (lx, ly, rx, ry, lt, rt))))
# Release every control at the end, rather than holding a final recorded axis.
frames.append((frames[-1][0] + 16, 0, 0, 0, 0, 0, 0, 0))
data = b'H3IR' + struct.pack('<I', len(frames)) + b''.join(
    struct.pack('<IHhhhhBB', *frame) for frame in frames)
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_bytes(data)
metadata = {'source_log': str(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'replay_sha256': hashlib.sha256(data).hexdigest(), 'recorded_states': len(states),
            'frames_with_final_release': len(frames), 'time_anchors': len(anchors),
            'anchor_spread_ms': round(spread, 3), 'first_ms': frames[0][0], 'last_ms': frames[-1][0],
            'limitation': 'Observed input states, not deterministic game state; verify scene/path after replay.'}
dest.with_suffix('.json').write_text(json.dumps(metadata, indent=2) + '\n')
print(json.dumps(metadata, indent=2))
