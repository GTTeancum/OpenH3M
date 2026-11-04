"""Append original Reach render-BSP collision to an isolated render-only mesh.

Called by the diagnostic exporter with target/definition_index globals. Standard
Foundry import, Blender material controls and Join only; no source scene save.
"""
import collections
import hashlib
import json
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/hrek'
source=json.loads((OUT/('original-instance-collision-'+str(definition_index)+'.json')).read_text())
bindings=json.loads((OUT/'h3-material-bindings.json').read_text())
assert hashlib.sha256(Path(source['source']).read_bytes()).hexdigest()==source['sha256']
assert len(source['render_bsp'])==1
raw=source['render_bsp'][0]
assert not any(s['flags']['invalid'] or s['flags']['invisible'] or s['flags']['two sided'] or s['flags']['slip'] or s['flags']['breakable'] or s['flags']['climbable'] for s in raw['surfaces'])
project=bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name=project.project_name=bpy.context.scene.nwo.scene_project
project.project_path=str(KIT);project.tags_directory=str(KIT/'tags');project.data_directory=str(KIT/'data');project.corinth=False
from io_scene_foundry.managed_blam.scenario_structure_bsp import ScenarioStructureBspTag
from io_scene_foundry.managed_blam.connected_geometry import BSPCollisionMaterial,InstanceCollision
with ScenarioStructureBspTag(path=source['source'],tag_must_exist=True) as bsp:
    materials=[BSPCollisionMaterial(e) for e in bsp.tag.SelectField('Block:collision materials').Elements]
    definitions=bsp.tag.SelectField('Struct:resource interface[0]/Block:raw_resources[0]/Struct:raw_items[0]/Block:instanced geometries definitions')
    block=definitions.Elements[definition_index].SelectField('Block:render bsp')
    assert block.Elements.Count==1
    collision=InstanceCollision(block.Elements[0],'original_render_bsp_collision_probe',materials).to_object()
bpy.context.scene.collection.objects.link(collision)
mesh=collision.data
assert len(mesh.vertices)==len(raw['vertices']) and len(mesh.polygons)==len(raw['surfaces'])
assert max(abs(v.co[a]-raw['vertices'][v.index]['point'][a]*100) for v in mesh.vertices for a in range(3))<.0001
for poly,surface in zip(mesh.polygons,raw['surfaces']):
    first=edge=surface['first edge'];vertices=[]
    for _ in range(len(raw['edges'])+1):
        e=raw['edges'][edge]
        if e['left surface']==poly.index:vertices.append(e['start vertex']);edge=e['forward edge']
        else:
            assert e['right surface']==poly.index
            vertices.append(e['end vertex']);edge=e['reverse edge']
        if edge==first:break
    else:raise AssertionError('Original render-BSP loop did not close')
    assert list(poly.vertices)==vertices
for index,original in enumerate(list(mesh.materials)):
    mat=original.copy();mat.name='bc_original_render_bsp_'+original.name
    p=mat.ass_jms;p.is_bm=True;p.precise=True;p.render_only=False;p.collision_only=True
    if mat.nwo.shader_path:
        b=bindings['bindings'][mat.nwo.shader_path]
        p.name_override=b['export_prefix']+' '+b['name']
    else:
        assert original.name.split('.')[0]=='+seamsealer'
        p.name_override='+seamsealer'
    mat.update_tag();mesh.materials[index]=mat
# Tool still calculates tangent space across this parent mesh. Give only the
# newly imported, nonvisual faces a standard Blender UV layout; joining then
# preserves every original visible UV. No new artwork or texture is generated.
collision_vertices_before_uv=[v.co.copy() for v in mesh.vertices]
collision_faces_before_uv=[list(p.vertices) for p in mesh.polygons]
assert len(mesh.uv_layers)==0
mesh.uv_layers.new(name=target.data.uv_layers[0].name)
bpy.ops.object.select_all(action='DESELECT')
collision.select_set(True);bpy.context.view_layer.objects.active=collision
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(island_margin=0.02)
bpy.ops.object.mode_set(mode='OBJECT')
assert [v.co for v in mesh.vertices]==collision_vertices_before_uv
assert [list(p.vertices) for p in mesh.polygons]==collision_faces_before_uv
before_vertices=[v.co.copy() for v in target.data.vertices]
before_faces=[list(p.vertices) for p in target.data.polygons]
before_normals=[n.vector.copy() for n in target.data.corner_normals]
before_uvs={layer.name:[v.uv.copy() for v in layer.data] for layer in target.data.uv_layers}
collision.matrix_world=target.matrix_world.copy()
original_collision_faces=[list(p.vertices) for p in mesh.polygons]
original_collision_vertices=[v.co.copy() for v in mesh.vertices]
original_collision_materials=[mesh.materials[p.material_index].ass_jms.name_override for p in mesh.polygons]
bpy.ops.object.select_all(action='DESELECT')
target.select_set(True);collision.select_set(True);bpy.context.view_layer.objects.active=target
bpy.ops.object.join()
joined=target.data
assert [v.co for v in joined.vertices[:len(before_vertices)]]==before_vertices
assert [list(p.vertices) for p in joined.polygons[:len(before_faces)]]==before_faces
for layer,uvs in before_uvs.items():assert [v.uv for v in joined.uv_layers[layer].data[:len(uvs)]]==uvs
normals=[n.vector.copy() for n in joined.corner_normals]
normal_delta=max((n-v).length for n,v in zip(normals,before_normals))
print('JOIN_VISIBLE_NORMAL_DELTA',normal_delta,flush=True)
if normal_delta>1e-6:
    normals[:len(before_normals)]=before_normals
    joined.normals_split_custom_set(normals);joined.update()
assert max((n.vector-v).length for n,v in zip(joined.corner_normals,before_normals))<1e-6
offset=len(before_vertices)
assert [v.co for v in joined.vertices[offset:]]==original_collision_vertices
assert [list(p.vertices) for p in joined.polygons[len(before_faces):]]==[[i+offset for i in face] for face in original_collision_faces]
assert [joined.materials[p.material_index].ass_jms.name_override for p in joined.polygons[len(before_faces):]]==original_collision_materials
assert hashlib.sha256(Path(source['source']).read_bytes()).hexdigest()==source['sha256']
report=dict(definition_index=definition_index,source_tag_sha256=source['sha256'],
    source_collision_vertices=len(original_collision_vertices),source_collision_faces=len(original_collision_faces),
    source_materials=dict(collections.Counter(original_collision_materials)),
    visible_vertices=len(before_vertices),visible_faces=len(before_faces),visible_corners=len(before_normals),
    visible_geometry_normals_uvs_preserved=True,
    nonvisual_collision_uvs='Blender Smart UV Project; no visible UV or source geometry changes',
    limitation='Isolated standard authoring diagnostic; native render-BSP/collision fidelity and MCC remain unverified.')
print('ORIGINAL_RENDER_BSP_APPENDED',json.dumps(report),flush=True)
