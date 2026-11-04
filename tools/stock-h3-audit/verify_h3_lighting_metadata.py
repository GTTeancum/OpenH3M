"""Verify saved H3 lighting fields and, optionally, their actual ASS faces."""
from array import array
import collections
import hashlib
import json
from pathlib import Path
import runpy
import sys
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
from io_scene_halo.file_ass.process_scene import get_material_strings
from io_scene_halo.global_functions.mesh_processing import append_material_symbols
report=json.loads((OUT/'h3-lighting-metadata-authoring.json').read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(report['scene'])==report['scene_sha256']
source=Path(bpy.data.filepath)
bound=source.name=='battle-canyon-h3-materials.blend'
assert source in (Path(report['scene']),OUT/'battle-canyon-h3-materials.blend')
before=sha(source)
if bound:
    binding=json.loads((OUT/'h3-material-bindings.json').read_text())
    assert before==binding['scene_sha256'] and not binding['pending']
else:assert before==report['scene_sha256']
native=json.loads((OUT/'original-material-lighting.json').read_text())
emissions=native['scenario_structure_lighting_info']['materials']
for kind,tag in native.items():assert sha(tag['source'])==tag['sha256']==report['source_tags'][kind]
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
for name,digest in report['geometry_and_uv_hashes'].items():assert geometry_hash(bpy.data.meshes[name])==digest,name
for row in report['records']:
    attr=bpy.data.meshes[row['mesh']].attributes[row['attribute']]
    assert [i for i,v in enumerate(attr.data) if v.value]==row['faces']
world_report=json.loads((OUT/report['world_collision_authoring']).read_text()) if report.get('world_collision_authoring') else None
for row in report['assignments']:
    mesh=bpy.data.meshes[row['mesh']]
    material=mesh.materials[mesh.polygons[row['face']].material_index]
    assert material.name==row['material']
    original=bpy.data.materials[row['original_material']]
    assert material.nwo.shader_path==original.nwo.shader_path
    p=material.ass_jms
    assert p.is_bm
    overrides=row.get('world_geometry_flags',{})
    if overrides:
        assert row['mesh']=='cluster:0'
        assert overrides==dict(is_bm=True,precise=True,render_only=True,collision_only=False,sphere_collision_only=False,slip_surface=False)
        assert world_report is not None
        assert world_report['scene_sha256']==report['scene_sha256'] and world_report['render_flag_overrides']==overrides
    for prop in p.bl_rna.properties:
        if prop.type=='BOOLEAN' and prop.identifier not in ('is_bm','attenuation_enabled','power_per_unit_area','use_shader_gel'):
            expected=overrides.get(prop.identifier,getattr(original.ass_jms,prop.identifier))
            assert getattr(p,prop.identifier)==expected,(material.name,prop.identifier)
    settings=row['settings']
    if 'lightmap_res' in settings:assert abs(p.lightmap_res-settings['lightmap_res'])<1e-6
    if 'emission_index' in settings:
        e=emissions[settings['emission_index']]
        for target,key in [('power','power'),('quality','quality'),('emissive_focus','focus'),
            ('falloff_distance','attenuation_falloff'),('cutoff_distance','attenuation_cutoff')]:
            assert abs(getattr(p,target)-e[key])<1e-6,(material.name,target)
        assert max(abs(a-b) for a,b in zip(p.color,e['color_srgb']))<1e-6
        assert p.power_per_unit_area==e['power_per_unit_area'] and p.use_shader_gel==e['use_shader_gel'] and p.attenuation_enabled
result=dict(scene_sha256=before,authoring_scene_sha256=report['scene_sha256'],
    geometry_and_uv_meshes_checked=len(report['geometry_and_uv_hashes']),source_selections_checked=len(report['records']),
    authored_faces_checked=len(report['assignments']),material_variants=report['variants'],ass_faces_checked=0)
wanted_materials={bpy.data.materials[r['material']] for r in report['assignments']}
result['expected_native_materials']=[dict(material=m.name,shader=m.nwo.shader_path,
    lightmap_res=m.ass_jms.lightmap_res,power=m.ass_jms.power,color=list(m.ass_jms.color),
    quality=m.ass_jms.quality,focus=m.ass_jms.emissive_focus,
    power_per_unit_area=m.ass_jms.power_per_unit_area,use_shader_gel=m.ass_jms.use_shader_gel,
    attenuation_enabled=m.ass_jms.attenuation_enabled,
    attenuation_falloff=m.ass_jms.falloff_distance*.01,attenuation_cutoff=m.ass_jms.cutoff_distance*.01)
    for m in sorted(wanted_materials,key=lambda m:m.name)]
if '--ass' in sys.argv:
    assert bound
    export=json.loads((OUT/'h3-bound-ass-inspection-report.json').read_text())
    assert before==export['source_sha256'] and sha(export['ass'])==export['ass_sha256']
    from io_scene_halo.file_ass.process_file import process_file
    asset=process_file(export['ass'])
    actual_materials={(m.name,tuple(m.lighting_info)) for m in asset.materials}
    def signature(mat):return append_material_symbols(mat,'halo3',True),tuple(get_material_strings(mat,7))
    assert {signature(m) for m in wanted_materials}<=actual_materials
    def key(vertices):return tuple(sorted(tuple(round(v,5) for v in point) for point in vertices))
    by_mesh=collections.defaultdict(list)
    for row in report['assignments']:by_mesh[row['mesh']].append(row)
    instances={i.name:i for i in asset.instances}
    for mesh_name,rows in by_mesh.items():
        mesh=bpy.data.meshes[mesh_name]
        obj=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.data==mesh)
        instance=instances[obj.ass_jms.name_override or obj.name]
        exported=asset.objects[instance.object_index]
        triangles=collections.defaultdict(collections.Counter)
        for tri in exported.triangles:
            mat=asset.materials[tri.material_index]
            points=[exported.vertices[i].translation for i in (tri.v0,tri.v1,tri.v2)]
            triangles[key(points)][(mat.name,tuple(mat.lighting_info))]+=1
        mesh.calc_loop_triangles()
        source_triangles=collections.defaultdict(list)
        for tri in mesh.loop_triangles:source_triangles[tri.polygon_index].append(tri)
        for row in rows:
            expected=signature(bpy.data.materials[row['material']])
            for tri in source_triangles[row['face']]:
                points=[mesh.vertices[i].co for i in tri.vertices]
                counter=triangles[key(points)]
                assert counter[expected]>0,(mesh_name,row['face'],expected)
                counter[expected]-=1
                result['ass_faces_checked']+=1
    result['ass_sha256']=export['ass_sha256']
assert sha(source)==before
result['limitation']='Saved source selections, shared inputs and optional ASS face assignments checked; actual native full-map import, bake and MCC appearance remain separate gates.'
suffix='ass' if '--ass' in sys.argv else 'bound' if bound else 'saved'
(OUT/('h3-lighting-metadata-'+suffix+'-verification.json')).write_text(json.dumps(result,indent=2)+'\n')
print('H3_LIGHTING_METADATA_VERIFIED',json.dumps({k:v for k,v in result.items() if k!='expected_native_materials'}),flush=True)
