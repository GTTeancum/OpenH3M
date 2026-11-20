"""Read-only: per-zone potential triangle load under the current and a proposed visibility table."""
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
c = Cache(sys.argv[1]); new = np.load(sys.argv[2])
scnr = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr'); bsp = next(t['offset'] for t in c.tags.values() if t['group'] == 'sbsp')
rows = c.block(c.block(c.block(scnr + 0x3C, 0x2C)[0] + 0x14, 0x54)[0], 0xC); n = len(rows)
old = np.zeros((n, n), dtype=bool)
for i, r in enumerate(rows):
    w = [c.u(x) for v in c.block(r, 0xC)[:1] for x in c.block(v, 4)]
    for j in range(n): old[i, j] = w[j // 32] >> (j % 32) & 1
meshes = c.block(bsp + 0x2e4, 76)
mtri = [sum(c.unpack('H', p + 6)[0] // 3 for p in c.block(m, 16)) for m in meshes]
world = []; reg = {}; imesh = {}
for ci, cl in enumerate(c.block(bsp + 0xB4, 0xDC)):
    mi = c.unpack('h', cl + 0x9C)[0]; world.append(mtri[mi] if mi >= 0 else 0)
    if mi < 0: continue
    for b in c.block(meshes[mi] + 0x34, 0x10):
        bm = c.unpack('h', b)[0]
        for i in c.block(b + 4, 2):
            ii = c.unpack('h', i)[0]; reg.setdefault(ii, set()).add(ci); imesh[ii] = bm
total = sum(world) + sum(mtri[m] for m in imesh.values())
def load(vis):
    out = []
    for ci in range(n):
        v = {j for j in range(n) if vis[ci, j]}
        out.append(sum(world[z] for z in v) + sum(mtri[imesh[i]] for i, zs in reg.items() if zs & v))
    return np.array(out)
a, b = load(old), load(new)
own = np.array([world[ci] + sum(mtri[imesh[i]] for i, zs in reg.items() if ci in zs) for ci in range(n)])
print(f'total {total}; visible pairs {int(old.sum())} -> {int(new.sum())}')
print(f'typical zone (median): {np.median(a):.0f} ({100*np.median(a)/total:.0f}%) -> {np.median(b):.0f} ({100*np.median(b)/total:.0f}%)')
print(f'mean: {a.mean():.0f} -> {b.mean():.0f}; worst: {a.max()} -> {b.max()}')
heavy = np.argsort(-own)[:8]
for z in heavy: print(f'  heavy zone {z:2d}: own {own[z]:6d}  in play {a[z]:6d} -> {b[z]:6d} ({100*b[z]/total:.0f}%)  sees {int(old[z].sum())} -> {int(new[z].sum())} zones')
c.close()
