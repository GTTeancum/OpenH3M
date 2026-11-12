"""Read rigid H4 source triangles for anchor proofs, without modifying assets.

Retail Gen4 layouts are documented in the repository's Halo4-mode/zone/play
XML references. Pages use the existing XMem/LZX decoder and must pass their
native CRC. This reader deliberately rejects unsupported nodes and buffers.
"""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import runpy
import struct
import subprocess
import numpy as np
import zlib

ROOT=Path(__file__).resolve().parents[2]
RESEARCH=ROOT/'work/h4-forge-research'
OUT=RESEARCH/'isolated/source-render'

def extract(name):
 assert name and all(c.isalnum() or c=='_' for c in name)
 with contextlib.redirect_stdout(io.StringIO()):h4=runpy.run_path(str(RESEARCH/'inspect_anchors.py'))
 data=h4['d'];uint=h4['u'];offset=h4['off'];block=h4['block'];tags={}
 for index in range(h4['nt']):
  group,salt,ptr=struct.unpack_from('>HHI',data,offset(h4['tp'])+8*index)
  if group==65535 or ptr in (0,0xffffffff):continue
  tags[index]=dict(group=h4['groups'][group],offset=offset(ptr),name=h4['text'](h4['names'],uint(h4['ni']+index*4)))
 candidates=[(i,t) for i,t in tags.items() if t['group']=='mode' and t['name'].endswith('\\'+name)]
 assert len(candidates)==1;index,model=candidates[0];at=model['offset']
 nodes=block(at+0x30,112);assert len(nodes)==1
 assert struct.unpack_from('>h',data,nodes[0]+4)[0]==-1
 assert struct.unpack_from('>7f',data,nodes[0]+12)==(0,0,0,0,0,0,1)
 assert struct.unpack_from('>f',data,nodes[0]+40)[0]==1
 assert struct.unpack_from('>9f',data,nodes[0]+44)==(1,0,0,0,1,0,0,0,1)
 assert struct.unpack_from('>3f',data,nodes[0]+80)==(0,0,0)
 compression=block(at+0x80,52);assert len(compression)==1
 assert struct.unpack_from('>H',data,compression[0])[0]&1
 bounds=np.array(struct.unpack_from('>6f',data,compression[0]+4)).reshape(3,2)
 zone=next(t['offset'] for t in tags.values() if t['group']=='zone')
 datum=uint(at+0xf8);records=block(zone+0x58,68);assert datum&65535<len(records)
 record=records[datum&65535]
 assert uint(record+12)&65535==index and struct.unpack_from('>H',data,record+16)[0]==datum>>16
 locations=[uint(p) for p in block(record+0x38,4)]
 assert len(locations)==3 and locations[0]!=0xffffffff and locations[1:]==[0xffffffff]*2
 length=uint(record+0x14);assert locations[0]+length<=uint(zone+0x154)
 base=offset(uint(zone+0x160));control=data[base+locations[0]:base+locations[0]+length]
 fix={uint(p):uint(p+4) for p in block(record+0x20,8)}
 assert all(p+4<=length for p in fix)
 root=uint(record+0x1c);assert root>>29==1;root&=0x1fffffff;assert root+48<=length
 layout=zone;segments=block(zone+0x4c,24);pages=block(zone+0x34,88)
 if not segments:
  layout=next(t['offset'] for t in tags.values() if t['group']=='play')
  segments=block(layout+0x30,24);pages=block(layout+0x18,88)
 segment_index=struct.unpack_from('>h',data,record+0x1a)[0];assert 0<=segment_index<len(segments)
 segment=segments[segment_index];raw=[];page_evidence=[]
 OUT.mkdir(exist_ok=True);page_dir=OUT/'pages';page_dir.mkdir(exist_ok=True)
 for part in range(3):
  page_index=struct.unpack_from('>h',data,segment+12+2*part)[0]
  if page_index<0:raw.append(b'');continue
  assert page_index<len(pages);page=pages[page_index]
  shared=struct.unpack_from('>h',data,page+4)[0]
  assert shared==-1,'Shared source render page needs an explicit repository-local source mapping'
  location,compressed,size,crc=struct.unpack_from('>4I',data,page+8)
  assert 0<size<=256*1024*1024
  page_start=((uint(0x480)+uint(0x494))&0xffffffff)+location
  payload=data[page_start:page_start+compressed];assert len(payload)==compressed
  decoded=page_dir/f'{page_index}.bin'
  if decoded.exists():value=decoded.read_bytes()
  elif data[page+3]==255:value=payload
  else:
   assert data[page+3]==0
   packed=page_dir/f'{page_index}.xmem';unchecked=page_dir/f'{page_index}.unchecked'
   packed.write_bytes(payload)
   subprocess.run([str(ROOT/'work/rexglue-sdk/out/win-amd64/h4_forge_lzx_decode.exe'),str(packed),str(unchecked),str(size)],cwd=ROOT,check=True,capture_output=True,timeout=60)
   value=unchecked.read_bytes()
  assert len(value)==size and zlib.crc32(value)^0xffffffff==crc
  decoded.write_bytes(value)
  start=uint(segment+part*4);assert start<=size;raw.append(value[start:])
  page_evidence.append(dict(page=page_index,part=part,offset=start,bytes=size,crc=hex(crc),sha256=hashlib.sha256(value).hexdigest()))
 def unpack(fmt,at):return struct.unpack_from('>'+fmt,control,at)
 def pointer(field):
  ptr=fix[field];assert ptr>>29==1;return ptr&0x1fffffff
 def buffers(relative):
  count=unpack('I',root+relative)[0];table=pointer(root+relative+4)
  assert count<=65535 and table+count*12<=len(control)
  return [pointer(table+12*i) for i in range(count)]
 def raw_buffer(field,length):
  ptr=fix[field];kind=(ptr>>29)-2;start=ptr&0x1fffffff;assert 0<=kind<3
  result=raw[kind][start:start+length];assert len(result)==length;return result
 vb=buffers(24);ib=buffers(36);all_triangles=[];mesh_evidence=[]
 for mesh_index,mesh in enumerate(block(at+0x68,112)):
  parts=block(mesh,24)
  if not parts:continue
  flags=struct.unpack_from('>H',data,mesh+0x2e)[0]
  assert data[mesh+0x30]==0 and data[mesh+0x31]==1 and not flags&((1<<4)|(1<<8)|(1<<10))
  vi,ii=struct.unpack_from('>h',data,mesh+0x18)[0],struct.unpack_from('>h',data,mesh+0x2a)[0]
  assert 0<=vi<len(vb) and 0<=ii<len(ib)
  count,fmt,stride=unpack('IHH',vb[vi]);assert fmt==2 and stride==20
  vertex_raw=raw_buffer(vb[vi]+20,count*stride)
  quantized=np.ndarray((count,3),dtype='>u2',buffer=vertex_raw,strides=(stride,2))
  positions=bounds[:,0]+quantized.astype(float)/65535*(bounds[:,1]-bounds[:,0])
  primitive=unpack('I',ib[ii])[0];assert primitive==data[mesh+0x34] and primitive in (3,5)
  # Gen4 retains the four-byte field after primitive type that Gen3 lacks.
  index_size=unpack('I',ib[ii]+8)[0];assert index_size>0 and index_size%2==0
  index_raw=raw_buffer(ib[ii]+20,index_size);indices=np.frombuffer(index_raw,dtype='>u2');candidates=[]
  for part in parts:
   start,length=struct.unpack_from('>II',data,part+4);assert start+length<=len(indices)
   values=indices[start:start+length]
   if primitive==3:
    assert length%3==0;tris=values.reshape(-1,3)
   else:tris=np.stack([values[:-2],values[1:-1],values[2:]],axis=1) if length>=3 else np.empty((0,3),dtype=int)
   valid=(tris!=65535).all(axis=1)&(tris[:,0]!=tris[:,1])&(tris[:,1]!=tris[:,2])&(tris[:,0]!=tris[:,2])
   tris=tris[valid];assert not tris.size or tris.max()<count;candidates.extend(tris.tolist())
  triangles=positions[np.array(candidates,dtype=int)];all_triangles.extend(triangles.tolist())
  mesh_evidence.append(dict(mesh=mesh_index,vertices=count,triangles=len(triangles),primitive=primitive,vertices_sha256=hashlib.sha256(vertex_raw).hexdigest(),indices_sha256=hashlib.sha256(index_raw).hexdigest()))
 triangles=np.array(all_triangles);cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
 triangles=triangles[np.linalg.norm(cross,axis=1)>1e-10];assert len(triangles)
 path=OUT/f'{name}.npz';np.savez_compressed(path,triangles=triangles)
 evidence=dict(name=model['name'],tag_index=index,resource=hex(datum),cache_sha256=hashlib.sha256(data).hexdigest(),
     pages=page_evidence,meshes=mesh_evidence,triangles=len(triangles),compression_bounds=bounds.tolist(),
     referenced_bounds=np.stack([triangles.min(axis=(0,1)),triangles.max(axis=(0,1))],axis=1).tolist(),
     triangle_file=str(path.relative_to(ROOT)),triangle_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 (OUT/f'{name}.json').write_text(json.dumps(evidence,indent=2)+'\n')
 return evidence

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('name');args=parser.parse_args()
 print(json.dumps(extract(args.name),indent=2))
