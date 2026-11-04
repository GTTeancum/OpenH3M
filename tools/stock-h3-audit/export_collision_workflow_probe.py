"""Isolate a failing source instance using the unmodified Blender ASS exporter.

No mesh repair, tag writer or saved source scene modification. The diagnostic
retains the actual render mesh and its authored collision child.
"""
import hashlib
import json
from pathlib import Path
import runpy
import re
import sys
import bpy
import bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
source=Path(bpy.data.filepath)
precise='--precise' in sys.argv
render_only='--render-only' in sys.argv
authored='--authored' in sys.argv
original_render_bsp='--original-render-bsp' in sys.argv
assert not original_render_bsp or (precise and render_only and not authored)
assert not (authored and (precise or render_only))
variant='-authored' if authored else ('-precise' if precise else '')+('-render-only' if render_only else '')
if original_render_bsp:variant+='-original-render-bsp'
stem='collision-workflow'+variant
ass_name='boulder'+variant.replace('-','_')
target_name=sys.argv[sys.argv.index('--target')+1] if '--target' in sys.argv else 'boulder_low035'
if '--target' in sys.argv:
    assert re.fullmatch(r'[a-zA-Z0-9_]+',target_name) and not authored
    stem+='-'+target_name
    ass_name+='_'+target_name
assert source==OUT/'battle-canyon-h3-materials.blend'
before=hashlib.sha256(source.read_bytes()).hexdigest()
bindings=json.loads((OUT/'h3-material-bindings.json').read_text())
assert before==bindings['scene_sha256']
target=bpy.context.scene.objects[target_name]
if '--target' in sys.argv:
    inventory=json.loads((OUT/'original-proxy-collision-inventory.json').read_text())
    assert hashlib.sha256(Path(inventory['source']).read_bytes()).hexdigest()==inventory['sha256']
    original=next(r for r in inventory['definitions'] if target_name in r['instances'])
    assert original['render_bsp_count']==int(original_render_bsp) and original['imported_physics_proxies']==0
    assert target.data.name=='instance_definition:'+str(original['definition_index'])
    assert not any(getattr(target.data.nwo,f'proxy_physics{i}') for i in range(200))
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
if precise or render_only:
    if render_only:
        for i,material in enumerate(list(target.data.materials)):
            copied=material.copy()
            copied.ass_jms.is_bm=True
            copied.ass_jms.render_only=True
            target.data.materials[i]=copied
    for material in {m for o in keep for m in o.data.materials}:
        if precise:
            material.ass_jms.is_bm=True
            material.ass_jms.precise=True
        material.update_tag()
    for obj in keep:
        obj.data.update()
        obj.update_tag(refresh={'DATA'})
render_bsp_report=None
if original_render_bsp:
    imported=runpy.run_path(str(ROOT/'tools/stock-h3-audit/add_original_render_bsp_probe.py'),init_globals={'target':target,'definition_index':original['definition_index']})
    render_bsp_report=imported['report']
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
path=KIT/'data/levels/custom/bc_collision_workflow_probe/structure'/(ass_name+'.ass')
if original_render_bsp:
    path=KIT/'data/levels/custom'/('bc_render_bsp_probe_'+str(original['definition_index']))/'structure/original_render_bsp.ass'
path.parent.mkdir(parents=True,exist_ok=True)
result=export_ass.write_file(bpy.context,str(path),7,'halo3',False,True,True,
    True,True,True,global_functions.EdgeSplit(False,False,0.0,False),
    False,1.0,lambda level,message:print(level,message,flush=True))
assert result=={'FINISHED'}
asset=process_file(str(path))
if precise:
    for material in asset.materials:
        if material.name=='+sky':continue
        flags=next(s.split()[1] for s in material.lighting_info if s.startswith('BM_FLAGS '))
        assert flags[13]=='1',(material.name,flags)
if render_only:
    assert any(s.startswith('BM_FLAGS ') and s.split()[1][3]=='1' for m in asset.materials for s in m.lighting_info)
if authored:
    flags=[s.split()[1] for m in asset.materials for s in m.lighting_info if s.startswith('BM_FLAGS ')]
    assert len(flags)==3 and all(f[13]=='1' for f in flags)
    assert sum(f[3]=='1' for f in flags)==1
assert len(asset.instances)==4
parent=next(i for i in asset.instances if i.name==(target.ass_jms.name_override or target.name))
child=next(i for i in asset.instances if i.name.startswith('@'))
# ASS parent_id is an instance-array index, not the separate unique_id field.
assert asset.instances[child.parent_id] is parent
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
report=dict(source=str(source),source_sha256=before,ass=str(path),
    target=target_name,render_instance=parent.name,collision_child=next(iter(children)).name,
    diagnostic_precise_flag=precise,
    diagnostic_render_only_flag=render_only,
    saved_authoring_flags_checked=authored,
    original_render_bsp=render_bsp_report,
    ass_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),geometry=geometry,
    instances=[dict(name=i.name,object_index=i.object_index,unique_id=i.unique_id,parent_id=i.parent_id) for i in asset.instances],
    materials=[m.name for m in asset.materials],
    limitation='Exact isolated instance input plus diagnostic-only enclosing sky box; no geometry repair or native collision acceptance implied.')
(OUT/(stem+'-probe.json')).write_text(json.dumps(report,indent=2)+'\n')
print('H3_COLLISION_WORKFLOW_PROBE',json.dumps(report),flush=True)
