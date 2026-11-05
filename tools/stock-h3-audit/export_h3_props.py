"""Bind reviewed stock H3 shaders and export source prop render models.

Uses unchanged Foundry transforms and the unchanged H3 JMS exporter.
Collision/physics source meshes remain in the saved authoring scene; their
native authoring and compilation are separate, unfinished work.
"""
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import bpy

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
for helper in ('check_foundry.py','check_h3_exporter.py'):runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
from io_scene_foundry import utils
from io_scene_halo.file_jms import export_jms
from io_scene_halo.global_functions import global_functions
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
source=Path(bpy.data.filepath);name=source.stem.removeprefix('original-prop-')
original=json.loads((OUT/('original-prop-'+name+'.json')).read_text())
assert source==Path(original['scene']) and sha(source)==original['scene_sha256']
assert sha(original['source'])==original['source_sha256']
reviewed={}
for path in OUT.glob('*-family/report.json'):
    pixels=json.loads((path.parent/'pixel-verification.json').read_text())
    assert not pixels['color_alpha_problems'],path
    for row in json.loads(path.read_text())['materials']:reviewed[row['source']]=row['target']
scene=bpy.context.scene
project=bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name=project.project_name='Original Reach prop export'
reach=ROOT/'work/editing-kits/hrek'
project.project_path=str(reach);project.tags_directory=str(reach/'tags');project.data_directory=str(reach/'data');project.corinth=False
scene.nwo.scene_project=project.name
assert scene.nwo.scale=='blender' and scene.nwo.forward_direction=='y-'
utils.transform_scene(bpy.context,1/.03048,utils.rotation_diff_from_forward('y-','x'),'y-','x',actions=[])
scene.nwo.scale='max';scene.nwo.forward_direction='x'
aliases=KIT/'tags/levels/custom/battle_canyon_fresh/export_shaders';bindings=[];meshes=[]
for obj in scene.objects:
    if obj.type=='EMPTY':obj.name='#'+obj.name.lstrip('#')
    if obj.type!='MESH':continue
    kind=obj.data.nwo.mesh_type
    if kind=='_connected_geometry_mesh_type_collision':obj.name='@'+obj.name.lstrip('@');continue
    if kind=='_connected_geometry_mesh_type_physics':obj.name='$'+obj.name.lstrip('$');continue
    assert kind=='_connected_geometry_mesh_type_default',(obj.name,kind)
    mesh=obj.data;meshes.append(dict(name=obj.name,vertices=len(mesh.vertices),triangles=len(mesh.polygons)))
    assert all(len(f.vertices)==3 for f in mesh.polygons)
    configurations=[{} for _ in mesh.polygons]
    controls=[dict(type=p.type,draw_distance=p.draw_distance,faces=sum(bool(v.value) for v in mesh.attributes[p.attribute_name].data)) for p in mesh.nwo.face_props]
    print('SOURCE_PROP_FACE_CONTROLS',json.dumps(controls),flush=True)
    for prop in mesh.nwo.face_props:
        settings={}
        if prop.type=='face_sides' and prop.face_sides_type=='two_sided':settings['two_sided']=prop.two_sided
        elif prop.type=='transparent':settings['transparent_1_sided']=prop.transparent
        elif prop.type=='no_shadow':settings['no_shadow']=prop.no_shadow
        elif prop.type=='draw_distance':
            selected=[i for i,item in enumerate(mesh.attributes[prop.attribute_name].data) if item.value]
            print('SOURCE_DRAW_DISTANCE',prop.draw_distance,len(selected),'faces',flush=True)
            assert prop.draw_distance=='normal',('H3 native part flags have no detail draw-distance control',prop.draw_distance,len(selected))
        else:raise AssertionError(('Review source prop face control',prop.type))
        for i,item in enumerate(mesh.attributes[prop.attribute_name].data):
            if item.value:configurations[i].update(settings)
    base=list(mesh.materials);variants={}
    for face,flags in zip(mesh.polygons,configurations):
        if not flags:continue
        if flags.get('two_sided') and flags.get('transparent_1_sided'):
            flags['transparent_1_sided']=False;flags['transparent_2_sided']=True
        key=(face.material_index,tuple(sorted(flags.items())))
        if key not in variants:
            mat=base[face.material_index].copy();mat.ass_jms.is_bm=True
            for flag,value in flags.items():setattr(mat.ass_jms,flag,value)
            variants[key]=len(mesh.materials);mesh.materials.append(mat)
        face.material_index=variants[key]
    for mat in mesh.materials:
        path=mat.nwo.shader_path;target=KIT/'tags'/reviewed[path]
        alias='bc_'+Path(path).stem.removeprefix('ca_bcreek_')[:12].rstrip('_')+'_'+hashlib.sha256(path.encode()).hexdigest()[:8]
        copied=aliases/(alias+target.suffix)
        if not copied.exists() or sha(copied)!=sha(target):shutil.copyfile(target,copied)
        assert sha(target)==sha(copied)
        mat.ass_jms.name_override='bcf '+alias;mat.update_tag()
        bindings.append(dict(source=path,target=str(target),alias=str(copied),sha256=sha(target)))
    mesh.update()
bpy.context.view_layer.update()
destination=OUT/('h3-prop-'+name+'.blend')
bpy.context.preferences.filepaths.save_version=0
scene.nwo.lights_export_on_save=False;scene.nwo.prefabs_export_on_save=False
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
jms=KIT/('data/levels/custom/battle_canyon_fresh/props/'+name+'/render/'+name+'.jms');jms.parent.mkdir(parents=True,exist_ok=True)
status=export_jms.write_file(context=bpy.context,filepath=str(jms),game_title='halo3',jms_version=8213,
    permutation_ce='default',level_of_detail_ce='superhigh',generate_checksum=True,file_checksum=0,
    folder_structure=False,write_textures=False,hidden_geo=True,nonrender_geo=True,export_render=True,
    export_collision=False,export_physics=False,apply_modifiers=True,triangulate_faces=True,
    loop_normals=True,clean_normalize_weights=False,edge_split=global_functions.EdgeSplit(False,False,0.0,False),
    fix_rotations=False,use_maya_sorting=False,folder_type=False,scale_value=1.0,merge_instances=False,
    report=lambda level,message:print(level,message,flush=True))
assert status=={'FINISHED'} and jms.is_file() and jms.stat().st_size>0
assert sha(source)==original['scene_sha256']
(OUT/('h3-prop-'+name+'-export.json')).write_text(json.dumps(dict(source=str(source),source_sha256=original['scene_sha256'],
    scene=str(destination),scene_sha256=sha(destination),jms=str(jms),jms_sha256=sha(jms),bindings=bindings,meshes=meshes,
    limitation='Render export only. Collision/physics compilation, object setup/placement, wheel animation and MCC appearance remain unverified.'),indent=2)+'\n')
print('H3_PROP_RENDER_EXPORTED',name,len(bindings),'material bindings',flush=True)
