"""Assign original scalar/color functions and bind the existing stock template.

Uses existing ManagedBlam inspection data and official Tool field operations.
Does not manufacture function data, introduce parameters, or change shader code.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
DEST=OUT/'terrain-scalar-inputs'
DEST.mkdir(exist_ok=True)
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:
    env[key]=str(OUT/relative)
sources=json.loads((OUT/'hrek-shader-setups.json').read_text())
options=json.loads((OUT/'h3-effective-terrain-options.json').read_text())
def xml(path):
    return ET.fromstring(path.read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
calls=[]
def tool(*args):
    result=subprocess.run([str(KIT/'tool.exe'),*args],cwd=KIT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log=DEST/(f'{len(calls):03d}-'+args[0]+'.log')
    log.write_bytes(result.stdout)
    calls.append(dict(args=args,log=str(log),exit_code=result.returncode))
    assert result.returncode==0
    if args[0]=='patch-tag-field':assert b'field successfully patched' in result.stdout
reports=[]
trials=[OUT/'terrain-trial-report.json',*sorted(OUT.glob('ca_bcreek_*-terrain-trial-report.json'))]
families=json.loads(Path(__file__).with_name('material_families.json').read_text())
native_sources={s:name for name,f in families.items() if f.get('kind')=='terrain' for s in f['sources']}
for path in trials:
    trial=json.loads(path.read_text())
    if trial['source'] in native_sources:
        family=native_sources[trial['source']]
        assert (OUT/(family+'-family/report.json')).is_file(),family
        print('TERRAIN_TRIAL_SUPERSEDED',trial['source'],family,flush=True)
        continue
    tag=trial['target']
    assert tag.startswith('levels\\custom\\battle_canyon_fresh\\shaders\\')
    source=ROOT/'work/editing-kits/hrek/tags'/trial['source']
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    destination=DEST/(Path(tag).stem+'.xml')
    tool('export-tag-to-xml',str(KIT/'tags'/tag),str(destination))
    saved=xml(destination)
    parameters={e.get('name'):e for e in saved.find("block[@name='parameters']")}
    selected=options[trial['stock_donor']]
    template=r'shaders\terrain_templates\_'+'_'.join(str(c['index']) for c in selected)
    assert (KIT/'tags'/(template+'.render_method_template')).is_file(), template
    assert any(template+'.render_method_template' in p.read_text(errors='replace')
               for p in OUT.glob('*-all-tags.txt')), 'Template not verified in a stock 360 inventory'
    actual_template=saved.find("block[@name='postprocess']/element[@index='0']/field[@name='shader template']")
    assert actual_template is not None
    reference=template+',rmt2'
    if actual_template.get('value')!=reference:
        tool('patch-tag-field',tag,'shader_terrain_struct_definition[0].render_method[0].postprocess[0].shader template',reference)
    active={name:field for c in options[trial['stock_donor']] for name,field in c['parameters'].items()}
    original={}
    for row in next(f for f in sources[trial['source']] if f['name']=='parameters')['elements']:
        fields={f['name']:f for f in row}
        original[fields['parameter name']['value']]=fields
    expected=[]
    for name,definition in active.items():
        if definition['parameter type']=='bitmap' or name not in original:
            continue
        source_parameter=original[name]
        target=parameters[name]
        source_animations=source_parameter['animated parameters']['elements']
        target_animations=list(target.find("block[@name='animated parameters']"))
        assert len(source_animations)==len(target_animations),name
        for index,(sa,ta) in enumerate(zip(source_animations,target_animations)):
            fields={f['name']:f for f in sa}
            kind={'0':'value','1':'color'}[fields['type']['value']]
            assert ta.get('name')==kind,(name,ta.get('name'),kind)
            assert fields['input name']['value']==fields['range name']['value']==''
            assert float(fields['time period']['value'])==0
            function=next(f for f in fields['function']['elements'][0] if f['name']=='data')['data_base64'].rstrip('=')
            field=f"shader_terrain_struct_definition[0].render_method[0].parameters[{target.get('index')}].animated parameters[{index}].function[0].data"
            tool('patch-tag-field',tag,field,'function_definition_data,'+function)
            expected.append(dict(parameter=name,index=index,function=function))
    tool('export-tag-to-xml',str(KIT/'tags'/tag),str(destination))
    verified=xml(destination)
    assert verified.find("block[@name='postprocess']/element[@index='0']/field[@name='shader template']").get('value')==reference
    for row in expected:
        field=verified.find(f"block[@name='parameters']/element[@name='{row['parameter']}']/block[@name='animated parameters']/element[@index='{row['index']}']/field[@name='data']")
        assert field.get('value')=='function_definition_data,'+row['function']
    assert ET.tostring(saved.find("block[@name='options']"))==ET.tostring(verified.find("block[@name='options']"))
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    reports.append(dict(target=tag,original_functions=expected,stock_template=template,stock_360_template_confirmed=True,stock_options_unchanged=True,source_sha256=before))
    print('TERRAIN_SCALAR_INPUTS_SAVED',Path(tag).name,len(expected),flush=True)
(DEST/'report.json').write_text(json.dumps(dict(materials=reports,calls=calls,limitation='Saved field verification; rendered MCC appearance not yet tested'),indent=2)+'\n')
