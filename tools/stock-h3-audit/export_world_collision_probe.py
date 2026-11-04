"""Export original world mesh alone, optionally testing native Precise flags.

Uses the unchanged ASS exporter. Does not save or repair the authoring scene.
"""
import hashlib
import json
from pathlib import Path
import runpy
import sys
import bpy
import bmesh

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
source=Path(bpy.data.filepath)
bindings=json.loads((OUT/'h3-material-bindings.json').read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert source==Path(bindings['scene']) and sha(source)==bindings['scene_sha256']
target=bpy.context.scene.objects['cex_beaver_creek_structure']
assert target.data.name=='cluster:0'
assert len(target.data.polygons)==61874
precise='--precise' in sys.argv
portals='--portals' in sys.argv
stem='world-collision'+('-precise' if precise else '-baseline')+('-portals' if portals else '')
keep={target}
if portals:keep.update(o for o in bpy.context.scene.objects if o.type=='MESH' and o.nwo.mesh_type.endswith('_portal'))
mesh=target.data
mesh.calc_loop_triangles()
triangle_count=len(mesh.loop_triangles)
bm=bmesh.new()
bm.from_mesh(mesh)
bm.normal_update()
geometry=dict(vertices=len(bm.verts),faces=len(bm.faces),
    boundary_edges=sum(e.is_boundary for e in bm.edges),
    nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),
    zero_area_faces=[f.index for f in bm.faces if f.calc_area()<1e-12],
    inconsistent_winding_edges=sum(e.is_manifold and not e.is_contiguous for e in bm.edges))
bm.free()
materials=[dict(name=m.name,shader=m.nwo.shader_path,
    flags={p.identifier:getattr(m.ass_jms,p.identifier) for p in m.ass_jms.bl_rna.properties if p.type=='BOOLEAN'},
    faces=sum(p.material_index==i for p in mesh.polygons)) for i,m in enumerate(mesh.materials)]
for obj in list(bpy.context.scene.objects):
    if obj not in keep:bpy.data.objects.remove(obj,do_unlink=True)
if precise:
    for material in mesh.materials:
        material.ass_jms.is_bm=True
        material.ass_jms.precise=True
        material.update_tag()
    mesh.update()
    target.update_tag(refresh={'DATA'})
bpy.context.view_layer.update()
from io_scene_halo.file_ass import export_ass
from io_scene_halo.file_ass.process_file import process_file
from io_scene_halo.global_functions import global_functions
path=KIT/'data/levels/custom/bc_world_collision_probe/structure'/(stem.replace('-','_')+'.ass')
path.parent.mkdir(parents=True,exist_ok=True)
result=export_ass.write_file(bpy.context,str(path),7,'halo3',False,True,True,
    True,True,True,global_functions.EdgeSplit(False,False,0.0,False),
    False,1.0,lambda level,message:print(level,message,flush=True))
assert result=={'FINISHED'}
asset=process_file(str(path))
assert len(asset.instances)==len(keep)+1
world=next(i for i in asset.instances if i.name==(target.ass_jms.name_override or target.name))
assert len(asset.objects[world.object_index].triangles)==triangle_count
if precise:
    for material in asset.materials:
        if material.name.startswith('+portal'):continue
        flags=next(s.split()[1] for s in material.lighting_info if s.startswith('BM_FLAGS '))
        assert flags[13]=='1',(material.name,flags)
assert sha(source)==bindings['scene_sha256']
report=dict(source=str(source),source_sha256=bindings['scene_sha256'],ass=str(path),ass_sha256=sha(path),
    precise=precise,portals=len(keep)-1,geometry=geometry,triangles=triangle_count,materials=materials,
    limitation='World-only diagnostic; geometry unchanged and saved map unmodified. Native import and collision fidelity remain separate checks.')
(OUT/(stem+'-probe.json')).write_text(json.dumps(report,indent=2)+'\n')
print('WORLD_COLLISION_PROBE',stem,json.dumps(geometry),flush=True)
