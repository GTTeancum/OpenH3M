"""Rig a Foundry-imported Reach vehicle onto an exact stock H3 skeleton; export render, collision and physics JMS
with the unchanged General-101 exporter. Run in background Blender with the Foundry source .blend open.

config keys:
  donor_xml        tool.exe XML of the stock render_model whose skeleton is reproduced
  bone_map         {reach bone: donor node} for skin weights and collision/physics parenting (every used bone)
  pivot_bones      {reach bone: donor node}: parts dominated by this reach bone move so the bone's pivot sits on
                   the donor node (needed because stock animations place nodes at stock positions)
  pivot_follow     {reach bone: reach bone}: move like another bone (e.g. blades follow engine)
  render_regions   ["region:perm", ...] Foundry render objects to export (region/permutation from the name)
  collision        true -> export '@' collision objects named region:perm:n (filtered by render perms present)
  physics          true -> export '$' convex physics shapes
  material_map     {reach shader stem: H3 shader name}; collision_material {region: name}; physics_material name
  markers          {h3 marker: {"from_object": reach empty} | {} (stock position)}
  out_dir, name, out_blend
"""
import bpy, json, sys
from collections import Counter
from mathutils import Matrix, Quaternion, Vector
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_env, kit
blender_env.enable('io_scene_halo', 'io_scene_foundry')
from io_scene_foundry import utils
from io_scene_halo.file_jms import export_jms
from io_scene_halo.global_functions import global_functions

cfg = json.loads(Path(sys.argv[sys.argv.index('--') + 1]).read_text())
utils.transform_scene(bpy.context, 1 / .03048, utils.rotation_diff_from_forward('y-', 'x'), 'y-', 'x', actions=[])
bpy.context.view_layer.update()
S = 100.0
def vec(s): return [float(x) for x in s.split(',')]
xml = kit.parse_xml(cfg['donor_xml'])
nodes = []
for e in xml.find("./block[@name='nodes']"):
    f = kit.fields(e); q = vec(f['default rotation'])
    nodes.append(dict(name=f['name'], parent=int(f['parent node'].split(',')[-1]), t=Vector(vec(f['default translation'])) * S,
                      q=Quaternion((q[3], q[0], q[1], q[2]))))
world = []
for n in nodes:
    local = Matrix.Translation(n['t']) @ n['q'].to_matrix().to_4x4()
    world.append(local if n['parent'] < 0 else world[n['parent']] @ local)
W = {n['name']: w for n, w in zip(nodes, world)}

src_arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
def src_pos(bone): return src_arm.matrix_world @ src_arm.pose.bones[bone].head
offsets = {b: W[n].to_translation() - src_pos(b) for b, n in cfg.get('pivot_bones', {}).items()}
for b, lead in cfg.get('pivot_follow', {}).items(): offsets[b] = offsets[lead]
print('PIVOT_OFFSETS_WU', {b: [round(x / S, 3) for x in v] for b, v in offsets.items()}, flush=True)

arm_data = bpy.data.armatures.new('h3_skeleton'); arm = bpy.data.objects.new('Armature_h3', arm_data)
bpy.context.scene.collection.objects.link(arm)
for o in bpy.context.scene.objects: o.select_set(False)
bpy.context.view_layer.objects.active = arm; arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for n, w in zip(nodes, world):
    b = arm_data.edit_bones.new(n['name']); b.head = (0, 0, 0); b.tail = (0, 1.0, 0)
    if n['parent'] >= 0: b.parent = arm_data.edit_bones[nodes[n['parent']]['name']]
    b.matrix = w
bpy.ops.object.mode_set(mode='OBJECT')
dg = bpy.context.evaluated_depsgraph_get()

