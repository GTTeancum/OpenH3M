"""Geometry-backed per-piece anchor proofs; no game runs or pairwise campaign.

Only implemented, satisfied proof obligations earn verified status. All other
inventory rows remain unverified, including previously tested individual joints.
"""
import contextlib
from collections import Counter
import argparse
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import runpy
import struct
import numpy as np
from anchor_frames import adapt
from node_frames import resolve_nodes

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/h4-forge-research/isolated'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check-pack',action='store_true',help='Also verify the exported runtime anchors for every proved entry')
args=parser.parse_args()
pack={}
if args.check_pack:
 payload=(OUT/'markers.bin').read_bytes();magic,count=struct.unpack_from('<4sI',payload)
 assert magic==b'AFM2';offset=8
 for _ in range(count):
  mid,datum,radius,n,fixed=struct.unpack_from('<IIfII',payload,offset);offset+=20
  points=[struct.unpack_from('<7f',payload,offset+i*28) for i in range(n)];offset+=28*n
  assert (mid,datum) not in pack
  pack[mid,datum]=(points,fixed,radius)
 assert offset==len(payload)
inventory=json.loads((OUT/'scenery-inventory.json').read_text())
geometry={(r['map'],r['palette_index']):r for r in json.loads((OUT/'scenery-geometry.json').read_text())}
if args.check_pack:
 bound_rows=[r for r in inventory['rows'] if r['bound']]
 assert len(bound_rows)==len(pack)
 for row in bound_rows:
  points,fixed,radius=pack[row['map_id'],int(row['datum'],16)]
  sphere=geometry[row['map'],row['palette_index']]['bounding_sphere']
  assert math.isfinite(radius) and radius>0
  # Triangle inequality: an origin-centered query sphere encloses the native
  # offset sphere, and every current authored/adapted anchor is inside it.
  assert radius+2e-6>=sphere['radius']+math.dist(sphere['center'],(0,0,0))
  assert all(math.dist(p[:3],(0,0,0))<=radius+2e-6 for p in points)
frames=json.loads((Path(__file__).parent/'anchor_frames.json').read_text())
completion=json.loads((Path(__file__).parent/'anchor_completion.json').read_text())
boxes=json.loads((Path(__file__).parent/'box_anchor_geometry.json').read_text())
detailed_boxes=json.loads((Path(__file__).parent/'detailed_box_anchor_geometry.json').read_text())
flat_slabs=json.loads((Path(__file__).parent/'flat_anchor_geometry.json').read_text())
straight_ramps=json.loads((Path(__file__).parent/'straight_ramp_geometry.json').read_text())
walls=json.loads((Path(__file__).parent/'wall_anchor_geometry.json').read_text())
railings=json.loads((Path(__file__).parent/'railing_anchor_geometry.json').read_text())
anchorless=json.loads((Path(__file__).parent/'anchorless_policy.json').read_text())
render_report=json.loads((OUT/'render-planes-block.json').read_text())
assert render_report['maps']==inventory['maps']
render_rows={(r['map'],r['palette_index']):r for r in render_report['rows']}
all_render=json.loads((OUT/'render-planes-all.json').read_text())
assert all_render['maps']==inventory['maps']
all_render_rows={(r['map'],r['palette_index']):r for r in all_render['rows']}
for m in inventory['maps']:
 path=next((ROOT/'work/dlc/installed-current').rglob(m['name']))
 with path.open('rb') as file:actual=hashlib.file_digest(file,'sha256').hexdigest()
 assert actual==m['sha256'],'Regenerate inventory after map changes'
with contextlib.redirect_stdout(io.StringIO()):
 h4=runpy.run_path(str(OUT.parent/'inspect_anchors.py'))
data=h4['d'];off=h4['off'];block=h4['block'];u=lambda at:struct.unpack_from('>I',data,at)[0]
tag_at=off(h4['tp'])
models={m['name'].split('\\')[-1]:m for m in h4['models']}
all_models={}
for index in range(h4['nt']):
 group,salt,ptr=struct.unpack_from('>HHI',data,tag_at+index*8)
 if group==65535 or ptr in (0,0xffffffff) or h4['groups'][group]!='mode':continue
 name=h4['text'](h4['names'],u(h4['ni']+index*4))
 all_models.setdefault(name.split('\\')[-1],[]).append((index,name,off(ptr)))

def axis_box(vertices,planes,tolerance=1e-5):
 """Prove the complete convex core is a box, not merely matching its bounds."""
 bounds=[[min(p[i] for p in vertices),max(p[i] for p in vertices)] for i in range(3)]
 assert len(vertices)==8 and len(planes)==6
 for corner in itertools.product(*bounds):
  assert min(math.dist(corner,p) for p in vertices)<tolerance
 expected={(i,sign) for i in range(3) for sign in (-1,1)};found=set()
 for plane in planes:
  axis=max(range(3),key=lambda i:abs(plane[i]));sign=1 if plane[axis]>0 else -1
  assert max(abs(plane[i]-(sign if i==axis else 0)) for i in range(3))<tolerance
  expected_d=-sign*bounds[axis][1 if sign==1 else 0]
  assert abs(plane[3]-expected_d)<tolerance
  assert max(sum(plane[i]*v[i] for i in range(3))+plane[3] for v in vertices)<tolerance
  found.add((axis,sign))
 assert found==expected
 return bounds

def rotation_axes(q):
 x,y,z,w=q
 return [(1-2*(y*y+z*z),2*(x*y+z*w),2*(x*z-y*w)),
         (2*(x*y-z*w),1-2*(x*x+z*z),2*(y*z+x*w)),
         (2*(x*z+y*w),2*(y*z-x*w),1-2*(x*x+y*y))]

def triangle_distance(point,triangles):
 """Exact minimum point-to-triangle distance (faces and all three edges)."""
 p=np.asarray(point);a,b,c=triangles[:,0],triangles[:,1],triangles[:,2]
 ab=b-a;ac=c-a;ap=p-a
 d00=np.einsum('ij,ij->i',ab,ab);d01=np.einsum('ij,ij->i',ab,ac);d11=np.einsum('ij,ij->i',ac,ac)
 d20=np.einsum('ij,ij->i',ap,ab);d21=np.einsum('ij,ij->i',ap,ac)
 denom=d00*d11-d01*d01;valid=denom>1e-20
 v=np.divide(d11*d20-d01*d21,denom,out=np.zeros_like(denom),where=valid)
 w=np.divide(d00*d21-d01*d20,denom,out=np.zeros_like(denom),where=valid)
 inside=valid&(v>=0)&(w>=0)&(v+w<=1)
 distances=np.where(inside,np.linalg.norm(ap-v[:,None]*ab-w[:,None]*ac,axis=1),np.inf)
 for start,end in ((a,b),(b,c),(c,a)):
  edge=end-start;length=np.einsum('ij,ij->i',edge,edge)
  t=np.clip(np.divide(np.einsum('ij,ij->i',p-start,edge),length,out=np.zeros_like(length),where=length>0),0,1)
  distances=np.minimum(distances,np.linalg.norm(p-start-t[:,None]*edge,axis=1))
 return float(distances.min())

def actual_triangles(row):
 rendered=all_render_rows[row['map'],row['palette_index']];assert rendered['status']=='measured'
 path=ROOT/rendered['triangle_file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==rendered['triangle_sha256']
 with np.load(path) as loaded:return loaded['triangles']

def ray_hits(origin,direction,triangles):
 """All positive ray/triangle intersections, merged only within mesh quantum."""
 origin=np.asarray(origin);direction=np.asarray(direction)
 e1=triangles[:,1]-triangles[:,0];e2=triangles[:,2]-triangles[:,0]
 h=np.cross(direction,e2);det=np.einsum('ij,ij->i',e1,h);valid=np.abs(det)>1e-12
 inv=np.divide(1,det,out=np.zeros_like(det),where=valid);s=origin-triangles[:,0]
 u=inv*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1);v=inv*(q@direction)
 t=inv*np.einsum('ij,ij->i',e2,q)
 selected=valid&(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)&(t>=0)
 hits=[]
 for value in sorted(t[selected]):
  if not hits or value-hits[-1]>.0002:hits.append(float(value))
 return hits

def identity_compound(g,body_node=0,plane_exceptions=None,expected_motion_type=5,planar_face_exceptions=None):
 """Resolve native rigid leaves without changing the explicitly expected motion."""
 assert len(g['bodies'])==1
 if body_node==0:assert len(g['nodes'])==1
 node_frames=resolve_nodes(g['nodes'])
 node=g['nodes'][0];body=g['bodies'][0]
 assert node['parent']==-1 and node['position']==[0,0,0] and node['rotation']==[0,0,0,1]
 assert node['inverse_basis']==[1,0,0,0,1,0,0,0,1] and node['inverse_scale']==1 and node['inverse_position']==[0,0,0]
 assert expected_motion_type in (2,5)
 assert body['node']==body_node and body['motion_type']==expected_motion_type
 leaves=[]
 def visit(kind,index,ancestors=()):
  assert (kind,index) not in ancestors
  if kind==4:
   assert 0<=index<len(g['polyhedra']);leaves.append(index)
  elif kind==14:
   assert 0<=index<len(g['shape_lists'])
   for child in g['shape_lists'][index]:visit(*child,ancestors+((kind,index),))
  elif kind==15:
   assert 0<=index<len(g['mopps']);visit(*g['mopps'][index],ancestors+((kind,index),))
  else:raise AssertionError('Unsupported compound child '+str(kind))
 visit(body['shape_type'],body['shape_index'])
 assert sorted(leaves)==list(range(len(g['polyhedra'])))
 planar_polygons=[];partial_plane_tetrahedra=[];native_plane_inconsistencies=[];plane_exceptions=plane_exceptions or {}
 planar_face_exceptions=planar_face_exceptions or {};native_planar_face_residuals=[]
 for shape_index,shape in enumerate(g['polyhedra']):
  vertices=np.asarray(shape['vertices']);planes=np.asarray(shape['planes'])
  assert len(vertices)>=3 and len(planes)>=2 and shape['radius']>0
  assert np.max(np.abs(np.linalg.norm(planes[:,:3],axis=1)-1))<1e-5
  distance=vertices@planes[:,:3].T+planes[:,3]
  inconsistent=tuple(np.where((distance.max(axis=0)>=.0001)|(np.abs(distance.max(axis=0))>=.0001))[0])
  assert inconsistent==plane_exceptions.get(shape_index,()),(shape_index,inconsistent)
  if inconsistent:
   # A specifically recorded native-data inconsistency does not change a node
   # transform. Retain it as evidence, and never pretend it proves a convex
   # face or silently repair console physics to make an editor audit pass.
   native_plane_inconsistencies.append(dict(shape=shape_index,planes=list(map(int,inconsistent)),
       maximum_vertex_distances=distance[:,list(inconsistent)].max(axis=0).tolist()))
   planes=np.delete(planes,inconsistent,axis=0);distance=vertices@planes[:,:3].T+planes[:,3]
  assert distance.max()<.0001 and np.max(np.abs(distance.max(axis=0)))<.0001
  # The converter retains redundant/interior support vertices on some leaves.
  # Reference/frame verification must not mistake those for corrupt corners.
  # Exact hull topology is a separate obligation in box/prism proofs above.
  centered=vertices-vertices.mean(axis=0);_,singular,basis=np.linalg.svd(centered,full_matrices=False)
  if len(planes)<4:
   # A four-vertex native convex support shape may store only a subset of
   # its face planes. Reconstruct the complete tetrahedron from its vertices
   # and prove each stored plane belongs to it, rather than requiring a map
   # repair or treating the incomplete half-space list as the entire shape.
   assert len(vertices)==4 and not inconsistent and singular[-1]>1e-6
   volume=float(abs(np.linalg.det((vertices[1:]-vertices[0]).T))/6);assert volume>1e-8
   complete=[]
   for indices in itertools.combinations(range(4),3):
    a,b,c=vertices[list(indices)];normal=np.cross(b-a,c-a);length=np.linalg.norm(normal);assert length>1e-8
    normal/=length
    if np.max((vertices-a)@normal)>1e-8:normal=-normal
    plane=np.r_[normal,-normal@a];residuals=vertices@normal+plane[3]
    assert residuals.max()<1e-10 and np.count_nonzero(abs(residuals)<1e-10)==3
    complete.append(plane)
   errors=[min(float(np.linalg.norm(p-q)) for q in complete) for p in planes];assert max(errors)<.000005
   assert len({int(np.argmin([np.linalg.norm(p-q) for q in complete])) for p in planes})==len(planes)
   partial_plane_tetrahedra.append(dict(index=shape_index,stored_planes=len(planes),volume=volume,
       reconstructed_planes=[p.tolist() for p in complete],stored_plane_residuals=errors))
   continue
  if singular[-1]<1e-6:
   # Radius-bearing planar polygons are valid native convex leaves. Establish
   # the complete 2D boundary, two opposed face planes, and edge half-spaces.
   # An extra plane touching one corner is a redundant support constraint.
   normal=basis[-1];assert singular[1]>1e-5
   assert np.max(np.abs(centered@normal))<1e-6
   faces=np.abs(planes[:,:3]@normal)>1-1e-6;assert faces.sum()==2
   face_residual=float(np.max(np.abs(distance[:,faces])))
   if shape_index in planar_face_exceptions:
    expected=planar_face_exceptions[shape_index]
    assert 1e-5<=expected<.0001 and abs(face_residual-expected)<1e-12
    native_planar_face_residuals.append(dict(index=shape_index,maximum_face_residual=face_residual))
   else:assert face_residual<1e-5
   assert np.linalg.norm(planes[faces,:3].sum(axis=0))<1e-5
   hull_edges=set()
   for i,j in itertools.combinations(range(len(vertices)),2):
    signed=np.cross(vertices[j]-vertices[i],vertices-vertices[i])@normal
    if (signed.min()>-1e-7 or signed.max()<1e-7) and np.max(np.abs(signed))>1e-6:
     hull_edges.add((i,j))
   assert len(hull_edges)==len(vertices)
   assert all(sum(i in edge for edge in hull_edges)==2 for i in range(len(vertices)))
   edges=set()
   for j in np.where(~faces)[0]:
    assert abs(planes[j,:3]@normal)<1e-5
    touched=tuple(np.where(np.abs(distance[:,j])<1e-5)[0]);assert len(touched) in (1,2)
    assert min(distance[:,j])<-1e-6
    if len(touched)==2:edges.add(touched)
   assert edges==hull_edges
   area=sum(abs(np.cross(centered[i],centered[j])@normal)/2 for i,j in hull_edges)
   planar_polygons.append(dict(index=shape_index,vertices=len(vertices),area=float(area),skin_radius=shape['radius']))
  else:
   assert np.linalg.matrix_rank(centered)==3

 assert {v['shape'] for v in native_plane_inconsistencies}==set(plane_exceptions)
 assert {v['index'] for v in native_planar_face_residuals}==set(planar_face_exceptions)
 return dict(root_shape=[body['shape_type'],body['shape_index']],resolved_polyhedra=len(leaves),
             native_plane_inconsistencies=native_plane_inconsistencies,
             native_planar_face_residuals=native_planar_face_residuals,
             planar_polygons=planar_polygons,partial_plane_tetrahedra=partial_plane_tetrahedra,
             body_node=body_node,native_motion_type=body['motion_type'],body_to_object=node_frames[body_node].tolist())

def source_markers(name):
 model=models[name];index=model['tag_index'];at=off(u(tag_at+index*8+4))
 nodes=block(at+0x30,112);assert len(nodes)==1
 assert struct.unpack_from('>7f',data,nodes[0]+12)==(0,0,0,0,0,0,1)
 assert struct.unpack_from('>h',data,nodes[0]+4)[0]==-1
 assert struct.unpack_from('>f',data,nodes[0]+40)[0]==1
 assert struct.unpack_from('>9f',data,nodes[0]+44)==(1,0,0,0,1,0,0,0,1)
 assert struct.unpack_from('>3f',data,nodes[0]+80)==(0,0,0)
 compression=block(at+0x80,52);assert len(compression)==1
 bounds=struct.unpack_from('>6f',data,compression[0]+4)
 anchors=[p for g in model['markers'] if g['group']=='sandbox_magnet' for p in g['points']]
 assert anchors and all(p['node']==0 for p in anchors)
 return index,bounds,anchors

def source_geometry(name,compound=False):
 index,bounds,anchors=source_markers(name)
 physics=[]
 for i in range(h4['nt']):
  group,salt,ptr=struct.unpack_from('>HHI',data,tag_at+i*8)
  if group==65535 or ptr in (0,0xffffffff) or h4['groups'][group]!='hlmt':continue
  hlmt=off(ptr)
  if u(hlmt+12)&65535==index:physics.append(u(hlmt+0x3c))
 assert len(set(physics))==1 and physics[0]!=0xffffffff
 ph=off(u(tag_at+(physics[0]&65535)*8+4));bodies=block(ph+0x5c,192)
 assert len(bodies)==1 and struct.unpack_from('>h',data,bodies[0])[0]==0
 root=struct.unpack_from('>2H',data,bodies[0]+0xa4)
 assert root[0] in (14,15) and root[1]==0 if compound else root==(4,0)
 shapes=block(ph+0xb0,144);assert len(shapes)>0 if compound else len(shapes)==1
 four=block(ph+0xbc,48);planes=block(ph+0xc8,16)
 result=[];vi=pi=0
 for shape in shapes:
  nv,nf,nplanes=u(shape+0x6c),u(shape+0x64),u(shape+0x78)
  assert 0<nv<=nf*4 and vi+nf<=len(four) and pi+nplanes<=len(planes)
  vertices=[]
  for row in four[vi:vi+nf]:
   xyz=struct.unpack_from('>12f',data,row);vertices.extend([xyz[i],xyz[i+4],xyz[i+8]] for i in range(4))
  result.append(dict(vertices=vertices[:nv],planes=[struct.unpack_from('>4f',data,row) for row in planes[pi:pi+nplanes]],
                     radius=struct.unpack_from('>f',data,shape+0x30)[0]))
  vi+=nf;pi+=nplanes
 assert vi==len(four) and pi==len(planes)
 return bounds,anchors,result if compound else result[0]

