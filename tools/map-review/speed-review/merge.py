"""Merge neighbouring placed pieces into fewer, larger pieces so the game issues fewer draws.

Each group gets one host piece (a piece whose definition is used once). The host's render mesh is
rebuilt to hold every member's triangles, moved into the host's own space, with one part per
material. Members keep their placement and collision but their render mesh is emptied; a shared
definition is only emptied when every placement of it was merged. Per-vertex baked lighting is
carried over vertex for vertex. Collision, materials, placements and cluster data are untouched.
"""
import argparse, hashlib, json, math, struct, sys, zlib, collections
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools')); sys.path.insert(0, str(Path(__file__).parent))
from cache_reader import Cache
from resource_reader import Resource
from source_schema import load_schema
from mopp_validate import walk, mopp_objects

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path); p.add_argument('--xex', type=Path, required=True)
p.add_argument('--out', type=Path); p.add_argument('--report', type=Path, required=True)
p.add_argument('--cell', type=float, default=20.0, help='neighbourhood size in world units')
p.add_argument('--reach', type=float, default=30.0, help='how far a piece may be from its host, world units')
p.add_argument('--fill', type=float, default=1.6, help='hosts per neighbourhood: this many times the minimum that could hold the triangles')
p.add_argument('--kind-mask', type=lambda v: int(v, 0), default=0xffff, help='placement flag bits that must match within a group')
p.add_argument('--max-indices', type=int, default=65532)
p.add_argument('--max-member-tris', type=int, default=1000000, help='leave pieces with more triangles than this alone')
p.add_argument('--subpart-tris', type=int, default=96)
p.add_argument('--limit-groups', type=int, default=0, help='debug: only build the first N groups')
a = p.parse_args()
c = Cache(a.source)
sc = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr'); bsp = next(t['offset'] for t in c.tags.values() if t['group'] == 'sbsp')
zone = next(t['offset'] for t in c.tags.values() if t['group'] == 'zone'); play = next(t['offset'] for t in c.tags.values() if t['group'] == 'play')
lb = c.block(c.tags[c.u(sc + 0x6fc) & 65535]['offset'] + 4, 436)[0]
datum = c.u(lb + 0x1ac); r = Resource(c, datum); cdatum = c.u(bsp + 0x37c); cr = Resource(c, cdatum)
schema = load_schema(c, 'zone'); co = int(next(x for x in schema if x.attrib.get('name') == 'Native Resource Control Data').attrib['offset'], 0)
control_base = c.pointer(c.u(zone + co + 12))


def control_file_offset(d):  # file offset of a resource's control data
    rec = c.block(zone + 88, 64)[d & 65535]; return control_base + c.unpack('I', rec + 20)[0], rec


r_ctl, r_rec = control_file_offset(datum); cr_ctl, _ = control_file_offset(cdatum)
assert bytes(c.data[r_ctl:r_ctl + 64]) == bytes(r.data[:64]) and bytes(c.data[cr_ctl:cr_ctl + 64]) == bytes(cr.data[:64])
fix_at = {c.u(x): x for x in c.block(r_rec + 40, 8)}  # control offset -> file offset of the fixup entry
vb, ib = r.buffers('vertex'), r.buffers('index'); raw = r.raw[0]; assert len(r.raw) < 2 or not len(r.raw[1])
dbase = cr.ptr(cr.root + 16); nd = cr.unpack('I', cr.root + 12)[0]
def_mesh = [cr.unpack('2H', dbase + i * 184 + 0xb0) for i in range(nd)]
assert all(x[1] == i for i, x in enumerate(def_mesh)) and len({x[0] for x in def_mesh}) == nd
meshes = c.block(bsp + 0x2e4, 76); lmeshes = c.block(lb + 0x134, 76); comps = c.block(bsp + 0x2f0, 44); lcomps = c.block(lb + 0x140, 44)
mopps = c.block(bsp + 0x320, 0x20); lmopps = c.block(lb + 0x170, 0x20); inst = c.block(bsp + 0x1B0, 0x78)
assert len(meshes) == len(lmeshes) == len(mopps) == len(lmopps) and len(comps) == len(lcomps) == nd
n118, a118 = c.unpack('II', lb + 0x118); n100, a100 = c.unpack('II', lb + 0x100); assert n118 == len(inst)
at118 = c.pointer(a118); at100 = c.pointer(a100)


