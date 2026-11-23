"""Export a Foundry-imported Reach vehicle on its OWN Reach skeleton as H3 JMS (render/collision/physics) and its
own Reach animations as H3 JMA/JMM/JMO, with the unchanged General-101 exporters.

Run in background Blender with the Foundry source .blend (imported with animations) open.
config keys:
  name, out_dir, out_blend
  render_regions   ["region:perm"] render objects to export
  material_map     {reach shader stem: H3 shader name}
  collision_material {region: name}; physics_material
  animations       [{"name": "vehicle hover", "action": "vehicle hover", "ext": "JMM", "reverse": false}]
  lift_aim         optional {"source_jmo": path, "map": {"engine_l": "b_engine_left", "thrust_l": "b_blades_left"},
                    "name": "any any l_lift_aim"} - transfer stock H3 overlay rotations (vehicle space) onto reach pivots
Seat/effect markers keep their Reach names (the vehicle tag's seats point at them).
"""
import bpy, json, sys
from mathutils import Matrix, Quaternion, Vector
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_env
blender_env.enable('io_scene_halo', 'io_scene_foundry')
from io_scene_foundry import utils
from io_scene_halo.file_jms import export_jms
from io_scene_halo.file_jma import export_jma
from io_scene_halo.global_functions import global_functions

cfg = json.loads(Path(sys.argv[sys.argv.index('--') + 1]).read_text())
scene = bpy.context.scene
utils.transform_scene(bpy.context, 1 / .03048, utils.rotation_diff_from_forward('y-', 'x'), 'y-', 'x', actions=list(bpy.data.actions))
bpy.context.view_layer.update()
arm = next(o for o in scene.objects if o.type == 'ARMATURE')
if arm.animation_data: arm.animation_data.action = None
for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()

