"""Verify reviewed donors against original caches and export their native tags."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

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
    kind=families[family].get('kind','shader')
    selected_configs=configs if kind=='shader' else {r['path']:r for r in json.loads((OUT/'stock-terrain-configurations.json').read_text())}
    selected_provenance=provenance if kind=='shader' else json.loads((OUT/'stock-terrain-provenance.json').read_text())
    if kind=='decal':
        selected_configs={r['path']:r for r in json.loads((OUT/'stock-decal-configurations.json').read_text())}
        selected_provenance=json.loads((OUT/'stock-decal-provenance.json').read_text())
    if kind=='water':
        water=json.loads((OUT/'stock-water-comparison.json').read_text())
        selected_configs={r['target']:dict(options=r['options'],sha256=water['source_hashes'][str(KIT/'tags'/r['target'])]) for r in water['candidates']}
        selected_provenance={r['target']:r['maps'] for r in water['candidates']}
    map_name=selected_provenance[donor][0]
    cache=Path('C:/X360/ISOs/H3M/maps')/('bunkerworld.map' if map_name=='standoff' else map_name+'.map')
    before=sha(cache)
    commands=OUT/(family+'-stock-options.commands')
    commands.write_text('EditTag '+donor+'\nForEach Options ListFields OptionIndex\n')
    run=subprocess.run([str(OUT/'bin/TagTool.exe'),str(cache),'RunCommands',str(commands)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (OUT/(family+'-stock-options.txt')).write_bytes(run.stdout)
    assert run.returncode==0 and sha(cache)==before
    options=[int(v) for v in re.findall(rb'OptionIndex: Int16 = (\d+)',run.stdout)]
    expected=selected_configs[donor]['options']
    count={'shader':10,'terrain':6,'water':8,'decal':6}[kind]
    assert len(options)==count and options==expected[:count],(donor,options,expected)
    world_witness=None
    if kind=='shader':
        assert not any(expected[10:]),('Review MCC-specific options',donor,expected)
        if options[9]!=0:
            # "Sometimes" supports stock third-person/world models as well as
            # first-person use. Require an actual original-cache reference;
            # never infer world use from the option's label alone.
            model=families[family].get('stock_world_model')
            assert options[9]==1 and model,('Review stock rendering context',donor,expected)
            commands=OUT/(family+'-world-model.commands')
            commands.write_text('EditTag '+model+'\nForEach Materials ListFields RenderMethod\n')
            run=subprocess.run([str(OUT/'bin/TagTool.exe'),str(cache),'RunCommands',str(commands)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
            (OUT/(family+'-world-model.log')).write_bytes(run.stdout)
            assert run.returncode==0 and sha(cache)==before
            references=re.findall(r'RenderMethod: CachedTag = \[0x[0-9A-Fa-f]+\] (\S+)',run.stdout.decode(errors='replace'))
            assert donor in references,('Stock world model does not reference donor',model,donor)
            world_witness=dict(model=model,material=donor,misc_option='first_person_sometimes')
    tag=KIT/'tags'/donor
    tag_hash=sha(tag)
    assert tag_hash==selected_configs[donor]['sha256']
    exported=OUT/'h3-shader-xml'/(Path(donor).name+'.xml')
    run=subprocess.run([str(KIT/'tool.exe'),'export-tag-to-xml',str(tag),str(exported)],cwd=KIT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (OUT/(family+'-donor-export.log')).write_bytes(run.stdout)
    assert run.returncode==0 and exported.is_file() and sha(tag)==tag_hash
    run=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('inspect_h3_terrain_options.py')),'--kind',kind,'--only',Path(donor).name],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (OUT/(family+'-effective-options.log')).write_bytes(run.stdout)
    assert run.returncode==0,run.stdout.decode(errors='replace')
    definition=ET.fromstring((OUT/('h3-'+kind+'-definition.xml')).read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
    categories=list(definition.find("block[@name='categories']"))
    option_paths=[]
    for i,category in enumerate(categories):
        index=expected[i] if i<len(expected) else 0
        name=category.find(f"block[@name='options']/element[@index='{index}']/field[@name='option']").get('value').rsplit(',',1)[0]
        if name:option_paths.append(name+'.render_method_option')
    native_output=OUT/(family+'-native-option-defaults.json')
    native_plan=OUT/(family+'-native-option-default-plan.json')
    native_plan.write_text(json.dumps(dict(Kit=str(KIT),Options=sorted(set(option_paths)),Output=str(native_output)),indent=2)+'\n')
    run=subprocess.run([str(OUT/'h3-api-probe/ReadH3ShaderConfigurations.exe'),str(native_plan)],cwd=KIT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    (OUT/(family+'-native-option-defaults.log')).write_bytes(run.stdout)
    assert run.returncode==0,run.stdout.decode(errors='replace')
    default_path=OUT/'h3-option-defaults.json'
    merged={r['path']:r for r in json.loads(default_path.read_text())} if default_path.is_file() else {}
    for row in json.loads(native_output.read_text()):
        if row['path'] in merged:assert merged[row['path']]['sha256']==row['sha256'],'Previously inspected stock option changed'
        merged[row['path']]=row
    default_path.write_text(json.dumps(list(merged.values()),indent=2)+'\n')
    (OUT/(family+'-donor-integrity.json')).write_text(json.dumps(dict(cache=str(cache),sha256=before,donor=donor,donor_sha256=tag_hash,stock_options=options,mcc_options=expected,stock_world_witness=world_witness),indent=2)+'\n')
    if families[family].get('stock_unlit_sky'):
        # Read the donor's actual native color function, rather than inventing
        # function bytes or assuming that "diffuse_only" means unlit.
        functions_path=OUT/'stock-sky-native-functions.json'
        previous_functions={r['path']:r for r in json.loads(functions_path.read_text())} if functions_path.exists() else {}
        functions_plan=OUT/'stock-sky-native-functions-plan.json'
        functions_plan.write_text(json.dumps(dict(Kit=str(KIT),Tags=[donor],IncludeFunctions=True,
            Output=str(OUT/'stock-sky-native-functions.json')),indent=2)+'\n')
        run=subprocess.run([str(OUT/'h3-api-probe/ReadH3ShaderConfigurations.exe'),str(functions_plan)],
            cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        (OUT/'stock-sky-native-functions.log').write_bytes(run.stdout)
        assert run.returncode==0,run.stdout.decode(errors='replace')
        for row in json.loads(functions_path.read_text()):previous_functions[row['path']]=row
        functions_path.write_text(json.dumps(list(previous_functions.values()),indent=2)+'\n')
    print('REVIEWED_DONOR_READY',family,donor,flush=True)
