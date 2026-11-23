"""Preview a vehicle with its turret child objects attached the way the model variant attaches them (child marker on
parent marker), for one damage permutation set. Workbench render in background Blender (run via blender_env).

Args (after --): <config.json>  {parent_blend, perms: {region: perm}, children: [{blend, parent_marker, child_marker,
                 perms}], textures: {material: tif}, out}
Meshes come from the '-own.blend' scenes written by build_vehicle_own.py (exactly what was exported to JMS).
"""
import bpy, json, sys
from mathutils import Matrix, Vector
cfg = json.loads(open(sys.argv[sys.argv.index('--') + 1]).read())
scene = bpy.context.scene

def region_perm(o):
    key = o.name.split('.')[0]  # render copies keep the Foundry 'region:permutation' object name
    if key[:1] in '@$#' or ':' not in key: return None, None
    region, perm = key.split(':')[:2]; return region, perm

def visible(o, perms):
    r, p = region_perm(o)
    return r is not None and perms.get(r, 'default') == p

def marker(objs, name):
    return next(o for o in objs if o.type == 'EMPTY' and o.name.split('.')[0] == '#' + name)

parent_objs = list(scene.objects)
for ch in cfg['children']:
    with bpy.data.libraries.load(ch['blend']) as (src, dst):
        dst.objects = list(src.objects)
    new = [o for o in dst.objects if o]
    for o in new: scene.collection.objects.link(o)
    root = Matrix.Identity(4)
    pm = marker(parent_objs, ch['parent_marker']).matrix_world
    cm = marker(new, ch['child_marker']).matrix_world if ch.get('child_marker') else Matrix.Identity(4)
    xf = pm @ cm.inverted()
    for o in new:
        if o.parent is None: o.matrix_world = xf @ o.matrix_world
    ch['objs'] = new
bpy.context.view_layer.update()
show = [o for o in parent_objs if o.type == 'MESH' and visible(o, cfg['perms'])]
for ch in cfg['children']:
    show += [o for o in ch['objs'] if o.type == 'MESH' and visible(o, ch.get('perms', {}))]
for o in scene.objects:
    if o.type == 'MESH': o.hide_render = o not in show
for o in show:
    for m in o.data.materials:
        if not m: continue
        key = m.name.split('.')[0].rstrip('%)#')  # build_vehicle_own names materials after the H3 shader
        m.use_nodes = True; nt = m.node_tree
        bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None) or nt.nodes.new('ShaderNodeBsdfPrincipled')
        if key in cfg['textures']:
            img = bpy.data.images.load(cfg['textures'][key]); img.alpha_mode = 'NONE'
            tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img; nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        else:
            bsdf.inputs['Base Color'].default_value = (0.25, 0.25, 0.25, 1) if 'damage' in key else (1, 0, 1, 1)
dg = bpy.context.evaluated_depsgraph_get()
pts = [o.evaluated_get(dg).matrix_world @ v.co for o in show for v in o.evaluated_get(dg).to_mesh().vertices]
lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
center = (lo + hi) / 2; size = max(hi - lo)
scene.render.engine = 'BLENDER_WORKBENCH'; scene.display.shading.light = 'STUDIO'; scene.display.shading.color_type = 'TEXTURE'
scene.render.resolution_x, scene.render.resolution_y = 900, 900
world = bpy.data.worlds.new('w'); scene.world = world; world.color = (0.35, 0.35, 0.38)
cd = bpy.data.cameras.new('cam'); cd.type = 'ORTHO'; cd.ortho_scale = size * 1.1; cd.clip_end = size * 10
cam = bpy.data.objects.new('cam', cd); scene.collection.objects.link(cam); scene.camera = cam
for name, d in {'three_quarter': Vector((0.6, -1, 0.45)), 'front': Vector((-1, 0, 0.2)), 'rear_quarter': Vector((-0.7, 0.9, 0.45))}.items():
    d = d.normalized(); cam.location = center - d * size * 3
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = cfg['out'].replace('.png', '-%s.png' % name); bpy.ops.render.render(write_still=True)
    print('PREVIEW', scene.render.filepath, flush=True)
