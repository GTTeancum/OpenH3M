"""Verify native sky references and retained material/texture evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('export_sky_metadata.py'))],cwd=ROOT,check=True)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def xml(name):return ET.fromstring((OUT/(name+'.xml')).read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
def field(e,name):return e.find('./field[@name="'+name+'"]').attrib['value']
def block(e,name):return e.find('./block[@name="'+name+'"]')
export=json.loads((OUT/'h3-sky-export.json').read_text())
assert sha(export['scene'])==export['scene_sha256'] and sha(export['jms'])==export['jms_sha256']
expected=set()
for binding in export['bindings']:
    assert sha(binding['export_tag'])==sha(binding['target'])==binding['sha256']
    expected.add(str(Path(binding['export_tag']).relative_to(KIT/'tags').with_suffix(''))+',rmsh')
render=xml('native-sky-render');materials=block(render,'materials')
assert len(materials)==13 and {field(m,'render method') for m in materials}==expected
sky=r'levels\custom\battle_canyon_fresh\sky\sky'
model=xml('native-sky-model');scenery=xml('native-sky-scenery');scenario=xml('native-sky-scenario')
assert field(model,'render model')==sky+',mode'
assert field(scenery,'model')==sky+',hlmt'
assert len(block(scenery,'functions'))==len(block(scenery,'attachments'))==0
assert len(block(scenario,'skies'))==1
assert field(block(scenario,'skies')[0],'sky')==sky+',scen'
assert field(block(scenario,'skies')[0],'active on bsps')=='1'
assert field(block(scenario,'structure bsps')[0],'default sky')==',0'
configured=json.loads((ROOT/'tools/stock-h3-audit/material_families.json').read_text())
families=[name for name in configured if name.startswith('sky_')]
for family in families:
    report=json.loads((OUT/(family+'-family/pixel-verification.json')).read_text())
    assert not report['color_alpha_problems'],family
    for image in report['textures']:assert sha(KIT/'tags'/image['target'])==image['target_sha256']
log=(OUT/'h3-sky-render-compile.log').read_text()
assert '13 materials, 1 nodes and 0 markers' in log and '6577 vertices, 6418 points and 11637 triangles' in log
assert 'ERROR' not in log and 'FATAL' not in log
tags=[KIT/'tags'/(sky+'.'+e) for e in ('render_model','model','scenery')]
tags.append(KIT/'tags/levels/custom/battle_canyon_fresh/battle_canyon_fresh.scenario')
report=dict(materials=13,vertices=6577,triangles=11637,sky_reference_verified=True,no_donor_attachments=True,
    tag_hashes={str(p):sha(p) for p in tags},export=export['jms_sha256'],
    tool_warning='rasterizer:textures: leaking 15 textures on map dispose',
    limitation='Native compilation and saved references verified. Native rendered colors, animation, clipping and sky visibility still require MCC review. Atmosphere, multiplayer placements and lighting remain unfinished.')
(OUT/'h3-sky-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('H3_SKY_VERIFIED',len(materials),'materials; 11637 triangles; active scenario reference',flush=True)
