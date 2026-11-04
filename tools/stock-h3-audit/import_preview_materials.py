"""Invoke Foundry's existing material reader on the imported inspection scene."""
import json
import runpy
import traceback
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_foundry.py'))
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'reach-render-preview.blend'))
prefs = bpy.context.preferences.addons['io_scene_foundry'].preferences
project = prefs.projects.add()
project.name = project.project_name = 'Original Reach material inspection'
kit = ROOT / 'work/editing-kits/hrek'
project.project_path = str(kit)
project.tags_directory = str(kit / 'tags')
project.data_directory = str(kit / 'data')
project.corinth = False
bpy.context.scene.nwo.scene_project = project.name
bpy.context.scene.nwo_export.show_output = False
bpy.context.scene.nwo.lights_export_on_save = False
bpy.context.scene.nwo.prefabs_export_on_save = False
from io_scene_foundry.tools import shader_reader
readers = {'.shader': shader_reader.ShaderTag, '.shader_terrain': shader_reader.ShaderTerrainTag,
           '.shader_foliage': shader_reader.ShaderFoliageTag, '.shader_glass': shader_reader.ShaderGlassTag}
report = {'imported': [], 'skipped': [], 'errors': [],
          'scope': 'Original Reach preview materials only, not H3 shader assignment.'}
for mat in list(bpy.data.materials):
    path = mat.nwo.shader_path
    if not mat.users or not path:
        continue
    if path.endswith('.shader_water'):
        report['skipped'].append(dict(tag=path, reason='Upstream reader uses generic Basic Water fallback; no substitute applied.'))
        continue
    print('READ_SOURCE_MATERIAL', path, flush=True)
    try:
        # Invoke the same upstream reader directly; node-editor layout needs a UI.
        with readers[Path(path).suffix](path=path) as shader:
            shader.to_nodes(mat, False)
        report['imported'].append(path)
    except Exception as exc:
        report['errors'].append(dict(tag=path, error=str(exc)))
        print('MATERIAL_IMPORT_ERROR', path, str(exc), flush=True)
        traceback.print_exc()
        if '--diagnose' in sys.argv:
            raise
    if '--diagnose' in sys.argv:
        break
    (OUT / 'preview-material-report.json').write_text(json.dumps(report, indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'reach-textured-preview.blend'))
print('MATERIAL_INSPECTION_COMPLETE', len(report['imported']), len(report['errors']), flush=True)
