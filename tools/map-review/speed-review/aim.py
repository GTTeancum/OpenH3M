"""Pick the most open viewing direction at a position: mean first-hit distance over a view-sized fan of rays."""
import ctypes as C, sys, math
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
d = np.load(sys.argv[1]); tris = np.ascontiguousarray(d['tris'], dtype=np.float32)
lib = C.CDLL(str(ROOT / 'work/speed-review/deps/raycast.dll')); F = C.POINTER(C.c_float)
lib.rc_build.argtypes = [F, C.c_int]; lib.rc_render.argtypes = [F, F, C.c_int, F, F, C.c_int]
lib.rc_build(tris.ctypes.data_as(F), len(tris))
for line in open(sys.argv[2]).read().split('\n'):
    v = line.split()
    if len(v) < 4: continue
    o = np.array([float(v[0]), float(v[1]), float(v[2]) + 0.62], dtype=np.float32); res = []
    for k in range(36):
        yaw = k * math.tau / 36
        h = np.radians(np.linspace(-38, 38, 39)); e = np.radians(np.linspace(-22, 22, 23))
        hh, ee = np.meshgrid(h + yaw, e)
        dirs = np.ascontiguousarray(np.stack([np.cos(ee) * np.cos(hh), np.cos(ee) * np.sin(hh), np.sin(ee)], -1).reshape(-1, 3), dtype=np.float32)
        t = np.zeros(len(dirs), np.float32); s = np.zeros(len(dirs), np.float32)
        lib.rc_render(o.ctypes.data_as(F), dirs.ctypes.data_as(F), len(dirs), t.ctypes.data_as(F), s.ctypes.data_as(F), 8)
        t = np.where((t <= 0) | (t > 60), 60, t); res.append((float(np.mean(t)), float(np.median(t)), yaw))
    given = min(res, key=lambda r: abs((r[2] - float(v[3]) + math.pi) % math.tau - math.pi))
    best = max(res, key=lambda r: r[1])
    print(line.strip(), '| given mean %.1f med %.1f | best yaw %.4f mean %.1f med %.1f' % (given[0], given[1], best[2], best[0], best[1]))
