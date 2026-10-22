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
parser.add_argument('--slot', choices=('lockout', 'zanzibar', 'chillout', 'sandbox'), default='lockout')
parser.add_argument('--capture', action='store_true')
parser.add_argument('--capture-times-ms', help='Comma-separated native guest capture times for bounded route diagnostics.')
parser.add_argument('--diagnostic-no-vsync', action='store_true',
                    help='Test existing vsync=false option; simulation speed must be validated separately.')
parser.add_argument('--walk-check', action='store_true',
                    help='Use process-local sticks to turn and walk briefly after loading.')
parser.add_argument('--forge-boundary-check', action='store_true',
                    help='Use the verified Forge lobby route, become monitor and strafe toward the Gulch split.')
parser.add_argument('--forge-palette-check', action='store_true',
                    help='Open the native Forge creation palette after the verified Sandbox route.')
parser.add_argument('--forge-vehicle-check', action='store_true',
                    help='Create the first stock vehicle (Banshee), drop it and attempt entry; inspect native captures.')
parser.add_argument('--vehicle-boundary-flight', action='store_true',
                    help='After verified Banshee entry, turn left and boost toward the split; observer samples determine coverage.')
parser.add_argument('--sample-observer', action='store_true',
                    help='Read the verified native observer position once per second after loading.')
parser.add_argument('--sample-font-cache', action='store_true',
                    help='Read bounded original font-cache records at 124 and 128 seconds.')
parser.add_argument('--powerup-check', action='store_true',
                    help='Extend the Prisoner walk toward the ground-floor camo; inspect capture to assess result.')
parser.add_argument('--manual-input', action='store_true', help='User operates the game; no scripted input.')
parser.add_argument('--sample-on-stall', action='store_true', help='Sample our child after GPU/input log progress stops.')
parser.add_argument('--trace-allocator', action='store_true')
parser.add_argument('--sample-resource-cache', action='store_true',
                    help='Read native resource LRU occupancy after loading; not total console RAM.')
parser.add_argument('--trace-memory', action='store_true',
                    help='Observe native memory queries and physical allocations; no synthetic calls.')
parser.add_argument('--sample-threads', action='store_true',
                    help='Record bounded thread instruction/stack samples near the watchdog')
parser.add_argument('--sample-world', action='store_true',
                    help='Read bounded gameplay table diagnostics at the first bullet impact.')
parser.add_argument('--sample-draws', action='store_true',
                    help='Read 1024 native GPU draw states after 110 seconds; no render-state changes.')
parser.add_argument('--shader-cache-seed', type=Path)
parser.add_argument('--cache-root', type=Path, help='Reuse a project-local cache instead of creating a diagnostic cache.')
parser.add_argument('--seconds', type=int, default=135, choices=range(135, 181))
options = parser.parse_args()
if options.vehicle_boundary_flight and (not options.forge_vehicle_check or options.seconds < 180):
    parser.error('--vehicle-boundary-flight requires --forge-vehicle-check and 180 seconds')
if options.forge_vehicle_check and (options.slot != 'sandbox' or options.walk_check or options.manual_input or options.forge_boundary_check or options.forge_palette_check or options.seconds < 165):
    parser.error('--forge-vehicle-check requires Sandbox, 165+ seconds, and no other movement check')
if options.forge_palette_check and (options.slot != 'sandbox' or options.walk_check or options.manual_input or options.forge_boundary_check):
    parser.error('--forge-palette-check requires Sandbox, scripted input, and no other movement check')
if options.forge_boundary_check and (options.slot != 'sandbox' or options.walk_check or options.manual_input or options.seconds < 180):
    parser.error('--forge-boundary-check requires Sandbox, scripted input, no --walk-check, and 180 seconds')
if options.powerup_check and (not options.walk_check or options.slot != 'chillout' or options.seconds < 165):
    parser.error('--powerup-check requires --walk-check --slot chillout and at least 165 seconds')
ROOT = options.project.resolve(strict=True)
REPOSITORY = Path(__file__).resolve().parents[4]
RUN = output_path(REPOSITORY / '.local/loading-traces' / (time.strftime('%Y%m%d-%H%M%S') + f'-{os.getpid()}'), REPOSITORY)
# The original disc root is an input-only baseline; all runtime output roots
# remain explicitly confined to RUN/CACHE below. Never copy the disc as a silo.
GAME = (ROOT if options.game and options.game.resolve(strict=True) == ROOT
        else output_path(options.game or ROOT / '.local/custom-maps-play', ROOT))
