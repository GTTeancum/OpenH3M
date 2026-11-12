"""Export full BSP authoring through unchanged General-101; inspect its ASS.

Shader/collision semantics remain pending. Export is an intermediate source
artifact, not a compiled or visually accepted map.
"""
from collections import Counter
from pathlib import Path
import json
import re
import shutil
import hashlib
from array import array
import sys
import bpy
import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from halo4_blender_context import ROOT, OUT, setup, sha
geometry_probe='--geometry-probe' in sys.argv
probe_instance=sys.argv[sys.argv.index('--probe-instance')+1] if '--probe-instance' in sys.argv else None
assert probe_instance is None or re.fullmatch(r'hvn_\d{4}',probe_instance)
instance_range=None
if '--instance-range' in sys.argv:
    index=sys.argv.index('--instance-range')
    instance_range=tuple(map(int,sys.argv[index+1:index+3]))
    assert len(instance_range)==2 and 0<=instance_range[0]<instance_range[1]<=1062
world_with_instance='--world-with-instance' in sys.argv or probe_instance is not None
world_only='--world-only' in sys.argv or world_with_instance
bake_world='--bake-world' in sys.argv
assert not bake_world or world_only
geometry_probe=geometry_probe or world_only
assert not instance_range or not world_only
geometry_probe=geometry_probe or instance_range is not None
probe_stem=('world_baked' if bake_world else 'world_scaled') if world_only else 'haven'
if world_with_instance:probe_stem='world_with_instance'
if probe_instance:probe_stem='world_with_'+probe_instance
if instance_range:probe_stem='range_%04d_%04d'%instance_range
one_sided_probe='--one-sided-probe' in sys.argv
assert not one_sided_probe or geometry_probe
if one_sided_probe:probe_stem+='_one_sided'
collision_role_probe='--collision-role-probe' in sys.argv
assert not collision_role_probe or geometry_probe
if collision_role_probe:probe_stem+='_collision_role'
link_identical_probe='--link-identical-probe' in sys.argv
assert not link_identical_probe or geometry_probe
if link_identical_probe:probe_stem+='_linked'
join_collision_probe='--join-collision-probe' in sys.argv
assert not join_collision_probe or (geometry_probe and not world_only and not instance_range and not link_identical_probe)
if join_collision_probe:probe_stem+='_joined'
collision_errors_only='--collision-errors-only' in sys.argv
assert not collision_errors_only or join_collision_probe
if collision_errors_only:probe_stem+='_errors'
precise_probe='--precise-probe' in sys.argv
assert not precise_probe or geometry_probe
if precise_probe:probe_stem+='_precise'
error_surface_probe='--error-surface-probe' in sys.argv
assert not error_surface_probe or (join_collision_probe and not precise_probe)
if error_surface_probe:probe_stem+='_surfaces'
opaque_draft='--opaque-draft' in sys.argv
assert not opaque_draft or (error_surface_probe and one_sided_probe and not collision_errors_only)
if opaque_draft:probe_stem+='_opaque_draft'
reflection_draft='--reflection-draft' in sys.argv
assert not reflection_draft or opaque_draft
if reflection_draft:probe_stem+='_reflections'
world_render='--world-render' in sys.argv
assert not world_render or reflection_draft
if world_render:probe_stem+='_worldrender'
if geometry_probe:
    probe_report='haven-geometry-probe-ass.json'
    if world_only or instance_range or link_identical_probe or join_collision_probe:probe_report='haven-'+probe_stem+'-probe-ass.json'
    assert not (OUT/probe_report).exists(),'Preserve the previous probe before an intentional reexport'
source=OUT/'h3-authoring/haven-h3-authoring.blend'
authoring=json.loads((OUT/'haven-h3-authoring-scene.json').read_text())
before=sha(source)
assert before==authoring['destination_sha256']
scene=setup(exporter=True,source=source)
from io_scene_halo.file_ass import export_ass
from io_scene_halo.file_ass.process_file import process_file
from io_scene_halo.global_functions import global_functions,mesh_processing

