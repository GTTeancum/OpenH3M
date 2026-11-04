"""Render actual imported geometry using Blender; no desktop capture/input."""
import json
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit/wip'
OUT.mkdir(exist_ok=True)
scene = bpy.context.scene
depsgraph = bpy.context.evaluated_depsgraph_get()
points = []
for instance in depsgraph.object_instances:
    ob = instance.object
    if ob.type == 'MESH' and not ob.hide_render:
        # Weight framing by surface vertices rather than distant backdrop bounds.
        points.extend(instance.matrix_world @ ob.data.vertices[i].co
                      for i in range(0, len(ob.data.vertices), max(1, len(ob.data.vertices)//2000)))
assert points
axes = [sorted(p[i] for p in points) for i in range(3)]
low = Vector(tuple(a[int(len(a)*.1)] for a in axes))
high = Vector(tuple(a[int(len(a)*.9)] for a in axes))
center = (low + high) / 2
span = max(high - low)
camera = bpy.data.objects.new('WIP proof camera', bpy.data.cameras.new('WIP proof camera'))
scene.collection.objects.link(camera)
scene.camera = camera
camera.data.type = 'ORTHO'
camera.data.clip_end = span * 10
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'SINGLE'
scene.display.shading.single_color = (0.55, 0.58, 0.61)
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.background_type = 'WORLD'
scene.world.color = (0.08, 0.08, 0.08)
scene.render.image_settings.file_format = 'PNG'
for name, direction, scale in [('overview', (1, -1, 1.3), 1.5), ('closer', (-1, -1, 1.5), 1.0)]:
    camera.location = center + Vector(direction).normalized() * span * 2
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = span * scale
    scene.render.filepath = str(OUT / (name + '.png'))
    bpy.ops.render.render(write_still=True)
(OUT / 'capture-info.json').write_text(json.dumps(dict(bounds_low=list(low), bounds_high=list(high),
    label='Original Reach geometry imported by Foundry; untextured Blender WIP, not H3 MCC'), indent=2)+'\n')
