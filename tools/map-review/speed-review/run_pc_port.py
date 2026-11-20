"""Load one custom-map package in the PC port without touching the user's desktop.

The game runs on a separate, never-displayed Windows desktop, muted, and is driven only by
its own timed input script; screenshots are the game's own guest-output captures. Nothing is
sent to the interactive desktop: no focus change, no cursor movement, no OS input.
"""
import argparse, ctypes as C, hashlib, json, os, shutil, subprocess, sys, time
from ctypes import wintypes as W
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/warlock-conversion/snapshot/tools'))
from dlc_menu_route import menu_route

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--build', type=Path, required=True, help='folder with halo3mp.exe and its DLLs')
p.add_argument('--game', type=Path, required=True, help='extracted disc folder (default.xex, maps, ...)')
p.add_argument('--package', type=Path, required=True, help='LIVE container to install')
p.add_argument('--map', required=True, help='internal map name, e.g. reactor')
p.add_argument('--run', type=Path, required=True, help='new run folder inside the repository')
p.add_argument('--seconds', type=int, default=170)
p.add_argument('--captures', default='60000,71500,110000,130000,150000')
p.add_argument('--extra-input', default='', help='extra steps, e.g. 120000:RSSLOWRIGHT+20000')
p.add_argument('--headless', action='store_true')
p.add_argument('--skip-install', action='store_true')
p.add_argument('--no-mute', action='store_true')
a = p.parse_args()
run = a.run.resolve(); assert run.is_relative_to(ROOT) and not run.exists()
build = a.build.resolve(strict=True); game = a.game.resolve(strict=True); package = a.package.resolve(strict=True)
(run / 'bin').mkdir(parents=True)
for f in build.iterdir():
    if f.suffix.lower() in ('.exe', '.dll') and (f.name.startswith(('halo3mp', 'rex')) or f.name.lower().startswith('sdl')):
        shutil.copy2(f, run / 'bin' / f.name)
exe = run / 'bin' / 'halo3mp.exe'; assert exe.is_file()
direction, steps = menu_route(game / 'maps/info', (), package, a.map)
inp = ['45000:DOWN+220', '46000:A+250', '55000:UP+220', '56000:A+250']
inp += [f'{58000 + n * 700}:{direction}+250' for n in range(steps)]
confirm = max(70000, 58000 + steps * 700 + 500); delay = confirm - 70000
inp += [f'{confirm}:A+250', f'{72000 + delay}:A+250', f'{74000 + delay}:DOWN+220', f'{95000 + delay}:A+250']
if a.extra_input: inp += a.extra_input.split(',')
args = [str(exe), f'--game_data_root={game}', f'--user_data_root={run}', f'--cache_root={run / "cache"}',
        f'--log_file={run / "runtime.log"}', '--keyboard_controller=false',
        '--input_script=' + ','.join(inp), '--input_script_button_state=true', '--input_script_keystrokes=false',
        '--log_level=debug', '--log_max_file_size_mb=5', '--log_max_files=4',
        f'--halo3mp_capture_guest_output_path={run / "shot.png"}', '--halo3mp_capture_guest_output_times_ms=' + a.captures]
if a.headless: args.append('--headless=true')
if not a.skip_install: args.append(f'--halo3mp_install_content={package}')
if not a.no_mute: args.append('--audio_mute=true')
(run / 'launch.json').write_text(json.dumps(dict(args=args, route=dict(direction=direction, steps=steps),
    exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(), package_sha256=hashlib.sha256(package.read_bytes()).hexdigest()), indent=1))

# --- start on a separate desktop so no window can appear or take focus on the user's desktop ---
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
desk_name = 'OpenH3MHiddenTest'
desk = user32.CreateDesktopW(desk_name, None, None, 0, 0x10000000, None)  # GENERIC_ALL
if not desk: raise C.WinError(C.get_last_error())
si = STARTUPINFOW(); si.cb = C.sizeof(si); si.lpDesktop = desk_name; pi = PROCESS_INFORMATION()
cmd = C.create_unicode_buffer(subprocess.list2cmdline(args))
if not kernel32.CreateProcessW(None, cmd, None, None, False, 0x08000000, None, str(run), C.byref(si), C.byref(pi)):  # CREATE_NO_WINDOW
    raise C.WinError(C.get_last_error())
print('started pid', pi.dwProcessId, 'on desktop', desk_name, 'route', direction, steps, flush=True)
kernel32.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
state = kernel32.WaitForSingleObject(pi.hProcess, a.seconds * 1000)
code = W.DWORD(0)
if state != 0:
    kernel32.TerminateProcess(pi.hProcess, 0); kernel32.WaitForSingleObject(pi.hProcess, 5000); outcome = 'ended by time limit'
else:
    kernel32.GetExitCodeProcess(pi.hProcess, C.byref(code)); outcome = f'exited by itself, code {code.value:#x}'
kernel32.CloseHandle(pi.hThread); kernel32.CloseHandle(pi.hProcess); user32.CloseDesktop(desk)
shots = sorted(x.name for x in run.glob('shot*.png'))
print(outcome, '| captures:', shots)
(run / 'result.json').write_text(json.dumps(dict(outcome=outcome, captures=shots), indent=1))
