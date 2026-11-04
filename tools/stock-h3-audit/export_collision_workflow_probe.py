"""Isolate a failing source instance using the unmodified Blender ASS exporter.

No mesh repair, tag writer or saved source scene modification. The diagnostic
retains the actual render mesh and its authored collision child.
"""
import hashlib
import json
from pathlib import Path
import runpy
import bpy
import bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
source=Path(bpy.data.filepath)
assert source==OUT/'battle-canyon-h3-materials.blend'
before=hashlib.sha256(source.read_bytes()).hexdigest()
bindings=json.loads((OUT/'h3-material-bindings.json').read_text())
assert before==bindings['scene_sha256']
target=bpy.context.scene.objects['boulder_low035']
children=[c for c in target.children if (c.ass_jms.name_override or c.name).startswith('@')]
assert len(children)==1
keep={target,*children}
geometry=[]
for obj in keep:
    mesh=obj.data
    bm=bmesh.new()
    bm.from_mesh(mesh)
    bm.normal_update()
    geometry.append(dict(name=obj.name,mesh=mesh.name,vertices=len(bm.verts),faces=len(bm.faces),
        boundary_edges=sum(e.is_boundary for e in bm.edges),
        nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),
        inconsistent_winding_edges=sum(e.is_manifold and not e.is_contiguous for e in bm.edges),
        zero_area_faces=sum(f.calc_area()<1e-12 for f in bm.faces),
        max_polygon_plane_deviation=max((abs((v.co-f.verts[0].co).dot(f.normal)) for f in bm.faces for v in f.verts),default=0),
        signed_volume=bm.calc_volume(signed=True),
        local_matrix=[list(row) for row in obj.matrix_basis]))
    bm.free()
for obj in list(bpy.context.scene.objects):
    if obj not in keep:bpy.data.objects.remove(obj,do_unlink=True)
bpy.context.view_layer.update()
# Tool requires world geometry even for an instance diagnostic. This enclosing
# sky box belongs only to this test and is never added to the map authoring file.
points=[o.matrix_world @ v.co for o in keep for v in o.data.vertices]
low=Vector(tuple(min(p[a] for p in points)-200 for a in range(3)))
high=Vector(tuple(max(p[a] for p in points)+200 for a in range(3)))
bpy.ops.mesh.primitive_cube_add(size=2,location=(low+high)/2)
envelope=bpy.context.object
envelope.name='Diagnostic world enclosure'
envelope.scale=(high-low)/2
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bm=bmesh.new()
bm.from_mesh(envelope.data)
bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
bm.to_mesh(envelope.data)
bm.free()
sky=bpy.data.materials.new('Diagnostic +sky')
sky.ass_jms.name_override='+sky'
envelope.data.materials.append(sky)
bpy.context.view_layer.update()
from io_scene_halo.file_ass import export_ass
from io_scene_halo.global_functions import global_functions
from io_scene_halo.file_ass.process_file import process_file
path=KIT/'data/levels/custom/bc_collision_workflow_probe/structure/boulder.ass'
path.parent.mkdir(parents=True,exist_ok=True)
result=export_ass.write_file(bpy.context,str(path),7,'halo3',False,True,True,
    True,True,True,global_functions.EdgeSplit(False,False,0.0,False),
    False,1.0,lambda level,message:print(level,message,flush=True))
assert result=={'FINISHED'}
asset=process_file(str(path))
assert len(asset.instances)==4
parent=next(i for i in asset.instances if i.name==(target.ass_jms.name_override or target.name))
child=next(i for i in asset.instances if i.name.startswith('@'))
# ASS parent_id is an instance-array index, not the separate unique_id field.
assert asset.instances[child.parent_id] is parent
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
report=dict(source=str(source),source_sha256=before,ass=str(path),
    ass_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),geometry=geometry,
    instances=[dict(name=i.name,object_index=i.object_index,unique_id=i.unique_id,parent_id=i.parent_id) for i in asset.instances],
    materials=[m.name for m in asset.materials],
    limitation='Exact isolated instance input plus diagnostic-only enclosing sky box; no geometry repair or native collision acceptance implied.')
(OUT/'collision-workflow-probe.json').write_text(json.dumps(report,indent=2)+'\n')
print('H3_COLLISION_WORKFLOW_PROBE',json.dumps(report),flush=True)
