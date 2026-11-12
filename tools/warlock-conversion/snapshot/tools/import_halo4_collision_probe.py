"""Compile isolated H4-derived collision inputs with unchanged official H3 Tool."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'work/halo4-to-h3/haven'
KIT=ROOT/'work/editing-kits/h3ek'
def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()
probe=json.loads((OUT/'haven-h3-collision-probe.json').read_text())
assert sha(probe['source'])==probe['source_sha256']
directory=OUT/'h3-authoring/collision-probe'
directory.mkdir(parents=True,exist_ok=True)
env=os.environ.copy()
for key,suffix in [('TEMP','temp'),('TMP','temp'),('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local')]:
    path=OUT/'h3-authoring'/suffix
    path.mkdir(parents=True,exist_ok=True)
    env[key]=str(path)
def tool(arguments,path):
    with path.open('wb') as stream:
        run=subprocess.run([str(KIT/'tool.exe'),*arguments],cwd=KIT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=120)
    return run.returncode,path.read_text(errors='replace')
def block(element,name):
    return element.find('./block[@name="'+name+'"]')
rows=[]
for variant in probe['variants']:
    name=variant['name']
    assert sha(variant['ass'])==variant['ass_sha256']
    code,log=tool(['structure',str(Path(variant['ass']).relative_to(KIT/'data'))],directory/(name+'-import.log'))
    row=dict(name=name,exit_code=code,issue_lines=[l.strip() for l in log.splitlines() if any(w in l for w in ('ERROR','FATAL','WARNING'))])
    tag=KIT/'tags/levels/custom/haven_collision_probe'/(name+'.scenario_structure_bsp')
    assert code==0 and '=== imported structure' in log and tag.is_file(),log
    before=sha(tag)
    xml=directory/(name+'.xml')
    code,log=tool(['export-tag-to-xml',str(tag),str(xml)],directory/(name+'-xml.log'))
    assert code==0 and '-ERROR-' not in log and sha(tag)==before
    root=ET.fromstring(xml.read_text().replace('<unavailable>','&lt;unavailable&gt;'))
    definitions=root.findall('.//block[@name="instanced geometries definitions"]')
    definitions=[b for b in definitions if len(b)]
    assert len(definitions)==1 and len(definitions[0])==1
    definition=definitions[0][0]
    row.update(native_tag_sha256=before,xml_sha256=sha(xml),
        definition_children=[dict(tag=e.tag,name=e.get('name'),count=len(e)) for e in definition],
        instance_xml=ET.tostring(block(root,'instanced geometry instances'),encoding='unicode'))
    rows.append(row)
assert sha(probe['source'])==probe['source_sha256']
report=dict(status='compiled_diagnostic',source_sha256=probe['source_sha256'],variants=rows,
    limitation='Inspect generated physics/surface flags before inferring representation. No game behavior or accepted mapping.')
(OUT/'haven-h3-collision-probe-native.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('H4_COLLISION_PROBE_COMPILED',json.dumps([dict(name=r['name'],issues=len(r['issue_lines'])) for r in rows]),flush=True)
