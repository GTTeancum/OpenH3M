import sys,json,struct,collections
from pathlib import Path
sys.path.insert(0,str(Path('tools/warlock-conversion/snapshot/tools').resolve()))
from cache_reader import Cache
from forge_mopp import terminals
out={}
for name,path,mcc in [('stock',Path('../../maps/zanzibar.map'),False),('source',Path(r'D:\SteamLibrary\steamapps\workshop\content\976730\3597611181\maps\forge_halo.map'),True),('candidate',(Path(sys.argv[1]) if len(sys.argv)>1 else Path('work/forge-world/sandbox-sky.map')),False)]:
 c=Cache(path,mcc);roots=[t['offset'] for t in c.tags.values() if t['group']=='Lbsp'] if mcc else [b for t in c.tags.values() if t['group']=='sLdT' for b in c.block(t['offset']+4,436)]
 bsps=[]
 for root in roots:
  meshrows=c.block(root+0x134,76); records=[]
  for mi,row in enumerate(c.block(root+0x170,32)):
   size=c.u(row);pointer=c.pointer(c.u(row+12)) if size else 0;offset=0;keys=[];headers=[]
   while offset<size:
    p=pointer+offset;length=c.u(p+(40 if mcc else 36));headers.append(c.unpack('4f',p+16));keys.extend(k for _,_,k in terminals(c.data[p+48:p+48+length]));offset=(offset+48+length+15)&~15
   reorder=[c.unpack('h',r)[0] for r in c.block(row+20,2)]
   records.append({'headers':headers,'keys':sorted(keys),'reorder':reorder,'subpart_count':c.u(meshrows[mi]+12)})
  bsps.append(records)
 out[name]=bsps;c.close()
comparison=[]
for bi,(s,d) in enumerate(zip(out['source'],out['candidate'])):
 for mi,(a,b) in enumerate(zip(s,d)):
  if a!=b:comparison.append([bi,mi])
out['source_candidate_mismatches']=comparison
Path('work/forge-world/visibility-tree-audit.json').write_text(json.dumps(out))
print('source/candidate mismatched per-mesh visibility trees:',comparison)
for name in ('stock','source','candidate'):
 print(name,'meshes with keys beyond subpart count',sum(any(k>=r['subpart_count'] for k in r['keys']) for bs in out[name] for r in bs))
