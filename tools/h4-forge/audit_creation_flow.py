"""Record creation/duplication provenance; no native success claim."""
import hashlib
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'work/h4-forge-research'
locations={'824506D8':169,'82450970':74,'82450AF8':34,'82451478':189,
           '823C5F58':130,'823C6350':98,'823C5278':44,
           '823C55E8':205,'823C1D80':11,'823C51D0':289,
           '8244A538':207,'823C53F0':83,'823C7378':258,
           '823C6678':271,'823C6828':177,'829D7760':173,'822B41F8':44,
           '8297C338':174,'82373220':122,'8222EB20':68}
records={}
bodies={}
for address,number in locations.items():
    p=R/f'generated/halo4_recomp.{number}.cpp'
    text=p.read_text();marker=f'DEFINE_REX_FUNC(sub_{address}) {{'
    start=text.index(marker)
    body=(marker+text[start+len(marker):].split('DEFINE_REX_FUNC(',1)[0]).strip()
    bodies[address]=body
    records[address]=dict(file=p.name,line=text.count('\n',0,start)+1,
        sha256=hashlib.sha256(body.encode()).hexdigest(),
        calls=re.findall(r'\b(sub_[0-9A-F]+)\(ctx, base\)',body))
sequence=['8244EF80','823C5F58','823C6350','824511B0','823C5278']
indices=[bodies['824506D8'].index(f'sub_{a}(ctx, base)') for a in sequence]
assert indices==sorted(indices)
assert bodies['82450AF8'].index('sub_824506D8(ctx, base)')<bodies['82450AF8'].index('sub_824515C8(ctx, base)')
assert '// li r10,217' in bodies['823C5278']
assert '// addi r9,r9,228' in bodies['823C5278']
(R/'isolated/full-re-creation.json').write_text(json.dumps(dict(
    scope='Static creation/duplication trace, not native transaction or save/load verification.',
    functions=records,create_call_order=sequence,
    open=['Creation filter indirect callbacks and object constructor',
          'Ordnance-specific property adapters','Runtime creation failure rollback',
          'Failure rollback, networking and native duplicate/grab sequence']),indent=2)+'\n')
(R/'isolated/quota_clamp_original.cpp').write_text(
    '#include "forge_original.h"\n#undef DEFINE_REX_FUNC\n'
    '#define DEFINE_REX_FUNC(name) void name(PPCContext& ctx,uint8_t* base)\n'
    'namespace h4_forge_original {\n'+bodies['8244A538']+'\n}\n')
print('Recorded twenty original lifecycle/property/filter functions; extracted unchanged quota clamp.')
