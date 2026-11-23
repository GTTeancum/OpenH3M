"""Import a Reach tag (render_model/model) into Blender with unchanged Foundry; save the scene + JSON report.

Run through blender_env.run (hidden desktop). Args: <tag relative to asset-kit-hrek\\tags> <out.blend> [--animations]
Mirrors tools/stock-h3-audit/import_original_props.py, pointed at the repo-local Reach project.
"""
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy, blender_env
blender_env.enable('io_scene_foundry')
KIT = blender_env.ROOT / '.local/asset-kit-hrek'
args = sys.argv[sys.argv.index('--') + 1:]
source = KIT / 'tags' / args[0]; destination = Path(args[1]); animated = '--animations' in args
before = hashlib.sha256(source.read_bytes()).hexdigest()
prefs = bpy.context.preferences.addons['io_scene_foundry'].preferences
project = prefs.projects.add(); project.name = project.project_name = 'Asset library Reach'
project.project_path = str(KIT); project.tags_directory = str(KIT / 'tags'); project.data_directory = str(KIT / 'data'); project.corinth = False
scene = bpy.context.scene; scene.nwo.scene_project = project.name
scene.nwo_export.show_output = False; scene.nwo.lights_export_on_save = False; scene.nwo.prefabs_export_on_save = False
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
status = bpy.ops.nwo.foundry_import(filepath=str(source), build_blender_materials=False,
    tag_import_lights=False, tag_collision=True, tag_physics=True, tag_markers=True,
    tag_animation=animated, graph_import_animations=animated, setup_as_asset=False)
assert status == {'FINISHED'}, status
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
objs = []
for o in scene.objects:
    d = dict(name=o.name, type=o.type, parent=o.parent.name if o.parent else None, parent_bone=o.parent_bone,
             loc=[round(x, 4) for x in o.matrix_world.translation])
    if o.type == 'MESH':
        d.update(mesh_type=o.data.nwo.mesh_type, verts=len(o.data.vertices), faces=len(o.data.polygons),
                 mats=[m.nwo.shader_path if m else None for m in o.data.materials], groups=[g.name for g in o.vertex_groups])
    if o.type == 'ARMATURE':
        d['bones'] = [dict(name=b.name, parent=b.parent.name if b.parent else None,
                           matrix=[list(r) for r in b.matrix_local]) for b in o.data.bones]
    objs.append(d)
report = dict(source=str(source), sha256=before, scene=str(destination), objects=objs,
              actions=[dict(name=a.name, frames=list(a.frame_range)) for a in bpy.data.actions],
              scale=scene.nwo.scale, forward=scene.nwo.forward_direction)
destination.with_suffix('.json').write_text(json.dumps(report, indent=1))
print('FOUNDRY_IMPORTED', source.name, len(objs), 'objects', flush=True)
