import sys,json
from pathlib import Path
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
from string_ids import StringTable
c=Cache('C:/X360/ISOs/H3M/maps/salvation.map');st=StringTable(c);name=r'shaders\shader_templates\_6_2_0_1_2_2_0_0_0_0';t=next(t['offset'] for k,t in c.tags.items() if t['group']=='rmt2' and c.name(k)==name);pix=c.tags[c.u(t+28)&65535]['offset'];pr=c.block(pix+20,80);entries=c.block(pix+4,2);refs=[]
for n,e in enumerate(entries):
 start,count=c.unpack('BB',e)
 for idx in range(start,start+count):
  p=pr[idx];refs.append(dict(entry=n,shader=idx,registers=[dict(name=st.text(c.u(r)),register=c.unpack('H',r+4)[0],count=c.data[r+6],set=c.data[r+7]) for r in c.block(p+40,8)],gprs=c.u(p+72)))
Path('work/sky-bridge/water-card-native-01/native-reflection.json').write_text(json.dumps(refs,indent=2));print('entries',[r['entry'] for r in refs]);print('pixel regs',next(r for r in refs if r['entry']==3)['registers'])
