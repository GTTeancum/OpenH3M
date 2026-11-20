"""Read-only: per-zone potential triangles if every placed piece were split evenly among the zones it is registered in."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
for path in sys.argv[1:]:
    c = Cache(path)
    scnr = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr'); bsp = next(t['offset'] for t in c.tags.values() if t['group'] == 'sbsp')
    rows = c.block(c.block(c.block(scnr + 0x3C, 0x2C)[0] + 0x14, 0x54)[0], 0xC); n = len(rows)
    vis = []
    for r in rows:
        w = [c.u(x) for v in c.block(r, 0xC)[:1] for x in c.block(v, 4)]
        vis.append({i for i in range(n) if w[i // 32] >> (i % 32) & 1})
    meshes = c.block(bsp + 0x2e4, 76)
    mtri = [sum(c.unpack('H', p + 6)[0] // 3 if c.data[m + 0x30] == 3 else max(c.unpack('H', p + 6)[0] - 2, 0) for p in c.block(m, 16)) for m in meshes]
    world = []; reg = {}; imesh = {}
    for ci, cl in enumerate(c.block(bsp + 0xB4, 0xDC)):
        mi = c.unpack('h', cl + 0x9C)[0]; world.append(mtri[mi] if mi >= 0 else 0)
        if mi < 0: continue
        for b in c.block(meshes[mi] + 0x34, 0x10):
            bm = c.unpack('h', b)[0]
            for i in c.block(b + 4, 2):
                ii = c.unpack('h', i)[0]; reg.setdefault(ii, set()).add(ci); imesh[ii] = bm
    total = sum(world) + sum(mtri[m] for m in imesh.values())
    now = []; split = []
    for ci in range(n):
        v = vis[ci]; base = sum(world[z] for z in v)
        now.append(base + sum(mtri[imesh[i]] for i, zs in reg.items() if zs & v))
        split.append(base + sum(mtri[imesh[i]] * len(zs & v) / len(zs) for i, zs in reg.items()))
    now.sort(); split.sort()
    multi = sum(mtri[imesh[i]] for i, zs in reg.items() if len(zs) > 1)
    print(f'{Path(path).name:16s} total {total:7d} | tris in multi-zone pieces {100*multi/total:3.0f}% | typical zone now {100*now[n//2]/total:3.0f}% ({now[n//2]:7.0f}) -> if split {100*split[n//2]/total:3.0f}% ({split[n//2]:7.0f}) | worst now {now[-1]:7.0f} -> {split[-1]:7.0f}')
    c.close()
