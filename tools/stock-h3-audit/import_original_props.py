"""Import remaining original appearance assets with unchanged Foundry.

Separate source scenes preserve render/collision/physics/markers for H3
authoring. This does not import Reach gameplay or approve H3 behavior.
"""
import hashlib
import json
from pathlib import Path
import runpy
import sys
import bpy

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/hrek'
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_foundry.py'))
palette=json.loads((OUT/'original-gameplay-palettes.json').read_text())['palettes']
sources={}
for group,stem in [('scenery palette','frunner_wheel'),('crate palette','cex_health_cabinet'),
                   ('crate palette','ff_redbase_rocks02'),('control palette','health_station')]:
    matches=[p for p in palette[group] if Path(p).stem==stem]
    assert len(matches)==1,(group,stem,matches)
    sources[stem]=matches[0]
name=sys.argv[sys.argv.index('--')+1];relative=sources[name];source=KIT/'tags'/relative
destination=OUT/('original-prop-'+name+'.blend')
assert not destination.exists(),'Inspect existing source scene before rerunning'
before=hashlib.sha256(source.read_bytes()).hexdigest()
prefs=bpy.context.preferences.addons['io_scene_foundry'].preferences
project=prefs.projects.add();project.name=project.project_name='Original Reach prop '+name
project.project_path=str(KIT);project.tags_directory=str(KIT/'tags');project.data_directory=str(KIT/'data');project.corinth=False
scene=bpy.context.scene;scene.nwo.scene_project=project.name
scene.nwo_export.show_output=False;scene.nwo.lights_export_on_save=False;scene.nwo.prefabs_export_on_save=False
bpy.context.preferences.filepaths.save_version=0
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
status=bpy.ops.nwo.foundry_import(filepath=str(source),build_blender_materials=False,
    tag_import_lights=False,tag_collision=True,tag_physics=True,tag_markers=True,
    tag_animation=False,setup_as_asset=False)
assert status=={'FINISHED'}
meshes=[o for o in scene.objects if o.type=='MESH'];assert meshes,name
materials=sorted({m.nwo.shader_path for o in meshes for m in o.data.materials if m and m.nwo.shader_path})
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
report=dict(source=str(source),source_sha256=before,scene=str(destination),
    scene_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),materials=materials,
    objects=[dict(name=o.name,type=o.type,mesh_type=o.data.nwo.mesh_type if o.type=='MESH' else None,
                  vertices=len(o.data.vertices) if o.type=='MESH' else None,
                  faces=len(o.data.polygons) if o.type=='MESH' else None) for o in scene.objects],
    limitation='Original source authoring import only. No H3 tags, gameplay, healing, animation or visual acceptance is established. Animation is separate work.')
(OUT/('original-prop-'+name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
print('ORIGINAL_PROP_IMPORTED',name,len(meshes),'meshes',len(materials),'materials',flush=True)
