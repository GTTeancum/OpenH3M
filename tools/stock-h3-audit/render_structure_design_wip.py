"""Native Blender proof of authored water volumes/boundary; no saved-scene edits."""
import hashlib
import json
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
report=json.loads((OUT/'h3-structure-design-authoring.json').read_text())
verification=json.loads((OUT/'h3-structure-design-verification.json').read_text())
source=Path(bpy.data.filepath)
before=hashlib.sha256(source.read_bytes()).hexdigest()
assert str(source)==report['scene'] and before==report['scene_sha256']==verification['scene_sha256']
scene=bpy.context.scene
for collection in bpy.data.collections:collection.hide_render=False
water=[o for o in scene.objects if o.name.startswith('~water_physics_')]
assert len(water)==28
points=[]
for ob in list(scene.objects):
    if ob.type!='MESH':continue
    ob.hide_render=False
    mesh=ob.data.copy()
    ob.data=mesh
    ob.data.materials.clear()
    selected=ob in water
    points.extend(ob.matrix_world @ v.co for v in mesh.vertices)
    ob.color=(0.02,0.7,0.95,1) if selected else (1.0,0.3,0.03,1)
    wire=ob.modifiers.new('Preview volume edges','WIREFRAME')
    wire.thickness=4.0 if selected else 3.0
    wire.use_replace=True
    if selected:
        cap=mesh.copy()
        bm=bmesh.new()
        bm.from_mesh(cap)
        bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.normal.z<0.9999],context='FACES')
        assert len(bm.faces)==1
        bm.to_mesh(cap)
        bm.free()
        cap_ob=bpy.data.objects.new('Preview top '+ob.name,cap)
        scene.collection.objects.link(cap_ob)
        cap_ob.matrix_world=ob.matrix_world.copy()
        cap_ob.color=(0.02,0.26,0.36,1)
low=Vector(tuple(min(p[a] for p in points) for a in range(3)))
high=Vector(tuple(max(p[a] for p in points) for a in range(3)))
center=(low+high)/2
span=max(high-low)
camera=bpy.data.objects.new('Native design proof camera',bpy.data.cameras.new('Native design proof camera'))
scene.collection.objects.link(camera)
camera.data.type='ORTHO'
camera.data.ortho_scale=span*1.2
camera.data.clip_end=span*10
camera.location=center+Vector((.85,-1,.8)).normalized()*span*2
camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
scene.camera=camera
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO'
scene.display.shading.color_type='OBJECT'
scene.display.shading.show_shadows=False
scene.display.shading.show_cavity=True
scene.display.shading.background_type='WORLD'
scene.world.color=(0.045,0.045,0.045)
scene.render.resolution_x=1600
scene.render.resolution_y=1100
scene.render.resolution_percentage=100
bpy.context.view_layer.update()
camera_points=[camera.matrix_world.inverted() @ p for p in points]
min_x,max_x=min(p.x for p in camera_points),max(p.x for p in camera_points)
min_y,max_y=min(p.y for p in camera_points),max(p.y for p in camera_points)
camera.location+=camera.rotation_euler.to_quaternion() @ Vector(((min_x+max_x)/2,(min_y+max_y)/2,0))
camera.data.ortho_scale=max(max_x-min_x,(max_y-min_y)*scene.render.resolution_x/scene.render.resolution_y)*1.08
scene.render.image_settings.file_format='PNG'
image=OUT/'wip/h3-structure-design-volumes.png'
scene.render.filepath=str(image)
bpy.ops.render.render(write_still=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(OUT/'wip/h3-structure-design-capture-info.json').write_text(json.dumps(dict(
    source_scene=str(source),source_sha256=before,image=str(image),water_volumes=len(water),
    label='Native Blender authoring proof: cyan water prisms and orange soft ceiling; diagnostic colors, not MCC rendering.',
    source_unchanged=True),indent=2)+'\n')
