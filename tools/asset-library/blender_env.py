"""Run background Blender 4.5 with repo-local profile and add-ons.

Usage (host python): blender_env.run(script, *args, log=path)
Inside Blender: import blender_env; blender_env.enable('io_scene_halo'|'io_scene_foundry')
"""
import os, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / '.local/asset-tools'
BLENDER = Path(r'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe')
def run(script, *args, log=None, timeout=3600, blend=None):
    e = os.environ.copy()
    for k, p in [('APPDATA', 'profile/roaming'), ('LOCALAPPDATA', 'profile/local'), ('BLENDER_USER_CONFIG', 'profile/blender'),
                 ('BLENDER_USER_SCRIPTS', 'profile/blender/scripts'), ('USERPROFILE', 'profile/home'), ('HOME', 'profile/home'), ('TEMP', 'temp'), ('TMP', 'temp')]:
        e[k] = str(TOOLS / p)
    cmd = [str(BLENDER), '--background', '--factory-startup']
    if blend: cmd.append(str(Path(blend).resolve()))
    cmd += ['--python-exit-code', '1', '--python', str(Path(script).resolve()), '--', *map(str, args)]
    # Always on a private desktop: Foundry loads ManagedBlam, which can raise assert dialogs.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import hidden_run
    log = Path(log) if log else TOOLS / 'temp' / 'blender-last.log'
    return hidden_run.run(cmd, ROOT, log, timeout=timeout, env=e)
def enable(*names):
    import addon_utils, bpy
    sys.path.insert(0, str(TOOLS / 'python-packages'))
    sys.path.insert(0, str(TOOLS / 'addons'))
    for n in names:
        addon_utils.enable(n, default_set=True, persistent=False)
        assert n in bpy.context.preferences.addons, n
if __name__ == '__main__':
    rc, out = run(*sys.argv[1:])
    print(out[-6000:]); sys.exit(rc)
