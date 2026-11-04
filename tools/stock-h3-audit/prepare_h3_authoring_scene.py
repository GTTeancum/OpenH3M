"""Configure documented H3 Blender authoring controls on the fresh source scene.

Uses upstream Foundry for coordinate conversion and existing Blender/Halo
properties for object names, collision parenting and portal materials. No mesh
conversion, topology repair, shader generation or custom ASS writer.
Face-level authoring and shader selection remain explicit outstanding work.
"""
import collections
import hashlib
import json
from pathlib import Path
import runpy
import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_foundry.py'))
runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_h3_exporter.py'))
from io_scene_foundry import utils

source = OUT / 'reach-source-inspection.blend'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
assert Path(bpy.data.filepath) == source
scene = bpy.context.scene
prefs = bpy.context.preferences.addons['io_scene_foundry'].preferences
project = prefs.projects.add()
project.name = project.project_name = scene.nwo.scene_project
project.project_path = str(ROOT / 'work/editing-kits/hrek')
project.tags_directory = str(ROOT / 'work/editing-kits/hrek/tags')
project.data_directory = str(ROOT / 'work/editing-kits/hrek/data')
project.corinth = False
bpy.context.preferences.filepaths.save_version = 0
scene.nwo.lights_export_on_save = False
scene.nwo.prefabs_export_on_save = False
originals = list(scene.objects)
mesh_counts = {o.data: (len(o.data.vertices), len(o.data.polygons)) for o in originals if o.type == 'MESH'}

# Reverse precisely the transform used by Foundry's own import operator.
assert scene.nwo.scale == 'blender' and scene.nwo.forward_direction == 'y-'
rotation = utils.rotation_diff_from_forward(scene.nwo.forward_direction, 'x')
utils.transform_scene(bpy.context, 1 / 0.03048, rotation,
                      scene.nwo.forward_direction, 'x', actions=[])
scene.nwo.scale = 'max'
scene.nwo.forward_direction = 'x'

names = []
collision_children = []
collision_defined = set()
physics_pending = []
portal_materials = {}
lighting = {'single_probe': '>', 'per_vertex': '?', 'per_pixel': '!'}
pathfinding = {'none': '-', 'static': '+', 'cutout': ''}
for obj in originals:
    if obj.type != 'MESH':
        continue
    kind = obj.nwo.mesh_type
    if kind.endswith('_default'):
        prefix = '%' + pathfinding[obj.nwo.poop_pathfinding] + lighting[obj.nwo.poop_lighting]
        for field, symbol in (('poop_render_only', '*'), ('poop_does_not_block_aoe', '^'),
                              ('poop_excluded_from_lightprobe', '<'), ('poop_decal_spacing', '|')):
            if getattr(obj.nwo, field):
                prefix += symbol
        obj.ass_jms.name_override = prefix + obj.name
        proxy = obj.data.nwo.proxy_collision
        if proxy and obj.data not in collision_defined:
            # A local collision child is the documented H3 ASS override.
            child = proxy.copy()
            scene.collection.objects.link(child)
            child.name = '@' + obj.name + '_collision'
            child.ass_jms.name_override = child.name
            child.parent = obj
            child.matrix_parent_inverse = Matrix.Identity(4)
            child.matrix_basis = Matrix.Identity(4)
            collision_children.append(dict(parent=obj.name, child=child.name, source=proxy.name,
                                           mesh=proxy.data.name, polygons=len(proxy.data.polygons)))
            collision_defined.add(obj.data)
        physics = [getattr(obj.data.nwo, f'proxy_physics{i}') for i in range(200)
                   if getattr(obj.data.nwo, f'proxy_physics{i}') is not None]
        if physics:
            physics_pending.append(dict(object=obj.name, proxies=[p.name for p in physics]))
    elif kind.endswith('_portal'):
        key = (obj.nwo.portal_ai_deafening, obj.nwo.portal_blocks_sounds, obj.nwo.portal_is_door)
        if key not in portal_materials:
            mat = bpy.data.materials.new('h3_portal_authoring')
            mat.ass_jms.name_override = '+portal'
            mat.ass_jms.is_bm = True
            mat.ass_jms.ai_deafening, mat.ass_jms.blocks_sound, mat.ass_jms.portal_door = key
            portal_materials[key] = mat
        obj.data.materials.clear()
        obj.data.materials.append(portal_materials[key])
        for polygon in obj.data.polygons:
            polygon.material_index = 0
    elif not (kind.endswith('_structure') or kind.endswith('_water_surface')):
        raise RuntimeError(f'Unhandled mesh type: {obj.name}: {kind}')
    names.append(dict(object=obj.name, mesh_type=kind, export_name=obj.ass_jms.name_override or obj.name))

