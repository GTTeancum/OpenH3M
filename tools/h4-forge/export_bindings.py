"""Create PC-only H4 marker bindings against current H3 map palettes."""
import hashlib,json,math,re,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from anchor_frames import adapt
from node_frames import resolve_nodes
from source_marker_data import SourceMarkerCache
frames=json.loads((Path(__file__).parent/"anchor_frames.json").read_text())
aliases=json.loads((Path(__file__).parent/'anchor_aliases.json').read_text())
completion=json.loads((Path(__file__).parent/'anchor_completion.json').read_text())
research=ROOT/'work/h4-forge-research'
models=json.loads((research/'ravine-magnets.json').read_text())['data']
source_models={m['name']:m for m in models}
# User decision, 2026-11-12: these four pieces remain available but have no
# magnets. Exclude them before alias/donor resolution, including legacy anchors.
MAGNETS_DISABLED=frozenset(('Radio Antennae','Weapon Holder','Glass Sail','Sniper Nest'))
# All other AFM3 bindings require actual original marker metadata.
missing_sources=[label for label,profile in completion.items()
                 if label not in MAGNETS_DISABLED and profile.get('source') not in source_models]
if missing_sources:
 raise ValueError('AFM3 requires original marker metadata for: '+', '.join(sorted(missing_sources)))
map_paths=sorted((ROOT/'work/dlc/installed-current/0000000000000000').rglob('forge_*.map'))
if not map_paths:
 raise ValueError('No staged Forge maps found; existing marker pack was not changed')