# A separate unsaved scene selects the BSP without moving/deleting source
# objects. Sky and the already-compiled structure design have separate native
# authoring paths; lights require their own verified unit/feature mapping.
export_scene=bpy.data.scenes.new('Haven H3 BSP export')
copies={}
selected_range=None
if instance_range:
    instance_rows=[r for r in authoring['objects'] if r['role'] in ('default','collision')]
    selected_range={r['source_object'] for r in instance_rows[instance_range[0]:instance_range[1]]}
for row in authoring['objects']:
    if row['role'] in ('sky','boundary_surface'):continue
    if world_only and row['role'] not in ('structure','portal'):
        selected=(row['export_name'].endswith(probe_instance) if probe_instance
            else row['source_object']=='nave_io_56|nave_30|nave_30')
        if not world_with_instance or not selected:continue
    if selected_range is not None and row['role'] in ('default','collision') and row['source_object'] not in selected_range:continue
    original=scene.objects[row['source_object']]
    obj=original.copy();obj.parent=None;obj.matrix_world=original.matrix_world
    export_scene.collection.objects.link(obj)
    copies[row['export_name']]=obj
assert len(copies)==(len(selected_range)+36 if selected_range is not None else
    37 if world_with_instance else 36 if world_only else 1098)
bpy.context.window.scene=export_scene
bpy.context.view_layer.update()
linked_meshes=[]
joined_batches=[]
if join_collision_probe:
    from halo4_join_collision import join_collision
    plan=json.loads((OUT/'haven-collision-join-groups.json').read_text())
    assert plan['source_sha256']==before
    joined_batches=join_collision(copies,authoring,plan,mesh_processing)
    assert len(copies)==1098-plan['proposed_object_reduction']
    print('H4_JOINED_COLLISION',len(joined_batches),'batches',len(copies),'objects',flush=True)
if collision_errors_only:
    failures=json.loads((OUT/'haven-joined-geometry-checkpoint.json').read_text())
    ids={re.search(r'hvn_\d{4}',line).group(0) for line in failures['actual_error_lines'] if 'hvn_' in line}
    roles={r['export_name']:r['role'] for r in authoring['objects']}
    for name,obj in list(copies.items()):
        if roles[name] not in ('structure','portal') and not any(name.endswith(i) for i in ids):
            bpy.data.objects.remove(obj,do_unlink=True)
            del copies[name]
    assert len(copies)==36+len(ids)==44
if link_identical_probe:
    # Exact existing mesh-data sharing only. No welding, simplification, face
    # omission or transform change. Preserve every exported attribute and
    # per-face material binding, with roles kept separate.
    groups={}
    roles={r['export_name']:r['role'] for r in authoring['objects']}
    for name,obj in sorted(copies.items()):
        if roles[name] not in ('default','collision'):continue
        mesh=obj.data
        assert not obj.modifiers,('Modifiers require separate identity audit',name)
        h=hashlib.sha256(roles[name].encode())
        for collection,field,width,code in ((mesh.vertices,'co',3,'f'),
            (mesh.loops,'vertex_index',1,'i'),(mesh.polygons,'loop_start',1,'i'),
            (mesh.polygons,'loop_total',1,'i'),(mesh.corner_normals,'vector',3,'f')):
            values=array(code,[0])*(len(collection)*width)
            collection.foreach_get(field,values);h.update(values.tobytes())
        for layer in mesh.uv_layers:
            values=array('f',[0])*(len(layer.data)*2)
            layer.data.foreach_get('uv',values);h.update(layer.name.encode());h.update(values.tobytes())
        for layer in mesh.color_attributes:
            values=array('f',[0])*(len(layer.data)*4)
            layer.data.foreach_get('color',values)
            h.update((layer.name+layer.domain+layer.data_type).encode());h.update(values.tobytes())
        h.update(str(mesh.attributes.active_color_name).encode())
        for face in mesh.polygons:
            material=mesh.materials[face.material_index]
            h.update(mesh_processing.append_material_symbols(material,'halo3',True).encode()+b'\0')
            h.update(material.nwo.shader_path.encode()+b'\0')
            h.update(str(material.get('haven_source_global_material','')).encode()+b'\0')
        key=h.hexdigest()
        if key in groups and groups[key].data!=mesh:
            owner=groups[key]
            linked_meshes.append(dict(object=name,previous_mesh=mesh.name,shared_with=owner.name,
                shared_mesh=owner.data.name,attribute_sha256=key))
            obj.data=owner.data
        else:groups[key]=obj
    bpy.context.view_layer.update()
    print('H4_EXACT_LINKS',len(linked_meshes),flush=True)
