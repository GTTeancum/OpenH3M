"""Native Blender WIP of the sky; Foundry source shading, not MCC rendering."""
import hashlib
import json
from pathlib import Path
import runpy
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit'
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_foundry.py'))
source=Path(bpy.data.filepath);before=hashlib.sha256(source.read_bytes()).hexdigest()
assert source==OUT/'battle-canyon-original-sky.blend'
prefs=bpy.context.preferences.addons['io_scene_foundry'].preferences
project=prefs.projects.add();project.name=project.project_name='Original Reach sky preview'
kit=ROOT/'work/editing-kits/hrek'
project.project_path=str(kit);project.tags_directory=str(kit/'tags');project.data_directory=str(kit/'data');project.corinth=False
scene=bpy.context.scene;scene.nwo.scene_project=project.name
scene.nwo_export.show_output=False;scene.nwo.lights_export_on_save=False;scene.nwo.prefabs_export_on_save=False
from io_scene_foundry.tools.shader_reader import ShaderTag
materials=sorted({m for o in scene.objects if o.type=='MESH' for m in o.data.materials},key=lambda m:m.name)
for mat in materials:
    with ShaderTag(path=mat.nwo.shader_path,tag_must_exist=True) as shader:shader.to_nodes(mat,False)
    print('SKY_PREVIEW_MATERIAL',mat.nwo.shader_path,flush=True)
camera=bpy.data.objects.new('Sky WIP camera',bpy.data.cameras.new('Sky WIP camera'))
scene.collection.objects.link(camera);scene.camera=camera
camera.location=(0,0,0);camera.data.lens=20;camera.data.clip_start=.01;camera.data.clip_end=100000
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
scene.world=bpy.data.worlds.new('Sky preview world');scene.world.use_nodes=True
scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=0
images=[]
for name,direction in [('east',(1,0,.2)),('west',(-1,0,.2))]:
    camera.rotation_euler=Vector(direction).to_track_quat('-Z','Y').to_euler()
    image=OUT/('wip/original-sky-'+name+'.png');scene.render.filepath=str(image)
    bpy.ops.render.render(write_still=True);images.append(str(image))
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(OUT/'sky-wip.json').write_text(json.dumps(dict(source=str(source),sha256=before,images=images,materials=len(materials),
    limitation='Actual original sky geometry and artwork rendered by Blender using unchanged Foundry preview shaders. This is not the H3 renderer or baked map lighting; H3 appearance awaits MCC review.'),indent=2)+'\n')
