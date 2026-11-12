"""Author the full imported scene using existing Blender/Halo controls.

No new meshes, binary converter, collision-category substitution or shader
approximation. Unresolved H3 mappings remain explicit in the saved authoring
file and report; this is not a production export or gameplay candidate.
"""
from array import array
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys
import bpy
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
from halo4_blender_context import OUT, setup, sha

source = OUT/'h3-authoring/haven-prefabs-realized.blend'
realization = json.loads((OUT/'haven-prefab-realization.json').read_text())
before = sha(source)
assert before == realization['destination_sha256']
scene = setup(exporter=True,source=source)
from io_scene_foundry import utils

def topology_uv_hash(mesh):
    h=hashlib.sha256()
    for collection,field,width,code in ((mesh.loops,'vertex_index',1,'i'),
        (mesh.polygons,'loop_start',1,'i'),(mesh.polygons,'loop_total',1,'i')):
        values=array(code,[0])*(len(collection)*width)
        collection.foreach_get(field,values);h.update(values.tobytes())
    for layer in mesh.uv_layers:
        values=array('f',[0])*(len(layer.data)*2)
        layer.data.foreach_get('uv',values);h.update(layer.name.encode());h.update(values.tobytes())
    for layer in mesh.color_attributes:
        values=array('f',[0])*(len(layer.data)*4)
        layer.data.foreach_get('color',values);h.update(layer.name.encode());h.update(values.tobytes())
    return h.hexdigest()

meshes = sorted({o.data for o in scene.objects if o.type=='MESH'},key=lambda m:m.name)
objects = sorted([o for o in scene.objects if o.type=='MESH'],key=lambda o:o.name)
original_data = {o.name:o.data for o in objects}
before_hashes = {m.name:topology_uv_hash(m) for m in meshes}
original_bindings = {m.name:[m.materials[p.material_index].nwo.shader_path
    if m.materials and m.materials[p.material_index] else '' for p in m.polygons] for m in meshes}
expected_positions = {o.name:[utils.halo_transforms(o) @ v.co for v in o.data.vertices] for o in objects}
normal_objects = {o.data.name:o for o in objects}
expected_normals = {}
for name,obj in normal_objects.items():
    matrix=utils.halo_transforms(obj).to_3x3().inverted().transposed()
    expected_normals[name]=[(matrix@n.vector).normalized() for n in obj.data.corner_normals]

assert scene.nwo.scale=='blender' and scene.nwo.forward_direction=='y-'
# Keep mesh coordinates and their split-normal encoding untouched. Scaling
# mesh data can change automatic normals on very thin source triangles. The
# existing Foundry transform supplies H3 world units; H3 ASS supports uniform
# instance scale, so author that transform on the objects through Blender.
target_matrices={o:Matrix.Scale(100,4)@utils.halo_transforms(o) for o in scene.objects}
def depth(obj):
    count=0
    while obj.parent:
        count+=1;obj=obj.parent
    return count
for level in sorted({depth(o) for o in target_matrices}):
    for obj,matrix in target_matrices.items():
        if depth(obj)==level:obj.matrix_world=matrix
    bpy.context.view_layer.update()
scene.nwo.scale='max';scene.nwo.forward_direction='x'
bpy.context.view_layer.update()
max_position_error=0.0
for obj in objects:
    expected=expected_positions[obj.name]
    assert len(expected)==len(obj.data.vertices)
    error=max(((obj.matrix_world@v.co/100-p).length for v,p in zip(obj.data.vertices,expected)),default=0)
    extent=max((max(abs(c) for c in p) for p in expected),default=1)
    assert error<=max(0.00002,extent*0.000002),(obj.name,error,extent)
    max_position_error=max(max_position_error,error)
max_normal_error=0.0
normal_errors=[]
for name,obj in normal_objects.items():
    matrix=obj.matrix_world.to_3x3().inverted().transposed()
    error=max((((matrix@n.vector).normalized()-p).length for n,p in zip(obj.data.corner_normals,expected_normals[name])),default=0)
    normal_errors.append(dict(mesh=name,error=error))
    max_normal_error=max(max_normal_error,error)
