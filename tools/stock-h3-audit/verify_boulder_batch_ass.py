"""Compare full exported boulder triangles/controls with clean isolated inputs."""
import collections
import hashlib
import json
from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_h3_exporter.py'))
from io_scene_halo.file_ass.process_file import process_file
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(name):return json.loads((OUT/name).read_text())
authoring=read('h3-boulder-batch-authoring.json')
export=read('h3-bound-ass-inspection-report.json')
saved=read('boulder-batch-bound-verification.json')
assert export['source_sha256']==saved['scene_sha256']
assert sha(export['ass'])==export['ass_sha256']
asset=process_file(export['ass'])
instances={i.name:i for i in asset.instances}
def triangles(asset,instance):
    mesh=asset.objects[instance.object_index];result=collections.Counter()
    for t in mesh.triangles:
        material=asset.materials[t.material_index]
        vertices=[]
        for i in (t.v0,t.v1,t.v2):
            v=mesh.vertices[i]
            vertices.append((tuple(v.translation),tuple(v.normal),tuple(tuple(uv) for uv in v.uv_set),tuple(v.color)))
        oriented=min(tuple(vertices[i:]+vertices[:i]) for i in range(3))
        result[(material.name,tuple(material.lighting_info),oriented)]+=1
    return result
checked=[]
for name in authoring['eligible']:
    probe=read('collision-workflow-precise-render-only-'+name+'-probe.json')
    assert probe['source_sha256']==authoring['diagnostic_scene_sha256']
    assert sha(probe['ass'])==probe['ass_sha256']
    expected=process_file(probe['ass'])
    row=dict(target=name,diagnostic_ass_sha256=probe['ass_sha256'])
    for role,instance_name in (('render',probe['render_instance']),('collision',probe['collision_child'])):
        source=next(i for i in expected.instances if i.name==instance_name)
        original=triangles(expected,source);current=triangles(asset,instances[instance_name])
        assert original==current,(name,role,sum((original-current).values()),sum((current-original).values()))
        row[role+'_triangles']=sum(current.values())
    parent=instances[probe['render_instance']];child=instances[probe['collision_child']]
    assert asset.instances[child.parent_id] is parent
    checked.append(row)
result=dict(scene_sha256=export['source_sha256'],ass_sha256=export['ass_sha256'],
    targets=checked,exact_diagnosed_triangles_and_material_controls=True,
    limitation='Full ASS matches the isolated clean inputs; combined native import and MCC still require verification.')
(OUT/'boulder-batch-ass-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print('BOULDER_BATCH_ASS_VERIFIED',len(checked),'definitions',flush=True)
