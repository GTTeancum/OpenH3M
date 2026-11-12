"""Invoke the unchanged importer after Blender startup; no UI or host input."""
from pathlib import Path
import bpy
import runpy
import sys
import traceback

def execute():
    try:
        print('INITIALIZED_DISPLAY_SCALE', bpy.context.preferences.system.ui_scale, flush=True)
        runpy.run_path(str(Path(__file__).with_name('inspect_halo4_geometry.py')), run_name='__main__')
    except BaseException:
        traceback.print_exc()
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        bpy.ops.wm.quit_blender()
    return None

# The launcher also checks the fresh JSON result: callback errors alone do not
# necessarily give Blender a failing process exit code.
bpy.app.timers.register(execute, first_interval=1.0)
