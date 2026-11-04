import collections,csv,json,sys,importlib.util
from pathlib import Path

ref=Path(__file__).resolve().parent
sys.path.insert(0,str(ref))
def load(name):
    spec=importlib.util.spec_from_file_location(name,ref/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
stage=load('read-stage-probe');pixel=load('read-pixel-probe')
rgba,PASSES,channels=stage.rgba,stage.PASSES,pixel.channels
run=Path(sys.argv[1]);run.resolve().relative_to(ref.parents[4])
point=(714,210)
def pixels(name):
    data={}
    for row in csv.DictReader((run/name).open()):
        if row['event']=='sample' and (int(row['x']),int(row['y']))==point:
            data[int(row['frame'])]=channels(int(row['packed_pixel']),int(row['format']),int(row['swizzle']))
    return data
source=pixels('pixels.csv');presented=pixels('presented.csv')
calls={}
for row in csv.DictReader((run/'stages.csv').open()):
    if row['event']!='sample' or (int(row['x']),int(row['y']))!=point:continue
    frame,sequence,phase,shader,count=(int(row[k]) for k in ['frame','sequence','phase','shader','index_count'])
    calls.setdefault((frame,sequence),{'frame':frame,'sequence':sequence,'pass':PASSES[shader],
        'index_count':count,'format':int(row['format']),'phases':{}})['phases'][phase]=rgba(row)
by_frame=collections.defaultdict(list);groups=collections.defaultdict(collections.Counter)
for call in sorted(calls.values(),key=lambda c:c['sequence']):
    if set(call['phases'])!={0,1}:raise ValueError('Incomplete primary-point draw pair')
    call['before']=call['phases'][0];call['after']=call['phases'][1];del call['phases']
    call['changed_rgb']=call['before'][:3]!=call['after'][:3]
    by_frame[call['frame']].append(call)
    groups[call['pass'],call['index_count']]['draws']+=1
    groups[call['pass'],call['index_count']]['changed_rgb']+=call['changed_rgb']
events=[]
for frame,value in sorted(presented.items()):
    if frame-1 not in presented or frame+1 not in presented:continue
    baseline=min(max(presented[frame-1][:3]),max(presented[frame+1][:3]));current=max(value[:3])
    if baseline-current<=.05 or current>baseline*.7:continue
    events.append({'frame':frame,'drop':baseline-current,'ratio':current/baseline,
        'presented':{str(f):presented[f] for f in range(frame-1,frame+2)},
        'source':{str(f):source.get(f) for f in range(frame-1,frame+2)},
        'candidate_draws':{str(f):by_frame.get(f,[]) for f in range(frame-1,frame+2)}})
report={'point':point,'source_frames':len(source),'presented_frames':len(presented),
    'stage_frames':len(by_frame),'groups':[{'pass':k[0],'index_count':k[1],**dict(v)} for k,v in groups.items()],
    'relative_darkening_events':events,
    'limitations':['Projected candidate triangles can be occluded by other geometry.',
        'Before/after values identify whether the observed target changes at this point; they do not identify every draw that may have written it.',
        'Different passes and final output may use different color spaces. Frame IDs are joined directly; ordering and format remain explicit.']}
(run/'primary-event-correlation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['relative_darkening_events','limitations']}))
print('Events:',[(r['frame'],round(r['drop'],4),round(r['ratio'],4)) for r in events])
