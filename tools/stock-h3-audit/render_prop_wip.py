"""Native Blender proof of imported source props, not H3 material acceptance."""
import hashlib
import json
from pathlib import Path
import runpy
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit'
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_foundry.py'))
source=Path(bpy.data.filepath);before=hashlib.sha256(source.read_bytes()).hexdigest()
name=source.stem.removeprefix('original-prop-')
original=json.loads((OUT/('original-prop-'+name+'.json')).read_text())
assert before==original['scene_sha256']
prefs=bpy.context.preferences.addons['io_scene_foundry'].preferences
project=prefs.projects.add();project.name=project.project_name='Original prop preview'
kit=ROOT/'work/editing-kits/hrek'
project.project_path=str(kit);project.tags_directory=str(kit/'tags');project.data_directory=str(kit/'data');project.corinth=False
scene=bpy.context.scene;scene.nwo.scene_project=project.name
scene.nwo_export.show_output=False;scene.nwo.lights_export_on_save=False;scene.nwo.prefabs_export_on_save=False
from io_scene_foundry.tools.shader_reader import ShaderTag, ShaderDecalTag
meshes=[o for o in scene.objects if o.type=='MESH' and o.data.nwo.mesh_type=='_connected_geometry_mesh_type_default']
assert meshes
for obj in scene.objects:
    obj.hide_render=obj.type=='MESH' and obj not in meshes
for collection in bpy.data.collections:collection.hide_render=False
for material in {m for o in meshes for m in o.data.materials if m and m.nwo.shader_path}:
    # The UI wrapper also arranges the node editor; call the same native reader
    # directly in background Blender, as in the existing source previews.
    reader=ShaderDecalTag if material.nwo.shader_path.endswith('.shader_decal') else ShaderTag
    with reader(path=material.nwo.shader_path,tag_must_exist=True) as shader:
        shader.to_nodes(material,False)
    print('PROP_PREVIEW_MATERIAL',material.nwo.shader_path,flush=True)
points=[o.matrix_world@Vector(p) for o in meshes for p in o.bound_box]
low=Vector(tuple(min(p[i] for p in points) for i in range(3)))
high=Vector(tuple(max(p[i] for p in points) for i in range(3)))
center=(low+high)/2;extent=(high-low).length
camera=bpy.data.objects.new('Source prop camera',bpy.data.cameras.new('Source prop camera'))
scene.collection.objects.link(camera);scene.camera=camera
camera.location=center+Vector((.55,-1,.45)).normalized()*extent*2
camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=extent*1.15
camera.data.clip_start=extent/10000;camera.data.clip_end=extent*10
sun=bpy.data.objects.new('Preview sun',bpy.data.lights.new('Preview sun','SUN'))
scene.collection.objects.link(sun);sun.rotation_euler=camera.rotation_euler;sun.data.energy=2;sun.data.angle=.3
scene.world=bpy.data.worlds.new('Source prop preview world');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.08,.08,.08,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
image=OUT/('wip/original-prop-'+name+'.png');scene.render.filepath=str(image)
bpy.ops.render.render(write_still=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(OUT/('original-prop-'+name+'-wip.json')).write_text(json.dumps(dict(source=str(source),source_sha256=before,
    image=str(image),image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
    limitation='Actual source geometry and artwork in Blender with unchanged Foundry preview shaders and neutral preview lights. Not H3 shaders, baked level lighting, animation or MCC acceptance.'),indent=2)+'\n')
print('PROP_WIP_RENDERED',image,flush=True)
