"""Join all-draw point measurements to actual submitted draws and final output."""
import argparse
import array
import collections
import csv
import importlib.util
import json
import math
from pathlib import Path
import struct

ref=Path(__file__).resolve().parent
def load(name):
    spec=importlib.util.spec_from_file_location(name,ref/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
stage,pixel=load('read-stage-probe'),load('read-pixel-probe')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('run',type=Path)
args=parser.parse_args();args.run.resolve().relative_to(ref.parents[4]/'work/sky-bridge')
root=args.run
records={};events=collections.Counter();non_samples=[]
with (root/'stages.csv').open() as stream:
    for row in csv.DictReader(stream):
        events[row['event']]+=1
        if row['event']!='sample':
            non_samples.append({k:int(v) if k!='event' else v for k,v in row.items()});continue
        row={k:int(v) if k!='event' else v for k,v in row.items()}
        sequence=row['sequence']
        if sequence in records or row['phase']!=1 or (row['x'],row['y'])!=(714,210):
            raise ValueError('Unexpected all-draw point record')
        row['rgba']=stage.rgba(row)
        if not all(math.isfinite(v) for v in row['rgba']):raise ValueError('Nonfinite point sample')
        records[sequence]=row

regs=array.array('I',[0])*0x5003
draws={};emitted=set();stop=[];ranges=[];frames=collections.Counter()
with (root/'draws.bin').open('rb') as stream:
    while header:=stream.read(8):
        kind,size=struct.unpack('<II',header);data=stream.read(size)
        if len(data)!=size:raise ValueError('Truncated draw packet')
        if kind==1:
            draw=struct.unpack('<11Q',data);sequence=draw[0]
            draws[sequence]={'frame':draw[1],'ns':draw[2],'vs':draw[3],'ps':draw[4],
                'primitive':draw[5],'index_count':draw[6],'index_address':draw[7]}
        elif kind==2:
            for index,value in struct.iter_unpack('<II',data):regs[index]=value
        elif kind==5:
            sequence,frame=struct.unpack('<QQ',data)
            if sequence not in draws or draws[sequence]['frame']!=frame or sequence in emitted:
                raise ValueError('Mismatched emitted draw')
            emitted.add(sequence);frames[frame]+=1
            if sequence in records:
                sample=records[sequence];d=draws[sequence]
                if sample['frame']!=frame or sample['shader']!=d['ps'] or sample['index_count']!=d['index_count']:
                    raise ValueError('Point does not match emitted draw')
                sample['draw']=d
                sample['viewport_registers']={hex(i):hex(regs[i]) for i in [0x2080,0x2081,0x2082,0x210f,0x2110,0x2111,0x2112,0x2206]}
        elif kind==8:ranges.append(list(struct.unpack('<5I',data)))
        elif kind==9:stop.append(struct.unpack('<Q',data)[0])
if any('draw' not in sample for sample in records.values()):raise ValueError('Point lacks emitted draw')

def final_values(name):
    result={}
    for row in csv.DictReader((root/name).open()):
        if row['event']=='sample' and (int(row['x']),int(row['y']))==(714,210):
            result[int(row['frame'])]=pixel.channels(int(row['packed_pixel']),int(row['format']),int(row['swizzle']))
    return result
source,presented=final_values('pixels.csv'),final_values('presented.csv')
decreases=[]
for frame,value in sorted(presented.items()):
    if frame-1 not in presented or frame+1 not in presented:continue
    baseline=min(max(presented[frame-1][:3]),max(presented[frame+1][:3]));current=max(value[:3])
    if baseline-current>.05 and current<=baseline*.7:
        decreases.append({'frame':frame,'drop':baseline-current,'ratio':current/baseline,
            'source':{str(f):source.get(f) for f in range(frame-1,frame+2)},
            'presented':{str(f):presented[f] for f in range(frame-1,frame+2)}})

ordered=collections.defaultdict(list)
for sample in sorted(records.values(),key=lambda v:v['sequence']):ordered[sample['frame']].append(sample)
transitions={};shader_summary=collections.Counter()
for frame,samples in ordered.items():
    previous={};changes=[]
    for sample in samples:
        shader_summary[sample['shader']]+=1
        key=(sample['resource'],sample['format'])
        if key not in previous or sample['rgba']!=previous[key]['rgba']:
            changes.append({k:sample[k] for k in ['sequence','shader','resource','format','width','height','rgba','draw','viewport_registers']})
        previous[key]=sample
    transitions[frame]=changes
for event in decreases:
    event['point_transitions']={str(f):transitions.get(f,[]) for f in range(event['frame']-1,event['frame']+2)}
report={'events':dict(events),'non_sample_events':non_samples,'recorded_draws':len(draws),'emitted_draws':len(emitted),
    'emitted_frame_count':len(frames),'point_frame_count':len(ordered),'point_samples':len(records),
    'draw_trace_stop_reasons':stop,'declared_register_ranges':ranges,
    'source_frames':len(source),'presented_frames':len(presented),
    'point_shader_samples':dict(shader_summary),'relative_decreases':decreases,
    'limitations':['Samples are after draws. A difference since the previous observation can also include intervening clears or resolves.',
        'Only color target 0 and supported single-sample formats covering the fixed coordinate are read. Unsupported targets are logged.',
        'A resource may back several logical targets. Viewport and resource identity must be examined before interpreting spatial correspondence.',
        'The probe changes command timing; event correspondence to the human black flash is not yet established.'],
    'credit':json.loads((ref/'sky-pixel-probe-build.json').read_text())['credit']}
(root/'late-pass-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['non_sample_events','relative_decreases','limitations','credit','point_shader_samples']}))
print('Decreases:',[(e['frame'],round(e['drop'],4),len(e['point_transitions'][str(e['frame'])])) for e in decreases])
