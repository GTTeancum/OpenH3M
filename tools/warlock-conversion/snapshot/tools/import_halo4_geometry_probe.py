"""Compile the full diagnostic ASS through unchanged official H3 Tool.

Neutral stock shader aliases isolate geometry errors. No collision category,
material appearance, lighting or gameplay acceptance follows from this probe.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'work/halo4-to-h3/haven'
KIT=ROOT/'work/editing-kits/h3ek'

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

variant=sys.argv[1] if len(sys.argv)>1 else 'full'
assert (variant in ('full','world_scaled','world_baked','world_with_instance','haven_linked','haven_one_sided_joined','haven_one_sided_joined_surfaces','haven_one_sided_joined_surfaces_opaque_draft','haven_one_sided_joined_surfaces_opaque_draft_reflections')
    or variant=='haven_one_sided_joined_surfaces_opaque_draft_reflections_worldrender'
    or re.fullmatch(r'(world_with_hvn_\d{4}|range_\d{4}_\d{4})(_one_sided)?(_collision_role)?',variant)
    or re.fullmatch(r'haven_one_sided_joined_errors(_precise|_surfaces)?',variant)) and len(sys.argv)<=2
name='haven-geometry-probe' if variant=='full' else 'haven-'+variant+'-probe'
report_path=OUT/(name+'-native.json')
assert not report_path.exists(),'Preserve the previous report before an intentional reimport'
probe=json.loads((OUT/(name+'-ass.json')).read_text())
assert probe['geometry_probe'] and probe['source_unchanged']
if variant=='full':assert probe['triangles_checked']==257822 and probe['instances']==1098
elif variant=='haven_linked':assert probe['link_identical_probe'] and probe['instances']==1098
elif variant in ('haven_one_sided_joined','haven_one_sided_joined_surfaces','haven_one_sided_joined_surfaces_opaque_draft','haven_one_sided_joined_surfaces_opaque_draft_reflections'):assert probe['join_collision_probe'] and probe['instances']==885
elif variant=='haven_one_sided_joined_surfaces_opaque_draft_reflections_worldrender':
    assert probe['join_collision_probe'] and probe['instances']==885
    assert probe['world_render']['source_instance']=='%!*hvn_0607' and probe['world_render']['triangles']==4
elif variant.startswith('haven_one_sided_joined_errors'):assert probe['collision_errors_only'] and probe['instances']==44
elif variant.startswith('range_'):
    start,end=probe['instance_range']
    assert probe['instances']==end-start+36
else:assert probe['instances']==(37 if variant.startswith('world_with_') else 36) and probe['world_only']
assert sha(probe['source'])==probe['source_sha256']
assert sha(probe['ass'])==probe['ass_sha256']
material_updates={}
if probe.get('opaque_draft'):
    updates=json.loads((OUT/'material-authoring/opaque-draft/physical-material-update.json').read_text())
    material_updates={str(KIT/'tags'/r['target']):r for r in updates['updates']}
    if probe.get('reflection_draft'):
        updates=json.loads((OUT/'material-authoring/reflection-draft/physical-material-update.json').read_text())
        material_updates.update({str(KIT/'tags'/r['target']):r for r in updates['updates']})
for binding in probe['probe_shader_bindings']:
    update=material_updates.get(binding['target'])
    if update:assert binding['sha256'] in (update['before_sha256'],update['after_sha256'])
    assert sha(binding['target'])==(update['after_sha256'] if update else binding['sha256'])
tool=KIT/'tool.exe'
assert sha(tool)=='1dcf51ec39bdf61b6a6ae40917908cf23a247bfedb7a4bff07124f508ee0f3b5'
directory=OUT/'h3-authoring/geometry-probe'/variant
directory.mkdir(parents=True,exist_ok=True)
env=os.environ.copy()
for key,suffix in [('TEMP','temp'),('TMP','temp'),('APPDATA','profile/roaming'),('LOCALAPPDATA','profile/local')]:
    path=OUT/'h3-authoring'/suffix
    path.mkdir(parents=True,exist_ok=True)
    env[key]=str(path)
command=[str(tool),'structure',str(Path(probe['ass']).relative_to(KIT/'data'))]
log_path=directory/'import.log'
assert not log_path.exists(),'Preserve earlier logs before an intentional reimport'
started=time.monotonic()
with log_path.open('wb') as stream:
    process=subprocess.Popen(command,cwd=KIT,env=env,stdout=stream,stderr=subprocess.STDOUT)
    print('H4_FULL_GEOMETRY_TOOL_PID',process.pid,flush=True)
    timed_out=False
    try:
        code=process.wait(timeout=180)
    except subprocess.TimeoutExpired:
        timed_out=True
        process.kill()
        code=process.wait(timeout=10)
log=log_path.read_text(errors='replace')
issues=[line.strip() for line in log.splitlines()
    if re.search(r'-ERROR-|-FATAL-|\bWARNING\b|\bASSERTION\b',line.upper())]
outputs=[]
for path in (KIT/'tags/levels/custom/haven_geometry_probe').glob(Path(probe['ass']).stem+'.*'):
    if path.is_file():
        outputs.append(dict(path=str(path.relative_to(ROOT)),bytes=path.stat().st_size,sha256=sha(path)))
assert sha(probe['source'])==probe['source_sha256']
report=dict(status='watchdog_timeout' if timed_out else 'diagnostic_finished',
    command=command,tool_sha256=sha(tool),exit_code=code,seconds=time.monotonic()-started,
    source_ass_sha256=probe['ass_sha256'],log=str(log_path.relative_to(ROOT)),log_sha256=sha(log_path),
    issue_lines=issues,issue_counts=dict(Counter(issues)),outputs=outputs,
    imported_structure_marker='=== imported structure' in log,
    source_blend_unchanged=True,geometry_accepted=False,
    limitation=('Opaque draft material binding; deferred surfaces retain neutral placeholders. ' if probe.get('opaque_draft') else
        'Neutral-material geometry diagnostic; inspect errors and native output before acceptance. ')+
        'Collision-category mappings, materials, lighting, native resource compatibility and gameplay remain unresolved.')
report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('H4_FULL_GEOMETRY_TOOL_RESULT',json.dumps({k:report[k] for k in
    ('status','exit_code','seconds','imported_structure_marker','source_blend_unchanged')}),flush=True)
print('H4_FULL_GEOMETRY_ISSUES',json.dumps(dict(count=len(issues),first=issues[:12],last=issues[-5:])),flush=True)
