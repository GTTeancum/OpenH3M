"""Read-only: find triangles of placed pieces that can never be seen because they are buried.

A point just off a triangle's surface is "buried" on a side when every direction on that side
first meets the BACK of solid opaque geometry and nothing escapes: it sits inside a closed
solid (or behind walls that all face away), where no camera in open space can look at it.
A triangle counts as buried only if all 7 sample points are buried, in every placement of its mesh.
Writes per-mesh lists of buried triangles (positions in the index buffer).
"""
import argparse, collections, ctypes as C, json, sys, time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource

p = argparse.ArgumentParser(); p.add_argument('source', type=Path); p.add_argument('out', type=Path)
p.add_argument('--eps', type=float, default=0.003); p.add_argument('--k', type=int, default=64)
p.add_argument('--min-back', type=float, default=1.0, help='share of first hits that must be back faces')
p.add_argument('--threads', type=int, default=14)
a = p.parse_args()
c = Cache(a.source)
sc = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
lm = c.tags[c.u(sc + 0x6fc) & 65535]['offset']; lb = c.block(lm + 4, 436)[0]
r = Resource(c, c.u(lb + 0x1ac))
bsp = next(t['offset'] for t in c.tags.values() if t['group'] == 'sbsp')
cr = Resource(c, c.u(bsp + 0x37c)); definitions = cr.ptr(cr.root + 16)
def_mesh = {}; comp_of = {}
for i in range(cr.unpack('I', cr.root + 12)[0]):
    mesh, comp = cr.unpack('2H', definitions + i * 184 + 0xb0); def_mesh[i] = mesh; comp_of[mesh] = comp
compressions = c.block(bsp + 0x2f0, 44); meshes = c.block(bsp + 0x2e4, 76)
vb, ib = r.buffers('vertex'), r.buffers('index')
solid = []
for mat in c.block(bsp + 0xC0, 0x24):
    tag = c.tags.get(c.u(mat + 0xC) & 65535); ok = False
    if tag and tag['group'] == 'rmtr': ok = True
    elif tag and tag['group'] == 'rmsh':
        opts = [c.unpack('h', o)[0] for o in c.block(tag['offset'] + 0x10, 2)]; ok = len(opts) >= 8 and opts[2] == 0 and opts[7] == 0
    solid.append(ok)


def payload(at):
    ptr = r.fix[at]; return r.raw[{0x40000000: 0, 0x60000000: 1}[ptr & 0xe0000000]], ptr & 0x1fffffff


