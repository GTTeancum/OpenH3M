"""Decode the bounded GPU particle-state records consumed by the arc vertex shader."""
import argparse
import array
from collections import Counter
import csv
import importlib.util
import json
import math
from pathlib import Path
import struct

REF=Path(__file__).resolve().parent
REPO=REF.parents[4]
spec=importlib.util.spec_from_file_location('arc',REF/'read-arc-pass-probe.py')
arc=importlib.util.module_from_spec(spec);spec.loader.exec_module(arc)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('run',type=Path)
args=parser.parse_args();run=args.run.resolve();run.relative_to(REPO/'work/sky-bridge')
registers=array.array('I',[0])*0x5003
calls={}
for kind,data in arc.packets(run/'draws.bin'):
    if kind==1:draw=struct.unpack('<11Q',data)
    elif kind==2:
        for i,v in struct.iter_unpack('<II',data):registers[i]=v
    elif kind==5:
        const=lambda i:struct.unpack('<4f',registers[0x4000+i*4:0x4004+i*4].tobytes())
        assert draw[3]==5227998057160693720 and draw[4]==arc.PS
        assert registers[0x48bd]&3==2 # vertex buffer endian is 8-in-32
        calls[draw[0]]={'frame':draw[1],'count':draw[6],'first_vertex':registers[0x2102]&0xffffff,
            'projection':[const(i) for i in range(4)],'local':[const(i) for i in range(33,37)],
            'corners':const(69),'billboard':const(77)[0],
            'viewport':struct.unpack('<4f',registers[0x210f:0x2113].tobytes())}
coverage_rows=list(csv.DictReader((run/'coverage.csv').open()))
coverage_events=Counter(r['event'] for r in coverage_rows)
all_coverage={int(r['sequence']):int(r['samples']) for r in coverage_rows if r['event']=='sample'}
coverage={seq:value for seq,value in all_coverage.items() if seq in calls}
state_events=Counter();particles=[];bounds=[];rows=0
for row in csv.DictReader((run/'arc-states.csv').open()):
    state_events[row['event']]+=1
    if row['event']!='sample':continue
    sequence=int(row['sequence']);call=calls[sequence];raw=bytes.fromhex(row['data']);rows+=1
    assert int(row['frame'])==call['frame'] and len(raw)==int(row['bytes'])==int(row['count'])*80
    assert int(row['first'])*4==call['first_vertex'] and int(row['count'])*4==call['count']
    for i in range(int(row['count'])):
        data=raw[i*80:i*80+80]
        # Packed halves use the source struct order. The native VS's yxwz /
        # w__z fetch swizzles undo the pair order introduced by 8-in-32.
        position=struct.unpack_from('>4f',data)
        velocity=struct.unpack_from('>4e',data,16)
        rotation=struct.unpack_from('>4H',data,40)
        time=struct.unpack_from('>4e',data,48)
        color=list(data[68:72][::-1]);alive=math.isfinite(time[2]) and time[2]<1 and color[3]>0
        assert all(math.isfinite(x) for x in position+velocity+time)
        local=call['local']
        world=[sum(position[j]*local[j][axis] for j in range(3))+local[3][axis] for axis in range(3)]
        def project(p):
            clip=[sum(x*y for x,y in zip(p+[1],c)) for c in call['projection']]
            if clip[3]<=0:return None
            sx,ox,sy,oy=call['viewport']
            return [clip[0]/clip[3]*sx+ox,clip[1]/clip[3]*sy+oy]
        center=project(world);corners=[]
        if alive and call['billboard']==7:
            angle=(rotation[0]+rotation[1])/65535*2*math.pi;sn,cs=math.sin(angle),math.cos(angle)
            for u,v in ((0,0),(1,0),(1,1),(0,1)):
                x=(call['corners'][0]+u*call['corners'][2])*velocity[3]
                y=call['corners'][1]+v*call['corners'][3]
                a,b=(x*cs-y*sn)*position[3],(x*sn+y*cs)*position[3]
                p=project([world[axis]+a*local[0][axis]+b*local[1][axis] for axis in range(3)])
                if p:corners.append(p)
        record={'frame':call['frame'],'sequence':sequence,'index':int(row['first'])+i,
            'world':world,'size':position[3],'aspect':velocity[3],'age':time[2],'intensity':time[3],
            'rgba_bytes':color,'alive':alive,'center':center,'projected_corners':corners,
            'draw_depth_passing_samples':coverage.get(sequence)}
        particles.append(record)
        if corners:bounds.extend(corners)
live=[p for p in particles if p['alive']]
near=[p for p in live if p['center'] and abs(p['center'][0]-650)<60 and abs(p['center'][1]-180)<80]
report={'draws':len(calls),'state_rows':rows,'state_events':dict(state_events),
    'coverage_events':dict(coverage_events),'queries':len(coverage),
    'coverage_records_outside_flushed_draw_trace':len(all_coverage)-len(coverage),
    'nonzero_coverage_draws':sum(v>0 for v in coverage.values()),
    'depth_passing_samples':sum(coverage.values()),'particles':len(particles),'live_particles':len(live),
    'live_frames':len({p['frame'] for p in live}),'near_marked_live_particles':len(near),
    'world_min':[min(p['world'][axis] for p in live) for axis in range(3)] if live else None,
    'world_max':[max(p['world'][axis] for p in live) for axis in range(3)] if live else None,
    'near_marked_examples':near[:8],
    'limitations':['Projected corners follow the traced shader and authored local-horizontal billboard path; they are not GPU vertex-output captures.',
        'Occlusion query counts cover the whole draw and do not prove visible color or a particular object.',
        'Color bytes are the vertex-buffer fetch order (BGRA), with alpha last.'],
    'credit':json.loads((REF/'sky-pixel-probe-build.json').read_text())['credit']}
(run/'arc-particle-records.json').write_text(json.dumps(particles,separators=(',',':'))+'\n')
(run/'arc-state-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('near_marked_examples','limitations','credit')}))