collision_role_meshes=[]
if collision_role_probe:
    # Foundry's existing non-Corinth scenario route converts the collision mesh
    # role to a collision-only instance. General-101 needs the corresponding
    # material control; face overrides alone do not carry this mesh-level role.
    targets={copies[r['export_name']].data for r in authoring['objects']
        if r['role']=='collision' and r['export_name'] in copies}
    for mesh in sorted(targets,key=lambda m:m.name):
        derived=mesh.copy()
        before_modes=Counter()
        for face in mesh.polygons:
            material=mesh.materials[face.material_index]
            before_modes[str((material.ass_jms.render_only,material.ass_jms.collision_only))]+=1
            assert not material.ass_jms.render_only,(mesh.name,face.index,'conflicting collision role/render-only face')
        for slot,material in enumerate(mesh.materials):
            if material:
                copied=material.copy()
                copied.ass_jms.collision_only=True
                copied.update_tag()
                derived.materials[slot]=copied
        for obj in copies.values():
            if obj.data==mesh:obj.data=derived
        collision_role_meshes.append(dict(mesh=mesh.name,polygons=len(mesh.polygons),
            prior_face_modes=dict(before_modes)))
    bpy.context.view_layer.update()
one_sided_meshes=[]
if one_sided_probe:
    # Existing H3 nonmanifold-surface authoring control, diagnostic only.
    # Preserve links between shared meshes and avoid changing world/portals.
    targets={obj.data for name,obj in copies.items() if name.startswith('%')}
    one_sided_materials={}
    for mesh in targets:
        bm=bmesh.new();bm.from_mesh(mesh)
        boundary=sum(e.is_boundary for e in bm.edges)
        nonmanifold=sum(not e.is_manifold for e in bm.edges)
        bm.free()
        if not nonmanifold:continue
        derived=mesh.copy()
        for slot in sorted({face.material_index for face in mesh.polygons}):
            material=mesh.materials[slot]
            if material:
                copied=one_sided_materials.get(material)
                if copied is None:
                    copied=material.copy()
                    copied.ass_jms.transparent_1_sided=True
                    copied.update_tag()
                    one_sided_materials[material]=copied
                derived.materials[slot]=copied
        for obj in copies.values():
            if obj.data==mesh:obj.data=derived
        one_sided_meshes.append(dict(mesh=mesh.name,boundary_edges=boundary,
            nonmanifold_edges=nonmanifold))
    bpy.context.view_layer.update()
world_transform_error=0.0
if bake_world:
    # Compare existing Blender's Apply Transforms on source world/portal
    # helpers only. This probe does not alter any saved authoring mesh.
    expected={name:[obj.matrix_world@v.co for v in obj.data.vertices] for name,obj in copies.items()}
    for obj in copies.values():
        obj.data=obj.data.copy()
        obj.select_set(True)
    bpy.context.view_layer.objects.active=next(iter(copies.values()))
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    for name,obj in copies.items():
        error=max(((obj.matrix_world@v.co-p).length for v,p in zip(obj.data.vertices,expected[name])),default=0)
        assert error<0.0001,(name,error)
        world_transform_error=max(world_transform_error,error)
probe_bindings=[]
if error_surface_probe:
    materials={}
    roles={r['export_name']:r['role'] for r in authoring['objects']}
    failures=json.loads((OUT/'haven-joined-geometry-checkpoint.json').read_text())
    error_ids={re.search(r'hvn_\d{4}',line).group(0) for line in failures['actual_error_lines'] if 'hvn_' in line}
    for name,obj in copies.items():
        if roles[name]=='portal':continue
        if roles[name]!='structure' and not any(name.endswith(i) for i in error_ids):continue
        obj.data=obj.data.copy()
        mesh=obj.data
        selected=[f for f in mesh.polygons if roles[name]!='structure' or f.index in (594,1209)]
        for face in selected:
            original=mesh.materials[face.material_index]
            if original not in materials:
                copied=original.copy();copied.ass_jms.transparent_1_sided=True
                copied.update_tag();materials[original]=copied
            copied=materials[original]
            slot=mesh.materials.find(copied.name)
            if slot<0:slot=len(mesh.materials);mesh.materials.append(copied)
            face.material_index=slot
        mesh.update();obj.update_tag(refresh={'DATA'})
    bpy.context.view_layer.update()
