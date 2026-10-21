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
import tomllib

from build_scenario_checkpoint import output_path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--project', type=Path, required=True)
p.add_argument('--exe', type=Path, required=True)
p.add_argument('--mode', choices=('baseline', 'sdl-timer', 'no-tearing', 'ui-thread', 'honor-timers', 'vblank-unthrottled', 'ntsc-refresh', 'filtering-off'), default='baseline')
p.add_argument('--capture', action='store_true')
p.add_argument('--host-sync-interval', type=int, choices=range(5), help='Opt-in host presentation synchronization; guest timing unchanged.')
p.add_argument('--present-timing', action='store_true', help='Read process-local DXGI presentation statistics; skip unreliable external ETW tracing.')
p.add_argument('--native-timing', action='store_true', help='Read the existing in-game frame counter without per-frame debugger traps.')
p.add_argument('--gpu-progress-timing', action='store_true', help='Also sample combined vblank/swap progress; requires --native-timing.')
p.add_argument('--guest-vblank-timing', action='store_true', help='Also sample the source-0 guest vblank handler counter.')
p.add_argument('--stock', action='store_true', help='Read original disc maps directly; keep generated files in .local.')
p.add_argument('--state-replay', type=Path, help='Replay a recorded H3IR file inside the game process instead of the canned route.')
p.add_argument('--effects-route', action='store_true', help='Extend the saved gameplay route with movement, firing and grenades inside the game process.')
p.add_argument('--portable-paths', action='store_true', help='Verify direct-launch bootstrap paths instead of passing path overrides.')
p.add_argument('--cache-root', type=Path, help='Explicit project-local cache for controlled cold/warm comparisons.')
p.add_argument('--slow-preparation-ms', type=int, choices=range(1, 1001), help='Enable threshold logging in the diagnostic GPU plugin.')
p.add_argument('--pacing-probe', type=Path, help='Explicit diagnostic DLL, owned child only; requires native timing.')
p.add_argument('--host-output-fps', type=int, choices=range(0, 361), help='Override source-patched host output pacing; 0 disables it.')
a = p.parse_args()
project = a.project.resolve(strict=True)
if a.state_replay:
    a.state_replay = a.state_replay.resolve(strict=True)
    a.state_replay.relative_to(project)
    if a.effects_route: raise SystemExit('State replay and effects route are mutually exclusive')
if a.pacing_probe:
    a.pacing_probe = a.pacing_probe.resolve(strict=True)
    a.pacing_probe.relative_to(project)
    if not a.native_timing: raise SystemExit('Pacing probe requires native timing')
root = output_path(project / '.local', project)
game = project if a.stock else root / 'custom-maps-play'
run = output_path(root / 'pacing' / (time.strftime('%Y%m%d-%H%M%S') + '-' + ('stock-' if a.stock else '') + ('host-probe-' if a.pacing_probe else '') + a.mode), project)
exe = a.exe.resolve(strict=True)
if a.state_replay and b'input_state_replay\0' not in (exe.parent / 'rexruntime.dll').read_bytes():
    raise SystemExit('This runtime lacks the opt-in recorded-state replay support')
if hashlib.sha256(exe.read_bytes()).hexdigest() != 'ec4d57ee4f654095bd5e512ffe650d65ac514b0fb8f21d5c7b09e61e689c3406':
    raise SystemExit('Unexpected runtime build')
listing = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq OpenH3M.exe', '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True, check=True)
if any(row and row[0].lower() == 'openh3m.exe' for row in csv.reader(listing.stdout.splitlines())):
    raise SystemExit('OpenH3M already running')
run.mkdir(parents=True)
cache = output_path(a.cache_root.resolve() if a.cache_root else root / 'custom-maps-play/cache', project)
cache.mkdir(parents=True, exist_ok=True)
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
if a.effects_route:
    steps += ['127000:LSUP+6500', '128000:RT+2500', '135000:LT+120',
              '137000:RSRIGHT+1400', '139000:LSUP+4000', '140000:RT+2500',
              '146000:LT+120', '149000:RSLEFT+1400']
