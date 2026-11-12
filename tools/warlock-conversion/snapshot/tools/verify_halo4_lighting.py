"""Check every saved light field and the isolated scenario reference change."""
import hashlib
import json
import math
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[4];OUT=ROOT/'work/halo4-to-h3/haven';KIT=ROOT/'work/editing-kits/h3ek'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def xml(name):return ET.fromstring((OUT/'h3-authoring'/name).read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
with_sky='--sky' in sys.argv
world_render='--world-render' in sys.argv
assert not world_render or with_sky
stem='native-lighting-with-sky' if with_sky else 'native-lighting'
prefix='lighting-with-sky' if with_sky else 'lighting'
if world_render:stem='native-lighting-worldrender';prefix='lighting-worldrender'
plan=read(OUT/'h3-authoring'/(stem+'-plan.json'))
assert sha(KIT.parent/'h4ek/tags'/plan['SourceH4'])==plan['SourceH4Sha256']
assert sha(KIT/'tags'/(plan['SourceTag']+'.scenario_structure_lighting_info'))==plan['SourceSha256']
if with_sky:assert sha(KIT.parent/'h4ek/tags'/plan['SourceH4Sky'])==plan['SourceH4SkySha256']
native=xml(prefix+'-authored.xml');count=0;maximum=0
for name,rows in [('generic light definitions',plan['Definitions']),('generic light instances',plan['Instances'])]:
    block=native.find('./block[@name="'+name+'"]');assert len(block)==len(rows)==plan['ExpectedCount']
    for element,row in zip(block,rows):
        for key,value in row['Fields'].items():
            saved=element.find('./field[@name="'+key+'"]');assert saved is not None
            actual=saved.get('value');kind=saved.get('type')
            if key=='flags':assert actual==('2' if value else '0'),(key,actual,value)
            elif kind.endswith('enum'):assert actual==value,(key,actual,value)
            else:
                a=list(map(float,actual.split(',')));b=list(map(float,value.split(',')))
                assert len(a)==len(b)
                for x,y in zip(a,b):
                    maximum=max(maximum,abs(x-y))
                    # Tool XML rounds real fields to roughly six significant
                    # digits; this check does not claim bit-exact float output.
                    assert math.isclose(x,y,rel_tol=6e-6,abs_tol=1e-7),(key,x,y)
            count+=1
before=xml('lighting-with-sky-scenario.xml' if world_render else 'lighting-scenario.xml' if with_sky else 'sky-scenario.xml');after=xml(prefix+'-scenario.xml')
ref='./block[@name="structure bsps"]/element/field[@name="structure lighting_info"]'
assert before.find(ref).get('value')==plan['PreviousTag']+',stli'
assert after.find(ref).get('value')==plan['TargetTag']+',stli'
before.find(ref).set('value',after.find(ref).get('value'))
if world_render:
    bspref='./block[@name="structure bsps"]/element/field[@name="structure bsp"]'
    assert before.find(bspref).get('value')==plan['PreviousBsp']+',sbsp'
    assert after.find(bspref).get('value')==plan['TargetBsp']+',sbsp'
    before.find(bspref).set('value',after.find(bspref).get('value'))
    # Tool derives the XML block label from the referenced BSP's short name.
    element='./block[@name="structure bsps"]/element'
    assert before.find(element).get('name')==plan['PreviousBsp'].rsplit('\\',1)[-1]
    assert after.find(element).get('name')==plan['TargetBsp'].rsplit('\\',1)[-1]
    before.find(element).set('name',after.find(element).get('name'))
def normalized(e):return (e.tag,sorted(e.attrib.items()),[normalized(c) for c in e])
assert normalized(before)==normalized(after),'Scenario changed beyond the lighting-info reference'
report=dict(definitions=plan['ExpectedCount'],instances=plan['ExpectedCount'],fields_checked=count,maximum_xml_rounding_difference=maximum,
    source_tags_unchanged=True,scenario_change_only_lighting_reference=not world_render,
    scenario_change_bsp_and_lighting_references=world_render,
    native_tag_sha256=sha(KIT/'tags'/(plan['TargetTag']+'.scenario_structure_lighting_info')),
    scenario_sha256=sha(KIT/'tags'/(plan['Scenario']+'.scenario')),
    baked=False,rendering_verified=False,pending=plan['Limitations'])
(OUT/('haven-h3-lighting-worldrender-verification.json' if world_render else 'haven-h3-lighting-with-sky-verification.json' if with_sky else 'haven-h3-lighting-verification.json')).write_text(json.dumps(report,indent=2)+'\n')
print('H4_LIGHTING_VERIFIED',count,'saved fields; only planned scenario references changed; source unchanged')