if precise_probe:
    for material in {obj.data.materials[f.material_index] for obj in copies.values() for f in obj.data.polygons}:
        if not (material.ass_jms.name_override or material.name).startswith('+portal'):
            material.ass_jms.precise=True
            material.update_tag()
if geometry_probe:
    # Isolated native compiler diagnostic: preserve all mesh data and existing
    # material flags, changing only shader names to immutable stock grey copies.
    # The source/authoring blend and ordinary export remain unchanged.
    kit=ROOT/'work/editing-kits/h3ek'
    donor=kit/'tags/levels/shared/shaders/simple/grey.shader'
    donor_hash=sha(donor)
    destination=kit/('tags/levels/custom/haven_h4/shaders' if opaque_draft else 'tags/levels/custom/haven_geometry_probe/shaders')
    destination.mkdir(parents=True,exist_ok=True)
    prefix='hvndraft' if opaque_draft else 'hvnprobe'
    source_names={}
    draft_shaders={}
    if opaque_draft:
        draft=json.loads((OUT/'material-authoring/opaque-draft/report.json').read_text())
        assert draft['status']=='native_authoring_readback_pass_draft'
        draft_shaders={r['source']:r for r in draft['materials']}
        if reflection_draft:
            reflections=json.loads((OUT/'material-authoring/reflection-draft/report.json').read_text())
            assert reflections['status']=='native_authoring_readback_pass_draft'
            assert len(reflections['materials'])==35
            draft_shaders.update({r['source']:r for r in reflections['materials']})
        source_names.update({v['export_name']:k.replace('\\','/') for k,v in authoring['material_bindings'].items()})
        inventory=json.loads((OUT/'haven-material-input-audit.json').read_text())['materials']
        for source_path,row in inventory.items():
            assert row['blender_material'] not in source_names
            source_names[row['blender_material']]=source_path
    used=sorted({m for obj in copies.values() for m in obj.data.materials if m},key=lambda m:m.name)
    for index,material in enumerate(used):
        original=material.ass_jms.name_override or material.name
        if original.startswith('+'):continue
        source_path=None
        if opaque_draft:
            source_path=source_names.get(original) or source_names.get(re.sub(r'(\.\d{3})+$','',original))
            assert source_path or original=='havenh4 collision_unbound',(material.name,original)
        mapped=draft_shaders.get(source_path)
        name=Path(mapped['target']).stem if mapped else (f'pending_m{index:03}' if opaque_draft else f'm{index:03}')
        target=destination/(name+'.shader')
        expected_hash=mapped['target_sha256'] if mapped else donor_hash
        if target.exists():assert sha(target)==expected_hash,target
        else:
            assert not mapped
            shutil.copyfile(donor,target)
        material.ass_jms.name_override=prefix+' '+name
        material.update_tag()
        probe_bindings.append(dict(material=material.name,original=original,
            alias=material.ass_jms.name_override,target=str(target),sha256=expected_hash,
            source_material=source_path,opaque_draft_mapped=bool(mapped)))
    collection=kit/'tags/levels/shader_collections.txt'
    relative=str(destination.relative_to(kit/'tags'))
    text=collection.read_text(encoding='utf-8-sig')
    existing=[l.split() for l in text.splitlines() if l.split() and l.split()[0]==prefix]
    assert not existing or existing==[[prefix,relative]],existing
    if not existing:
        with collection.open('a',encoding='utf-8',newline='') as stream:
            stream.write('\n'+prefix+'\t'+relative+'\n')
    assert sha(donor)==donor_hash
    for obj in copies.values():
        obj.data.update()
        obj.update_tag(refresh={'DATA'})
    bpy.context.view_layer.update()
