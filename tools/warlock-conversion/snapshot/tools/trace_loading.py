"""Bounded debugger logging for our own OpenH3M child; no UI or host input.

Software breakpoints execute the original instruction using single-step, and are
restored on detach. No executable files, guest checks, or return values are changed.
"""
import argparse
import bisect
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
parser.add_argument('--slot', choices=('lockout', 'zanzibar', 'chillout'), default='lockout')
parser.add_argument('--capture', action='store_true')
parser.add_argument('--walk-check', action='store_true',
                    help='Use process-local sticks to turn and walk briefly after loading.')
parser.add_argument('--powerup-check', action='store_true',
                    help='Extend the Prisoner walk toward the ground-floor camo; inspect capture to assess result.')
parser.add_argument('--manual-input', action='store_true', help='User operates the game; no scripted input.')
parser.add_argument('--sample-on-stall', action='store_true', help='Sample our child after GPU/input log progress stops.')
parser.add_argument('--trace-allocator', action='store_true')
parser.add_argument('--sample-threads', action='store_true',
                    help='Record bounded thread instruction/stack samples near the watchdog')
parser.add_argument('--sample-world', action='store_true',
                    help='Read bounded gameplay table diagnostics at the first bullet impact.')
parser.add_argument('--shader-cache-seed', type=Path)
parser.add_argument('--seconds', type=int, default=135, choices=range(135, 181))
options = parser.parse_args()
if options.powerup_check and (not options.walk_check or options.slot != 'chillout' or options.seconds < 165):
    parser.error('--powerup-check requires --walk-check --slot chillout and at least 165 seconds')
ROOT = options.project.resolve(strict=True)
RUN = output_path(ROOT / '.local/loading-traces' / (time.strftime('%Y%m%d-%H%M%S') + f'-{os.getpid()}'), ROOT)
GAME = output_path(options.game or ROOT / '.local/custom-maps-play', ROOT)
EXE = options.exe.resolve(strict=True)
if hashlib.sha256(EXE.read_bytes()).hexdigest() != 'ec4d57ee4f654095bd5e512ffe650d65ac514b0fb8f21d5c7b09e61e689c3406':
    raise SystemExit('This diagnostic requires the verified runtime build; function addresses are build-specific.')
if not (GAME / 'maps' / (options.slot + '.map')).is_file():
    raise SystemExit('Missing staged map for selected slot')
listing = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq OpenH3M.exe', '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True, check=True)
if any(row and row[0].casefold() == 'openh3m.exe' for row in csv.reader(listing.stdout.splitlines())):
    raise SystemExit('An OpenH3M process is already running; refusing a parallel test.')
FUNCS = {0x821B0DD0: 'header_verify', 0x821B1020: 'header_authenticate',
         0x821B1140: 'header_read_wrapper', 0x82204360: 'load_204360',
         0x82204DA8: 'load_204da8', 0x82205AC0: 'load_205ac0',
         0x82151DC8: 'hash_verify', 0x82241478: 'decal_sprite'}
if options.trace_allocator:
    FUNCS[0x822c2058] = 'resource_compact'
    FUNCS[0x822c2480] = 'resource_move'
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
suspend_thread = api('SuspendThread', [W.HANDLE], W.DWORD)
resume_thread = api('ResumeThread', [W.HANDLE], W.DWORD)


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
input_steps = ['45000:DOWN+220', '46000:A+250', '55000:UP+220', '56000:A+250']
# A fresh profile starts Custom Games on Last Resort. Warlock needs the
# first alphabetic map (Blackout); Last Resort must retain its current choice.
if options.slot in ('lockout', 'chillout'):
    input_steps.extend(f'{at}:UP+120' for at in range(58000, 68000, 1000))
    if options.slot == 'chillout':
        # The menu retains disc entries even when their map files are absent.
        # Unattended observations: two DOWNs select Construct, three Epitaph.
        # Cold Storage is the preceding entry, reached with one DOWN.
        input_steps.append('68000:DOWN+120')
input_steps.extend(['70000:A+250', '72000:A+250', '74000:DOWN+220', '95000:A+250'])
if options.walk_check:
    if options.manual_input:
        raise SystemExit('--walk-check requires scripted input')
    if options.slot == 'chillout':
        # Prisoner's initial ledge opens south after walking west. Native
        # position samples and source collision sightlines establish this path.
        input_steps.extend(['115000:RT+100', '117000:LSRIGHT+1000',
                            '119000:LSUP+3500', '124000:RSLEFT+1800', '130000:RT+100'])
    else:
        input_steps.extend(['120000:RSRIGHT+1600', '124000:LSUP+1500'])
