"""Measure bank collision-hull overlap from read-only native object snapshots.

This proves geometric overlap and observed poses, not a general Havok contact
solver oracle. The fixture deliberately uses a single direct polyhedron on an
identity root node. Reject other model layouts rather than guessing transforms.
"""
import argparse
from datetime import datetime
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('run', type=Path)
p.add_argument('--bank', choices=('1x1', '2x1'), required=True)
p.add_argument('--expect', choices=('phased', 'fixed', 'normal'), required=True)
a = p.parse_args()
run = a.run.resolve(strict=True)
run.relative_to(ROOT)
command = json.loads((run/'launch-command.json').read_text())
assert f'--halo3mp_advanced_forge_test_physics={a.expect}' in command
log = (run/'trace-runtime.log').read_text(errors='replace')
mode = {'normal': 0, 'fixed': 0x40, 'phased': 0xc0}[a.expect]
selected = re.findall(r'physics selected: ([0-9A-F]+) mode ([0-9A-F]+) flags ([0-9A-F]+) held true', log)
assert len(selected) == 1 and int(selected[0][1], 16) == mode, selected
held = int(selected[0][0], 16)
flags = int(selected[0][2], 16)
assert flags & 0x100000 and bool(flags & 0x40) == (mode != 0)
assert bool(flags & 0x80) == (mode != 0xc0)
released = re.findall(r'physics released: ([0-9A-F]+) mode ([0-9A-F]+) flags ([0-9A-F]+) held false', log)
assert len(released) == 1 and int(released[0][0], 16) == held
release_flags = int(released[0][2], 16)
assert release_flags & 0x80 and bool(release_flags & 0x40) == (mode != 0)
restored = re.findall(r'physics restored: ([0-9A-F]+) flags ([0-9A-F]+) original ([0-9A-F]+)', log)
assert len(restored) == 1 and int(restored[0][0], 16) == held
assert not ((int(restored[0][1], 16) ^ int(restored[0][2], 16)) & 0x1000c0)
assert 'Advanced Forge disabled:' not in log
events = [json.loads(line) for line in (run/'loading-trace.jsonl').read_text().splitlines()]
clock = json.loads((run/'launch-clock.json').read_text())
# The trace origin precedes launch-clock by at most the first attach event.
# Exclude that uncertainty interval instead of assigning borderline samples.
clock_slack = next(e['seconds'] for e in events if e['event'] == 'attached') + .1
release_time = re.search(r'^\[([^]]+)\].*Advanced Forge physics released:', log, re.M)[1]
release_lower = datetime.fromisoformat(release_time).timestamp()-clock['wall_time']
release_upper = release_lower+clock_slack

tag = {'1x1': 0x90002937, '2x1': 0x90002948}[a.bank]
fixture = ROOT/f'work/h4-forge-research/isolated/overlap-fixture-{a.bank}.json'
source = json.loads(fixture.read_text())
cache_path = next((ROOT/'work/dlc/installed-current').rglob('forge_gulch.map'))
cache_hash = hashlib.sha256(cache_path.read_bytes()).hexdigest()
assert cache_hash == source['map_sha256']
c = Cache(cache_path)
try:
    obj = c.tags[tag & 65535]['offset']
    model = c.tags[c.u(obj+0x40) & 65535]['offset']
    render = c.tags[c.u(model+12) & 65535]['offset']
    physics = c.tags[c.u(model+0x3c) & 65535]['offset']
    nodes = list(c.block(render+0x30, 96))
    assert len(nodes) == 1
    node = nodes[0]
    assert c.unpack('h', node+4) == (-1,)
    assert c.unpack('3f', node+12) == (0., 0., 0.)
    assert c.unpack('4f', node+24) == (0., 0., 0., 1.)
    assert c.unpack('f', node+40) == (1.,)
    bodies = list(c.block(physics+0x58, 176))
    assert len(bodies) == 1 and c.unpack('h', bodies[0]) == (0,)
    assert c.unpack('2H', bodies[0]+0x58) == (4, 0)
    shapes = list(c.block(physics+0xac, 128))
    assert len(shapes) == 1
    shape = shapes[0]
    groups = list(c.block(physics+0xb8, 48))
    assert len(groups) == c.u(shape+0x64)
    vertices = []
    for group in groups:
        v = c.unpack('12f', group)
        vertices.extend((v[i], v[4+i], v[8+i]) for i in range(4))
    vertices = np.asarray(vertices[:c.u(shape+0x6c)])
