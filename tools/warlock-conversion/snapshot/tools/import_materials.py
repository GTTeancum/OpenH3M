"""Import source albedos through a stock retail shader, without runtime changes."""
import struct,json,hashlib,zlib,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
from map_builder import MapBuilder
from cache_reader import Cache
from mcc_bitmap_source import BitmapSource
from encode_bitmap import encode_bitmap_base, SUPPORTED_FORMATS
from xexlib import Xex
R=Path(__file__).resolve().parents[2]
assert not 'OpenH3M.exe' in subprocess.check_output(['tasklist','/FI','IMAGENAME eq OpenH3M.exe'],text=True)
subprocess.run([sys.executable,str(R/'.local/tools/relocate_candidate.py')],check=True,stdout=subprocess.DEVNULL)
b=MapBuilder(R/'.local/candidate/lockout.map',0x300000);c=b.cache
s=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/2977651586/maps/warlock.map',True);source=BitmapSource(s)
addr=lambda off:off-c.start+c.base
z=next(v['offset'] for v in c.tags.values() if v['group']=='zone');p=next(v['offset'] for v in c.tags.values() if v['group']=='play')
zschema=ET.parse(R/'.local/reference/plugins/zone.xml').getroot()
ctrlfield=next(x for x in zschema if x.attrib.get('name')=='Native Resource Control Data');co=z+int(ctrlfield.attrib['offset'],0);control=bytearray(c.data[c.pointer(c.u(co+12)):c.pointer(c.u(co+12))+c.u(co)])
def table(off,stride):return bytearray(b''.join(c.data[x:x+stride] for x in c.block(off,stride)))
resources=table(z+0x58,64);pages=table(p+0x18,88);locations=table(p+0x30,16)
index=c.pointer(c.u(16));count=c.u(index+8);tags=bytearray(c.data[c.pointer(c.u(index+12)):c.pointer(c.u(index+12))+count*8]);first_tag=count;first_resource=len(resources)//64
xex=Xex(str(R/'default.xex'));im=xex.image();rr=xex.hdrs[0x2ff];salt=None
for pos in range(rr+4,rr+struct.unpack_from('>I',xex.raw,rr)[0],16):
 if xex.raw[pos:pos+8].rstrip(b'\0')==b'00':
  a,n=struct.unpack_from('>II',xex.raw,pos+8);salt=im[a-xex.image_base:a-xex.image_base+34]
assert salt

def newtag(group,payload):
 i=len(tags)//8;datum=(0x9000<<16)|i;a=b.alloc(payload);tags.extend(struct.pack('>HHI',c.groups.index(group),0x9000,a));return datum,a
bitmaps={};shaders={};report={'materials':[],'skipped':[]}
def bitmap(tid):
 if tid in bitmaps:return bitmaps[tid]
 record,ctrl,raw=encode_bitmap_base(source,tid);root=bytearray(c.data[c.tags[8796]['offset']:c.tags[8796]['offset']+0xa4]);root[0x54:0x8c]=bytes(0x38)
 datum,a=newtag('bitm',root);b.put(a+0x60,'III',1,b.alloc(record),0)
 rid=len(resources)//64;rsalt=0x9100;rdatum=(rsalt<<16)|rid;b.put(a+0x8c,'III',1,b.alloc(struct.pack('>II',rdatum,0)),0);b.put(a+0x98,'III',0,0,0)
 compressed=zlib.compress(raw)[2:-4];off=b.append_raw(compressed);page=len(pages)//88;pagebytes=bytearray(88);struct.pack_into('>hBBhhIIII',pagebytes,0,0,1,0,-1,0,off,len(compressed),len(raw),zlib.crc32(raw)^0xffffffff)
 pagebytes[24:84]=b''.join(hashlib.sha1(salt+part).digest() for part in (raw,raw[:1024],raw[-1024:]));struct.pack_into('>hh',pagebytes,84,1,-1);pages.extend(pagebytes)
 li=len(locations)//16;locations.extend(struct.pack('>hhIIhh',page,-1,0,0,-1,-1))
 ro=bytearray(64);ro[:4]=b'bitm';struct.pack_into('>I',ro,12,datum);struct.pack_into('>HBBIIIHhI',ro,16,rsalt,1,2,len(control),64,0xffffffff,1,li,0x20000034)
 control.extend(ctrl);fix=b.alloc(struct.pack('>4I',12,0x40000000,52,0x20000000));interop=b.alloc(struct.pack('>II',0x20000034,2));struct.pack_into('>III',ro,40,2,fix,0);struct.pack_into('>III',ro,52,1,interop,0);resources.extend(ro);bitmaps[tid]=datum;return datum
