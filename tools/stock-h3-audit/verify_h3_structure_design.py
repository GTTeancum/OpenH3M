"""Compile the authored design with official Tool and compare native XML geometry."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
authoring=json.loads((OUT/'h3-structure-design-authoring.json').read_text())
source=json.loads((OUT/'original-structure-design.json').read_text())
assert sha(source['source'])==source['sha256']==authoring['source_sha256']
assert sha(authoring['scene'])==authoring['scene_sha256']
assert sha(authoring['ass'])==authoring['ass_sha256']
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:
    env[key]=str(OUT/relative)
def tool(arguments,log):
    with (OUT/log).open('wb') as stream:
        result=subprocess.run([str(KIT/'tool.exe'),*arguments],cwd=KIT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=120)
    text=(OUT/log).read_text(errors='replace')
    assert result.returncode==0 and '-ERROR-' not in text and 'FATAL' not in text,text
    return text
log=tool(['structure-design',str(Path(authoring['ass']).relative_to(KIT/'data'))],'h3-structure-design-import.log')
assert '=== finished import' in log
tag=KIT/'tags/levels/custom/battle_canyon_rebuild/battle_canyon.structure_design'
tag_hash=sha(tag)
xml=OUT/'h3-structure-design-native.xml'
tool(['export-tag-to-xml',str(tag),str(xml)],'h3-structure-design-xml.log')
assert sha(tag)==tag_hash
root=ET.parse(xml).getroot()
assert root.attrib['group']=='structure_design'
def block(element,name):
    return element.find('./block[@name="'+name+'"]')
def field(element,name):
    return element.find('./field[@name="'+name+'"]').attrib['value']
def vector(element,name):return tuple(float(v) for v in field(element,name).split(','))
def distance(a,b):return max(abs(x-y) for x,y in zip(a,b))
# Tool's XML prints six significant digits: at these coordinates this allows
# at most 0.00005 world units of decimal rounding. Do not claim bitwise equality.
tolerance=0.00006
groups=[field(e,'name') for e in block(root,'water groups block')]
assert set(groups)==set(authoring['water_groups']) and len(groups)==28
water=list(block(root,'water instances block'))
assert len(water)==28
remaining=list(enumerate(source['blocks']['water instances block']))
rows=[]
for compiled in water:
    triangles=block(compiled,'water debug triangles block')
    assert len(triangles)==8
    vertices={vector(e,k) for e in triangles for k in ('point0','point1','point2')}
    assert len(vertices)==6
    match=None
    for index,original in remaining:
        expected={tuple(p) for t in original['water debug triangles block'] for p in t.values()}
        if len(expected)==6 and all(min(distance(p,q) for q in vertices)<tolerance for p in expected):
            match=(index,original)
            break
    assert match is not None,vertices
    remaining.remove(match)
    index,original=match
    direction=vector(compiled,'direction')
    assert distance(direction,original['flow velocity'])<1e-6
    planes=[vector(e,'plane') for e in block(compiled,'water planes block')]
    expected_planes=[p['plane'] for p in original['water planes block']]
    assert len(planes)==len(expected_planes)==5
    assert all(min(distance(p,q) for q in planes)<tolerance for p in expected_planes)
    group=int(field(compiled,'group').rsplit(',',1)[1])
    rows.append(dict(source_instance=index,group=groups[group],vertices=6,planes=5,direction=list(direction)))
assert not remaining
ceilings=block(root,'soft ceilings block')
assert len(ceilings)==1
ceiling=ceilings[0]
original=source['blocks']['soft ceilings block'][0]
assert field(ceiling,'name')==(original['name'] or 'soft_ceiling') and field(ceiling,'type')=='acceleration' and original['type']==0
remaining=original['soft ceiling triangles'].copy()
for compiled in block(ceiling,'soft ceiling triangles'):
    triangle=[vector(compiled,k) for k in ('vertex0','vertex1','vertex2')]
    match=next((t for t in remaining if all(distance(p,t[k])<tolerance for p,k in zip(triangle,('vertex0','vertex1','vertex2')))),None)
    assert match is not None,triangle
    assert distance(vector(compiled,'plane'),match['plane'])<tolerance
    remaining.remove(match)
assert not remaining and len(block(ceiling,'soft ceiling triangles'))==40
for name in ('water mopp code','soft ceiling mopp code block'):
    assert len(block(root,name))>0
    assert all(len(block(e,'mopp data block '))>0 for e in block(root,name))
assert sha(source['source'])==source['sha256']
(OUT/'h3-structure-design-verification.json').write_text(json.dumps(dict(
    source_sha256=source['sha256'],scene_sha256=authoring['scene_sha256'],ass_sha256=authoring['ass_sha256'],
    native_tag=str(tag),native_tag_sha256=tag_hash,xml_sha256=sha(xml),
    water=rows,soft_ceiling_triangles=40,coordinate_tolerance_world_units=tolerance,
    limitation='Native design geometry/flow and collision data verified. Fog, scenario linkage and user-driven MCC physics testing remain pending.'),indent=2)+'\n')
print('H3_DESIGN_VERIFIED: 28 source convex water volumes and flow directions, 40 oriented soft-ceiling triangles, native collision data.',flush=True)