arena_source_bounds,arena_source_anchors,arena_source_shape=source_geometry('fw_unsc_c_arena_wall')
assert len(arena_source_anchors)==9
arena_source_core=axis_box(arena_source_shape['vertices'],arena_source_shape['planes'])
proofs=[]
for row in inventory['rows']:
 result={k:row[k] for k in ('map','palette_index','datum','label','group')}
 result.update(status='unverified',reason='No complete mathematical proof recorded yet')
 if row['group'] not in ('bloc','scen'):
  result.update(status='not_scenery',reason='Native object tag group is '+row['group']+'; retained in inventory, outside scenery-transform scope')
 elif row['label'] in anchorless:
  policy=anchorless[row['label']];evidence=[]
  assert not row['bound'],'Anchorless policy conflicts with current runtime bindings'
  for suffix in policy['h4_models']:
   matches=all_models[suffix];assert len(matches)==1
   index,name,at=matches[0]
   groups=[(h4['sid'](u(group)),len(block(group+4,48))) for group in block(at+0x3c,16)]
   assert not any(count for label,count in groups if label=='sandbox_magnet')
   evidence.append(dict(tag_index=index,name=name,marker_groups=groups))
  if args.check_pack:assert (row['map_id'],int(row['datum'],16)) not in pack
  result.update(status='no_authored_anchors',reason=policy['reason'],source_evidence=evidence,
                limitation='Category behavior checked against actual H4 models; not a claim of identical cross-game geometry.')
 if row['label']=='Arena Wall':
  g=geometry[row['map'],row['palette_index']]
  assert len(g['nodes'])==1 and g['nodes'][0]['parent']==-1
  assert g['nodes'][0]['position']==[0,0,0] and g['nodes'][0]['rotation']==[0,0,0,1]
  assert g['nodes'][0]['inverse_basis']==[1,0,0,0,1,0,0,0,1] and g['nodes'][0]['inverse_scale']==1
  assert g['bodies']==[dict(node=0,motion_type=5,shape_type=4,shape_index=0)]
  assert len(g['polyhedra'])==1 and len(g['compression_bounds'])==1
  shape=g['polyhedra'][0];core=axis_box(shape['vertices'],shape['planes'])
  target=g['compression_bounds'][0];expected=(-5,5,-.25,.25,-6,6)
  assert max(abs(a-b) for a,b in zip(target,expected))<1e-5
  # This piece's core is inset by 2r from every nominal construction plane.
  # Require independent agreement on all six planes; do not generalize the
  # skin convention to other objects without their own geometry proof.
  skin=2*shape['radius']
  assert max(abs(core[i][side]+(-skin if side==0 else skin)-target[2*i+side])
             for i in range(3) for side in range(2))<1e-5
  source_expected=(-5,5,-.3,.3,-5.9,5.9)
  assert max(abs(a-b) for a,b in zip(arena_source_bounds,source_expected))<1e-5
  frame=frames['fw_unsc_c_arena_wall'];mapped=[adapt(p,frame) for p in arena_source_anchors]
  evidence=[]
  for i,(before,after) in enumerate(zip(arena_source_anchors,mapped)):
   constraints=[]
   for axis in range(3):
    for side in range(2):
     if abs(before['position'][axis]-arena_source_bounds[2*axis+side])<1e-5:
      residual=abs(after['position'][axis]-target[2*axis+side]);assert residual<1e-5
      constraints.append(dict(axis=axis,side=side,residual=residual,
                              unadapted_residual=abs(before['position'][axis]-target[2*axis+side])))
   assert constraints
   assert all(target[2*i]-1e-5<=after['position'][i]<=target[2*i+1]+1e-5 for i in range(3))
   assert abs(sum(v*v for v in after['rotation'])-1)<1e-5
   # adapt() independently rejects a scale that changes any frame direction.
   assert math.dist(before['rotation'],after['rotation'])<1e-6
   evidence.append(dict(index=i,position=after['position'],plane_constraints=constraints))
  # Contact spacing follows directly from opposing support planes, without
  # enumerating object pairs. X/Y/Z extents now coincide with the target box.
  mapped_corners=[adapt(dict(position=p,rotation=[0,0,0,1]),frame)['position']
                  for p in itertools.product(*[arena_source_bounds[i:i+2] for i in (0,2,4)])]
  spans=[max(p[i] for p in mapped_corners)-min(p[i] for p in mapped_corners) for i in range(3)]
  target_spans=[target[2*i+1]-target[2*i] for i in range(3)]
  assert max(abs(a-b) for a,b in zip(spans,target_spans))<1e-5
  result.update(status='verified',reason='All nine anchors: box topology, identity node/body, corresponding planes, cardinal frames and support spacing',
    anchors=evidence,contact_spacing=spans,collision_core_inset=skin,
    arena_source_core=arena_source_core,target_core=core,raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Arena Window':
  name='fw_unsc_c_arena_window';_,_,original=source_markers(name)
  g=geometry[row['map'],row['palette_index']];assert len(g['nodes'])==1
  node=g['nodes'][0]
  assert node['parent']==-1 and node['position']==[0,0,0] and node['rotation']==[0,0,0,1]
  assert node['inverse_basis']==[1,0,0,0,1,0,0,0,1] and node['inverse_scale']==1 and node['inverse_position']==[0,0,0]
  assert g['bodies']==[dict(node=0,motion_type=2,shape_type=4,shape_index=0)] and len(g['polyhedra'])==1
  shape=g['polyhedra'][0];skin=2*shape['radius']
  profile=[(-9.6,-3),(5.5,-3),(9,.5),(9,3),(-4.4,3),(-9.6,-2.2)]
  inset_profile=[(x-math.copysign(skin,x+.3),z-math.copysign(skin,z)) for x,z in profile]
  expected_vertices=[(x,y,z) for x,z in inset_profile for y in (-.5+skin,.5-skin)]
  assert len(shape['vertices'])==12 and len(shape['planes'])==8
  assert all(min(math.dist(v,p) for p in shape['vertices'])<1e-5 for v in expected_vertices)
  expected_planes=[(0,-1,0,-.5+skin),(0,1,0,-.5+skin)]
  support_planes=[(0,-1,0,-.5),(0,1,0,-.5)]
  for polygon,destination in ((inset_profile,expected_planes),(profile,support_planes)):
   for a,b in zip(polygon,polygon[1:]+polygon[:1]):
    dx,dz=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dz)
    nx,nz=dz/length,-dx/length
    destination.append((nx,0,nz,-nx*a[0]-nz*a[1]))
  remaining=list(shape['planes'])
  for expected in expected_planes:
   plane=min(remaining,key=lambda p:math.dist(p,expected));remaining.remove(plane)
   assert math.dist(plane,expected)<1e-5
   assert max(sum(a*b for a,b in zip(plane,v))+plane[3] for v in shape['vertices'])<1e-5
  triangles=actual_triangles(row);vertices=triangles.reshape(-1,3);support_errors=[]
  for plane in support_planes:
   error=float((vertices@np.asarray(plane[:3])+plane[3]).max());assert abs(error)<.0002
   support_errors.append(error)
  # Independent role table: the two sloped ends require height-dependent X,
  # while center/front/back anchors keep the source construction-axis roles.
  expected=[(0,.5,0),(5.5,-.5,-3),(-7.4,0,0),(0,.5,3),(-4.4,.5,3),
            (-9.6,.5,-3),(0,.5,-3),(8.5,0,0),(9,-.5,3),(5.5,.5,-3),
            (-4.4,-.5,3),(-9.6,-.5,-3),(0,-.5,-3),(9,.5,3),(0,-.5,0),(0,-.5,3)]
  assert len(original)==len(expected)==16
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,target) in enumerate(zip(original,mapped,expected)):
   assert math.dist(after['position'],target)<1e-6
   constraints=[j for j,p in enumerate(support_planes) if abs(sum(a*b for a,b in zip(p,target))+p[3])<1e-6]
   assert constraints and all(sum(a*b for a,b in zip(p,target))+p[3]<1e-6 for p in support_planes)
   angle=math.pi/4 if i in (2,4,7,9,10) else 0;c,s=math.cos(angle),math.sin(angle)
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):
    assert math.dist((c*old[0]+s*old[2],old[1],-s*old[0]+c*old[2]),new)<1e-6
   assert abs(sum(v*v for v in after['rotation'])-1)<1e-5
   evidence.append(dict(index=i,position=after['position'],construction_planes=constraints,frame_y_rotation_degrees=math.degrees(angle)))
  result.update(status='verified',reason='Complete twelve-vertex/eight-plane extruded profile, every support plane independently matches actual render geometry, all sixteen original marker roles mapped to the target perimeter and five side frames rotated onto the slopes',
                anchors=evidence,contact_spacing=[18.6,1,6],render_support_residuals=support_errors,
                native_fixed_release=False,collision_core_vertex_inset=skin,raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label'] in ('Bank, 1x1','Bank, 1x2','Bank, 2x1','Bank, 2x2'):
  size=row['label'].split(' ')[1];width,height=map(int,size.split('x'))
  name='fw_unsc_c_bank_'+size
  bank_source_bounds,original,bank_source_shape=source_geometry(name)
  g=geometry[row['map'],row['palette_index']]
  assert len(g['nodes'])==1 and g['nodes'][0]['parent']==-1
  assert g['nodes'][0]['position']==[0,0,0] and g['nodes'][0]['rotation']==[0,0,0,1]
  assert g['nodes'][0]['inverse_basis']==[1,0,0,0,1,0,0,0,1] and g['nodes'][0]['inverse_scale']==1
  assert g['bodies']==[dict(node=0,motion_type=5,shape_type=4,shape_index=0)]
  assert len(g['polyhedra'])==1
  shape=g['polyhedra'][0];skin=2*shape['radius']
  assert len(shape['vertices'])==4 and len(shape['planes'])==4
  # The converter inset these tetrahedron VERTICES along their AABB axes,
  # rather than translating every face plane uniformly. Account for that
  # explicitly: the inset diagonal's normal differs from the nominal one.
  corners=[(-width,0,-.5),(0,height,-.5),(0,0,-.5),(0,0,.5)]
  nominal_bounds=[min(p[i] for p in corners) if side==0 else max(p[i] for p in corners)
                  for i in range(3) for side in (0,1)]
  inset_corners=[tuple(v+(skin if v==nominal_bounds[2*i] else -skin) for i,v in enumerate(p)) for p in corners]
  for expected_vertex in inset_corners:
   assert min(math.dist(expected_vertex,p) for p in shape['vertices'])<1e-5
  expected_normals=[(1,0,0),(0,-1,0),(0,0,-1)]
  slope=(-1/(width-2*skin),1/(height-2*skin),1/(1-2*skin));length=math.sqrt(sum(x*x for x in slope))
  expected_normals.append(tuple(x/length for x in slope))
  remaining=list(shape['planes'])
  for normal in expected_normals:
   plane=min(remaining,key=lambda p:math.dist(p[:3],normal));remaining.remove(plane)
   assert math.dist(plane[:3],normal)<1e-5
   support=max(sum(n*v for n,v in zip(normal,corner)) for corner in inset_corners)
   assert abs(-plane[3]-support)<1e-5
   assert max(sum(n*v for n,v in zip(plane,point))+plane[3] for point in shape['vertices'])<1e-5
  assert len(g['compression_bounds'])==1
  assert max(abs(a-b) for a,b in zip(nominal_bounds,g['compression_bounds'][0]))<1e-5
  targets={'1x1':[(-.5,.5,-.5),(-.5,0,-.5),(0,.5,-.5)],
           '1x2':[(0,1,-.5),(-.5,1,-.5),(-.5,0,-.5)],
           '2x1':[(-1,0,-.5),(0,.5,-.5),(-1,.5,-.5)],
           '2x2':[(-1,0,-.5),(0,1,-.5),(-1,1,-.5)]}[size]
  assert len(original)==len(targets)==3
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,expected) in enumerate(zip(original,mapped,targets)):
   residual=math.dist(after['position'],expected);assert residual<1e-6
   before_axes=rotation_axes(before['rotation']);after_axes=rotation_axes(after['rotation'])
   for axis,(before_axis,after_axis) in enumerate(zip(before_axes,after_axes)):
    expected_axis=tuple(v*(-1 if i==1 else 1)*(-1 if axis==1 else 1)
                        for i,v in enumerate(before_axis)) if size=='2x1' else before_axis
    assert math.dist(expected_axis,after_axis)<1e-6
   evidence.append(dict(index=i,position=after['position'],expected_edge_midpoint=expected,residual=residual,
                        unadapted_residual=math.dist(before['position'],expected)))
  result.update(status='verified',reason='All three anchors: identity node/body, four target convex planes, render envelope and exact triangular base-edge midpoints; authored marker frames transformed by the reviewed reflection/translation',
                anchors=evidence,contact_spacing=[width,height,1],collision_core_vertex_inset=skin,
                raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label'] in ('Ramp, 1x2','Ramp, 1x2, Shallow'):
  shallow=row['label'].endswith('Shallow');height=.5 if shallow else 1.
  name='fw_unsc_c_ramp_1x2'+('_shallow' if shallow else '')
  _,_,original=source_markers(name);g=geometry[row['map'],row['palette_index']]
  assert len(g['nodes'])==1 and g['nodes'][0]['parent']==-1
  node=g['nodes'][0]
  assert node['position']==[0,0,0] and node['rotation']==[0,0,0,1]
  assert node['inverse_basis']==[1,0,0,0,1,0,0,0,1] and node['inverse_scale']==1 and node['inverse_position']==[0,0,0]
  assert g['bodies']==[dict(node=0,motion_type=5,shape_type=4,shape_index=0)] and len(g['polyhedra'])==1
  shape=g['polyhedra'][0];skin=shape['radius']
  corners=[(x,y,z) for x,z in ((-1,0),(1,0),(1,height)) for y in (-.5,.5)]
  limits=[(-1,1),(-.5,.5),(0,height)]
  inset=[tuple(v+(skin if v==limits[i][0] else -skin) for i,v in enumerate(p)) for p in corners]
  assert len(shape['vertices'])==6 and len(shape['planes'])==5
  assert all(min(math.dist(c,p) for p in shape['vertices'])<1e-5 for c in inset)
  slope=(-(height-2*skin)/(2-2*skin),0,1);length=math.sqrt(sum(v*v for v in slope))
  normals=[(1,0,0),(0,1,0),(0,-1,0),(0,0,-1),tuple(v/length for v in slope)]
  remaining=list(shape['planes'])
  for normal in normals:
   plane=min(remaining,key=lambda p:math.dist(p[:3],normal));remaining.remove(plane)
   assert math.dist(plane[:3],normal)<1e-5
   assert abs(-plane[3]-max(sum(n*v for n,v in zip(normal,p)) for p in inset))<1e-5
  expected=[(-1,0,0),(1,0,0),(1,0,height)]
  frame=frames.get(name,dict(yaw_degrees=0,translation=[0,0,0]));mapped=[adapt(p,frame) for p in original]
  assert len(mapped)==3
  remaining=list(expected);triangles=actual_triangles(row);evidence=[]
  for i,(before,after) in enumerate(zip(original,mapped)):
   nearest=min(remaining,key=lambda p:math.dist(p,after['position']));remaining.remove(nearest)
   assert math.dist(nearest,after['position'])<1e-6
   # Beveled tips need not contain the mathematical construction corner.
   # Establish both support planes independently from referenced vertices;
   # the full convex-core proof above establishes their wedge relationship.
   residual=triangle_distance(nearest,triangles)
   x_support=float(triangles[:,:,0].min() if nearest[0]<0 else triangles[:,:,0].max())
   z_support=float(triangles[:,:,2].max() if nearest[2]>0 else triangles[:,:,2].min())
   assert abs(x_support-nearest[0])<.0004 and abs(z_support-nearest[2])<.0004
   assert math.dist(before['rotation'],after['rotation'])<1e-6
   forward=rotation_axes(after['rotation'])[0]
   assert math.dist(forward,(-1 if nearest[0]<0 else 1,0,0))<1e-6
   evidence.append(dict(index=i,position=after['position'],nearest_render_surface_distance=residual,
                        construction_support_residual=[abs(x_support-nearest[0]),abs(z_support-nearest[2])]))
  result.update(status='verified',reason='Complete six-vertex/five-plane wedge, identity node/body, all three ramp endpoints at intersections of measured construction support planes (including beveled tips), correctly outward authored frames',
                anchors=evidence,contact_spacing=[2,1,height],collision_core_vertex_inset=skin,
                raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label'] in ('Bridge, 2x1','Bridge, 2x2','Bridge, 2x3','Bridge, 2x5'):
  size=row['label'].split(' ')[1];name='fw_unsc_c_bridge_'+size
  _,_,original=source_markers(name);assert len(original)==4
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g)
  assert len(g['polyhedra'])==3
  half,deck={'2x1':(.5,-.00237),'2x2':(1,-.00237),'2x3':(1.49945,0),'2x5':(2.5,0)}[size]
  triangles=actual_triangles(row);rendered=all_render_rows[row['map'],row['palette_index']]
  assert max(abs(rendered['referenced_bounds'][0][i]-value) for i,value in enumerate((-half,half)))<.00001
  assert any(abs(p['coordinate']-deck)<.00001 and p['area']>2*half for p in rendered['axis_planes'][2])
  cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);length=np.linalg.norm(cross,axis=1)
  end_triangles=triangles[np.abs(cross[:,0]/length)>1-1e-6]
  mapped=[adapt(p,frames[name]) for p in original];midpoint=(min(p['position'][2] for p in original)+max(p['position'][2] for p in original))/2
  evidence=[];roles=[]
  for i,(before,after) in enumerate(zip(original,mapped)):
   side=-1 if before['position'][0]<0 else 1;tier=0 if before['position'][2]>midpoint else 1
   expected=(side*half,0,deck-.15*tier);roles.append((side,tier))
   assert math.dist(after['position'],expected)<1e-6
   residual=triangle_distance(expected,end_triangles);assert residual<.0001
   assert math.dist(rotation_axes(after['rotation'])[0],(side,0,0))<1e-6
   assert math.dist(before['rotation'],after['rotation'])<1e-6
   evidence.append(dict(index=i,position=after['position'],side=side,tier=tier,
                        matching_end_face_residual=residual,height_relative_to_deck=-.15*tier))
  assert set(roles)==set(itertools.product((-1,1),(0,1)))
  # For any two bridge types, equal-role anchor coincidence implies equal
  # deck heights: worldDeckA-.15*tier = worldDeckB-.15*tier. The shared
  # tier offset cancels, so this proof does not enumerate bridge pairs.
  result.update(status='verified',reason='All three compound leaves resolved; four source end-face roles lie on actual target end triangles with outward frames; measured deck plane and common tier offsets prove equal-role deck alignment across bridge lengths',
                anchors=evidence,compound=compound,contact_spacing=[2*half,2,.15],deck_plane=deck,
                raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Dish Antenna':
  name='fw_unsc_c_dish_antenna';_,_,original=source_markers(name)
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g,body_node=1)
  assert len(g['nodes'])==2 and len(g['polyhedra'])==18 and len(original)==12
  assert g['animation']=='0xffffffff','Rigid-child proof requires a static model'
  transform=np.asarray(compound['body_to_object'])
  expected_transform=np.array([[0,-1,0,0],[1,0,0,0],[0,0,1,0],[0,0,0,1]])
  assert np.max(np.abs(transform-expected_transform))<1e-6
  rendered=all_render_rows[row['map'],row['palette_index']]
  assert all(m['node']==1 for m in rendered['meshes'])
  triangles=actual_triangles(row);mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after) in enumerate(zip(original,mapped)):
   p=after['position'];radius=math.hypot(p[0],p[1]);direction=np.array([p[0]/radius,p[1]/radius,0])
   assert abs(p[2]-before['position'][2])<1e-7
   hits=ray_hits((0,0,p[2]),direction,triangles)
   if i in (0,1,2):
    assert len(hits)==3;contact=hits[1];role='middle cap ring'
   elif i in (3,6,9):
    assert len(hits)>=3;contact=hits[-1];role='outer upper stem'
   elif i in (4,7,10):
    assert len(hits)==2;contact=hits[-1];role='outer foot'
   else:
    assert len(hits)==2;contact=hits[0];role='inner collar'
   residual=abs(radius-contact);assert residual<.0002,(i,role,radius,hits)
   assert triangle_distance(p,triangles)<.0002
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):
    assert math.dist(old,new)<1e-6
   sign=-1 if i in (5,8,11) else 1
   assert math.dist(rotation_axes(after['rotation'])[0],direction*sign)<1e-5
   evidence.append(dict(index=i,position=p,radial_role=role,ordered_ray_intersections=hits,
                        contact_radius_residual=residual,preserved_source_height=p[2]))
  for group in ((0,1,2),(3,6,9),(4,7,10),(5,8,11)):
   radii=[math.hypot(*mapped[i]['position'][:2]) for i in group];assert max(radii)-min(radii)<1e-7
   directions=[np.asarray(mapped[i]['position'][:2])/radii[j] for j,i in enumerate(group)]
   assert all(abs(float(a@b)+.5)<1e-5 for a,b in itertools.combinations(directions,2))
  # Independent object-space extent check catches applying the child rotation
  # twice: raw physics is node-local while render vertices already use bind
  # object space. Only physics is rotated by the +90-degree child transform.
  physics_vertices=np.array([v for shape in g['polyhedra'] for v in shape['vertices']])
  physics_world=physics_vertices@transform[:3,:3].T+transform[:3,3]
  rendered_bounds=np.array(rendered['referenced_bounds'])
  physics_bounds=np.c_[physics_world.min(axis=0),physics_world.max(axis=0)]
  assert np.max(np.abs(physics_bounds-rendered_bounds))<.04
  result.update(status='verified',reason='Both rigid nodes and inverse binds resolved; node-local collision rotated into object space agrees with the already-object-space render envelope; all twelve original angular/height roles map to corresponding ordered radial mesh intersections with authored radial orientations unchanged',
                anchors=evidence,compound=compound,contact_spacing=[2*v['target_radius'] for v in frames[name]['radial_profile']['levels']],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Staircase':
  name='fw_unsc_c_stair_case';_,_,original=source_markers(name)
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g)
  assert len(g['polyhedra'])==16 and len(original)==4
  triangles=actual_triangles(row);frame=frames[name];mapped=[adapt(p,frame) for p in original]
  expected=[(4.000133037567139,-.75,-1),(4.000133037567139,1.75,1.5003771543502808),
            (2.4,3,1.5003771543502808),(2.3,.5,1.5003771543502808)]
  forward=[(1,0,0),(1,0,0),(0,1,0),(0,-1,0)];evidence=[]
  for i,(before,after,target,normal) in enumerate(zip(original,mapped,expected,forward)):
   assert math.dist(after['position'],target)<.0002
   residual=triangle_distance(after['position'],triangles);assert residual<.0002
   assert math.dist(rotation_axes(after['rotation'])[0],normal)<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):
    assert math.dist((-old[0],-old[1],old[2]),new)<1e-6
   # Require a local face perpendicular to the intended outward frame, not
   # merely proximity to some unrelated part of the staircase.
   cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);length=np.linalg.norm(cross,axis=1)
   selected=np.abs(cross@np.asarray(normal)/length)>1-1e-6
   face_residual=triangle_distance(after['position'],triangles[selected]);assert face_residual<.0002
   evidence.append(dict(index=i,position=after['position'],expected_construction_point=target,
                        matching_face_residual=face_residual,outward_normal=normal))
  # Independent mesh planes establish the widened parallel lanes and two
  # entrance levels. H4 anchors on Y=-1.7/.3 map to Y=3/.5 after 180deg,
  # giving the measured 1.25 cross-lane scale and the +.875 origin.
  rendered=all_render_rows[row['map'],row['palette_index']]
  for axis,coordinate in [(0,4.000133037567139),(1,3),(1,.5),(1,-2),(2,-1),(2,1.5003771543502808)]:
   assert any(abs(p['coordinate']-coordinate)<.0002 and p['area']>.1 for p in rendered['axis_planes'][axis]),(axis,coordinate)
  result.update(status='verified',reason='Resolved all sixteen compound leaves; four original entrance/edge roles map onto actual target faces with matching outward frames; lane widening, rotation and floor origins independently supported by rendered planes',
                anchors=evidence,compound=compound,contact_spacing=[7,5,3.5],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Base Round':
  name='fw_unsc_c_base_round';_,source_bounds,original=source_markers(name);assert len(original)==10
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==49
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);bounds=np.c_[mesh.min(axis=0),mesh.max(axis=0)]
  assert np.max(np.abs(bounds[:2]-[[-5.5,5.5],[-5.5,0]]))<.000004
  assert abs(bounds[2,0]+1)<1e-6 and abs(source_bounds[4]+.9)<1e-6
  assert max(abs(source_bounds[0]+6),abs(source_bounds[1]-6))<.000004
  frame=frames[name];assert abs(frame['horizontal_scale']-11/12)<1e-12
  assert frame['yaw_degrees']==180 and math.dist(frame['translation'],(0,-3.25*11/12,-.1))<1e-12
  expected=[(0,0,0),(0,-1.2763764,1.6),(0,-5.5,-.2),(11/8,0,0),(-11/8,0,0),
            (-11/6,-.491526,1.6),(11/6,-.491526,1.6),(0,-5.002928,1.6),
            (-5.5,-.491526,-.2),(5.5,-.491526,-.2)]
  forwards=[(0,1,0),(0,1,0),(0,-1,0),(0,1,0),(0,1,0),(1,0,0),(-1,0,0),(0,-1,0),(-1,0,0),(1,0,0)]
  mapped=[adapt(p,frame) for p in original];evidence=[]
  for i,(before,after,target,forward) in enumerate(zip(original,mapped,expected,forwards)):
   assert math.dist(after['position'],target)<1e-7
   assert math.dist(rotation_axes(after['rotation'])[0],forward)<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):
    assert math.dist((-old[0],-old[1],old[2]),new)<1e-6
   residual=triangle_distance(target,triangles);assert residual<.012
   detail={}
   if i in (0,3,4):
    assert abs(before['position'][1]+3.25)<.0001 and abs(before['position'][2]-.1)<.000002
    # Front floor/flat support intersection. The small mesh bevel is inset
    # from that construction edge; an interior ray proves the adjacent floor.
    heights=[4-h for h in ray_hits((target[0],-.02,4),(0,0,-1),triangles)]
    assert min(abs(z) for z in heights)<.00002
    assert np.max(mesh[:,1])<1e-7
    detail=dict(role='flat front floor',floor_intersections=heights,front_plane=0)
   elif i in (1,5,6,7):
    assert abs(before['position'][2]-1.7)<.000002 and residual<.00004
    cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);normals=cross/np.linalg.norm(cross,axis=1)[:,None]
    roof=(np.abs(normals[:,2])>1-1e-5)&(np.max(np.abs(triangles[:,:,2]-1.6),axis=1)<.0001)
    assert triangle_distance(target,triangles[roof])<.00004
    detail=dict(role='roof',roof_plane=1.6)
   else:
    assert abs(before['position'][2]+.1)<.000004
    # Back ledge has a slight inward slope; side ledges are flat. Establish
    # the local deck by three interior intersections and extend its measured
    # plane through the small edge bevel to the outer construction support.
    axis=1 if i==2 else 0;coordinates=[];heights=[]
    sign=1 if target[axis]>0 else -1
    for inset in (.02,.05,.1):
     point=list(target);point[axis]-=sign*inset;point[2]=4
     hits=ray_hits(point,(0,0,-1),triangles);assert hits
     coordinates.append(point[axis]);heights.append(4-hits[0])
    slope,intercept=np.polyfit(coordinates,heights,1)
    assert np.max(np.abs(np.asarray(heights)-(slope*np.asarray(coordinates)+intercept)))<.000004
    edge_height=slope*target[axis]+intercept
    assert abs(edge_height+.2)<.0002
    if axis==0:assert abs(slope)<.00001
    else:assert .07<slope<.09
    detail=dict(role='outer ledge',support_axis=axis,support_coordinate=target[axis],
                interior_coordinates=coordinates,interior_heights=heights,extrapolated_edge_height=float(edge_height))
   evidence.append(dict(index=i,position=after['position'],authored_rotated_forward=forward,
                        surface_residual=residual,**detail))
  # For the reported disc joint, both complete meshes occupy opposite closed
  # half-spaces after a 180-degree turn about their common Y=0 seam. No piece
  # pair campaign is needed to establish the seam or unchanged floor heights.
  assert all(mapped[i]['position'][1]==0 and mapped[i]['position'][2]==0 for i in (0,3,4))
  result.update(status='verified',reason='All ten original roles proved: three exact front-floor supports, three outer ledge/deck intersections and four actual roof points; full node/body compound resolved; 11/12 construction-radius mapping and all rotated marker axes checked; front half-space seam follows algebraically',
                anchors=evidence,compound=compound,contact_spacing=[11,5.5,2.7],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Bridge Diag':
  name='fw_unsc_c_bridge_diag';_,_,original=source_markers(name);assert len(original)==2
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==9
  triangles=actual_triangles(row);cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
  normals=cross/np.linalg.norm(cross,axis=1)[:,None]
  mapped=[adapt(p,frames[name]) for p in original];targets=[(2.5,-1.5,0),(-1.5,2.5,0)]
  authored_forwards=[(1,0,0),(0,-1,0)];evidence=[]
  for i,(before,after,target,forward) in enumerate(zip(original,mapped,targets,authored_forwards)):
   axis=i;cross_axis=1-axis
   # Each actual end-cap spans -2.5..-0.5 across the bridge, independently
   # fixing its -1.5 entrance center. The cap includes both rails and deck.
   end=(np.abs(normals[:,axis])>1-1e-5)&(np.max(np.abs(triangles[:,:,axis]-2.5),axis=1)<.0001)
   vertices=triangles[end].reshape(-1,3);assert len(vertices)>0
   assert abs(vertices[:,cross_axis].min()+2.5)<.0001 and abs(vertices[:,cross_axis].max()+.5)<.0001
   assert math.dist(after['position'],target)<1e-7
   residual=triangle_distance(target,triangles);assert residual<.000003
   source=(2.6,-1.4) if i==0 else (-1.4,2.6)
   assert math.dist(before['position'][:2],source)<.008
   assert abs(before['position'][2]-.0053365)<.000003
   assert math.dist(rotation_axes(before['rotation'])[0],forward)<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   samples=[]
   for inset in (.001,.01,.1):
    point=list(target);point[axis]-=inset;point[2]=2
    heights=[2-h for h in ray_hits(point,(0,0,-1),triangles)]
    assert len(heights)==2 and abs(heights[0])<.000003 and abs(heights[1]+.2)<.000003
    samples.append(dict(inset=inset,top=heights[0],bottom=heights[1]))
   evidence.append(dict(index=i,position=after['position'],authored_forward=forward,
                        entrance_width=2,surface_residual=residual,deck_samples=samples))
  result.update(status='verified',reason='Both original entrance roles lie at independently proved end-cap centers on the actual zero-height deck; complete compound reference, two-unit widths, thickness, and all original marker axes verified',
                anchors=evidence,compound=compound,contact_spacing=[4,4,0],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Cover, 2':
  name='fw_unsc_c_cover_2';_,source_bounds,original=source_markers(name);assert len(original)==5
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g)
  assert len(g['polyhedra'])==13
  triangles=actual_triangles(row);rendered=all_render_rows[row['map'],row['palette_index']]
  bounds=np.asarray(rendered['referenced_bounds']);source_bounds=np.asarray(source_bounds).reshape(3,2)
  assert np.max(np.abs(bounds[0]-source_bounds[0]))<1e-6
  assert np.max(np.abs(bounds[2]-(source_bounds[2]-.1)))<1e-6
  assert np.max(np.abs(source_bounds[1]-[-2,2]))<1e-6
  assert np.max(np.abs(bounds[1]-[-2.0099923610687256,2.0099923610687256]))<1e-6
  for axis,coordinate,area in ((0,1.4,.3),(2,.9,.4),(1,bounds[1,0],.9),(1,bounds[1,1],.3)):
   assert any(abs(p['coordinate']-coordinate)<.00003 and p['area']>area for p in rendered['axis_planes'][axis])
  clearance=original[0]['position'][2]-1;assert abs(clearance+.007463932)<1e-7
  lateral=original[1]['position'][0]
  expected=[(1.4,0,.9+clearance),(lateral,bounds[1,1],.8+clearance),
            (lateral,bounds[1,0],.8+clearance),(-.4,1.85,-1+clearance),(-.4,-1.85,-1+clearance)]
  source_expected=[(1.4,0,1+clearance),(lateral,2,.9+clearance),(lateral,-2,.9+clearance),
                   (-.4,1.85,-.9+clearance),(-.4,-1.85,-.9+clearance)]
  forwards=[(1,0,0),(0,1,0),(0,-1,0),(1,0,0),(1,0,0)]
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);normals=cross/np.linalg.norm(cross,axis=1)[:,None]
  for i,(before,after,target,source,forward) in enumerate(zip(original,mapped,expected,source_expected,forwards)):
   assert math.dist(before['position'],source)<.00002 and math.dist(after['position'],target)<1e-7
   assert math.dist(rotation_axes(before['rotation'])[0],forward)<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   residual=triangle_distance(target,triangles);assert residual<(.0072 if i==0 else .0019 if i<3 else .00004)
   if i>=3:
    # Resolve each foot's front plane and Y center from its native core,
    # then require a matching actual mesh face at the anchor itself.
    shape=g['polyhedra'][5 if i==3 else 10];v=np.asarray(shape['vertices']);skin=2*shape['radius']
    assert abs(v[:,0].max()+skin-target[0])<1e-6
    assert abs((v[:,1].min()+v[:,1].max())/2-target[1])<.00002
    assert v[:,2].min()-skin<target[2]<v[:,2].max()+skin
    selected=np.abs(normals[:,0])>1-1e-6
    assert triangle_distance(target,triangles[selected])<.00004
   evidence.append(dict(index=i,position=after['position'],authored_forward=forward,
                        surface_residual=residual,preserved_vertical_clearance=clearance))
  result.update(status='verified',reason='All five original upper-beam/end/foot roles retain their shared vertical clearance and authored frames; model X/Z support planes prove the origin change; end faces and both foot centers/front planes are independently checked; complete compound reference resolved',
                anchors=evidence,compound=compound,contact_spacing=[2.5,float(bounds[1,1]-bounds[1,0]),1.9],
                raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label'] in ('Cylinder Small','Cylinder Big'):
  big=row['label']=='Cylinder Big';name='fw_unsc_c_cylinder_'+('big' if big else 'small')
  _,_,original=source_markers(name);assert len(original)==4
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==(16 if big else 14)
  triangles=actual_triangles(row);rendered=all_render_rows[row['map'],row['palette_index']]
  radius=3.1 if big else 1.79613;deck=2 if big else 1
  for axis in (0,1):
   for side in (-1,1):
    assert any(abs(p['coordinate']-side*radius)<.00008 and p['area']>1 for p in rendered['axis_planes'][axis])
  for level,area in ((deck,5),(deck+.3,1)):
   assert any(abs(p['coordinate']-level)<.00008 and p['area']>area for p in rendered['axis_planes'][2])
  # H4 Big has higher Y-side roles; Reach's raised rim is on X. Rotate
  # that distinction, rather than collapsing all markers to one height.
  source_positions=[(-3.0600009,0,1.78979993),(0,3.05999994,2.08979988),(3.0600009,0,1.78979993),(0,-3.05999994,2.08979988)] if big else [
   (0,-1.83483088,1.09578168),(0,1.83487248,1.09578168),(-1.83483219,.000020763,1.09578168),(1.83483195,.000020763,1.09578168)]
  roles=[(1,-1),(0,-1),(1,1),(0,1)] if big else [(1,-1),(1,1),(0,-1),(0,1)]
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,source,(axis,side)) in enumerate(zip(original,mapped,source_positions,roles)):
   assert math.dist(before['position'],source)<.000002
   target=np.array([0.,0.,deck+(.3 if big and axis==0 else 0)]);target[axis]=side*radius
   assert math.dist(after['position'],target)<1e-7
   normal=np.zeros(3);normal[axis]=side
   assert math.dist(rotation_axes(after['rotation'])[0],normal)<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):
    expected=(-old[1],old[0],old[2]) if big else old
    assert math.dist(expected,new)<1e-6
   # Independently probe the actual walking/rim surface inside the bevel.
   inside=target.copy();inside[axis]-=side*.05;inside[2]=4
   heights=[4-hit for hit in ray_hits(inside,(0,0,-1),triangles)]
   expected_height=deck+(.3 if axis==0 else 0)
   assert heights and abs(max(heights)-expected_height)<.00008
   residual=triangle_distance(target,triangles)
   if big:assert .028<residual<.0284
   elif axis==0:assert residual<.00006
   else:assert .0167<residual<.017
   evidence.append(dict(index=i,position=after['position'],outward_forward=normal.tolist(),
                        surface_residual=residual,inside_surface_heights=heights))
  assert set(roles)==set(itertools.product((0,1),(-1,1)))
  result.update(status='verified',reason='Four original cardinal roles and complete bases map to independently witnessed side planes and actual deck/rim heights; large cylinder rotates the raised pair onto X; every native compound leaf and measured bevel clearance checked',
                anchors=evidence,compound=compound,contact_spacing=[2*radius,2*radius,.3 if big else 0],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Walkway, Large':
  name='fw_unsc_c_walkway_small';_,source_bounds,original=source_markers(name);assert len(original)==3
  g=geometry[row['map'],row['palette_index']]
  compound=identity_compound(g,plane_exceptions={24:(5,),74:(5,)});assert len(g['polyhedra'])==91
  issues=compound['native_plane_inconsistencies'];assert len(issues)==2
  for issue,expected in zip(issues,(.00010814728699415355,.00010407927456412835)):
   assert len(issue['maximum_vertex_distances'])==1 and abs(issue['maximum_vertex_distances'][0]-expected)<1e-12
  tetrahedra=compound['partial_plane_tetrahedra'];assert len(tetrahedra)==1 and tetrahedra[0]['index']==33
  assert tetrahedra[0]['stored_planes']==2 and abs(tetrahedra[0]['volume']-.00046333985464560895)<1e-12
  native_vertices=np.vstack([s['vertices'] for s in g['polyhedra']]);skin=g['polyhedra'][0]['radius']
  assert all(s['radius']==skin for s in g['polyhedra'])
  native_bounds=np.c_[native_vertices.min(0)-skin,native_vertices.max(0)+skin]
  native_margin=np.maximum(np.array([-1,-7])-native_bounds[:2,0],native_bounds[:2,1]-np.array([1,7]))
  assert math.dist(native_margin,(.0046378578990698,.003885408863425))<1e-10 and abs(native_bounds[2,0])<1e-6
  triangles=actual_triangles(row);rendered=all_render_rows[row['map'],row['palette_index']]
  for axis,level,area,tolerance in ((0,-1,3.3,.00002),(0,1,3.3,.00002),(1,7,.55,.00011),(2,6,16,.00004)):
   assert any(abs(p['coordinate']-level)<tolerance and p['area']>area for p in rendered['axis_planes'][axis])
  sources=[(-1.1999993324279785,-.10000137239694595,5.799936771392822),
           (1.19993257522583,-.10000137239694595,5.799936771392822),
           (-.000032062533136922866,6.900000095367432,5.799924373626709)]
  targets=[(-1,0,6),(1,0,6),(0,7,6)];surface_normals=[(-1,0,0),(1,0,0),(0,1,0)]
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,source,target,normal) in enumerate(zip(original,mapped,sources,targets,surface_normals)):
   assert math.dist(before['position'],source)<1e-10 and math.dist(after['position'],target)<1e-10
   assert abs(before['position'][2]-source_bounds[4]-6)<.00002
   if i<2:assert abs(before['position'][1]-(source_bounds[2]+source_bounds[3])/2)<.000002
   else:assert abs(before['position'][1]-source_bounds[3])<1e-10
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   assert math.dist(rotation_axes(after['rotation'])[0],(1,0,0))<1e-6
   residual=triangle_distance(target,triangles);assert .0703<residual<.0704 if i<2 else residual<.0001
   evidence.append(dict(index=i,position=after['position'],authored_forward=[1,0,0],surface_normal=normal,surface_residual=residual))
  center_heights=[7-h for h in ray_hits((0,0,7),(0,0,-1),triangles)]
  assert len(center_heights)==2 and abs(max(center_heights)-6)<.00003 and abs(min(center_heights))<1e-6
  side_crossings=[-2+h for h in ray_hits((-2,0,5.8),(1,0,0),triangles)]
  assert len(side_crossings)==2 and math.dist(side_crossings,(-1,1))<.000102
  # Independently witness the slope of the existing .1-unit top-edge bevel.
  bevel_crossings=[-2+h for h in ray_hits((-2,0,5.95),(1,0,0),triangles)]
  assert abs(min(bevel_crossings)+.9505132052216372)<1e-10 and abs(max(bevel_crossings)-.9505121323380314)<1e-10
  end_hits=ray_hits((0,7.1,6),(0,-1,0),triangles);assert end_hits and abs(min(end_hits)-.1)<.00011
  result.update(status='verified',reason='All three original high side/end references and complete authored +X bases checked against six-unit source-relative height, actual target deck/side/end planes, native bounds and independent center/side/end sections; complete 91-leaf graph resolved with two recorded native plane residuals and the two-plane leaf proven as a full vertex tetrahedron',
                anchors=evidence,compound=compound,contact_spacing=[2,7,6],native_bounds=native_bounds.tolist(),native_xy_overhang=native_margin.tolist(),
                center_surface_heights=center_heights,raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Bunker Stair':
  from bunker_stair_geometry import references
  import zlib
  name='fw_unsc_c_bunker_stair';source_bounds,original,source_shapes=source_geometry(name,compound=True)
  assert len(original)==11 and len(source_shapes)==38
  source_report=json.loads((OUT/'source-render'/f'{name}.json').read_text())
  assert source_report['cache_sha256']==hashlib.sha256(data).hexdigest()
  assert source_report['tag_index']==models[name]['tag_index'] and source_report['triangles']==2821
  source_path=ROOT/source_report['triangle_file']
  assert hashlib.sha256(source_path.read_bytes()).hexdigest()==source_report['triangle_sha256']
  for page in source_report['pages']:
   raw=(OUT/'source-render/pages'/f"{page['page']}.bin").read_bytes()
   assert len(raw)==page['bytes'] and zlib.crc32(raw)^0xffffffff==int(page['crc'],16)
   assert hashlib.sha256(raw).hexdigest()==page['sha256']
  with np.load(source_path) as loaded:source_triangles=loaded['triangles']
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g)
  assert len(g['polyhedra'])==25
  triangles=actual_triangles(row);targets,feature_evidence=references(source_triangles,triangles,original,ray_hits)
  # Establish the shared left stair center and front/rear inner-wall junction.
  left_source=np.array(source_shapes[15]['vertices']);left_target=np.array(g['polyhedra'][2]['vertices'])
  assert abs(original[0]['position'][1]-(left_source[:,1].min()+left_source[:,1].max())/2)<.01
  assert abs(targets[0][1]-(left_target[:,1].min()+left_target[:,1].max())/2)<.00001
  source_junction=np.array(source_shapes[36]['vertices'])[:,0].min()-source_shapes[36]['radius']
  target_junction=np.array(g['polyhedra'][23]['vertices'])[:,0].min()-2*g['polyhedra'][23]['radius']
  assert all(abs(original[i]['position'][0]-source_junction)<.006 for i in (2,4,5,10))
  assert abs(targets[2][0]-target_junction)<.00001
  assert all(abs(original[i]['position'][2]-source_bounds[4])<.002 for i in (1,2,4))
  assert max(original[i]['position'][2] for i in (3,5,6,9))-min(original[i]['position'][2] for i in (3,5,6,9))<.00012
  assert abs(original[10]['position'][2]-original[3]['position'][2]-.3)<.0002
  # The eighth-index marker is intentionally a construction reference in
  # empty space: it extends the actual wall foot beneath the raised stair.
  assert original[7]['position'][::2]==original[8]['position'][::2]
  assert original[8]['position'][1]==original[9]['position'][1]
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,target) in enumerate(zip(original,mapped,targets)):
   assert math.dist(after['position'],target)<1e-10
   source_residual=triangle_distance(before['position'],source_triangles)
   residual=triangle_distance(target,triangles)
   if i==8:
    assert .47<source_residual<.49 and .5<residual<.7
    assert target[::2]==targets[7][::2] and target[1]==targets[9][1]
   else:assert source_residual<.005 and residual<.0001
   axis,sign=(0,-1) if i in (0,1,3) else (1,-1) if i in (2,10) else (1,1) if i in (4,5) else (0,1)
   assert math.dist(rotation_axes(before['rotation'])[0],tuple(sign if j==axis else 0 for j in range(3)))<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   evidence.append(dict(index=i,position=after['position'],source_surface_residual=source_residual,
                        target_surface_residual=residual,virtual_foot_reference=i==8))
  result.update(status='verified',reason='Eleven construction roles transferred to the stair entrance, base, roof, inner-wall junction and beveled foot; authored side-wall/stair fractions and the virtual under-stair foot extension preserved. Ten surface references lie within target mesh quantum; original complete frames and all 25 native leaves retained',
                anchors=evidence,compound=compound,features=feature_evidence,source_render=source_report,
                contact_spacing=[4.7,5,3],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Room Triple':
  name='fw_unsc_c_room_triple';source_bounds,original,source_shapes=source_geometry(name,compound=True)
  assert len(original)==6 and len(source_shapes)==112
  g=geometry[row['map'],row['palette_index']]
  compound=identity_compound(g,planar_face_exceptions={52:1.1831422684238646e-5})
  assert len(g['polyhedra'])==92 and len(compound['planar_polygons'])==2
  triangles=actual_triangles(row);rendered=all_render_rows[row['map'],row['palette_index']]
  planes=[]
  for axis,low,high in ((1,2.44,2.46),(1,-1.96,-1.94),(0,-5.11,-5.09),(0,5.09,5.11)):
   p=max((p for p in rendered['axis_planes'][axis] if low<p['coordinate']<high),key=lambda p:p['area'])
   faces=triangles[np.max(abs(triangles[:,:,axis]-p['coordinate']),axis=1)<.00001]
   assert len(faces)>4 and np.ptp(faces[:,:,axis])<1e-8
   planes.append((axis,float(faces[:,:,axis].mean())))
  sets=[];sections=[]
  for axis,plane in planes:
   sign=1 if plane>0 else -1;lateral=1-axis
   origin=np.zeros(3);origin[axis]=plane-sign*.01;origin[lateral]=-7
   direction=np.zeros(3);direction[lateral]=1;hits=[-7+h for h in ray_hits(origin,direction,triangles)]
   assert len(hits)%2==0
   refs=[];rejected=[]
   for a,b in zip(hits[1::2],hits[2::2]):
    if b-a<.6:continue
    point=np.zeros(3);point[axis]=plane;point[lateral]=(a+b)/2
    outside=point.copy();outside[axis]+=sign*.1;inward=np.zeros(3);inward[axis]=-sign
    entries=ray_hits(outside,inward,triangles)
    if entries and min(entries)<.3:
     rejected.append(dict(gap=[a,b],reason='blocked',first_hit=min(entries)));continue
    if axis==1:
     above=point.copy();above[2]=3;heights=sorted(3-h for h in ray_hits(above,(0,0,-1),triangles))
     floor=[h for h in heights if -.61<h<-.49]
     if not floor:
      rejected.append(dict(gap=[a,b],reason='no_floor'));continue
     assert len(floor)==1;point[2]=floor[0]
    else:
     # Exact lateral section of the horizontal floor faces locates the lip
     # before its bevel, rather than assuming the main wall is the floor edge.
     faces=triangles[(np.ptp(triangles[:,:,2],axis=1)<1e-7)&(triangles[:,:,2].min(axis=1)>-.61)&(triangles[:,:,2].max(axis=1)<-.59)]
     ends=[]
     for tri in faces:
      cut=[]
      for start,end in zip(tri,np.roll(tri,-1,axis=0)):
       if abs(end[1]-start[1])<1e-12:continue
       fraction=(point[1]-start[1])/(end[1]-start[1])
       if 0<=fraction<=1:cut.append(start+fraction*(end-start))
      if len(cut)>1:ends.extend(cut)
     assert ends
     point=max(ends,key=lambda p:sign*p[0]);assert .2<sign*(plane-point[0])<.25
     above=point.copy();above[2]=3;heights=sorted(3-h for h in ray_hits(above,(0,0,-1),triangles))
    assert triangle_distance(point,triangles)<1e-10
    refs.append(dict(position=point.tolist(),gap=[a,b],local_heights=heights,first_inward_hit=min(entries) if entries else None))
   sets.append(refs);sections.append(dict(axis=axis,plane=plane,intersections=hits,rejected=rejected))
  assert list(map(len,sets))==[3,1,1,1]
  refs=[sets[1][0],sets[2][0],sets[0][0],sets[0][1],sets[0][2],sets[3][0]]
  assert len(sections[0]['rejected'])==2 and all(r['reason']=='no_floor' for r in sections[0]['rejected'])
  def source_intervals(axis,plane):
   lateral=1-axis;origin=np.zeros(3);origin[axis]=plane;intervals=[]
   for shape in source_shapes:
    planes=np.array(shape['planes']);value=planes[:,:3]@origin+planes[:,3]-shape['radius'];slope=planes[:,lateral]
    if np.any(value[abs(slope)<1e-8]>0):continue
    lo=max((-a/b for a,b in zip(value,slope) if b< -1e-8),default=-100)
    hi=min((-a/b for a,b in zip(value,slope) if b>1e-8),default=100)
    if lo<=hi:intervals.append([lo,hi])
   merged=[]
   for lo,hi in sorted(intervals):
    if merged and lo<=merged[-1][1]+.001:merged[-1][1]=max(merged[-1][1],hi)
    else:merged.append([lo,hi])
   return merged
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,reference,shape_index) in enumerate(zip(original,mapped,refs,(79,65,31,104,12,15))):
   axis=0 if i in (1,5) else 1;sign=-1 if i in (0,1) else 1;point=np.array(before['position'])
   intervals=source_intervals(axis,point[axis]-sign*.05)
   gaps=[[a[1],b[0]] for a,b in zip(intervals,intervals[1:]) if a[1]<point[1-axis]<b[0]]
   assert len(gaps)==1 and gaps[0][1]-gaps[0][0]>.9 and abs(point[1-axis]-sum(gaps[0])/2)<.025
   shape=source_shapes[shape_index];vertices=np.array(shape['vertices']);planes=np.array(shape['planes']);radius=shape['radius']
   floor_top=float(vertices[:,2].max()+radius)
   edge=float(vertices[:,axis].max()+radius if sign>0 else vertices[:,axis].min()-radius)
   source_residual=float(np.max(planes[:,:3]@point+planes[:,3]-radius))
   assert source_residual<.005 and abs(point[2]-floor_top)<.025 and abs(point[axis]-edge)<.025
   assert math.dist(after['position'],reference['position'])<1e-10
   assert math.dist(rotation_axes(before['rotation'])[0],tuple(sign if j==axis else 0 for j in range(3)))<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   assert abs(sum(q*q for q in after['rotation'])-1)<1e-6
   residual=triangle_distance(after['position'],triangles);assert residual<1e-10
   evidence.append(dict(index=i,position=after['position'],source_floor_shape=shape_index,source_floor_top=floor_top,
       source_edge=edge,source_support_residual=source_residual,source_opening=gaps[0],
       target_opening=reference['gap'],target_local_heights=reference['local_heights'],surface_residual=residual))
  assert abs(mapped[0]['position'][2]-mapped[3]['position'][2])<1e-10
  assert abs(mapped[2]['position'][2]-mapped[4]['position'][2])<1e-10
  assert abs(mapped[1]['position'][2]-mapped[5]['position'][2])<1e-10
  assert .1000<mapped[0]['position'][2]-mapped[2]['position'][2]<.1001
  assert .0009<mapped[2]['position'][2]-mapped[1]['position'][2]<.0010
  assert abs((mapped[1]['position'][0]+mapped[5]['position'][0])/2-mapped[0]['position'][0])<1e-10
  result.update(status='verified',reason='All six source entrance roles identified by convex aperture sections and native floor caps; actual target wall sections locate clear openings, floor rays reject decorative gaps, and exact horizontal floor sections locate the recessed side lips. Three distinct native threshold levels and all complete original frames preserved; all 92 native leaves resolved with the specific existing planar-face residual recorded',
                anchors=evidence,compound=compound,target_apertures=sections,
                contact_spacing=[mapped[5]['position'][0]-mapped[1]['position'][0],mapped[3]['position'][1]-mapped[0]['position'][1]],
                raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Tower':
  name='fw_unsc_c_tower';source_bounds,original,source_shapes=source_geometry(name,compound=True)
  assert len(original)==5 and len(source_shapes)==59
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==59
  triangles=actual_triangles(row);rendered=all_render_rows[row['map'],row['palette_index']]
  floor_sets=[]
  for low,high in ((.39,.41),(2.39,2.41)):
   principal=max((p for p in rendered['axis_planes'][2] if low<p['coordinate']<high),key=lambda p:p['area'])
   faces=triangles[np.max(abs(triangles[:,:,2]-principal['coordinate']),axis=1)<.00001]
   assert len(faces)>4;floor_sets.append(faces.reshape(-1,3))
  ground,upper=floor_sets
  specs=[(1,float(ground[:,1].max()),.8),(0,float(ground[:,0].min()),.8),
         (1,float(ground[:,1].min()),.8),(0,float(upper[:,0].min()),2.6)]
  reference_sets=[];apertures=[]
  for axis,plane,z in specs:
   sign=1 if plane>0 else -1;lateral=1-axis
   origin=np.zeros(3);origin[axis]=plane-sign*.05;origin[lateral]=-3;origin[2]=z
   direction=np.zeros(3);direction[lateral]=1;hits=[-3+h for h in ray_hits(origin,direction,triangles)]
   assert len(hits)%2==0 and len(hits)>=4
   candidates=[];rejected=[]
   for a,b in zip(hits[1::2],hits[2::2]):
    if b-a<=.5:continue
    point=np.zeros(3);point[axis]=plane;point[lateral]=(a+b)/2;point[2]=z
    outside=point.copy();outside[axis]+=sign*.1;inward=np.zeros(3);inward[axis]=-sign
    entries=ray_hits(outside,inward,triangles)
    if entries and min(entries)<.3:
     rejected.append(dict(gap=[a,b],first_hit=min(entries)));continue
    point[2]=5;heights=sorted(5-h for h in ray_hits(point,(0,0,-1),triangles))
    floor=[h for h in heights if abs(h-(2.4 if z>2 else .4))<.01];assert len(floor)==1
    point[2]=floor[0];assert triangle_distance(point,triangles)<1e-10
    candidates.append(dict(position=point.tolist(),gap=[a,b],local_heights=heights))
   apertures.append(dict(axis=axis,plane=plane,section_height=z,intersections=hits,rejected=rejected))
   reference_sets.append(candidates)
  assert list(map(len,reference_sets))==[2,1,1,1]
  assert len(apertures[3]['rejected'])==1 # Outer trim gap is blocked by the railing.
  references=[reference_sets[0][1],reference_sets[0][0],reference_sets[1][0],reference_sets[3][0],reference_sets[2][0]]
  # Clip a source line against every native convex leaf, then union occupied
  # intervals. This identifies the authored openings without guessing a
  # nearest door from the marker name or assuming one global origin shift.
  def source_aperture_intervals(axis,plane,z):
   lateral=1-axis;origin=np.zeros(3);origin[axis]=plane;origin[2]=z;intervals=[]
   for shape in source_shapes:
    planes=np.array(shape['planes']);value=planes[:,:3]@origin+planes[:,3]-shape['radius'];slope=planes[:,lateral]
    if np.any(value[abs(slope)<1e-8]>0):continue
    lo=max((-a/b for a,b in zip(value,slope) if b< -1e-8),default=-100)
    hi=min((-a/b for a,b in zip(value,slope) if b>1e-8),default=100)
    if lo<=hi:intervals.append([lo,hi])
   merged=[]
   for lo,hi in sorted(intervals):
    if merged and lo<=merged[-1][1]+.001:merged[-1][1]=max(merged[-1][1],hi)
    else:merged.append([lo,hi])
   return merged
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,reference) in enumerate(zip(original,mapped,references)):
   axis,sign=(1,1) if i<2 else (1,-1) if i==4 else (0,-1)
   point=np.array(before['position']);section_z=2.6 if i==3 else .8
   intervals=source_aperture_intervals(axis,point[axis]-sign*.05,section_z)
   gaps=[[a[1],b[0]] for a,b in zip(intervals,intervals[1:]) if a[1]<point[1-axis]<b[0]]
   assert len(gaps)==1 and gaps[0][1]-gaps[0][0]>.9
   assert abs(point[1-axis]-sum(gaps[0])/2)<.1
   floor_shape=source_shapes[57 if i==0 else 41 if i==3 else 26]
   floor_vertices=np.array(floor_shape['vertices']);radius=floor_shape['radius']
   source_edge=float(floor_vertices[:,axis].max()+radius if sign>0 else floor_vertices[:,axis].min()-radius)
   assert abs(point[axis]-source_edge)<.01
   assert floor_vertices[:,1-axis].min()-radius<point[1-axis]<floor_vertices[:,1-axis].max()+radius
   source_floor_top=float(floor_vertices[:,2].max()+radius)
   assert abs(point[2]-source_floor_top)<(.05 if i==3 else .01)
   assert math.dist(after['position'],reference['position'])<1e-10
   forward=tuple(sign if j==axis else 0 for j in range(3))
   assert math.dist(rotation_axes(before['rotation'])[0],forward)<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   assert abs(sum(q*q for q in after['rotation'])-1)<1e-6
   residual=triangle_distance(after['position'],triangles);assert residual<1e-10
   evidence.append(dict(index=i,position=after['position'],role='upper_balcony_opening' if i==3 else 'ground_entrance',
       source_opening=gaps[0],source_floor_top=source_floor_top,target_opening=reference['gap'],
       target_local_heights=reference['local_heights'],surface_residual=residual))
  # Equal source Z must map to two actual ground-panel heights. A full role
  # mapping preserves those local surfaces without changing original geometry.
  assert abs(mapped[0]['position'][2]-mapped[1]['position'][2]-.003801020395457)<1e-10
  assert abs(mapped[1]['position'][2]-mapped[4]['position'][2])<1e-10
  result.update(status='verified',reason='Five source roles independently identified by native convex aperture sections and floor edges; target mesh sections locate four ground entrances and the free upper balcony opening, outside rays reject blocked trim, exact local floor intersections set all five heights, complete original frames and all 59 target leaves preserved',
                anchors=evidence,compound=compound,target_apertures=apertures,
                contact_spacing=[mapped[0]['position'][0]-mapped[1]['position'][0],specs[0][1]-specs[2][1]],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Pyramid':
  name='fw_unsc_c_pyramid';source_bounds,original,source_shapes=source_geometry(name,compound=True)
  assert len(original)==5 and len(source_shapes)==19
  g=geometry[row['map'],row['palette_index']]
  compound=identity_compound(g,plane_exceptions={0:(5,),1:(4,),2:(5,)})
  assert len(g['polyhedra'])==10
  expected_errors=[.00016155088918878846,.00010126124178100326,.0001624586354829205]
  assert all(abs(item['maximum_vertex_distances'][0]-error)<1e-12 for item,error in zip(compound['native_plane_inconsistencies'],expected_errors))
  triangles=actual_triangles(row);vertices=triangles.reshape(-1,3);rendered=all_render_rows[row['map'],row['palette_index']]
  front=float(vertices[:,1].min());rear=float(vertices[:,1].max());width=float(vertices[:,0].max())
  assert abs(width-7.5)<1e-10 and abs(vertices[:,0].min()+width)<1e-10
  assert abs(rear-front-7.5)<1e-10
  caps=[]
  for axis,coordinate in ((0,-width),(0,width),(1,front),(1,rear)):
   faces=triangles[np.max(abs(triangles[:,:,axis]-coordinate),axis=1)<1e-5]
   area=float(np.linalg.norm(np.cross(faces[:,1]-faces[:,0],faces[:,2]-faces[:,0]),axis=1).sum()/2)
   assert area>(.5 if axis==0 else 1)
   caps.append(faces)
  # Three target entrance caps share exact vertical bounds. The common upper
  # edge is a construction reference derived from these faces, not an assumed
  # global Z offset applied to the source's different cap shapes.
  cap_bounds=[(float(f[:,:,2].min()),float(f[:,:,2].max())) for f in caps[:3]]
  assert max(math.dist(b,cap_bounds[0]) for b in cap_bounds)<1e-12
  entry=cap_bounds[0][1];assert -.011<entry<-.010
  inner=next(p for p in rendered['axis_planes'][1] if abs(p['coordinate']-(rear-1.5))<.00001 and p['area']>5)
  inner_faces=triangles[np.max(abs(triangles[:,:,1]-inner['coordinate']),axis=1)<.00001]
  inner_plane=float(inner_faces[:,:,1].mean());assert abs(rear-inner_plane-1.5)<1e-10
  side_center=(inner_plane+rear)/2
  # Exact X=0 section of the actual rear-facing triangles identifies the
  # lower floor and upper structure independently, including their bevels.
  intervals=[]
  for tri in caps[3]:
   cut=[]
   for a,b in zip(tri,np.roll(tri,-1,axis=0)):
    if abs(b[0]-a[0])<1e-12:continue
    fraction=-a[0]/(b[0]-a[0])
    if 0<=fraction<=1:cut.append(float(a[2]+fraction*(b[2]-a[2])))
   if len(cut)>1:intervals.append([min(cut),max(cut)])
  sections=[]
  for lo,hi in sorted(intervals):
   if sections and lo<=sections[-1][1]+.00001:sections[-1][1]=max(sections[-1][1],hi)
   else:sections.append([lo,hi])
  assert len(sections)==2 and sections[1][0]-sections[0][1]>2.2
  low,high=sections[0][1],sections[1][1]
  targets=[(-width,side_center,entry),(0,front,entry),(width,side_center,entry),(0,rear,high),(0,rear,low)]
  # Identify the source role against its actual convex leaf. The side ramp
  # anchors lie near the upper part of their end caps; front and rear markers
  # identify the corresponding cap/roof/floor tiers on the H4 structure.
  source_evidence=[]
  for i,shape_index in enumerate((4,10,7,8,12)):
   shape=source_shapes[shape_index];vs=np.array(shape['vertices']);radius=shape['radius'];point=np.array(original[i]['position'])
   axis=0 if i in (0,2) else 1;sign=1 if i in (0,1) else -1
   end=float(vs[:,axis].max() if sign>0 else vs[:,axis].min())
   face=vs[abs(vs[:,axis]-end)<1e-6];assert len(face)>=4
   assert abs(point[axis]-(end+sign*radius))<.008
   lateral=1-axis;assert face[:,lateral].min()-radius<point[lateral]<face[:,lateral].max()+radius
   top=float(face[:,2].max()+radius)
   assert abs(point[2]-top)<(.08 if i in (0,2) else .04)
   assert math.dist(rotation_axes(original[i]['rotation'])[0],tuple(sign if j==axis else 0 for j in range(3)))<1e-6
   source_evidence.append(dict(index=i,shape=shape_index,cap_axis=axis,cap_support=end+sign*radius,
                               upper_reference=top,original_upper_offset=float(point[2]-top)))
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,target) in enumerate(zip(original,mapped,targets)):
   assert math.dist(after['position'],target)<1e-10
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):
    assert math.dist((-old[0],-old[1],old[2]),new)<1e-6
   assert abs(sum(q*q for q in after['rotation'])-1)<1e-6
   cap=caps[0 if i==0 else 1 if i==2 else 2 if i==1 else 3]
   residual=triangle_distance(target,cap);assert residual<1e-10
   outward=np.array(rotation_axes(after['rotation'])[0]);outward=np.round(outward)
   assert np.max((vertices-np.array(target))@outward)<1e-6
   evidence.append(dict(index=i,position=after['position'],cap_residual=residual,
                        role=('left_ramp_entrance','front_ramp_entrance','right_ramp_entrance','rear_roof','rear_floor')[i]))
  gap_height=(sections[0][1]+sections[1][0])/2
  openings=ray_hits((0,rear+.1,gap_height),(0,-1,0),triangles)
  assert not openings or min(openings)>.3
  result.update(status='verified',reason='Five original ramp-entry/roof/floor roles identified in source leaves; 180-degree full-frame rotation; actual target entrance caps establish one common upper edge and independent wall planes establish side centers; exact rear cap section establishes floor/roof references and opening, all five anchors incident on actual faces, ten native leaves retained with three recorded plane residuals',
                anchors=evidence,compound=compound,source_roles=source_evidence,rear_sections=sections,
                entrance_cap_vertical_bounds=cap_bounds,contact_spacing=[2*width,rear-front,high-low],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label'] in ('Dish','Dish Door'):
  door=row['label']=='Dish Door';name='fw_unsc_c_dish_door' if door else 'fw_unsc_c_dish'
  source_bounds,original,source_shapes=source_geometry(name,compound=True)
  assert len(original)==(2 if door else 4) and len(source_shapes)==(32 if door else 34)
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g)
  assert len(g['polyhedra'])==(30 if door else 26)
  triangles=actual_triangles(row);vertices=triangles.reshape(-1,3)
  base=float(vertices[:,2].min());rear=float(vertices[:,1].min())
  assert abs(base+1.4)<1e-6 and abs(vertices[:,1].max())<1e-6
  assert abs(vertices[:,0].min()+vertices[:,0].max())<1e-6
  front=triangles[np.max(abs(triangles[:,:,1]),axis=1)<.0002]
  assert len(front)>160
  front_area=float(np.linalg.norm(np.cross(front[:,1]-front[:,0],front[:,2]-front[:,0]),axis=1).sum()/2)
  assert front_area>2
  # Both target variants share the complete central cut-face vertex set. This
  # independently requires the same mating references, even though H4's Door
  # lower marker was authored .04 above its base. Do not keep that mismatch.
  central=front[np.max(abs(front[:,:,0]),axis=1)<1.5].reshape(-1,3)
  other_row=next(r for r in inventory['rows'] if r['map']==row['map'] and r['label']==('Dish' if door else 'Dish Door'))
  other=actual_triangles(other_row)
  other=other[(np.max(abs(other[:,:,1]),axis=1)<.0002)&(np.max(abs(other[:,:,0]),axis=1)<1.5)].reshape(-1,3)
  assert len(central)==len(other)==120
  distances=np.linalg.norm(central[:,None,:]-other[None,:,:],axis=2)
  shared_error=float(max(distances.min(0).max(),distances.min(1).max()));assert shared_error<.0000015
  reference_bounds,reference_points,reference_shapes=source_geometry('fw_unsc_c_dish',compound=True)
  reference_height=reference_points[1]['position'][2]-reference_bounds[4]
  assert abs(reference_height-1.4966936114692688)<1e-9
  assert abs(original[1]['position'][2]-source_bounds[4]-reference_height)<1e-6
  source_cap=source_shapes[9 if door else 0];source_base=source_shapes[8 if door else 1]
  source_cap_top=max(p[2] for p in source_cap['vertices'])+source_cap['radius']
  source_base_bottom=min(p[2] for p in source_base['vertices'])-source_base['radius']
  assert abs(original[1]['position'][2]-source_cap_top)<1e-6
  assert abs(source_base_bottom-source_bounds[4])<.0002
  assert abs(original[0]['position'][0]-source_bounds[0])<.0006
  assert abs(original[1]['position'][0]-source_bounds[0])<.0006
  lower_source_offset=original[0]['position'][2]-source_bounds[4]
  assert abs(lower_source_offset-(.040163418278098106 if door else -.00015401807830798626))<1e-7
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after) in enumerate(zip(original,mapped)):
   x,y,z=before['position'];assert abs(y)<.000238
   target=(0,0 if i<2 else rear,base if i==0 else base+reference_height if i==1 else base+z-source_bounds[4])
   assert math.dist(after['position'],target)<1e-10
   if i>=2:assert not door and abs(x-source_bounds[1])<1e-6
   expected_forward=(0,1 if i<2 else -1,0)
   assert math.dist(rotation_axes(after['rotation'])[0],expected_forward)<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):
    assert math.dist((old[1],-old[0],old[2]),new)<1e-6
   assert abs(sum(q*q for q in after['rotation'])-1)<1e-6
   residual=triangle_distance(target,triangles)
   if i==0:assert .026<residual<.027
   elif i==1:
    assert .507<residual<.509
    # This is H4's common floating construction reference, not an anchor on
    # the bowl floor. The two variants retain the same height and clear space.
    hits=ray_hits((0,.1,target[2]),(0,-1,0),triangles)
    assert not hits or min(hits)>2
    if not door:assert hits
   else:
    sections=[-7+h for h in ray_hits((0,-7,target[2]),(0,1,0),triangles)]
    assert sections
    if i==2:
     assert residual<.000006 and abs(sections[0]-rear)<.000006
    else:
     assert .023<residual<.025 and .026<sections[0]-rear<.029
   evidence.append(dict(index=i,position=after['position'],surface_residual=residual,
                        role=('front_base','front_upper_reference','rear_lower','rear_upper_reference')[i],
                        original_height_above_base=z-source_bounds[4]))
  # A cut-face mating plane has every rendered point behind it. The rear
  # tangent plane likewise supports the complete mesh; its beveled upper
  # reference deliberately remains on that plane, as in the source roles.
  assert np.max(vertices[:,1])<1e-6 and np.min(vertices[:,1]-rear)>=0
  seam_heights=sorted(-2+h for h in ray_hits((0,-.02,-2),(0,0,1),triangles))
  assert len(seam_heights)>=3 and .025<seam_heights[0]-base<.028
  result.update(status='verified',reason='Complete native compounds and half-dish orientation; both variants share central front geometry within 0.0000015 and common base/upper references; all four Dish or two Dish Door original roles and full rotated bases checked, rear support and source-relative heights corrected, floating references and native bevel clearances explicitly proved',
                anchors=evidence,compound=compound,shared_front_error=shared_error,front_area=front_area,
                source_lower_offset_corrected=lower_source_offset,source_upper_height=reference_height,
                front_section_heights=seam_heights,contact_spacing=[-rear,reference_height],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Walkway Small Cover':
  g=geometry[row['map'],row['palette_index']]
  compound=identity_compound(g,expected_motion_type=2);assert len(g['polyhedra'])==56
  result.update(reason='Native motion-type-2 body, identity node and all 56 collision leaves resolved; nine source anchor feature correspondences still need proof',
                native_compound=compound,native_fixed_release=False)
 elif row['label']=='Door, 2':
  name='fw_unsc_c_door_2';source_bounds,original,source_shapes=source_geometry(name,compound=True)
  assert len(original)==10 and len(source_shapes)==15
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==5
  triangles=actual_triangles(row);rendered=all_render_rows[row['map'],row['palette_index']]
  target_bounds=rendered['referenced_bounds'];base_z=target_bounds[2][0];dz=base_z-source_bounds[4]
  # Height and depth agree independently; only the jamb/foot X features move.
  assert abs((target_bounds[2][1]-base_z)-(source_bounds[5]-source_bounds[4]))<2e-6
  assert abs(target_bounds[1][0]-source_bounds[2])<2e-6 and abs(target_bounds[1][1]-source_bounds[3])<2e-6
  foot_section=[-2+h for h in ray_hits((-2,0,round(base_z,4)),(1,0,0),triangles)]
  mid_section=[-2+h for h in ray_hits((-2,0,0),(1,0,0),triangles)]
  assert len(foot_section)==len(mid_section)==4
  assert max(abs(a-b) for a,b in zip(foot_section,[-.9,-.6,.6,.9]))<.00017
  assert math.dist(mid_section,[-.9,-.7,.7,.9])<.00006
  source_features={};target_features={}
  for side,foot_index,jamb_index in ((-1,3,2),(1,4,1)):
   shape=source_shapes[foot_index];vertices=np.array(shape['vertices']);radius=shape['radius']
   center=float((vertices[:,0].min()+vertices[:,0].max())/2)
   assert abs(center-side*1.15)<1e-6
   bottom=vertices[abs(vertices[:,2]-vertices[:,2].min())<1e-6]
   assert len(bottom)>=4 and abs(bottom[:,0].min()-vertices[:,0].min())<1e-6 and abs(bottom[:,0].max()-vertices[:,0].max())<1e-6
   assert abs(vertices[:,2].min()-radius-source_bounds[4])<1e-6
   shape=source_shapes[jamb_index];vertices=np.array(shape['vertices']);planes=np.array(shape['planes'])
   normal=np.array([-side,0,0]);selected=planes[np.linalg.norm(planes[:,:3]-normal,axis=1)<1e-6];assert len(selected)==1
   distance=vertices@selected[0,:3]+selected[0,3];assert abs(distance.max())<1e-6 and distance.min()<-.1
   face=vertices[abs(distance)<1e-6];assert len(face)>=4 and face[:,2].min()<0<face[:,2].max()
   assert face[:,1].min()<-.1 and face[:,1].max()>.1
   edge=float(vertices[:,0].min()-shape['radius'] if side>0 else vertices[:,0].max()+shape['radius'])
   assert abs(edge-side*1.1)<1e-6
   source_features[side]=dict(foot_center=center,jamb=edge)
   target_features[side]=dict(foot_center=sum(foot_section[2:4] if side>0 else foot_section[0:2])/2,
                              jamb=mid_section[2] if side>0 else mid_section[1])
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after) in enumerate(zip(original,mapped)):
   x,y,z=before['position'];side=1 if x>0 else -1
   assert abs(abs(y)-(.2 if i in (0,2) else .175 if i<6 else .1))<2e-6
   if i in (0,2):
    role='header';source_reference=(source_bounds[0]+source_bounds[1])/2;target_reference=sum(target_bounds[0])/2
    assert abs(x-source_reference)<.006 and .04<source_bounds[5]-z<.041
   else:
    role='foot_center' if i<6 else 'jamb';source_reference=source_features[side][role];target_reference=target_features[side][role]
    if i<6:assert abs(z-source_bounds[4])<1e-6 and abs(x-source_reference)<.017
    else:assert .030<abs(x-source_reference)<.033 and abs(z)<.001
   target=(target_reference+x-source_reference,y,z+dz)
   assert math.dist(after['position'],target)<1e-10
   assert abs((target[2]-base_z)-(z-source_bounds[4]))<1e-12
   assert math.dist(rotation_axes(before['rotation'])[0],(0,1 if y>0 else -1,0))<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   assert abs(sum(q*q for q in after['rotation'])-1)<1e-6
   residual=triangle_distance(target,triangles)
   if i<6:assert residual<.00003
   else:
    # The original middle roles are deliberately inside the opening, not on
    # the visible face. Prove the preserved offset, rather than hiding it in
    # a loose surface tolerance or projecting away the authored placement.
    assert abs(residual-abs(x-source_reference))<1e-6
    assert mid_section[1]<target[0]<mid_section[2]
    assert not ray_hits((target[0],-1,target[2]),(0,1,0),triangles)
   evidence.append(dict(index=i,role=role,position=after['position'],source_reference=source_reference,
       target_reference=target_reference,preserved_lateral_offset=x-source_reference,surface_residual=residual))
  for a,b in ((0,2),(1,5),(3,4),(6,7),(8,9)):
   assert abs((mapped[a]['position'][1]-mapped[b]['position'][1])-(original[a]['position'][1]-original[b]['position'][1]))<1e-12
  result.update(status='verified',reason='Ten original header/foot/jamb roles mapped from native source features to independent target sections; original per-role offsets, base-relative heights, front/back depths and every complete basis retained; intentional middle opening clearances proved separately; all five target leaves resolved',
                anchors=evidence,compound=compound,source_features=source_features,target_features=target_features,
                foot_section=foot_section,mid_section=mid_section,contact_spacing=[mid_section[2]-mid_section[1],target_bounds[2][1]-base_z],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Brace, Large':
  name='fw_unsc_c_large_brace';source_bounds,original,source_shapes=source_geometry(name,compound=True)
  assert len(original)==5 and len(source_shapes)==20
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g,plane_exceptions={1:(4,)})
  assert len(g['polyhedra'])==8
  assert abs(compound['native_plane_inconsistencies'][0]['maximum_vertex_distances'][0]-.00015723472573725417)<1e-12
  triangles=actual_triangles(row);rendered=all_render_rows[row['map'],row['palette_index']]
  def inflated_bounds(shape):
   vertices=np.array(shape['vertices']);return np.c_[vertices.min(0)-shape['radius'],vertices.max(0)+shape['radius']]
  source_foot=inflated_bounds(source_shapes[19]);target_foot=inflated_bounds(g['polyhedra'][2])
  assert np.max(abs(source_foot[:2]-np.array([[-1,1],[.3,1.2]])))<.00001
  assert np.max(abs(target_foot[:2]-np.array([[-2,0],[0,.9]])))<.000001
  assert abs((source_foot[1,1]-source_foot[1,0])-(target_foot[1,1]-target_foot[1,0]))<1e-6
  assert abs(source_foot[2,0]-source_bounds[4])<1e-6 and abs(target_foot[2,0]+2)<1e-6
  source_beam=inflated_bounds(source_shapes[8]);source_upper=inflated_bounds(source_shapes[12]);source_front=inflated_bounds(source_shapes[15])
  assert abs(source_beam[1,0]+9.2)<1e-6 and abs(source_upper[2,1]-(source_bounds[4]+4.5))<1e-6
  assert abs(source_front[1,1]-1.8)<.0001 and abs(source_front[2,1]-(source_bounds[4]+3.1))<1e-6
  # Native construction features establish the nominal planes; actual mesh
  # patches independently establish that they are meaningful target surfaces.
  target_beam=inflated_bounds(g['polyhedra'][1]);target_front=inflated_bounds(g['polyhedra'][3])
  assert abs(target_beam[1,0]+9)<1e-6 and abs(target_beam[2,1]-2.5)<1e-6
  assert abs(target_front[1,1]-1.5)<1e-6 and abs(target_front[2,1]-1.1)<1e-6
  surfaces=[]
  for axis,coordinate,min_area in ((2,-2,.2),(2,2.5,2),(1,-9,.05),(1,1.5,.5)):
   faces=triangles[np.max(abs(triangles[:,:,axis]-coordinate),axis=1)<.00001]
   area=float(np.linalg.norm(np.cross(faces[:,1]-faces[:,0],faces[:,2]-faces[:,0]),axis=1).sum()/2)
   assert area>min_area;surfaces.append(dict(axis=axis,coordinate=coordinate,area=area))
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  source_center=round(float(source_foot[1].mean()),4);target_center=round(float(target_foot[1].mean()),4)
  directions=[(-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,1,0)]
  roles=['left_foot','right_foot','beam_end','front_lower','front_upper']
  for i,(before,after) in enumerate(zip(original,mapped)):
   x,y,z=before['position'];height=z-source_bounds[4]
   assert abs(height-[0,0,4.5,1,3.1][i])<1e-6
   if i<2:
    assert abs(x-(-1 if i==0 else 1))<1e-6 and source_foot[1,0]<y<source_foot[1,1]
    ty=target_center+y-source_center
   elif i==2:assert abs(y-source_beam[1,0])<1e-6;ty=round(float(target_beam[1,0]),4)
   else:assert abs(y-source_front[1,1])<.0001;ty=round(float(target_front[1,1]),4)
   target=(x-1,ty,-2+height);assert math.dist(target,after['position'])<1e-10
   assert math.dist(rotation_axes(before['rotation'])[0],directions[i])<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   assert abs(sum(q*q for q in after['rotation'])-1)<1e-6
   residual=triangle_distance(target,triangles);assert residual<(.000002 if i<2 else .0101)
   evidence.append(dict(index=i,role=roles[i],position=after['position'],height_above_base=height,
                        preserved_lateral_offset=x if i>=2 else y-source_center,surface_residual=residual))
  # The small end/front clearances are the existing mesh bevel, not missing
  # node transforms. Interior sections confirm the corresponding solid faces.
  section_evidence=[]
  for point,axis,nominal in (((-1,-8.9,3),2,2.5),((-1,2,-1),1,1.5),((-1,2,1.1),1,1.5)):
   direction=[0,0,0];direction[axis]=-1;hits=ray_hits(point,direction,triangles);assert hits
   boundary=point[axis]-min(hits);assert abs(boundary-nominal)<.02
   section_evidence.append(dict(origin=point,axis=axis,outer_surface=boundary,construction_plane=nominal))
  result.update(status='verified',reason='All five H4 roles identified against source feet/front/beam; target native features and real mesh patches establish the changed origin, shorter beam and foot reference; authored offsets/heights and full bases preserved, exact foot incidence and measured front/beam bevel clearances checked, all eight leaves resolved with one specifically recorded native plane residual',
                anchors=evidence,compound=compound,construction_surfaces=surfaces,sections=section_evidence,
                contact_spacing=[2,.9,4.5],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Room Double':
  name='fw_unsc_c_room_double';source_bounds,original,source_shapes=source_geometry(name,compound=True)
  assert len(original)==2 and len(source_shapes)==34
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==31
  source_left_gap=[np.array(source_shapes[16]['vertices'])[:,1].max(),np.array(source_shapes[4]['vertices'])[:,1].min()]
  source_front_gap=[np.array(source_shapes[20]['vertices'])[:,0].max(),np.array(source_shapes[15]['vertices'])[:,0].min()]
  assert abs(original[0]['position'][1]-sum(source_left_gap)/2)<.011
  assert abs(original[1]['position'][0]-sum(source_front_gap)/2)<.001
  assert all(abs(p['position'][2]-source_bounds[4]-.3)<.000002 for p in original)
  triangles=actual_triangles(row);rendered=all_render_rows[row['map'],row['palette_index']]
  def cap_sections(axis,plane,lateral):
   faces=triangles[np.max(abs(triangles[:,:,axis]-plane),axis=1)<.00003];intervals=[]
   for tri in faces:
    cut=[]
    for a,b in zip(tri,np.roll(tri,-1,axis=0)):
     if abs(b[2]-a[2])<1e-10:continue
     fraction=(1-a[2])/(b[2]-a[2])
     if 0<=fraction<=1:cut.append(float(a[lateral]+fraction*(b[lateral]-a[lateral])))
    if len(cut)>=2:intervals.append((min(cut),max(cut)))
   merged=[]
   for lo,hi in sorted(intervals):
    if merged and lo<=merged[-1][1]+.0002:merged[-1][1]=max(merged[-1][1],hi)
    else:merged.append([lo,hi])
   return merged
  openings=[]
  for axis,side,lateral in ((0,-1,1),(1,1,0)):
   candidates=[]
   for plane in sorted(rendered['axis_planes'][axis],key=lambda p:-side*p['coordinate']):
    if plane['area']<.3 or (axis==0 and plane['coordinate']>-2.6) or (axis==1 and plane['coordinate']<1.9):continue
    sections=cap_sections(axis,plane['coordinate'],lateral)
    if len(sections)!=(2 if axis==0 else 4):continue
    gaps=[[a[1],b[0]] for a,b in zip(sections,sections[1:]) if b[0]-a[1]>1 and (axis==0 or a[1]>0)]
    if len(gaps)==1:candidates.append(dict(axis=axis,wall_plane=plane['coordinate'],wall_sections=sections,gap=gaps[0]))
   assert candidates;openings.append(candidates[0])
  floor_plane=max((p for p in rendered['axis_planes'][2] if .2<p['coordinate']<.4),key=lambda p:p['area'])
  assert floor_plane['area']>11
  floor_faces=triangles[np.max(abs(triangles[:,:,2]-floor_plane['coordinate']),axis=1)<.00001]
  floor_vertices=floor_faces.reshape(-1,3);floor_z=float(floor_vertices[:,2].mean())
  targets=[(float(floor_vertices[:,0].min()),sum(openings[0]['gap'])/2,floor_z),
           (sum(openings[1]['gap'])/2,float(floor_vertices[:,1].max()),floor_z)]
  sources=[(-2.650000810623169,.6602168083190918,.3081369698047638),
           (1.9500007629394531,1.9500011205673218,.30813688039779663)]
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,source,target) in enumerate(zip(original,mapped,sources,targets)):
   assert math.dist(before['position'],source)<1e-10 and math.dist(after['position'],target)<1e-10
   assert math.dist(rotation_axes(before['rotation'])[0],(-1,0,0))<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   residual=triangle_distance(target,floor_faces);assert residual<1e-10
   normal=np.array([-1,0,0] if i==0 else [0,1,0]);outside=np.array(target)+normal*.1;outside[2]=1
   entries=ray_hits(outside,-normal,triangles);assert not entries or min(entries)>.3
   inside=np.array(target)-normal*.05;inside[2]=3
   heights=sorted(3-h for h in ray_hits(inside,(0,0,-1),triangles))
   assert any(abs(h-floor_z)<1e-10 for h in heights) and min(h for h in heights if h>floor_z+.001)-floor_z>1.4
   evidence.append(dict(index=i,position=after['position'],authored_forward=[-1,0,0],
                        opening_normal=normal.tolist(),floor_residual=residual,inside_heights=heights,opening=openings[i]))
  result.update(status='verified',reason='Both original entrance-floor roles identified in source wall gaps; actual target wall-cap cross-sections independently locate both opening centers on the exact outer floor edges; both complete authored -X frames retained, opening normals recorded separately, clear entrance rays/headroom and all 31 native leaves checked',
                anchors=evidence,compound=compound,contact_spacing=[p['gap'][1]-p['gap'][0] for p in openings],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Platform, Ramped':
  name='fw_unsc_c_ramp_plat';source_bounds,original,source_shapes=source_geometry(name,compound=True)
  assert len(original)==4 and len(source_shapes)==9
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==9
  source_vertices=np.vstack([s['vertices'] for s in source_shapes]);target_vertices=np.vstack([s['vertices'] for s in g['polyhedra']])
  skin=source_shapes[0]['radius'];assert all(s['radius']==skin for s in source_shapes+g['polyhedra'])
  source_extents=np.c_[source_vertices.min(0)-skin,source_vertices.max(0)+skin]
  target_extents=np.c_[target_vertices.min(0)-skin,target_vertices.max(0)+skin]
  assert np.max(abs(source_extents-np.array([[-2.283333333,2.716666667],[-3.4,2],[0,2.1]])))<.00012
  assert np.max(abs(target_extents-np.array([[-3,2],[-2.2,2.3],[-1,1.1]])))<.0017
  assert abs((target_extents[1,1]-target_extents[1,0])/(source_extents[1,1]-source_extents[1,0])-5/6)<1e-6
  # Native inner rail faces establish the actual low-ramp width and center.
  inner=[np.array(g['polyhedra'][1]['vertices'])[:,1].max()+skin,np.array(g['polyhedra'][0]['vertices'])[:,1].min()-skin]
  assert math.dist(inner,(.5,2.1))<.000004 and abs(sum(inner)/2-1.3)<.000002
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);rendered=all_render_rows[row['map'],row['palette_index']]
  low_x=float(mesh[:,0].min());low_z=float(mesh[:,2].min())
  deck_candidates=[p for p in rendered['axis_planes'][2] if .6<p['coordinate']<.8]
  main=max(deck_candidates,key=lambda p:p['area']);assert main['area']>5
  deck_faces=triangles[np.max(abs(triangles[:,:,2]-main['coordinate']),axis=1)<.00001]
  high_z=float(deck_faces[:,:,2].mean())
  assert any(abs(p['coordinate']-2)<.00004 and p['area']>.57 for p in rendered['axis_planes'][0])
  assert any(abs(p['coordinate']-low_x)<.00001 and p['area']>.16 for p in rendered['axis_planes'][0])
  assert any(abs(p['coordinate']-low_z)<.00001 and p['area']>.64 for p in rendered['axis_planes'][2])
  sources=[(2.716700315475464,-2.199998378753662,.00002540588320698589),
           (-2.283331871032715,-1.949998140335083,1.699997901916504),
           (-2.283332109451294,-.6999978423118591,1.699997901916504),
           (-2.283332347869873,.5500024557113647,1.699998140335083)]
  targets=[(low_x,1.3,low_z),(2,1.0916666666666668,high_z),(2,.05,high_z),(2,-.9916666666666667,high_z)]
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,source,target) in enumerate(zip(original,mapped,sources,targets)):
   assert math.dist(before['position'],source)<1e-10 and math.dist(after['position'],target)<1e-10
   assert abs(-before['position'][1]*5/6-.5333333333333333-target[1])<.000003
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist((-old[0],-old[1],old[2]),new)<1e-6
   normal=(-1,0,0) if i==0 else (1,0,0);assert math.dist(rotation_axes(after['rotation'])[0],normal)<1e-6
   residual=triangle_distance(target,triangles);assert .0188<residual<.0189 if i==0 else .0129<residual<.0137
   if i:
    heights=[3-h for h in ray_hits((1.95,target[1],3),(0,0,-1),triangles)]
    assert heights and abs(max(heights)-high_z)<1e-10
   else:
    heights=[3-h for h in ray_hits((-2.95,1.3,3),(0,0,-1),triangles)]
    assert len(heights)==2 and abs(min(heights)-low_z)<1e-10 and .02<max(heights)-low_z<.03
   evidence.append(dict(index=i,position=after['position'],outward_forward=normal,surface_residual=residual,inside_heights=heights))
  assert all(abs(targets[i][1]-targets[i+1][1]-1.25*5/6)<1e-10 for i in (1,2))
  result.update(status='verified',reason='All four original low/high entrance roles and full cardinal bases rotate 180 degrees; source/target authored collision extents establish 5/6 lateral scale, actual target inner rails establish low entrance center, and three independent upper deck sections corroborate the retained evenly spaced upper roles',
                anchors=evidence,compound=compound,contact_spacing=[2-low_x,1.25*5/6,high_z-low_z],
                low_ramp_inner_rails=list(map(float,inner)),source_collision_extents=source_extents.tolist(),raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Landing Pad':
  name='fw_unsc_c_plat_4x6';_,source_bounds,original=source_markers(name);assert len(original)==8
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==7
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);rendered=all_render_rows[row['map'],row['palette_index']]
  target_bounds=np.array([[-2,2],[-4,2],[-.3,0]])
  base_shape=g['polyhedra'][2];vertices=np.array(base_shape['vertices']);skin=base_shape['radius']
  assert len(vertices)==20 and len(base_shape['planes'])==14
  assert np.max(abs(np.c_[vertices.min(0)-skin,vertices.max(0)+skin]-target_bounds))<.000006
  for axis,level,area in ((0,-2,2.2),(0,2,2.2),(1,-4,.43),(1,2,1.8),(2,-.3,13),(2,0,8)):
   assert any(abs(p['coordinate']-level)<.00002 and p['area']>area for p in rendered['axis_planes'][axis])
  assert np.max(abs(np.c_[mesh.min(0),mesh.max(0)][:2]-target_bounds[:2]))<.000004
  sources=[(-2.5400078296661377,1.3498485088348389,0),(.10000000149011612,3.0999975204467773,.30000001192092896),
           (-2.599881649017334,1.3498485088348389,.30000001192092896),(2.799999952316284,1.3500025272369385,.30000001192092896),
           (.10000000149011612,-2.9000024795532227,.30000001192092896),(.10000000149011612,-2.8333024978637695,0),
           (2.740112781524658,1.3500025272369385,0),(.10000000149011612,3.03324818611145,0)]
  roles=[(0,0,0),(1,1,1),(0,0,1),(0,1,1),(1,0,1),(1,0,0),(0,1,0),(1,1,0)]
  assert set(roles)==set(itertools.product((0,1),(0,1),(0,1)))
  # Retain the authored front-relative side location. Overall-bound centers
  # would move it into a different part of the extended landing platform.
  side_y=target_bounds[1,1]-1.75
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,source,(axis,side,tier)) in enumerate(zip(original,mapped,sources,roles)):
   assert math.dist(before['position'],source)<1e-10
   if axis==0:assert abs(source_bounds[3]-before['position'][1]-1.75)<.00016
   target=np.array([0.,side_y,target_bounds[2,tier]]);target[axis]=target_bounds[axis,side]
   if axis==1:target[0]=0
   assert math.dist(after['position'],target)<1e-10
   normal=np.zeros(3);normal[axis]=2*side-1
   assert math.dist(rotation_axes(after['rotation'])[0],normal)<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   residual=triangle_distance(target,triangles)
   assert residual<.000004 if axis==0 and tier else .00704<residual<.00708
   evidence.append(dict(index=i,position=after['position'],outward_forward=normal.tolist(),surface_residual=residual))
  # Both real entrance strips expose the same deck/base levels, independently
  # of recessed decorative panels in the middle of the platform.
  for y in (-3.9,1.9):
   heights=[3-h for h in ray_hits((0,y,3),(0,0,-1),triangles)]
   assert len(heights)==2 and math.dist(sorted(heights),target_bounds[2])<.000012
  result.update(status='verified',reason='All eight original perimeter/tier roles and complete cardinal frames map to independently witnessed principal side/end planes and base/deck levels; authored 1.75-unit front-relative side offset retained; actual entrance sections, base support geometry, all seven native leaves and cap bevels checked',
                anchors=evidence,compound=compound,contact_spacing=[4,6,.3],side_front_offset=1.75,raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Ramp, XL':
  name='fw_unsc_c_ramp_4x2';source_bounds,original,source_shape=source_geometry(name);assert len(original)==4
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==1
  # Prove both complete end-varying convex prisms. Source longitudinal Y maps
  # to target X, and upper/lower slopes exchange roles. This is not a rigid
  # shape match; anchor bases retain upright Z while position tiers reverse.
  prism_evidence=[]
  for shape,longitudinal,lateral in ((source_shape,1,0),(g['polyhedra'][0],0,1)):
   vertices=np.array(shape['vertices']);planes=np.array(shape['planes'])
   assert len(vertices)==8 and len(planes)==6
   ends=sorted(set(vertices[:,longitudinal]));assert len(ends)==2
   levels=[]
   for end in ends:
    cap=vertices[vertices[:,longitudinal]==end];zs=[float(cap[:,2].min()),float(cap[:,2].max())];assert zs[1]-zs[0]>.1 and len(cap)==4
    assert abs(cap[:,lateral].min()+cap[:,lateral].max())<1e-6
    for side,z in itertools.product((-1,1),zs):
     target=np.zeros(3);target[longitudinal]=end;target[lateral]=side*abs(cap[:,lateral]).max();target[2]=z
     assert np.min(np.linalg.norm(cap-target,axis=1))<1e-6
    levels.append(zs)
   distances=vertices@planes[:,:3].T+planes[:,3]
   assert np.max(abs(np.linalg.norm(planes[:,:3],axis=1)-1))<1e-6
   assert np.max(distances)<.0001 and np.max(abs(distances.max(0)))<.0001
   assert all(np.count_nonzero(abs(distances[:,i])<.0001)==4 for i in range(6))
   slopes=(np.array(levels[1])-levels[0])/(ends[1]-ends[0])
   prism_evidence.append(dict(core_ends=ends,core_end_heights=levels,core_slopes=slopes.tolist()))
  source_slopes=prism_evidence[0]['core_slopes'];target_slopes=prism_evidence[1]['core_slopes']
  assert source_slopes[0]<0<source_slopes[1] and target_slopes[0]<0<target_slopes[1]
  assert abs(source_slopes[0]+target_slopes[1])<.001 and abs(source_slopes[1]+target_slopes[0])<.001
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);rendered=all_render_rows[row['map'],row['palette_index']]
  xends=[float(mesh[:,0].min()),float(mesh[:,0].max())]
  for end,area in zip(xends,(.47,4.5)):
   assert any(abs(p['coordinate']-end)<.000005 and p['area']>area for p in rendered['axis_planes'][0])
  assert abs(mesh[:,1].min()+mesh[:,1].max())<.000002
  cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);lengths=np.linalg.norm(cross,axis=1)
  normals=np.divide(cross,lengths[:,None],out=np.zeros_like(cross),where=lengths[:,None]>0);groups={}
  for i,(tri,normal,length) in enumerate(zip(triangles,normals,lengths)):
   if length<1e-8 or abs(normal[1])>1e-5 or abs(normal[2])<.5:continue
   if normal[2]<0:normal=-normal
   key=tuple(np.round(normal,4))+(round(float(tri[0]@normal),4),)
   groups.setdefault(key,[]).append(i)
  surfaces=[]
  for slope_sign in (-1,1):
   ids=max((ids for key,ids in groups.items() if np.sign(-key[0])==slope_sign and abs(key[0])>.1),key=lambda ids:lengths[ids].sum())
   assert lengths[ids].sum()/2>9.5
   normal=np.sum(normals[ids]*np.sign(normals[ids,2])[:,None]*lengths[ids,None],axis=0);normal/=np.linalg.norm(normal)
   distance=float(np.mean(triangles[ids]@normal));surfaces.append((normal,distance))
  heights=[[float((distance-normal[0]*x)/normal[2]) for normal,distance in surfaces] for x in xends]
  assert .21<heights[0][1]-heights[0][0]<.22 and 3.2<heights[1][1]-heights[1][0]<3.201
  for x in (-1.95,-1,0,1,1.95):
   crossings=[5-h for h in ray_hits((x,0,5),(0,0,-1),triangles)]
   expected=[(distance-normal[0]*x)/normal[2] for normal,distance in surfaces]
   assert len(crossings)==2 and math.dist(sorted(crossings),expected)<.000005
  sources=[(.021070249378681183,1.7000000476837158,-1.2000000476837158),
           (.02107005938887596,1.7000000476837158,2),
           (.02106986753642559,-2.299999952316284,-.20000000298023224),
           (.02106967754662037,-2.299999952316284,0)]
  roles=[(1,1),(1,0),(0,1),(0,0)];assert set(roles)==set(itertools.product((0,1),(0,1)))
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,source,(end,tier)) in enumerate(zip(original,mapped,sources,roles)):
   assert math.dist(before['position'],source)<1e-10
   target=(xends[end],0,heights[end][tier]);assert math.dist(after['position'],target)<1e-10
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist((old[1],-old[0],old[2]),new)<1e-6
   expected_forward=(2*end-1,0,0);axes=rotation_axes(after['rotation'])
   assert math.dist(axes[0],expected_forward)<1e-6 and math.dist(axes[2],(0,0,1))<1e-6
   normal,distance=surfaces[tier];assert abs(np.dot(normal,target)-distance)<1e-10
   residual=triangle_distance(target,triangles);assert residual<(.009 if end else .002)
   evidence.append(dict(index=i,position=after['position'],outward_forward=expected_forward,up=axes[2],surface_residual=residual))
  result.update(status='verified',reason='All four source thick/thin end roles map to independent actual end/slope intersections with reversed vertical tier correspondence; full source and target convex prisms establish the slope inversion; five actual vertical sections corroborate both target faces and complete rotated bases remain outward/upright',
                anchors=evidence,compound=compound,contact_spacing=[xends[1]-xends[0],heights[0][1]-heights[0][0],heights[1][1]-heights[1][0]],
                native_prisms=prism_evidence,construction_end_heights=heights,raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Ramp, Stunt':
  name='fw_unsc_c_race_stunt_ramp';_,source_bounds,original=source_markers(name);assert len(original)==5
  assert math.dist(source_bounds,(-1.2,1.2,-2,2,0,1.5))<1e-7
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==4
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);rendered=all_render_rows[row['map'],row['palette_index']]
  cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);lengths=np.linalg.norm(cross,axis=1)
  normals=np.divide(cross,lengths[:,None],out=np.zeros_like(cross),where=lengths[:,None]>0)
  groups={}
  for i,(tri,normal,length) in enumerate(zip(triangles,normals,lengths)):
   if length<1e-8 or abs(normal[1])>1e-5 or abs(normal[2])<.5:continue
   if normal[2]<0:normal=-normal
   key=tuple(np.round(normal,4))+(round(float(tri[0]@normal),4),)
   groups.setdefault(key,[]).append(i)
  horizontal=[ids for key,ids in groups.items() if abs(key[0])+abs(key[1])<1e-8 and key[2]==1]
  floor_ids=max(horizontal,key=lambda ids:lengths[ids].sum());assert lengths[floor_ids].sum()/2>9
  landing_ids=max((ids for ids in horizontal if lengths[ids].sum()/2>.2),key=lambda ids:triangles[ids,:,2].mean())
  assert lengths[landing_ids].sum()/2>.44
  base=float(triangles[floor_ids,:,2].mean());top=float(triangles[landing_ids,:,2].mean())
  front_ids=max((ids for key,ids in groups.items() if key[0]<-.1 and triangles[ids,:,0].max()<0),key=lambda ids:lengths[ids].sum())
  assert lengths[front_ids].sum()/2>2.27
  front_normal=np.sum(normals[front_ids]*np.sign(normals[front_ids,2])[:,None]*lengths[front_ids,None],axis=0)
  front_normal/=np.linalg.norm(front_normal);front_distance=float(np.mean(triangles[front_ids]@front_normal))
  nose=(front_distance-front_normal[2]*base)/front_normal[0]
  rear_groups={}
  for i,tri in enumerate(triangles):
   if np.ptp(tri[:,0])<1e-6 and tri[:,0].min()>1.9:rear_groups.setdefault(round(float(tri[:,0].mean()),5),[]).append(i)
  rear_ids=max(rear_groups.values(),key=lambda ids:lengths[ids].sum());assert lengths[rear_ids].sum()/2>3.3
  back=float(triangles[rear_ids,:,0].mean());center=(nose+back)/2
  assert abs(back-nose-4)<.00024 and abs(top-base-1.5)<.000005
  for side in (-1,1):
   assert any(abs(p['coordinate']-side*1.2)<1e-8 and p['area']>1.6 for p in rendered['axis_planes'][1])
  assert mesh[:,1].min()>-1.200001 and mesh[:,1].max()<1.200001
  sources=[(-1.1999998092651367,-.007914066314697266,.007474112324416637),
           (0,-1.9906975030899048,0),(1.2000000476837158,-.007914066314697266,.007474112324416637),
           (0,1.9911378622055054,0),(0,1.954723596572876,1.5)]
  targets=[(center,1.2,base),(nose,0,base),(center,-1.2,base),(back,0,base),(back,0,top)]
  forwards=[(0,1,0),(-1,0,0),(0,-1,0),(1,0,0),(1,0,0)]
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,source,target,forward) in enumerate(zip(original,mapped,sources,targets,forwards)):
   assert math.dist(before['position'],source)<1e-10 and math.dist(after['position'],target)<1e-10
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist((old[1],-old[0],old[2]),new)<1e-6
   assert math.dist(rotation_axes(after['rotation'])[0],forward)<1e-6
   residual=triangle_distance(target,triangles)
   limits=(.00368,.00369) if i in (0,2) else ((.01927,.01929) if i==1 else (.01416,.01418))
   assert limits[0]<residual<limits[1]
   evidence.append(dict(index=i,position=after['position'],outward_forward=forward,surface_residual=residual))
  # Probe actual lower and upper surfaces inside the rear edge bevel; the
  # virtual front corner is proven by its two intersecting face equations.
  heights=[3-h for h in ray_hits((back-.05,0,3),(0,0,-1),triangles)]
  assert len(heights)==2 and abs(min(heights)-base)<1e-10 and abs(max(heights)-top)<1e-10
  assert abs(np.dot(front_normal,(nose,0,base))-front_distance)<1e-10
  native_vertices=np.vstack([s['vertices'] for s in g['polyhedra']]);skin=g['polyhedra'][0]['radius']
  assert all(s['radius']==skin for s in g['polyhedra'])
  native_bounds=np.c_[native_vertices.min(0)-skin,native_vertices.max(0)+skin]
  assert np.max(abs(native_bounds-np.array([[-2,2],[-1.2,1.2],[0,1.5]])))<1e-6
  result.update(status='verified',reason='Five original side/base-end/upper-end roles and full bases rotated -90 degrees; actual main ramp/base intersection determines the beveled nose, actual rear/landing/side planes determine all other references; independent landing section and complete four-leaf native compound checked',
                anchors=evidence,compound=compound,contact_spacing=[back-nose,2.4,top-base],
                front_plane=[*front_normal.tolist(),-front_distance],native_bounds=native_bounds.tolist(),raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Platform, Y':
  name='fw_unsc_c_plat_y_cross';_,_,original=source_markers(name);assert len(original)==6
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==1
  shape=g['polyhedra'][0];skin=shape['radius'];vertices=np.array(shape['vertices'])
  core_x=sorted(set(vertices[:,0]));assert len(core_x)==3
  left,shoulder,tip=[x+math.copysign(skin,x) for x in core_x]
  half_width=float(vertices[:,1].max()+skin);height=float(vertices[:,2].max()+skin)
  assert abs(half_width-1.5)<1e-7 and abs(height-.1)<1e-7
  polygon=[(left,-half_width),(shoulder,-half_width),(tip,0),(shoulder,half_width),(left,half_width)]
  inset=[(x-math.copysign(skin,x),y-math.copysign(skin,y) if y else 0) for x,y in polygon]
  expected_vertices=[(x,y,z) for x,y in inset for z in (-height+skin,height-skin)]
  assert len(vertices)==10 and len(shape['planes'])==7
  assert all(min(math.dist(p,w) for w in vertices)<1e-7 for p in expected_vertices)
  core_planes=[(0,0,-1,-height+skin),(0,0,1,-height+skin)];supports=[(0,0,-1,-height),(0,0,1,-height)]
  for profile,planes in ((inset,core_planes),(polygon,supports)):
   for a,b in zip(profile,profile[1:]+profile[:1]):
    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);nx,ny=dy/length,-dx/length
    planes.append((nx,ny,0,-nx*a[0]-ny*a[1]))
  core_plane_residuals=[min(math.dist(p,q) for q in shape['planes']) for p in core_planes]
  # These two stored native diagonal normals differ from the exact vertex
  # planes by 3.31e-5 in coefficient norm; retain and report that local error.
  for i,error in enumerate(core_plane_residuals):
   assert .000033<error<.000034 if i in (3,4) else error<1e-6
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);face_areas=[];support_residuals=[]
  for plane in supports:
   offsets=triangles@np.array(plane[:3])+plane[3]
   assert float(offsets.max())<.000002
   faces=triangles[np.max(abs(offsets),axis=1)<.00003]
   area=float(np.linalg.norm(np.cross(faces[:,1]-faces[:,0],faces[:,2]-faces[:,0]),axis=1).sum()/2)
   assert area>(7 if abs(plane[2])>.5 else .3),(plane,area,float(offsets.max()));face_areas.append(area)
   support_residuals.append(float(offsets.max()))
  sources=[(1.7071094512939453,0,.20000000298023224),(.7071094512939453,-1.5,.20000000298023224),
           (.7071094512939453,1.5,.20000000298023224),(-2.2928898334503174,0,.20000000298023224),
           (-1.2928905487060547,1,.20000000298023224),(-1.2928895950317383,-1.000000238418579,.20000000298023224)]
  targets=[(left,0,height),((left+shoulder)/2,half_width,height),((left+shoulder)/2,-half_width,height),
           (tip,0,height),((shoulder+tip)/2,-half_width/2,height),((shoulder+tip)/2,half_width/2,height)]
  root2=math.sqrt(2);forwards=[(-1,0,0),(0,1,0),(0,-1,0),(1,0,0),(1/root2,-1/root2,0),(1/root2,1/root2,0)]
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,source,target,forward) in enumerate(zip(original,mapped,sources,targets,forwards)):
   assert math.dist(before['position'],source)<1e-10 and math.dist(after['position'],target)<3e-8
   assert math.dist(rotation_axes(before['rotation'])[2],(0,0,1))<1e-6
   expected_axes=[forward,(-forward[1],forward[0],0),(0,0,1)]
   for expected,actual in zip(expected_axes,rotation_axes(after['rotation'])):assert math.dist(expected,actual)<1e-6
   for plane in supports:assert np.dot(plane[:3],target)+plane[3]<1e-7
   if i==3:
    # A bisector-facing tip reference remains a valid outward support even
    # though the two diagonal faces meet behind a small rendered chamfer.
    assert abs(target[0]-mesh[:,0].max()-.014142176136374474)<1e-10
    assert math.dist(np.array(supports[3][:3])+np.array(supports[4][:3]),(root2,0,0))<1e-6
   else:
    plane=min(supports[2:],key=lambda p:math.dist(p[:3],forward))
    assert math.dist(plane[:3],forward)<1e-6 and abs(np.dot(plane[:3],target)+plane[3])<1e-7
   residual=triangle_distance(target,triangles);assert .02309<residual<.02310 if i==3 else .01413<residual<.01416
   evidence.append(dict(index=i,position=after['position'],outward_forward=forward,surface_residual=residual))
  result.update(status='verified',reason='All six original top-edge/tip roles map to independently reconstructed pentagonal construction edges and apex; all seven native core planes and ten vertices checked, actual mesh supports and face areas corroborated, complete upright frames follow cardinal/diagonal normals with the tip in their outward normal cone',
                anchors=evidence,compound=compound,contact_spacing=[tip-left,2*half_width,2*height],construction_polygon=polygon,
                support_face_areas=face_areas,support_plane_residuals=support_residuals,
                native_core_plane_residuals=core_plane_residuals,raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Platform, Y, Large':
  name='fw_unsc_c_plat_y_cross_large';_,source_bounds,original=source_markers(name);assert len(original)==2
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==9
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);rendered=all_render_rows[row['map'],row['palette_index']]
  assert abs(mesh[:,0].min()+2.5)<.000003 and abs(mesh[:,0].max()-2.5)<.000003
  assert abs(mesh[:,1].min()+mesh[:,1].max())<1e-6
  for axis,level,area,tolerance in ((0,2.5,1,.00001),(0,-2.5,.2,.00006),(2,0,4,.00002),(2,-.5,4,.00002)):
   assert any(abs(p['coordinate']-level)<tolerance and p['area']>area for p in rendered['axis_planes'][axis])
  # The main deck leaves corroborate both construction levels independently
  # of surface decoration: native convex top plus its authored skin.
  for leaf,level in ((1,0),(3,-.5)):
   shape=g['polyhedra'][leaf];vertices=np.asarray(shape['vertices'])
   assert abs(vertices[:,2].max()+shape['radius']-level)<1e-6
  sources=[(-2.456725835800171,-.09998290985822678,.7386285066604614),
           (2.543208360671997,-.09999240934848785,.2197987288236618)]
  assert original[0]['position'][2]>original[1]['position'][2]
  assert abs(original[0]['position'][0]-source_bounds[0])<.00002
  assert abs(original[1]['position'][0]-source_bounds[1])<.00008
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,source) in enumerate(zip(original,mapped,sources)):
   assert math.dist(before['position'],source)<1e-10
   side=1 if i==0 else -1;level=0 if i==0 else -.5;target=(side*2.5,0,level)
   assert math.dist(after['position'],target)<1e-10
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist((-old[0],-old[1],old[2]),new)<1e-6
   assert math.dist(rotation_axes(after['rotation'])[0],(side,0,0))<1e-6
   heights=[3-h for h in ray_hits((side*2,0,3),(0,0,-1),triangles)]
   assert heights and abs(max(heights)-level)<.00001
   residual=triangle_distance(target,triangles);assert residual<(.00001 if i==0 else .00007)
   evidence.append(dict(index=i,position=after['position'],outward_forward=[side,0,0],surface_residual=residual,main_deck_heights=heights))
  rim_heights=[3-h for h in ray_hits((-2.49,0,3),(0,0,-1),triangles)]
  assert abs(max(rim_heights)+.462387677093)<1e-10
  result.update(status='verified',reason='Both original end/high-low roles and complete bases rotated 180 degrees onto independently measured centered end planes and main deck levels; actual deck sections, lower entrance rim and all nine native collision leaves checked',
                anchors=evidence,compound=compound,contact_spacing=[5,.5],lower_end_rim_height=max(rim_heights),raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Block, 1x1 Tall':
  name='fw_unsc_c_plat_1x1_tall';_,source_bounds,original=source_markers(name);assert len(original)==9
  assert math.dist(source_bounds,(-.5,.5,-.5,.5,-1.5,1.5))<1e-8
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==1
  shape=g['polyhedra'][0];core=np.array(axis_box(shape['vertices'],shape['planes']));skin=shape['radius']
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);rendered=all_render_rows[row['map'],row['palette_index']]
  # The outer substantial vertical rib planes are the mating references;
  # the thin raised decoration and inset caps are accounted for separately.
  bounds=[]
  for axis in (0,1):
   candidates=[p['coordinate'] for p in rendered['axis_planes'][axis] if p['area']>.1]
   bounds.append([min(candidates),max(candidates)])
  bounds.append([float(mesh[:,2].min()),float(mesh[:,2].max())]);bounds=np.array(bounds)
  assert np.max(abs(bounds-np.array([[-.50728,.50718],[-.50728,.50718],[-1,1.5]])))<1e-8
  for level in bounds[2]:assert any(abs(p['coordinate']-level)<1e-8 and p['area']>.58 for p in rendered['axis_planes'][2])
  collision_envelope=core+[-skin,skin]
  assert np.max(abs(collision_envelope-bounds))<.001
  relief=np.maximum(bounds[:,0]-mesh.min(0),mesh.max(0)-bounds[:,1]);assert np.max(relief)<.0019
  center=bounds.mean(1);roles=[(1,1,0),(0,1,0),(1,0,0),(0,0,0),(0,0,1),(1,0,1),(0,1,1),(1,1,1)]
  assert set(roles)==set(itertools.product((0,1),(0,1),(0,1)))
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after) in enumerate(zip(original,mapped)):
   if i<8:
    axis,side,tier=roles[i];source=np.array([0.,0.,source_bounds[4+tier]]);source[axis]=source_bounds[2*axis+side]
    assert math.dist(before['position'],source)<.000448
    target=center.copy();target[axis]=bounds[axis,side];target[2]=bounds[2,tier]
    normal=np.zeros(3);normal[axis]=2*side-1
   else:
    assert math.dist(before['position'],(0,0,1.5))<1e-10
    target=center.copy();target[2]=bounds[2,1];normal=np.array([0,0,1])
   assert math.dist(after['position'],target)<1e-10
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   assert math.dist(rotation_axes(after['rotation'])[0],normal)<1e-6
   residual=triangle_distance(target,triangles)
   assert .0059<residual<.00591 if i<8 else .00438<residual<.00439
   evidence.append(dict(index=i,position=after['position'],outward_forward=normal.tolist(),surface_residual=residual))
  # Independent mesh sections corroborate all four vertical faces and the
  # deliberate top-center recess beneath the shared cap construction plane.
  for axis in (0,1):
   origin=np.array([center[0],center[1],0.]);origin[axis]=-2;direction=np.zeros(3);direction[axis]=1
   crossings=[-2+h for h in ray_hits(origin,direction,triangles)]
   assert len(crossings)==2 and math.dist(crossings,bounds[axis])<.000004
  center_heights=[3-h for h in ray_hits((center[0],center[1],3),(0,0,-1),triangles)]
  assert len(center_heights)==4 and abs(max(center_heights)-1.495613031205)<1e-10
  result.update(status='verified',reason='All nine original side/tier/top-center roles and full cardinal bases map to independently measured outer rib planes and cap heights; complete native box and radius, four actual side sections, top-center recess and decorative relief checked',
                anchors=evidence,compound=compound,contact_spacing=(bounds[:,1]-bounds[:,0]).tolist(),
                construction_planes=bounds.tolist(),decoration_beyond_planes=relief.tolist(),
                center_surface_heights=center_heights,raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Wall Curve Short':
  name='fw_unsc_c_wall_curve_short';_,source_bounds,original=source_markers(name);assert len(original)==8
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g)
  assert len(g['polyhedra'])==3 and all(len(s['vertices'])==8 and len(s['planes'])==6 for s in g['polyhedra'])
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3)
  cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);lengths=np.linalg.norm(cross,axis=1)
  normals=np.divide(cross,lengths[:,None],out=np.zeros_like(cross),where=lengths[:,None]>0)
  # Derive the positive end's dominant vertical cap plane from actual mesh
  # triangles, independently of the adapter's reviewed yaw and coordinates.
  groups={}
  for i,(tri,normal,length) in enumerate(zip(triangles,normals,lengths)):
   if normal[1]<0:normal=-normal
   if length<1e-8 or normal[1]<.98 or normal[0]<.1 or abs(normal[2])>1e-5 or tri[:,1].min()<1:continue
   key=tuple(np.round(normal,4))+(round(float(tri[0]@normal),4),)
   groups.setdefault(key,[]).append(i)
  indices=max(groups.values(),key=lambda ids:lengths[ids].sum())
  assert len(indices)==4 and lengths[indices].sum()/2>.21
  cap_normal=np.sum(normals[indices]*np.sign(normals[indices,1])[:,None]*lengths[indices,None],axis=0)
  cap_normal/=np.linalg.norm(cap_normal);assert abs(cap_normal[2])<1e-12
  ends={}
  for side in (-1,1):
   normal=cap_normal*np.array([1,side,1]);tangent=np.array([normal[1]*side,-normal[0]*side,0])
   caps=triangles[(abs(normals@normal)>1-1e-6)&(np.min(triangles@normal,axis=1)>1)]
   assert len(caps)==12
   vertices=caps.reshape(-1,3);distance=float((vertices@normal).max());ts=vertices@tangent
   extents=[float(ts.min()),float(ts.max())]
   assert abs(extents[1]-extents[0]-.1717123562307115)<1e-10
   # The virtual end rectangle spans all parallel cap strips, including the
   # recessed sides. Every rendered vertex must remain behind its support.
   assert float((mesh@normal).max())-distance<1e-10
   ends[side]=(normal,tangent,distance,extents)
  levels=[float(mesh[:,2].min()),float(mesh[:,2].max())]
  assert abs(levels[0]-source_bounds[4])<.0001 and abs(levels[1]-source_bounds[5])<.003
  sources=[(-.076402656734,-1.100000023842,-.997333407402),(.097702242434,1.047849535942,-.997333407402),
           (-.076402656734,-1.100000023842,1.002667427063),(.097702242434,1.047849535942,1.002667427063),
           (-.078816287220,1.100000023842,-.997333228588),(-.078816287220,1.100000023842,1.002667069435),
           (.100000001490,-1.047388195992,1.002667427063),(.100000001490,-1.047388195992,-.997333407402)]
  roles=[(-1,0,0),(1,1,0),(-1,0,1),(1,1,1),(1,0,0),(1,0,1),(-1,1,1),(-1,1,0)]
  assert set(roles)==set(itertools.product((-1,1),(0,1),(0,1)))
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,source,(side,corner,tier)) in enumerate(zip(original,mapped,sources,roles)):
   assert math.dist(before['position'],source)<1e-10
   normal,tangent,distance,extents=ends[side]
   target=normal*distance+tangent*extents[corner];target[2]=levels[tier]
   assert math.dist(after['position'],target)<1e-10
   source_axes=rotation_axes(before['rotation']);assert math.dist(source_axes[2],(0,0,1))<1e-6
   correction=math.degrees(math.acos(np.clip(np.dot(source_axes[0],normal),-1,1)))
   assert 5<correction<6
   expected_axes=[normal,(-normal[1],normal[0],0),(0,0,1)]
   for expected,actual in zip(expected_axes,rotation_axes(after['rotation'])):assert math.dist(expected,actual)<1e-6
   residual=triangle_distance(target,triangles);assert .0307<residual<.031
   evidence.append(dict(index=i,position=after['position'],outward_forward=normal.tolist(),
                        end=side,tangential_corner=corner,tier=tier,yaw_correction_degrees=correction,
                        surface_residual=residual))
  result.update(status='verified',reason='All eight original end/corner/tier roles map onto independently derived actual cap supports and parallel-strip extents; complete upright bases follow the measured end angle; full mesh lies behind each support; existing recess/bevel clearances and all three native collision hulls preserved',
                anchors=evidence,compound=compound,contact_spacing=[ends[1][3][1]-ends[1][3][0],levels[1]-levels[0]],
                cap_supports=[dict(side=side,normal=ends[side][0].tolist(),distance=ends[side][2],tangential_extents=ends[side][3]) for side in (-1,1)],
                raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Base Strut':
  name='fw_unsc_c_base_strut';_,source_bounds,original=source_markers(name);assert len(original)==7
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g)
  assert len(g['polyhedra'])==1 and len(g['polyhedra'][0]['vertices'])==12 and len(g['polyhedra'][0]['planes'])==8
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);rendered=all_render_rows[row['map'],row['palette_index']]
  assert abs(source_bounds[5]-.1-mesh[:,2].max())<1e-6
  base=float(mesh[:,2].min());assert abs(base+1.991763830)<1e-8
  shape=g['polyhedra'][0];vertices=np.asarray(shape['vertices']);skin=2*shape['radius']
  assert abs(vertices[:,1].max()+skin-.8)<1e-6 and abs(vertices[:,2].max()+skin-2.2)<1e-6
  for axis,level,area in ((1,.8,2.3),(2,base,.94),(2,2.2,.21)):
   assert any(abs(p['coordinate']-level)<.00003 and p['area']>area for p in rendered['axis_planes'][axis])
  sources=[(0,0,-1.923830390),(0,1.049024582,-.395133317),(.0000016085,1.049026251,1.367932677),
           (0,.532705665,-1.760525465),(0,-.531080604,-1.758913755),
           (.478488356,.000812531,-1.759719849),(-.478488356,.000812531,-1.759719610)]
  foot_height=sum(p['position'][2] for p in original[3:])/4-.1
  assert max(abs(p['position'][2]-.1-foot_height) for p in original[3:])<.00081
  foot_y=[-2+hit for hit in ray_hits((0,-2,foot_height),(0,1,0),triangles)];assert len(foot_y)==2
  center_y=sum(foot_y)/2
  foot_x=[-2+hit for hit in ray_hits((-2,center_y,foot_height),(1,0,0),triangles)];assert len(foot_x)==2
  assert abs(center_y+.248411330)<1e-8
  expected=[(0,-.25,base),(0,.8,original[1]['position'][2]-.1),(0,.8,original[2]['position'][2]-.1),
            (0,foot_y[1],foot_height),(0,foot_y[0],foot_height),
            (foot_x[1],center_y,foot_height),(foot_x[0],center_y,foot_height)]
  forwards=[(0,0,-1),(0,1,0),(0,1,0),(0,1,0),(0,-1,0),(1,0,0),(-1,0,0)]
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,source,target,forward) in enumerate(zip(original,mapped,sources,expected,forwards)):
   assert math.dist(before['position'],source)<1e-8 and math.dist(after['position'],target)<1e-8
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   assert math.dist(rotation_axes(after['rotation'])[0],forward)<1e-6
   residual=triangle_distance(target,triangles);assert residual<(.000025 if i in (1,2) else 1e-8)
   evidence.append(dict(index=i,position=after['position'],authored_forward=forward,surface_residual=residual))
  result.update(status='verified',reason='All seven original base/front/foot roles and complete cardinal frames checked; actual base/front planes and top-origin shift independently witnessed; common foot tier derived from source roles and all four perimeter points independently intersected with the mesh; complete native hull resolved',
                anchors=evidence,compound=compound,contact_spacing=[foot_x[1]-foot_x[0],foot_y[1]-foot_y[0]],
                foot_height=foot_height,native_bottom_clearance=base-(vertices[:,2].min()-skin),raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Antenna':
  name='fw_unsc_c_antenna';_,source_bounds,original=source_markers(name);assert len(original)==3
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==4
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);rendered=all_render_rows[row['map'],row['palette_index']]
  target_bounds=np.c_[mesh.min(0),mesh.max(0)]
  rotated_bounds=np.array([[source_bounds[2],source_bounds[3]],[-source_bounds[1],-source_bounds[0]],source_bounds[4:6]])
  assert np.max(np.abs(target_bounds-rotated_bounds))<.000001
  sources=[(.00006605697854,-.69240415096283,.59457671642303),
           (.00006605697854,.50416982173920,.59457671642303),(0,0,0)]
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,source) in enumerate(zip(original,mapped,sources)):
   assert math.dist(before['position'],source)<1e-10
   target=np.array([source[1],-source[0],source[2]])
   assert math.dist(after['position'],target)<1e-10
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):
    assert math.dist((old[1],-old[0],old[2]),new)<1e-6
   residual=triangle_distance(target,triangles);detail={}
   if i<2:
    assert math.dist(rotation_axes(after['rotation'])[0],(-1 if i==0 else 1,0,0))<1e-6
    faces=triangles[np.max(np.abs(triangles[:,:,0]-target[0]),axis=1)<.00003]
    assert len(faces)==8
    cross=np.cross(faces[:,1]-faces[:,0],faces[:,2]-faces[:,0]);area=float(np.linalg.norm(cross,axis=1).sum()/2)
    assert area>(.0039 if i==0 else .013)
    # Intersect each real cap triangle with the anchor's lateral coordinate.
    # Both cap strips must bracket its Z; the gap itself is intentional.
    intervals=[]
    for tri in faces:
     heights=[]
     for a,b in zip(tri,np.roll(tri,-1,axis=0)):
      if abs(b[1]-a[1])<1e-12:continue
      fraction=(target[1]-a[1])/(b[1]-a[1])
      if 0<=fraction<=1:heights.append(float(a[2]+fraction*(b[2]-a[2])))
     if len(heights)>=2:intervals.append([min(heights),max(heights)])
    below=[p for p in intervals if p[1]<target[2]];above=[p for p in intervals if p[0]>target[2]]
    assert below and above and len(below)+len(above)==len(intervals)
    lower=max(p[1] for p in below);upper=min(p[0] for p in above)
    expected_gap=(.5699645711,.6299495865) if i==0 else (.5590582047,.6408559530)
    assert abs(lower-expected_gap[0])<.000002 and abs(upper-expected_gap[1])<.000002
    assert .011<residual<.016
    detail=dict(cap_area=area,cap_sections=intervals,opening_vertical_limits=[lower,upper])
   else:
    assert residual<1e-10 and math.dist(rotation_axes(after['rotation'])[0],(0,0,-1))<1e-6
    assert any(abs(p['coordinate'])<1e-8 and p['area']>.03 for p in rendered['axis_planes'][2])
   evidence.append(dict(index=i,position=after['position'],surface_residual=residual,**detail))
  result.update(status='verified',reason='All three original roles and full frames rotated -90 degrees; complete rotated source bounds agree with target; actual cap-strip cross-sections bracket both authored opening references and the base lies on the actual zero plane; all four native leaves resolved',
                anchors=evidence,compound=compound,contact_spacing=[sources[1][1]-sources[0][1]],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Bunker Full':
  name='fw_unsc_c_bunker_full';_,source_bounds,original=source_markers(name);assert len(original)==4
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==26
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);rendered=all_render_rows[row['map'],row['palette_index']]
  root2=math.sqrt(2);forward=np.array([1,1,0])/root2;left=np.array([-1,1,0])/root2
  axial=mesh@forward;transverse=mesh@left;u_bounds=[float(axial.min()),float(axial.max())];v_center=float((transverse.min()+transverse.max())/2)
  assert abs(u_bounds[0]+1.138054188)<1e-8 and abs(u_bounds[1]-1.573972338)<1e-8
  assert abs(v_center-.000156786)<1e-8
  assert abs(mesh[:,2].min()+.9)<1e-6 and abs(mesh[:,2].max()-1.1)<1e-6
  for level,area in ((-.9,10),(1.1,3)):
   assert any(abs(p['coordinate']-level)<.00004 and p['area']>area for p in rendered['axis_planes'][2])
  sources=[(1.238833189,0,-.862215877),(-1.455514550,0,1.123533726),
           (-1.455514550,0,-.862870693),(1.236630678,0,1.128429055)]
  roles=[(1,0),(0,1),(0,0),(1,1)];mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  assert set(roles)==set(itertools.product((0,1),(0,1)))
  for i,(before,after,source,(end,tier)) in enumerate(zip(original,mapped,sources,roles)):
   assert math.dist(before['position'],source)<1e-8
   # The original roles lie at both source axial extremes and both height
   # extremes, with all four source frames deliberately facing the same way.
   assert abs(before['position'][0]-source_bounds[end])<.003
   assert abs(before['position'][2]-source_bounds[4+tier])<.006
   assert math.dist(rotation_axes(before['rotation'])[0],(1,0,0))<1e-6
   target=forward*u_bounds[end]+left*v_center;target[2]=1.1 if tier else -.9
   assert math.dist(after['position'],target)<1e-8
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):
    assert math.dist(((old[0]-old[1])/root2,(old[0]+old[1])/root2,old[2]),new)<1e-6
   assert math.dist(rotation_axes(after['rotation'])[0],forward)<1e-6
   support_normal=forward*(2*end-1)
   assert np.max((mesh-target)@support_normal)<1e-10
   # Probe the local top and bottom inside the end bevel. This distinguishes
   # the end roof reference from the recessed central roof panel.
   inside=target-support_normal*.05;inside[2]=3
   heights=[3-hit for hit in ray_hits(inside,(0,0,-1),triangles)]
   assert abs(min(heights)+.9)<1e-6 and abs(max(heights)-1.1)<.00004
   residual=triangle_distance(target,triangles)
   assert .028<residual<.0282 if end else .016<residual<.0175
   evidence.append(dict(index=i,position=after['position'],support_normal=support_normal.tolist(),
                        authored_forward=forward.tolist(),surface_residual=residual,local_heights=heights))
  result.update(status='verified',reason='Four original end/tier roles map onto independently measured diagonal support planes and local floor/roof references; 45-degree rotation and complete original frames retained, including common forward at both ends; whole render half-spaces, end bevel residuals and all 26 native leaves checked',
                anchors=evidence,compound=compound,contact_spacing=[u_bounds[1]-u_bounds[0],2],diagonal_bounds=u_bounds,transverse_center=v_center,raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Teleport Frame':
  name='fw_unsc_c_teleporter_frame';_,_,original=source_markers(name);assert len(original)==4
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==4
  assert len(g['polyhedra'][0]['vertices'])==24 and len(g['polyhedra'][0]['planes'])==22
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);bounds=np.c_[mesh.min(0),mesh.max(0)]
  expected_bounds=np.array([[-.7108675241470337,.7108675241470337],[-.6881840825080872,.6900004744529724],[-.08347351104021072,1.2165788412094116]])
  assert np.max(np.abs(bounds-expected_bounds))<1e-8
  # Establish that these extrema belong to the base, not the upper frame.
  base_triangles=triangles[np.max(triangles[:,:,2],axis=1)<.11];base_vertices=base_triangles.reshape(-1,3)
  assert np.max(np.abs(np.c_[base_vertices[:,:2].min(0),base_vertices[:,:2].max(0)]-bounds[:2]))<.00003
  rendered=all_render_rows[row['map'],row['palette_index']]
  assert any(abs(p['coordinate']-bounds[2,0])<.00001 and p['area']>1.7 for p in rendered['axis_planes'][2])
  center=bounds.mean(1);roles=[(1,1),(0,0),(1,0),(0,1)]
  sources=[(0,.7,0),(-.9,-.000909,0),(0,-.7,0),(.9,-.000908,0)]
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,source,(axis,side)) in enumerate(zip(original,mapped,sources,roles)):
   target=center.copy();target[axis]=bounds[axis,side];target[2]=bounds[2,0]
   assert math.dist(before['position'],source)<1e-7 and math.dist(after['position'],target)<1e-8
   normal=np.zeros(3);normal[axis]=2*side-1
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   assert math.dist(rotation_axes(after['rotation'])[0],normal)<1e-6
   assert np.max((mesh-target)@normal)<1e-10
   residual=triangle_distance(target,base_triangles);assert residual<(.00003 if axis==0 else .00047)
   evidence.append(dict(index=i,position=after['position'],outward_forward=normal.tolist(),base_surface_residual=residual))
  result.update(status='verified',reason='All four original cardinal base roles and complete frames checked; extrema independently belong to actual base triangles; whole render support half-spaces, common bottom face, measured center and small base bevel residuals verified; complete four-leaf native compound resolved',
                anchors=evidence,compound=compound,contact_spacing=(bounds[:2,1]-bounds[:2,0]).tolist(),raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Corner, 45 Degrees':
  name='fw_unsc_c_plat_2x2_45';_,_,original=source_markers(name);assert len(original)==4
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==6
  # The two-unit angled entrance runs from A to B. The adjacent outer
  # edge is at 45 degrees and meets the straight entrance's lower end.
  root2=math.sqrt(2);a=np.array([-.4,1]);b=a+np.array([root2,-root2]);c=np.array([b[0]-b[1]-1,-1])
  polygon=[a,b,c,np.array([-.4,-1])];base=g['polyhedra'][0];skin=base['radius']
  core_xy=[a+[skin,-skin],b+[-skin,skin],c+[-skin,skin],polygon[3]+[skin,skin]]
  expected_vertices=[(xy[0],xy[1],z) for xy in core_xy for z in (skin,.2-skin)]
  assert len(base['vertices'])==8 and len(base['planes'])==6
  assert max(min(math.dist(v,p) for v in base['vertices']) for p in expected_vertices)<.000005
  expected_planes=[(0,0,-1,skin),(0,0,1,-.2+skin)]
  for start,end in zip(core_xy,core_xy[1:]+core_xy[:1]):
   delta=end-start;normal=np.array([-delta[1],delta[0]])/np.linalg.norm(delta)
   expected_planes.append((*normal,0,-normal@start))
  assert max(min(math.dist(p,q) for p in base['planes']) for q in expected_planes)<.00005
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);rendered=all_render_rows[row['map'],row['palette_index']]
  for axis,level,area in ((0,-.4,.49),(2,0,.59),(2,.2,.50)):
   assert any(abs(p['coordinate']-level)<.00001 and p['area']>area for p in rendered['axis_planes'][axis])
  centers=[(-.4,0),tuple((a+b)/2)];normals=[(-1,0,0),(1/root2,1/root2,0)]
  assert abs(np.linalg.norm(b-a)-2)<1e-12
  expected=[(*centers[0],.2),(*centers[1],.2),(*centers[0],.05),(*centers[1],.05)]
  sources=[(.897286594,0,.0000947),(.043316085,-.353413612,.000100351),
           (.897286594,0,-.149869904),(.043316085,-.353413612,-.149869904)]
  cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);lengths=np.linalg.norm(cross,axis=1)
  mesh_normals=np.divide(cross,lengths[:,None],out=np.zeros_like(cross),where=lengths[:,None]>0)
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,source,target) in enumerate(zip(original,mapped,sources,expected)):
   normal=np.asarray(normals[i%2]);assert math.dist(before['position'],source)<1e-8
   assert math.dist(after['position'],target)<1e-8
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):
    assert math.dist((-old[0],-old[1],old[2]),new)<1e-6
   assert math.dist(rotation_axes(after['rotation'])[0],normal)<1e-6
   face=triangles[np.abs(mesh_normals@normal)>1-1e-6]
   assert triangle_distance((target[0],target[1],.1),face)<.00002
   assert np.max((mesh-np.asarray(target))@normal)<.00006
   inside=np.asarray(target)-normal*.04;inside[2]=2
   heights=[2-hit for hit in ray_hits(inside,(0,0,-1),triangles)]
   assert len(heights)==2 and abs(max(heights)-.2)<.000001 and abs(min(heights))<.000001
   residual=triangle_distance(target,triangles);assert residual<(.0069 if i<2 else .00002)
   evidence.append(dict(index=i,position=after['position'],outward_forward=normal.tolist(),surface_residual=residual,inside_heights=heights))
  result.update(status='verified',reason='Four original entrance/tier roles rotate onto two measured outward planes; equal two-unit entrance widths, complete base quad and skin-derived native topology, actual face sections and deck/base intersections, preserved .15 tier spacing and every marker basis independently checked',
                anchors=evidence,compound=compound,contact_spacing=[2,2,.15],construction_polygon=[p.tolist() for p in polygon],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Corner, 4x4':
  name='fw_unsc_c_plat_4x4_corner';_,_,original=source_markers(name);assert len(original)==10
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==4
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);rendered=all_render_rows[row['map'],row['palette_index']]
  for axis,level,area in ((0,2,.7),(1,2,.7),(2,-.3,10),(2,-.1,9)):
   assert any(abs(p['coordinate']-level)<.00001 and p['area']>area for p in rendered['axis_planes'][axis])
  base=g['polyhedra'][0];v=np.asarray(base['vertices']);skin=base['radius']
  assert abs(v[:,0].max()+skin-2)<1e-6 and abs(v[:,1].max()+skin-2)<.000002
  assert abs(v[:,2].min()-skin+.3)<1e-6 and abs(v[:,2].max()+skin+.1)<1e-6
  sources=[(.3,-1.6,.2),(-1.7,-1.6,.03),(.3,-1.6,0),(-1.7,.4,0),(-1.7,.4,.2),
           (2.3,-1.6,.2),(-1.7,2.4,.2),(-1.7,-1.6,.2),(-1.7,-1.6,.2),(-1.7,-1.6,.03)]
  expected=[(0,2,-.1),(2,2,-.27),(0,2,-.3),(2,0,-.3),(2,0,-.1),
            (-2,2,-.1),(2,-2,-.1),(2,2,-.1),(2,2,-.1),(2,2,-.27)]
  axes=[1,0,1,0,0,1,0,1,0,1]
  cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);lengths=np.linalg.norm(cross,axis=1)
  normals=np.divide(cross,lengths[:,None],out=np.zeros_like(cross),where=lengths[:,None]>0)
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,source,target,axis) in enumerate(zip(original,mapped,sources,expected,axes)):
   assert math.dist(before['position'],source)<.000005 and math.dist(after['position'],target)<1e-8
   normal=np.zeros(3);normal[axis]=1
   assert math.dist(rotation_axes(after['rotation'])[0],normal)<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):
    assert math.dist((-old[0],-old[1],old[2]),new)<1e-6
   assert np.max((mesh-np.asarray(target))@normal)<.000003
   face=triangles[np.abs(normals[:,axis])>1-1e-6]
   section=[target[0],target[1],-.2]
   if i in (5,6):section[1-axis]+=.03 # Probe inside the .02 end chamfer.
   assert triangle_distance(section,face)<.00001
   residual=triangle_distance(target,triangles);assert residual<(.000005 if i in (1,9) else .0143)
   evidence.append(dict(index=i,position=after['position'],outward_forward=normal.tolist(),surface_residual=residual))
  result.update(status='verified',reason='All ten original midpoint/end/corner roles rotate onto the actual positive X/Y mating faces; full render support half-spaces, deck/base planes, preserved .03 corner tier, four native leaves, corresponding face sections and complete rotated frames independently checked',
                anchors=evidence,compound=compound,contact_spacing=[4,4,.2],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Corner, 2x2':
  name='fw_unsc_c_plat_2x2_corner';_,_,original=source_markers(name);assert len(original)==10
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==1
  shape=g['polyhedra'][0];vertices=shape['vertices'];planes=shape['planes'];a=1-shape['radius']
  assert len(vertices)==10 and len(planes)==7
  polygon=[(-1,0),(0,-1),(1,-1),(1,1),(-1,1)]
  core_z=[.0164,.1783925];expected_vertices=[(a*x,a*y,z) for x,y in polygon for z in core_z]
  assert max(min(math.dist(v,p) for v in vertices) for p in expected_vertices)<1e-6
  expected_planes=[(0,0,-1,core_z[0]),(0,0,1,-core_z[1])]
  for start,end in zip(polygon,polygon[1:]+polygon[:1]):
   dx,dy=end[0]-start[0],end[1]-start[1];length=math.hypot(dx,dy);nx,ny=dy/length,-dx/length
   expected_planes.append((nx,ny,0,-a*(nx*start[0]+ny*start[1])))
  assert max(min(math.dist(p,q) for p in planes) for q in expected_planes)<1e-6
  triangles=actual_triangles(row);rendered=all_render_rows[row['map'],row['palette_index']]
  for axis,level,area in ((0,-1,.15),(0,1,.3),(1,-1,.15),(1,1,.3),(2,0,1.7),(2,.2,1.6)):
   assert any(abs(p['coordinate']-level)<.00001 and p['area']>area for p in rendered['axis_planes'][axis])
  cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);lengths=np.linalg.norm(cross,axis=1)
  normals=np.divide(cross,lengths[:,None],out=np.zeros_like(cross),where=lengths[:,None]>0)
  diag=np.array([-1/math.sqrt(2),-1/math.sqrt(2),0])
  diagonal=triangles[(np.abs(normals@diag)>1-1e-6)&(np.max(np.abs(triangles[:,:,0]+triangles[:,:,1]+1),axis=1)<.0001)]
  assert len(diagonal)>0
  xy=[(-1,.5),(0,1),(1,0),(.5,-1),(-.5,-.5)]
  expected=[(*p,0) for p in xy]+[(*p,.2) for p in reversed(xy)]
  outward=[(-1,0,0),(0,1,0),(1,0,0),(0,-1,0),tuple(diag)]
  outward=outward+list(reversed(outward));mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,target,normal) in enumerate(zip(original,mapped,expected,outward)):
   assert math.dist(before['position'],target)<.0000002 and math.dist(after['position'],target)<1e-8
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   assert math.dist(rotation_axes(after['rotation'])[0],normal)<1e-6
   residual=triangle_distance(target,triangles);assert .013<residual<.0142
   # The .02 edge bevel retreats from the construction-plane intersection;
   # require the corresponding vertical face at mid-height independently.
   face=triangles[np.abs(normals@np.asarray(normal))>1-1e-6]
   assert triangle_distance((target[0],target[1],.1),face)<.00002
   evidence.append(dict(index=i,position=after['position'],outward_forward=normal,surface_residual=residual))
  result.update(status='verified',reason='Complete ten-vertex/seven-plane native pentagonal prism reconstructed; actual five side faces and both construction heights independently checked; all ten edge-midpoint roles and full authored frames retained with bounded noise removal',
                anchors=evidence,compound=compound,contact_spacing=[2,2,.2],native_core_top=core_z[1],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Brace':
  name='fw_unsc_c_brace';_,_,original=source_markers(name);assert len(original)==6
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==10
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);rendered=all_render_rows[row['map'],row['palette_index']]
  bottom=float(mesh[:,2].min());top=max(3-h for h in ray_hits((0,0,3),(0,0,-1),triangles))
  assert abs(bottom+1.500693321)<1e-8 and abs(top-1.499263286)<1e-8
  foot_triangles=triangles[np.max(np.abs(triangles[:,:,2]-bottom),axis=1)<1e-6]
  centers=[]
  for sign in (-1,1):
   foot=foot_triangles[np.all(foot_triangles[:,:,1]*sign>0,axis=1)].reshape(-1,3)
   center=(foot[:,1].min()+foot[:,1].max())/2;assert abs(center-sign*.9)<.00004
   assert abs(foot[:,1].max()-foot[:,1].min()-.57)<.00001
   centers.append(float(center))
  for axis,level,area in ((0,-.25,3),(0,.25,2),(0,-.05,.04),(0,.05,.04),(2,bottom,.5),(2,top,.12)):
   assert any(abs(p['coordinate']-level)<.00002 and p['area']>area for p in rendered['axis_planes'][axis])
  source_expected=[(.1,0,1.79388678),(-.1,.95,-1.20611501),(-.1,-.893625736,-1.20611501),
                   (.4,-.95,-1.20611501),(.4,.95,-1.20611501),(.2,0,1.79388678)]
  expected=[(-.05,0,top),(-.25,.9,bottom),(-.25,-.9,bottom),(.25,-.9,bottom),(.25,.9,bottom),(.05,0,top)]
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);lengths=np.linalg.norm(cross,axis=1)
  normals=np.divide(cross,lengths[:,None],out=np.zeros_like(cross),where=lengths[:,None]>0)
  x_faces=triangles[np.abs(normals[:,0])>.99999]
  for i,(before,after,source,target) in enumerate(zip(original,mapped,source_expected,expected)):
   assert math.dist(before['position'],source)<.00001 and math.dist(after['position'],target)<1e-7
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   assert math.dist(rotation_axes(after['rotation'])[0],(-1 if i<3 else 1,0,0))<1e-6
   residual=triangle_distance(target,triangles);face_residual=triangle_distance(target,x_faces)
   if i in (0,5):assert residual<.00002 and face_residual<.00002
   else:assert .0105<residual<.0107 and face_residual<.0151
   evidence.append(dict(index=i,position=after['position'],surface_residual=residual,face_residual=face_residual))
  result.update(status='verified',reason='All six authored top/foot roles and complete frames checked against actual thin/thick face planes; flat bottom patches independently establish both foot centers; top height obtained from mesh intersection; all ten native leaves resolved with existing bevels retained',
                anchors=evidence,compound=compound,contact_spacing=[.5,.1,1.8,top-bottom],foot_centers=centers,raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Crenel Full':
  name='fw_unsc_c_crenel_full';_,_,original=source_markers(name);assert len(original)==4
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==2
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);rendered=all_render_rows[row['map'],row['palette_index']]
  for axis,level,area in ((0,-1,.15),(0,1,.15),(1,.1,1.8),(2,-.8,.29),(2,.5,.08)):
   assert any(abs(p['coordinate']-level)<.00004 and p['area']>area for p in rendered['axis_planes'][axis])
  # Each native hull uses the same principal front plane; the broad upper
  # hull supplies the outer sides/top and the lower foot the bottom.
  for i,shape in enumerate(g['polyhedra']):
   vertices=np.asarray(shape['vertices']);skin=2*shape['radius']
   assert abs(vertices[:,1].max()+skin-.1)<1e-6
   if i==0:
    assert abs(vertices[:,0].min()-skin+1)<.00007 and abs(vertices[:,0].max()+skin-1)<1e-6
    assert abs(vertices[:,2].max()+skin-.5)<.000002
   else:assert abs(vertices[:,2].min()-skin+.8)<1e-6
  expected=[(0,0,-.8),(-1,.1,0),(1,.1,0),(0,0,.5)]
  sources=[(.000146704,-.000176533,-.882824302),(-1.250038505,.114999577,-.000752911),
           (1.244218111,.125000194,-.007755979),(.000146704,-.000176533,.748609722)]
  normals=[(0,0,-1),(-1,0,0),(1,0,0),(0,0,1)]
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,target,source,normal) in enumerate(zip(original,mapped,expected,sources,normals)):
   assert math.dist(before['position'],source)<1e-8 and math.dist(after['position'],target)<1e-8
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   assert math.dist(rotation_axes(after['rotation'])[0],normal)<1e-6
   residual=triangle_distance(target,triangles);assert residual<(.000001 if i==0 else .0041 if i<3 else .0051)
   assert np.max((mesh-target)@np.asarray(normal))<.00007
   evidence.append(dict(index=i,position=after['position'],outward_forward=normal,surface_residual=residual))
  result.update(status='verified',reason='All four original outward face roles and full frames retained; target outer X/Z and principal front planes independently witnessed by mesh and both native hulls; complete render support envelope and bevel residuals checked',
                anchors=evidence,compound=compound,contact_spacing=[2,1.3],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Column':
  name='fw_unsc_c_column';_,_,original=source_markers(name);assert len(original)==8
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g)
  assert len(g['polyhedra'])==1 and g['bodies'][0]['shape_type']==4
  shape=g['polyhedra'][0];core=np.asarray(axis_box(shape['vertices'],shape['planes']))
  bounds=np.array([[-.15,.15],[-.15,.15],[0,1]])
  assert np.max(np.abs(core+np.array([-2*shape['radius'],2*shape['radius']])-bounds))<1e-6
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);rendered=all_render_rows[row['map'],row['palette_index']]
  assert np.max(np.abs(np.c_[mesh.min(0),mesh.max(0)]-bounds))<1e-6
  for axis in range(3):
   for level in bounds[axis]:
    assert any(abs(p['coordinate']-level)<.00001 and p['area']>.04 for p in rendered['axis_planes'][axis])
  source_expected=[(.2,-.046875,1),(-.1,-.046875,1),(.0312347412,-.2,1),(.0312347412,.1,-.00215190975),
                   (-.1,-.046875,-.00215190975),(.2,-.046875,-.00215190975),(.0312347412,.1,1),(.0312347412,-.2,-.00215190975)]
  roles=[(0,1,1),(0,-1,1),(1,-1,1),(1,1,0),(0,-1,0),(0,1,0),(1,1,1),(1,-1,0)]
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  assert set(roles)==set(itertools.product((0,1),(-1,1),(0,1)))
  for i,(before,after,source,(axis,side,tier)) in enumerate(zip(original,mapped,source_expected,roles)):
   assert math.dist(before['position'],source)<1e-7
   target=np.array([0.,0.,tier]);target[axis]=side*.15
   assert math.dist(after['position'],target)<1e-7
   normal=np.zeros(3);normal[axis]=side
   axes=rotation_axes(after['rotation']);old_axes=rotation_axes(before['rotation'])
   assert math.dist(axes[0],normal)<1e-6 and math.dist(axes[2],(0,0,1))<1e-6
   assert math.dist(old_axes[2],(0,0,1))<1e-6
   error=math.degrees(math.atan2(np.linalg.norm(np.cross(old_axes[0],normal)),np.dot(old_axes[0],normal)))
   assert abs(error-4.5619)<.0002 if i in (6,7) else error<.001
   residual=triangle_distance(target,triangles);assert .007<residual<.0071
   assert np.max((mesh-target)@normal)<1e-7
   # The target uses a .01-unit edge bevel; the marker denotes the
   # intersection of its two independently witnessed construction planes.
   evidence.append(dict(index=i,position=after['position'],outward_forward=normal.tolist(),
                        source_normal_error_degrees=error,beveled_edge_residual=residual))
  result.update(status='verified',reason='All eight original side/tier roles map to the measured .3 by .3 by 1 construction box; complete convex core and two-radius skin, all six actual face planes and envelope checked; two reviewed source yaw errors corrected to target face normals',
                anchors=evidence,compound=compound,contact_spacing=[.3,.3,1],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Crenel Notch':
  name='fw_unsc_c_crenel_notch';_,source_bounds,original=source_markers(name);assert len(original)==4
  assert np.max(np.abs(np.asarray(source_bounds)-[-.1,.1,-1.2,1.2,0,1]))<1e-6
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g);assert len(g['polyhedra'])==3
  base=g['polyhedra'][0];vertices=np.asarray(base['vertices']);core=np.c_[vertices.min(0),vertices.max(0)]
  assert len(vertices)==8 and len(base['planes'])==6
  profile=[(-.0672,-.3328),(0,-.4672),(.0672,-.4672),(.0672,-.3328)]
  expected_vertices=[(x,y,z) for x,z in profile for y in (-1.2172,1.2172)]
  assert max(min(math.dist(v,p) for v in vertices) for p in expected_vertices)<.000003
  assert np.max(np.abs(core+np.array([-2*base['radius'],2*base['radius']])-np.array([[-.1,.1],[-1.25,1.25],[-.5,-.3]])))<.000002
  triangles=actual_triangles(row);rendered=all_render_rows[row['map'],row['palette_index']]
  for axis,level,area in ((1,-1.25,.05),(1,1.25,.05),(2,-.5,.2)):
   assert any(abs(p['coordinate']-level)<.00006 and p['area']>area for p in rendered['axis_planes'][axis])
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after) in enumerate(zip(original,mapped)):
   assert abs(before['position'][0]-.05)<.000002
   if i<2:
    side=1 if i==0 else -1;assert math.dist(before['position'],(.05,side*1.2,0))<.000002
    target=(.05,side*1.25,-.5)
   else:
    assert abs(before['position'][2]-1)<1e-6
    y=before['position'][1];assert abs(y-(-.7749685049 if i==2 else .7858545184))<1e-7
    # Determine the upper height from actual mesh intersections, not from
    # the exported mapping or from the highest decorative vertex.
    heights=[2-hit for hit in ray_hits((.05,y,2),(0,0,-1),triangles)]
    assert len(heights)==2 and abs(min(heights)+.5)<1e-6
    target=(.05,y,max(heights));assert .50750<target[2]<.50751
   assert math.dist(after['position'],target)<1e-7
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   assert math.dist(rotation_axes(after['rotation'])[0],(0,1 if i==0 else -1,0))<1e-6
   residual=triangle_distance(target,triangles);assert residual<(.0057 if i<2 else 1e-7)
   evidence.append(dict(index=i,position=after['position'],surface_residual=residual,role='bottom end' if i<2 else 'upper surface'))
  result.update(status='verified',reason='Four original roles and complete authored frames checked; lower end spacing established by actual side planes and complete native tapered base prism; upper heights independently intersected with mesh at original lateral roles; all three compound leaves resolved',
                anchors=evidence,compound=compound,contact_spacing=[2.5,1.0075030530613407],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Arch Brace':
  name='fw_unsc_c_arch_brace';_,_,original=source_markers(name);assert len(original)==5
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g)
  assert len(g['polyhedra'])==19
  triangles=actual_triangles(row);rendered=all_render_rows[row['map'],row['palette_index']]
  for axis,coordinate,area in ((0,2.9,.2),(0,1.9,.2),(0,-1.9,.1),(1,-1.2,1),(1,1.2,1),(2,.9,3),(2,3.1,1)):
   assert any(abs(p['coordinate']-coordinate)<.00005 and p['area']>area for p in rendered['axis_planes'][axis])
  # Preserve the authored lateral position of the two side roles. Their
  # source depth is not the target width, so explicitly map those levels.
  lateral=.2-original[2]['position'][0]
  assert abs(lateral-(.2-original[3]['position'][0]))<1e-7
  source_expected=[(-2.7,-.05,4.1),(-1.7,-.05,1.9),(-.11271635,-1.22073317,.25007176),
                   (-.11271635,1.12429905,.25007176),(2.1,-.05,1.9)]
  expected=[(2.9,0,3.1),(1.9,0,.9),(lateral,1.2,-.75),(lateral,-1.2,-.75),(-1.9,0,.9)]
  forwards=[(1,0,0),(1,0,0),(0,1,0),(0,-1,0),(-1,0,0)]
  cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);lengths=np.linalg.norm(cross,axis=1)
  normals=np.divide(cross,lengths[:,None],out=np.zeros_like(cross),where=lengths[:,None]>0)
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,target,source,forward) in enumerate(zip(original,mapped,expected,source_expected,forwards)):
   assert math.dist(before['position'],source)<.0001
   assert math.dist(after['position'],target)<1e-8
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):
    assert math.dist((-old[0],-old[1],old[2]),new)<1e-6
   assert math.dist(rotation_axes(after['rotation'])[0],forward)<1e-6
   axis=1 if i in (2,3) else 0
   faces=triangles[np.abs(normals[:,axis])>.99999]
   residual=triangle_distance(target,faces);assert residual<.00012
   if i in (0,1):
    # Ledge height and end face must both meet at the same marker.
    assert triangle_distance(target,triangles[np.abs(normals[:,2])>.99999])<.00012
   if i in (2,3):
    # Side role lies on the bevel/vertical-face edge, not the top at -.7.
    bevels=triangles[(np.abs(normals[:,1])>.70)&(np.abs(normals[:,1])<.72)&(np.abs(normals[:,2])>.70)]
    assert triangle_distance(target,bevels)<.00008
    assert abs(rendered['referenced_bounds'][1][1 if i==2 else 0]-target[1])<.00004
   evidence.append(dict(index=i,position=after['position'],forward=forward,face_residual=residual))
  result.update(status='verified',reason='All five original roles map onto actual end/ledge or side/bevel intersections; explicit side-level mapping corrects the source inset; every rotated frame and all 19 native compound leaves resolved',
                anchors=evidence,compound=compound,contact_spacing=[2.4,2.2],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label'] in ('Bunker Covered','Bunker Low'):
  covered=row['label']=='Bunker Covered';name='fw_unsc_c_bunker_'+('covered' if covered else 'low')
  _,_,original=source_markers(name);assert len(original)==2
  g=geometry[row['map'],row['palette_index']]
  exceptions={} if covered else {10:(2,),11:(2,),14:(1,)}
  compound=identity_compound(g,plane_exceptions=exceptions)
  assert len(g['polyhedra'])==(37 if covered else 23)
  assert len(compound['planar_polygons'])==(9 if covered else 5)
  assert sum(p['vertices']==3 for p in compound['planar_polygons'])==(6 if covered else 1)
  base=-.5 if covered else -.35;expected=[(0,-1.2,base),(0,1.2,base+.5)]
  if not covered:
   # These three inconsistent stored planes belong to the native bottom/roof,
   # away from both entrance levels. Anchor positions below use actual render
   # surfaces; no conclusion relies on the inconsistent planes.
   for issue in compound['native_plane_inconsistencies']:
    shape=g['polyhedra'][issue['shape']]
    assert all(min(abs(v[2]-base),abs(v[2]-base-.5))>.1 for v in shape['vertices'])
    expected_violation=.01856949 if issue['shape']==14 else .17646449
    assert abs(issue['maximum_vertex_distances'][0]-expected_violation)<1e-6
  triangles=actual_triangles(row);rendered=all_render_rows[row['map'],row['palette_index']]
  for axis,coordinate,min_area in ((1,-1.2,.29),(1,1.2,.03),(2,base,.015),(2,base+.5,2.7)):
   assert any(abs(p['coordinate']-coordinate)<.00005 and p['area']>min_area
              for p in rendered['axis_planes'][axis]),(row['label'],axis,coordinate)
  mapped=[adapt(p,frames[name]) for p in original];evidence=[]
  for i,(before,after,target) in enumerate(zip(original,mapped,expected)):
   source=(0,-1.2,0) if i==0 else (0,1.25,.5)
   assert math.dist(before['position'],source)<1e-6
   assert math.dist(after['position'],target)<1e-7
   forward=(0,2*i-1,0)
   assert math.dist(rotation_axes(before['rotation'])[0],forward)<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   residual=triangle_distance(target,triangles);assert residual<(.0071 if covered and i==1 else .00002)
   # The rear ramp begins at the lower entrance and the front landing has
   # the upper floor. Ray intersections select those actual surfaces even
   # when the covered bunker's roof also crosses the vertical ray.
   sample_y=-1.2 if i==0 else 1.1;heights=[3-h for h in ray_hits((0,sample_y,3),(0,0,-1),triangles)]
   assert min(abs(z-target[2]) for z in heights)<.00002
   evidence.append(dict(index=i,position=after['position'],entrance='rear ramp' if i==0 else 'front landing',
                        outward_forward=forward,surface_residual=residual,centerline_floor_intersections=heights))
  assert abs(mapped[1]['position'][2]-mapped[0]['position'][2]-.5)<1e-7
  result.update(status='verified',reason='Both original entrance roles map onto actual end/floor planes with the same half-unit rise and unchanged outward frames; centerline floor intersections and bevel residuals checked; every native compound leaf including planar polygons resolved',
                anchors=evidence,compound=compound,contact_spacing=[2.4,.5],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label'] in railings:
  spec=railings[row['label']];name=spec['source'];source_bounds,original,source_shape=source_geometry(name)
  assert len(original)==6 and len(source_shape['vertices'])==10 and len(source_shape['planes'])==7
  # Source cap has a flat +X half at .5 and a descending -X edge at .4.
  # Its convex core includes the corresponding two upper levels and x=0 seam.
  source_vertices=np.asarray(source_shape['vertices']);r=source_shape['radius']
  for x,z in ((.1-r,.5-r),(0,.5-r),(-.1+r,.4-r)):
   assert any(abs(v[0]-x)<1e-6 and abs(v[2]-z)<.00002 for v in source_vertices)
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g)
  assert len(g['polyhedra'])==1 and g['bodies'][0]['shape_type']==4
  shape=g['polyhedra'][0];vertices=np.asarray(shape['vertices']);core=np.c_[vertices.min(axis=0),vertices.max(axis=0)]
  half=spec['source_half_length'];height=spec['height'];y0,y1=spec['y_min'],spec['y_max'];radius=shape['radius']
  profile=[(-.1+radius,radius),(.1-radius,radius),(.1-radius,.8*height-radius),(0,height-radius),(-.1+radius,height-radius)]
  expected_vertices=[(x,y,z) for x,z in profile for y in (-half+radius,half-radius)]
  assert len(shape['vertices'])==10 and len(shape['planes'])==7
  assert max(min(math.dist(v,p) for p in shape['vertices']) for v in expected_vertices)<1e-6
  expected_planes=[(0,-1,0,-half+radius),(0,1,0,-half+radius)]
  for a,b in zip(profile,profile[1:]+profile[:1]):
   dx,dz=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dz);nx,nz=dz/length,-dx/length
   expected_planes.append((nx,0,nz,-nx*a[0]-nz*a[1]))
  assert max(min(math.dist(v,p) for p in shape['planes']) for v in expected_planes)<.000003
  nominal=np.array([[-.1,.1],[-half,half],[0,height]])
  assert np.max(np.abs(core+np.array([-shape['radius'],shape['radius']])-nominal))<1e-6
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3)
  assert abs(mesh[:,1].min()-y0)<1e-7 and abs(mesh[:,1].max()-y1)<1e-7
  assert abs(mesh[:,2].min())<1e-6 and abs(mesh[:,2].max()-height)<1e-7
  samples=[]
  for x in (-.05,-.02,.02,.05,.07):
   hits=ray_hits((x,0,2),(0,0,-1),triangles);assert len(hits)==2
   top,bottom=2-hits[0],2-hits[-1];expected=height if x<0 else height*(1-2*x)
   assert abs(top-expected)<.000003 and abs(bottom)<1e-6
   samples.append(dict(x=x,actual_top=top,profile_top=expected))
  # Independently require extensive triangles of both cap planes, rather than
  # allowing five isolated ray intersections to establish the whole profile.
  cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);areas=np.linalg.norm(cross,axis=1)/2
  flat=np.max(np.abs(triangles[:,:,2]-height),axis=1)<.00001
  slope=np.max(np.abs(triangles[:,:,2]+2*height*triangles[:,:,0]-height),axis=1)<.00001
  assert areas[flat].sum()>(y1-y0)*.07 and areas[slope].sum()>(y1-y0)*.07
  mapped=[adapt(p,frames[name]) for p in original];seen=set();evidence=[]
  for i,(before,after) in enumerate(zip(original,mapped)):
   p=np.asarray(before['position']);q=np.asarray(after['position'])
   if abs(abs(p[1])-half)<.000001:
    source_side=1 if p[1]>0 else -1;role=('end',source_side)
    assert abs(p[0])<.008 and abs(p[2]-.22581)<.0002
    expected=(0,y0 if source_side>0 else y1,spec['end_reference_height'])
    forward=(0,-source_side,0)
   else:
    source_side=1 if p[0]>0 else -1;tier=0 if p[2]<.001 else 1;role=('side',source_side,tier)
    assert abs(p[0]-source_side*.1)<1e-6 and abs(p[1])<1e-6
    assert abs(p[2]-(0 if tier==0 else (.5 if source_side>0 else .4)))<1e-6
    expected=(-source_side*.1,(y0+y1)/2,0 if tier==0 else (height if source_side>0 else .8*height))
    forward=(-source_side,0,0)
   assert role not in seen;seen.add(role)
   assert math.dist(q,expected)<1e-7 and math.dist(rotation_axes(after['rotation'])[0],forward)<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):
    assert math.dist((-old[0],-old[1],old[2]),new)<1e-6
   residual=triangle_distance(q,triangles);assert residual<.012
   evidence.append(dict(index=i,position=q.tolist(),role=role,outward_forward=forward,
                        beveled_surface_residual=residual))
  assert len(seen)==6
  # All end markers share this base-relative reference, so matching any two
  # lengths cancels it and yields equal floor levels without all-pairs tests.
  assert abs(spec['end_reference_height']-.180648)<1e-12
  result.update(status='verified',reason='Both actual cap planes and the source/target profiles establish the 180-degree orientation and height change; all ten target convex vertices and seven planes reconstructed; all six original side/end roles have proved rotated frames and construction levels; end centers share one base reference across lengths; native fixed profile retained',
                anchors=evidence,compound=compound,contact_spacing=[.2,y1-y0,height],
                cap_profile_samples=samples,common_end_reference=spec['end_reference_height'],
                raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label'] in walls:
  spec=walls[row['label']];name=spec['source'];_,_,original=source_markers(name)
  assert len(original)==8
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g)
  assert len(g['polyhedra'])==1 and g['bodies'][0]['shape_type']==4
  shape=g['polyhedra'][0];core=np.asarray(axis_box(shape['vertices'],shape['planes']))
  nominal=np.array([[-spec['nominal_half_width'],spec['nominal_half_width']],[-.1,.1],[-1,1]])
  inset_radii=2 if row['label']=='Wall, 2x2' else 1
  outer=core+np.array([-inset_radii*shape['radius'],inset_radii*shape['radius']])
  assert np.max(np.abs(outer[1:]-nominal[1:]))<1e-6
  if row['label']!='Wall, Double':assert np.max(np.abs(outer[0]-nominal[0]))<1e-6
  source=np.asarray(spec['source_bounds']);target=np.asarray(spec['target_bounds'])
  rendered=all_render_rows[row['map'],row['palette_index']];triangles=actual_triangles(row)
  vertices=triangles.reshape(-1,3);bounds=np.c_[vertices.min(axis=0),vertices.max(axis=0)]
  assert np.max(np.abs(bounds[[0,2]]-target[[0,2]]))<1e-6
  assert np.all(core[:,0]>target[:,0]) and np.all(core[:,1]<target[:,1])
  for y in target[1]:
   assert any(abs(p['coordinate']-y)<.00002 and p['area']>.5 for p in rendered['axis_planes'][1])
  # A full rectangular panel with beveled edges/trim still has four perimeter
  # roles on each main Y face. Prove those roles, not just an AABB match.
  mapped=[adapt(p,frames[name]) for p in original];seen=set();evidence=[]
  for i,(before,after) in enumerate(zip(original,mapped)):
   p=np.asarray(before['position']);mid=source.mean(axis=1)
   sides=[j for j in (0,1) if abs(p[1]-source[1,j])<1e-6];assert len(sides)==1;face=sides[0]
   roles=[(axis,side) for axis in (0,2) for side in (0,1)
          if abs(p[axis]-source[axis,side])<.00001 and abs(p[2-axis]-mid[2-axis])<.00001]
   assert len(roles)==1;axis,side=roles[0];role=(face,axis,side)
   assert role not in seen;seen.add(role)
   expected=target.mean(axis=1);expected[axis]=target[axis,side];expected[1]=target[1,face]
   assert math.dist(after['position'],expected)<1e-7
   # H4 Wall Double's side markers face +/-X; the 2x2 wall/window side markers
   # face +/-Y like their top/bottom markers. Preserve this authored difference.
   forward=np.zeros(3)
   if row['label']=='Wall, Double' and axis==0:forward[0]=2*side-1
   else:forward[1]=2*face-1
   assert math.dist(rotation_axes(before['rotation'])[0],forward)<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   residual=triangle_distance(expected,triangles);assert residual<.03
   evidence.append(dict(index=i,position=after['position'],face=face,perimeter_axis=axis,side=side,
                        authored_forward=forward.tolist(),bevel_or_trim_surface_distance=residual))
  assert seen==set(itertools.product((0,1),(0,2),(0,1)))
  result.update(status='verified',reason='Eight original front/back perimeter roles and authored cardinal frames preserved on independently measured main face and X/Z support planes; complete native fixed collision box resolved with per-piece skin differences recorded; decorative trim retained',
                anchors=evidence,compound=compound,contact_spacing=(target[:,1]-target[:,0]).tolist(),
                construction_bounds=target.tolist(),render_bounds=bounds.tolist(),collision_core=core.tolist(),
                collision_yz_inset_radii=inset_radii,collision_x_core_clearance=[core[0,0]-target[0,0],target[0,1]-core[0,1]],
                raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label'] in straight_ramps:
  spec=straight_ramps[row['label']];name=spec['source'];_,_,original=source_markers(name)
  assert len(original)==2
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g)
  assert len(g['polyhedra'])==spec['compound_leaves'] and g['bodies'][0]['shape_type']==14
  x0,x1=spec['x_min'],spec['x_max'];slope,b=spec['deck_slope'],spec['deck_intercept'];length=x1-x0
  triangles=actual_triangles(row);vertices=triangles.reshape(-1,3)
  assert abs(vertices[:,0].min()-x0)<1e-6 and abs(vertices[:,0].max()-x1)<1e-6
  offsets=triangles[:,:,2]-slope*triangles[:,:,0]-b
  deck=np.max(np.abs(offsets),axis=1)<.0002
  assert deck.any()
  cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);areas=np.linalg.norm(cross,axis=1)/2
  deck_area=areas[deck].sum();assert deck_area>length*1.5
  deck_vertices=triangles[deck].reshape(-1,3)
  assert abs(deck_vertices[:,0].min()-x0)<.01 and abs(deck_vertices[:,0].max()-x1)<.01
  assert deck_vertices[:,1].min()<-.79 and deck_vertices[:,1].max()>.79
  # Ray/triangle intersections distinguish the central walking deck from the
  # parallel underside and raised side rails; these rays stay inside one piece.
  samples=[]
  for fraction in (.25,.5,.75):
   x=x0+fraction*length;hits=ray_hits((x,0,10),(0,0,-1),triangles)
   assert hits;actual_top=10-hits[0];expected_top=slope*x+b
   assert abs(actual_top-expected_top)<.0001
   samples.append(dict(x=x,actual_deck=actual_top,plane_deck=expected_top))
  rendered=all_render_rows[row['map'],row['palette_index']]
  # A triangular ramp's low endpoint is a tip; bridge ramps have two vertical
  # end faces. The high end must always have an independently measured face.
  high_x=x0 if slope<0 else x1
  for x in ((x0,x1) if slope<0 else (high_x,)):
   assert any(abs(p['coordinate']-x)<.00003 and p['area']>.05 for p in rendered['axis_planes'][0])
  left,right=sorted(original,key=lambda p:p['position'][0])
  assert abs(right['position'][0]-left['position'][0]-spec['source_length'])<.00001
  assert abs(right['position'][2]-left['position'][2]-slope*spec['source_length'])<.00001
  mapped=[adapt(p,frames[name]) for p in original];evidence=[];seen=set()
  for i,(before,after) in enumerate(zip(original,mapped)):
   side=0 if before is left else 1;assert side not in seen;seen.add(side)
   x=(x0,x1)[side];expected=(x,0,slope*x+b)
   assert math.dist(after['position'],expected)<1e-7
   normal=(2*side-1,0,0)
   assert math.dist(rotation_axes(before['rotation'])[0],normal)<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   residual=triangle_distance(expected,triangles);assert residual<.02
   evidence.append(dict(index=i,position=after['position'],entrance='left' if side==0 else 'right',
                        outward_normal=normal,beveled_surface_residual=residual))
  assert seen=={0,1}
  result.update(status='verified',reason='Both original entrance roles map to independently witnessed end/deck plane intersections; extensive actual deck triangles and centerline rays distinguish walking surface from raised rails and underside; compound nodes resolved and authored outward frames unchanged',
                anchors=evidence,compound=compound,contact_spacing=[length,2,abs(slope*length)],
                deck_plane=dict(slope=slope,intercept=b,area=float(deck_area),samples=samples),
                raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label']=='Block, 1x1, Short':
  name='fw_unsc_c_plat_1x1_short';_,_,original=source_markers(name);assert len(original)==8
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g)
  assert len(g['polyhedra'])==3 and g['bodies'][0]['shape_type']==14
  cores=[np.asarray(axis_box(s['vertices'],s['planes'])) for s in g['polyhedra'][:2]]
  main=[]
  for shape,core in zip(g['polyhedra'][:2],cores[:2]):
   outer=core+np.array([-shape['radius'],shape['radius']])
   assert np.max(np.abs(outer[:2]-[[-.5,.5],[-.5,.5]]))<1e-6
   main.append(outer)
  assert abs(main[0][2,0])<1e-6 and abs(main[1][2,1]-.5)<1e-6
  assert 0<main[1][2,0]<main[0][2,1]<.5
  cap=g['polyhedra'][2]
  expected_cap=[(x,y,z) for radius,z in ((.5,.5),(.4,.52)) for x,y in itertools.product((-radius,radius),repeat=2)]
  assert len(cap['vertices'])==8 and len(cap['planes'])==6
  assert max(min(math.dist(v,p) for p in cap['vertices']) for v in expected_cap)<1e-6
  cap_planes=[(0,0,-1,.5),(0,0,1,-.52)]
  for axis in (0,1):
   for sign in (-1,1):
    plane=np.array([0.,0.,5.,-3.]);plane[axis]=sign;cap_planes.append(plane/math.sqrt(26))
  assert max(min(math.dist(v,p) for p in cap['planes']) for v in cap_planes)<.00003
  rendered=all_render_rows[row['map'],row['palette_index']];triangles=actual_triangles(row)
  for axis,levels in ((0,(-.5,.5)),(1,(-.5,.5)),(2,(0,.5))):
   for level in levels:
    assert any(abs(p['coordinate']-level)<.00003 and p['area']>.1 for p in rendered['axis_planes'][axis])
  mapped=[adapt(p,frames[name]) for p in original];seen=set();evidence=[]
  for i,(before,after) in enumerate(zip(original,mapped)):
   p=np.asarray(after['position']);axis=int(np.argmax(np.abs(p[:2])));side=1 if p[axis]>0 else -1
   assert p[axis]==side*.5 and p[1-axis]==0 and p[2] in (0,.5)
   role=(axis,side,p[2]);assert role not in seen;seen.add(role)
   normal=np.zeros(3);normal[axis]=side
   assert math.dist(rotation_axes(after['rotation'])[0],normal)<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   residual=triangle_distance(p,triangles);assert residual<.00002
   evidence.append(dict(index=i,position=p.tolist(),surface_residual=residual,
                        outward_construction_normal=normal.tolist()))
  assert seen==set(itertools.product((0,1),(-1,1),(0,.5)))
  result.update(status='verified',reason='All eight original side-midpoint roles lie on the actual mesh at independently witnessed construction planes; both native boxes, the tapered upper cap and body resolved; original cardinal frames preserved',
                anchors=evidence,compound=compound,contact_spacing=[1,1,.5],
                authored_collision_cap_vertices=cap['vertices'],raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label'] in flat_slabs:
  spec=flat_slabs[row['label']];name=spec['source']
  _,_,original=source_markers(name);assert len(original)==8
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g)
  assert len(g['polyhedra'])==1 and g['bodies'][0]['shape_type']==4
  shape=g['polyhedra'][0];vertices=np.asarray(shape['vertices']);planes=np.asarray(shape['planes'])
  assert vertices.shape==(8,3) and planes.shape==(6,4)
  # Prove the six-faced native convex core from all feasible three-plane
  # intersections. 2x1 Flat has a slightly tilted bottom, so axis_box would
  # incorrectly identify it as a rectangular collision box.
  corners=[]
  for indices in itertools.combinations(range(6),3):
   face=planes[list(indices)]
   if abs(np.linalg.det(face[:,:3]))<1e-6:continue
   point=np.linalg.solve(face[:,:3],-face[:,3])
   if np.max(planes[:,:3]@point+planes[:,3])<1e-5:corners.append(point)
  assert len(corners)==8
  assert max(min(np.linalg.norm(v-p) for p in corners) for v in vertices)<1e-5
  assert max(min(np.linalg.norm(v-p) for v in vertices) for p in corners)<1e-5
  directions=set()
  for plane in planes:
   axis=int(np.argmax(np.abs(plane[:3])));sign=1 if plane[axis]>0 else -1
   expected=np.zeros(3);expected[axis]=sign
   assert np.linalg.norm(plane[:3]-expected)<.002
   directions.add((axis,sign))
  assert directions==set(itertools.product(range(3),(-1,1)))
  source=np.asarray(spec['source_bounds']).reshape(3,2)
  target=np.asarray(spec['target_bounds']).reshape(3,2)
  rendered=all_render_rows[row['map'],row['palette_index']]
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3)
  measured=np.c_[mesh.min(axis=0),mesh.max(axis=0)]
  assert np.max(np.abs(measured-target))<.000002
  # The top/bottom support planes contain substantial actual faces. The XY
  # boundary may be a beveled support edge, so do not invent face triangles.
  for side in (0,1):
   assert any(abs(p['coordinate']-target[2,side])<.00002 and p['area']>.5
              for p in rendered['axis_planes'][2])
  core_bounds=np.c_[vertices.min(axis=0),vertices.max(axis=0)]
  clearances=np.c_[core_bounds[:,0]-target[:,0],target[:,1]-core_bounds[:,1]]
  assert clearances.min()>0 and clearances.max()<.02
  frame=frames[name];mapped=[adapt(p,frame) for p in original]
  seen=set();evidence=[]
  for i,(before,after) in enumerate(zip(original,mapped)):
   position=np.asarray(before['position']);center=source.mean(axis=1)
   choices=[(axis,side) for axis in (0,1) for side in (0,1)
            if abs(position[axis]-source[axis,side])<.0001 and abs(position[1-axis]-center[1-axis])<.0001]
   assert len(choices)==1;axis,side=choices[0]
   tier=int(np.argmin(abs(source[2]-position[2])));assert abs(source[2,tier]-position[2])<.0001
   assert (axis,side,tier) not in seen;seen.add((axis,side,tier))
   expected=target.mean(axis=1);expected[axis]=target[axis,side];expected[2]=target[2,tier]
   assert math.dist(after['position'],expected)<1e-7
   normal=np.zeros(3);normal[axis]=2*side-1
   assert math.dist(rotation_axes(before['rotation'])[0],normal)<1e-6
   assert math.dist(rotation_axes(after['rotation'])[0],normal)<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   # Every rendered vertex is in the anchor's inward support half-space.
   assert np.max((mesh-expected)@normal)<.000002
   evidence.append(dict(index=i,position=after['position'],side_axis=axis,side=side,tier=tier,
                        outward_normal=normal.tolist(),actual_surface_distance=triangle_distance(expected,triangles)))
  assert seen==set(itertools.product((0,1),(0,1),(0,1)))
  # Equal top roles make worldTopA == worldTopB; equal bottom roles likewise.
  # Opposed outward frames place both complete render envelopes on opposite
  # sides of their common support plane, independent of the partner's size.
  result.update(status='verified',reason='All eight H4 side/top/bottom roles and cardinal frames map onto the actual six render support planes; complete native convex topology and identity body resolved separately, with its authored collision skin retained',
                anchors=evidence,compound=compound,contact_spacing=(target[:,1]-target[:,0]).tolist(),
                rendered_bounds=measured.tolist(),collision_core_bounds=core_bounds.tolist(),
                collision_core_clearances=clearances.tolist(),collision_radius=shape['radius'],
                raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label'] in detailed_boxes:
  spec=detailed_boxes[row['label']];name=spec['source'];_,source_bounds,original=source_markers(name)
  source=np.asarray(spec['source_bounds']);target=np.asarray(spec['target_planes']);native=np.asarray(spec['native_bounds'])
  assert np.max(np.abs(np.asarray(source_bounds).reshape(3,2)-source))<1e-6 and len(original)==8
  g=geometry[row['map'],row['palette_index']];compound=identity_compound(g)
  assert len(g['polyhedra'])==1 and g['bodies'][0]['shape_type']==4
  shape=g['polyhedra'][0];core=np.asarray(axis_box(shape['vertices'],shape['planes']))
  assert np.max(np.abs(core+np.array([-shape['radius'],shape['radius']])-native))<1e-6
  triangles=actual_triangles(row);mesh=triangles.reshape(-1,3);rendered=all_render_rows[row['map'],row['palette_index']]
  for axis in range(3):
   for level in target[axis]:
    assert any(abs(p['coordinate']-level)<.00005 and p['area']>spec['minimum_face_area'] for p in rendered['axis_planes'][axis])
  actual_bounds=np.c_[mesh.min(0),mesh.max(0)]
  relief=np.c_[target[:,0]-actual_bounds[:,0],actual_bounds[:,1]-target[:,1]]
  assert relief.min()>-.000001 and relief.max()<spec['maximum_decoration']
  mapped=[adapt(p,frames[name]) for p in original];evidence=[];roles=set()
  for i,(before,after) in enumerate(zip(original,mapped)):
   position=np.asarray(before['position']);c=source.mean(1)
   matches=[(axis,side,tier) for axis in (0,1) for side in (0,1) for tier in (0,1)
            if abs(position[axis]-source[axis,side])<1e-6 and abs(position[1-axis]-c[1-axis])<1e-6 and abs(position[2]-source[2,tier])<1e-6]
   assert len(matches)==1;axis,side,tier=matches[0];assert matches[0] not in roles;roles.add(matches[0])
   expected=target.mean(1);expected[axis]=target[axis,side];expected[2]=target[2,tier]
   assert math.dist(after['position'],expected)<1e-7
   normal=np.zeros(3);normal[axis]=2*side-1
   assert math.dist(rotation_axes(after['rotation'])[0],normal)<1e-6
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):assert math.dist(old,new)<1e-6
   residual=triangle_distance(expected,triangles)
   if row['label']=='Block, 1x4':assert residual<.00002 if axis==0 else .009<residual<.0092
   else:assert .006<residual<.0063
   evidence.append(dict(index=i,position=after['position'],outward_forward=normal.tolist(),surface_residual=residual))
  assert roles==set(itertools.product((0,1),(0,1),(0,1)))
  result.update(status='verified',reason='All eight original side/tier roles and cardinal frames map to six independently witnessed principal faces; complete native box and one-radius skin checked separately; measured decoration/bevel residuals retained without altering native geometry or physics',
                anchors=evidence,compound=compound,contact_spacing=(target[:,1]-target[:,0]).tolist(),
                construction_planes=target.tolist(),decoration_beyond_planes=relief.tolist(),raw_geometry_signature=row['raw_geometry_signature'])
 elif row['label'] in boxes:
  spec=boxes[row['label']];name=spec['source'];target=spec['bounds'];tol=spec['geometry_tolerance']
  _,_,original=source_markers(name)
  g=geometry[row['map'],row['palette_index']]
  assert len(g['nodes'])==1 and g['nodes'][0]['parent']==-1
  node=g['nodes'][0]
  assert node['position']==[0,0,0] and node['rotation']==[0,0,0,1]
  assert node['inverse_basis']==[1,0,0,0,1,0,0,0,1] and node['inverse_scale']==1 and node['inverse_position']==[0,0,0]
  assert g['bodies']==[dict(node=0,motion_type=5,shape_type=4,shape_index=0)]
  assert len(g['polyhedra'])==1
  shape=g['polyhedra'][0];core=axis_box(shape['vertices'],shape['planes'])
  # These later-added box hulls use one radius, unlike the earlier banks.
  skin=shape['radius']
  collision_error=max(abs(core[i][side]+(-skin if side==0 else skin)-target[2*i+side]) for i in range(3) for side in range(2))
  assert collision_error<tol,(row['label'],'collision',collision_error)
  rendered=render_rows[row['map'],row['palette_index']];assert rendered['status']=='measured'
  surfaces=[]
  for axis in range(3):
   for side in range(2):
    coordinate=target[2*axis+side]
    candidates=[p for p in rendered['axis_planes'][axis] if p['area']>1e-6 and abs(p['coordinate']-coordinate)<tol]
    support_error=abs(rendered['referenced_bounds'][axis][side]-coordinate)
    assert candidates or support_error<tol,(row['label'],'render plane',axis,side,support_error)
    surfaces.append(dict(axis=axis,side=side,coordinate=coordinate,triangle_planes=candidates,
                         support_residual=support_error,evidence='face triangles' if candidates else 'referenced mesh support edge'))
  cx,cy=[(target[2*i]+target[2*i+1])/2 for i in range(2)]
  xy=[(target[0],cy),(target[1],cy),(cx,target[2]),(cx,target[3])]
  if spec['extra_centers']:xy.append((cx,cy))
  expected=[(x,y,z) for x,y in xy for z in target[4:6]]
  frame=frames[name];mapped=[adapt(p,frame) for p in original]
  rounded=lambda p:tuple(round(v,6) for v in p)
  assert Counter(rounded(p['position']) for p in mapped)==Counter(rounded(p) for p in expected),(row['label'],'anchor pattern')
  unprojected=dict(frame);unprojected.pop('coordinate_planes');unprojected.pop('coordinate_tolerance')
  angle=math.radians(frame['yaw_degrees']);c,s=math.cos(angle),math.sin(angle)
  evidence=[]
  for i,(before,after) in enumerate(zip(original,mapped)):
   residual=max(abs(a-b) for a,b in zip(adapt(before,unprojected)['position'],after['position']))
   assert residual<=frame['coordinate_tolerance']
   assert abs(sum(v*v for v in after['rotation'])-1)<1e-5
   for old,new in zip(rotation_axes(before['rotation']),rotation_axes(after['rotation'])):
    assert math.dist((c*old[0]-s*old[1],s*old[0]+c*old[1],old[2]),new)<1e-6
   evidence.append(dict(index=i,position=after['position'],authored_noise_projection=residual))
  result.update(status='verified',reason='Complete convex box topology, identity node/body, all six construction planes supported by actual render triangles or mesh support edges, complete two-level side-midpoint anchor pattern and independently rotated authored frames',
                anchors=evidence,contact_spacing=[target[2*i+1]-target[2*i] for i in range(3)],
                collision_core_inset=skin,collision_plane_residual=collision_error,render_surfaces=surfaces,
                raw_geometry_signature=row['raw_geometry_signature'])
 if row['label'] in completion:
  from check_transform_equations import check
  profile=completion[row['label']];original=None;source_bounds=None
  if profile['source']:
   name=profile['source'].split('\\')[-1];model=models[name]
   original=[p for group in model['markers'] if group['group']=='sandbox_magnet' for p in group['points']]
   at=off(u(tag_at+model['tag_index']*8+4));compression=block(at+0x80,52);assert len(compression)==1
   source_bounds=struct.unpack_from('>6f',data,compression[0]+4)
  mapped=check(profile,row,actual_triangles(row),original,source_bounds)
  g=geometry[row['map'],row['palette_index']]
  result.update(status='equations_checked',reason=profile['method'],anchors=mapped,
                native_fixed_release=bool(g['bodies']) and all(b['motion_type']==5 for b in g['bodies']),
                testing='Gameplay testing and follow-up corrections belong to the user, per the latest scope',
                contact_spacing=(np.array(profile['target_bounds'])[:,1]-np.array(profile['target_bounds'])[:,0]).tolist())
 if args.check_pack and result['status'] in ('verified','equations_checked'):
  actual,fixed,radius=pack[row['map_id'],int(row['datum'],16)]
  assert len(actual)==len(mapped) and fixed==int(result.get('native_fixed_release',True))
  sphere=geometry[row['map'],row['palette_index']]['bounding_sphere']
  enclosing_radius=max(sphere['radius']+math.sqrt(sum(v*v for v in sphere['center'])),
                       max(math.sqrt(sum(v*v for v in p['position'])) for p in mapped))
  assert abs(radius-enclosing_radius)<2e-6
  for p,expected in zip(actual,mapped):
   assert math.dist(p[:3],expected['position'])<1e-6
   assert math.dist(p[3:],expected['rotation'])<1e-6
   assert math.sqrt(sum(v*v for v in p[:3]))<=radius+.0005,(row['label'],'anchor outside broad-phase radius',radius,p[:3])
  result['runtime_pack_matches']=True
 proofs.append(result)
