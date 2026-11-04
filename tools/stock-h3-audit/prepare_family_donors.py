"""Verify reviewed donors against original caches and export their native tags."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
families=json.loads(Path(__file__).with_name('material_families.json').read_text())
parser=argparse.ArgumentParser()
parser.add_argument('--family',action='append',choices=sorted(families),required=True)
args=parser.parse_args()
env=os.environ.copy()
for key,relative in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/relative)
env['DOTNET_ROLL_FORWARD']='Major'
configs={r['path']:r for r in json.loads((OUT/'stock-shader-configurations.json').read_text())}
provenance=json.loads((OUT/'stock-shader-map-provenance.json').read_text())
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
for family in args.family:
    donor=families[family]['donor']
    map_name=provenance[donor][0]
    cache=Path('C:/X360/ISOs/H3M/maps')/('bunkerworld.map' if map_name=='standoff' else map_name+'.map')
    before=sha(cache)
    commands=OUT/(family+'-stock-options.commands')
    commands.write_text('EditTag '+donor+'\nForEach Options ListFields OptionIndex\n')
    run=subprocess.run([str(OUT/'bin/TagTool.exe'),str(cache),'RunCommands',str(commands)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (OUT/(family+'-stock-options.txt')).write_bytes(run.stdout)
    assert run.returncode==0 and sha(cache)==before
    options=[int(v) for v in re.findall(rb'OptionIndex: Int16 = (\d+)',run.stdout)]
    expected=configs[donor]['options']
    assert len(options)==10 and options==expected[:10],(donor,options,expected)
    assert options[9]==0 and not any(expected[10:]),('Review non-world or MCC-specific options',donor,expected)
    tag=KIT/'tags'/donor
    tag_hash=sha(tag)
    assert tag_hash==configs[donor]['sha256']
    exported=OUT/'h3-shader-xml'/(Path(donor).name+'.xml')
    run=subprocess.run([str(KIT/'tool.exe'),'export-tag-to-xml',str(tag),str(exported)],cwd=KIT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (OUT/(family+'-donor-export.log')).write_bytes(run.stdout)
    assert run.returncode==0 and exported.is_file() and sha(tag)==tag_hash
    run=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('inspect_h3_terrain_options.py')),'--kind','shader','--only',Path(donor).name],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (OUT/(family+'-effective-options.log')).write_bytes(run.stdout)
    assert run.returncode==0,run.stdout.decode(errors='replace')
    (OUT/(family+'-donor-integrity.json')).write_text(json.dumps(dict(cache=str(cache),sha256=before,donor=donor,donor_sha256=tag_hash,stock_options=options,mcc_options=expected),indent=2)+'\n')
    print('REVIEWED_DONOR_READY',family,donor,flush=True)
