"""Extract original H4 collision polyhedra for comparison with Reach counterparts."""
import contextlib,io,json,runpy,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];research=ROOT/'work/h4-forge-research'
with contextlib.redirect_stdout(io.StringIO()):g=runpy.run_path(str(research/'inspect_anchors.py'))
d=g['d'];off=g['off'];block=g['block'];u=lambda a:struct.unpack_from('>I',d,a)[0]
models={m['name']:m for m in json.loads((research/'ravine-magnets.json').read_text())['data']}
entries=json.loads((research/'isolated/marker-bindings.json').read_text())
tags={}
for i in range(g['nt']):
 group,salt,ptr=struct.unpack_from('>HHI',d,off(g['tp'])+i*8)
 if group!=65535 and ptr not in (0,0xffffffff):tags[i]=(g['groups'][group],off(ptr))
models_to_physics={}
for index,(group,at) in tags.items():
 if group=='hlmt' and u(at+12)!=0xffffffff and u(at+0x3c)!=0xffffffff:
  models_to_physics[u(at+12)&65535]=u(at+0x3c)&65535
report=[]
for name in sorted({e['h4_source'] for e in entries}):
 index=models[name]['tag_index'];phindex=models_to_physics[index];group,ph=tags[phindex]
 if group!='phmo':raise ValueError('Physics reference group mismatch')
 four=block(ph+0xbc,48);planes=block(ph+0xc8,16);shapes=[];vi=pi=0
 for r in block(ph+0xb0,144):
  nf,nv,np=u(r+0x64),u(r+0x6c),u(r+0x78)
  if not 0<nv<=nf*4 or vi+nf>len(four) or pi+np>len(planes):raise ValueError('Invalid H4 polyhedron layout')
  verts=[]
  for f in four[vi:vi+nf]:
   coords=struct.unpack_from('>12f',d,f);verts.extend([[coords[i],coords[4+i],coords[8+i]] for i in range(4)])
  shapes.append(dict(vertices=verts[:nv],planes=[struct.unpack_from('>4f',d,p) for p in planes[pi:pi+np]],radius=struct.unpack_from('>f',d,r+0x30)[0]))
  vi+=nf;pi+=np
 if vi!=len(four) or pi!=len(planes):raise ValueError('Unaccounted H4 polyhedron data')
 report.append(dict(name=name,model_index=index,physics_index=phindex,shapes=shapes))
(research/'isolated/h4-collision.json').write_text(json.dumps(report,indent=2)+'\n')
print('Extracted original collision for',len(report),'H4 models')
