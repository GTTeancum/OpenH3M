import sys, struct
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
c = Cache(sys.argv[1]); want = int(sys.argv[2]); shown = 0
bsp = next(t['offset'] for t in c.tags.values() if t['group'] == 'sbsp')
meshes = c.block(bsp + 0x2e4, 76); mopps = c.block(bsp + 0x320, 0x20)
clm = {c.unpack('h', cl + 0x9C)[0] for cl in c.block(bsp + 0xB4, 0xDC)}
for mi, m in enumerate(meshes):
    parts = c.block(m, 16); subs = c.block(m + 12, 8)
    size = c.u(mopps[mi]); 
    if not size or not parts: continue
    if not (len(subs) <= 6 and len(subs) >= 2 and mi not in clm): continue
    hdr = c.data[mopps[mi]:mopps[mi] + 0x20]
    at = c.pointer(c.u(mopps[mi] + 0xC)); blob = c.data[at:at + size]
    reorder = [c.unpack('h', x)[0] for x in c.block(mopps[mi] + 0x14, 2)]
    print('mesh', mi, 'parts', len(parts), 'subs', len(subs), 'mopp size', size, 'hdr', hdr.hex(), 'reorder', reorder)
    print('  parts', [c.unpack('4H', p + 4) for p in parts]); print('  subs', [c.unpack('2Hh', s) for s in subs])
    print('  blob', blob.hex())
    shown += 1
    if shown >= want: break
