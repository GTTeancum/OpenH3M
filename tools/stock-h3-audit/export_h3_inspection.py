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
source = Path(bpy.data.filepath)
assert source in (OUT / 'battle-canyon-h3-authoring.blend', OUT / 'battle-canyon-h3-materials.blend')
bound = source.name == 'battle-canyon-h3-materials.blend'
before = hashlib.sha256(source.read_bytes()).hexdigest()
path = OUT / ('h3-bound-inspection.ass' if bound else 'h3-authoring-inspection.ass')
# The operator's dynamic version enum is initially H2-only in background mode.
# Invoke the exact upstream function called by its execute method instead.
from io_scene_halo.file_ass import export_ass
from io_scene_halo.global_functions import global_functions
if bound:
    from io_scene_halo.global_functions.mesh_processing import append_material_symbols
    bindings=json.loads((OUT/'h3-material-bindings.json').read_text())
    assert before==bindings['scene_sha256']
    assert {m['export_name'] for m in bindings['assigned']} <= {append_material_symbols(m,'halo3',True) for m in bpy.data.materials}
    print('H3_EXPORT_SAVED_BINDINGS_PRESENT',len(bindings['assigned']),flush=True)
bpy.context.view_layer.update()
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
if bound:
    bindings=json.loads((OUT/'h3-material-bindings.json').read_text())
    assert before==bindings['scene_sha256']
    names={m.name for m in asset.materials}
    assert {m['export_name'] for m in bindings['assigned']} <= names
    for binding in bindings['bindings'].values():
        assert hashlib.sha256(Path(binding['authored']).read_bytes()).hexdigest()==binding['sha256']
        assert hashlib.sha256(Path(binding['export_tag']).read_bytes()).hexdigest()==binding['sha256']
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
report = dict(source_sha256=before, ass=str(path), ass_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
              bytes=path.stat().st_size, version=asset.version, materials=len(asset.materials),
              unique_objects=len(asset.objects), instances=len(asset.instances),
              triangles=sum(len(o.triangles) for o in asset.objects),
              expected_object_names_present=True, source_blend_unchanged=True,
              limitation='Exporter/reader checks only. Outstanding items in h3-authoring-scene-report.json remain; not a compiled map or visual validation.')
if bound:report.update(bound_shader_tags=len(bindings['bindings']),pending_material_slots=len(bindings['pending']))
(OUT / ('h3-bound-ass-inspection-report.json' if bound else 'h3-ass-inspection-report.json')).write_text(json.dumps(report, indent=2) + '\n')
print('H3_ASS_INSPECTION', json.dumps(report), flush=True)
