"""Verify exported visible world geometry and original collision independently."""
import collections
import gc
import hashlib
import json
from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_h3_exporter.py'))
from io_scene_halo.file_ass.process_file import process_file
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(name):return json.loads((OUT/name).read_text())
baseline=read('h3-bound-before-world-split.json')
current=read('h3-bound-ass-inspection-report.json')
collision=read('world-collision-source-probe.json')
assert sha(OUT/'h3-bound-before-world-split.ass')==baseline['ass_sha256']
assert sha(current['ass'])==current['ass_sha256']
assert sha(collision['ass'])==collision['ass_sha256']

def flag_string(material):
    return next((line.split()[1] for line in material.lighting_info if line.startswith('BM_FLAGS ')),'0'*22)
def triangle_key(triangle,geometry,material,with_lighting):
    vertices=[]
    for i in (triangle.v0,triangle.v1,triangle.v2):
        v=geometry.vertices[i]
        vertices.append((tuple(v.translation),tuple(v.normal),tuple(tuple(uv) for uv in v.uv_set),tuple(v.color)))
    rotations=[tuple(vertices[i:]+vertices[:i]) for i in range(3)]
    return material.name,min(rotations),tuple(material.lighting_info) if with_lighting else ()
def extract(path,name,mode):
    asset=process_file(str(path))
    instance=next(i for i in asset.instances if i.name==name)
    geometry=asset.objects[instance.object_index]
    counts=collections.Counter()
    for triangle in geometry.triangles:
        material=asset.materials[triangle.material_index];flags=flag_string(material)
        if mode=='old_visible' and (material.name=='+sky' or flags[4]=='1' or flags[5]=='1'):continue
        if mode=='new_visible':assert flags[3]=='1' and flags[13]=='1' and flags[21]=='0'
        if mode=='collision':assert material.name=='+sky' or flags[4]=='1' or flags[5]=='1'
        counts[triangle_key(triangle,geometry,material,mode=='collision')]+=1
    del asset;gc.collect()
    return counts
old=extract(OUT/'h3-bound-before-world-split.ass','cex_beaver_creek_structure','old_visible')
new=extract(current['ass'],'cex_beaver_creek_structure','new_visible')
assert old==new,('Visible ASS geometry differs',sum((old-new).values()),sum((new-old).values()))
visible=sum(new.values());del old,new;gc.collect()
old=extract(collision['ass'],'bc_original_world_collision_diagnostic','collision')
new=extract(current['ass'],'bc_world_collision','collision')
assert old==new,('Original collision ASS differs',sum((old-new).values()),sum((new-old).values()))
report=dict(ass_sha256=current['ass_sha256'],source_sha256=current['source_sha256'],
    baseline_ass_sha256=baseline['ass_sha256'],diagnostic_collision_ass_sha256=collision['ass_sha256'],
    visible_triangles_checked=visible,collision_triangles_checked=sum(new.values()),
    exact_visible_positions_normals_uvs_colors_winding_and_materials=True,exact_diagnosed_collision_and_material_controls=True,
    limitation='Actual ASS input equality verified; native full-map compilation, lighting and MCC acceptance remain separate gates.')
(OUT/'world-collision-ass-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('WORLD_COLLISION_ASS_VERIFIED',json.dumps(report),flush=True)
