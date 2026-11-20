"""Independent check of a reduce2.py candidate against its source map.

Proves: tag data differs only in part triangle counts, subpart ranges, subpart MOPP code bytes
and geometry page descriptors; geometry payload differs only inside index ranges of changed
opaque parts; collision resource identical; every drawn triangle uses original vertices and was
checked to lie inside a region its regenerated culling tree reports; both tree copies match.
"""
import hashlib, json, math, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
sys.path.insert(0, str(Path(__file__).parent))
from cache_reader import Cache
from resource_reader import Resource
from mopp_validate import walk, mopp_objects

src, cand, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
a = Cache(src); b = Cache(cand)
assert a.base == b.base and a.u(0x490) == b.u(0x490)
size = a.u(0x490); allowed = np.zeros(size, dtype=bool)
def permit(at, n): allowed[at - a.start:at - a.start + n] = True
def tb(at): return at - a.start + b.start
sc = next(t['offset'] for t in a.tags.values() if t['group'] == 'scnr')
lm = a.tags[a.u(sc + 0x6fc) & 65535]['offset']; lb = a.block(lm + 4, 436)[0]
bsp = next(t['offset'] for t in a.tags.values() if t['group'] == 'sbsp')
datum = a.u(lb + 0x1ac); ra = Resource(a, datum); rb = Resource(b, datum)
assert ra.data == rb.data and ra.fix == rb.fix
cr = Resource(a, a.u(bsp + 0x37c)); definitions = cr.ptr(cr.root + 16); comp_of = {}
for i in range(cr.unpack('I', cr.root + 12)[0]):
    mesh, comp = cr.unpack('2H', definitions + i * 184 + 0xb0); comp_of[mesh] = comp
