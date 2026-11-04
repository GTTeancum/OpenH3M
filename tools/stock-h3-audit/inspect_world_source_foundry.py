"""Import complete original world collision through unchanged Foundry.

Save an isolated diagnostic scene; never alter the authoritative authoring file.
"""
import hashlib
import collections
import json
from pathlib import Path
import runpy
import bpy
import bmesh

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/hrek'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
source=Path(bpy.data.filepath)
bindings=json.loads((OUT/'h3-material-bindings.json').read_text())
native=json.loads((OUT/'original-world-collision.json').read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert source==Path(bindings['scene']) and sha(source)==bindings['scene_sha256']
assert sha(native['source'])==native['sha256']
scene=bpy.context.scene
project=bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name=project.project_name=scene.nwo.scene_project
project.project_path=str(KIT)
project.tags_directory=str(KIT/'tags')
project.data_directory=str(KIT/'data')
project.corinth=False
scene.nwo.lights_export_on_save=False
scene.nwo.prefabs_export_on_save=False
assert scene.nwo.scale=='max' and scene.nwo.forward_direction=='x'
from io_scene_foundry.managed_blam.scenario_structure_bsp import ScenarioStructureBspTag
from io_scene_foundry.managed_blam.connected_geometry import BSPCollisionMaterial,StructureCollision
world=scene.objects['cex_beaver_creek_structure']
for obj in list(scene.objects):
    if obj!=world and not (obj.type=='MESH' and obj.nwo.mesh_type.endswith('_portal')):
        bpy.data.objects.remove(obj,do_unlink=True)
with ScenarioStructureBspTag(path=native['source'],tag_must_exist=True) as bsp:
    materials=[BSPCollisionMaterial(e) for e in bsp.tag.SelectField('Block:collision materials').Elements]
    block=bsp.tag.SelectField('Struct:resource interface[0]/Block:raw_resources[0]/Struct:raw_items[0]/Block:large collision bsp')
    assert block.Elements.Count==1
    collision=StructureCollision(block.Elements[0],'bc_original_world_collision_diagnostic',materials)
    obj=collision.to_object()
    scene.collection.objects.link(obj)
mesh=obj.data
print('WORLD_SOURCE_FOUNDRY_COUNTS',len(mesh.vertices),len(mesh.polygons),flush=True)
raw=native['collision']['large collision bsp'][0]
assert len(mesh.vertices)==28302
# Foundry's set_two_sided folds coincident front/back polygons into a single
# two-sided face. Verify every original polygon, not just the resulting count.
original=collections.defaultdict(list)
for index,surface in enumerate(raw['surfaces']):
    first=edge_index=surface['first edge']
    vertices=[]
    while True:
        edge=raw['edges'][edge_index]
        if edge['left surface']==index:
            vertices.append(edge['start vertex']);edge_index=edge['forward edge']
        else:
            assert edge['right surface']==index
            vertices.append(edge['end vertex']);edge_index=edge['reverse edge']
        if edge_index==first:break
        assert len(vertices)<1000
    original[frozenset(vertices)].append(index)
assert len(original)==46032 and collections.Counter(map(len,original.values()))=={1:45886,2:146}
actual={frozenset(p.vertices):p for p in mesh.polygons}
assert len(actual)==len(mesh.polygons)==len(original) and actual.keys()==original.keys()
two_sided=[p for p in mesh.nwo.face_props if p.type=='face_sides']
assert len(two_sided)==1
two_sided_attr=mesh.attributes[two_sided[0].attribute_name]
for key,indices in original.items():
    if len(indices)==2:
        assert all(raw['surfaces'][i]['flags']['two sided'] and raw['surfaces'][i]['flags']['invisible'] for i in indices)
        assert raw['surfaces'][indices[0]]['material']==raw['surfaces'][indices[1]]['material']
        assert two_sided_attr.data[actual[key].index].value
assert max(abs(v.co[a]-raw['vertices'][v.index]['point'][a]*100) for v in mesh.vertices for a in range(3))<.05
bm=bmesh.new();bm.from_mesh(mesh)
geometry=dict(vertices=len(bm.verts),faces=len(bm.faces),boundary_edges=sum(e.is_boundary for e in bm.edges),
    nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),zero_area_faces=sum(f.calc_area()<1e-12 for f in bm.faces))
bm.free()
def bounds(mesh):return [[min(v.co[a] for v in mesh.vertices),max(v.co[a] for v in mesh.vertices)] for a in range(3)]
report=dict(source=str(source),source_sha256=bindings['scene_sha256'],original_tag=native['source'],
    original_tag_sha256=native['sha256'],geometry=geometry,original_surface_sets_verified=46178,
    source_front_back_pairs_folded_to_two_sided=146,collision_bounds=bounds(mesh),world_bounds=bounds(world.data),
    materials=[dict(name=m.name,shader=m.nwo.shader_path) for m in mesh.materials],
    face_properties=[dict(type=p.type,attribute=p.attribute_name,count=p.face_count) for p in mesh.nwo.face_props],
    limitation='Original collision imported through unchanged Foundry. Diagnostic only; native H3 compilation and fidelity remain unverified.')
assert sha(source)==bindings['scene_sha256'] and sha(native['source'])==native['sha256']
bpy.context.preferences.filepaths.save_version=0
destination=OUT/'world-source-collision-inspection.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
report.update(scene=str(destination),scene_sha256=sha(destination))
(OUT/'world-source-collision-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
print('WORLD_SOURCE_COLLISION_IMPORTED',json.dumps({k:v for k,v in report.items() if k not in ('materials','face_properties')}),flush=True)