report=dict(method='Per-piece mathematical geometry/anchor proof; no exhaustive object combinations',
            maps=inventory['maps'],h4_cache_sha256=hashlib.sha256(data).hexdigest(),
            frames_sha256=hashlib.sha256((Path(__file__).parent/'anchor_frames.json').read_bytes()).hexdigest(),
            verified=sum(r['status'] in ('verified','equations_checked') for r in proofs),
            detailed_geometry_proofs=sum(r['status']=='verified' for r in proofs),
            equation_transforms=sum(r['status']=='equations_checked' for r in proofs),total=len(proofs),pieces=proofs,
            runtime_pack_checked=args.check_pack,
            runtime_origin_bounds_checked=len(pack) if args.check_pack else 0,
            scenery_entries=sum(r['group'] in ('bloc','scen') for r in proofs),
            non_scenery_entries=sum(r['status']=='not_scenery' for r in proofs))
report['anchorless_entries']=sum(r['status']=='no_authored_anchors' for r in proofs)
report['unresolved_entries']=sum(r['status']=='unverified' for r in proofs)
(OUT/'scenery-math-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(f"Verified {report['verified']}/{report['scenery_entries']} scenery entries; {report['non_scenery_entries']} non-scenery rows separately accounted for.")
print(f"Additionally {report['anchorless_entries']} scenery entries have source-backed anchorless behavior; {report['unresolved_entries']} remain unresolved.")
for r in proofs:
 if r['status']=='verified':print(r['map'],r['label'],'all',len(r['anchors']),'anchors; contact spacing',r['contact_spacing'])
