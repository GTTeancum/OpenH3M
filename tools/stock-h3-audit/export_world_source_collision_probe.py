"""Test original world collision with standard H3 render/collision-only flags.

Diagnostic scene only; unchanged upstream ASS exporter and original geometry.
"""
import collections
import hashlib
import json
from pathlib import Path
import runpy
import bpy
import bmesh

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
inspection=json.loads((OUT/'world-source-collision-inspection.json').read_text())
bindings=json.loads((OUT/'h3-material-bindings.json').read_text())
source=Path(bpy.data.filepath)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert str(source)==inspection['scene'] and sha(source)==inspection['scene_sha256']
assert sha(inspection['source'])==inspection['source_sha256']==bindings['scene_sha256']
assert sha(inspection['original_tag'])==inspection['original_tag_sha256']
world=bpy.data.objects['cex_beaver_creek_structure']
collision=bpy.data.objects['bc_original_world_collision_diagnostic']
assert len(bpy.context.scene.objects)==69
# The original collision now supplies these nonvisual source surfaces once.
# Keep all visible triangles in the render mesh, without using them as collision.
remove=[]
for face in world.data.polygons:
    material=world.data.materials[face.material_index]
    if (material.ass_jms.name_override or material.name)=='+sky' or material.ass_jms.collision_only or material.ass_jms.sphere_collision_only:
        remove.append(face.index)
bm=bmesh.new();bm.from_mesh(world.data);bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm,geom=[bm.faces[i] for i in remove],context='FACES')
bm.to_mesh(world.data);bm.free()
for index,material in enumerate(list(world.data.materials)):
    copied=material.copy()
    p=copied.ass_jms
    p.is_bm=p.precise=p.render_only=True
    p.collision_only=p.sphere_collision_only=False
    world.data.materials[index]=copied
    copied.update_tag()
mesh=collision.data
settings=[dict(slip=False,two_sided=False,sphere=False) for _ in mesh.polygons]
for prop in mesh.nwo.face_props:
    key={'slip_surface':'slip','face_sides':'two_sided','face_mode':'sphere'}[prop.type]
    if key=='sphere':assert prop.face_mode=='sphere_collision_only'
    for index,item in enumerate(mesh.attributes[prop.attribute_name].data):
        if item.value:settings[index][key]=True
original_slots=list(mesh.materials)
variants={}
for face,flags in zip(mesh.polygons,settings):
    original=original_slots[face.material_index]
    key=(face.material_index,tuple(flags.values()))
    if key not in variants:
        material=original.copy()
        p=material.ass_jms
        p.is_bm=p.precise=True
        p.render_only=p.lightmap_only=p.shadow_only=False
        p.sphere_collision_only=flags['sphere']
        p.slip_surface=flags['slip']
        p.two_sided=flags['two_sided']
        special=not original.nwo.shader_path
        if special:
            assert original.name=='+sky'
            p.name_override='+sky'
        else:
            row=bindings['bindings'][original.nwo.shader_path]
            assert sha(row['export_tag'])==row['sha256']
            p.name_override=row['export_prefix']+' '+row['name']
        p.collision_only=not special and not flags['sphere']
        material.update_tag()
        variants[key]=len(mesh.materials)
        mesh.materials.append(material)
    face.material_index=variants[key]
for obj in (world,collision):
    obj.data.update();obj.update_tag(refresh={'DATA'})
bpy.context.view_layer.update()
from io_scene_halo.file_ass import export_ass
from io_scene_halo.file_ass.process_file import process_file
from io_scene_halo.global_functions import global_functions
path=KIT/'data/levels/custom/bc_world_collision_probe/structure/world_collision_source.ass'
result=export_ass.write_file(bpy.context,str(path),7,'halo3',False,True,True,
    True,True,True,global_functions.EdgeSplit(False,False,0.0,False),
    False,1.0,lambda level,message:print(level,message,flush=True))
assert result=={'FINISHED'}
asset=process_file(str(path))
assert len(asset.instances)==70
for obj,mode in ((world,'render'),(collision,'collision')):
    instance=next(i for i in asset.instances if i.name==obj.name)
    obj.data.calc_loop_triangles()
    output=asset.objects[instance.object_index]
    assert len(output.triangles)==len(obj.data.loop_triangles)
    for tri in output.triangles:
        material=asset.materials[tri.material_index]
        flags=next(s.split()[1] for s in material.lighting_info if s.startswith('BM_FLAGS '))
        assert flags[13]=='1'
        if mode=='render':assert flags[3]=='1'
assert sha(source)==inspection['scene_sha256'] and sha(inspection['source'])==bindings['scene_sha256']
report=dict(source=str(source),source_sha256=inspection['scene_sha256'],ass=str(path),ass_sha256=sha(path),
    original_bound_scene_sha256=bindings['scene_sha256'],original_tag_sha256=inspection['original_tag_sha256'],
    replaced_nonvisual_faces=len(remove),preserved_visible_world_faces=len(world.data.polygons),
    original_collision_faces=len(collision.data.polygons),collision_material_variants=len(variants),
    limitation='Diagnostic standard material controls only; no main-map authoring changes or native collision fidelity acceptance.')
(OUT/'world-collision-source-probe.json').write_text(json.dumps(report,indent=2)+'\n')
print('WORLD_SOURCE_COLLISION_EXPORTED',json.dumps(report),flush=True)
