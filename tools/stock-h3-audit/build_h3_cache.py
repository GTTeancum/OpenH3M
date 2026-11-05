"""Run official MCC cache compilation for the current unfinished map.

This is a build-blocker check, not MCC visual/gameplay acceptance or a 360 build.
"""
import hashlib
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
parser=argparse.ArgumentParser();parser.add_argument('--job',default='2026110401');parser.add_argument('--previous-job');args=parser.parse_args()
assert args.job.isdigit() and (args.previous_job is None or args.previous_job.isdigit())
DEST=OUT/('cache-build-'+args.job);assert not DEST.exists(),'Inspect existing cache job before retrying'
DEST.mkdir()
env=os.environ.copy()
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/path)
scenario=r'levels\custom\battle_canyon_fresh\battle_canyon_fresh'
cache=KIT/'maps/battle_canyon_fresh.map'
lighting=json.loads((OUT/'draft-lighting-2026110401/report.json').read_text())
assert lighting['status']=='commands-completed' and all(s['returncode']==0 for s in lighting['steps'])
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
previous=None
if cache.exists():
    assert args.previous_job,'Identify the prior completed cache before native overwrite'
    previous=json.loads((OUT/('cache-build-'+args.previous_job)/'report.json').read_text(encoding='utf-8'))
    assert previous['status']=='tool-returned' and previous['returncode']==0 and sha(cache)==previous['cache_sha256']
report=dict(status='running',scenario=sha(KIT/'tags'/(scenario+'.scenario')),started=time.time(),
    args=['build-cache-file',scenario,'x64'],
    limitation='WIP MCC cache check. Known geometry and lighting errors, unfinished props/effects/atmosphere/audio and user decisions remain. No MCC approval or 360 conversion.')
if previous:report['replaced_previous_cache_sha256']=previous['cache_sha256']
def save():(DEST/'report.json').write_text(json.dumps(report,indent=2)+'\n')
save()
with (DEST/'tool.log').open('wb') as log:
    process=subprocess.Popen([str(KIT/'tool_fast.exe'),*report['args']],cwd=KIT,env=env,stdout=log,stderr=subprocess.STDOUT)
    report['pid']=process.pid;save();print('MCC_CACHE_JOB',process.pid,flush=True)
    try:report['returncode']=process.wait(timeout=1800)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
        report.update(status='timed-out',seconds=time.time()-report['started']);save();raise
report.update(status='tool-returned',seconds=time.time()-report['started'],cache_exists=cache.is_file())
if cache.is_file():report.update(cache=str(cache),cache_sha256=sha(cache),bytes=cache.stat().st_size)
save();print('MCC_CACHE_RESULT',json.dumps(report),flush=True)
raise SystemExit(report['returncode'])
