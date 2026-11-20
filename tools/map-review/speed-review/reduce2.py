"""Deep triangle reduction of opaque placed pieces with regenerated culling groups.

Each opaque part is simplified as a whole (original vertices kept, part borders locked),
the surviving triangles are regrouped into the part's existing subpart slots, and the mesh's
subpart MOPP is regenerated from the new group bounds using only instruction forms validated
against stock maps (mopp_validate.py / mopp_wide_check.py): cuts 0x26-0x28, splits 0x10-0x12
and 0x23-0x25, terminals 0x30-0x4f / 0x50 / 0x51. Code never grows: it is zero padded to the
original length. Vertex buffers, collision, placements, materials and the per-part MOPP are untouched.
"""
import argparse, ctypes as C, hashlib, json, math, struct, sys, zlib
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
sys.path.insert(0, str(Path(__file__).parent))
from cache_reader import Cache
from resource_reader import Resource
from mopp_validate import walk, mopp_objects

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path); p.add_argument('--xex', type=Path, required=True)
p.add_argument('--out', type=Path); p.add_argument('--report', type=Path, required=True)
p.add_argument('--tolerance', type=float, default=.01, help='max geometric error in world units')
p.add_argument('--ratio', type=float, default=.4, help='target fraction of triangles to keep per part')
p.add_argument('--min-part-tris', type=int, default=24)
p.add_argument('--only-meshes', type=str, default='', help='comma list; default all eligible')
p.add_argument('--weld', action='store_true', help='simplify across texture/normal seams (positions welded); corners then reuse the best matching original vertex, which can smear textures')
a = p.parse_args()
only = {int(x) for x in a.only_meshes.split(',') if x}
c = Cache(a.source)
sc = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
lm = c.tags[c.u(sc + 0x6fc) & 65535]['offset']; lb = c.block(lm + 4, 436)[0]
datum = c.u(lb + 0x1ac); r = Resource(c, datum)
bsp = next(t['offset'] for t in c.tags.values() if t['group'] == 'sbsp')
cr = Resource(c, c.u(bsp + 0x37c)); definitions = cr.ptr(cr.root + 16)
compression_by_mesh = {}
for i in range(cr.unpack('I', cr.root + 12)[0]):
    mesh, comp = cr.unpack('2H', definitions + i * 184 + 0xb0)
    assert mesh not in compression_by_mesh or compression_by_mesh[mesh] == comp
    compression_by_mesh[mesh] = comp
compressions = c.block(bsp + 0x2f0, 44)
meshes = c.block(bsp + 0x2e4, 76); light_meshes = c.block(lb + 0x134, 76)
mopps = c.block(bsp + 0x320, 0x20); lmopps = c.block(lb + 0x170, 0x20)
assert len(meshes) == len(light_meshes) == len(mopps) == len(lmopps)
vb, ib = r.buffers('vertex'), r.buffers('index')
lib = C.CDLL(str(ROOT / 'work/speed-review/deps/meshoptimizer.dll'))
U = C.POINTER(C.c_uint); F = C.POINTER(C.c_float)
lib.meshopt_simplifyWithAttributes.argtypes = [U, U, C.c_size_t, F, C.c_size_t, C.c_size_t, F, C.c_size_t, F, C.c_size_t, C.c_void_p, C.c_size_t, C.c_float, C.c_uint, F]
lib.meshopt_simplifyWithAttributes.restype = C.c_size_t
lib.meshopt_optimizeVertexCache.argtypes = [U, U, C.c_size_t, C.c_size_t]
lib.meshopt_simplify.argtypes = [U, U, C.c_size_t, F, C.c_size_t, C.c_size_t, C.c_size_t, C.c_float, C.c_uint, F]
lib.meshopt_simplify.restype = C.c_size_t
weights = (C.c_float * 5)(.5, .5, .5, 10, 10)
patched = {}; writes = {}; rows = []; skipped = []; total = 0; smeared = 0


def payload(at):
    ptr = r.fix[at]; return {0x40000000: 0, 0x60000000: 1}[ptr & 0xe0000000], ptr & 0x1fffffff


