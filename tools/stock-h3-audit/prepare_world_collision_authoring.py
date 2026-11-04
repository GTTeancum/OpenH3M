"""Apply the diagnosed original-world collision split with Blender controls.

Default is an in-memory dry run. --apply saves only after preservation checks.
"""
from array import array
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import sys
import bpy
import bmesh

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
def read(name):return json.loads((OUT/name).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
source=Path(bpy.data.filepath)
lighting=read('h3-lighting-metadata-authoring.json')
inspection=read('world-source-collision-inspection.json')
proof=read('world-source-collision-saved-verification.json')
native=read('world-collision-source-native.json')
plan=read('world-collision-authoring-plan.json')
assert source==OUT/'battle-canyon-h3-authoring.blend' and sha(source)==lighting['scene_sha256']
assert native['clean_geometry_import'] and native['source_sha256']==inspection['scene_sha256']==proof['scene_sha256']
assert sha(inspection['scene'])==inspection['scene_sha256']
assert sha(inspection['original_tag'])==inspection['original_tag_sha256']
assert not plan['lighting_assignments_on_removed_faces']
assert not (OUT/'h3-world-collision-authoring.json').exists(),'Already applied; verify saved evidence first'
before=sha(source)
project=bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name=project.project_name=bpy.context.scene.nwo.scene_project
project.project_path=str(ROOT/'work/editing-kits/hrek')
project.tags_directory=str(ROOT/'work/editing-kits/hrek/tags')
project.data_directory=str(ROOT/'work/editing-kits/hrek/data')
project.corinth=False
world=bpy.data.objects['cex_beaver_creek_structure'];mesh=world.data
removed=set(plan['removed_faces'])
actual_removed={p.index for p in mesh.polygons if
    (mesh.materials[p.material_index].ass_jms.name_override or mesh.materials[p.material_index].name)=='+sky'
    or mesh.materials[p.material_index].ass_jms.collision_only or mesh.materials[p.material_index].ass_jms.sphere_collision_only}
assert actual_removed==removed and len(removed)==2079
positions=[v.co.copy() for v in mesh.vertices]
corners=[l.vertex_index for l in mesh.loops]
normals=[n.vector.copy() for n in mesh.corner_normals]
uvs={layer.name:[v.uv.copy() for v in layer.data] for layer in mesh.uv_layers}
old_faces=[list(p.loop_indices) for p in mesh.polygons]
old_materials=[p.material_index for p in mesh.polygons]
old_slots=list(mesh.materials)
for name,domain,count in [('bc_world_source_face','FACE',len(mesh.polygons)),('bc_world_source_corner','CORNER',len(mesh.loops))]:
    assert name not in mesh.attributes
    attribute=mesh.attributes.new(name,'INT',domain)
    attribute.data.foreach_set('value',array('i',range(count)))
bm=bmesh.new();bm.from_mesh(mesh);bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm,geom=[bm.faces[i] for i in sorted(removed)],context='FACES')
bm.to_mesh(mesh);bm.free();mesh.update()
face_ids=[v.value for v in mesh.attributes['bc_world_source_face'].data]
corner_ids=[v.value for v in mesh.attributes['bc_world_source_corner'].data]
mapping={old:new for new,old in enumerate(face_ids)}
assert len(mapping)==len(mesh.polygons)==59795 and set(mapping)==set(range(61874))-removed
for face,old in zip(mesh.polygons,face_ids):
    assert [corner_ids[i] for i in face.loop_indices]==old_faces[old]
    assert face.material_index==old_materials[old]
for index,loop in enumerate(mesh.loops):
    assert mesh.vertices[loop.vertex_index].co==positions[corners[corner_ids[index]]]
for layer in mesh.uv_layers:
    assert all(item.uv==uvs[layer.name][corner_ids[i]] for i,item in enumerate(layer.data))
normal_delta=max((n.vector-normals[corner_ids[i]]).length for i,n in enumerate(mesh.corner_normals))
if normal_delta>1e-6:
    mesh.normals_split_custom_set([normals[i] for i in corner_ids])
    mesh.update()
normal_delta=max((n.vector-normals[corner_ids[i]]).length for i,n in enumerate(mesh.corner_normals))
assert normal_delta<1e-4,('Visible normal preservation failed',normal_delta)
overrides=dict(is_bm=True,precise=True,render_only=True,collision_only=False,sphere_collision_only=False,slip_surface=False)
copies={}
for index,original in enumerate(old_slots):
    copied=original.copy();copied.name='bc_world_render_'+original.name
    copied.ass_jms.name_override=original.ass_jms.name_override or original.name
    for field,value in overrides.items():setattr(copied.ass_jms,field,value)
    copied.update_tag();mesh.materials[index]=copied
    copies[original.name]=copied.name
for row in lighting['assignments']:
    bpy.data.materials[row['original_material']].use_fake_user=True
    if row['mesh']==mesh.name:
        row['source_face_before_world_split']=row['face']
        row['face']=mapping[row['face']]
        row['material']=copies[row['material']]
        row['world_geometry_flags']=overrides
for row in lighting['records']:
    if row['mesh']==mesh.name:
        assert not (set(row['faces'])&removed)
        row['source_faces_before_world_split']=row['faces']
        row['faces']=[mapping[i] for i in row['faces']]
        assert row['faces']==[i for i,v in enumerate(mesh.attributes[row['attribute']].data) if v.value]

