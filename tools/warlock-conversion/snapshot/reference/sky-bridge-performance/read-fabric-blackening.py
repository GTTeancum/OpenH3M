"""Correlate witnessed fabric black writes, guest blend state and final colors.

Target is candidate32 model 10177, mesh 0, part 1, at (711,197). The exact
geometry attribution is produced separately by trace-model-draws.py. Frame
identities are joined only within one run, never across human/private traces.
"""
import argparse
import array
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

REF = Path(__file__).resolve().parent
REPO = REF.parents[4]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, REF/file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def analyze(run):
    run = run.resolve()
    run.relative_to(REPO/'work/sky-bridge')
    model = module('model', 'trace-model-draws.py')
    stage = module('stage', 'read-stage-probe.py')
    pixel = module('pixel', 'read-pixel-probe.py')
    calls = json.loads((run/'model-draw-calls.json').read_text())['calls']
    identity = dict(owner=10177,mesh=0,part=1)
    selected = {c['sequence']:c for c in calls if c['candidates']==[identity]}
    assert selected, 'No byte-attributed target model calls'
    registers = array.array('I',[0])*0x5003
    states = {}
    for kind,raw in model.packets(run/'draws.bin'):
        if kind == 1:
            seq,frame,ns,vs,ps,*_ = struct.unpack('<11Q',raw)
        elif kind == 2:
            for i,v in struct.iter_unpack('<II',raw):
                registers[i] = v
        elif kind == 5 and seq in selected:
            assert struct.unpack('<QQ',raw)==(seq,frame)
            blend = registers[0x2201]
            states[seq] = dict(sequence=seq,frame=frame,elapsed_seconds=ns/1e9,vs=vs,ps=ps,
                blend_control0=hex(blend),color_control=hex(registers[0x2202]),
                color_info=hex(registers[0x2001]),color_mask=hex(registers[0x2104]),
                blend=dict(src=blend&31,op=(blend>>5)&7,dst=(blend>>8)&31,
                    alpha_src=(blend>>16)&31,alpha_op=(blend>>21)&7,alpha_dst=(blend>>24)&31),
                samples={})
    with (run/'stages.csv').open(newline='') as stream:
        for row in csv.DictReader(stream):
            if row['event']!='sample' or (int(row['x']),int(row['y']))!=(711,197):
                continue
            seq = int(row['sequence'])
            if seq not in states:
                continue
            state=states[seq]
            assert (state['frame'],state['ps'])==(int(row['frame']),int(row['shader']))
            phase=int(row['phase'])
            assert phase not in state['samples']
            state['samples'][phase] = dict(rgba=stage.rgba(row),
                target=[int(row[k]) for k in ('resource','format','resource_format','width','height','bytes')])
    final = {}
    for name in ('pixels.csv','presented.csv'):
        values={}
        with (run/name).open(newline='') as stream:
            for row in csv.DictReader(stream):
                if row['event']=='sample' and (int(row['x']),int(row['y']))==(711,197):
                    assert (int(row['width']),int(row['height']))==(1152,640)
                    frame=int(row['frame'])
                    assert frame not in values
                    values[frame]=pixel.channels(int(row['packed_pixel']),int(row['format']),int(row['swizzle']))
        final[name]=values
    black=[]
    for state in states.values():
        assert set(state['samples'])=={0,1}
        a,b=state['samples'][0],state['samples'][1]
        assert a['target']==b['target']
        if max(a['rgba'][:3])>.03 and max(b['rgba'][:3])<=.01:
            black.append(state)
    black.sort(key=lambda s:s['frame'])
    frames=sorted({s['frame'] for s in black})
    intervals=[]
    for frame in frames:
        if not intervals or intervals[-1][-1]+1!=frame:
            intervals.append([])
        intervals[-1].append(frame)
    windows=[]
    for interval in intervals:
        first,last=interval[0],interval[-1]
        window=dict(first_frame=first,last_frame=last,frames=len(interval),stages={})
        for name,values in final.items():
            available=all(f in values for f in [first-1,*interval,last+1])
            item=dict(exact_point_available=available)
            if available:
                baseline=min(max(values[first-1][:3]),max(values[last+1][:3]))
                item.update(before=values[first-1],after=values[last+1],baseline_max_rgb=baseline,
                    during=[dict(frame=f,rgba=values[f],ratio_to_boundary= max(values[f][:3])/baseline)
                            for f in interval])
            window['stages'][name]=item
        windows.append(window)
    report=dict(trace=str(run.relative_to(REPO)),identity=identity,point=[711,197],
        selected_calls=len(selected),black_writes=len(black),frames=frames,windows=windows,
        black_draw_states=black,
        inputs_sha256={n:hashlib.sha256((run/n).read_bytes()).hexdigest() for n in
            ('draws.bin','stages.csv','model-draw-calls.json','pixels.csv','presented.csv')},
        conclusions=[
            'Paired color-0 samples directly identify draws which replace a previously lit fabric pixel with near-zero RGB.',
            'RB_BLENDCONTROL0 decoding uses the active SDK register layout: src/dst 1/0 is replacement, 1/1 is additive.',
            'Final samples use the actual DXGI format and component mapping, not a fixed 8-bit interpretation.',
            'The original human bad frame was not located numerically; these are private replay events.',
            'This decoder measures sampled overwrites only; causal state tracing and candidate comparisons are reported separately.'],
        limitations=['Native guest-output samples after host gamma/FXAA precede presenter scaling and desktop composition.',
            'A 3-4-frame dark window is not an isolated one-frame near-black pulse; the old pulse-only metric can miss it.',
            'Only the saved camera is exact; the replay is not a full simulation savestate.',
            'No rendering fix or visual acceptance is established by this diagnostic.'],
        credit=json.loads((REF/'sky-pixel-probe-build.json').read_text())['credit'])
    (run/'fabric-blackening-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(selected_calls=len(selected),black_writes=len(black),windows=windows)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    analyze(parser.parse_args().run)
