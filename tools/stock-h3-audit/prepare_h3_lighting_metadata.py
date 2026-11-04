"""Author approved native H3 lighting controls on the original face selections.

Without --apply, inspect and write a plan only. Uses existing Blender material
properties consumed by the unchanged ASS exporter; no tag/lighting serializer.
"""
from array import array
import collections
import hashlib
import json
import math
from pathlib import Path
import runpy
import sys
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
from io_scene_foundry import utils
from io_scene_foundry.constants import WU_SCALAR
project=bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name=project.project_name=bpy.context.scene.nwo.scene_project
project.project_path=str(ROOT/'work/editing-kits/hrek')
project.tags_directory=str(ROOT/'work/editing-kits/hrek/tags')
project.data_directory=str(ROOT/'work/editing-kits/hrek/data')
project.corinth=False
source=Path(bpy.data.filepath)
assert source==OUT/'battle-canyon-h3-authoring.blend'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
before=sha(source)
assert before==json.loads((OUT/'water-channel-authoring.json').read_text())['scene_sha256']
proposal=ROOT/'tools/stock-h3-audit/LIGHTING-METADATA-PROPOSAL.md'
assert 'Status: approved by the user on 2026-11-04' in proposal.read_text()
native=json.loads((OUT/'original-material-lighting.json').read_text())
for tag in native.values():assert sha(tag['source'])==tag['sha256']
emissions=native['scenario_structure_lighting_info']['materials']
original_materials=native['scenario_structure_bsp']['materials']
pending=json.loads((OUT/'h3-authoring-scene-report.json').read_text())['pending_face_properties']
expected={(r['mesh'],r['attribute'],r['property']) for r in pending}
assert len(expected)==117
priorities={1:.0625,2:.25,3:1,4:4,5:8,6:16,7:32}

def close(a,b):return abs(a-b)<1e-5
def emission_matches(prop,e):
    return (close(prop.light_intensity_value,e['power'])
        and all(close(a,utils.srgb_to_linear(b)) for a,b in zip(prop.material_lighting_emissive_color,e['color_srgb']))
        and close(prop.material_lighting_emissive_focus,e['focus']*math.pi)
        and close(prop.material_lighting_emissive_quality,e['quality'])
        and prop.material_lighting_emissive_per_unit==e['power_per_unit_area']
        and prop.material_lighting_use_shader_gel==e['use_shader_gel']
        and close(prop.material_lighting_bounce_ratio,e['bounce_ratio'])
        and close(prop.material_lighting_attenuation_falloff,e['attenuation_falloff']*.01/WU_SCALAR)
        and close(prop.material_lighting_attenuation_cutoff,e['attenuation_cutoff']*.01/WU_SCALAR))

def geometry_hash(mesh):
    digest=hashlib.sha256()
    for collection,field,width,code in ((mesh.vertices,'co',3,'f'),(mesh.loops,'vertex_index',1,'i'),
        (mesh.polygons,'loop_start',1,'i'),(mesh.polygons,'loop_total',1,'i')):
        values=array(code,[0])*(len(collection)*width)
        collection.foreach_get(field,values)
        digest.update(values.tobytes())
    for layer in mesh.uv_layers:
        values=array('f',[0])*(len(layer.data)*2)
        layer.data.foreach_get('uv',values)
        digest.update(layer.name.encode())
        digest.update(values.tobytes())
    return digest.hexdigest()

