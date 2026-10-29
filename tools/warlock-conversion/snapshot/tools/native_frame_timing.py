"""Observe an owned native game's existing guest-output counter.

Restored debugger breakpoints discover existing counter addresses before the
measurement window. Measurement itself only reads memory; no per-frame traps.
The explicit pacing_probe option prepares a host-only diagnostic DLL and arms
it at the stopped presenter entry. Default runs restore every discovery byte.
"""
import ctypes as C
from ctypes import wintypes as W
import csv
import hashlib
import struct
import time
import pefile


def record(child, runtime, output, started, begin=110, end=155, gpu_progress=False, guest_vblank=False, pacing_probe=None):
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
    attached = False; originals = {}; pointers = {}
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
        probe = None
        if pacing_probe:
            from prepare_host_pacing_probe import prepare
            probe = prepare(child, pacing_probe)
        handles = (W.HMODULE * 1024)(); needed = W.DWORD()
        check(modules(ph, handles, C.sizeof(handles), C.byref(needed)))
        base = None; gpu_base = None; exe_base = None
        for h in handles[:needed.value // C.sizeof(W.HMODULE)]:
            name = C.create_unicode_buffer(260)
            if modname(ph, h, name, 260):
                if name.value.lower() == runtime.name.lower(): base = h
                if name.value.lower() == 'rexgpu-xenos.dll': gpu_base = h
                if name.value.lower() == 'openh3m.exe': exe_base = h
        if base is None: raise RuntimeError('Runtime module not loaded')
        pe = pefile.PE(str(runtime), fast_load=True); pe.parse_data_directories(directories=[0])
        entry = next(s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols
                     if s.name and s.name.startswith(b'?RefreshGuestOutput@Presenter@'))
        accessor = next((s for s in pe.DIRECTORY_ENTRY_EXPORT.symbols
                         if s.name == b'RexHostGuestOutputCount'), None)
        counter_offset = 0x1b8
        if accessor:
            # Compiled read-only accessor: mov rax,[rcx+disp32]; ret.
            code = pe.get_data(accessor.address, 8)
            if code[:3] != b'\x48\x8b\x81' or code[7:] != b'\xc3':
                raise RuntimeError('Unsupported native counter accessor layout')
            counter_offset = struct.unpack_from('<i', code, 3)[0]
            if not 0 < counter_offset < 0x4000:
                raise RuntimeError('Invalid presenter counter offset')
        elif pe.get_data(entry + 0xe3, 8) != bytes.fromhex('f048ff87b8010000'):
            raise RuntimeError('Frame-counter layout differs from verified runtime')
        hook = base + entry
        if read(hook, 1) != b'\x55': raise RuntimeError('Unexpected presenter entry instruction')
        hooks = {hook: ('guest', 128, counter_offset)}  # Win64 CONTEXT RCX
        if gpu_progress:
            gpu_path = runtime.parent / 'rexgpu-xenos.dll'
            if hashlib.sha256(gpu_path.read_bytes()).hexdigest() != 'aed76f757f9c570923e90ec99d26305f368857e972ea9d97b650af1ce806bc94':
                raise RuntimeError('Unexpected GPU runtime build')
            gpu = pefile.PE(str(gpu_path), fast_load=True)
            # Verified worker increments [RAX+78h]; swaps also increment it.
            # This is GPU progress, NOT an isolated virtual-vblank clock.
            if gpu_base is None or gpu.get_data(0x1552b, 3) != bytes.fromhex('ff4078'):
                raise RuntimeError('Unsupported gpu_progress counter layout')
            hooks[gpu_base + 0x1552b] = ('gpu_progress', 120, 0x78)  # CONTEXT RAX
        if guest_vblank:
            exe_path = runtime.parent / 'OpenH3M.exe'
            if hashlib.sha256(exe_path.read_bytes()).hexdigest() != 'ec4d57ee4f654095bd5e512ffe650d65ac514b0fb8f21d5c7b09e61e689c3406':
                raise RuntimeError('Unexpected game runtime build')
            ep = pefile.PE(str(exe_path), fast_load=True)
            if exe_base is None or ep.get_data(0x1c7c0e0, 4) != bytes.fromhex('4883ec48') or ep.get_data(0x1c7c233, 5) != bytes.fromhex('0594400000'):
                raise RuntimeError('Unexpected guest vblank handler')
            hooks[exe_base + 0x1c7c0e0] = ('guest_vblank', 128, 0x4094)
        check(attach(child.pid)); attached = True; check(kill(False))
        for address in hooks:
            originals[address] = read(address, 1)
            write(address, b'\xcc')
        deadline = time.perf_counter() + 10
        while len(pointers) < len(hooks) and time.perf_counter() < deadline:
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
                if exception == 0x80000003 and address in originals:
                    th = ot(0x1f03ff, False, tid); check(th)
                    try:
                        backing = C.create_string_buffer(1248)
                        addr = (C.addressof(backing) + 15) & ~15
                        ctx = (C.c_ubyte * 1232).from_address(addr)
                        struct.pack_into('<I', ctx, 48, 0x10001f); check(get(th, addr))
                        name, register, offset = hooks[address]
                        if name == 'guest_vblank':
                            ppc = struct.unpack_from('<Q', ctx, 128)[0]
                            memory = struct.unpack_from('<Q', ctx, 136)[0]
                            device = struct.unpack('<Q', read(ppc, 8))[0] & 0xffffffff
                            if not 0x1000 <= device < 0xe0000000:
                                raise RuntimeError('Unexpected guest device address')
                            pointers[name] = memory + device + offset
                        else:
                            pointers[name] = struct.unpack_from('<Q', ctx, register)[0] + offset
                        write(address, originals.pop(address))
                        if probe and name == 'guest':
                            # All threads are stopped at this debugger event;
                            # this is the single guest-output producer's entry.
                            expected = bytes.fromhex('55415741565657534881ec88000000')
                            if read(address, 15) != expected:
                                raise RuntimeError('Probe prologue changed before arming')
                            write(address, b'\xff\x25\0\0\0\0' + struct.pack('<Q', probe['target']) + b'\x90')
                            probe['armed_seconds'] = time.perf_counter() - started
                        struct.pack_into('<Q', ctx, 248, address); check(setctx(th, addr))
                    finally: close(th)
                elif exception != 0x80000003: status = 0x80010001
            check(cont(pid, tid, status))
        if len(pointers) != len(hooks): raise RuntimeError('Counter discovery timed out')
        pointer = pointers['guest']
        check(detach(child.pid)); attached = False
        while time.perf_counter() - started < begin:
            if child.poll() is not None: raise RuntimeError('Game exited before measurement')
            time.sleep(.05)
        previous = None; previous_gpu_progress = None; previous_guest_vblank = None; previous_guest_flip = None
        d3d_callbacks = None
        if guest_vblank:
            device_host = pointers['guest_vblank'] - 0x4094
            d3d_callbacks = list(struct.unpack('>II', read(device_host + 0x408c, 8)))
            writeback_guest = struct.unpack('>I', read(device_host + 0x2a94, 4))[0]
            if writeback_guest < 0x1000:
                raise RuntimeError(f'Unexpected D3D writeback address {writeback_guest:#x}')
            # Match the installed generated PPC memory access: physical aliases
            # E0000000..FFFFFFFF include the runtime's extra 4 KiB mapping gap.
            writeback_host = memory + writeback_guest + (0x1000 if writeback_guest >= 0xe0000000 else 0)
        from contextlib import ExitStack
        with ExitStack() as stack:
            stream = stack.enter_context(output.open('w', newline=''))
            if gpu_progress:
                vstream = stack.enter_context(output.with_name('gpu-progress.csv').open('w', newline=''))
                vwriter = csv.writer(vstream); vwriter.writerow(['seconds', 'gpu_progress_count', 'poll_gap_ms'])
            if guest_vblank:
                gvstream = stack.enter_context(output.with_name('guest-vblank.csv').open('w', newline=''))
                gvwriter = csv.writer(gvstream); gvwriter.writerow(['seconds', 'guest_vblank_count', 'poll_gap_ms'])
                flipstream = stack.enter_context(output.with_name('guest-flip.csv').open('w', newline=''))
                flipwriter = csv.writer(flipstream); flipwriter.writerow(['seconds', 'guest_flip_count', 'poll_gap_ms'])
                queue_stream = stack.enter_context(output.with_name('guest-queue.csv').open('w', newline=''))
                queue_writer = csv.writer(queue_stream)
                queue_writer.writerow(['seconds', 'vblank', 'completed', 'head', 'tail',
                                       'poll_gap_ms', 'last_requested_target', 'issued',
                                       'interrupt_callback', 'interrupt_argument'] + [f'slot_{i}_{field}' for i in range(16)
                                                        for field in ('buffer', 'target_vblank')])
            writer = csv.writer(stream); writer.writerow(['seconds', 'guest_frame_count', 'poll_gap_ms'])
            last_poll = time.perf_counter()
            while time.perf_counter() - started < end and child.poll() is None:
                now = time.perf_counter(); count = struct.unpack('<Q', read(pointer, 8))[0]
                if count != previous:
                    writer.writerow([time.perf_counter() - started, count, (now - last_poll) * 1000])
                    previous = count
                if gpu_progress:
                    vc = struct.unpack('<I', read(pointers['gpu_progress'], 4))[0]
                    if vc != previous_gpu_progress:
                        vwriter.writerow([time.perf_counter() - started, vc, (now - last_poll) * 1000])
                        previous_gpu_progress = vc
                if guest_vblank:
                    # One bounded snapshot through device+0x4130. The original
                    # D3D interrupt compares each ring entry's target vblank to
                    # +0x4094 before advancing +0x40a8. Read only; cross-thread
                    # writes can still make a snapshot transiently inconsistent.
                    state = read(pointers['guest_vblank'], 0xa0)
                    gc = struct.unpack_from('>I', state, 0)[0]
                    fc = struct.unpack_from('>I', state, 20)[0]
                    if gc != previous_guest_vblank or fc != previous_guest_flip:
                        head, tail = struct.unpack_from('>II', state, 0x98)
                        slots = struct.unpack_from('>32I', state, 0x18)
                        interrupt = struct.unpack('>II', read(writeback_host + 0x10, 8))
                        queue_writer.writerow([time.perf_counter() - started, gc, fc, head, tail,
                                               (now - last_poll) * 1000,
                                               struct.unpack_from('>I', state, 8)[0],
                                               struct.unpack_from('>I', state, 16)[0], *interrupt, *slots])
                    if fc != previous_guest_flip:
                        flipwriter.writerow([time.perf_counter() - started, fc, (now - last_poll) * 1000])
                        previous_guest_flip = fc
                    if gc != previous_guest_vblank:
                        gvwriter.writerow([time.perf_counter() - started, gc, (now - last_poll) * 1000])
                        previous_guest_vblank = gc
                last_poll = now
                time.sleep(.001)
        if probe:
            values = struct.unpack('<IIQQQQ', read(probe['stats'], 40))
            probe['counters'] = dict(zip(('version', 'prepared', 'calls', 'paced', 'waits', 'late'), values))
        return {'counter_address': hex(pointer), 'gpu_progress_counter_address': hex(pointers.get('gpu_progress', 0)), 'guest_vblank_counter_address': hex(pointers.get('guest_vblank', 0)), 'd3d_callbacks': d3d_callbacks, 'measurement_start': begin, 'measurement_end': end,
                'pacing_probe': probe,
                'method': f'{len(hooks)} discovery breakpoints, read-only counter polling' + ('; explicit host pacing probe armed while debugger stopped all threads' if probe else '; original instructions restored')}
    finally:
        if attached:
            for address, original in originals.items(): write(address, original)
        if attached: detach(child.pid)
        close(ph)