def mesh_copy(s):
    c = s.copy(); c.data = bpy.data.meshes.new_from_object(s.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    scene.collection.objects.link(c); c.parent = None; c.modifiers.clear(); c.animation_data_clear()
    c.data.transform(s.matrix_world); c.matrix_world = Matrix.Identity(4); return c

def set_region(c, region, perm):
    c.data.region_list.clear(); it = c.data.region_list.add(); it.name = '%s %s' % (perm, region)
    c.data.active_region = 0; a = c.data.get_custom_attribute()
    for i in range(len(c.data.polygons)): a.data[i].value = 1

sources = [o for o in list(scene.objects) if o.type == 'MESH']
render, coll, phys = [], [], []
for s in sources:
    kind = s.data.nwo.mesh_type; key = s.name.split('.')[0]
    if kind == '_connected_geometry_mesh_type_default' and key in cfg['render_regions']:
        c = mesh_copy(s); region, perm = key.split(':')
        if not c.vertex_groups:
            g = c.vertex_groups.new(name=s.parent_bone or arm.data.bones[0].name); g.add(range(len(c.data.vertices)), 1.0, 'REPLACE')
        for i, slot in enumerate(c.material_slots):
            stem = Path((slot.material.nwo.shader_path or slot.material.name).replace(chr(92), '/')).stem
            if stem not in cfg['material_map']: raise SystemExit('unmapped material %s in %s' % (stem, s.name))
            m = bpy.data.materials.get(cfg['material_map'][stem]) or bpy.data.materials.new(cfg['material_map'][stem])
            m.ass_jms.is_bm = True; m.ass_jms.name_override = cfg['material_map'][stem] + ')'
            c.data.materials[i] = m
        set_region(c, region, perm)
        c.parent = arm; mod = c.modifiers.new('Armature', 'ARMATURE'); mod.object = arm
        render.append(c)
    elif kind == '_connected_geometry_mesh_type_collision':
        parts = key.split(':')
        if parts[0] + ':' + parts[1] not in cfg['render_regions']: continue
        if (s.parent_bone or '') in cfg.get('collision_skip_bones', []): continue
        c = mesh_copy(s); bone = s.parent_bone or arm.data.bones[0].name
        c.name = '@' + key.replace(':', '_'); c.parent = arm; c.parent_type = 'BONE'; c.parent_bone = bone; c.matrix_world = Matrix.Identity(4)
        if cfg.get('seal_collision'):
            # H3 collision needs closed shells: weld coincident points and fill open boundaries (collision copy only).
            import bmesh
            b = bmesh.new(); b.from_mesh(c.data)
            bmesh.ops.remove_doubles(b, verts=b.verts, dist=0.001)
            bmesh.ops.dissolve_degenerate(b, edges=b.edges, dist=0.001)
            holes = bmesh.ops.holes_fill(b, edges=b.edges, sides=0)
            bmesh.ops.triangulate(b, faces=holes['faces'])
            opened = sum(1 for e in b.edges if not e.is_manifold)
            print('SEAL', c.name, 'non-manifold edges after sealing', opened, flush=True)
            b.to_mesh(c.data); b.free()
        set_region(c, parts[0], parts[1])
        m = bpy.data.materials.get('coll_' + parts[0]) or bpy.data.materials.new('coll_' + parts[0])
        m.ass_jms.name_override = cfg['collision_material'].get(parts[0], parts[0]); c.data.materials.clear(); c.data.materials.append(m)
        coll.append(c)
    elif kind == '_connected_geometry_mesh_type_physics':
        c = mesh_copy(s); bone = s.parent_bone or arm.data.bones[0].name
        c.name = '$' + key.lstrip('$_'); c.parent = arm; c.parent_type = 'BONE'; c.parent_bone = bone; c.matrix_world = Matrix.Identity(4)
        c.data.ass_jms.Object_Type = 'CONVEX SHAPES'
        set_region(c, cfg.get('physics_region', 'hull'), 'default')  # must match a render-model region
        m = bpy.data.materials.get('phys') or bpy.data.materials.new('phys'); m.ass_jms.name_override = cfg['physics_material']
        c.data.materials.clear(); c.data.materials.append(m); phys.append(c)
markers = []
for e in [o for o in list(scene.objects) if o.type == 'EMPTY' and o.parent == arm]:
    mk = bpy.data.objects.new('#' + e.name.split('.')[0], None); scene.collection.objects.link(mk)
    mk.parent = arm; mk.parent_type = 'BONE'; mk.parent_bone = e.parent_bone or arm.data.bones[0].name; mk.matrix_world = e.matrix_world
    markers.append(mk)
print('RENDER', sum(len(c.data.polygons) for c in render), 'faces', len(render), 'objects; COLLISION', len(coll), 'PHYSICS', len(phys), 'MARKERS', len(markers), flush=True)
keep = set(render) | set(coll) | set(phys) | set(markers) | {arm}
for o in list(scene.objects):
    if o not in keep: bpy.data.objects.remove(o, do_unlink=True)
bpy.context.view_layer.update()

out = Path(cfg['out_dir'])
def jms(kind, flags):
    d = out / kind; d.mkdir(parents=True, exist_ok=True)
    st = export_jms.write_file(context=bpy.context, filepath=str(d / (cfg['name'] + '.jms')), game_title='halo3', jms_version=8213,
        permutation_ce='default', level_of_detail_ce='superhigh', generate_checksum=True, file_checksum=0, folder_structure=False,
        write_textures=False, hidden_geo=True, nonrender_geo=True, export_render=flags[0], export_collision=flags[1], export_physics=flags[2],
        apply_modifiers=True, triangulate_faces=True, loop_normals=True, clean_normalize_weights=False,
        edge_split=global_functions.EdgeSplit(False, False, 0.0, False), fix_rotations=False, use_maya_sorting=False,
        folder_type=False, scale_value=1.0, merge_instances=False, report=lambda l, m: print(l, m, flush=True))
    print('EXPORTED', kind, st, flush=True)
jms('render', (True, False, False))
if coll: jms('collision', (False, True, False))
if phys: jms('physics', (False, False, True))

# ---- animations -------------------------------------------------------------------------------------------
anim_dir = out / 'animations'; anim_dir.mkdir(parents=True, exist_ok=True)
for o in scene.objects: o.select_set(False)
bpy.context.view_layer.objects.active = arm; arm.select_set(True)
if not arm.animation_data: arm.animation_data_create()

def action_fcurves(action):
    curves = [fc for layer in getattr(action, 'layers', []) for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
    return curves or list(getattr(action, 'fcurves', []))

def export_action(action, name, ext, frame_range=None):
    # Match each bone's rotation mode to the channels the action actually keys (Foundry keys Euler or quaternion).
    modes = {}
    for fc in action_fcurves(action):
        if fc.data_path.startswith('pose.bones["') and 'rotation' in fc.data_path:
            bone = fc.data_path.split('"')[1]
            modes[bone] = 'QUATERNION' if fc.data_path.endswith('rotation_quaternion') else ('AXIS_ANGLE' if fc.data_path.endswith('rotation_axis_angle') else 'XYZ')
    for pb in arm.pose.bones: pb.rotation_mode = modes.get(pb.name, 'QUATERNION')
    if frame_range: action.use_frame_range = True; action.frame_start, action.frame_end = frame_range
    arm.animation_data.action = action
    if action.slots: arm.animation_data.action_slot = action.slots[0]
    scene.frame_start, scene.frame_end = int(action.frame_range[0]), int(action.frame_range[1])
    print('ROTATION_MODES', name, sorted(set(modes.values())), flush=True)
    st = export_jma.write_file(bpy.context, str(anim_dir / (name + '.' + ext)), lambda l, m: print(l, m, flush=True), '.' + ext,
                               16392, 'halo3', True, 0, False, False, False, 30, 1.0)
    print('ANIM', name, ext, st, int(action.frame_range[1] - action.frame_range[0] + 1), 'frames', flush=True)

for a in cfg.get('animations', []):
    act = bpy.data.actions[a['action']]; rng = tuple(act.frame_range)
    if a.get('reverse'):
        act = act.copy(); act.name = a['action'] + ' reversed'
        lo, hi = act.frame_range
        for fc in action_fcurves(act):
            for kp in fc.keyframe_points:
                kp.co.x = lo + hi - kp.co.x; kp.handle_left.x = lo + hi - kp.handle_left.x; kp.handle_right.x = lo + hi - kp.handle_right.x
            fc.update()
    export_action(act, a['name'], a['ext'], rng)

def load_jma(path):
    t = [l.strip() for l in open(path, encoding='utf-8', errors='replace') if l.strip()]
    i = 1; frames = int(t[i]); i += 2; actors = int(t[i]); i += 1 + actors; n = int(t[i]); i += 2
    names, child, sib = [], [], []
    for _ in range(n): names.append(t[i]); child.append(int(t[i + 1])); sib.append(int(t[i + 2])); i += 3
    parent = [-1] * n
    for p in range(n):
        c = child[p]
        while c != -1: parent[c] = p; c = sib[c]
    data = []
    for _ in range(frames):
        row = []
        for _ in range(n):
            tr = Vector(map(float, t[i].split())); q = list(map(float, t[i + 1].split())); i += 3
            row.append(Matrix.Translation(tr) @ Quaternion((q[3], q[0], q[1], q[2])).conjugated().to_matrix().to_4x4())
        data.append(row)
    def world(f, k):
        m = data[f][k]; p = parent[k]
        while p != -1: m = data[f][p] @ m; p = parent[p]
        return m
    return names, frames, world

for lift in cfg.get('lift_aims', []):
    names, frames, world = load_jma(lift['source_jmo'])
    act = bpy.data.actions.new(lift['name']); arm.animation_data.action = act
    for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
    rest = {b.name: arm.data.bones[b.name].matrix_local.copy() for b in arm.pose.bones}
    order = [b for b in lift['map'].values()]  # parent first (engine then blades)
    for f in range(frames):
        for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()
        for stock, reach in lift['map'].items():
            k = names.index(stock)
            delta = (world(f, k).to_quaternion() @ world(0, k).to_quaternion().inverted()).to_matrix().to_4x4()
            pb = arm.pose.bones[reach]
            head = pb.matrix.to_translation()  # current pivot (moved by parent if already posed)
            rot = delta @ rest[reach].to_quaternion().to_matrix().to_4x4()
            pb.matrix = Matrix.Translation(head) @ rot
            bpy.context.view_layer.update()
        for pb in arm.pose.bones:
            pb.keyframe_insert('location', frame=f); pb.keyframe_insert('rotation_quaternion', frame=f); pb.keyframe_insert('scale', frame=f)
    export_action(act, lift['name'], 'JMO')
for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
arm.animation_data.action = None
bpy.ops.wm.save_as_mainfile(filepath=cfg['out_blend'])
print('DONE', sorted(p.name for p in anim_dir.iterdir()), flush=True)
