"""Inside Blender: translate Foundry's Reach markings on Reflection into the H3 ASS authoring controls of the unchanged
General-101 exporter, then export one H3 ASS per BSP. Same translation as Battle Canyon's
tools/stock-h3-audit/prepare_h3_authoring_scene.py (Foundry transform back to Max units/axes; instance policy
symbols; proxy collision as a local '@' collision child; per-face Foundry face modes as H3 material flags).
No geometry is rebuilt. Usage (launch.py): prepare_h3_scene.py -- <bsp-suffix e.g. 030>"""
import collections, hashlib, json, sys, traceback
from pathlib import Path
import bpy
from mathutils import Matrix

OLD = Path(r'C:\X360\ISOs\H3M\.local\OpenH3M-source\work')
OUT = Path(r'C:\Programming\GitHub\OpenH3M\.local\reflection-rebuild')
KIT = Path(r'C:\Programming\GitHub\OpenH3M\.local\asset-kit-hrek')
SOURCE = OUT / 'reflection-reach-source.blend'
BSP = sys.argv[sys.argv.index('--') + 1]
sys.path.insert(0, str(OLD / 'halo4-to-h3/python-packages-313'))
sys.path.insert(0, str(OLD / 'halo4-to-h3/upstream/Foundry-1.9.19'))
sys.path.insert(0, str(OLD / 'stock-h3-audit/upstream/Halo-Asset-Blender-Development-Toolset-81e86bf98aee4607a2159ff9a22a223a1a91c9d7'))


