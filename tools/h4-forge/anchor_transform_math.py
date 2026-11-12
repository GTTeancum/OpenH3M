"""Offline affine anchor transfer and closest-point geometry correction."""
import numpy as np
from scipy.spatial.transform import Rotation

def transfer(point,matrix,translation):
 a=np.asarray(matrix);p=a@point['position']+translation
 basis=Rotation.from_quat(point['rotation']).as_matrix()
 forward=np.linalg.solve(a.T,basis[:,0]);forward/=np.linalg.norm(forward)
 up=a@basis[:,2];up-=forward*np.dot(up,forward);up/=np.linalg.norm(up)
 left=np.cross(up,forward)
 q=Rotation.from_matrix(np.column_stack((forward,left,up))).as_quat()
 return dict(node=0,position=p.tolist(),rotation=q.tolist())

def closest(point,triangles):
 p=np.asarray(point);a,b,c=triangles[:,0],triangles[:,1],triangles[:,2]
 ab=b-a;ac=c-a;ap=p-a
 dot=lambda x,y:np.einsum('ij,ij->i',x,y)
 aa=dot(ab,ab);bb=dot(ab,ac);cc=dot(ac,ac);da=dot(ap,ab);dc=dot(ap,ac)
 denominator=aa*cc-bb*bb;valid=denominator>1e-20
 s=np.divide(cc*da-bb*dc,denominator,out=np.zeros_like(denominator),where=valid)
 t=np.divide(aa*dc-bb*da,denominator,out=np.zeros_like(denominator),where=valid)
 projected=a+s[:,None]*ab+t[:,None]*ac
 dist=np.where(valid&(s>=0)&(t>=0)&(s+t<=1),dot(projected-p,projected-p),np.inf)
 choices=[projected];distances=[dist]
 for start,end in ((a,b),(b,c),(c,a)):
  edge=end-start;length=dot(edge,edge)
  f=np.clip(np.divide(dot(p-start,edge),length,out=np.zeros_like(length),where=length>0),0,1)
  q=start+f[:,None]*edge;choices.append(q);distances.append(dot(q-p,q-p))
 distance=np.array(distances);kind,index=np.unravel_index(distance.argmin(),distance.shape)
 return choices[kind][index].tolist(),float(np.sqrt(distance[kind,index])),int(index)

def bounds_matrix(source,target,yaw=0,scale=True):
 r=Rotation.from_euler('z',yaw,degrees=True).as_matrix()
 source=np.array(source);target=np.array(target)
 extent=abs(r)@(source[:,1]-source[:,0]);sizes=(target[:,1]-target[:,0])/extent if scale else np.ones(3)
 a=np.diag(sizes)@r;t=target.mean(axis=1)-a@source.mean(axis=1)
 assert np.linalg.det(a)>0 and np.isfinite(a).all() and np.isfinite(t).all()
 return a,t
