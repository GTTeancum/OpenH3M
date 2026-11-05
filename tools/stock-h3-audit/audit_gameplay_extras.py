"""Read extra stock gameplay donors with unchanged TagTool and compare MCC."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit'
tags=[r'objects\weapons\rifle\plasma_rifle\plasma_rifle.weapon',
      r'objects\multi\spawning\respawn_point_invisible.scenery',
      r'objects\multi\infection\infection_haven_static.crate']
caches={'360':Path('C:/X360/ISOs/H3M/maps/guardian.map'),
        'mcc':Path('D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo3/maps/guardian.map')}
env=os.environ.copy();env['DOTNET_ROLL_FORWARD']='Major'
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/path)
def sha(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
reports={}
for label,cache in caches.items():
    before=sha(cache);entries={}
    for tag in tags:
        stem='gameplay-extra-'+label+'-'+Path(tag).stem
        commands=OUT/(stem+'.commands')
        lines=['TagDependency List '+tag,'EditTag '+tag,'ListFields','ForEach MultiplayerObject ListFields']
        if tag.endswith('.weapon'):lines+=['ForEach Barrels ListFields','ForEach Magazines ListFields','ForEach Triggers ListFields']
        commands.write_text('\n'.join(lines)+'\n')
        run=subprocess.run([str(OUT/'bin/TagTool.exe'),str(cache),'RunCommands',str(commands)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
        log=OUT/(stem+'.log');log.write_bytes(run.stdout)
        text=run.stdout.decode(errors='replace')
        assert run.returncode==0 and not re.search(r'ERROR|Exception|Invalid tag|Command failed',text),log
        references=sorted(set(re.findall(r'\[Index: 0x[0-9A-Fa-f]+, Offset: 0x[0-9A-Fa-f]+\] (\S+)',text)))
        fields=[]
        for line in text.splitlines():
            if re.match(r'\s*(?:\[\d+\] )?\w+: .* = ',line):fields.append(re.sub(r'\[0x[0-9A-Fa-f]+\]', '[tag]',line.strip()))
        assert references and fields,(tag,log)
        entries[tag]=dict(references=references,fields=fields,log=str(log))
    assert sha(cache)==before
    reports[label]=dict(cache=str(cache),sha256=before,tags=entries)
comparison=[]
for tag in tags:
    a=reports['360']['tags'][tag];b=reports['mcc']['tags'][tag]
    comparison.append(dict(tag=tag,stock_only_references=sorted(set(a['references'])-set(b['references'])),
        mcc_only_references=sorted(set(b['references'])-set(a['references'])),
        stock_only_fields=sorted(set(a['fields'])-set(b['fields'])),mcc_only_fields=sorted(set(b['fields'])-set(a['fields']))))
report=dict(sources=reports,comparison=comparison,limitation='Stock provenance, immediate dependencies and native TagTool field readback only. MCC assets retain native platform infrastructure; the later approved conversion reuses original H3 objects. Runtime appearance and behavior remain for MCC/360 testing.')
(OUT/'gameplay-extra-stock-audit.json').write_text(json.dumps(report,indent=2)+'\n')
for row in comparison:print('STOCK_GAMEPLAY_EXTRA',row['tag'],'reference differences',len(row['stock_only_references']),len(row['mcc_only_references']),'field differences',len(row['stock_only_fields']),len(row['mcc_only_fields']),flush=True)
