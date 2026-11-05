"""Compile exported prop render models with official Tool and verify bindings."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
env=os.environ.copy()
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/path)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
names=sys.argv[1:];assert names and set(names)<={'frunner_wheel','cex_health_cabinet','ff_redbase_rocks02','health_station'}
for name in names:
    export=json.loads((OUT/('h3-prop-'+name+'-export.json')).read_text())
    assert sha(export['jms'])==export['jms_sha256'] and sha(export['scene'])==export['scene_sha256']
    relative='levels\\custom\\battle_canyon_fresh\\props\\'+name
    log=OUT/('h3-prop-'+name+'-compile.log')
    with log.open('wb') as stream:
        run=subprocess.run([str(KIT/'tool.exe'),'render',relative,'draft'],cwd=KIT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=180)
    output=log.read_text(errors='replace')
    assert run.returncode==0 and not re.search(r'\b(ERROR|FATAL)\b',output),log
    target=KIT/'tags'/(relative+'\\'+name+'.render_model');assert target.is_file()
    xml=OUT/('h3-prop-'+name+'-render.xml')
    with (OUT/('h3-prop-'+name+'-native-export.log')).open('wb') as stream:
        run=subprocess.run([str(KIT/'tool.exe'),'export-tag-to-xml',str(target),str(xml)],cwd=KIT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=90)
    assert run.returncode==0 and xml.stat().st_size>1000
    parsed=ET.fromstring(xml.read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
    refs={e.find('./field[@name="render method"]').get('value').rsplit(',',1)[0] for e in parsed.find('./block[@name="materials"]')}
    expected=set()
    for row in export['bindings']:
        assert sha(row['alias'])==sha(row['target'])==row['sha256']
        expected.add(str(Path(row['alias']).relative_to(KIT/'tags').with_suffix('')))
    assert refs==expected,(name,refs,expected)
    counts=re.findall(r'(\d+) vertices, (\d+) points and (\d+) triangles',output)
    assert len(counts)==1,(name,counts)
    vertices,points,triangles=map(int,counts[0]);assert triangles==sum(m['triangles'] for m in export['meshes'])
    report=dict(source_scene_sha256=export['source_sha256'],jms_sha256=export['jms_sha256'],render_model=str(target),
        render_model_sha256=sha(target),materials=len(refs),vertices=vertices,points=points,triangles=triangles,
        warnings=[line.strip() for line in output.splitlines() if 'WARNING' in line],
        limitation='Native render compilation and shader bindings verified. Collision/physics, object setup/placement, animation and MCC appearance are separate unfinished work.')
    (OUT/('h3-prop-'+name+'-verification.json')).write_text(json.dumps(report,indent=2)+'\n')
    print('H3_PROP_RENDER_VERIFIED',name,vertices,'vertices',triangles,'triangles',len(refs),'shaders',flush=True)
