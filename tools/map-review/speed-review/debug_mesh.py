import sys, ctypes as C
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import mopp_validate as mv
from mopp_validate import *
mv.SHARED = {}
ROOT = Path(__file__).resolve().parents[3]
c, lb, r, bsp, compressions, cbm = load(sys.argv[1]); mi = int(sys.argv[2])
vb, ib = r.buffers('vertex'), r.buffers('index'); m = c.block(bsp + 0x2e4, 76)[mi]
xyz, indices = mesh_geometry(c, r, bsp, compressions, cbm, vb, ib, mi, m); xyz = np.ascontiguousarray(xyz, dtype=np.float32); n = len(xyz)
lib = C.CDLL(str(ROOT / 'work/speed-review/deps/meshoptimizer.dll')); U = C.POINTER(C.c_uint); F = C.POINTER(C.c_float)
lib.meshopt_simplify.argtypes = [U, U, C.c_size_t, F, C.c_size_t, C.c_size_t, C.c_size_t, C.c_float, C.c_uint, F]; lib.meshopt_simplify.restype = C.c_size_t
_, first, inv = np.unique(np.round(xyz, 4), axis=0, return_index=True, return_inverse=True); rep = first[inv.reshape(-1)].astype(np.uint32)
ext = float((xyz.max(0) - xyz.min(0)).max()); print('mesh', mi, 'verts', n, 'unique positions', len(first), 'extent', ext, 'bbox', (xyz.max(0) - xyz.min(0)).round(2))
for p_ in c.block(m, 16):
    mat, _, start, count = c.unpack('hhHH', p_); 
    if count < 90: continue
    src = np.ascontiguousarray(rep[indices[start:start + count]], dtype=np.uint32)
    t = src.reshape(-1, 3); e = np.sort(np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]]), axis=1); ue, cnt = np.unique(e, axis=0, return_counts=True)
    # triangle size stats
    P = xyz[t]; area = np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1) / 2; edge = np.linalg.norm(P[:, 1] - P[:, 0], axis=1)
    res = []
    for opt, err in ((1, 0.01), (0, 0.01), (0, 0.05), (0, 0.3)):
        dest = np.empty_like(src); er = C.c_float()
        k = lib.meshopt_simplify(dest.ctypes.data_as(U), src.ctypes.data_as(U), count, xyz.ctypes.data_as(F), n, 12, int(count * .2) // 3 * 3, err, opt, C.byref(er)); res.append(k // 3)
    print(f' part mat {mat} tris {count//3}: edges 1-tri {100*(cnt==1).mean():.0f}% 2-tri {100*(cnt==2).mean():.0f}% 3+ {100*(cnt>2).mean():.0f}%  median edge {np.median(edge)*304.8:.1f} cm  area total {area.sum():.2f} sq wu | kept lock/1% {res[0]} nolock/1% {res[1]} nolock/5% {res[2]} nolock/30% {res[3]}')
