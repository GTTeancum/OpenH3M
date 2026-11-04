import hashlib,json,struct,sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
from resource_reader import Resource
from xbox_bitmap import untile_base
out=Path('work/sky-bridge/fabric-cutout-build')
a=Cache('work/sky-bridge/payload-32/sky_bridge.map');b=Cache('work/sky-bridge/payload-35/sky_bridge.map')
build=json.loads((out/'build.json').read_text());assert set(b.tags)-set(a.tags)=={build['private_template']&65535,build['private_pixel']&65535}
materials=0
for tid,t in a.tags.items():
 if t['group']!='rmsh':continue
 n=b.tags[tid];assert a.data[t['offset']:t['offset']+68]==b.data[n['offset']:n['offset']+68]
 ap=a.block(t['offset']+40,132);bp=b.block(n['offset']+40,132);assert len(ap)==len(bp)
 for x,y in zip(ap,bp):
  left=bytearray(a.data[x:x+132]);right=bytes(b.data[y:y+132])
  if tid==9821:struct.pack_into('>I',left,12,build['private_template']);struct.pack_into('>I',left,108,0)
  assert left==right,tid
 materials+=1
for tid,size in ((225,132),(227,32),(10177,280)):
 x=a.tags[tid]['offset'];y=b.tags[tid]['offset'];assert a.data[x:x+size]==b.data[y:y+size]
# Compare original and private pixel rows: only the runtime shader-info pointer
# changes. Shader reflection, native GPR count and entry routing are unchanged.
old=a.tags[227]['offset'];new=b.tags[build['private_pixel']&65535]['offset']
assert [bytes(a.data[x:x+2]) for x in a.block(old+4,2)]==[bytes(b.data[x:x+2]) for x in b.block(new+4,2)]
for x,y in zip(a.block(old+20,80),b.block(new+20,80)):assert a.data[x:x+76]==b.data[y:y+76]
f32=lambda v:struct.unpack('>f',struct.pack('>f',v))[0]
threshold=struct.unpack('>f',struct.pack('>I',0x3f008081))[0]
values=[f32(i/255) for i in range(256)]+[struct.unpack('>f',struct.pack('>I',0x3f008081+d))[0] for d in range(-256,257)]+[-10.,0.,1.,10.]
assert all((v>=threshold)==(not threshold>v) for v in values)
programs=[]
for p in build['programs']:
 w0,w1,w2=struct.unpack('>III',bytes.fromhex(p['discard_instruction']))
 assert (w2>>24)&31==25 and (w0>>16)&15==0 # KILL_GT, no GPR destination.
 assert (w2>>16)&255==252 and not (w2>>31)&1
 swizzle=(w1>>16)&255
 assert [((swizzle>>(2*i))+i)&3 for i in range(4)]==[3]*4
 programs.append(dict(index=p['index'],opcode='KILL_GT',threshold_register='c252.w',destination_write_mask=0))
textures=[]
for cache in (a,b):
 t=cache.tags[9686]['offset'];row,=cache.block(t+96,48);width,height=cache.unpack('HH',row+4);fmt=cache.unpack('H',row+12)[0]
 hw,=cache.block(t+140,8);resource=Resource(cache,cache.u(hw));raw=untile_base(resource.raw[0],width,height,fmt);assert fmt==16
 alpha=np.asarray(Image.frombytes('RGBA',(width,height),raw,'bcn',3))[:,:,3]
 textures.append(dict(bitmap=9686,width=width,height=height,mips=cache.data[row+20]+1,
  raw_resource_sha256=[hashlib.sha256(x).hexdigest() for x in resource.raw],
  below_threshold=int(np.count_nonzero(alpha<128)),at_or_above_threshold=int(np.count_nonzero(alpha>=128))))
assert textures[0]==textures[1] and textures[0]['below_threshold']==41144
report=dict(materials_checked=materials,changed_materials=[9821],stock_template_and_pixel_unchanged=True,model10177_root_unchanged=True,private_pixel_interfaces_unchanged=True,finite_alpha_cases=len(values),threshold=threshold,discard_decodes=programs,unchanged_alpha_texture=textures[0],limitations=['Finite alpha inputs only; the native comparison rejects NaN while shader KILL_GT does not. Texture alpha and witnessed exposure inputs are finite.','The whole native base-mip alpha distribution is checked numerically; runtime edge coverage still requires verification.','Runtime probes still required for actual coverage and lighting; physical Xbox 360 not verified.'])
(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));a.close();b.close()
