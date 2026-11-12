"""Conservative H3 definition spheres from authored Reach instance AABBs.

Reach removes the definition sphere but retains world-space bounds per instance.
Transform every authored box corner back into definition space, union repeated
instances, and round the resulting sphere outwards. No visual geometry changes.
"""
import itertools
import numpy as np


def definition_spheres(instances,definition_count,collision_points=None):
    corners={i:[] for i in range(definition_count)}
    for row in instances:
        definition=row['definition']
        if definition not in corners:raise ValueError('Definition outside bounds table')
        matrix=np.asarray(row['matrix'],dtype=np.float64)
        basis=matrix[:9].reshape(3,3).T
        translation=matrix[9:12]
        scale=row['scale']
        if not np.isfinite(matrix).all() or not np.isfinite(scale) or scale<=0:
            raise ValueError('Nonfinite/invalid instance pose')
        if not np.allclose(basis.T@basis,np.eye(3),rtol=0,atol=2e-5):
            raise ValueError('Nonorthogonal instance basis needs explicit sphere handling')
        bounds=np.asarray(row['bounds'],dtype=np.float64).reshape(3,2)
        if not np.isfinite(bounds).all() or np.any(bounds[:,0]>bounds[:,1]):
            raise ValueError('Invalid authored Reach bounding box')
        world=np.asarray(list(itertools.product(*bounds)))
        local=np.linalg.solve(basis,(world-translation).T).T/scale
        if not np.allclose((basis@local.T).T*scale+translation,world,rtol=0,atol=1e-6):
            raise ValueError('Instance bounds transform failed roundtrip')
        corners[definition].extend(local)
    result={}
    for definition,points in corners.items():
        if not points:raise ValueError('Unplaced definition needs another authored bound source')
        # Collision vertices can extend slightly beyond the authored render box.
        # Include them instead of accepting a tolerance that could cull collision.
        points.extend((collision_points or {}).get(definition,()))
        points=np.asarray(points)
        if not np.isfinite(points).all():raise ValueError('Nonfinite collision bound input')
        center=((points.min(axis=0)+points.max(axis=0))/2).astype(np.float32)
        distance=np.linalg.norm(points-center.astype(np.float64),axis=1)
        radius=np.float32(distance.max())
        if float(radius)<distance.max():radius=np.nextafter(radius,np.float32(np.inf))
        if not np.isfinite(radius) or np.any(distance>float(radius)):
            raise ValueError('Native sphere does not enclose authored bounds')
        result[definition]=tuple(float(x) for x in center)+(float(radius),)
    return result
