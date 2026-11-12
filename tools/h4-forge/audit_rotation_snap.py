"""Extract the original rotation quantizer for isolated behavior checks."""
import hashlib
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'work/h4-forge-research'
text = (R/'generated/halo4_recomp.282.cpp').read_text()
name = 'sub_82451A38'
body = 'DEFINE_REX_FUNC('+name+') {' + text.split('DEFINE_REX_FUNC('+name+') {',1)[1].split('DEFINE_REX_FUNC(',1)[0]
body = body.strip()
assert 'REX_CALL_INDIRECT' not in body
dependencies = sorted(set(re.findall(r'\b((?:sub_|__save|__rest)\w+)\(ctx, base\)',body)))
extracted = json.loads((R/'isolated/extraction.json').read_text())
assert set(dependencies) <= set(extracted['functions'])
image = (R/'h4-image.bin').read_bytes()
table = struct.unpack_from('>6i',image,0x833f195c-0x82000000)
assert table == (0,90,45,30,15,5)
constants = {hex(a):struct.unpack_from('>f',image,a-0x82000000)[0]
             for a in [0x821289e4,0x82128a08,0x82128a20,0x82128a44,0x82128a54]}
assert constants['0x82128a08'] == 0.5 and constants['0x82128a44'] == -1
out = R/'isolated'
(out/'rotation_original.cpp').write_text(
    '#include "forge_original.h"\n#define DEFINE_REX_FUNC(name) void name(PPCContext& ctx, uint8_t* base)\n'
    'namespace h4_forge_original {\n'+('' if name in extracted['functions'] else body)+'\n}\n')
(out/'full-re-rotation.json').write_text(json.dumps(dict(
    function=name, source='halo4_recomp.282.cpp', sha256=hashlib.sha256(body.encode()).hexdigest(),
    dependencies=dependencies, angle_table_address='0x833f195c', degrees=table,
    constants=constants, scope='Unchanged original quantizer; not full editor verification.'),indent=2)+'\n')
print('Extracted unchanged original rotation quantizer; all dependencies already available; image table verified.')
