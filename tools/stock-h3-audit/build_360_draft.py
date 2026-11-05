"""Official source compile followed by the established original-H3 converter."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
p=argparse.ArgumentParser();p.add_argument('--candidate',type=int,required=True);p.add_argument('--source-only',action='store_true');p.add_argument('--convert-only',action='store_true');a=p.parse_args()
dest=ROOT/'.local/battle-canyon-fresh'/('candidate'+str(a.candidate));dest.mkdir(parents=True,exist_ok=True)
env=os.environ.copy()
for k,v in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[k]=str(OUT/v)
env['PYTHONDONTWRITEBYTECODE']='1'
steps=[]
def run(name,command,cwd,timeout):
    entry=dict(name=name,command=list(map(str,command)),status='running',started=time.time());steps.append(entry)
    report=dest/'run.json'
    def save():report.write_text(json.dumps(steps,indent=2),encoding='utf8')
    with (dest/(name+'.log')).open('wb') as log:
        child=subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
        entry['pid']=child.pid;save();print(name,child.pid,flush=True)
        try:entry['returncode']=child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:child.kill();child.wait();entry['status']='timeout';save();raise
    entry.update(status='complete' if entry['returncode']==0 else 'failed',seconds=time.time()-entry['started']);save()
    if entry['returncode']:raise SystemExit(entry['returncode'])
if not a.convert_only:
    report=json.loads((OUT/'360-collision-draft.json').read_text(encoding='utf8'))
    run('structure',[KIT/'tool.exe','structure',r'levels\custom\battle_canyon_fresh\structure\battle_canyon.ass'],KIT,600)
    run('cache',[KIT/'tool_fast.exe','build-cache-file',r'levels\custom\battle_canyon_fresh\battle_canyon_fresh','x64'],KIT,600)
if not a.source_only:
    run('convert',[sys.executable,'-B',ROOT/'tools/warlock-conversion/snapshot/tools/build_scenario_checkpoint.py',
        '--project',ROOT,'--stock-h3-draft','--slot','zanzibar','--source',KIT/'maps/battle_canyon_fresh.map',
        '--basis','C:/X360/ISOs/H3M/maps/zanzibar.map','--xex','C:/X360/ISOs/H3M/default.xex',
        '--disc-maps','C:/X360/ISOs/H3M/maps','--sound-bank','D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo3/fmod/pc/sfx.fsb',
        '--decoder','C:/X360/ISOs/H3M/.local/tools/vgmstream-r2117/vgmstream-cli.exe',
        '--output',dest/'zanzibar.map','--report',dest/'build.json'],ROOT,900)
