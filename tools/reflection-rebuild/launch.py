"""Run a Blender script for the Reflection rebuild on a private desktop with a repo-local profile.
Usage: python launch.py <script.py> [timeout_seconds] [-- script args]"""
import os, sys
from pathlib import Path
sys.path.insert(0, r'C:\Programming\GitHub\OpenH3M\tools\asset-library')
from hidden_run import run

BLENDER = r'C:\X360\ISOs\H3M\.local\OpenH3M-source\work\halo4-to-h3\upstream\blender-5.2.3-windows-x64\blender.exe'
OUT = Path(r'C:\Programming\GitHub\OpenH3M\.local\reflection-rebuild')
script = Path(sys.argv[1]).resolve()
timeout = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != '--' else 1800
extra = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
env = dict(os.environ)
for k, sub in (('TEMP', 'temp'), ('TMP', 'temp'), ('APPDATA', 'profile/roaming'), ('LOCALAPPDATA', 'profile/local'),
               ('BLENDER_USER_CONFIG', 'profile/blender')):
    (OUT / sub).mkdir(parents=True, exist_ok=True); env[k] = str(OUT / sub)
env['PYTHONDONTWRITEBYTECODE'] = '1'; env['PYTHONUNBUFFERED'] = '1'
code, text = run([BLENDER, '--factory-startup', '--python-exit-code', '1', '--python', str(script), '--', *extra],
                 r'C:\Programming\GitHub\OpenH3M\.local\asset-kit-hrek', OUT / (script.stem + '.log'), timeout=timeout, env=env)
print('exit', code)
print(text[-3000:])
