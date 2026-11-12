"""Independently bound every metadata/resource edit in the simplified map."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
work=ROOT/'work/map-review-20261105'
a=Cache(work/'powerhouse-cache-order.map');b=Cache(work/'powerhouse-simplified.map')
assert a.base==b.base and a.u(0x490)==b.u(0x490)
allowed=np.zeros(a.u(0x490),dtype=bool)
def permit(at,n):allowed[at-a.start:at-a.start+n]=True
sc=next(t['offset'] for t in a.tags.values() if t['group']=='scnr')
lm=a.tags[a.u(sc+0x6fc)&65535]['offset'];lb=a.block(lm+4,436)[0]
bsp=next(t['offset'] for t in a.tags.values() if t['group']=='sbsp')
datum=a.u(lb+0x1ac);ra=Resource(a,datum);rb=Resource(b,datum)
assert ra.data==rb.data and ra.fix==rb.fix
raw_allowed=[np.zeros(len(x),dtype=bool) for x in ra.raw]
ib=ra.buffers('index');changed=0;triangles_before=triangles_after=0
for mesh,light in zip(a.block(bsp+0x2e4,76),a.block(lb+0x134,76)):
    parts=a.block(mesh,16);lights=a.block(light,16)
    for p,lp in zip(parts,lights):
        q=p-a.start+b.start
        start,count=a.unpack('2H',p+4);new_count=b.unpack('H',q+6)[0]
        triangles_before+=count//3;triangles_after+=new_count//3
        if count==new_count:continue
        changed+=1
        assert a.data[p+12] in (1,2,3) and 0<new_count<count
        assert a.data[p+13]&8==0, 'Water part changed'
        permit(p+6,2);permit(lp+6,2)
        first,num=a.unpack('2H',p+8)
        for m in (mesh,light):
            for sub in a.block(m+12,8)[first:first+num]:permit(sub,4)
        index=a.unpack('h',mesh+40)[0];ptr=ra.fix[ib[index]+16]
        seg={0x40000000:0,0x60000000:1}[ptr&0xe0000000];offset=(ptr&0x1fffffff)+start*2
        raw_allowed[seg][offset:offset+count*2]=True
play=next(t['offset'] for t in a.tags.values() if t['group']=='play')
for page in a.block(play+24,88):
    q=page-a.start+b.start
    if a.data[page:page+88]!=b.data[q:q+88]:
        permit(page+3,1);permit(page+8,16);permit(page+24,60)
ma=np.frombuffer(a.data,dtype=np.uint8,count=len(allowed),offset=a.start)
mb=np.frombuffer(b.data,dtype=np.uint8,count=len(allowed),offset=b.start)
assert not np.any((ma!=mb)&~allowed), 'Unapproved metadata edit'
for i,(x,y) in enumerate(zip(ra.raw,rb.raw)):
    assert len(x)==len(y)
    assert not np.any((np.frombuffer(x,dtype=np.uint8)!=np.frombuffer(y,dtype=np.uint8))&~raw_allowed[i]), 'Non-index payload changed'
collision=a.u(bsp+0x37c);ca=Resource(a,collision);cb=Resource(b,collision)
assert ca.data==cb.data and ca.fix==cb.fix and ca.raw==cb.raw
report=dict(candidate_sha256=hashlib.sha256((work/'powerhouse-simplified.map').read_bytes()).hexdigest(),
    triangles_before=triangles_before,triangles_after=triangles_after,changed_parts=changed,
    collision_resource_identical=True,all_other_metadata_identical_except_index_ranges_and_geometry_page_descriptors=True,
    geometry_payload_identical_except_reduced_opaque_index_ranges=True,
    scope='Preserves lights, exposure, materials, placements, culling trees, collision and all vertex attributes; reduced topology changes interpolation and still needs visual review.')
(work/'powerhouse-reduction-preservation.json').write_text(json.dumps(report,indent=2))
del ma,mb
a.close();b.close();print(json.dumps(report,indent=2))
