"""Run unmodified Foundry extraction for explicitly named original bitmaps.

Run in background Blender with -- followed by one or more relative .bitmap
paths. No pixel edits, blue-channel reconstruction, or tag writes are requested.
"""
import bpy
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
KIT = ROOT / 'work/editing-kits/hrek'
runpy.run_path(str(ROOT / 'tools/stock-h3-audit/check_foundry.py'))
project = bpy.context.preferences.addons['io_scene_foundry'].preferences.projects.add()
project.name = project.project_name = 'Original Reach bitmap extraction'
project.project_path = str(KIT)
project.tags_directory = str(KIT / 'tags')
project.data_directory = str(KIT / 'data')
project.corinth = False
bpy.context.scene.nwo.scene_project = project.name
from io_scene_foundry.managed_blam.bitmap import BitmapTag
from io_scene_foundry.managed_blam import mb_init
mb_init()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

paths = sys.argv[sys.argv.index('--') + 1:]
assert paths
report_path = OUT / 'extra-reach-bitmap-extractions.json'
report = json.loads(report_path.read_text()) if report_path.is_file() else {}
for path in paths:
    source = (KIT / 'tags' / path).resolve()
    assert source.is_relative_to((KIT / 'tags').resolve()) and source.suffix == '.bitmap'
    assert source.is_file()
    before = sha(source)
    destination = (KIT / 'data' / path).with_suffix('.tiff').resolve()
    assert destination.is_relative_to((KIT / 'data').resolve())
    existed = destination.is_file()
    if not existed:
        with BitmapTag(path=path, tag_must_exist=True) as bitmap:
            result = bitmap.save_to_tiff(blue_channel_fix=False)
        assert Path(result).resolve() == destination, 'Review non-single-image extraction separately'
    assert sha(source) == before and destination.is_file()
    row = dict(source=str(source), source_sha256=before, image=str(destination),
               image_sha256=sha(destination))
    if path in report:
        assert all(report[path][k] == v for k, v in row.items()), 'Previously inspected source/image changed'
    else:
        row['method'] = ('Existing source image retained; extraction not repeated' if existed else
                         'Unmodified Foundry BitmapTag.save_to_tiff; blue_channel_fix=False')
        report[path] = row
    print('ORIGINAL_BITMAP_READY', path, 'existing' if existed else 'extracted', flush=True)
report_path.write_text(json.dumps(report, indent=2) + '\n')
