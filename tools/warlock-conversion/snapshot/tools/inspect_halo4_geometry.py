"""Run unmodified Foundry's H4 scenario geometry import and inventory its output.

Structural checkpoint only: includes collision/design/prefabs and requests lights.
Scenario object/sky authoring and material previews are separate pending steps.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json
import runpy
import sys
import time
import bpy

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'work/halo4-to-h3/haven'
KIT = ROOT / 'work/editing-kits/h4ek'
TAGS = KIT / 'tags'
SOURCE = TAGS / 'levels/multi/wraparound/wraparound.scenario'
RELEASED = '--foundry-release' in sys.argv
VISUAL_SOURCE = '--source-visuals' in sys.argv
assert not VISUAL_SOURCE or RELEASED, 'Visual source import uses the verified released tool'
if RELEASED:
    OUT = OUT / 'foundry-1.9.19' / ('background' if bpy.app.background else 'application')
    if VISUAL_SOURCE:
        OUT = OUT.with_name(OUT.name + '-visuals')
    OUT.mkdir(parents=True, exist_ok=True)


def tag_manifest():
    rows = {}
    for path in TAGS.rglob('*'):
        if path.is_file():
            with path.open('rb') as stream:
                rows[str(path.relative_to(TAGS)).replace('\\', '/')] = hashlib.file_digest(stream, 'sha256').hexdigest()
    return rows


before = tag_manifest()
if RELEASED:
    import addon_utils
    sys.path.insert(0, str(ROOT / 'work/halo4-to-h3/python-packages-313'))
    sys.path.insert(0, str(ROOT / 'work/halo4-to-h3/upstream/Foundry-1.9.19'))
    addon_utils.enable('io_scene_foundry', default_set=True, persistent=False)
    assert 'io_scene_foundry' in bpy.context.preferences.addons, 'Released Foundry failed to enable'
else:
    runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_foundry.py'))
prefs = bpy.context.preferences.addons['io_scene_foundry'].preferences
project = prefs.projects.add()
project.name = project.project_name = 'Haven official H4 source'
project.project_path = str(KIT)
project.tags_directory = str(TAGS)
project.data_directory = str(KIT / 'data')
project.corinth = True
bpy.context.scene.nwo.scene_project = project.name
bpy.context.scene.nwo_export.show_output = False
bpy.context.scene.nwo.lights_export_on_save = False
bpy.context.scene.nwo.prefabs_export_on_save = False
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
started = time.perf_counter()
report = dict(source=str(SOURCE.relative_to(KIT)), source_sha256=before[str(SOURCE.relative_to(TAGS)).replace('\\', '/')],
    foundry_revision='release-1.9.19' if RELEASED else '5dc085e4432b6b57b2bf97e02a442ecc6edc985f',
    blender_version=bpy.app.version_string,
    background=bpy.app.background, display_scale=bpy.context.preferences.system.ui_scale,
    requested=dict(material_previews=VISUAL_SOURCE, render_only=False, geometry=True,
        design=True, lights=True, scenario_objects=False, decals=True, sky=VISUAL_SOURCE),
    status='running', scope='Structural source import only; not complete scene, export, visual or gameplay acceptance.')
try:
    extra_options = dict(tag_bsp_import_havok=True, tag_scenario_import_decorators=False) if RELEASED else {}
    if VISUAL_SOURCE:
        extra_options['tag_sky'] = 'environments/shared/skies/wraparound_sky/wraparound_sky_new/wraparound_sky_new.scenery'
    result = bpy.ops.nwo.foundry_import(filepath=str(SOURCE), build_blender_materials=VISUAL_SOURCE,
        tag_bsp_render_only=False, tag_bsp_import_geometry=True,
        tag_import_design=True, tag_import_lights=True, tag_scenario_import_objects=False,
        tag_scenario_import_decals=True, setup_as_asset=False, **extra_options)
    assert result == {'FINISHED'}, result
    objects = list(bpy.context.scene.objects)
    meshes = [obj for obj in objects if obj.type == 'MESH']
    assert meshes, 'Foundry returned no scene meshes'
    report.update(status='operator_finished', objects=len(objects), mesh_objects=len(meshes),
        polygons=sum(len(obj.data.polygons) for obj in meshes),
        light_objects=sum(obj.type == 'LIGHT' for obj in objects),
        material_count=len(bpy.data.materials),
        image_inventory=[dict(name=img.name, filepath=img.filepath, size=list(img.size),
            has_data=img.has_data, source=img.source) for img in bpy.data.images],
        light_inventory=[dict(name=obj.name, type=obj.data.type, energy=obj.data.energy,
            color=list(obj.data.color), matrix_world=[list(row) for row in obj.matrix_world])
            for obj in objects if obj.type == 'LIGHT'],
        mesh_types=dict(Counter(obj.data.nwo.mesh_type for obj in meshes)),
        collections=[dict(name=c.name, direct_objects=len(c.objects), total_objects=len(c.all_objects))
                     for c in bpy.data.collections],
        object_inventory=[dict(name=obj.name, type=obj.type,
            location=list(obj.location), matrix_world=[list(row) for row in obj.matrix_world],
            mesh=obj.data.name if obj.type == 'MESH' else None,
            vertices=len(obj.data.vertices) if obj.type == 'MESH' else None,
            polygons=len(obj.data.polygons) if obj.type == 'MESH' else None,
            instance_collection=obj.instance_collection.name if obj.instance_collection else None)
            for obj in objects])
except BaseException as error:
    report.update(status='failed', error=repr(error))
    raise
finally:
    after = tag_manifest()
    report.update(seconds=time.perf_counter()-started, source_tags_unchanged=before == after,
        changed_tags=sorted(name for name,sha in before.items() if after.get(name) != sha),
        new_tags=sorted(set(after)-set(before)))
    if before != after:
        report['status'] = 'rejected_source_mutation'
    (OUT / 'haven-geometry-import-report.json').write_text(json.dumps(report,indent=2)+'\n', encoding='utf-8')
    assert before == after, 'Source tags changed during import; reject output and inspect the manifest diff'

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'haven-source-geometry.blend'))
print('H4_GEOMETRY_IMPORT', json.dumps({key:report[key] for key in
    ('status','objects','mesh_objects','polygons','light_objects','source_tags_unchanged','seconds')}), flush=True)
