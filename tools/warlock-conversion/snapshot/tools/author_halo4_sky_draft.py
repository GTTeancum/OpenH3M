"""Bind the authored H4 sky artwork through existing H3 shader authoring APIs.

Draft only: source vertex fades, scrolling and secondary tower emission remain
explicit follow-ups; this does not accept their omission from the final port.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'work/halo4-to-h3/haven'
KIT=ROOT/'work/editing-kits/h3ek'
DEST=OUT/'material-authoring/sky-draft'
DEST.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
materials=read(OUT/'haven-material-input-audit.json')['materials']
functions=read(OUT/'haven-material-function-audit.json')['materials']
bitmaps={r['source']:r['target'] for r in read(OUT/'bitmap-import/ordinary-2d.json')['images']}
stock={r['path']:r for r in read(ROOT/'work/stock-h3-audit/stock-shader-configurations.json')}
options=read(ROOT/'work/stock-h3-audit/h3-effective-shader-options.json')
black=functions['environments/shared/skies/wraparound_sky/wa_bigclouds.material']['si_color']
assert black[0]['constant']==[0.,0.,0.,1.]
env=os.environ.copy()
for key,suffix in [('TEMP','temp'),('TMP','temp'),('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local')]:
    env[key]=str(OUT/'h3-authoring'/suffix)
report=dict(status='authoring',materials=[],actual_rendering_verified=False)
assert not (DEST/'report.json').exists(),'Preserve previous authoring evidence'
for source,m in materials.items():
    if '/skies/wraparound_sky/' not in source:continue
    assert sha(KIT.parent/'h4ek/tags'/source)==m['source_sha256']
    blend=m['alpha_blend_mode']
    donor={
        'opaque':r'levels\dlc\bunkerworld\sky\shaders\dish_illum_red.shader',
        'alpha_blend':r'levels\dlc\docks\sky\shaders\clouds_horizon_sun.shader',
        'additive':r'levels\dlc\chillout\shaders\z_flood_lightpanel.shader',
        'add_src_times_srcalpha':r'levels\dlc\chillout\shaders\z_flood_lightpanel.shader',
    }[blend]
    assert sha(KIT/'tags'/donor)==stock[donor]['sha256']
    active={n:p for c in options[donor] for n,p in c['parameters'].items()}
    ps=m['parameters'];fs=functions.get(source,{})
    identifier='h4_sky_'+hashlib.sha256(source.encode()).hexdigest()[:12]
    target=rf'levels\custom\haven_h4\shaders\{identifier}.shader'
    assert not (KIT/'tags'/target).exists()
    plan=dict(Kit=str(KIT),Donor=donor,Target=target,Parameters=[],RemoveParameters=[])
    def parameter(name,typ,funcs=(),**values):
        assert name in active
        row=dict(Name=name,Type=typ,Animations=[],**values)
        for f in funcs:
            index,label={'COLOR':(1,'color'),'VALUE':(0,'value'),'SCALE_X':(3,'scale x'),'SCALE_Y':(4,'scale y')}[f['animated_type']]
            row['Animations'].append(dict(Type=index,TypeName=label,Input=f['source_input'],Range=f['range'],Period=f['time_period'],DataBase64=f['data_base64']))
        plan['Parameters'].append(row)
    bitmap=bitmaps[ps['color_map']['effective_static']].replace('/','\\')
    parameter('self_illum_map',0,fs.get('color_map',[]),Bitmap=bitmap)
    if 'base_map' in active:parameter('base_map',0,fs.get('color_map',[]),Bitmap=bitmap)
    if 'detail_map' in active:parameter('detail_map',0,Bitmap=r'shaders\default_bitmaps\bitmaps\default_detail.bitmap')
    # Black diffuse contribution and independent emission reproduce the
    # existing stock unlit-sky authoring pattern; source bitmap alpha remains.
    parameter('albedo_color',5,black)
    if 'no_dynamic_lights' in active:parameter('no_dynamic_lights',4,Integer=1)
    color=fs.get('albedo_tint')
    if color:parameter('self_illum_color',1,color)
    else:assert ps['albedo_tint']['effective_static']==[1.,1.,1.,1.]
    parameter('self_illum_intensity',2,fs['diffuse_intensity'],Real=ps['diffuse_intensity']['effective_static'])
    names={p['Name'] for p in plan['Parameters']}
    plan['RemoveParameters']=[p['name'] for p in stock[donor]['parameters'] if p['name'] not in names]
    path=DEST/(identifier+'.json');path.write_text(json.dumps(plan,indent=2)+'\n')
    with (DEST/(identifier+'.log')).open('wb') as log:
        run=subprocess.run([str(OUT/'h3-api/ApplyHavenShaderPlan.exe'),str(path)],cwd=KIT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=45)
    assert run.returncode==0,(source,run.returncode)
    assert {r['name'] for r in read(Path(str(path)+'.readback.json'))}==names
    assert sha(KIT/'tags'/donor)==stock[donor]['sha256']
    pending=[]
    if 'vertalpha' in m['material_shader']:pending.append('Source vertex-red opacity needs a matching H3 native shader path; texture alpha is draft only.')
    if ps['scroll_rate_u']['effective_static'] or ps['scroll_rate_v']['effective_static']:pending.append('Source scrolling time units and native mapping pending; draft is static.')
    if 'tower' in source:pending.append('Secondary tower-light texture and its animated intensity are pending; base tower artwork retained.')
    if 'lightshafts' in m['material_shader']:pending.append('Source alpha-weighted additive blend, view Fresnel and distance fades remain pending.')
    report['materials'].append(dict(source=source,source_sha256=m['source_sha256'],target=target,target_sha256=sha(KIT/'tags'/target),donor=donor,donor_sha256=stock[donor]['sha256'],source_blend=blend,pending=pending))
    print('H4_SKY_DRAFT',len(report['materials']),source,flush=True)
assert len(report['materials'])==11
report['status']='native_authoring_readback_pass_draft'
(DEST/'report.json').write_text(json.dumps(report,indent=2)+'\n')
