"""Verify saved Foundry world collision against original official-API evidence."""
import collections
import hashlib
import json
from pathlib import Path
import runpy
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_foundry.py'))
inspection=json.loads((OUT/'world-source-collision-inspection.json').read_text())
native=json.loads((OUT/'original-world-collision.json').read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=Path(bpy.data.filepath)
assert str(source)==inspection['scene'] and sha(source)==inspection['scene_sha256']
assert sha(native['source'])==native['sha256']==inspection['original_tag_sha256']
raw=native['collision']['large collision bsp'][0]
mesh=bpy.data.objects['bc_original_world_collision_diagnostic'].data
assert len(mesh.vertices)==len(raw['vertices'])
assert all(v.co==Vector(raw['vertices'][v.index]['point'])*100 for v in mesh.vertices)
original=collections.defaultdict(list)
for index,surface in enumerate(raw['surfaces']):
    first=edge_index=surface['first edge'];vertices=[]
    while True:
        edge=raw['edges'][edge_index]
        if edge['left surface']==index:
            vertices.append(edge['start vertex']);edge_index=edge['forward edge']
        else:
            assert edge['right surface']==index
            vertices.append(edge['end vertex']);edge_index=edge['reverse edge']
        if edge_index==first:break
        assert len(vertices)<1000
    original[frozenset(vertices)].append((index,vertices))
properties={p.type:mesh.attributes[p.attribute_name] for p in mesh.nwo.face_props}
assert set(properties)=={'slip_surface','face_mode','face_sides'}
assert len(mesh.polygons)==len(original)
seen=set();paired=0
for polygon in mesh.polygons:
    key=frozenset(polygon.vertices)
    assert key not in seen
    seen.add(key)
    matches=original[key]
    if len(matches)==2:paired+=1
    index,vertices=matches[0]
    # For a two-sided pair, either original orientation represents both sides.
    actual=list(polygon.vertices)
    assert any(actual==v[shift:]+v[:shift] for _,v in matches for shift in range(len(v)))
    row=raw['surfaces'][index]
    assert bool(properties['slip_surface'].data[polygon.index].value)==row['flags']['slip']
    assert bool(properties['face_mode'].data[polygon.index].value)==row['flags']['invisible']
    assert bool(properties['face_sides'].data[polygon.index].value)==(len(matches)==2)
    material=mesh.materials[polygon.material_index]
    if row['material']<0:assert material.name=='+sky'
    else:assert material.nwo.shader_path==native['material_names'][row['material']]['render method']
assert seen==original.keys() and paired==146
report=dict(scene_sha256=inspection['scene_sha256'],original_tag_sha256=native['sha256'],
    vertices_checked=len(mesh.vertices),source_surfaces_checked=len(raw['surfaces']),
    saved_faces_checked=len(mesh.polygons),two_sided_pairs=paired,
    exact_foundry_vertex_conversion=True,polygon_winding_materials_and_flags_verified=True,
    limitation='Original source to saved Foundry collision verified. Native H3 compilation and gameplay remain separate gates.')
(OUT/'world-source-collision-saved-verification.json').write_text(json.dumps(report,indent=2)+'\n')
assert sha(source)==inspection['scene_sha256']
print('WORLD_SOURCE_COLLISION_VERIFIED',json.dumps(report),flush=True)
