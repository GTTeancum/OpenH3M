"""Read saved native placements and ensure unrelated scenario data is unchanged."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def xml(p):return ET.fromstring(p.read_text(encoding='utf-8',errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
def f(e,n):return e.find(f"field[@name='{n}']").get('value')
def block(e,n):return e.find(f"block[@name='{n}']")
def canonical(e):return ET.canonicalize(ET.tostring(e,encoding='unicode'),strip_text=True)
plan=json.loads((OUT/'h3-static-prop-placement-plan.json').read_text(encoding='utf-8'))
backup=OUT/'scenario-before-static-props.scenario';assert sha(backup)==plan['ScenarioSha256']
baseline=KIT/'tags/levels/custom/battle_canyon_audit/before_static_props.scenario'
if baseline.exists():assert sha(baseline)==sha(backup)
else:shutil.copyfile(backup,baseline)
scenario=KIT/'tags/levels/custom/battle_canyon_fresh/battle_canyon_fresh.scenario'
before=sha(scenario);env=os.environ.copy()
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/path)
for tag,name in [(scenario,'h3-static-props-saved'),(baseline,'h3-static-props-baseline')]:
    with (OUT/(name+'.log')).open('wb') as log:
        subprocess.run([str(KIT/'tool.exe'),'export-tag-to-xml',str(tag),str(OUT/(name+'.xml'))],cwd=KIT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,check=True)
assert sha(scenario)==before and sha(baseline)==sha(backup)
a=xml(OUT/'h3-static-props-baseline.xml');b=xml(OUT/'h3-static-props-saved.xml')
assert len(a)==len(b)
for x,y in zip(a,b):
    assert x.tag==y.tag and x.get('name')==y.get('name')
    if x.get('name') not in ('crates','crate palette'):assert canonical(x)==canonical(y),x.get('name')
for category in ('crates','crate palette'):
    for x,y in zip(block(a,category),block(b,category)):assert canonical(x)==canonical(y)
assert len(block(b,'crates'))==len(block(a,'crates'))+9
assert len(block(b,'crate palette'))==len(block(a,'crate palette'))+2
source=OUT/'original-lighting-scenario.xml';assert sha(source)==plan['SourceXmlSha256']
sources={};category=None
for e in xml(source):
    if e.tag=='field':category=e.get('name')
    elif e.tag=='element' and category=='crates':sources[int(e.get('index'))]=e
for row,e in zip(plan['Placements'],list(block(b,'crates'))[len(block(a,'crates')):]):
    s=sources[row['SourceIndex']];assert f(s,'type')==row['SourceType']
    assert sha(KIT/'tags'/row['TargetTag'])==row['TargetSha256']
    p=block(b,'crate palette')[int(f(e,'type').split(',')[-1])]
    assert f(p,'name')==row['TargetTag'].rsplit('.',1)[0]+',bloc'
    for name in ('position','rotation','scale','spawn order','quota minimum','quota maximum','spawn time','abandonment time','boundary width or radius','boundary box length','boundary positive height','boundary negative height','natural respawn weight'):
        u=[float(v) for v in f(e,name).split(',')];v=[float(v) for v in f(s,name).split(',')]
        assert len(u)==len(v) and all(abs(x-y)<=max(1e-5,abs(y)*2e-6) for x,y in zip(u,v)),(row,name)
    for name in ('owner team','game engine symmetric placement','remapping policy','boundary shape','teleporter channel','bsp policy','Pathfinding policy'):assert f(e,name)==f(s,name),(row,name)
    for name in ('game engine flags','spawn flags','placement flags','transform flags'):
        flags={x.strip() for x in (e.find(f"field[@name='{name}']").text or '').splitlines() if x.strip()}
        expected=row['Mode'] if name=='game engine flags' else '' if name=='spawn flags' else f(s,name)
        assert flags==({expected} if expected else set()),(row,name,flags)
    assert int(f(e,'unique id'))==row['UniqueId'] and f(e,'name')==',-1'
ids=[f(e,'unique id') for e in block(b,'crates')];assert len(ids)==len(set(ids))
report=dict(scenario_sha256=before,added=len(plan['Placements']),crate_count=len(block(b,'crates')),new_palette_entries=2,
    unrelated_sections_unchanged=len(a)-2,existing_placements_unchanged=True,stock_tags_unchanged=True,
    saved_transforms_boundaries_mode_flags_and_ids_verified=True,limitation=plan['limitation'])
(OUT/'h3-static-prop-placement-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('STATIC_PROP_PLACEMENTS_VERIFIED',json.dumps(report),flush=True)