print('H4_H3_TRANSFORM_ERRORS',json.dumps(dict(position=max_position_error,
    normals=sorted(normal_errors,key=lambda r:r['error'],reverse=True)[:8])),flush=True)
assert max_normal_error<0.0001,max_normal_error

lighting={'single_probe':'>','per_vertex':'?','per_pixel':'!'}
pathfinding={'none':'-','static':'+','cutout':''}
rows=[]
for index,obj in enumerate(objects):
    kind=obj.data.nwo.mesh_type
    is_sky=obj.name=='default:default'
    role='sky' if is_sky else kind.removeprefix('_connected_geometry_mesh_type_')
    collision=obj.nwo.poop_collision_type
    obj['haven_source_name']=obj.name
    obj['haven_source_collision_type']=collision
    obj['haven_authoring_role']=role
    identifier=f'hvn_{index:04}'
    if role in ('default','collision'):
        prefix='%'+pathfinding[obj.nwo.poop_pathfinding]+lighting[obj.nwo.poop_lighting]
        for field,symbol in (('poop_render_only','*'),('poop_does_not_block_aoe','^'),
            ('poop_excluded_from_lightprobe','<'),('poop_decal_spacing','|')):
            if getattr(obj.nwo,field):prefix+=symbol
        obj.ass_jms.name_override=prefix+identifier
        obj['haven_collision_mapping_pending']=collision in ('bullet_collision','play_collision','invisible_wall')
    else:
        assert role in ('sky','structure','portal','boundary_surface'),(obj.name,role)
        obj.ass_jms.name_override=identifier
    # Fixed IDs avoid time-dependent export identity; names remain mapped here.
    obj.ass_jms.unique_id=str(10000+index)
    rows.append(dict(source_object=obj.name,mesh=obj.data.name,role=role,
        export_name=obj.ass_jms.name_override,source_collision_type=collision,
        collision_mapping_pending=bool(obj.get('haven_collision_mapping_pending',False)),
        polygons=len(obj.data.polygons),lighting=obj.nwo.poop_lighting,
        pathfinding=obj.nwo.poop_pathfinding))

material_sources=sorted({m.nwo.shader_path for mesh in meshes for m in mesh.materials if m and m.nwo.shader_path})
bindings={path:dict(export_name=f'havenh4 m{i:03}',target=f'levels/custom/haven_h4/shaders/m{i:03}.shader',
    source_material=path,shader_mapping_pending=True) for i,path in enumerate(material_sources)}
