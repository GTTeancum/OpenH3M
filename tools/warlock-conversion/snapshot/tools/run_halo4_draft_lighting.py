"""Run the official local lightmap command sequence, with four native workers.

Commands/order match the kit's unchanged calc_lm_farm_local.py. The distinct
job ID avoids another map's work. This WIP bake does not waive pending assets.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[4];OUT=ROOT/'work/halo4-to-h3/haven';KIT=ROOT/'work/editing-kits/h3ek'
SCENARIO=r'levels\custom\haven_h4\haven_draft'
short_names='--short-names' in sys.argv
world_render='--world-render' in sys.argv or short_names
BSP='haven_one_sided_joined_surfaces_opaque_draft'+('_reflections_worldrender' if world_render else '')
if short_names:SCENARIO=r'levels\custom\haven_h4\haven_preview';BSP='haven'
JOB='2026110503' if short_names else '2026110502' if world_render else '2026110501';BLOB='faux\\'+JOB
DEST=OUT/('draft-lighting-'+JOB);assert not DEST.exists(),'Inspect existing job before retrying'
assert not (KIT/BLOB).exists(),'Native job directory already exists'
DEST.mkdir()
env=os.environ.copy()
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/'h3-authoring'/path)
tool=KIT/'tool_fast.exe'
owned=[]
def sha(p):
    with Path(p).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
report=dict(status='running',scenario=SCENARIO,bsp=BSP,quality='draft',job=JOB,workers=4,
    official_script_sha256=sha(KIT/'calc_lm_farm_local.py'),before={},steps=[],
    limitation='Provisional Haven bake: all 290 static source BSP/sky light records are authored. Source H4 response, material emission, fog/exposure, sky effects and remaining gameplay content are unverified. No runtime or visual acceptance.')
verification=json.loads((OUT/('haven-short-bake-verification.json' if short_names else 'haven-h3-lighting-worldrender-verification.json' if world_render else 'haven-h3-lighting-with-sky-verification.json')).read_text())
assert verification['definitions']==verification['instances']==290
inputs=[KIT/'tags/levels/custom/haven_h4/haven_draft.scenario',
    KIT/'tags/levels/custom/haven_geometry_probe'/(BSP+'.scenario_structure_bsp'),
    KIT/'tags/levels/custom/haven_geometry_probe'/(BSP+'.scenario_structure_lighting_info'),
    KIT/'tags/levels/custom/haven_h4'/('haven_lighting_worldrender.scenario_structure_lighting_info' if world_render else 'haven_lighting_with_sky.scenario_structure_lighting_info')]
if short_names:
    inputs=[KIT/'tags/levels/custom/haven_h4/haven_preview.scenario',
        KIT/'tags/levels/custom/haven_h4/haven.scenario_structure_bsp',
        KIT/'tags/levels/custom/haven_geometry_probe/haven_one_sided_joined_surfaces_opaque_draft_reflections_worldrender.scenario_structure_lighting_info',
        KIT/'tags/levels/custom/haven_h4/haven.scenario_structure_lighting_info']
assert sha(inputs[0])==verification['scenario_sha256']
assert sha(inputs[3])==verification['native_tag_sha256']
for path in inputs:
    report['before'][str(path)]=sha(path);shutil.copyfile(path,DEST/path.name)
report['tool_sha256']=sha(tool)

def save():(DEST/'report.json').write_text(json.dumps(report,indent=2)+'\n')
def execute(name,args):
    print('DRAFT_STAGE',name,flush=True);entry=dict(name=name,args=args,start=time.time());report['steps'].append(entry);save()
    with (DEST/(name+'.log')).open('wb') as log:
        process=subprocess.Popen([str(tool),*args],cwd=KIT,env=env,stdout=log,stderr=subprocess.STDOUT)
        owned.append(process)
        entry['pid']=process.pid;save();entry['returncode']=process.wait(timeout=1800)
    entry['seconds']=time.time()-entry['start'];save()
    if entry['returncode']!=0:raise RuntimeError(name+' returned '+str(entry['returncode']))
try:
    execute('data-sync',['faux_data_sync',SCENARIO,BSP])
    assert sha(inputs[3])==verification['native_tag_sha256'],'Data sync changed the authored light inputs'
    execute('begin',['faux_farm_begin',SCENARIO,BSP,'all','draft',JOB])
    for stage in ('dillum','pcast','radest','extillum','fgather'):
        jobs=[]
        for index in range(4):
            name=stage+'-'+str(index);log=(DEST/(name+'.log')).open('wb')
            args=['faux_farm_'+stage,BLOB,str(index),'4']
            process=subprocess.Popen([str(tool),*args],cwd=KIT,env=env,stdout=log,stderr=subprocess.STDOUT)
            owned.append(process)
            entry=dict(name=name,args=args,pid=process.pid,start=time.time());report['steps'].append(entry);jobs.append((process,log,entry))
        save();print('DRAFT_STAGE',stage,'workers',[p.pid for p,_,_ in jobs],flush=True)
        for process,log,entry in jobs:
            entry['returncode']=process.wait(timeout=1800);log.close();entry['seconds']=time.time()-entry['start'];save()
        if any(entry['returncode']!=0 for _,_,entry in jobs):raise RuntimeError(stage+' worker failure')
        execute(stage+'-merge',['faux_farm_'+stage+'_merge',BLOB,'4'])
    execute('finish',['faux_farm_finish',BLOB])
    for name,command in [('linear-textures','faux-build-linear-textures-with-intensity-from-quadratic'),
                         ('compress','faux-compress-scenario-bitmaps-dxt5'),('compression-merge','faux-farm-compression-merge')]:
        execute(name,[command,SCENARIO,BSP])
    report['after']={str(p):sha(p) for p in inputs}
    report['status']='commands-completed';save();print('DRAFT_COMMANDS_COMPLETED',flush=True)
except Exception as error:
    for child in owned:
        if child.poll() is None:
            child.terminate()
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=10)
    report['status']='failed';report['error']=str(error);save();raise
