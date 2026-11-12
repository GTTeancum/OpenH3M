"""Numerical checks for the applied transforms, without gameplay validation."""
import math
import numpy as np
from scipy.spatial.transform import Rotation
from anchor_transform_math import bounds_matrix,closest,transfer

def check(profile,row,triangles,original=None,source_bounds=None):
 target=next(t for t in profile['targets'] if t['map']==row['map'] and t['palette_index']==row['palette_index'])
 assert target['geometry_signature']==row['raw_geometry_signature']
 vertices=triangles.reshape(-1,3);bounds=np.stack((vertices.min(0),vertices.max(0)),axis=1)
 assert np.max(abs(bounds-profile['target_bounds']))<1e-10
 points=profile['points'];assert 0<len(points)<=32 and len(points)==len(profile['evidence'])
 if profile['source']:
  assert len(original)==len(profile['original'])==len(points)
  assert np.max(abs(np.array(source_bounds).reshape(3,2)-profile['source_bounds']))<1e-10
  for a,b in zip(original,profile['original']):
   assert a['node']==b['node'] and math.dist(a['position'],b['position'])<1e-10 and math.dist(a['rotation'],b['rotation'])<1e-10
  a,t=bounds_matrix(profile['source_bounds'],profile['target_bounds'],profile['yaw_degrees'],scale=row['label']!='Tower 3 Story')
  assert np.max(abs(a-profile['matrix']))<1e-12 and np.max(abs(t-profile['translation']))<1e-12
  for before,after,evidence in zip(original,points,profile['evidence']):
   calculated=transfer(before,a,t)
   assert math.dist(calculated['position'],evidence['affine'])<1e-10
   assert math.dist(np.array(calculated['position'])+evidence['correction'],after['position'])<1e-10
   assert math.dist(calculated['rotation'],after['rotation'])<1e-10
   nearest,distance,index=closest(evidence['reference'],triangles)
   assert abs(distance-evidence['surface_distance'])<1e-9
   expected=evidence['reference'] if evidence['construction_reference'] else nearest
   assert math.dist(expected,after['position'])<1e-9
 else:
  for point,evidence in zip(points,profile['evidence']):
   axis,sign=evidence['support_axis'],evidence['support_sign']
   support=float(vertices[:,axis].max() if sign>0 else vertices[:,axis].min())
   assert abs(support-evidence['support_coordinate'])<1e-10
   face=vertices[abs(vertices[:,axis]-support)<.00001];expected=face.mean(axis=0);expected[axis]=support
   assert math.dist(expected,point['position'])<1e-10
   forward=Rotation.from_quat(point['rotation']).as_matrix()[:,0]
   assert math.dist(forward,np.eye(3)[axis]*sign)<1e-10
   assert np.max((vertices-np.array(point['position']))@forward)<1e-10
 for point in points:
  assert point['node']==0 and np.isfinite(point['position']).all()
  assert abs(sum(q*q for q in point['rotation'])-1)<1e-10
 return points
