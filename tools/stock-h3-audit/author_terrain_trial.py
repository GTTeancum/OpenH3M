"""Author one Reach-textured stock H3 terrain material through official Tool.

Copies stock H3 tags, imports original extracted images, and assigns existing
texture/function fields through patch-tag-field. No binary writer, function
generation, shader code or geometry conversion. Unchanged H3 shader options
are deliberate; this remains a material trial pending visual review.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
KIT = ROOT / 'work/editing-kits/h3ek'
REACH = ROOT / 'work/editing-kits/hrek'
SOURCE = r'levels\dlc\cex_beaver_creek\shaders\ca_bcreek_terrain.shader_terrain'
DONOR = r'levels\dlc\bunkerworld\shaders\nature\ground.shader_terrain'
TARGET = r'levels\custom\battle_canyon_fresh\shaders\ca_bcreek_terrain.shader_terrain'
PREFIX = r'levels\custom\battle_canyon_fresh\bitmaps'
logs = OUT / 'terrain-trial'
logs.mkdir(exist_ok=True)
env = os.environ.copy()
for key, relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:
    env[key] = str(OUT / relative)

def xml(path):
    return ET.fromstring(path.read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))

hashes = {}
def remember(path):
    hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()

calls = []
def tool(*args):
    index = len(calls)
    run = subprocess.run([str(KIT/'tool.exe'),*args],cwd=KIT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log = logs / f'{index:03d}-{args[0]}.log'
    log.write_bytes(run.stdout)
    calls.append(dict(args=list(args),exit_code=run.returncode,log=str(log)))
    text = run.stdout.decode(errors='replace')
    if run.returncode or any(s in text.lower() for s in ("can't resolve", 'tag not found','failed to','fatal error')):
        raise RuntimeError(f'Official Tool command failed; see {log}')
    if args[0] == 'patch-tag-field' and 'field successfully patched' not in text:
        raise RuntimeError(f'No patch confirmation; see {log}')

source_fields = json.loads((OUT/'hrek-shader-setups.json').read_text())[SOURCE]
source_parameters = {}
for row in next(f for f in source_fields if f['name']=='parameters')['elements']:
    fields = {f['name']:f for f in row}
    source_parameters[fields['parameter name']['value']] = fields
effective = json.loads((OUT/'reach-effective-shader-options.json').read_text())[SOURCE]
defaults = {name:value for category in effective['categories'] for name,value in category['bitmap_defaults'].items()}
assert 'material_0' in {c['category'] for c in effective['categories']}, 'Wrong source shader type'
donor_xml = xml(OUT/'h3-shader-xml/ground.shader_terrain.xml')
donor_parameters = list(donor_xml.find("block[@name='parameters']"))
remember(REACH/'tags'/SOURCE)
remember(KIT/'tags'/DONOR)
target_path = KIT/'tags'/TARGET
if not target_path.exists():
    target_path.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(KIT/'tags'/DONOR,target_path)

bindings = []
imported = {}
expected_functions = []
for parameter in donor_parameters:
    name = parameter.get('name')
    if name not in defaults:
        continue  # Not a texture input in the selected original Reach options.
    source_parameter = source_parameters.get(name,{})
    source_bitmap = source_parameter.get('bitmap',{}).get('value') or defaults[name]
    assert source_bitmap, f'Unresolved texture default: {name}'
    if source_bitmap.startswith('shaders\\default_bitmaps\\'):
        # Reuse stock H3's corresponding neutral/default asset.
        bitmap_tag = source_bitmap
        assert (KIT/'tags'/bitmap_tag).is_file(), bitmap_tag
    else:
        basename = Path(source_bitmap).stem
        bitmap_tag = PREFIX + '\\' + basename + '.bitmap'
        image = (REACH/'data'/source_bitmap).with_suffix('.tiff')
        assert image.is_file(), image
        target_image = (KIT/'data'/bitmap_tag).with_suffix('.tif')
        target_bitmap = KIT/'tags'/bitmap_tag
        template_reference = parameter.find("field[@name='bitmap']").get('value')
        template_name, group = template_reference.rsplit(',',1)
        assert group == 'bitm' and template_name
        template = KIT/'tags'/(template_name+'.bitmap')
        remember(image)
        remember(template)
        if bitmap_tag not in imported:
            assert not target_bitmap.exists() and not target_image.exists(), f'Terrain image target exists; inspect before rerun: {target_bitmap}'
            target_image.parent.mkdir(parents=True,exist_ok=True)
            target_bitmap.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(image,target_image)
            shutil.copyfile(template,target_bitmap)
            if 'bump_map' in name:
                # H3 usage 17 is ZBrush Bump Map (from Bump Map), for RGB normals.
                # The stock terrain donor instead expects a grayscale height image.
                tool('patch-tag-field',bitmap_tag,'bitmap_block_struct[0].Usage','ZBrush Bump Map (from Bump Map)')
            tool('bitmap_single',str(Path(bitmap_tag).with_suffix('.tif')))
            if 'bump_map' in name:
                normal_xml=logs/(basename+'.bitmap.xml')
                tool('export-tag-to-xml',str(target_bitmap),str(normal_xml))
                assert xml(normal_xml).find("field[@name='Usage']").get('value')=='ZBrush Bump Map (from Bump Map)'
            imported[bitmap_tag]=dict(source=str(image),template=str(template),image_sha256=hashes[str(image)])
    field_base=f"shader_terrain_struct_definition[0].render_method[0].parameters[{parameter.get('index')}]"
    reference=bitmap_tag.rsplit('.',1)[0]+',bitm'
    tool('patch-tag-field',TARGET,field_base+'.bitmap',reference)
    bindings.append(dict(input=name,reference=reference,source=source_bitmap))
    source_animations=source_parameter.get('animated parameters',{}).get('elements',[])
    target_animations=parameter.find("block[@name='animated parameters']")
    if len(source_animations) != len(target_animations):
        if source_animations:
            raise RuntimeError(f'Texture animation block mismatch: {name}; do not invent a replacement')
        # Neutral detail-normal inputs can retain existing transform settings.
        continue
    for index,(original,target) in enumerate(zip(source_animations,target_animations)):
        fields={f['name']:f for f in original}
        assert fields['type']['value']=='2' and target.get('name')=='scale uniform', name
        assert fields['input name']['value']==fields['range name']['value']==''
        assert float(fields['time period']['value'])==0
        function=next(f for f in fields['function']['elements'][0] if f['name']=='data')
        encoded=function['data_base64'].rstrip('=')
        tool('patch-tag-field',TARGET,field_base+f'.animated parameters[{index}].function[0].data',
             'function_definition_data,'+encoded)
        expected_functions.append(dict(input=name,index=index,data_base64=encoded))

export=logs/'terrain.shader_terrain.xml'
tool('export-tag-to-xml',str(target_path),str(export))
trial=xml(export)
assert ET.tostring(trial.find("block[@name='options']"))==ET.tostring(donor_xml.find("block[@name='options']"))
for row in bindings:
    p=trial.find(f"block[@name='parameters']/element[@name='{row['input']}']")
    assert p.find("field[@name='bitmap']").get('value')==row['reference']
for row in expected_functions:
    p=trial.find(f"block[@name='parameters']/element[@name='{row['input']}']/block[@name='animated parameters']/element[@index='{row['index']}']/field[@name='data']")
    actual=p.get('value').split(',',1)[1]
    assert actual==row['data_base64'], row['input']
for path,before in hashes.items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==before, path
report=dict(source=SOURCE,stock_donor=DONOR,target=TARGET,stock_shader_options_unchanged=True,
            original_hashes=hashes,bindings=bindings,texture_functions=expected_functions,imports=imported,calls=calls,
            limitation='Saved authoring fields verified only. Stock H3 ground uses diffuse terrain layers; Reach uses specular layers. Color, normal maps, blending, collision material and actual MCC appearance remain unverified.')
(OUT/'terrain-trial-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('H3_TERRAIN_TRIAL_AUTHORED',len(imported),'images',len(bindings),'texture bindings',len(expected_functions),'source texture functions',flush=True)
