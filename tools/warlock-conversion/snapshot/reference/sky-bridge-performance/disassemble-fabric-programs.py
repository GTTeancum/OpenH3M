import hashlib,json,os,struct,subprocess
from pathlib import Path
repo=Path.cwd();out=repo/'work/sky-bridge/fabric-cutout-build'
env=dict(os.environ,TEMP=str(repo/'.local/build-temp'),TMP=str(repo/'.local/build-temp'))
report=[]
for p in json.loads((out/'programs.json').read_text()):
 i=p['index'];tool=out/'shader-tool.exe'
 for mode,src,dst in [('disassemble',f'original-{i}.bin',f'original-{i}.asm'),('assemble',f'original-{i}.asm',f'roundtrip-{i}.bin')]:
  run=subprocess.run([str(tool),mode,str(out/src),str(out/dst)],cwd=repo,env=env,capture_output=True)
  if run.returncode:raise RuntimeError(run.stdout+run.stderr)
 a=(out/f'original-{i}.bin').read_bytes();b=(out/f'roundtrip-{i}.bin').read_bytes()
 # The serialized physical shader includes code, literal values and metadata;
 # equality is useful but mismatch is not interpreted as equivalence.
 da=struct.unpack_from('>I',a,4)[0];db=struct.unpack_from('>I',b,4)[0]
 asm=(out/f'original-{i}.asm').read_text().rstrip('\x00')
 row=dict(index=i,entries=p['entries'],physical_equal=a[da:]==b[db:],physical_sizes=[len(a)-da,len(b)-db],tail=asm[asm.rfind('    alloc'):].split('// PDB')[0],literals=[x for x in asm.splitlines() if x.startswith('def ')],kill=[x for x in asm.splitlines() if 'kill' in x])
 report.append(row)
(out/'roundtrip-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
