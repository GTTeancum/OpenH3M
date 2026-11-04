"""Enable the unmodified community H3 exporter; no asset export or conversion."""
import sys
from pathlib import Path
import addon_utils
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'work/stock-h3-audit'
pin = (OUT / 'h3-exporter-pin.txt').read_text(encoding='utf-8-sig').strip()
sys.path.insert(0, str(OUT / f'upstream/Halo-Asset-Blender-Development-Toolset-{pin}'))
addon_utils.enable('io_scene_halo', default_set=True, persistent=False)
assert 'io_scene_halo' in bpy.context.preferences.addons, 'H3 exporter failed to enable'
print('H3_EXPORTER_BACKGROUND_LOAD_OK', bpy.app.version_string, pin, flush=True)
