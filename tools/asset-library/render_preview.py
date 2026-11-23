"""Render a textured side + 3/4 preview of the export mesh in a rigged .blend (Workbench, background).

Args: <out.png> <material=texture.tif> ...   (materials matched by name with trailing JMS symbols stripped)
"""
import bpy, sys, math
from mathutils import Vector
args = sys.argv[sys.argv.index('--') + 1:]
out = args[0]; texmap = dict(a.split('=', 1) for a in args[1:])
scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type == 'MESH' and not o.name.startswith(('#', '@', '$'))
          and (':' not in o.name or o.name.split('.')[0].endswith((':default',)))
          and not (hasattr(o.data, 'nwo') and o.data.nwo.mesh_type not in ('', '_connected_geometry_mesh_type_default'))]
for o in scene.objects:
    if o.type == 'MESH' and o not in meshes: o.hide_render = True
for o in meshes:
    o.hide_render = False; o.hide_set(False); o.hide_viewport = False
    for col in o.users_collection: col.hide_render = False
for o in meshes:
    for m in o.data.materials:
        key = (m.ass_jms.name_override if hasattr(m, 'ass_jms') and m.ass_jms.name_override else m.name).rstrip('%)#')
        m.use_nodes = True; nt = m.node_tree
        bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None) or nt.nodes.new('ShaderNodeBsdfPrincipled')
        if key in texmap:
            img = bpy.data.images.load(texmap[key]); img.alpha_mode = 'NONE'; tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img
            nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        else:
            bsdf.inputs['Base Color'].default_value = (1, 0, 1, 1)  # unmapped = magenta
dg_ = bpy.context.evaluated_depsgraph_get()
pts = [o.evaluated_get(dg_).matrix_world @ v.co for o in meshes for v in o.evaluated_get(dg_).to_mesh().vertices]
lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
center = (lo + hi) / 2; size = max(hi - lo)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'; scene.display.shading.color_type = 'TEXTURE' if texmap else 'SINGLE'
scene.render.resolution_x, scene.render.resolution_y = 1000, 1000
scene.render.film_transparent = False
world = bpy.data.worlds.new('w'); scene.world = world; world.color = (0.35, 0.35, 0.38)
cam_data = bpy.data.cameras.new('cam'); cam_data.type = 'ORTHO'; cam_data.ortho_scale = size * 1.15; cam_data.clip_end = size * 10
cam = bpy.data.objects.new('cam', cam_data); scene.collection.objects.link(cam); scene.camera = cam
views = {'side': (Vector((0, -1, 0)), 'Y'), 'three_quarter': (Vector((0.6, -1, 0.5)).normalized(), 'Y'), 'front': (Vector((-1, 0, 0.15)).normalized(), 'Y')}
for name, (d, _) in views.items():
    cam.location = center - d * size * 3
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = out.replace('.png', '-%s.png' % name)
    bpy.ops.render.render(write_still=True)
    print('PREVIEW', scene.render.filepath, flush=True)
