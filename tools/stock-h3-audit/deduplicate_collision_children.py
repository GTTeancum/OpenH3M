"""Keep one identical collision definition per linked H3 instance mesh."""
import hashlib
import json
from pathlib import Path
import runpy
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
source=Path(bpy.data.filepath)
inspection=json.loads((OUT/'h3-collision-authoring-inspection.json').read_text())
assert str(source)==inspection['source']
assert hashlib.sha256(source.read_bytes()).hexdigest()==inspection['sha256']
project=bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name=project.project_name=bpy.context.scene.nwo.scene_project
project.project_path=str(ROOT/'work/editing-kits/hrek')
project.tags_directory=str(ROOT/'work/editing-kits/hrek/tags')
project.data_directory=str(ROOT/'work/editing-kits/hrek/data')
project.corinth=False
bpy.context.scene.nwo.lights_export_on_save=False
bpy.context.scene.nwo.prefabs_export_on_save=False
removed=[]
retained=[]
for row in inspection['definitions']:
    entries=row['collision_children']
    if not entries:continue
    assert row['collision_children_equivalent']
    children=sorted([bpy.data.objects[e['name']] for e in entries],key=lambda c:c.parent.name)
    first=children[0]
    for child in children:
        assert child.data==first.data and child.matrix_basis==first.matrix_basis and child.matrix_parent_inverse==first.matrix_parent_inverse
        assert child.parent.data.name==row['mesh']
    retained.append(dict(mesh=row['mesh'],child=first.name,instances=row['instances']))
    for child in children[1:]:
        removed.append(child.name)
        bpy.data.objects.remove(child,do_unlink=True)
assert len(removed)==inspection['summary']['redundant_equivalent_children']==71
assert len(retained)==44
assert all(bpy.data.objects[name].data.name==row['mesh'] for row in inspection['definitions'] for name in row['instances'])
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(source))
(OUT/'h3-collision-child-authoring.json').write_text(json.dumps(dict(source=str(source),
    before_sha256=inspection['sha256'],scene_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    retained=retained,removed_redundant_children=removed,
    limitation='Shared collision definitions authored per official H3 workflow. Native reimport and gameplay validation remain pending.'),indent=2)+'\n')
print('H3_COLLISION_CHILDREN_DEDUPLICATED: 71 equivalent children removed; 44 shared definitions retained.',flush=True)
