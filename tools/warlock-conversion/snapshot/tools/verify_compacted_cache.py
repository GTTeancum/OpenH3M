"""Verify repacked basis payloads and unchanged external page descriptors."""
import argparse,json,zlib,hashlib,struct
from cache_reader import Cache
from string_ids import StringTable
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--map',required=True)
parser.add_argument('--basis',required=True)
args=parser.parse_args()
a=Cache(args.basis);b=Cache(args.map);page_cache={}
def tables(c):
 z=next(t['offset'] for t in c.tags.values() if t['group']=='zone');p=next(t['offset'] for t in c.tags.values() if t['group']=='play');return z,p,c.block(z+88,64),c.block(p+48,16),c.block(p+24,88)
za,pa,ra,la,pga=tables(a);zb,pb,rb,lb,pgb=tables(b)
# All original external page descriptors must remain unchanged.
for x,y in zip(pga,pgb):
 if a.unpack('h',x+4)[0]>=0:assert a.data[x:x+88]==b.data[y:y+88]
def page(c,pages,index):
 key=(str(c.file.name),index)
 if key not in page_cache:
  p=pages[index];assert c.unpack('h',p+4)[0]==-1
  off,n,size=c.unpack('III',p+8);base=(c.u(0x484)+c.u(0x470))&0xffffffff;raw=c.data[base+off:base+off+n]
  data=zlib.decompress(raw,-15) if c.data[p+3]==0 else raw
  assert len(data)==size
  crc=c.u(p+20)
  if crc:assert (zlib.crc32(data)^0xffffffff)==crc
  page_cache[key]=data
 return page_cache[key]
from pathlib import Path
import xml.etree.ElementTree as E
co=int(next(f for f in E.parse(Path(__file__).resolve().parents[1]/'reference/plugins/zone.xml').getroot() if f.get('name')=='Native Resource Control Data').get('offset'),0)
ca=a.pointer(a.u(za+co+12));cb=b.pointer(b.u(zb+co+12));checked=0;payload_bytes=0
for i,(old,new) in enumerate(zip(ra,rb)):
 if b.unpack('h',new+34)[0]<0 or a.unpack('H',old+16)[0]==65535:continue
 ao,an=a.unpack('II',old+20);bo,bn=b.unpack('II',new+20);assert an==bn and a.data[ca+ao:ca+ao+an]==b.data[cb+bo:cb+bo+bn]
 al=la[a.unpack('h',old+34)[0]];bl=lb[b.unpack('h',new+34)[0]]
 for slot in (0,1):
  api=a.unpack('h',al+slot*2)[0];bpi=b.unpack('h',bl+slot*2)[0]
  if api<0 or bpi<0 or a.unpack('h',pga[api]+4)[0]!=-1:continue
  apos=a.u(al+4+slot*4);bpos=b.u(bl+4+slot*4)
  if bpi==api and apos==bpos and a.u(pga[api]+12)==b.u(pgb[bpi]+12):continue
  old_data=page(a,pga,api);new_data=page(b,pgb,bpi);part=new_data[bpos:]
  assert part==old_data[apos:apos+len(part)],(i,slot)
  payload_bytes+=len(part);checked+=1
print(json.dumps({'retained_repacked_segments_verified':checked,'bytes_verified':payload_bytes,'original_shared_descriptors_unchanged':True}))
a.close();b.close()
