"""Read-only: test hypotheses about per-mesh render MOPP semantics against stock data.

For every terminal reached in a mesh's subpart MOPP, the region implied by the path's
cuts/splits must contain the quantised AABB of the subpart the key refers to.
"""
import sys, struct, collections, itertools
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource


def walk(code, split_swapped):
    """Yield (key, lo[3], hi[3], rescaled, exotic) for each reachable terminal."""
    out = []
    stack = [(0, 0, [0, 0, 0], [255, 255, 255], False, False)]
    seen = set()
    while stack:
        at, base, lo, hi, resc, exo = stack.pop()
        lo, hi = list(lo), list(hi)
        while True:
            if not 0 <= at < len(code):
                raise ValueError('branch outside code')
            op = code[at]
            if op == 0:
                break
            if 0x30 <= op <= 0x53:
                key = op - 0x30 if op < 0x50 else int.from_bytes(code[at + 1:at + 1 + op - 0x4f], 'big')
                out.append((key + base, tuple(lo), tuple(hi), resc, exo)); break
            if 1 <= op <= 4:
                resc = True; at += 4
            elif 5 <= op <= 7:
                size = op - 4; at += 1 + size + int.from_bytes(code[at + 1:at + 1 + size], 'big')
            elif op in (9, 10, 11):
                size = {9: 1, 10: 2, 11: 4}[op]; v = int.from_bytes(code[at + 1:at + 1 + size], 'big')
                base = v if op == 11 else base + v; at += size + 1
            elif 0x10 <= op <= 0x12:
                ax = op - 0x10; a, b, off = code[at + 1], code[at + 2], code[at + 3]
                left_hi, right_lo = (b, a) if split_swapped else (a, b)
                rlo, rhi = list(lo), list(hi); rlo[ax] = max(rlo[ax], right_lo)
                stack.append((at + 4 + off, base, rlo, rhi, resc, exo))
                hi[ax] = min(hi[ax], left_hi); at += 4
            elif 0x13 <= op <= 0x1c:
                stack.append((at + 4 + code[at + 3], base, list(lo), list(hi), resc, True)); exo = True; at += 4
            elif 0x20 <= op <= 0x22:
                ax = op - 0x20; v, off = code[at + 1], code[at + 2]
                rlo, rhi = list(lo), list(hi); rlo[ax] = max(rlo[ax], v)
                stack.append((at + 3 + off, base, rlo, rhi, resc, exo))
                hi[ax] = min(hi[ax], v); at += 3
            elif 0x23 <= op <= 0x25:
                ax = op - 0x23; a, b = code[at + 1], code[at + 2]
                lo_off = int.from_bytes(code[at + 3:at + 5], 'big'); ro = int.from_bytes(code[at + 5:at + 7], 'big')
                left_hi, right_lo = (b, a) if split_swapped else (a, b)
                rlo, rhi = list(lo), list(hi); rlo[ax] = max(rlo[ax], right_lo)
                stack.append((at + 7 + ro, base, rlo, rhi, resc, exo))
                hi[ax] = min(hi[ax], left_hi); at += 7 + lo_off
            elif 0x26 <= op <= 0x28:
                ax = op - 0x26; lo[ax] = max(lo[ax], code[at + 1]); hi[ax] = min(hi[ax], code[at + 2]); at += 3
            elif 0x29 <= op <= 0x2b:
                exo = True; at += 7
            else:
                raise ValueError(f'unsupported op {op:#x}')
    return out


def mopp_objects(blob):
    """Split the dataref into hkpMoppCode objects: (offset vec3, scale, code bytes, code file offset)."""
    objs = []; at = 0
    while at + 0x30 <= len(blob):
        ox, oy, oz, scale = struct.unpack_from('>4f', blob, at + 0x10)
        size = struct.unpack_from('>I', blob, at + 0x24)[0]
        code = blob[at + 0x30:at + 0x30 + size]
        objs.append(((ox, oy, oz), scale, code, at + 0x30, size))
        at += 0x30 + ((size + 15) & ~15)
    return objs


