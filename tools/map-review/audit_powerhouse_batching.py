"""Read-only inventory of material batch redundancy, preserving mesh boundaries."""
import collections,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
c=Cache(ROOT/'work/map-review-20261105/powerhouse-cache-order.map')
bsp=next(t['offset'] for t in c.tags.values() if t['group']=='sbsp')
rows=[]
for mi,m in enumerate(c.block(bsp+0x2e4,76)):
    parts=[c.unpack('hhHHhHBBH',p) for p in c.block(m,16)]
    groups=collections.Counter((p[0],p[1],p[6],p[7]) for p in parts if p[6] in (1,2,3) and p[3])
    duplicates=sum(n-1 for n in groups.values())
    adjacent=sum(a[6] in (1,2,3) and a[3]>0 and b[3]>0 and
        (a[0],a[1],a[6],a[7])==(b[0],b[1],b[6],b[7]) and a[2]+a[3]==b[2]
        for a,b in zip(parts,parts[1:]))
    rows.append(dict(mesh=mi,parts=len(parts),subparts=c.u(m+12),duplicate_opaque_batches=duplicates,
        adjacent_compatible_batches=adjacent))
report=dict(scope='Static within-mesh inventory only. No culling, vertex streams, lightmaps, collision, or map bytes changed; compatible material labels alone do not prove merge safety.',
    meshes=len(rows),parts=sum(x['parts'] for x in rows),subparts=sum(x['subparts'] for x in rows),
    duplicate_opaque_batches=sum(x['duplicate_opaque_batches'] for x in rows),
    adjacent_compatible_batches=sum(x['adjacent_compatible_batches'] for x in rows),rows=rows)
(ROOT/'work/map-review-20261105/powerhouse-batching-audit.json').write_text(json.dumps(report,indent=2))
c.close()
print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
