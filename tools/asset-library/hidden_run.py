"""Run a command on a private, invisible Windows desktop.

Any dialog the program raises (for example a ManagedBlam assert box) appears
on that desktop, never on the user's screen. If the program is still running
at the timeout (typically blocked on such a dialog) it is terminated and the
run is reported as failed. Output is captured through cmd redirection.

Usage: run(cmd_list, cwd, log_path, timeout=600, env=None) -> (exit_code, text)
"""
import ctypes as C
import ctypes.wintypes as W
import os
import subprocess
import uuid
from pathlib import Path

user32 = C.WinDLL('user32', use_last_error=True)
kernel32 = C.WinDLL('kernel32', use_last_error=True)


class STARTUPINFOW(C.Structure):
    _fields_ = [('cb', W.DWORD), ('lpReserved', W.LPWSTR), ('lpDesktop', W.LPWSTR), ('lpTitle', W.LPWSTR),
                ('dwX', W.DWORD), ('dwY', W.DWORD), ('dwXSize', W.DWORD), ('dwYSize', W.DWORD),
                ('dwXCountChars', W.DWORD), ('dwYCountChars', W.DWORD), ('dwFillAttribute', W.DWORD),
                ('dwFlags', W.DWORD), ('wShowWindow', W.WORD), ('cbReserved2', W.WORD),
                ('lpReserved2', C.c_void_p), ('hStdInput', W.HANDLE), ('hStdOutput', W.HANDLE), ('hStdError', W.HANDLE)]


class PROCESS_INFORMATION(C.Structure):
    _fields_ = [('hProcess', W.HANDLE), ('hThread', W.HANDLE), ('dwProcessId', W.DWORD), ('dwThreadId', W.DWORD)]


user32.CreateDesktopW.restype = W.HANDLE
user32.CreateDesktopW.argtypes = [W.LPCWSTR, W.LPCWSTR, C.c_void_p, W.DWORD, W.DWORD, C.c_void_p]
user32.CloseDesktop.argtypes = [W.HANDLE]
kernel32.CreateProcessW.argtypes = [W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL, W.DWORD, C.c_void_p,
                                    W.LPCWSTR, C.POINTER(STARTUPINFOW), C.POINTER(PROCESS_INFORMATION)]
kernel32.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
kernel32.GetExitCodeProcess.argtypes = [W.HANDLE, C.POINTER(W.DWORD)]
kernel32.CloseHandle.argtypes = [W.HANDLE]
CREATE_NO_WINDOW = 0x08000000
CREATE_UNICODE_ENVIRONMENT = 0x00000400


def run(cmd, cwd, log_path, timeout=600, env=None):
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    inner = subprocess.list2cmdline([str(c) for c in cmd])
    line = 'cmd.exe /d /s /c "' + inner + ' > "' + str(log_path) + '" 2>&1"'
    name = 'openh3m-asset-' + uuid.uuid4().hex[:8]
    desk = user32.CreateDesktopW(name, None, None, 0, 0x10000000, None)  # GENERIC_ALL
    if not desk:
        raise OSError('CreateDesktop failed %d' % C.get_last_error())
    block = None
    if env is not None:
        text = ''.join('%s=%s\0' % kv for kv in sorted(env.items())) + '\0'
        block = C.create_unicode_buffer(text, len(text))
    si = STARTUPINFOW(); si.cb = C.sizeof(si); si.lpDesktop = name
    pi = PROCESS_INFORMATION()
    try:
        if not kernel32.CreateProcessW(None, C.create_unicode_buffer(line), None, None, False,
                                       CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT,
                                       C.cast(block, C.c_void_p) if block is not None else None,
                                       str(cwd), C.byref(si), C.byref(pi)):
            raise OSError('CreateProcess failed %d' % C.get_last_error())
        timed_out = kernel32.WaitForSingleObject(pi.hProcess, int(timeout * 1000)) != 0
        if timed_out:
            # Kill the whole tree (the tool and any dialog it is blocked on).
            subprocess.run(['taskkill', '/T', '/F', '/PID', str(pi.dwProcessId)], capture_output=True)
            kernel32.WaitForSingleObject(pi.hProcess, 10000)
        code = W.DWORD()
        kernel32.GetExitCodeProcess(pi.hProcess, C.byref(code))
        kernel32.CloseHandle(pi.hThread); kernel32.CloseHandle(pi.hProcess)
    finally:
        user32.CloseDesktop(desk)
    text = log_path.read_text(encoding='utf-8', errors='replace') if log_path.exists() else ''
    if timed_out:
        text += '\nHIDDEN_RUN_TIMEOUT: process killed after %ss (likely blocked on a dialog)\n' % timeout
        return -999, text
    return code.value, text