with bpy.data.libraries.load(inspection['scene'],link=False) as (available,loaded):
    assert 'bc_original_world_collision_diagnostic' in available.objects
    loaded.objects=['bc_original_world_collision_diagnostic']
collision=loaded.objects[0]
bpy.context.scene.collection.objects.link(collision)
collision.name='bc_world_collision'
collision.ass_jms.name_override=collision.name
cm=collision.data;cm.name='bc_original_world_collision'
settings=[dict(slip=False,two_sided=False,sphere=False) for _ in cm.polygons]
for prop in cm.nwo.face_props:
    key={'slip_surface':'slip','face_sides':'two_sided','face_mode':'sphere'}[prop.type]
    if key=='sphere':assert prop.face_mode=='sphere_collision_only'
    for i,item in enumerate(cm.attributes[prop.attribute_name].data):
        if item.value:settings[i][key]=True
slots=list(cm.materials);variants={}
for face,flags in zip(cm.polygons,settings):
    original=slots[face.material_index];key=(face.material_index,tuple(flags.values()))
    if key not in variants:
        material=original.copy();material.name='bc_world_collision_'+str(len(variants))+'_'+original.name
        p=material.ass_jms;p.is_bm=p.precise=True
        p.render_only=p.lightmap_only=p.shadow_only=False
        p.sphere_collision_only=flags['sphere'];p.slip_surface=flags['slip'];p.two_sided=flags['two_sided']
        special=not original.nwo.shader_path
        if special:
            assert original.name.split('.')[0]=='+sky'
            p.name_override='+sky'
        p.collision_only=not special and not flags['sphere']
        material.update_tag();variants[key]=len(cm.materials);cm.materials.append(material)
    face.material_index=variants[key]
assert len(cm.vertices)==28302 and len(cm.polygons)==46032 and len(variants)==57
for obj in (world,collision):obj.data.update();obj.update_tag(refresh={'DATA'})
bpy.context.view_layer.update()
def geometry_hash(m):
    digest=hashlib.sha256()
    for collection,field,width,code in ((m.vertices,'co',3,'f'),(m.loops,'vertex_index',1,'i'),(m.polygons,'loop_start',1,'i'),(m.polygons,'loop_total',1,'i')):
        values=array(code,[0])*(len(collection)*width);collection.foreach_get(field,values);digest.update(values.tobytes())
    for layer in m.uv_layers:
        values=array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);digest.update(layer.name.encode());digest.update(values.tobytes())
    return digest.hexdigest()
for name,digest in lighting['geometry_and_uv_hashes'].items():
    if name!=mesh.name:assert geometry_hash(bpy.data.meshes[name])==digest,name
report=dict(scene=str(source),before_sha256=before,original_collision_scene_sha256=inspection['scene_sha256'],
    diagnostic_native_tag_sha256=native['native_tag_sha256'],source_world_face_ids=face_ids,
    removed_nonvisual_faces=sorted(removed),visible_faces_preserved=len(mesh.polygons),visible_corners_preserved=len(mesh.loops),
    maximum_visible_normal_delta=normal_delta,geometry_and_uv_preserved=True,render_flag_overrides=overrides,
    collision_mesh=cm.name,collision_vertices=len(cm.vertices),collision_faces=len(cm.polygons),collision_material_variants=len(variants),
    limitation='Standard original-collision authoring split; saved/ASS/native full-map checks and MCC acceptance remain separate gates.')
print('WORLD_COLLISION_AUTHORING_CHECKED',len(mesh.polygons),'visible faces;',len(mesh.loops),'corners; normal delta',normal_delta,flush=True)
if '--apply' not in sys.argv:
    (OUT/'world-collision-authoring-dry-run.json').write_text(json.dumps(report,indent=2)+'\n')
else:
    backup=OUT/'world-authoring-before-split.blend'
    assert not backup.exists()
    shutil.copyfile(source,backup)
    shutil.copyfile(OUT/'h3-lighting-metadata-authoring.json',OUT/'h3-lighting-metadata-before-world-split.json')
    bpy.context.preferences.filepaths.save_version=0
    bpy.context.scene.nwo.lights_export_on_save=False;bpy.context.scene.nwo.prefabs_export_on_save=False
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    runpy.run_path(str(ROOT/'tools/stock-h3-audit/prepare_water_channels.py'))
    report['scene_sha256']=sha(source)
    report['source_scene_before_split']=str(backup)
    lighting['scene_sha256']=report['scene_sha256']
    lighting['geometry_and_uv_hashes'][mesh.name]=geometry_hash(mesh)
    lighting['geometry_and_uv_hashes'][cm.name]=geometry_hash(cm)
    lighting['variants']=len({r['material'] for r in lighting['assignments']})
    lighting['world_collision_authoring']='h3-world-collision-authoring.json'
    (OUT/'h3-lighting-metadata-authoring.json').write_text(json.dumps(lighting,indent=2)+'\n')
    (OUT/'h3-world-collision-authoring.json').write_text(json.dumps(report,indent=2)+'\n')
    print('WORLD_COLLISION_AUTHORING_SAVED',report['scene_sha256'],flush=True)
