"""Locate the remaining diagnostic error triangle in original Reach collision."""
import hashlib
import json
from pathlib import Path
import re
import runpy
import bpy
from mathutils import Vector, kdtree

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_foundry.py'))
source=json.loads((OUT/'original-instance-collision-418.json').read_text())
assert hashlib.sha256(Path(source['source']).read_bytes()).hexdigest()==source['sha256']
proxy=bpy.context.scene.objects['@boulder_west_lowz002_collision']
bpy.context.view_layer.update()
tree=kdtree.KDTree(len(proxy.data.vertices))
for v in proxy.data.vertices:tree.insert(proxy.matrix_world@v.co,v.index)
tree.balance()
wrl=ROOT/'work/editing-kits/h3ek/import_errors/bc_collision_workflow_probe_boulder_precise_render_only_boulder_west_lowz002.wrl'
matches=[]
for coordinates in re.findall(r'\bpoint\s*\[([^]]+)\]',wrl.read_text()):
    values=[float(x) for x in re.findall(r'[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?',coordinates)]
    for i in range(0,len(values),3):
        point=Vector(values[i:i+3]);_,index,distance=tree.find(point)
        matches.append(dict(point=list(point),vertex=index,distance=distance))
indices={m['vertex'] for m in matches}
assert len(indices)==3
faces=[]
edges=source['collision']['edges']
assert len(proxy.data.polygons)==len(source['collision']['surfaces'])
for poly in proxy.data.polygons:
    original=source['collision']['surfaces'][poly.index]
    start=original['first edge'];edge_index=start;vertices=[]
    for _ in range(len(edges)+1):
        edge=edges[edge_index]
        if edge['left surface']==poly.index:
            vertices.append(edge['start vertex']);edge_index=edge['forward edge']
        else:
            assert edge['right surface']==poly.index
            vertices.append(edge['end vertex']);edge_index=edge['reverse edge']
        if edge_index==start:break
    else:raise AssertionError('Original collision loop does not close')
    assert set(vertices)==set(poly.vertices),(poly.index,vertices,list(poly.vertices))
    overlap=indices&set(poly.vertices)
    if len(overlap)>=2:
        plane=source['collision']['planes'][original['plane index']]['plane']
        faces.append(dict(index=poly.index,vertices=list(poly.vertices),error_vertex_overlap=sorted(overlap),
            material=proxy.data.materials[poly.material_index].nwo.shader_path,
            original_plane=plane,original_plane_max_vertex_distance=max(abs(Vector(plane[:3]).dot(Vector(source['collision']['vertices'][i]['point']))-plane[3]) for i in vertices),
            original_surface=source['collision']['surfaces'][poly.index]))
source_vertices=source['collision']['vertices']
assert len(source_vertices)==len(proxy.data.vertices)
vertex_deltas=[(Vector(source_vertices[i]['point'])*100-proxy.data.vertices[i].co).length for i in range(len(source_vertices))]
report=dict(source_sha256=source['sha256'],error_sha256=hashlib.sha256(wrl.read_bytes()).hexdigest(),
    error_endpoints=matches,error_vertices=sorted(indices),adjacent_faces=faces,
    maximum_vertex_delta_authoring_units=max(vertex_deltas),
    limitation='Original/source endpoint and neighboring-face diagnosis only; does not authorize deletion or remeshing.')
(OUT/'west-boulder-error-faces.json').write_text(json.dumps(report,indent=2)+'\n')
print('WEST_BOULDER_ERROR_FACES',json.dumps(report),flush=True)