source_cache=SourceMarkerCache(research/'disc2-assets/ca_forge_ravine.map')
key=lambda s:re.sub('[^a-z0-9]','',s.lower())
lookup={key(m['name'].split('\\')[-1].removeprefix('fw_unsc_c_')):m for m in models if 'fw_unsc_c_' in m['name']}
entries=[];report=[]
for path in map_paths:
 c=Cache(path)
 try:
  scenario=next(t['offset'] for t in c.tags.values() if t['group']=='scnr')
  mapid=c.u(scenario+8)
  matg=next(t['offset'] for t in c.tags.values() if t['group']=='matg')
  count,size,refs,data=c.unpack('4I',matg+0x1c4)
  refs=(refs+c.u(0x478))&0xffffffff;data=(data+c.u(0x478))&0xffffffff
  labels={}
  for j in range(count):
   sid,off=c.unpack('II',refs+j*8)
   end=c.data.find(b'\0',data+off,data+size)
   if end>=data+off:labels[sid]=c.data[data+off:end].decode('utf8',errors='strict')
  for row in c.block(scenario+0x20c,48):
   datum=c.u(row+12);label=labels.get(c.u(row+16),'')
   if label in MAGNETS_DISABLED:
    report.append(dict(map=path.name,map_id=mapid,datum=hex(datum),label=label,
                       points=0,status='Magnets omitted by user decision, 2026-11-12'))
    continue
   m=lookup.get(key(aliases.get(label,label)));completed=completion.get(label)
   if not m and not completed:continue
   obj=c.tags[datum&65535]
   if obj['group'] not in ('bloc','scen') or obj['salt']!=datum>>16:raise ValueError('Palette reference invalid')
   h=c.u(obj['offset']+0x40);model=c.u(c.tags[h&65535]['offset']+12);mo=c.tags[model&65535]['offset']
   nodes=c.block(mo+0x30,96)
   frame=dict(completion_profile=label) if completed else frames.get(m['name'].split('\\')[-1])
   if not nodes or (len(nodes)!=1 and not (frame and frame.get('allow_rigid_children'))):continue
   # Quaternion q and -q represent the same rotation. Compare the resolved
   # frame, not raw quaternion components, including on single-node props.
   resolve_nodes([dict(parent=c.unpack('h',n+4)[0],position=c.unpack('3f',n+12),rotation=c.unpack('4f',n+24),
      inverse_scale=c.unpack('f',n+40)[0],inverse_basis=c.unpack('9f',n+44),inverse_position=c.unpack('3f',n+80)) for n in nodes])
   if len(nodes)>1:
    if c.u(c.tags[h&65535]['offset']+0x2c)!=0xffffffff:
     raise ValueError('Reviewed rigid-child bindings require a static animation-free model')
    resolve_nodes([dict(parent=c.unpack('h',n+4)[0],position=c.unpack('3f',n+12),rotation=c.unpack('4f',n+24),
       inverse_scale=c.unpack('f',n+40)[0],inverse_basis=c.unpack('9f',n+44),inverse_position=c.unpack('3f',n+80)) for n in nodes])
   points=completed['points'] if completed else [p for g in m['markers'] if g['group']=='sandbox_magnet' for p in g['points']]
   if not points or len(points)>32 or any(p['node']!=0 for p in points):continue
   if frame and not completed:points=[adapt(p,frame) for p in points]
   native_radius=c.unpack('f',obj['offset']+4)[0]
   native_center=c.unpack('3f',obj['offset']+8)
   # The adapter supplies the object origin to H4, whereas H3's tag sphere
   # can be centered elsewhere. Enclose it about the supplied origin so the
   # broad-phase query cannot discard anchors near an offset piece's edge.
   radius=max(native_radius+math.sqrt(sum(v*v for v in native_center)),
              max(math.sqrt(sum(v*v for v in p['position'])) for p in points))
   phdatum=c.u(c.tags[h&65535]['offset']+0x3c)
   fixed=False
   if phdatum!=0xffffffff:
    ph=c.tags[phdatum&65535]['offset'];bodies=list(c.block(ph+0x58,176))
    fixed=bool(bodies) and all(c.unpack('H',body+0x1a)[0]==5 for body in bodies)
   fixed=fixed and not (c.unpack('H',obj['offset']+2)[0] & (1<<11))
   source_model=source_models[completed['source']] if completed else m
   records=source_cache.records(source_model['tag_index'])
   original=[p for g in source_model['markers'] if g['group']=='sandbox_magnet' for p in g['points']]
   if len(records)!=len(points) or len(original)!=len(points):
    raise ValueError('Original marker metadata/order does not match adapted binding')
   adapted_records=[]
   for raw,prior,point in zip(records,original,points):
    if raw[2]!=prior['node'] or struct.unpack_from('>7f',raw,4)!=tuple(prior['position']+prior['rotation']):
     raise ValueError('Original marker record differs from indexed source point')
    if point['node']!=raw[2]:raise ValueError('Node remap requires explicit metadata adaptation')
    record=bytearray(raw)
    struct.pack_into('>7f',record,4,*point['position'],*point['rotation'])
    adapted_records.append(record)
   entries.append((mapid,datum,radius,points,fixed,adapted_records))
   report.append(dict(map=path.name,map_id=mapid,datum=hex(datum),label=label,h4_source=completed['source'] if completed else m['name'],points=len(points),native_fixed_release=fixed,coordinate_frame=frame,native_bounds=dict(radius=native_radius,center=native_center),editor_origin_radius=radius,status=('Equations applied; gameplay testing is user-owned' if completed else 'Coordinate adaptation present; consult scenery-math-verification.json for proved coverage' if frame else 'Original H4 coordinates; consult scenery-math-verification.json for proved coverage')))
 finally:c.close()
source_cache.close()
out=research/'isolated';payload=bytearray(struct.pack('<4sI',b'AFM3',len(entries)))
for mid,datum,radius,points,fixed,records in entries:
 payload+=struct.pack('<IIfII',mid,datum,radius,len(points),int(fixed))
 for p in points:payload+=struct.pack('<7f',*p['position'],*p['rotation'])
 for record in records:payload+=record
(out/'markers.bin').write_bytes(payload)
(out/'marker-bindings.json').write_text(json.dumps(report,indent=2)+'\n')
print('Bindings:',len(entries),'bytes:',len(payload))
