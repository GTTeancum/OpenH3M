"""Run one map that lives in a repo-local game folder (no LIVE package) in the PC port, on a hidden desktop.

Same method as tools/map-review/speed-review/run_pc_port.py (separate never-shown desktop, muted, the game's own
timed input script and guest-output captures; no focus change, cursor movement or OS input), for a stock map slot
whose map file was replaced in a private game folder, e.g. an Inject360 output.

  python run_stock_map.py --game <repo game folder> --map sandbox --run <new run folder in repo> [--seconds 170]
"""
import argparse, ctypes as C, json, shutil, subprocess, sys, time
from ctypes import wintypes as W
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from dlc_menu_route import menu_route

BUILD = Path('C:/X360/ISOs/H3M/.local/OpenH3M-source/work/rexglue-sdk/out/win-amd64')
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--game', type=Path, required=True)
p.add_argument('--map', required=True)
p.add_argument('--run', type=Path, required=True)
p.add_argument('--seconds', type=int, default=170)
p.add_argument('--captures', default='60000,71500,110000,130000,150000')
p.add_argument('--extra-input', default='')
p.add_argument('--extra-args', default='', help='extra game options, space separated')
p.add_argument('--forge', action='store_true', help='start the map in Forge instead of Custom Games (one entry lower on the main menu)')
p.add_argument('--build', type=Path, default=None, help='folder holding halo3mp.exe and its DLLs (default: the installed developer build)')
a = p.parse_args()
run = a.run.resolve(); game = a.game.resolve(strict=True)
assert run.is_relative_to(ROOT) and game.is_relative_to(ROOT) and not run.exists()
running = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
assert 'halo3mp.exe' not in running and 'xenia' not in running, 'a game instance is already running'
(run / 'bin').mkdir(parents=True)
for f in (a.build.resolve(strict=True) if a.build else BUILD).iterdir():
    if f.suffix.lower() in ('.exe', '.dll') and (f.name.startswith(('halo3mp', 'rex')) or f.name.lower().startswith('sdl')):
        shutil.copy2(f, run / 'bin' / f.name)
exe = run / 'bin' / 'halo3mp.exe'
direction, steps = menu_route(game / 'maps/info', (), None, a.map)
inp = ['45000:DOWN+220', '46000:A+250', '55000:UP+220', '56000:A+250']
if a.forge: inp.insert(1, '45500:DOWN+220')   # same route as trace_loading.py's Forge checks
inp += [f'{58000 + n * 700}:{direction}+250' for n in range(steps)]
confirm = max(70000, 58000 + steps * 700 + 500); delay = confirm - 70000
inp += [f'{confirm}:A+250', f'{72000 + delay}:A+250', f'{74000 + delay}:DOWN+220', f'{95000 + delay}:A+250']
if a.extra_input: inp += a.extra_input.split(',')
args = [str(exe), f'--game_data_root={game}', f'--user_data_root={run}', f'--cache_root={run / "cache"}',
        f'--log_file={run / "runtime.log"}', '--keyboard_controller=false',
        '--input_script=' + ','.join(inp), '--input_script_button_state=true', '--input_script_keystrokes=false',
        '--log_level=debug', '--log_max_file_size_mb=5', '--log_max_files=4',
        f'--halo3mp_capture_guest_output_path={run / "shot.png"}',
        '--halo3mp_capture_guest_output_times_ms=' + a.captures, '--audio_mute=true'] + a.extra_args.split()
(run / 'launch.json').write_text(json.dumps(dict(args=args, route=[direction, steps]), indent=1))

user32 = C.WinDLL('user32', use_last_error=True); kernel32 = C.WinDLL('kernel32', use_last_error=True)
class STARTUPINFOW(C.Structure):
    _fields_ = [('cb', W.DWORD), ('lpReserved', W.LPWSTR), ('lpDesktop', W.LPWSTR), ('lpTitle', W.LPWSTR), ('dwX', W.DWORD), ('dwY', W.DWORD),
                ('dwXSize', W.DWORD), ('dwYSize', W.DWORD), ('dwXCountChars', W.DWORD), ('dwYCountChars', W.DWORD), ('dwFillAttribute', W.DWORD),
                ('dwFlags', W.DWORD), ('wShowWindow', W.WORD), ('cbReserved2', W.WORD), ('lpReserved2', C.c_void_p),
                ('hStdInput', W.HANDLE), ('hStdOutput', W.HANDLE), ('hStdError', W.HANDLE)]
class PROCESS_INFORMATION(C.Structure):
    _fields_ = [('hProcess', W.HANDLE), ('hThread', W.HANDLE), ('dwProcessId', W.DWORD), ('dwThreadId', W.DWORD)]
user32.CreateDesktopW.restype = W.HANDLE
user32.CreateDesktopW.argtypes = [W.LPCWSTR, W.LPCWSTR, C.c_void_p, W.DWORD, W.DWORD, C.c_void_p]
kernel32.CreateProcessW.argtypes = [W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL, W.DWORD, C.c_void_p, W.LPCWSTR, C.POINTER(STARTUPINFOW), C.POINTER(PROCESS_INFORMATION)]
kernel32.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
desk_name = 'OpenH3MInject360Test'
desk = user32.CreateDesktopW(desk_name, None, None, 0, 0x10000000, None)
if not desk: raise C.WinError(C.get_last_error())
si = STARTUPINFOW(); si.cb = C.sizeof(si); si.lpDesktop = desk_name; pi = PROCESS_INFORMATION()
cmd = C.create_unicode_buffer(subprocess.list2cmdline(args))
if not kernel32.CreateProcessW(None, cmd, None, None, False, 0x08000000, None, str(run), C.byref(si), C.byref(pi)):
    raise C.WinError(C.get_last_error())
print('started pid', pi.dwProcessId, 'route', direction, steps, flush=True)
state = kernel32.WaitForSingleObject(pi.hProcess, a.seconds * 1000)
code = W.DWORD(0)
if state != 0:
    kernel32.TerminateProcess(pi.hProcess, 0); kernel32.WaitForSingleObject(pi.hProcess, 5000); outcome = 'ended by time limit'
else:
    kernel32.GetExitCodeProcess(pi.hProcess, C.byref(code)); outcome = f'exited by itself, code {code.value:#x}'
kernel32.CloseHandle(pi.hThread); kernel32.CloseHandle(pi.hProcess); user32.CloseDesktop(desk)
shots = sorted(x.name for x in run.glob('*.png'))
print(outcome, '| captures:', shots)
(run / 'result.json').write_text(json.dumps(dict(outcome=outcome, captures=shots), indent=1))
shutil.rmtree(run / 'bin', ignore_errors=True)   # the exe copy is not evidence