def mesh_data(mi):
    """local xyz, occluder tris (T,3), candidate tris (T,3) with their index-buffer positions."""
    m = meshes[mi]; vi, ii = c.unpack('h', m + 24)[0], c.unpack('h', m + 40)[0]
    if vi < 0 or ii < 0 or c.data[m + 0x30] != 3: return None
    n, fmt, stride = r.unpack('IHH', vb[vi]); raw, off = payload(vb[vi] + 20)
    if (fmt, stride) == (2, 24):
        if mi not in comp_of: return None
        b = np.array(c.unpack('6f', compressions[comp_of[mi]] + 4)).reshape(3, 2)
        xyz = np.ndarray((n, 3), '>u2', raw, off, (stride, 2)) / 65535 * (b[:, 1] - b[:, 0]) + b[:, 0]
    elif (fmt, stride) == (1, 32): xyz = np.ndarray((n, 3), '>f4', raw, off, (stride, 4)).astype(np.float64)
    else: return None
    iraw, ioff = payload(ib[ii] + 16); indices = np.frombuffer(iraw, '>u2', r.unpack('I', ib[ii] + 4)[0] // 2, ioff)
    occ = []; cand = []; cand_pos = []
    for part in c.block(m, 16):
        mat, _, start, count = c.unpack('hhHH', part); ptype = c.data[part + 12]
        if count < 3: continue
        sel = indices[start:start + count // 3 * 3]
        if sel.max() >= n: continue
        t = sel.reshape(-1, 3).astype(np.int64)
        if ptype in (2, 3) and 0 <= mat < len(solid) and solid[mat]: occ.append(t)
        if ptype in (1, 2, 3) and not c.data[part + 13] & 8 and (fmt, stride) == (2, 24):
            cand.append(t); cand_pos.append(start + 3 * np.arange(len(t)))
    z = np.zeros((0, 3), dtype=np.int64)
    return xyz, (np.concatenate(occ) if occ else z), (np.concatenate(cand) if cand else z), (np.concatenate(cand_pos) if cand_pos else np.zeros(0, dtype=np.int64))


occluders = []; placements = []; cache = {}
for cl in c.block(bsp + 0xB4, 0xDC):
    mi = c.unpack('h', cl + 0x9C)[0]
    if mi < 0: continue
    g = mesh_data(mi)
    if g is not None and len(g[1]): occluders.append(g[0][g[1]])
for i, at in enumerate(c.block(bsp + 0x1B0, 0x78)):
    scale = c.unpack('f', at)[0]; fwd = np.array(c.unpack('3f', at + 4)); left = np.array(c.unpack('3f', at + 0x10)); up = np.array(c.unpack('3f', at + 0x1C))
    pos = np.array(c.unpack('3f', at + 0x28)); di = c.unpack('h', at + 0x34)[0]
    if di not in def_mesh: continue
    mi = def_mesh[di]
    if mi not in cache: cache[mi] = mesh_data(mi)
    g = cache[mi]
    if g is None: continue
    xyz, occ, cand, cand_pos = g
    world = pos + scale * (xyz[:, :1] * fwd + xyz[:, 1:2] * left + xyz[:, 2:3] * up)
    if len(occ): occluders.append(world[occ])
    if len(cand): placements.append((mi, world[cand]))
tris = np.ascontiguousarray(np.concatenate(occluders), dtype=np.float32)
lib = C.CDLL(str(ROOT / 'work/speed-review/deps/raycast.dll')); F = C.POINTER(C.c_float); I = C.POINTER(C.c_int)
lib.rc_build.argtypes = [F, C.c_int]; lib.rc_hemisphere.argtypes = [F, F, C.c_int, C.c_int, I, I, I, C.c_int]
lib.rc_build(tris.ctypes.data_as(F), len(tris))
print('occluder triangles', len(tris), 'placements with candidates', len(placements), 'candidate placed triangles', sum(len(w) for _, w in placements), flush=True)


def buried_points(pts, nrm):
    pts = np.ascontiguousarray(pts, dtype=np.float32); nrm = np.ascontiguousarray(nrm, dtype=np.float32); n = len(pts)
    f = np.zeros(n, np.int32); b = np.zeros(n, np.int32); m = np.zeros(n, np.int32)
    lib.rc_hemisphere(pts.ctypes.data_as(F), nrm.ctypes.data_as(F), n, a.k, f.ctypes.data_as(I), b.ctypes.data_as(I), m.ctypes.data_as(I), a.threads)
    tot = f + b + m
    return (m == 0) & (tot > 0) & (b >= a.min_back * tot)


W = [(1 / 3, 1 / 3, 1 / 3), (.8, .1, .1), (.1, .8, .1), (.1, .1, .8), (.45, .45, .1), (.1, .45, .45), (.45, .1, .45)]
t0 = time.time()
front_all = collections.defaultdict(lambda: None); both_all = collections.defaultdict(lambda: None)
stat = collections.Counter()
for pi, (mi, w) in enumerate(placements):
    w = w.astype(np.float64); n = np.cross(w[:, 1] - w[:, 0], w[:, 2] - w[:, 0]); ln = np.linalg.norm(n, axis=1)
    good = ln > 1e-12; nn = np.where(good[:, None], n / np.maximum(ln, 1e-30)[:, None], 0)
    # phase 1: centroid, front side
    cen = w.mean(1); fb = buried_points(cen + nn * a.eps, nn) & good
    front = fb.copy(); both = np.zeros(len(w), dtype=bool)
    idx = np.nonzero(fb)[0]
    if len(idx):
        ok = np.ones(len(idx), dtype=bool)
        for wt in W[1:]:
            q = w[idx, 0] * wt[0] + w[idx, 1] * wt[1] + w[idx, 2] * wt[2]
            ok &= buried_points(q + nn[idx] * a.eps, nn[idx])
        front[idx] = ok
        idx2 = idx[ok]
        if len(idx2):
            ok2 = np.ones(len(idx2), dtype=bool)
            for wt in W:
                q = w[idx2, 0] * wt[0] + w[idx2, 1] * wt[1] + w[idx2, 2] * wt[2]
                ok2 &= buried_points(q - nn[idx2] * a.eps, -nn[idx2])
            both[idx2] = ok2
    front_all[mi] = front if front_all[mi] is None else front_all[mi] & front
    both_all[mi] = both if both_all[mi] is None else both_all[mi] & both
    stat['placed tris'] += len(w); stat['placed front-buried'] += int(front.sum()); stat['placed both-buried'] += int(both.sum())
    if pi % 200 == 0: print(f'  {pi}/{len(placements)} t={time.time()-t0:.0f}s', dict(stat), flush=True)
out = {}; tot = fa = ba = 0
for mi, fr in front_all.items():
    pos = cache[mi][3]; tot += len(fr); fa += int(fr.sum()); ba += int(both_all[mi].sum())
    out[str(mi)] = dict(front=pos[fr].tolist(), both=pos[both_all[mi]].tolist(), candidates=int(len(fr)))
print(dict(stat)); print(f'unique mesh triangles {tot}: buried in every placement front-side {fa} ({100*fa/tot:.1f}%), both sides {ba} ({100*ba/tot:.1f}%)  t={time.time()-t0:.0f}s')
json.dump(dict(source=str(a.source), eps=a.eps, k=a.k, min_back=a.min_back, stats=dict(stat), unique=tot, front=fa, both=ba, meshes=out), open(a.out, 'w'))
c.close()
