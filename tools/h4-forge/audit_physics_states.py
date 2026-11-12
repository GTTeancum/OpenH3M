"""Record original physics state selection/application and menu provenance."""
import contextlib
import hashlib
import io
import json
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/'work/h4-forge-research'
locations = {'82687088':274,'8244A180':195,'8244A2A0':58,
             '82449B18':172,'82469630':94,'8244A5F0':208,'824515C8':212}
functions = {}
bodies = {}
for name,number in locations.items():
    file=f'halo4_recomp.{number}.cpp'
    text=(R/'generated'/file).read_text()
    marker=f'DEFINE_REX_FUNC(sub_{name}) {{'
    start=text.index(marker)
    body=(marker+text[start+len(marker):].split('DEFINE_REX_FUNC(',1)[0]).strip()
    bodies[name]=body
    functions[name]=dict(file=file,line=text.count('\n',0,start)+1,
        sha256=hashlib.sha256(body.encode()).hexdigest(),
        calls=sorted(set(re.findall(r'\b(sub_[0-9A-F]+)\(ctx, base\)',body))))
with contextlib.redirect_stdout(io.StringIO()):
    menu=runpy.run_path(str(ROOT/'tools/h4-forge/audit_forge_menu.py'))
labels=[menu['label'](0x80608+i) for i in range(3)]
assert labels==['physics_normal','physics_fixed','physics_phased']
constructor=bodies['82687088']
for instruction in ['ori r24,r19,1421','stw r24,644(r31)',
                    'stw r25,652(r31)','addi r25,r31,208',
                    'li r24,192','sth r24,660(r31)',
                    'li r5,64','li r5,192',
                    'ori r4,r8,1544','ori r4,r8,1545','ori r4,r8,1546']:
    assert '// '+instruction in constructor,instruction
assert '// cmplwi cr6,r8,4' in bodies['82469630']
assert '// addi r11,r11,192' in bodies['82469630']
schema=ROOT/'work/stock-h3-audit/TagTool/TagTool/Tags/Definitions/Gen4/PhysicsModel.cs'
report=dict(scope='Static source trace, not native collision or full editor verification.',
            functions=functions,menu=dict(labels=labels,values=[0,64,192],mask=192,
            control_offset=640,list_offset=208,property_offset=138),
            keyframed_model_test=dict(function='82469630',body_stride=192,
              motion_offset=28,match=4,schema=str(schema.relative_to(ROOT)),
              schema_sha256=hashlib.sha256(schema.read_bytes()).hexdigest()),
            open=['Property list availability and serialization',
                  'Special Normal-state predicate 8244A5F0',
                  'Runtime physics rebuild helpers and collision effects',
                  'H3 adapter and multiplayer equivalence'])
(R/'isolated/full-re-physics.json').write_text(json.dumps(report,indent=2)+'\n')
(R/'isolated/physics_selector_original.cpp').write_text(
    '#include "forge_original.h"\n#define DEFINE_REX_FUNC(name) void name(PPCContext& ctx,uint8_t* base)\n'
    'namespace h4_forge_original {\n'
    'void sub_82449B18(PPCContext&,uint8_t*);\n'
    'void sub_82469630(PPCContext&,uint8_t*);\n'
    'void sub_8244A5F0(PPCContext&,uint8_t*);\n'
    'void sub_823C2020(PPCContext&,uint8_t*);\n'+bodies['8244A180']+'\n}\n')
print('Verified physics menu labels/values/mask and recorded seven original function bodies.')
