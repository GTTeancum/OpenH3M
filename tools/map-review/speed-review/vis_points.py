"""Diagnostic: how many doorway sample points sit in open playable space vs inside/behind solid geometry."""
import ctypes as C, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
d = np.load(sys.argv[1]); tris = np.ascontiguousarray(d['tris'], dtype=np.float32)
lib = C.CDLL(str(ROOT / 'work/speed-review/deps/raycast.dll')); F = C.POINTER(C.c_float)
lib.rc_build.argtypes = [F, C.c_int]; lib.rc_first_facing.argtypes = [F, F, C.c_int, C.POINTER(C.c_int)]
lib.rc_build(tris.ctypes.data_as(F), len(tris))
rng = np.random.default_rng(2)
polys = np.split(d['portal_verts'], np.cumsum(d['portal_counts'])[:-1])
K = 48; fr = []; areas = []
for poly in polys:
    if len(poly) < 3: continue
    poly = poly.astype(np.float64); area = 0
    for i in range(1, len(poly) - 1): area += np.linalg.norm(np.cross(poly[i] - poly[0], poly[i + 1] - poly[0])) / 2
    areas.append(area)
    pts = []
    for _ in range(40):
        i = rng.integers(1, len(poly) - 1); u = rng.random(2)
        if u.sum() > 1: u = 1 - u
        pts.append(poly[0] + u[0] * (poly[i] - poly[0]) + u[1] * (poly[i + 1] - poly[0]))
    pts = np.repeat(np.array(pts, dtype=np.float32), K, axis=0); dirs = rng.normal(size=pts.shape).astype(np.float32)
    sign = np.zeros(len(pts), dtype=np.int32)
    lib.rc_first_facing(np.ascontiguousarray(pts).ctypes.data_as(F), dirs.ctypes.data_as(F), len(pts), sign.ctypes.data_as(C.POINTER(C.c_int)))
    s = sign.reshape(-1, K); front = (s < 0).sum(1); back = (s > 0).sum(1)
    fr.extend((front / np.maximum(front + back, 1)).tolist())
fr = np.array(fr)
print('doorways', len(areas), 'area median %.1f max %.1f sq wu' % (np.median(areas), max(areas)))
print('front-first fraction histogram (10 bins 0..1):', np.histogram(fr, bins=10, range=(0, 1))[0].tolist())
