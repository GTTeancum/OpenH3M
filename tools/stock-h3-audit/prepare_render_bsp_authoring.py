"""Apply strictly passing original render-BSP cases with standard Blender tools."""
from array import array
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import sys
import bpy

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit'
for helper in ('check_foundry.py','check_h3_exporter.py'):runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
def read(name):return json.loads((OUT/name).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
source=Path(bpy.data.filepath)
assert source==OUT/'battle-canyon-h3-authoring.blend'
before=sha(source);bindings=read('h3-material-bindings.json')
assert before==bindings['source_sha256'] and sha(bindings['scene'])==bindings['scene_sha256']
assert not (OUT/'h3-render-bsp-authoring.json').exists(),'Already applied; inspect saved report'
lighting=read('h3-lighting-metadata-authoring.json')
world=read('h3-world-collision-authoring.json');boulders=read('h3-boulder-batch-authoring.json')
assert lighting['scene_sha256']==world['scene_sha256']==boulders['scene_sha256']==before
targets={160:'baseblue_ent',339:'object372'}
pending={53:'teleporter_trimlowside003',261:'teleporter_trimlowside004'}
def geometry(mesh):
    digest=hashlib.sha256()
    for collection,field,width,code in ((mesh.vertices,'co',3,'f'),(mesh.loops,'vertex_index',1,'i'),(mesh.polygons,'loop_start',1,'i'),(mesh.polygons,'loop_total',1,'i')):
        values=array(code,[0])*(len(collection)*width);collection.foreach_get(field,values);digest.update(values.tobytes())
    for layer in mesh.uv_layers:
        values=array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);digest.update(layer.name.encode());digest.update(values.tobytes())
    return digest.hexdigest()
for name,digest in lighting['geometry_and_uv_hashes'].items():assert geometry(bpy.data.meshes[name])==digest
cases=[]
for index,name in targets.items():
    stem='collision-workflow-precise-render-only-original-render-bsp-'+name
    probe=read(stem+'-probe.json');native=read(stem+'-native.json');render=read(stem+'-geometry-comparison.json')
    collision=read('original-render-bsp-native-comparison'+('' if index==53 else '-'+name)+'.json')
    assert probe['source_sha256']==bindings['scene_sha256']
    assert sha(probe['ass'])==probe['ass_sha256']==native['ass_sha256']==render['ass_sha256']==collision['ass_sha256']
    assert not any('ERROR' in s or 'FATAL' in s or 'untextured' in s for s in native['issue_lines'])
    assert all(render['checks'].values()),(name,render['checks'])
    assert collision['within_sample_tolerance'] and collision['physical_flags_match']
    target=bpy.context.scene.objects[name]
    assert target.data.name=='instance_definition:'+str(index)
    assert [o for o in bpy.context.scene.objects if o.type=='MESH' and o.data==target.data]==[target]
    assert not any(getattr(target.data.nwo,f'proxy_physics{i}') for i in range(200))
    children=[c for c in target.children if (c.ass_jms.name_override or c.name).startswith('@')]
    assert len(children)==1
    changes=[]
    for obj in [target,*children]:
        assert not any(r['mesh']==obj.data.name for r in lighting['assignments'])
        for slot,original in enumerate(list(obj.data.materials)):
            copied=original.copy();copied.name='bc_rbs_'+str(index)+'_'+original.name
            copied.ass_jms.name_override=original.ass_jms.name_override or original.name
            copied.ass_jms.is_bm=True;copied.ass_jms.precise=True
            if obj==target:copied.ass_jms.render_only=True
            copied.update_tag();obj.data.materials[slot]=copied
            changes.append(dict(object=obj.name,slot=slot,source_material=original.name,material=copied.name,shader=original.nwo.shader_path,render_only=copied.ass_jms.render_only))
        obj.data.update();obj.update_tag(refresh={'DATA'})
    bpy.context.view_layer.update()
    joined=runpy.run_path(str(ROOT/'tools/stock-h3-audit/add_original_render_bsp_probe.py'),init_globals={'target':target,'definition_index':index})['report']
    cases.append(dict(target=name,mesh=target.data.name,collision_child=children[0].name,changes=changes,join=joined,
        diagnostic_ass_sha256=probe['ass_sha256'],diagnostic_scene_sha256=bindings['scene_sha256']))
modified={r['mesh'] for r in cases}
for name,digest in lighting['geometry_and_uv_hashes'].items():
    if name not in modified:assert geometry(bpy.data.meshes[name])==digest,name
report=dict(scene=str(source),before_sha256=before,cases=cases,pending=pending,
    limitation='Two strictly passing isolated cases. Both trim instances remain unchanged because their strict native comparisons fail. Saved/full ASS/native import and MCC are independent gates.')
if '--apply' in sys.argv:
    for name in ('battle-canyon-h3-authoring.blend','battle-canyon-h3-materials.blend','h3-world-collision-authoring.json','h3-boulder-batch-authoring.json','h3-lighting-metadata-authoring.json','h3-material-bindings.json','h3-full-geometry-import.json','h3-full-geometry-import.log'):
        destination=OUT/('render-bsp-before-'+name);assert not destination.exists();shutil.copyfile(OUT/name,destination)
    bpy.context.preferences.filepaths.save_version=0
    bpy.context.scene.nwo.lights_export_on_save=False;bpy.context.scene.nwo.prefabs_export_on_save=False
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    runpy.run_path(str(ROOT/'tools/stock-h3-audit/prepare_water_channels.py'))
    report['scene_sha256']=sha(source)
    for name in modified:lighting['geometry_and_uv_hashes'][name]=geometry(bpy.data.meshes[name])
    for name,data in (('h3-lighting-metadata-authoring.json',lighting),('h3-world-collision-authoring.json',world),('h3-boulder-batch-authoring.json',boulders)):
        data['scene_sha256']=report['scene_sha256'];data['render_bsp_followup']='h3-render-bsp-authoring.json'
        (OUT/name).write_text(json.dumps(data,indent=2)+'\n')
    destination=OUT/'h3-render-bsp-authoring.json'
else:destination=OUT/'render-bsp-authoring-dry-run.json'
destination.write_text(json.dumps(report,indent=2)+'\n')
print('ORIGINAL_RENDER_BSP_AUTHORING',len(cases),'applied' if '--apply' in sys.argv else 'dry run',report.get('scene_sha256',before),flush=True)