cmd = [str(exe), f'--game_data_root={game}', f'--user_data_root={run}',
       f'--cache_root={cache}', f'--log_file={run / "runtime.log"}',
       '--keyboard_controller=false', '--input_script=' + ','.join(steps),
       '--input_script_button_state=true', '--input_script_keystrokes=false', '--halo3mp_log_fps=true']
if a.state_replay:
    cmd = [arg for arg in cmd if not arg.startswith('--input_script=')]
    cmd += [f'--input_state_replay={a.state_replay}']
if a.portable_paths:
    bootstrap = tomllib.loads(exe.with_suffix('.bootstrap.toml').read_text())
    if Path(bootstrap['game_data_root']).resolve() != game or Path(bootstrap['cache_root']).resolve() != cache:
        raise SystemExit('Bootstrap does not match the requested game/cache paths')
    output_path(Path(bootstrap['user_data_root']), project)
    cmd = [arg for arg in cmd if not arg.startswith(('--game_data_root=', '--user_data_root=', '--cache_root='))]
if a.mode == 'filtering-off':
    cmd += ['--anisotropic_override=0']
if a.host_output_fps is not None:
    cmd += [f'--host_guest_output_fps={a.host_output_fps}']
if a.host_sync_interval is not None:
    if b'd3d12_host_sync_interval\0' not in (exe.parent / 'rexruntime.dll').read_bytes():
        raise SystemExit('Runtime lacks host presentation synchronization option')
    cmd += [f'--d3d12_host_sync_interval={a.host_sync_interval}']
if a.present_timing:
    if b'd3d12_log_present_timing\0' not in (exe.parent / 'rexruntime.dll').read_bytes():
        raise SystemExit('Runtime lacks native presentation timing')
    cmd += ['--d3d12_log_present_timing=true']
if a.slow_preparation_ms is not None:
    cmd += [f'--d3d12_slow_preparation_ms={a.slow_preparation_ms}']
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
         'runtime_sha256': hashlib.sha256((exe.parent / 'rexruntime.dll').read_bytes()).hexdigest(),
         'gpu_sha256': hashlib.sha256((exe.parent / 'rexgpu-xenos.dll').read_bytes()).hexdigest(),
         'cache_root': str(cache),
         'state_replay_sha256': hashlib.sha256(a.state_replay.read_bytes()).hexdigest() if a.state_replay else None,
         'host_output_fps_override': a.host_output_fps,
         'SDL_TIMER_RESOLUTION': env.get('SDL_TIMER_RESOLUTION'), 'watchdog_seconds': 165}
print(run, flush=True)
with (run / 'console.log').open('wb') as out, (run / 'presentmon.log').open('wb') as pmout:
    child = subprocess.Popen(cmd, cwd=run, env=env, stdout=out, stderr=out, creationflags=subprocess.CREATE_NO_WINDOW)
    started = time.perf_counter()
    state['started_unix_seconds'] = time.time()
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
        if not a.present_timing:
            pm = subprocess.Popen([str(root / 'tools/PresentMon-2.6.0-x64.exe'), '--process_id', str(child.pid),
                '--delay', '110', '--timed', '45', '--terminate_after_timed', '--no_track_input',
                '--no_console_stats', '--session_name', 'H3M-pacing-' + str(child.pid),
                '--output_file', str(run / 'frames.csv')], cwd=run, env=env,
                stdout=pmout, stderr=pmout, creationflags=subprocess.CREATE_NO_WINDOW)
        if a.native_timing:
            from native_frame_timing import record
            state['native_timing'] = record(child, exe.parent / 'rexruntime.dll', run / 'guest-frames.csv', started, gpu_progress=a.gpu_progress_timing, guest_vblank=a.guest_vblank_timing, pacing_probe=a.pacing_probe)
        try:
            state['exit_code'] = child.wait(timeout=max(0.01, 165 - (time.perf_counter() - started)))
        except subprocess.TimeoutExpired:
            state['watchdog'] = True
        state['presentmon_exit_code'] = pm.wait(timeout=10) if pm else None
        state['presentation_method'] = 'native DXGI statistics' if a.present_timing else 'PresentMon; validate CSV and lost events separately'
    except Exception as error:
        state['harness_error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        state['child_exit_before_cleanup'] = child.poll()
        for proc in (child, pm):
            if proc is not None and proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)
        (run / 'run.json').write_text(json.dumps(state, indent=2))
