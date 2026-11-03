import sys,json,subprocess,os
from pathlib import Path
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
from string_ids import StringTable
c=Cache('C:/X360/ISOs/H3M/maps/sandbox.map');st=StringTable(c)
r=next(t['offset'] for i,t in c.tags.items() if t['group']=='rmdf' and c.name(i)==r'shaders\halogram');g=c.tags[c.u(r+80)&65535]['offset'];rows=c.block(g+16,80);out=Path('work/sky-bridge/soft-native-01');report=[]
for typ,v in enumerate(c.block(g,12)):
 entries=c.block(v,16)
 if not entries:continue
 for entry in (9,14,17):
  p=entries[entry];idx=c.u(p+12);deps=c.block(p,16)
  report.append(dict(type=typ,entry=entry,default=idx,dependencies=[dict(category=c.u(d),options=[c.u(x) for x in c.block(d+4,4)]) for d in deps]))
  if idx==0xffffffff:continue
  row=rows[idx];at=c.pointer(c.u(row+76));debug=at+0x368;ds,cs=c.unpack('II',debug+4);code=c.pointer(c.u(at+16));binary=out/f'native-{typ}-{entry}.bin';binary.write_bytes(c.data[debug:debug+ds]+c.data[code:code+cs]);env=dict(os.environ,TEMP=str(Path('.local/build-temp').resolve()),TMP=str(Path('.local/build-temp').resolve()))
  subprocess.run(['work/powerhouse/shader-toolchain/disassemble.exe',str(binary),str(binary.with_suffix('.asm'))],check=True,env=env,timeout=30)
  report[-1]['registers']=[dict(name=st.text(c.u(x)),register=c.unpack('H',x+4)[0],count=c.data[x+6],set=c.data[x+7]) for x in c.block(row+40,8)]
(out/'native-vertex-table.json').write_text(json.dumps(report,indent=2));print(json.dumps(report[:9],indent=2));c.close()
