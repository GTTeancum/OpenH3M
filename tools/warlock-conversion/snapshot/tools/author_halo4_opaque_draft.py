"""Author Haven's opaque draft through the existing official H3 shader API.

This is a staged material binding, not appearance acceptance. Unsupported
source features remain named in each record for subsequent authoring.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'work/halo4-to-h3/haven'
KIT=ROOT/'work/editing-kits/h3ek'
reflection_mode='--reflections' in sys.argv
DEST=OUT/'material-authoring'/('reflection-draft' if reflection_mode else 'opaque-draft')
DEST.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
materials=read(OUT/'haven-material-input-audit.json')['materials']
functions=read(OUT/'haven-material-function-audit.json')['materials']
imports=read(OUT/'bitmap-import/ordinary-2d.json')
assert imports['status']=='native_import_and_metadata_pass'
bitmaps={r['source']:r['target'] for r in imports['images']}
bitmaps.update({r['source']:r['target'] for r in read(OUT/'haven-stock-bitmap-bindings.json')['bindings']})
if reflection_mode:
    special=read(OUT/'bitmap-import/special.json')
    assert special['status']=='native_import_and_metadata_pass'
    bitmaps.update({r['source']:r['target'] for r in special['images']})
configurations={r['path']:r for r in read(ROOT/'work/stock-h3-audit/stock-shader-configurations.json')}
options=read(ROOT/'work/stock-h3-audit/h3-effective-shader-options.json')
types={'bitmap':0,'color':1,'real':2,'int':3,'bool':4,'argb color':5}
animation_types={'VALUE':(0,'value'),'COLOR':(1,'color'),'SCALE_X':(3,'scale x'),'SCALE_Y':(4,'scale y')}
env=os.environ.copy()
for key,suffix in [('TEMP','temp'),('TMP','temp'),('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local')]:
    env[key]=str(OUT/'h3-authoring'/suffix)
report_path=DEST/'report.json'
assert not report_path.exists(),'Preserve existing authoring evidence'
report=dict(status='running',materials=[],deferred_materials=[],actual_rendering_verified=False)
for source,material in materials.items():
    family=Path(material['material_shader']).stem
    selected=(family.startswith('srf_blinn_reflection') if reflection_mode else family.startswith('srf_blinn') or family=='srf_lambert')
    if not selected:
        report['deferred_materials'].append(source)
        continue
    assert material['alpha_blend_mode']=='opaque'
    assert sha(KIT.parent/'h4ek/tags'/source)==material['source_sha256']
    lambert=family=='srf_lambert'
    params=material['parameters'];funcs=functions.get(source,{})
    donor=(r'levels\dlc\bunkerworld\sky\shaders\road.shader' if lambert else
        r'levels\dlc\bunkerworld\shaders\bunker_concrete_ext_layer.shader' if 'normal_detail_map' in params else
        r'levels\dlc\bunkerworld\shaders\bunker_concrete_ext.shader')
    if reflection_mode:
        donor=(r'levels\multi\salvation\shaders\panel_deco_trim.shader' if 'normal_detail_map' in params else
            r'levels\dlc\bunkerworld\shaders\bunker_plate_brackets.shader')
    stock=configurations[donor]
    assert sha(KIT/'tags'/donor)==stock['sha256']
    active={n:v for c in options[donor] for n,v in c['parameters'].items()}
    identifier=('h4_reflection_' if reflection_mode else 'h4_')+hashlib.sha256(source.encode()).hexdigest()[:12]
    target=rf'levels\custom\haven_h4\shaders\{identifier}.shader'
    assert not (KIT/'tags'/target).exists()
    plan=dict(Kit=str(KIT),Donor=donor,Target=target,Parameters=[],RemoveParameters=[])
    mapped=set()
    def add(target_name,source_name):
        if source_name not in params:return
        p=params[source_name];definition=active[target_name]
        row=dict(Name=target_name,Type=types[definition['parameter type']],Animations=[])
        if row['Type']==0:
            bitmap=p['effective_static'].replace('\\','/')
            row['Bitmap']=bitmaps[bitmap].replace('/','\\')
            assert (KIT/'tags'/row['Bitmap']).is_file()
        elif row['Type']==2:row['Real']=p['effective_static']
        elif row['Type'] in (1,5):
            # Unauthored white uses the native option's white default.
            assert funcs.get(source_name) or p['effective_static']==[1.,1.,1.,1.]
        for f in funcs.get(source_name,[]):
            index,name=animation_types[f['animated_type']]
            row['Animations'].append(dict(Type=index,TypeName=name,Input=f['source_input'],Range=f['range'],
                Period=f['time_period'],DataBase64=f['data_base64']))
        if row['Type']==2 and not row['Animations']:
            row['Animations']=[dict(Type=0,TypeName='value',Input='',Range='',Period=0,Constant=row['Real'])]
        if row['Type'] not in (1,5) or row['Animations']:plan['Parameters'].append(row)
        mapped.add(source_name)
    add('base_map','color_map');add('albedo_color','albedo_tint')
    # A neutral stock detail replaces the donor's authored concrete pattern.
    plan['Parameters'].append(dict(Name='detail_map',Type=0,Bitmap=r'shaders\default_bitmaps\bitmaps\default_detail.bitmap',Animations=[]))
    if not lambert:
        for target_name,source_name in [('bump_map','normal_map'),('bump_detail_map','normal_detail_map'),
            ('bump_detail_coefficient','detail_normals'),('diffuse_coefficient','diffuse_intensity'),
            ('specular_coefficient','specular_intensity'),('normal_specular_power','specular_power_max'),
            ('glancing_specular_power','specular_power_min'),('normal_specular_tint','specular_color'),
            ('glancing_specular_tint','specular_color'),('albedo_specular_tint_blend','specular_mix_albedo')]:
            if target_name in active:add(target_name,source_name)
        if reflection_mode:
            add('environment_map','reflection_map')
            add('env_tint_color','reflection_color')
            add('environment_map_specular_contribution','reflection_intensity')
    else:
        assert params['normal_map']['effective_static'].endswith('/default_normal.bitmap')
        assert params['diffuse_intensity']['effective_static']==1
        assert all(f.get('constant')==1 for f in funcs.get('diffuse_intensity',[]))
        mapped.update(('normal_map','diffuse_intensity'))
    names={p['Name'] for p in plan['Parameters']}
    assert len(names)==len(plan['Parameters'])
    plan['RemoveParameters']=[p['name'] for p in stock['parameters'] if p['name'] not in names]
    path=DEST/(identifier+'.json');path.write_text(json.dumps(plan,indent=2)+'\n')
    with (DEST/(identifier+'.log')).open('wb') as stream:
        result=subprocess.run([str(OUT/'h3-api/ApplyHavenShaderPlan.exe'),str(path)],cwd=KIT,env=env,
            stdout=stream,stderr=subprocess.STDOUT,timeout=45)
    assert result.returncode==0,(source,DEST/(identifier+'.log'))
    assert sha(KIT/'tags'/donor)==stock['sha256']
    native=read(Path(str(path)+'.readback.json'))
    assert {r['name'] for r in native}==names
    row=dict(source=source,source_sha256=material['source_sha256'],family=family,target=target,
        target_sha256=sha(KIT/'tags'/target),donor=donor,donor_sha256=stock['sha256'],
        parameters_authored=len(names),mapped_source_parameters=sorted(mapped),
        pending_source_parameters=sorted(set(params)-mapped),physical_material=material['physics_material'],
        physical_material_binding_pending=True,
        shading_limitations=[] if lambert else ['H3 two-lobe Phong draft response needs visual comparison to H4 Blinn.',
            'Control-map specular/gloss channel packing and source vertex occlusion remain pending.',
            'Normal-detail distance fade remains pending; source detail coefficient and UV scales retained.'])
    if reflection_mode:
        row['shading_limitations'].extend(['Source reflection masks/Fresnel controls and roughness response remain pending.',
            'Cube face content checked; world-space orientation and color response need native visual verification.'])
    report['materials'].append(row)
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print('H4_OPAQUE_SHADER_AUTHORED',len(report['materials']),source,flush=True)
expected=35 if reflection_mode else 59
assert len(report['materials'])==expected and len(report['deferred_materials'])==75-expected
physical_plan=dict(Kit=str(KIT),Output=str(DEST/'physical-materials-applied.json'),Tags=[
    dict(Path=r['target'],Fields={'material name':r['physical_material']}) for r in report['materials']])
physical_path=DEST/'physical-materials-apply-plan.json'
physical_path.write_text(json.dumps(physical_plan,indent=2)+'\n')
with (DEST/'physical-materials-apply.log').open('wb') as stream:
    result=subprocess.run([str(OUT/'h3-api/ApplyHavenMaterialNames.exe'),str(physical_path),'--apply'],
        cwd=KIT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=45)
assert result.returncode==0
readback=read(Path(physical_plan['Output']))
assert readback['applied'] and len(readback['tags'])==expected
updates=[]
for row in report['materials']:
    after=sha(KIT/'tags'/row['target'])
    updates.append(dict(target=row['target'],before_sha256=row['target_sha256'],after_sha256=after))
    row['shader_hash_before_physical_material']=row['target_sha256']
    row['target_sha256']=after;row['physical_material_binding_pending']=False
(DEST/'physical-material-update.json').write_text(json.dumps(dict(updates=updates,
    official_api_readback=str(Path(physical_plan['Output']).relative_to(ROOT))),indent=2)+'\n')
report['status']='native_authoring_readback_pass_draft'
report_path.write_text(json.dumps(report,indent=2)+'\n')
