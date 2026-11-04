"""Read saved stock bindings and native exporter flags; do not author lighting."""
import hashlib
import json
from pathlib import Path
import runpy
import sys
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
for helper in ('check_foundry.py', 'check_h3_exporter.py'):
    runpy.run_path(str(ROOT / 'tools/stock-h3-audit' / helper))
from io_scene_halo.file_ass.process_scene import get_material_strings

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

source = OUT / 'battle-canyon-h3-materials.blend'
assert Path(bpy.data.filepath) == source
before = sha(source)
bindings = json.loads((OUT / 'h3-material-bindings.json').read_text())
assert before == bindings['scene_sha256']
stock = json.loads((OUT / 'stock-material-bindings.json').read_text())
path = r'shaders\invalid.shader'
binding = bindings['bindings'][path]
assert sha(Path(binding['authored'])) == sha(Path(binding['export_tag'])) == stock[path]['target_sha256']
expected = {'box003': ('sphere_collision_only', 6, 5),
            'emissive_sun': ('lightmap_only', 32, 12)}
rows = []
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    for index, material in enumerate(obj.data.materials):
        faces = [p.index for p in obj.data.polygons if p.material_index == index]
        if not faces or material.nwo.shader_path != path:
            continue
        assert obj.name in expected, obj.name
        mode, count, bit = expected[obj.name]
        assert len(faces) == count and getattr(material.ass_jms, mode)
        assert material.ass_jms.name_override == binding['name']
        strings = get_material_strings(material, 7)
        flags = next(s.split()[1] for s in strings if s.startswith('BM_FLAGS '))
        assert flags[bit] == '1'
        other_bit = 12 if bit == 5 else 5
        assert flags[other_bit] == '0'
        rows.append(dict(object=obj.name, faces=len(faces), mode=mode,
                         material=material.name, native_exporter_strings=strings))
assert {r['object'] for r in rows} == set(expected)
ass_checked = None
if '--ass' in sys.argv:
    from io_scene_halo.file_ass.process_file import process_file
    from io_scene_halo.global_functions.mesh_processing import append_material_symbols
    exported = json.loads((OUT / 'h3-bound-ass-inspection-report.json').read_text())
    assert exported['source_sha256'] == before
    ass_path = Path(exported['ass'])
    assert sha(ass_path) == exported['ass_sha256']
    asset = process_file(str(ass_path))
    for row in rows:
        material = bpy.data.materials[row['material']]
        name = append_material_symbols(material, 'halo3', True)
        obj = bpy.data.objects[row['object']]
        instance_name = obj.ass_jms.name_override or obj.name
        instances = [i for i in asset.instances if i.name == instance_name]
        assert len(instances) == 1
        triangles = asset.objects[instances[0].object_index].triangles
        assert len(triangles) == sum(len(p.vertices)-2 for p in obj.data.polygons)
        # Both variants share a shader name. Check the actual object's triangle
        # references, not every same-name material in the global table.
        for index in {t.material_index for t in triangles}:
            exported_material = asset.materials[index]
            assert exported_material.name == name
            assert exported_material.lighting_info == row['native_exporter_strings']
    ass_checked = dict(path=str(ass_path), sha256=exported['ass_sha256'])

# Capture only active lighting-property values. Other RNA defaults are unrelated
# to that face selection and must never be treated as authored source settings.
fields = {
    'emissive': ('material_lighting_emissive_power', 'light_intensity',
        'light_intensity_value', 'material_lighting_emissive_color',
        'material_lighting_emissive_focus', 'material_lighting_emissive_per_unit',
        'material_lighting_emissive_quality', 'material_lighting_attenuation_falloff',
        'material_lighting_attenuation_cutoff', 'material_lighting_use_shader_gel',
        'material_lighting_bounce_ratio'),
    'lightmap_resolution_scale': ('lightmap_resolution_scale',),
    'lightmap_chart_group': ('lightmap_chart_group',),
    'lightmap_type': ('lightmap_type',),
}
metadata = []
for mesh in sorted({o.data for o in bpy.context.scene.objects if o.type == 'MESH'}, key=lambda m:m.name):
    for prop in mesh.nwo.face_props:
        if prop.type not in fields:
            continue
        attribute = mesh.attributes[prop.attribute_name]
        assert attribute.domain == 'FACE'
        values = {}
        for name in fields[prop.type]:
            value = getattr(prop, name)
            values[name] = list(value) if getattr(prop.bl_rna.properties[name], 'is_array', False) else value
        metadata.append(dict(mesh=mesh.name, type=prop.type,
            faces=sum(bool(item.value) for item in attribute.data), values=values))
assert sha(source) == before
report = dict(scene_sha256=before, ass_checked=ass_checked, stock_binding=binding, surfaces=rows,
    pending_lighting_metadata=metadata,
    limitation='Saved binding and native flag checks only. Emission units, lightmap resolution semantics and other recorded metadata remain unresolved; no visual or lighting acceptance.')
(OUT / 'nonvisual-material-verification.json').write_text(json.dumps(report, indent=2)+'\n')
print('NONVISUAL_MATERIALS_VERIFIED', len(rows), 'surfaces;', len(metadata), 'pending lighting records', flush=True)
