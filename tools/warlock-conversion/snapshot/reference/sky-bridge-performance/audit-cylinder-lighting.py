"""Source effect fidelity and per-frame light/pixel evidence at the marked cylinder."""
import array,collections,csv,hashlib,importlib.util,json,struct,sys
from pathlib import Path
import numpy as np
REF=Path(__file__).resolve().parent;REPO=REF.parents[4]
assert Path.cwd().resolve()==REPO
sys.path.insert(0,str(REPO/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from tag_functions import convert_function
spec=importlib.util.spec_from_file_location('model',REF/'trace-model-draws.py')
model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
s=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map',True)
c=Cache(REPO/'work/sky-bridge/payload-36/sky_bridge.map')
functions=[]
for off,name in ((0x28,'color'),(0x4c,'intensity')):
    payload=[]
    for cache,tid in ((s,4464),(c,10420)):
        field=cache.tags[tid]['offset']+off;n=cache.u(field);p=cache.pointer(cache.u(field+12))
        payload.append(bytes(cache.data[p:p+n]))
    assert convert_function(payload[0])==payload[1]
    functions.append(dict(name=name,bytes=len(payload[1]),exact_endian_conversion=True,
        source_sha256=hashlib.sha256(payload[0]).hexdigest(),native_sha256=hashlib.sha256(payload[1]).hexdigest()))
events=[]
for i,(sr,tr) in enumerate(zip(s.block(s.tags[4463]['offset']+0x2c,68),c.block(c.tags[10419]['offset']+0x2c,68))):
    assert s.unpack('5f',sr+12)==c.unpack('5f',tr+12)
    sp,=s.block(sr+0x20,96);tp,=c.block(tr+0x20,96)
    assert s.u(sp+28)&65535==4464 and c.u(tp+28)&65535==10420
    assert s.unpack('3f',sp+0x44)==c.unpack('3f',tp+0x44)
    events.append(dict(index=i,skip_delay_duration=c.unpack('5f',tr+12),light_relative_offset=c.unpack('3f',tp+0x44)))
assert len(events)==2
sr=s.tags[4464]['offset'];tr=c.tags[10420]['offset']
assert s.unpack('IHH6f',sr)==c.unpack('IHH6f',tr)
assert s.unpack('4f',sr+0x70)==c.unpack('4f',tr+0x70)
source=dict(effect=s.name(4463),light=s.name(4464),particle=s.name(4465),
    source_tags=[4462,4463,4464,4465],target_tags=[10418,10419,10420,10421],
    light_maximum_distance=c.unpack('f',tr+8)[0],light_lifetime=c.unpack('f',tr+0x7c)[0],
    events=events,functions=functions)
s.close();c.close()
results=[]
for number in (51,52,53,54):
    run=REPO/f'work/sky-bridge/reproduction-{number}'
    summary=json.loads((run/'cylinder-analysis.json').read_text())
    colors={int(row['frame']):tuple((int(row['w0'])>>n)&255 for n in (0,8,16))
        for row in csv.DictReader((run/'stages.csv').open())
        if row['event']=='sample' and row['phase']=='1' and row['x']=='643' and row['y']=='182'
        and row['index_count']=='3522' and row['shader']=='14617156369365479079'}
    regs=array.array('I',[0])*0x5003;frames=[];inputs=collections.defaultdict(set)
    for kind,data in model.packets(run/'draws.bin'):
        if kind==1:seq,frame,_,vs,ps,primitive,count,*_=struct.unpack('<11Q',data)
        elif kind==2:
            for index,value in struct.iter_unpack('<II',data):regs[index]=value
        elif kind==5 and count==3522 and ps==14617156369365479079:
            loop=regs[0x4918];assert (loop>>8)&255==0 and (loop>>16)&255==5
            lights=[]
            for i in range(loop&255):
                at=0x4400+(18+i*5)*4;lights.append(list(struct.unpack('<20f',regs[at:at+20].tobytes())))
            nearest=[light for light in lights if np.linalg.norm(np.array(light[:3])-[25.11797332763672,97.47196960449219,6.819040298461914])<.00001]
            assert len(nearest)<=1
            frames.append(dict(frame=frame,rgb=colors[frame],light_count=len(lights),
                marked_electric_light=nearest[0] if nearest else None))
            for name,start,size in [('camera',0x4440,4),('exposure',0x4400,4),('material',0x4588,44),
                ('environment0',0x4806,6),('environment1',0x480c,6),('albedo',0x483c,6),('normal',0x4842,6)]:
                inputs[name].add(regs[start:start+size].tobytes().hex())
    (run/'cylinder-active-light-frames.json').write_text(json.dumps(frames,indent=2)+'\n')
    points=[]
    for group in summary['groups']:
        identity=summary['identities'][group['identity']]
        if identity['mesh']==357 and identity['ps']==14617156369365479079:
            points.append({k:group[k] for k in ('x','y','pairs','changed','after_min_rgb','after_max_rgb','maximum_adjacent_after_rgb_delta')})
    results.append(dict(run=number,candidate=json.loads((run/'recording-configuration.json').read_text())['candidate'],
        frames=len(frames),events=summary['events'],draws=summary['draws'],
        observed_meshes=sorted({v['mesh'] for v in summary['identities'].values()}),
        marked_light_present_frames=sum(f['marked_electric_light'] is not None for f in frames),
        pixel_rgb_states=sorted({tuple(f['rgb']) for f in frames}),
        input_variants={k:len(v) for k,v in inputs.items()},lighting_points=points,
        observer=json.loads((run/'native-observer-comparison.json').read_text())['same_result']))
report=dict(source=source,runs=results,credit=json.loads((REF/'candidate36-visual-review-result.json').read_text())['credit'],
    limitation='Paired GPU color and authored-source evidence; no new captures. Arc-particle appearance is not isolated by the light control.')
out=REPO/'work/sky-bridge/marked-object-review/cylinder-lighting-causal.json'
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([dict(run=r['run'],candidate=r['candidate'],frames=r['frames'],
    marked_light_present_frames=r['marked_light_present_frames'],pixel_rgb_states=r['pixel_rgb_states'],
    target_jump=next(p['maximum_adjacent_after_rgb_delta'] for p in r['lighting_points'] if (p['x'],p['y'])==(643,182))) for r in results],indent=2))
