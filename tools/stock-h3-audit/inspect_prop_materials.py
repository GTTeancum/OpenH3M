"""Extend the fresh source inventory with actual Foundry-imported prop surfaces.

Run the existing read-only native inspection workflow; no shader authoring.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';HERE=Path(__file__).resolve().parent
BLENDER=Path(r'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe')
env=os.environ.copy()
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp'),('BLENDER_USER_CONFIG','profile/blender')]:env[key]=str(OUT/path)
path=OUT/'reach-source-references.json';inventory=json.loads(path.read_text())
surfaces=set(inventory['surface_references']);props={}
for name in ('frunner_wheel','cex_health_cabinet','ff_redbase_rocks02','health_station'):
    row=json.loads((OUT/('original-prop-'+name+'.json')).read_text())
    for file,expected in [(row['source'],row['source_sha256']),(row['scene'],row['scene_sha256'])]:
        assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==expected,file
    props[name]=dict(source=row['source'],source_sha256=row['source_sha256'],surfaces=row['materials'])
    surfaces.update(row['materials'])
inventory['surface_references']=sorted(surfaces);inventory['additional_prop_surfaces']=props
path.write_text(json.dumps(inventory,indent=2)+'\n')
steps=[('inspect_shader_setups.py',False,['hrek']),('inspect_effective_shader_options.py',True,[]),
       ('inspect_reach_option_defaults.py',False,[]),('inspect_inherited_functions.py',True,[])]
for helper,blender,args in steps:
    command=([str(BLENDER),'-b','--factory-startup','--python-exit-code','1','--python',str(HERE/helper)] if blender
             else [sys.executable,'-B',str(HERE/helper),*args])
    log=OUT/('prop-'+helper.removesuffix('.py')+'.log')
    with log.open('wb') as stream:
        result=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=180)
    assert result.returncode==0,log
    print('PROP_SOURCE_INSPECTION',helper,'complete',flush=True)

# Inventory the selected native decal setup separately from ordinary shaders.
# Its original-360 option values are verified by prepare_family_donors.py.
family=json.loads((HERE/'material_families.json').read_text())['prop_unsc_decal']
donor=family['donor']
assert any(line.endswith('] '+donor) for line in (OUT/'standoff-all-tags.txt').read_text(encoding='utf-8-sig').splitlines())
kit=ROOT/'work/editing-kits/h3ek'
plan=OUT/'stock-decal-read-plan.json'
plan.write_text(json.dumps(dict(Kit=str(kit),Tags=[donor],Output=str(OUT/'stock-decal-configurations.json')),indent=2)+'\n')
(OUT/'stock-decal-provenance.json').write_text(json.dumps({donor:['standoff']},indent=2)+'\n')
with (OUT/'stock-decal-read.log').open('wb') as stream:
    result=subprocess.run([str(OUT/'h3-api-probe/ReadH3ShaderConfigurations.exe'),str(plan)],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=90)
assert result.returncode==0,'Native stock decal inspection failed'
print('PROP_STOCK_DECAL_INSPECTED',donor,flush=True)
