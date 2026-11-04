"""Verify shared H3 lighting controls through official import and native XML."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
stem='bound_shaders' if '--bound-shaders' in sys.argv else 'lighting'
probe=json.loads((OUT/(stem+'-workflow-probe.json')).read_text())
assert sha(probe['ass'])==probe['ass_sha256']
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:
    env[key]=str(OUT/relative)
def tool(args,log):
    with (OUT/log).open('wb') as stream:
        result=subprocess.run([str(KIT/'tool.exe'),*args],cwd=KIT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=120)
    text=(OUT/log).read_text(errors='replace')
    assert result.returncode==0 and '-ERROR-' not in text and 'FATAL' not in text,text
    return text
log=tool(['structure',str(Path(probe['ass']).relative_to(KIT/'data'))],stem+'-workflow-import.log')
assert '=== imported structure' in log
reports={}
hashes={}
for suffix,kind in [('scenario_structure_bsp','bsp'),('scenario_structure_lighting_info','info')]:
    tag=KIT/'tags/levels/custom/bc_lighting_workflow_probe'/(stem+'.'+suffix)
    before=sha(tag)
    xml=OUT/(stem+'-workflow-'+kind+'.xml')
    tool(['export-tag-to-xml',str(tag),str(xml)],stem+'-workflow-'+kind+'-xml.log')
    assert sha(tag)==before
    # Native Tool emits a literal <unavailable> inside one resource attribute.
    # Escape only that XML text for parsing; the native output/tag stay unchanged.
    reports[kind]=ET.fromstring(xml.read_text().replace('<unavailable>','&lt;unavailable&gt;'))
    hashes[suffix]=before
def field(element,name):return element.find('./field[@name="'+name+'"]').attrib['value']
def block(element,name):return element.find('./block[@name="'+name+'"]')
materials=block(reports['bsp'],'materials')
lighting=block(reports['info'],'material info')
assert len(materials)==len(lighting)==len(probe['cases'])==6
verified=[]
for case,material in zip(probe['cases'],materials):
    if 'expected_shader' in case:assert field(material,'render method')==case['expected_shader']
    properties=list(block(material,'properties'))
    resolution=next(p for p in properties if field(p,'type')=='lightmap resolution')
    assert float(field(resolution,'real-value'))==case['priority']
    info=lighting[int(field(material,'imported material index'))]
    original=case['source_emission']
    for source,target in [('power','emissive power'),('quality','emissive quality'),('focus','emissive focus')]:
        assert abs(float(field(info,target))-original[source])<1e-6
    color=[float(v) for v in field(info,'emissive color').split(',')]
    assert max(abs(a-b) for a,b in zip(color,original['color_srgb']))<1e-6
    for source,target in [('attenuation_falloff','attenuation falloff'),('attenuation_cutoff','attenuation cutoff')]:
        assert abs(float(field(info,target))-original[source]*.01)<1e-6
    flags=int(field(info,'flags'))
    assert bool(flags&1) and bool(flags&2)==original['power_per_unit_area']
    assert original['use_shader_gel'] is False
    verified.append(dict(priority=case['priority'],source_emission_index=original['index'],
                         native_power=float(field(info,'emissive power')),
                         native_cutoff=float(field(info,'attenuation cutoff'))))
assert sha(probe['ass'])==probe['ass_sha256']
(OUT/(stem+'-workflow-verification.json')).write_text(json.dumps(dict(
    ass_sha256=probe['ass_sha256'],native_tags=hashes,cases=verified,
    attenuation_import_scale=.01,source_rgb_preserved=True,source_power_preserved=True,authored_shader_lookups_checked=sum('expected_shader' in c for c in probe['cases']),
    limitation='Native inputs verified on a diagnostic. Proposed lighting differences await user approval; actual map authoring/bake and MCC appearance remain unverified.'),indent=2)+'\n')
print('H3_LIGHTING_INPUTS_VERIFIED: 6 priorities; source RGB/power/quality/focus; attenuation x0.01; power-per-area flags.',flush=True)