stock=c.tags[0x21bb]['offset'];sp=c.block(stock+40,132)[0];stex=c.block(sp+16,24)
materials=json.loads((R/'.local/reports/mcc-visual-data.json').read_text())['9178:sbsp']['blocks'];materials=next(v['materials'] for v in materials if v['name']=='Materials');dest=c.block(c.tags[8798]['offset']+0xc0,36)
for i,m in enumerate(materials):
 if m['group']=='rmhg':
  if i==97:
   # Source core options [0,3,1,0,0,0,1] match the retail powerup plasma variant.
   st=s.tags[int(m['datum'],16)&65535]['offset'];spost=s.block(st+40,140)[0]
   dt=c.tags[1611]['offset'];dpost=c.block(dt+40,132)[0]
   assert [s.unpack('h',x)[0] for x in s.block(st+16,2)][:7]==[c.unpack('h',x)[0] for x in c.block(dt+16,2)]
   native=bytearray(c.data[dt:dt+68]);native[28:40]=bytes(12);datum,da=newtag('rmhg',native)
   pp=bytearray(c.data[dpost:dpost+132]);tx=bytearray(b''.join(c.data[x:x+24] for x in c.block(dpost+16,24)))
   names_base=(c.u(0x2b8)+c.u(0x46c))&0xffffffff;names_index=(c.u(0x2c0)+c.u(0x46c))&0xffffffff;lookup={}
   for tag_id,tag in c.tags.items():
    if tag['group']!='bitm' or tag_id>=c.u(0x2b4):continue
    na=names_base+c.u(names_index+tag_id*4);lookup[c.data[na:c.data.find(b'\0',na)].decode(errors='replace')]=(tag['salt']<<16)|tag_id
   for j,texture in enumerate(s.block(spost+16,28)):
    source_id=s.u(texture+12)&65535;name=s.name(source_id)
    target=lookup[name] if name in lookup else bitmap(source_id)
    struct.pack_into('>I',tx,j*24+12,target)
    tx[j*24+18:j*24+20]=s.data[texture+18:texture+20];tx[j*24+20:j*24+22]=s.data[texture+21:texture+23]
   floats=s.block(spost+28,16);assert len(floats)==len(c.block(dpost+28,16))
   constants=b''.join(struct.pack('>4f',*s.unpack('4f',x)) for x in floats)
   struct.pack_into('>III',pp,16,len(tx)//24,b.alloc(tx),0);struct.pack_into('>III',pp,28,len(floats),b.alloc(constants),0)
   b.put(da+40,'III',1,b.alloc(pp),0);b.put(addr(dest[i]),'I',int.from_bytes(b'rmhg','big'));b.put(addr(dest[i])+12,'I',datum)
   report['light_cone']='Source constants and textures with matching retail core shader variant'
   continue
  fallback={2:5177,44:5177,45:1628,46:1643,47:1611}.get(i,5177)
  tag=c.tags[fallback];datum=(tag['salt']<<16)|fallback
  b.put(addr(dest[i]),'I',int.from_bytes(b'rmhg','big'));b.put(addr(dest[i])+12,'I',datum)
  report.setdefault('hologram_approximations',[]).append({'slot':i,'source':m['name'],'retail_tag':fallback})
  continue
 if m['group'] not in ('rmsh','rmtr','rmfl') or not m['textures'] or not m['textures'][0]['name']:
  report['skipped'].append({'slot':i,'name':m['name'],'reason':'special shader'});continue
 texture_slot=1 if m['group']=='rmtr' else 0
 tid=int(m['textures'][texture_slot]['datum'],16)&65535
 if source.info(tid)[0]['format'] not in SUPPORTED_FORMATS:
  report['skipped'].append({'slot':i,'name':m['name'],'reason':'texture format'});continue
 if m['datum'] not in shaders:
  source_tag=s.tags[int(m['datum'],16)&65535]['offset']
  opts=[s.unpack('h',x)[0] for x in s.block(source_tag+16,2)]
  alpha=m['group']=='rmfl' or (m['group']=='rmsh' and len(opts)>2 and opts[2]==1)
  stock=c.tags[392 if alpha else 0x21bb]['offset'];sp=c.block(stock+40,132)[0];stex=c.block(sp+16,24)
  texdatum=bitmap(tid);root=bytearray(c.data[stock:stock+68]);root[28:40]=bytes(12);datum,a=newtag('rmsh',root);pp=bytearray(c.data[sp:sp+132]);tx=bytearray(b''.join(c.data[x:x+24] for x in stex));struct.pack_into('>I',tx,12,texdatum)
  if alpha:struct.pack_into('>I',tx,2*24+12,texdatum)
  # Preserve the retail compiled shader and its normal/detail defaults for this first import.
  source_tag=s.tags[int(m['datum'],16)&65535]['offset'];source_pp=s.block(source_tag+40,140)[0];source_tx=s.block(source_pp+16,28)[texture_slot];transform=s.data[source_tx+22]
  constants=bytearray(b''.join(c.data[x:x+16] for x in c.block(sp+28,16)));source_constants=s.block(source_pp+28,16)
  if transform<len(source_constants):struct.pack_into('>4f',constants,0,*s.unpack('4f',source_constants[transform]))
  struct.pack_into('>III',pp,28,len(constants)//16,b.alloc(constants),0)
  tp=b.alloc(tx);struct.pack_into('>III',pp,16,len(stex),tp,0);pa=b.alloc(pp);b.put(a+40,'III',1,pa,0);shaders[m['datum']]=datum
 b.put(addr(dest[i])+12,'I',shaders[m['datum']]);report['materials'].append({'slot':i,'source':m['name'],'albedo':s.name(tid)})
# Use an authored Slayer start looking toward the arena, not the editor fallback.
source_scenario=next(v['offset'] for v in s.tags.values() if v['group']=='scnr')
source_spawn=s.block(source_scenario+0xb4,0xb4)[100]
spawn_values=s.unpack('6f',source_spawn+8)
player_start=c.block(c.tags[8]['offset']+0x254,24)[0]
b.put(addr(player_start),'5f',*spawn_values[:3],spawn_values[3],0.0)
report['player_start']={'source_scenery_index':100,'position':spawn_values[:3],'yaw':spawn_values[3]}
# Multiplayer uses scenery spawn objects rather than the editor fallback.
retail_scenario_schema=ET.parse(R/'.local/reference/plugins/scnr.xml').getroot()
scenery_field=next(x for x in retail_scenario_schema if x.attrib.get('name')=='Scenery')
scenery_rows=c.block(c.tags[8]['offset']+int(scenery_field.attrib['offset'],0),int(scenery_field.attrib['elementSize'],0))
source_rows=s.block(source_scenario+0xb4,0xb4)
for i,row in enumerate(scenery_rows):
 source_row=source_rows[100+i%8]
 b.put(addr(row)+8,'6f',*s.unpack('6f',source_row+8))
report['multiplayer_spawns']='Existing spawn objects use the eight authored Slayer start positions and orientations.'

# Restore the source's camera exposure/color grading rather than Blackout defaults.
camera_schema=ET.parse(R/'.local/reference/plugins/cfxs.xml').getroot()
source_camera=s.tags[0x1823]['offset'];camera=bytearray(0xe4)
for field in camera_schema:
 kind=field.tag.lower()
 if kind in ('comment','revisions'):continue
 offset=int(field.attrib['offset'],0)
 fmt={'flags16':'H','int16':'h','float32':'f','rangef':'2f','colorf':'3f'}[kind]
 struct.pack_into('>'+fmt,camera,offset,*s.unpack(fmt,source_camera+offset))
camera_datum,_=newtag('cfxs',camera)
b.put(addr(c.tags[8]['offset'])+0x6bc,'I',camera_datum)
report['camera_effects']='Warlock source camera settings, including exposure range 2.3 to 4.3'
for off,stride,payload in ((z+0x58,64,resources),(p+0x18,88,pages),(p+0x30,16,locations)):
 b.put(addr(off),'III',len(payload)//stride,b.alloc(payload),0)
b.put(addr(co),'I',len(control));b.put(addr(co+12),'I',b.alloc(control));b.put(addr(index+8),'II',len(tags)//8,b.alloc(tags))
# Add imported textures to the active BSP's static resource manifest.
manifest=next(x for x in zschema if x.attrib.get('name')=='Static BSP Zone Manifests')
for row in c.block(z+int(manifest.attrib['offset'],0),0x78):
 for field,ids in ((0,range(first_resource,len(resources)//64)),(0x54,range(first_tag,len(tags)//8)),(0x60,range(first_tag,len(tags)//8))):
  ids=list(ids);old=table(row+field,4);needed=(max(ids)+32)//32*4 if ids else len(old);old.extend(bytes(max(0,needed-len(old))))
  for i in ids:
   at=(i//32)*4;v=struct.unpack_from('>I',old,at)[0]|(1<<(i%32));struct.pack_into('>I',old,at,v)
  b.put(addr(row+field),'III',len(old)//4,b.alloc(old),0)
out=b.finish(salt);report.update(bitmap_count=len(bitmaps),shader_count=len(shaders),metadata_used=b.used,output_bytes=len(out),sha256=hashlib.sha256(out).hexdigest());b.close();s.close()
(R/'.local/candidate/lockout.map').write_bytes(out);(R/'.local/reports/material-import.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('materials','skipped')},indent=2));print('Skipped',len(report['skipped']))