CACHE = output_path(options.cache_root or RUN / 'cache', ROOT)
EXE = options.exe.resolve(strict=True)
if options.sample_draws and hashlib.sha256((EXE.parent / 'rexgpu-xenos.dll').read_bytes()).hexdigest() != 'c9f3b77b65d46dbfc382f6b16e5f44c6dac883f2253c62887fcc165aa6087e4c':
    raise SystemExit('Draw diagnostic requires the verified GPU plugin.')
if hashlib.sha256(EXE.read_bytes()).hexdigest() != 'ec4d57ee4f654095bd5e512ffe650d65ac514b0fb8f21d5c7b09e61e689c3406':
    raise SystemExit('This diagnostic requires the verified runtime build; function addresses are build-specific.')
if not (GAME / 'maps' / (options.slot + '.map')).is_file():
    raise SystemExit('Missing staged map for selected slot')
if options.sample_observer:
    from cache_reader import Cache
    from forge_gulch_boundary import boundary_y
    cache = Cache(GAME / 'maps' / (options.slot + '.map'))
    try:
        scenario_index = next(k for k, t in cache.tags.items() if t['group'] == 'scnr')
    finally:
        cache.close()
listing = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq OpenH3M.exe', '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True, check=True)
if any(row and row[0].casefold() == 'openh3m.exe' for row in csv.reader(listing.stdout.splitlines())):
    raise SystemExit('An OpenH3M process is already running; refusing a parallel test.')
FUNCS = {0x821B0DD0: 'header_verify', 0x821B1020: 'header_authenticate',
         0x821B1140: 'header_read_wrapper', 0x82204360: 'load_204360',
         0x82204DA8: 'load_204da8', 0x82205AC0: 'load_205ac0',
         0x82151DC8: 'hash_verify', 0x82241478: 'decal_sprite'}
if options.trace_allocator or options.sample_resource_cache:
    FUNCS[0x822c2058] = 'resource_compact'
    FUNCS[0x822c2480] = 'resource_move'
if options.sample_font_cache:
    FUNCS[0x82201c50] = 'font_character_insert'
if options.trace_memory:
    # Retail XEX import ordinals C6 / BA / BD, resolved through its import records.
    FUNCS.update({0x82723fa4: 'memory_statistics', 0x82723b64: 'physical_allocate',
                  0x82723b94: 'physical_free'})
kernel = C.WinDLL('kernel32', use_last_error=True)


def api(name, args, result=W.BOOL):
    fn = getattr(kernel, name)
    fn.argtypes, fn.restype = args, result
    return fn


open_process = api('OpenProcess', [W.DWORD, W.BOOL, W.DWORD], W.HANDLE)
open_thread = api('OpenThread', [W.DWORD, W.BOOL, W.DWORD], W.HANDLE)
close = api('CloseHandle', [W.HANDLE])
query_virtual = api('VirtualQueryEx', [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t], C.c_size_t)
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
    shutil.copytree(seed, CACHE / 'shaders', dirs_exist_ok=True)
env = os.environ.copy()
env.update(TEMP=str(RUN / 'temp'), TMP=str(RUN / 'temp'),
           LOCALAPPDATA=str(RUN / 'profile'), APPDATA=str(RUN / 'profile'))
input_steps = ['45000:DOWN+220', '46000:A+250', '55000:UP+220', '56000:A+250']
if options.forge_boundary_check or options.forge_palette_check or options.forge_vehicle_check:
    input_steps.insert(1, '45500:DOWN+220')
# A fresh profile starts Custom Games on Last Resort. Warlock needs the
# first alphabetic map (Blackout); Last Resort must retain its current choice.
if options.slot in ('lockout', 'chillout'):
    input_steps.extend(f'{at}:UP+120' for at in range(58000, 68000, 1000))
    if options.slot == 'chillout':
        # The menu retains disc entries even when their map files are absent.
        # Unattended observations: two DOWNs select Construct, three Epitaph.
        # Cold Storage is the preceding entry, reached with one DOWN.
        input_steps.append('68000:DOWN+120')
