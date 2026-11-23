"""Rig a source mesh onto an exact stock H3 skeleton and export an H3 JMS (General-101 exporter).

Run in background Blender with a source .blend already open (mesh + optional '#' marker objects):
  blender_env.run(this, config.json, blend=source.blend)
config keys:
  donor_xml      tool.exe export-tag-to-xml of the stock render_model whose skeleton is reproduced
  mesh_objects   names of source mesh objects to export (joined)
  offset         [x,y,z] JMS-unit translation applied to source geometry and source markers
  group_map      {source vertex group: donor node}; unmapped groups are an error
  material_map   {source material: H3 material name (shader tag name)}
  markers        {h3 marker name: {"from_object": source marker obj} | {"donor": true}}
  region, permutation  JMS region/permutation names
  out_jms, out_blend
  quat_mode      'as_is' or 'conjugate' (convention check; verified against compiled output)
Stock nodes, hierarchy and default transforms come only from donor_xml.
"""
import bpy, bmesh, json, sys
from math import radians
from mathutils import Matrix, Quaternion, Vector
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import blender_env
import kit
blender_env.enable('io_scene_halo')
from io_scene_halo.file_jms import export_jms
from io_scene_halo.global_functions import global_functions

cfg = json.loads(Path(sys.argv[sys.argv.index('--') + 1]).read_text())
xml = kit.parse_xml(cfg['donor_xml'])
if cfg.get('foundry_transform'):
    # Foundry scenes are metres / forward y-. Convert with Foundry's own transform (as in export_h3_props.py).
    blender_env.enable('io_scene_foundry')
    from io_scene_foundry import utils
    utils.transform_scene(bpy.context, 1 / .03048, utils.rotation_diff_from_forward('y-', 'x'), 'y-', 'x', actions=[])
    bpy.context.view_layer.update()
S = 100.0  # world units -> JMS units

def vec(s): return [float(x) for x in s.split(',')]
nodes = []
for e in xml.find("./block[@name='nodes']"):
    f = kit.fields(e)
    q = vec(f['default rotation'])  # i,j,k,w
    quat = Quaternion((q[3], q[0], q[1], q[2]))
    if cfg.get('quat_mode', 'as_is') == 'conjugate': quat = quat.conjugated()
    nodes.append(dict(name=f['name'], parent=int(f['parent node'].split(',')[-1]),
                      t=Vector(vec(f['default translation'])) * S, q=quat))
world = []
for n in nodes:
    local = Matrix.Translation(n['t']) @ n['q'].to_matrix().to_4x4()
    world.append(local if n['parent'] < 0 else world[n['parent']] @ local)

# Armature with bone matrices equal to the stock node world matrices.
arm_data = bpy.data.armatures.new('h3_skeleton'); arm = bpy.data.objects.new('Armature_h3', arm_data)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
for o in bpy.context.scene.objects: o.select_set(False)
arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for n, w in zip(nodes, world):
    b = arm_data.edit_bones.new(n['name']); b.head = (0, 0, 0); b.tail = (0, 1.0, 0)
    if n['parent'] >= 0: b.parent = arm_data.edit_bones[nodes[n['parent']]['name']]
    b.matrix = w
bpy.ops.object.mode_set(mode='OBJECT')

off = Vector(cfg.get('offset', [0, 0, 0]))
if cfg.get('align'):
    src_arm = bpy.data.objects[cfg['align']['source_armature']]
    src_head = src_arm.matrix_world @ src_arm.pose.bones[cfg['align']['source_bone']].head  # posed, as displayed
    dst = world[[n['name'] for n in nodes].index(cfg['align']['donor_node'])].to_translation()
    off = off + (dst - src_head)
