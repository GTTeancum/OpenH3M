"""Read-only checks before applying the diagnosed world collision split."""
import json
from pathlib import Path
import runpy
import bpy
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
mesh=bpy.data.objects['cex_beaver_creek_structure'].data
removed=set()
for face in mesh.polygons:
    m=mesh.materials[face.material_index]
    if (m.ass_jms.name_override or m.name)=='+sky' or m.ass_jms.collision_only or m.ass_jms.sphere_collision_only:removed.add(face.index)
lighting=json.loads((OUT/'h3-lighting-metadata-authoring.json').read_text())
report=dict(removed_faces=sorted(removed),lighting_assignments_on_removed_faces=[r for r in lighting['assignments'] if r['mesh']==mesh.name and r['face'] in removed],
    lighting_selections_on_removed_faces=[dict(attribute=r['attribute'],type=r['type'],faces=sorted(set(r['faces'])&removed)) for r in lighting['records'] if r['mesh']==mesh.name],
    attributes=[dict(name=a.name,domain=a.domain,type=a.data_type) for a in mesh.attributes],custom_normals=mesh.has_custom_normals)
(OUT/'world-collision-authoring-plan.json').write_text(json.dumps(report,indent=2)+'\n')
print('WORLD_COLLISION_AUTHORING_PLAN',len(removed),'removed,',len(report['lighting_assignments_on_removed_faces']),'lighting assignments removed,',report['lighting_selections_on_removed_faces'],flush=True)
