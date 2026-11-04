"""Check saved H3 glass bindings against native Reach controls and stock donors."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
REACH=ROOT/'work/editing-kits/hrek'
env=os.environ.copy()
for key,rel in [('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local'),('TEMP','temp'),('TMP','temp')]:env[key]=str(OUT/rel)
source=json.loads((OUT/'glass-native-source-controls.json').read_text())
families={name:json.loads((OUT/(name+'-family/report.json')).read_text()) for name in ['glass_interior','glass_exterior']}
targets={m['source']:m['target'] for r in families.values() for m in r['materials']}
donors={r['donor'] for r in families.values()}
plan=OUT/'glass-native-bindings-plan.json'
plan.write_text(json.dumps(dict(Kit=str(KIT),Tags=sorted(set(targets.values())|donors),IncludeFunctions=True,
    Output=str(OUT/'glass-native-bindings.json')),indent=2)+'\n')
result=subprocess.run([str(OUT/'h3-api-probe/ReadH3ShaderConfigurations.exe'),str(plan)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
(OUT/'glass-native-bindings.log').write_bytes(result.stdout)
assert result.returncode==0,result.stdout.decode(errors='replace')
native={r['path']:r for r in json.loads((OUT/'glass-native-bindings.json').read_text())}
packed=json.loads((OUT/'glass-channel-preparation/native-import-report.json').read_text())
assert hashlib.sha256((KIT/'tags'/packed['target']).read_bytes()).hexdigest()==packed['target_sha256']
rows=[]
for row in source:
    assert hashlib.sha256((REACH/'tags'/row['source']).read_bytes()).hexdigest()==row['source_sha256']
    actual=native[targets[row['source']]]
    donor=native[families[row['family']]['donor']]
    assert actual['options']==donor['options']
    parameters={p['name']:p for p in actual['parameters']}
    donor_parameters={p['name']:p for p in donor['parameters']}
    assert parameters['base_map']['bitmap']==packed['target']
    for target_name,source_name in [('base_map','opacity_texture'),('specular_mask_texture','base_map'),('bump_map','bump_map'),('environment_map','environment_map')]:
        old=row['parameters'][source_name]
        new=parameters[target_name]
        if target_name!='base_map':
            assert new['bitmap']==str(Path(r'levels\custom\battle_canyon_fresh\bitmaps')/Path(old['bitmap']).name)
        assert len(new['functions'])==len(old['functions'])
        for saved,original in zip(new['functions'],old['functions']):
            assert all(saved[key]==value for key,value in original.items()),(row['source'],target_name,saved,original)
    retained={}
    if row['family']=='glass_exterior':
        for name in ['fresnel_coefficient','fresnel_curve_steepness','fresnel_curve_bias']:
            assert parameters.get(name)==donor_parameters.get(name),(name,parameters.get(name),donor_parameters.get(name))
            retained[name]=parameters.get(name)
    rows.append(dict(source=row['source'],target=actual['path'],target_sha256=actual['sha256'],
        donor=donor['path'],transparency_scale=2,specular_scale=1,stock_fresnel_controls=retained))
    print('NATIVE_GLASS_BINDINGS_CHECKED',actual['path'],flush=True)
(OUT/'glass-material-verification.json').write_text(json.dumps(dict(materials=rows,
    limitation='Native input and donor checks; MCC appearance, transparency sorting and reflection response remain unverified.'),indent=2)+'\n')
