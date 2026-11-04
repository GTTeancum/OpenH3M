"""Run official H3 Tool on the isolated collision diagnostic and export its XML."""
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
variant='-authored' if '--authored' in sys.argv else ('-precise' if '--precise' in sys.argv else '')+('-render-only' if '--render-only' in sys.argv else '')
stem='collision-workflow'+variant
probe=json.loads((OUT/(stem+'-probe.json')).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert sha(probe['ass'])==probe['ass_sha256']
assert sha(probe['source'])==probe['source_sha256']
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/relative)
def tool(args,suffix):
    path=OUT/(stem+suffix+'.log')
    with path.open('wb') as stream:
        result=subprocess.run([str(KIT/'tool.exe'),*args],cwd=KIT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=120)
    return result,path.read_text(errors='replace')
result,log=tool(['structure',str(Path(probe['ass']).relative_to(KIT/'data'))],'-import')
assert result.returncode==0 and '=== imported structure' in log
tag=KIT/'tags/levels/custom/bc_collision_workflow_probe'/(Path(probe['ass']).stem+'.scenario_structure_bsp')
before=sha(tag)
xml=OUT/(stem+'-bsp.xml')
export,export_log=tool(['export-tag-to-xml',str(tag),str(xml)],'-bsp-xml')
assert export.returncode==0 and '-ERROR-' not in export_log and xml.is_file()
assert sha(tag)==before and sha(probe['ass'])==probe['ass_sha256']
report=dict(ass_sha256=probe['ass_sha256'],native_tag_sha256=before,native_xml_sha256=sha(xml),
    issue_lines=[line.strip() for line in log.splitlines() if any(word in line for word in ('WARNING','ERROR','FATAL'))],
    limitation='Diagnostic only; successful import does not waive issue lines or establish visual/collision acceptance.')
if variant=='-authored':
    reference=OUT/'collision-workflow-precise-render-only-bsp.xml'
    expected=ET.fromstring(reference.read_text().replace('<unavailable>','&lt;unavailable&gt;'))
    actual=ET.fromstring(xml.read_text().replace('<unavailable>','&lt;unavailable&gt;'))
    def canonical(e):return ET.canonicalize(ET.tostring(e,encoding='unicode'),strip_text=True)
    checks={}
    for name in ('instanced geometries definitions','per mesh temporary','compression info'):
        checks[name]=[canonical(e) for e in expected.findall('.//block[@name="'+name+'"]') if len(e)]==[canonical(e) for e in actual.findall('.//block[@name="'+name+'"]') if len(e)]
    assert all(checks.values()),checks
    report['matches_diagnosed_native_geometry']=checks
(OUT/(stem+'-native.json')).write_text(json.dumps(report,indent=2)+'\n')
print('H3_COLLISION_NATIVE_DIAGNOSTIC',json.dumps(report),flush=True)
