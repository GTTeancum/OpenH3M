"""Read-only: which placed pieces hold a map's triangles (by piece name), heaviest first."""
import sys, collections, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
from string_ids import StringTable
c = Cache(sys.argv[1]); strings = StringTable(c)
bsp = next(t['offset'] for t in c.tags.values() if t['group'] == 'sbsp')
cr = Resource(c, c.u(bsp + 0x37c)); definitions = cr.ptr(cr.root + 16); def_mesh = {}
for i in range(cr.unpack('I', cr.root + 12)[0]): def_mesh[i] = cr.unpack('2H', definitions + i * 184 + 0xb0)[0]
meshes = c.block(bsp + 0x2e4, 76); mtri = [sum(c.unpack('H', p + 6)[0] // 3 for p in c.block(m, 16)) for m in meshes]
groups = collections.defaultdict(lambda: [0, 0, 0.0, set()]); total = 0
for at in c.block(bsp + 0x1B0, 0x78):
    di = c.unpack('h', at + 0x34)[0]
    if di not in def_mesh: continue
    t = mtri[def_mesh[di]]; total += t
    try: name = strings.text(c.u(at + 0x54)) or '?'
    except Exception: name = '?'
    key = re.sub(r'[\d_\-\.]+$', '', re.sub(r'\(\d+\)$', '', name)).strip('_- ') or name
    g = groups[key]; g[0] += t; g[1] += 1; g[2] = max(g[2], c.unpack('f', at + 0x4C)[0]); g[3].add(name)
print('placed triangles', total, 'name groups', len(groups))
acc = 0
for key, (t, n, rad, names) in sorted(groups.items(), key=lambda x: -x[1][0])[:int(sys.argv[2]) if len(sys.argv) > 2 else 45]:
    acc += t
    print(f'{100*t/total:5.1f}% (running {100*acc/total:5.1f}%)  {t:7d} tris  {n:3d} placed  largest radius {rad:5.1f} wu  {key[:70]}')
c.close()
