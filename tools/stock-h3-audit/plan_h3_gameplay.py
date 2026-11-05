"""Prepare stock H3 editor placements from the original Reach layout."""
import collections
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
source_xml=OUT/'original-lighting-scenario.xml'
source=ET.fromstring(source_xml.read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
inventory={r['name']:r['path']+'.'+r['group'] for r in csv.DictReader((OUT/'standoff-forge-no-vehicles.csv').open())}
audit=json.loads((OUT/'gameplay-extra-stock-audit.json').read_text())
for tag in audit['sources']['360']['tags']:inventory[Path(tag).stem]=tag
def f(e,name):return e.find('./field[@name="'+name+'"]').get('value')
groups={};current=None
for e in source:
    if e.tag=='field':current=e.get('name') if e.get('type')=='block' else None
    elif e.tag=='element' and current in ('scenery','weapons','equipment','crates'):groups.setdefault(current,[]).append(e)
rows=[];pending=[];excluded=[];base=json.loads((OUT/'h3-basic-placements-verification.json').read_text())
scenario=KIT/'tags/levels/custom/battle_canyon_fresh/battle_canyon_fresh.scenario'
assert hashlib.sha256(scenario.read_bytes()).hexdigest()==base['scenario_sha256']
zone_roles={'ctf_res_zone':'ctf_flag_at_home_respawn_zone','ctf_res_zone_away':'ctf_flag_away_respawn_zone','assault':'assault_respawn_zone'}
crate_roles={'as_bomb':['assault_bomb_spawn_point'],'as_goal':['assault_bomb_goal_area'],
    'ctf_flag_return':['ctf_flag_spawn_point','ctf_flag_return_area'],
    'oddball_ball':['oddball_ball_spawn_point'],'koth_hill':['koth_hill_static'],
    'terr_object':['territory_static'],'inf_haven':['infection_haven_static']}
for category,elements in groups.items():
    for e in elements:
        name=f(e,'type');label=f(e,'megalo label');selected=[]
        if category=='equipment' or (category=='scenery' and name=='respawn_point'):continue
        if category=='weapons':
            replacements={'dmr':'battle_rifle','grenade_launcher':'brute_shot','plasma_rifle':'plasma_rifle'}
            if name not in replacements:continue
            selected=[replacements[name]]
        elif category=='scenery':
            if name=='respawn_point_invisible':selected=[name]
            elif name=='initial_spawn_point':
                if label=='inf_spawn':selected=['infection_initial_spawn_point']
                else:
                    assert label in ('team_only','ffa_only'),label
                    selected=[mode+'_initial_spawn_point' for mode in ('slayer','ctf','assault','koth','oddball','territories','vip')]
            elif name=='respawn_zone' and label in zone_roles:selected=[zone_roles[label]]
        elif category=='crates':
            if name=='5thspartan':
                excluded.append(dict(category=category,index=int(e.get('index')),source=name,reason='Explicit user instruction: remove decorative Spartan doll'));continue
            if name=='ff_teleporter_2_way':selected=['teleporter_2way']
            elif name=='gravity_lift':selected=['gravlift_equipment']
            elif name in ('mp_flag_base','mp_circle','mp_hill_beacon'):
                if label in zone_roles:selected=[zone_roles[label]]
                elif label in crate_roles:selected=crate_roles[label]
        if not selected:
            pending.append(dict(category=category,index=int(e.get('index')),source=name,label=label,
                reason='Reach-only mode decision' if label in ('stockpile','stp_goal','stp_flag','hh_drop_point') else 'Separate original asset or gameplay authoring required'));continue
        for target in selected:
            tag=inventory[target];extension=tag.rsplit('.',1)[-1]
            destination={'scenery':'scenery','crate':'crates','weapon':'weapons','equipment':'equipment'}[extension]
            assert (KIT/'tags'/tag).is_file(),tag
            rows.append(dict(SourceBlock=category,SourceIndex=int(e.get('index')),SourceType=name,SourceLabel=label,
                TargetBlock=destination,TargetTag=tag,UniqueId=int(f(e,'unique id')) if len(selected)==1 else -1128267776+len(rows),
                TranslateScriptedFlag=f(e,'spawn flags')=='hide unless megalo required',
                TargetSha256=hashlib.sha256((KIT/'tags'/tag).read_bytes()).hexdigest()))
existing_ids={(category,int(f(e,'unique id'))) for category,es in groups.items() for e in es if category in ('equipment','weapons') or (category=='scenery' and f(e,'type')=='respawn_point')}
ids=[(r['TargetBlock'],r['UniqueId']) for r in rows];assert len(ids)==len(set(ids))
# Replacements retain their own source ID; expanded initial/objective markers
# receive editor IDs outside the source set, never duplicated placements' IDs.
for r in rows:
    if r['SourceBlock']=='weapons':existing_ids.discard(('weapons',r['UniqueId']))
assert not existing_ids.intersection(ids)
result=dict(ScenarioSha256=base['scenario_sha256'],SourceXmlSha256=hashlib.sha256(source_xml.read_bytes()).hexdigest(),Placements=rows,
    counts=dict(collections.Counter(r['TargetBlock'] for r in rows)),pending=pending,excluded=excluded,
    semantics='Keep native stock mode-specific tags and their game filters. Copy source teams, transforms, boundaries and spawn ordering. Reach scripted-required flags are represented by the selected native H3 role; no Megalo runtime is imported. Mode/team spawning behavior remains for MCC testing.')
(OUT/'h3-gameplay-plan.json').write_text(json.dumps(result,indent=2)+'\n')
print('H3_GAMEPLAY_PLAN',result['counts'],'pending',len(pending),'explicitly excluded',len(excluded),flush=True)
