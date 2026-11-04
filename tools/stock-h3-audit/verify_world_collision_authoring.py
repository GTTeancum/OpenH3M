"""Verify saved visible geometry and imported original collision after the split."""
import hashlib
import json
from pathlib import Path
import runpy
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
def read(name):return json.loads((OUT/name).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
report=read('h3-world-collision-authoring.json')
inspection=read('world-source-collision-inspection.json')
source=Path(bpy.data.filepath)
bound=source.name=='battle-canyon-h3-materials.blend'
assert sha(report['scene'])==report['scene_sha256']
if bound:assert sha(source)==read('h3-material-bindings.json')['scene_sha256']
else:assert str(source)==report['scene'] and sha(source)==report['scene_sha256']
before=sha(source)
assert sha(report['source_scene_before_split'])==report['before_sha256']
assert sha(inspection['scene'])==inspection['scene_sha256']==report['original_collision_scene_sha256']
world=bpy.data.objects['cex_beaver_creek_structure'].data
collision=bpy.data.objects['bc_world_collision'].data
with bpy.data.libraries.load(report['source_scene_before_split'],link=False) as (_,loaded):loaded.objects=['cex_beaver_creek_structure']
old=loaded.objects[0].data
face_ids=[v.value for v in world.attributes['bc_world_source_face'].data]
corner_ids=[v.value for v in world.attributes['bc_world_source_corner'].data]
assert face_ids==report['source_world_face_ids']
assert set(face_ids)==set(range(len(old.polygons)))-set(report['removed_nonvisual_faces'])
for face,original_index in zip(world.polygons,face_ids):
    original=old.polygons[original_index]
    assert [corner_ids[i] for i in face.loop_indices]==list(original.loop_indices)
    mat=world.materials[face.material_index]
    assert mat.nwo.shader_path==old.materials[original.material_index].nwo.shader_path
    for key,value in report['render_flag_overrides'].items():assert getattr(mat.ass_jms,key)==value
maximum_normal_delta=0
for i,loop in enumerate(world.loops):
    oi=corner_ids[i]
    assert world.vertices[loop.vertex_index].co==old.vertices[old.loops[oi].vertex_index].co
    for layer in world.uv_layers:assert layer.data[i].uv==old.uv_layers[layer.name].data[oi].uv
    maximum_normal_delta=max(maximum_normal_delta,(world.corner_normals[i].vector-old.corner_normals[oi].vector).length)
assert maximum_normal_delta<1e-4
with bpy.data.libraries.load(inspection['scene'],link=False) as (_,loaded):loaded.objects=['bc_original_world_collision_diagnostic']
original=loaded.objects[0].data
assert len(collision.vertices)==len(original.vertices) and len(collision.polygons)==len(original.polygons)
assert all(v.co==o.co for v,o in zip(collision.vertices,original.vertices))
properties={p.type:original.attributes[p.attribute_name] for p in original.nwo.face_props}
for face,other in zip(collision.polygons,original.polygons):
    assert list(face.vertices)==list(other.vertices)
    mat=collision.materials[face.material_index];oldmat=original.materials[other.material_index]
    assert mat.nwo.shader_path==oldmat.nwo.shader_path
    p=mat.ass_jms
    assert p.is_bm and p.precise and not p.render_only and not p.lightmap_only
    assert p.slip_surface==bool(properties['slip_surface'].data[face.index].value)
    assert p.sphere_collision_only==bool(properties['face_mode'].data[face.index].value)
    assert p.two_sided==bool(properties['face_sides'].data[face.index].value)
    assert p.collision_only==(bool(mat.nwo.shader_path) and not p.sphere_collision_only)
    if not mat.nwo.shader_path:assert p.name_override=='+sky'
result=dict(scene_sha256=before,authoring_scene_sha256=report['scene_sha256'],visible_faces_checked=len(world.polygons),
    visible_corners_checked=len(world.loops),maximum_visible_normal_delta=maximum_normal_delta,
    collision_vertices_checked=len(collision.vertices),collision_faces_checked=len(collision.polygons),
    limitation='Saved source geometry, normals, UVs, materials and standard flags checked. ASS/full native import and MCC remain separate gates.')
assert sha(source)==before
(OUT/('world-collision-'+('bound' if bound else 'saved')+'-verification.json')).write_text(json.dumps(result,indent=2)+'\n')
print('WORLD_COLLISION_AUTHORING_VERIFIED',json.dumps(result),flush=True)
