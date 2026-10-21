import sys,json,struct
from pathlib import Path
sys.path.insert(0,str(Path('tools/warlock-conversion/snapshot/tools').resolve()))
from cache_reader import Cache
from resource_reader import Resource
result={}
paths=[(n,Path('../../maps')/(n+'.map'),False) for n in ('zanzibar','riverworld','docks','deadlock')]+[('forge_source',Path(r'D:\SteamLibrary\steamapps\workshop\content\976730\3597611181\maps\forge_halo.map'),True),('forge_candidate',Path('work/forge-world/sandbox-sky.map'),False)]
for name,path,mcc in paths:
 c=Cache(path,mcc); out=[]
 roots=[t['offset'] for t in c.tags.values() if t['group']=='Lbsp'] if mcc else [r for t in c.tags.values() if t['group']=='sLdT' for r in c.block(t['offset']+4,436)]
 for bi,root in enumerate(roots):
  r=Resource(c,c.u(root+0x1ac),{'maps\\shared.map':Path('../../maps/shared.map')});vb=r.buffers('vertex');ib=r.buffers('index')
  def raw(field,size):
   p=r.fix[field];a=p&0x1fffffff;return r.raw[(p>>29)-2][a:a+size]
  for mi,mesh in enumerate(c.block(root+0x134,76)):
   parts=[p for p in c.block(mesh,16) if c.data[p+13]&8]
   if not parts:continue
   slots=c.unpack('8h',mesh+24);starts=[c.unpack('h',v)[0] for v in c.block(mesh+64,2)]
   descriptors=[r.unpack('IHH',vb[v]) for v in slots[6:8]]
   vertex=vb[slots[0]];count,fmt,stride=r.unpack('IHH',vertex);positions=raw(vertex+20,count*stride)
   index=ib[c.unpack('h',mesh+40)[0]];indices=raw(index+16,r.unpack('I',index+4)[0])
   ps=[]
   for p in parts:
    start,length=c.unpack('HH',p+4);verts=struct.unpack(c.endian+str(length)+'H',indices[start*2:(start+length)*2]);zs=[struct.unpack_from(c.endian+'f',positions,v*stride+8)[0] for v in verts]
    ps.append({'start':start,'count':length,'z':[min(zs),max(zs)]})
   out.append({'bsp':bi,'mesh':mi,'water_starts':starts,'buffers':descriptors,'parts':ps})
 result[name]=out;c.close()
Path('work/forge-world/water-geometry-audit.json').write_text(json.dumps(result,indent=2))
for n,v in result.items():print(n,json.dumps(v)[:5500])
