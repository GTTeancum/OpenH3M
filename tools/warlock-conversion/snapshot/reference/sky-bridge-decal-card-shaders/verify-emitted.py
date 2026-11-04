"""Compare final cache shader payloads and reflection with audited compiler outputs."""
import sys,json,hashlib,re
from pathlib import Path
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
from string_ids import StringTable
result=[]
for cache_path in ('work/sky-bridge/zanzibar-31.map',):
 c=Cache(cache_path);strings=StringTable(c)
 for profile,material in [('decal-card',json.loads(Path(f'work/sky-bridge/candidate-31-decal-card-{tid}-verification.json').read_text())['target_material']) for tid in (12453,12458,12579,12591)]:
  directory=Path('work/sky-bridge')/(profile+'-native-01')
  manifest={x['entry']:x for x in json.loads((directory/'compilation.json').read_text())['programs']}
  plan=json.loads((directory/'route-plan.json').read_text())
  post,=c.block(c.tags[material]['offset']+40,132)
  template=c.tags[c.u(post+12)&65535]['offset']
  pixel=c.tags[c.u(template+28)&65535]['offset']
  entries=c.block(pixel+4,2);programs=c.block(pixel+20,80)
  assert len(programs)==12
  for program in plan['programs']:
   entry=program['entry'];index,count=c.unpack('BB',entries[entry])
   assert count==1 and index==program['shader']
   row=programs[index];info=c.pointer(c.u(row+76))
   debug_size,code_size=c.unpack('II',info+44)
   code=c.pointer(c.u(info+16))
   assert info+40+debug_size<=len(c.data) and code+code_size<=len(c.data)
   raw=bytes(c.data[info+40:info+40+debug_size])+bytes(c.data[code:code+code_size])
   expected=(directory/(program['name']+'-ps.bin')).read_bytes()
   digest=hashlib.sha256(raw).hexdigest()
   assert raw==expected and digest==manifest[entry]['sha256']
   reflection=[dict(name=strings.text(c.u(r)),register=c.unpack('H',r+4)[0],count=c.data[r+6],set=c.data[r+7]) for r in c.block(row+40,8)]
   expected_reflection=[dict(v,name=v['name'].lower()) for v in program['registers']]
   assert reflection==expected_reflection
   assembly=(directory/(program['name']+'-ps.asm')).read_text()
   gprs=int(re.search(r'PsMaxReg=(\d+)',assembly).group(1))+1
   assert c.u(row+72)==gprs
   result.append(dict(cache=cache_path,profile=profile,entry=entry,shader=index,sha256=digest,reflection_exact=True,gprs=gprs))
 c.close()
report=dict(program_checks=len(result),checks=result,limitation='Bytecode identity and metadata checks; no visual or runtime execution proof.')
Path('work/sky-bridge/candidate-31-decal-card-emitted-programs.json').write_text(json.dumps(report,indent=2))
print('Verified',len(result),'emitted program payloads, reflection tables and register counts in candidate 31.')
