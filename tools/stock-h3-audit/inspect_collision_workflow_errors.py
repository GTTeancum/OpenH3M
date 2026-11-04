"""Locate native Tool's diagnostic edges against original authoring meshes."""
import collections
import hashlib
import json
from pathlib import Path
import re
import runpy
import xml.etree.ElementTree as ET
import bpy
from mathutils import Vector, kdtree

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
KIT=ROOT/'work/editing-kits/h3ek'
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
probe=json.loads((OUT/'collision-workflow-probe.json').read_text())
assert hashlib.sha256(Path(probe['ass']).read_bytes()).hexdigest()==probe['ass_sha256']
source=Path(bpy.data.filepath)
assert str(source)==probe['source']
assert hashlib.sha256(source.read_bytes()).hexdigest()==probe['source_sha256']
error=KIT/'import_errors/bc_collision_workflow_probe_boulder.wrl'
text=error.read_text()
blocks=[]
for part in text.split('geometry DEF ')[1:]:
    label=re.match(r'"([^"]+)"',part).group(1)
    match=re.search(r'\bpoint\s*\[([^]]+)\]',part)
    if not match:continue
    numbers=[float(n) for n in re.findall(r'[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?',match[1])]
    assert len(numbers)%3==0
    blocks.append((label,[Vector(numbers[i:i+3]) for i in range(0,len(numbers),3)]))
bpy.context.view_layer.update()
from io_scene_halo.global_functions.mesh_processing import append_material_symbols
meshes={}
for row in probe['geometry']:
    obj=bpy.context.scene.objects[row['name']]
    data=dict(material_faces=dict(collections.Counter(append_material_symbols(obj.data.materials[p.material_index],'halo3',True) for p in obj.data.polygons)))
    for space in ('local','world'):
        tree=kdtree.KDTree(len(obj.data.vertices))
        for v in obj.data.vertices:tree.insert(obj.matrix_world @ v.co if space=='world' else v.co,v.index)
        tree.balance()
        by_label=collections.defaultdict(list)
        for label,points in blocks:by_label[label].extend(tree.find(p)[2] for p in points)
        data[space]={label:dict(points=len(ds),within_001=sum(d<.001 for d in ds),maximum_distance=max(ds),mean_distance=sum(ds)/len(ds)) for label,ds in by_label.items()}
    meshes[obj.name]=data
xml=OUT/'collision-workflow-bsp.xml'
native=ET.fromstring(xml.read_text().replace('<unavailable>','&lt;unavailable&gt;'))
definition=native.find('.//block[@name="instanced geometries definitions"]/element')
assert definition is not None
native_geometry={}
def field(e,name):return e.find('./field[@name="'+name+'"]').attrib['value']
for name,element in [('collision',definition),('render_bsp',definition.find('./block[@name="render bsp"]/element'))]:
    vertices=element.find('./block[@name="vertices"]')
    edges=element.find('./block[@name="edges"]')
    surfaces=element.find('./block[@name="surfaces"]')
    row=dict(vertices=len(vertices),edges=len(edges),surfaces=len(surfaces),
        boundary_edges=sum(int(field(e,'left surface'))<0 or int(field(e,'right surface'))<0 for e in edges))
    if name=='collision':
        proxy=bpy.context.scene.objects['@boulder_low035_collision']
        tree=kdtree.KDTree(len(proxy.data.vertices))
        for v in proxy.data.vertices:tree.insert(v.co*.01,v.index)
        tree.balance()
        distances=[tree.find(Vector(tuple(float(x) for x in field(v,'point').split(','))))[2] for v in vertices]
        row['maximum_distance_to_source_proxy_world_units']=max(distances)
        row['all_source_proxy_vertices_retained']=len(vertices)==len(proxy.data.vertices) and max(distances)<.00001
    native_geometry[name]=row
report=dict(source_sha256=probe['source_sha256'],ass_sha256=probe['ass_sha256'],
    native_error_sha256=hashlib.sha256(error.read_bytes()).hexdigest(),meshes=meshes,
    native_bsp_xml_sha256=hashlib.sha256(xml.read_bytes()).hexdigest(),native_geometry=native_geometry,
    limitation='Endpoint proximity identifies which authored surface matches an error; it does not establish the cause or authorize a geometry change.')
assert hashlib.sha256(source.read_bytes()).hexdigest()==probe['source_sha256']
(OUT/'collision-workflow-error-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
print('H3_COLLISION_ERROR_LOCATIONS',json.dumps(report),flush=True)
