"""Read diagnostic world collision from official Tool XML, without tag writes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
stem='world-collision-source'
native=json.loads((OUT/(stem+'-native.json')).read_text())
assert native['import_completed']
tag=KIT/'tags/levels/custom/bc_world_collision_probe/world_collision_source.scenario_structure_bsp'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(tag)==native['native_tag_sha256']
xml=OUT/(stem+'-bsp.xml')
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/relative)
with (OUT/(stem+'-bsp-xml.log')).open('wb') as log:
    result=subprocess.run([str(KIT/'tool.exe'),'export-tag-to-xml',str(tag),str(xml)],cwd=KIT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
assert result.returncode==0 and '-ERROR-' not in (OUT/(stem+'-bsp-xml.log')).read_text(errors='replace')
# Tool sometimes emits an unescaped diagnostic placeholder; replace only that
# literal while streaming rather than loading the entire render-geometry XML.
fixed=OUT/(stem+'-bsp-readable.xml')
with xml.open(encoding='utf-8') as src,fixed.open('w',encoding='utf-8') as dst:
    for line in src:dst.write(line.replace('<unavailable>','&lt;unavailable&gt;'))
collision={}
capture=None
for event,element in ET.iterparse(fixed,events=('start','end')):
    if event=='start':
        if capture is None and element.tag=='block' and element.get('name') in ('collision bsp','large collision bsp'):
            capture=element
    elif element is capture:
        rows=[]
        for item in element.findall('./element'):
            rows.append({name:[{f.get('name'):f.get('value') for f in e.findall('./field')}
                for e in item.findall('./block[@name="'+name+'"]/element')]
                for name in ('vertices','edges','surfaces','planes')})
        collision.setdefault(element.get('name'),[]).extend(rows)
        capture=None
        element.clear()
    elif capture is None:element.clear()
assert sum(len(v) for v in collision.values())==1,collision.keys()
assert sha(tag)==native['native_tag_sha256']
report=dict(native_tag_sha256=native['native_tag_sha256'],ass_sha256=native['ass_sha256'],
    xml_sha256=sha(xml),collision=collision,
    limitation='Actual H3 collision fields read from official export. Geometry errors and source fidelity remain separate checks.')
(OUT/(stem+'-collision.json')).write_text(json.dumps(report,indent=2)+'\n')
print('NATIVE_WORLD_COLLISION_READ',json.dumps({k:[{n:len(v) for n,v in b.items()} for b in rows] for k,rows in collision.items()}),flush=True)