if options.slot == 'sandbox':
    # Native capture: four DOWNs reach Rat's Nest; fifth selects Sandbox.
    input_steps.extend(f'{at}:DOWN+120' for at in range(58000, 63000, 1000))
input_steps.extend(['70000:A+250', '72000:A+250', '74000:DOWN+220', '95000:A+250'])
if options.forge_boundary_check:
    # Native 20261021-173147 route probe confirms Forge / Sandbox. From the
    # +X spawn facing, left strafe travels +Y toward the curved split.
    # Halo 3's original manual documents LT as monitor thrust. At ordinary
    # speed the 40-second probe travels only ~87 units of the ~184-unit gap.
    input_steps.extend(['118000:UP+200', '120000:RB+8000',
                        '119900:LT+58100', '130000:LSLEFT+48000'])
if options.forge_palette_check:
    input_steps.extend(['118000:UP+200', '121000:X+200'])
if options.forge_vehicle_check:
    # Original Sandbox scenario vehicle palette starts with the stock Banshee.
    # Captures must establish actual category, placement and entry outcomes.
    input_steps.extend(['118000:UP+200', '121000:X+200', '123000:RB+200',
                        '127000:A+200', '129000:A+200', '131000:UP+200',
                        '133000:LSUP+3000', '139000:RB+1800'])
    if options.vehicle_boundary_flight:
        input_steps.extend(['142000:RSLEFT+500', '143000:LSUP+35000', '143000:LT+35000'])
    else:
        input_steps.append('145000:LSUP+10000')
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
        f'--user_data_root={RUN}', f'--cache_root={CACHE}',
        f'--log_file={RUN / "trace-runtime.log"}', '--keyboard_controller=false',
        '--input_script=' + ','.join(input_steps), '--input_script_button_state=true',
        '--input_script_keystrokes=false']
if options.manual_input:
    args = [arg for arg in args if not arg.startswith(('--keyboard_controller=', '--input_script'))]
if options.diagnostic_no_vsync:
    args += ['--vsync=false']
