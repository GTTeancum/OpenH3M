"""Read-only static drawing-load audit of native H3 caches: per-zone potential load using the PVS."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache

def audit(path):
    c = Cache(path, False)
    scnr = next(t['offset'] for t in c.tags.values() if t['group'] == 'scnr')
    sb = [t['offset'] for t in c.tags.values() if t['group'] == 'sbsp']
    zones = c.block(scnr + 0x3C, 0x2C)
    if len(sb) != 1 or len(zones) < 1:
        c.close(); return None
    bsp = sb[0]
    spvs = c.block(zones[0] + 0x14, 0x54)
    rows = c.block(spvs[0] + 0, 0xC)
    vis = []
    for r in rows:
        words = [c.u(w) for v in c.block(r, 0xC)[:1] for w in c.block(v, 4)]
        vis.append({i for i in range(len(rows)) if words[i // 32] >> (i % 32) & 1})
    meshes = []
    for m in c.block(bsp + 0x2E4, 0x4C):
        itype = c.data[m + 0x30]
        tri = parts = tparts = ttri = 0
        for p in c.block(m, 0x10):
            n = c.unpack('H', p + 6)[0]
            if not n: continue
            t = n // 3 if itype == 3 else max(n - 2, 0)
            ptype = c.unpack('b', p + 0xC)[0]
            parts += 1; tri += t
            if ptype >= 4 or ptype == 0: tparts += 1; ttri += t
        buckets = [(c.unpack('h', b)[0], [c.unpack('h', i)[0] for i in c.block(b + 4, 2)]) for b in c.block(m + 0x34, 0x10)]
        meshes.append(dict(tri=tri, parts=parts, tparts=tparts, ttri=ttri, buckets=buckets))
    clusters = []
    for cl in c.block(bsp + 0xB4, 0xDC):
        mi = c.unpack('h', cl + 0x9C)[0]
        b = c.unpack('6f', cl)
        clusters.append(dict(mesh=mi, bounds=b, portals=len(c.block(cl + 0x3C, 2))))
    ninst = len(c.block(bsp + 0x1B0, 0x78))
    nportal = len(c.block(bsp + 0x6C, 0x28))
    def own(ci):
        m = meshes[clusters[ci]['mesh']] if clusters[ci]['mesh'] >= 0 else dict(tri=0, parts=0, tparts=0, ttri=0, buckets=[])
        inst = {}
        for mesh, ids in m['buckets']:
            for i in ids: inst[i] = mesh
        return m, inst
    owns = [own(i) for i in range(len(clusters))]
    res = []
    for ci in range(len(clusters)):
        tri = parts = tparts = 0; inst = {}
        for v in vis[ci] if ci < len(vis) else []:
            m, ins = owns[v]
            tri += m['tri']; parts += m['parts']; tparts += m['tparts']; inst.update(ins)
        for i, mesh in inst.items():
            mm = meshes[mesh]; tri += mm['tri']; parts += mm['parts']; tparts += mm['tparts']
        m, ins = owns[ci]
        otri = m['tri'] + sum(meshes[x]['tri'] for x in ins.values())
        oparts = m['parts'] + sum(meshes[x]['parts'] for x in ins.values())
        otp = m['tparts'] + sum(meshes[x]['tparts'] for x in ins.values())
        res.append(dict(cluster=ci, vis=len(vis[ci]), tri=tri, draws=parts, tdraws=tparts, inst=len(inst), own_tri=otri, own_draws=oparts, own_tdraws=otp, own_inst=len(ins), bounds=clusters[ci]['bounds']))
    allinst = {}
    for m, ins in owns: allinst.update(ins)
    total_tri = sum(m['tri'] for m, _ in owns) + sum(meshes[x]['tri'] for x in allinst.values())
    total_draws = sum(m['parts'] for m, _ in owns) + sum(meshes[x]['parts'] for x in allinst.values())
    c.close()
    return dict(name=Path(path).name, clusters=len(clusters), portals=nportal, instances=ninst, placed=len(allinst), total_tri=total_tri, total_draws=total_draws, rows=res)

if __name__ == '__main__':
    out = {}
    print(f'{"map":18s} {"zones":>5s} {"inst":>5s} {"all tris":>9s} {"all draws":>9s} | {"worst tris":>10s} {"worst draws":>11s} {"worst inst":>10s} | {"avg tris":>9s} {"avg draws":>9s}')
    for p in sys.argv[1:]:
        try: a = audit(p)
        except Exception as e:
            print(Path(p).name, 'ERR', repr(e)); continue
        if not a: continue
        out[a['name']] = a
        r = a['rows']; n = len(r)
        print(f'{a["name"]:18s} {n:5d} {a["placed"]:5d} {a["total_tri"]:9d} {a["total_draws"]:9d} | {max(x["tri"] for x in r):10d} {max(x["draws"] for x in r):11d} {max(x["inst"] for x in r):10d} | {sum(x["tri"] for x in r)//n:9d} {sum(x["draws"] for x in r)//n:9d}')
    Path('load-audit.json').write_text(json.dumps(out))
