"""Verify every saved stock placement against the original Tool XML."""
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
tag=KIT/'tags/levels/custom/battle_canyon_fresh/battle_canyon_fresh.scenario';before=sha(tag)
env=os.environ.copy()
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/path)
native=OUT/'h3-basic-placements.xml'
backup=OUT/'scenario-before-basic-placements.scenario'
# Tool requires input tags beneath its tag root. Copy the unchanged checkpoint
# into an audit-only directory so the comparison always reads the real baseline.
baseline_tag=KIT/'tags/levels/custom/battle_canyon_audit/before_basic_placements.scenario'
baseline_tag.parent.mkdir(parents=True,exist_ok=True)
if baseline_tag.exists():assert sha(baseline_tag)==sha(backup)
else:shutil.copyfile(backup,baseline_tag)
baseline_xml=OUT/'scenario-before-basic-placements.xml'
for input_tag,output_xml in [(tag,native),(baseline_tag,baseline_xml)]:
    with (OUT/(output_xml.stem+'-export.log')).open('wb') as log:
        run=subprocess.run([str(KIT/'tool.exe'),'export-tag-to-xml',str(input_tag),str(output_xml)],cwd=KIT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    assert run.returncode==0 and output_xml.stat().st_size>1000
assert sha(tag)==before and sha(baseline_tag)==sha(backup)
def xml(path):return ET.fromstring(path.read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
def field(node,name):return node.find('./field[@name="'+name+'"]').attrib['value']
source=xml(OUT/'original-lighting-scenario.xml');actual=xml(native);earlier=xml(baseline_xml)
inventory={r['name']:r for r in csv.DictReader((OUT/'standoff-forge-no-vehicles.csv').open())}
groups={};current=None
for e in source:
    if e.tag=='field':current=e.get('name') if e.get('type')=='block' else None
    elif e.tag=='element' and current in ('scenery','weapons','equipment'):groups.setdefault(current,[]).append(e)
counts={};pending=[];ids=set();changes=set()
for category,expected_count in [('scenery',130),('weapons',13),('equipment',16)]:
    extension='weapon' if category=='weapons' else category
    palette_name=('weapon' if category=='weapons' else category)+' palette'
    stock=[]
    for e in groups[category]:
        name=field(e,'type');target='energy_blade' if name=='energy_sword' else name
        match=inventory.get(target)
        if (category=='scenery' and name!='respawn_point') or not match or match['group']!=extension:
            pending.append(dict(category=category,index=int(e.get('index')),source=name));continue
        stock.append((e,match))
    block=actual.find('./block[@name="'+category+'"]');palette=actual.find('./block[@name="'+palette_name+'"]')
    assert len(stock)==len(block)==expected_count,(category,len(stock),len(block))
    for (s,donor),a in zip(stock,block):
        index=int(field(a,'type').split(',')[-1])
        reference=field(palette[index],'name')
        group={'scenery':'scen','weapon':'weap','equipment':'eqip'}[extension]
        assert reference==donor['path']+','+group
        assert (KIT/'tags'/(donor['path']+'.'+extension)).is_file()
        for name in ('position','rotation','scale','spawn order','quota minimum','quota maximum','spawn time','abandonment time','boundary width or radius','boundary box length','boundary positive height','boundary negative height','natural respawn weight'):
            expected=[float(x) for x in field(s,name).split(',')];found=[float(x) for x in field(a,name).split(',')]
            assert len(expected)==len(found) and all(abs(x-y)<=max(1e-5,abs(x)*2e-6) for x,y in zip(expected,found)),(category,s.get('index'),name,expected,found)
        for name in ('unique id','game engine symmetric placement','owner team','remapping policy','boundary shape','teleporter channel'):
            assert field(s,name)==field(a,name),(category,s.get('index'),name)
        uid=field(a,'unique id');assert uid not in ids;ids.add(uid)
        for name in ('placement flags','transform flags','game engine flags','spawn flags'):
            native_field=a.find('./field[@name="'+name+'"]')
            flags={line.strip() for line in (native_field.text or '').splitlines() if line.strip()}
            expected=field(s,name)
            assert flags==({expected} if expected else set()),(category,s.get('index'),name,flags,expected)
        assert field(a,'name')==',-1' and field(a,'editor folder')==',-1'
        assert all(p.get('value')==',-1' for p in a.findall('./field[@name="parent object"]'))
    counts[category]=len(block);changes.update((category,palette_name))
# Sky, starting profile, Forge palette, BSP links and every other saved section
# must be identical to the checkpoint immediately before these placements.
for old,new in zip(earlier,actual):
    assert old.tag==new.tag and old.get('name')==new.get('name')
    if old.get('name') not in changes:assert ET.tostring(old)==ET.tostring(new),old.get('name')
assert len(earlier)==len(actual)
report=dict(scenario_sha256=before,baseline_sha256=sha(backup),counts=counts,unique_ids=len(ids),all_transforms_and_spawn_settings_match=True,
    other_scenario_sections_unchanged=True,pending=pending,
    limitation='159 directly matched stock placements verified. Initial starts, objectives, six remaining weapon placements, decorative objects, effects, lighting and gameplay review are unfinished.')
(OUT/'h3-basic-placements-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('H3_BASIC_PLACEMENTS_VERIFIED',counts,'other scenario sections unchanged',flush=True)
