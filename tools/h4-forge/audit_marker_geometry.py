"""Read current H3 collision geometry and H4 anchor fit without changing assets."""
import json,sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
research=ROOT/'work/h4-forge-research'
models={m['name']:m for m in json.loads((research/'ravine-magnets.json').read_text())['data']}
entries=json.loads((research/'isolated/marker-bindings.json').read_text())
report=[]
for name in sorted({e['map'] for e in entries}):
 path=next((ROOT/'work/dlc/installed-current').rglob(name));c=Cache(path)
 try:
  for e in entries:
   if e['map']!=name:continue
   obj=c.tags[int(e['datum'],16)&65535]['offset']
   model=c.tags[c.u(obj+0x40)&65535]['offset']
   physics=c.u(model+0x3c)
   if physics==0xffffffff:continue
   ph=c.tags[physics&65535]['offset']
   bodies=[dict(node=c.unpack('h',r)[0],motion_type=c.unpack('H',r+0x1a)[0],flags=c.unpack('H',r+0x18)[0]) for r in c.block(ph+0x58,176)]
   four=list(c.block(ph+0xb8,48));planes=list(c.block(ph+0xc4,16))
   shapes=[];vi=pi=0
   for r in c.block(ph+0xac,128):
    nv=c.u(r+0x6c);nf=c.u(r+0x64);np=c.u(r+0x74)
    verts=[]
    for f in four[vi:vi+nf]:
     coords=c.unpack('12f',f)
     verts.extend([[coords[i],coords[4+i],coords[8+i]] for i in range(4)])
    shapes.append(dict(vertices=verts[:nv],planes=[c.unpack('4f',p) for p in planes[pi:pi+np]],radius=c.unpack('f',r+0x30)[0]))
    vi+=nf;pi+=np
   anchors=[p for g in models[e['h4_source']]['markers'] if g['group']=='sandbox_magnet' for p in g['points']]
   report.append(dict(map=name,label=e['label'],datum=e['datum'],physics=hex(physics),bodies=bodies,shapes=shapes,anchors=anchors,
     limitation='Raw local collision shapes; transformed rigid bodies require additional transform resolution.'))
 finally:c.close()
out=research/'isolated/marker-geometry.json';out.write_text(json.dumps(report,indent=2)+'\n')
print('Audited',len(report),'bindings:',out)
for e in report:
 if e['map']=='forge_gulch.map' and e['label']=='Bank, 1x1':print(json.dumps(e,indent=2))
