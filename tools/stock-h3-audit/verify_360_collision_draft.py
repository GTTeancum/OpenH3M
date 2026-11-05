"""Read-only Blender check: visible world and portal-adjacent collision retained."""
import bpy,json,runpy
from array import array
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'work/stock-h3-audit'
for h in ('check_foundry.py','check_h3_exporter.py'):runpy.run_path(str(ROOT/'tools/stock-h3-audit'/h))
world=bpy.data.objects['cex_beaver_creek_structure'];collision=bpy.data.objects['bc_world_collision']
boxes=[]
for ob in bpy.context.scene.objects:
 if ob.type=='MESH' and any(m and m.ass_jms.name_override=='+portal' for m in ob.data.materials):
  ps=[ob.matrix_world@v.co for v in ob.data.vertices]
  boxes.append(([min(v[k] for v in ps)-10 for k in range(3)],[max(v[k] for v in ps)+10 for k in range(3)]))
with bpy.data.libraries.load(str(OUT/'battle-canyon-h3-materials.blend'),link=False) as (_,loaded):
 loaded.objects=['cex_beaver_creek_structure','bc_world_collision']
oldworld,oldcollision=loaded.objects
def coords(mesh):return [tuple(v.co) for v in mesh.vertices]
assert coords(world.data)==coords(oldworld.data)
assert [(tuple(p.vertices),p.material_index) for p in world.data.polygons]==[(tuple(p.vertices),p.material_index) for p in oldworld.data.polygons]
for a,b in zip(world.data.uv_layers,oldworld.data.uv_layers):assert [tuple(v.uv) for v in a.data]==[tuple(v.uv) for v in b.data]
assert set(coords(collision.data)) <= set(coords(oldcollision.data)), 'Collision vertices moved'
def key(mesh,p):return tuple(sorted(tuple(mesh.vertices[i].co) for i in p.vertices))
newfaces={key(collision.data,p) for p in collision.data.polygons}
positions=[oldcollision.matrix_world@v.co for v in oldcollision.data.vertices]
protected=missing=0;missing_faces=[]
for p in oldcollision.data.polygons:
 ps=[positions[i] for i in p.vertices];lo=[min(v[k] for v in ps) for k in range(3)];hi=[max(v[k] for v in ps) for k in range(3)]
 if oldcollision.data.materials[p.material_index].ass_jms.name_override=='+sky' or any(all(lo[k]<=b[k] and hi[k]>=a[k] for k in range(3)) for a,b in boxes):
  protected+=1
  if key(oldcollision.data,p) not in newfaces:
   missing+=1;missing_faces.append(dict(index=p.index,area=p.area,vertices=key(oldcollision.data,p)))
result=dict(visible_world_positions_faces_material_indices_and_uvs_unchanged=True,collision_vertices_all_original=True,
 portal_objects=len(boxes),protected_source_faces=protected,missing_protected_faces=missing,missing_faces=missing_faces)
(OUT/'360-collision-planar-preservation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('PLANAR_PRESERVATION',json.dumps(result),flush=True)
assert missing==0
