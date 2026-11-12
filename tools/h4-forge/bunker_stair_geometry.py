"""Bunker Stair construction references, derived from the two actual meshes."""
import numpy as np

def foot_corner(triangles,y,min_x):
 """Bottom of the outer vertical foot face, above the lower bevel."""
 ends=[]
 for tri in triangles:
  if tri[:,0].min()<=min_x or tri[:,2].min()>=0:continue
  cut=[]
  for a,b in zip(tri,np.roll(tri,-1,axis=0)):
   if abs(b[1]-a[1])<1e-12:continue
   fraction=(y-a[1])/(b[1]-a[1])
   if 0<=fraction<=1:cut.append(a+fraction*(b-a))
  if len(cut)==2 and abs(cut[0][0]-cut[1][0])<1e-6 and abs(cut[0][2]-cut[1][2])>.05:
   ends.extend(cut)
 assert ends
 return min(ends,key=lambda p:p[2]).tolist()

def references(source,target,original,ray_hits):
 # Match the side-wall span and the adjacent gap beneath the raised stair.
 # Preserve the authored fraction along each span instead of guessing that
 # either original marker was centered on that feature.
 source_hits=[-4+h for h in ray_hits((original[6]['position'][0]-.01,-4,1),(0,1,0),source)]
 target_hits=[-4+h for h in ray_hits((1.79,-4,.5),(0,1,0),target)]
 assert len(source_hits)==len(target_hits)==4
 assert np.max(abs(np.array(source_hits)-[-2.55429,-2.33361,-1.32917,2.83587]))<.00001
 assert np.max(abs(np.array(target_hits)-[-2.4,-2.2,-1,2.6]))<.0001
 def transfer(value,span):
  lo,hi=span;fraction=(value-source_hits[lo])/(source_hits[hi]-source_hits[lo])
  assert 0<fraction<1
  return target_hits[lo]+fraction*(target_hits[hi]-target_hits[lo])
 wall_y=transfer(original[6]['position'][1],(2,3))
 stair_y=transfer(original[9]['position'][1],(1,2))
 old_foot=foot_corner(source,original[7]['position'][1],2.48)
 new_foot=foot_corner(target,wall_y,1.81)
 assert np.linalg.norm(np.array(original[7]['position'])-old_foot)<.003
 # Three left references share the stair-entry center. Front/rear references
 # share the inner stair-wall junction. These are construction planes, with
 # target render quantization checked by the caller, not decoration bounds.
 points=[[-2.9,1.4,-.5],[-2.9,1.4,-1],[-.3,-2.4,-1],[-2.9,1.4,2],
         [-.3,2.6,-1],[-.3,2.6,2],[1.8,wall_y,2],new_foot,
         [new_foot[0],stair_y,new_foot[2]],[1.8,stair_y,2],[-.3,-2.4,2.3]]
 return points,dict(source_side_intersections=source_hits,target_side_intersections=target_hits,
                    source_foot_corner=old_foot,target_foot_corner=new_foot,
                    wall_fraction=(original[6]['position'][1]-source_hits[2])/(source_hits[3]-source_hits[2]),
                    stair_fraction=(original[9]['position'][1]-source_hits[1])/(source_hits[2]-source_hits[1]))
