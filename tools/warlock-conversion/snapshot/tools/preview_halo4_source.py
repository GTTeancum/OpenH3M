"""One native Blender source preview; not an H3 or game-rendering acceptance."""
from pathlib import Path
import json
import sys
import bpy
import bmesh
from mathutils import Matrix, Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from halo4_blender_context import ROOT, OUT, SOURCE, setup, sha

before = sha(SOURCE)
scene = setup()
from io_scene_foundry import utils
hidden = []
filtered = {}
for obj in scene.objects:
    if obj.type != 'MESH':
        continue
    kind = obj.data.nwo.mesh_type
    if kind.endswith(('_collision','_portal','_boundary_surface','_structure')):
        obj.hide_render = True
        hidden.append(obj.name)
    else:
        excluded = set()
        for prop in obj.data.nwo.face_props:
            if prop.type == 'face_mode' and prop.face_mode in ('collision_only','sphere_collision_only','lightmap_only','shadow_only'):
                attr = obj.data.attributes[prop.attribute_name]
                excluded.update(i for i,v in enumerate(attr.data) if v.value)
        if excluded:
            obj.data = obj.data.copy()
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.faces.ensure_lookup_table()
            bmesh.ops.delete(bm, geom=[bm.faces[i] for i in excluded], context='FACES')
            bm.to_mesh(obj.data)
            bm.free()
            filtered[obj.name] = len(excluded)
# Hidden source prefab collision helpers must also be hidden inside their collections.
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.data.nwo.mesh_type.endswith(('_collision','_portal','_boundary_surface')):
        obj.hide_render = True

inventory = json.loads((OUT / 'haven-scenario-authoring-inventory.json').read_text())
main = inventory['scenarios']['levels/multi/wraparound/wraparound.scenario']
start = main['player starting locations'][0]
# Field-path keys come from the official API; fail rather than choosing another location.
position_key = next(k for k in start if k.endswith(':position'))
position = Vector(start[position_key])
position.z += 1.7 / 3.048  # Preview eye height only; not saved or gameplay authoring.
transform = utils.blender_transform_matrix(Matrix.Identity(4))
camera = bpy.data.objects.new('Source inspection camera', bpy.data.cameras.new('Source inspection camera'))
scene.collection.objects.link(camera)
camera.location = transform @ position
direction = (transform.to_3x3() @ Vector((1,0,0))).normalized()
camera.rotation_euler = direction.to_track_quat('-Z','Y').to_euler()
camera.data.lens = 24
camera.data.clip_start = 0.05
camera.data.clip_end = 50000
scene.camera = camera
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.render.resolution_x = 960
scene.render.resolution_y = 540
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.threads_mode = 'FIXED'
scene.render.threads = 8
scene.view_settings.view_transform = 'AgX'
scene.view_settings.exposure = 0
destination = OUT / 'h3-authoring/haven-source-preview.png'
scene.render.filepath = str(destination)
bpy.ops.render.render(write_still=True)
assert sha(SOURCE) == before
report = dict(source_sha256=before, source_unchanged=True, image=str(destination), image_sha256=sha(destination),
    source_player_start=list(start[position_key]), preview_eye_height_meters=1.7,
    camera_position=list(camera.location), camera_direction=list(direction), lens_mm=24,
    hidden_nonrender_objects=hidden, filtered_nonrender_faces=filtered,
    engine='Cycles CPU, 16 samples, denoised, AgX exposure 0',
    limitation='Source authoring preview with imported materials/lights; no H4 post effects, lightmaps, scenario objects, gameplay, H3 or final appearance acceptance.')
(OUT / 'haven-source-preview.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print('H4_SOURCE_PREVIEW', str(destination), flush=True)
