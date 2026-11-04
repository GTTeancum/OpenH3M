"""Prepare original inputs and run official H3 API/Tool authoring operations."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
REACH=ROOT/'work/editing-kits/hrek'
DEST=OUT/'wall-detail-trial'
DEST.mkdir(exist_ok=True)
SOURCE=r'levels\dlc\cex_beaver_creek\shaders\ca_bcreek_bb_walldetail.shader'
DONOR=r'levels\dlc\bunkerworld\shaders\bunker_plate_wall.shader'
TARGET=r'levels\custom\battle_canyon_fresh\shaders\ca_bcreek_bb_walldetail.shader'
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:
    env[key]=str(OUT/relative)
def xml(path):
    return ET.fromstring(path.read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
calls=[]
def tool(*args):
    run=subprocess.run([str(KIT/'tool.exe'),*args],cwd=KIT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log=DEST/(f'{len(calls):03d}-'+args[0]+'.log')
    log.write_bytes(run.stdout)
    calls.append(dict(args=args,log=str(log),exit_code=run.returncode))
    assert run.returncode==0
    text=run.stdout.decode(errors='replace').lower()
    assert not any(s in text for s in ["can't resolve",'failed to','-error-']),log
    if args[0]=='patch-tag-field':assert 'field successfully patched' in text
hashes={}
def remember(path):
    hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
remember(REACH/'tags'/SOURCE)
remember(KIT/'tags'/DONOR)
setups=json.loads((OUT/'hrek-shader-setups.json').read_text())
source={f['name']:f for f in setups[SOURCE]}
assert not source['reference'].get('value'), 'Resolve inherited inputs before authoring'
parameters={}
for row in source['parameters']['elements']:
    fields={f['name']:f for f in row}
    parameters[fields['parameter name']['value']]=fields
selected=json.loads((OUT/'h3-effective-shader-options.json').read_text())[DONOR]
active={name:definition for c in selected for name,definition in c['parameters'].items()}
donor=xml(OUT/'h3-shader-xml/bunker_plate_wall.shader.xml')
donor_parameters={e.get('name'):e for e in donor.find("block[@name='parameters']")}
types={'bitmap':0,'color':1,'real':2,'int':3,'bool':4,'argb color':5}
plan=dict(Kit=str(KIT),Donor=DONOR,Target=TARGET,Parameters=[])
imports=[]
bitmap_settings=[]
for name,definition in active.items():
    if name not in parameters:continue # Retain stock H3 settings for other inputs.
    original=parameters[name]
    row=dict(Name=name,Type=types[definition['parameter type']],Bitmap=None,Animations=[])
    if row['Type']==0:
        bitmap=original['bitmap'].get('value')
        assert bitmap, 'Resolve original/default image before authoring: '+name
        image=(REACH/'data'/bitmap).with_suffix('.tiff')
        remember(image)
        target_bitmap=str(Path(r'levels\custom\battle_canyon_fresh\bitmaps')/Path(bitmap).name)
        target_image=(KIT/'data'/target_bitmap).with_suffix('.tif')
        template_name=donor_parameters[name].find("field[@name='bitmap']").get('value').rsplit(',',1)[0]+'.bitmap'
        template=KIT/'tags'/template_name
        remember(template)
        target=KIT/'tags'/target_bitmap
        if target.exists() or target_image.exists():
            assert target.is_file() and target_image.is_file()
            assert hashlib.sha256(target_image.read_bytes()).hexdigest()==hashes[str(image)]
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            target_image.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(image,target_image)
            shutil.copyfile(template,target)
            if name=='bump_map':
                tool('patch-tag-field',target_bitmap,'bitmap_block_struct[0].Usage','ZBrush Bump Map (from Bump Map)')
            tool('bitmap_single',str(Path(target_bitmap).with_suffix('.tif')))
        if name in ('base_map','detail_map','environment_map'):
            bitmap_settings.append(dict(Path=target_bitmap,
                Usage={'base_map':'Diffuse Map','detail_map':'Detail Map','environment_map':'Cube Map (Reflection Map)'}[name],
                Format=('DXT5 (Compressed Color + Compressed 8-bit Alpha)' if name=='environment_map' else '8-bit Monochrome + 8-bit Alpha'),
                LinearSource=name!='environment_map'))
        exported=DEST/(Path(bitmap).stem+'.bitmap.xml')
        tool('export-tag-to-xml',str(target),str(exported))
        imported=xml(exported)
        if name=='bump_map':assert imported.find("field[@name='Usage']").get('value')=='ZBrush Bump Map (from Bump Map)'
        if name=='environment_map':assert imported.find("block[@name='bitmaps']/element/field[@name='type']").get('value')=='cube map'
        row['Bitmap']=target_bitmap
        imports.append(dict(input=name,source=str(image),target=target_bitmap,xml=str(exported)))
    for animation in original['animated parameters']['elements']:
        fields={f['name']:f for f in animation}
        data=next(f for f in fields['function']['elements'][0] if f['name']=='data')['data_base64']
        row['Animations'].append(dict(Type=int(fields['type']['value']),Input=fields['input name']['value'],
            Range=fields['range name']['value'],Period=float(fields['time period']['value']),DataBase64=data))
    plan['Parameters'].append(row)
# These two source bitmaps are genuinely monochrome/linear; the cubemap is colored.
# Do not generalize this import choice to other source textures.
source_bitmap_settings=json.loads((DEST/'source-bitmap-settings.json').read_text())
for row in source_bitmap_settings:
    if row['input'] in ('base_map','detail_map'):assert row['bitmaps'][0]['curve']=='3'
    remember(REACH/'tags'/row['tag'])
    assert hashes[str(REACH/'tags'/row['tag'])]==row['sha256'],row['tag']
bitmap_plan_path=DEST/'bitmap-import-plan.json'
bitmap_plan_path.write_text(json.dumps(dict(Kit=str(KIT),Bitmaps=bitmap_settings),indent=2)+'\n')
run=subprocess.run([str(OUT/'h3-api-probe/ApplyH3BitmapPlan.exe'),str(bitmap_plan_path)],cwd=KIT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
(DEST/'bitmap-import-settings.log').write_bytes(run.stdout)
assert run.returncode==0,run.stdout.decode(errors='replace')
for row in imports:
    if row['input']=='bump_map':continue
    tool('bitmap_single',str(Path(row['target']).with_suffix('.tif')))
    tool('export-tag-to-xml',str(KIT/'tags'/row['target']),row['xml'])
    imported=xml(Path(row['xml']))
    data=imported.find("block[@name='bitmaps']/element")
    if row['input']=='environment_map':
        assert data.find("field[@name='type']").get('value')=='cube map'
        assert data.find("field[@name='format']").get('value')=='dxt5'
    else:
        assert data.find("field[@name='curve']").get('value')=='linear'
        assert data.find("field[@name='format']").get('value')=='a8y8'
plan_path=DEST/'plan.json'
plan_path.write_text(json.dumps(plan,indent=2)+'\n')
run=subprocess.run([str(OUT/'h3-api-probe/ApplyH3ShaderPlan.exe'),str(plan_path)],cwd=KIT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
(DEST/'official-api-authoring.log').write_bytes(run.stdout)
assert run.returncode==0,run.stdout.decode(errors='replace')
exported=DEST/'saved.shader.xml'
tool('export-tag-to-xml',str(KIT/'tags'/TARGET),str(exported))
saved=xml(exported)
original_options=[int(e.find('field').get('value')) for e in donor.find("block[@name='options']")]
saved_options=[int(e.find('field').get('value')) for e in saved.find("block[@name='options']")]
assert saved_options[:len(original_options)]==original_options
assert saved_options==[c['index'] for c in selected]
assert all(c['index']==0 for c in selected[len(original_options):])
template=saved.find("block[@name='postprocess']/element/field[@name='shader template']").get('value').rsplit(',',1)[0]
assert (KIT/'tags'/(template+'.render_method_template')).is_file(),template
for row in plan['Parameters']:
    actual=saved.find(f"block[@name='parameters']/element[@name='{row['Name']}']")
    assert actual is not None,row['Name']
    assert actual.find("field[@name='parameter type']").get('value')==next(k for k,v in types.items() if v==row['Type'])
    if row['Bitmap']:
        assert actual.find("field[@name='bitmap']").get('value')==row['Bitmap'].rsplit('.',1)[0]+',bitm'
    animations=list(actual.find("block[@name='animated parameters']"))
    assert len(animations)==len(row['Animations']),row['Name']
    for expected,animation in zip(row['Animations'],animations):
        animation_types={0:'value',1:'color',2:'scale uniform',3:'scale x',4:'scale y'}
        assert animation.find("field[@name='type']").get('value')==animation_types[expected['Type']]
        assert animation.find("field[@name='input name']").get('value')==expected['Input']
        assert animation.find("field[@name='range name']").get('value')==expected['Range']
        assert float(animation.find("field[@name='time period']").get('value'))==expected['Period']
        assert animation.find("field[@name='data']").get('value')=='function_definition_data,'+expected['DataBase64'].rstrip('=')
for path,expected in hashes.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected,path
report=dict(source=SOURCE,donor=DONOR,target=TARGET,inputs=len(plan['Parameters']),imports=imports,bitmap_settings=bitmap_settings,
            functions=sum(len(p['Animations']) for p in plan['Parameters']),source_hashes=hashes,stock_shader_options_unchanged=True,
            original_options=original_options,saved_options=saved_options,
            appended_mcc_options=[c['category'] for c in selected[len(original_options):]],existing_mcc_template=template,
            calls=calls,limitation='Official API writes and Tool saved-field verification only; MCC rendering, bitmap pixel fidelity and reflection orientation remain unverified.')
(DEST/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print('H3_WALL_DETAIL_AUTHORED',report['inputs'],'inputs',report['functions'],'functions',flush=True)
