"""Inside Blender: run unchanged Foundry 1.9.19's tag import on Reach's own Reflection (52_ivory_tower) from the
Reach Editing Kit, save the scene and write an inventory. Thin driver only: no geometry is changed here.

Run through launch.py (private desktop, repo-local profile). Waits for Blender to finish starting (Foundry's light
import needs a non-zero display scale), then quits."""
from collections import Counter
from pathlib import Path
import hashlib, json, sys, time, traceback
import bpy

REPO = Path(r'C:\Programming\GitHub\OpenH3M')
OLD = Path(r'C:\X360\ISOs\H3M\.local\OpenH3M-source\work\halo4-to-h3')
KIT = REPO / '.local/asset-kit-hrek'
TAGS = KIT / 'tags'
SOURCE = TAGS / 'levels/multi/52_ivory_tower/52_ivory_tower.scenario'
OUT = REPO / '.local/reflection-rebuild'


def manifest():
    rows = {}
    for p in (TAGS / 'levels/multi/52_ivory_tower').rglob('*'):
        if p.is_file():
            rows[str(p.relative_to(TAGS))] = hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
    return rows


def run():
    import addon_utils
    sys.path.insert(0, str(OLD / 'python-packages-313'))
    sys.path.insert(0, str(OLD / 'upstream/Foundry-1.9.19'))
    addon_utils.enable('io_scene_foundry', default_set=True, persistent=False)
    assert 'io_scene_foundry' in bpy.context.preferences.addons
    prefs = bpy.context.preferences.addons['io_scene_foundry'].preferences
    project = prefs.projects.add()
    project.name = project.project_name = 'Reach HREK'
    project.project_path = str(KIT)
    project.tags_directory = str(TAGS)
    project.data_directory = str(KIT / 'data')
    project.corinth = False
    bpy.context.scene.nwo.scene_project = project.name
    bpy.context.scene.nwo_export.show_output = False
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    before = manifest()
    t = time.perf_counter()
    report = dict(source=str(SOURCE), status='running')
    try:
        r = bpy.ops.nwo.foundry_import(filepath=str(SOURCE), build_blender_materials=False,
            tag_bsp_render_only=False, tag_bsp_import_geometry=True, tag_import_design=True, tag_import_lights=True,
            tag_scenario_import_objects=False, tag_scenario_import_decals=False, setup_as_asset=False)
        assert r == {'FINISHED'}, r
        obs = list(bpy.context.scene.objects)
        meshes = [o for o in obs if o.type == 'MESH']
        face_modes = Counter()
        for o in meshes:
            for fp in o.data.nwo.face_props:
                face_modes[(fp.type, getattr(fp, 'face_mode', ''))] += 1
        report.update(status='finished', objects=len(obs), meshes=len(meshes),
            polygons=sum(len(o.data.polygons) for o in meshes),
            mesh_types=dict(Counter(o.data.nwo.mesh_type for o in meshes)),
            face_props={f'{k[0]}:{k[1]}': v for k, v in face_modes.items()},
            collections=[dict(name=c.name, objects=len(c.all_objects)) for c in bpy.data.collections])
    except BaseException as e:
        report.update(status='failed', error=repr(e), trace=traceback.format_exc())
    report.update(seconds=time.perf_counter() - t, source_tags_unchanged=manifest() == before)
    (OUT / 'import-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if report['status'] == 'finished' and report['source_tags_unchanged']:
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'reflection-reach-source.blend'))
    print('REACH_IMPORT', report['status'], flush=True)


def tick():
    try:
        run()
    except BaseException:
        traceback.print_exc()
    finally:
        sys.stdout.flush(); sys.stderr.flush()
        bpy.ops.wm.quit_blender()


bpy.app.timers.register(tick, first_interval=1.0)
