import array,collections,csv,importlib.util,json,struct
from pathlib import Path
repo=Path.cwd();ref=repo/'tools/warlock-conversion/snapshot/reference/sky-bridge-performance'
spec=importlib.util.spec_from_file_location('model',ref/'trace-model-draws.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
spec=importlib.util.spec_from_file_location('stage',ref/'read-stage-probe.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
result=[]
for number in (36,37):
 run=repo/f'work/sky-bridge/reproduction-{number}';calls=json.loads((run/'model-draw-calls.json').read_text())['calls']
 target={c['sequence']:c for c in calls if c['candidates']==[dict(owner=10177,mesh=0,part=1)]}
 regs=array.array('I',[0])*0x5003;states={};groups={}
 for k,raw in m.packets(run/'draws.bin'):
  if k==1:seq,frame,_,vs,ps,*_=struct.unpack('<11Q',raw)
  elif k==2:
   for i,v in struct.iter_unpack('<II',raw):regs[i]=v
  elif k==5 and seq in target:
   key=ps,vs,regs[0x2201],regs[0x2202],regs[0x210e],regs[0x47f3]
   item=groups.setdefault(key,dict(ps=ps,vs=vs,blend=hex(regs[0x2201]),color_control=hex(regs[0x2202]),alpha_ref=hex(regs[0x210e]),c252w=hex(regs[0x47f3]),draws=0,paired_points=0,black_overwrites=0,rgb_increases=0,rgb_decreases=0,unchanged=0,frames=[],point711=[]))
   item['draws']+=1;item['frames'].append(frame);states[seq]=item
 before={}
 with (run/'stages.csv').open() as stream:
  for row in csv.DictReader(stream):
   if row['event']!='sample' or int(row['sequence']) not in states:continue
   seq=int(row['sequence']);point=int(row['x']),int(row['y']);key=seq,point;color=s.rgba(row);group=states[seq]
   if int(row['phase'])==0:before[key]=color;continue
   a=before.pop(key);b=color;group['paired_points']+=1
   group['black_overwrites']+=max(a[:3])>.03 and max(b[:3])<=.01
   group['rgb_increases']+=any(y>x+1e-6 for x,y in zip(a[:3],b[:3]));group['rgb_decreases']+=any(y<x-1e-6 for x,y in zip(a[:3],b[:3]));group['unchanged']+=a==b
   if point==(711,197) and group['vs']==1802336714319958646:group['point711'].append(dict(frame=int(row['frame']),before=a,after=b))
 assert not before
 result.append(dict(run=number,groups=list(groups.values()),blackening=json.loads((run/'fabric-blackening-analysis.json').read_text())['black_writes']))
out=repo/'work/sky-bridge/fabric-cutout-build/comparison.json';out.write_text(json.dumps(result,indent=2)+'\n')
for r in result:
 print('run',r['run'],'black writes',r['blackening'])
 for g in r['groups']:
  print({k:v for k,v in g.items() if k not in ('frames','point711')})
