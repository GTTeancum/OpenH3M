"""Compare actual H4/H3 model bounds before treating name matches as reskins."""
import contextlib,io,json,runpy,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
research=ROOT/'work/h4-forge-research'
with contextlib.redirect_stdout(io.StringIO()):
 g=runpy.run_path(str(research/'inspect_anchors.py'))
models={m['name']:m for m in json.loads((research/'ravine-magnets.json').read_text())['data']}
entries=json.loads((research/'isolated/marker-bindings.json').read_text())
def bounds(rows,unpack):
 values=[unpack(row+4) for row in rows]
 if not values:raise ValueError('Missing model compression bounds')
 return [min(v[i] for v in values) if i%2==0 else max(v[i] for v in values) for i in range(6)]
report=[]
for name in sorted({e['map'] for e in entries}):
 c=Cache(next((ROOT/'work/dlc/installed-current').rglob(name)))
 try:
  for e in entries:
   if e['map']!=name:continue
   obj=c.tags[int(e['datum'],16)&65535]['offset'];hlmt=c.tags[c.u(obj+0x40)&65535]['offset'];model=c.tags[c.u(hlmt+12)&65535]['offset']
   h3=bounds(c.block(model+0x74,44),lambda a:c.unpack('6f',a))
   index=models[e['h4_source']]['tag_index']
   ptr=struct.unpack_from('>I',g['d'],g['off'](g['tp'])+index*8+4)[0]
   h4=bounds(g['block'](g['off'](ptr)+0x80,52),lambda a:struct.unpack_from('>6f',g['d'],a))
   report.append(dict(map=name,label=e['label'],h3_bounds=h3,h4_bounds=h4,
     maximum_bound_difference=max(abs(a-b) for a,b in zip(h3,h4)),
     limitation='Bounds flag dimensional differences; matching bounds do not prove shape equivalence.'))
 finally:c.close()
out=research/'isolated/binding-bounds.json';out.write_text(json.dumps(report,indent=2)+'\n')
for r in sorted(report,key=lambda r:r['maximum_bound_difference'],reverse=True):
 if r['map']=='forge_gulch.map':print(r['label'],round(r['maximum_bound_difference'],4))
