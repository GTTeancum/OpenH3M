import argparse,array,collections,hashlib,json,struct
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--trace-dir',type=Path,default=Path('work/sky-bridge/draw-trace-20261103-200444'))
root=parser.parse_args().trace_dir
root.resolve().relative_to(Path(__file__).resolve().parents[5])
prefixes=json.loads((root/'geometry-prefix-matches.json').read_text())['matches']
shader_rows=json.loads((root/'program-slice-matches.json').read_text())
shader_materials={r['shader']:{m['id'] for s in r['matches'] for p in s['programs'] for t in p['templates'] for m in t['materials']} for r in shader_rows}
shader_fields={r['shader']:{field['name']:field for s in r['matches'] for p in s['programs'] for field in p['reflection'] if field['register_set']==2 and field['count']<=4} for r in shader_rows}
shader_all_floats={r['shader']:{field['name']:field for s in r['matches'] for p in s['programs'] for field in p['reflection'] if field['register_set']==2} for r in shader_rows}
shader_samplers={r['shader']:{field['name']:field for s in r['matches'] for p in s['programs'] for field in p['reflection'] if field['register_set']==3} for r in shader_rows}
addresses=collections.defaultdict(dict)
for p in prefixes:
 for e in p['matches']:
  if e['index_count']*2==p['length']: addresses[p['address']][(e['owner'],e['mesh'],e['part'])]=e
vertex_hashes=collections.defaultdict(set)
with (root/'draws.bin').open('rb') as f:
 while h:=f.read(8):
  kind,size=struct.unpack('<II',h);data=f.read(size)
  if kind==6: prefix_sequence,prefix_address,prefix_length,prefix_size=struct.unpack('<4Q',data)
  elif kind==7: vertex_hashes[prefix_address].add(hashlib.sha256(data).hexdigest())
regs=array.array('I',[0])*0x5003; groups={}; cache={}; mapped=0; prefix_only=0
with (root/'draws.bin').open('rb') as f:
 while h:=f.read(8):
  kind,size=struct.unpack('<II',h);data=f.read(size)
  if kind==1:
   seq,frame,ns,vs,ps,primitive,count,addr,length,fmt,endian=struct.unpack('<11Q',data)
  elif kind==2:
   for index,value in struct.iter_unpack('<II',data):regs[index]=value
  elif kind==5:
   vertex_address=regs[0x48be]&0xfffffffc
   key=(addr,count,ps,vertex_address)
   if key not in cache:
    candidates=[e for e in addresses.get(addr,{}).values() if e['index_count']==count and e['target_material'] in shader_materials.get(ps,set())
      and vertex_hashes.get(vertex_address)=={e['vertex_prefix_sha256']}]
    cache[key]=candidates[0] if len(candidates)==1 else None
   geometry=cache[key]
   if not geometry:continue
   model=regs[0x4000+16*4:0x4000+19*4].tobytes().hex() if geometry['vertex_format']==2 else 'world-space vertices'
   mapped+=1;key=(geometry['owner'],geometry['mesh'],geometry['part'],ps,model)
   if key not in groups:groups[key]={'geometry':geometry,'ps':ps,'model':model,'vertex_constants_0_18':regs[0x4000:0x4000+19*4].tobytes().hex(),'frames':collections.Counter(),'lighting':collections.defaultdict(set),'textures':collections.defaultdict(set),'cameras':collections.defaultdict(set),'states':collections.defaultdict(set),'parameters':{name:collections.defaultdict(set) for name in shader_fields[ps]},'samplers':{name:collections.defaultdict(set) for name in shader_samplers[ps]}}
   g=groups[key];g['frames'][frame]+=1
   if geometry['mesh'] in (183,184):
    if 'pipeline_registers' not in g:
     g['pipeline_registers']={}
     g['all_float_parameters']={name:collections.defaultdict(set) for name in shader_all_floats[ps]}
    for ri in list(range(0x2000,0x2400))+list(range(0x4900,0x4928)):
     g['pipeline_registers'].setdefault(hex(ri),collections.defaultdict(set))[hex(regs[ri])].add(frame)
    for name,field in shader_all_floats[ps].items():
     start=0x4400+field['register']*4
     g['all_float_parameters'][name][regs[start:start+field['count']*4].tobytes().hex()].add(frame)
   g['lighting'][regs[0x4400+210*4:0x4400+213*4].tobytes().hex()].add(frame)
   g['textures'][hashlib.sha256(regs[0x4800:0x48c0].tobytes()).hexdigest()].add(frame)
   g['cameras'][regs[0x4000+7*4:0x4000+8*4].tobytes().hex()].add(frame)
   g['states'][regs[0x2200:0x2240].tobytes().hex()].add(frame)
   for name,field in shader_fields[ps].items():
    start=0x4400+field['register']*4
    g['parameters'][name][regs[start:start+field['count']*4].tobytes().hex()].add(frame)
   for name,field in shader_samplers[ps].items():
    start=0x4800+field['register']*6
    g['samplers'][name][regs[start:start+field['count']*6].tobytes().hex()].add(frame)
output=[]
for g in groups.values():
 g['frames']=dict(g['frames'])
 for field in ('lighting','textures','cameras','states'):g[field]={k:sorted(v) for k,v in g[field].items()}
 g['parameters']={name:{k:sorted(v) for k,v in values.items()} for name,values in g['parameters'].items()}
 g['samplers']={name:{k:sorted(v) for k,v in values.items()} for name,values in g['samplers'].items()}
 if 'pipeline_registers' in g:
  g['pipeline_registers']={name:{k:sorted(v) for k,v in values.items()} for name,values in g['pipeline_registers'].items()}
  g['all_float_parameters']={name:{k:sorted(v) for k,v in values.items()} for name,values in g['all_float_parameters'].items()}
 output.append(g)
(root/'geometry-state.json').write_text(json.dumps({'uniquely_attributed_submitted_draws':mapped,'groups':output},indent=2)+'\n')
print('attributed submitted draws',mapped,'mesh-part shader groups',len(output))
for g in output:
 if len(g['lighting'])>1:
  print(g['geometry']['mesh'],g['geometry']['part'],g['geometry']['material'],'frames',len(g['frames']),'lighting variants',len(g['lighting']),[(struct.unpack('<12f',bytes.fromhex(k)),len(v)) for k,v in g['lighting'].items()][:4])
