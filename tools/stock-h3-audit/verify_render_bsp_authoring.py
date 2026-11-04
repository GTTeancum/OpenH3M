"""Read back saved original geometry and both preserved collision layers."""
import hashlib
import json
from pathlib import Path
import runpy
import bpy

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
report=json.loads((OUT/'h3-render-bsp-authoring.json').read_text())
source=Path(bpy.data.filepath);before=sha(source)
bound=source.name=='battle-canyon-h3-materials.blend'
assert sha(report['scene'])==report['scene_sha256']
if bound:assert before==json.loads((OUT/'h3-material-bindings.json').read_text())['scene_sha256']
else:assert str(source)==report['scene'] and before==report['scene_sha256']
previous=OUT/'render-bsp-before-battle-canyon-h3-authoring.blend'
assert sha(previous)==report['before_sha256']
names=[name for case in report['cases'] for name in (case['target'],case['collision_child'])]
# Pending trims must also retain their original geometry and controls.
names+=list(report['pending'].values())
current={name:bpy.context.scene.objects[name] for name in names}
with bpy.data.libraries.load(str(previous),link=False) as (_,loaded):loaded.objects=list(names)
old=dict(zip(names,loaded.objects))
cases={case['target']:case for case in report['cases']}
for name,obj in current.items():
    original=old[name];mesh=obj.data;baseline=original.data
    assert obj.matrix_basis==original.matrix_basis and obj.matrix_parent_inverse==original.matrix_parent_inverse,name
    if obj.parent:assert original.parent==old[obj.parent.name]
    else:assert original.parent is None
    nv,np,nl=len(baseline.vertices),len(baseline.polygons),len(baseline.loops)
    assert [tuple(v.co) for v in mesh.vertices[:nv]]==[tuple(v.co) for v in baseline.vertices],name
    assert [tuple(p.vertices) for p in mesh.polygons[:np]]==[tuple(p.vertices) for p in baseline.polygons],name
    assert [p.material_index for p in mesh.polygons[:np]]==[p.material_index for p in baseline.polygons],name
    assert [tuple(v.vector) for v in mesh.corner_normals[:nl]]==[tuple(v.vector) for v in baseline.corner_normals],name
    assert [l.name for l in mesh.uv_layers]==[l.name for l in baseline.uv_layers],name
    for layer in mesh.uv_layers:
        assert [tuple(v.uv) for v in layer.data[:nl]]==[tuple(v.uv) for v in baseline.uv_layers[layer.name].data],name
    if name in cases:
        joined=cases[name]['join']
        assert [list(v.co) for v in mesh.vertices[nv:]]==joined['collision_vertices_authoring'],name
        assert [list(p.vertices) for p in mesh.polygons[np:]]==[[i+nv for i in face] for face in joined['collision_faces_authoring']],name
        for p,expected in zip(mesh.polygons[np:],joined['collision_materials_authoring']):
            mat=mesh.materials[p.material_index]
            assert mat.ass_jms.name_override==expected and mat.ass_jms.is_bm and mat.ass_jms.precise and mat.ass_jms.collision_only and not mat.ass_jms.render_only,name
    else:assert (len(mesh.vertices),len(mesh.polygons),len(mesh.loops))==(nv,np,nl),name
for case in report['cases']:
    for row in case['changes']:
        mat=current[row['object']].data.materials[row['slot']]
        original=old[row['object']].data.materials[row['slot']]
        assert mat.nwo.shader_path==original.nwo.shader_path==row['shader']
        assert mat.ass_jms.is_bm and mat.ass_jms.precise and mat.ass_jms.render_only==row['render_only']
        for prop in mat.ass_jms.bl_rna.properties:
            if prop.type=='BOOLEAN' and prop.identifier not in ('is_bm','precise') and not (row['object']==case['target'] and prop.identifier=='render_only'):
                assert getattr(mat.ass_jms,prop.identifier)==getattr(original.ass_jms,prop.identifier)
for name in report['pending'].values():
    for mat,original in zip(current[name].data.materials,old[name].data.materials):
        assert mat.nwo.shader_path==original.nwo.shader_path
        for prop in mat.ass_jms.bl_rna.properties:
            if prop.type=='BOOLEAN':assert getattr(mat.ass_jms,prop.identifier)==getattr(original.ass_jms,prop.identifier)
assert sha(source)==before
result=dict(scene_sha256=before,targets=list(cases),pending_unchanged=list(report['pending'].values()),
    exact_visible_geometry_normals_uvs_transforms=True,exact_original_collision_layers=True,standard_flags_verified=True,
    limitation='Saved scene evidence only; native compile and MCC remain independent gates.')
(OUT/('render-bsp-'+('bound' if bound else 'saved')+'-verification.json')).write_text(json.dumps(result,indent=2)+'\n')
print('RENDER_BSP_SAVED_VERIFIED',json.dumps(result),flush=True)
