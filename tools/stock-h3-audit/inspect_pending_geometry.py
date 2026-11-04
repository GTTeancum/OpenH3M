"""Read native Blender water channels and unresolved sky/metadata surfaces."""
import bpy
import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_foundry.py'))
runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_h3_exporter.py'))
source = Path(bpy.data.filepath)
assert source == OUT / 'battle-canyon-h3-authoring.blend'
before = hashlib.sha256(source.read_bytes()).hexdigest()
rows = []
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    mesh = obj.data
    paths = {m.nwo.shader_path for m in mesh.materials if m}
    if not (obj.nwo.mesh_type.endswith('_water_surface') or
            any(p == r'shaders\invalid.shader' or 'beaver_creek_sky_' in p for p in paths)):
        continue
    materials = []
    for index, material in enumerate(mesh.materials):
        used = sum(p.material_index == index for p in mesh.polygons)
        if not material or not used:
            continue
        materials.append(dict(name=material.name, source=material.nwo.shader_path, faces=used,
            flags={p.identifier: getattr(material.ass_jms, p.identifier) for p in material.ass_jms.bl_rna.properties
                   if p.type == 'BOOLEAN' and getattr(material.ass_jms, p.identifier)}))
    face_properties = []
    for prop in mesh.nwo.face_props:
        values = {}
        for p in prop.bl_rna.properties:
            if p.type in ('BOOLEAN', 'STRING', 'ENUM', 'INT', 'FLOAT'):
                value = getattr(prop, p.identifier)
                values[p.identifier] = list(value) if getattr(p, 'is_array', False) else value
        face_properties.append(values)
    channels = []
    for layer in mesh.uv_layers:
        channels.append(dict(name=layer.name, loops=len(layer.data),
            ranges=[[min(v.uv[i] for v in layer.data), max(v.uv[i] for v in layer.data)] for i in range(2)]))
    rows.append(dict(object=obj.name, mesh=mesh.name, mesh_type=obj.nwo.mesh_type,
        vertices=len(mesh.vertices), faces=len(mesh.polygons), materials=materials,
        uv_channels=channels, attributes=[dict(name=a.name, domain=a.domain, type=a.data_type) for a in mesh.attributes],
        face_properties=face_properties))
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
(OUT / 'pending-geometry-inspection.json').write_text(json.dumps(dict(source=str(source), source_sha256=before,
    objects=rows, limitation='Read-only metadata inspection; no geometry or export behavior changed.'), indent=2) + '\n')
for row in rows:
    print('PENDING_GEOMETRY', row['object'], row['mesh_type'], row['faces'],
          'UV_CHANNELS', row['uv_channels'], 'FACE_PROPERTIES', [p['type'] for p in row['face_properties']], flush=True)