if options.powerup_check:
    input_steps.extend(['132000:LSUP+3000', '138000:LSRIGHT+900', '143000:RT+100'])
args = [str(EXE), f'--game_data_root={GAME}',
        f'--user_data_root={RUN}', f'--cache_root={RUN / "cache"}',
        f'--log_file={RUN / "trace-runtime.log"}', '--keyboard_controller=false',
        '--input_script=' + ','.join(input_steps), '--input_script_button_state=true',
        '--input_script_keystrokes=false']
if options.manual_input:
    args = [arg for arg in args if not arg.startswith(('--keyboard_controller=', '--input_script'))]
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
    out.flush()
    if event in ('attached', 'error', 'exit', 'watchdog'):
        print(json.dumps(record), flush=True)


log('input_map', path=str(GAME / 'maps' / (options.slot + '.map')),
    sha256=hashlib.sha256((GAME / 'maps' / (options.slot + '.map')).read_bytes()).hexdigest(),
    executable=str(EXE), seconds_limit=duration)
proc = subprocess.Popen(args, cwd=RUN, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
ph = open_process(0x1F0FFF, False, proc.pid)
check(ph)
breakpoints, entries, pending, stepping = {}, {}, {}, {}
hash_counts = {'passed': 0, 'failed': 0}
attached = False
thread_ids = set()
sampled = False
stall_offset = 0
stall_last_progress = None
stall_samples = 0
stall_last_check = 0.0


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


def sample_threads():
    # Only inspect this harness's child. No window enumeration or host input.
    import numpy as np
    words = np.frombuffer(binary[:len(binary) & ~7], dtype='<u8')
    base = pe.OPTIONAL_HEADER.ImageBase
    size = pe.OPTIONAL_HEADER.SizeOfImage
    mask = ((words[:-1] >= 0x82000000) & (words[:-1] < 0x83000000)
            & (words[1:] >= base) & (words[1:] < base + size))
    mappings = sorted((int(words[n + 1]) - base, int(words[n]))
                      for n in np.flatnonzero(mask))
    addresses = [rva for rva, _ in mappings]

    def describe(address):
        rva = address - image_base
        result = {'host': hex(address)}
        if 0 <= rva < size:
            result['rva'] = hex(rva)
            index = bisect.bisect_right(addresses, rva) - 1
            if index >= 0 and rva - addresses[index] < 0x10000:
                result['nearest_guest'] = hex(mappings[index][1])
                result['host_offset'] = hex(rva - addresses[index])
        return result

    for tid in sorted(thread_ids):
        handle = open_thread(0x1F03FF, False, tid)
        if not handle:
            continue
        suspended = False
        try:
            suspended = suspend_thread(handle) != 0xffffffff
            if not suspended:
                continue
            th, backing, ctx, _ = context(tid)
            try:
                rip, rsp = struct.unpack_from('<Q', ctx, 248)[0], struct.unpack_from('<Q', ctx, 152)[0]
                stack = read(rsp, 1024)
                candidates = [v for v in struct.unpack('<128Q', stack)
                              if image_base <= v < image_base + size]
                extra = {}
                instruction = describe(rip)
                if instruction.get('nearest_guest') == '0x822c2058':
                    # Verified executable's allocator prologue keeps PPCContext
                    # and guest memory base in these two fixed stack slots.
                    ppc, memory = struct.unpack('<2Q', read(rsp + 0x38, 16))
                    registers = struct.unpack('<32Q', read(ppc, 256))
                    heap = registers[30] & 0xffffffff
                    def gu(address):
                        address &= 0xffffffff
                        return struct.unpack('>I', read(memory + address + (0x1000 if address >= 0xe0000000 else 0), 4))[0]
                    head, table = gu(heap + 0x48), gu(heap + 0x70)
                    nodes, seen = [], set()
                    node_handle = head
                    for _ in range(24):
                        if node_handle == 0xffffffff or node_handle in seen:
                            break
                        seen.add(node_handle)
                        node = gu(table + 0x44) + (node_handle & 65535) * 24
                        words = [gu(node + j * 4) for j in range(6)]
                        nodes.append({'handle': hex(node_handle), 'address': hex(node), 'words': [hex(v) for v in words]})
                        node_handle = words[3]
                    extra['allocator'] = {'heap': hex(heap),
                                          'name': guest_string(memory, heap, 32),
                                          'entries': hex(gu(table + 0x44)), 'table': hex(table), 'table_name': guest_string(memory, table, 32),
                                          'header_words': [hex(gu(heap + j * 4)) for j in range(30)],
                                          'head': hex(head), 'nodes': nodes,
                                          'cycle': node_handle in seen, 'next': hex(node_handle)}
                log('thread_sample', tid=tid, instruction=describe(rip),
                    stack_candidates=[describe(v) for v in candidates[:24]], **extra)
            finally:
                close(th)
        except OSError as error:
            log('thread_sample_error', tid=tid, detail=str(error))
        finally:
            if suspended:
                resume_thread(handle)
            close(handle)


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
            now = time.monotonic()
            if (options.sample_on_stall and stall_samples < 3 and now - stall_last_check >= 1
                    and now - started >= (60 if options.manual_input else 105)):
                stall_last_check = now
                runtime_path = RUN / 'trace-runtime.log'
                if runtime_path.exists():
                    with runtime_path.open('rb') as stream:
                        stream.seek(stall_offset)
                        chunk = stream.read()
                        stall_offset = stream.tell()
                    if b'GPU context update' in chunk or b'[input-script] returned' in chunk:
                        stall_last_progress = now
                    elif stall_last_progress is not None and now - stall_last_progress >= 3:
                        log('possible_gameplay_stall', seconds_without_progress=now-stall_last_progress)
                        sample_threads()
                        stall_samples += 1
                        stall_last_progress = now
            if options.sample_threads and not sampled and time.monotonic() - started >= duration - 10:
                sample_threads()
                sampled = True
            continue
        code, pid, tid = struct.unpack_from('<III', event)
        if code in (2, 3):
            thread_ids.add(tid)
        elif code == 4:
            thread_ids.discard(tid)
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
                        if name in ('resource_compact', 'resource_move'):
                            try:
                                def gu(at): return struct.unpack('>I', read(rdx + (at & 0xffffffff), 4))[0]
                                wrapper = record['argument']
                                heap = gu(wrapper + 12)
                                table = gu(heap + 0x70)
                                node = gu(table + 0x44)
                                extra = {'heap': hex(heap), 'table': hex(table), 'entries': hex(node),
                                         'wrapper_words': [hex(gu(wrapper + j * 4)) for j in range(16)],
                                         'arguments': [hex(regs[j] & 0xffffffff) for j in (0, 4, 5, 6)],
                                         'resource_table_header': [hex(gu(gu(wrapper) + j * 4)) for j in range(22)],
                                         'head': hex(gu(heap + 0x48)),
                                         'nodes': [hex(gu(node + j * 4)) for j in range(18)]}
                            except OSError as error:
                                extra['read_error'] = str(error)
                        if name == 'decal_sprite':
                            try:
                                def gu(at): return struct.unpack('>I', read(rdx + (at & 0xffffffff), 4))[0]
                                state = record['argument']
                                system = gu(state + 4)
                                handle = gu(state + 8)
                                r13 = struct.unpack('<Q', read(rcx + 104, 8))[0] & 0xffffffff
                                if options.sample_world and time.monotonic() - getattr(options,'world_last_sample',0) > 5:
                                    options.world_last_sample = time.monotonic()
                                    tls = gu(r13)
                                    tables = []
                                    for offset in range(0, 0x800, 4):
                                        try:
                                            pointer = gu(tls + offset)
                                            if not 0x80000000 <= pointer < 0xe0000000: continue
                                            header = read(rdx + pointer, 96)
                                            label = header[:32].split(b'\0')[0]
                                            if not label or not all(32 <= v < 127 for v in label): continue
                                            if not any(v in label.lower() for v in (b'object',b'player',b'observer',b'camera')): continue
                                            data = struct.unpack_from('>I',header,0x44)[0]
                                            item = {'offset':hex(offset),'pointer':hex(pointer),'name':label.decode(),
                                                    'header':header.hex()}
                                            if 0x80000000 <= data < 0xe0000000:
                                                item['data'] = read(rdx+data,512).hex()
                                            tables.append(item)
                                        except OSError: pass
                                    player_unit = None
                                    players = next((t for t in tables if t['name']=='players'),None)
                                    objects = next((t for t in tables if t['name']=='object'),None)
                                    if players and objects:
                                        unit = struct.unpack_from('>I',bytes.fromhex(players['data']),0x28)[0]
                                        object_data = struct.unpack_from('>I',bytes.fromhex(objects['header']),0x44)[0]
                                        head = read(rdx+object_data+(unit & 65535)*16,16)
                                        if struct.unpack_from('>H',head)[0] == unit>>16:
                                            pointer = struct.unpack_from('>I',head,12)[0]
                                            player_unit = {'handle':hex(unit),'header':head.hex(),
                                                           'body':read(rdx+pointer,512).hex()}
                                    log('world_tables',tls=hex(tls),tables=tables,player_unit=player_unit)
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
