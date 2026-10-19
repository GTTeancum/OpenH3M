"""Bounded debugger logging for our own OpenH3M child; no UI or host input.

Software breakpoints execute the original instruction using single-step, and are
restored on detach. No executable files, guest checks, or return values are changed.
"""
import argparse
import hashlib
import ctypes as C
import csv
from ctypes import wintypes as W
import json
import os
import shutil
from pathlib import Path
import struct
import subprocess
import sys
import time
import pefile

from build_scenario_checkpoint import output_path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--project', type=Path, required=True)
parser.add_argument('--exe', type=Path, required=True)
parser.add_argument('--game', type=Path)
parser.add_argument('--capture', action='store_true')
parser.add_argument('--shader-cache-seed', type=Path)
parser.add_argument('--seconds', type=int, default=135, choices=range(135, 181))
options = parser.parse_args()
ROOT = options.project.resolve(strict=True)
RUN = output_path(ROOT / '.local/loading-traces' / (time.strftime('%Y%m%d-%H%M%S') + f'-{os.getpid()}'), ROOT)
GAME = output_path(options.game or ROOT / '.local/warlock-play', ROOT)
EXE = options.exe.resolve(strict=True)
if hashlib.sha256(EXE.read_bytes()).hexdigest() != 'ec4d57ee4f654095bd5e512ffe650d65ac514b0fb8f21d5c7b09e61e689c3406':
    raise SystemExit('This diagnostic requires the verified runtime build; function addresses are build-specific.')
if not (GAME / 'maps/lockout.map').is_file():
    raise SystemExit('Missing staged Warlock map')
listing = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq OpenH3M.exe', '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True, check=True)
if any(row and row[0].casefold() == 'openh3m.exe' for row in csv.reader(listing.stdout.splitlines())):
    raise SystemExit('An OpenH3M process is already running; refusing a parallel test.')
FUNCS = {0x821B0DD0: 'header_verify', 0x821B1020: 'header_authenticate',
         0x821B1140: 'header_read_wrapper', 0x82204360: 'load_204360',
         0x82204DA8: 'load_204da8', 0x82205AC0: 'load_205ac0',
         0x82151DC8: 'hash_verify', 0x82241478: 'decal_sprite'}
kernel = C.WinDLL('kernel32', use_last_error=True)


def api(name, args, result=W.BOOL):
    fn = getattr(kernel, name)
    fn.argtypes, fn.restype = args, result
    return fn


open_process = api('OpenProcess', [W.DWORD, W.BOOL, W.DWORD], W.HANDLE)
open_thread = api('OpenThread', [W.DWORD, W.BOOL, W.DWORD], W.HANDLE)
close = api('CloseHandle', [W.HANDLE])
read_mem = api('ReadProcessMemory', [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)])
write_mem = api('WriteProcessMemory', [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)])
flush = api('FlushInstructionCache', [W.HANDLE, C.c_void_p, C.c_size_t])
get_ctx = api('GetThreadContext', [W.HANDLE, C.c_void_p])
set_ctx = api('SetThreadContext', [W.HANDLE, C.c_void_p])
attach = api('DebugActiveProcess', [W.DWORD])
detach = api('DebugActiveProcessStop', [W.DWORD])
wait_event = api('WaitForDebugEvent', [C.c_void_p, W.DWORD])
continue_event = api('ContinueDebugEvent', [W.DWORD, W.DWORD, W.DWORD])
kill_on_exit = api('DebugSetProcessKillOnExit', [W.BOOL])


def check(ok):
    if not ok:
        raise C.WinError(C.get_last_error())


for name in ('temp', 'profile'):
    (RUN / name).mkdir(parents=True, exist_ok=True)
if options.shader_cache_seed:
    seed = options.shader_cache_seed.resolve(strict=True)
    seed.relative_to(ROOT)  # Project confinement applies to cache inputs too.
    shutil.copytree(seed, RUN / 'cache/shaders')
env = os.environ.copy()
env.update(TEMP=str(RUN / 'temp'), TMP=str(RUN / 'temp'),
           LOCALAPPDATA=str(RUN / 'profile'), APPDATA=str(RUN / 'profile'))
args = [str(EXE), f'--game_data_root={GAME}',
        f'--user_data_root={RUN}', f'--cache_root={RUN / "cache"}',
        f'--log_file={RUN / "trace-runtime.log"}', '--keyboard_controller=false',
        '--input_script=45000:DOWN+220,46000:A+250,55000:UP+220,56000:A+250,58000:UP+120,59000:UP+120,60000:UP+120,61000:UP+120,62000:UP+120,63000:UP+120,64000:UP+120,65000:UP+120,66000:UP+120,67000:UP+120,68000:UP+120,70000:A+250,72000:A+250,74000:DOWN+220,95000:A+250', '--input_script_button_state=true',
        '--input_script_keystrokes=false']
