"""Check authored searchlight animation bytes and witnessed per-pass transforms."""
import argparse,array,collections,hashlib,importlib.util,json,struct,sys
from pathlib import Path
REF=Path(__file__).resolve().parent;REPO=REF.parents[4]
sys.path.insert(0,str(REPO/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
from string_ids import StringTable
from animation_resource import convert_animation_resource
spec=importlib.util.spec_from_file_location('model',REF/'trace-model-draws.py')
model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)

def animation():
    source=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map',mcc=True)
    target=Cache(REPO/'work/sky-bridge/payload-35/sky_bridge.map')
    strings=[StringTable(c) for c in (source,target)]
    metadata=[];resources=[]
    for c,st,tag in zip((source,target),strings,(4237,10134)):
        root=c.tags[tag]['offset']
        metadata.append(dict(nodes=[st.text(c.u(x)) for x in c.block(root+20,32)],
            animations=[dict(name=st.text(c.u(x)),frames=c.unpack('h',x+16)[0],nodes=c.data[x+15],compression_field=c.data[x+14]) for x in c.block(root+80,136)]))
        group,=c.block(root+248,12);resources.append(Resource(c,c.u(group+4)))
    assert metadata[0]==metadata[1]
    converted=convert_animation_resource(resources[0],lambda sid:strings[0].translate(sid,strings[1]))
    actual=resources[1]
    assert actual.root==converted['root'] and actual.fix==dict(converted['fixups'])
    assert actual.data==converted['control']
    assert actual.raw[0][:len(converted['raw'])]==converted['raw']
    result=dict(metadata=metadata[0],members=converted['members'],codecs=converted['codecs'],
        converted_raw_bytes=len(converted['raw']),control_bytes=len(converted['control']),
        raw_sha256=hashlib.sha256(converted['raw']).hexdigest(),control_sha256=hashlib.sha256(converted['control']).hexdigest(),
        control_fixups_and_raw_equal=True)
    source.close();target.close();return result

def analyze(run,output):
    for path in (run,output):path.resolve().relative_to(REPO/'work/sky-bridge')
    calls={c['sequence']:c for c in json.loads((run/'model-draw-calls.json').read_text())['calls']}
    regs=array.array('I',[0])*0x5003
    transforms=collections.defaultdict(dict);states=collections.defaultdict(set);geometry_parts={}
    metadata=json.loads((run/'model-draw-analysis.json').read_text())
    for p in metadata['parts']:
        if p['owner']==10122:geometry_parts[p['part']]=p
    for kind,raw in model.packets(run/'draws.bin'):
        if kind==1:seq=struct.unpack('<11Q',raw)[0]
        elif kind==2:
            for i,v in struct.iter_unpack('<II',raw):regs[i]=v
        elif kind==5:
            c=calls[seq];owner,=c['candidates']
            if owner['owner']!=10122:continue
            part=owner['part'];key=(part,c['vs'],c['ps'])
            data=regs[0x4000:0x4020].tobytes()+regs[0x4030:0x4040].tobytes()
            for bone in geometry_parts[part]['palette_indices']:data+=regs[0x4040+bone*12:0x404c+bone*12].tobytes()
            transforms[c['frame'],part][c['vs']]=hashlib.sha256(data).hexdigest()
            states[key].add(tuple(regs[i] for i in (0x2200,0x210d,0x2205,0x2002)))
    equality={}
    for part in (0,1):
        frames=[v for (f,p),v in transforms.items() if p==part]
        assert all(len(v)==3 and len(set(v.values()))==1 for v in frames)
        equality[part]=dict(frames=len(frames),passes_per_frame=3,all_position_inputs_identical=True)
    state_report=[]
    for key,values in sorted(states.items()):
        for depth,stencil,raster,depth_info in sorted(values):
            state_report.append(dict(part=key[0],vs=key[1],ps=key[2],depth_control=hex(depth),depth_info=hex(depth_info),
                stencil=hex(stencil),raster=hex(raster),z_enable=bool(depth&2),z_write=bool(depth&4),z_func=(depth>>4)&7,
                stencil_enabled=bool(depth&1),stencil_func=(depth>>8)&7,stencil_ref=stencil&255,stencil_read_mask=(stencil>>8)&255))
    report=dict(run=str(run.relative_to(REPO)),animation=animation(),cross_pass_position_inputs=equality,states=state_report,
        inputs_sha256={n:hashlib.sha256((run/n).read_bytes()).hexdigest() for n in ('draws.bin','model-draw-calls.json','model-draw-analysis.json')},
        limitations=['Matching animation payloads and finite/smooth matrices do not establish correct animated geometry or lighting.',
            'The position-input comparison excludes shader literal slots; the distinct native vertex programs still need execution/output comparison.',
            'Zero surviving lighting coverage remains unexplained: later occlusion, rasterization, shader discard, and depth/stencil rejection have not been distinguished.',
            'No animation suppression, depth override or lighting fix follows from this audit.'],
        credit=json.loads((REF/'sky-pixel-probe-build.json').read_text())['credit'])
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(animation=report['animation'],position_inputs=equality)))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('run','output'):parser.add_argument(name,type=lambda s:Path(s).resolve())
    args=parser.parse_args();analyze(args.run,args.output)
