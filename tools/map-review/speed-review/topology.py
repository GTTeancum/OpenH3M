"""Read-only: vertex sharing statistics of placed-piece meshes (how hard-edged the geometry is)."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import mopp_validate as mv
from mopp_validate import *
mv.SHARED = {}
c, lb, r, bsp, compressions, cbm = load(sys.argv[1])
vb, ib = r.buffers('vertex'), r.buffers('index')
meshes = c.block(bsp + 0x2e4, 76)
T = V = P = 0; border_e = edges = 0; rows = []
for mi, m in enumerate(meshes):
    g = mesh_geometry(c, r, bsp, compressions, cbm, vb, ib, mi, m)
    if g is None: continue
    xyz, indices = g
    parts = [c.unpack('4H', p + 4) for p in c.block(m, 16)]
    tris = []
    for start, count, _, _ in parts:
        sel = indices[start:start + count]
        if len(sel) and sel.max() < len(xyz): tris.append(sel[:count // 3 * 3].reshape(-1, 3))
    if not tris: continue
    tri = np.concatenate(tris); used = np.unique(tri)
    pos = np.unique(np.round(xyz[used], 4), axis=0)
    # edges by position: count edges used by exactly one triangle after welding
    _, inv = np.unique(np.round(xyz, 4), axis=0, return_inverse=True)
    w = inv[tri]
    e = np.sort(np.concatenate([w[:, [0, 1]], w[:, [1, 2]], w[:, [2, 0]]]), axis=1)
    ue, cnt = np.unique(e, axis=0, return_counts=True)
    T += len(tri); V += len(used); P += len(pos); edges += len(ue); border_e += int((cnt == 1).sum())
    rows.append((len(tri), mi, len(used), len(pos), int((cnt == 1).sum()), len(ue), float((xyz.max(0) - xyz.min(0)).max())))
print(f'triangles {T}  vertices used {V}  unique positions {P}  vertices/triangle {V/T:.2f}  positions/triangle {P/T:.2f}  open edges {100*border_e/edges:.0f}% of welded edges')
for t, mi, v, pcount, be, ne, ext in sorted(rows, reverse=True)[:12]:
    print(f'  mesh {mi:3d} tris {t:6d} verts {v:6d} positions {pcount:6d} open-edges {100*be/ne:3.0f}% extent {ext:6.2f} wu')