def record(at, data):
    assert at not in writes or writes[at] == data
    writes[at] = data


def groups_of(tris, centroids, g):
    """Split triangle ids into g spatially compact groups of similar size."""
    if g <= 1 or len(tris) <= 1:
        return [tris]
    pts = centroids[tris]; axis = int(np.argmax(pts.max(0) - pts.min(0)))
    order = tris[np.argsort(pts[:, axis], kind='stable')]
    gl = g // 2; nl = max(1, min(len(order) - 1, round(len(order) * gl / g)))
    return groups_of(order[:nl], centroids, gl) + groups_of(order[nl:], centroids, g - gl)


def terminal(key):
    if key < 32: return bytes([0x30 + key])
    if key < 256: return bytes([0x50, key])
    assert key < 65536
    return bytes([0x51, key >> 8, key & 255])


def emit(items, cuts):
    if len(items) == 1:
        key, lo, hi = items[0]
        out = b''
        if cuts:
            for ax in (2, 1, 0): out += bytes([0x26 + ax, lo[ax], hi[ax]])
        return out + terminal(key)
    centers = np.array([[(l + h) / 2 for l, h in zip(lo, hi)] for _, lo, hi in items])
    ax = int(np.argmax(centers.max(0) - centers.min(0)))
    order = sorted(range(len(items)), key=lambda i: (centers[i][ax], i))
    mid = len(order) // 2
    left = [items[i] for i in order[:mid]]; right = [items[i] for i in order[mid:]]
    L = emit(left, cuts); R = emit(right, cuts)
    left_max = max(h[ax] for _, _, h in left); right_min = min(l[ax] for _, l, _ in right)
    if len(L) <= 255:
        return bytes([0x10 + ax, left_max, right_min, len(L)]) + L + R
    if len(L) > 65535: raise ValueError('MOPP branch too far')
    return bytes([0x23 + ax, left_max, right_min, 0, 0, len(L) >> 8, len(L) & 255]) + L + R


def build_mopp(items, limit):
    lo = [min(i[1][k] for i in items) for k in range(3)]; hi = [max(i[2][k] for i in items) for k in range(3)]
    root = b''.join(bytes([0x26 + ax, lo[ax], hi[ax]]) for ax in (2, 1, 0))
    for cuts in (True, False):
        code = root + emit(items, cuts)
        if len(code) <= limit: return code, cuts
    return None, None


