"""Shared setup for repository-confined H4 source authoring checkpoints."""
from pathlib import Path
import hashlib
import runpy
import sys
import bpy
import addon_utils

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'work/halo4-to-h3/haven'
KIT = ROOT / 'work/editing-kits/h4ek'
SOURCE = OUT / 'foundry-1.9.19/application-visuals/haven-source-geometry.blend'

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def setup(exporter=False, source=SOURCE):
    sys.path.insert(0, str(ROOT / 'work/halo4-to-h3/python-packages-313'))
    sys.path.insert(0, str(ROOT / 'work/halo4-to-h3/upstream/Foundry-1.9.19'))
    addon_utils.enable('io_scene_foundry', default_set=True, persistent=False)
    assert 'io_scene_foundry' in bpy.context.preferences.addons
    if exporter:
        runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_h3_exporter.py'))
    bpy.ops.wm.open_mainfile(filepath=str(source))
    project = bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
    project.name = project.project_name = bpy.context.scene.nwo.scene_project
    project.project_path = str(KIT)
    project.tags_directory = str(KIT / 'tags')
    project.data_directory = str(KIT / 'data')
    project.corinth = True
    bpy.context.scene.nwo.lights_export_on_save = False
    bpy.context.scene.nwo.prefabs_export_on_save = False
    bpy.context.preferences.filepaths.save_version = 0
    return bpy.context.scene

def stored(group):
    result = {}
    for key in group.keys():
        value = getattr(group, key, None)
        if value is None or isinstance(value, (str, bool, int, float)):
            result[key] = value
        elif isinstance(value, bpy.types.ID):
            result[key] = value.name
        else:
            result[key] = str(value)
    return result
