"""Read-only: how many separate draws the level geometry is split into."""
import sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
c = Cache(sys.argv[1])
bsp = next(t['offset'] for t in c.tags.values() if t['group'] == 'sbsp')
cr = Resource(c, c.u(bsp + 0x37c)); definitions = cr.ptr(cr.root + 16); def_mesh = {}
for i in range(cr.unpack('I', cr.root + 12)[0]): def_mesh[i] = cr.unpack('2H', definitions + i * 184 + 0xb0)[0]
meshes = c.block(bsp + 0x2e4, 76)
parts = [c.block(m, 16) for m in meshes]
nparts = [len(p) for p in parts]; mtri = [sum(c.unpack('H', p + 6)[0] // 3 for p in ps) for ps in parts]
clusters = c.block(bsp + 0xB4, 0xDC); cm = [c.unpack('h', x + 0x9C)[0] for x in clusters]
print('clusters', len(clusters), 'cluster parts', sum(nparts[m] for m in cm if m >= 0), 'cluster tris', sum(mtri[m] for m in cm if m >= 0))
inst = c.block(bsp + 0x1B0, 0x78); ip = 0; it = 0; hist = collections.Counter(); used = collections.Counter()
for at in inst:
    di = c.unpack('h', at + 0x34)[0]
    if di not in def_mesh: continue
    m = def_mesh[di]; ip += nparts[m]; it += mtri[m]; hist[nparts[m]] += 1; used[di] += 1
print('instances', len(inst), 'definitions used', len(used), 'instance parts (draws if all visible)', ip, 'instance tris', it)
print('parts-per-instance histogram', sorted(hist.items()))
print('instances per definition: 1x', sum(1 for v in used.values() if v == 1), ' 2-4x', sum(1 for v in used.values() if 2 <= v <= 4), ' 5+x', sum(1 for v in used.values() if v >= 5))
small = sum(1 for at in inst if c.unpack('h', at + 0x34)[0] in def_mesh and mtri[def_mesh[c.unpack('h', at + 0x34)[0]]] < 100)
print('instances under 100 tris', small)
print('materials', len(c.block(bsp + 0xC0, c and 0x10)) if False else '')
c.close()
