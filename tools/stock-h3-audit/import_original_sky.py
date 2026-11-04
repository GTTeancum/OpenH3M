"""Import the original Reach sky using the unchanged Foundry operator."""
import hashlib
import json
from pathlib import Path
import runpy
import bpy

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit'
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_foundry.py'))
kit=ROOT/'work/editing-kits/hrek'
source=kit/'tags/levels/dlc/cex_beaver_creek/beavercreek_sky/beavercreek_sky.render_model'
before=hashlib.sha256(source.read_bytes()).hexdigest()
destination=OUT/'battle-canyon-original-sky.blend'
assert not destination.exists(),'Original sky already imported; inspect saved work'
project=bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name=project.project_name='Original Reach sky'
project.project_path=str(kit);project.tags_directory=str(kit/'tags');project.data_directory=str(kit/'data');project.corinth=False
scene=bpy.context.scene;scene.nwo.scene_project=project.name
scene.nwo_export.show_output=False;scene.nwo.lights_export_on_save=False;scene.nwo.prefabs_export_on_save=False
bpy.context.preferences.filepaths.save_version=0
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
status=bpy.ops.nwo.foundry_import(filepath=str(source),build_blender_materials=False,tag_import_lights=False,setup_as_asset=False)
assert status=={'FINISHED'}
meshes=[o for o in scene.objects if o.type=='MESH'];assert meshes
materials=sorted({m.nwo.shader_path for o in meshes for m in o.data.materials if m})
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
report=dict(source=str(source),source_sha256=before,scene=str(destination),scene_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
    meshes=[dict(name=o.name,vertices=len(o.data.vertices),faces=len(o.data.polygons)) for o in meshes],materials=materials,
    limitation='Original sky geometry imported by unchanged Foundry. H3 material binding/model compilation/scenario sky reference and lighting remain pending.')
(OUT/'original-sky-import.json').write_text(json.dumps(report,indent=2)+'\n')
print('ORIGINAL_SKY_IMPORTED',len(meshes),'meshes',len(materials),'materials',flush=True)
