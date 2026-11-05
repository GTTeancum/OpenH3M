"""Use Blender's standard decimator on the nonvisual world collision only."""
import bpy, hashlib, json, runpy, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'work/stock-h3-audit'
for name in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/name))
source=Path(bpy.data.filepath)
assert source==OUT/'battle-canyon-h3-materials.blend'
collision=bpy.data.objects['bc_world_collision']
before=len(collision.data.polygons)
# Standard planar dissolve preserves vertex positions. Mark portal neighborhoods
# and sky closure as seams so their source faces cannot be dissolved.
boxes=[]
for ob in bpy.context.scene.objects:
    if ob.type=='MESH' and any(m and m.ass_jms.name_override=='+portal' for m in ob.data.materials):
        points=[ob.matrix_world@v.co for v in ob.data.vertices]
        boxes.append(([min(v[k] for v in points)-10 for k in range(3)],
                      [max(v[k] for v in points)+10 for k in range(3)]))
positions=[collision.matrix_world@v.co for v in collision.data.vertices]
protected=set()
for face in collision.data.polygons:
    ps=[positions[i] for i in face.vertices]
    lo=[min(v[k] for v in ps) for k in range(3)];hi=[max(v[k] for v in ps) for k in range(3)]
    if collision.data.materials[face.material_index].ass_jms.name_override=='+sky' or any(all(lo[k]<=b[k] and hi[k]>=a[k] for k in range(3)) for a,b in boxes):
        protected.update(tuple(sorted(e)) for e in face.edge_keys)
for edge in collision.data.edges:
    if tuple(sorted(edge.vertices)) in protected:edge.use_seam=True
print('COLLISION_PORTALS_PROTECTED',len(boxes),len(protected),before,flush=True)
bpy.context.view_layer.objects.active=collision
modifier=collision.modifiers.new('Native 360 collision budget','DECIMATE')
modifier.decimate_type='DISSOLVE';modifier.angle_limit=math.radians(30);modifier.delimit={'MATERIAL','SEAM'}
bpy.ops.object.modifier_apply(modifier=modifier.name)
collision.data.calc_loop_triangles()
print('COLLISION_DECIMATED',len(collision.data.polygons),'triangles',len(collision.data.loop_triangles),flush=True)
bpy.context.view_layer.update()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'battle-canyon-360-planar-draft.blend'),check_existing=False)
from io_scene_halo.file_ass import export_ass
from io_scene_halo.global_functions import global_functions
ass=ROOT/'work/editing-kits/h3ek/data/levels/custom/battle_canyon_fresh/structure/battle_canyon.ass'
result=export_ass.write_file(bpy.context,str(ass),7,'halo3',False,True,True,True,True,True,
    global_functions.EdgeSplit(False,False,0.0,False),False,1.,lambda level,message:print(level,message,flush=True))
assert result=={'FINISHED'}
report=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    original_collision_faces=before,draft_collision_faces=len(collision.data.polygons),draft_collision_triangles=len(collision.data.loop_triangles),
    method='Standard planar dissolve, 30 degrees; portal neighborhoods/sky closure protected by seam delimiters',
    visible_meshes_edited=False,ass=str(ass),ass_sha256=hashlib.sha256(ass.read_bytes()).hexdigest(),
    limitation='Collision simplification requires traversal review. Original authored scene retained.')
(OUT/'360-collision-draft.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('COLLISION_DRAFT',json.dumps(report),flush=True)
