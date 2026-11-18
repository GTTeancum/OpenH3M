"""Read-only retail Halo 3 scenario attachment audit. No emulator, no guest code, no map mutation.

Reimplemented after the source conversion workspace disappeared. This is independent corroboration,
not a recovered copy of the lost original conversion program or proof of any scene in game.
"""
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import json,mmap,struct,argparse
class Native:
 def __init__(self,p):
  self.f=Path(p).open('rb'); self.d=mmap.mmap(self.f.fileno(),0,access=mmap.ACCESS_READ)
  if self.d[:4]!=b'head' or self.d[0x2ffc:0x3000]!=b'foot' or self.u(4)!=11 or self.u(8)!=len(self.d):raise ValueError('not a complete H3 retail 360 cache')
  self.base=self.u(0x2e8);self.start=(self.u(0x48c)+self.u(0x474))&0xffffffff;self.end=self.start+self.u(0x490)
  if self.start>self.end or self.end>len(self.d):raise ValueError('metadata span')
  ix=self.ptr(self.u(0x10),16);n,g,nt,t=struct.unpack_from('>IIII',self.d,ix);g=self.ptr(g,16*n);t=self.ptr(t,8*nt);self.tags={};self.names={}
  self.nb=(self.u(0x2b8)+self.u(0x46c))&0xffffffff;self.nl=self.u(0x2bc);self.nx=(self.u(0x2c0)+self.u(0x46c))&0xffffffff;self.nc=self.u(0x2b4)
  if self.nb+self.nl>len(self.d) or self.nx+self.nc*4>len(self.d):raise ValueError('debug span')
  for i in range(nt):
   k,s,a=struct.unpack_from('>HHI',self.d,t+i*8)
   if k==65535 or a in (0,0xffffffff):continue
   if k>=n:raise ValueError('group index')
   self.tags[(s<<16)|i]=(self.d[g+16*k:g+16*k+4],self.ptr(a,1));
 def u(self,at):return struct.unpack_from('>I',self.d,at)[0]
 def u16(self,at):return struct.unpack_from('>H',self.d,at)[0]
 def ptr(self,a,s):
  off=a-self.base+self.start
  if not self.start<=off<=self.end-s:raise ValueError('block address outside metadata')
  return off
 def name(self,datum):
  if datum in self.names:return self.names[datum]
  i=datum&65535
  if i>=self.nc: return None
  rel=self.u(self.nx+4*i)
  if rel==0xffffffff:return None
  if rel>=self.nl: raise ValueError('name offset')
  end=self.d.find(b'\0',self.nb+rel,self.nb+self.nl)
  if end<0:raise ValueError('name terminator')
  self.names[datum]=self.d[self.nb+rel:end].decode('utf-8');return self.names[datum]
 def block(self,a,s):
  n,p=struct.unpack_from('>II',self.d,a)
  if not n:return []
  at=self.ptr(p,n*s);return range(at,at+n*s,s)
 def close(self):self.d.close();self.f.close()
 def scenery(self):
  roots=[a for g,a in self.tags.values() if g==b'scnr']
  if len(roots)!=1:raise ValueError('expected one scenario')
  sc=roots[0]; palette=[]
  for pos in self.block(sc+0xc8,0x30):
   datum=self.u(pos+0xc)
   if datum==0xffffffff:palette.append(None);continue
   target=self.tags.get(datum)
   if target is None or target[0]!=b'scen':raise ValueError('scenery palette type/salt')
   palette.append(self.name(datum))
  for i,row in enumerate(self.block(sc+0xbc,0xb4)):
   pi=struct.unpack_from('>h',self.d,row)[0]
   if pi==-1:continue
   if not 0<=pi<len(palette):raise ValueError('placement palette index')
   yield i,row,palette[pi],self.u16(row+0x32),self.d[row+0x40],self.u16(row+0x50)

def report(paths):
 maps={};counts=Counter();roles=Counter();markers=Counter();eligible=Counter();excluded=[]
 for p in paths:
  raw=Native(p); tab=Counter();paths_seen=Counter()
  try:
   for index,off,name,manual,policy,compiled in raw.scenery():
    if name is None:continue
    tail=name.rsplit('\\',1)[-1]; key=f'{tail}:manual{manual:#x}/policy{policy}/compiled{compiled:#x}'
    if 'spawn' not in name:continue
    paths_seen[name]+=1;tab[key]+=1;roles[tail]+=1;counts[key]+=1
    if name in {r'objects\multi\spawning\respawn_point',r'objects\multi\spawning\respawn_point_invisible',r'objects\multi\slayer\slayer_initial_spawn_point'}:
     game_flags=raw.u16(off+0x84)
     if game_flags==0 or (game_flags & 2):eligible[key]+=1
     else: excluded.append({'map':Path(p).name,'scenery_index':index,'palette_name':name,'mode_mask':hex(game_flags)})
   for k,v in paths_seen.items():markers[k]+=v
   maps[Path(p).name]={'spawn_scenery_names':dict(sorted(paths_seen.items())),'attachment_rows':dict(sorted(tab.items()))}
  finally:raw.close()
 return {'status':'fresh read-only stock-H3 scan, not Reach runtime','layout':{'scenery_root':'0xbc','scenery_stride':'0xb4','scenery_palette_root':'0xc8','palette_stride':'0x30','native_manual_mask':'0x32 u16','native_bsp_policy':'0x40 u8','native_compiled_mask':'0x50 u16'},'eligible_slayer_attachment_rows':dict(sorted(eligible.items())),'mode_excluded_markers':excluded,'maps':maps,'all_spawn_scenery_names':dict(sorted(markers.items())),'aggregate_attachment_rows':dict(sorted(counts.items()))}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('stock_maps_root',type=Path);ap.add_argument('-o','--out',type=Path,required=True);a=ap.parse_args();maps=[p for p in sorted(a.stock_maps_root.glob('*.map')) if p.stem not in ('mainmenu','shared','campaign')];assert maps; q=report(maps);a.out.write_text(json.dumps(q,indent=2,sort_keys=True)+'\n');print(len(maps),'native maps;',len(q['all_spawn_scenery_names']),'spawn marker named palette assets; rows:',sum(q['aggregate_attachment_rows'].values()));print(json.dumps(q['all_spawn_scenery_names'],indent=1))
