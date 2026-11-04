"""Correlate paired numeric GPU colors with exact recorded cylinder buffers."""
import array,collections,csv,hashlib,importlib.util,json,struct,sys
from pathlib import Path
REF=Path(__file__).resolve().parent;REPO=REF.parents[4]
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,REF/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
packets=module('models','trace-model-draws.py').packets
rgba=module('stage','read-stage-probe.py').rgba
def analyze(run):
    run.relative_to(REPO/'work/sky-bridge')
    matches=json.loads((run/'geometry-prefix-matches.json').read_text())['matches']
    geometry=collections.defaultdict(list)
    for row in matches:
        for g in row['matches']:
            if g['owner']==9894 and g['index_count']*2==row['length']:geometry[row['address']].append(g)
    prefixes={}
    for kind,data in packets(run/'draws.bin'):
        if kind==6:_,address,_,_=struct.unpack('<4Q',data)
        elif kind==7:prefixes[address]=hashlib.sha256(data).hexdigest()
    regs=array.array('I',[0])*0x5003;draws={};identities={}
    for kind,data in packets(run/'draws.bin'):
        if kind==1:seq,frame,_,vs,ps,primitive,count,address,*_=struct.unpack('<11Q',data)
        elif kind==2:
            for i,v in struct.iter_unpack('<II',data):regs[i]=v
        elif kind==5:
            candidates=[g for g in geometry[address] if g['index_count']==count and g['vertex_prefix_sha256']==prefixes.get(regs[0x48be]&~3)]
            assert len(candidates)==1,(seq,candidates)
            g=candidates[0];assert g['mesh'] in (121,357)
            transform=regs[0x4040:0x404c].tobytes().hex()
            key=f"mesh{g['mesh']}-ps{ps}-transform{hashlib.sha256(bytes.fromhex(transform)).hexdigest()[:12]}"
            identities.setdefault(key,dict(mesh=g['mesh'],material=g['target_material'],ps=ps,vs=vs,
                transform=list(struct.unpack('<12f',bytes.fromhex(transform))),depth_control=hex(regs[0x2200])))
            draws[frame,seq]=key
    pairs=collections.defaultdict(dict);events=collections.Counter()
    for row in csv.DictReader((run/'stages.csv').open()):
        events[row['event']]+=1
        if row['event']=='sample':
            key=tuple(int(row[k]) for k in ('frame','sequence','x','y'));phase=int(row['phase'])
            assert phase not in pairs[key];pairs[key][phase]=row
    assert not (set(events)-{'sample','end'}),events
    groups={};ownership=collections.defaultdict(set);per_frame=collections.defaultdict(dict)
    for (frame,seq,x,y),phases in pairs.items():
        assert set(phases)=={0,1}
        identity=draws[frame,seq];a,b=(rgba(phases[p]) for p in (0,1))
        changed=a!=b;k=identity,x,y
        group=groups.setdefault(k,dict(identity=identity,x=x,y=y,pairs=0,changed=0,maximum_draw_rgb_delta=0,after_min_rgb=[1e30]*3,after_max_rgb=[-1e30]*3))
        group['pairs']+=1;group['changed']+=changed
        group['maximum_draw_rgb_delta']=max(group['maximum_draw_rgb_delta'],max(abs(aa-bb) for aa,bb in zip(a[:3],b[:3])))
        group['after_min_rgb']=[min(aa,bb) for aa,bb in zip(group['after_min_rgb'],b[:3])]
        group['after_max_rgb']=[max(aa,bb) for aa,bb in zip(group['after_max_rgb'],b[:3])]
        if changed:ownership[frame,x,y].add(identities[identity]['mesh'])
        per_frame[k][frame]=b[:3]
    for k,values in per_frame.items():
        groups[k]['maximum_adjacent_after_rgb_delta']=max((max(abs(a-b) for a,b in zip(value,values[f-1])) for f,value in values.items() if f-1 in values),default=0)
    presented=collections.defaultdict(list);present_events=collections.Counter()
    for row in csv.DictReader((run/'presented.csv').open()):
        present_events[row['event']]+=1
        if row['event']!='sample':continue
        assert int(row['format'])==24
        word=int(row['packed_pixel']);value=tuple((word>>shift&1023)/1023 for shift in (0,10,20))
        presented[int(row['x']),int(row['y'])].append((int(row['frame']),value))
    final=[]
    for (x,y),values in presented.items():
        if not (642<=x<=657 and 175<=y<=188):continue
        consecutive=[(max(abs(a-b) for a,b in zip(v,pv)),f,pf,pv,v) for (pf,pv),(f,v) in zip(values,values[1:]) if f==pf+1]
        largest=max(consecutive,default=None)
        final.append(dict(x=x,y=y,samples=len(values),min_rgb=[min(v[i] for f,v in values) for i in range(3)],
            max_rgb=[max(v[i] for f,v in values) for i in range(3)],maximum_adjacent_delta=largest))
    result=dict(run=str(run.relative_to(REPO)),events=events,frames=len({f for f,s in draws}),draws=len(draws),
        identities=identities,groups=list(groups.values()),same_frame_both_meshes_changed_points=sum(v=={121,357} for v in ownership.values()),
        presented_events=present_events,presented_core=final,
        limitation='Numeric draw ownership and temporal colors at saved pixels. No new visual captures; not full traversal acceptance.')
    (run/'cylinder-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(run=result['run'],events=events,frames=result['frames'],draws=len(draws),
        mesh_changed_samples={m:sum(g['changed'] for g in groups.values() if identities[g['identity']]['mesh']==m) for m in (121,357)},
        both_meshes_changed_points=result['same_frame_both_meshes_changed_points'],
        target_groups=[g for g in groups.values() if (g['x'],g['y'])==(643,182)],
        presented_target=[g for g in final if (g['x'],g['y'])==(643,182)]),indent=2))
if __name__=='__main__':analyze((REPO/sys.argv[1]).resolve())
