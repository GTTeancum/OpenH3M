"""Plan Haven's native scenario using authored points and stock H3 roles.

Reads existing official-API JSON and unmodified TagTool text; no cache decoder.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'work/halo4-to-h3/haven'
DEST=OUT/'scenario-authoring';DEST.mkdir(exist_ok=True)
KIT=ROOT/'work/editing-kits/h3ek'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def field(row,name):return next(v for k,v in row.items() if k.rsplit(':',1)[-1]==name)
def text(v):
    if isinstance(v,dict):
        if 'name' in v:return v['name']
        if 'set_flags' in v:
            assert len(v['set_flags'])<=1
            return '|'.join(v['set_flags'])
        raise ValueError(v)
    if isinstance(v,list):return ','.join(map(str,v))
    return str(v)
source=OUT/'haven-scenario-authoring-inventory.json'
inventory=json.loads(source.read_text());assert inventory['status']=='complete' and inventory['source_tags_unchanged']
original_inventory=json.loads((OUT/'haven-source-inventory.json').read_text())
for relative,row in original_inventory['tags'].items():
    if relative.endswith('.scenario'):assert sha(KIT.parent/'h4ek/tags'/relative)==row['sha256']
tags={}
for line in (DEST/'construct-all-tags.log').read_text().splitlines():
    match=re.match(r'^\[Index: (0x[0-9A-F]+), Offset: (0x[0-9A-F]+)\] (.*)\.([^.]*)$',line)
    if match:tags[match[1]]=dict(path=match[3]+'.'+match[4],cache_index=match[1])
assert tags
stock_by_path={r['path']:r for r in tags.values()}
palette=[];category=None;current=None
palette_text=(DEST/'construct-forge-palette.log').read_text()
assert 'ERROR' not in palette_text.upper()
for line in palette_text.splitlines():
    marker=re.search(r'CATEGORY (\w+)',line)
    if marker:category=marker[1]
    obj=re.search(r'Object: CachedTag = \[(0x[0-9A-F]+)\] (.*?)\s*$',line)
    if obj:
        assert obj[2]==tags[obj[1]]['path']
        current=dict(Category=category,Path=obj[2]);palette.append(current)
    for name,pattern in [('Name',r'^Name: StringId = (.*?)\s*$'),('Maximum',r'^MaxAllowed: Int32 = (\d+)\s*$'),('Cost',r'^Cost: Single = ([\d.]+)\s*$')]:
        match=re.search(pattern,line)
        if match:current[name]=match[1] if name=='Name' else float(match[1]) if name=='Cost' else int(match[1])
assert all(len(r)==5 for r in palette)
main=inventory['scenarios']['levels/multi/wraparound/wraparound.scenario']
start=main['player starting locations'][0]
source_path='levels/multi/wraparound/wraparound_spawns.scenario'
spawns=inventory['scenarios'][source_path]
source_palette=[field(r,'name') for r in spawns['scenery palette']]
placements=[];pending=[]
for index,row in enumerate(spawns['scenery']):
    asset=source_palette[field(row,'type')];name=Path(asset).stem
    obj=field(row,'object data')[0];mp=field(row,'multiplayer data')[0]
    label=field(mp,'megalo label');targets=[]
    if name in ('respawn_point','respawn_point_invisible'):targets=[asset]
    elif name=='initial_spawn_point':
        assert label in ('fld_spawn','ffa_spawn','team_spawn')
        modes=['infection'] if label=='fld_spawn' else ['slayer','ctf','assault','koth','oddball','territories','vip']
        targets=[f'objects/multi/{mode}/{mode}_initial_spawn_point.scenery' for mode in modes]
    else:
        pending.append(dict(source_index=index,source=asset,label=label,reason='Mode-specific respawn-zone or cinematic camera mapping remains separate.'))
        continue
    assert field(obj,'node orientations')==[]
    fields={}
    for n in ('placement flags','position','rotation','scale','transform flags','bsp policy'):
        fields['Struct:object data/'+n]=text(field(obj,n))
    for n in ('game engine symmetric placement','game engine flags','owner team','spawn order','quota minimum','quota maximum',
        'spawn flags','spawn time','abandonment time','remapping policy','boundary shape','teleporter channel',
        'boundary width or radius','boundary box length','boundary positive height','boundary negative height'):
        fields['Struct:multiplayer data/'+n]=text(field(mp,n))
    if fields['Struct:multiplayer data/owner team']=='eighth party':fields['Struct:multiplayer data/owner team']='eigth party'
    if fields['Struct:multiplayer data/spawn flags']=='hide unless megalo required':
        assert name=='initial_spawn_point'
        fields['Struct:multiplayer data/spawn flags']=''
    identity=field(obj,'object id')[0]
    fields['Struct:object data/Struct:object id/source']=text(field(identity,'source'))
    fields['Struct:object data/Struct:object id/type']='scenery'
    for target in targets:
        target=target.replace('/','\\');assert target in stock_by_path,target
        assert (KIT/'tags'/target).is_file()
        placements.append(dict(SourceScenario=source_path,SourceIndex=index,SourceTag=asset,SourceLabel=label,
            Target=target,TargetSha256=sha(KIT/'tags'/target),OriginalCacheIndex=stock_by_path[target]['cache_index'],
            UniqueId=-1700000000+len(placements),Fields=fields))
assert len(placements)==510 and len(pending)==20
assert len({r['SourceIndex'] for r in placements})==174
plan=dict(Kit=str(KIT),Target=r'levels\custom\haven_h4\haven_draft',Donor=r'levels\multi\construct\construct',
    Bsp=r'levels\custom\haven_geometry_probe\haven_one_sided_joined_surfaces_opaque_draft',
    LightingInfo=r'levels\custom\haven_geometry_probe\haven_one_sided_joined_surfaces_opaque_draft',
    Design=r'levels\custom\haven_h4\haven',StartPosition=field(start,'position'),StartFacing=field(start,'facing'),
    Forge=palette,Placements=placements,Output=str(DEST/'native-scenario-readback.json'),
    SourceInventorySha256=sha(source),StockCache=json.loads((DEST/'construct-integrity.json').read_text()),
    PendingSpawnRecords=pending,ForgeCounts=dict(Counter(r['Category'] for r in palette)),
    Scope='Editor draft: original positions/teams; stock H3 mode-specific initial points replace H4 scripted labels. '
        'Mode/team spawn behavior, remaining zones/cameras/objectives/ordnance/audio and native packaging remain unverified. '
        'Copy donor map ID for this private editor stage only; release identity remains pending.')
path=DEST/'scenario-plan.json';assert not path.exists()
path.write_text(json.dumps(plan,indent=2)+'\n')
print('H4_SCENARIO_PLANNED',len(placements),'stock spawn objects from 174 source records;',len(palette),'stock Forge entries')
