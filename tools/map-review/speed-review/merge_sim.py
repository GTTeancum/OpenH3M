"""Read-only: how many draws merging placed pieces (by neighbourhood and material) would save, per test view."""
import sys, collections, math
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
c = Cache(sys.argv[1]); cell = float(sys.argv[3])
bsp = next(t['offset'] for t in c.tags.values() if t['group'] == 'sbsp')
cr = Resource(c, c.u(bsp + 0x37c)); definitions = cr.ptr(cr.root + 16); def_mesh = {}
for i in range(cr.unpack('I', cr.root + 12)[0]): def_mesh[i] = cr.unpack('2H', definitions + i * 184 + 0xb0)[0]
meshes = c.block(bsp + 0x2e4, 76)
P = [[c.unpack('hhHHHHBBH', p) for p in c.block(m, 16)] for m in meshes]
I = []; use = collections.Counter()
for at in c.block(bsp + 0x1B0, 0x78):
    di = c.unpack('h', at + 0x34)[0]
    if di not in def_mesh: continue
    use[di] += 1
    I.append((di, np.array(c.unpack('3f', at + 0x40)), c.unpack('f', at + 0x4C)[0], P[def_mesh[di]], c.unpack('f', at)[0]))
print('instances', len(I), 'parts', sum(len(i[3]) for i in I), 'single-use instances', sum(1 for i in I if use[i[0]] == 1), 'their parts', sum(len(i[3]) for i in I if use[i[0]] == 1))
def visible(pos, yaw, centre, rad):
    d = centre - pos; dist = np.linalg.norm(d)
    if dist <= rad: return True
    f = np.array([math.cos(yaw), math.sin(yaw), 0]); ang = math.acos(max(-1, min(1, float(d @ f) / dist)))
    return ang <= math.radians(55) + math.asin(min(1, rad / dist))
for line in open(sys.argv[2]).read().split('\n'):
    v = line.split()
    if len(v) < 4: continue
    pos = np.array([float(v[0]), float(v[1]), float(v[2]) + .62]); yaw = float(v[3])
    vis = [i for i in I if visible(pos, yaw, i[1], i[2])]
    before = sum(len(i[3]) for i in vis); out = [before]
    for singles_only in (True, False):
        groups = set(); keep = 0
        for i in vis:
            if singles_only and use[i[0]] != 1: keep += len(i[3]); continue
            key = tuple(np.floor(i[1] / cell).astype(int))
            for p in i[3]: groups.add((key, p[0], p[6], p[7]))
        out.append(keep + len(groups))
    print('view', line.strip()[:28], '| pieces in view', len(vis), '| parts now', out[0], '| merge single-use only', out[1], '| merge all', out[2])
c.close()
