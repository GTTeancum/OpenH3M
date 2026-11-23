"""DIAGNOSTIC ONLY (leaves holes): stop drawing every second placed-piece mesh, to measure what fewer draws buys."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
from map_builder import MapBuilder
from build_scenario_checkpoint import resource_salt
src, out, xex = sys.argv[1:4]
c = Cache(src)
bsp = next(t['offset'] for t in c.tags.values() if t['group'] == 'sbsp')
sc = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
cr = Resource(c, c.u(bsp + 0x37c)); definitions = cr.ptr(cr.root + 16)
dm = sorted({cr.unpack('2H', definitions + i * 184 + 0xb0)[0] for i in range(cr.unpack('I', cr.root + 12)[0])})
drop = set(dm[1::2])
meshes = c.block(bsp + 0x2e4, 76)
lm = c.tags[c.u(sc + 0x6fc) & 65535]; lb = c.block(lm['offset'] + 4, 436); assert len(lb) == 1
lmesh = c.block(lb[0] + 0x134, 76); assert len(lmesh) == len(meshes)
b = MapBuilder(src, 0); n = 0
for i in drop:
    for m in (meshes[i], lmesh[i]):
        assert c.u(m) == len(c.block(m, 16)); b.put(m - c.start + c.base, 'I', 0)
    n += 1
Path(out).write_bytes(b.finish(resource_salt(xex))); b.close(); print('meshes emptied', n, 'of', len(dm))
