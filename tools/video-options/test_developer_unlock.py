"""Bounded native OFF/ON/OFF run; input is entirely inside the game process."""
import json
import argparse
import os
from pathlib import Path
import subprocess
import time
import tomllib
import sys

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--map', help='Stock/internal map name for existing process-local menu route')
options = parser.parse_args()
RUN = ROOT / '.local/developer-framerate' / time.strftime('test-%Y%m%d-%H%M%S')
BUILD = ROOT / 'work/rexglue-sdk/out/win-amd64'
settings = tomllib.loads(Path('C:/X360/ISOs/H3M/OpenH3M.bootstrap.toml').read_text())
for name in ('temp', 'profile'):
    (RUN / name).mkdir(parents=True, exist_ok=True)
settings.update(halo3mp_dev_unlock_test=True, halo3mp_log_fps=True,
                log_file=str(RUN / 'runtime.log'), log_max_file_size_mb=50,
                halo3mp_capture_guest_output_times_ms='35000,55000,80000',
                halo3mp_capture_guest_output_path=str(RUN / 'native.png'))
if options.map:
    sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
    from dlc_menu_route import menu_route
    direction, steps = menu_route(Path(settings['game_data_root']) / 'maps/info',
                                 (Path(settings['user_data_root']),), None, options.map)
    script = ['45000:DOWN+220', '46000:A+250', '55000:UP+220', '56000:A+250']
    script += [f'{58000+n*700}:{direction}+120' for n in range(steps)]
    script += ['70000:A+250', '72000:A+250', '74000:DOWN+220', '95000:A+250']
    settings.update(input_script=','.join(script), input_script_button_state=True,
                    input_script_keystrokes=False, halo3mp_dev_unlock_test_on_ms=125000,
                    halo3mp_dev_unlock_test_off_ms=150000,
                    halo3mp_capture_guest_output_times_ms='115000,140000,165000')
args = [str(BUILD / 'halo3mp.exe')] + [
    f'--{key}={str(value).lower() if isinstance(value, bool) else value}'
    for key, value in settings.items()]
env = dict(os.environ, TEMP=str(RUN / 'temp'), TMP=str(RUN / 'temp'),
           APPDATA=str(RUN / 'profile'), LOCALAPPDATA=str(RUN / 'profile'))
print(RUN, flush=True)
with (RUN / 'console.log').open('wb') as console:
    child = subprocess.Popen(args, cwd=ROOT, env=env, stdout=console, stderr=console)
    (RUN / 'run.json').write_text(json.dumps(dict(pid=child.pid, args=args), indent=2))
    try:
        child.wait(timeout=178 if options.map else 95)
    except subprocess.TimeoutExpired:
        child.terminate()
        child.wait(timeout=10)
print(f'Finished bounded test: {RUN}', flush=True)
