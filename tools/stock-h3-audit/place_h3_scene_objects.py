"""Place original wheel and all 13 light anchors through the established native editor workflow."""
import hashlib,json,os,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def f(e,n):return e.find(f"field[@name='{n}']").get('value')
source=OUT/'original-lighting-scenario.xml';xml=ET.fromstring(source.read_text(encoding='utf-8').replace('<unavailable>','&lt;unavailable&gt;'))
rows=[];category=None
for e in xml:
    if e.tag=='field':category=e.get('name')
    elif e.tag=='element' and category=='scenery':
        name=f(e,'type')
        if name not in ('frunner_wheel','ca_bcreek_omni_1','ca_bcreek_spot_5','ca_bcreek_spot_7'):continue
        assert f(e,'megalo label')=='' and f(e,'spawn flags')==''
        target=fr'levels\custom\battle_canyon_fresh\props\{name}\{name}.scenery'
        rows.append(dict(SourceBlock='scenery',SourceIndex=int(e.get('index')),SourceType=name,SourceLabel='',TargetBlock='scenery',
            TargetTag=target,TargetSha256=sha(KIT/'tags'/target),UniqueId=int(f(e,'unique id')),TranslateScriptedFlag=False))
assert len(rows)==14
scenario=KIT/'tags/levels/custom/battle_canyon_fresh/battle_canyon_fresh.scenario'
assert not (OUT/'scenario-before-scene-objects.scenario').exists(),'Inspect existing scene checkpoint'
plan=dict(ScenarioSha256=sha(scenario),SourceXmlSha256=sha(source),Placements=rows,counts={'scenery':14})
(OUT/'h3-scene-object-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
env=os.environ.copy()
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/path)
api=OUT/'h3-api-probe';exe=api/'PrepareH3Gameplay.exe'
subprocess.run([r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe','/nologo','/target:exe','/r:'+str(api/'ManagedBlam.dll'),
    '/r:Microsoft.CSharp.dll','/r:System.Web.Extensions.dll','/main:PrepareH3Gameplay','/out:'+str(exe),
    str(ROOT/'tools/stock-h3-audit/PrepareH3BasicPlacements.cs'),str(ROOT/'tools/stock-h3-audit/PrepareH3Gameplay.cs')],cwd=ROOT,env=env,check=True)
for mode in ('dry-run','apply'):
    with (OUT/f'h3-scene-placement-{mode}.log').open('wb') as log:
        subprocess.run([str(exe),str(ROOT),'--scene-objects']+(['--dry-run'] if mode=='dry-run' else []),cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,check=True)
print('SCENE_PLACEMENTS_SAVED',len(rows),flush=True)
