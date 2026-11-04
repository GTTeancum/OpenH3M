"""Fresh saved-scene check of boulder geometry, normals and material flags."""
import hashlib
import json
from pathlib import Path
import runpy
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
report=json.loads((OUT/'h3-boulder-batch-authoring.json').read_text())
source=Path(bpy.data.filepath);before=sha(source)
bound=source.name=='battle-canyon-h3-materials.blend'
assert sha(report['scene'])==report['scene_sha256']
if bound:assert before==json.loads((OUT/'h3-material-bindings.json').read_text())['scene_sha256']
else:assert str(source)==report['scene'] and before==report['scene_sha256']
previous=OUT/'boulder-batch-before-battle-canyon-h3-authoring.blend'
assert sha(previous)==report['before_sha256']
names=list(dict.fromkeys(r['object'] for r in report['changes']))
current={name:bpy.context.scene.objects[name] for name in names}
with bpy.data.libraries.load(str(previous),link=False) as (_,loaded):loaded.objects=list(names)
old=dict(zip(names,loaded.objects))
for name,obj in current.items():
    original=old[name];mesh=obj.data;baseline=original.data
    # Appended objects are not linked/evaluated; compare stored transforms and
    # the actual parent relationship instead of their unevaluated matrix_world.
    assert obj.matrix_basis==original.matrix_basis
    assert obj.matrix_parent_inverse==original.matrix_parent_inverse
    if obj.parent:assert original.parent==old[obj.parent.name]
    else:assert original.parent is None
    assert [tuple(v.co) for v in mesh.vertices]==[tuple(v.co) for v in baseline.vertices]
    assert [tuple(p.vertices) for p in mesh.polygons]==[tuple(p.vertices) for p in baseline.polygons]
    assert [p.material_index for p in mesh.polygons]==[p.material_index for p in baseline.polygons]
    assert [tuple(v.vector) for v in mesh.corner_normals]==[tuple(v.vector) for v in baseline.corner_normals]
    assert [l.name for l in mesh.uv_layers]==[l.name for l in baseline.uv_layers]
    for layer in mesh.uv_layers:assert [tuple(v.uv) for v in layer.data]==[tuple(v.uv) for v in baseline.uv_layers[layer.name].data]
for row in report['changes']:
    obj=current[row['object']];original=old[row['object']]
    mat=obj.data.materials[row['slot']];oldmat=original.data.materials[row['slot']]
    assert mat.name==row['material'] and mat.nwo.shader_path==oldmat.nwo.shader_path==row['shader']
    assert mat.ass_jms.is_bm and mat.ass_jms.precise and mat.ass_jms.render_only==row['render_only']
    render=obj.name in report['eligible']
    for prop in mat.ass_jms.bl_rna.properties:
        if prop.type=='BOOLEAN' and prop.identifier not in ('is_bm','precise') and not (render and prop.identifier=='render_only'):
            assert getattr(mat.ass_jms,prop.identifier)==getattr(oldmat.ass_jms,prop.identifier),(mat.name,prop.identifier)
assert sha(source)==before
result=dict(scene_sha256=before,objects_checked=len(names),material_slots_checked=len(report['changes']),
    exact_geometry_normals_uvs_transforms=True,standard_flags_verified=True,
    limitation='Saved authoring preservation only; native compilation and MCC remain independent gates.')
(OUT/('boulder-batch-'+('bound' if bound else 'saved')+'-verification.json')).write_text(json.dumps(result,indent=2)+'\n')
print('BOULDER_BATCH_SAVED_VERIFIED',json.dumps(result),flush=True)
