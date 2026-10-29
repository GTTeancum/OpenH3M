"""One bounded native Last Resort video sweep. No host input or desktop capture."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from script_input_replay import encode

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--game', type=Path, required=True, help='Read-only original Halo 3 disc files')
parser.add_argument('--visual-confirmation', action='store_true', help='Stationary, isolated native shadow/LOD/water comparisons on the private beach fixture')
parser.add_argument('--water-interaction', action='store_true', help='Aim at the nearby water and fire matched bursts through the native process-local replay')
parser.add_argument('--shadow-confirmation', action='store_true', help='Original/Low/Medium shadows and an explicit diagnostic off control')
options = parser.parse_args()
if options.water_interaction or options.shadow_confirmation:
    options.visual_confirmation = True
run = ROOT / 'work/video-options/remaining' / time.strftime('sweep-%Y%m%d-%H%M%S')
run.mkdir(parents=True, exist_ok=False)
for name in ('temp', 'profile'):
    (run / name).mkdir()
exe = ROOT / 'work/rexglue-sdk/out/win-amd64/halo3mp.exe'
steps = ['45000:DOWN+220', '46000:A+250', '55000:UP+220', '56000:A+250',
         '70000:A+250', '72000:A+250', '74000:DOWN+220', '95000:A+250',
         '109000:RSSLOWRIGHT+61000']
# Repeat firing during each quality phase while turning in place.
steps += [f'{at}:RT+1200' for at in (116000, 128000, 140000, 152000, 164000)]
steps += [f'{at}:X+200' for at in (120000, 144000, 168000)]
replay = run / 'input.h3ir'
replay.write_bytes(encode(steps))
duration = 250 if options.visual_confirmation else 180
if options.visual_confirmation:
    steps = steps[:8]
    if options.water_interaction:
        duration = 210
        steps += ['108000:RSDOWN+250']
        steps += [f'{at}:RT+2000' for at in (143500,153500,173500,183500)]
        steps += [f'{at}:X+200' for at in (146000,156000,176000)]
    if options.shadow_confirmation:
        duration = 190
        steps += ['108000:RSDOWN+400']
    replay.write_bytes(encode(steps))
args = [str(exe), f'--game_data_root={options.game.resolve()}',
        f'--user_data_root={run}', f'--cache_root={ROOT / "work/dlc/cache"}',
        f'--log_file={run / "runtime.log"}', '--log_level=info',
        '--log_max_file_size_mb=20', '--log_max_files=2',
        '--keyboard_controller=false', f'--input_state_replay={replay}',
        '--show_settings_on_startup=true', '--halo3mp_video_sweep=true',
        f'--halo3mp_video_sweep_config={run / "custom.toml"}',
        f'--halo3mp_capture_guest_output_path={run / "scene.png"}',
        '--halo3mp_capture_guest_output_times_ms=105000,111000,117000,123000,129000,135000,141000,147000,153000,159000,165000',
        f'--d3d12_host_capture_path={run / "video-menu.bmp"}',
        '--d3d12_host_capture_after_ms=160000',
        '--host_guest_output_fps=30', '--host_present_from_non_ui_thread=false',
        '--d3d12_host_sync_interval=1', '--d3d12_host_waitable_presentation=true',
        '--d3d12_host_maximum_frame_latency=2', '--host_output_display_phase=true',
        '--d3d12_async_occlusion_readback=true']
if options.visual_confirmation:
    args = [arg for arg in args if not arg.startswith(('--halo3mp_video_sweep=', '--halo3mp_capture_guest_output_times_ms=', '--d3d12_host_capture_after_ms=', '--show_settings_on_startup='))]
    args += ['--halo3mp_video_visual_sweep=true', '--show_settings_on_startup=false',
             '--halo3mp_capture_guest_output_times_ms=105000,115000,125000,135000,145000,155000,165000,175000,185000,195000,205000,215000,225000',
             '--d3d12_host_capture_after_ms=235000']
    if options.water_interaction:
        args = [arg for arg in args if not arg.startswith(('--halo3mp_capture_guest_output_times_ms=', '--d3d12_host_capture_after_ms='))]
        args += ['--halo3mp_capture_guest_output_times_ms=115000,145000,155000,165000,175000,185000',
                 '--d3d12_host_capture_after_ms=195000']
    if options.shadow_confirmation:
        args = [arg for arg in args if not arg.startswith(('--halo3mp_video_visual_sweep=', '--halo3mp_capture_guest_output_times_ms=', '--d3d12_host_capture_after_ms='))]
        args += ['--halo3mp_video_shadow_sweep=true',
                 '--halo3mp_capture_guest_output_times_ms=111000,115000,125000,135000,145000,155000,165000,175000',
                 '--d3d12_host_capture_after_ms=180000']
env = os.environ.copy()
env.update(TEMP=str(run / 'temp'), TMP=str(run / 'temp'),
           APPDATA=str(run / 'profile'), LOCALAPPDATA=str(run / 'profile'))
manifest = {'args': args, 'exe_sha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
            'steps': steps, 'seconds_limit': duration, 'started': time.time()}
(run / 'launch.json').write_text(json.dumps(manifest, indent=2))
print(run, flush=True)
with (run / 'stdout.log').open('w') as output:
    proc = subprocess.Popen(args, cwd=run, env=env, stdout=output,
                            stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        proc.wait(timeout=duration)
        manifest['watchdog'] = False
    except subprocess.TimeoutExpired:
        proc.terminate()
        proc.wait(timeout=10)
        manifest['watchdog'] = True
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
manifest.update(returncode=proc.returncode, ended=time.time())
(run / 'result.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps({'run': str(run), 'returncode': proc.returncode, 'watchdog': manifest['watchdog']}), flush=True)
