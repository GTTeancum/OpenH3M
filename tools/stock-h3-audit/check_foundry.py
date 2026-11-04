"""Load unmodified upstream Foundry in background Blender; no asset import."""
import sys
from pathlib import Path
import bpy
import addon_utils

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
sys.path.insert(0, str(OUT / 'python-packages'))
sys.path.insert(0, str(OUT / 'upstream/Foundry-5dc085e4432b6b57b2bf97e02a442ecc6edc985f/blender/addons'))
addon_utils.enable('io_scene_foundry', default_set=True, persistent=False)
assert 'io_scene_foundry' in bpy.context.preferences.addons, 'Foundry failed to enable'
assert hasattr(bpy.types.Scene, 'nwo'), 'Foundry scene properties missing'
print('FOUNDRY_BACKGROUND_LOAD_OK', bpy.app.version_string)
