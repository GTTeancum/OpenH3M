"""Read-only: meshes whose every placement name matches a pattern; prints mesh ids, sizes and one placement position each."""
import sys, re, collections, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
from string_ids import StringTable
c = Cache(sys.argv[1]); pat = re.compile(sys.argv[2]); strings = StringTable(c)
bsp = next(t['offset'] for t in c.tags.values() if t['group'] == 'sbsp')
cr = Resource(c, c.u(bsp + 0x37c)); definitions = cr.ptr(cr.root + 16); def_mesh = {}
for i in range(cr.unpack('I', cr.root + 12)[0]): def_mesh[i] = cr.unpack('2H', definitions + i * 184 + 0xb0)[0]
meshes = c.block(bsp + 0x2e4, 76)
info = collections.defaultdict(lambda: dict(names=set(), n=0, pos=None, rad=0))
for at in c.block(bsp + 0x1B0, 0x78):
    di = c.unpack('h', at + 0x34)[0]
    if di not in def_mesh: continue
    try: name = strings.text(c.u(at + 0x54)) or '?'
    except Exception: name = '?'
    d = info[def_mesh[di]]; d['names'].add(name); d['n'] += 1; d['pos'] = c.unpack('3f', at + 0x40); d['rad'] = c.unpack('f', at + 0x4C)[0]
out = []; tot = 0
for mi, d in sorted(info.items()):
    if not all(pat.search(x) for x in d['names']): continue
    m = meshes[mi]; parts = c.block(m, 16); tris = sum(c.unpack('H', p + 6)[0] // 3 for p in parts)
    out.append(dict(mesh=mi, tris=tris, placed=d['n'], parts=len(parts), subparts=len(c.block(m + 12, 8)), pos=[round(x, 2) for x in d['pos']], radius=round(d['rad'], 2), name=sorted(d['names'])[0]))
    tot += tris * d['n']
for o in sorted(out, key=lambda x: -x['tris'] * x['placed']): print(o)
print('meshes', len(out), 'placed triangles', tot)
print('IDS', ','.join(str(o['mesh']) for o in out))
c.close()
