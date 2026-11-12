"""Record original editor transition provenance and verify mode event strings."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'work/h4-forge-research'
locations = {'8244BE08':25,'82449A60':173,'8244BEC8':18,'8244F8A8':204,
             '8244FC48':96,'8244FFE8':192,'8246B098':144,'823C9B48':256,
             '8244C580':265,'8244C6D8':8,'82372010':208,
             '82939B70':43,'82939C98':150}
bodies = {}
functions = {}
for name,number in locations.items():
    file = f'halo4_recomp.{number}.cpp'
    text = (R/'generated'/file).read_text()
    marker = f'DEFINE_REX_FUNC(sub_{name}) {{'
    start = text.index(marker)
    body = marker + text[start+len(marker):].split('DEFINE_REX_FUNC(',1)[0]
    body = body.strip()
    bodies[name] = body
    functions[name] = dict(file=file,line=text.count('\n',0,start)+1,
        sha256=hashlib.sha256(body.encode()).hexdigest(),
        calls=sorted(set(re.findall(r'\b(sub_[0-9A-F]+)\(ctx, base\)',body))),
        indirect='REX_CALL_INDIRECT' in body)
for instruction in ['bl 0x82449a60','bl 0x8244f8a8','bl 0x8244fc48',
                    'bl 0x8244bec8','bl 0x82451500']:
    assert '// '+instruction in bodies['8244BE08']
assert '// stw r5,20(r11)' in bodies['8244BEC8']
image = (R/'h4-image.bin').read_bytes()
events = {}
for address,expected in [(0x821312c8,'forge_mode_play'),(0x821312d8,'forge_mode_edit')]:
    offset = address-0x82000000
    actual = image[offset:image.index(b'\0',offset)].decode('ascii')
    assert actual == expected
    events[hex(address)] = actual
report = dict(scope='Static source audit; not native transition or full gameplay verification.',
              functions=functions,original_event_names=events,
              state_field='editor +0x14: 0 play, 1 edit',
              open_boundaries=['Input producer and transition authorization',
                               'Original object creation and control reassignment adapters',
                               'Session type 4 semantics',
                               'Transform, collision and attachment restoration',
                               'Multiple local players and replication'])
(R/'isolated/full-re-transition.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'Recorded {len(functions)} original functions and verified edit/play event strings from image.')
