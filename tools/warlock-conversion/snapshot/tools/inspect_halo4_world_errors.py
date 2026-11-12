"""Locate official Tool's text diagnostics on the unchanged source geometry.

Reuses tools/stock-h3-audit/inspect_world_collision_errors.py's WRL diagnostic
and Blender KD-tree method. This is not an asset converter or mesh repair.
"""
from pathlib import Path
import json
import re
import sys
import bpy
import bmesh
from mathutils import Vector, kdtree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from halo4_blender_context import ROOT, OUT, setup, sha

source=OUT/'h3-authoring/haven-h3-authoring.blend'
before=sha(source)
scene=setup(source=source)
obj=scene.objects['structure_collision']
mesh=obj.data
tree=kdtree.KDTree(len(mesh.vertices))
for vertex in mesh.vertices:tree.insert(obj.matrix_world@vertex.co,vertex.index)
tree.balance()
bm=bmesh.new();bm.from_mesh(mesh)
bm.verts.ensure_lookup_table();bm.edges.ensure_lookup_table();bm.faces.ensure_lookup_table()
bm.verts.index_update();bm.edges.index_update();bm.faces.index_update()
path=ROOT/'work/editing-kits/h3ek/import_errors/haven_geometry_probe_world_scaled.wrl'
edges=[];face_ids=set()
for part in path.read_text().split('geometry DEF ')[1:]:
    label=re.match(r'"([^"]+)"',part).group(1)
    match=re.search(r'\bpoint\s*\[([^]]+)\]',part)
    if not match:continue
    numbers=list(map(float,re.findall(r'[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?',match[1])))
    assert len(numbers)==6 and label=='open edge'
    indices=[];points=[]
    for i in (0,3):
        position=Vector(numbers[i:i+3]);_,index,distance=tree.find(position)
        indices.append(index)
        nearest=tree.find_n(position,2)
        points.append(dict(position=list(position),vertex=index,distance=distance,
            second_nearest_distance=nearest[1][2]))
    edge=bm.edges.get((bm.verts[indices[0]],bm.verts[indices[1]]))
    adjacent=[f.index for f in edge.link_faces] if edge else []
    face_ids.update(adjacent)
    edges.append(dict(label=label,points=points,source_edge=edge.index if edge else None,
        boundary=edge.is_boundary if edge else None,adjacent_faces=adjacent))
faces=[]
for index in sorted(face_ids):
    face=bm.faces[index]
    faces.append(dict(index=index,vertices=[v.index for v in face.verts],
        positions=[list(obj.matrix_world@v.co) for v in face.verts],
        original_area=face.calc_area(),normal=list(face.normal)))
report=dict(source=str(source),source_sha256=before,source_unchanged=sha(source)==before,
    diagnostic=str(path.relative_to(ROOT)),diagnostic_sha256=sha(path),
    source_polygons=len(mesh.polygons),source_boundary_edges=sum(e.is_boundary for e in bm.edges),
    source_nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),
    reported_edges=edges,adjacent_source_faces=faces,
    limitation='Locates native error edges on source geometry; no repair or source omission is accepted.')
assert report['source_unchanged']
bm.free()
(OUT/'haven-world-error-locations.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('H4_WORLD_EDGE_LOCATIONS',json.dumps(dict(source_boundary_edges=report['source_boundary_edges'],
    source_nonmanifold_edges=report['source_nonmanifold_edges'],reported_edges=edges,adjacent_faces=len(faces))),flush=True)
