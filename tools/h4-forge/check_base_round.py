"""Reproduce Base, Round's flat-face defect through the original H4 bridge."""
import argparse
import json
import math
from pathlib import Path
import re
import struct
import subprocess
from anchor_frames import adapt

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/h4-forge-research/isolated'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--native-run',type=Path,help='Also inspect the released native Base Round fixture snapshot')
args=parser.parse_args()
models=json.loads((OUT.parent/'ravine-magnets.json').read_text())['data']
model=next(m for m in models if m['name'].split('\\')[-1]=='fw_unsc_c_base_round')
points=[p for g in model['markers'] if g['group']=='sandbox_magnet' for p in g['points']]
frame=json.loads((Path(__file__).parent/'anchor_frames.json').read_text())['fw_unsc_c_base_round']

def basis(q):
 x,y,z,w=q
 return [1-2*(y*y+z*z),2*(x*y+z*w),2*(x*z-y*w),
         2*(x*y-z*w),1-2*(x*x+z*z),2*(y*z+x*w),
         2*(x*z+y*w),2*(y*z-x*w),1-2*(x*x+y*y)]

def marker(point,position,opposed):
 m=bytearray(112)
 local=basis(point['rotation']);p=point['position']
 signs=(-1,-1,1) if opposed else (1,1,1)
 world=[v*signs[i%3] for i,v in enumerate(local)]
 for off in (4,0x38):struct.pack_into('>f',m,off,1)
 struct.pack_into('>9f',m,8,*local);struct.pack_into('>9f',m,0x3c,*world)
 struct.pack_into('>3f',m,0x2c,*p)
 struct.pack_into('>3f',m,0x60,*(p[i]*signs[i]+position[i] for i in range(3)))
 return m

results={}
for name,anchors in [('raw',points),('adapted',[adapt(p,frame) for p in points])]:
 # Hemorrhage uses opposing halves with coincident origins. Start .1 apart
 # so a successful result must actually close the gap, not preserve the input.
 data=bytearray(struct.pack('<4sII3f9f',b'AFS1',2,2,0,0,0,1,0,0,0,1,0,0,0,1))
 for datum,pos,opposed in [(123,(0,0,0),False),(456,(0,.1,0),True)]:
  data+=struct.pack('<I3ffI',datum,*pos,6.295636177,len(anchors))
  for p in anchors:data+=marker(p,pos,opposed)
 path=OUT/f'base-round-{name}.afs';path.write_bytes(data)
 run=subprocess.run([str(OUT/'test_bridge.exe'),str(path)],cwd=ROOT,text=True,capture_output=True,check=True)
 match=re.search(r'snap=(\d+) target=(\d+) position=([^\n]+)',run.stdout)
 if not match:raise RuntimeError(run.stdout+run.stderr)
 rotation=re.search(r'rotation=([^\n]+)',run.stdout)
 if not rotation:raise RuntimeError('Rebuild test_bridge.exe with rotation reporting')
 results[name]=dict(snapped=bool(int(match[1])),target=int(match[2]),position=[float(x) for x in match[3].split(',')],rotation=[float(x) for x in rotation[1].split(',')])
 print(name,run.stdout.strip())
assert not results['raw']['snapped'] or math.dist(results['raw']['position'],(0,.1,0))>.01,results
assert results['adapted']['snapped'] and results['adapted']['target']==456,results
assert math.dist(results['adapted']['position'],(0,.1,0))<.0003,results
assert max(abs(a-b) for a,b in zip(basis(results['adapted']['rotation']),(1,0,0,0,1,0,0,0,1)))<1e-5,results
(OUT/'base-round-bridge-result.json').write_text(json.dumps(results,indent=2)+'\n')
print('PASS raw anchors miss the seam; adapted anchors mate at the opposed target origin')

if args.native_run:
 run=args.native_run.resolve(strict=True);run.relative_to(ROOT)
 log=(run/'trace-runtime.log').read_text(errors='replace')
 assert 'Advanced Forge original H4 snap:' in log
 assert 'Advanced Forge disabled:' not in log
 snapped_held=re.search(r'Advanced Forge original H4 snap: held ([0-9A-F]+)',log)[1]
 initial=re.findall(r'Advanced Forge initial physics: ([0-9A-F]+) mode ([0-9A-F]+) flags ([0-9A-F]+)',log)
 defaults=[(datum,int(flags,16)) for datum,mode,flags in initial if datum==snapped_held and int(mode,16)==0x40]
 assert len(defaults)==1,initial
 held,held_flags=defaults[0]
 assert held_flags&0x1000c0==0x1000c0,defaults
 restored=re.findall(rf'Advanced Forge physics restored: {held} flags ([0-9A-F]+) original ([0-9A-F]+)',log)
 assert len(restored)==1 and not (int(restored[0][0],16)^int(restored[0][1],16))&0x1000c0,restored
 data=(run/'native-variant.bin').read_bytes()
 assert len(data)==0xe090 and struct.unpack_from('>H',data,0xf8)[0]==12
 objects=[]
 for slot in range(640):
  at=0x130+slot*0x54
  flags=struct.unpack_from('>H',data,at)[0]
  if not flags&1 or flags&32:continue
  quota=struct.unpack_from('>i',data,at+12)[0]
  if quota<0:continue
  assert quota<256
  if struct.unpack_from('>I',data,0xd34c+quota*12)[0]!=0x90002952:continue
  values=struct.unpack_from('>9f',data,at+16)
  objects.append(dict(slot=slot,position=values[:3],forward=values[3:6],up=values[6:9]))
 assert len(objects)==2,objects
 a,b=objects
 separation=math.dist(a['position'],b['position'])
 assert separation<.0003,objects
 assert math.dist(a['forward'],[-v for v in b['forward']])<1e-5,objects
 assert math.dist(a['up'],(0,0,1))<1e-5 and math.dist(b['up'],(0,0,1))<1e-5,objects
 expected=json.loads((OUT/'snap-fixture-base-round.json').read_text())['layout']['objects'][0]['position']
 assert max(math.dist(o['position'],expected) for o in objects)<.0003,objects
 result=dict(objects=objects,origin_separation=separation,format='ordinary H3 version 12',
             default_fixed_flags=hex(held_flags),restored_motion_flags=True,
             limitation='Numeric fixture result; inspect the native captures separately for visual correctness.')
 (run/'base-round-result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(f'PASS native released disc: opposed halves, origin separation {separation:.9f}, ordinary H3 records')
