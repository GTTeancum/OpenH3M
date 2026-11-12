"""Inventory compatible native Blender Join groups without editing source data."""
from pathlib import Path
import json
import sys
from collections import defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parent))
from halo4_blender_context import OUT,setup,sha
source=OUT/'h3-authoring/haven-h3-authoring.blend'
before=sha(source)
scene=setup(exporter=True,source=source)
authoring=json.loads((OUT/'haven-h3-authoring-scene.json').read_text())
groups=defaultdict(list)
for row in authoring['objects']:
    if row['role']!='collision':continue
    obj=scene.objects[row['source_object']]
    # Group only exact transforms and matching documented instance controls.
    # Category equivalence is not assumed. Mesh data stays untouched.
    prefix=row['export_name'].split('hvn_')[0]
    key=(tuple(v for line in obj.matrix_world for v in line),
        row['source_collision_type'],prefix)
    groups[key].append(row)
rows=[]
for (matrix,category,prefix),members in groups.items():
    if len(members)<2:continue
    rows.append(dict(category=category,prefix=prefix,matrix=matrix,
        objects=[m['source_object'] for m in members],
        polygons=sum(m['polygons'] for m in members),
        distinct_meshes=len({m['mesh'] for m in members})))
rows.sort(key=lambda r:len(r['objects']),reverse=True)
lookup={r['source_object']:r for r in authoring['objects']}
batches=[]
for group in rows:
    batch=[];count=0
    for name in group['objects']:
        n=lookup[name]['polygons']
        if batch and (len(batch)>=8 or count+n>2048):
            if len(batch)>1:batches.append(dict(objects=batch,polygons=count,category=group['category']))
            batch=[];count=0
        batch.append(name);count+=n
    if len(batch)>1:batches.append(dict(objects=batch,polygons=count,category=group['category']))
assert sha(source)==before
report=dict(source=str(source),source_sha256=before,source_unchanged=True,
    groups=rows,grouped_objects=sum(len(r['objects']) for r in rows),
    proposed_bounded_batches=batches,
    proposed_object_reduction=sum(len(b['objects'])-1 for b in batches),
    limitation='Inventory only. Blender Join, output geometry, native collision and definition counts must be verified before adoption.')
path=OUT/'haven-collision-join-groups.json'
assert not path.exists()
path.write_text(json.dumps(report,indent=2)+'\n')
print('H4_COLLISION_JOIN_GROUPS',json.dumps(dict(groups=len(rows),grouped_objects=report['grouped_objects'],
    largest=[dict(objects=len(r['objects']),polygons=r['polygons'],category=r['category']) for r in rows[:8]])),flush=True)
