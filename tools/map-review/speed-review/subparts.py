import sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
for path in sys.argv[1:]:
    c = Cache(path)
    sb = [t['offset'] for t in c.tags.values() if t['group'] == 'sbsp']
    if len(sb) != 1: c.close(); continue
    bsp = sb[0]
    meshes = c.block(bsp + 0x2e4, 76); mopps = c.block(bsp + 0x320, 0x20); vis = c.block(bsp + 0x338, 0xC)
    clm = {c.unpack('h', cl + 0x9C)[0] for cl in c.block(bsp + 0xB4, 0xDC)}
    st = collections.Counter(); flags = collections.Counter(); tri_per_sub = []
    for mi, m in enumerate(meshes):
        if mi in clm: continue
        parts = c.block(m, 16); subs = c.block(m + 12, 8)
        if not parts: continue
        mopp_n = c.u(mopps[mi]) if mi < len(mopps) else -1
        tris = sum(c.unpack('H', p + 6)[0] // 3 for p in parts)
        one = all(c.unpack('H', p + 10)[0] <= 1 for p in parts)
        st[('1 subpart/part' if one else 'multi', 'mopp' if mopp_n > 0 else 'no mopp')] += 1
        st[('tris', 'one' if one else 'multi', 'mopp' if mopp_n > 0 else 'no mopp')] += tris
        flags[c.data[m + 0x2C]] += 1; st[('vis spheres', len(c.block(vis[mi], 0x30)) > 0 if mi < len(vis) else None)] += 1; st[('reorder', len(c.block(mopps[mi] + 0x14, 2)) == len(subs) if mi < len(mopps) else None)] += 1
        if subs: tri_per_sub.append(tris / len(subs))
    tri_per_sub.sort()
    print(Path(path).name, 'instance meshes:', {k: v for k, v in st.items()}, 'flags', dict(flags), 'mopp entries', len(mopps), 'vis entries', len(vis), 'median tris/subpart', round(tri_per_sub[len(tri_per_sub)//2], 1) if tri_per_sub else None)
    c.close()
