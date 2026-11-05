"""Export original prop collision through unchanged Blender/H3 JMS tools."""
import hashlib
import json
from pathlib import Path
import re
import runpy
import bpy
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
for helper in ('check_foundry.py','check_h3_exporter.py'):runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
from io_scene_halo.file_jms import export_jms
from io_scene_halo.global_functions import global_functions
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
source=Path(bpy.data.filepath);name=source.stem.removeprefix('h3-prop-')
original=json.loads((OUT/('h3-prop-'+name+'-export.json')).read_text())
assert sha(source)==original['scene_sha256']
scene=bpy.context.scene;assert scene.nwo.scale=='max' and scene.nwo.forward_direction=='x'
project=bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
reach=ROOT/'work/editing-kits/hrek';project.name=project.project_name='Source prop collision'
project.project_path=str(reach);project.tags_directory=str(reach/'tags');project.data_directory=str(reach/'data');project.corinth=False
scene.nwo.scene_project=project.name
stock=set(re.findall(r'\] Name: StringId = (\S+)',(OUT/'standoff-global-materials.txt').read_text()))
collisions=[]
for obj in scene.objects:
    if obj.type!='MESH' or obj.data.nwo.mesh_type!='_connected_geometry_mesh_type_collision':continue
    assert obj.name.startswith('@') and obj.parent and obj.parent.type=='ARMATURE'
    mesh=obj.data;settings=[dict(material=None) for _ in mesh.polygons]
    for prop in mesh.nwo.face_props:
        print('COLLISION_FACE_CONTROL',name,prop.type,flush=True)
        assert prop.type=='global_material',('Review native collision control',name,prop.type)
        for index,entry in enumerate(mesh.attributes[prop.attribute_name].data):
            if entry.value:settings[index]['material']=prop.global_material or 'default'
    mesh.materials.clear();slots={}
    for face,row in zip(mesh.polygons,settings):
        material=row['material']
        # Keep the source's literal default identifier for native Tool to
        # resolve; its saved global-material mapping must be checked later.
        assert material in stock or material=='default',('No original H3 physical material',material)
        if material not in slots:
            mat=bpy.data.materials.new('Prop collision '+material);mat.ass_jms.name_override=material
            slots[material]=len(mesh.materials);mesh.materials.append(mat)
        face.material_index=slots[material]
    collisions.append(dict(name=obj.name,vertices=len(mesh.vertices),polygon_faces=len(mesh.polygons),
                           triangulated_faces=sum(len(face.vertices)-2 for face in mesh.polygons),materials=slots))
assert collisions
bpy.context.view_layer.update()
directory=KIT/('data/levels/custom/battle_canyon_fresh/props/'+name+'/collision');directory.mkdir(parents=True,exist_ok=True)
requested=directory/(name+'.jms')
status=export_jms.write_file(context=bpy.context,filepath=str(requested),game_title='halo3',jms_version=8213,
    permutation_ce='default',level_of_detail_ce='superhigh',generate_checksum=True,file_checksum=0,
    folder_structure=False,write_textures=False,hidden_geo=True,nonrender_geo=True,export_render=False,
    export_collision=True,export_physics=False,apply_modifiers=True,triangulate_faces=True,
    loop_normals=True,clean_normalize_weights=False,edge_split=global_functions.EdgeSplit(False,False,0.0,False),
    fix_rotations=False,use_maya_sorting=False,folder_type=False,scale_value=1.0,merge_instances=False,
    report=lambda level,message:print(level,message,flush=True))
jms=directory/(name+'_collision.jms')
assert status=={'FINISHED'} and jms.is_file() and jms.stat().st_size>0
assert sha(source)==original['scene_sha256']
(OUT/('h3-prop-'+name+'-collision-export.json')).write_text(json.dumps(dict(source=str(source),source_sha256=sha(source),
    jms=str(jms),jms_sha256=sha(jms),meshes=collisions,
    limitation='Original collision geometry and source material identifiers exported. Named physical materials occur in stock H3; literal default requires native mapping verification. Native compilation, physics and in-game collision remain unverified.'),indent=2)+'\n')
print('PROP_COLLISION_EXPORTED',name,collisions,flush=True)
