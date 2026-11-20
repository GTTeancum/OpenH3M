"""Offline before/after preview renders of a map's opaque geometry (flat shaded, back faces culled).

Not the game's renderer: no textures or lighting. It shows shape, silhouettes and holes only.
"""
import argparse, ctypes as C, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource

p = argparse.ArgumentParser(); p.add_argument('before', type=Path); p.add_argument('after', type=Path); p.add_argument('vis', type=Path)
p.add_argument('outdir', type=Path); p.add_argument('--zone', type=int, required=True); p.add_argument('--views', type=int, default=4)
p.add_argument('--width', type=int, default=800); p.add_argument('--height', type=int, default=450)
a = p.parse_args(); a.outdir.mkdir(parents=True, exist_ok=True)
lib = C.CDLL(str(ROOT / 'work/speed-review/deps/raycast.dll')); F = C.POINTER(C.c_float); I = C.POINTER(C.c_int)
lib.rc_build.argtypes = [F, C.c_int]; lib.rc_render.argtypes = [F, F, C.c_int, F, F, C.c_int]
lib.rc_surroundings.argtypes = [F, C.c_int, C.c_int, I, I, I, C.c_int]


def world_tris(path):
    c = Cache(path)
    sc = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
    lm = c.tags[c.u(sc + 0x6fc) & 65535]['offset']; lb = c.block(lm + 4, 436)[0]; r = Resource(c, c.u(lb + 0x1ac))
    bsp = next(t['offset'] for t in c.tags.values() if t['group'] == 'sbsp')
    cr = Resource(c, c.u(bsp + 0x37c)); definitions = cr.ptr(cr.root + 16); def_mesh = {}; comp_of = {}
    for i in range(cr.unpack('I', cr.root + 12)[0]):
        mesh, comp = cr.unpack('2H', definitions + i * 184 + 0xb0); def_mesh[i] = mesh; comp_of[mesh] = comp
    compressions = c.block(bsp + 0x2f0, 44); meshes = c.block(bsp + 0x2e4, 76); vb, ib = r.buffers('vertex'), r.buffers('index')
    def payload(at):
        ptr = r.fix[at]; return r.raw[{0x40000000: 0, 0x60000000: 1}[ptr & 0xe0000000]], ptr & 0x1fffffff
    def mesh(mi):
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
        out = []
        for part in c.block(m, 16):
            _, _, start, count = c.unpack('hhHH', part)
            if c.data[part + 12] not in (2, 3) or count < 3: continue
            sel = indices[start:start + count // 3 * 3]
            if sel.max() < n: out.append(sel.reshape(-1, 3).astype(np.int64))
        return (xyz, np.concatenate(out)) if out else None
    tris = []; cache = {}
    for cl in c.block(bsp + 0xB4, 0xDC):
        mi = c.unpack('h', cl + 0x9C)[0]
        g = mesh(mi) if mi >= 0 else None
        if g: tris.append(g[0][g[1]])
    for at in c.block(bsp + 0x1B0, 0x78):
        scale = c.unpack('f', at)[0]; fwd = np.array(c.unpack('3f', at + 4)); left = np.array(c.unpack('3f', at + 0x10)); up = np.array(c.unpack('3f', at + 0x1C))
        pos = np.array(c.unpack('3f', at + 0x28)); di = c.unpack('h', at + 0x34)[0]
        if di not in def_mesh: continue
        mi = def_mesh[di]
        if mi not in cache: cache[mi] = mesh(mi)
        g = cache[mi]
        if g is None: continue
        world = pos + scale * (g[0][:, :1] * fwd + g[0][:, 1:2] * left + g[0][:, 2:3] * up)
        tris.append(world[g[1]])
    c.close()
    return np.ascontiguousarray(np.concatenate(tris), dtype=np.float32)


d = np.load(a.vis); polys = np.split(d['portal_verts'], np.cumsum(d['portal_counts'])[:-1]); pcl = d['portal_clusters']
bounds = d['cluster_bounds'][a.zone]; centre = np.array([(bounds[0] + bounds[1]) / 2, (bounds[2] + bounds[3]) / 2, (bounds[4] + bounds[5]) / 2])
cands = np.array([poly.mean(0) for poly, (b_, f_) in zip(polys, pcl) if a.zone in (b_, f_) and len(poly) >= 3], dtype=np.float32)
TA = world_tris(a.before); TB = world_tris(a.after)
print('triangles drawn before', len(TA), 'after', len(TB))
lib.rc_build(TA.ctypes.data_as(F), len(TA))
f = np.zeros(len(cands), np.int32); bk = np.zeros(len(cands), np.int32); ms = np.zeros(len(cands), np.int32)
lib.rc_surroundings(np.ascontiguousarray(cands).ctypes.data_as(F), len(cands), 64, f.ctypes.data_as(I), bk.ctypes.data_as(I), ms.ctypes.data_as(I), 8)
good = cands[(f >= 0.9 * np.maximum(f + bk, 1)) & (f + bk > 0)]
print('open doorway centres for zone', a.zone, ':', len(good), 'of', len(cands))
# pick views spread apart
order = [0]
while len(order) < min(a.views, len(good)):
    dist = np.min(np.linalg.norm(good[:, None] - good[order][None], axis=2), axis=1); order.append(int(np.argmax(dist)))
cams = []
for i in order:
    cams.append((good[i], centre))                      # from the doorway toward the room centre
    cams.append((good[i] + (centre - good[i]) * 0.55, centre))   # closer in


def rays(eye, target):
    fwd = target - eye; fwd /= np.linalg.norm(fwd); upv = np.array([0, 0, 1.0])
    right = np.cross(fwd, upv); right /= max(np.linalg.norm(right), 1e-9); up = np.cross(right, fwd)
    w, h = a.width, a.height; t = np.tan(np.radians(70) / 2)
    xs = (np.arange(w) + .5) / w * 2 - 1; ys = 1 - (np.arange(h) + .5) / h * 2
    dirs = fwd[None, None] + xs[None, :, None] * t * right[None, None] + ys[:, None, None] * t * h / w * up[None, None]
    return np.ascontiguousarray(dirs.reshape(-1, 3), dtype=np.float32)


def render(tris, eye, dirs):
    lib.rc_build(tris.ctypes.data_as(F), len(tris))
    t = np.zeros(len(dirs), np.float32); s = np.zeros(len(dirs), np.float32)
    lib.rc_render(np.ascontiguousarray(eye, dtype=np.float32).ctypes.data_as(F), dirs.ctypes.data_as(F), len(dirs), t.ctypes.data_as(F), s.ctypes.data_as(F), 14)
    return t.reshape(a.height, a.width), s.reshape(a.height, a.width)


summary = []
all_dirs = [rays(np.array(e, dtype=np.float64), np.array(tg, dtype=np.float64)) for e, tg in cams]
ra = []; rb = []
lib.rc_build(TA.ctypes.data_as(F), len(TA))
for (eye, _), dirs in zip(cams, all_dirs):
    t = np.zeros(len(dirs), np.float32); s = np.zeros(len(dirs), np.float32)
    lib.rc_render(np.ascontiguousarray(eye, dtype=np.float32).ctypes.data_as(F), dirs.ctypes.data_as(F), len(dirs), t.ctypes.data_as(F), s.ctypes.data_as(F), 14)
    ra.append((t.reshape(a.height, a.width), s.reshape(a.height, a.width)))
lib.rc_build(TB.ctypes.data_as(F), len(TB))
for (eye, _), dirs in zip(cams, all_dirs):
    t = np.zeros(len(dirs), np.float32); s = np.zeros(len(dirs), np.float32)
    lib.rc_render(np.ascontiguousarray(eye, dtype=np.float32).ctypes.data_as(F), dirs.ctypes.data_as(F), len(dirs), t.ctypes.data_as(F), s.ctypes.data_as(F), 14)
    rb.append((t.reshape(a.height, a.width), s.reshape(a.height, a.width)))


def shade(t, s):
    img = np.where(t > 0, 40 + 200 * np.clip(s, 0, 1) * np.exp(-np.maximum(t, 0) / 60), 12)
    return np.clip(img, 0, 255).astype(np.uint8)


for vi, ((ta, sa), (tb_, sb)) in enumerate(zip(ra, rb)):
    A = shade(ta, sa); B = shade(tb_, sb)
    hole = (ta > 0) & (tb_ < 0)                       # geometry before, nothing after
    depth = (ta > 0) & (tb_ > 0) & (np.abs(ta - tb_) > 0.05)   # surface moved by more than 15 cm
    diff = np.stack([B, B, B], axis=2).astype(np.uint8)
    diff[depth] = [255, 170, 0]; diff[hole] = [255, 0, 0]
    canvas = Image.new('RGB', (a.width * 3 + 20, a.height + 24), (0, 0, 0))
    canvas.paste(Image.fromarray(A).convert('RGB'), (0, 24)); canvas.paste(Image.fromarray(B).convert('RGB'), (a.width + 10, 24)); canvas.paste(Image.fromarray(diff), (a.width * 2 + 20, 24))
    dr = ImageDraw.Draw(canvas); dr.text((4, 4), 'before', fill=(255, 255, 255)); dr.text((a.width + 14, 4), 'after', fill=(255, 255, 255)); dr.text((a.width * 2 + 24, 4), 'after, changes marked (red = hole, orange = moved > 15 cm)', fill=(255, 255, 255))
    canvas.save(a.outdir / f'view-{vi}.png')
    px = a.width * a.height
    summary.append(dict(view=vi, hole_pixels_pct=round(100 * hole.sum() / px, 3), moved_pixels_pct=round(100 * depth.sum() / px, 3), covered_pct=round(100 * (ta > 0).sum() / px, 1)))
    print(summary[-1])
