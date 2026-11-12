"""Record original H4 variant codec provenance without claiming round-trip parity."""
import hashlib
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'work/h4-forge-research'
records = {}
for address, number in {'823C3930':186,'823C3D30':215,'823C97D8':170,'823C9A08':81,'823C7530':174,'823C7C88':235}.items():
    path=R/f'generated/halo4_recomp.{number}.cpp'
    text=path.read_text();marker=f'DEFINE_REX_FUNC(sub_{address}) {{'
    start=text.index(marker)
    body=(marker+text[start+len(marker):].split('DEFINE_REX_FUNC(',1)[0]).strip()
    records[address]={'source':path.name,'line':text.count('\n',0,start)+1,
        'sha256':hashlib.sha256(body.encode()).hexdigest(),
        'calls':re.findall(r'\b(sub_[0-9A-F]+)\(ctx, base\)',body)}
    if address in ('823C3930','823C3D30'):
        assert '// li r30,651' in body and '// addi r29,r29,76' in body
    if address=='823C3D30':
        assert '// cmpwi cr6,r10,50' in body and '// cmpwi cr6,r10,256' in body
path=ROOT/'halo3mp/generated/default/halo3mp_recomp.25.cpp'
text=path.read_text();marker='DEFINE_REX_FUNC(sub_821E01E0) {'
start=text.index(marker)
body=(marker+text[start+len(marker):].split('DEFINE_REX_FUNC(',1)[0]).strip()
assert all(x in body for x in ('// cmpwi cr6,r11,640', '// cmpwi cr6,r11,256', '// addi r31,r31,84'))
records['H3_821E01E0']={'source':str(path.relative_to(ROOT)),
    'line':text.count('\n',0,start)+1,
    'sha256':hashlib.sha256(body.encode()).hexdigest(),
    'calls':re.findall(r'\b(sub_[0-9A-F]+)\(ctx, base\)',body)}
(R/'isolated/full-re-save.json').write_text(json.dumps({
    'scope':'Static codec tracing, not executed round-trip or H3 save/load verification.',
    'functions':records,
    'open':['Property bit codecs and quantization','Configuration block semantics',
            'Malformed stream/capacity handling','H3 field mapping and native round-trip'],
},indent=2)+'\n')
print('Recorded six H4 codecs and H3 decoder provenance; static audit only.')