print('ALIGN_OFFSET', [round(x, 5) for x in off], flush=True)
offset = Matrix.Translation(off)
# Copy source meshes (keeps custom normals/UVs), move them, remap vertex groups and materials, join.
copies = []
for s in [bpy.data.objects[n] for n in cfg['mesh_objects']]:
    # Use the mesh as displayed (source armature pose applied): CE gbxmodels place parts via node default pose.
    dg = bpy.context.evaluated_depsgraph_get()
    c = s.copy(); c.data = bpy.data.meshes.new_from_object(s.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    bpy.context.scene.collection.objects.link(c)
    c.parent = None; c.modifiers.clear()
    c.data.transform(offset @ s.matrix_world); c.matrix_world = Matrix.Identity(4)
    if len(c.vertex_groups) != len(s.vertex_groups): raise SystemExit('vertex groups lost on evaluation')
    for g in list(c.vertex_groups):
        if g.name not in cfg['group_map']: raise SystemExit('unmapped vertex group %s' % g.name)
    for g in list(c.vertex_groups):
        tgt = cfg['group_map'][g.name]
        if tgt == g.name: continue
        dst = c.vertex_groups.get(tgt)
        if dst is None: g.name = tgt; continue
        for v in c.data.vertices:
            for ge in v.groups:
                if ge.group == g.index: dst.add([v.index], ge.weight, 'ADD')
        c.vertex_groups.remove(g)
    for v in c.data.vertices:
        if not v.groups: raise SystemExit('unweighted vertex in %s' % s.name)
    for i, slot in enumerate(c.material_slots):
        key = slot.material.name
        if key not in cfg['material_map'] and getattr(slot.material, 'nwo', None) and slot.material.nwo.shader_path:
            key = Path(slot.material.nwo.shader_path.replace('\\', '/')).stem
        mname = cfg['material_map'][key]
        c.data.materials[i] = bpy.data.materials.get(mname) or bpy.data.materials.new(mname)
    if cfg.get('reach_face_flags') and hasattr(s.data, 'nwo'):
        # Carry Foundry two-sided faces into H3 JMS material flags (same approach as stock-h3-audit/export_h3_props.py).
        me_c = c.data; flags = [dict() for _ in me_c.polygons]
        assert len(s.data.polygons) == len(me_c.polygons)
        for prop in s.data.nwo.face_props:
            if prop.type == 'face_sides' and prop.face_sides_type == 'two_sided':
                for fi, item in enumerate(s.data.attributes[prop.attribute_name].data):
                    if item.value: flags[fi]['two_sided'] = True
        base = list(me_c.materials); variants = {}
        for face, fl in zip(me_c.polygons, flags):
            if not fl: continue
            k = (face.material_index, tuple(sorted(fl)))
            if k not in variants:
                m = base[face.material_index].copy(); m.name = base[face.material_index].name + '_2s'
                m.ass_jms.is_bm = True; m.ass_jms.two_sided = True; m.ass_jms.name_override = base[face.material_index].name + '%'
                variants[k] = len(me_c.materials); me_c.materials.append(m)
            face.material_index = variants[k]
        print('TWO_SIDED_FACES', sum(bool(f) for f in flags), flush=True)
    if cfg.get('drop_detail_close') and hasattr(s.data, 'nwo'):
        # Reach marks close-up-only detail faces (draw distance 'detail_close'); omit them from the 3rd-person model.
        import bmesh as _bm
        assert len(s.data.polygons) == len(c.data.polygons)  # evaluated copy keeps face order (armature only)
        attrs = [p.attribute_name for p in s.data.nwo.face_props if p.type == 'draw_distance' and p.draw_distance == 'detail_close']
        drop = {i for a in attrs for i, it in enumerate(s.data.attributes[a].data) if it.value}
        b = _bm.new(); b.from_mesh(c.data); b.faces.ensure_lookup_table()
        _bm.ops.delete(b, geom=[b.faces[i] for i in sorted(drop)], context='FACES'); b.to_mesh(c.data); b.free()
        print('DROPPED_DETAIL_CLOSE', len(drop), 'remaining', len(c.data.polygons), flush=True)
    if cfg.get('precise'):
        # H3 tool welds nearby points at its fixed tolerance; ')' precise keeps fine Reach-scale detail intact.
        # The H3 JMS path writes flags only as name symbols (General-101 append_material_symbols).
        for m in c.data.materials:
            m.ass_jms.is_bm = True; m.ass_jms.precise = True
            m.ass_jms.name_override = (m.ass_jms.name_override or m.name) + ')'
    copies.append(c)
for o in bpy.context.scene.objects: o.select_set(False)
for c in copies: c.select_set(True)
bpy.context.view_layer.objects.active = copies[0]
if len(copies) > 1: bpy.ops.object.join()
obj = copies[0]; obj.name = cfg.get('object_name', 'mesh'); me = obj.data
if cfg.get('region'):
    # Region/permutation must match the reused stock collision/physics model regions (General-101 region list).
    me.region_list.clear(); it = me.region_list.add(); it.name = '%s %s' % (cfg.get('permutation', 'default'), cfg['region'])
    me.active_region = 0; ra = me.get_custom_attribute()
    for i in range(len(me.polygons)): ra.data[i].value = 1
bpy.ops.object.select_all(action='DESELECT')
if cfg.get('decimate_ratio'):
    # Third-person budget: Blender's collapse decimation, applied before rigging (vertex groups are preserved).
    before = len(me.polygons)
    dec = obj.modifiers.new('Decimate', 'DECIMATE'); dec.ratio = cfg['decimate_ratio']; dec.use_collapse_triangulate = True
    for o in bpy.context.scene.objects: o.select_set(False)
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=dec.name)
    print('DECIMATED', before, '->', len(me.polygons), flush=True)
