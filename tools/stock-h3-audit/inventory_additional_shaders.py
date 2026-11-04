"""Read additional original stock caches for missing material candidates."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
MAPS=Path('C:/X360/ISOs/H3M/maps')
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/relative)
env['DOTNET_ROLL_FORWARD']='Major'
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

evidence=[]
# Other stock levels are inspected for configurations absent from Standoff,
# Guardian, Valhalla and Sandtrap. They do not expand the chosen Forge palette.
additional=['construct','cyberdyne','deadlock','salvation','snowbound','zanzibar','sandbox',
            'armory','chill','chillout','descent','docks','fortress','ghosttown',
            'isolation','lockout','midship','sidewinder','spacecamp','warehouse',
            'mainmenu','shared']
for name in additional:
    path=MAPS/(name+'.map');before=sha(path);log=OUT/(name+'-all-tags.txt')
    run=subprocess.run([str(OUT/'bin/TagTool.exe'),str(path),'ListTags'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    log.write_bytes(run.stdout)
    assert run.returncode==0,log
    assert b'[Index:' in run.stdout or name=='shared',log
    after=sha(path);assert before==after,path
    evidence.append(dict(map=str(path),sha256=before,unchanged=True,log=str(log),
                         listed_tags=run.stdout.count(b'[Index:'),
                         limitation='Shared resource cache returned no standalone tag entries' if name=='shared' else None))
    print('STOCK_MAP_READ',name,flush=True)
(OUT/'additional-stock-map-integrity.json').write_text(json.dumps(evidence,indent=2)+'\n')
provenance={}
missing=[]
for name in ['standoff','guardian','riverworld','shrine',*additional]:
    for line in (OUT/(name+'-all-tags.txt')).read_text(encoding='utf-8-sig').splitlines():
        # Stock object/equipment shaders can provide missing native setups too.
        # Names must still occur in these original 360 cache inventories.
        match=re.search(r'\] (.+\.shader)$',line)
        if not match:continue
        path=match[1]
        if (KIT/'tags'/path).is_file():provenance.setdefault(path,[]).append(name)
        else:missing.append(dict(tag=path,map=name))
(OUT/'stock-shader-map-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
(OUT/'stock-shader-missing-kit-tags.json').write_text(json.dumps(missing,indent=2)+'\n')
plan=OUT/'stock-shader-configuration-read-plan.json'
plan.write_text(json.dumps(dict(Kit=str(KIT),Tags=sorted(provenance),Output=str(OUT/'stock-shader-configurations.json')),indent=2)+'\n')
run=subprocess.run([str(OUT/'h3-api-probe/ReadH3ShaderConfigurations.exe'),str(plan)],cwd=KIT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
(OUT/'stock-shader-configuration-read.log').write_bytes(run.stdout)
assert run.returncode==0,run.stdout.decode(errors='replace')
print(run.stdout.decode(errors='replace').strip(),'MISSING_KIT',len(missing),flush=True)
