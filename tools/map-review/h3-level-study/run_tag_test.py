"""Run the editing kit's halo3_tag_test.exe on a separate, never-displayed desktop with a given
init.txt, for a fixed time, then end it. No window reaches the user's desktop; no input is sent.
Usage: run_tag_test.py <init.txt source> <seconds>"""
import ctypes as C, ctypes.wintypes as W, sys, shutil, subprocess
from pathlib import Path
KIT = Path(r"C:\Programming\GitHub\OpenH3M\.local\h3ek-source")
src, seconds = Path(sys.argv[1]), int(sys.argv[2])
init = KIT / "init.txt"
if init.exists():
    raise SystemExit("kit init.txt already exists; not overwriting it")
shutil.copy(src, init)
try:
    user32 = C.WinDLL("user32", use_last_error=True); kernel32 = C.WinDLL("kernel32", use_last_error=True)
    class SI(C.Structure):
        _fields_ = [("cb", W.DWORD), ("lpReserved", W.LPWSTR), ("lpDesktop", W.LPWSTR), ("lpTitle", W.LPWSTR), ("dwX", W.DWORD), ("dwY", W.DWORD),
                    ("dwXSize", W.DWORD), ("dwYSize", W.DWORD), ("dwXCountChars", W.DWORD), ("dwYCountChars", W.DWORD), ("dwFillAttribute", W.DWORD),
                    ("dwFlags", W.DWORD), ("wShowWindow", W.WORD), ("cbReserved2", W.WORD), ("lpReserved2", C.c_void_p),
                    ("hStdInput", W.HANDLE), ("hStdOutput", W.HANDLE), ("hStdError", W.HANDLE)]
    class PI(C.Structure):
        _fields_ = [("hProcess", W.HANDLE), ("hThread", W.HANDLE), ("dwProcessId", W.DWORD), ("dwThreadId", W.DWORD)]
    user32.CreateDesktopW.restype = W.HANDLE
    user32.CreateDesktopW.argtypes = [W.LPCWSTR, W.LPCWSTR, C.c_void_p, W.DWORD, W.DWORD, C.c_void_p]
    kernel32.CreateProcessW.argtypes = [W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL, W.DWORD, C.c_void_p, W.LPCWSTR, C.POINTER(SI), C.POINTER(PI)]
    kernel32.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
    name = "OpenH3MHiddenTagTest"
    desk = user32.CreateDesktopW(name, None, None, 0, 0x10000000, None)
    if not desk: raise C.WinError(C.get_last_error())
    si = SI(); si.cb = C.sizeof(si); si.lpDesktop = name; pi = PI()
    cmd = C.create_unicode_buffer(subprocess.list2cmdline([str(KIT / "halo3_tag_test.exe")]))
    if not kernel32.CreateProcessW(None, cmd, None, None, False, 0x08000000, None, str(KIT), C.byref(si), C.byref(pi)):
        raise C.WinError(C.get_last_error())
    print("started pid", pi.dwProcessId, flush=True)
    import time, json
    script = json.loads(sys.argv[3]) if len(sys.argv) > 3 else []   # [[at_seconds, "console text"], ...]
    t0 = time.time()
    EnumProc = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    user32.EnumDesktopWindows.argtypes = [W.HANDLE, EnumProc, W.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    user32.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    def windows():
        found = []
        def cb(h, _):
            pid = W.DWORD(); user32.GetWindowThreadProcessId(h, C.byref(pid))
            if pid.value == pi.dwProcessId: found.append(h)
            return True
        user32.EnumDesktopWindows(desk, EnumProc(cb), 0); return found
    def post(h, text):
        # message posting to the hidden game's own window only (no OS-level input, no focus change)
        for ch in text:
            if ch == "`":
                user32.PostMessageW(h, 0x100, 0xC0, 0x00290001); time.sleep(0.05); user32.PostMessageW(h, 0x101, 0xC0, 0xC0290001)
            elif ch == "\n":
                user32.PostMessageW(h, 0x100, 0x0D, 0x001C0001); user32.PostMessageW(h, 0x102, 0x0D, 0x001C0001); user32.PostMessageW(h, 0x101, 0x0D, 0xC01C0001)
            else:
                user32.PostMessageW(h, 0x102, ord(ch), 1)
            time.sleep(0.03)
    for at, text in script:
        while time.time() - t0 < at:
            if kernel32.WaitForSingleObject(pi.hProcess, 200) == 0: break
        if text.startswith("!mv "):   # host-side: rename a kit-root output file between steps
            a, b = text[4:].split(" ", 1); time.sleep(1.5)
            try: (KIT / a).replace(Path(b)); print(f"t={time.time()-t0:.0f}s moved {a} -> {b}", flush=True)
            except OSError as e: print("move failed", a, e, flush=True)
            continue
        ws = windows(); print(f"t={time.time()-t0:.0f}s windows={len(ws)} send {text!r}", flush=True)
        for h in ws: post(h, text)
    state = kernel32.WaitForSingleObject(pi.hProcess, max(0, int((seconds - (time.time() - t0)) * 1000)))
    if state != 0:
        kernel32.TerminateProcess(pi.hProcess, 0); kernel32.WaitForSingleObject(pi.hProcess, 5000); print("ended by time limit")
    else:
        code = W.DWORD(0); kernel32.GetExitCodeProcess(pi.hProcess, C.byref(code)); print(f"exited by itself {code.value:#x}")
    kernel32.CloseHandle(pi.hThread); kernel32.CloseHandle(pi.hProcess); user32.CloseDesktop(desk)
finally:
    init.unlink()
