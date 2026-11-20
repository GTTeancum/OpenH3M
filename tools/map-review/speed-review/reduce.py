"""Opaque rigid placed-piece triangle reduction; original vertices, collision and culling groups retained.

Generalised from tools/map-review/simplify_powerhouse.py. Each culling group (subpart) is
simplified on its own, so its triangles stay inside the bounds its culling tree already has.
"""
import argparse, ctypes as C, hashlib, json, struct, sys, zlib
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('source', type=Path); p.add_argument('--xex', type=Path, required=True)
p.add_argument('--out', type=Path); p.add_argument('--report', type=Path, required=True)
p.add_argument('--error', type=float, default=.01); p.add_argument('--ratio', type=float, default=.5)
p.add_argument('--lock-border', type=int, default=1)
p.add_argument('--keep-order', action='store_true', help='keep the simplifier output order instead of re-optimising for vertex cache')
p.add_argument('--tolerance', type=float, default=0, help='if set: max error in world units (overrides --error per mesh)')
p.add_argument('--min-tris', type=int, default=0, help='only touch meshes with at least this many triangles')
a = p.parse_args()
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
assert len(meshes) == len(light_meshes)
vb, ib = r.buffers('vertex'), r.buffers('index')
lib = C.CDLL(str(ROOT / 'work/speed-review/deps/meshoptimizer.dll'))
U = C.POINTER(C.c_uint); F = C.POINTER(C.c_float)
lib.meshopt_simplifyWithAttributes.argtypes = [U, U, C.c_size_t, F, C.c_size_t, C.c_size_t, F, C.c_size_t, F, C.c_size_t, C.c_void_p, C.c_size_t, C.c_float, C.c_uint, F]
lib.meshopt_simplifyWithAttributes.restype = C.c_size_t
lib.meshopt_optimizeVertexCache.argtypes = [U, U, C.c_size_t, C.c_size_t]
weights = (C.c_float * 5)(.5, .5, .5, 10, 10)
patched = {}; writes = {}; rows = []; seen = set(); total = 0
def payload(at):
    ptr = r.fix[at]; return {0x40000000: 0, 0x60000000: 1}[ptr & 0xe0000000], ptr & 0x1fffffff
def record(at, fmt, values):
    data = struct.pack('>' + fmt, *values)
    assert at not in writes or writes[at] == data
    writes[at] = data
for mi, (m, lmm) in enumerate(zip(meshes, light_meshes)):
    parts = c.block(m, 16); mesh_tris = sum(c.unpack('H', q + 6)[0] // 3 for q in parts); total += mesh_tris
    vi, ii = c.unpack('h', m + 24)[0], c.unpack('h', m + 40)[0]
    if vi < 0 or ii < 0 or mi not in compression_by_mesh or mesh_tris < a.min_tris: continue
    n, fmt, stride = r.unpack('IHH', vb[vi])
    if (fmt, stride) != (2, 24): continue
    assert c.unpack('B', m + 0x30)[0] == 3
    seg, offset = payload(vb[vi] + 20); raw = r.raw[seg]
    bounds = np.array(c.unpack('6f', compressions[compression_by_mesh[mi]] + 4)).reshape(3, 2)
    xyz = np.ascontiguousarray(np.ndarray((n, 3), '>u2', raw, offset, (stride, 2)) / 65535 * (bounds[:, 1] - bounds[:, 0]) + bounds[:, 0], dtype=np.float32)
    packed = np.ndarray((n,), '>u4', raw, offset + 12, (stride,)).astype(np.uint32)
    normals = []
    for shift, bits in ((0, 10), (10, 11), (21, 11)):
        val = ((packed >> shift) & ((1 << bits) - 1)).astype(np.int32)
        val = np.where(val & (1 << (bits - 1)), val - (1 << bits), val)
        normals.append(np.maximum(-1, val / ((1 << (bits - 1)) - 1)))
    uv = np.ndarray((n, 2), '>u2', raw, offset + 8, (stride, 2)) / 65535
    attrs = np.ascontiguousarray(np.column_stack((*normals, uv)), dtype=np.float32)
    mesh_error = min(1.0, a.tolerance / max(float((xyz.max(0) - xyz.min(0)).max()), 1e-9)) if a.tolerance > 0 else a.error
    iseg, ioff = payload(ib[ii] + 16); length = r.unpack('I', ib[ii] + 4)[0]
    indices = np.frombuffer(r.raw[iseg], '>u2', length // 2, ioff)
    lparts = c.block(lmm, 16); subs = c.block(m + 12, 8); lsubs = c.block(lmm + 12, 8)
    assert len(parts) == len(lparts) and len(subs) == len(lsubs)
    for pi, part in enumerate(parts):
        start, count, first, num = c.unpack('4H', part + 4)
        if c.unpack('B', part + 12)[0] not in (1, 2, 3) or count < 30: continue
        if c.data[part + 13] & 8: continue  # water
        assert c.unpack('4H', lparts[pi] + 4) == (start, count, first, num)
        key = (ii, start, count)
        assert key not in seen, 'Shared index ranges require explicit handling'
        seen.add(key); new = []; changes = []; before = 0; worst = 0; ok = True
        for si in range(first, first + num):
            old_start, size = c.unpack('2H', subs[si])
            if old_start != start + before or size % 3 or c.unpack('2H', lsubs[si]) != (old_start, size): ok = False; break
            if not size:
                changes.append((si, start + len(new), 0)); continue
            src = np.ascontiguousarray(indices[old_start:old_start + size], dtype=np.uint32)
            assert max(src, default=0) < n
            dest = np.empty_like(src); error = C.c_float()
            kept = lib.meshopt_simplifyWithAttributes(dest.ctypes.data_as(U), src.ctypes.data_as(U), size,
                xyz.ctypes.data_as(F), n, 12, attrs.ctypes.data_as(F), 20, weights, 5, None,
                int(size * a.ratio) // 3 * 3, mesh_error, a.lock_border, C.byref(error))
            if kept == 0 or kept > size:
                kept = size; dest[:] = src; error.value = 0
            assert kept % 3 == 0
            cache = np.empty(kept, dtype=np.uint32)
            if a.keep_order: cache[:] = dest[:kept]
            else: lib.meshopt_optimizeVertexCache(cache.ctypes.data_as(U), dest.ctypes.data_as(U), kept, n)
            changes.append((si, start + len(new), kept)); new.extend(cache.tolist()); before += size; worst = max(worst, error.value)
        if not ok or before != count or len(new) == count: continue
        data = patched.setdefault(iseg, bytearray(r.raw[iseg]))
        data[ioff + start * 2:ioff + (start + count) * 2] = np.array(new + [0] * (count - len(new)), dtype='>u2').tobytes()
        for at in (part, lparts[pi]): record(at + 6, 'H', (len(new),))
        for si, new_start, kept in changes:
            for at in (subs[si], lsubs[si]): record(at, '2H', (new_start, kept))
        rows.append(dict(mesh=mi, part=pi, before=count // 3, after=len(new) // 3, max_relative_error=worst))
removed = sum(x['before'] - x['after'] for x in rows)
report = dict(source=str(a.source), stored_triangles_before=total, stored_triangles_after=total - removed,
              reduction_percent=removed / total * 100, target_ratio=a.ratio, error_limit=a.error, tolerance_world_units=a.tolerance, lock_border=a.lock_border,
              changed_parts=len(rows), rows=rows)
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
            new_offset = b.append_raw(compressed); report['geometry_page'] = 'appended (%d > %d)' % (len(compressed), old_size)
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
print(json.dumps({k: v for k, v in report.items() if k != 'rows'}))
c.close()
