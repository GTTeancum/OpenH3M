"""Static sightline test between zones, through their doorways (cluster portals).

A zone pair stays visible unless every sampled segment between any doorway of one zone and any
doorway of the other is blocked by solid opaque geometry. Adjacent zones are always kept.
"""
import argparse, ctypes as C, json, sys, time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
p = argparse.ArgumentParser(); p.add_argument('data', type=Path); p.add_argument('out', type=Path)
p.add_argument('--density', type=float, default=6.0, help='samples per square world unit of doorway')
p.add_argument('--confirm-density', type=float, default=40.0)
p.add_argument('--threads', type=int, default=14)
p.add_argument('--min-front', type=float, default=0.5, help='drop doorway points where fewer than this share of surrounding first hits are front faces')
a = p.parse_args()
d = np.load(a.data); tris = np.ascontiguousarray(d['tris'], dtype=np.float32)
lib = C.CDLL(str(ROOT / 'work/speed-review/deps/raycast.dll'))
F = C.POINTER(C.c_float)
lib.rc_build.argtypes = [F, C.c_int]; lib.rc_build.restype = C.c_int
lib.rc_first_facing.argtypes = [F, F, C.c_int, C.POINTER(C.c_int)]
lib.rc_clear_segments.argtypes = [F, C.c_int, F, C.c_int, C.c_int, C.c_longlong, C.c_int]; lib.rc_clear_segments.restype = C.c_longlong
t0 = time.time(); print('bvh nodes', lib.rc_build(tris.ctypes.data_as(F), len(tris)), 'in %.1fs' % (time.time() - t0), flush=True)
counts = d['portal_counts']; verts = d['portal_verts']; pcl = d['portal_clusters']; vis = d['vis'].copy(); n = len(vis)
polys = np.split(verts, np.cumsum(counts)[:-1])
rng = np.random.default_rng(1)


def samples(poly, density):
    poly = poly.astype(np.float64); cen = poly.mean(0); pts = [cen[None]]
    for i in range(1, len(poly) - 1):
        a0, b0, c0 = poly[0], poly[i], poly[i + 1]
        area = np.linalg.norm(np.cross(b0 - a0, c0 - a0)) / 2
        k = int(max(3, min(400, round(area * density))))
        u = rng.random((k, 2)); flip = u.sum(1) > 1; u[flip] = 1 - u[flip]
        pts.append(a0 + u[:, :1] * (b0 - a0) + u[:, 1:] * (c0 - a0))
    # corners and edge midpoints, pulled slightly inward
    edge = np.concatenate([poly, (poly + np.roll(poly, -1, 0)) / 2])
    pts.append(cen + (edge - cen) * 0.97)
    return np.concatenate(pts)


def zone_points(density):
    out = [[] for _ in range(n)]
    for poly, (b, f) in zip(polys, pcl):
        if len(poly) < 3: continue
        s = samples(poly, density)
        for z in (b, f):
            if 0 <= z < n: out[z].append(s)
    res = []
    for x in out:
        x = np.ascontiguousarray(np.concatenate(x), dtype=np.float32) if x else np.zeros((0, 3), np.float32)
        res.append(open_space(x) if a.min_front > 0 and len(x) else x)
    return res


def open_space(x, k=32):
    """Keep only points in open playable space: most first hits around them are front faces."""
    pts = np.ascontiguousarray(np.repeat(x, k, axis=0)); dirs = rng.normal(size=pts.shape).astype(np.float32)
    sg = np.zeros(len(pts), dtype=np.int32)
    lib.rc_first_facing(pts.ctypes.data_as(F), dirs.ctypes.data_as(F), len(pts), sg.ctypes.data_as(C.POINTER(C.c_int)))
    sg = sg.reshape(-1, k); front = (sg < 0).sum(1); back = (sg > 0).sum(1)
    if FACING[0] < 0: front, back = back, front
    keep = front >= a.min_front * np.maximum(front + back, 1)
    keep &= (front + back) > 0
    return np.ascontiguousarray(x[keep])


adj = np.zeros((n, n), dtype=bool)
for b, f in pcl:
    if 0 <= b < n and 0 <= f < n: adj[b, f] = adj[f, b] = True
FACING = [1]
_mf = a.min_front; a.min_front = 0
pts = zone_points(a.density)
# facing calibration
allp = np.concatenate([x for x in pts if len(x)])
sel = allp[rng.integers(0, len(allp), 20000)]; dirs = rng.normal(size=sel.shape).astype(np.float32)
sign = np.zeros(len(sel), dtype=np.int32)
lib.rc_first_facing(np.ascontiguousarray(sel).ctypes.data_as(F), np.ascontiguousarray(dirs).ctypes.data_as(F), len(sel), sign.ctypes.data_as(C.POINTER(C.c_int)))
neg, pos, none = int((sign < 0).sum()), int((sign > 0).sum()), int((sign == 0).sum())
facing = 1 if neg >= pos else -1
FACING[0] = facing; a.min_front = _mf
pts = zone_points(a.density)
print('zones with no open-space doorway points:', [i for i, x in enumerate(pts) if not len(x)], flush=True)
print(f'facing calibration: first hits with dot<0 {neg}, dot>0 {pos}, no hit {none} -> front faces have dot{"<" if facing > 0 else ">"}0 ({100*max(neg,pos)/max(neg+pos,1):.1f}% agree)', flush=True)


def clear(pa, pb, stop=1):
    if not len(pa) or not len(pb): return 1  # no usable points: keep the pair visible
    return lib.rc_clear_segments(pa.ctypes.data_as(F), len(pa), pb.ctypes.data_as(F), len(pb), facing, stop, a.threads)


pairs = [(i, j) for i in range(n) for j in range(i + 1, n) if (vis[i, j] or vis[j, i]) and not adj[i, j]]
print('zone pairs to test', len(pairs), 'points per zone avg', int(np.mean([len(x) for x in pts])), flush=True)
blocked = []; t0 = time.time(); rays = 0
for k, (i, j) in enumerate(pairs):
    if clear(pts[i], pts[j]) == 0: blocked.append((i, j))
    if k % 100 == 0: print(f'  {k}/{len(pairs)} blocked so far {len(blocked)} t={time.time()-t0:.0f}s', flush=True)
print('pass 1 blocked pairs', len(blocked), 'of', len(pairs), flush=True)
dense = zone_points(a.confirm_density); confirmed = []; reopened = []
for k, (i, j) in enumerate(blocked):
    (confirmed if clear(dense[i], dense[j]) == 0 else reopened).append((i, j))
    if k % 50 == 0: print(f'  confirm {k}/{len(blocked)} t={time.time()-t0:.0f}s', flush=True)
print('confirmed blocked', len(confirmed), 'reopened by dense pass', len(reopened), flush=True)
new = vis.copy()
for i, j in confirmed: new[i, j] = new[j, i] = False
json.dump(dict(zones=n, facing=facing, calibration=dict(neg=neg, pos=pos, none=none), pairs_tested=len(pairs),
               blocked_pass1=len(blocked), confirmed=[list(map(int, x)) for x in confirmed], reopened=[list(map(int, x)) for x in reopened],
               visible_pairs_before=int(vis.sum()), visible_pairs_after=int(new.sum()),
               density=a.density, confirm_density=a.confirm_density,
               points_per_zone=[int(len(x)) for x in pts], dense_points_per_zone=[int(len(x)) for x in dense]), open(a.out, 'w'))
np.save(str(a.out) + '.vis.npy', new)
print('visible ordered pairs', int(vis.sum()), '->', int(new.sum()), 'total %.0fs' % (time.time() - t0))
