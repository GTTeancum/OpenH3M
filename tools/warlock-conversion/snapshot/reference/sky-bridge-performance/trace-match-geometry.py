import argparse,sys,json,struct,hashlib,collections
from pathlib import Path
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
from resource_reader import Resource
parser=argparse.ArgumentParser()
parser.add_argument('--trace-dir',type=Path,default=Path('work/sky-bridge/draw-trace-20261103-200444'))
root=parser.parse_args().trace_dir
root.resolve().relative_to(Path(__file__).resolve().parents[5])
c=Cache('work/sky-bridge/payload-32/sky_bridge.map')
c.shared_paths={'maps\\shared.map':Path('C:/X360/ISOs/H3M/maps/shared.map')};c.decoded_pages={}
materials=json.loads(Path('work/sky-bridge/card-material-geometry-audit.json').read_text())['materials']
material_by_slot={m['slot']:m for m in materials}
blobs=collections.defaultdict(list); meshes=[]
for tid,t in c.tags.items():
 roots=[]
 if t['group']=='sbsp': roots=[(t['offset'],0x2e4,0x37c)]
 elif t['group']=='sLdT': roots=[(r,0x134,0x1ac) for r in c.block(t['offset']+4,436)]
 for base,mesh_offset,resource_offset in roots:
  records=c.block(base+mesh_offset,76)
  if not records:continue
  r=Resource(c,c.u(base+resource_offset));vb=r.buffers('vertex');ib=r.buffers('index')
  print('geometry owner',tid,t['group'],'meshes',len(records),'vertex buffers',len(vb),'index buffers',len(ib))
  if not vb or not ib:continue
  def raw(field,size):
   ptr=r.fix[field]; return r.raw[(ptr>>29)-2][(ptr&0x1fffffff):(ptr&0x1fffffff)+size]
  for mi,mesh in enumerate(records):
   vi=c.unpack('h',mesh+24)[0]; ii=c.unpack('h',mesh+40)[0]
   if vi<0 or ii<0:continue
   vertex=vb[vi]; count,fmt,stride=r.unpack('IHH',vertex)
   positions=raw(vertex+20,count*stride)
   index=ib[ii];indices=raw(index+16,r.unpack('I',index+4)[0])
   for pi,part in enumerate(c.block(mesh,16)):
    slot=c.unpack('h',part)[0];start,length=c.unpack('HH',part+4)
    e=dict(owner=tid,owner_group=t['group'],mesh=mi,part=pi,material_slot=slot,index_start=start,index_count=length,
      vertex_format=fmt,vertex_stride=stride,vertex_count=count,
      vertex_prefix_sha256=hashlib.sha256(positions[:512]).hexdigest(),vertex_prefix_length=min(512,len(positions)),
      material=material_by_slot.get(slot,{}).get('source'),target_material=material_by_slot.get(slot,{}).get('target_id'))
    prefix=indices[start*2:start*2+min(512,length*2)]
    if prefix:blobs[hashlib.sha256(prefix).hexdigest()].append(e)
   meshes.append((tid,mi,count,fmt,stride))
matches=[];prefixes=0
with (root/'draws.bin').open('rb') as f:
 while h:=f.read(8):
  kind,size=struct.unpack('<II',h);d=f.read(size)
  if kind==6: seq,address,length,recorded=struct.unpack('<4Q',d)
  elif kind==7:
   prefixes+=1;digest=hashlib.sha256(d).hexdigest()
   if digest in blobs:matches.append(dict(sequence=seq,address=address,length=length,prefix_length=recorded,matches=blobs[digest]))
report={'mesh_count':len(meshes),'prefixes':prefixes,'matched_prefixes':len(matches),'matches':matches}
(root/'geometry-prefix-matches.json').write_text(json.dumps(report,indent=2)+'\n')
print('meshes',len(meshes),'prefixes',prefixes,'matched',len(matches));print('formats',collections.Counter((m[3],m[4]) for m in meshes));print(json.dumps(matches[:2],indent=2))
c.close()
