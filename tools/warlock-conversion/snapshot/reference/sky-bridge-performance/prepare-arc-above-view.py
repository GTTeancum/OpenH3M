"""Prepare a private numeric view above electric_02 placement58; no game assets change."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

REF=Path(__file__).resolve().parent;REPO=REF.parents[4]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path)
run=p.parse_args().run.resolve();run.relative_to(REPO/'work/sky-bridge')
assert not (run/'draws.bin').exists()
path=run/'observer-command.bin';original=path.read_bytes();values=list(struct.unpack('>16f',original))
target=[25.11797332763672,97.47196960449219,4.319040298461914]
position=[target[0],target[1]-3,target[2]+6]
forward=[0,1/math.sqrt(5),-2/math.sqrt(5)]
up=[0,2/math.sqrt(5),1/math.sqrt(5)]
values[:3]=position;values[3:9]=[0]*6;values[10:13]=forward;values[13:16]=up
new=struct.pack('>16f',*values);path.write_bytes(new)
points=[(x,y) for y in (304,320,336) for x in (544,560,576,592,608)]+[(576,352)]
assert len(points)==16
(run/'arc-points.txt').write_text(''.join(f'{x} {y}\n' for x,y in points))
report={'purpose':'View the authored single-sided horizontal arc particles from above with native culling and depth intact.',
    'target':target,'requested_camera_position':position,'forward':forward,'up':up,
    'original_command_sha256':hashlib.sha256(original).hexdigest(),'command_sha256':hashlib.sha256(new).hexdigest(),
    'points':points,'native_captures':0,'map_changes':False,'player_pose_changes':False,
    'limitation':'Intentional diagnostic camera change; not the saved human view.'}
(run/'above-view-preparation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
