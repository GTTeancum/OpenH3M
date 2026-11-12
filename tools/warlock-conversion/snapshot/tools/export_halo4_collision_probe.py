"""Export one real H4 bullet surface under existing H3 material controls.

Diagnostic-only enclosure and neutral stock material. No map/source mesh edits
are saved and no collision-category equivalence is assumed.
"""
from pathlib import Path
import json
import sys
import bpy
import bmesh
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from halo4_blender_context import ROOT, OUT, SOURCE, setup, sha

before = sha(SOURCE)
scene = setup(exporter=True)
from io_scene_foundry import utils
from io_scene_halo.file_ass import export_ass
from io_scene_halo.file_ass.process_file import process_file
from io_scene_halo.global_functions import global_functions
target = scene.objects['nave_io_56|nave_30|nave_30']
assert target.nwo.poop_collision_type == 'bullet_collision'
assert len(target.data.polygons) == 2
source_name = target.name
bm = bmesh.new()
bm.from_mesh(target.data)
topology = dict(vertices=len(bm.verts), faces=len(bm.faces),
    boundary_edges=sum(e.is_boundary for e in bm.edges),
    nonmanifold_edges=sum(not e.is_manifold for e in bm.edges))
bm.free()
expected = [utils.halo_transforms(target) @ v.co for v in target.data.vertices]
for obj in list(scene.objects):
    if obj != target:
        bpy.data.objects.remove(obj, do_unlink=True)
rotation = utils.rotation_diff_from_forward(scene.nwo.forward_direction, 'x')
utils.transform_scene(bpy.context,1/0.03048,rotation,scene.nwo.forward_direction,'x',actions=[])
scene.nwo.scale = 'max'
scene.nwo.forward_direction = 'x'
bpy.context.view_layer.update()
assert all((target.matrix_world @ vertex.co / 100 - point).length < 0.00002 for vertex,point in zip(target.data.vertices,expected))
target.ass_jms.name_override = '%bullet_surface'
material = bpy.data.materials.new('H3 diagnostic neutral')
material.ass_jms.name_override = 'simple grey'
material.ass_jms.is_bm = True
material.ass_jms.precise = True
target.data.materials.clear()
target.data.materials.append(material)
for face in target.data.polygons:
    face.material_index = 0

# This fixture exists only for the isolated compiler test, never for Haven.
points = [target.matrix_world @ v.co for v in target.data.vertices]
low = Vector(tuple(min(p[a] for p in points)-200 for a in range(3)))
high = Vector(tuple(max(p[a] for p in points)+200 for a in range(3)))
bpy.ops.mesh.primitive_cube_add(size=2, location=(low+high)/2)
enclosure = bpy.context.object
enclosure.name = 'Diagnostic enclosure'
enclosure.scale = (high-low)/2
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bm = bmesh.new()
bm.from_mesh(enclosure.data)
bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
bm.to_mesh(enclosure.data)
bm.free()
sky = bpy.data.materials.new('+sky')
sky.ass_jms.name_override = '+sky'
enclosure.data.materials.append(sky)
scene.ass.game_title = 'halo3'
scene.ass.ass_version = '7'
scene.ass.edge_split = False
scene.ass.clean_normalize_weights = False
scene.ass.scale_enum = '0'
variants = []
for name, transparent, sphere in [('ordinary',False,False),('one_sided',True,False),('sphere_only',True,True)]:
    material.ass_jms.transparent_1_sided = transparent
    material.ass_jms.sphere_collision_only = sphere
    material.update_tag()
    target.data.update()
    target.update_tag(refresh={'DATA'})
    bpy.context.view_layer.update()
    path = ROOT/'work/editing-kits/h3ek/data/levels/custom/haven_collision_probe/structure'/f'{name}.ass'
    path.parent.mkdir(parents=True,exist_ok=True)
    result = export_ass.write_file(bpy.context,str(path),7,'halo3',False,True,True,
        True,True,True,global_functions.EdgeSplit(False,False,0.0,False),False,1.0,
        lambda level,message:print(level,message,flush=True))
    assert result == {'FINISHED'}
    asset = process_file(str(path))
    exported_material = next(m for m in asset.materials if m.name == 'simple grey')
    flags = next(s.split()[1] for s in exported_material.lighting_info if s.startswith('BM_FLAGS '))
    assert flags[1] == str(int(transparent)) and flags[5] == str(int(sphere)) and flags[13] == '1'
    assert len(asset.instances) == 3 and sum(len(o.triangles) for o in asset.objects) == 14
    variants.append(dict(name=name,ass=str(path),ass_sha256=sha(path),material_flags=flags))
assert sha(SOURCE) == before
report = dict(source=str(SOURCE),source_sha256=before,source_unchanged=True,
    source_object=source_name,source_collision_type='bullet_collision',topology=topology,
    variants=variants,geometry_preserved=True,
    limitation='Compiler diagnostic only; a neutral material and enclosing box are test fixtures. No full-map authoring or gameplay equivalence.')
(OUT/'haven-h3-collision-probe.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('H4_COLLISION_PROBE_EXPORTED',json.dumps(report),flush=True)