world_render_record=None
if world_render:
    # H3 faux_data_sync rejects an all-instanced render scene. Classify an
    # existing four-triangle, render-only floor mesh as world render geometry.
    # Its original placement, topology and attributes are retained; no helper
    # geometry is added. Carry the instance's no-collision behavior to faces.
    original_name='%!*hvn_0607'
    obj=copies.pop(original_name)
    assert len(obj.data.polygons)==4
    assert {m.nwo.shader_path.replace('\\','/') for m in obj.data.materials if m}=={
        'environments/shared/materials/forerunner/mp_forerunner_floortile_02c.material'}
    obj.data=obj.data.copy()
    for i,material in enumerate(obj.data.materials):
        if material:
            derived=material.copy();derived.ass_jms.is_bm=True
            derived.ass_jms.render_only=True;derived.ass_jms.collision_only=False
            derived.update_tag();obj.data.materials[i]=derived
    name='hvn_0607_world'
    obj.ass_jms.name_override=name;copies[name]=obj
    obj.data.update();bpy.context.view_layer.update()
    world_render_record=dict(source_instance=original_name,export_name=name,
        source_object=obj['haven_source_name'],triangles=4,render_only=True,
        matrix_world=[list(row) for row in obj.matrix_world],
        reason='Official H3 faux_data_sync requires a world render mesh; first all-instanced draft failed with no mesh in the structure.')
export_scene.ass.game_title='halo3';export_scene.ass.ass_version='7'
export_scene.ass.edge_split=False;export_scene.ass.clean_normalize_weights=False
export_scene.ass.scale_enum='0'
messages=[]
def message(level,text):
    messages.append(dict(level=sorted(level),message=text));print(level,text,flush=True)
path=OUT/'h3-authoring/haven-bsp-unbound.ass'
if geometry_probe:
    path=ROOT/'work/editing-kits/h3ek/data/levels/custom/haven_geometry_probe/structure'/(probe_stem+'.ass')
    path.parent.mkdir(parents=True,exist_ok=True)
result=export_ass.write_file(bpy.context,str(path),7,'halo3',False,True,True,
    True,True,True,global_functions.EdgeSplit(False,False,0.0,False),False,1.0,message)
assert result=={'FINISHED'}
assert not any('WARNING' in m['level'] or 'ERROR' in m['level'] for m in messages),messages
print('H4_H3_FULL_ASS_WRITTEN',path.stat().st_size,flush=True)
asset=process_file(str(path))
assert len(asset.instances)==len(copies)+1
assert asset.instances[0].name=='Scene Root'
instances={i.name:i for i in asset.instances[1:]}
assert set(instances)==set(copies)
depsgraph=bpy.context.evaluated_depsgraph_get()
seen=set();triangles=0;corners=0;max_position_error=0.0;max_normal_error=0.0;max_uv_error=0.0
max_matrix_error=0.0;colors_checked=0;alpha=[];zero_normal_fallbacks=0
for name,obj in copies.items():
    inst=instances[name]
    assert inst.parent_id==0 and inst.object_index>=0
    t=inst.local_transform
    matrix=Matrix.Translation(t.translation)@t.rotation.to_matrix().to_4x4()@Matrix.Scale(t.scale,4)
    error=max(abs(matrix[r][c]-obj.matrix_world[r][c]) for r in range(4) for c in range(4))
    assert error<0.0001,(name,error)
    max_matrix_error=max(max_matrix_error,error)
    if inst.object_index in seen:continue
    seen.add(inst.object_index)
    geometry=asset.objects[inst.object_index]
    evaluated=obj.evaluated_get(depsgraph)
    mesh=evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=depsgraph)
    assert geometry.geo_class=='MESH' and len(geometry.triangles)==len(mesh.polygons)
    assert len(geometry.vertices)==len(mesh.loops)
    color=mesh.attributes.active_color
    if color:
        values=[v.color[3] for v in color.data]
        alpha.append(dict(mesh=obj.data.name,domain=color.domain,min=min(values),max=max(values),
            nonidentity=sum(abs(v-1)>0.000001 for v in values)))
    for face,triangle in zip(mesh.polygons,geometry.triangles):
        assert len(face.loop_indices)==3
        material=obj.material_slots[face.material_index].material
        exported=asset.materials[triangle.material_index]
        expected_material=mesh_processing.append_material_symbols(material,'halo3',True)
        assert exported.name==expected_material,(obj.name,face.index,exported.name,expected_material)
        for li,vi in zip(face.loop_indices,(triangle.v0,triangle.v1,triangle.v2)):
            v=geometry.vertices[vi]
            vertex=mesh.vertices[mesh.loops[li].vertex_index]
            error=(v.translation-vertex.co).length;max_position_error=max(max_position_error,error)
            assert error<0.000001,(obj.name,face.index,'position',error)
            normal=mesh.corner_normals[li].vector.normalized()
            if not normal.length:normal=face.normal.normalized();zero_normal_fallbacks+=1
            error=(v.normal-normal).length;max_normal_error=max(max_normal_error,error)
            assert error<0.000001,(obj.name,face.index,'normal',error)
            assert len(v.uv_set)==len(mesh.uv_layers)
            for uv,layer in zip(v.uv_set,mesh.uv_layers):
                error=(Vector(uv[:2])-layer.data[li].uv).length;max_uv_error=max(max_uv_error,error)
                assert error<0.000001,(obj.name,face.index,'uv',error)
            expected=mesh_processing.process_mesh_export_color(mesh,li,vertex.index)
            assert max(abs(v.color[a]-expected[a]) for a in range(3))<0.000001
            colors_checked+=1;corners+=1
        triangles+=1
    evaluated.to_mesh_clear()
