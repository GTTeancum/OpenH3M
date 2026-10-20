"""Bounded native run plus PID-filtered PresentMon; no desktop input or capture.

Uses the runtime's process-local input script and optional native guest capture.
All generated files remain in the project's .local directory.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from build_scenario_checkpoint import output_path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--project', type=Path, required=True)
p.add_argument('--exe', type=Path, required=True)
p.add_argument('--mode', choices=('baseline', 'sdl-timer', 'no-tearing', 'ui-thread', 'honor-timers', 'vblank-unthrottled', 'ntsc-refresh', 'filtering-off'), default='baseline')
p.add_argument('--capture', action='store_true')
p.add_argument('--native-timing', action='store_true', help='Read the existing in-game frame counter without per-frame debugger traps.')
p.add_argument('--gpu-progress-timing', action='store_true', help='Also sample combined vblank/swap progress; requires --native-timing.')
p.add_argument('--guest-vblank-timing', action='store_true', help='Also sample the source-0 guest vblank handler counter.')
p.add_argument('--stock', action='store_true', help='Read original disc maps directly; keep generated files in .local.')
a = p.parse_args()
project = a.project.resolve(strict=True)
root = output_path(project / '.local', project)
game = project if a.stock else root / 'custom-maps-play'
run = output_path(root / 'pacing' / (time.strftime('%Y%m%d-%H%M%S') + '-' + ('stock-' if a.stock else '') + a.mode), project)
exe = a.exe.resolve(strict=True)
if hashlib.sha256(exe.read_bytes()).hexdigest() != 'ec4d57ee4f654095bd5e512ffe650d65ac514b0fb8f21d5c7b09e61e689c3406':
    raise SystemExit('Unexpected runtime build')
listing = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq OpenH3M.exe', '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True, check=True)
if any(row and row[0].lower() == 'openh3m.exe' for row in csv.reader(listing.stdout.splitlines())):
    raise SystemExit('OpenH3M already running')
run.mkdir(parents=True)
for name in ('temp', 'profile'):
    (run / name).mkdir()
env = dict(os.environ, TEMP=str(run / 'temp'), TMP=str(run / 'temp'),
           APPDATA=str(run / 'profile'), LOCALAPPDATA=str(run / 'profile'))
if a.mode == 'sdl-timer':
    env['SDL_TIMER_RESOLUTION'] = '1'
steps = ['45000:DOWN+120', '46000:A+250', '55000:UP+120', '56000:A+250']
steps += [f'{t}:UP+120' for t in range(58000, 68000, 1000)]
steps += ['68000:DOWN+120', '70000:A+250', '72000:A+250', '74000:DOWN+220', '95000:A+250',
          '117000:LSRIGHT+1000', '119000:LSUP+3500', '124000:RSLEFT+1800']
cmd = [str(exe), f'--game_data_root={game}', f'--user_data_root={run}',
       f'--cache_root={root / "custom-maps-play/cache"}', f'--log_file={run / "runtime.log"}',
       '--keyboard_controller=false', '--input_script=' + ','.join(steps),
       '--input_script_button_state=true', '--input_script_keystrokes=false', '--halo3mp_log_fps=true']
if a.mode == 'filtering-off':
    cmd += ['--anisotropic_override=0']
if a.mode == 'ntsc-refresh':
    cmd += ['--video_mode_refresh_rate=59.94']
if a.mode == 'no-tearing':
    cmd += ['--d3d12_allow_variable_refresh_rate_and_tearing=false']
if a.mode == 'ui-thread':
    cmd += ['--host_present_from_non_ui_thread=false']
if a.mode == 'vblank-unthrottled':
    # Diagnostic only: reject as a production fix if simulation/output speeds up.
    cmd += ['--vsync=false']
if a.capture or a.mode == 'vblank-unthrottled':
    cmd += ['--halo3mp_capture_guest_output_times_ms=52000,145000',
            f'--halo3mp_capture_guest_output_path={run / "native-output.png"}']
state = {'mode': a.mode, 'stock': a.stock, 'command': cmd, 'map_sha256': hashlib.sha256((game / 'maps/chillout.map').read_bytes()).hexdigest(),
         'SDL_TIMER_RESOLUTION': env.get('SDL_TIMER_RESOLUTION'), 'watchdog_seconds': 165}
print(run, flush=True)
with (run / 'console.log').open('wb') as out, (run / 'presentmon.log').open('wb') as pmout:
    child = subprocess.Popen(cmd, cwd=run, env=env, stdout=out, stderr=out, creationflags=subprocess.CREATE_NO_WINDOW)
    started = time.perf_counter()
    state['pid'] = child.pid
    pm = None
    try:
        if a.mode == 'honor-timers':
            # Owned child only. Honor its existing timer-resolution request even
            # when occluded; no global timer setting or persistent OS change.
            import ctypes as C
            from ctypes import wintypes as W
            kernel = C.WinDLL('kernel32', use_last_error=True)
            fn = kernel.SetProcessInformation
            fn.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD]
            fn.restype = W.BOOL
            policy = (W.DWORD * 3)(1, 4, 0)
            if not fn(int(child._handle), 4, C.byref(policy), C.sizeof(policy)):
                raise C.WinError(C.get_last_error())
            state['timer_policy'] = 'Always honor existing process timer-resolution requests'
        pm = subprocess.Popen([str(root / 'tools/PresentMon-2.6.0-x64.exe'), '--process_id', str(child.pid),
            '--delay', '110', '--timed', '45', '--terminate_after_timed', '--no_track_input',
            '--no_console_stats', '--session_name', 'H3M-pacing-' + str(child.pid),
            '--output_file', str(run / 'frames.csv')], cwd=run, env=env,
            stdout=pmout, stderr=pmout, creationflags=subprocess.CREATE_NO_WINDOW)
        if a.native_timing:
            from native_frame_timing import record
            state['native_timing'] = record(child, exe.parent / 'rexruntime.dll', run / 'guest-frames.csv', started, gpu_progress=a.gpu_progress_timing, guest_vblank=a.guest_vblank_timing)
        try:
            state['exit_code'] = child.wait(timeout=max(0.01, 165 - (time.perf_counter() - started)))
        except subprocess.TimeoutExpired:
            state['watchdog'] = True
        state['presentmon_exit_code'] = pm.wait(timeout=10)
    finally:
        for proc in (child, pm):
            if proc is not None and proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)
        (run / 'run.json').write_text(json.dumps(state, indent=2))
