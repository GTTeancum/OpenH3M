"""Inspect native draft outputs without claiming visual/gameplay acceptance."""
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
env=os.environ.copy()
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/path)
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def xml(path):return ET.fromstring(path.read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
def export(relative,name):
    source=KIT/'tags'/relative;before=sha(source);target=OUT/(name+'.xml')
    with (OUT/(name+'-export.log')).open('wb') as stream:
        result=subprocess.run([str(KIT/'tool.exe'),'export-tag-to-xml',str(source),str(target)],cwd=KIT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=90)
    assert result.returncode==0 and target.stat().st_size>1000 and sha(source)==before
    return xml(target)
scenario=export(r'levels\custom\battle_canyon_fresh\battle_canyon_fresh.scenario','h3-draft-scenario')
baseline=xml(OUT/'h3-gameplay-saved.xml')
def canonical(element):return ET.canonicalize(ET.tostring(element,encoding='unicode'),strip_text=True)
preserved=[]
assert len(baseline)==len(scenario)
for a,b in zip(baseline,scenario):
    assert (a.tag,a.get('name'))==(b.tag,b.get('name'))
    if a.tag=='field' and a.get('name')=='new lightmaps':continue
    assert canonical(a)==canonical(b),a.get('name')
    preserved.append(dict(kind=a.tag,name=a.get('name')))
lightrefs=[dict(field=e.get('name'),value=e.get('value')) for e in scenario.findall('field') if 'lightmap' in e.get('name','')]
lighting=json.loads((OUT/'draft-lighting-2026110401/report.json').read_text())
assert lighting['status']=='commands-completed' and all(s['returncode']==0 for s in lighting['steps'])
errors={}
for path in sorted((OUT/'draft-lighting-2026110401').glob('*.log')):
    lines=[line.strip() for line in path.read_text(errors='replace').splitlines() if re.search(r'\b(ERROR|FATAL)\b',line)]
    if lines:errors[path.name]=dict(collections.Counter(lines))
cache=json.loads((OUT/'cache-build-2026110401/report.json').read_text());assert cache['returncode']==0 and cache['cache_exists']
assert sha(Path(cache['cache']))==cache['cache_sha256']
stock=json.loads((OUT/'stock-animation-cache-audit.json').read_text())
animation=[]
for original,mcc,fresh in zip(stock['360']['models'],stock['mcc']['models'],stock['fresh']['models']):
    assert original['model']==mcc['model']==fresh['model']
    fields=lambda row:[line for line in row['fields'] if line.startswith(('Animation:','Nodes:'))]
    assert fields(original)==fields(mcc)==fields(fresh)
    assert 'Animation: CachedTag = null' in fields(fresh)
    animation.append(dict(model=fresh['model'],matching_native_cache_fields=fields(fresh)))
report=dict(lighting_commands_completed=len(lighting['steps']),lighting_error_lines=errors,scenario_lightmap_fields=lightrefs,
    unchanged_scenario_sections=preserved,cache_sha256=cache['cache_sha256'],cache_bytes=cache['bytes'],stock_animation_cache_matches=animation,
    limitation='WIP native compilation checkpoint only. Out-of-bounds lightmap UV errors, ray errors and existing geometry failures remain unresolved. Props/effects/atmosphere/audio are unfinished; MCC visual/gameplay testing and user approval have not occurred.')
(OUT/'h3-draft-checkpoint-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('DRAFT_CHECKPOINT_VERIFIED',len(preserved),'scenario sections unchanged;',len(errors),'lighting logs contain unresolved errors;',len(animation),'stock animation references match shipping caches',flush=True)
