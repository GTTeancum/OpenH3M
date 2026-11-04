"""Apply the diagnosed native H3 authoring flags to boulder definition 74 only.

Copies material slots locally; does not alter geometry, shaders, exporter or
compiler. Native compilation differs slightly from source and still needs MCC
review. Other collision definitions remain unresolved.
"""
import hashlib
import json
from pathlib import Path
import runpy
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
project=bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name=project.project_name=bpy.context.scene.nwo.scene_project
project.project_path=str(ROOT/'work/editing-kits/hrek')
project.tags_directory=str(ROOT/'work/editing-kits/hrek/tags')
project.data_directory=str(ROOT/'work/editing-kits/hrek/data')
project.corinth=False
source=Path(bpy.data.filepath)
assert source==OUT/'battle-canyon-h3-authoring.blend'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
before=sha(source)
report_path=OUT/'h3-boulder-collision-authoring.json'
previous=json.loads(report_path.read_text()) if report_path.is_file() else None
if previous:
    assert previous['scene_sha256']==before
else:
    assert before=='b0a48702e42d7edb421dfcff320413077d4accb3d5fb85a68dcfcbccf1fdccc5'
stem='collision-workflow-precise-render-only'
probe=json.loads((OUT/(stem+'-probe.json')).read_text())
comparison=json.loads((OUT/(stem+'-geometry-comparison.json')).read_text())
baseline=json.loads((OUT/'collision-workflow-geometry-comparison.json').read_text())
native=json.loads((OUT/(stem+'-native.json')).read_text())
assert sha(probe['ass'])==comparison['ass_sha256']==native['ass_sha256']
assert not any('ERROR' in line or 'FATAL' in line for line in native['issue_lines'])
assert comparison['render_triangles_matched']==710 and comparison['render_winding_preserved']
assert comparison['checks']['uv'] and comparison['checks']['collision_samples']
assert comparison['max_render_position_delta_world_units']<baseline['max_render_position_delta_world_units']
assert comparison['max_normal_delta']==baseline['max_normal_delta']
target=bpy.context.scene.objects['boulder_low035']
child=bpy.context.scene.objects['@boulder_low035_collision']
assert target.data.name=='instance_definition:74' and child.parent==target
assert [o for o in bpy.context.scene.objects if o.type=='MESH' and o.data==target.data]==[target]
assert not any(getattr(target.data.nwo,f'proxy_physics{i}') for i in range(200))
def geometry(mesh):
    return dict(vertices=[tuple(v.co) for v in mesh.vertices],faces=[tuple(p.vertices) for p in mesh.polygons],
        uv={layer.name:[tuple(v.uv) for v in layer.data] for layer in mesh.uv_layers})
snapshots={obj.name:geometry(obj.data) for obj in (target,child)}
changes=[]
for obj in (target,child):
    for index,material in enumerate(list(obj.data.materials)):
        existing=next((r for r in previous['changes'] if r['object']==obj.name and r['slot']==index),None) if previous else None
        if existing:
            assert material.name==existing['material']
            copy=material
            source_name=existing['source_material']
        else:
            copy=material.copy()
            source_name=material.name
            copy.name=material.name+'_native_collision'
        # A copied special material must retain its exact native keyword.
        copy.ass_jms.name_override=material.ass_jms.name_override or source_name
        copy.ass_jms.is_bm=True
        copy.ass_jms.precise=True
        if obj==target:copy.ass_jms.render_only=True
        copy.update_tag()
        obj.data.materials[index]=copy
        changes.append(dict(object=obj.name,slot=index,source_material=source_name,material=copy.name,
            precise=copy.ass_jms.precise,render_only=copy.ass_jms.render_only))
    obj.data.update()
    obj.update_tag(refresh={'DATA'})
    assert geometry(obj.data)==snapshots[obj.name]
bpy.context.view_layer.update()
bpy.context.preferences.filepaths.save_version=0
bpy.context.scene.nwo.lights_export_on_save=False
bpy.context.scene.nwo.prefabs_export_on_save=False
bpy.ops.wm.save_as_mainfile(filepath=str(source))
# Refresh water provenance only after rechecking all original UV values.
runpy.run_path(str(ROOT/'tools/stock-h3-audit/prepare_water_channels.py'))
report=dict(scene=str(source),before_sha256=previous['before_sha256'] if previous else before,
    previous_scene_sha256=before,scene_sha256=sha(source),changes=changes,
    vertices_faces_uvs_unchanged=True,native_comparison=comparison,
    limitation='One diagnosed boulder only. Bound scene/ASS must be refreshed; full import, lighting and MCC approval remain. Strict source position/normal comparisons still report native compiler differences.')
report_path.write_text(json.dumps(report,indent=2)+'\n')
print('H3_BOULDER_COLLISION_AUTHORED',sha(source),len(changes),'local material slots',flush=True)
