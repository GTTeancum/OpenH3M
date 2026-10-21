"""Deploy the host binaries beside the disc files, reusing shared maps and cache.

No game assets are copied. Existing unrelated destination files are rejected.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--project', type=Path, required=True)
parser.add_argument('--source', type=Path, required=True)
args = parser.parse_args()
project = args.project.resolve(strict=True)
source = args.source.resolve(strict=True)
source.relative_to(project)
if 'OpenH3M.exe'.lower() in subprocess.check_output(
        ['tasklist', '/FI', 'IMAGENAME eq OpenH3M.exe', '/FO', 'CSV', '/NH'], text=True).lower():
    raise SystemExit('Close OpenH3M before deployment')
game = project / '.local/custom-maps-play'
if not (game / 'maps/chillout.map').is_file():
    raise SystemExit('Shared converted maps are missing')
names = ['OpenH3M.exe', 'rexruntime.dll', 'rexgpu-xenos.dll', 'halo3mp_l360.dll',
         'halo3mp_q10.dll', 'halo3mp_waveshell-xbox.dll', 'halo3mp_waveslibdll.dll']
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
record = project / '.local/runtime-deployment.json'
previous = json.loads(record.read_text()) if record.exists() else {}
for name in names:
    if not (source / name).is_file():
        raise SystemExit(f'Missing source binary: {name}')
    dest = project / name
    if dest.exists() and digest(dest) not in (digest(source / name), previous.get('files', {}).get(name)):
        raise SystemExit(f'Refusing to replace an unmanaged binary: {dest}')
config = project / 'OpenH3M.bootstrap.toml'
marker = '# Managed by deploy_host_runtime.py\n'
if config.exists() and not config.read_text().startswith(marker):
    raise SystemExit('Refusing to replace an unmanaged bootstrap config')
log = project / '.local/runtime-logs/OpenH3M.log'
log.parent.mkdir(parents=True, exist_ok=True)
for path in (game / 'user', game / 'cache'):
    path.mkdir(exist_ok=True)
settings = {'game_data_root': game, 'user_data_root': game / 'user',
            'cache_root': game / 'cache', 'log_file': log}
content = marker + ''.join(f'{key} = {json.dumps(path.as_posix())}\n' for key, path in settings.items())
content += 'host_guest_output_fps = 30\nlog_max_file_size_mb = 5\nlog_max_files = 3\n'
for name in names:
    if not (project / name).exists() or digest(project / name) != digest(source / name):
        shutil.copy2(source / name, project / name)
config.write_text(content)
manifest = {'source': str(source), 'files': {name: digest(project / name) for name in names},
            'bootstrap': str(config), 'shared_game': str(game)}
record.write_text(json.dumps(manifest, indent=2) + '\n')
for name in ('Run-CustomMaps.cmd', 'Run-Warlock.cmd', 'Run-Resuscitation.cmd'):
    launcher = project / name
    if launcher.exists():
        old = launcher.read_text()
        new = re.sub(r'-Exe "[^"]+"', '-Exe "%~dp0OpenH3M.exe"', old)
        if old != new:
            launcher.write_text(new)
print(json.dumps(manifest, indent=2))
