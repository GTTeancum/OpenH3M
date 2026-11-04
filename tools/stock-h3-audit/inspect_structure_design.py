"""Inspect original Reach water/other design geometry through unmodified Foundry."""
import hashlib
import json
from pathlib import Path
import runpy
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_foundry.py'))
kit = ROOT / 'work/editing-kits/hrek'
source = kit / 'tags/levels/dlc/cex_beaver_creek/cex_beaver_creek_design.structure_design'
before = hashlib.sha256(source.read_bytes()).hexdigest()
project = bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name = project.project_name = 'Original Reach design inspection'
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
status = bpy.ops.nwo.foundry_import(filepath=str(source), build_blender_materials=False, setup_as_asset=False)
assert status == {'FINISHED'}, status
rows = []
for obj in bpy.context.scene.objects:
    row = dict(name=obj.name, type=obj.type)
    if obj.type == 'MESH':
        row.update(mesh_type=obj.nwo.mesh_type, vertices=len(obj.data.vertices), faces=len(obj.data.polygons))
        row['water_properties'] = {p.identifier: getattr(obj.nwo, p.identifier) for p in obj.nwo.bl_rna.properties
                                   if p.identifier.startswith('water_') and p.type in ('FLOAT', 'INT', 'STRING', 'BOOLEAN', 'ENUM') and not getattr(p, 'is_array', False)}
    rows.append(row)
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
bpy.context.preferences.filepaths.save_version = 0
output = OUT / 'reach-structure-design-inspection.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output))
report = dict(source=str(source), source_sha256=before, scene=str(output), scene_sha256=hashlib.sha256(output.read_bytes()).hexdigest(), objects=rows,
              limitation='Original source inspection only; no geometry merged into H3 authoring and no H3 physical-water behavior validated.')
(OUT / 'reach-structure-design-inspection.json').write_text(json.dumps(report, indent=2) + '\n')
print('SOURCE_STRUCTURE_DESIGN_INSPECTED', json.dumps(rows), flush=True)
