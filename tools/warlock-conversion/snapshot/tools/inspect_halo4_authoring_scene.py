"""Read the saved source scene's metadata before H3 authoring; no edits saved."""
from collections import Counter
from pathlib import Path
import json
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from halo4_blender_context import ROOT, OUT, SOURCE, setup, sha, stored

before = sha(SOURCE)
scene = setup(exporter=True)
objects = []
for obj in scene.objects:
    row = dict(name=obj.name, type=obj.type, nwo=stored(obj.nwo),
        hidden=obj.hide_get(), hide_render=obj.hide_render, collections=[c.name for c in obj.users_collection],
        matrix_world=[list(r) for r in obj.matrix_world],
        instance_collection=obj.instance_collection.name if obj.instance_collection else None)
    if obj.type == 'MESH':
        row.update(mesh=obj.data.name, mesh_type=obj.data.nwo.mesh_type,
            mesh_nwo=stored(obj.data.nwo), polygons=len(obj.data.polygons),
            uv_layers=[u.name for u in obj.data.uv_layers],
            attributes=[dict(name=a.name,domain=a.domain,data_type=a.data_type) for a in obj.data.attributes],
            materials=[m.name if m else None for m in obj.data.materials],
            face_properties=[stored(p) for p in obj.data.nwo.face_props])
    objects.append(row)
instances = []
for inst in bpy.context.evaluated_depsgraph_get().object_instances:
    if inst.is_instance:
        obj = inst.object.original
        instances.append(dict(parent=inst.parent.original.name if inst.parent else None,
            object=obj.name,type=obj.type,mesh=obj.data.name if obj.type=='MESH' else None,
            mesh_type=obj.data.nwo.mesh_type if obj.type=='MESH' else None,
            matrix_world=[list(r) for r in inst.matrix_world]))
report = dict(source_sha256=before, source_blend_unchanged=sha(SOURCE)==before,
    scene=stored(scene.nwo), scale=scene.nwo.scale, forward=scene.nwo.forward_direction,
    objects=objects, evaluated_collection_instances=instances,
    mesh_types=dict(Counter(o['mesh_type'] for o in objects if o['type']=='MESH')),
    materials=[dict(name=m.name,nwo=stored(m.nwo),users=m.users) for m in bpy.data.materials])
(OUT/'h4-authoring-scene-inspection.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('H4_AUTHORING_INSPECTION',json.dumps(dict(mesh_types=report['mesh_types'],
    collection_instances=len(instances),collection_instance_types=dict(Counter(i['mesh_type'] for i in instances)),
    face_property_types=dict(Counter(p.get('type') for o in objects for p in o.get('face_properties',[]))),
    source_blend_unchanged=report['source_blend_unchanged'])),flush=True)
assert report['source_blend_unchanged']
