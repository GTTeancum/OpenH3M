"""Export original convex prop shapes using unchanged Blender/H3 JMS tools."""
import hashlib
import json
from pathlib import Path
import runpy
import xml.etree.ElementTree as ET
import bpy
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
for helper in ('check_foundry.py','check_h3_exporter.py'):runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
from io_scene_halo.file_jms import export_jms
from io_scene_halo.global_functions import global_functions

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
source=Path(bpy.data.filepath);name=source.stem.removeprefix('h3-prop-')
assert name in ('frunner_wheel','cex_health_cabinet','ff_redbase_rocks02')
original=json.loads((OUT/f'h3-prop-{name}-export.json').read_text())
assert sha(source)==original['scene_sha256']
scene=bpy.context.scene;assert scene.nwo.scale=='max' and scene.nwo.forward_direction=='x'
project=bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
reach=ROOT/'work/editing-kits/hrek';project.name=project.project_name='Original prop physics'
project.project_path=str(reach);project.tags_directory=str(reach/'tags');project.data_directory=str(reach/'data');project.corinth=False
scene.nwo.scene_project=project.name
native=ET.fromstring((OUT/f'original-prop-{name}-physics.xml').read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
blocks={};block=None
for e in native:
    if e.tag=='field':
        block=e.get('name') if e.get('type')=='block' else None
        if block:blocks[block]=[]
    elif e.tag=='element' and block:blocks[block].append(e)
assert len(blocks['rigid bodies'])==len(blocks['polyhedra'])==len(blocks['materials'])==1
assert all(not blocks.get(k) for k in ('spheres','pills','boxes','lists','mopps','ragdoll constraints','limited hinge constraints','hinge constraints'))
field=lambda element,key:element.find(f'./field[@name="{key}"]').get('value')
material=field(blocks['materials'][0],'name');body=blocks['rigid bodies'][0]
assert field(body,'shape type')=='polyhedron' and field(body,'mass')=='0'
objects=[o for o in scene.objects if o.type=='MESH' and o.data.nwo.mesh_type=='_connected_geometry_mesh_type_physics']
assert len(objects)==1
obj=objects[0];assert obj.name.startswith('$') and obj.parent and obj.parent.type=='ARMATURE'
obj.data.ass_jms.Object_Type='CONVEX SHAPES'
obj.data.materials.clear();mat=bpy.data.materials.new('Original physics '+material);mat.ass_jms.name_override=material;obj.data.materials.append(mat)
for face in obj.data.polygons:face.material_index=0
bpy.context.view_layer.update()
directory=KIT/('data/levels/custom/battle_canyon_fresh/props/'+name+'/physics');directory.mkdir(parents=True,exist_ok=True)
status=export_jms.write_file(context=bpy.context,filepath=str(directory/(name+'.jms')),game_title='halo3',jms_version=8213,
    permutation_ce='default',level_of_detail_ce='superhigh',generate_checksum=True,file_checksum=0,
    folder_structure=False,write_textures=False,hidden_geo=True,nonrender_geo=True,export_render=False,
    export_collision=False,export_physics=True,apply_modifiers=True,triangulate_faces=True,
    loop_normals=True,clean_normalize_weights=False,edge_split=global_functions.EdgeSplit(False,False,0.0,False),
    fix_rotations=False,use_maya_sorting=False,folder_type=False,scale_value=1.0,merge_instances=False,
    report=lambda level,message:print(level,message,flush=True))
jms=directory/(name+'_physics.jms')
assert status=={'FINISHED'} and jms.is_file() and jms.stat().st_size>0 and sha(source)==original['scene_sha256']
(OUT/f'h3-prop-{name}-physics-export.json').write_text(json.dumps(dict(source=str(source),source_sha256=sha(source),
    jms=str(jms),jms_sha256=sha(jms),mesh=obj.name,vertices=len(obj.data.vertices),polygon_faces=len(obj.data.polygons),
    material=material,source_body_node=field(body,'node'),source_motion_type=field(body,'motion type'),
    limitation='Original convex geometry exported through standard tools. Native physics/material resolution and MCC behavior remain unverified.'),indent=2)+'\n')
print('PROP_PHYSICS_EXPORTED',name,len(obj.data.vertices),'vertices',material,flush=True)