# Assign existing H3 material flags to the same faces selected by Foundry.
# The exporter stores these flags per material, so Blender material slots are
# duplicated as needed; vertices, polygons, UVs and normals are not rebuilt.
face_variants = {}
handled = collections.Counter()
pending_faces = []
all_meshes = {o.data for o in scene.objects if o.type == 'MESH'}
for mesh in all_meshes:
    configurations = [dict() for _ in mesh.polygons]
    for prop in mesh.nwo.face_props:
        attribute = mesh.attributes.get(prop.attribute_name)
        if attribute is None or attribute.domain != 'FACE':
            raise RuntimeError(f'Missing source face selection: {mesh.name}: {prop.attribute_name}')
        selected = [i for i, item in enumerate(attribute.data) if item.value]
        settings = {}
        if prop.type == 'face_mode':
            if prop.face_mode not in ('render_only','collision_only','sphere_collision_only','lightmap_only','breakable','shadow_only'):
                raise RuntimeError(f'Unresolved face mode: {prop.face_mode}')
            settings[prop.face_mode] = True
        elif prop.type == 'face_sides' and prop.face_sides_type == 'two_sided':
            settings['two_sided'] = prop.two_sided
        elif prop.type in ('no_shadow', 'slip_surface'):
            settings[prop.type] = getattr(prop, prop.type)
        elif prop.type == 'transparent':
            settings['transparent_1_sided'] = prop.transparent
        elif prop.type == 'lightmap_transparency_override':
            settings['override_lightmap_transparency'] = prop.lightmap_transparency_override
        elif prop.type == 'lightmap_translucency_tint_color':
            settings['two_sided_transparent_tint'] = tuple(prop.lightmap_translucency_tint_color)
        else:
            pending_faces.append(dict(mesh=mesh.name, property=prop.type, faces=len(selected), attribute=prop.attribute_name))
            continue
        for index in selected:
            for key, value in settings.items():
                if key in configurations[index] and configurations[index][key] != value:
                    raise RuntimeError(f'Conflicting source face properties: {mesh.name}, {index}, {key}')
                configurations[index][key] = value
        handled[prop.type] += len(selected)
    original_slots = list(mesh.materials)
    for polygon, settings in zip(mesh.polygons, configurations):
        if not settings:
            continue
        material = original_slots[polygon.material_index]
        if material is None:
            raise RuntimeError(f'Unassigned material: {mesh.name}, {polygon.index}')
        if settings.get('transparent_1_sided') and settings.get('two_sided'):
            settings['transparent_1_sided'] = False
            settings['transparent_2_sided'] = True
        key = (material.name, tuple(sorted(settings.items())))
        variant = face_variants.get(key)
        if variant is None:
            variant = material.copy()
            variant.name = material.name + '_h3_flags'
            variant.ass_jms.name_override = material.ass_jms.name_override or material.name
            variant.ass_jms.is_bm = True
            for name, value in settings.items():
                setattr(variant.ass_jms, name, value)
            face_variants[key] = variant
        slot = mesh.materials.find(variant.name)
        if slot == -1:
            slot = len(mesh.materials)
            mesh.materials.append(variant)
        polygon.material_index = slot

assert all((len(m.vertices), len(m.polygons)) == counts for m, counts in mesh_counts.items())
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
scene.ass.game_title = 'halo3'
scene.ass.ass_version = '7'
scene.ass.clean_normalize_weights = False
scene.ass.edge_split = False
scene.ass.scale_enum = '0'
destination = OUT / 'battle-canyon-h3-authoring.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
report = dict(source=str(source), source_sha256=source_hash, scene=str(destination),
              source_mesh_counts_unchanged=True, coordinate_conversion='Unmodified Foundry transform_scene; Blender/y- to Max/x',
              instances=sum(n['mesh_type'].endswith('_default') for n in names),
              portals=sum(n['mesh_type'].endswith('_portal') for n in names),
              collision_children=collision_children, objects=names,
              pending_physics_proxies=physics_pending,
              face_property_assignments=dict(handled), material_flag_variants=len(face_variants),
              pending_face_properties=pending_faces,
              outstanding=['Resolve remaining face lighting metadata before final authoring/export',
                           'Resolve separate convex physics proxies through documented H3 tools',
                           'Assign Reach-textured stock H3 shader tags',
                           'Configure water channels, source sky and fresh H3 lighting',
                           'ASS export and official compile have not been attempted'])
(OUT / 'h3-authoring-scene-report.json').write_text(json.dumps(report, indent=2) + '\n')
print('H3_AUTHORING_SCENE_SAVED', str(destination), 'instances', report['instances'], 'portals', report['portals'],
      'collision_children', len(collision_children), 'physics_pending', len(physics_pending), flush=True)
