import hashlib, json, struct, sys
from pathlib import Path
repo=Path.cwd()
sys.path.insert(0,str(repo/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
c=Cache(repo/'work/sky-bridge/payload-32/sky_bridge.map')
t=c.tags[225]['offset'];p=c.tags[c.u(t+28)&65535]['offset']
out=repo/'work/sky-bridge/fabric-cutout-build'
entries=[list(c.data[x:x+2]) for x in c.block(p+4,2)]
rows=[]
for i,row in enumerate(c.block(p+20,80)):
 info=c.pointer(c.u(row+76)); debug=info+40
 magic,dsize,csize=c.unpack('III',debug)
 code=c.pointer(c.u(info+16))
 raw=bytes(c.data[debug:debug+dsize])+bytes(c.data[code:code+csize])
 (out/f'original-{i}.bin').write_bytes(raw)
 rows.append(dict(index=i,entries=[j for j,(first,count) in enumerate(entries) if count and first==i],gprs=c.u(row+72),header=list(struct.unpack('>7I',raw[:28])),sha256=hashlib.sha256(raw).hexdigest()))
(out/'programs.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows))
c.close()