finally:
    c.close()


def pose(body):
    data = bytes.fromhex(body)
    position = np.array(struct.unpack_from('>3f', data, 0x54))
    forward = np.array(struct.unpack_from('>3f', data, 0x60))
    up = np.array(struct.unpack_from('>3f', data, 0x6c))
    basis = np.array([forward, np.cross(up, forward), up])
    assert np.max(np.abs(basis@basis.T-np.eye(3))) < .001
    return position, basis, struct.unpack_from('>I', data, 0xac)[0]


def intersection_radius(first, second):
    planes = np.concatenate([ConvexHull(vertices@basis+position).equations
                             for position, basis, _ in (first, second)])
    # Largest sphere wholly inside BOTH convex cores. Positive radius proves
    # volume intersection, even without Havok's additional convex radius.
    result = linprog([0., 0., 0., -1.], A_ub=np.c_[planes[:, :3], np.ones(len(planes))],
                     b_ub=-planes[:, 3], bounds=[(None, None)]*3+[(0, None)],
                     method='highs')
    if result.status == 2:  # No common interior sphere.
        return 0.
    if not result.success:
        raise ValueError(f'Collision intersection solver failed: {result.message}')
    return float(result.x[3])


samples = []
for event in events:
    if event.get('event') != 'machine_crate_snapshot':
        continue
    objects = [o for o in event['objects'] if int(o['tag'], 16) == tag]
    current = next((o for o in objects if int(o['handle'], 16) == held), None)
    others = [o for o in objects if int(o['handle'], 16) != held]
    if current is None:
        continue
    assert len(others) == 1
    first, second = pose(current['body']), pose(others[0]['body'])
    phase = 'held' if event['seconds'] < release_lower else (
        'after_release' if event['seconds'] > release_upper else 'transition')
    samples.append(dict(seconds=event['seconds'], phase=phase, position=first[0].tolist(),
                        flags=hex(first[2]), overlap_core_radius=intersection_radius(first, second)))
assert len(samples) >= 3, samples
requested = np.array([-44.7924538, -197.9406281, 2.582953])
if a.expect in ('phased', 'fixed'):
    assert all(np.linalg.norm(np.array(s['position'])-requested) < .0001 for s in samples)
    assert all(s['overlap_core_radius'] > .01 for s in samples)
    if a.expect == 'phased':
        assert any(not int(s['flags'], 16) & 0x80 for s in samples)
    assert any(int(s['flags'], 16) & 0x80 and not int(s['flags'], 16) & 0x100000 for s in samples)
else:
    # Normal remains collidable even while held. Its live pose may already
    # react between exact-coordinate updates, so an unchanged held transform
    # would be the wrong oracle. Require measured overlap before release and
    # separation afterwards, in addition to actual native motion.
    assert any(s['phase'] == 'held' and s['overlap_core_radius'] > .01 for s in samples)
    assert any(s['phase'] == 'after_release' and np.linalg.norm(np.array(s['position'])-requested) > .02 for s in samples)
    assert all(s['overlap_core_radius'] == 0 for s in samples if s['phase'] == 'after_release')
    assert any(int(s['flags'], 16) & 0x80 and not int(s['flags'], 16) & 0x40 for s in samples)

saved = (run/'native-variant.bin').read_bytes()
assert len(saved) == 0xe090 and struct.unpack_from('>H', saved, 0xf8)[0] == 12
slots = [i for i in range(640) if struct.unpack_from('>I', saved, 0x134+i*84)[0] == held]
assert len(slots) == 1
saved_position = struct.unpack_from('>3f', saved, 0x140+slots[0]*84)
assert np.linalg.norm(np.array(samples[-1]['position'])-saved_position) < .0001
report = dict(result='PASS', bank=a.bank, mode=a.expect, source_cache_sha256=cache_hash,
              live_samples=samples, saved_position=saved_position,
              native_version=12, restored=True,
              limitation='Controlled exact-coordinate overlap and release on one direct polyhedron. Does not prove unrestricted drag collision, every scenery shape, physical-console or system-link behavior. Inspect native captures separately.')
(run/'overlap-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
