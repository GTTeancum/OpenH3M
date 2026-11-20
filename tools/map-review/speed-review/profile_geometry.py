"""Read-only: where the triangles are, by vertex format / part type / placement count."""
import sys, collections, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
from build_scenario_checkpoint import resource_salt
c = Cache(sys.argv[1])
sc = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
lmtag = c.tags[c.u(sc + 0x6fc) & 65535]; print('lightmap tag group', lmtag['group'])
lbs = c.block(lmtag['offset'] + 4, 436); print('Lbsp blocks', len(lbs))
lb = lbs[0]; datum = c.u(lb + 0x1ac); r = Resource(c, datum)
bsp = next(t['offset'] for t in c.tags.values() if t['group'] == 'sbsp')
meshes = c.block(bsp + 0x2e4, 76); lmeshes = c.block(lb + 0x134, 76)
print('meshes', len(meshes), 'lightmap meshes', len(lmeshes), 'raw segs', [len(x) for x in r.raw])
vb, ib = r.buffers('vertex'), r.buffers('index')
# placement count per mesh
use = collections.Counter(); seen = set()
clmesh = set()
for cl in c.block(bsp + 0xB4, 0xDC):
    mi = c.unpack('h', cl + 0x9C)[0]
    if mi < 0: continue
    clmesh.add(mi); use[mi] += 1
    for b in c.block(meshes[mi] + 0x34, 0x10):
        bm = c.unpack('h', b)[0]
        for i in c.block(b + 4, 2):
            ii = c.unpack('h', i)[0]
            if (ii) not in seen: seen.add(ii); use[bm] += 1
byfmt = collections.Counter(); bytype = collections.Counter(); sub = collections.Counter()
same = 0
for mi, m in enumerate(meshes):
    vi = c.unpack('h', m + 24)[0]; ii = c.unpack('h', m + 40)[0]
    if vi < 0: continue
    n, fmt, stride = r.unpack('IHH', vb[vi])
    itype = c.data[m + 0x30]
    lparts = c.block(lmeshes[mi], 16) if mi < len(lmeshes) else []
    for pi, p in enumerate(c.block(m, 16)):
        start, cnt, first, num = c.unpack('4H', p + 4); pt = c.data[p + 12]
        t = cnt // 3 if itype == 3 else max(cnt - 2, 0)
        kind = 'world' if mi in clmesh else 'instance'
        byfmt[(kind, fmt, stride, itype)] += t * max(use[mi], 1)
        bytype[(kind, pt)] += t * max(use[mi], 1)
        sub[(kind, 'parts')] += 1; sub[(kind, 'subparts')] += num
        if pi < len(lparts) and c.unpack('4H', lparts[pi] + 4) == (start, cnt, first, num): same += 1
print('by (kind, vertex fmt, stride, index type) placement-weighted tris:'); [print('  ', k, v) for k, v in sorted(byfmt.items())]
print('by (kind, part type):'); [print('  ', k, v) for k, v in sorted(bytype.items())]
print(dict(sub), 'lightmap parts matching', same)
print('unused meshes (no placement):', sum(1 for i in range(len(meshes)) if not use[i]))
# salt check
salt = resource_salt(sys.argv[2])
zone = next(t['offset'] for t in c.tags.values() if t['group'] == 'zone'); play = next(t['offset'] for t in c.tags.values() if t['group'] == 'play')
res = c.block(zone + 88, 64)[datum & 65535]; loc = c.block(play + 48, 16)[c.unpack('h', res + 34)[0]]
pages = c.block(play + 24, 88); ids = c.unpack('2h', loc); offs = c.unpack('2I', loc + 4)
for seg, pid in enumerate(ids):
    if pid < 0: continue
    page = pages[pid]
    print('seg', seg, 'page', pid, 'offset', offs[seg], 'shared', c.unpack('h', page + 4)[0], 'size', c.u(page + 16), 'codec', c.data[page + 3])
    if offs[seg] == 0:
        data = r.raw[seg]
        print('   salt hash ok:', hashlib.sha1(salt + data).digest() == c.data[page + 24:page + 44])
