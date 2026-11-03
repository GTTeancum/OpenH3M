import sys,ctypes,json
from pathlib import Path
sys.path.insert(0,'tools/warlock-conversion/snapshot/tools')
from cache_reader import Cache
from string_ids import StringTable
c=Cache('D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map',True);st=StringTable(c)
dll=ctypes.WinDLL('d3dcompiler_47.dll');fn=dll.D3DDisassemble;fn.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_char_p,ctypes.POINTER(ctypes.c_void_p)];fn.restype=ctypes.c_long
out=Path('work/sky-bridge/source-soft');out.mkdir(exist_ok=True)
report=[]
for tag_id,tag in c.tags.items():
 if tag['group']!='rmhg':continue
 options=[c.unpack('h',x)[0] for x in c.block(tag['offset']+16,2)]
 if not any(options[7:]):continue
 post=c.block(tag['offset']+40,140)[0];template=c.tags[c.u(post+12)&65535]['offset'];pix=c.tags[c.u(template+28)&65535]['offset']
 results=[]
 for idx,row in enumerate(c.block(pix+20,144)):
  at=c.pointer(c.u(row+52));data=bytes(c.data[at:at+c.u(row+40)]);blob=ctypes.c_void_p();hr=fn(data,len(data),0,None,ctypes.byref(blob));assert hr==0,hr
  vtable=ctypes.cast(blob,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
  ptr=ctypes.WINFUNCTYPE(ctypes.c_void_p,ctypes.c_void_p)(vtable[3])(blob);size=ctypes.WINFUNCTYPE(ctypes.c_size_t,ctypes.c_void_p)(vtable[4])(blob)
  assembly=ctypes.string_at(ptr,size).rstrip(b'\0').decode();ctypes.WINFUNCTYPE(ctypes.c_uint,ctypes.c_void_p)(vtable[2])(blob)
  file=out/f'{tag_id}-{idx}.asm';file.write_text(assembly)
  lines=[line for line in assembly.splitlines() if any(n in line for n in ('___soft_','___use_soft_','___distort_')) and 'Offset:' in line]
  results.append(dict(program=idx,sha256=__import__('hashlib').sha256(data).hexdigest(),parameters=lines,all_unused=all('[unused]' in line for line in lines)))
 report.append(dict(material=c.name(tag_id),options=options,programs=results,all_unused=all(r['all_unused'] for r in results)))
Path('work/sky-bridge/mcc-unused-options-proof.json').write_text(json.dumps(report,indent=2))
print([(r['material'],r['all_unused'],len(r['programs'])) for r in report]);c.close()
