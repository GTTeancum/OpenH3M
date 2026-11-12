"""Evaluate topology-preserving index ordering; cache estimates are not measured FPS."""
import ctypes as C,sys,json,collections,struct,hashlib,zlib
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
lib=C.CDLL(str(root/'.local/map-review-deps/meshoptimizer-build/Release/meshoptimizer.dll'))
class Stats(C.Structure):_fields_=[('vertices',C.c_uint),('warps',C.c_uint),('acmr',C.c_float),('atvr',C.c_float)]
lib.meshopt_analyzeVertexCache.argtypes=[C.POINTER(C.c_uint),C.c_size_t,C.c_size_t,C.c_uint,C.c_uint,C.c_uint];lib.meshopt_analyzeVertexCache.restype=Stats
lib.meshopt_optimizeVertexCache.argtypes=[C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.c_size_t,C.c_size_t]
c=Cache(root/'work/powerhouse/zanzibar-139.map');sc=next(t['offset'] for t in c.tags.values() if t['group']=='scnr');lm=c.tags[c.u(sc+0x6fc)&65535]['offset'];lb=c.block(lm+4,436)[0];r=Resource(c,c.u(lb+0x1ac));bsp=next(t['offset'] for t in c.tags.values() if t['group']=='sbsp');ibs=r.buffers('index');rows=[];seen=set();patched={};spans=[]
for mi,m in enumerate(c.block(bsp+0x2e4,76)):
 ib=c.unpack('h',m+0x28)[0]
 if ib<0:continue
 assert c.unpack('B',m+0x30)[0]==3
 b=ibs[ib];n=r.unpack('I',b+4)[0];ptr=r.fix[b+16];raw=r.raw[{0x40000000:0,0x60000000:1}[ptr&0xe0000000]];off=ptr&0x1fffffff;indices=struct.unpack_from('>'+str(n//2)+'H',raw,off)
 subs=c.block(m+12,8)
 for pi,p in enumerate(c.block(m,16)):
  part_type=c.unpack('B',p+12)[0]
  if part_type not in (1,2,3):continue
  first,count=c.unpack('2H',p+8)
  for si,sub in enumerate(subs[first:first+count],first):
   start,size=c.unpack('2H',sub);key=(ib,start,size)
   if key in seen or size<3:continue
   seen.add(key);assert size%3==0 and start+size<=len(indices)
   src=indices[start:start+size];vc=max(src)+1;array=(C.c_uint*size)(*src);dest=(C.c_uint*size)()
   lib.meshopt_optimizeVertexCache(dest,array,size,vc)
   assert collections.Counter(zip(src[::3],src[1::3],src[2::3]))==collections.Counter(zip(dest[::3],dest[1::3],dest[2::3]))
   before=lib.meshopt_analyzeVertexCache(array,size,vc,32,32,256);after=lib.meshopt_analyzeVertexCache(dest,size,vc,32,32,256)
   if after.vertices < before.vertices:
    segment={0x40000000:0,0x60000000:1}[ptr&0xe0000000];at=off+start*2
    patched.setdefault(segment,bytearray(r.raw[segment]))[at:at+size*2]=struct.pack('>'+str(size)+'H',*dest)
    spans.append((segment,at,at+size*2))
   rows.append(dict(mesh=mi,part=pi,subpart=si,triangles=size//3,before=before.vertices,after=after.vertices))
report=dict(tool='meshoptimizer v1.3, 9e1f07b159d3cb777f1c67ed31fc11fd117986f4',source='https://github.com/zeux/meshoptimizer',scope='Per opaque subpart; triangle tuples/winding preserved exactly. Simplified cache simulation only, no runtime gain claimed; map unchanged.',subparts=len(rows),triangles=sum(x['triangles'] for x in rows),before=sum(x['before'] for x in rows),after=sum(min(x['before'],x['after']) for x in rows),improved_subparts=sum(x['after']<x['before'] for x in rows),rows=rows)
(root/'work/map-review-20261105/powerhouse-cache-order-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
if '--build' in sys.argv:
 from map_builder import MapBuilder
 from build_scenario_checkpoint import resource_salt
 from resource_reader import Resource
 import numpy as np
 for segment,data in patched.items():
  ranges=sorted((a,b) for seg,a,b in spans if seg==segment)
  assert all(a[1]<=b[0] for a,b in zip(ranges,ranges[1:])), 'Overlapping subparts need explicit handling'
  permitted=np.zeros(len(data),dtype=bool)
  for a,b in ranges:permitted[a:b]=True
  diffs=np.frombuffer(data,dtype=np.uint8)!=np.frombuffer(r.raw[segment],dtype=np.uint8)
  assert not np.any(diffs & ~permitted)
 b=MapBuilder(root/'work/powerhouse/zanzibar-139.map',0);salt=resource_salt('C:/X360/ISOs/H3M/default.xex')
 zone=next(t['offset'] for t in c.tags.values() if t['group']=='zone');play=next(t['offset'] for t in c.tags.values() if t['group']=='play')
 resource=c.block(zone+88,64)[c.u(lb+0x1ac)&65535];location=c.block(play+48,16)[c.unpack('h',resource+34)[0]]
 pages=c.block(play+24,88);page_ids=c.unpack('2h',location);offsets=c.unpack('2I',location+4)
 for segment,data in patched.items():
  assert offsets[segment]==0,'Nonzero page slice requires whole-page preservation'
  page=pages[page_ids[segment]];assert c.unpack('h',page+4)[0]==-1 and c.u(page+16)==len(data)
  compressed=zlib.compress(bytes(data))[2:-4];new_offset=b.append_raw(compressed);address=page-c.start+c.base
  b.put(address+3,'B',0);b.put(address+8,'4I',new_offset,len(compressed),len(data),zlib.crc32(data)^0xffffffff)
  hashes=b''.join(hashlib.sha1(salt+x).digest() for x in (data,data[:1024],data[-1024:]))
  for i,v in enumerate(hashes):b.put(address+24+i,'B',v)
 out=root/'work/map-review-20261105/powerhouse-cache-order.map';assert not out.exists();out.write_bytes(b.finish(salt));b.close()
 check=Cache(out);check_resource=Resource(check,c.u(lb+0x1ac))
 assert check_resource.data==r.data and check_resource.fix==r.fix
 for segment,original in enumerate(r.raw):assert check_resource.raw[segment]==patched.get(segment,original)
 report.update(candidate=str(out),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),resource_controls_preserved=True,vertex_and_other_payload_bytes_preserved=True,changed_subparts=len(spans),native_tested=False)
 (root/'work/map-review-20261105/powerhouse-cache-order-build.json').write_text(json.dumps(report,indent=2));check.close()
 print('Private topology-preserving candidate built and resource bytes verified:',out)
c.close()

