"""Read-only spatial split estimates. Does not serialize playable collision."""
import argparse,json,struct
from pathlib import Path
import numpy as np
from cache_reader import Cache
from resource_reader import Resource


def analyze(path,cut,cut_x=None):
 c=Cache(path,True)
 try:
  t=next(t for n,t in c.tags.items() if t['group']=='sbsp' and c.name(n)==r'levels\multi\forge_halo\forge_halo')
  root=t['offset'];r=Resource(c,c.u(root+0x38c));a=r.fix[r.root+16]&0x1fffffff
  strides=[12,16,8,8,20,16,24,20]
  def block(j):
   n=r.unpack('I',a+j*12)[0];p=r.fix[a+j*12+4];seg=p>>29
   data=r.data if seg==1 else r.raw[seg-2];off=p&0x1fffffff;size=n*strides[j]
   if off+size>len(data):raise ValueError('Out-of-bounds collision block')
   return bytes(data[off:off+size])
  nodes=np.frombuffer(block(0),dtype='<i4').reshape(-1,3)
  plane_bytes=block(1)
  leaves=list(struct.iter_unpack('<BBHI',block(2)))
  refs=np.frombuffer(block(3),dtype='<i4').reshape(-1,2)
  nodes2=list(struct.iter_unpack('<3fii',block(4)))
  surfs=list(struct.iter_unpack('<iihhhBb',block(5)))
  edges=np.frombuffer(block(6),dtype='<i4').reshape(-1,6)
  verts=np.frombuffer(block(7),dtype=np.dtype([('xyz','<f4',(3,)),('edge','<i4'),('sink','<i4')]))['xyz']
  mins=[];maxs=[];surface_edges=[]
  for idx,s in enumerate(surfs):
   e=s[1];seen=set()
   while e not in seen:
    if not 0<=e<len(edges):raise ValueError('Invalid edge')
    seen.add(e);v=edges[e]
    if v[4]==idx:e=int(v[2])
    elif v[5]==idx:e=int(v[3])
    else:raise ValueError('Edge does not belong to surface')
   if e!=s[1]:raise ValueError('Open surface loop')
   xyz=verts[np.unique(edges[list(seen),:2])]
   mins.append(xyz.min(axis=0));maxs.append(xyz.max(axis=0));surface_edges.append(seen)
  mins=np.array(mins);maxs=np.array(maxs)
  def tree_states(children,terminal):
   states=np.zeros(len(children),dtype=np.uint8);active=np.zeros(len(children),dtype=bool)
   def value(child):return terminal(child) if child<0 else active[child]
   for start in range(len(children)):
    stack=[(start,False)]
    while stack:
     n,leave=stack.pop()
     if n<0:continue
     if n>=len(children):raise ValueError('Out-of-range collision child')
     if leave:
      active[n]=any(value(int(ch)) for ch in children[n]);states[n]=2;continue
     if states[n]==2:continue
     if states[n]==1:raise ValueError('Cyclic collision tree')
     states[n]=1;stack.append((n,True))
     stack.extend((int(ch),False) for ch in children[n] if ch>=0)
   return active,value
  outputs={}
  gulch = mins[:,1]<=cut
  world = maxs[:,1]>=cut
  if cut_x is not None:
   gulch &= mins[:,0]<=cut_x
   world |= maxs[:,0]>=cut_x
  for name,keep in [('Forge Gulch',gulch),('Forge World',world)]:
   def surface(ch):
    if ch==-1:return False
    n=ch&0x7fffffff
    if n>=len(keep):raise ValueError('Invalid terminal surface')
    return bool(keep[n])
   active2,v2=tree_states([n[3:] for n in nodes2],surface)
   active_refs=np.array([v2(int(n)) for n in refs[:,1]])
   if any(n and f+n>len(refs) for _,_,n,f in leaves):raise ValueError('Leaf reference range outside table')
   active_leaves=np.array([bool(active_refs[f:f+n].any()) for _,_,n,f in leaves])
   def leaf(ch):
    if ch==-1:return False
    idx=ch&0x7fffffff
    if idx>=len(leaves):raise ValueError('Invalid terminal leaf')
    return bool(active_leaves[idx])
   active3,_=tree_states(nodes[:,1:],leaf)
   pi=set((int(v)&0x7fffffff) for v in nodes[active3,0])
   pi.update(int(v)&0x7fffffff for v in refs[active_refs,0])
   pi.update(surfs[n][0]&0x7fffffff for n in np.flatnonzero(keep))
   ei=set().union(*(surface_edges[n] for n in np.flatnonzero(keep)))
   vi=np.unique(edges[list(ei),:2])
   if max(pi)>=len(plane_bytes)//16:raise ValueError('Plane out of range')
   unique=len({plane_bytes[n*16:n*16+16] for n in pi})
   ref_planes={int(v)&0x7fffffff for v in refs[active_refs,0]}
   reference_unique=len({plane_bytes[n*16:n*16+16] for n in ref_planes})
   outputs[name]={'main_bsp_surfaces':int(keep.sum()),'main_bsp_edges':len(ei),'main_bsp_vertices':len(vi),
     'retained_tree_nodes':int(active3.sum()),'retained_tree_planes':len(pi),'byte_unique_retained_planes':unique,
     'nodes_2d':int(active2.sum()),'leaves':int(active_leaves.sum()),
     'signed_2d_reference_plane_count':reference_unique,
     'two_d_signed_index_ranges_fit':reference_unique<32768 and int(keep.sum())<32767 and int(active2.sum())<32767,
     'plane_and_edge_counts_within_16_bit_range':unique<=65536 and len(ei)<65535}
  from mcc_bitmap_source import BitmapSource
  bs=BitmapSource(c);geometry=[];lightmaps=[]
  for n,t in c.tags.items():
   if t['group']=='Lbsp':
    res=Resource(c,c.u(t['offset']+0x1ac))
    geometry.append({'name':c.name(n),'raw_bytes':sum(map(len,res.raw))})
    for off in (0xe0,0xf0):
     idx=c.u(t['offset']+off+12)&65535
     info=bs.info(idx)[0];lightmaps.append({'name':c.name(idx),'raw_bytes':info['size']})
  from bsp_source import convert_bsp_geometry
  from encode_bitmap import encode_lightmap_array
  retail_geometry=[];retail_lightmaps=[]
  for index in (0,1):
   converted,_=convert_bsp_geometry(c,index)
   retail_geometry.append({'bsp':index,'raw_bytes':len(converted['raw']),'control_bytes':len(converted['control'])})
  for n,t in c.tags.items():
   if t['group']=='Lbsp':
    for off in (0xe0,0xf0):
     idx=c.u(t['offset']+off+12)&65535
     _,_,raw=encode_lightmap_array(bs,idx)
     retail_lightmaps.append({'name':c.name(idx),'raw_bytes':len(raw)})
  return {'retail_visual_payloads':{'geometry':retail_geometry,'lightmaps':retail_lightmaps,
      'total_raw_bytes':sum(x['raw_bytes'] for x in retail_geometry+retail_lightmaps)},
    'candidate_cut':{'cut_y':cut,'cut_x':cut_x,'gulch_side':'Y <= cut_y and optional X <= cut_x','world_side':'Complement, including crossing polygons',
     'status':'Provisional canyon-mouth cut; final boundary requires visual/gameplay validation',
     'crossing_surfaces_retained_on_both_sides':int((gulch & world).sum())},
    'estimates':outputs,'source_visual_payloads':{'geometry':geometry,'lightmaps':lightmaps,
      'total_bytes':sum(x['raw_bytes'] for x in geometry+lightmaps)},
    'limitations':['Read-only estimate, not converted collision or fit certification.',
     'Counts retain ancestors of surviving surface references; no BSP planes are arbitrarily removed.',
     'Excludes instance collision, boundary walls, shared-BSP collision and final retail allocation overhead.',
     'Source geometry/lightmap bytes exclude textures, stock assets, audio, metadata and engine allocations.',
     'Visual geometry is unchanged by this analysis; no runtime/rendering performance measured.']}
 finally:c.close()


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--source',required=True);p.add_argument('--cut-y',type=float,default=-20)
 p.add_argument('--cut-x',type=float)
 p.add_argument('--report',type=Path,required=True);a=p.parse_args()
 report=a.report.resolve();repo=Path(__file__).resolve().parents[4]
 if not report.is_relative_to(repo):raise ValueError('Report must stay in repository')
 result=analyze(a.source,a.cut_y,a.cut_x);report.parent.mkdir(parents=True,exist_ok=True)
 report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()

