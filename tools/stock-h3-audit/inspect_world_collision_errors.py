"""Locate official Tool's world-only errors on unchanged Blender source faces."""
import collections
import hashlib
import json
from pathlib import Path
import re
import runpy
import sys
import bpy
from mathutils import Vector,kdtree

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
stem='world-collision-precise'+('' if '--no-portals' in sys.argv else '-portals')
probe=json.loads((OUT/(stem+'-probe.json')).read_text())
native=json.loads((OUT/(stem+'-native.json')).read_text())
source=Path(bpy.data.filepath)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(source)==probe['source_sha256'] and native['ass_sha256']==probe['ass_sha256']==sha(probe['ass'])
assert native['returncode']==0
error=KIT/'import_errors'/('bc_world_collision_probe_'+Path(probe['ass']).stem+'.wrl')
text=error.read_text()
obj=bpy.context.scene.objects['cex_beaver_creek_structure']
mesh=obj.data
tree=kdtree.KDTree(len(mesh.vertices))
for v in mesh.vertices:tree.insert(obj.matrix_world@v.co,v.index)
tree.balance()
adjacent=collections.defaultdict(list)
for face in mesh.polygons:
    for i in face.vertices:adjacent[i].append(face.index)
blocks=[]
for part in text.split('geometry DEF ')[1:]:
    label=re.match(r'"([^"]+)"',part).group(1)
    match=re.search(r'\bpoint\s*\[([^]]+)\]',part)
    if not match:continue
    numbers=[float(n) for n in re.findall(r'[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?',match[1])]
    assert len(numbers)%3==0
    points=[]
    for i in range(0,len(numbers),3):
        point=Vector(numbers[i:i+3])
        _,index,distance=tree.find(point)
        points.append(dict(position=list(point),nearest_vertex=index,distance=distance,adjacent_faces=adjacent[index]))
    blocks.append(dict(label=label,points=points))
faces={i for b in blocks for p in b['points'] for i in p['adjacent_faces'] if p['distance']<.001}
details=[]
for i in sorted(faces):
    face=mesh.polygons[i]
    material=mesh.materials[face.material_index]
    details.append(dict(index=i,vertices=list(face.vertices),area=face.area,material=material.name,
        shader=material.nwo.shader_path,flags={p.identifier:getattr(material.ass_jms,p.identifier)
            for p in material.ass_jms.bl_rna.properties if p.type=='BOOLEAN'},
        source_properties=[dict(type=p.type,attribute=p.attribute_name) for p in mesh.nwo.face_props
            if mesh.attributes[p.attribute_name].data[i].value]))
report=dict(source_sha256=probe['source_sha256'],ass_sha256=probe['ass_sha256'],error_sha256=sha(error),
    errors=blocks,nearby_faces=details,
    limitation='Nearest original vertices/faces locate native diagnostics; proximity alone does not establish a repair or authorize changing geometry.')
(OUT/(stem+'-error-locations.json')).write_text(json.dumps(report,indent=2)+'\n')
assert sha(source)==probe['source_sha256']
print('WORLD_COLLISION_ERROR_LOCATIONS',json.dumps([dict(label=b['label'],points=len(b['points']),
    near_vertices=sum(p['distance']<.001 for p in b['points'])) for b in blocks]),'nearby faces',len(details),flush=True)
