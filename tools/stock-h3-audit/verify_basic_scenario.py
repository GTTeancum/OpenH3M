"""Read saved scenario fields through official Tool XML after initial setup."""
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
tag=KIT/'tags/levels/custom/battle_canyon_fresh/battle_canyon_fresh.scenario'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
before=sha(tag);xml=OUT/'h3-scenario-basic-setup.xml'
env=os.environ.copy()
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/path)
with (OUT/'h3-scenario-basic-setup-export.log').open('wb') as log:
    result=subprocess.run([str(KIT/'tool.exe'),'export-tag-to-xml',str(tag),str(xml)],cwd=KIT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
assert result.returncode==0 and xml.stat().st_size>0
def read_xml(path):return ET.fromstring(path.read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
tree=read_xml(xml)
def field(element,name):return element.find('./field[@name="'+name+'"]').attrib['value']
def block(name):return tree.find('./block[@name="'+name+'"]')
assert field(tree,'type')=='multiplayer' and float(field(tree,'sandbox budget'))==800
assert int(field(tree,'map id'))==10020
assert len(block('structure bsps'))==1 and len(block('zone sets'))==1
assert field(block('structure bsps')[0],'structure design')==r'levels\custom\battle_canyon_rebuild\battle_canyon,sddt'
assert field(block('zone sets')[0],'bsp zone flags')=='1'
assert len(block('player starting locations'))==1 and len(block('player starting profile'))==1
assert field(block('player starting locations')[0],'position')=='-1.02144,0.560463,-0.113322'
assert float(field(block('player starting locations')[0],'facing'))==0
donor=read_xml(OUT/'standoff-authoring-scenario.xml')
profile=donor.find('./block[@name="player starting profile"]/element')
for expected in profile.findall('./field'):
    if expected.attrib['name']!='name':assert field(block('player starting profile')[0],expected.attrib['name'])==expected.attrib['value'],expected.attrib['name']
names={'Weapons':'mv weapon palette','Equipment':'mv equipment palette','Scenery':'mv scenery palette',
       'Teleporters':'mv teleporters palette','Goals':'mv goals palette','Spawning':'mv spawners palette'}
with (OUT/'standoff-forge-no-vehicles.csv').open(newline='') as stream:rows=list(csv.DictReader(stream))
assert len(rows)==99 and len(block('mv vehicle palette'))==0
for category,name in names.items():
    expected=[r for r in rows if r['category']==category];actual=list(block(name));assert len(actual)==len(expected)
    for row,element in zip(expected,actual):
        assert field(element,'name').split(',')[0]==row['path']
        assert field(element,'display_name')==row['name']
        assert int(field(element,'maximum allowed'))==int(row['max_allowed'])
        assert float(field(element,'price per instance'))==float(row['cost'])
assert sha(tag)==before
report=dict(scenario=str(tag),scenario_sha256=before,map_id=10020,multiplayer=True,budget=800,forge_entries=99,
    vehicle_category_entries=0,stock_starting_profile_verified=True,original_reach_initial_location_verified=True,
    structure_design_linked=True,active_bsp_zone=True,
    limitation='Basic saved setup only. Source sky, lighting, actual multiplayer spawns/object placements, atmosphere and MCC gameplay remain unfinished.')
(OUT/'h3-scenario-basic-setup.json').write_text(json.dumps(report,indent=2)+'\n')
print('H3_BASIC_SCENARIO_VERIFIED',json.dumps(report),flush=True)
