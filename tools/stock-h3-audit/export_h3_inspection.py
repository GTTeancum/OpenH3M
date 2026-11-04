"""Exercise the unmodified H3 ASS exporter and reader on the full WIP scene.

An inspection artifact only: unresolved authoring items are not waived.
No custom serializer, geometry repair, map compilation or installation.
"""
import hashlib
import json
from pathlib import Path
import runpy
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_foundry.py'))
runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_h3_exporter.py'))
source = OUT / 'battle-canyon-h3-authoring.blend'
assert Path(bpy.data.filepath) == source
before = hashlib.sha256(source.read_bytes()).hexdigest()
path = OUT / 'h3-authoring-inspection.ass'
# The operator's dynamic version enum is initially H2-only in background mode.
# Invoke the exact upstream function called by its execute method instead.
from io_scene_halo.file_ass import export_ass
from io_scene_halo.global_functions import global_functions
result = export_ass.write_file(bpy.context, str(path), 7, 'halo3', False, True, True,
    True, True, True, global_functions.EdgeSplit(False, False, 0.0, False),
    False, 1.0, lambda level, message: print(level, message, flush=True))
assert result == {'FINISHED'}, result
assert path.is_file() and path.stat().st_size > 0
from io_scene_halo.file_ass.process_file import process_file
asset = process_file(str(path))
assert asset.version == 7
assert len(asset.instances) == len(bpy.context.scene.objects) + 1
expected_names = {o.ass_jms.name_override or o.name for o in bpy.context.scene.objects}
assert expected_names <= {i.name for i in asset.instances}
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
report = dict(source_sha256=before, ass=str(path), ass_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
              bytes=path.stat().st_size, version=asset.version, materials=len(asset.materials),
              unique_objects=len(asset.objects), instances=len(asset.instances),
              triangles=sum(len(o.triangles) for o in asset.objects),
              expected_object_names_present=True, source_blend_unchanged=True,
              limitation='Exporter/reader checks only. Outstanding items in h3-authoring-scene-report.json remain; not a compiled map or visual validation.')
(OUT / 'h3-ass-inspection-report.json').write_text(json.dumps(report, indent=2) + '\n')
print('H3_ASS_INSPECTION', json.dumps(report), flush=True)
