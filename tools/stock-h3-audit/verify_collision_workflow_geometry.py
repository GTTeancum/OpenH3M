"""Compare compiled diagnostic render triangles and collision surfaces to source.

Reads official XML, original Blender meshes and the unmodified ASS reader. No
geometry or tag writes. This does not replace MCC collision/lighting testing.
"""
import hashlib
import json
from pathlib import Path
import runpy
import sys
import xml.etree.ElementTree as ET
import bpy
from mathutils import Vector, kdtree
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
stem='collision-workflow' if '--baseline' in sys.argv else 'collision-workflow-precise-render-only'
if '--original-render-bsp' in sys.argv:stem+='-original-render-bsp'
if '--target' in sys.argv:
    target_name=sys.argv[sys.argv.index('--target')+1]
    assert target_name.replace('_','').isalnum()
    stem+='-'+target_name
for helper in ('check_foundry.py','check_h3_exporter.py'):
    runpy.run_path(str(ROOT/'tools/stock-h3-audit'/helper))
probe=json.loads((OUT/(stem+'-probe.json')).read_text())
compiled=json.loads((OUT/(stem+'-native.json')).read_text())
source=Path(bpy.data.filepath)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert str(source)==probe['source'] and sha(source)==probe['source_sha256']
assert sha(probe['ass'])==probe['ass_sha256']==compiled['ass_sha256']
xml=OUT/(stem+'-bsp.xml')
assert sha(xml)==compiled['native_xml_sha256']
native=ET.fromstring(xml.read_text().replace('<unavailable>','&lt;unavailable&gt;'))
def field(e,name):return e.find('./field[@name="'+name+'"]').attrib['value']
def vector(e,name):return Vector(tuple(float(v) for v in field(e,name).split(',')))
definition=native.find('.//block[@name="instanced geometries definitions"]/element')
mesh_index=int(field(definition,'mesh index'))
compression_index=int(field(definition,'compression index'))
compression=next(b for b in native.findall('.//block[@name="compression info"]') if len(b)>0)[compression_index]
first=vector(compression,'position bounds 0')
second=vector(compression,'position bounds 1')
position_low=Vector((first[0],first[2],second[1]))
position_high=Vector((first[1],second[0],second[2]))
u_bounds=vector(compression,'texcoord bounds 0')
v_bounds=vector(compression,'texcoord bounds 1')
def position(element):
    p=vector(element,'position')
    return Vector(tuple(position_low[a]+p[a]*(position_high[a]-position_low[a]) for a in range(3)))
def texcoord(element):
    uv=vector(element,'texcoord')
    # Native vertex UVs use the opposite V origin from Blender/ASS, as in
    # Foundry Mesh._true_uvs; compression bounds must be applied before flipping.
    return Vector((u_bounds[0]+uv.x*(u_bounds[1]-u_bounds[0]),1-(v_bounds[0]+uv.y*(v_bounds[1]-v_bounds[0]))))
raw=next(block for block in native.findall('.//block[@name="per mesh temporary"]') if len(block)>0)[mesh_index]
vertices=list(raw.find('./block[@name="raw vertices"]'))
indices=[int(field(e,'word')) for e in raw.find('./block[@name="raw indices"]')]
from io_scene_halo.file_ass.process_file import process_file
ass=process_file(probe['ass'])
render=next(i for i in ass.instances if i.name==probe.get('render_instance','%-?boulder_low035'))
mesh=ass.objects[render.object_index]
render_triangles=mesh.triangles
if probe.get('original_render_bsp'):
    def visible(triangle):
        material=ass.materials[triangle.material_index]
        flags=next((line.split()[1] for line in material.lighting_info if line.startswith('BM_FLAGS ')),'0'*22)
        return material.name!='+seamsealer' and flags[4]=='0' and flags[5]=='0'
    render_triangles=[t for t in mesh.triangles if visible(t)]
assert len(indices)==len(render_triangles)*3
source_triangles=[]
for t in render_triangles:
    source_triangles.append([mesh.vertices[i] for i in (t.v0,t.v1,t.v2)])
