"""Inventory every installed Gulch/Cove palette row, independently of bindings.

Name-based source candidates are research leads, never verified mappings.
All geometry/evidence outputs remain in the repository's private work tree.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache

OUT=ROOT/'work/h4-forge-research/isolated'
key=lambda s:re.sub('[^a-z0-9]','',s.lower())
models=json.loads((OUT.parent/'ravine-magnets.json').read_text())['data']
sources={key(m['name'].split('\\')[-1].removeprefix('fw_unsc_c_')):m
         for m in models if 'fw_unsc_c_' in m['name']}
bindings={(r['map'],int(r['datum'],16)):r for r in json.loads((OUT/'marker-bindings.json').read_text())}
aliases={'teleportframe':'teleporterframe','bracelarge':'largebrace',
         'railingsmall':'railing1','railingmedium':'railing2','railinglong':'railing3',
         'corner45degrees':'plat2x245','corner2x2':'plat2x2corner','corner4x4':'plat4x4corner',
         'platformy':'platycross','platformylarge':'platycrosslarge',
         'rampcircularlarge':'rampcirclelarge','rampcircularsmall':'rampcirclesmall',
         'rampstunt':'racestuntramp'}

def labels(c):
 at=next(t['offset'] for t in c.tags.values() if t['group']=='matg')
 count,size,refs,data=c.unpack('4I',at+0x1c4)
 refs=(refs+c.u(0x478))&0xffffffff;data=(data+c.u(0x478))&0xffffffff
 result={}
 for i in range(count):
  sid,offset=c.unpack('II',refs+i*8)
  end=c.data.find(b'\0',data+offset,data+size)
  if end<data+offset:raise ValueError('Unterminated palette label')
  result[sid]=c.data[data+offset:end].decode('utf8')
 return result

def geometry(c,datum):
 obj=c.tags[datum&65535]['offset'];model_datum=c.u(obj+0x40)
 if model_datum==0xffffffff:return None
 model=c.tags[model_datum&65535]['offset'];render_datum=c.u(model+12);physics_datum=c.u(model+0x3c)
 result=dict(model=hex(model_datum),render=hex(render_datum),physics=hex(physics_datum),
             animation=hex(c.u(model+0x2c)),
             bounding_sphere=dict(radius=c.unpack('f',obj+4)[0],center=c.unpack('3f',obj+8)),
             nodes=[],compression_bounds=[],bodies=[],polyhedra=[],shape_lists=[],mopps=[])
 if render_datum!=0xffffffff:
  render=c.tags[render_datum&65535]['offset']
  for row in c.block(render+0x30,96):
   result['nodes'].append(dict(parent=c.unpack('h',row+4)[0],position=c.unpack('3f',row+12),
      rotation=c.unpack('4f',row+24),inverse_scale=c.unpack('f',row+40)[0],
      inverse_basis=c.unpack('9f',row+44),inverse_position=c.unpack('3f',row+80)))
  result['compression_bounds']=[c.unpack('6f',row+4) for row in c.block(render+0x74,44)]
 if physics_datum!=0xffffffff:
  physics=c.tags[physics_datum&65535]['offset']
  for row in c.block(physics+0x58,176):
   result['bodies'].append(dict(node=c.unpack('h',row)[0],motion_type=c.unpack('H',row+0x1a)[0],
      shape_type=c.unpack('H',row+0x58)[0],shape_index=c.unpack('H',row+0x5a)[0]))
  vertices=c.block(physics+0xb8,48);planes=c.block(physics+0xc4,16);vi=pi=0
  for row in c.block(physics+0xac,128):
   nv,nf,np=c.u(row+0x6c),c.u(row+0x64),c.u(row+0x74)
   assert 0<nv<=nf*4 and vi+nf<=len(vertices) and pi+np<=len(planes)
   points=[]
   for at in vertices[vi:vi+nf]:
    xyz=c.unpack('12f',at);points.extend([xyz[i],xyz[i+4],xyz[i+8]] for i in range(4))
   result['polyhedra'].append(dict(vertices=points[:nv],planes=[c.unpack('4f',at) for at in planes[pi:pi+np]],
                                  radius=c.unpack('f',row+0x30)[0]))
   vi+=nf;pi+=np
  assert vi==len(vertices) and pi==len(planes),'Unaccounted polyhedron data'
  children=c.block(physics+0xe8,16);child_offset=0
  for at in c.block(physics+0xdc,80):
   count=c.u(at+0x1c)
   assert child_offset+count<=len(children)
   result['shape_lists'].append([c.unpack('2H',r) for r in children[child_offset:child_offset+count]])
   child_offset+=count
  assert child_offset==len(children),'Unaccounted list children'
  result['mopps']=[c.unpack('2H',at+0x14) for at in c.block(physics+0xf4,32)]
 result['limitation']='Raw local polyhedra: resolve body/shape lists, transforms and render geometry before verification.'
 return result

inventory=[];geometries=[];maps=[]
for name in ('forge_gulch.map','forge_island.map'):
 path=next((ROOT/'work/dlc/installed-current').rglob(name));c=Cache(path)
 try:
  scenario=next(t['offset'] for t in c.tags.values() if t['group']=='scnr');strings=labels(c)
  map_info=dict(name=name,id=c.u(scenario+8),sha256=hashlib.sha256(c.data).hexdigest())
  maps.append(map_info)
  for index,row in enumerate(c.block(scenario+0x20c,48)):
   datum=c.u(row+12);tag=c.tags[datum&65535]
   assert tag['salt']==datum>>16
   label=strings.get(c.u(row+16),'');normalized=key(label);candidate_key=aliases.get(normalized,normalized)
   if candidate_key.startswith('block'):candidate_key='plat'+candidate_key[5:].replace('and','')
   source=sources.get(candidate_key);binding=bindings.get((name,datum));geo=geometry(c,datum)
   reasons=[]
   if not binding:
    if not source:reasons.append('No name-matched H4 source; research required, not an automatic exclusion')
    elif candidate_key!=normalized:reasons.append('Source-name alias missing from current exporter')
    if geo and (len(geo['nodes'])!=1 or any(abs(a-b)>1e-6 for a,b in zip(
       geo['nodes'][0]['position']+geo['nodes'][0]['rotation'],(0,0,0,0,0,0,1)))):
     reasons.append('Current exporter rejects non-single-identity-node models')
   shape_signature=None
   if geo:
    signature={k:geo[k] for k in ('nodes','compression_bounds','bodies','polyhedra','shape_lists','mopps','bounding_sphere','animation')}
    shape_signature=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
    geometries.append(dict(map=name,palette_index=index,datum=hex(datum),label=label,**geo))
   inventory.append(dict(map=name,map_id=map_info['id'],palette_index=index,datum=hex(datum),group=tag['group'],
     label=label,tag_name=c.name(datum&65535),bound=bool(binding),
     current_source=binding['h4_source'] if binding else None,
     candidate_source=source['name'] if source else None,
     current_frame=binding['coordinate_frame'] if binding else None,
     raw_geometry_signature=shape_signature,missing_reasons=reasons,status='unverified'))
 finally:c.close()
report=dict(maps=maps,palette_rows=len(inventory),bound_rows=sum(r['bound'] for r in inventory),
            rows=inventory,limitation='Inventory is not a transform or mating proof; no runtime bindings changed.')
(OUT/'scenery-inventory.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'scenery-geometry.json').write_text(json.dumps(geometries,indent=2)+'\n')
for m in maps:
 rows=[r for r in inventory if r['map']==m['name']]
 print(m['name'],len(rows),'palette rows;',sum(r['bound'] for r in rows),'bound;',
       sum(not r['bound'] and r['candidate_source'] is not None for r in rows),'additional name candidates')
print('No runtime bindings changed. All inventory rows remain unverified.')
