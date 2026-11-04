"""Read the c20 author's water example with Blender auto-execution disabled."""
import hashlib
import json
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
source=OUT/'upstream/c20-water-example/water-visual.blend'
assert Path(bpy.data.filepath)==source
before=hashlib.sha256(source.read_bytes()).hexdigest()
rows=[]
for obj in bpy.context.scene.objects:
    if obj.type!='MESH':continue
    channels=[]
    for layer in obj.data.uv_layers:
        values=[list(v.uv) for v in layer.data]
        unique=sorted(set(tuple(v) for v in values))
        channels.append(dict(name=layer.name,ranges=[[min(v[i] for v in values),max(v[i] for v in values)] for i in range(2)],
            unique_count=len(unique),unique_sample=unique[:8],coordinates=values))
    rows.append(dict(object=obj.name,vertices=len(obj.data.vertices),faces=len(obj.data.polygons),
        materials=[m.name if m else None for m in obj.data.materials],channels=channels))
    print('EXAMPLE_MESH',obj.name,len(obj.data.polygons),'CHANNELS',
          [(c['name'],c['ranges'],c['unique_count']) for c in channels],flush=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(OUT/'water-example-inspection.json').write_text(json.dumps(dict(source=str(source),sha256=before,
    meshes=rows,limitation='Author-provided workflow example, not Battle Canyon geometry or game acceptance.'),indent=2)+'\n')
