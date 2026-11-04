"""Run the existing official-Tool diagnostic wrapper serially for each boulder."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
batch=json.loads((OUT/'boulder-batch-export.json').read_text())
assert hashlib.sha256((OUT/'battle-canyon-h3-materials.blend').read_bytes()).hexdigest()==batch['scene_sha256']
reports=[]
for target in batch['targets']:
    command=[sys.executable,'-B',str(ROOT/'tools/stock-h3-audit/import_collision_workflow_probe.py'),
             '--precise','--render-only','--target',target]
    subprocess.run(command,cwd=ROOT,check=True,timeout=300)
    report=json.loads((OUT/('collision-workflow-precise-render-only-'+target+'-native.json')).read_text())
    reports.append(dict(target=target,report=report))
(OUT/'boulder-batch-import.json').write_text(json.dumps(dict(scene_sha256=batch['scene_sha256'],results=reports),indent=2)+'\n')
print('BOULDER_BATCH_IMPORTED',len(reports),flush=True)