capture = options.capture
duration = options.seconds
if capture:
    args += [f'--halo3mp_capture_guest_output_after_ms={(duration - 15) * 1000}',
             f'--halo3mp_capture_guest_output_path={RUN / "proof-loaded.png"}']
binary = EXE.read_bytes()
pe = pefile.PE(data=binary, fast_load=True)
rvas = {}
for guest, name in FUNCS.items():
    pos = binary.find(struct.pack('<Q', guest))
    assert pos >= 0, f'Missing function mapping: {guest:x}'
    host = struct.unpack_from('<Q', binary, pos + 8)[0]
    rvas[host - pe.OPTIONAL_HEADER.ImageBase] = (guest, name)

out = (RUN / 'loading-trace.jsonl').open('w', encoding='utf-8', buffering=1)
started = time.monotonic()


def log(event, **values):
    record = {'seconds': round(time.monotonic() - started, 3), 'event': event, **values}
    out.write(json.dumps(record) + '\n')
    if event in ('attached', 'error', 'exit', 'watchdog'):
        print(json.dumps(record), flush=True)


log('input_map', path=str(GAME / 'maps/lockout.map'),
    sha256=hashlib.sha256((GAME / 'maps/lockout.map').read_bytes()).hexdigest(),
    executable=str(EXE), seconds_limit=duration)
