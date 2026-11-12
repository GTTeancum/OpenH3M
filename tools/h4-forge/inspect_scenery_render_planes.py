"""Measure actual rigid render triangles' axis-aligned planes, read-only.

Compression bounds are used only to decode vertices, not as a surface proof.
Unsupported meshes fail explicitly rather than inventing their transforms.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
from node_frames import resolve_nodes

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--prefix',default='Block')
args=parser.parse_args()
OUT=ROOT/'work/h4-forge-research/isolated'
inventory=json.loads((OUT/'scenery-inventory.json').read_text())
geometries={(r['map'],r['palette_index']):r for r in json.loads((OUT/'scenery-geometry.json').read_text())}
results=[]
for info in inventory['maps']:
 path=next((ROOT/'work/dlc/installed-current').rglob(info['name']));c=Cache(path)
 try:
  assert hashlib.sha256(c.data).hexdigest()==info['sha256']
  c.decoded_pages={}
  for row in inventory['rows']:
   if row['map']!=info['name'] or not row['label'].startswith(args.prefix):continue
   g=geometries[row['map'],row['palette_index']]
   result={k:row[k] for k in ('map','palette_index','datum','label')}
   try:
    node_frames=resolve_nodes(g['nodes'])
    assert len(node_frames)==1 or g['animation']=='0xffffffff','Animated child-node model requires pose-specific verification'
    at=c.tags[int(g['render'],16)&65535]['offset'];compression=c.block(at+0x74,44)
    assert len(compression)==1 and c.unpack('H',compression[0])[0]&1,'Unknown position compression'
    bounds=np.array(c.unpack('6f',compression[0]+4)).reshape(3,2)
    r=Resource(c,c.u(at+0xe0));vb=r.buffers('vertex');ib=r.buffers('index')
    all_triangles=[];mesh_records=[]
    def raw(field,length):
     ptr=r.fix[field];address=ptr&0x1fffffff;kind=(ptr>>29)-2
     assert kind in (0,1)
     value=r.raw[kind][address:address+length];assert len(value)==length
     return value
    for number,mesh in enumerate(c.block(at+0x68,76)):
     node_index=c.data[mesh+0x2d]
     assert node_index<len(node_frames) and c.data[mesh+0x2e]==1,'Not an authored rigid mesh'
     vi=c.unpack('h',mesh+0x18)[0];ii=c.unpack('h',mesh+0x28)[0]
     assert 0<=vi<len(vb) and 0<=ii<len(ib)
     count,fmt,stride=r.unpack('IHH',vb[vi]);assert fmt==2 and stride==24
     vertices_raw=raw(vb[vi]+20,count*stride)
     quantized=np.ndarray((count,3),dtype='>u2',buffer=vertices_raw,strides=(stride,2))
     positions=bounds[:,0]+quantized.astype(float)/65535*(bounds[:,1]-bounds[:,0])
     # H3 render vertices are stored in object bind space. The node index
     # selects the deformation matrix (posed node * inverse bind), which is
     # identity at this authored pose. Applying the node bind transform here
     # would rotate twice. Physics vertices and marker records differ: those
     # are node-local and do require the node-to-object transform.
     index_bytes=r.unpack('I',ib[ii]+4)[0];assert index_bytes%2==0
     indices_raw=raw(ib[ii]+16,index_bytes);indices=np.frombuffer(indices_raw,dtype='>u2')
     primitive=c.data[mesh+0x30];assert primitive in (3,5)
     tris=[]
     for part in c.block(mesh,16):
      start,length=c.unpack('HH',part+4);assert start+length<=len(indices)
      values=indices[start:start+length]
      if primitive==3:
       assert length%3==0
       candidate=values.reshape(-1,3)
      else:candidate=np.stack([values[:-2],values[1:-1],values[2:]],axis=1) if length>=3 else np.empty((0,3),dtype=int)
      valid=(candidate!=65535).all(axis=1)&(candidate[:,0]!=candidate[:,1])&(candidate[:,1]!=candidate[:,2])&(candidate[:,0]!=candidate[:,2])
      candidate=candidate[valid];assert not candidate.size or candidate.max()<count
      tris.extend(candidate.tolist())
     triangle_points=positions[np.array(tris,dtype=int)] if tris else np.empty((0,3,3))
     all_triangles.extend(triangle_points.tolist())
     mesh_records.append(dict(mesh=number,node=node_index,vertices=count,triangles=len(tris),primitive=primitive,
       vertices_sha256=hashlib.sha256(vertices_raw).hexdigest(),indices_sha256=hashlib.sha256(indices_raw).hexdigest()))
    triangles=np.asarray(all_triangles);assert len(triangles)
    cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);length=np.linalg.norm(cross,axis=1)
    valid=length>1e-10;triangles=triangles[valid];cross=cross[valid];area=length[valid]/2
    normals=cross/length[valid,None];planes=[defaultdict(float) for _ in range(3)]
    triangle_path=OUT/'render-triangles'/f"{row['map']}-{row['palette_index']}.npz"
    triangle_path.parent.mkdir(exist_ok=True)
    np.savez_compressed(triangle_path,triangles=triangles)
    for axis in range(3):
     selected=np.abs(normals[:,axis])>1-1e-7
     for coord,size in zip(triangles[selected,:,axis].mean(axis=1),area[selected]):
      planes[axis][round(float(coord),5)]+=float(size)
    result.update(status='measured',meshes=mesh_records,triangles=len(triangles),
      node_frames=[m.tolist() for m in node_frames],
      triangle_file=str(triangle_path.relative_to(ROOT)),triangle_sha256=hashlib.sha256(triangle_path.read_bytes()).hexdigest(),
      referenced_bounds=[[float(triangles[:,:,i].min()),float(triangles[:,:,i].max())] for i in range(3)],
      position_quantum=((bounds[:,1]-bounds[:,0])/65535).tolist(),
      axis_planes=[[dict(coordinate=k,area=v) for k,v in sorted(items.items(),key=lambda kv:-kv[1])] for items in planes])
   except (AssertionError,ValueError,KeyError) as exc:
    result.update(status='unsupported',reason=str(exc) or type(exc).__name__)
   results.append(result)
 finally:c.close()
report=dict(maps=inventory['maps'],prefix=args.prefix,method='All referenced rigid triangles; no bounding-box surface assumption',rows=results)
(OUT/('render-planes-'+(args.prefix.lower().replace(' ','-') or 'all')+'.json')).write_text(json.dumps(report,indent=2)+'\n')
for r in results:
 print(r['map'],r['label'],r['status'],[[(p['coordinate'],round(p['area'],3)) for p in planes[:3]] for planes in r.get('axis_planes',[])],r.get('reason',''))
