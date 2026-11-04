"""Check sparse probe points against projected candidate triangles, not just bounds."""
import argparse
import array
import collections
import csv
import json
from pathlib import Path
import sys
import struct
import numpy as np

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('trace_dir',type=Path)
parser.add_argument('--region-events',type=Path,
                    help='Test measured relative-darkening coordinates from this region CSV.')
args=parser.parse_args(); root=args.trace_dir
repo=Path(__file__).resolve().parents[5];root.resolve().relative_to(repo)
sys.path.insert(0,str(repo/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource

groups=json.loads((root/'geometry-state.json').read_text())['groups']
with (root/'pixels.csv').open() as stream:
    rows=[r for r in csv.DictReader(stream) if r['event']=='sample']
first=rows[0]
width,height=int(first['width']),int(first['height'])
registers=array.array('I',[0])*0x5003
viewport_variants=collections.Counter()
with (root/'draws.bin').open('rb') as stream:
    while header:=stream.read(8):
        kind,size=struct.unpack('<II',header);data=stream.read(size)
        if len(data)!=size:raise ValueError('Truncated draw packet')
        if kind==1:draw=struct.unpack('<11Q',data)
        elif kind==2:
            for index,value in struct.iter_unpack('<II',data):registers[index]=value
        elif kind==5 and draw[4] in {g['ps'] for g in groups}:
            state=tuple(registers[i] for i in (0x2080,0x2081,0x2082,0x210f,0x2110,0x2111,0x2112,0x2206))
            viewport_variants[state]+=1
if not viewport_variants:raise ValueError('No emitted viewport evidence')
viewport_evidence=[]
for state,count in viewport_variants.items():
    window,tl,br,*values,vte=state
    sx,ox,sy,oy=struct.unpack('<4f',struct.pack('<4I',*values))
    if window or tl or br!=(height<<16|width) or (sx,ox,sy,oy)!=(width/2,width/2,-height/2,height/2) or vte!=0x43f:
        raise ValueError('Recorded viewport differs from the supported projection-to-probe mapping')
    viewport_evidence.append({'draws':count,'x_scale':sx,'x_offset':ox,'y_scale':sy,'y_offset':oy,
                              'vte':hex(vte),'scissor_width':width,'scissor_height':height})
points=np.array([[int(r['x']),int(r['y'])] for r in rows if r['frame']==first['frame']])
if len(points)!=144 or len(set(map(tuple,points)))!=144:raise ValueError('Incomplete or duplicate sample grid')
event_count=0
if args.region_events:
    args.region_events.resolve().relative_to(repo)
    with args.region_events.open() as stream:
        events=[r for r in csv.DictReader(stream) if r['event']=='sample' and float(r['worst_pulse_drop'])>51/1023]
    if not events:raise ValueError('No relative-darkening coordinates')
    if any((int(r['viewport_width']),int(r['viewport_height']))!=(width,height) for r in events):
        raise ValueError('Event viewport differs from recorded geometry viewport')
    points=np.array(sorted({(int(r['worst_x']),int(r['worst_y'])) for r in events}))
    if any(not (0<=x<width and 0<=y<height) for x,y in points):raise ValueError('Event point outside viewport')
    event_count=len(events)
uv=(points+.5)/[width,height]
cache=Cache('work/sky-bridge/payload-32/sky_bridge.map')
cache.shared_paths={'maps\\shared.map':Path('C:/X360/ISOs/H3M/maps/shared.map')}
base,=cache.block(cache.tags[9894]['offset']+4,436)
meshes=cache.block(base+0x134,76)
resource=Resource(cache,cache.u(base+0x1ac))
vb=resource.buffers('vertex');ib=resource.buffers('index')
def raw(field,size):
    p=resource.fix[field];return resource.raw[(p>>29)-2][(p&0x1fffffff):(p&0x1fffffff)+size]
seen=set();results=[]
for group in groups:
    g=group['geometry'];key=(g['mesh'],g['part'],group['model'])
    if key in seen:continue
    seen.add(key)
    mesh=meshes[g['mesh']]
    vertex=vb[cache.unpack('h',mesh+24)[0]];index=ib[cache.unpack('h',mesh+40)[0]]
    count,fmt,stride=resource.unpack('IHH',vertex)
    if fmt!=2 or stride!=24:raise ValueError('Only the traced rigid vertex format is established')
    payload=raw(vertex+20,count*stride)
    vertices=np.ndarray((count,3),dtype='>u2',buffer=payload,strides=(stride,2)).astype(np.float64)/65535
    vs=np.frombuffer(bytes.fromhex(group['vertex_constants_0_18']),dtype='<f4').reshape(19,4)
    vertices=vertices*vs[12,:3]+vs[13,:3]
    world=np.c_[vertices,np.ones(count)]@vs[16:19].T
    clip=np.c_[world,np.ones(count)]@vs[:4].T
    indices=np.frombuffer(raw(index+16,resource.unpack('I',index+4)[0]),dtype='>u2')
    indices=indices[g['index_start']:g['index_start']+g['index_count']]
    # Recorded draw primitive 4 is triangle list; reject primitive restart.
    if len(indices)%3 or max(indices)>=count:raise ValueError('Invalid triangle list')
    triangle_indices=indices.reshape(-1,3)
    valid=np.all(clip[triangle_indices,3]>0,axis=1)
    tri_clip=clip[triangle_indices[valid]]
    tri_uv=tri_clip[:,:,:2]/tri_clip[:,:,3,None]*[.5,-.5]+[.5,.5]
    a,b,c=tri_uv[:,0],tri_uv[:,1],tri_uv[:,2]
    ab=b-a;ac=c-a
    det=ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]
    nondegenerate=np.abs(det)>1e-14
    hits=[]
    for point,pixel in zip(uv,points):
        ap=point-a
        safe=np.where(nondegenerate,det,1)
        s=(ap[:,0]*ac[:,1]-ap[:,1]*ac[:,0])/safe
        t=(ab[:,0]*ap[:,1]-ab[:,1]*ap[:,0])/safe
        inside=nondegenerate&(s>=0)&(t>=0)&(s+t<=1)
        if np.any(inside):
            hits.append({'x':int(pixel[0]),'y':int(pixel[1]),'triangles':int(inside.sum())})
    results.append({'mesh':g['mesh'],'part':g['part'],'material':g['material'],
                    'projected_triangles':len(tri_uv),'covered_sample_points':hits})
report={'width':width,'height':height,'viewport_evidence':viewport_evidence,'results':results,
        'limitation':'Geometric coverage only: does not establish visibility through other objects, front-face acceptance, MSAA sample coverage, or correspondence to the human-circled surface.',
        'vertex_transform_evidence':'Live VS 17757447148780339854: fetch 12, decompression 22, model 24-29, homogeneous 36, projection 50-53, position export 101. c255 is (0,1,31.75,0.001). Vertex fetch 95 uses endian 8-in-32, and y/x/w swizzle recovers big-endian u16 XYZ.'}
report['query']={'kind':'relative_darkening_event_coordinates' if args.region_events else 'sparse_pixel_probe',
                 'event_rows':event_count,'unique_points':len(points)}
output='region-event-triangle-coverage.json' if args.region_events else 'sample-triangle-coverage.json'
(root/output).write_text(json.dumps(report,indent=2)+'\n')
for result in results:
    print(result['mesh'],len(result['covered_sample_points']),'covered points' if args.region_events else result['covered_sample_points'])
cache.close()
