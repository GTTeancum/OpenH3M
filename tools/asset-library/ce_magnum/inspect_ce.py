"""Import the CE pistol gbxmodels with the unchanged General-101 toolset; report contents."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy, blender_env
blender_env.enable('io_scene_halo')
from io_scene_halo.file_tag import import_tag
ROOT = blender_env.ROOT
SRC = ROOT / 'work/asset-library/_work/source/hceek/tags'
bpy.context.preferences.addons['io_scene_halo'].preferences.halo_1_tag_path = str(SRC) + __import__('os').sep
args = sys.argv[sys.argv.index('--') + 1:]
tag = SRC / args[0]; out = Path(args[1])
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete()
r = import_tag.load_file(bpy.context, str(tag), 'halo1', 0, False, False, False, lambda *a: print('REPORT', a))
print('LOAD', r)
rep = []
for o in bpy.context.scene.objects:
    d = dict(name=o.name, type=o.type, parent=o.parent.name if o.parent else None, parent_bone=o.parent_bone,
             loc=list(o.matrix_world.translation))
    if o.type == 'MESH':
        d.update(verts=len(o.data.vertices), faces=len(o.data.polygons), mats=[m.name if m else None for m in o.data.materials],
                 groups=[g.name for g in o.vertex_groups])
    if o.type == 'ARMATURE':
        d['bones'] = [dict(name=b.name, parent=b.parent.name if b.parent else None, head=list(b.head_local), tail=list(b.tail_local)) for b in o.data.bones]
    rep.append(d)
out.write_text(json.dumps(rep, indent=1))
bpy.ops.wm.save_as_mainfile(filepath=str(out.with_suffix('.blend')))
print('DONE', len(rep))