def seg_off(at):
    v = r.fix[at]
    return (v & 0x1fffffff) if v & 0xe0000000 == 0x40000000 else None


def unpack_vec(u):
    out = []
    for shift, bits in ((0, 10), (10, 11), (21, 11)):
        v = ((u >> shift) & ((1 << bits) - 1)).astype(np.int64); v = np.where(v & (1 << (bits - 1)), v - (1 << bits), v)
        out.append(np.maximum(-1.0, v / ((1 << (bits - 1)) - 1)))
    return np.stack(out, -1)


def pack_vec(v):
    ln = np.linalg.norm(v, axis=1, keepdims=True); v = v / np.where(ln > 0, ln, 1); u = np.zeros(len(v), dtype=np.uint64)
    for k, (shift, bits) in enumerate(((0, 10), (10, 11), (21, 11))):
        q = np.rint(v[:, k] * ((1 << (bits - 1)) - 1)).astype(np.int64) & ((1 << bits) - 1); u |= q.astype(np.uint64) << np.uint64(shift)
    return u.astype('>u4')


class Piece: pass


pieces = []; use = collections.Counter(c.unpack('h', at + 0x34)[0] for at in inst)
for i, at in enumerate(inst):
    q = Piece(); q.i = i; q.at = at; q.d = c.unpack('h', at + 0x34)[0]; q.ok = False; pieces.append(q)
    if not 0 <= q.d < nd: continue
    q.scale = c.unpack('f', at)[0]; q.R = np.array(c.unpack('9f', at + 4), dtype=np.float64).reshape(3, 3); q.pos = np.array(c.unpack('3f', at + 0x28), dtype=np.float64)
    q.centre = np.array(c.unpack('3f', at + 0x40), dtype=np.float64); q.radius = c.unpack('f', at + 0x4C)[0]; q.flags = c.unpack('H', at + 0x36)[0]
    q.tail = bytes(c.data[at + 0x58:at + 0x78]); q.mi = def_mesh[q.d][0]; m = meshes[q.mi]; q.parts = [c.unpack('hhHHhhbBH', x) for x in c.block(m, 16)]
    if abs(np.linalg.det(q.R) - 1) > 1e-3 or not q.parts or c.unpack('h', at + 0x38)[0] != -1: continue
    e = c.unpack('4h', at118 + i * 8)
    if e[0] != -1 or not 0 <= e[1] < n100: continue
    q.vi = c.unpack('h', m + 24)[0]; q.ii = c.unpack('h', m + 40)[0]; q.li = c.u(at100 + e[1] * 16 + 12)
    if q.vi < 0 or q.ii < 0 or c.unpack('7h', m + 26) != (-1,) * 7 or c.data[m + 0x30] != 3: continue
    if bytes(c.data[m + 24:m + 76]) != bytes(c.data[lmeshes[q.mi] + 24:lmeshes[q.mi] + 76]): continue
    q.n, fmt, stride = r.unpack('IHH', vb[q.vi]); ln = r.unpack('IHH', vb[q.li])
    if (fmt, stride) != (2, 24) or ln != (q.n, 6, 20) or seg_off(vb[q.vi] + 20) is None or seg_off(vb[q.li] + 20) is None or seg_off(ib[q.ii] + 16) is None: continue
    q.nidx = sum(x[3] for x in q.parts)
    if any(x[3] % 3 for x in q.parts) or q.nidx // 3 > a.max_member_tris or q.nidx > a.max_indices: continue
    q.ok = True