unbound=bpy.data.materials.new('haven_h4_unbound_collision')
unbound.ass_jms.name_override='havenh4 collision_unbound';unbound.ass_jms.is_bm=True
variants={};pending=[];handled=Counter();face_assignments=[]
for mesh in meshes:
    props=[{} for _ in mesh.polygons]
    original_slots=list(mesh.materials)
    role=next(r['role'] for r in rows if r['mesh']==mesh.name)
    if role=='portal':
        material=bpy.data.materials.new('haven_h4_portal_'+mesh.name)
        material.ass_jms.is_bm=True;material.ass_jms.name_override='+portal'
        owner=next(o for o in objects if o.data==mesh)
        material.ass_jms.ai_deafening=owner.nwo.portal_ai_deafening
        material.ass_jms.blocks_sound=owner.nwo.portal_blocks_sounds
        material.ass_jms.portal_door=owner.nwo.portal_is_door
        mesh.materials.clear();mesh.materials.append(material)
        for face in mesh.polygons:face.material_index=0
        continue
    if role=='boundary_surface':
        # Already compiled separately; keep source helper intact here.
        continue
    for prop in mesh.nwo.face_props:
        attr=mesh.attributes[prop.attribute_name]
        assert attr.domain=='FACE'
        selected=[i for i,v in enumerate(attr.data) if v.value]
        settings={}
        if prop.type=='face_mode':
            assert prop.face_mode in ('render_only','collision_only'),prop.face_mode
            settings[prop.face_mode]=True
        elif prop.type=='face_sides':
            assert prop.face_sides_type=='two_sided',prop.face_sides_type
            settings['two_sided']=prop.two_sided
        elif prop.type=='no_shadow':settings['no_shadow']=prop.no_shadow
        elif prop.type=='global_material':settings['source_global_material']=prop.global_material
        elif prop.type=='emissive':
            pending.append(dict(mesh=mesh.name,type=prop.type,attribute=prop.attribute_name,
                faces=selected,reason='Retain source emission settings; native H3 lighting units/semantics not yet verified.'))
            continue
        else:raise AssertionError((mesh.name,prop.type))
        for index in selected:
            for k,v in settings.items():
                assert k not in props[index] or props[index][k]==v
                props[index][k]=v
        handled[prop.type]+=len(selected)
    for face,settings in zip(mesh.polygons,props):
        original=original_slots[face.material_index] if original_slots else None
        source_path=original.nwo.shader_path if original else ''
        key=(original.name if original else '',tuple(sorted(settings.items())))
        if key not in variants:
            variant=(original or unbound).copy()
            variant.name=f'haven_h4_assignment_{len(variants):03}'
            variant.ass_jms.is_bm=True
            if source_path:variant.ass_jms.name_override=bindings[source_path]['export_name']
            for k,v in settings.items():
                if k=='source_global_material':variant['haven_source_global_material']=v
                else:setattr(variant.ass_jms,k,v)
            variants[key]=variant
        variant=variants[key]
        slot=mesh.materials.find(variant.name)
        if slot<0:slot=len(mesh.materials);mesh.materials.append(variant)
        face.material_index=slot
    face_assignments.append(dict(mesh=mesh.name,role=role,
        global_material_overrides=sorted({p['source_global_material'] for p in props if 'source_global_material' in p})))

for mesh in meshes:
    assert topology_uv_hash(mesh)==before_hashes[mesh.name],mesh.name
    role=next(r['role'] for r in rows if r['mesh']==mesh.name)
    if role not in ('portal','boundary_surface'):
        assert original_bindings[mesh.name]==[mesh.materials[p.material_index].nwo.shader_path for p in mesh.polygons],mesh.name
assert all(o.data==original_data[o.name] for o in objects)
assert sha(source)==before
scene.ass.game_title='halo3';scene.ass.ass_version='7';scene.ass.edge_split=False
scene.ass.clean_normalize_weights=False;scene.ass.scale_enum='0'
destination=OUT/'h3-authoring/haven-h3-authoring.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
report=dict(status='authored_with_explicit_pending_mappings',source=str(source),source_sha256=before,
    source_unchanged=True,destination=str(destination),destination_sha256=sha(destination),
    scene_objects=len(scene.objects),mesh_objects=len(objects),unique_meshes=len(meshes),
    roles=dict(Counter(r['role'] for r in rows)),collision_categories=dict(Counter(r['source_collision_type'] for r in rows)),
    maximum_world_position_error=max_position_error,maximum_world_normal_error=max_normal_error,
    coordinate_authoring='Unmodified Foundry halo_transforms; native Blender object matrices in ASS units. Mesh coordinates/normals not rescaled.',
    topology_uv_and_vertex_colors_preserved=True,source_material_assignments_preserved=True,
    shared_mesh_links_preserved=True,face_property_assignments=dict(handled),
    material_variants=len(variants),material_bindings=bindings,objects=rows,face_assignments=face_assignments,
    pending_face_properties=pending,geometry_attribute_hashes=before_hashes,
    pending=['Native collision-category behavior','Shader feature mapping and physical material bindings',
        'Source emission and light mapping','Separate sky render-model authoring','Full ASS export and native compile',
        'Stock H3 gameplay/audio and Forge authoring','Native appearance and runtime checks'])
(OUT/'haven-h3-authoring-scene.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('H4_H3_FULL_SCENE_AUTHORED',json.dumps({k:report[k] for k in ('mesh_objects','unique_meshes','roles',
    'maximum_world_position_error','maximum_world_normal_error','face_property_assignments','material_variants')}),flush=True)
