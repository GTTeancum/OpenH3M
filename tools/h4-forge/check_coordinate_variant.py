"""Verify the native record produced by the process-local coordinate fixture."""
import argparse
import json
import math
import struct
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('snapshot',type=Path)
a=p.parse_args()
path=a.snapshot.resolve(strict=True);path.relative_to(ROOT)
data=path.read_bytes()
if len(data)!=0xe090:raise ValueError('Unexpected native variant size')
if struct.unpack_from('>H',data,0xf8)[0]!=12:raise ValueError('Unexpected native variant version')
expected=(-44.125,-197.5,3)
matches=[]
for slot in range(640):
    at=0x130+slot*0x54
    if not struct.unpack_from('>H',data,at)[0]&1:continue
    position=struct.unpack_from('>3f',data,at+16)
    if math.dist(position,expected)>1e-4:continue
    forward=struct.unpack_from('>3f',data,at+28)
    up=struct.unpack_from('>3f',data,at+40)
    if math.dist(forward,(0,1,0))>1e-4 or math.dist(up,(0,0,1))>1e-4:
        raise ValueError(f'Slot {slot}: original coordinate orientation not retained')
    matches.append(dict(slot=slot,position=position,forward=forward,up=up))
if len(matches)!=1:raise ValueError(f'Expected one precise placement, found {len(matches)}')
print(json.dumps(dict(result='PASS',native_version=12,native_size=len(data),placements=matches,
    limitation='Snapshot verification only; independent reload and physical console tests remain separate.'),indent=2))