def mesh_geometry(c, r, bsp, compressions, compression_by_mesh, vb, ib, mi, m):
    vi, ii = c.unpack('h', m + 24)[0], c.unpack('h', m + 40)[0]
    if vi < 0 or ii < 0 or mi not in compression_by_mesh: return None
    n, fmt, stride = r.unpack('IHH', vb[vi])
    if (fmt, stride) != (2, 24) or c.data[m + 0x30] != 3: return None
    ptr = r.fix[vb[vi] + 20]; raw = r.raw[{0x40000000: 0, 0x60000000: 1}[ptr & 0xe0000000]]; off = ptr & 0x1fffffff
    bounds = np.array(c.unpack('6f', compressions[compression_by_mesh[mi]] + 4)).reshape(3, 2)
    xyz = np.ndarray((n, 3), '>u2', raw, off, (stride, 2)) / 65535 * (bounds[:, 1] - bounds[:, 0]) + bounds[:, 0]
    ptr = r.fix[ib[ii] + 16]; iraw = r.raw[{0x40000000: 0, 0x60000000: 1}[ptr & 0xe0000000]]; ioff = ptr & 0x1fffffff
    length = r.unpack('I', ib[ii] + 4)[0]
    return xyz, np.frombuffer(iraw, '>u2', length // 2, ioff)


def load(path):
    c = Cache(path)
    sc = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
    lm = c.tags[c.u(sc + 0x6fc) & 65535]['offset']; lb = c.block(lm + 4, 436)[0]
    r = Resource(c, c.u(lb + 0x1ac), shared_paths=SHARED)
    bsp = next(t['offset'] for t in c.tags.values() if t['group'] == 'sbsp')
    cr = Resource(c, c.u(bsp + 0x37c), shared_paths=SHARED); definitions = cr.ptr(cr.root + 16)
    cbm = {}
    for i in range(cr.unpack('I', cr.root + 12)[0]):
        mesh, comp = cr.unpack('2H', definitions + i * 184 + 0xb0); cbm[mesh] = comp
    return c, lb, r, bsp, c.block(bsp + 0x2f0, 44), cbm


SHARED = {}
if __name__ == '__main__':
    maps = Path(sys.argv[1])
    SHARED = {'maps\\shared.map': maps / 'shared.map', 'maps\\mainmenu.map': maps / 'mainmenu.map'}
    tally = collections.Counter(); ops = collections.Counter()
    for path in sys.argv[2:]:
        c, lb, r, bsp, compressions, cbm = load(path)
        vb, ib = r.buffers('vertex'), r.buffers('index')
        meshes = c.block(bsp + 0x2e4, 76); mopps = c.block(bsp + 0x320, 0x20); lmopps = c.block(lb + 0x170, 0x20)
        tally['lightmap mopp entries equal count'] += len(mopps) == len(lmopps)
        for mi, m in enumerate(meshes):
            size = c.u(mopps[mi])
            if not size: continue
            g = mesh_geometry(c, r, bsp, compressions, cbm, vb, ib, mi, m)
            if g is None: continue
            xyz, indices = g
            at = c.pointer(c.u(mopps[mi] + 0xC)); blob = bytes(c.data[at:at + size])
            if mi < len(lmopps) and c.u(lmopps[mi]) == size:
                lat = c.pointer(c.u(lmopps[mi] + 0xC)); tally['lightmap blob identical'] += bytes(c.data[lat:lat + size]) == blob; tally['lightmap blob compared'] += 1
            subs = [c.unpack('2H', s) for s in c.block(m + 12, 8)]; parts = [c.unpack('4H', p + 4) for p in c.block(m, 16)]
            reorder = [c.unpack('h', x)[0] for x in c.block(mopps[mi] + 0x14, 2)]
            objs = mopp_objects(blob)
            tally['objects per blob', len(objs)] += 1
            tally['reorder len == 2*subs+2*parts'] += len(reorder) == 2 * len(subs) + 2 * len(parts)
            if len(objs) != 2 or len(reorder) != 2 * len(subs) + 2 * len(parts): continue
            for which, (ranges, table) in enumerate(((subs, reorder[:2 * len(subs)]), ([(p[0], p[1]) for p in parts], reorder[2 * len(subs):]))):
                (off, scale, code, _, _) = objs[which]
                for b in code: pass
                n = len(ranges); A, B = table[:n], table[n:]
                boxes = []
                for start, count in ranges:
                    if not count: boxes.append(None); continue
                    sel = indices[start:start + count]
                    if sel.max() >= len(xyz): boxes.append(None); tally['index beyond vertices', Path(path).name, which] += 1; continue
                    pts = xyz[sel]
                    q = (pts - np.array(off)) * scale / 65536.0
                    boxes.append((q.min(0), q.max(0)))
                for swapped in (False, True):
                    try: terms = walk(code, swapped)
                    except ValueError as e:
                        tally['walk error', which, str(e)[:30]] += 1; break
                    for key, lo, hi, resc, exo in terms:
                        if resc: tally['terminal under rescale', which] += 1; continue
                        for name, idx in (('direct', key), ('A', A[key] if key < n else -1), ('B', B[key] if key < n else -1)):
                            if not 0 <= idx < n or boxes[idx] is None:
                                tally[which, swapped, name, 'invalid'] += 1; continue
                            bl, bh = boxes[idx]
                            ok = all(bl[k] >= lo[k] - 1.01 and bh[k] <= hi[k] + 1.01 for k in range(3))
                            tally[which, swapped, name, 'ok' if ok else 'FAIL'] += 1
                for b in set(code): ops[b] += 0
        c.close()
    for k in sorted(tally, key=str): print(k, tally[k])
