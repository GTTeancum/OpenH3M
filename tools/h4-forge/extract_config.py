"""Extract the Forge settings tag from the private retail H4 Ravine cache."""
import contextlib
import io
import json
import runpy
import struct
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RESEARCH=ROOT/'work/h4-forge-research'
with contextlib.redirect_stdout(io.StringIO()):
    g=runpy.run_path(str(RESEARCH/'inspect_anchors.py'))
for i in range(g['nt']):
    group,salt,ptr=struct.unpack_from('>HHI',g['d'],g['off'](g['tp'])+i*8)
    if group==65535 or ptr in (0,0xffffffff) or g['groups'][group]!='forg':
        continue
    offset=g['off'](ptr)
    data=g['d'][offset:offset+0x58]
    if struct.unpack_from('>I',data,0x1c)[0]!=0x193:
        raise RuntimeError('Unexpected Forge marker group')
    out=RESEARCH/'isolated';out.mkdir(exist_ok=True)
    (out/'forge-globals.bin').write_bytes(data)
    report=dict(source='disc2-assets/ca_forge_ravine.map',tag_index=i,offset=offset,
        sha256=hashlib.sha256(data).hexdigest(),byte_count=len(data),
        legacy_80_sha256=hashlib.sha256(data[:0x50]).hexdigest(),marker_group='0x193',
        sensitivities=struct.unpack_from('>5f',data,0x28),
        angle_degrees=struct.unpack_from('>f',data,0x3c)[0],
        score_weight=struct.unpack_from('>f',data,0x40)[0])
    (out/'forge-globals.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    break
else:
    raise RuntimeError('No retail Forge settings tag found')
