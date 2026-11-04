"""Author native H3 design controls on Foundry-imported original Reach geometry.

Uses Blender's extrusion and existing ASS exporter; no tag or ASS serializer.
Original fog sheets remain in the separate source inspection pending H3 review.
"""
import hashlib
import json
from pathlib import Path
import runpy
import bpy
import bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
from io_scene_foundry import utils
from io_scene_halo.file_ass import export_ass
from io_scene_halo.global_functions import global_functions
from io_scene_halo.file_ass.process_file import process_file

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
inspection=json.loads((OUT/'reach-structure-design-inspection.json').read_text())
native=json.loads((OUT/'original-structure-design.json').read_text())
assert Path(bpy.data.filepath)==Path(inspection['scene'])
assert sha(bpy.data.filepath)==inspection['scene_sha256']
assert sha(native['source'])==native['sha256']==inspection['source_sha256']
instances=native['blocks']['water instances block']
assert len(instances)==28
flows={tuple(i['flow velocity']) for i in instances}
assert len(flows)==1
flow=Vector(next(iter(flows)))
assert abs(flow.length-1)<1e-6 and flow.z==0
points=[p for i in instances for t in i['water debug triangles block'] for p in t.values()]
bottom=min(p[2] for p in points)
top=max(p[2] for p in points)
assert all(p[2] in (bottom,top) for p in points)
depth=(top-bottom)*100

scene=bpy.context.scene
project=bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name=project.project_name=scene.nwo.scene_project
project.project_path=str(ROOT/'work/editing-kits/hrek')
project.tags_directory=str(ROOT/'work/editing-kits/hrek/tags')
project.data_directory=str(ROOT/'work/editing-kits/hrek/data')
project.corinth=False
scene.nwo.lights_export_on_save=False
scene.nwo.prefabs_export_on_save=False
assert scene.nwo.scale=='blender' and scene.nwo.forward_direction=='y-'
rotation=utils.rotation_diff_from_forward(scene.nwo.forward_direction,'x')
utils.transform_scene(bpy.context,1/0.03048,rotation,scene.nwo.forward_direction,'x',actions=[])
scene.nwo.scale='max'
scene.nwo.forward_direction='x'

water=bpy.data.objects['water_physics']
ceiling=bpy.data.objects['soft_ceiling']
for obj in list(scene.objects):
    if obj not in (water,ceiling):bpy.data.objects.remove(obj,do_unlink=True)
for obj in (water,ceiling):
    obj.data.transform(obj.matrix_world)
    obj.matrix_world.identity()
    obj.data.materials.clear()
assert len(water.data.polygons)==28
assert all(p.normal.z>0.99999 for p in water.data.polygons)
assert all(abs(v.co.z-top*100)<0.001 for v in water.data.vertices)

# Source importer preserved one top triangle per convex source water volume.
# Keep those caps, extrude down by the verified original depth and orient outward.
bm=bmesh.new()
bm.from_mesh(water.data)
extruded=bmesh.ops.extrude_face_region(bm,geom=list(bm.faces),use_keep_orig=True)
new_vertices=[e for e in extruded['geom'] if isinstance(e,bmesh.types.BMVert)]
bmesh.ops.translate(bm,verts=new_vertices,vec=Vector((0,0,-depth)))
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
assert all(e.is_manifold for e in bm.edges)
assert len(bm.verts)==168 and len(bm.faces)==140
bm.to_mesh(water.data)
bm.free()
# H3 Tool makes a convex volume per water object; disconnected pieces in one
# object would become one enclosing hull. Separate the original convex prisms.
bpy.ops.object.select_all(action='DESELECT')
water.select_set(True)
bpy.context.view_layer.objects.active=water
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.separate(type='LOOSE')
bpy.ops.object.mode_set(mode='OBJECT')
waters=sorted([o for o in scene.objects if o.type=='MESH' and o!=ceiling],
              key=lambda o:tuple(sum(v.co[a] for v in o.data.vertices)/len(o.data.vertices) for a in range(3)))
assert len(waters)==28
for index,water in enumerate(waters):
    assert len(water.data.vertices)==6 and len(water.data.polygons)==5
    water.name=f'~water_physics_{index:02d}'
    water.ass_jms.name_override=water.name
    direction=bpy.data.objects.new(f'#water_direction_{index:02d}',None)
    scene.collection.objects.link(direction)
    direction.parent=water
    direction.empty_display_type='ARROWS'
    direction.rotation_mode='QUATERNION'
    direction.rotation_quaternion=Vector((1,0,0)).rotation_difference(flow.normalized())

mat=bpy.data.materials.new('+soft_ceiling:soft_ceiling')
mat.ass_jms.name_override=mat.name
ceiling.data.materials.append(mat)
for polygon in ceiling.data.polygons:polygon.material_index=0
assert len(ceiling.data.polygons)==40

# Compare all authored prism vertices with original native debug geometry.
authored=[tuple(v.co/100) for water in waters for v in water.data.vertices]
expected={tuple(p) for p in points}
assert all(any(max(abs(a-b) for a,b in zip(p,q))<2e-6 for q in expected) for p in authored)
assert all(any(max(abs(a-b) for a,b in zip(p,q))<2e-6 for q in authored) for p in expected)
scene.ass.game_title='halo3'
scene.ass.ass_version='7'
scene.ass.clean_normalize_weights=False
scene.ass.edge_split=False
scene.ass.scale_enum='0'
bpy.context.preferences.filepaths.save_version=0
destination=OUT/'battle-canyon-h3-structure-design.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
ass=ROOT/'work/editing-kits/h3ek/data/levels/custom/battle_canyon_rebuild/structure_design/battle_canyon.ass'
ass.parent.mkdir(parents=True,exist_ok=True)
result=export_ass.write_file(bpy.context,str(ass),7,'halo3',False,True,True,
    True,True,True,global_functions.EdgeSplit(False,False,0.0,False),False,1.0,
    lambda level,message:print(level,message,flush=True))
assert result=={'FINISHED'}
asset=process_file(str(ass))
assert len(asset.instances)==58
assert sum(len(o.triangles) for o in asset.objects)==264
assert sha(native['source'])==native['sha256'] and sha(inspection['scene'])==inspection['scene_sha256']
report=dict(source_sha256=native['sha256'],scene=str(destination),scene_sha256=sha(destination),
    ass=str(ass),ass_sha256=sha(ass),water_prisms=28,water_triangles=224,soft_ceiling_triangles=40,
    source_flow=list(flow),source_depth_world_units=top-bottom,
    authored_vertices_match_original=True,water_groups=[w.name[1:] for w in waters],
    pending=['Two original planar fog sheets need supported stock H3 appearance settings',
             'Native Tool design import and readback', 'MCC physics and appearance acceptance'])
(OUT/'h3-structure-design-authoring.json').write_text(json.dumps(report,indent=2)+'\n')
print('H3_DESIGN_AUTHORED',json.dumps(report),flush=True)
