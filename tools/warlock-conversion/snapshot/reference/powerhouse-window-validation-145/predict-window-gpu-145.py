from pathlib import Path
import json,struct
import numpy as np
w=Path('work/powerhouse');a=json.loads((w/'window-rays-before-143.json').read_text());b=json.loads((w/'window-rays-after-145.json').read_text())
hit=a['probes']['(560, 350)'][0];tri=np.array(hit['triangle']);tex=np.array(hit['uv']);p=np.array(hit['position'])
o=np.array(a['camera']['position']);oo=np.array(b['camera']['position'])
basis=np.stack([tri[1]-tri[0],tri[2]-tri[0]],axis=1);bc=np.linalg.pinv(basis)@(p-tri[0]);weights=np.array([1-bc.sum(),*bc])
t=weights@np.array(hit['tangent']);t/=np.linalg.norm(t);bn=weights@np.array(hit['binormal']);bn/=np.linalg.norm(bn)
world_per_uv=basis@np.linalg.inv(np.stack([tex[1]-tex[0],tex[2]-tex[0]],axis=1))
height=(85/255-.5)*.1
def offset(origin,point):
 v=origin-point;v/=np.linalg.norm(v);return height*np.array([t@v,bn@v])
initial=offset(o,p);q=p.copy()
for _ in range(20):q=p+world_per_uv@(initial-offset(oo,q))
raw=bytes.fromhex(b['camera']['observer_bytes']);f=np.array(b['camera']['forward']);u=np.array(struct.unpack_from('>3f',raw,52));r=np.cross(f,u);focal=576/np.tan(struct.unpack_from('>f',raw,64)[0]/2)
matrix=np.array(json.loads((w/'gpu-projection-145.json').read_text())['matrix'])
def project(point):
 clip=matrix@np.append(point,1);return np.array([576+576*clip[0]/clip[3],320-320*clip[1]/clip[3]])
out=dict(height=height,camera_displacement=float(np.linalg.norm(oo-o)),uv_before=initial.tolist(),uv_after=offset(oo,p).tolist(),predicted_same_feature_pixel_shift=(project(q)-project(p)).tolist(),source_uvs=tex.tolist(),world_per_uv=world_per_uv.tolist(),tangent=t.tolist(),binormal=bn.tolist(),assumptions='Source compressed UV bounds and signed-short tangent/binormal decoded; normalized interpolated tangent basis used. Same source point solved iteratively for unchanged sampled UV. This is a shader expectation, not proof of GPU output.')
(w/'window-gpu-prediction-145.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
