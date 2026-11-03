import sys,json,re
from pathlib import Path
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
from string_ids import StringTable
out=Path('work/sky-bridge/lamp-native-01')
c=Cache('C:/X360/ISOs/H3M/maps/sandbox.map');strings=StringTable(c)
t=next(t['offset'] for i,t in c.tags.items() if t['group']=='rmt2' and c.name(i)==r'shaders\halogram_templates\_2_8_0_0_0_1_0')
names={usage:[strings.text(c.u(x)) for x in c.block(t+offset,4)] for usage,offset in ((0,108),(4,72),(5,84),(6,96))}

names[4].extend(['base_map','detail_map']);names[0].extend(['base_map','detail_map'])
passes=c.block(t+48,28);routes=c.block(t+60,4);entries=c.block(t+36,2)
refs={x['entry']:x for x in json.loads((out/'native-reflection.json').read_text())}
compiled=json.loads((out/'compilation.json').read_text())['programs']
externs={};persistent={};native_usages={}
sets={0:3,4:2,5:1,6:0,7:3,10:2,11:1}
for entry,row in refs.items():
 packed=c.unpack('H',entries[entry])[0];assert packed>>10==1
 p=passes[packed&1023];regs=row['registers'];used=set();usages=[]
 for usage in range(12):
  packed=c.unpack('H',p+usage*2)[0]
  data=[c.unpack('HBB',x) for x in routes[packed&1023:(packed&1023)+(packed>>10)]]
  usages.append(data)
  if usage not in sets: continue
  for register,source,flags in data:
   matches=[v for v in regs if v['set']==sets[usage] and v['register']<=register<v['register']+v['count']]
   assert len(matches)==1,(entry,usage,register,matches)
   v=matches[0];used.add(v['name'].lower())
   if usage in (7,10,11):
    key=v['name'].lower();value=(usage,source,flags,register-v['register'])
    assert key not in externs or externs[key]==value,(key,value,externs.get(key))
    externs[key]=value
 native_usages[entry]=usages
 for v in regs:
  if v['name'].lower() not in used:
   key=v['name'].lower();value=(v['set'],v['register'],v['count'])
   assert key not in persistent or persistent[key][:2]==value[:2],(key,value,persistent.get(key))
   persistent[key]=max(persistent.get(key,value),value,key=lambda x:x[2])
result=[];unresolved=[]
for row in compiled:
 entry=row['entry']
 if entry not in refs: continue
 text=(out/f"{row['name']}.asm").read_text()
 regs=[dict(name=n,set={'b':0,'i':1,'c':2,'s':3}[k],register=int(i),count=int(count)) for n,k,i,count in re.findall(r'^//\s+(\w+)\s+([cbis])(\d+)\s+(\d+)\s*$',text,re.M)]
 usages=[list(x) if j in (1,2,3,8,9) else [] for j,x in enumerate(native_usages[entry])];fixed=[]
 for v in regs:
  n=v['name'].lower();name=n.removesuffix('_xform') if v['set']==2 else n
  usage={3:0,2:4,1:5,0:6}[v['set']]
  if name in names[usage]:
   assert v['count']==1,(n,v)
   usages[usage].append((v['register'],names[usage].index(name),0))
  elif n in externs:
   usage,source,flags,offset=externs[n];assert offset==0
   usages[usage].append((v['register'],source,flags))
  elif n in persistent and persistent[n][:2]==(v['set'],v['register']) and v['count']<=persistent[n][2]: fixed.append(n)
  else: unresolved.append(dict(entry=entry,parameter=v,persistent=persistent.get(n)))
 result.append(dict(entry=entry,name=row['name'],shader=refs[entry]['shader'],registers=regs,usages=usages,persistent=fixed))
from lightmap_register_reservations import require_safe_material_routes, require_safe_shared_float_uploads
require_safe_material_routes(dict(programs=result));require_safe_shared_float_uploads(dict(programs=result))
report=dict(names=names,externs=externs,persistent=persistent,programs=result,unresolved=unresolved)
(out/'route-plan.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(unresolved=unresolved,externs=externs,program_count=len(result)),indent=2));c.close()
