"""Verify every added gameplay placement using saved official Tool XML."""
import collections
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=json.loads((OUT/'h3-gameplay-plan.json').read_text())
scenario=KIT/'tags/levels/custom/battle_canyon_fresh/battle_canyon_fresh.scenario';before=sha(scenario)
backup=OUT/'scenario-before-gameplay-setup.scenario';assert sha(backup)==plan['ScenarioSha256']
baseline=KIT/'tags/levels/custom/battle_canyon_audit/before_gameplay.scenario';baseline.parent.mkdir(parents=True,exist_ok=True)
if baseline.exists():assert sha(baseline)==sha(backup)
else:shutil.copyfile(backup,baseline)
env=os.environ.copy()
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/path)
for tag,name in [(scenario,'h3-gameplay-saved'),(baseline,'h3-gameplay-baseline')]:
    with (OUT/(name+'-export.log')).open('wb') as log:
        run=subprocess.run([str(KIT/'tool.exe'),'export-tag-to-xml',str(tag),str(OUT/(name+'.xml'))],cwd=KIT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    assert run.returncode==0 and (OUT/(name+'.xml')).stat().st_size>1000
assert sha(scenario)==before and sha(baseline)==sha(backup)
def xml(path):return ET.fromstring(path.read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
def f(e,n):return e.find('./field[@name="'+n+'"]').get('value')
def block(e,n):return e.find('./block[@name="'+n+'"]')
def canonical(e):return ET.canonicalize(ET.tostring(e,encoding='unicode'),strip_text=True)
source=xml(OUT/'original-lighting-scenario.xml');actual=xml(OUT/'h3-gameplay-saved.xml');old=xml(OUT/'h3-gameplay-baseline.xml')
assert sha(OUT/'original-lighting-scenario.xml')==plan['SourceXmlSha256']
sources={};current=None
for e in source:
    if e.tag=='field':current=e.get('name') if e.get('type')=='block' else None
    elif e.tag=='element' and current in ('scenery','weapons','equipment','crates'):sources[(current,int(e.get('index')))]=e
counts={};offsets={};changed=set();identities=set()
for category in plan['counts']:
    offsets[category]=len(block(old,category));counts[category]=len(block(actual,category))
    assert counts[category]==offsets[category]+plan['counts'][category]
    for previous,current in zip(block(old,category),block(actual,category)):
        assert canonical(previous)==canonical(current),('Existing object changed',category,previous.get('index'))
    changed.update([category,('weapon' if category=='weapons' else 'crate' if category=='crates' else category)+' palette'])
for row in plan['Placements']:
    category=row['TargetBlock'];index=offsets[category];offsets[category]+=1
    e=block(actual,category)[index];s=sources[(row['SourceBlock'],row['SourceIndex'])]
    assert sha(KIT/'tags'/row['TargetTag'])==row['TargetSha256']
    extension=row['TargetTag'].rsplit('.',1)[-1]
    palette=block(actual,('weapon' if category=='weapons' else 'crate' if category=='crates' else category)+' palette')
    reference=f(palette[int(f(e,'type').split(',')[-1])],'name')
    assert reference==row['TargetTag'].rsplit('.',1)[0]+','+{'weapon':'weap','scenery':'scen','crate':'bloc','equipment':'eqip'}[extension]
    for name in ('position','rotation','scale','spawn order','quota minimum','quota maximum','spawn time','abandonment time','boundary width or radius','boundary box length','boundary positive height','boundary negative height','natural respawn weight'):
        a=[float(v) for v in f(e,name).split(',')];b=[float(v) for v in f(s,name).split(',')]
        assert len(a)==len(b) and all(abs(x-y)<=max(1e-5,abs(y)*2e-6) for x,y in zip(a,b)),(row,name,a,b)
    for name in ('game engine symmetric placement','remapping policy','boundary shape','teleporter channel','bsp policy'):
        assert f(e,name)==f(s,name),(row,name)
    expected_team='eigth party' if f(s,'owner team')=='eighth party' else f(s,'owner team')
    assert f(e,'owner team')==expected_team and int(f(e,'unique id'))==row['UniqueId']
    for name in ('placement flags','transform flags','game engine flags','spawn flags'):
        element=e.find('./field[@name="'+name+'"]');flags={x.strip() for x in (element.text or '').splitlines() if x.strip()}
        expected='' if name=='spawn flags' and row['TranslateScriptedFlag'] else f(s,name)
        assert flags==({expected} if expected else set()),(row,name,flags,expected)
    assert f(e,'name')==',-1' and f(e,'editor folder')==',-1'
    assert all(p.get('value')==',-1' for p in e.findall('./field[@name="parent object"]'))
for category in counts:
    for e in block(actual,category):
        key=(category,int(f(e,'unique id')));assert key not in identities,key;identities.add(key)
assert len(old)==len(actual)
for a,b in zip(old,actual):
    assert a.tag==b.tag and a.get('name')==b.get('name')
    if a.get('name') not in changed:assert canonical(a)==canonical(b),a.get('name')
starts=collections.Counter(Path(row['TargetTag']).stem for row in plan['Placements'] if row['SourceType']=='initial_spawn_point')
assert starts=={**{m+'_initial_spawn_point':68 for m in ('slayer','ctf','assault','koth','oddball','territories','vip')},'infection_initial_spawn_point':24}
report=dict(scenario_sha256=before,baseline_sha256=sha(backup),plan_sha256=sha(OUT/'h3-gameplay-plan.json'),counts=counts,
    added=plan['counts'],initial_starts_by_native_mode=dict(starts),all_saved_transforms_boundaries_teams_and_spawn_settings_verified=True,
    existing_placements_and_other_scenario_sections_unchanged=True,source_pending=plan['pending'],explicitly_excluded=plan['excluded'],
    limitation='Native authoring/readback only. H3 team/FFA start selection, game objectives, teleporters and grav-lift traversal require MCC playtesting. Reach-only modes and other source objects remain unresolved as listed; no completion or acceptance is implied.')
(OUT/'h3-gameplay-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('H3_GAMEPLAY_VERIFIED',counts,'added',sum(plan['counts'].values()),'placements; native mode starts',dict(starts),flush=True)
