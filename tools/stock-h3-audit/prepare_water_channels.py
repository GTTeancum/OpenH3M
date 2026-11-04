"""Author verified H3 water channels through Blender; preserve original artwork UVs."""
import hashlib
import json
from pathlib import Path
import runpy
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
source=OUT/'battle-canyon-h3-authoring.blend'
assert Path(bpy.data.filepath)==source
project=bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name=project.project_name=bpy.context.scene.nwo.scene_project
project.project_path=str(ROOT/'work/editing-kits/hrek')
project.tags_directory=str(ROOT/'work/editing-kits/hrek/tags')
project.data_directory=str(ROOT/'work/editing-kits/hrek/data')
project.corinth=False
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
before=sha(source)
original=OUT/'reach-source-inspection.blend'
original_hash=sha(original)
scene_report=json.loads((OUT/'h3-authoring-scene-report.json').read_text())
assert original_hash==scene_report['source_sha256']
witness=json.loads((OUT/'water-channel-workflow-verification.json').read_text())
kit=ROOT/'work/editing-kits/h3ek'
assert sha(kit/'tags/levels/custom/bc_water_workflow_probe/water_four_channels.scenario_structure_bsp')==witness['bsp_sha256']
assert witness['authoring_local_info']==[1000,0] and witness['native_local_info']==[10,0,0]
report_path=OUT/'water-channel-authoring.json'
previous=json.loads(report_path.read_text()) if report_path.exists() else None
meshes={obj.data for obj in bpy.context.scene.objects if obj.type=='MESH' and obj.nwo.mesh_type.endswith('_water_surface')}
assert len(meshes)==3
rows=[]
for mesh in sorted(meshes,key=lambda m:m.name):
    topology=[(tuple(v.co)) for v in mesh.vertices], [tuple(p.vertices) for p in mesh.polygons]
    if len(mesh.uv_layers)==2:
        assert [l.name for l in mesh.uv_layers]==['UVMap0','UVMap1']
        main=[list(v.uv) for v in mesh.uv_layers[0].data]
        shape=[list(v.uv) for v in mesh.uv_layers[1].data]
        mesh.uv_layers.remove(mesh.uv_layers[1])
        local=mesh.uv_layers.new(name='UVMap1',do_init=False)
        velocity=mesh.uv_layers.new(name='UVMap2',do_init=False)
        shape_layer=mesh.uv_layers.new(name='UVMap3',do_init=False)
        for i,uv in enumerate(shape):
            local.data[i].uv=witness['authoring_local_info']
            velocity.data[i].uv=(0,0)
            shape_layer.data[i].uv=uv
    else:
        assert len(mesh.uv_layers)==4 and previous
        # Other authoring may change the scene hash. Verify every UV below
        # against the original retained coordinates before refreshing provenance.
        old=next(r for r in previous['meshes'] if r['mesh']==mesh.name)
        main,shape=old['original_main_uv'],old['original_water_uv']
    assert [l.name for l in mesh.uv_layers]==['UVMap0','UVMap1','UVMap2','UVMap3']
    assert [list(v.uv) for v in mesh.uv_layers[0].data]==main
    assert [list(v.uv) for v in mesh.uv_layers[3].data]==shape
    assert all(tuple(v.uv)==(1000,0) for v in mesh.uv_layers[1].data)
    assert all(tuple(v.uv)==(0,0) for v in mesh.uv_layers[2].data)
    assert topology==([(tuple(v.co)) for v in mesh.vertices],[tuple(p.vertices) for p in mesh.polygons])
    mesh.uv_layers.active_index=0
    rows.append(dict(mesh=mesh.name,vertices=len(mesh.vertices),faces=len(mesh.polygons),
        original_main_uv=main,original_water_uv=shape))
assert sum(r['faces'] for r in rows)==42
bpy.context.preferences.filepaths.save_version=0
bpy.context.scene.nwo.lights_export_on_save=False
bpy.context.scene.nwo.prefabs_export_on_save=False
bpy.ops.wm.save_as_mainfile(filepath=str(source))
assert sha(original)==original_hash
report_path.write_text(json.dumps(dict(scene=str(source),before_sha256=before,scene_sha256=sha(source),
    original_scene_sha256=original_hash,meshes=rows,native_witness=witness,
    limitation='Coordinate authoring verified. Full map native import, physical water volume and MCC behavior remain pending.'),indent=2)+'\n')
print('WATER_CHANNELS_AUTHORED',len(rows),'meshes, 42 faces; original main/shape UVs and topology unchanged.')
