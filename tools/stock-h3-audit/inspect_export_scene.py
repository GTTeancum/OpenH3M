"""Read saved Foundry scene metadata before configuring the H3 exporter.

No geometry edits, tag writes, export, or changes to either upstream add-on.
"""
import collections
import json
import runpy
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_foundry.py'))
runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_h3_exporter.py'))

def stored(group):
    result = {}
    for key in group.keys():
        value = getattr(group, key, None)
        if isinstance(value, (str, bool, int, float)) or value is None:
            result[key] = value
        elif isinstance(value, bpy.types.ID):
            result[key] = value.name
        else:
            result[key] = str(value)
    return result

objects = []
for obj in bpy.context.scene.objects:
    row = dict(name=obj.name, type=obj.type, collections=[c.name for c in obj.users_collection],
               nwo=stored(obj.nwo), mesh_type=obj.nwo.mesh_type, hidden=obj.hide_get(), hide_render=obj.hide_render,
               scale=list(obj.scale), location=list(obj.location))
    if obj.type == 'MESH':
        row.update(mesh=obj.data.name, polygons=len(obj.data.polygons),
                   uv_layers=[u.name for u in obj.data.uv_layers],
                   attributes=[dict(name=a.name, type=a.data_type, domain=a.domain) for a in obj.data.attributes],
                   materials=[m.name if m else None for m in obj.data.materials],
                   mesh_nwo=stored(obj.data.nwo), face_properties=[stored(p) for p in obj.data.nwo.face_props])
    objects.append(row)
report = dict(scene=stored(bpy.context.scene.nwo),
              scene_scale=bpy.context.scene.nwo.scale,
              forward_direction=bpy.context.scene.nwo.forward_direction,
              mesh_types=dict(collections.Counter(o.nwo.mesh_type for o in bpy.context.scene.objects if o.type == 'MESH')),
              materials=[dict(name=m.name, nwo=stored(m.nwo)) for m in bpy.data.materials], objects=objects)
(OUT / 'export-scene-inspection.json').write_text(json.dumps(report, indent=2) + '\n')
print('EXPORT_SCENE_INSPECTION', json.dumps({k:v for k,v in report.items() if k not in ('objects','materials')}), flush=True)
