import sys,json,re
from pathlib import Path
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
from string_ids import StringTable
c=Cache('C:/X360/ISOs/H3M/maps/sandbox.map');st=StringTable(c);t=next(t for i,t in c.tags.items() if t['group']=='rmt2' and c.name(i)==r'shaders\halogram_templates\_0_1_1_0_0_0_1');tm=t['offset'];pix=c.tags[c.u(tm+28)&65535]['offset'];pr=c.block(pix+20,80);entries=c.block(pix+4,2);out=[]
for n,e in enumerate(entries):
 start,count=c.unpack('BB',e)
 for idx in range(start,start+count):
  p=pr[idx];constants=[dict(name=st.text(c.u(r)),register=c.unpack('H',r+4)[0],count=c.data[r+6],set=c.data[r+7]) for r in c.block(p+40,8)];out.append(dict(entry=n,shader=idx,registers=constants,gprs=c.u(p+72)))
Path('work/powerhouse/../sky-bridge/soft-native-01/native-reflection.json').write_text(json.dumps(out,indent=2));print(json.dumps([x for x in out if x['entry']==3],indent=2));c.close()
