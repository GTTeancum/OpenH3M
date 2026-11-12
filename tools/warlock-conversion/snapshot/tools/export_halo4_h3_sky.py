"""Export Haven's existing sky mesh through unchanged General-101 JMS authoring."""
import json
import sys
from pathlib import Path
import bpy

sys.path.insert(0,str(Path(__file__).resolve().parent))
from halo4_blender_context import ROOT,OUT,setup,sha
KIT=ROOT/'work/editing-kits/h3ek'
authoring=json.loads((OUT/'haven-h3-authoring-scene.json').read_text())
source=OUT/'h3-authoring/haven-h3-authoring.blend'
assert sha(source)==authoring['destination_sha256']
report_path=OUT/'haven-h3-sky-export-bound.json'
assert not report_path.exists(),'Preserve prior export evidence'
scene=setup(exporter=True,source=source)
from io_scene_halo.file_jms import export_jms
from io_scene_halo.global_functions import global_functions
rows=[r for r in authoring['objects'] if r['role']=='sky']
assert len(rows)==1 and rows[0]['polygons']==18238
original=scene.objects[rows[0]['source_object']]
target_scene=bpy.data.scenes.new('Haven H3 sky export')
obj=original.copy();obj.data=original.data.copy();obj.parent=None
obj.matrix_world=original.matrix_world
target_scene.collection.objects.link(obj)
# JMS needs a model root even for a rigid sky. An identity node retains the
# already verified world-space transform; it adds no rendered geometry.
root=bpy.data.objects.new('frame_haven_sky',None)
target_scene.collection.objects.link(root)
obj.parent=root;obj.matrix_world=original.matrix_world
bpy.context.window.scene=target_scene
target_scene.nwo.lights_export_on_save=False
target_scene.nwo.prefabs_export_on_save=False
material_report=json.loads((OUT/'material-authoring/sky-draft/report.json').read_text())
bindings={r['source']:r for r in material_report['materials']}
used=set();slots=[]
for i,original_material in enumerate(obj.data.materials):
    key=original_material.nwo.shader_path.replace('\\','/')
    row=bindings[key];used.add(key)
    tag=KIT/'tags'/row['target'];assert sha(tag)==row['target_sha256']
    mat=original_material.copy();obj.data.materials[i]=mat
    # Tool resolves JMS names using its shader collection, not full tag paths.
    # The scoped Haven collection is discovered by Tool under this tag root.
    mat.ass_jms.name_override='haven_h4 '+Path(row['target']).stem
    mat.update_tag()
    slots.append(dict(source=key,target=row['target'],name=mat.ass_jms.name_override,shader_sha256=sha(tag)))
assert used==set(bindings)
bpy.context.view_layer.update()
obj.select_set(True);root.select_set(True);bpy.context.view_layer.objects.active=obj
destination=OUT/'h3-authoring/haven-h3-sky-bound.blend'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
jms=KIT/'data/levels/custom/haven_h4/sky/render/haven_sky.jms'
jms.parent.mkdir(parents=True,exist_ok=True)
status=export_jms.write_file(bpy.context,str(jms),'halo3',8213,'default','superhigh',True,0,
    False,False,True,True,True,False,False,True,True,True,False,
    global_functions.EdgeSplit(False,False,0.0,False),False,False,False,1.0,False,
    lambda level,message:print(level,message,flush=True))
assert status=={'FINISHED'} and jms.is_file() and jms.stat().st_size>1000
assert sha(source)==authoring['destination_sha256']
report=dict(source=str(source),source_sha256=sha(source),source_unchanged=True,
    scene=str(destination),scene_sha256=sha(destination),jms=str(jms),jms_sha256=sha(jms),
    jms_version=8213,source_polygons=18238,material_slots=slots,
    vertex_colors_preserved_in_authoring=True,
    limitation='Native compile/readback and rendered sky remain pending. JMS carries RGB; source red opacity is retained as data but its native shader consumption remains pending.')
report_path.write_text(json.dumps(report,indent=2)+'\n')
print('H4_SKY_JMS_EXPORTED',jms,len(slots),'material slots',flush=True)
