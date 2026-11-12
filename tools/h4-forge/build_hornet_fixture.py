"""Native H3 Hornet layout with the player beside the pilot seat; no asset edits."""
import copy
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from h3_saved_layout import write
report=json.loads((ROOT/'work/forge-world/variants/layouts/hemorrhage.json').read_text())
layout=copy.deepcopy(report['layout'])
map_path=next((ROOT/'work/dlc/installed-current').rglob('forge_gulch.map'))
if hashlib.sha256(map_path.read_bytes()).hexdigest()!=report['map_sha256']:
    raise ValueError('Fixture base differs from verified layout base')
index=next(i for i,q in enumerate(layout['quotas']) if q.get('name','').endswith('vehicles\\hornet\\hornet'))
vehicle=copy.deepcopy(next(o for o in layout['objects'] if o['quota']==index))
quota=copy.deepcopy(layout['quotas'][index]);quota['count']=1
# Use the native Bank test's verified player spawn. The old Falcon-derived
# aircraft location doesn't establish a valid adjacent infantry spawn.
vehicle.update(position=[-47.56380081176758,-196.8840057373047,3.0],
               forward=[0.,1.,0.],up=[0.,0.,1.])
spawns=[]
for i,q in enumerate(layout['quotas']):
    if q.get('name','').endswith(('slayer_initial_spawn_point','spawning\\respawn_point')):
        obj=copy.deepcopy(next(o for o in layout['objects'] if o['quota']==i))
        spawn_quota=copy.deepcopy(q);spawn_quota['count']=1
        obj.update(position=[-49.56380081176758,-195.6840057373047,1.4517199993133545],
                   forward=[1.,0.,0.],up=[0.,0.,1.])
        spawns.append((obj,spawn_quota))
assert len(spawns)==2
vehicle.update(quota=0,spawn_time=0)
layout.update(name='Hornet Depth',description='Private native effect visibility diagnostic.',
              unique_id=0x48464f43434c5531,objects=[vehicle],quotas=[quota])
for obj,q in spawns:
    obj['quota']=len(layout['quotas']);layout['quotas'].append(q);layout['objects'].append(obj)
out=ROOT/'work/h4-forge-research/isolated/hornet-fixture.bin'
data=write(layout);out.write_bytes(data)
out.with_suffix('.json').write_text(json.dumps(dict(layout=layout,map_sha256=report['map_sha256'],
    sha256=hashlib.sha256(data).hexdigest()),indent=2)+'\n')
print(f'{out}: Hornet plus native initial/respawn points')
