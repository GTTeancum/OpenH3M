"""Edit a map's own performance throttles (the retail `perf` tag the scenario points at).

Each map carries four rows, one per local player count. Row 0 is single-screen play. The water
value selects native water features: above 0.66 both extras, 0.33-0.66 one, below 0.33 neither;
stock maps already use 0 for split screen. Only the named fields of the chosen row change; the
script proves every other tag byte is identical.
"""
import argparse, hashlib, json, struct, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache

FIELDS = dict(water=(0x04, 'f'), decorators=(0x08, 'f'), effects=(0x0C, 'f'), instances=(0x10, 'f'), object_fade=(0x14, 'f'),
              object_lod=(0x18, 'f'), decals=(0x1C, 'f'), cpu_lights=(0x20, 'i'), cpu_light_scale=(0x24, 'f'),
              gpu_lights=(0x28, 'i'), gpu_light_scale=(0x2C, 'f'), shadows=(0x30, 'i'), shadow_lod=(0x34, 'f'))
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path); p.add_argument('out', type=Path)
p.add_argument('--xex', type=Path, required=True); p.add_argument('--report', type=Path, required=True)
p.add_argument('--row', type=int, default=0)
p.add_argument('--set', action='append', default=[], metavar='FIELD=VALUE', help='e.g. water=0.5')
a = p.parse_args()
c = Cache(a.source)
sc = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
ref = c.u(sc + 0x700 + 0xC); tag = c.tags.get(ref & 65535) if ref != 0xffffffff else None
if tag is None:
    # No per-map throttles (as on Rat's Nest): the game falls back to the map's globals\default tag.
    perfs = [i for i, t in c.tags.items() if t['group'] == 'perf']
    assert len(perfs) == 1 and c.name(perfs[0]) == 'globals\\default', 'expected exactly one fallback perf tag'
    ref = perfs[0]; tag = c.tags[ref]
assert tag['group'] == 'perf', 'scenario does not point at a performance throttles tag'
rows = c.block(tag['offset'], 0x38); assert len(rows) == 4 and 0 <= a.row < 4
row = rows[a.row]
before = {k: c.unpack(fmt, row + off)[0] for k, (off, fmt) in FIELDS.items()}
writes = {}
for item in a.set:
    key, value = item.split('='); off, fmt = FIELDS[key]
    value = float(value) if fmt == 'f' else int(value)
    if fmt == 'f': assert 0.0 <= value <= 1.0
    writes[row + off] = struct.pack('>' + fmt, value)
assert writes, 'nothing to set'
assert not a.out.exists(), 'refusing to overwrite'
from map_builder import MapBuilder
from build_scenario_checkpoint import resource_salt
b = MapBuilder(a.source, 0); salt = resource_salt(a.xex)
for at, data in writes.items(): b.put(at - c.start + c.base, '4s', data)
a.out.write_bytes(b.finish(salt)); b.close()
check = Cache(a.out); size = c.u(0x490); assert check.u(0x490) == size and check.base == c.base
ma = np.frombuffer(c.data, dtype=np.uint8, count=size, offset=c.start); mb = np.frombuffer(check.data, dtype=np.uint8, count=size, offset=check.start)
diff = set(int(x) for x in np.nonzero(ma != mb)[0]); allowed = set()
for at in writes: allowed.update(range(at - c.start, at - c.start + 4))
unexpected = len(diff - allowed)
row2 = check.block(check.tags[ref & 65535]['offset'], 0x38)[a.row]
after = {k: check.unpack(fmt, row2 + off)[0] for k, (off, fmt) in FIELDS.items()}
del ma, mb
report = dict(source=str(a.source), source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(), candidate=str(a.out),
              sha256=hashlib.sha256(a.out.read_bytes()).hexdigest(), perf_tag=c.name(ref & 65535), row=a.row,
              before=before, after=after, tag_bytes_changed=len(diff), unexpected_tag_bytes_changed=unexpected,
              file_size_unchanged=a.out.stat().st_size == a.source.stat().st_size)
check.close(); c.close()
a.report.write_text(json.dumps(report, indent=1)); print(json.dumps(report, indent=1))
assert unexpected == 0
