"""Read-only: extract world-space opaque occluder triangles, zone doorways (cluster portals) and the PVS.

Occluders are deliberately conservative: only parts drawn as opaque (part types 2 and 3) whose
material is a plain opaque shader (rmsh with alpha test off and opaque blend) or terrain, and,
for placed pieces, only pieces at least --min-radius world units across.
"""
import argparse, collections, struct, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource

p = argparse.ArgumentParser(); p.add_argument('source', type=Path); p.add_argument('out', type=Path)
p.add_argument('--min-radius', type=float, default=1.0)
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
compressions = c.block(bsp + 0x2f0, 44)
meshes = c.block(bsp + 0x2e4, 76)
vb, ib = r.buffers('vertex'), r.buffers('index')

# materials: which are solid occluders
solid = []; kinds = collections.Counter()
for mat in c.block(bsp + 0xC0, 0x24):
    datum = c.u(mat + 0xC); tag = c.tags.get(datum & 65535); ok = False; why = 'none'
    if tag:
        why = tag['group']
        if tag['group'] == 'rmtr': ok = True
        elif tag['group'] == 'rmsh':
            opts = [c.unpack('h', o)[0] for o in c.block(tag['offset'] + 0x10, 2)]
            ok = len(opts) >= 8 and opts[2] == 0 and opts[7] == 0
            why = 'rmsh solid' if ok else 'rmsh alpha/blend'
    solid.append(ok); kinds[why] += 1
print('materials', dict(kinds))


def payload(at):
    ptr = r.fix[at]; return r.raw[{0x40000000: 0, 0x60000000: 1}[ptr & 0xe0000000]], ptr & 0x1fffffff


def mesh_tris(mi):
    """Return (local positions Nx3 float64, solid triangle index array Tx3) or None."""
    m = meshes[mi]
    vi, ii = c.unpack('h', m + 24)[0], c.unpack('h', m + 40)[0]
    if vi < 0 or ii < 0 or c.data[m + 0x30] != 3: return None
    n, fmt, stride = r.unpack('IHH', vb[vi]); raw, off = payload(vb[vi] + 20)
    if (fmt, stride) == (2, 24):
        if mi not in comp_of: return None
        b = np.array(c.unpack('6f', compressions[comp_of[mi]] + 4)).reshape(3, 2)
        xyz = np.ndarray((n, 3), '>u2', raw, off, (stride, 2)) / 65535 * (b[:, 1] - b[:, 0]) + b[:, 0]
    elif (fmt, stride) == (1, 32):
        xyz = np.ndarray((n, 3), '>f4', raw, off, (stride, 4)).astype(np.float64)
    else:
        return None
    iraw, ioff = payload(ib[ii] + 16); length = r.unpack('I', ib[ii] + 4)[0]
    indices = np.frombuffer(iraw, '>u2', length // 2, ioff)
    out = []
    for part in c.block(m, 16):
        mat, _, start, count = c.unpack('hhHH', part); ptype = c.data[part + 12]
        if ptype not in (2, 3) or count < 3 or not (0 <= mat < len(solid)) or not solid[mat]: continue
        sel = indices[start:start + count // 3 * 3]
        if sel.max() >= n: continue
        out.append(sel.reshape(-1, 3))
    if not out: return xyz, np.zeros((0, 3), dtype=np.int64)
    return xyz, np.concatenate(out).astype(np.int64)


tris = []; stats = collections.Counter()
clusters = c.block(bsp + 0xB4, 0xDC)
cluster_bounds = np.array([c.unpack('6f', cl) for cl in clusters])
for ci, cl in enumerate(clusters):
    mi = c.unpack('h', cl + 0x9C)[0]
    if mi < 0: continue
    g = mesh_tris(mi)
    if g is None: stats['world mesh unreadable'] += 1; continue
    xyz, t = g
    if len(t):
        w = xyz[t]; tris.append(w); stats['world tris'] += len(t)
        lo, hi = w.reshape(-1, 3).min(0), w.reshape(-1, 3).max(0); bb = cluster_bounds[ci]
        if not (lo[0] >= bb[0] - 1 and hi[0] <= bb[1] + 1 and lo[1] >= bb[2] - 1 and hi[1] <= bb[3] + 1): stats['world mesh outside its zone bounds'] += 1
cache = {}
for i, at in enumerate(c.block(bsp + 0x1B0, 0x78)):
    scale = c.unpack('f', at)[0]; fwd = np.array(c.unpack('3f', at + 4)); left = np.array(c.unpack('3f', at + 0x10)); up = np.array(c.unpack('3f', at + 0x1C))
    pos = np.array(c.unpack('3f', at + 0x28)); di = c.unpack('h', at + 0x34)[0]
    centre = np.array(c.unpack('3f', at + 0x40)); radius = c.unpack('f', at + 0x4C)[0]
    if di not in def_mesh: stats['placement without definition'] += 1; continue
    mi = def_mesh[di]
    if mi not in cache: cache[mi] = mesh_tris(mi)
    g = cache[mi]
    if g is None: stats['placement mesh unreadable'] += 1; continue
    xyz, t = g
    if not len(t): continue
    if radius < a.min_radius: stats['small placement tris ignored'] += len(t); continue
    world = pos + scale * (xyz[:, :1] * fwd + xyz[:, 1:2] * left + xyz[:, 2:3] * up)
    d = np.linalg.norm(world[np.unique(t)] - centre, axis=1).max()
    if d > radius * 1.05 + 0.05: stats['placement outside its sphere'] += 1
    tris.append(world[t]); stats['placement tris'] += len(t)
tris = np.concatenate(tris).astype(np.float32)
portals = []; pclusters = []
for po in c.block(bsp + 0x6C, 0x28):
    back, front = c.unpack('2h', po); verts = np.array([c.unpack('3f', v) for v in c.block(po + 0x1C, 0xC)], dtype=np.float32)
    portals.append(verts); pclusters.append((back, front))
rows = c.block(c.block(c.block(sc + 0x3C, 0x2C)[0] + 0x14, 0x54)[0], 0xC); n = len(rows)
vis = np.zeros((n, n), dtype=bool)
for i, row in enumerate(rows):
    w = [c.u(x) for v in c.block(row, 0xC)[:1] for x in c.block(v, 4)]
    for j in range(n): vis[i, j] = w[j // 32] >> (j % 32) & 1
print(dict(stats)); print('occluder triangles', len(tris), 'portals', len(portals), 'zones', n, 'visible pairs', int(vis.sum()))
np.savez(a.out, tris=tris, portal_counts=np.array([len(v) for v in portals]), portal_verts=np.concatenate(portals),
         portal_clusters=np.array(pclusters), vis=vis, cluster_bounds=cluster_bounds)
c.close()
