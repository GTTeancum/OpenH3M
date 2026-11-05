"""Batch the established native material workflow for the original sky."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';HERE=Path(__file__).resolve().parent
configured=json.loads((HERE/'material_families.json').read_text())
available=[name for name in configured if name.startswith('sky_')]
families=sys.argv[1:] or available;assert set(families)<=set(available)
env=os.environ.copy()
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/path)
results=[]
for family in families:
    steps=[('author_wall_family.py',['--family',family,'--prepare']),
           ('inspect_wall_bitmaps.py',['--family','--family-name',family]),
           ('author_wall_family.py',['--family',family]),
           ('verify_wall_family.py',['--family',family])]
    result=dict(family=family,complete=False)
    for index,(helper,args) in enumerate(steps):
        log=OUT/(family+'-batch-'+str(index)+'.log')
        with log.open('wb') as stream:
            run=subprocess.run([sys.executable,'-B',str(HERE/helper),*args],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=300)
        if run.returncode:
            result.update(failed_step=helper,log=str(log),returncode=run.returncode)
            break
    else:result['complete']=True
    results.append(result)
    print('SKY_MATERIAL_FAMILY',json.dumps(result),flush=True)
(OUT/'sky-material-batch-result.json').write_text(json.dumps(results,indent=2)+'\n')
raise SystemExit(0 if all(r['complete'] for r in results) else 1)
