"""Read-only comparison of flagged cylinder instances and merged render geometry."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
REPO=Path(__file__).resolve().parents[5]
assert Path.cwd().resolve()==REPO
sys.path.insert(0,str(REPO/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
from string_ids import StringTable
c=Cache(REPO/'work/sky-bridge/payload-36/sky_bridge.map')
strings=StringTable(c);bsp=c.tags[9225]['offset']
collision=Resource(c,c.u(bsp+0x37c));definitions=collision.ptr(collision.root+16)
base,=c.block(c.tags[9894]['offset']+4,436)
meshes=c.block(base+0x134,76);compression=c.block(base+0x140,44)
r=Resource(c,c.u(base+0x1ac));vbs=r.buffers('vertex');ibs=r.buffers('index')
instances=[]
for i,row in enumerate(c.block(bsp+0x1b0,120)):
    definition,flags=c.unpack('hH',row+52)
    mesh,ci=collision.unpack('HH',definitions+definition*184+176)
    instances.append(dict(index=i,name=strings.text(c.u(row+84)),definition=definition,
        mesh=mesh,compression=ci,flags=flags,transform=c.unpack('13f',row)))
def raw(field,size):
    p=r.fix[field];return r.raw[(p>>29)-2][(p&0x1fffffff):(p&0x1fffffff)+size]
def geometry(instance):
    mesh=meshes[instance['mesh']];vb=vbs[c.unpack('h',mesh+24)[0]];ib=ibs[c.unpack('h',mesh+40)[0]]
    n,fmt,stride=r.unpack('IHH',vb);assert fmt==2
    data=raw(vb+20,n*stride)
    bounds=np.array(c.unpack('6f',compression[instance['compression']]+4)).reshape(3,2)
    xyz=np.ndarray((n,3),dtype='>u2',buffer=data,strides=(stride,2)).astype(float)/65535
    xyz=xyz*(bounds[:,1]-bounds[:,0])+bounds[:,0]
    transform=np.array(instance['transform']);basis=transform[1:10].reshape(3,3)
    world=xyz@basis*transform[0]+transform[10:13]
    indices=np.frombuffer(raw(ib+16,r.unpack('I',ib+4)[0]),dtype='>u2').astype(int)
    parts=[dict(material=c.unpack('h',p)[0],start=c.unpack('H',p+4)[0],count=c.unpack('H',p+6)[0]) for p in c.block(mesh,16)]
    return world,indices,parts
cylinders=[i for i in instances if 'cilinder' in (i['name'] or '')]
comparisons=[]
for merged in [i for i in cylinders if '_merged' in i['name']]:
    mv,mi,mp=geometry(merged)
    for original in [i for i in cylinders if i['flags']&64]:
        if original['index']==merged['index']:continue
        ov,oi,op=geometry(original)
        # Closest stored vertex and triangle topology, not just an AABB overlap.
        distance=((ov[:,None,:]-mv[None,:,:])**2).sum(2)
        match=distance.argmin(1);maximum=float(np.sqrt(distance.min(1)).max())
        if maximum>.01:continue
        assert len(mp)==len(op)==1
        ot=match[oi[op[0]['start']:op[0]['start']+op[0]['count']]].reshape(-1,3)
        mt=mi[mp[0]['start']:mp[0]['start']+mp[0]['count']].reshape(-1,3)
        # Equivalent coincident vertices can have separate UV/normal seams.
        # Match triangle corners geometrically instead of requiring vertex IDs.
        oc=ov[oi[op[0]['start']:op[0]['start']+op[0]['count']]].reshape(-1,3,3)
        mc=mv[mt]
        errors=[]
        for triangle in oc:
            errors.append(min(float(np.linalg.norm(triangle-np.roll(mc,shift,axis=1),axis=2).max(1).min()) for shift in range(3)))
        comparisons.append(dict(original=original['index'],merged=merged['index'],
            original_mesh=original['mesh'],merged_mesh=merged['mesh'],
            original_vertices=len(ov),merged_vertices=len(mv),triangles=len(ot),
            maximum_nearest_vertex_distance=maximum,maximum_triangle_corner_distance=max(errors),
            material_equal=op[0]['material']==mp[0]['material']))
out=dict(map_sha256=hashlib.sha256(c.data).hexdigest(),cylinders=cylinders,
    source_flag64_instances=sum(bool(i['flags']&64) for i in instances),
    geometry_comparisons=comparisons,
    limitation='Geometric overlap does not establish GPU-visible contribution or the cause of temporal flicker.')
c.close();(REPO/'work/sky-bridge/marked-object-review/cylinder-overlap.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(cylinders=[{k:i[k] for k in ('index','name','mesh','flags')} for i in cylinders],
    flagged_instances=out['source_flag64_instances'],comparisons=comparisons),indent=2))