capture = options.capture
duration = options.seconds
if capture:
    args += [f'--halo3mp_capture_guest_output_path={RUN / "proof-loaded.png"}']
    if not options.capture_times_ms:
        args += [f'--halo3mp_capture_guest_output_after_ms={(duration - 15) * 1000}']
    if options.capture_times_ms:
        capture_times = [int(t) for t in options.capture_times_ms.split(',')]
        if not capture_times or any(t <= 0 or t >= duration * 1000 for t in capture_times):
            raise SystemExit('Capture times must be inside the bounded run')
        args += ['--halo3mp_capture_guest_output_times_ms=' + ','.join(map(str, capture_times))]
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
creation_flags = subprocess.CREATE_NO_WINDOW | (0x2 if options.trace_memory else 0)
# DEBUG_ONLY_THIS_PROCESS installs observation before any guest startup allocations.
proc = subprocess.Popen(args, cwd=RUN, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creation_flags)
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
draw_address = None
draw_armed = False
draw_samples = 0
guest_memory_base = None
guest_r13 = None
observer_sample_time = 0
font_samples = 0
font_r13 = None
font_cache_address = None
memory_sample_time = 0
resource_sample_time = 0
resource_wrappers = set()
sampled_vertex_addresses = set()
draw_stream = (RUN / 'draw-registers.bin').open('wb') if options.sample_draws else None


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
    if not options.trace_memory:
        time.sleep(35)
        check(attach(proc.pid))
    attached = True
    check(kill_on_exit(False))
    while time.monotonic() - started < duration:
        now = time.monotonic()
        if options.sample_resource_cache and guest_memory_base and now-started >= 105 and now-resource_sample_time >= 5:
            resource_sample_time = now
            from resource_heap_probe import snapshot as resource_snapshot
            for wrapper in sorted(resource_wrappers):
                try:
                    log('resource_heap', **resource_snapshot(read, guest_memory_base, wrapper))
                except (OSError, ValueError) as error:
                    log('resource_heap_error', wrapper=hex(wrapper), detail=str(error))
        if (options.sample_font_cache and guest_memory_base and font_r13
                and font_samples < 2 and now-started >= 124+font_samples*4):
            font_samples += 1
            try:
                from font_cache_probe import snapshot
                log('font_cache', **snapshot(read, guest_memory_base, font_r13, font_cache_address, include_atlas=True))
            except (OSError, ValueError) as error:
                log('font_cache_error', detail=str(error))
        if options.trace_memory and guest_memory_base and now-started >= 105 and now-memory_sample_time >= 5:
            memory_sample_time = now
            counts = {}
            # MapViews aliases 0x90000000 to the XEX view and 0x7f000000 to
            # physical memory: exclude both to avoid counting backing twice.
            for label, low, high in (('virtual', 0, 0x7f000000), ('xex', 0x80000000, 0x90000000)):
                cursor, total = guest_memory_base+low, 0
                end = guest_memory_base+high
                while cursor < end:
                    mbi = C.create_string_buffer(48)
                    check(query_virtual(ph, cursor, mbi, 48))
                    base = struct.unpack_from('<Q', mbi, 0)[0]
                    size = struct.unpack_from('<Q', mbi, 24)[0]
                    state = struct.unpack_from('<I', mbi, 32)[0]
                    if not size or base+size <= cursor:
                        raise ValueError('Invalid guest memory query extent')
                    limit = min(base+size, end)
                    if state == 0x1000:
                        total += limit-cursor
                    cursor = limit
                counts[label+'_committed_bytes'] = total
            log('guest_virtual_commit', **counts,
                accounting_scope='Unique guest virtual/XEX backing; physical aliases excluded; not host RSS')
        if (options.sample_observer and guest_memory_base and guest_r13
                and now-started >= 105 and now-observer_sample_time >= 1):
            observer_sample_time = now
            try:
                def observer_word(address):
                    return struct.unpack('>I', read(guest_memory_base+(address & 0xffffffff), 4))[0]
                tls = observer_word(guest_r13)
                pointer = observer_word(tls+0x25c)
                if not 0x80000000 <= pointer < 0xe0000000:
                    raise ValueError('Observer pointer outside expected guest range')
                data = read(guest_memory_base+pointer+0x1cc, 96)
                position = struct.unpack_from('>3f', data)
                table = observer_word(0x827f0f8c)
                root = observer_word(table+scenario_index*8+4)
                count = observer_word(root+0x23c)
                if not 0 <= count <= 128:
                    raise ValueError('Unexpected live soft-ceiling count')
                ceilings = observer_word(root+0x240)
                flags = [read(guest_memory_base+ceilings+j*12, 12).hex() for j in range(count)]
                log('observer_position', position=position, location=data[12:16].hex(),
                    gulch_margin=float(boundary_y(position[0]))-position[1],
                    forward=struct.unpack_from('>3f', data, 40), observer_bytes=data.hex(),
                    soft_ceiling_records=flags)
            except (OSError, ValueError) as error:
                log('observer_sample_error', detail=str(error))
        event = C.create_string_buffer(176)
        if not wait_event(event, 100):
            if proc.poll() is not None:
                break
            now = time.monotonic()
            if options.sample_draws and draw_address and not draw_armed and now - started >= 110:
                check(kernel.DebugBreakProcess(ph))
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
        if options.sample_draws and draw_address and not draw_armed and time.monotonic() - started >= 110:
            breakpoint(draw_address)
            draw_armed = True
            log('draw_trace_armed', address=hex(draw_address))
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
                if options.sample_draws:
                    path_buffer = C.create_unicode_buffer(2048)
                    get_path = kernel.GetFinalPathNameByHandleW
                    get_path.argtypes = [W.HANDLE, W.LPWSTR, W.DWORD, W.DWORD]
                    if get_path(file_handle, path_buffer, 2048, 0) and path_buffer.value.lower().endswith('rexgpu-xenos.dll'):
                        module_base = struct.unpack_from('<Q', event, 24)[0]
                        draw_address = module_base + 0x14e740
                        if read(draw_address, 13) != bytes.fromhex('55415741564155415456575348'):
                            raise ValueError('Draw entry signature mismatch')
                        log('draw_plugin', base=hex(module_base))
                close(file_handle)
        elif code == 1:  # EXCEPTION_DEBUG_EVENT
            exception = struct.unpack_from('<I', event, 16)[0]
            address = struct.unpack_from('<Q', event, 32)[0]
            if exception == 0x80000003 and address in breakpoints:
                th, backing, ctx, ctx_address = context(tid)
                try:
                    rcx, rdx = struct.unpack_from('<QQ', ctx, 128)
                    rsp = struct.unpack_from('<Q', ctx, 152)[0]
                    if address == draw_address:
                        registers = struct.unpack('<Q', read(rcx + 0x20, 8))[0]
                        shaders = struct.unpack('<2Q', read(rcx + 0xf0, 16))
                        state = read(registers, 0x5003 * 4)
                        draw_stream.write(state)
                        if draw_samples == 200 and guest_memory_base and guest_r13:
                            import numpy as np
                            camera = struct.unpack_from('<3f', state, (0x4000 + 7 * 4) * 4)
                            def gu_draw(at):
                                return struct.unpack('>I', read(guest_memory_base + (at & 0xffffffff), 4))[0]
                            tls = gu_draw(guest_r13)
                            matches = []
                            scanned = set()
                            for tls_offset in range(0, 0x800, 4):
                                try:
                                    pointer = gu_draw(tls + tls_offset)
                                    if pointer in scanned or not 0x80000000 <= pointer < 0xe0000000:
                                        continue
                                    scanned.add(pointer)
                                    data = read(guest_memory_base + pointer, 16384)
                                    floats = np.frombuffer(data, dtype='>f4')
                                    with np.errstate(invalid='ignore'):
                                        found = np.flatnonzero((np.abs(floats[:-2] - camera[0]) < .02)
                                            & (np.abs(floats[1:-1] - camera[1]) < .02)
                                            & (np.abs(floats[2:] - camera[2]) < .02))
                                    for offset in found[:8]:
                                        byte_offset = int(offset) * 4
                                        matches.append({'tls_offset':hex(tls_offset),'pointer':hex(pointer),
                                            'offset':hex(byte_offset),'bytes':data[byte_offset:byte_offset+96].hex()})
                                except OSError:
                                    continue
                            log('camera_location_candidates', camera=camera, tls=hex(tls), matches=matches)
                            from cache_reader import Cache
                            map_cache = Cache(GAME / 'maps' / (options.slot + '.map'))
                            try:
                                tag_table = gu_draw(0x827f0f8c)
                                bsp_state = []
                                for tag_index, tag in map_cache.tags.items():
                                    if tag['group'] != 'sbsp':
                                        continue
                                    live_root = gu_draw(tag_table + tag_index * 8 + 4)
                                    count = gu_draw(live_root + 0x30)
                                    leaf_pointer = gu_draw(live_root + 0x34)
                                    if count > 1000000:
                                        raise ValueError('Unexpected live leaf count')
                                    live_leaves = read(guest_memory_base + leaf_pointer, count)
                                    offline_rows = map_cache.block(tag['offset'] + 0x30, 1)
                                    offline_leaves = bytes(map_cache.data[row] for row in offline_rows)
                                    bsp_state.append({'tag':tag_index,'name':map_cache.name(tag_index),
                                        'root':hex(live_root),'leaf_count':count,
                                        'leaf_bytes_match':live_leaves == offline_leaves,
                                        'selected_leaves':{hex(n):live_leaves[n] for n in (0x63bd,0xba14) if n<count},
                                        'root_bytes':read(guest_memory_base+live_root,0x388).hex()})
                                log('live_bsp_state',bsps=bsp_state)
                            finally:
                                map_cache.close()

                        extra_draw = {}
                        index_info = struct.unpack_from('<Q', ctx, 192)[0]
                        if index_info:
                            extra_draw['index_info'] = read(index_info, 24).hex()
                        fetch, size = struct.unpack_from('<II', state, 0x48be * 4)
                        vertex_address = fetch & 0x1ffffffc
                        if guest_memory_base and fetch & 3 == 3 and vertex_address not in sampled_vertex_addresses:
                            try:
                                extra_draw['vertex_address'] = hex(vertex_address)
                                extra_draw['vertex_head'] = read(guest_memory_base + 0xa0000000 + vertex_address, 96).hex()
                                sampled_vertex_addresses.add(vertex_address)
                            except OSError as error:
                                extra_draw['vertex_read_error'] = str(error)
                        log('draw', sample=draw_samples, primitive=rdx,
                            index_count=struct.unpack_from('<Q', ctx, 184)[0],
                            shaders=[read(p, 64).hex() if p else None for p in shaders], **extra_draw)
                        draw_samples += 1
                    elif address in entries:
                        guest_memory_base = rdx
                        guest_r13 = struct.unpack('<Q', read(rcx + 104, 8))[0] & 0xffffffff
                        guest, name = entries[address]
                        if name == 'font_character_insert':
                            font_tls = struct.unpack('>I', read(rdx+guest_r13, 4))[0]
                            font_address = struct.unpack('>I', read(rdx+font_tls+0xf4, 4))[0]
                            if font_address:
                                font_r13 = guest_r13
                                font_cache_address = font_address
                        regs = struct.unpack('<7Q', read(rcx, 56))
                        return_address = struct.unpack('<Q', read(rsp, 8))[0]
                        record = {'name': name, 'guest': hex(guest), 'ctx': rcx,
                                  'memory': rdx, 'stack': regs[2], 'argument': regs[0] & 0xFFFFFFFF}
                        if name == 'hash_verify':
                            record['bytes'] = regs[4] & 0xFFFFFFFF
                        pending.setdefault((tid, return_address), []).append(record)
                        breakpoint(return_address)
                        extra = {}
                        if name in ('physical_allocate', 'physical_free'):
                            extra['guest_arguments'] = [hex(v & 0xffffffff) for v in
                                (regs[0], *struct.unpack('<5Q', read(rcx+32, 40))) ]
                        if name in ('resource_compact', 'resource_move'):
                            resource_wrappers.add(record['argument'])
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
                                    game_time_candidates = []
                                    for offset in range(0, 0x800, 4):
                                        try:
                                            pointer = gu(tls + offset)
                                            if not 0x80000000 <= pointer < 0xe0000000: continue
                                            header = read(rdx + pointer, 96)
                                            # Candidate Halo 3 game_time_globals layout. Validate
                                            # via live tick deltas; do not assume a TLS offset.
                                            rate = struct.unpack_from('>h', header, 4)[0]
                                            length = struct.unpack_from('>f', header, 8)[0]
                                            speed = struct.unpack_from('>f', header, 16)[0]
                                            if header[0] == 1 and rate == 30 and abs(length - 1 / 30) < 1e-7 and speed == 1:
                                                game_time_candidates.append({'tls_offset': hex(offset),
                                                    'pointer': hex(pointer), 'tick_rate': rate,
                                                    'tick_length': length, 'ticks': struct.unpack_from('>i', header, 12)[0],
                                                    'speed': speed, 'bytes': header[:44].hex()})
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
                                    log('world_tables',tls=hex(tls),tables=tables,player_unit=player_unit,
                                        game_time_candidates=game_time_candidates)
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
                        if record['name'] == 'memory_statistics' and result & 0xffffffff == 0:
                            words = struct.unpack('>26I', read(record['memory']+record['argument'], 104))
                            extra['statistics_words'] = list(words)
                            extra['available_physical_bytes'] = words[3]*4096
                            extra['heap_accounted_physical_bytes'] = (words[1]-words[2]-words[3])*4096
                            extra['accounting_scope'] = 'Physical heap counters only; excludes independent virtual/XEX heaps'
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
                if (address == draw_address and draw_samples < 1024) or address in entries or any(a == address and records for (_, a), records in pending.items()):
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
    if draw_stream:
        draw_stream.close()
        import gzip
        raw_path = RUN / 'draw-registers.bin'
        compressed_path = RUN / 'draw-registers.bin.gz'
        with raw_path.open('rb') as source, gzip.open(compressed_path, 'wb', compresslevel=3) as dest:
            shutil.copyfileobj(source, dest)
        with gzip.open(compressed_path, 'rb') as source:
            decoded_size = sum(len(block) for block in iter(lambda: source.read(1048576), b''))
        if decoded_size != raw_path.stat().st_size:
            raise ValueError('Draw evidence compression failed readback')
        raw_path.unlink()
    out.close()
