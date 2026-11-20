"""Read-only: how many triangles sit in small separate elements (connected components by welded position) of placed pieces."""
import sys, collections
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
sys.path.insert(0, str(Path(__file__).parent))
import mopp_validate as mv
from mopp_validate import *
mv.SHARED = {}
c, lb, r, bsp, compressions, cbm = load(sys.argv[1])
vb, ib = r.buffers('vertex'), r.buffers('index')
meshes = c.block(bsp + 0x2e4, 76)
cr = Resource(c, c.u(bsp + 0x37c)); definitions = cr.ptr(cr.root + 16); def_mesh = {}
for i in range(cr.unpack('I', cr.root + 12)[0]): def_mesh[i] = cr.unpack('2H', definitions + i * 184 + 0xb0)[0]
placed = collections.Counter()
for at in c.block(bsp + 0x1B0, 0x78):
    di = c.unpack('h', at + 0x34)[0]
    if di in def_mesh: placed[def_mesh[di]] += 1
limits = [0.05, 0.1, 0.2, 0.35, 0.5, 1.0]; by = collections.Counter(); total = 0; ncomp = 0
for mi, m in enumerate(meshes):
    if not placed[mi]: continue
    g = mesh_geometry(c, r, bsp, compressions, cbm, vb, ib, mi, m)
    if g is None: continue
    xyz, indices = g; tris = []
    for p_ in c.block(m, 16):
        start, count = c.unpack('2H', p_ + 4)
        if c.data[p_ + 12] not in (1, 2, 3) or count < 3: continue
        sel = indices[start:start + count // 3 * 3]
        if sel.max() < len(xyz): tris.append(sel.reshape(-1, 3))
    if not tris: continue
    tri = np.concatenate(tris).astype(np.int64)
    _, inv = np.unique(np.round(xyz, 4), axis=0, return_inverse=True); w = inv.reshape(-1)[tri]
    nv = int(w.max()) + 1
    e = np.concatenate([w[:, [0, 1]], w[:, [1, 2]]])
    ncc, lab = connected_components(coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(nv, nv)), directed=False)
    tl = lab[w[:, 0]]; pts = xyz[tri].reshape(-1, 3); pl = np.repeat(tl, 3)
    lo = np.full((ncc, 3), 1e9); hi = np.full((ncc, 3), -1e9)
    np.minimum.at(lo, pl, pts); np.maximum.at(hi, pl, pts)
    ext = (hi - lo).max(1); cnt = np.bincount(tl, minlength=ncc)
    k = placed[mi]; total += len(tri) * k; ncomp += int((cnt > 0).sum())
    for L in limits: by[L] += int(cnt[ext <= L].sum()) * k
print(Path(sys.argv[1]).name, 'placed opaque triangles', total, 'separate elements', ncomp)
for L in limits: print(f'  elements up to {L*3.048*100:5.0f} cm across: {100*by[L]/total:5.1f}% of triangles')