centers=kdtree.KDTree(len(source_triangles))
for i,tri in enumerate(source_triangles):centers.insert(sum((Vector(v.translation)*.01 for v in tri),Vector())/3,i)
centers.balance()
used=set()
max_position=max_uv=max_normal=0.0
for offset in range(0,len(indices),3):
    triangle=[vertices[i] for i in indices[offset:offset+3]]
    positions=[position(v) for v in triangle]
    center=sum(positions,Vector())/3
    # Broad correspondence search only; the stricter acceptance check below
    # remains unchanged and reports failures instead of hiding discrepancies.
    candidates=sorted(centers.find_range(center,.05),key=lambda item:item[2])
    matched=None
    for _,index,_ in candidates:
        if index in used:continue
        original=source_triangles[index]
        for shift in range(3):
            reordered=original[shift:]+original[:shift]
            delta=max((p-Vector(v.translation)*.01).length for p,v in zip(positions,reordered))
            if delta<.05:
                matched=index,reordered,delta
                break
        if matched:break
    if matched is None:
        _,nearest,distance=centers.find(center)
        print('UNMATCHED_NATIVE_TRIANGLE',offset//3,'centroid_distance',distance,
            'native_positions',[list(p) for p in positions],
            'nearest_source_positions',[list(Vector(v.translation)*.01) for v in source_triangles[nearest]],flush=True)
        raise AssertionError(('missing oriented render triangle',offset//3))
    index,original,delta=matched
    used.add(index)
    max_position=max(max_position,delta)
    for element,v in zip(triangle,original):
        max_uv=max(max_uv,(texcoord(element)-Vector(v.uv_set[0][:2])).length)
        max_normal=max(max_normal,(vector(element,'normal')-Vector(v.normal)).length)
assert len(used)==len(render_triangles)
print('RENDER_DELTAS',max_position,max_uv,max_normal,flush=True)
native_vertices=[vector(v,'point') for v in definition.find('./block[@name="vertices"]')]
edges=list(definition.find('./block[@name="edges"]'))
surfaces=list(definition.find('./block[@name="surfaces"]'))
polygons=[]
for si,surface in enumerate(surfaces):
    start=int(field(surface,'first edge'))
    current=start
    polygon=[]
    for _ in range(len(edges)+1):
        edge=edges[current]
        if int(field(edge,'left surface'))==si:
            polygon.append(int(field(edge,'start vertex')))
            current=int(field(edge,'forward edge'))
        else:
            assert int(field(edge,'right surface'))==si
            polygon.append(int(field(edge,'end vertex')))
            current=int(field(edge,'reverse edge'))
        if current==start:break
    else:raise AssertionError('Native collision edge loop does not close')
    polygons.append(polygon)
proxy=bpy.context.scene.objects[probe.get('collision_child','@boulder_low035_collision')].data
source_vertices=[v.co*.01 for v in proxy.vertices]
source_polygons=[list(p.vertices) for p in proxy.polygons]
source_bvh=BVHTree.FromPolygons(source_vertices,source_polygons)
native_bvh=BVHTree.FromPolygons(native_vertices,polygons)
def samples(verts,faces):
    return list(verts)+[sum((verts[i] for i in face),Vector())/len(face) for face in faces]
to_source=max(source_bvh.find_nearest(p)[3] for p in samples(native_vertices,polygons))
to_native=max(native_bvh.find_nearest(p)[3] for p in samples(source_vertices,source_polygons))
mopp=definition.find('./block[@name="mopp codes"]/element/block[@name="mopp data block "]')
assert mopp is not None and len(mopp)>0
render_bsp_count=len(definition.find('./block[@name="render bsp"]'))
assert sha(source)==probe['source_sha256']
report=dict(source_sha256=probe['source_sha256'],ass_sha256=probe['ass_sha256'],
    native_tag_sha256=compiled['native_tag_sha256'],native_xml_sha256=compiled['native_xml_sha256'],
    render_triangles_matched=len(render_triangles),render_winding_preserved=True,max_render_position_delta_world_units=max_position,
    render_position_tolerance_world_units=.0001,
    max_uv_delta=max_uv,max_normal_delta=max_normal,collision_vertices=len(native_vertices),collision_surfaces=len(polygons),
    max_native_collision_sample_to_source_world_units=to_source,max_source_collision_sample_to_native_world_units=to_native,
    collision_surface_tolerance_world_units=.0001,collision_samples='All vertices and polygon centroids, both directions; not exhaustive continuous surface or gameplay testing.',
    mopp_bytes=len(mopp),render_bsp_absent_as_in_reach=render_bsp_count==0,
    checks=dict(render_position=max_position<.0001,uv=max_uv<.00001,normals=max_normal<.0001,collision_samples=max(to_source,to_native)<.0001),
    limitation='Isolated native data comparison. Broad triangle correspondence does not waive stricter failed checks. No map-wide authoring change or MCC visual, shadow, lighting or gameplay acceptance.')
if probe.get('original_render_bsp'):
    report['render_bsp_count']=render_bsp_count
    report['checks']['original_render_bsp_retained']=render_bsp_count==1
    report['zero_tangents']=sum(vector(v,'tangent').length<.01 for v in vertices)
    report['zero_binormals']=sum(vector(v,'binormal').length<.01 for v in vertices)
    report['checks']['render_tangent_space_present']=report['zero_tangents']==report['zero_binormals']==0
(OUT/(stem+'-geometry-comparison.json')).write_text(json.dumps(report,indent=2)+'\n')
print('H3_COLLISION_WORKFLOW_GEOMETRY_COMPARISON',json.dumps(report),flush=True)
raise SystemExit(0 if all(report['checks'].values()) else 1)
