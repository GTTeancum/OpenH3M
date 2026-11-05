"""Export original sky and stock H3 templates using official Tool commands."""
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit'
env=os.environ.copy()
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/path)
requests=[('hrek','source-sky-'+ext,'levels/dlc/cex_beaver_creek/beavercreek_sky/beavercreek_sky.'+ext) for ext in ('scenery','model')]
requests += [('h3ek','stock-sky-'+ext,'levels/dlc/bunkerworld/sky/'+name+'.'+ext) for ext,name in [('scenery','bunkerworld'),('model','sky_bunkerworld'),('sky_atm_parameters','bunkerworld')]]
requests += [('h3ek','native-sky-render','levels/custom/battle_canyon_fresh/sky/sky.render_model')]
requests += [('h3ek','native-sky-'+ext,'levels/custom/battle_canyon_fresh/sky/sky.'+ext) for ext in ('model','scenery')]
requests += [('h3ek','native-sky-scenario','levels/custom/battle_canyon_fresh/battle_canyon_fresh.scenario'),
             ('h3ek','stock-sky-render','levels/dlc/bunkerworld/sky/sky.render_model')]
for kit_name,name,relative in requests:
    kit=ROOT/'work/editing-kits'/kit_name
    source=kit/'tags'/relative;assert source.is_file(),source
    destination=OUT/(name+'.xml')
    with (OUT/(name+'-export.log')).open('wb') as log:
        run=subprocess.run([str(kit/('tool_fast.exe' if kit_name=='hrek' else 'tool.exe')),'export-tag-to-xml',str(source),str(destination)],cwd=kit,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
    assert run.returncode==0 and destination.stat().st_size>1000,name
    print('SKY_METADATA',name,flush=True)
