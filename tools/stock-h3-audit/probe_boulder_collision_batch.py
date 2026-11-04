"""Batch existing isolated Blender diagnostics for matching original boulders.

Does not save an authoring scene. Native Tool imports run separately, serially.
"""
import hashlib
import json
from pathlib import Path
import runpy
import sys
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
inventory=json.loads((OUT/'original-proxy-collision-inventory.json').read_text())
assert hashlib.sha256(Path(inventory['source']).read_bytes()).hexdigest()==inventory['sha256']
targets=[r['instances'][0] for r in inventory['definitions']
         if r['render_bsp_count']==0 and r['imported_physics_proxies']==0 and r['definition_index']!=74]
assert len(targets)==11 and all(n.startswith('boulder_') for n in targets)
scene=OUT/'battle-canyon-h3-materials.blend'
before=hashlib.sha256(scene.read_bytes()).hexdigest()
verify='--verify' in sys.argv
results=[]
for index,target in enumerate(targets):
    if index and not verify:bpy.ops.wm.open_mainfile(filepath=str(scene))
    sys.argv=['blender','--','--target',target,'--precise','--render-only']
    helper='verify_collision_workflow_geometry.py' if verify else 'export_collision_workflow_probe.py'
    code=0
    try:runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper),run_name='__main__')
    except SystemExit as exit_result:
        code=exit_result.code
        if not verify or code not in (0,1):raise
    if verify:
        path=OUT/('collision-workflow-precise-render-only-'+target+'-geometry-comparison.json')
        result=json.loads(path.read_text())
        assert result['source_sha256']==before
        results.append(dict(target=target,strict_checks_passed=code==0,comparison=result))
    print('BOULDER_BATCH_PROGRESS',index+1,len(targets),target,flush=True)
assert hashlib.sha256(scene.read_bytes()).hexdigest()==before
report=dict(scene_sha256=before,targets=targets,results=results,
    limitation='Isolated diagnostics only. Original source and saved authoring unchanged; no MCC acceptance.')
(OUT/('boulder-batch-'+('verification' if verify else 'export')+'.json')).write_text(json.dumps(report,indent=2)+'\n')