def main():
    import addon_utils
    addon_utils.enable('io_scene_foundry', default_set=True, persistent=False)
    addon_utils.enable('io_scene_halo', default_set=True, persistent=False)
    assert 'io_scene_halo' in bpy.context.preferences.addons
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    from io_scene_foundry import utils
    scene = bpy.context.scene
    prefs = bpy.context.preferences.addons['io_scene_foundry'].preferences
    project = prefs.projects.add()
    project.name = project.project_name = scene.nwo.scene_project
    project.project_path = str(KIT); project.tags_directory = str(KIT / 'tags'); project.data_directory = str(KIT / 'data')
    project.corinth = False

    # Keep only this BSP's collections; seams are Reach BSP-connection data (H3 loads BSPs without seams).
    keep = f'52_ivory_tower_{BSP}'
    kept = set(bpy.data.collections[keep].all_objects)
    for o in list(scene.objects):
        if o not in kept or o.data is not None and getattr(getattr(o.data, 'nwo', None), 'mesh_type', '').endswith('_seam'):
            bpy.data.objects.remove(o, do_unlink=True)
    assert all(o.parent is None or o.parent in kept for o in scene.objects)
    originals = list(scene.objects)

    assert scene.nwo.scale == 'blender' and scene.nwo.forward_direction == 'y-', (scene.nwo.scale, scene.nwo.forward_direction)
    rotation = utils.rotation_diff_from_forward(scene.nwo.forward_direction, 'x')
    utils.transform_scene(bpy.context, 1 / 0.03048, rotation, scene.nwo.forward_direction, 'x', actions=[])
    scene.nwo.scale = 'max'; scene.nwo.forward_direction = 'x'

    lighting = {'single_probe': '>', 'per_vertex': '?', 'per_pixel': '!'}
    pathfinding = {'none': '-', 'static': '+', 'cutout': ''}
    collision_children = []; collision_defined = set(); physics_pending = []; portal_materials = {}; kinds = collections.Counter()
    for obj in originals:
        if obj.type != 'MESH':
            continue
        kind = obj.nwo.mesh_type; kinds[kind] += 1
        if kind.endswith('_default'):
            prefix = '%' + pathfinding[obj.nwo.poop_pathfinding] + lighting[obj.nwo.poop_lighting]
            for field, symbol in (('poop_render_only', '*'), ('poop_does_not_block_aoe', '^'),
                                  ('poop_excluded_from_lightprobe', '<'), ('poop_decal_spacing', '|')):
                if getattr(obj.nwo, field):
                    prefix += symbol
            obj.ass_jms.name_override = prefix + obj.name
            proxy = obj.data.nwo.proxy_collision
            if proxy and obj.data not in collision_defined:
                child = proxy.copy(); scene.collection.objects.link(child)
                child.name = '@' + obj.name + '_collision'; child.ass_jms.name_override = child.name
                child.parent = obj; child.matrix_parent_inverse = Matrix.Identity(4); child.matrix_basis = Matrix.Identity(4)
                collision_children.append(dict(parent=obj.name, child=child.name, polygons=len(proxy.data.polygons)))
                collision_defined.add(obj.data)
            physics = [getattr(obj.data.nwo, f'proxy_physics{i}') for i in range(200) if getattr(obj.data.nwo, f'proxy_physics{i}', None) is not None]
            if physics:
                physics_pending.append(dict(object=obj.name, proxies=[p.name for p in physics]))
        elif kind.endswith('_portal'):
            key = (obj.nwo.portal_ai_deafening, obj.nwo.portal_blocks_sounds, obj.nwo.portal_is_door)
            if key not in portal_materials:
                mat = bpy.data.materials.new('h3_portal_authoring'); mat.ass_jms.name_override = '+portal'; mat.ass_jms.is_bm = True
                mat.ass_jms.ai_deafening, mat.ass_jms.blocks_sound, mat.ass_jms.portal_door = key
                portal_materials[key] = mat
            obj.data.materials.clear(); obj.data.materials.append(portal_materials[key])
            for p in obj.data.polygons: p.material_index = 0
        elif not (kind.endswith('_structure') or kind.endswith('_water_surface')):
            raise RuntimeError(f'Unhandled mesh type: {obj.name}: {kind}')

    face_variants = {}; handled = collections.Counter(); pending_faces = []
    for mesh in {o.data for o in scene.objects if o.type == 'MESH'}:
        configs = [dict() for _ in mesh.polygons]
        for prop in mesh.nwo.face_props:
            attr = mesh.attributes.get(prop.attribute_name)
            if attr is None or attr.domain != 'FACE':
                raise RuntimeError(f'Missing source face selection: {mesh.name}: {prop.attribute_name}')
            sel = [i for i, it in enumerate(attr.data) if it.value]
            s = {}
            if prop.type == 'face_mode':
                if prop.face_mode not in ('render_only', 'collision_only', 'sphere_collision_only', 'lightmap_only', 'breakable', 'shadow_only'):
                    raise RuntimeError(f'Unresolved face mode: {prop.face_mode}')
                s[prop.face_mode] = True
            elif prop.type == 'face_sides' and prop.face_sides_type == 'two_sided':
                s['two_sided'] = prop.two_sided
            elif prop.type in ('no_shadow', 'slip_surface'):
                s[prop.type] = getattr(prop, prop.type)
            elif prop.type == 'transparent':
                s['transparent_1_sided'] = prop.transparent
            elif prop.type == 'lightmap_transparency_override':
                s['override_lightmap_transparency'] = prop.lightmap_transparency_override
            elif prop.type == 'lightmap_translucency_tint_color':
                s['two_sided_transparent_tint'] = tuple(prop.lightmap_translucency_tint_color)
            else:
                pending_faces.append(dict(mesh=mesh.name, property=prop.type, faces=len(sel))); continue
            for i in sel:
                for k, v in s.items():
                    if k in configs[i] and configs[i][k] != v:
                        raise RuntimeError(f'Conflicting source face properties: {mesh.name}, {i}, {k}')
                    configs[i][k] = v
            handled[prop.type] += len(sel)
        slots = list(mesh.materials)
        for poly, s in zip(mesh.polygons, configs):
            if not s: continue
            mat = slots[poly.material_index]
            if mat is None: raise RuntimeError(f'Unassigned material: {mesh.name}, {poly.index}')
            if s.get('transparent_1_sided') and s.get('two_sided'):
                s['transparent_1_sided'] = False; s['transparent_2_sided'] = True
            key = (mat.name, tuple(sorted(s.items())))
            var = face_variants.get(key)
            if var is None:
                var = mat.copy(); var.name = mat.name + '_h3_flags'
                var.ass_jms.name_override = mat.ass_jms.name_override or mat.name; var.ass_jms.is_bm = True
                for k, v in s.items(): setattr(var.ass_jms, k, v)
                face_variants[key] = var
            slot = mesh.materials.find(var.name)
            if slot == -1: slot = len(mesh.materials); mesh.materials.append(var)
            poly.material_index = slot

    # Halo 3 limits a cluster's structure section to 32767 vertices (Reach does not). Decorative structure detail
    # named on the command line (--instance-materials a,b) becomes instanced geometry, the H3 authoring route for
    # detail: faces split off unchanged, grouped by 24-unit area cells, render-only and per-pixel lit; the structure keeps the
    # same faces as collision-only.
    moved = []
    if '--instance-materials' in sys.argv:
        import bmesh
        wanted = sys.argv[sys.argv.index('--instance-materials') + 1].split(',')
        for st in [o for o in scene.objects if o.type == 'MESH' and o.nwo.mesh_type.endswith('_structure')]:
            me = st.data
            pick = [i for i, m in enumerate(me.materials) if m and any((m.ass_jms.name_override or m.name).split('_h3_flags')[0] == w or m.name.split('_h3_flags')[0] == w for w in wanted)]
            # Faces that never rendered (collision-only / sphere-only variants) stay in the structure untouched.
            pick = [i for i in pick if not (me.materials[i].ass_jms.collision_only or me.materials[i].ass_jms.sphere_collision_only)]
            render_only = {i for i in pick if me.materials[i].ass_jms.render_only}
            if not pick: continue
            bm = bmesh.new(); bm.from_mesh(me)
            faces = [f for f in bm.faces if f.material_index in pick]
            cells = collections.defaultdict(list)
            for f in faces:
                c = f.calc_center_median()
                cell = 24 / 0.03048  # 24 world units in the exported (Max) units
                cells[(int(c.x // cell), int(c.y // cell), int(c.z // cell))].append(f.index)
            bm.free()
            for n, (cell, idx) in enumerate(sorted(cells.items())):
                ob = st.copy(); ob.data = me.copy(); scene.collection.objects.link(ob)
                keep_set = set(idx)
                b2 = bmesh.new(); b2.from_mesh(ob.data)
                bmesh.ops.delete(b2, geom=[f for f in b2.faces if f.index not in keep_set], context='FACES')
                b2.to_mesh(ob.data); b2.free()
                ob.name = f'detail_{wanted[0]}_{n:02d}'
                ob.ass_jms.name_override = '%-!*' + ob.name  # render-only instance
                moved.append(dict(object=ob.name, faces=len(idx)))
            # The structure keeps these faces as collision-only (same collision as Reach, no render vertices).
            # Render-only faces had no collision in Reach: removed from the structure entirely.
            bm = bmesh.new(); bm.from_mesh(me)
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in render_only], context='FACES')
            bm.to_mesh(me); bm.free()
            for i in pick:
                if i in render_only: continue
                m = me.materials[i]
                c = m.copy(); c.name = m.name + '_collision_only'
                c.ass_jms.name_override = m.ass_jms.name_override or m.name.split('_h3_flags')[0]
                c.ass_jms.is_bm = True; c.ass_jms.collision_only = True
                for k in ('render_only', 'sphere_collision_only', 'lightmap_only'):
                    if hasattr(c.ass_jms, k): setattr(c.ass_jms, k, False)
                me.materials[i] = c

    scene.ass.game_title = 'halo3'; scene.ass.ass_version = '7'; scene.ass.clean_normalize_weights = False
    scene.ass.edge_split = False; scene.ass.scale_enum = '0'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / f'reflection-h3-{BSP}.blend'))
    from io_scene_halo.file_ass import export_ass
    from io_scene_halo.global_functions import global_functions
    ass = OUT / f'reflection_{BSP}.ass'
    bpy.context.view_layer.update()
    r = export_ass.write_file(bpy.context, str(ass), 7, 'halo3', False, True, True, True, True, True,
                              global_functions.EdgeSplit(False, False, 0.0, False), False, 1.0,
                              lambda level, msg: print(level, msg, flush=True))
    assert r == {'FINISHED'}, r
    report = dict(bsp=BSP, moved_to_instances=moved, mesh_kinds=dict(kinds), collision_children=collision_children, physics_pending=physics_pending,
                  face_assignments=dict(handled), material_variants=len(face_variants), pending_faces=pending_faces,
                  ass=str(ass), ass_bytes=ass.stat().st_size)
    (OUT / f'prepare-{BSP}-report.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
    print('PREPARED', BSP, ass.stat().st_size, flush=True)


try:
    main()
except BaseException:
    traceback.print_exc()
    sys.stdout.flush()
    sys.exit(1)
sys.stdout.flush()
sys.exit(0)
