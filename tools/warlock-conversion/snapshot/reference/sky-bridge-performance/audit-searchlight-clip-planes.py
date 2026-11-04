"""Project searchlight body vertices against witnessed dynamic-light clip planes.

This is an offline mathematical audit, not GPU vertex-output capture. It is
useful alongside the query that remains zero with depth/stencil bypassed.
"""
import argparse,array,hashlib,importlib.util,json,struct
from pathlib import Path
import numpy as np
REF=Path(__file__).resolve().parent;REPO=REF.parents[4]
spec=importlib.util.spec_from_file_location('model',REF/'trace-model-draws.py')
model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)

def analyze(run):
    run=run.resolve();run.relative_to(REPO/'work/sky-bridge')
    config=json.loads((run/'recording-configuration.json').read_text())
    path=REPO/f"work/sky-bridge/payload-{config['candidate']}/sky_bridge.map"
    assert hashlib.sha256(path.read_bytes()).hexdigest()==config['map_sha256']
    cache=model.Cache(path);root=cache.tags[10122]['offset'];mesh,=cache.block(root+0x68,76)
    resource=model.Resource(cache,cache.u(root+0xe0))
    vb=resource.buffers('vertex')[cache.unpack('h',mesh+24)[0]]
    ib=resource.buffers('index')[cache.unpack('h',mesh+40)[0]]
    def raw(field,size):
        p=resource.fix[field];return resource.raw[(p>>29)-2][(p&0x1fffffff):(p&0x1fffffff)+size]
    count,fmt,stride=resource.unpack('IHH',vb);assert (fmt,stride)==(3,32)
    vertices=raw(vb+20,count*stride);indices=raw(ib+16,resource.unpack('I',ib+4)[0])
    part=cache.block(mesh,16)[0];start,length=cache.unpack('HH',part+4);assert length==562
    used=np.unique(np.frombuffer(indices,dtype='>u2')[start:start+length]);used=used[used!=65535]
    xyz=np.ndarray((count,3),dtype='>u2',buffer=vertices,strides=(stride,2))[used].astype(float)/65535
    bones=np.ndarray((count,4),dtype='u1',buffer=vertices,offset=24,strides=(stride,1))[used]
    weights=np.ndarray((count,4),dtype='u1',buffer=vertices,offset=28,strides=(stride,1))[used].astype(float)
    assert np.all(weights.sum(axis=1)>0) and bones.max()<3
    weights/=weights.sum(axis=1,keepdims=True)
    cache.close()
    calls={x['sequence']:x for x in json.loads((run/'model-draw-calls.json').read_text())['calls']}
    regs=array.array('I',[0])*0x5003;rows=[]
    for kind,data in model.packets(run/'draws.bin'):
        if kind==1:seq=struct.unpack('<11Q',data)[0]
        elif kind==2:
            for i,v in struct.iter_unpack('<II',data):regs[i]=v
        elif kind==5:
            c=calls[seq]
            if c['candidates']!=[dict(owner=10122,mesh=0,part=0)] or c['vs']!=1802336714319958646:continue
            assert c['ps']==14007674117786981017 and regs[0x2204]==0x8003f and regs[0x2206]==0x43f
            assert not regs[0x2202]&8,'Unexpected hardware alpha test'
            constants=np.frombuffer(regs[0x4000:0x4400].tobytes(),dtype='<f4').reshape(256,4).astype(float)
            assert tuple(constants[255])==(0,1,3,0)
            positions=np.c_[xyz*constants[12,:3]+constants[13,:3],np.ones(len(xyz))]
            palette=constants[16:25].reshape(3,3,4)
            # Native disassembly uses normalized four-bone matrix blending,
            # then affine position and camera projection. The host computes
            # user clip distances before its viewport/depth remapping.
            blended=np.einsum('vi,vijk->vjk',weights,palette[bones])
            world=np.einsum('vij,vj->vi',blended,positions)
            clip=np.c_[world,np.ones(len(world))]@constants[:4].T
            planes=np.frombuffer(regs[0x2388:0x23a0].tobytes(),dtype='<f4').reshape(6,4).astype(float)
            distances=clip@planes.T
            rows.append(dict(sequence=seq,frame=c['frame'],plane_min=distances.min(0).tolist(),
                plane_max=distances.max(0).tolist(),fully_outside_planes=np.flatnonzero(distances.max(0)<0).tolist()))
    assert rows and all(r['fully_outside_planes'] for r in rows)
    report=dict(run=str(run.relative_to(REPO)),frames=len(rows),vertices=len(used),indices=length,
        all_frames_have_fully_excluding_plane=True,
        largest_closest_excluding_distance=max(max(r['plane_max'][i] for i in r['fully_outside_planes']) for r in rows),
        rows=rows,inputs_sha256={n:hashlib.sha256((run/n).read_bytes()).hexdigest() for n in ('draws.bin','model-draw-calls.json')},
        limitations=['Mathematical reconstruction with float64 intermediates, not bit-exact GPU vertex execution.',
            'Uses the byte-attributed model buffer and observed transforms, but does not directly capture post-VS positions.',
            'Consistent with native light-volume clipping; does not by itself prove the authored light or shader is visually correct.'],
        credit=json.loads((REF/'sky-pixel-probe-build.json').read_text())['credit'])
    (run/'searchlight-clip-plane-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('frames','vertices','all_frames_have_fully_excluding_plane','largest_closest_excluding_distance')}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);analyze(p.parse_args().run)
