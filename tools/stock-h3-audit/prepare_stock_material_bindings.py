"""Verify unchanged stock material reuse; never generate or rewrite shader tags."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
REACH=ROOT/'work/editing-kits/hrek'
config=json.loads(Path(__file__).with_name('stock_material_bindings.json').read_text())
inventory={r['path']:r for r in json.loads((OUT/'stock-shader-configurations.json').read_text())}
env=os.environ.copy()
for key,rel in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/rel)
env['DOTNET_ROLL_FORWARD']='Major'

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

rows={}
for source,choice in config.items():
    target=KIT/'tags'/choice['target']
    expected=inventory[choice['target']]
    assert sha(target)==expected['sha256']
    cache=Path('C:/X360/ISOs/H3M/maps')/(choice['original_map']+'.map')
    before=sha(cache)
    commands=OUT/(Path(source).stem+'-stock-binding.commands')
    commands.write_text('EditTag '+choice['target']+'\nForEach Options ListFields OptionIndex\n')
    result=subprocess.run([str(OUT/'bin/TagTool.exe'),str(cache),'RunCommands',str(commands)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (OUT/(Path(source).stem+'-stock-binding.log')).write_bytes(result.stdout)
    assert result.returncode==0 and sha(cache)==before
    options=[int(v) for v in re.findall(rb'OptionIndex: Int16 = (\d+)',result.stdout)]
    assert len(options)==10 and options==expected['options'][:10] and not any(expected['options'][10:])
    assert choice['allowed_face_modes']==['sphere_collision_only','lightmap_only']
    rows[source]=dict(target=choice['target'],target_sha256=sha(target),source_sha256=sha(REACH/'tags'/source),
        original_cache=str(cache),original_cache_sha256=before,stock_options=options,
        allowed_face_modes=choice['allowed_face_modes'],limitation='Nonvisual binding only. Source emission/collision metadata still requires authoring verification.')
    print('STOCK_MATERIAL_BINDING_VERIFIED',source,flush=True)
(OUT/'stock-material-bindings.json').write_text(json.dumps(rows,indent=2)+'\n')
