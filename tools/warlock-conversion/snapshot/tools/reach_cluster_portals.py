"""Split a cluster's portal polygons without changing its external neighbors."""
from copy import deepcopy
import numpy as np


def polygon_area(vertices):
    p=np.asarray(vertices,dtype=float)
    if len(p)<3:return 0.
    return float(np.linalg.norm(np.cross(p,np.roll(p,-1,axis=0)).sum(axis=0))*.5)


def clip_polygon(vertices,axis,value,positive):
    p=np.asarray(vertices,dtype=float);out=[]
    for a,b in zip(p,np.roll(p,-1,axis=0)):
        da=(a[axis]-value)*(1 if positive else -1)
        db=(b[axis]-value)*(1 if positive else -1)
        if da>=0:out.append(a)
        if (da<0<db) or (db<0<da):
            q=a+(b-a)*(da/(da-db));q[axis]=value;out.append(q)
    clean=[]
    for v in out:
        if not clean or not np.array_equal(v,clean[-1]):clean.append(v)
    if len(clean)>1 and np.array_equal(clean[0],clean[-1]):clean.pop()
    return np.asarray(clean,dtype=np.float32).astype(float).tolist()


def split_cluster_portals(portals,cluster_count,parent,bounds,axis,value,plane_index):
    if not 0<=parent<cluster_count or axis not in (0,1,2):raise ValueError('Invalid cluster split identity')
    bounds=np.asarray(bounds,dtype=float).reshape(3,2)
    if not bounds[axis,0]<value<bounds[axis,1]:raise ValueError('Plane outside parent cluster')
    child=cluster_count;output=deepcopy(portals);source_map={i:[i] for i in range(len(portals))}
    def adjusted(source,vertices,side):
        row=deepcopy(source);row['vertices']=vertices
        for field in ('back','front'):
            if row[field]==parent:row[field]=parent if side==0 else child
        center=np.asarray(vertices).mean(axis=0).astype(np.float32)
        radius=np.float32(np.linalg.norm(np.asarray(vertices)-center,axis=1).max())
        radius=np.nextafter(radius,np.float32(np.inf))
        row.update(centroid=center.tolist(),radius=float(radius))
        return row
    area_checks=[]
    for i,source in enumerate(portals):
        if parent not in (source['back'],source['front']):continue
        if source['back']==source['front']:raise ValueError('Self-connected source portal')
        points=np.asarray(source['vertices']);signed=points[:,axis]-value
        if np.all(signed==0):raise ValueError('Split plane coincides with authored portal')
        pieces=[clip_polygon(points,axis,value,side==1) for side in (0,1)]
        valid=[(side,p) for side,p in enumerate(pieces) if polygon_area(p)>0]
        area=polygon_area(points);combined=sum(polygon_area(p) for _,p in valid)
        if not np.isclose(area,combined,rtol=2e-5,atol=1e-5):raise ValueError('Portal clipping changed area')
        if not valid:raise ValueError('Portal disappeared during split')
        area_checks.append(dict(source_portal=i,source_area=area,partition_area=combined,pieces=len(valid)))
        side,p=valid[0];output[i]=adjusted(source,p,side)
        for side,p in valid[1:]:
            source_map[i].append(len(output));output.append(adjusted(source,p,side))
    # A conservative internal portal across the original cluster bounds. Solid
    # geometry still occludes; native visibility acceptance remains mandatory.
    other=[a for a in range(3) if a!=axis];rectangle=[]
    for u,v in ((0,0),(1,0),(1,1),(0,1)):
        p=[0.,0.,0.];p[axis]=value;p[other[0]]=bounds[other[0],u];p[other[1]]=bounds[other[1],v];rectangle.append(p)
    normal=np.cross(np.subtract(rectangle[1],rectangle[0]),np.subtract(rectangle[2],rectangle[1]))
    if normal[axis]<0:rectangle.reverse()
    internal=dict(back=parent,front=child,plane=plane_index,flags=0,vertices=rectangle)
    output.append(adjusted(internal,rectangle,0))
    incidence=[[] for _ in range(cluster_count+1)]
    for i,p in enumerate(output):
        for cluster in (p['back'],p['front']):
            if not 0<=cluster<len(incidence):raise ValueError('Portal cluster outside table')
            incidence[cluster].append(i)
    # Contract the new pair: every original connection must remain, no new
    # external connection may appear. Orientation and authored flags retained.
    before={(p['back'],p['front'],p['flags']) for p in portals}
    after={(parent if p['back']==child else p['back'],parent if p['front']==child else p['front'],p['flags']) for p in output[:-1]}
    if before!=after:raise ValueError('Partition changed external portal graph')
    return dict(portals=output,cluster_portals=incidence,source_portal_remap=source_map,
                new_cluster=child,internal_portal=len(output)-1,area_checks=area_checks,
                requires_leaf_and_visibility_integration=True)