# --- grouping: same flags and tail fields, same neighbourhood; packed under the index and vertex limits
kind = lambda q: (q.flags & a.kind_mask, q.tail[:4], q.tail[8:12])
drop = set()
while True:  # settle: a shared definition merges only if every placement of it finds a host
    groups = []; failed = set()
    for k in sorted({kind(q) for q in pieces if q.ok}):
        todo = [q for q in pieces if q.ok and q.d not in drop and kind(q) == k]; singles = [q for q in todo if use[q.d] == 1]
        if not singles: failed |= {q.d for q in todo}; continue
        want = max(1, min(len(singles), math.ceil(a.fill * sum(q.nidx for q in todo) / a.max_indices)))
        seeds = [min(singles, key=lambda q: (q.nidx, q.i))]  # farthest-point seeds among single-use pieces
        dist = np.array([np.linalg.norm(q.centre - seeds[0].centre) for q in singles])
        while len(seeds) < want:
            j = int(np.argmax(dist)); seeds.append(singles[j]); dist = np.minimum(dist, [np.linalg.norm(q.centre - singles[j].centre) for q in singles])
        built = {h.i: [h] for h in seeds}; load = {h.i: [h.nidx, h.n] for h in seeds}; sc_ = np.array([h.centre for h in seeds])
        for q in sorted((q for q in todo if q.i not in built), key=lambda q: (-q.nidx, q.i)):
            dd = np.linalg.norm(sc_ - q.centre, axis=1); placed = False
            for j in np.argsort(dd, kind='stable'):
                h = seeds[int(j)]
                if dd[j] > (a.reach if use[q.d] == 1 else a.reach * 2): break
                if load[h.i][0] + q.nidx <= a.max_indices and load[h.i][1] + q.n <= 65535:
                    built[h.i].append(q); load[h.i][0] += q.nidx; load[h.i][1] += q.n; placed = True; break
            if not placed and use[q.d] > 1: failed.add(q.d)
        groups += [g for g in built.values() if len(g) > 1]
    if not failed: break
    drop |= failed
print('groups', len(groups), 'shared definitions left alone', len(drop), 'their placements', sum(use[d] for d in drop))
if a.limit_groups: groups = groups[:a.limit_groups]
parts_before = sum(len(q.parts) for q in pieces if hasattr(q, 'parts'))


