"""Render actual imported geometry using Blender; no desktop capture/input."""
import json
import hashlib
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit/wip'
OUT.mkdir(exist_ok=True)
scene = bpy.context.scene
authoring = '--authoring' in sys.argv
world_split = '--world-collision-split' in sys.argv
assert not world_split or authoring
assignment_preview = '--material-assignments' in sys.argv
dirty_glass_preview = '--dirty-glass' in sys.argv
water_preview = '--water' in sys.argv
assert not dirty_glass_preview or assignment_preview
assert not water_preview or (assignment_preview and not dirty_glass_preview)
buildings = '--buildings' in sys.argv or assignment_preview
source_hash = hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
if authoring:
    import runpy
    import bmesh
    runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_foundry.py'))
    runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_h3_exporter.py'))
    for ob in bpy.data.objects:
        if ob.type == 'MESH' and (ob.name=='bc_world_collision' or ob.name.startswith('@') or ob.nwo.mesh_type in {'_connected_geometry_mesh_type_portal', '_connected_geometry_mesh_type_collision', '_connected_geometry_mesh_type_physics'}):
            ob.hide_render = True
    # Workbench ignores Halo's per-face visibility flags. Filter preview copies
    # only; never save this temporary render scene over the authoring .blend.
    preview_meshes = {}
    removed = 0
    for ob in scene.objects:
        if ob.type != 'MESH' or ob.hide_render:
            continue
        original = ob.data
        if original not in preview_meshes:
            hidden_slots = {i for i,m in enumerate(original.materials) if m and
                            any(getattr(m.ass_jms,flag) for flag in ('collision_only','sphere_collision_only','lightmap_only','shadow_only'))}
            preview = original.copy()
            bm = bmesh.new()
            bm.from_mesh(preview)
            hidden = [f for f in bm.faces if f.material_index in hidden_slots]
            removed += len(hidden)
            bmesh.ops.delete(bm, geom=hidden, context='FACES')
            bm.to_mesh(preview)
            bm.free()
            preview_meshes[original] = preview
        ob.data = preview_meshes[original]
    print('PREVIEW_ONLY_NONRENDER_FACES_HIDDEN', removed, flush=True)
depsgraph = bpy.context.evaluated_depsgraph_get()
points = []
for instance in depsgraph.object_instances:
    ob = instance.object
    if ob.type == 'MESH' and not ob.hide_render:
        if buildings:
            if assignment_preview:
                suffix='ca_bcreek_river.shader_water' if water_preview else 'glass_window_dirty_subdued.shader_glass' if dirty_glass_preview else 'ca_bcreek_glass_bridge.shader'
                slots={i for i,m in enumerate(ob.data.materials) if m and m.nwo.shader_path.endswith(suffix)}
            else:
                slots={i for i,m in enumerate(ob.data.materials) if m and any(n in m.name for n in ('ca_bcreek_bb_walldetail','ca_bcreek_bb_main'))}
            if slots:
                vertices={v for p in ob.data.polygons if p.material_index in slots for v in p.vertices}
                world_points=[instance.matrix_world @ ob.data.vertices[i].co for i in vertices]
                points.extend(p for p in world_points if not dirty_glass_preview or p.x < 0)
            continue
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
textured = '--textured' in sys.argv
if textured:
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    sun = bpy.data.objects.new('Preview light only', bpy.data.lights.new('Preview light only', 'SUN'))
    scene.collection.objects.link(sun)
    sun.data.energy = 2.0
    sun.rotation_euler = (.45, -.55, -.5)
    scene.world.use_nodes = True
    scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value = (.8, .8, .8, 1)
    scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value = .8
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'SINGLE'
scene.display.shading.single_color = (0.55, 0.58, 0.61)
highlighted = {}
if assignment_preview:
    assert authoring and not textured
    bindings = json.loads((OUT.parent / 'h3-material-bindings.json').read_text())
    assert bpy.data.filepath == bindings['scene'] and source_hash == bindings['scene_sha256']
    scene.display.shading.color_type = 'MATERIAL'
    families = json.loads((ROOT/'tools/stock-h3-audit/material_families.json').read_text())
    for material in bpy.data.materials:
        source = material.nwo.shader_path
        preview_families=('water',) if water_preview else ('dirty_glass',) if dirty_glass_preview else ('glass_interior', 'glass_exterior', 'circle_panels', 'forge_panel')
        selected = next((family for family in preview_families
                         if source in families[family]['sources']), None)
        material.diffuse_color = (0.38, 0.41, 0.44, 1)
        if selected:
            assert source in bindings['bindings']
            material.diffuse_color = (0.02, 0.75, 0.95, 1) if 'glass' in selected or selected=='water' else (1, 0.32, 0.04, 1)
            highlighted[source] = bindings['bindings'][source]['export_tag']
    assert len(highlighted) == (1 if dirty_glass_preview or water_preview else 6)
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.display.shading.background_type = 'WORLD'
scene.world.color = (0.08, 0.08, 0.08)
scene.render.image_settings.file_format = 'PNG'
views=[('overview', (1, -1, 1.3), 1.5), ('closer', (-1, -1, 1.5), 1.0)]
if buildings:
    # This base faces into the canyon along +Y; the generic overview directions
    # put the camera behind its surrounding cliffs. Keep all geometry visible.
    views=[('overview',(0,1,.3),1.15),('closer',(.4,1,.3),.85)]
    if authoring:
        from mathutils import Matrix
        from io_scene_foundry import utils
        rotation=Matrix.Rotation(utils.rotation_diff_from_forward('y-','x'),3,'Z')
        views=[(name,rotation @ Vector(direction),scale) for name,direction,scale in views]
if assignment_preview:
    views=[('bridge',Vector((1,-.25,.45)),1.3)]
    if dirty_glass_preview:views=[('skylights',Vector((0,-.2,1)),1.4)]
    if water_preview:views=[('river',Vector((0,-.15,1)),1.25)]
for name, direction, scale in views:
    camera.location = center + Vector(direction).normalized() * span * (.7 if buildings else 2)
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    if textured:
        sun.rotation_euler = camera.rotation_euler
    camera.data.ortho_scale = span * scale
    prefix = ('h3-buildings-' if authoring else 'buildings-') if buildings else ('h3-authoring-' if authoring else ('textured-' if textured else ''))
    if assignment_preview:
        prefix = 'h3-material-assignments-'
        if dirty_glass_preview:prefix='h3-dirty-glass-assignments-'
        if water_preview:prefix='h3-water-assignments-'
    if world_split:prefix='h3-world-split-'
    scene.render.filepath = str(OUT / (prefix + name + '.png'))
    bpy.ops.render.render(write_still=True)
(OUT / (prefix + 'capture-info.json')).write_text(json.dumps(dict(bounds_low=list(low), bounds_high=list(high),
    source_scene=bpy.data.filepath,
    label='Blender authoring geometry WIP, not H3 MCC' if authoring else 'Original Reach geometry imported by Foundry; Blender WIP, not H3 MCC',
    highlighted=highlighted, source_sha256=source_hash,
    preview_colors=('Cyan: assigned river. Water coordinates and game shading remain unverified.' if water_preview else 'Cyan: assigned dirty glass. Diagnostic color, not game shading.' if dirty_glass_preview else 'Cyan: assigned glass; orange: assigned panels. Diagnostic colors, not game shading.') if assignment_preview else None,
    textured=textured, lighting='Studio preview lighting, not map lighting'), indent=2)+'\n')
assert hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest() == source_hash
