"""Resolve authored rigid-node transforms and check their inverse bind frames."""
import numpy as np

def resolve_nodes(nodes):
    if not nodes or [i for i,n in enumerate(nodes) if n['parent']==-1]!=[0]:
        raise ValueError('Expected one root at node zero')
    result={}
    def resolve(i,ancestors=()):
        if i in ancestors or not 0<=i<len(nodes):raise ValueError('Invalid node hierarchy')
        if i in result:return result[i]
        node=nodes[i];x,y,z,w=node['rotation']
        if abs(x*x+y*y+z*z+w*w-1)>1e-5:raise ValueError('Non-unit node quaternion')
        rotation=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                           [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                           [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
        local=np.eye(4);local[:3,:3]=rotation;local[:3,3]=node['position']
        transform=local if node['parent']==-1 else resolve(node['parent'],ancestors+(i,))@local
        inverse=np.eye(4);inverse[:3,:3]=np.array(node['inverse_basis']).reshape(3,3).T*node['inverse_scale']
        inverse[:3,3]=node['inverse_position']
        if not np.isfinite(transform).all() or np.max(np.abs(inverse@transform-np.eye(4)))>1e-5:
            raise ValueError('Node and inverse bind frame disagree')
        result[i]=transform
        return transform
    frames=[resolve(i) for i in range(len(nodes))]
    if np.max(np.abs(frames[0]-np.eye(4)))>1e-6:raise ValueError('Nonidentity object root')
    return frames
