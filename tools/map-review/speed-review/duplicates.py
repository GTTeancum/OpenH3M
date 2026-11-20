"""Read-only: coincident duplicate triangles (same three positions) within each part of placed pieces."""
import sys, collections
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import mopp_validate as mv
from mopp_validate import *
mv.SHARED = {}
c, lb, r, bsp, compressions, cbm = load(sys.argv[1])
vb, ib = r.buffers('vertex'), r.buffers('index'); meshes = c.block(bsp + 0x2e4, 76)
cr = Resource(c, c.u(bsp + 0x37c)); definitions = cr.ptr(cr.root + 16); def_mesh = {}
for i in range(cr.unpack('I', cr.root + 12)[0]): def_mesh[i] = cr.unpack('2H', definitions + i * 184 + 0xb0)[0]
placed = collections.Counter()
for at in c.block(bsp + 0x1B0, 0x78):
    di = c.unpack('h', at + 0x34)[0]
    if di in def_mesh: placed[def_mesh[di]] += 1
tot = same = flip = cross_same = cross_flip = 0; stored = stored_same = stored_flip = 0; rows = []
for mi, m in enumerate(meshes):
    g = mesh_geometry(c, r, bsp, compressions, cbm, vb, ib, mi, m)
    if g is None: continue
    xyz, indices = g
    _, inv = np.unique(np.round(xyz, 4), axis=0, return_inverse=True); inv = inv.reshape(-1)
    seen = {}; ms = mf = mt = 0
    for pi, p_ in enumerate(c.block(m, 16)):
        start, count = c.unpack('2H', p_ + 4)
        if c.data[p_ + 12] not in (1, 2, 3) or count < 3: continue
        sel = indices[start:start + count // 3 * 3]
        if sel.max() >= len(xyz): continue
        w = inv[sel.reshape(-1, 3)]
        for a_, b_, c_ in w.tolist():
            if a_ == b_ or b_ == c_ or a_ == c_: continue
            mt += 1
            key = tuple(sorted((a_, b_, c_)))
            # orientation parity relative to sorted order
            rot = (a_, b_, c_); k = rot.index(key[0]); rot = rot[k:] + rot[:k]; par = rot[1] == key[1]
            if key in seen:
                if par in seen[key]: ms += 1
                else: mf += 1; seen[key].add(par)
            else: seen[key] = {par}
    k = placed[mi]; stored += mt; stored_same += ms; stored_flip += mf
    tot += mt * k; same += ms * k; flip += mf * k
    if ms + mf: rows.append((( ms + mf) * k, mi, mt, ms, mf, k))
print(Path(sys.argv[1]).name)
print(f'  stored opaque triangles {stored}: exact duplicates same facing {stored_same} ({100*stored_same/stored:.1f}%), back-to-back copies {stored_flip} ({100*stored_flip/stored:.1f}%)')
print(f'  counting placements {tot}: same facing {same} ({100*same/tot:.1f}%), back-to-back {flip} ({100*flip/tot:.1f}%)')
for x in sorted(rows, reverse=True)[:8]: print('   mesh %d: %d tris, same-facing dup %d, back-to-back %d, placed %d' % x[1:])