for mi, (m, lmm) in enumerate(zip(meshes, light_meshes)):
    parts = c.block(m, 16); mesh_tris = sum(c.unpack('H', q + 6)[0] // 3 for q in parts); total += mesh_tris
    if only and mi not in only: continue
    vi, ii = c.unpack('h', m + 24)[0], c.unpack('h', m + 40)[0]
    if vi < 0 or ii < 0 or mi not in compression_by_mesh: continue
    n, fmt, stride = r.unpack('IHH', vb[vi])
    if (fmt, stride) != (2, 24) or c.unpack('B', m + 0x30)[0] != 3: continue
    size = c.u(mopps[mi])
    if not size or c.u(lmopps[mi]) != size: continue
    mat = c.pointer(c.u(mopps[mi] + 0xC)); lat = c.pointer(c.u(lmopps[mi] + 0xC))
    blob = bytes(c.data[mat:mat + size])
    if bytes(c.data[lat:lat + size]) != blob: skipped.append((mi, 'lightmap mopp differs')); continue
    objs = mopp_objects(blob)
    lparts = c.block(lmm, 16); subs = c.block(m + 12, 8); lsubs = c.block(lmm + 12, 8)
    if len(objs) != 2 or len(parts) != len(lparts) or len(subs) != len(lsubs): skipped.append((mi, 'layout')); continue
    (moff, mscale, mcode, code_at, code_size) = objs[0]
    seg, offset = payload(vb[vi] + 20); raw = r.raw[seg]
    bounds = np.array(c.unpack('6f', compressions[compression_by_mesh[mi]] + 4)).reshape(3, 2)
    xyz = np.ascontiguousarray(np.ndarray((n, 3), '>u2', raw, offset, (stride, 2)) / 65535 * (bounds[:, 1] - bounds[:, 0]) + bounds[:, 0], dtype=np.float32)
    pos16 = np.array(np.ndarray((n, 3), '>u2', raw, offset, (stride, 2))); rep = None
    packed = np.ndarray((n,), '>u4', raw, offset + 12, (stride,)).astype(np.uint32)
    normals = []
    for shift, bits in ((0, 10), (10, 11), (21, 11)):
        val = ((packed >> shift) & ((1 << bits) - 1)).astype(np.int32)
        val = np.where(val & (1 << (bits - 1)), val - (1 << bits), val)
        normals.append(np.maximum(-1, val / ((1 << (bits - 1)) - 1)))
    uv = np.ndarray((n, 2), '>u2', raw, offset + 8, (stride, 2)) / 65535
    attrs = np.ascontiguousarray(np.column_stack((*normals, uv)), dtype=np.float32)
    iseg, ioff = payload(ib[ii] + 16); length = r.unpack('I', ib[ii] + 4)[0]
    indices = np.frombuffer(r.raw[iseg], '>u2', length // 2, ioff)
    extent = float((xyz.max(0) - xyz.min(0)).max())
    if extent <= 0: continue
    rel = min(1.0, a.tolerance / extent)
    quant = lambda pts: (pts.astype(np.float64) - np.array(moff)) * mscale / 65536.0
    sub_rows = [c.unpack('2H', s) for s in subs]
    new_sub = {}; part_new = {}; mesh_rows = []; bad = False
    for pi, part in enumerate(parts):
        start, count, first, num = c.unpack('4H', part + 4)
        if c.unpack('4H', lparts[pi] + 4) != (start, count, first, num): bad = True; break
        if c.unpack('B', part + 12)[0] not in (1, 2, 3) or c.data[part + 13] & 8 or count < a.min_part_tris * 3 or count % 3 or not num: continue
        pos = start; ok = True
        for si in range(first, first + num):
            s0, sz = sub_rows[si]
            if s0 != pos or sz % 3 or c.unpack('2H', lsubs[si]) != (s0, sz): ok = False; break
            pos += sz
        if not ok or pos != start + count: continue
        src = np.ascontiguousarray(indices[start:start + count], dtype=np.uint32)
        if src.max() >= n: continue
        dest = np.empty_like(src); error = C.c_float()
        if a.weld:
            if rep is None:
                _, first_idx, inv = np.unique(pos16, axis=0, return_index=True, return_inverse=True)
                rep = first_idx[inv.reshape(-1)].astype(np.uint32)
            welded = rep[src].reshape(-1, 3)
            welded = np.ascontiguousarray(welded[(welded[:, 0] != welded[:, 1]) & (welded[:, 1] != welded[:, 2]) & (welded[:, 0] != welded[:, 2])].reshape(-1), dtype=np.uint32)
            if len(welded) < 9: continue
            wdest = np.empty_like(welded)
            kept = lib.meshopt_simplify(wdest.ctypes.data_as(U), welded.ctypes.data_as(U), len(welded), xyz.ctypes.data_as(F), n, 12,
                int(len(welded) * a.ratio) // 3 * 3, rel, 1, C.byref(error))
            if kept == 0 or kept >= count or kept % 3: continue
            # islands of the original part: vertices connected through shared indices
            parent = {}
            def find(x):
                while parent.setdefault(x, x) != x:
                    parent[x] = parent[parent[x]]; x = parent[x]
                return x
            for t3 in src.reshape(-1, 3).tolist():
                ra_, rb_, rc_ = find(t3[0]), find(t3[1]), find(t3[2]); parent[rb_] = ra_; parent[find(rc_)] = ra_
            wedges = {}
            for v in np.unique(src).tolist(): wedges.setdefault(int(rep[v]), []).append((v, find(v)))
            nrm3 = attrs[:, :3].astype(np.float64); out_t = []
            for r0, r1, r2 in wdest[:kept].reshape(-1, 3).tolist():
                fn = np.cross(xyz[r1].astype(np.float64) - xyz[r0], xyz[r2].astype(np.float64) - xyz[r0]); ln_ = np.linalg.norm(fn)
                fn = fn / ln_ if ln_ > 0 else fn
                cands = [wedges[r0], wedges[r1], wedges[r2]]
                common = set(i for _, i in cands[0]) & set(i for _, i in cands[1]) & set(i for _, i in cands[2])
                best = None
                for isl in common:
                    pick = [max((v for v, i in cnd if i == isl), key=lambda v: float(nrm3[v] @ fn)) for cnd in cands]
                    score = sum(float(nrm3[v] @ fn) for v in pick)
                    if best is None or score > best[0]: best = (score, pick)
                if best is None:
                    best = (0, [max((v for v, _ in cnd), key=lambda v: float(nrm3[v] @ fn)) for cnd in cands]); smeared += 1
                out_t.append(best[1])
            dest = np.ascontiguousarray(np.array(out_t, dtype=np.uint32).reshape(-1))
        else:
            kept = lib.meshopt_simplifyWithAttributes(dest.ctypes.data_as(U), src.ctypes.data_as(U), count,
                xyz.ctypes.data_as(F), n, 12, attrs.ctypes.data_as(F), 20, weights, 5, None,
                int(count * a.ratio) // 3 * 3, rel, 1, C.byref(error))
        if kept == 0 or kept >= count or kept % 3: continue
        tri = dest[:kept].reshape(-1, 3)
        centroids = xyz[tri].mean(1)
        nonempty = sum(1 for si in range(first, first + num) if sub_rows[si][1])
        avg = (count // 3) / max(nonempty, 1)
        g = int(max(1, min(num, round(len(tri) / max(avg, 1)))))
        grp = groups_of(np.arange(len(tri)), centroids, g)
        out_idx = []; ranges = []
        for gi in range(num):
            if gi < len(grp):
                ids = tri[grp[gi]].reshape(-1).astype(np.uint32)
                cache = np.empty(len(ids), dtype=np.uint32)
                lib.meshopt_optimizeVertexCache(cache.ctypes.data_as(U), np.ascontiguousarray(ids).ctypes.data_as(U), len(ids), n)
                ranges.append((start + len(out_idx), len(ids))); out_idx.extend(cache.tolist())
            else:
                ranges.append((start + len(out_idx), 0))
        assert len(out_idx) == kept
        for gi, rg in enumerate(ranges): new_sub[first + gi] = rg
        part_new[pi] = (start, count, kept, out_idx)
        mesh_rows.append(dict(mesh=mi, part=pi, before=count // 3, after=kept // 3, error_world_units=error.value * extent, groups=len(grp), slots=num))
    if bad or not part_new: continue
    # boxes for every subpart of the mesh (new or original)
    new_indices = np.array(indices[:], dtype=np.uint32)
    for pi, (start, count, kept, out_idx) in part_new.items():
        new_indices[start:start + count] = np.array(out_idx + [0] * (count - kept), dtype=np.uint32)
    items = []; fail = False
    for si in range(len(subs)):
        s0, sz = new_sub.get(si, sub_rows[si])
        if not sz: continue
        sel = new_indices[s0:s0 + sz]
        if sel.max() >= n: fail = True; break
        q = quant(xyz[sel])
        lo = [int(max(0, min(255, math.floor(v) - 1))) for v in q.min(0)]
        hi = [int(max(0, min(255, math.ceil(v) + 1))) for v in q.max(0)]
        items.append((si, lo, hi))
    if fail or not items: skipped.append((mi, 'index range')); continue
    code, with_cuts = build_mopp(items, code_size)
    if code is None: skipped.append((mi, 'mopp does not fit')); continue
    # self-check with the validated walker
    found = {}
    for key, lo, hi, resc, exo in walk(code, False):
        assert not resc and not exo
        found.setdefault(key, []).append((lo, hi))
    for si, lo, hi in items:
        assert any(all(l[k] <= lo[k] and h[k] >= hi[k] for k in range(3)) for l, h in found.get(si, [])), (mi, si)
    assert set(found) == {i[0] for i in items}
    padded = code + bytes(code_size - len(code))
    for base_at in (mat, lat): record(base_at + code_at, padded)
    data = patched.setdefault(iseg, bytearray(r.raw[iseg]))
    for pi, (start, count, kept, out_idx) in part_new.items():
        data[ioff + start * 2:ioff + (start + count) * 2] = np.array(out_idx + [0] * (count - kept), dtype='>u2').tobytes()
        for at in (parts[pi], lparts[pi]): record(at + 6, struct.pack('>H', kept))
    for si, (s0, sz) in new_sub.items():
        for at in (subs[si], lsubs[si]): record(at, struct.pack('>2H', s0, sz))
    for row in mesh_rows: row['leaf_cuts'] = with_cuts
    rows.extend(mesh_rows)
removed = sum(x['before'] - x['after'] for x in rows)
report = dict(source=str(a.source), stored_triangles_before=total, stored_triangles_after=total - removed,
              reduction_percent=removed / total * 100, target_ratio=a.ratio, tolerance_world_units=a.tolerance,
              changed_parts=len(rows), changed_meshes=len({x['mesh'] for x in rows}), welded=a.weld, triangles_spanning_texture_islands=smeared, skipped=skipped, rows=rows)
if a.out:
    from map_builder import MapBuilder
    from build_scenario_checkpoint import resource_salt
    assert not a.out.exists(), 'refusing to overwrite'
    b = MapBuilder(a.source, 0); salt = resource_salt(a.xex)
    for at, data in writes.items(): b.put(at - c.start + c.base, str(len(data)) + 's', data)
    zone = next(t['offset'] for t in c.tags.values() if t['group'] == 'zone'); play = next(t['offset'] for t in c.tags.values() if t['group'] == 'play')
    resource = c.block(zone + 88, 64)[datum & 65535]; location = c.block(play + 48, 16)[c.unpack('h', resource + 34)[0]]
    pages = c.block(play + 24, 88); page_ids = c.unpack('2h', location); offsets = c.unpack('2I', location + 4)
    for segment, data in patched.items():
        assert offsets[segment] == 0
        page = pages[page_ids[segment]]; assert c.unpack('h', page + 4)[0] == -1 and c.u(page + 16) == len(data)
        compressed = zlib.compress(bytes(data), 9)[2:-4]; address = page - c.start + c.base
        old_block, old_size = c.unpack('2I', page + 8)
        if len(compressed) <= old_size:
            # Reuse the page's existing place in the file so the map does not grow.
            raw_base = (c.u(0x484) + c.u(0x470)) & 0xffffffff
            original = bytearray(b.original); original[raw_base + old_block:raw_base + old_block + old_size] = compressed + bytes(old_size - len(compressed))
            b.original = bytes(original); new_offset = old_block; report['geometry_page'] = 'rewritten in place'
        else:
            new_offset = b.append_raw(compressed); report['geometry_page'] = 'appended'
        b.put(address + 3, 'B', 0); b.put(address + 8, '4I', new_offset, len(compressed), len(data), zlib.crc32(data) ^ 0xffffffff)
        hashes = b''.join(hashlib.sha1(salt + bytes(x)).digest() for x in (data, data[:1024], data[-1024:]))
        b.put(address + 24, str(len(hashes)) + 's', hashes)
    a.out.write_bytes(b.finish(salt)); b.close()
    check = Cache(a.out); rr = Resource(check, datum)
    assert rr.data == r.data and rr.fix == r.fix
    for segment, original in enumerate(r.raw): assert rr.raw[segment] == patched.get(segment, original)
    for at, data in writes.items():
        new_at = at - c.start + check.start; assert check.data[new_at:new_at + len(data)] == data
    check.close(); report.update(candidate=str(a.out), sha256=hashlib.sha256(a.out.read_bytes()).hexdigest())
a.report.write_text(json.dumps(report, indent=1))
print(json.dumps({k: v for k, v in report.items() if k not in ('rows', 'skipped')}), 'skipped', len(skipped))
c.close()
