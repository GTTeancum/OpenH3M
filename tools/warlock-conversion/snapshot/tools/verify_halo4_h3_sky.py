"""Verify official Tool sky output and saved scenario references, without rendering."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'work/halo4-to-h3/haven'
KIT=ROOT/'work/editing-kits/h3ek'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def xml(name):return ET.fromstring((OUT/'h3-authoring'/('sky-'+name+'.xml')).read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
def field(e,name):return e.find('./field[@name="'+name+'"]').attrib['value']
def block(e,name):return e.find('./block[@name="'+name+'"]')
export=read(OUT/'haven-h3-sky-export-bound.json')
assert sha(export['source'])==export['source_sha256']
assert sha(export['scene'])==export['scene_sha256'] and sha(export['jms'])==export['jms_sha256']
expected=set()
for b in export['material_slots']:
    assert sha(KIT/'tags'/b['target'])==b['shader_sha256']
    expected.add(b['target'].removesuffix('.shader')+',rmsh')
render=xml('render');materials=block(render,'materials')
assert len(materials)==11 and {field(m,'render method') for m in materials}==expected
sky=r'levels\custom\haven_h4\sky\sky'
model=xml('model');scenery=xml('scenery');scenario=xml('scenario')
assert field(model,'render model')==sky+',mode'
assert field(scenery,'model')==sky+',hlmt'
assert len(block(scenery,'functions'))==len(block(scenery,'attachments'))==0
assert len(block(scenario,'skies'))==1
assert field(block(scenario,'skies')[0],'sky')==sky+',scen'
assert field(block(scenario,'skies')[0],'active on bsps')=='1'
assert field(block(scenario,'structure bsps')[0],'default sky')==',0'
assert len(block(scenario,'scenery'))==510
log=(OUT/'h3-authoring/sky-render-bound-compile.log').read_text(errors='replace')
assert '11 materials, 1 nodes and 0 markers' in log
assert '10182 vertices, 9644 points and 18238 triangles' in log
assert 'ERROR' not in log and 'FATAL' not in log
tags=[KIT/'tags'/(sky+'.'+ext) for ext in ('render_model','model','scenery')]
tags.append(KIT/'tags/levels/custom/haven_h4/haven_draft.scenario')
report=dict(materials=11,vertices=10182,triangles=18238,sky_reference_verified=True,
    spawn_count_retained=510,no_donor_attachments=True,
    tag_hashes={str(p.relative_to(ROOT)):sha(p) for p in tags},jms_sha256=export['jms_sha256'],
    tool_warning='rasterizer:textures: leaking 15 textures on map dispose',
    cache_rebuilt_with_sky=False,rendering_verified=False,
    pending=['Native sky appearance, clipping and placement need actual renderer review.',
        'Source cloud scrolling, vertex-red opacity and lightshaft view/distance fades remain pending.',
        'Tower secondary emission texture and animated intensities remain pending.',
        'Source sky lighting and atmosphere need separate native authoring; this checkpoint is render geometry only.'])
(OUT/'haven-h3-sky-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('H4_SKY_NATIVE_VERIFIED: 11 materials, 18238 triangles, active scenario link; draft appearance and effects remain pending.')
