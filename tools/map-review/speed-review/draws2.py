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
P = [[c.unpack('hhHHHHBBH', p) for p in c.block(m, 16)] for m in meshes]
print('sample parts', P[def_mesh[0]][:4])
ip = im = 0; flags = collections.Counter(); types = collections.Counter()
for at in c.block(bsp + 0x1B0, 0x78):
    di = c.unpack('h', at + 0x34)[0]
    if di not in def_mesh: continue
    ps = P[def_mesh[di]]; ip += len(ps); im += len({(p[0], p[6], p[7]) for p in ps})
    for p in ps: types[(p[6], p[7])] += 1
print('instance parts', ip, 'if merged by material+type within each instance', im)
print('part type/flag bytes', types.most_common(8))
c.close()
