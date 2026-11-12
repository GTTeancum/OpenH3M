"""Use existing Blender/Foundry/H3 authoring controls for Haven's soft ceiling."""
from pathlib import Path
import json
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from halo4_blender_context import ROOT, OUT, SOURCE, setup, sha

source_hash = sha(SOURCE)
scene = setup(exporter=True)
from io_scene_foundry import utils
from io_scene_halo.file_ass import export_ass
from io_scene_halo.global_functions import global_functions
from io_scene_halo.file_ass.process_file import process_file
original = json.loads((OUT / 'haven-source-design.json').read_text())
ceilings = original['blocks']['soft ceilings block']
assert len(ceilings) == 1 and ceilings[0]['name'] == 'ceiling1'
assert ceilings[0]['type']['name'] == 'acceleration', ceilings[0]['type']
assert not original['blocks']['water instances block']
ceiling = bpy.data.objects['ceiling1']
assert ceiling.data.nwo.boundary_surface_type == 'SOFT_CEILING'
assert len(ceiling.data.polygons) == len(ceilings[0]['soft ceiling triangles']) == 60
for obj in list(scene.objects):
    if obj != ceiling:
        bpy.data.objects.remove(obj, do_unlink=True)
rotation = utils.rotation_diff_from_forward(scene.nwo.forward_direction, 'x')
utils.transform_scene(bpy.context, 1 / 0.03048, rotation, scene.nwo.forward_direction, 'x', actions=[])
scene.nwo.scale = 'max'
scene.nwo.forward_direction = 'x'
bpy.context.view_layer.update()
def difference(a, b):
    return max(abs(x-y) for x,y in zip(a,b))
maximum_error = 0.0
for polygon, triangle in zip(ceiling.data.polygons, ceilings[0]['soft ceiling triangles']):
    assert len(polygon.vertices) == 3
    for index, key in zip(polygon.vertices, ('vertex0','vertex1','vertex2')):
        point = ceiling.matrix_world @ ceiling.data.vertices[index].co / 100
        error = difference(point, triangle[key])
        maximum_error = max(maximum_error, error)
        assert error < 0.00002, (point, triangle[key], error)
material = bpy.data.materials.new('+soft_ceiling:ceiling1')
material.ass_jms.name_override = material.name
ceiling.data.materials.clear()
ceiling.data.materials.append(material)
for polygon in ceiling.data.polygons:
    polygon.material_index = 0
ceiling.data.update()
scene.ass.game_title = 'halo3'
scene.ass.ass_version = '7'
scene.ass.clean_normalize_weights = False
scene.ass.edge_split = False
scene.ass.scale_enum = '0'
destination = OUT / 'h3-authoring/haven-h3-design.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
ass = ROOT / 'work/editing-kits/h3ek/data/levels/custom/haven_h4/structure_design/haven.ass'
ass.parent.mkdir(parents=True, exist_ok=True)
result = export_ass.write_file(bpy.context, str(ass), 7, 'halo3', False, True, True,
    True, True, True, global_functions.EdgeSplit(False,False,0.0,False), False, 1.0,
    lambda level, message: print(level, message, flush=True))
assert result == {'FINISHED'}
asset = process_file(str(ass))
assert sum(len(obj.triangles) for obj in asset.objects) == 60
assert sha(SOURCE) == source_hash
report = dict(status='exported', source_sha256=source_hash,
    source_design_sha256=original['source_sha256'], source_unchanged=True,
    scene=str(destination), scene_sha256=sha(destination), ass=str(ass), ass_sha256=sha(ass),
    soft_ceiling_name='ceiling1', triangles=60, source_triangle_order_and_winding_match=True,
    maximum_vertex_error_world_units=maximum_error,
    limitation='Design-only authoring/export; official compile, scenario linkage and game behavior not yet verified.')
(OUT / 'haven-h3-design-authoring.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('H3_DESIGN_EXPORTED', json.dumps(report), flush=True)
