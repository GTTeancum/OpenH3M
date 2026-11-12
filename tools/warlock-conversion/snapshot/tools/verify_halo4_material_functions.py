"""Run the official H3 editor interoperability probe on every distinct function."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT/'work/halo4-to-h3/haven'
KIT = ROOT/'work/editing-kits/h3ek'
source = OUT/'haven-material-function-audit.json'
before = hashlib.sha256(source.read_bytes()).hexdigest()
audit = json.loads(source.read_text())
assert audit['status']=='complete' and audit['source_tags_unchanged'] and audit['source_blend_unchanged']
distinct = {}
for material, parameters in audit['materials'].items():
    for parameter, functions in parameters.items():
        for index, function in enumerate(functions):
            key = tuple(function[k] for k in ('data_base64','source_type','source_input','range','time_period'))
            if key not in distinct:
                # Foundry's existing UV-function reader names these SCALE_X/Y;
                # the official H3 enumeration uses x/y where H4 uses u/v.
                expected = {'VALUE':('value','value'), 'COLOR':('color','color'),
                    'SCALE_X':('scale u','scale x'), 'SCALE_Y':('scale v','scale y')}
                source_type,target_type = expected[function['animated_type']]
                assert function['source_type']==source_type
                distinct[key] = dict(function, target_type=target_type, origins=[])
            distinct[key]['origins'].append(f'{material}:{parameter}[{index}]')
output = OUT/'h3-api/material-functions-readback.json'
env = os.environ.copy()
for key, relative in [('TEMP','temp'),('TMP','temp'),('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local')]:
    env[key] = str(OUT/'h3-authoring'/relative)
rows = list(distinct.values())
readback = dict(status='running',functions=[],batches=[],source_audit_sha256=before,
    limitation='Native editor interoperability only; no shader feature or runtime appearance acceptance.')
# H3 rejected a 65th parameter during the first diagnostic. Stay below its
# native per-shader limit; there is no reason to aggregate all map functions
# into a single production shader.
for batch_index,start in enumerate(range(0,len(rows),32)):
    stem = f'material-functions-{batch_index:02}'
    plan_path = OUT/'h3-api'/(stem+'-plan.json')
    batch_output = OUT/'h3-api'/(stem+'-readback.json')
    plan = dict(Kit=str(KIT),Donor=r'levels\shared\shaders\simple\grey.shader',
        Target=rf'levels\custom\haven_function_probe\functions_{batch_index:02}.shader',
        Output=str(batch_output),Functions=rows[start:start+32])
    plan_path.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
    log = OUT/'h3-api'/(stem+'-readback.log')
    with log.open('wb') as stream:
        result = subprocess.run([str(OUT/'h3-api/VerifyH4FunctionsInH3.exe'),str(plan_path)],
            cwd=KIT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=30)
    print('\n'.join(log.read_text(errors='replace').splitlines()[-8:]),flush=True)
    assert result.returncode==0, result.returncode
    native = json.loads(batch_output.read_text())
    assert native['status']=='verified' and native['donor_unchanged']
    readback['batches'].append(native)
    readback['functions'].extend(dict(f,batch=batch_index) for f in native['functions'])
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
assert len(readback['functions'])==len(distinct)
readback['status']='verified'
output.write_text(json.dumps(readback,indent=2)+'\n',encoding='utf-8')
print('H4_H3_FUNCTIONS_VERIFIED',json.dumps(dict(source_records=audit['summary']['functions'],
    distinct_records=len(distinct),scalar_samples=sum(f['samples'] for f in readback['functions']),
    max_scalar_error=max(f['max_sample_error'] for f in readback['functions']))),flush=True)
