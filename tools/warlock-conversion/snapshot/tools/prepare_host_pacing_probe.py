"""Prepare a diagnostic DLL in an owned Popen child; never patches live code."""
import ctypes as C
from ctypes import wintypes as W
import hashlib
from pathlib import Path
import pefile


def prepare(child, dll):
    if child.poll() is not None:
        raise RuntimeError('Owned game child has exited')
    dll = Path(dll).resolve(strict=True)
    kernel = C.WinDLL('kernel32', use_last_error=True)
    psapi = C.WinDLL('psapi', use_last_error=True)
    def api(lib, name, args, result=W.BOOL):
        f = getattr(lib, name); f.argtypes = args; f.restype = result
        return f
    def check(value):
        if not value: raise C.WinError(C.get_last_error())
        return value
    enum = api(psapi, 'EnumProcessModules', [W.HANDLE, C.c_void_p, W.DWORD, C.POINTER(W.DWORD)])
    name = api(psapi, 'GetModuleBaseNameW', [W.HANDLE, W.HMODULE, W.LPWSTR, W.DWORD], W.DWORD)
    close = api(kernel, 'CloseHandle', [W.HANDLE])
    alloc = api(kernel, 'VirtualAllocEx', [W.HANDLE, C.c_void_p, C.c_size_t, W.DWORD, W.DWORD], C.c_void_p)
    free = api(kernel, 'VirtualFreeEx', [W.HANDLE, C.c_void_p, C.c_size_t, W.DWORD])
    write = api(kernel, 'WriteProcessMemory', [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)])
    thread = api(kernel, 'CreateRemoteThread', [W.HANDLE, C.c_void_p, C.c_size_t, C.c_void_p, C.c_void_p, W.DWORD, C.c_void_p], W.HANDLE)
    wait = api(kernel, 'WaitForSingleObject', [W.HANDLE, W.DWORD], W.DWORD)
    result = api(kernel, 'GetExitCodeThread', [W.HANDLE, C.POINTER(W.DWORD)])
    owner = api(kernel, 'GetModuleHandleExW', [W.DWORD, C.c_void_p, C.POINTER(W.HMODULE)])
    filename = api(kernel, 'GetModuleFileNameW', [W.HMODULE, W.LPWSTR, W.DWORD], W.DWORD)
    ph = int(child._handle)
    def modules():
        handles = (W.HMODULE * 1024)(); needed = W.DWORD()
        check(enum(ph, handles, C.sizeof(handles), C.byref(needed)))
        found = {}
        for handle in handles[:needed.value // C.sizeof(W.HMODULE)]:
            text = C.create_unicode_buffer(1024)
            if name(ph, handle, text, len(text)): found[text.value.lower()] = handle
        return found
    def call(address, argument):
        th = check(thread(ph, None, 0, address, argument, 0, None))
        try:
            if wait(th, 10000) != 0:
                # Never free arguments or restart while a timed-out thread runs.
                child.kill(); child.wait(timeout=10)
                raise RuntimeError('Owned probe preparation timed out; game terminated')
            value = W.DWORD(); check(result(th, C.byref(value)))
            return value.value
        finally: close(th)
    # Resolve the *actual* module owning LoadLibraryW, including forwarders.
    # Never assume local and remote ASLR bases match.
    local = C.cast(kernel.LoadLibraryW, C.c_void_p).value
    module = W.HMODULE(); check(owner(6, local, C.byref(module)))
    path = C.create_unicode_buffer(1024); check(filename(module, path, len(path)))
    remote = modules()[Path(path.value).name.lower()] + local - module.value
    encoded = (str(dll) + '\0').encode('utf-16-le')
    argument = check(alloc(ph, None, len(encoded), 0x3000, 4))
    try:
        size = C.c_size_t(); check(write(ph, argument, encoded, len(encoded), C.byref(size)))
        if size.value != len(encoded): raise RuntimeError('Partial probe-path write')
        call(remote, argument)
    finally:
        if child.poll() is None: free(ph, argument, 0, 0x8000)
    base = modules().get(dll.name.lower())
    if base is None: raise RuntimeError('Probe DLL did not load')
    pe = pefile.PE(str(dll), fast_load=True); pe.parse_data_directories(directories=[0])
    exports = {s.name.decode(): base + s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name}
    status = call(exports['PrepareProbe'], None)
    if status: raise RuntimeError(f'Probe preparation rejected runtime: {status}')
    return {'target': exports['RefreshPaced'], 'stats': exports['ProbeState'],
            'dll_sha256': hashlib.sha256(dll.read_bytes()).hexdigest()}
