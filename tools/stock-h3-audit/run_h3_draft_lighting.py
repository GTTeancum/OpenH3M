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
import time
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
SCENARIO=r'levels\custom\battle_canyon_fresh\battle_canyon_fresh';BSP='battle_canyon';JOB='2026110401';BLOB='faux\\'+JOB
DEST=OUT/('draft-lighting-'+JOB);assert not DEST.exists(),'Inspect existing job before retrying'
assert not (KIT/BLOB).exists(),'Native job directory already exists'
DEST.mkdir()
env=os.environ.copy()
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/path)
tool=KIT/'tool_fast.exe'
owned=[]
def sha(p):
    with Path(p).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
report=dict(status='running',scenario=SCENARIO,bsp=BSP,quality='draft',job=JOB,workers=4,
    official_script_sha256=sha(KIT/'calc_lm_farm_local.py'),before={},steps=[],
    limitation='WIP lighting run with current geometry/material emitters. Remaining original light/scenery assets and atmosphere are not complete. Existing geometry failures remain open; this does not establish MCC readiness or visual acceptance.')
for name in ('battle_canyon_fresh.scenario','battle_canyon.scenario_structure_bsp','battle_canyon.scenario_structure_lighting_info'):
    path=KIT/'tags/levels/custom/battle_canyon_fresh'/name
    report['before'][str(path)]=sha(path);shutil.copyfile(path,DEST/name)
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
    report['status']='commands-completed';save();print('DRAFT_COMMANDS_COMPLETED',flush=True)
except Exception as error:
    for child in owned:
        if child.poll() is None:
            child.terminate()
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=10)
    report['status']='failed';report['error']=str(error);save();raise
