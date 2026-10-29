import struct,mmap,json,xml.etree.ElementTree as ET
from pathlib import Path
R=Path.cwd();p=Path('D:/SteamLibrary/steamapps/workshop/content/976730/2977651586/maps/warlock.map')
with p.open('rb') as f:
 d=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
 b,ix=struct.unpack_from('<QQ',d,0x2e0);s=struct.unpack_from('<I',d,16)[0];o=lambda a:a-b+s
 ng,ga,nt,ta=struct.unpack_from('<QQQQ',d,o(ix))
 groups=[d[o(ga)+i*16:o(ga)+i*16+4][::-1].decode('ascii') for i in range(ng)]
 tags={}
 for i in range(nt):
  g,salt,ptr=struct.unpack_from('<HHI',d,o(ta)+i*8)
  if g!=65535 and ptr:tags[i]=(groups[g],o(ptr*4))
 names_base,names_size,names_index=struct.unpack_from('<III',d,0x24)
 def name(i):
  rel=struct.unpack_from('<I',d,names_index+i*4)[0]
  if rel==0xffffffff:return None
  at=names_base+rel
  assert names_base<=at<names_base+names_size
  return d[at:d.find(b'\0',at)].decode('utf-8',errors='replace')
 report={}
 for i,(g,t) in tags.items():
  if g not in ('sbsp','sLdT'):continue
  schema=ET.parse(R/f'.local/reference/mcc/{g}.xml').getroot();blocks=[]
  for field in schema:
   if field.tag.lower()!='tagblock':continue
   n,ptr=struct.unpack_from('<II',d,t+int(field.attrib['offset'],0));item={'name':field.attrib['name'],'count':n}
   if n and field.attrib['name']=='Materials':
    refs=[]
    for k in range(n):
     at=o(ptr*4)+k*int(field.attrib['elementSize'],0);datum=struct.unpack_from('<I',d,at+12)[0];refs.append(hex(datum))
    item['references']=refs
    item['materials']=[]
    for ref in refs:
     tid=int(ref,16)&65535; group,at=tags[tid];mat={'datum':ref,'name':name(tid),'group':group,'textures':[]}
     if group in ('rmsh','rmtr','rmfl'):
      pn,pp=struct.unpack_from('<II',d,at+0x28)
      if pn:
       tn,tp=struct.unpack_from('<II',d,o(pp*4)+0x10)
       for j in range(tn):
        bid=struct.unpack_from('<I',d,o(tp*4)+j*0x1c+12)[0]
        mat['textures'].append({'datum':hex(bid),'name':name(bid&65535) if bid!=0xffffffff else None})
     item['materials'].append(mat)
   blocks.append(item)
  report[f'{i}:{g}']={'offset':t,'blocks':blocks}
 (R/'.local/reports/mcc-visual-data.json').write_text(json.dumps(report,indent=2))
 for v in report.values():
  for block in v['blocks']:
   if 'materials' in block:
    print('distinct material refs',len(set(block['references'])))
    for m in block['materials'][:12]:print(m)
