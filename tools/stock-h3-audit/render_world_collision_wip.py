"""Native Blender close-up of source faces identified by official Tool errors."""
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
source=Path(bpy.data.filepath)
evidence=json.loads((OUT/'world-collision-precise-portals-error-locations.json').read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest()==evidence['source_sha256']
scene=bpy.context.scene
world=bpy.data.objects['cex_beaver_creek_structure']
for obj in list(scene.objects):
    if obj!=world:bpy.data.objects.remove(obj,do_unlink=True)
world.color=(.3,.36,.43,1)
positions=[]
normals=[]
selected_vertices=set()
for index in (13787,13837):
    face=world.data.polygons[index]
    assert len(face.vertices)==3
    points=[world.matrix_world@world.data.vertices[i].co for i in face.vertices]
    normal=(world.matrix_world.to_3x3()@face.normal).normalized()
    normals.append(normal)
    selected_vertices.update(face.vertices)
    positions.extend(points)
    curve=bpy.data.curves.new('Source triangle '+str(index),'CURVE')
    curve.dimensions='3D'
    curve.bevel_depth=.35
    curve.bevel_resolution=2
    line=curve.splines.new('POLY')
    line.points.add(2)
    for p,co in zip(line.points,points):p.co=(*(co+normal*.4),1)
    line.use_cyclic_u=True
    overlay=bpy.data.objects.new(curve.name,curve)
    scene.collection.objects.link(overlay)
    overlay.color=(1,.06,.02,1)
# Display only the actual neighboring source faces so roofs/floors elsewhere
# cannot hide the diagnostic. This cropped mesh is never saved or exported.
world.data=world.data.copy()
bm=bmesh.new()
bm.from_mesh(world.data)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if not any(v.index in selected_vertices for v in f.verts)],context='FACES')
bm.to_mesh(world.data)
bm.free()
center=sum(positions,Vector())/len(positions)
camera=bpy.data.objects.new('Diagnostic camera',bpy.data.cameras.new('Diagnostic camera'))
scene.collection.objects.link(camera)
camera.location=center+sum(normals,Vector()).normalized()*260
camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO'
camera.data.ortho_scale=280
camera.data.clip_start=1
camera.data.clip_end=500
scene.camera=camera
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='FLAT'
scene.display.shading.color_type='OBJECT'
scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH'
scene.display.shading.background_type='WORLD'
scene.world=bpy.data.worlds.new('Diagnostic world')
scene.world.color=(.035,.035,.035)
scene.render.resolution_x=1400
scene.render.resolution_y=1000
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
path=OUT/'wip/h3-world-thin-triangle-diagnostic.png'
path.parent.mkdir(parents=True,exist_ok=True)
scene.render.filepath=str(path)
bpy.ops.render.render(write_still=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==evidence['source_sha256']
(OUT/'world-collision-wip.json').write_text(json.dumps(dict(source_sha256=evidence['source_sha256'],image=str(path),
    image_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),highlighted_source_faces=[13787,13837],
    limitation='Cropped source-face neighborhood in neutral Blender shading with thickened red edge overlays; not final materials, compiled collision, baked lighting or MCC appearance.'),indent=2)+'\n')
print('WORLD_COLLISION_WIP',path,flush=True)
