"""Batch the reviewed stock wall setup through official H3 API and Tool only.

No geometry/shader generation or tag serialization. Material appearance still
requires MCC review. Existing source images are copied without pixel edits.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
REACH=ROOT/'work/editing-kits/hrek'
PREFIX=Path(r'levels\custom\battle_canyon_fresh')
families=json.loads((Path(__file__).with_name('material_families.json')).read_text())
CATEGORIES={'albedo','bump_mapping','alpha_test','specular_mask','material_model','environment_mapping','self_illumination','blend_mode','parallax'}
parser=argparse.ArgumentParser()
parser.add_argument('--family',choices=sorted(families),default='wall')
parser.add_argument('--prepare',action='store_true',help='Write reviewed source/image inventory only, for native metadata inspection')
parser.add_argument('--only-bitmap',help='Reimport one named bitmap and update its existing batch evidence')
args=parser.parse_args()
family=families[args.family]
DONOR=family['donor']
DEST=OUT/(args.family+'-family')
DEST.mkdir(exist_ok=True)
expected_count,expected_images=len(family['sources']),family['image_count']
expected_roles=set(family['bitmap_roles'])
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:
    env[key]=str(OUT/relative)
sys.path.insert(0,str(OUT/'python-packages'))
from PIL import Image, ImageChops, ImageStat

def xml(path):
    return ET.fromstring(path.read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
hashes={}
def remember(path):hashes[str(path)]=sha(path)
def execute(exe,arguments,label):
    run=subprocess.run([str(exe),*arguments],cwd=KIT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    log=DEST/(label+'.log');log.write_bytes(run.stdout)
    assert run.returncode==0,log
    assert not any(s in run.stdout.decode(errors='replace').lower() for s in ["can't resolve",'failed to','-error-','fatal error']),log
def tool(label,*arguments):execute(KIT/'tool.exe',list(arguments),label)

setups=json.loads((OUT/'hrek-shader-setups.json').read_text())
reach_options=json.loads((OUT/'reach-effective-shader-options.json').read_text())
stock_options=json.loads((OUT/'h3-effective-shader-options.json').read_text())[DONOR]
active={n:p for c in stock_options for n,p in c['parameters'].items()}
stock_names={c['category']:c['option'] for c in stock_options}
sources=[]
images={}
parameters={}
for source,inspection in reach_options.items():
    if source not in family['sources']:continue
    if not source.endswith('.shader'):continue
    selected={c['category']:c['option'] for c in inspection['categories']}
    if any(selected.get(c)!=stock_names[c] for c in CATEGORIES):continue
    fields={f['name']:f for f in setups[source]}
    assert not fields['reference'].get('value'),'Inherited inputs require separate review'
    params={}
    for element in fields['parameters']['elements']:
        row={f['name']:f for f in element};params[row['parameter name']['value']]=row
    defaults={n:v for c in inspection['categories'] for n,v in c['bitmap_defaults'].items()}
    assert set(defaults)==expected_roles,source
    for name,default in defaults.items():
        bitmap=params.get(name,{}).get('bitmap',{}).get('value') or default
        if bitmap.startswith('shaders\\default_bitmaps\\'):continue
        image=(REACH/'data'/bitmap).with_suffix('.tiff')
        assert image.is_file(),image
        entry=images.setdefault(bitmap,dict(path=bitmap,source=str(image),roles=[]))
        if name not in entry['roles']:entry['roles'].append(name)
    sources.append(source);parameters[source]=(params,defaults)
# Exact reviewed source lists prevent inventory changes from silently expanding
# a batch. Nine matching categories are necessary, not visual acceptance.
assert len(sources)==expected_count and len(images)==expected_images,(len(sources),len(images))
assert set(sources)==set(family['sources'])
assert len({Path(p).name for p in images})==len(images),'Resolve image-name collisions'
inventory=dict(donor=DONOR,sources=sorted(sources),images=sorted(images))
(OUT/(args.family+'-family-candidates.json')).write_text(json.dumps(inventory,indent=2)+'\n')
if args.prepare:
    print('WALL_FAMILY_PREPARED',len(sources),'surfaces',len(images),'images',flush=True)
    raise SystemExit(0)

metadata={r['tag']:r for r in json.loads((OUT/(args.family+'-family-bitmap-settings.json')).read_text())}
donor=xml(OUT/'h3-shader-xml'/(Path(DONOR).name+'.xml'))
donor_params={p.get('name'):p for p in donor.find("block[@name='parameters']")}
remember(KIT/'tags'/DONOR)
verified_images={}
for previous_path in OUT.glob('*-family/report.json'):
    pixels_path=previous_path.with_name('pixel-verification.json')
    if not pixels_path.is_file():continue
    previous=json.loads(previous_path.read_text())
    pixels=json.loads(pixels_path.read_text())
    if pixels['color_alpha_problems']:continue
    digests={t['target']:t['target_sha256'] for t in pixels['textures']}
    for previous_entry in previous['images'].values():
        target=previous_entry['target']
        if target in digests and sha(KIT/'tags'/target)==digests[target]:
            verified_images[target]=(previous_entry,digests[target])
settings=[]
for bitmap,entry in images.items():
    original=Path(entry['source']);remember(original);remember(REACH/'tags'/bitmap)
    assert hashes[str(REACH/'tags'/bitmap)]==metadata[bitmap]['sha256'],bitmap
    assert len(entry['roles'])==1 or set(entry['roles'])<={'base_map','self_illum_map','self_illum_detail_map'},entry
    role=entry['roles'][0]
    entry['target']=str(PREFIX/'bitmaps'/Path(bitmap).name)
    target=KIT/'tags'/entry['target'];data=(KIT/'data'/entry['target']).with_suffix('.tif')
    if data.exists():assert sha(data)==sha(original),data
    else:shutil.copyfile(original,data)
    template_reference=(donor_params[role].find("field[@name='bitmap']").get('value') if role in donor_params else '')
    if not template_reference.rsplit(',',1)[0]:template_reference=active[role]['default bitmap']
    assert template_reference.endswith(',bitm') and template_reference.rsplit(',',1)[0],(role,template_reference)
    template_name=template_reference.rsplit(',',1)[0]+'.bitmap'
    template=KIT/'tags'/template_name;remember(template)
    if not target.exists():shutil.copyfile(template,target)
    with Image.open(original) as image:
        image=image.convert('RGBA')
        monochrome=ImageChops.difference(image.getchannel('R'),image.getchannel('G')).getbbox() is None and ImageChops.difference(image.getchannel('R'),image.getchannel('B')).getbbox() is None
        entry['size']=image.size;entry['monochrome']=monochrome
    curve=int(metadata[bitmap]['bitmaps'][0]['curve'])
    assert curve in (1,3),metadata[bitmap]
    usage={'base_map':'Diffuse Map','detail_map':'Detail Map','bump_map':'ZBrush Bump Map (from Bump Map)','environment_map':'Cube Map (Reflection Map)','self_illum_map':'Self-Illum Map','self_illum_detail_map':'Detail Map'}[role]
    if len(entry['roles'])>1:
        usage={0:'Diffuse Map',4:'Detail Map',5:'Self-Illum Map'}[int(metadata[bitmap]['fields']['Usage'])]
    setting=dict(Path=entry['target'],Usage=usage,
        Format='Use Default (defined by usage)' if role=='bump_map' else ('8-bit Monochrome + 8-bit Alpha' if monochrome and role!='environment_map' else 'DXT5 (Compressed Color + Compressed 8-bit Alpha)'),
        LinearSource=curve==3 and role!='bump_map',Curve='sRGB' if curve==1 and role!='bump_map' else None,SourceGamma=2.2)
    entry['source_curve']=curve;entry['settings']=setting
    if 'max mipmap level' in metadata[bitmap]['fields']:
        setting['MaxMipmapLevel']=int(metadata[bitmap]['fields']['max mipmap level'])
    if role=='environment_map' and curve==1:
        # The stock cube import path already preserved these encoded source
        # pixels; a generic explicit gamma override changed them.
        setting.update(Curve=None,ClearOverride=True)
    prior=verified_images.get(entry['target'])
    if prior and not args.only_bitmap:
        old,digest=prior
        old_settings=dict(old['settings'])
        if 'MaxMipmapLevel' in setting and 'MaxMipmapLevel' not in old_settings:
            old_settings['MaxMipmapLevel']=int(xml(Path(old['xml'])).find("field[@name='max mipmap level']").get('value'))
        assert old_settings==setting,('Shared texture import settings differ',entry['target'],old_settings,setting)
        assert old['path']==entry['path'] and sha(Path(old['source']))==sha(original)
        entry.update(saved=old['saved'],xml=old['xml'],reused_verified_tag=True,reused_tag_sha256=digest)
    else:settings.append(setting)
bitmap_plan=DEST/'bitmap-import-plan.json'
selected_settings=[s for s in settings if not args.only_bitmap or Path(s['Path']).stem==args.only_bitmap]
assert not args.only_bitmap or len(selected_settings)==1
bitmap_plan.write_text(json.dumps(dict(Kit=str(KIT),Bitmaps=selected_settings),indent=2)+'\n')
if selected_settings:execute(OUT/'h3-api-probe/ApplyH3BitmapPlan.exe',[str(bitmap_plan)],'bitmap-import-settings')
for index,entry in enumerate(images.values()):
    if entry.get('reused_verified_tag'):continue
    if args.only_bitmap and Path(entry['path']).stem!=args.only_bitmap:continue
    tool('bitmap-'+str(index),'bitmap_single',str(Path(entry['target']).with_suffix('.tif')))
    exported=DEST/(Path(entry['path']).stem+'.bitmap.xml')
    tool('bitmap-xml-'+str(index),'export-tag-to-xml',str(KIT/'tags'/entry['target']),str(exported))
    bitmap=xml(exported).find("block[@name='bitmaps']/element")
    assert bitmap is not None,exported
    saved={f.get('name'):f.get('value') for f in bitmap.findall('field')}
    role=entry['roles'][0]
    expected_size=entry['size'] if role!='environment_map' else (entry['size'][0]//4,entry['size'][1]//3)
    assert (int(saved['width']),int(saved['height']))==tuple(expected_size),entry
    assert int(saved['mipmap count'])>0,entry
    if 'mipmap count' in metadata[bitmap]['bitmaps'][0]:
        assert int(saved['mipmap count'])==int(metadata[bitmap]['bitmaps'][0]['mipmap count']),entry
    if role=='environment_map':assert saved['type']=='cube map'
    if role!='bump_map':assert saved['curve']==('linear' if entry['source_curve']==3 else 'sRGB'),entry
    assert saved['format']==('dxn' if role=='bump_map' else ('a8y8' if entry['monochrome'] and role!='environment_map' else 'dxt5')),entry
    entry['xml']=str(exported);entry['saved']=saved
    if index%8==0:print('BITMAPS_IMPORTED',index+1,'of',len(images),flush=True)

if args.only_bitmap:
    report=json.loads((DEST/'report.json').read_text())
    for path,entry in images.items():
        if Path(path).stem==args.only_bitmap:report['images'][path]=entry
    for path,expected in report['source_hashes'].items():assert sha(Path(path))==expected,path
    (DEST/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('BITMAP_REFRESHED',args.only_bitmap,flush=True)
    raise SystemExit(0)

types={'bitmap':0,'color':1,'real':2,'int':3,'bool':4,'argb color':5}
reports=[]
for index,source in enumerate(sorted(sources)):
    remember(REACH/'tags'/source)
    params,defaults=parameters[source]
    plan=dict(Kit=str(KIT),Donor=DONOR,Target=str(PREFIX/'shaders'/Path(source).name),Parameters=[])
    for name,definition in active.items():
        original=params.get(name)
        if original is None and name not in defaults:continue
        row=dict(Name=name,Type=types[definition['parameter type']],Bitmap=None,Animations=[])
        if row['Type']==0:
            bitmap=(original or {}).get('bitmap',{}).get('value') or defaults[name]
            row['Bitmap']=bitmap if bitmap.startswith('shaders\\default_bitmaps\\') else images[bitmap]['target']
            assert (KIT/'tags'/row['Bitmap']).is_file(),row
        if original:
            if row['Type']==2:row['Real']=float(original['real']['value'])
            if row['Type'] in (3,4):row['Integer']=int(original['int/bool']['value'])
            for element in original['animated parameters']['elements']:
                f={p['name']:p for p in element}
                data=next(p for p in f['function']['elements'][0] if p['name']=='data')['data_base64']
                atype=int(f['type']['value'])
                row['Animations'].append(dict(Type=atype,TypeName=f['type']['enum_names'][atype],Input=f['input name']['value'],Range=f['range name']['value'],Period=float(f['time period']['value']),DataBase64=data))
        plan['Parameters'].append(row)
    plan_path=DEST/(Path(source).stem+'-plan.json');plan_path.write_text(json.dumps(plan,indent=2)+'\n')
    execute(OUT/'h3-api-probe/ApplyH3ShaderPlan.exe',[str(plan_path)],'shader-'+str(index))
    native_readback={p['name']:p['functions'] for p in json.loads(Path(str(plan_path)+'.readback.json').read_text())}
    exported=DEST/(Path(source).name+'.xml')
    tool('shader-xml-'+str(index),'export-tag-to-xml',str(KIT/'tags'/plan['Target']),str(exported))
    saved=xml(exported)
    assert [int(e.find('field').get('value')) for e in saved.find("block[@name='options']")]==[c['index'] for c in stock_options]
    template=saved.find("block[@name='postprocess']/element/field[@name='shader template']").get('value').rsplit(',',1)[0]
    assert (KIT/'tags'/(template+'.render_method_template')).is_file()
    for row in plan['Parameters']:
        actual=saved.find(f"block[@name='parameters']/element[@name='{row['Name']}']")
        assert actual is not None,row
        if row['Bitmap']:assert actual.find("field[@name='bitmap']").get('value')==row['Bitmap'].rsplit('.',1)[0]+',bitm',row
        if 'Real' in row:assert abs(float(actual.find("field[@name='real']").get('value'))-row['Real'])<1e-5,row
        if 'Integer' in row:assert int(actual.find("field[@name='int/bool']").get('value'))==row['Integer'],row
        animations=list(actual.find("block[@name='animated parameters']"))
        assert len(animations)==len(row['Animations']),row
        for animation_index,(expected,actual_animation) in enumerate(zip(row['Animations'],animations)):
            assert actual_animation.find("field[@name='type']").get('value')==expected['TypeName']
            assert actual_animation.find("field[@name='input name']").get('value')==expected['Input']
            assert actual_animation.find("field[@name='range name']").get('value')==expected['Range']
            assert abs(float(actual_animation.find("field[@name='time period']").get('value'))-expected['Period'])<1e-5
            assert native_readback[row['Name']][animation_index]==expected['DataBase64']
            exported_data=actual_animation.find("field[@name='data']").get('value')
            assert exported_data in ('function_definition_data,','function_definition_data,'+expected['DataBase64'].rstrip('=')),row
    reports.append(dict(source=source,target=plan['Target'],plan=str(plan_path),xml=str(exported),inputs=len(plan['Parameters']),functions=sum(len(p['Animations']) for p in plan['Parameters']),source_only_inputs=sorted(set(params)-set(active)),stock_inputs_retained=sorted(set(active)-{p['Name'] for p in plan['Parameters']})))
    print('MATERIAL_AUTHORED',index+1,'of',len(sources),Path(source).stem,flush=True)
for path,expected in hashes.items():assert sha(Path(path))==expected,path
report=dict(donor=DONOR,materials=reports,images=images,source_hashes=hashes,
    limitation='Saved native fields verified, not MCC appearance. Stock H3 sRGB imports replace legacy xRGB color response; normals, mips and reflections require visual review. Source-only inputs are not fabricated in H3.')
(DEST/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print('WALL_FAMILY_AUTHORED',len(reports),'materials',len(images),'images',flush=True)
