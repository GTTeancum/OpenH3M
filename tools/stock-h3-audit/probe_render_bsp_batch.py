"""Run isolated standard-tool diagnostics for the other no-extra-physics cases."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit'
BLENDER=Path(r'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe')
scene=OUT/'battle-canyon-h3-materials.blend'
before=hashlib.sha256(scene.read_bytes()).hexdigest()
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp'),('BLENDER_USER_CONFIG','profile/blender')]:env[key]=str(OUT/relative)
results=[]
allowed=('teleporter_trimlowside004','baseblue_ent','object372')
targets=sys.argv[1:] or allowed
assert all(t in allowed for t in targets)
for target in targets:
    def run(helper,args,blender=False,load=True,allow_strict_failure=False):
        command=([str(BLENDER),'-b','--disable-autoexec','--python-exit-code','1']+
                 ([str(scene)] if load else [])+['--python',str(ROOT/'tools/stock-h3-audit'/helper),'--'] if blender
                 else [sys.executable,'-B',str(ROOT/'tools/stock-h3-audit'/helper)])+args
        path=OUT/('render-bsp-batch-'+target+'-'+Path(helper).stem+'.log')
        with path.open('wb') as stream:
            result=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=180)
        assert result.returncode==0 or (allow_strict_failure and result.returncode==1),(target,helper,result.returncode,str(path))
        return result.returncode
    flags=['--target',target,'--precise','--render-only','--original-render-bsp']
    run('export_collision_workflow_probe.py',flags,blender=True)
    run('import_collision_workflow_probe.py',flags)
    render_code=run('verify_collision_workflow_geometry.py',flags,blender=True,allow_strict_failure=True)
    collision_code=run('verify_original_render_bsp_probe.py',['--target',target],blender=True,load=False,allow_strict_failure=True)
    stem='collision-workflow-precise-render-only-original-render-bsp-'+target
    comparison=json.loads((OUT/(stem+'-geometry-comparison.json')).read_text())
    collision=json.loads((OUT/('original-render-bsp-native-comparison-'+target+'.json')).read_text())
    native=json.loads((OUT/(stem+'-native.json')).read_text())
    assert comparison['source_sha256']==before and comparison['ass_sha256']==native['ass_sha256']==collision['ass_sha256']
    results.append(dict(target=target,render_strict_code=render_code,collision_strict_code=collision_code,render=comparison,collision=collision,native=native))
    print('RENDER_BSP_BATCH_CASE',target,'checked',flush=True)
assert hashlib.sha256(scene.read_bytes()).hexdigest()==before
(OUT/'render-bsp-batch-verification.json').write_text(json.dumps(dict(scene_sha256=before,results=results),indent=2)+'\n')
