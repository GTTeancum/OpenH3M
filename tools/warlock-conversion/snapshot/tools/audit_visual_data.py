import struct,json,xml.etree.ElementTree as ET
from pathlib import Path
R=Path.cwd()
p=R/'.local/candidate/lockout.map'; d=p.read_bytes()
u=lambda o:struct.unpack_from('>I',d,o)[0]
b=u(0x2e8); f=(u(0x48c)+u(0x474))&0xffffffff
o=lambda a:a-b+f
ix=o(u(0x10)); ng,ga,nt,ta=struct.unpack_from('>4I',d,ix)
groups=[d[o(ga)+i*16:o(ga)+i*16+4].decode('ascii') for i in range(ng)]
tags={}
for i in range(nt):
 g,s,a=struct.unpack_from('>HHI',d,o(ta)+i*8)
 if g!=65535 and a not in (0,0xffffffff):tags[i]=(groups[g],o(a))
report={}
for i,(g,t) in tags.items():
 if g not in ('sbsp','sLdT','scnr'):continue
 schema=ET.parse(R/f'.local/reference/plugins/{g}.xml').getroot()
 blocks=[]
 for field in schema:
  if field.tag.lower()!='tagblock':continue
  off=int(field.attrib['offset'],0);n,ptr=struct.unpack_from('>II',d,t+off)
  item={'name':field.attrib['name'],'count':n,'pointer':hex(ptr)}
  if n and field.attrib['name']=='Materials':
   item['references']=[]
   for k in range(n):
    at=o(ptr)+k*int(field.attrib['elementSize'],0);datum=u(at+12)
    item['references'].append({'datum':hex(datum),'target':tags.get(datum&65535)})
  if n and field.attrib['name']=='Meshes':
   item['mesh_summary']=[]
   for k in range(n):
    at=o(ptr)+k*int(field.attrib['elementSize'],0)
    pn,pp=struct.unpack_from('>II',d,at)
    item['mesh_summary'].append({'parts':pn,'buffers':struct.unpack_from('>10h',d,at+0x18),'formats':list(d[at+0x2c:at+0x31]),'materials':[struct.unpack_from('>h',d,o(pp)+j*16)[0] for j in range(pn)]})
  if n and field.attrib['name']=='Compression Info':item['values']=[struct.unpack_from('>HH10f',d,o(ptr)+k*44) for k in range(n)]
  blocks.append(item)
 report[f'{i}:{g}']={'address':hex(t-f+b),'blocks':blocks}
out=R/'.local/reports/visual-data-audit.json';out.write_text(json.dumps(report,indent=2))
for tag,v in report.items():
 print(tag,v['address'])
 for x in v['blocks']:
  if x['count']:print(x['name'],x['count'],str({k:v for k,v in x.items() if k not in ('name','count','pointer')})[:1800])