proc = subprocess.Popen(args, cwd=RUN, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
ph = open_process(0x1F0FFF, False, proc.pid)
check(ph)
breakpoints, entries, pending, stepping = {}, {}, {}, {}
hash_counts = {'passed': 0, 'failed': 0}
attached = False


def read(address, size):
    buf = C.create_string_buffer(size)
    count = C.c_size_t()
    check(read_mem(ph, address, buf, size, C.byref(count)))
    return buf.raw[:count.value]


def write(address, data):
    count = C.c_size_t()
    check(write_mem(ph, address, data, len(data), C.byref(count)))
    check(flush(ph, address, len(data)))


def breakpoint(address):
    if address not in breakpoints:
        original = read(address, 1)
        assert original != b'\xcc', 'Refuse pre-existing breakpoint'
        breakpoints[address] = original
        write(address, b'\xcc')


def context(tid):
    th = open_thread(0x1F03FF, False, tid)
    check(th)
    backing = C.create_string_buffer(1232 + 16)
    address = (C.addressof(backing) + 15) & ~15
    ctx = (C.c_ubyte * 1232).from_address(address)
    struct.pack_into('<I', ctx, 48, 0x10001F)
    check(get_ctx(th, address))
    return th, backing, ctx, address


def guest_string(memory_base, address, length=300):
    try:
        return read(memory_base + (address & 0xFFFFFFFF), length).split(b'\0')[0].decode('ascii', 'replace')
    except OSError:
        return '<unreadable>'


try:
    # Skip normal startup's numerous lazy-memory first-chance exceptions.
    time.sleep(35)
    check(attach(proc.pid))
    attached = True
    check(kill_on_exit(False))
    while time.monotonic() - started < duration:
        event = C.create_string_buffer(176)
        if not wait_event(event, 100):
            if proc.poll() is not None:
                break
            continue
        code, pid, tid = struct.unpack_from('<III', event)
        status = 0x10002  # DBG_CONTINUE
        if code == 3:  # CREATE_PROCESS_DEBUG_EVENT
            image_base = struct.unpack_from('<Q', event, 40)[0]
            for rva, descriptor in rvas.items():
                address = image_base + rva
                entries[address] = descriptor
                breakpoint(address)
            log('attached', pid=pid, image_base=hex(image_base), functions=len(entries))
            file_handle = struct.unpack_from('<Q', event, 16)[0]
            if file_handle:
                close(file_handle)
        elif code == 6:  # LOAD_DLL_DEBUG_EVENT
            file_handle = struct.unpack_from('<Q', event, 16)[0]
            if file_handle:
                close(file_handle)
        elif code == 1:  # EXCEPTION_DEBUG_EVENT
            exception = struct.unpack_from('<I', event, 16)[0]
            address = struct.unpack_from('<Q', event, 32)[0]
            if exception == 0x80000003 and address in breakpoints:
                th, backing, ctx, ctx_address = context(tid)
                try:
                    rcx, rdx = struct.unpack_from('<QQ', ctx, 128)
                    rsp = struct.unpack_from('<Q', ctx, 152)[0]
                    if address in entries:
                        guest, name = entries[address]
                        regs = struct.unpack('<7Q', read(rcx, 56))
                        return_address = struct.unpack('<Q', read(rsp, 8))[0]
                        record = {'name': name, 'guest': hex(guest), 'ctx': rcx,
                                  'memory': rdx, 'stack': regs[2], 'argument': regs[0] & 0xFFFFFFFF}
                        if name == 'hash_verify':
                            record['bytes'] = regs[4] & 0xFFFFFFFF
                        pending.setdefault((tid, return_address), []).append(record)
                        breakpoint(return_address)
                        extra = {}
                        if name == 'decal_sprite':
                            try:
                                def gu(at): return struct.unpack('>I', read(rdx + (at & 0xffffffff), 4))[0]
                                state = record['argument']
                                system = gu(state + 4)
                                handle = gu(state + 8)
                                r13 = struct.unpack('<Q', read(rcx + 104, 8))[0] & 0xffffffff
                                table = gu(gu(gu(r13) + 0x1b4) + 0x44)
                                datum = gu(table + (handle & 65535) * 80 + 4)
                                root = gu(gu(0x827f0f8c) + (datum & 65535) * 8 + 4)
                                row = gu(root + 24) + system * 116
                                post = gu(row + 52)
                                extra.update(system=system, handle=hex(handle), datum=hex(datum),
                                             root=hex(root), row=hex(row), post=hex(post),
                                             system_count=gu(root + 20), flags=hex(gu(row + 4)))
                            except OSError as error:
                                extra['read_error'] = str(error)
                        if name.startswith('header_') and name != 'header_read_wrapper':
                            try:
                                h = read(rdx + record['argument'], 0x3000)
                                extra = {'map': h[0x18C:0x1AC].split(b'\0')[0].decode('ascii', 'replace'),
                                         'header_magic': h[:4].hex()}
                            except OSError:
                                pass
                        if name != 'hash_verify':
                            log('enter', tid=tid, function=name, argument=hex(record['argument']), **extra)
                    elif pending.get((tid, address)):
                        record = pending[(tid, address)].pop()
                        result = struct.unpack('<Q', read(record['ctx'], 8))[0]
                        extra = {}
                        if record['name'] == 'header_verify' and result & 0xFF == 0:
                            extra['failure_text'] = guest_string(record['memory'], record['stack'] - 0x120)
                        if record['name'] == 'hash_verify':
                            hash_counts['passed' if result & 0xFF else 'failed'] += 1
                            if result & 0xFF == 0:
                                log('hash_failure', tid=tid, argument=hex(record['argument']),
                                    byte_count=record['bytes'])
                        else:
                            log('return', tid=tid, function=record['name'], result=hex(result), **extra)
                    write(address, breakpoints[address])
                    struct.pack_into('<Q', ctx, 248, address)
                    flags = struct.unpack_from('<I', ctx, 68)[0]
                    struct.pack_into('<I', ctx, 68, flags | 0x100)
                    check(set_ctx(th, ctx_address))
                    stepping[tid] = address
                finally:
                    close(th)
            elif exception == 0x80000004 and tid in stepping:
                address = stepping.pop(tid)
                if address in entries or any(a == address and records for (_, a), records in pending.items()):
                    write(address, b'\xcc')
                else:
                    breakpoints.pop(address, None)
                th, backing, ctx, ctx_address = context(tid)
                try:
                    flags = struct.unpack_from('<I', ctx, 68)[0]
                    struct.pack_into('<I', ctx, 68, flags & ~0x100)
                    check(set_ctx(th, ctx_address))
                finally:
                    close(th)
            elif exception != 0x80000003:
                # First-chance faults are routinely handled by lazy guest-memory mapping.
                first_chance = struct.unpack_from('<I', event, 168)[0]
                if not first_chance:
                    fault = struct.unpack_from('<Q', event, 56)[0]
                    log('exception', code=hex(exception), address=hex(address), tid=tid,
                        fault_address=hex(fault), first_chance=False)
                status = 0x80010001  # Preserve normal exception handling.
        elif code == 5:
            log('exit', code=struct.unpack_from('<I', event, 16)[0])
            continue_event(pid, tid, status)
            break
        check(continue_event(pid, tid, status))
    else:
        log('watchdog', seconds_limit=duration)
except Exception as exc:
    log('error', detail=str(exc))
    raise
finally:
    if proc.poll() is None:
        for address, original in breakpoints.items():
            try:
                write(address, original)
            except OSError:
                pass
        if attached:
            detach(proc.pid)
        proc.terminate()
        proc.wait(timeout=10)
    close(ph)
    log('hash_summary', **hash_counts)
    out.close()
