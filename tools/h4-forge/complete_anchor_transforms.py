"""Apply the remaining object transforms; gameplay testing belongs to the user."""
import contextlib,hashlib,io,json,runpy,struct
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from anchor_transform_math import bounds_matrix,closest,transfer

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/h4-forge-research/isolated'
inventory=json.loads((OUT/'scenery-inventory.json').read_text())
render={(r['map'],r['palette_index']):r for r in json.loads((OUT/'render-planes-all.json').read_text())['rows']}
with contextlib.redirect_stdout(io.StringIO()):h4=runpy.run_path(str(OUT.parent/'inspect_anchors.py'))
models={m['name'].split('\\')[-1]:m for m in h4['models']}
sources={'Tower 3 Story':'fw_unsc_c_tower_3_story','Tower Tall':'fw_unsc_c_tower_tall',
 'Walkway Small Cover':'fw_unsc_c_walkway_small_cover','Ramp, Circular, Small':'fw_unsc_c_ramp_circle_small',
 'Ramp, Circular, Large':'fw_unsc_c_ramp_circle_large','Cannon, Man':'fw_cannon_man','Tunnel, Long':'fw_unsc_c_tunnel_3x3'}
labels=list(sources)+['Radio Antennae','Weapon Holder','Glass Sail','Sniper Nest'];output={}
for label in labels:
 rows=[r for r in inventory['rows'] if r['label']==label];assert rows
 row=rows[0];rr=render[row['map'],row['palette_index']];path=ROOT/rr['triangle_file']
 assert hashlib.sha256(path.read_bytes()).hexdigest()==rr['triangle_sha256']
 with np.load(path) as file:triangles=file['triangles']
 target_bounds=np.array(rr['referenced_bounds']);evidence=[];references={}
 if label in sources:
  name=sources[label];model=models[name];at=h4['off'](h4['u'](h4['off'](h4['tp'])+model['tag_index']*8+4))
  compression=h4['block'](at+0x80,52);assert len(compression)==1
  source_bounds=np.array(struct.unpack_from('>6f',h4['d'],compression[0]+4)).reshape(3,2)
  original=[p for g in model['markers'] if g['group']=='sandbox_magnet' for p in g['points']]
  assert original and all(p['node']==0 for p in original)
  yaw=-90 if label in ('Ramp, Circular, Small','Cannon, Man') else 0
  matrix,translation=bounds_matrix(source_bounds,target_bounds,yaw,scale=label!='Tower 3 Story')
  points=[transfer(p,matrix,translation) for p in original]
  if label=='Ramp, Circular, Small':
   # Matching half-ring, rotated clockwise. Construction end plane X=0;
   # low/high deck and underside levels are .7/1.7 and .5/1.5.
   for i,z in enumerate((.7,1.7,.5,1.5)):
    references[i]=[0,-original[i]['position'][0],z]
   references[4]=[0,0,original[4]['position'][2]+.5]
  elif label=='Ramp, Circular, Large':
   references[0]=[0,points[0]['position'][1],.25]
   references[1]=[0,points[1]['position'][1],2.55]
   references[2]=[4,0,original[2]['position'][2]-source_bounds[2,0]]
   references[3]=[0,4,2.15];references[4]=[0,-4,2.15]
  elif label=='Walkway Small Cover':
   references.update({1:[1,original[1]['position'][1]-.95,.8],2:[-1,original[2]['position'][1]-.95,.8],
     3:[-.85,1.75,-1.7],4:[.85,1.75,-1.7],5:[1,4.25,-1.7],6:[-1,4.25,-1.7],7:[0,-6,1]})
  elif label=='Cannon, Man':
   # H4 authors these below the visual base. Preserve that reference through
   # the affine transform; projecting into H3's V-shaped housing changes it.
   references={i:list(p['position']) for i,p in enumerate(points)}
  for i,p in enumerate(points):
   affine=list(p['position']);reference=references.get(i,affine)
   # Preserve named construction planes on beveled pieces. For the other
   # transferred references, remove the local surface offset after fitting.
   projected,distance,triangle=closest(reference,triangles)
   use_reference=i in references
   p['position']=reference if use_reference else projected
   evidence.append(dict(index=i,affine=affine,reference=reference,correction=(np.array(p['position'])-affine).tolist(),
       construction_reference=use_reference,surface_distance=distance,triangle=triangle))
  source=model['name']
 else:
  # H3-only pieces have no corresponding H4 object. Author ordinary marker
  # frames on their geometric supporting planes; H4 still does all snapping.
  points=[];original=[];matrix=np.eye(3);translation=np.zeros(3);source_bounds=None;source=None
  axes=[(2,-1)] if label in ('Radio Antennae','Weapon Holder') else [(a,s) for a in range(3) for s in (-1,1)]
  vertices=triangles.reshape(-1,3)
  for axis,sign in axes:
   support=float(vertices[:,axis].max() if sign>0 else vertices[:,axis].min())
   face=vertices[abs(vertices[:,axis]-support)<.00001];point=face.mean(axis=0);point[axis]=support
   forward=np.eye(3)[axis]*sign;up=np.array([0.,0.,1.]) if axis!=2 else np.array([1.,0.,0.])
   left=np.cross(up,forward);q=Rotation.from_matrix(np.column_stack((forward,left,up))).as_quat()
   points.append(dict(node=0,position=point.tolist(),rotation=q.tolist()))
   evidence.append(dict(index=len(points)-1,support_axis=axis,support_sign=sign,support_coordinate=support,
                        supporting_vertices=len(face),maximum_outside=float(((vertices-point)@forward).max())))
  yaw=0
 output[label]=dict(source=source,source_bounds=None if source_bounds is None else source_bounds.tolist(),
   target_bounds=target_bounds.tolist(),yaw_degrees=yaw,matrix=matrix.tolist(),translation=translation.tolist(),
   original=original,points=points,evidence=evidence,
   targets=[dict(map=r['map'],palette_index=r['palette_index'],geometry_signature=r['raw_geometry_signature']) for r in rows],
   method='p_target = A p_source + t + local correction; normal = normalize(inverse(A).T normal_source); proper orthonormal frame retained' if source else 'Native object supporting-plane anchors in ordinary H4 marker format',
   testing='In-game behavior and further corrections are user-owned; no object-combination campaign')
 print(label,len(points),'anchors',max((e.get('surface_distance',0) for e in evidence),default=0))
(Path(__file__).parent/'anchor_completion.json').write_text(json.dumps(output,indent=2)+'\n')
