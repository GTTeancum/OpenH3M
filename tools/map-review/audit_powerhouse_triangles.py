"""Inspect native Powerhouse triangle lists without changing geometry."""
import sys,collections,json,struct
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
c=Cache(root/'work/powerhouse/zanzibar-139.map');sc=next(t['offset'] for t in c.tags.values() if t['group']=='scnr');lm=c.tags[c.u(sc+0x6fc)&65535]['offset'];lb=c.block(lm+4,436)[0];r=Resource(c,c.u(lb+0x1ac));bsp=next(t['offset'] for t in c.tags.values() if t['group']=='sbsp');ibs=r.buffers('index');rows=[]
for mi,m in enumerate(c.block(bsp+0x2e4,76)):
 ib=c.unpack('h',m+0x28)[0]
 if ib<0:continue
 assert c.unpack('B',m+0x30)[0]==3
 b=ibs[ib];n=r.unpack('I',b+4)[0];ptr=r.fix[b+16];raw=r.raw[{0x40000000:0,0x60000000:1}[ptr&0xe0000000]];off=ptr&0x1fffffff;indices=struct.unpack_from('>'+str(n//2)+'H',raw,off)
 for pi,p in enumerate(c.block(m,16)):
  start,count=c.unpack('2H',p+4);assert count%3==0 and start+count<=len(indices)
  triangles=list(zip(indices[start:start+count:3],indices[start+1:start+count:3],indices[start+2:start+count:3]));seen=set();dup=deg=0
  for t in triangles:
   deg+=len(set(t))<3
   key=min(t,t[1:]+t[:1],t[2:]+t[:2]);dup+=key in seen;seen.add(key)
  rows.append(dict(mesh=mi,part=pi,triangles=len(triangles),degenerate=deg,duplicate=dup))
report=dict(total_triangles=sum(x['triangles'] for x in rows),degenerate=sum(x['degenerate'] for x in rows),same_winding_duplicate=sum(x['duplicate'] for x in rows),largest_parts=sorted(rows,key=lambda x:x['triangles'],reverse=True)[:20],scope='Index identity only; not spatially equivalent vertices, visibility or per-frame draw cost. No mesh changed.')
(root/'work/map-review-20261105/powerhouse-triangle-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));c.close()
