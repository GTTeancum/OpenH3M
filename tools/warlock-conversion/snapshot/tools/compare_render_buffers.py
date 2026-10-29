"""Compare converted render geometry against MCC without extracting asset files."""
import json,collections
import numpy as np
from pathlib import Path
from cache_reader import Cache
from resource_reader import Resource
R=Path(__file__).resolve().parents[2]
s=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/2977651586/maps/warlock.map',True);d=Cache(R/'.local/candidate/lockout.map');a=Resource(s,0xbe0);b=Resource(d,4557)
report={'vertex_formats':{},'index_mismatches':[],'position_uv_mismatches':[],'normal_mismatches':[]};counts=collections.Counter()
for i,(x,y) in enumerate(zip(a.buffers('index'),b.buffers('index'))):
 ns=a.unpack('I',x+4)[0];nd=b.unpack('I',y+4)[0];rs=a.raw[0][a.ptr(x+16):a.ptr(x+16)+ns];rd=b.raw[0][b.ptr(y+16):b.ptr(y+16)+nd]
 if ns!=nd or not np.array_equal(np.frombuffer(rs,dtype='<u2'),np.frombuffer(rd,dtype='>u2')):report['index_mismatches'].append(i)
for i,(x,y) in enumerate(zip(a.buffers('vertex'),b.buffers('vertex'))):
 n,f,ss=a.unpack('IHH',x);nn,ff,ds=b.unpack('IHH',y);counts[(f,ss,ds)]+=1
 if f not in (1,2):continue
 assert n==nn and f==ff
 st=a.ptr(x+20);dt=b.ptr(y+20);kind='u2' if f==2 else 'u4';unit=2 if f==2 else 4;num=6 if f==2 else 5
 src=np.frombuffer(a.raw[0],dtype='<'+kind,count=n*ss//unit,offset=st).reshape(n,ss//unit)[:,:num]
 dst=np.frombuffer(b.raw[0],dtype='>'+kind,count=n*ds//unit,offset=dt).reshape(n,ds//unit)[:,:num]
 if not np.array_equal(src,dst):report['position_uv_mismatches'].append(i)
 for channel in range(3):
  start=12 if f==2 else 20
  ns=np.ndarray((n,3),dtype='<i2',buffer=a.raw[0],offset=st+start+channel*8,strides=(ss,2)).astype(float)/32767
  packed=np.ndarray((n,),dtype='>u4',buffer=b.raw[0],offset=dt+start+channel*4,strides=(ds,)).astype(np.uint32)
  components=[]
  for shift,bits in ((0,10),(10,11),(21,11)):
   v=((packed>>shift)&((1<<bits)-1)).astype(np.int32);v[v>=(1<<(bits-1))]-=1<<bits;components.append(v/((1<<(bits-1))-1))
  nd=np.stack(components,axis=1)
  error=np.max(np.abs(ns-nd)) if n else 0
  if error>0.005:report['normal_mismatches'].append({'buffer':i,'channel':channel,'max_error':float(error)})
report['vertex_formats']={str(k):v for k,v in counts.items()};(R/'.local/reports/geometry-payload-comparison.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2)[:3500]);s.close();d.close()