meshes={o.data for o in bpy.context.scene.objects if o.type=='MESH'}
plans={}
records=[]
seen=set()
for mesh in sorted(meshes,key=lambda m:m.name):
    faces={}
    for prop in mesh.nwo.face_props:
        key=(mesh.name,prop.attribute_name,prop.type)
        if key not in expected:continue
        assert key not in seen,key
        seen.add(key)
        attr=mesh.attributes[prop.attribute_name]
        assert attr.domain=='FACE'
        indices=[i for i,v in enumerate(attr.data) if v.value]
        assert len(indices)==next(r['faces'] for r in pending if (r['mesh'],r['attribute'],r['property'])==key)
        row=dict(mesh=mesh.name,attribute=prop.attribute_name,type=prop.type,faces=indices)
        if prop.type=='lightmap_resolution_scale':
            category=int(prop.lightmap_resolution_scale)
            row.update(source_category=category,h3_priority=priorities[category])
            for index in indices:
                settings=faces.setdefault(index,{})
                assert 'lightmap_res' not in settings
                settings['lightmap_res']=priorities[category]
        elif prop.type=='emissive':
            paths={mesh.materials[mesh.polygons[i].material_index].nwo.shader_path for i in indices}
            candidates={r['emission_index'] for r in original_materials if r['shader'] in paths and r['emission_index']>0}
            matches=[i for i in sorted(candidates) if emission_matches(prop,emissions[i])]
            assert len(matches)==1,(mesh.name,prop.attribute_name,paths,matches,candidates)
            index=matches[0]
            row.update(source_emission_index=index,source_emission=emissions[index])
            for face in indices:
                settings=faces.setdefault(face,{})
                assert 'emission_index' not in settings
                settings['emission_index']=index
        elif prop.type=='lightmap_chart_group':
            assert prop.lightmap_chart_group==17 and len(indices)==28
            row['approved_native_behavior']='H3 chart packing'
        elif prop.type=='lightmap_type':
            assert len(indices)==2432
            row['approved_native_behavior']='H3 default BSP lighting; preserve geometry and separate instance lighting policies'
        else:raise AssertionError(prop.type)
        records.append(row)
    if faces:plans[mesh]=faces
assert seen==expected,(seen^expected)
counts=dict(collections.Counter(r['type'] for r in records))
plan=dict(scene=str(source),before_sha256=before,approval_document_sha256=sha(proposal),
    source_tags={k:v['sha256'] for k,v in native.items()},counts=counts,records=records,
    limitation='Approved native H3 lighting authoring plan. Not baked lighting or MCC acceptance.')
(OUT/'h3-lighting-metadata-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print('H3_LIGHTING_METADATA_PLAN',json.dumps(counts),'meshes',len(plans),flush=True)
if '--apply' not in sys.argv:raise SystemExit(0)
report_path=OUT/'h3-lighting-metadata-authoring.json'
assert not report_path.exists(),'Lighting has already been applied; verify existing evidence before repeating.'
snapshots={mesh:geometry_hash(mesh) for mesh in meshes}
variants={}
assignments=[]
for mesh,faces in plans.items():
    for index,settings in sorted(faces.items()):
        polygon=mesh.polygons[index]
        original=mesh.materials[polygon.material_index]
        key=(original.name,tuple(sorted(settings.items())))
        variant=variants.get(key)
        if variant is None:
            variant=original.copy()
            variant.name='bc_lighting_'+str(len(variants)).zfill(3)+'_'+original.name
            variant.ass_jms.name_override=original.ass_jms.name_override or original.name
            p=variant.ass_jms
            p.is_bm=True
            if 'lightmap_res' in settings:p.lightmap_res=settings['lightmap_res']
            if 'emission_index' in settings:
                e=emissions[settings['emission_index']]
                p.power=e['power']
                p.color=e['color_srgb']
                p.quality=e['quality']
                p.emissive_focus=e['focus']
                p.power_per_unit_area=e['power_per_unit_area']
                p.use_shader_gel=e['use_shader_gel']
                p.attenuation_enabled=True
                p.falloff_distance=e['attenuation_falloff']
                p.cutoff_distance=e['attenuation_cutoff']
            variant.update_tag()
            variants[key]=variant
        slot=mesh.materials.find(variant.name)
        if slot<0:
            slot=len(mesh.materials)
            mesh.materials.append(variant)
        polygon.material_index=slot
        assignments.append(dict(mesh=mesh.name,face=index,material=variant.name,original_material=original.name,settings=settings))
    mesh.update()
assert all(geometry_hash(mesh)==digest for mesh,digest in snapshots.items())
bpy.context.view_layer.update()
bpy.context.preferences.filepaths.save_version=0
bpy.context.scene.nwo.lights_export_on_save=False
bpy.context.scene.nwo.prefabs_export_on_save=False
bpy.ops.wm.save_as_mainfile(filepath=str(source))
runpy.run_path(str(ROOT/'tools/stock-h3-audit/prepare_water_channels.py'))
plan.update(scene_sha256=sha(source),variants=len(variants),assignments=assignments,
    geometry_and_uv_hashes={m.name:d for m,d in snapshots.items()},
    limitation='Approved controls authored on original selections; geometry/UVs unchanged. Saved-scene, ASS and native full-map checks plus bake/MCC review remain.')
report_path.write_text(json.dumps(plan,indent=2)+'\n')
print('H3_LIGHTING_METADATA_AUTHORED',len(variants),'material variants',len(assignments),'faces',flush=True)
