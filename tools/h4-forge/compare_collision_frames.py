"""Propose, never apply, coordinate registrations from both original collision meshes."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[2];out=ROOT/'work/h4-forge-research/isolated'
h3=json.loads((out/'marker-geometry.json').read_text());h4={x['name']:x for x in json.loads((out/'h4-collision.json').read_text())}
bindings=json.loads((out/'marker-bindings.json').read_text());names={(x['map'],x['label']):x['h4_source'] for x in bindings}
def points(model):
 p=np.array([v for shape in model['shapes'] for v in shape['vertices']],dtype=float)
 if not len(p):raise ValueError('No collision vertices')
 return np.unique(np.round(p,6),axis=0)
result=[]
for entry in h3:
 name=names[entry['map'],entry['label']];a=points(h4[name]);b=points(entry);bt=cKDTree(b)
 candidates=[]
 for quarter in range(4):
  angle=quarter*np.pi/2;c,s=round(np.cos(angle)),round(np.sin(angle));rotation=np.array([[c,-s,0],[s,c,0],[0,0,1]])
  ar=a@rotation.T;t=(b.min(0)+b.max(0)-ar.min(0)-ar.max(0))/2
  for _ in range(16):
   dist,indices=bt.query(ar+t);keep=dist<=np.quantile(dist,.85)
   delta=np.median(b[indices[keep]]-(ar+t)[keep],axis=0);t+=delta
   if np.linalg.norm(delta)<1e-6:break
  transformed=ar+t
  da=bt.query(transformed)[0];db=cKDTree(transformed).query(b)[0]
  score=float((np.mean(da)+np.mean(db))/2)
  candidates.append(dict(z_degrees=quarter*90,translation=t.tolist(),score=score,p95=float(max(np.quantile(da,.95),np.quantile(db,.95)))))
 candidates.sort(key=lambda x:x['score'])
 result.append(dict(map=entry['map'],label=entry['label'],source=name,candidates=candidates,
   status='Candidate registration only; collision reskins can differ and symmetry can be ambiguous.'))
(out/'collision-frame-candidates.json').write_text(json.dumps(result,indent=2)+'\n')
for r in result:
 if r['map']=='forge_gulch.map':
  b=r['candidates'][0];print(r['label'],b['z_degrees'],[round(v,4) for v in b['translation']],round(b['score'],4),'next',round(r['candidates'][1]['score'],4))
