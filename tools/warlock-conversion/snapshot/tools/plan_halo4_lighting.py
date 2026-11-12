"""Map source static-light fields into supported native H3 authoring inputs."""
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'work/halo4-to-h3/haven'
KIT=ROOT/'work/editing-kits/h3ek'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def field(row,name):return next(v for k,v in row.items() if k.rsplit(':',1)[-1]==name)
def constant(row,name):
    data=field(row,name)[0]
    assert field(data,'Input Variable')==field(data,'Range Variable')==''
    value=next(v for k,v in data.items() if k.endswith('/Custom:Mapping'))
    assert value['MasterType']=='Basic' and value['IsRanged']=='False'
    return float(value['ClampRangeMin'])
def number(v):return format(v,'.9g')
def vector(v):return ','.join(map(number,v))
inventory=read(OUT/'haven-lighting-source.json')
source='levels/multi/wraparound/wraparound_000.scenario_structure_lighting_info'
entry=inventory['tags'][source];assert sha(KIT.parent/'h4ek/tags'/source)==entry['sha256']
fields=entry['fields'];defs=fields['Block:generic light definitions'];instances=fields['Block:generic light instances']
assert len(defs)==len(instances)==194
with_sky='--sky' in sys.argv
world_render='--world-render' in sys.argv
assert not world_render or with_sky
sky_source=None
if with_sky:
    sky_inventory=read(OUT/'haven-sky-lighting-source.json')
    sky_source,sky_entry=next(iter(sky_inventory['tags'].items()))
    assert sha(KIT.parent/'h4ek/tags'/sky_source)==sky_entry['sha256']
    extra_defs=sky_entry['fields']['Block:generic light definitions']
    extra_instances=sky_entry['fields']['Block:generic light instances']
    assert len(extra_defs)==len(extra_instances)==96
    for instance in extra_instances:
        key=next(k for k in instance if k.endswith(':Light Definition Index'))
        instance[key]+=len(defs)
    defs+=extra_defs;instances+=extra_instances
base=read(OUT/'scenario-authoring/scenario-plan.json')['LightingInfo']
target=r'levels\custom\haven_h4\haven_lighting'
previous=target if with_sky else base
if with_sky:target+='_with_sky'
stem='native-lighting-with-sky' if with_sky else 'native-lighting'
if world_render:
    previous=target
    target=r'levels\custom\haven_h4\haven_lighting_worldrender'
    base=r'levels\custom\haven_geometry_probe\haven_one_sided_joined_surfaces_opaque_draft_reflections_worldrender'
    stem='native-lighting-worldrender'
plan=dict(Kit=str(KIT),Scenario=r'levels\custom\haven_h4\haven_draft',SourceTag=base,TargetTag=target,
    PreviousTag=previous,ExpectedCount=len(defs),
    Output=str(OUT/'h3-authoring'/(stem+'-authored.json')),
    Backup=str(OUT/'h3-authoring'/('scenario-before-'+stem+'-setup.scenario' if with_sky else 'scenario-before-lighting-setup.scenario')),
    SourceSha256=sha(KIT/'tags'/(base+'.scenario_structure_lighting_info')),Definitions=[],Instances=[],
    SourceH4=source,SourceH4Sha256=entry['sha256'],Pending=[])
if sky_source:plan.update(SourceH4Sky=sky_source,SourceH4SkySha256=sky_entry['sha256'])
if world_render:
    plan.update(TargetBsp=base,PreviousBsp=read(OUT/'scenario-authoring/scenario-plan.json')['Bsp'])
for index,d in enumerate(defs):
    p=field(d,'Midnight_Light_Parameters')[0];kind=field(p,'Light Type')['name']
    assert field(p,'Lighting Mode')['name']=='Artistic'
    assert field(p,'Cone Projection Shape')['name']=='Cone' and field(p,'Aspect Ratio')==1
    assert field(p,'Gobo Tag Path') is None and field(p,'Lens Flare') is None
    inner=field(p,'Inner Cone Angle');outer=constant(p,'Outer Cone End')
    start=field(p,'Distance Attenuation Start');end=constant(p,'Distance Attenuation End')
    assert start<=end and (kind!='Spot' or 0<=inner<=outer<=180)
    plan['Definitions'].append(dict(SourceIndex=index,Name=field(p,'haloLightNode'),Fields={
        'type':{'Point':'omni','Spot':'spot','Directional':'directional'}[kind],
        'flags':'use far attenuation' if kind!='Directional' else '',
        'shape':'circle','color':vector(field(p,'Light Color')),
        'intensity':number(constant(p,'Intensity')),
        'hotspot size':number(math.radians(inner)),
        'hotspot falloff size':number(math.radians(outer)),
        'near attenuation bounds':'0,0','far attenuation bounds':vector([start,end]),'aspect':'1'}))
    plan['Pending'].append(dict(SourceIndex=index,IndirectAmplification=field(d,'indirect amplification factor'),
        JitterSphereRadius=field(d,'jitter sphere radius'),JitterAngle=field(d,'jitter angle'),
        Sun=field(d,'sun'),SourceShadowControl=field(p,'Shadows'),
        SourceScreenspaceControl=field(p,'Screenspace Light'),SpecularContribution=field(p,'Specular Contribution')))
for index,i in enumerate(instances):
    assert field(i,'light mode')['name']=='Static'
    definition=field(i,'Light Definition Index');assert 0<=definition<len(defs)
    forward=field(i,'forward');up=field(i,'up')
    assert abs(sum(v*v for v in forward)-1)<.0001 and abs(sum(v*v for v in up)-1)<.0001
    plan['Instances'].append(dict(SourceIndex=index,Fields={'definition index':str(definition),
        'origin':vector(field(i,'origin')),'forward':vector(forward),'up':vector(up)}))
plan['Limitations']=['Source authored values retained; cross-engine illumination and attenuation response need actual render comparison.',
    'H3 generic-light schema lacks source indirect amplification, sun/jitter and dynamic-only controls; retained in Pending, not silently accepted.',
    ('Sky-model lights are included as native generic directional lights; their rendered response remains unverified.' if with_sky else 'Additional sky-model lights remain separate work.'),
    'Material emission and atmosphere remain separate work. No bake or visual acceptance.']
path=OUT/'h3-authoring'/(stem+'-plan.json');path.write_text(json.dumps(plan,indent=2)+'\n')
print('H4_LIGHTING_PLAN',len(plan['Definitions']),'definitions',len(plan['Instances']),'instances')
