"""Automate the upstream Foundry import operator for source inspection only."""
import hashlib
import json
import runpy
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_foundry.py'))
kit = ROOT / 'work/editing-kits/hrek'
source = kit / 'tags/levels/dlc/cex_beaver_creek/cex_beaver_creek.scenario_structure_bsp'
before = hashlib.sha256(source.read_bytes()).hexdigest()
prefs = bpy.context.preferences.addons['io_scene_foundry'].preferences
project = prefs.projects.add()
project.name = project.project_name = 'Original Reach source inspection'
project.project_path = str(kit)
project.tags_directory = str(kit / 'tags')
project.data_directory = str(kit / 'data')
project.corinth = False
bpy.context.scene.nwo.scene_project = project.name
bpy.context.scene.nwo_export.show_output = False
bpy.context.scene.nwo.lights_export_on_save = False
bpy.context.scene.nwo.prefabs_export_on_save = False
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
status = bpy.ops.nwo.foundry_import(filepath=str(source), build_blender_materials=False,
    tag_bsp_render_only=False, tag_bsp_import_geometry=True, tag_import_lights=False,
    setup_as_asset=False)
assert status == {'FINISHED'}, status
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
assert meshes, 'No geometry imported'
after = hashlib.sha256(source.read_bytes()).hexdigest()
assert before == after, 'Source BSP changed'
report = dict(source=str(source), sha256=before, mesh_objects=len(meshes),
    polygons=sum(len(o.data.polygons) for o in meshes),
    materials=len(bpy.data.materials),
    limit='Source inspection only. Materials not built; no visual, export or MCC acceptance.')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'reach-source-inspection.blend'))
(OUT / 'geometry-import-report.json').write_text(json.dumps(report, indent=2)+'\n')
print('SOURCE_GEOMETRY_IMPORT', json.dumps(report))
