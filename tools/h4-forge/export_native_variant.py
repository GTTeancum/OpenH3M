"""Wrap a captured native H3 variant for an ordinary saved-layout reload check."""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/warlock-conversion/snapshot/tools'))
from h3_saved_layout import chunk, fixed

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('snapshot',type=Path)
p.add_argument('output',type=Path)
a=p.parse_args()
source=a.snapshot.resolve(strict=True);output=a.output.resolve()
source.relative_to(ROOT);output.relative_to(ROOT)
b=bytearray(source.read_bytes())
if len(b)!=0xe090:raise ValueError('Not a native H3 map variant')
version,scenario,slots,quotas,mid=struct.unpack_from('>4HI',b,0xf8)
if version!=12 or not 0<=scenario<=slots<=640 or quotas>256 or mid not in (1730,1731):
    raise ValueError('Unexpected native variant header')
placements=[]
for i in range(640):
    at=0x130+i*84
    flags=struct.unpack_from('>H',b,at)[0]
    if i<slots and flags&1 and not flags&32:
        quota=struct.unpack_from('>i',b,at+12)[0]
        if not 0<=quota<quotas:raise ValueError('Placement quota outside table')
        placements.append(dict(slot=i,quota=quota,
            datum=hex(struct.unpack_from('>I',b,0xd34c+quota*12)[0]),
            position=struct.unpack_from('>3f',b,at+16)))
    # Runtime object/helper handles are not portable between game sessions.
    struct.pack_into('>ii',b,at+4,-1,-1)
struct.pack_into('>80i',b,0xdf4c,*([-1]*80))
b[8:40]=fixed('Magnet Result',32,True)
b[40:168]=fixed('Original H4 snap; native H3 placement snapshot.',128)
data=chunk(b'_blf',1,2,b'\xff\xfe'+bytes(34))
data+=chunk(b'chdr',9,2,struct.pack('>HH',12070,0)+b[:0xf8])
data+=chunk(b'mapv',12,1,bytes(4)+b+bytes(4))
data+=chunk(b'_eof',1,1,struct.pack('>IB',len(data),0))
output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(data)
output.with_suffix('.json').write_text(json.dumps(dict(source=str(source),
    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    sha256=hashlib.sha256(data).hexdigest(),map_id=mid,placements=placements,
    limitation='Native format export; reload verification still required.'),indent=2)+'\n')
print(f'Exported {len(placements)} placements, {len(data)} bytes: {output}')