def mesh_copy(s):
    c = s.copy(); c.data = bpy.data.meshes.new_from_object(s.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    bpy.context.scene.collection.objects.link(c); c.parent = None; c.modifiers.clear()
    c.data.transform(s.matrix_world); c.matrix_world = Matrix.Identity(4); return c

def set_region(c, region, perm):
    c.data.region_list.clear(); item = c.data.region_list.add(); item.name = '%s %s' % (perm, region)
    c.data.active_region = 0
    attr = c.data.get_custom_attribute()
    for i in range(len(c.data.polygons)): attr.data[i].value = 1

render_objs = []; faces = Counter()
for s in [o for o in list(bpy.context.scene.objects) if o.type == 'MESH' and o.data.nwo.mesh_type == '_connected_geometry_mesh_type_default']:
    key = s.name.split('.')[0]
    if key not in cfg['render_regions']: continue
    region, perm = key.split(':')
    rigid_bone = s.parent_bone if s.parent_type == 'BONE' or s.parent_bone else None
    c = mesh_copy(s)
    if rigid_bone and not c.vertex_groups:  # rigidly parented part -> weight fully to that bone
        g = c.vertex_groups.new(name=rigid_bone); g.add(range(len(c.data.vertices)), 1.0, 'REPLACE')
    names = {g.index: g.name for g in c.vertex_groups}
    for v in c.data.vertices:  # pivot moves by dominant reach bone
        if not v.groups: raise SystemExit('unweighted vertex in ' + s.name)
        dom = names[max(v.groups, key=lambda x: x.weight).group]
        if dom in offsets: v.co += offsets[dom]
    for g in list(c.vertex_groups):
        if g.name not in cfg['bone_map']: raise SystemExit('unmapped bone %s in %s' % (g.name, s.name))
        tgt = cfg['bone_map'][g.name]; dst = c.vertex_groups.get(tgt)
        if tgt == g.name: continue
        if dst is None: g.name = tgt; continue
        for v in c.data.vertices:
            for ge in v.groups:
                if ge.group == g.index: dst.add([v.index], ge.weight, 'ADD')
        c.vertex_groups.remove(g)
    for i, slot in enumerate(c.material_slots):
        stem = Path((slot.material.nwo.shader_path or slot.material.name).replace(chr(92), '/')).stem
        if stem not in cfg['material_map']: raise SystemExit('unmapped material %s in %s' % (stem, s.name))
        m = bpy.data.materials.get(cfg['material_map'][stem]) or bpy.data.materials.new(cfg['material_map'][stem])
        m.ass_jms.is_bm = True; m.ass_jms.name_override = cfg['material_map'][stem] + ')'  # precise: keep fine Reach detail
        c.data.materials[i] = m
    set_region(c, region, perm)
    c.parent = arm; mod = c.modifiers.new('Armature', 'ARMATURE'); mod.object = arm
    render_objs.append(c); faces[key] = len(c.data.polygons)
print('RENDER_PARTS', dict(faces), 'total', sum(faces.values()), flush=True)

def rigid_copy(s, prefix):
    c = mesh_copy(s); bone = s.parent_bone or 'b_pedestal'
    if bone in offsets: c.data.transform(Matrix.Translation(offsets[bone]))
    tgt = cfg['bone_map'][bone]
    c.name = prefix + s.name.split('.')[0].replace(':', '_').lstrip('$_') + ('.' + s.name.split('.')[1] if '.' in s.name else '')
    c.parent = arm; c.parent_type = 'BONE'; c.parent_bone = tgt
    c.matrix_world = Matrix.Identity(4)
    return c
coll_objs, phys_objs = [], []
perms = {k.split(':')[1] for k in cfg['render_regions']}
if cfg.get('collision'):
    for s in [o for o in list(bpy.context.scene.objects) if o.type == 'MESH' and o.data.nwo.mesh_type == '_connected_geometry_mesh_type_collision']:
        parts = s.name.split('.')[0].split(':')
        if parts[1] not in perms or 'Armature_h3' in s.name: continue
        c = rigid_copy(s, '@'); set_region(c, parts[0], parts[1])
        mat = bpy.data.materials.get('coll_' + parts[0]) or bpy.data.materials.new('coll_' + parts[0])
        mat.ass_jms.name_override = cfg['collision_material'].get(parts[0], parts[0])
        c.data.materials.clear(); c.data.materials.append(mat); coll_objs.append(c)
if cfg.get('physics'):
    for s in [o for o in list(bpy.context.scene.objects) if o.type == 'MESH' and o.data.nwo.mesh_type == '_connected_geometry_mesh_type_physics']:
        if s.name.startswith(('@', '$')) and s.parent == arm: continue
        c = rigid_copy(s, '$'); c.data.ass_jms.Object_Type = 'CONVEX SHAPES'
        mat = bpy.data.materials.get('phys') or bpy.data.materials.new('phys'); mat.ass_jms.name_override = cfg['physics_material']
        c.data.materials.clear(); c.data.materials.append(mat); phys_objs.append(c)
print('COLLISION_PIECES', len(coll_objs), 'PHYSICS_SHAPES', len(phys_objs), flush=True)

donor_markers = {}
for e in xml.find("./block[@name='marker groups']"):
    m = e.find('block')[0]; mf = kit.fields(m)
    donor_markers[kit.fields(e)['name']] = (int(mf['node index']), Vector(vec(mf['translation'])) * S, vec(mf['rotation']))
for name, spec in cfg['markers'].items():
    src = bpy.data.objects.get(spec.get('from_object', '')) if spec.get('from_object') else None
    if name in donor_markers:
        ni, t, q = donor_markers[name]; mw = world[ni] @ Matrix.Translation(t) @ Quaternion((q[3], q[0], q[1], q[2])).to_matrix().to_4x4()
        node = nodes[ni]['name']
    else:
        mw = Matrix.Identity(4); node = spec.get('node', nodes[0]['name'])
    if src:
        sb = src.parent_bone or 'b_pedestal'
        mw = Matrix.Translation(src.matrix_world.to_translation() + offsets.get(sb, Vector())) @ src.matrix_world.to_quaternion().to_matrix().to_4x4()
        node = spec.get('node') or cfg['bone_map'].get(sb, node)
    mk = bpy.data.objects.new('#' + name, None); bpy.context.scene.collection.objects.link(mk)
    mk.parent = arm; mk.parent_type = 'BONE'; mk.parent_bone = node; mk.matrix_world = mw

keep = set(render_objs) | set(coll_objs) | set(phys_objs) | {arm} | {o for o in bpy.context.scene.objects if o.name.startswith('#') and o.parent == arm}
for o in list(bpy.context.scene.objects):
    if o not in keep: bpy.data.objects.remove(o, do_unlink=True)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=cfg['out_blend'])
out = Path(cfg['out_dir'])
for kind, flags in [('render', (True, False, False)), ('collision', (False, True, False)), ('physics', (False, False, True))]:
    if kind == 'collision' and not coll_objs or kind == 'physics' and not phys_objs: continue
    d = out / kind; d.mkdir(parents=True, exist_ok=True)
    st = export_jms.write_file(context=bpy.context, filepath=str(d / (cfg['name'] + '.jms')), game_title='halo3', jms_version=8213,
        permutation_ce='default', level_of_detail_ce='superhigh', generate_checksum=True, file_checksum=0, folder_structure=False,
        write_textures=False, hidden_geo=True, nonrender_geo=True, export_render=flags[0], export_collision=flags[1], export_physics=flags[2],
        apply_modifiers=True, triangulate_faces=True, loop_normals=True, clean_normalize_weights=False,
        edge_split=global_functions.EdgeSplit(False, False, 0.0, False), fix_rotations=False, use_maya_sorting=False,
        folder_type=False, scale_value=1.0, merge_instances=False, report=lambda l, m: print(l, m, flush=True))
    print('EXPORTED', kind, st, sorted(p.name for p in d.iterdir()), flush=True)
