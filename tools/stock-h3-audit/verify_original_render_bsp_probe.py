"""Compare original and official H3 render-BSP collision by material and flags."""
import collections
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit';KIT=ROOT/'work/editing-kits/h3ek'
stem='collision-workflow-precise-render-only-original-render-bsp-teleporter_trimlowside003'
def read(name):return json.loads((OUT/name).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
source=read('original-instance-collision-53.json');probe=read(stem+'-probe.json');compiled=read(stem+'-native.json')
bindings=read('h3-material-bindings.json')
assert sha(source['source'])==source['sha256']==probe['original_render_bsp']['source_tag_sha256']
assert sha(probe['ass'])==probe['ass_sha256']==compiled['ass_sha256']
xml=OUT/(stem+'-bsp.xml');assert sha(xml)==compiled['native_xml_sha256']
assert not any('ERROR' in s or 'FATAL' in s or 'untextured' in s for s in compiled['issue_lines'])
native=ET.fromstring(xml.read_text().replace('<unavailable>','&lt;unavailable&gt;'))
def field(e,name):return e.find('./field[@name="'+name+'"]').attrib['value']
definition=native.find('.//block[@name="instanced geometries definitions"]/element')
assert len(definition.find('./block[@name="render bsp"]'))==1
block=definition.find('./block[@name="render bsp"]/element')
actual={name:[{f.attrib['name']:f.attrib['value'] for f in e.findall('./field')} for e in block.find('./block[@name="'+name+'"]')]
        for name in ('vertices','edges','surfaces')}
for row in actual['vertices']:row['point']=[float(v) for v in row['point'].split(',')]
for name in ('edges','surfaces'):
    for row in actual[name]:
        for key,value in row.items():row[key]=int(value)
raw=source['render_bsp'][0]
def polygons(data):
    result=[]
    for index,surface in enumerate(data['surfaces']):
        start=current=surface['first edge'];vertices=[]
        for _ in range(len(data['edges'])+1):
            edge=data['edges'][current]
            if edge['left surface']==index:vertices.append(edge['start vertex']);current=edge['forward edge']
            else:
                assert edge['right surface']==index
                vertices.append(edge['end vertex']);current=edge['reverse edge']
            if current==start:break
        else:raise AssertionError('Collision loop did not close')
        result.append(vertices)
    return result
source_vertices=[Vector(v['point']) for v in raw['vertices']]
native_vertices=[Vector(v['point']) for v in actual['vertices']]
source_faces=polygons(raw);native_faces=polygons(actual)
source_groups=collections.defaultdict(list);native_groups=collections.defaultdict(list)
material_block=native.find('./block[@name="collision materials"]')
for face,surface in zip(source_faces,raw['surfaces']):
    assert not any(v for k,v in surface['flags'].items() if k!='plane negated')
    material=surface['material']
    if material<0:key='+seamsealer'
    else:
        shader=source['materials'][str(material)]['render method'];binding=bindings['bindings'][shader]
        key=str(Path(binding['export_tag']).relative_to(KIT/'tags').with_suffix(''))
        assert sha(binding['export_tag'])==binding['sha256']
    source_groups[key].append(face)
for face,surface in zip(native_faces,actual['surfaces']):
    assert surface['flags']==0
    material=surface['material']
    key='+seamsealer' if material<0 else field(material_block[material],'render method').split(',')[0]
    native_groups[key].append(face)
assert source_groups.keys()==native_groups.keys()
def samples(vertices,faces):
    return [vertices[i] for i in sorted({i for f in faces for i in f})]+[sum((vertices[i] for i in f),Vector())/len(f) for f in faces]
rows=[]
for material,faces in source_groups.items():
    other=native_groups[material]
    a=BVHTree.FromPolygons(source_vertices,faces);b=BVHTree.FromPolygons(native_vertices,other)
    rows.append(dict(material=material,source_faces=len(faces),native_faces=len(other),
        source_to_native=max(b.find_nearest(p)[3] for p in samples(source_vertices,faces)),
        native_to_source=max(a.find_nearest(p)[3] for p in samples(native_vertices,other))))
boundary=sum(e['left surface']<0 or e['right surface']<0 for e in actual['edges'])
assert boundary==0
passed=all(max(r['source_to_native'],r['native_to_source'])<.0001 for r in rows)
report=dict(source_tag_sha256=source['sha256'],ass_sha256=probe['ass_sha256'],native_tag_sha256=compiled['native_tag_sha256'],
    source_vertices=len(source_vertices),native_vertices=len(native_vertices),source_surfaces=len(source_faces),native_surfaces=len(native_faces),
    native_boundary_edges=boundary,physical_flags_match=True,material_groups=rows,within_sample_tolerance=passed,
    limitation='All vertices and polygon centroids compared within matching shader groups; not continuous-surface equivalence, MCC traversal or final appearance.')
(OUT/'original-render-bsp-native-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print('ORIGINAL_RENDER_BSP_NATIVE_COMPARISON',json.dumps(report),flush=True)
raise SystemExit(0 if passed else 1)
