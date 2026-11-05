"""Prepare and apply original prop placements with the official H3 editor API."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def value(e,name):return e.find(f"field[@name='{name}']").get('value')
source=OUT/'original-lighting-scenario.xml'
xml=ET.fromstring(source.read_text(encoding='utf-8').replace('<unavailable>','&lt;unavailable&gt;'))
rows=[];category=None
for e in xml:
    if e.tag=='field':category=e.get('name')
    elif e.tag=='element' and category=='crates':
        name=value(e,'type')
        if name not in ('cex_health_cabinet','ff_redbase_rocks02'):continue
        cabinet=name=='cex_health_cabinet'
        assert value(e,'megalo label')==('terr_object' if cabinet else '')
        assert value(e,'spawn flags')==('hide unless megalo required' if cabinet else '')
        targets=[fr'levels\custom\battle_canyon_fresh\props\{name}\{name}.crate']
        if cabinet:targets.append(r'objects\multi\territories\territory_static.crate')
        for i,target in enumerate(targets):
            rows.append(dict(SourceIndex=int(e.get('index')),SourceType=name,TargetTag=target,
                TargetSha256=sha(KIT/'tags'/target),
                UniqueId=int(value(e,'unique id')) if i==0 else -1130000000+int(e.get('index')),
                Mode='territories' if cabinet else '',Role='stock territory objective' if i else 'original appearance'))
assert len(rows)==9
scenario=KIT/'tags/levels/custom/battle_canyon_fresh/battle_canyon_fresh.scenario'
plan=dict(ScenarioSha256=sha(scenario),SourceXmlSha256=sha(source),Placements=rows,
    limitation='Native authoring only. Territory selection, visible cabinet overlap and collision require MCC review. No stock tags or Forge palette entries are changed.')
assert not (OUT/'scenario-before-static-props.scenario').exists(),'Inspect existing checkpoint before rerunning'
(OUT/'h3-static-prop-placement-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
env=os.environ.copy()
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/path)
api=OUT/'h3-api-probe';exe=api/'PrepareH3StaticPropPlacements.exe'
command=[r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe','/nologo','/target:exe',
    '/r:'+str(api/'ManagedBlam.dll'),'/r:Microsoft.CSharp.dll','/r:System.Web.Extensions.dll',
    '/main:PrepareH3StaticPropPlacements','/out:'+str(exe),
    str(ROOT/'tools/stock-h3-audit/PrepareH3BasicPlacements.cs'),str(ROOT/'tools/stock-h3-audit/PrepareH3StaticPropPlacements.cs')]
subprocess.run(command,cwd=ROOT,env=env,check=True)
for mode in ('dry-run','apply'):
    with (OUT/f'static-prop-placement-{mode}.log').open('wb') as log:
        run=subprocess.run([str(exe),str(ROOT)]+(['--dry-run'] if mode=='dry-run' else []),
            cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    assert run.returncode==0,(mode,run.returncode)
print('STATIC_PROP_PLACEMENTS_SAVED',len(rows),flush=True)
