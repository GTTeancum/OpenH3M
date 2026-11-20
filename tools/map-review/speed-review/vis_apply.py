"""Write a tightened zone visibility table (open and doors-closed) into a copy of a native map.

Only bits are cleared, never set; the table keeps its size and place. Everything else in the
tag data is byte-identical, which this script proves before reporting success.
"""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path); p.add_argument('vis', type=Path); p.add_argument('out', type=Path)
p.add_argument('--xex', type=Path, required=True); p.add_argument('--report', type=Path, required=True)
a = p.parse_args()
new = np.load(a.vis); n = len(new)
c = Cache(a.source)
sc = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
zones = c.block(sc + 0x3C, 0x2C); assert len(zones) == 1
spvs = c.block(zones[0] + 0x14, 0x54); assert len(spvs) == 1
writes = {}; cleared = 0
for off in (0, 0xC):
    rows = c.block(spvs[0] + off, 0xC); assert len(rows) == n
    for i, row in enumerate(rows):
        vecs = c.block(row, 0xC); assert len(vecs) == 1
        words = c.block(vecs[0], 4); assert len(words) == (n + 31) // 32
        for wi, at in enumerate(words):
            old = c.u(at); val = old
            for bit in range(32):
                j = wi * 32 + bit
                if j < n and (old >> bit & 1) and not new[i, j]:
                    assert i != j
                    val &= ~(1 << bit); cleared += 1
                if j < n and not (old >> bit & 1): assert not new[i, j], 'table may only be tightened'
            if val != old: writes[at] = val
assert not a.out.exists(), 'refusing to overwrite'
from map_builder import MapBuilder
from build_scenario_checkpoint import resource_salt
b = MapBuilder(a.source, 0); salt = resource_salt(a.xex)
for at, val in writes.items(): b.put(at - c.start + c.base, 'I', val)
a.out.write_bytes(b.finish(salt)); b.close()
check = Cache(a.out)
assert check.base == c.base and check.u(0x490) == c.u(0x490)
size = c.u(0x490)
ma = np.frombuffer(c.data, dtype=np.uint8, count=size, offset=c.start); mb = np.frombuffer(check.data, dtype=np.uint8, count=size, offset=check.start)
diff = np.nonzero(ma != mb)[0]
allowed = set()
for at in writes: allowed.update(range(at - c.start, at - c.start + 4))
unexpected = [int(x) for x in diff if int(x) not in allowed]
report = dict(source=str(a.source), candidate=str(a.out), sha256=hashlib.sha256(a.out.read_bytes()).hexdigest(),
              bits_cleared_both_tables=cleared, words_changed=len(writes), tag_bytes_changed=int(len(diff)),
              unexpected_tag_bytes_changed=len(unexpected))
del ma, mb
check.close(); c.close()
a.report.write_text(json.dumps(report, indent=1)); print(json.dumps(report))
assert not unexpected, 'unexpected tag data changes'
