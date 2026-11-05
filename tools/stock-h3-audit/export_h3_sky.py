"""Bind stock H3 materials and export the original sky with unchanged tools."""
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
original=json.loads((OUT/'original-sky-import.json').read_text());source=Path(bpy.data.filepath)
assert str(source)==original['scene'] and sha(source)==original['scene_sha256']
assert sha(original['source'])==original['source_sha256']
configured=json.loads((ROOT/'tools/stock-h3-audit/material_families.json').read_text())
families=[name for name in configured if name.startswith('sky_')]+['unlit_sky']
reviewed={}
for family in families:
    report=json.loads((OUT/(family+'-family/report.json')).read_text())
    pixels=json.loads((OUT/(family+'-family/pixel-verification.json')).read_text())
    assert not pixels['color_alpha_problems'],family
    for material in report['materials']:reviewed[material['source']]=material['target']
scene=bpy.context.scene
assert scene.nwo.scale=='blender' and scene.nwo.forward_direction=='y-'
utils.transform_scene(bpy.context,1/.03048,utils.rotation_diff_from_forward('y-','x'),'y-','x',actions=[])
scene.nwo.scale='max';scene.nwo.forward_direction='x'
aliases=KIT/'tags/levels/custom/battle_canyon_fresh/export_shaders';assert aliases.is_dir()
bindings=[];selections=[]
for mesh in {o.data for o in scene.objects if o.type=='MESH'}:
    configurations=[{} for _ in mesh.polygons]
    for prop in mesh.nwo.face_props:
        selection=mesh.attributes[prop.attribute_name]
        settings={}
        if prop.type=='face_sides' and prop.face_sides_type=='two_sided':settings['two_sided']=prop.two_sided
        elif prop.type=='transparent':settings['transparent_1_sided']=prop.transparent
        elif prop.type=='no_shadow':settings['no_shadow']=prop.no_shadow
        else:raise AssertionError(('Review source sky face control',prop.type))
        count=0
        for i,item in enumerate(selection.data):
            if item.value:configurations[i].update(settings);count+=1
        selections.append(dict(property=prop.type,faces=count,settings=settings))
    base=list(mesh.materials);variants={}
    for face,flags in zip(mesh.polygons,configurations):
        if not flags:continue
        if flags.get('two_sided') and flags.get('transparent_1_sided'):
            flags['transparent_1_sided']=False;flags['transparent_2_sided']=True
        key=(face.material_index,tuple(sorted(flags.items())))
        if key not in variants:
            mat=base[face.material_index].copy();mat.ass_jms.is_bm=True
            for name,value in flags.items():setattr(mat.ass_jms,name,value)
            variants[key]=len(mesh.materials);mesh.materials.append(mat)
        face.material_index=variants[key]
    for mat in mesh.materials:
        path=mat.nwo.shader_path;target=KIT/'tags'/reviewed[path]
        alias='bc_'+Path(path).stem.removeprefix('ca_bcreek_')[:12].rstrip('_')+'_'+hashlib.sha256(path.encode()).hexdigest()[:8]
        copied=aliases/(alias+target.suffix);shutil.copyfile(target,copied)
        assert sha(target)==sha(copied)
        mat.ass_jms.name_override='bcf '+alias;mat.update_tag()
        bindings.append(dict(source=path,target=str(target),export_tag=str(copied),sha256=sha(target),name=mat.ass_jms.name_override))
    mesh.update()
bpy.context.view_layer.update()
destination=OUT/'battle-canyon-h3-sky.blend'
bpy.context.preferences.filepaths.save_version=0
scene.nwo.lights_export_on_save=False;scene.nwo.prefabs_export_on_save=False
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
jms=KIT/'data/levels/custom/battle_canyon_fresh/sky/render/battle_canyon_sky.jms';jms.parent.mkdir(parents=True,exist_ok=True)
# JMS 8213 is the upstream H3 format which also retains vertex colors.
status=export_jms.write_file(bpy.context,str(jms),'halo3',8213,'default','superhigh',True,0,
    False,False,True,True,True,False,False,True,True,True,False,
    global_functions.EdgeSplit(False,False,0.0,False),False,False,False,1.0,False,
    lambda level,message:print(level,message,flush=True))
assert status=={'FINISHED'} and jms.is_file() and jms.stat().st_size>0
assert sha(source)==original['scene_sha256']
report=dict(source_sha256=original['scene_sha256'],scene=str(destination),scene_sha256=sha(destination),
    jms=str(jms),jms_sha256=sha(jms),jms_version=8213,bindings=bindings,source_face_controls=selections,
    limitation='Standard authoring/export only. Native model compile, sky object/scenario setup and MCC appearance remain separate steps.')
(OUT/'h3-sky-export.json').write_text(json.dumps(report,indent=2)+'\n')
print('H3_SKY_EXPORTED',str(jms),len(bindings),'material slots',flush=True)
