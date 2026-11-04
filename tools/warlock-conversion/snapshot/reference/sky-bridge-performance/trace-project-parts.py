import argparse,sys,json,numpy as np
from pathlib import Path
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
from resource_reader import Resource
parser=argparse.ArgumentParser()
parser.add_argument('--trace-dir',type=Path,default=Path('work/sky-bridge/draw-trace-20261103-200444'))
root=parser.parse_args().trace_dir
root.resolve().relative_to(Path(__file__).resolve().parents[5])
groups=json.loads((root/'geometry-state.json').read_text())['groups']
c=Cache('work/sky-bridge/payload-32/sky_bridge.map'); c.shared_paths={'maps\\shared.map':Path('C:/X360/ISOs/H3M/maps/shared.map')}
base,=c.block(c.tags[9894]['offset']+4,436); meshes=c.block(base+0x134,76)
r=Resource(c,c.u(base+0x1ac)); vb=r.buffers('vertex');ib=r.buffers('index')
def raw(field,size):
 p=r.fix[field]; return r.raw[(p>>29)-2][(p&0x1fffffff):(p&0x1fffffff)+size]
seen=set();out=[]
for group in groups:
 g=group['geometry']; key=(g['mesh'],g['part'],group['model'])
 if key in seen:continue
 seen.add(key)
 if not any(word in (g['material'] or '') for word in ('envelope','screen','farplane')):continue
 mesh=meshes[g['mesh']]; vertex=vb[c.unpack('h',mesh+24)[0]]; index=ib[c.unpack('h',mesh+40)[0]]
 count,fmt,stride=r.unpack('IHH',vertex); positions=raw(vertex+20,count*stride)
 indices=np.frombuffer(raw(index+16,r.unpack('I',index+4)[0]),dtype='>u2')[g['index_start']:g['index_start']+g['index_count']]
 indices=np.unique(indices[indices!=65535]);assert max(indices)<count
 vs=np.frombuffer(bytes.fromhex(group['vertex_constants_0_18']),dtype='<f4').reshape(19,4)
 if fmt==2:
  points=np.ndarray((count,3),dtype='>u2',buffer=positions,strides=(stride,2))[indices].astype(float)/65535
  points=points*vs[12,:3]+vs[13,:3]
  points=np.c_[points,np.ones(len(points))]@vs[16:19].T
 elif fmt==1: points=np.ndarray((count,3),dtype='>f4',buffer=positions,strides=(stride,4))[indices].astype(float)
 else:raise ValueError(fmt)
 clip=np.c_[points,np.ones(len(points))]@vs[:4].T
 forward=clip[:,3]>0
 if not np.any(forward):continue
 ndc=clip[forward,:2]/clip[forward,3,None];uv=ndc*np.array([.5,-.5])+np.array([.5,.5])
 out.append(dict(mesh=g['mesh'],part=g['part'],material=g['material'],model=group['model'],camera=vs[7,:3].tolist(),
  world_min=points.min(axis=0).tolist(),world_max=points.max(axis=0).tolist(),
  uv_min=uv.min(axis=0).tolist(),uv_max=uv.max(axis=0).tolist(),vertices_in_front=int(forward.sum()),vertices=len(points),
  limitation='Projection follows source rigid/world transform convention; live vertex program mapping and screenshot camera equivalence still require confirmation.'))
(root/'projected-parts.json').write_text(json.dumps(out,indent=2)+'\n')
for row in out:
 if row['uv_max'][0]>0 and row['uv_min'][0]<1 and row['uv_max'][1]>0 and row['uv_min'][1]<1: print(row['mesh'],row['part'],row['material'].split('\\')[-1],np.round(row['uv_min'],3),np.round(row['uv_max'],3))
c.close()
