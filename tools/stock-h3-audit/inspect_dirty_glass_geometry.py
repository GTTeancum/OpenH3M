"""Read actual dirty-glass assignments and face flags in the saved Blender WIP."""
import hashlib
import json
from pathlib import Path
import runpy
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
for helper in ('check_foundry.py', 'check_h3_exporter.py'):
    runpy.run_path(str(ROOT / 'tools/stock-h3-audit' / helper))
from io_scene_halo.file_ass.process_scene import get_material_strings
source = Path(bpy.data.filepath)
bindings = json.loads((OUT / 'h3-material-bindings.json').read_text())
before = hashlib.sha256(source.read_bytes()).hexdigest()
assert str(source) == bindings['scene'] and before == bindings['scene_sha256']
path = r'levels\shared\shaders\human\glass\glass_window_dirty_subdued.shader_glass'
assert path in bindings['bindings']
rows = []
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    for index, material in enumerate(obj.data.materials):
        if not material or material.nwo.shader_path != path:
            continue
        polygons = [p for p in obj.data.polygons if p.material_index == index]
        if not polygons:
            continue
        assert material.ass_jms.name_override == bindings['bindings'][path]['name']
        points = [obj.matrix_world @ obj.data.vertices[i].co
                  for i in {v for p in polygons for v in p.vertices}]
        flags = {p.identifier:bool(getattr(material.ass_jms,p.identifier))
                 for p in material.ass_jms.bl_rna.properties if p.type == 'BOOLEAN'}
        assert all(flags[name] for name in ('is_bm','two_sided','transparent_2_sided','breakable'))
        rows.append(dict(object=obj.name, mesh=obj.data.name, material=material.name,
            faces=len(polygons), flags=flags, native_exporter_strings=get_material_strings(material,7),
            bounds=[[min(v[i] for v in points), max(v[i] for v in points)] for i in range(3)]))
assert rows and hashlib.sha256(source.read_bytes()).hexdigest() == before
assert {r['object']:r['faces'] for r in rows} == {
    'plane001':2,'plane002.001':2,'glass_plane3':2,'glass_plane1':8}
(OUT / 'dirty-glass-geometry.json').write_text(json.dumps(dict(scene_sha256=before, surfaces=rows,
    limitation='Saved assignment/face flags only; H3 two-sided appearance must be checked in MCC.'),indent=2)+'\n')
for row in rows:
    print('DIRTY_GLASS_GEOMETRY', row['object'], row['faces'],
          {k:v for k,v in row['flags'].items() if v}, row['bounds'], flush=True)
