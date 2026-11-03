"""Numerical supplement only: remove source-surface perspective before comparing pixels."""
from pathlib import Path
import json,struct
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
w=Path('work/powerhouse');run=Path('.local/loading-traces/20261103-114046-30584')
a=json.loads((w/'window-rays-before-143.json').read_text());b=json.loads((w/'window-rays-after-145.json').read_text())
images=[np.asarray(Image.open(p).convert('RGB'),dtype=float) for p in (run/'proof-loaded_128137ms.png',Path('.local/loading-traces/20261103-114715-14444/proof-loaded.png'))]
def camera(r):
 c=r['camera'];raw=bytes.fromhex(c['observer_bytes']);f=np.array(c['forward']);u=np.array(struct.unpack_from('>3f',raw,52));return np.array(c['position']),f,u,np.cross(f,u),576/np.tan(struct.unpack_from('>f',raw,64)[0]/2)
o,f,u,right,focal=camera(a);oo,ff,uu,rr,ffocal=camera(b)
ma=np.array(json.loads((w/'gpu-projection-143.json').read_text())['matrix']);mb=np.array(json.loads((w/'gpu-projection-145.json').read_text())['matrix'])
reports=[];seen=set()
for key,hits in a['probes'].items():
 hit=hits[0]
 if not hit['material'].endswith('windowbox_subfloor_a'):continue
 signature=json.dumps(hit['triangle'])
 if signature in seen:continue
 seen.add(signature)
 tri=np.array(hit['triangle']);normal=np.cross(tri[1]-tri[0],tri[2]-tri[0]);normal/=np.linalg.norm(normal)
 yy,xx=np.mgrid[200:440,250:850];px=xx.ravel();py=yy.ravel()
 rowx=ma[0]-((px-576)/576)[:,None]*ma[3];rowy=ma[1]-((320-py)/320)[:,None]*ma[3]
 equations=np.stack([rowx[:,:3],rowy[:,:3],np.broadcast_to(normal,(len(px),3))],axis=1)
 rhs=np.stack([-rowx[:,3],-rowy[:,3],np.full(len(px),tri[0]@normal)],axis=1)
 world=np.linalg.solve(equations,rhs[...,None])[...,0];depth=(world-o)@f
 basis=np.stack([tri[1]-tri[0],tri[2]-tri[0]],axis=1);uv=(np.linalg.pinv(basis)@(world-tri[0]).T).T
 mask=(uv[:,0]>.035)&(uv[:,1]>.035)&(uv.sum(axis=1)<.965)&(depth>0)
 clip=np.column_stack([world,np.ones(len(world))])@mb.T;qx=576+576*clip[:,0]/clip[:,3];qy=320-320*clip[:,1]/clip[:,3]
 mask&=(qx>5)&(qx<1146)&(qy>5)&(qy<634)
 px=px[mask];py=py[mask];qx=qx[mask];qy=qy[mask]
 if len(px)<100:continue
 ref=images[0][py,px];search=[]
 for dy in np.arange(-3,3.01,.25):
  for dx in np.arange(-3,3.01,.25):
   sampled=np.stack([map_coordinates(images[1][:,:,c],[qy+dy,qx+dx],order=1,prefilter=False) for c in range(3)],axis=1)
   # Remove one global additive brightness difference; never warp/rewrite saved captures.
   residual=sampled-ref;residual-=np.median(residual,axis=0)
   search.append(dict(dx=float(dx),dy=float(dy),mae=float(np.mean(abs(residual)))))
 baseline=next(x for x in search if x['dx']==x['dy']==0);best=min(search,key=lambda x:x['mae'])
 reports.append(dict(probe=key,triangle=hit['triangle'],pixels=len(px),source_roi=[250,200,850,440],baseline=baseline,best=best,improvement=baseline['mae']-best['mae']))
out=dict(scope='Supplementary surface-registered photometric comparison. Residual shifts can also reflect rasterization, lighting, camera timing or interpolation; these numbers alone do not prove parallax.',reports=reports)
(w/'window-gpu-registration-145.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
