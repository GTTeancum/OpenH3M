import ctypes as C, sys, math
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
d = np.load(sys.argv[1]); tris = np.ascontiguousarray(d['tris'], dtype=np.float32)
lib = C.CDLL(str(ROOT / 'work/speed-review/deps/raycast.dll')); F = C.POINTER(C.c_float)
lib.rc_build.argtypes = [F, C.c_int]; lib.rc_render.argtypes = [F, F, C.c_int, F, F, C.c_int]
lib.rc_build(tris.ctypes.data_as(F), len(tris))
v = tris.reshape(-1, 3); print('bounds', v.min(0), v.max(0), 'median', np.median(v, 0))
def cast(o, dirs):
    o = np.array(o, np.float32); dirs = np.ascontiguousarray(dirs, np.float32); t = np.zeros(len(dirs), np.float32); s = np.zeros(len(dirs), np.float32)
    lib.rc_render(o.ctypes.data_as(F), dirs.ctypes.data_as(F), len(dirs), t.ctypes.data_as(F), s.ctypes.data_as(F), 8); return t
z = float(sys.argv[2]); x0, x1, y0, y1 = map(float, sys.argv[3:7]); step = float(sys.argv[7])
ring = np.array([[math.cos(a), math.sin(a), 0] for a in np.linspace(0, math.tau, 72, endpoint=False)])
for y in np.arange(y1, y0 - 1e-6, -step):
    row = ''
    for x in np.arange(x0, x1 + 1e-6, step):
        down = cast([x, y, z + 0.62], [[0, 0, -1]])[0]
        if not (0.4 < down < 1.0): row += '  . '; continue
        t = cast([x, y, z + 0.62], ring); t = np.where((t <= 0) | (t > 60), 60, t)
        row += '%3d ' % round(float(np.median(t)))
    print('%6.1f %s' % (y, row))
print('x:', ' '.join('%3d' % round(x) for x in np.arange(x0, x1 + 1e-6, step)))
