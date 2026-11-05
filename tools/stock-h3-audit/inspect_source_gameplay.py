"""Read source gameplay palette paths and team meanings through ManagedBlam."""
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/hrek'
for key,path in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:os.environ[key]=str(OUT/path)
sys.path.insert(0,str(OUT/'python-packages'))
import clr
clr.AddReference(str(KIT/'bin/ManagedBlam.dll'))
import Bungie
callback=Bungie.ManagedBlamCrashCallback(lambda info:None);parameters=Bungie.ManagedBlamStartupParameters();parameters.InitializationLevel=Bungie.InitializationType.TagsOnly
base=r'levels\dlc\cex_beaver_creek\cex_beaver_creek';source=KIT/'tags'/(base+'.scenario');before=hashlib.sha256(source.read_bytes()).hexdigest()
Bungie.ManagedBlamSystem.Start(str(KIT),callback,parameters)
tag=Bungie.Tags.TagFile()
try:
    tag.Load(Bungie.Tags.TagPath.FromPathAndExtension(base,'scenario'))
    palettes={}
    for name in ('scenery palette','weapon palette','equipment palette','crate palette','control palette','sound scenery palette'):
        palettes[name]=[str(e.SelectField('name').Path.RelativePathWithExtension) for e in tag.SelectField(name).Elements]
    team=tag.SelectField('scenery').Elements[0].SelectField('Struct:multiplayer data/owner team')
    teams=[dict(index=int(item.EnumIndex),name=str(item.EnumName)) for item in team.Items]
finally:
    tag.Dispose();Bungie.ManagedBlamSystem.Stop()
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(OUT/'original-gameplay-palettes.json').write_text(json.dumps(dict(source=str(source),sha256=before,palettes=palettes,team_options=teams),indent=2)+'\n')
print('ORIGINAL_GAMEPLAY', {k:len(v) for k,v in palettes.items()},teams,flush=True)
