import sys,json,collections,xml.etree.ElementTree as E
from pathlib import Path
sys.path.insert(0,str(Path('tools/warlock-conversion/snapshot/tools').resolve()))
from cache_reader import Cache
out={}
for name,path,mcc in [('guardian',Path('../../maps/guardian.map'),False),('zanzibar',Path('../../maps/zanzibar.map'),False),('source',Path(r'D:\SteamLibrary\steamapps\workshop\content\976730\3597611181\maps\forge_halo.map'),True),('candidate',(Path(sys.argv[1]) if len(sys.argv)>1 else Path('work/forge-world/sandbox-sky.map')),False)]:
 c=Cache(path,mcc);schema=E.parse('tools/warlock-conversion/snapshot/reference/'+('mcc' if mcc else 'plugins')+'/sbsp.xml').getroot();mf=next(f for f in schema if f.get('name')=='Materials')
 bsps=[t['offset'] for t in c.tags.values() if t['group']=='sbsp'];roots=[t['offset'] for t in c.tags.values() if t['group']=='Lbsp'] if mcc else [b for t in c.tags.values() if t['group']=='sLdT' for b in c.block(t['offset']+4,436)]
 issues=[];used=collections.Counter()
 for bi,(b,root) in enumerate(zip(bsps,roots)):
  mats=c.block(b+int(mf.get('offset'),0),int(mf.get('elementSize'),0))
  for mi,m in enumerate(c.block(root+0x134,76)):
   prt=c.data[m+47]
   for p in c.block(m,16):
    material=c.unpack('h',p)[0];datum=c.u(mats[material]+12);tag=c.tags[datum&65535];group=tag['group'];used[group]+=1
    if not prt:continue
    for post in c.block(tag['offset']+40,140 if mcc else 132):
     tid=c.u(post+12)&65535;mask=c.u(c.tags[tid]['offset']+32)
     if not mask&(1<<(5+prt)):
      issues.append({'bsp':bi,'mesh':mi,'material':material,'group':group,'prt':prt,'mask':hex(mask),'name':c.name(datum&65535)})
 out[name]={'material_part_uses':dict(used),'missing_prt_entrypoints':issues};c.close()
Path('work/forge-world/shader-entrypoint-audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out)[:8000])
