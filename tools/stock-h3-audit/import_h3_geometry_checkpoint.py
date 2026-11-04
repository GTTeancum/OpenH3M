"""Import the current full ASS through official Tool to expose authoring errors.

Diagnostic only: does not bake lighting, launch MCC, install or convert to 360.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
export=json.loads((OUT/'h3-bound-ass-inspection-report.json').read_text())
bindings=json.loads((OUT/'h3-material-bindings.json').read_text())
assert not bindings['pending']
assert export['source_sha256']==bindings['scene_sha256']==sha(bindings['scene'])
assert sha(export['ass'])==export['ass_sha256']
collection=bindings['shader_collection']
assert sha(collection['path'])==collection['sha256']
for binding in bindings['bindings'].values():
    assert sha(binding['authored'])==sha(binding['export_tag'])==binding['sha256']
ass=KIT/'data/levels/custom/battle_canyon_fresh/structure/battle_canyon.ass'
ass.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(export['ass'],ass)
assert sha(ass)==export['ass_sha256']
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:
    env[key]=str(OUT/relative)
log=OUT/'h3-full-geometry-import.log'
with log.open('wb') as stream:
    result=subprocess.run([str(KIT/'tool.exe'),'structure',str(ass.relative_to(KIT/'data'))],
        cwd=KIT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=1800)
text=log.read_text(errors='replace')
issues=[line.strip() for line in text.splitlines() if any(s in line.lower() for s in ('error','warning','failed','could not','cannot find','not found'))]
tags=KIT/'tags/levels/custom/battle_canyon_fresh'
outputs={p.name:sha(p) for suffix in ('scenario_structure_bsp','scenario_structure_lighting_info','scenario')
         for p in tags.glob('*.'+suffix)}
report=dict(scene_sha256=bindings['scene_sha256'],ass_sha256=export['ass_sha256'],
    returncode=result.returncode,import_completed='=== imported structure' in text,issues=issues,native_outputs=outputs,
    limitation='Diagnostic import only. Output and issues require inspection; unresolved authoring, lighting proposal, gameplay and MCC approval remain.')
report['clean_import_completed']=bool(result.returncode==0 and report['import_completed']
    and not any('error' in line.lower() or 'fatal' in line.lower() for line in issues)
    and (tags/'battle_canyon.scenario_structure_bsp').is_file())
(OUT/'h3-full-geometry-import.json').write_text(json.dumps(report,indent=2)+'\n')
print('H3_FULL_GEOMETRY_IMPORT',json.dumps({k:v for k,v in report.items() if k!='issues'}),'issue lines',len(issues),flush=True)
assert sha(ass)==export['ass_sha256']
assert sha(bindings['scene'])==bindings['scene_sha256']
raise SystemExit(0 if report['clean_import_completed'] else 1)