assert len(seen)==len(asset.objects)
assert sha(source)==before
report=dict(status='export_geometry_verified_semantics_pending',source=str(source),source_sha256=before,
    source_unchanged=True,ass=str(path),ass_sha256=sha(path),ass_bytes=path.stat().st_size,
    instances=len(copies),unique_meshes=len(seen),materials=len(asset.materials),
    triangles_checked=triangles,corners_checked=corners,rgb_values_checked=colors_checked,
    maximum_local_position_error=max_position_error,maximum_normal_error=max_normal_error,
    maximum_uv_error=max_uv_error,maximum_instance_matrix_error=max_matrix_error,
    exporter_zero_normal_fallbacks=zero_normal_fallbacks,vertex_alpha_inventory=alpha,
    source_vertex_alpha_not_in_ass=any(r['nonidentity'] for r in alpha),messages=messages,
    excluded_separate_assets=['sky render model','structure design','lights pending native H3 authoring'],
    geometry_probe=geometry_probe,opaque_draft=opaque_draft,reflection_draft=reflection_draft,probe_shader_bindings=probe_bindings,
    world_render=world_render_record,
    world_only=world_only,baked_world_transforms=bake_world,world_transform_error=world_transform_error,
    world_with_one_instance=world_with_instance,
    instance_range=instance_range,
    one_sided_probe=one_sided_probe,one_sided_meshes=one_sided_meshes,
    collision_role_probe=collision_role_probe,collision_role_meshes=collision_role_meshes,
    link_identical_probe=link_identical_probe,linked_meshes=linked_meshes,
    join_collision_probe=join_collision_probe,joined_batches=joined_batches,
    collision_errors_only=collision_errors_only,precise_probe=precise_probe,
    error_surface_probe=error_surface_probe,
    error_surface_world_faces=[594,1209] if error_surface_probe else [],
    error_surface_instances=sorted(error_ids) if error_surface_probe else [],
    limitation=('Opaque draft bindings; deferred materials retain neutral placeholders. ' if opaque_draft else 'Neutral-material compiler diagnostic only. ' if geometry_probe else '')+
        'Actual ASS geometry, normals, UVs, RGB, material names and transforms verified. '
        'Shader tags, collision categories, alpha semantics, lighting and native full-map compilation remain pending.')
report_name='haven-geometry-probe-ass.json' if geometry_probe else 'haven-h3-ass-verification.json'
if world_only:report_name='haven-'+probe_stem+'-probe-ass.json'
if instance_range or link_identical_probe or join_collision_probe:report_name='haven-'+probe_stem+'-probe-ass.json'
(OUT/report_name).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('H4_H3_FULL_ASS_VERIFIED',json.dumps({k:v for k,v in report.items() if k not in
    ('vertex_alpha_inventory','messages','probe_shader_bindings','one_sided_meshes','collision_role_meshes','linked_meshes','joined_batches')}),flush=True)
