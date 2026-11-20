"""Read-only: per-placement fade thresholds and sizes, weighted by triangles."""
import sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
for path in sys.argv[1:]:
    c = Cache(path)
    sb = [t['offset'] for t in c.tags.values() if t['group'] == 'sbsp']
    if len(sb) != 1: c.close(); continue
    bsp = sb[0]
    meshes = c.block(bsp + 0x2e4, 76)
    mtri = [sum(c.unpack('H', p + 6)[0] // 3 if c.data[m + 0x30] == 3 else max(c.unpack('H', p + 6)[0] - 2, 0) for p in c.block(m, 16)) for m in meshes]
    inst_mesh = {}
    for cl in c.block(bsp + 0xB4, 0xDC):
        mi = c.unpack('h', cl + 0x9C)[0]
        if mi < 0: continue
        for b in c.block(meshes[mi] + 0x34, 0x10):
            bm = c.unpack('h', b)[0]
            for i in c.block(b + 4, 2): inst_mesh[c.unpack('h', i)[0]] = bm
    insts = c.block(bsp + 0x1B0, 0x78)
    fades = collections.Counter(); tri_by_fade = collections.Counter(); radius_tri = []
    flags = collections.Counter()
    for i, at in enumerate(insts):
        fs, fe = c.unpack('2h', at + 0x6C); rad = c.unpack('f', at + 0x4C)[0]; fl = c.unpack('H', at + 0x36)[0]
        t = mtri[inst_mesh[i]] if i in inst_mesh else 0
        fades[(fs, fe)] += 1; tri_by_fade[(fs, fe)] += t; radius_tri.append((rad, t)); flags[fl] += 1
    tot = sum(t for _, t in radius_tri) or 1
    print(f'== {Path(path).name}: placements {len(insts)} placed tris {tot}')
    print('   fade (start,end) -> placements / tris:', sorted(((k, v, tri_by_fade[k]) for k, v in fades.items()), key=lambda x: -x[1])[:8])
    for lim in (0.25, 0.5, 1, 2, 4):
        print(f'   radius <= {lim:4} wu: {sum(1 for r_, _ in radius_tri if r_ <= lim):4d} placements, {100*sum(t for r_, t in radius_tri if r_ <= lim)/tot:4.1f}% of placed tris')
    print('   flags', dict(flags.most_common(6)))
    c.close()
