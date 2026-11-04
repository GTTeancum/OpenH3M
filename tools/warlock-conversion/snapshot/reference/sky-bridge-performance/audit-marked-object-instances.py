import json,re,sys
from pathlib import Path
repo=Path(__file__).resolve().parents[5]
assert Path.cwd().resolve()==repo
sys.path.insert(0,str(repo/'tools/warlock-conversion/snapshot/tools'))
from cache_reader import Cache
from resource_reader import Resource
from string_ids import StringTable
c=Cache(repo/'work/sky-bridge/payload-36/sky_bridge.map')
strings=StringTable(c)
bsp=c.tags[9225]['offset']
collision=Resource(c,c.u(bsp+0x37c))
definition_base=collision.fix[collision.root+16]&0x1fffffff
instances=[]
for i,row in enumerate(c.block(bsp+0x1b0,120)):
    definition,flags=c.unpack('hH',row+52)
    mesh,compression=collision.unpack('HH',definition_base+definition*184+176)
    if mesh not in (121,357):continue
    instances.append(dict(index=i,name=strings.text(c.u(row+84)),definition=definition,
        mesh=mesh,compression=compression,flags=hex(flags),position=c.unpack('3f',row+40),
        transform=c.unpack('13f',row)))
base,=c.block(c.tags[9894]['offset']+4,436)
mesh_rows=c.block(base+0x134,76)
buckets=[]
for i,mesh in enumerate(mesh_rows):
    for row in c.block(mesh+52,16):
        mi,definition=c.unpack('hh',row)
        refs=[c.unpack('h',r)[0] for r in c.block(row+4,2)]
        if mi in (121,357) or any(v['index'] in refs for v in instances):
            buckets.append(dict(owner_mesh=i,mesh=mi,definition=definition,instances=refs))
c.close()
hits=[]
for path in (repo/'halo3mp/generated/default').glob('*.cpp'):
    text=path.read_text();lines=text.splitlines();function=''
    for i,line in enumerate(lines):
        if line.startswith('DEFINE_REX_FUNC('):function=line
        m=re.search(r'// lhz (r\d+),54\((r\d+)\)',line)
        if not m:continue
        reg=m[1]
        following='\n'.join(lines[i+1:i+22])
        if re.search(r'rlwinm\.? \w+,'+reg+r',(0,(25,25|26,26)|2[67],31,31)',following):
            hits.append(dict(path=str(path.relative_to(repo)),line=i+1,function=function,
                context='\n'.join(lines[max(0,i-14):i+24])))
out=dict(instances=instances,buckets=buckets,native_flag_tests=hits,
    limitation='An offset/mask match alone does not identify a BSP-instance flag consumer. Verify base pointer provenance.')
(repo/'work/sky-bridge/marked-object-review/instance-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(instances=instances,buckets=buckets,native_flag_tests=hits),indent=2))
