"""Private prototype: replace material 9821 hardware alpha testing with shader discard.

The Xbox assembler supplies validated scheduling/header metadata. Original
ALU/fetch words are restored verbatim to avoid its disassembly round-trip
normalization of otherwise unused instruction fields.
"""
import hashlib,json,os,re,struct,subprocess,sys
from pathlib import Path
repo=Path.cwd();out=repo/'work/sky-bridge/fabric-cutout-build'
sys.path.insert(0,str(repo/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from map_builder import MapBuilder
from cache_registry import CacheRegistry
from build_scenario_checkpoint import resource_salt
env=dict(os.environ,TEMP=str(repo/'.local/build-temp'),TMP=str(repo/'.local/build-temp'))
sha=lambda b:hashlib.sha256(b).hexdigest()
def command(mode,src,dst):
 p=subprocess.run([str(out/'shader-tool.exe'),mode,str(src),str(dst)],cwd=repo,env=env,capture_output=True)
 (dst.with_suffix(dst.suffix+'.log')).write_bytes(p.stdout+p.stderr)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
def cf_words(code):
 result=[]
 # The first EXEC names the start of ALU/fetch storage in all twelve inputs.
 first=struct.unpack_from('>I',code)[0]&4095
 for a,b,c in struct.iter_unpack('>III',code[:first*12]):
  result.extend([a|((b&65535)<<32),(b>>16)|(c<<16)])
 return result
programs=[]
for p in json.loads((out/'programs.json').read_text()):
 i=p['index'];raw=(out/f'original-{i}.bin').read_bytes()
 asm=(out/f'original-{i}.asm').read_text().rstrip('\x00')
 # c252.w is part of the existing native literal upload and is unused by
 # every original instruction, including the debug program's branches.
 for line in asm.splitlines():
  if line.startswith('def '):continue
  for swizzle in re.findall(r'\bc252(?:\.([xyzw]+))?\b',line):
   assert swizzle and 'w' not in swizzle,(i,line)
 literal=re.search(r'^def c252, (.*)$',asm,re.M)
 values=literal.group(1).split(', ');assert values[3]=='0'
 values[3]='0.501960814' # exact witnessed RB_ALPHA_REF = 0x3f008081
 updated=asm[:literal.start(1)]+', '.join(values)+asm[literal.end(1):]
 assert updated.count('    exece\n')==1
 alpha='r0.w' if i==0 else 'c255.z' if i==10 else 'r1.w'
 # Entry 13 (debug) writes constant-zero color-0 alpha. Preserve its
 # hardware-alpha-test rejection using its existing literal zero.
 if i==10:assert 'def c255, 1, 0.699999988, 0, 0.300000012' in asm and 'mov oC0.xyz0' in asm
 elif i==0:assert 'movs oC0.w, r0.w' in asm
 else:assert 'mov oC0, r1' in asm
 updated=updated.replace('    exece\n',f'    exece\n    kill_gt r0._, c252.w, {alpha}\n')
 (out/f'cutout-{i}.asm').write_text(updated)
 command('assemble',out/f'cutout-{i}.asm',out/f'assembled-{i}.bin')
 new=bytearray((out/f'assembled-{i}.bin').read_bytes())
 da=struct.unpack_from('>I',raw,4)[0];db=struct.unpack_from('>I',new,4)[0]
 a=raw[da:];b=new[db:]
 expected=bytearray(a[:64]);struct.pack_into('>I',expected,12,0x3f008081)
 assert b[:64]==expected,(i,'literal upload changed')
 code=a[64:-12];nc=bytes(b[64:-12]);oldcf=cf_words(code);newcf=cf_words(nc)
 assert len(oldcf)==len(newcf) and len(nc)==len(code)+12
 end=[j for j,v in enumerate(oldcf) if v>>44==2];assert len(end)==1
 cf=end[0];v=oldcf[cf];at=v&4095;count=(v>>12)&7
 assert count<=5 and (v>>16)&4095==0 and at*12+count*12==len(code)
 # No control-flow change except executing one extra ALU in the final EXEC.
 expectedcf=list(oldcf);expectedcf[cf]+=1<<12
 # The official text round trip also normalizes unused loop condition bits.
 # Keep the source control flow verbatim apart from the final ALU count.
 assert all((x&4095)==(y&4095) for x,y in zip(oldcf,newcf)),(i,'address relocation')
 for j in range(0,len(expectedcf),2):
  x,y=expectedcf[j:j+2]
  struct.pack_into('>III',new,db+64+j//2*12,x&0xffffffff,((x>>32)&65535)|((y&65535)<<16),y>>16)
 assert cf_words(bytes(new[db+64:-12]))==expectedcf
 first=(oldcf[0]&4095)*12
 # Preserve every original fetch and ALU byte, before and after insertion.
 new[db+64+first:db+64+at*12]=code[first:at*12]
 new[db+64+(at+1)*12:db+64+len(nc)]=code[at*12:]
 patched=bytes(new);assert patched[db+64+first:db+64+at*12]==code[first:at*12]
 assert patched[db+64+(at+1)*12:db+64+len(nc)]==code[at*12:]
 (out/f'cutout-{i}.bin').write_bytes(patched)
 command('disassemble',out/f'cutout-{i}.bin',out/f'cutout-{i}-verified.asm')
 verified=(out/f'cutout-{i}-verified.asm').read_text().rstrip('\x00')
 # Official disassembler sees exactly the intended original assembly plus
 # one literal change and one discard; ignore source-symbol hints only.
 normalize=lambda s:[x.strip() for x in s.split('// PDB hint')[0].splitlines() if x.strip()]
 assert normalize(verified)==normalize(updated),(i,'disassembly differs')
 # Official assembler validates the restored bytecode's disassembly too.
 command('assemble',out/f'cutout-{i}-verified.asm',out/f'validated-{i}.bin')
 programs.append(dict(index=i,entries=p['entries'],alpha=alpha,original_sha256=sha(raw),sha256=sha(patched),gprs=p['gprs'],original_instructions_preserved=True,control_flow_change=dict(index=cf,count_before=count,count_after=count+1),literal=dict(register=252,component=3,bits='0x3f008081'),discard_instruction=patched[db+64+at*12:db+64+(at+1)*12].hex()))
basis=repo/'work/sky-bridge/payload-32/sky_bridge.map'
assert sha(basis.read_bytes())=='311ad88580c5e099546c029f07f93976c346a8bb9bf9b12c1d48f72f5e0c3e5d'
destination=repo/'work/sky-bridge/payload-35/sky_bridge.map'
assert not destination.exists()
destination.parent.mkdir(exist_ok=True)
b=MapBuilder(basis,0x200000);r=CacheRegistry(b,resource_salt('C:/X360/ISOs/H3M/default.xex'));c=b.cache
template=bytearray(c.data[c.tags[225]['offset']:c.tags[225]['offset']+132]);pixel_id=struct.unpack_from('>I',template,28)[0]&65535
assert pixel_id==227
pixel=bytearray(c.data[c.tags[pixel_id]['offset']:c.tags[pixel_id]['offset']+32]);rows=[bytearray(c.data[x:x+80]) for x in c.block(c.tags[pixel_id]['offset']+20,80)]
assert len(rows)==12
for p,row in zip(programs,rows):
 raw=(out/f"cutout-{p['index']}.bin").read_bytes();ds=struct.unpack_from('>I',raw,4)[0]
 info=bytearray(40);struct.pack_into('>I',info,16,b.alloc(raw[ds:]));info.extend(raw[:ds])
 # Reflection, register count and all native material routes stay unchanged.
 struct.pack_into('>I',row,76,b.alloc(info))
struct.pack_into('>III',pixel,20,len(rows),b.alloc(b''.join(rows)),0)
pix,_=r.newtag('pixl',pixel);struct.pack_into('>I',template,28,pix)
tm,_=r.newtag('rmt2',template)
material=9821;post,=c.block(c.tags[material]['offset']+40,132)
assert c.u(post+12)&65535==225 and c.u(post+108)==2 and c.u(post+104)==0
b.put(r.address(post+12),'I',tm);b.put(r.address(post+108),'I',0)
r.finalize();payload=b.finish(r.salt);destination.write_bytes(payload)
report=dict(candidate=35,basis_sha256=sha(basis.read_bytes()),map_sha256=sha(payload),material=material,source_material=4299,original_template=225,private_template=tm,private_pixel=pix,programs=programs,scope='Only material 9821; original donor tags and other users unchanged',runtime_verified=False)
(out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='programs'}))
b.close()
