"""Observe an owned native game's existing guest-output counter.

One restored debugger breakpoint discovers the presenter instance before the
measurement window. Measurement itself only reads memory; no per-frame traps,
injected code, screenshots, input or executable changes.
"""
import ctypes as C
from ctypes import wintypes as W
import csv
import struct
import time
import pefile


def record(child, runtime, output, started, begin=110, end=155):
    kernel = C.WinDLL('kernel32', use_last_error=True)
    psapi = C.WinDLL('psapi', use_last_error=True)
    def api(lib, name, args, result=W.BOOL):
        fn = getattr(lib, name); fn.argtypes = args; fn.restype = result
        return fn
    op = api(kernel, 'OpenProcess', [W.DWORD, W.BOOL, W.DWORD], W.HANDLE)
    close = api(kernel, 'CloseHandle', [W.HANDLE])
    rpm = api(kernel, 'ReadProcessMemory', [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)])
    wpm = api(kernel, 'WriteProcessMemory', [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)])
    flush = api(kernel, 'FlushInstructionCache', [W.HANDLE, C.c_void_p, C.c_size_t])
    modules = api(psapi, 'EnumProcessModules', [W.HANDLE, C.c_void_p, W.DWORD, C.POINTER(W.DWORD)])
    modname = api(psapi, 'GetModuleBaseNameW', [W.HANDLE, W.HMODULE, W.LPWSTR, W.DWORD], W.DWORD)
    attach = api(kernel, 'DebugActiveProcess', [W.DWORD])
    detach = api(kernel, 'DebugActiveProcessStop', [W.DWORD])
    kill = api(kernel, 'DebugSetProcessKillOnExit', [W.BOOL])
    wait = api(kernel, 'WaitForDebugEvent', [C.c_void_p, W.DWORD])
    cont = api(kernel, 'ContinueDebugEvent', [W.DWORD, W.DWORD, W.DWORD])
    ot = api(kernel, 'OpenThread', [W.DWORD, W.BOOL, W.DWORD], W.HANDLE)
    get = api(kernel, 'GetThreadContext', [W.HANDLE, C.c_void_p])
    setctx = api(kernel, 'SetThreadContext', [W.HANDLE, C.c_void_p])
    def check(ok):
        if not ok: raise C.WinError(C.get_last_error())
    ph = op(0x1f0fff, False, child.pid); check(ph)
    attached = False; original = None; hook = None
    def read(address, size):
        b = C.create_string_buffer(size); n = C.c_size_t()
        check(rpm(ph, address, b, size, C.byref(n)))
        if n.value != size: raise RuntimeError('Partial frame-counter read')
        return b.raw
    def write(address, value):
        n = C.c_size_t(); check(wpm(ph, address, value, len(value), C.byref(n)))
        check(flush(ph, address, len(value)))
    try:
        while time.perf_counter() - started < 15:
            if child.poll() is not None: raise RuntimeError('Game exited before counter discovery')
            time.sleep(.05)
        handles = (W.HMODULE * 1024)(); needed = W.DWORD()
        check(modules(ph, handles, C.sizeof(handles), C.byref(needed)))
        base = None
        for h in handles[:needed.value // C.sizeof(W.HMODULE)]:
            name = C.create_unicode_buffer(260)
            if modname(ph, h, name, 260) and name.value.lower() == runtime.name.lower(): base = h
        if base is None: raise RuntimeError('Runtime module not loaded')
        pe = pefile.PE(str(runtime), fast_load=True); pe.parse_data_directories(directories=[0])
        entry = next(s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols
                     if s.name and s.name.startswith(b'?RefreshGuestOutput@Presenter@'))
        # Verified installed build: lock inc qword ptr [rdi+1b8h]. Fail closed.
        if pe.get_data(entry + 0xe3, 8) != bytes.fromhex('f048ff87b8010000'):
            raise RuntimeError('Frame-counter layout differs from verified runtime')
        hook = base + entry
        original = read(hook, 1)
        if original != b'\x55': raise RuntimeError('Unexpected presenter entry instruction')
        check(attach(child.pid)); attached = True; check(kill(False)); write(hook, b'\xcc')
        pointer = None; deadline = time.perf_counter() + 10
        while pointer is None and time.perf_counter() < deadline:
            ev = C.create_string_buffer(176)
            if not wait(ev, 100): continue
            code, pid, tid = struct.unpack_from('<III', ev)
            status = 0x10002
            if code in (3, 6):
                fh = struct.unpack_from('<Q', ev, 16)[0]
                if fh: close(fh)
            if code == 1:
                exception = struct.unpack_from('<I', ev, 16)[0]
                address = struct.unpack_from('<Q', ev, 32)[0]
                if exception == 0x80000003 and address == hook:
                    th = ot(0x1f03ff, False, tid); check(th)
                    try:
                        backing = C.create_string_buffer(1248)
                        addr = (C.addressof(backing) + 15) & ~15
                        ctx = (C.c_ubyte * 1232).from_address(addr)
                        struct.pack_into('<I', ctx, 48, 0x10001f); check(get(th, addr))
                        pointer = struct.unpack_from('<Q', ctx, 128)[0] + 0x1b8
                        write(hook, original); original = None
                        struct.pack_into('<Q', ctx, 248, hook); check(setctx(th, addr))
                    finally: close(th)
                elif exception != 0x80000003: status = 0x80010001
            check(cont(pid, tid, status))
        if pointer is None: raise RuntimeError('Presenter discovery timed out')
        check(detach(child.pid)); attached = False
        while time.perf_counter() - started < begin:
            if child.poll() is not None: raise RuntimeError('Game exited before measurement')
            time.sleep(.05)
        previous = None
        with output.open('w', newline='') as stream:
            writer = csv.writer(stream); writer.writerow(['seconds', 'guest_frame_count', 'poll_gap_ms'])
            last_poll = time.perf_counter()
            while time.perf_counter() - started < end and child.poll() is None:
                now = time.perf_counter(); count = struct.unpack('<Q', read(pointer, 8))[0]
                if count != previous:
                    writer.writerow([time.perf_counter() - started, count, (now - last_poll) * 1000])
                    previous = count
                last_poll = now
                time.sleep(.001)
        return {'counter_address': hex(pointer), 'measurement_start': begin, 'measurement_end': end,
                'method': 'one restored discovery breakpoint, then read-only counter polling'}
    finally:
        if original is not None and hook is not None and attached: write(hook, original)
        if attached: detach(child.pid)
        close(ph)
