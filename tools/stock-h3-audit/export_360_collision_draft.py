"""Use Blender's standard decimator on the nonvisual world collision only."""
import bpy, hashlib, json, runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'work/stock-h3-audit'
for name in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/name))
source=Path(bpy.data.filepath)
assert source==OUT/'battle-canyon-h3-materials.blend'
collision=bpy.data.objects['bc_world_collision']
before=len(collision.data.polygons)
# Keep material borders (including sky closure) fixed while simplifying terrain.
adj={v.index:set() for v in collision.data.vertices}
for p in collision.data.polygons:
    for v in p.vertices: adj[v].add(p.material_index)
group=collision.vertex_groups.new(name='360_collision_interior')
interior=[v for v,mats in adj.items() if len(mats)==1 and not any(collision.data.materials[m].ass_jms.name_override=='+sky' for m in mats)]
group.add(interior,1.0,'REPLACE')
print('COLLISION_INTERIOR',len(interior),before,flush=True)
bpy.context.view_layer.objects.active=collision
modifier=collision.modifiers.new('Native 360 collision budget','DECIMATE')
modifier.ratio=.35;modifier.vertex_group=group.name;modifier.vertex_group_factor=10.0
bpy.ops.object.modifier_apply(modifier=modifier.name)
print('COLLISION_DECIMATED',len(collision.data.polygons),flush=True)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'battle-canyon-360-draft.blend'),check_existing=False)
from io_scene_halo.file_ass import export_ass
from io_scene_halo.global_functions import global_functions
ass=ROOT/'work/editing-kits/h3ek/data/levels/custom/battle_canyon_fresh/structure/battle_canyon.ass'
result=export_ass.write_file(bpy.context,str(ass),7,'halo3',False,True,True,True,True,True,
    global_functions.EdgeSplit(False,False,0.0,False),False,1.,lambda level,message:print(level,message,flush=True))
assert result=={'FINISHED'}
report=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    original_collision_faces=before,draft_collision_faces=len(collision.data.polygons),
    visible_meshes_edited=False,ass=str(ass),ass_sha256=hashlib.sha256(ass.read_bytes()).hexdigest(),
    limitation='Collision simplification requires traversal review. Original authored scene retained.')
(OUT/'360-collision-draft.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('COLLISION_DRAFT',json.dumps(report),flush=True)
