"""Audit candidate32 water mips and compare a partial texture model to paired GPU samples.

Run after geometry-state.json and water-pass-analysis.json have been produced.
All output stays in the supplied private replay directory; no image is written.
"""
import argparse,json,sys,struct,hashlib,math,csv,array,re
from pathlib import Path
import numpy as np
from PIL import Image
ref=Path(__file__).resolve().parent;repo=ref.parents[4]
sys.path.insert(0,str(repo/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
from mcc_bitmap_source import BitmapSource
from xbox_mip_chain import layout
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('run',type=Path)
args=parser.parse_args();run=args.run.resolve();run.relative_to(repo/'work/sky-bridge')
out=run
def sha(path):
 with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
map_path=repo/'work/sky-bridge/payload-32/sky_bridge.map'
assert sha(map_path)=='311ad88580c5e099546c029f07f93976c346a8bb9bf9b12c1d48f72f5e0c3e5d'
shader_source=repo/'work/sky-bridge/water-card-native-01/xenos-source/albedo.fx'
shader_text=shader_source.read_text()
detail_multiplier=float(re.search(r'^#define DETAIL_MULTIPLIER ([0-9.]+)f$',shader_text,re.M)[1])
assert detail_multiplier==4.59479
s=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map',True)
c=Cache(map_path);c.decoded_pages={}
c.shared_paths={'maps\\shared.map':Path('C:/X360/ISOs/H3M/maps/shared.map')}
bs=BitmapSource(s);textures={};audits=[]
for si,ti in [(12314,9411),(12315,9412),(12316,9413)]:
 info=bs.info(si)[0];src=bs.pixels(si);native,=c.block(c.tags[ti]['offset']+0x60,48)
 w,h=c.unpack('HH',native+4);fmt=c.unpack('H',native+12)[0];count=c.data[native+20]+1
 assert fmt==info['format']==16
 hw,=c.block(c.tags[ti]['offset']+0x8c,8);res=Resource(c,c.u(hw));assert not c.u(native+36)
 payload=res.raw[0][c.u(native+24):c.u(native+24)+c.u(native+28)]
 sw,sh=info['width'],info['height'];start=0;dropped=0
 while (sw,sh)!=(w,h):
  assert sw>=w and sh>=h
  start+=((sw+3)//4)*((sh+3)//4)*16;sw=max(1,sw//2);sh=max(1,sh//2);dropped+=1
 assert count==info['mips']-dropped
 levels=[];rows,_=layout(w,h,count,16,4);level_reports=[]
 for level,(positions,length) in enumerate(rows):
  data=np.frombuffer(payload,dtype=np.uint8)[positions.reshape(-1,1)+np.arange(16)]
  linear=data.reshape(-1,8,2)[:,:,::-1].tobytes();authored=src[start:start+length]
  assert linear==authored,(si,ti,level)
  lw,lh=max(1,w>>level),max(1,h>>level)
  levels.append(np.asarray(Image.frombytes('RGBA',(lw,lh),linear,'bcn',3),dtype=np.float64)/255)
  level_reports.append({'level':level,'source_level':level+dropped,'width':lw,'height':lh,'blocks_equal':True,'sha256':hashlib.sha256(linear).hexdigest()})
  start+=length
 textures[ti]=levels;audits.append({'source':si,'target':ti,'source_name':s.name(si),'source_curve':s.data[s.block(s.tags[si]['offset']+0x60,56)[0]+21],'target_curve':c.data[native+21],'mips':level_reports})

group=next(g for g in json.loads((run/'geometry-state.json').read_text())['groups'] if g['geometry']['mesh']==7 and g['geometry']['part']==0)
# Read the actual rasterization mode; D3D9 integer centers are shifted +0.5
# by this runtime's enabled-by-default half_pixel_offset path.
regs=array.array('I',[0])*0x5003
pipeline=set();mesh7_draws={};prefix_hashes={}
with (run/'draws.bin').open('rb') as stream:
 while header:=stream.read(8):
  kind,size=struct.unpack('<II',header);data=stream.read(size);assert len(data)==size
  if kind==6:prefix_address=struct.unpack('<4Q',data)[1]
  elif kind==7:prefix_hashes.setdefault(prefix_address,set()).add(hashlib.sha256(data).hexdigest())
with (run/'draws.bin').open('rb') as stream:
 while header:=stream.read(8):
  kind,size=struct.unpack('<II',header);data=stream.read(size)
  if kind==1:draw=struct.unpack('<11Q',data)
  elif kind==2:
   for i,v in struct.iter_unpack('<II',data):regs[i]=v
  elif kind==5 and draw[6]==84:
   pipeline.add(tuple(regs[i] for i in (0x2302,0x2205,0x2080,0x2081,0x2082,0x210f,0x2110,0x2111,0x2112,0x2206)))
   assert struct.unpack('<QQ',data)==draw[:2]
   if prefix_hashes.get(regs[0x48be]&0xfffffffc)=={group['geometry']['vertex_prefix_sha256']}:
    assert draw[1] not in mesh7_draws and draw[4]==group['ps']
    assert regs[0x4000:0x404c].tobytes().hex()==group['vertex_constants_0_18']
    mesh7_draws[draw[1]]=draw[0]
assert len(pipeline)==1,pipeline
pipeline=next(iter(pipeline));pixel_offset=.5 if not(pipeline[0]&1) else 0
geometry=group['geometry'];vs=np.frombuffer(bytes.fromhex(group['vertex_constants_0_18']),dtype='<f4').reshape(19,4).astype(np.float64)
base,=c.block(c.tags[9894]['offset']+4,436);mesh=c.block(base+0x134,76)[7]
r=Resource(c,c.u(base+0x1ac));vb=r.buffers('vertex');ib=r.buffers('index')
def raw(field,n):
 p=r.fix[field];return r.raw[(p>>29)-2][(p&0x1fffffff):(p&0x1fffffff)+n]
vertex=vb[c.unpack('h',mesh+24)[0]];index=ib[c.unpack('h',mesh+40)[0]]
count,fmt,stride=r.unpack('IHH',vertex);assert (fmt,stride)==(2,24)
payload=raw(vertex+20,count*stride);positions=np.ndarray((count,3),dtype='>u2',buffer=payload,strides=(stride,2)).astype(np.float64)/65535
coords=np.ndarray((count,2),dtype='>u2',buffer=payload,offset=8,strides=(stride,2)).astype(np.float64)/65535
coords=coords*vs[14,:2]+vs[14,2:]
positions=positions*vs[12,:3]+vs[13,:3]
world=np.c_[positions,np.ones(count)]@vs[16:19].T
clip=np.c_[world,np.ones(count)]@vs[:4].T
indices=np.frombuffer(raw(index+16,r.unpack('I',index+4)[0]),dtype='>u2')[:84].reshape(-1,3)
hits=[]
def bary(pixel,triangle):
 xy=clip[triangle,:2]/clip[triangle,3,None]*[576,-320]+[576+pixel_offset,320+pixel_offset]
 weights=np.linalg.solve(np.vstack([xy.T,np.ones(3)]),[*pixel,1.0])
 perspective=weights/clip[triangle,3];perspective/=sum(perspective)
 return weights,perspective@coords[triangle],xy
for ti,triangle in enumerate(indices):
 if np.any(clip[triangle,3]<=0):continue
 weights,uv,xy=bary((714.5,210.5),triangle)
 if min(weights)<-1e-9:continue
 _,uvx,_=bary((715.5,210.5),triangle);_,uvy,_=bary((714.5,211.5),triangle)
 hits.append({'triangle':ti,'indices':triangle.tolist(),'screen':xy.tolist(),'world':world[triangle].tolist(),'uv':uv.tolist(),'du_dx':(uvx-uv).tolist(),'du_dy':(uvy-uv).tolist()})
assert hits
assert all(np.allclose(h['uv'],hits[0]['uv'],rtol=0,atol=1e-12) and np.allclose(h['du_dx'],hits[0]['du_dx'],rtol=0,atol=1e-12) and np.allclose(h['du_dy'],hits[0]['du_dy'],rtol=0,atol=1e-12) for h in hits),hits
hit=hits[0];uv=np.array(hit['uv']);dx=np.array(hit['du_dx']);dy=np.array(hit['du_dy'])
parameters={}
for name,variants in group['parameters'].items():
 parameters[name]={frame:np.frombuffer(bytes.fromhex(value),dtype='<f4').astype(np.float64) for value,frames in variants.items() for frame in frames}
samplers={}
for name,variants in group['samplers'].items():
 if name not in ('base_map','detail_map','detail_map2','detail_map_overlay'):continue
 assert len(variants)==1
 words=struct.unpack('<6I',bytes.fromhex(next(iter(variants))))
 samplers[name]={'words':[hex(w) for w in words],'signs':[(words[0]>>shift)&3 for shift in (2,4,6,8)],'clamp':[(words[0]>>shift)&7 for shift in (10,13)],'mag':words[3]>>19&3,'min':words[3]>>21&3,'mip':words[3]>>23&3,'aniso':words[3]>>25&7,'bias':((words[4]>>12&1023)^512)-512,'mip_max':words[4]>>6&15}

assert all(s['mag']==s['min']==s['mip']==1 and s['aniso']==s['bias']==0 for s in samplers.values())

def bilinear(image,p,clamp):
 h,w,_=image.shape;position=np.asarray(p)*[w,h]-.5;cell=np.floor(position).astype(int);frac=position-cell
 x,y=cell;u,v=frac
 def address(i,n,mode):
  if mode==0:return i%n
  assert mode==1
  j=i%(2*n);return j if j<n else 2*n-1-j
 x0,x1=[address(k,w,clamp[0]) for k in (x,x+1)];y0,y1=[address(k,h,clamp[1]) for k in (y,y+1)]
 return (image[y0,x0]*(1-u)+image[y0,x1]*u)*(1-v)+(image[y1,x0]*(1-u)+image[y1,x1]*u)*v
def sample(tid,p,transform,sampler):
 levels=textures[tid];h,w,_=levels[0].shape
 footprint=max(np.linalg.norm(dx*transform[:2]*[w,h]),np.linalg.norm(dy*transform[:2]*[w,h]))
 lod=max(0,min(len(levels)-1,math.log2(max(footprint,1e-30))+sampler['bias']/32))
 lo=int(math.floor(lod));hi=min(lo+1,len(levels)-1)
 a=bilinear(levels[lo],p,sampler['clamp']);b=bilinear(levels[hi],p,sampler['clamp'])
 result=a*(1-(lod-lo))+b*(lod-lo)
 for j,sign in enumerate(sampler['signs']):
  if sign==0:continue
  assert sign==3
  gamma=max(0,min(1,result[j]))
  scale,offset=(8/1024,-1024) if gamma>=192/255 else (4/1024,-256) if gamma>=96/255 else (2/1024,-64) if gamma>=64/255 else (1/1024,0)
  value=gamma*(255*1024*scale)+offset;result[j]=(value+math.trunc(value*scale))/1023
 return result,lod
rows=[]
stage={}
for row in csv.DictReader((run/'stages.csv').open()):
 if row['event']=='sample' and int(row['index_count'])==84:
  stage.setdefault(int(row['frame']),{}).setdefault(int(row['sequence']),{})[int(row['phase'])]=int(row['w0'])
for frame in sorted(parameters['base_map_xform']):
 samples={};lods={}
 for name,tid in [('base_map',9411),('detail_map',9412),('detail_map2',9411),('detail_map_overlay',9413)]:
  tr=parameters[name+'_xform'][frame];samples[name],lods[name]=sample(tid,uv*tr[:2]+tr[2:],tr,samplers[name])
 base=samples['base_map'];blend=(1-base[3])*samples['detail_map']+base[3]*samples['detail_map2']
 albedo=base[:3]*(detail_multiplier**2)*blend[:3]*samples['detail_map_overlay'][:3]
 # Match actual submitted sequence and vertex prefix; never assume draw order.
 seq=mesh7_draws[frame];before,after=(stage[frame][seq][p] for p in (0,1))
 delta=np.array([(after>>shift&255)-(before>>shift&255) for shift in (0,8,16)],dtype=float)/255
 rows.append({'frame':frame,'uv':uv.tolist(),'albedo_rgb':albedo.tolist(),'samples':{k:v.tolist() for k,v in samples.items()},'lods':lods,'measured_water_delta_rgb':delta.tolist()})
albedo=np.array([row['albedo_rgb'] for row in rows]);delta=np.array([row['measured_water_delta_rgb'] for row in rows])
report={'detail_multiplier':detail_multiplier,'shader_source_sha256':hashlib.sha256(shader_source.read_bytes()).hexdigest(),'texture_conversion':audits,'geometry_hits':hits,'pipeline_register_words':[hex(x) for x in pipeline],'runtime_half_pixel_offset':pixel_offset,'samplers':samplers,'rows':rows,
 'correlation_max_channel':float(np.corrcoef(albedo.max(axis=1),delta.max(axis=1))[0,1]),
 'correlation_sqrt_max_channel':float(np.corrcoef(np.sqrt(albedo.max(axis=1)),delta.max(axis=1))[0,1]),
 'limitations':['Partial CPU texture model using recorded linear filtering, address modes, LOD, and PWL gamma conversion. Lighting, full shader output and exact GPU precision are not reproduced; correlation is not a visual correctness verdict.',
 'Source block equality validates the converted bitmap payload; runtime GPU texture contents are a separate question. No image is generated.']}
report['inputs']={name:sha(run/name) for name in ('draws.bin','stages.csv','geometry-state.json','water-pass-analysis.json')}
report['map_sha256']=sha(map_path)
report['credit']=json.loads((ref/'sky-pixel-probe-build.json').read_text())['credit']
by_frame={r['frame']:r for r in rows};report['event_windows']=[]
for event in json.loads((run/'water-pass-analysis.json').read_text())['relative_decreases']:
 if not event['complete_stage_window']:continue
 frame=event['frame'];values=[by_frame[f] for f in (frame-1,frame,frame+1)]
 report['event_windows'].append({'frame':frame,'model_max_albedo':[max(v['albedo_rgb']) for v in values],'measured_max_delta':[max(v['measured_water_delta_rgb']) for v in values]})
(out/'water-texture-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'mip_counts':[len(a['mips']) for a in audits],'uv':hit['uv'],'correlation':report['correlation_max_channel'],'sqrt_correlation':report['correlation_sqrt_max_channel'],'samplers':samplers}))
c.close();s.close()
