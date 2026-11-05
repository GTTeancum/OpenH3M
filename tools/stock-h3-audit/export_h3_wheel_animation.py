"""Export the unchanged Foundry-imported idle clip through the standard JMA tool."""
import hashlib,json,runpy
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
for helper in ('check_foundry.py','check_h3_exporter.py'):runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
from io_scene_foundry import utils
from io_scene_halo.file_jma import export_jma
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
report=json.loads((OUT/'original-prop-frunner_wheel-animated-clips.json').read_text(encoding='utf-8'))
source=Path(bpy.data.filepath);assert str(source)==report['scene'] and sha(source)==report['scene_sha256']
scene=bpy.context.scene;assert len(scene.nwo.animations)==1 and len(bpy.data.actions)==1
animation=scene.nwo.animations[0];action=bpy.data.actions[0]
assert animation.name=='any idle' and animation.animation_type=='base' and animation.animation_movement_data=='none'
assert (animation.frame_start,animation.frame_end)==(1,200)
armature=next(o for o in scene.objects if o.type=='ARMATURE')
bpy.context.view_layer.objects.active=armature;armature.select_set(True)
assert armature.animation_data.action==action
project=bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
reach=ROOT/'work/editing-kits/hrek';project.name=project.project_name='Original wheel animation export'
project.project_path=str(reach);project.tags_directory=str(reach/'tags');project.data_directory=str(reach/'data');project.corinth=False
scene.nwo.scene_project=project.name
assert scene.nwo.scale=='blender' and scene.nwo.forward_direction=='y-'
utils.transform_scene(bpy.context,1/.03048,utils.rotation_diff_from_forward('y-','x'),'y-','x',actions=[action])
scene.nwo.scale='max';scene.nwo.forward_direction='x'
# Foundry records the authoritative clip interval on the scene animation.
# Its Action defaults to frame zero; export only the original 200 frames.
action.use_frame_range=True;action.frame_start=scene.frame_start=animation.frame_start
def poses():
    result=[]
    for frame in range(1,201):
        scene.frame_set(frame)
        result.append([[v for row in bone.matrix for v in row] for bone in armature.pose.bones])
    return result
original_poses=poses()
# H3 Tool consumes the last JMM sample as the loop boundary, leaving N-1
# playable frames. Add only that boundary with Blender's native keyframe API;
# retain every original frame and verify them all below.
scene.frame_set(1)
first=[(bone.name,bone.location.copy(),bone.rotation_quaternion.copy(),bone.scale.copy()) for bone in armature.pose.bones]
scene.frame_set(201)
for name,location,rotation,scale in first:
    bone=armature.pose.bones[name];assert bone.rotation_mode=='QUATERNION'
    bone.location=location;bone.rotation_quaternion=rotation;bone.scale=scale
    for field in ('location','rotation_quaternion','scale'):bone.keyframe_insert(data_path=field,frame=201,group=name)
after_poses=poses()
deviation=max(abs(a-b) for p,q in zip(original_poses,after_poses) for u,v in zip(p,q) for a,b in zip(u,v))
assert deviation<1e-6,('Loop-boundary insertion changed original frames',deviation)
action.frame_end=scene.frame_end=201
scene.render.fps=30;scene.render.fps_base=1
scene.nwo.lights_export_on_save=False;scene.nwo.prefabs_export_on_save=False
bpy.context.preferences.filepaths.save_version=0
destination=OUT/'h3-wheel-animation.blend';bpy.ops.wm.save_as_mainfile(filepath=str(destination))
jmm=KIT/'data/levels/custom/battle_canyon_fresh/props/frunner_wheel/animations/any idle.JMM'
jmm.parent.mkdir(parents=True,exist_ok=True)
status=export_jma.write_file(context=bpy.context,filepath=str(jmm),report=lambda level,message:print(level,message,flush=True),
    extension='.JMM',jma_version=16395,game_title='halo3',generate_checksum=True,file_checksum=0,
    folder_structure=False,fix_rotations=False,use_maya_sorting=False,frame_rate_value=30,scale_value=1.0)
assert status=={'FINISHED'} and jmm.is_file() and sha(source)==report['scene_sha256']
result=dict(source=str(source),source_sha256=report['scene_sha256'],scene=str(destination),scene_sha256=sha(destination),
    animation='any idle',frames=200,exported_samples=201,loop_boundary='duplicate source frame 1',
    all_200_original_pose_frames_max_deviation=deviation,frame_rate=30,movement='none',jmm=str(jmm),jmm_sha256=sha(jmm),
    limitation='Standard export of source animation only; native compilation, graph linkage and MCC motion remain unverified.')
(OUT/'h3-wheel-animation-export.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('WHEEL_IDLE_EXPORTED',200,'frames',flush=True)
