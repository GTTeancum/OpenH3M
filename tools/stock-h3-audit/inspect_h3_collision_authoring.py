"""Inspect saved H3 collision children and separate Reach physics proxies."""
import hashlib
import json
from pathlib import Path
import runpy
import bpy
import bmesh

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
source=Path(bpy.data.filepath)
assert source==OUT/'battle-canyon-h3-authoring.blend'
before=hashlib.sha256(source.read_bytes()).hexdigest()
definitions={}
for obj in bpy.context.scene.objects:
    if obj.type=='MESH' and obj.nwo.mesh_type.endswith('_default') and not obj.name.startswith('@'):
        definitions.setdefault(obj.data,[]).append(obj)
rows=[]
collision_meshes={}
for mesh,objects in sorted(definitions.items(),key=lambda item:item[0].name):
    children=[c for o in objects for c in o.children if (c.ass_jms.name_override or c.name).startswith('@')]
    proxies=[getattr(mesh.nwo,f'proxy_physics{i}') for i in range(200) if getattr(mesh.nwo,f'proxy_physics{i}')]
    equivalent=False
    if children:
        first=children[0]
        equivalent=all(c.data==first.data and c.matrix_basis==first.matrix_basis and c.matrix_parent_inverse==first.matrix_parent_inverse for c in children)
        if first.data.name not in collision_meshes:
            bm=bmesh.new()
            bm.from_mesh(first.data)
            collision_meshes[first.data.name]=dict(vertices=len(bm.verts),faces=len(bm.faces),
                boundary_edges=sum(e.is_boundary for e in bm.edges),
                nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),
                zero_area_faces=sum(f.calc_area()<1e-12 for f in bm.faces),
                shortest_edge=min((e.calc_length() for e in bm.edges),default=0))
            bm.free()
    rows.append(dict(mesh=mesh.name,instances=[o.name for o in objects],
        collision_children=[dict(name=c.name,parent=c.parent.name,mesh=c.data.name) for c in children],
        collision_children_equivalent=equivalent,
        physics_proxies=[dict(name=p.name,vertices=len(p.data.vertices),faces=len(p.data.polygons)) for p in proxies]))
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
summary=dict(definitions=len(rows),instances=sum(len(r['instances']) for r in rows),
    collision_children=sum(len(r['collision_children']) for r in rows),
    definitions_with_collision=sum(bool(r['collision_children']) for r in rows),
    redundant_equivalent_children=sum(len(r['collision_children'])-1 for r in rows if r['collision_children_equivalent']),
    definitions_with_physics=sum(bool(r['physics_proxies']) for r in rows),
    instances_with_physics=sum(len(r['instances']) for r in rows if r['physics_proxies']))
(OUT/'h3-collision-authoring-inspection.json').write_text(json.dumps(dict(source=str(source),sha256=before,
    summary=summary,definitions=rows,collision_meshes=collision_meshes,limitation='Read-only authoring inventory. Native collision output and gameplay remain to be verified.'),indent=2)+'\n')
print('H3_COLLISION_AUTHORING_INSPECTED',json.dumps(summary),flush=True)