obj.parent = arm; mod = obj.modifiers.new('Armature', 'ARMATURE'); mod.object = arm
groups_out = [g.name for g in obj.vertex_groups]
mat_index = {m.name: i for i, m in enumerate(me.materials)}

# Markers ('#name' objects parented to bones).
donor_markers = {}
for e in xml.find("./block[@name='marker groups']"):
    m = e.find('block')[0]; mf = kit.fields(m)
    donor_markers[kit.fields(e)['name']] = (int(mf['node index']), Vector(vec(mf['translation'])) * S, vec(mf['rotation']))
report_markers = {}
for name, spec in cfg['markers'].items():
    ni, t, q = donor_markers[name]
    mw = world[ni] @ Matrix.Translation(t) @ Quaternion((q[3], q[0], q[1], q[2])).to_matrix().to_4x4()
    if spec.get('from_object'):
        src = bpy.data.objects[spec['from_object']]
        loc = (offset @ src.matrix_world).to_translation()
        mw = Matrix.Translation(loc) @ mw.to_quaternion().to_matrix().to_4x4()
    mk = bpy.data.objects.new('#' + name, None); mk.empty_display_type = 'ARROWS'; mk.empty_display_size = 0.5
    bpy.context.scene.collection.objects.link(mk)
    mk.parent = arm; mk.parent_type = 'BONE'; mk.parent_bone = nodes[spec.get('node', ni)]['name'] if 'node' in spec else nodes[ni]['name']
    mk.matrix_world = mw
    report_markers[name] = [round(x, 4) for x in mw.to_translation()]

# Remove everything else from the export scene.
keep = {arm, obj} | {o for o in bpy.context.scene.objects if o.name.startswith('#') and o.parent == arm}
for o in list(bpy.context.scene.objects):
    if o not in keep: bpy.data.objects.remove(o, do_unlink=True)
bpy.context.view_layer.update()
out_jms = Path(cfg['out_jms']); out_jms.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(cfg['out_blend']))
status = export_jms.write_file(context=bpy.context, filepath=str(out_jms), game_title='halo3', jms_version=8213,
    permutation_ce=cfg.get('permutation', 'default'), level_of_detail_ce='superhigh', generate_checksum=True, file_checksum=0,
    folder_structure=False, write_textures=False, hidden_geo=True, nonrender_geo=True, export_render=True,
    export_collision=False, export_physics=False, apply_modifiers=True, triangulate_faces=True,
    loop_normals=True, clean_normalize_weights=False, edge_split=global_functions.EdgeSplit(False, False, 0.0, False),
    fix_rotations=False, use_maya_sorting=False, folder_type=False, scale_value=cfg.get('scale_value', 1.0), merge_instances=False,
    report=lambda level, message: print(level, message, flush=True))
assert status == {'FINISHED'} and out_jms.is_file(), status
bounds = [v.co for v in me.vertices]
print('RIGGED_JMS', out_jms, len(me.polygons), 'faces', json.dumps(dict(materials=list(mat_index), groups=groups_out,
      markers=report_markers, min=[round(min(b[i] for b in bounds), 3) for i in range(3)],
      max=[round(max(b[i] for b in bounds), 3) for i in range(3)])), flush=True)
