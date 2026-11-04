"""Native Blender proof: source ASS render mesh beside official H3 output.

Neutral diagnostic shading, not a material or MCC appearance claim.
"""
import hashlib
import json
from pathlib import Path
import runpy
import sys
import xml.etree.ElementTree as ET
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'
runpy.run_path(str(ROOT/'tools/stock-h3-audit/check_h3_exporter.py'))
stem='collision-workflow-precise-render-only'
target=sys.argv[sys.argv.index('--target')+1] if '--target' in sys.argv else None
if target:
    assert target.replace('_','').isalnum()
    stem+='-'+target
probe=json.loads((OUT/(stem+'-probe.json')).read_text())
comparison=json.loads((OUT/(stem+'-geometry-comparison.json')).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert sha(probe['ass'])==comparison['ass_sha256']
xml=OUT/(stem+'-bsp.xml')
assert sha(xml)==comparison['native_xml_sha256']
from io_scene_halo.file_ass.process_file import process_file
ass=process_file(probe['ass'])
instance=next(i for i in ass.instances if i.name==probe.get('render_instance','%-?boulder_low035'))
source=ass.objects[instance.object_index]
native=ET.fromstring(xml.read_text().replace('<unavailable>','&lt;unavailable&gt;'))
def field(e,name):return e.find('./field[@name="'+name+'"]').attrib['value']
def vector(e,name):return tuple(float(v) for v in field(e,name).split(','))
definition=native.find('.//block[@name="instanced geometries definitions"]/element')
compression=next(b for b in native.findall('.//block[@name="compression info"]') if len(b)>0)[int(field(definition,'compression index'))]
first=vector(compression,'position bounds 0')
second=vector(compression,'position bounds 1')
low=(first[0],first[2],second[1])
high=(first[1],second[0],second[2])
raw=next(b for b in native.findall('.//block[@name="per mesh temporary"]') if len(b)>0)[int(field(definition,'mesh index'))]
native_vertices=list(raw.find('./block[@name="raw vertices"]'))
positions=[tuple(low[a]+vector(v,'position')[a]*(high[a]-low[a]) for a in range(3)) for v in native_vertices]
indices=[int(field(e,'word')) for e in raw.find('./block[@name="raw indices"]')]
scene=bpy.data.scenes.new('Native geometry comparison')
bpy.context.window.scene=scene
source_positions=[Vector(v.translation)*.01 for v in source.vertices]
low=Vector(tuple(min(v[a] for v in source_positions) for a in range(3)))
high=Vector(tuple(max(v[a] for v in source_positions) for a in range(3)))
center=(low+high)/2
span=max(high-low)
for name,verts,faces,normals,offset in [
    ('Original source', [tuple(Vector(v.translation)*.01) for v in source.vertices],[(t.v0,t.v1,t.v2) for t in source.triangles],[tuple(v.normal) for v in source.vertices],-1.25),
    ('Official H3 output',positions,[indices[i:i+3] for i in range(0,len(indices),3)],[vector(v,'normal') for v in native_vertices],1.25)]:
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    for polygon in mesh.polygons:polygon.use_smooth=True
    mesh.normals_split_custom_set_from_vertices(normals)
    obj=bpy.data.objects.new(name,mesh)
    scene.collection.objects.link(obj)
    obj.location.x=offset
    if target:obj.location=Vector(((-.7 if offset<0 else .7)*span,0,0))-center
    obj.color=(.55,.58,.62,1)
camera=bpy.data.objects.new('Proof camera',bpy.data.cameras.new('Proof camera'))
scene.collection.objects.link(camera)
camera.location=(0,-7,4)
camera.rotation_euler=(-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO'
camera.data.ortho_scale=5.0
if target:camera.data.ortho_scale=span*3.3
scene.camera=camera
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO'
scene.display.shading.color_type='OBJECT'
scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True
scene.display.shading.background_type='WORLD'
scene.world=bpy.data.worlds.new('Proof world')
scene.world.color=(.035,.035,.035)
scene.render.resolution_x=1600
scene.render.resolution_y=800
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
image=OUT/('wip/h3-boulder-native-geometry-comparison'+('-'+target if target else '')+'.png')
scene.render.filepath=str(image)
bpy.ops.render.render(write_still=True)
assert sha(probe['ass'])==comparison['ass_sha256'] and sha(xml)==comparison['native_xml_sha256']
image.with_suffix('.json').write_text(json.dumps(dict(
    image=str(image),source_ass_sha256=comparison['ass_sha256'],native_xml_sha256=comparison['native_xml_sha256'],
    left='Original source render mesh',right='Official H3 compiled render mesh with precise/render-only authoring flags',
    limitation='Native Blender geometry comparison with neutral shading. Not actual materials, baked lighting or MCC; strict position/normal checks remain open.'),indent=2)+'\n')
print('H3_BOULDER_NATIVE_PROOF',str(image),flush=True)
