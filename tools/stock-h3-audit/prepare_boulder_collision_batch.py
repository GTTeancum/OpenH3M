"""Apply standard material flags only to the ten clean isolated boulder cases.

Native compiler position/normal differences remain documented for MCC review.
No mesh, shader, collision serializer, exporter or compiler implementation edits.
"""
from array import array
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import sys
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
def read(name):return json.loads((OUT/name).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
source=Path(bpy.data.filepath)
assert source==OUT/'battle-canyon-h3-authoring.blend'
before=sha(source)
bindings=read('h3-material-bindings.json')
batch=read('boulder-batch-verification.json')
imports=read('boulder-batch-import.json')
assert before==bindings['source_sha256']
assert sha(bindings['scene'])==batch['scene_sha256']==imports['scene_sha256']==bindings['scene_sha256']
assert not (OUT/'h3-boulder-batch-authoring.json').exists(),'Already applied; inspect saved report'
eligible=[];excluded=[]
for row in batch['results']:
    name=row['target'];comparison=row['comparison']
    native=next(r['report'] for r in imports['results'] if r['target']==name)
    stem='collision-workflow-precise-render-only-'+name
    probe=read(stem+'-probe.json')
    assert sha(probe['ass'])==comparison['ass_sha256']==native['ass_sha256']
    assert sha(OUT/(stem+'-bsp.xml'))==native['native_xml_sha256']==comparison['native_xml_sha256']
    assert probe['source_sha256']==batch['scene_sha256']
    if any('ERROR' in line or 'FATAL' in line for line in native['issue_lines']):
        excluded.append(name);continue
    assert comparison['render_winding_preserved'] and comparison['checks']['uv']
    assert comparison['render_bsp_absent_as_in_reach'] and comparison['mopp_bytes']>0
    eligible.append(name)
assert len(eligible)==10 and excluded==['boulder_west_lowz002']
lighting=read('h3-lighting-metadata-authoring.json')
world=read('h3-world-collision-authoring.json')
assert lighting['scene_sha256']==world['scene_sha256']==before
def geometry(mesh):
    digest=hashlib.sha256()
    for collection,field,width,code in ((mesh.vertices,'co',3,'f'),(mesh.loops,'vertex_index',1,'i'),
                                      (mesh.polygons,'loop_start',1,'i'),(mesh.polygons,'loop_total',1,'i')):
        values=array(code,[0])*(len(collection)*width);collection.foreach_get(field,values);digest.update(values.tobytes())
    for layer in mesh.uv_layers:
        values=array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);digest.update(layer.name.encode());digest.update(values.tobytes())
    return digest.hexdigest()
for name,digest in lighting['geometry_and_uv_hashes'].items():assert geometry(bpy.data.meshes[name])==digest
changes=[];normals={}
for name in eligible:
    target=bpy.context.scene.objects[name]
    children=[c for c in target.children if (c.ass_jms.name_override or c.name).startswith('@')]
    assert len(children)==1
    assert not any(getattr(target.data.nwo,f'proxy_physics{i}') for i in range(200))
    assert [o for o in bpy.context.scene.objects if o.type=='MESH' and o.data==target.data]==[target]
    for obj in [target,*children]:
        assert not any(r['mesh']==obj.data.name for r in lighting['assignments'])
        normals[obj.data.name]=[tuple(n.vector) for n in obj.data.corner_normals]
        for index,original in enumerate(list(obj.data.materials)):
            copied=original.copy();copied.name='bc_boulder_'+name+'_'+original.name
            copied.ass_jms.name_override=original.ass_jms.name_override or original.name
            copied.ass_jms.is_bm=True;copied.ass_jms.precise=True
            if obj==target:copied.ass_jms.render_only=True
            copied.update_tag();obj.data.materials[index]=copied
            changes.append(dict(object=obj.name,mesh=obj.data.name,slot=index,source_material=original.name,
                material=copied.name,precise=True,render_only=copied.ass_jms.render_only,shader=original.nwo.shader_path))
        obj.data.update();obj.update_tag(refresh={'DATA'})
bpy.context.view_layer.update()
for name,digest in lighting['geometry_and_uv_hashes'].items():assert geometry(bpy.data.meshes[name])==digest
for name,values in normals.items():assert [tuple(n.vector) for n in bpy.data.meshes[name].corner_normals]==values
report=dict(scene=str(source),before_sha256=before,diagnostic_scene_sha256=batch['scene_sha256'],
    eligible=eligible,excluded=excluded,changes=changes,all_geometry_uv_hashes_unchanged=True,
    all_target_corner_normals_unchanged=True,native_comparisons=batch['results'],
    limitation='Ten clean native authoring cases only. Numeric position/normal and four collision-sample tolerance failures remain recorded; no MCC acceptance. West boulder remains unchanged.')
if '--apply' in sys.argv:
    for name in ('battle-canyon-h3-authoring.blend','battle-canyon-h3-materials.blend','h3-world-collision-authoring.json','h3-lighting-metadata-authoring.json','h3-material-bindings.json','h3-full-geometry-import.json','h3-full-geometry-import.log'):
        dest=OUT/('boulder-batch-before-'+name)
        assert not dest.exists();shutil.copyfile(OUT/name,dest)
    project=bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
    project.name=project.project_name=bpy.context.scene.nwo.scene_project
    project.project_path=str(ROOT/'work/editing-kits/hrek')
    project.tags_directory=str(ROOT/'work/editing-kits/hrek/tags')
    project.data_directory=str(ROOT/'work/editing-kits/hrek/data');project.corinth=False
    bpy.context.preferences.filepaths.save_version=0
    bpy.context.scene.nwo.lights_export_on_save=False;bpy.context.scene.nwo.prefabs_export_on_save=False
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    runpy.run_path(str(ROOT/'tools/stock-h3-audit/prepare_water_channels.py'))
    report['scene_sha256']=sha(source)
    for data in (lighting,world):
        data['scene_sha256']=report['scene_sha256']
        data['boulder_batch_authoring']='h3-boulder-batch-authoring.json'
    (OUT/'h3-world-collision-authoring.json').write_text(json.dumps(world,indent=2)+'\n')
    (OUT/'h3-lighting-metadata-authoring.json').write_text(json.dumps(lighting,indent=2)+'\n')
    destination=OUT/'h3-boulder-batch-authoring.json'
else:destination=OUT/'boulder-batch-authoring-dry-run.json'
destination.write_text(json.dumps(report,indent=2)+'\n')
print('BOULDER_BATCH_AUTHORING',len(eligible),'applied' if '--apply' in sys.argv else 'dry run',report.get('scene_sha256',before),flush=True)
