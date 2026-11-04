"""Inspect saved river assignments through Blender and the unmodified exporter."""
import hashlib
import json
from pathlib import Path
import runpy
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
from io_scene_halo.global_functions.mesh_processing import append_material_symbols

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

bindings=json.loads((OUT/'h3-material-bindings.json').read_text())
assert bpy.data.filepath==bindings['scene'] and sha(bpy.data.filepath)==bindings['scene_sha256']
assert not bindings['pending']
for binding in bindings['bindings'].values():
    assert sha(binding['authored'])==sha(binding['export_tag'])==binding['sha256']
source=r'levels\dlc\cex_beaver_creek\shaders\ca_bcreek_river.shader_water'
binding=bindings['bindings'][source]
pixels=json.loads((OUT/'water-family/pixel-verification.json').read_text())
channels=json.loads((OUT/'water-channel-authoring.json').read_text())
assert bindings['source_sha256']==channels['scene_sha256']
assert not pixels['color_alpha_problems']
for texture in pixels['textures']:
    assert sha(ROOT/'work/editing-kits/h3ek/tags'/texture['target'])==texture['target_sha256']
rows=[]
for obj in bpy.context.scene.objects:
    if obj.type!='MESH':continue
    for index,material in enumerate(obj.data.materials):
        if not material or material.nwo.shader_path!=source:continue
        faces=[p for p in obj.data.polygons if p.material_index==index]
        if not faces:continue
        assert obj.nwo.mesh_type.endswith('_water_surface')
        name=append_material_symbols(material,'halo3',True)
        assert name==binding['name']+"'",name
        expected=next(r for r in channels['meshes'] if r['mesh']==obj.data.name)
        assert [l.name for l in obj.data.uv_layers]==['UVMap0','UVMap1','UVMap2','UVMap3']
        assert [list(v.uv) for v in obj.data.uv_layers[0].data]==expected['original_main_uv']
        assert [list(v.uv) for v in obj.data.uv_layers[3].data]==expected['original_water_uv']
        assert all(tuple(v.uv)==(1000,0) for v in obj.data.uv_layers[1].data)
        assert all(tuple(v.uv)==(0,0) for v in obj.data.uv_layers[2].data)
        rows.append(dict(object=obj.name,mesh=obj.data.name,faces=len(faces),export_name=name,
            uv_layers=[layer.name for layer in obj.data.uv_layers]))
assert sorted(r['faces'] for r in rows)==[9,10,23]
assert sha(bpy.data.filepath)==bindings['scene_sha256']
(OUT/'water-material-binding-verification.json').write_text(json.dumps(dict(
    scene_sha256=bindings['scene_sha256'],all_binding_hashes_checked=len(bindings['bindings']),
    surfaces=rows,limitation='Saved assignments and all four authored channels verified. Native full-map import, physical water and MCC acceptance remain pending.'),indent=2)+'\n')
print('WATER_BINDINGS_VERIFIED',len(rows),'surfaces;',sum(r['faces'] for r in rows),'faces; all four channels verified.')
