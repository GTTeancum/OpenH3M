"""Resolve existing stock H3 shader options with official Tool XML exports."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
parser=argparse.ArgumentParser()
parser.add_argument('--kind',choices=['terrain','shader'],default='terrain')
kind=parser.parse_args().kind
group='shader_terrain' if kind=='terrain' else 'shader'
DEST=OUT/('h3-'+kind+'-option-xml')
DEST.mkdir(exist_ok=True)
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:
    env[key]=str(OUT/relative)
def xml(path):
    return ET.fromstring(path.read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
definition_path=OUT/('h3-'+kind+'-definition.xml')
if not definition_path.exists():
    result=subprocess.run([str(KIT/'tool.exe'),'export-tag-to-xml',str(KIT/'tags/shaders'/(kind+'.render_method_definition')),str(definition_path)],cwd=KIT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (DEST/'definition-export.log').write_bytes(result.stdout)
    assert result.returncode==0
definition=xml(definition_path)
categories=list(definition.find("block[@name='categories']"))
options={}
report={}
for path in sorted((OUT/'h3-shader-xml').glob('*.'+group+'.xml')):
    shader=xml(path)
    selected=list(shader.find("block[@name='options']"))
    assert len(selected)<=len(categories)
    resolved=[]
    for ci,category in enumerate(categories):
        index=int(selected[ci].find('field').get('value')) if ci<len(selected) else 0
        option=category.find(f"block[@name='options']/element[@index='{index}']")
        assert option is not None
        reference=option.find("field[@name='option']").get('value')
        fields={}
        if reference.split(',',1)[0]:
            name,option_group=reference.rsplit(',',1)
            assert option_group=='rmop'
            tag=name+'.render_method_option'
            if tag not in options:
                source=KIT/'tags'/tag
                before=hashlib.sha256(source.read_bytes()).hexdigest()
                destination=DEST/(Path(tag).name+'.xml')
                result=subprocess.run([str(KIT/'tool.exe'),'export-tag-to-xml',str(source),str(destination)],cwd=KIT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
                (DEST/(Path(tag).name+'.log')).write_bytes(result.stdout)
                assert result.returncode==0
                parsed=xml(destination)
                assert parsed.get('id')==name
                assert hashlib.sha256(source.read_bytes()).hexdigest()==before
                options[tag]={p.get('name'):{f.get('name'):f.get('value') for f in p.findall('field')} for p in parsed.find("block[@name='parameters']")}
            fields=options[tag]
        resolved.append(dict(category=category.get('name'),index=index,option=option.get('name'),parameters=fields,defaulted_missing_option=ci>=len(selected)))
    report[shader.get('id')+'.'+group]=resolved
(OUT/('h3-effective-'+kind+'-options.json')).write_text(json.dumps(report,indent=2)+'\n')
print('STOCK_H3_OPTIONS',kind,len(report),'shaders',len(options),'option tags',flush=True)
