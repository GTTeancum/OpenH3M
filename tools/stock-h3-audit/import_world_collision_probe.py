"""Run official H3 Tool on an isolated world-mesh ASS diagnostic."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
stem='world-collision'+('-precise' if '--precise' in sys.argv else '-baseline')+('-portals' if '--portals' in sys.argv else '')
probe=json.loads((OUT/(stem+'-probe.json')).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(probe['ass'])==probe['ass_sha256'] and sha(probe['source'])==probe['source_sha256']
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/relative)
log=OUT/(stem+'-import.log')
start=time.monotonic()
with log.open('wb') as stream:
    process=subprocess.Popen([str(KIT/'tool.exe'),'structure',str(Path(probe['ass']).relative_to(KIT/'data'))],cwd=KIT,env=env,stdout=stream,stderr=subprocess.STDOUT)
    print('WORLD_COLLISION_NATIVE_PID',process.pid,stem,flush=True)
    try:
        code=process.wait(timeout=1800)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise
text=log.read_text(errors='replace')
issues=[line.strip() for line in text.splitlines() if any(w in line for w in ('WARNING','ERROR','FATAL'))]
tag=KIT/'tags/levels/custom/bc_world_collision_probe'/(Path(probe['ass']).stem+'.scenario_structure_bsp')
report=dict(source_sha256=probe['source_sha256'],ass_sha256=probe['ass_sha256'],returncode=code,
    elapsed_seconds=time.monotonic()-start,import_completed='=== imported structure' in text,
    issues=issues,native_tag_sha256=sha(tag) if tag.is_file() else None,
    limitation='Isolated native diagnostic. Output and issue lines require inspection; no map changes or fidelity acceptance.')
report['clean_geometry_import']=code==0 and report['import_completed'] and not any('ERROR' in l or 'FATAL' in l for l in issues)
(OUT/(stem+'-native.json')).write_text(json.dumps(report,indent=2)+'\n')
assert sha(probe['source'])==probe['source_sha256'] and sha(probe['ass'])==probe['ass_sha256']
print('WORLD_COLLISION_NATIVE',json.dumps({k:v for k,v in report.items() if k!='issues'}),'issue lines',len(issues),flush=True)