compressions = a.block(bsp + 0x2f0, 44)
raw_allowed = [np.zeros(len(x), dtype=bool) for x in ra.raw]
vb, ib = ra.buffers('vertex'), ra.buffers('index')
meshes = a.block(bsp + 0x2e4, 76); lmeshes = a.block(lb + 0x134, 76); mopps = a.block(bsp + 0x320, 0x20); lmopps = a.block(lb + 0x170, 0x20)
changed_meshes = changed_parts = before = after = checked_subparts = 0
for mi, (m, l) in enumerate(zip(meshes, lmeshes)):
    parts = a.block(m, 16); lparts = a.block(l, 16); subs = a.block(m + 12, 8); lsubs = a.block(l + 12, 8)
    mesh_changed = False
    for p_, lp in zip(parts, lparts):
        start, count, first, num = a.unpack('4H', p_ + 4); new_count = b.unpack('H', tb(p_) + 6)[0]
        assert b.unpack('H', tb(lp) + 6)[0] == new_count
        before += count // 3; after += new_count // 3
        if new_count == count: continue
        mesh_changed = True; changed_parts += 1
        assert a.data[p_ + 12] in (1, 2, 3) and not a.data[p_ + 13] & 8 and 0 < new_count < count and new_count % 3 == 0
        permit(p_ + 6, 2); permit(lp + 6, 2)
        pos = start
        for si in range(first, first + num):
            permit(subs[si], 4); permit(lsubs[si], 4)
            s0, sz = b.unpack('2H', tb(subs[si])); assert b.unpack('2H', tb(lsubs[si])) == (s0, sz)
            assert s0 == pos and sz % 3 == 0; pos += sz
        assert pos == start + new_count
        index = a.unpack('h', m + 40)[0]; ptr = ra.fix[ib[index] + 16]
        seg = {0x40000000: 0, 0x60000000: 1}[ptr & 0xe0000000]; off = (ptr & 0x1fffffff) + start * 2
        raw_allowed[seg][off:off + count * 2] = True
    if not mesh_changed: continue
    changed_meshes += 1
    # culling tree: only the subpart tree's code bytes may differ, in both copies, identically
    msize = a.u(mopps[mi]); mat = a.pointer(a.u(mopps[mi] + 0xC)); lat = a.pointer(a.u(lmopps[mi] + 0xC))
    blob_a = bytes(a.data[mat:mat + msize]); blob_b = bytes(b.data[tb(mat):tb(mat) + msize])
    assert bytes(b.data[tb(lat):tb(lat) + msize]) == blob_b
    oa = mopp_objects(blob_a); ob = mopp_objects(blob_b); assert len(oa) == len(ob) == 2
    assert oa[1] == ob[1] and oa[0][:2] == ob[0][:2] and oa[0][3:] == ob[0][3:]
    permit(mat + oa[0][3], oa[0][4]); permit(lat + oa[0][3], oa[0][4])
    # geometry check in the candidate
    vi, ii = a.unpack('h', m + 24)[0], a.unpack('h', m + 40)[0]
    n, fmt, stride = ra.unpack('IHH', vb[vi]); assert (fmt, stride) == (2, 24)
    ptr = ra.fix[vb[vi] + 20]; raw = rb.raw[{0x40000000: 0, 0x60000000: 1}[ptr & 0xe0000000]]; voff = ptr & 0x1fffffff
    bounds = np.array(a.unpack('6f', compressions[comp_of[mi]] + 4)).reshape(3, 2)
    xyz = np.ndarray((n, 3), '>u2', raw, voff, (stride, 2)) / 65535 * (bounds[:, 1] - bounds[:, 0]) + bounds[:, 0]
    ptr = ra.fix[ib[ii] + 16]; iraw = rb.raw[{0x40000000: 0, 0x60000000: 1}[ptr & 0xe0000000]]; ioff = ptr & 0x1fffffff
    indices = np.frombuffer(iraw, '>u2', ra.unpack('I', ib[ii] + 4)[0] // 2, ioff)
    if blob_a == blob_b:
        # Tree untouched: every group must draw only vertices its original group already used.
        iraw_a = ra.raw[{0x40000000: 0, 0x60000000: 1}[ptr & 0xe0000000]]
        ind_a = np.frombuffer(iraw_a, '>u2', ra.unpack('I', ib[ii] + 4)[0] // 2, ioff)
        for si, s_ in enumerate(subs):
            a0, asz = a.unpack('2H', s_); s0, sz = b.unpack('2H', tb(s_))
            if not sz: continue
            assert set(indices[s0:s0 + sz].tolist()) <= set(ind_a[a0:a0 + asz].tolist()), (mi, si)
            checked_subparts += 1
        unchanged_trees = globals().get('unchanged_trees', 0) + 1
        continue
    (moff, mscale, code, _, _) = ob[0]
    regions = {}
    for key, lo, hi, resc, exo in walk(code, False):
        assert not resc and not exo
        regions.setdefault(key, []).append((lo, hi))
    live = set()
    for si, s in enumerate(subs):
        s0, sz = b.unpack('2H', tb(s))
        if not sz: continue
        live.add(si); sel = indices[s0:s0 + sz]; assert sel.max() < n
        q = (xyz[sel] - np.array(moff)) * mscale / 65536.0
        lo, hi = q.min(0), q.max(0)
        assert any(all(r_lo[k] <= lo[k] and r_hi[k] >= hi[k] for k in range(3)) for r_lo, r_hi in regions.get(si, [])), (mi, si)
        checked_subparts += 1
    assert set(regions) == live, (mi, sorted(set(regions) ^ live)[:5])
play = next(t['offset'] for t in a.tags.values() if t['group'] == 'play')
for page in a.block(play + 24, 88):
    if a.data[page:page + 88] != b.data[tb(page):tb(page) + 88]:
        permit(page + 3, 1); permit(page + 8, 16); permit(page + 24, 60)
ma = np.frombuffer(a.data, dtype=np.uint8, count=size, offset=a.start); mb = np.frombuffer(b.data, dtype=np.uint8, count=size, offset=b.start)
bad = int(np.count_nonzero((ma != mb) & ~allowed)); assert bad == 0, f'{bad} unapproved tag bytes changed'
for i, (x, y) in enumerate(zip(ra.raw, rb.raw)):
    assert len(x) == len(y)
    assert not np.any((np.frombuffer(x, dtype=np.uint8) != np.frombuffer(y, dtype=np.uint8)) & ~raw_allowed[i]), 'non-index payload changed'
col = a.u(bsp + 0x37c); ca = Resource(a, col); cb = Resource(b, col)
assert ca.data == cb.data and ca.fix == cb.fix and ca.raw == cb.raw
report = dict(source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(), candidate_sha256=hashlib.sha256(cand.read_bytes()).hexdigest(),
              stored_triangles_before=before, stored_triangles_after=after, changed_meshes=changed_meshes, changed_parts=changed_parts,
              culling_groups_checked=checked_subparts, collision_resource_identical=True,
              tag_data_identical_except_counts_ranges_tree_code_and_page_descriptors=True,
              geometry_payload_identical_except_reduced_index_ranges=True, lightmap_copies_match=True,
              meshes_with_untouched_culling_tree=globals().get('unchanged_trees', 0), candidate_bytes=cand.stat().st_size, source_bytes=src.stat().st_size)
del ma, mb
out.write_text(json.dumps(report, indent=1)); print(json.dumps(report, indent=1)); a.close(); b.close()
