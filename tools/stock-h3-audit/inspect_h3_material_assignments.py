"""Inspect actual Blender face assignments before native H3 material naming."""
import collections
import hashlib
import json
from pathlib import Path
import runpy
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_foundry.py'))
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_h3_exporter.py'))
source=OUT/'battle-canyon-h3-authoring.blend'
assert Path(bpy.data.filepath)==source
before=hashlib.sha256(source.read_bytes()).hexdigest()
usage=collections.defaultdict(collections.Counter)
for obj in bpy.context.scene.objects:
    if obj.type!='MESH':continue
    for polygon in obj.data.polygons:
        material=obj.data.materials[polygon.material_index] if polygon.material_index<len(obj.data.materials) else None
        usage[material.name if material else '<unassigned>'][obj.name]+=1
rows=[]
for name,objects in sorted(usage.items()):
    material=bpy.data.materials.get(name)
    rows.append(dict(material=name,source_shader=material.nwo.shader_path if material else None,
                     export_name=(material.ass_jms.name_override or material.name) if material else None,
                     faces=sum(objects.values()),objects=dict(objects)))
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(OUT/'h3-material-assignment-inspection.json').write_text(json.dumps(dict(source=str(source),sha256=before,materials=rows),indent=2)+'\n')
print('BLENDER_MATERIAL_ASSIGNMENTS',len(rows),'unassigned',sum(r['faces'] for r in rows if r['material']=='<unassigned>'),flush=True)
