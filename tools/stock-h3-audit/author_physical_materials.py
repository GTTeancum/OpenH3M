"""Apply exact source physical names only when present in original H3 Standoff.

Uses the official H3 API; no custom material definitions or tag serializer.
Run after any shader-donor authoring batch, before compiling geometry.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
REACH=ROOT/'work/editing-kits/hrek'
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/relative)
env['DOTNET_ROLL_FORWARD']='Major'

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

cache=Path('C:/X360/ISOs/H3M/maps/bunkerworld.map')
if not cache.is_file():cache=Path('C:/X360/ISOs/H3M/maps/standoff.map')
before=sha(cache)
commands=OUT/'standoff-global-materials.commands'
commands.write_text('EditTag globals\\globals.globals\nForEach Materials ListFields Name\n')
run=subprocess.run([str(OUT/'bin/TagTool.exe'),str(cache),'RunCommands',str(commands)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
(OUT/'standoff-global-materials.txt').write_bytes(run.stdout)
assert run.returncode==0 and sha(cache)==before,'Stock read failed or changed cache'
stock_names=set(re.findall(r'\] Name: StringId = (\S+)',run.stdout.decode(errors='replace')))
assert stock_names,'No original H3 material names read'
(OUT/'standoff-global-materials-integrity.json').write_text(json.dumps(dict(map=str(cache),sha256=before,unchanged=True),indent=2)+'\n')
source=json.loads((OUT/'hrek-physical-materials.json').read_text())
by_name={Path(path).name:path for path in source}
assert len(by_name)==len(source),'Ambiguous source shader name'
tags=[]
retained=[]
hashes={str(KIT/'tags/globals/globals.globals'):sha(KIT/'tags/globals/globals.globals')}
for target in sorted((KIT/'tags/levels/custom/battle_canyon_fresh/shaders').iterdir()):
    assert target.name in by_name,'Unknown authored source: '+target.name
    original=by_name[target.name]
    hashes[str(REACH/'tags'/original)]=sha(REACH/'tags'/original)
    fields={v['name']:v['value'] for v in source[original] if v['name'].startswith('material name') and v['value']}
    for name in fields.values():assert name in stock_names,'Requires stock alternative review: '+name
    if fields:tags.append(dict(Path=str(target.relative_to(KIT/'tags')),Fields=fields))
    else:retained.append(dict(path=str(target.relative_to(KIT/'tags')),reason='Source material name is empty; retain selected stock H3 material'))
plan=OUT/'physical-material-plan.json'
plan.write_text(json.dumps(dict(Kit=str(KIT),Output=str(OUT/'physical-material-report.json'),Tags=tags),indent=2)+'\n')
run=subprocess.run([str(OUT/'h3-api-probe/ApplyH3MaterialNames.exe'),str(plan),'--apply'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
(OUT/'physical-material-authoring.log').write_bytes(run.stdout)
assert run.returncode==0,run.stdout.decode(errors='replace')
for path,expected in hashes.items():assert sha(Path(path))==expected,path
(OUT/'physical-material-evidence.json').write_text(json.dumps(dict(original_cache=str(cache),cache_sha256=before,source_hashes=hashes,retained=retained,limitation='Native names verified; impact sounds/effects and terrain selection require MCC gameplay review'),indent=2)+'\n')
print(run.stdout.decode(errors='replace').strip(),flush=True)
