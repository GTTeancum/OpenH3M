"""Read actual stock cache model/animation relationships with unchanged TagTool."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit'
env=os.environ.copy();env['DOTNET_ROLL_FORWARD']='Major'
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/path)
models=[r'objects\equipment\gravlift_permanent\gravlift_permanent',r'objects\weapons\melee\gravity_hammer\gravity_hammer',r'objects\multi\powerups\powerup_red\powerup_red']
caches={'360':Path('C:/X360/ISOs/H3M/maps/bunkerworld.map'),
        'mcc':Path('D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo3/maps/bunkerworld.map'),
        'fresh':ROOT/'work/editing-kits/h3ek/maps/battle_canyon_fresh.map'}
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
results={}
for label,cache in caches.items():
    before=sha(cache);rows=[]
    for model in models:
        stem='stock-animation-'+label+'-'+Path(model).name
        commands=OUT/(stem+'.commands')
        commands.write_text('EditTag '+model+'.model\nListFields\n')
        run=subprocess.run([str(OUT/'bin/TagTool.exe'),str(cache),'RunCommands',str(commands)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        log=OUT/(stem+'.log');log.write_bytes(run.stdout)
        text=run.stdout.decode(errors='replace')
        assert run.returncode==0 and not re.search(r'ERROR|Exception|Invalid tag|Command failed',text),log
        lines=[line.strip() for line in text.splitlines() if re.match(r'\s*(RenderModel|Animation|Nodes|Materials)',line)]
        assert any('RenderModel' in line for line in lines),log
        rows.append(dict(model=model,fields=lines,log=str(log)))
        print('STOCK_ANIMATION_MODEL',label,model,lines,flush=True)
    assert sha(cache)==before
    results[label]=dict(cache=str(cache),sha256=before,models=rows)
(OUT/'stock-animation-cache-audit.json').write_text(json.dumps(results,indent=2)+'\n')
