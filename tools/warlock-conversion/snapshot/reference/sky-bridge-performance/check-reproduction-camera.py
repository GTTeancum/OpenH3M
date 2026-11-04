"""Compare emitted candidate-draw camera constants with the human recording."""
import argparse
import array
import collections
import json
from pathlib import Path
import struct

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('trace_dir',type=Path)
parser.add_argument('--billboard',action='store_true')
parser.add_argument('--models',action='store_true',help='Compare skinned albedo and lit model passes')
args=parser.parse_args();root=args.trace_dir
if args.models and args.billboard:parser.error('Choose one geometry family')
reference=Path(__file__).parent
root.resolve().relative_to(reference.resolve().parents[4])
pose=json.loads((reference/'candidate32-flicker-reproduction-view.json').read_text())
expected={bytes.fromhex(value)[:128] for value in pose['recorded_vertex_constants_0_18']}
if len(expected)!=1:raise ValueError('Human recording had multiple camera matrices')
expected=expected.pop();expected_floats=struct.unpack('<32f',expected)
registers=array.array('I',[0])*0x5003
passes={8562590739555380577:'albedo',14617156369365479079:'static',14007674117786981017:'dynamic'}
if args.billboard:
    passes={3413622546942440597:'banner',10494309294728871449:'text',8658708157452486949:'scanline'}
variants=collections.Counter();frames=set();counts=collections.Counter();draws=0
with (root/'draws.bin').open('rb') as stream:
    while header:=stream.read(8):
        kind,size=struct.unpack('<II',header);data=stream.read(size)
        if len(data)!=size:raise ValueError('Truncated draw packet')
        if kind==1:draw=struct.unpack('<11Q',data)
        elif kind==2:
            for index,value in struct.iter_unpack('<II',data):registers[index]=value
        elif kind==5 and ((args.models and draw[3] in (12627602885350085323,15518101065676308936)) or (not args.models and draw[4] in passes)):
            sequence,frame=struct.unpack('<QQ',data)
            if (sequence,frame)!=(draw[0],draw[1]):raise ValueError('Mismatched emitted draw')
            variants[registers[0x4000:0x4020].tobytes()]+=1
            label=('skinned_albedo' if draw[3]==12627602885350085323 else 'skinned_lit') if args.models else passes[draw[4]]
            frames.add(frame);counts[label]+=1;draws+=1
if not draws:raise ValueError('No emitted candidate material draws')
results=[]
for raw,count in variants.items():
    values=struct.unpack('<32f',raw)
    results.append({'draws':count,'exactly_equal':raw==expected,
                    'max_absolute_constant_delta':max(abs(a-b) for a,b in zip(values,expected_floats)),
                    'camera_position':values[28:31],'constants_0_7':raw.hex()})
report={'draws':draws,'frame_count':len(frames),'passes':dict(counts),'variants':results,
        'all_candidate_cameras_exact':all(r['exactly_equal'] for r in results),
        'limitation':'Matches camera/projection constants only. Vehicle pose, attachment, pixels, temporal behavior and performance require separate evidence.',
        'credit':pose['credit']}
(root/'camera-reproduction-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('variants','credit','limitation')}))
print('Maximum camera constant delta:',max(r['max_absolute_constant_delta'] for r in results))
