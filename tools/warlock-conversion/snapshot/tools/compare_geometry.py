import json,xml.etree.ElementTree as ET
from pathlib import Path
from cache_reader import Cache
R=Path.cwd();src=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/2977651586/maps/warlock.map',True);dst=Cache(R/'.local/candidate/lockout.map')
ss=ET.parse(R/'.local/reference/mcc/sbsp.xml').getroot();ds=ET.parse(R/'.local/reference/plugins/sbsp.xml').getroot()
formats={'float32':'f','point3':'3f','vector3':'3f','rangef':'2f','int16':'h','uint16':'H','flags16':'H','enum16':'h','int8':'b'}
report={}
for name in ('Instanced Geometry Instances','Clusters','Compression Info'):
 a=[x for x in ss if x.attrib.get('name')==name][-1];b=[x for x in ds if x.attrib.get('name')==name][-1]
 sa=src.block(src.tags[9178]['offset']+int(a.attrib['offset'],0),int(a.attrib['elementSize'],0));da=dst.block(dst.tags[8798]['offset']+int(b.attrib['offset'],0),int(b.attrib['elementSize'],0))
 result={'source_count':len(sa),'candidate_count':len(da),'fields':{}}
 for x in a:
  k=x.attrib.get('name');fmt=formats.get(x.tag.lower());ys=[y for y in b if y.attrib.get('name')==k]
  if not fmt or not ys or k=='Unknown':continue
  y=ys[0];diff=[]
  for i,(so,do) in enumerate(zip(sa,da)):
   sv=src.unpack(fmt,so+int(x.attrib['offset'],0));dv=dst.unpack(fmt,do+int(y.attrib['offset'],0))
   if sv!=dv:diff.append({'index':i,'source':sv,'candidate':dv})
  result['fields'][k]={'mismatch_count':len(diff),'examples':diff[:3]}
 report[name]=result
(R/'.local/reports/geometry-comparison.json').write_text(json.dumps(report,indent=2))
for k,v in report.items():
 print(k,v['source_count'],v['candidate_count'])
 for n,f in v['fields'].items():
  if f['mismatch_count']:print(n,f)
src.close();dst.close()