def geometry(q):
    off = seg_off(vb[q.vi] + 20); b = np.array(c.unpack('10f', comps[q.d] + 4), dtype=np.float64)
    v = np.ndarray((q.n, 6), '>u2', raw, off, (24, 2)).astype(np.float64) / 65535
    xyz = v[:, :3] * (b[[1, 3, 5]] - b[[0, 2, 4]]) + b[[0, 2, 4]]; uv = v[:, 4:6] * (b[[7, 9]] - b[[6, 8]]) + b[[6, 8]]
    assert not np.ndarray((q.n,), '>u2', raw, off + 6, (24,)).any()
    vecs = [unpack_vec(np.ndarray((q.n,), '>u4', raw, off + o, (24,)).astype(np.uint64)) for o in (12, 16, 20)]
    lo = seg_off(vb[q.li] + 20); light = np.frombuffer(raw, np.uint8, q.n * 20, lo).reshape(q.n, 20)
    io = seg_off(ib[q.ii] + 16); length = r.unpack('I', ib[q.ii] + 4)[0]; idx = np.frombuffer(raw, '>u2', length // 2, io).astype(np.int64)
    return xyz, uv, vecs, light, idx


def groups_of(tris, centroids, g):
    if g <= 1 or len(tris) <= 1: return [tris]
    pts = centroids[tris]; axis = int(np.argmax(pts.max(0) - pts.min(0))); order = tris[np.argsort(pts[:, axis], kind='stable')]
    gl = g // 2; nl = max(1, min(len(order) - 1, round(len(order) * gl / g)))
    return groups_of(order[:nl], centroids, gl) + groups_of(order[nl:], centroids, g - gl)


def terminal(key):
    if key < 32: return bytes([0x30 + key])
    if key < 256: return bytes([0x50, key])
    assert key < 65536
    return bytes([0x51, key >> 8, key & 255])


def emit(items):
    if len(items) == 1:
        key, lo, hi = items[0]; out = b''
        for ax in (2, 1, 0): out += bytes([0x26 + ax, lo[ax], hi[ax]])
        return out + terminal(key)
    centers = np.array([[(l + h) / 2 for l, h in zip(lo, hi)] for _, lo, hi in items]); ax = int(np.argmax(centers.max(0) - centers.min(0)))
    order = sorted(range(len(items)), key=lambda i: (centers[i][ax], i)); mid = len(order) // 2
    left = [items[i] for i in order[:mid]]; right = [items[i] for i in order[mid:]]; L = emit(left); R = emit(right)
    left_max = max(h[ax] for _, _, h in left); right_min = min(l[ax] for _, l, _ in right)
    if len(L) <= 255: return bytes([0x10 + ax, left_max, right_min, len(L)]) + L + R
    assert len(L) <= 65535, 'MOPP branch too far'
    return bytes([0x23 + ax, left_max, right_min, 0, 0, len(L) >> 8, len(L) & 255]) + L + R


def mopp_code(items):
    lo = [min(i[1][k] for i in items) for k in range(3)]; hi = [max(i[2][k] for i in items) for k in range(3)]
    code = b''.join(bytes([0x26 + ax, lo[ax], hi[ax]]) for ax in (2, 1, 0)) + emit(items)
    found = {}
    for key, l, h, resc, exo in walk(code, False):
        assert not resc and not exo; found.setdefault(key, []).append((l, h))
    for key, l, h in items: assert any(all(x[k] <= l[k] and y[k] >= h[k] for k in range(3)) for x, y in found.get(key, [])), key
    assert set(found) == {i[0] for i in items}
    return code


new_page = bytearray(); meta = []  # (file offset, bytes) writes into tag memory
allocs = []                            # (target, count, payload) blocks needing new tag memory
emptied = set(); rows = []; added = [0]; replaced_vb = set(); replaced_ib = set(); stub_vb = set(); stub_ib = set()


def append(data):
    new_page.extend(bytes((-len(new_page)) % 16)); at = len(new_page); new_page.extend(data); added[0] += len(data); return at


for g in groups:
    host = g[0]; Rh = host.R; ph = host.pos; sh = host.scale
    X = []; UV = []; V = [[], [], []]; L = []; tri_by_key = collections.OrderedDict(); base = 0
    for q in g:
        xyz, uv, vecs, light, idx = geometry(q)
        world = q.pos + q.scale * (xyz @ q.R); X.append(((world - ph) @ Rh.T) / sh)
        rel = q.R @ Rh.T
        for k in range(3): V[k].append(vecs[k] @ rel)
        UV.append(uv - np.floor(uv.min(0))); L.append(light)
        for (mat, sort, start, count, fs, ns, typ, flg, vc) in q.parts:
            t = idx[start:start + count].reshape(-1, 3); assert t.max() < q.n
            tri_by_key.setdefault((mat, sort, typ, flg), []).append(t + base)
        base += q.n
    X = np.concatenate(X); UV = np.concatenate(UV); V = [np.concatenate(x) for x in V]; L = np.concatenate(L); n = len(X); assert n == base <= 65535
    lo3 = X.min(0) - 1e-4; hi3 = X.max(0) + 1e-4; ulo = UV.min(0) - 1e-5; uhi = UV.max(0) + 1e-5
    out = np.zeros((n, 24), dtype=np.uint8); view = out.view('>u2').reshape(n, 12)
    view[:, 0:3] = np.rint((X - lo3) / (hi3 - lo3) * 65535).astype(np.int64); view[:, 4:6] = np.rint((UV - ulo) / (uhi - ulo) * 65535).astype(np.int64)
    v4 = out.view('>u4').reshape(n, 6)
    for k in range(3): v4[:, 3 + k] = pack_vec(V[k])
    Xq = view[:, 0:3].astype(np.float64) / 65535 * (hi3 - lo3) + lo3  # positions as the game will decode them
    moff = lo3 - 0.05; mscale = 254 * 65536 / (float((hi3 - lo3).max()) + 0.1)

    def box(pts):
        qv = (pts - moff) * mscale / 65536.0
        return [int(max(0, min(255, math.floor(v) - 1))) for v in qv.min(0)], [int(max(0, min(255, math.ceil(v) + 1))) for v in qv.max(0)]

    indices = []; parts = []; subparts = []; sub_items = []; part_items = []
    for (mat, sort, typ, flg), tl in tri_by_key.items():
        tris = np.concatenate(tl); cent = Xq[tris].mean(1); first = len(subparts); start = len(indices)
        for grp in groups_of(np.arange(len(tris)), cent, max(1, math.ceil(len(tris) / a.subpart_tris))):
            ids = tris[grp].reshape(-1); l, h = box(Xq[ids]); sub_items.append((len(subparts), l, h))
            subparts.append((len(indices), len(ids), 0, len(np.unique(ids)))); indices.extend(ids.tolist())
        ids = tris.reshape(-1); l, h = box(Xq[ids]); part_items.append((len(parts), l, h))
        parts.append((mat, sort, start, len(ids), first, len(subparts) - first, typ, flg, len(np.unique(ids))))
    assert len(indices) <= a.max_indices and len(subparts) < 32768 and all(x[2] < 65536 and x[3] < 65536 for x in parts)
    # culling trees: copy the host's two object headers, replace offset, scale, size and code
    size0 = c.u(mopps[host.mi]); mat0 = c.pointer(c.u(mopps[host.mi] + 0xC)); blob0 = bytes(c.data[mat0:mat0 + size0]); objs = mopp_objects(blob0)
    assert len(objs) == 2
    blob = b''
    for (_, _, _, code_at, _), items in zip(objs, (sub_items, part_items)):
        code = mopp_code(items); hdr = bytearray(blob0[code_at - 0x30:code_at])
        struct.pack_into('>4f', hdr, 0x10, *moff, mscale); struct.pack_into('>II', hdr, 0x24, len(code), len(code) | 0x80000000)
        blob += bytes(hdr) + code + bytes((-len(code)) % 16)
    vat = append(out.tobytes()); lat_ = append(L.tobytes()); iat = append(np.array(indices, dtype='>u2').tobytes())
    for desc, stride, where in ((vb[host.vi], 24, vat), (vb[host.li], 20, lat_)):
        assert r.unpack('I', desc + 8)[0] == r.unpack('I', desc)[0] * stride
        meta.append((r_ctl + desc, struct.pack('>I', n))); meta.append((r_ctl + desc + 8, struct.pack('>I', n * stride)))
        meta.append((fix_at[desc + 20] + 4, struct.pack('>I', 0x40000000 | where)))
    meta.append((r_ctl + ib[host.ii] + 4, struct.pack('>I', len(indices) * 2))); meta.append((fix_at[ib[host.ii] + 16] + 4, struct.pack('>I', 0x40000000 | iat)))
    pdata = b''.join(struct.pack('>hhHHhhbBH', *x) for x in parts); sdata = b''.join(struct.pack('>HHhH', *x) for x in subparts)
    for m in (meshes[host.mi], lmeshes[host.mi]):
        allocs.append((m, len(parts), pdata)); allocs.append((m + 12, len(subparts), sdata))
    for mp in (mopps[host.mi], lmopps[host.mi]): allocs.append((('mopp', mp), len(blob), blob))
    comp = struct.pack('>10f', lo3[0], hi3[0], lo3[1], hi3[1], lo3[2], hi3[2], ulo[0], uhi[0], ulo[1], uhi[1])
    for cp_ in (comps[host.d], lcomps[host.d]): meta.append((cp_ + 4, comp))
    cen = (X.min(0) + X.max(0)) / 2; rad = float(np.linalg.norm(X - cen, axis=1).max()) * 1.001
    meta.append((cr_ctl + dbase + host.d * 184 + 4, struct.pack('>4f', *cen, rad)))
    wc = ph + sh * (cen @ Rh); meta.append((host.at + 0x40, struct.pack('>4f', *wc, rad * sh)))
    for q in g[1:]: emptied.add(q.mi); stub_vb.add(q.li)
    replaced_vb.update((host.vi, host.li)); replaced_ib.add(host.ii)
    rows.append(dict(host_piece=host.i, members=len(g), vertices=n, triangles=len(indices) // 3, parts_before=sum(len(q.parts) for q in g), parts_after=len(parts), radius=rad * sh))
for mi in emptied:
    for m in (meshes[mi], lmeshes[mi]): meta.append((m, struct.pack('>I', 0)))
    stub_vb.add(c.unpack('h', meshes[mi] + 24)[0]); stub_ib.add(c.unpack('h', meshes[mi] + 40)[0])
assert not (stub_vb & replaced_vb) and not (stub_ib & replaced_ib)
stub = append(bytes(64)); kept_bytes = 0
for i, desc in enumerate(vb):
    if i in replaced_vb: continue
    count, fmt, stride, size = r.unpack('IHHI', desc); assert size == count * stride
    if i in stub_vb:
        meta.append((r_ctl + desc, struct.pack('>I', 1))); meta.append((r_ctl + desc + 8, struct.pack('>I', stride))); where = stub
    else:
        o = seg_off(desc + 20); assert o is not None; where = append(raw[o:o + size]); kept_bytes += size
    meta.append((fix_at[desc + 20] + 4, struct.pack('>I', 0x40000000 | where)))
for i, desc in enumerate(ib):
    if i in replaced_ib: continue
    length = r.unpack('I', desc + 4)[0]
    if i in stub_ib:
        meta.append((r_ctl + desc + 4, struct.pack('>I', 6))); where = stub
    else:
        o = seg_off(desc + 16); assert o is not None; where = append(raw[o:o + length]); kept_bytes += length
    meta.append((fix_at[desc + 16] + 4, struct.pack('>I', 0x40000000 | where)))
parts_before = sum(len(q.parts) for q in pieces if hasattr(q, 'parts'))
parts_after = parts_before - sum(x['parts_before'] - x['parts_after'] for x in rows)
report = dict(source=str(a.source), cell=a.cell, pieces=len(inst), eligible=sum(q.ok for q in pieces), groups=len(groups), pieces_merged=sum(x['members'] for x in rows),
              placed_parts_before=parts_before, placed_parts_after=parts_after, geometry_bytes_added=added[0], page_before=len(raw), page_after=len(new_page), rows=rows)
if a.out:
    from map_builder import MapBuilder
    from build_scenario_checkpoint import resource_salt
    assert not a.out.exists(), 'refusing to overwrite'
    need = sum(len(x[2]) + 32 for x in allocs); reserve = (need + 0xffff) & ~0xffff
    b = MapBuilder(a.source, reserve); salt = resource_salt(a.xex)

    def va(fo): return fo - c.start + c.base

    for fo, data in meta: b.put(va(fo), str(len(data)) + 's', data)
    for where, count, payload in allocs:
        addr = b.alloc(payload)
        if isinstance(where, tuple): b.put(va(where[1]), 'I', count); b.put(va(where[1]) + 0xC, 'I', addr)
        else: b.put(va(where), 'II', count, addr)
    location = c.block(play + 48, 16)[c.unpack('h', r_rec + 34)[0]]; page = c.block(play + 24, 88)[c.unpack('2h', location)[0]]
    assert c.unpack('2I', location + 4)[0] == 0 and c.unpack('h', page + 4)[0] == -1 and c.u(page + 16) == len(raw)
    data = bytes(new_page); compressed = zlib.compress(data, 6)[2:-4]; address = va(page)
    b.put(address + 3, 'B', 0); b.put(address + 8, '4I', b.append_raw(compressed), len(compressed), len(data), zlib.crc32(data) ^ 0xffffffff)
    hashes = b''.join(hashlib.sha1(salt + bytes(x)).digest() for x in (data, data[:1024], data[-1024:])); b.put(address + 24, str(len(hashes)) + 's', hashes)
    a.out.write_bytes(b.finish(salt)); b.close(); report.update(candidate=str(a.out), tag_memory_added=reserve)
a.report.write_text(json.dumps(report, indent=1)); print(json.dumps({k: v for k, v in report.items() if k != 'rows'}))
c.close()
