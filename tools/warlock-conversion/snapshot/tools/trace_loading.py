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
parser.add_argument('--expected-exe-sha256', default='ec4d57ee4f654095bd5e512ffe650d65ac514b0fb8f21d5c7b09e61e689c3406',
                    help='Explicit pinned SHA256 for a newly rebuilt executable; mappings are read from its PE.')
parser.add_argument('--game', type=Path)
parser.add_argument('--video-surface-quality', choices=('original','balanced','performance'),
                    help='Explicit D3D12 texture/filter settings for bounded quality validation.')
parser.add_argument('--quiet-timing', action='store_true',
                    help='Use info-level runtime logs and omit decal breakpoints; retain load/hash validation.')
parser.add_argument('--dlc-payload', type=Path,
                    help='Repo-local payload exposed as one installed content bundle via hardlinks.')
parser.add_argument('--dlc-package', type=Path,
                    help='Install a repository-local LIVE container using the native installer before this run.')
parser.add_argument('--dlc-installed-root', type=Path,
                    help='Reuse a native-installed repository-local content tree through hardlinks.')
parser.add_argument('--dlc-map',
                    help='Select a distinct DLC entry from the full stock-plus-custom map list.')
parser.add_argument('--dlc-menu-check', action='store_true',
                    help='Stop the process-local route at the map list for DLC discovery inspection.')
parser.add_argument('--saved-layout', type=Path,
                    help='Native saved-layout BLF copied into the isolated test profile, never the live profile.')
parser.add_argument('--profile-seed', type=Path,
                    help='Copy the two H3 title-specific settings from a repository-local profile/User directory into this isolated run.')
parser.add_argument('--saved-layout-library', type=Path,
                    help='Also copy every native .bin layout from this repository-local directory for menu discovery checks.')
parser.add_argument('--layout-menu-check', action='store_true',
                    help='Stop after opening the selected base map\'s saved-layout list.')
parser.add_argument('--layout-overview-check', action='store_true',
                    help='Load a saved layout in Forge and rise for native architecture inspection.')
parser.add_argument('--forge-overview-check', action='store_true',
                    help='Load the base DLC map in Forge and rise for native architecture/water inspection.')
parser.add_argument('--dlc-preview-tour', action='store_true',
                    help='Menu-only tour: Last Resort, Forge Gulch, Prisoner, Resuscitation, Warlock.')
parser.add_argument('--trace-dlc-paths', action='store_true',
                    help='Trace native cache path resolution; verbose and slows timing runs.')
parser.add_argument('--trace-console-loader', action='store_true',
                    help='Observe cache-copy state, file opens, load retries and fatal dispatch; no guest behavior changes.')
parser.add_argument('--slot', choices=('lockout', 'zanzibar', 'chillout', 'sandbox'), default='lockout')
parser.add_argument('--capture', action='store_true')
parser.add_argument('--host-capture-after-ms', type=int,
                    help='Capture the application final backbuffer including host UI, inside this run directory.')
parser.add_argument('--capture-times-ms', help='Comma-separated native guest capture times for bounded route diagnostics.')
parser.add_argument('--inspection-input', help='Additional exclusive process-local H3IR steps: ms:BUTTON+duration, starting after 100 seconds.')
parser.add_argument('--audio-frames', type=int, default=0,
                    help='Read up to 8 seconds of this child\'s submitted six-channel PCM; diagnostic timing only.')
parser.add_argument('--audio-after-seconds', type=float, default=145,
                    help='Wall-clock delay before arming native guest PCM observation.')
parser.add_argument('--diagnostic-no-vsync', action='store_true',
                    help='Test existing vsync=false option; simulation speed must be validated separately.')
parser.add_argument('--diagnostic-async-occlusion', action='store_true', help='Validate fence-completed asynchronous visibility results.')
parser.add_argument('--diagnostic-display-phase-off', action='store_true', help='Isolate host display-phase pacing without changing guest clocks.')
parser.add_argument('--slow-turn-check', action='store_true', help='Stationary slow yaw sweep using exclusive process-local replay.')
parser.add_argument('--slow-turn-forge', action='store_true', help='Run the slow-turn benchmark in Forge mode.')
parser.add_argument('--turn-duration-ms', type=int, default=30000)
parser.add_argument('--walk-check', action='store_true',
                    help='Use process-local sticks to turn and walk briefly after loading.')
parser.add_argument('--walk-route', choices=('default', 'elongation', 'lockout-light', 'lockout-exit'), default='default',
                    help='Map-specific process-local movement route; requires --walk-check.')
parser.add_argument('--timing-diagnostics', action='store_true',
                    help='Log native presentation timing and GPU preparation exceeding 8 ms.')
parser.add_argument('--forge-boundary-check', action='store_true',
                    help='Use the verified Forge lobby route, become monitor and strafe toward the Gulch split.')
parser.add_argument('--forge-sanctuary-check', action='store_true',
                    help='Fly the Island monitor toward the Coliseum for native lighting captures.')
parser.add_argument('--forge-water-check', action='store_true',
                    help='Become monitor, rise above the canyon and face the water; process-local input only.')
parser.add_argument('--forge-palette-check', action='store_true',
                    help='Open the native Forge creation palette after the verified Sandbox route.')
parser.add_argument('--forge-scenery-check', action='store_true',
                    help='In Forge, open Scenery and place a Reach architecture piece.')
parser.add_argument('--forge-existing-pair-check', action='store_true', help='Grab, separate and return a pre-placed opposed pair using native input')
parser.add_argument('--forge-pair-lift', action='store_true', help='Lift the held existing pair piece before pulling, to distinguish ground obstruction from controller failure')
parser.add_argument('--forge-pair-approach-up-ms', type=int, default=0, choices=range(0,9001), help='Fly upward before grabbing elevated saved scenery; process-local input only')
parser.add_argument('--forge-manipulation-check', action='store_true',
                    help='Native create/move/release/re-grab/move sequence without forced object poses.')
parser.add_argument('--forge-delete-check', action='store_true',
                    help='Delete held scenery after menu cancellation; remain in monitor mode without a follow-up grab or player-mode transition.')
parser.add_argument('--forge-spawn-clearance-check', action='store_true',
                    help='Ascend before native scenery creation to inspect clearance away from terrain.')
parser.add_argument('--advanced-forge-data', type=Path,
                    help='Enable the original H4 magnet bridge using repository-local private inputs.')
parser.add_argument('--advanced-forge-auto', action='store_true',
                    help='Test automatic Forge activation and adjacent private inputs, without enable/data-path overrides.')
parser.add_argument('--advanced-forge-anchor-check', action='store_true',
                    help='Keep the scenery piece held for original-material and depth captures.')
parser.add_argument('--advanced-forge-base-round-check', action='store_true',
                    help='Inspect the released Base Round disc from an elevated monitor viewpoint; process-local replay only.')
parser.add_argument('--advanced-forge-test-coordinates', help='Process-local coordinate panel command x,y,z,yaw,pitch,roll; tests with magnets disabled')
parser.add_argument('--advanced-forge-test-physics', help='Process-local editor physics sequence, one mode every 90 ticks: normal,fixed,phased')
parser.add_argument('--advanced-forge-test-menu', action='store_true', help='Open the native held-object properties menu during the scenery replay')
parser.add_argument('--advanced-forge-test-menu-case', choices=('position', 'rotation', 'rotation-cancel', 'resume', 'lifecycle'), default='position')
parser.add_argument('--advanced-forge-test-position',
                    help='Diagnostic-only world-space held drag request x,y,z; requires Advanced Forge replay.')
parser.add_argument('--forge-scenery-index', type=int, default=4, choices=range(40),
                    help='Reach palette row; default Bank 1x1 fits the camera, unlike the large Arena Wall at row 0.')
parser.add_argument('--forge-vehicle-check', action='store_true',
                    help='Create the first stock vehicle (Banshee), drop it and attempt entry; inspect native captures.')
parser.add_argument('--hornet-occlusion-check', action='store_true',
                    help='Enter the Hornet in a dedicated saved fixture and turn; process-local input only.')
parser.add_argument('--forge-vehicle-index', type=int, default=0, choices=range(11),
                    help='Stock vehicle palette row; 0 Banshee, 2 Hornet.')
parser.add_argument('--vehicle-boundary-flight', action='store_true',
                    help='After verified Banshee entry, turn left and boost toward the split; observer samples determine coverage.')
parser.add_argument('--sample-native-variant', action='store_true', help='Read-only native H3 map-variant snapshots from this test child')
parser.add_argument('--sample-observer', action='store_true',
                    help='Read the verified native observer position once per second after loading.')
parser.add_argument('--sample-object-map', type=Path,
                    help='Read bounded machine/crate object snapshots using tag identities from this native cache.')
parser.add_argument('--sample-equipment-objects', action='store_true',
                    help='Include equipment in the read-only object snapshots; requires --sample-object-map.')
parser.add_argument('--sample-player-objects', action='store_true', help='Include read-only player object headers in bounded machine samples.')
parser.add_argument('--sample-object-body-bytes', type=int, choices=(256, 1024), default=256,
                    help='Bounded read-only object body sample size; expanded mode includes device state.')
parser.add_argument('--sample-object-interval', type=int, choices=(1, 5), default=5)
parser.add_argument('--trace-bsp-seams', action='store_true',
                    help='Read native scenario/BSP/cluster seam bindings when diagnosing a visibility fault.')
parser.add_argument('--trace-scenario-objects', action='store_true',
                    help='Trace original scenario placement preparation and object creation; no game-code changes.')
parser.add_argument('--font-upload-probe', action='store_true',
                    help='Enable bounded font staging evidence with the diagnostic GPU plugin.')
parser.add_argument('--sample-font-cache', action='store_true',
                    help='Read bounded original font-cache records at 124 and 128 seconds.')
parser.add_argument('--powerup-check', action='store_true',
                    help='Extend the Prisoner walk toward the ground-floor camo; inspect capture to assess result.')
parser.add_argument('--manual-input', action='store_true', help='User operates the game; no scripted input.')
parser.add_argument('--exclusive-input', action='store_true',
                    help='Use existing process-local H3IR replay, excluding physical controller input during this test.')
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
parser.add_argument('--draw-after-seconds', type=int, default=110,
                    help='Delay bounded GPU draw sampling until the target screen is open.')
parser.add_argument('--sample-draws', action='store_true',
                    help='Read 1024 native GPU draw states after 110 seconds; no render-state changes.')
parser.add_argument('--draw-sample-limit', type=int, default=1024, choices=(1024, 2048, 4096),
                    help='Bounded draw-state count; larger scenes may exceed 1024 draws before postprocessing.')
parser.add_argument('--shader-cache-seed', type=Path)
parser.add_argument('--cache-root', type=Path, help='Reuse a project-local cache instead of creating a diagnostic cache.')
parser.add_argument('--fpsunlock', action='store_true', help='Use the existing FPS-only unlock for private performance measurements.')
parser.add_argument('--menu-press-ms', type=int, default=50, choices=range(1,251), metavar='1..250', help='Native replay menu-button duration for uncapped tests; does not alter game timing.')
parser.add_argument('--menu-delay-ms', type=int, default=0, choices=range(0,30001), metavar='0..30000', help='Delay the private menu replay to allow startup to settle; no game timing changes.')
parser.add_argument('--menu-route', help='Explicit bounded process-local menu replay; requires exclusive input.')
parser.add_argument('--seconds', type=int, default=135, choices=range(75, 241))
parser.add_argument('--reuse-run', type=Path, help='Reuse an existing loading-traces installation; overwrites its current diagnostic outputs')
options = parser.parse_args()
if options.forge_pair_lift and not options.forge_existing_pair_check:
    parser.error('Pair lift requires the existing-pair check')
if options.forge_pair_approach_up_ms and not options.forge_existing_pair_check:
    parser.error('Pair approach requires the existing-pair check')
if not 0 <= options.audio_frames <= 1500:
    parser.error('Audio observation is limited to 0..1500 frames (8 seconds)')
forge_test = bool(options.advanced_forge_data or options.advanced_forge_auto)
if options.forge_delete_check and (not forge_test or not options.forge_scenery_check or not options.exclusive_input or options.manual_input or options.seconds < 180 or not options.advanced_forge_test_menu or options.advanced_forge_test_menu_case != 'rotation-cancel' or options.forge_spawn_clearance_check or options.inspection_input):
    parser.error('Deletion check requires exclusive rotation-cancel scenery replay, 180 seconds and no additional inspection/ascent input')
if options.forge_existing_pair_check and (not forge_test or not options.saved_layout or not options.exclusive_input or options.manual_input or options.seconds<175 or options.forge_scenery_check or options.forge_manipulation_check or options.advanced_forge_test_position or options.advanced_forge_test_coordinates or options.advanced_forge_test_menu or options.forge_spawn_clearance_check):
    parser.error('Existing pair requires exclusive saved-layout Forge replay without creation or forced poses')
if options.forge_manipulation_check and (not forge_test or not options.forge_scenery_check or not options.exclusive_input or options.manual_input or options.seconds < 175 or options.advanced_forge_test_position or options.advanced_forge_test_coordinates or options.advanced_forge_test_menu or options.advanced_forge_anchor_check or options.advanced_forge_base_round_check):
    parser.error('Manipulation check requires exclusive native scenery replay, 175+ seconds and no forced pose/menu route')
if options.advanced_forge_base_round_check and (not forge_test or not options.forge_scenery_check or options.forge_scenery_index != 8 or options.advanced_forge_test_menu or options.advanced_forge_anchor_check):
    parser.error('Base Round inspection requires its dedicated Advanced Forge scenery route')
if options.advanced_forge_anchor_check and (not forge_test or not options.forge_scenery_check or options.advanced_forge_test_menu):
    parser.error('Anchor capture requires the Advanced Forge scenery route without a properties-menu test')
if options.advanced_forge_auto and (options.advanced_forge_data or options.advanced_forge_test_coordinates):
    parser.error('Automatic activation cannot use explicit data or the disabled-magnets coordinate diagnostic')
if options.hornet_occlusion_check and (not options.saved_layout or not options.exclusive_input or options.seconds < 180 or options.forge_vehicle_check or options.walk_check):
    parser.error('Hornet visibility check requires a saved fixture, exclusive input, 180 seconds, and no other movement route')
if options.advanced_forge_test_position and not forge_test:
    parser.error('Diagnostic drag requires an Advanced Forge test route')
if options.advanced_forge_test_coordinates and not options.advanced_forge_data:
    parser.error('Diagnostic coordinate command requires --advanced-forge-data')
if options.advanced_forge_test_physics and not forge_test:
    parser.error('Diagnostic physics command requires an Advanced Forge test route')
if options.advanced_forge_test_menu and (not forge_test or not options.forge_scenery_check):
    parser.error('Native properties check requires Advanced Forge scenery replay')
if options.advanced_forge_test_menu_case != 'position' and not options.advanced_forge_test_menu:
    parser.error('A native menu case requires --advanced-forge-test-menu')
if options.dlc_map == 'warlock' and options.walk_check:
    parser.error('Warlock requires the documented stationary visual route; the generic walk ends against a wall')
if options.vehicle_boundary_flight and (not options.forge_vehicle_check or options.seconds < 180):
    parser.error('--vehicle-boundary-flight requires --forge-vehicle-check and 180 seconds')
if options.forge_vehicle_check and (options.slot != 'sandbox' or options.walk_check or options.manual_input or options.forge_boundary_check or options.forge_palette_check or options.seconds < 165):
    parser.error('--forge-vehicle-check requires Sandbox, 165+ seconds, and no other movement check')
if options.forge_palette_check and (options.slot not in ('sandbox', 'zanzibar') or options.walk_check or options.manual_input or options.forge_boundary_check):
    parser.error('--forge-palette-check requires Sandbox/Last Resort, scripted input, and no other movement check')
if options.forge_boundary_check and (options.slot != 'sandbox' or options.walk_check or options.manual_input or options.seconds < 180):
    parser.error('--forge-boundary-check requires Sandbox, scripted input, no --walk-check, and 180 seconds')
if options.powerup_check and (not options.walk_check or options.slot != 'chillout' or options.seconds < 165):
    parser.error('--powerup-check requires --walk-check --slot chillout and at least 165 seconds')
ROOT = options.project.resolve(strict=True)
REPOSITORY = Path(__file__).resolve().parents[4]
RUN = None
if options.reuse_run:
    if options.dlc_payload or options.dlc_package or options.profile_seed:
        parser.error('Run reuse supports installed content without payload/package/profile seeding')
    RUN = options.reuse_run.resolve(strict=True)
    traces = (REPOSITORY / '.local/loading-traces').resolve(strict=True)
    if RUN.parent != traces or not (RUN / 'launch-command.json').is_file():
        parser.error('Run reuse requires an existing direct loading-traces child with a launch manifest')
    processes = subprocess.check_output(['tasklist', '/FI', 'IMAGENAME eq halo3mp.exe', '/FO', 'CSV', '/NH'],
                                        text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if '"halo3mp.exe"' in processes.lower():
        parser.error('Close the existing game before reusing its test installation')
else:
    RUN = output_path(REPOSITORY / '.local/loading-traces' / (time.strftime('%Y%m%d-%H%M%S') + f'-{os.getpid()}'), REPOSITORY)
# The original disc root is an input-only baseline; all runtime output roots
# remain explicitly confined to RUN/CACHE below. Never copy the disc as a silo.
GAME = (ROOT if options.game and options.game.resolve(strict=True) == ROOT
        else output_path(options.game or ROOT / '.local/custom-maps-play', ROOT))
CACHE = output_path(options.cache_root or RUN / 'cache', ROOT)
EXE = options.exe.resolve(strict=True)
# Verified against each build's IssueDraw COFF symbol and linked prologue.
DRAW_RVAS = {
    # Installed Oct-26 runtime: RTTI/vtable + original virtual layout and
    # linked draw/register/shader reads verified by battle-canyon-rebuild/
    # resolve_installed_draw.py (the newer COFF includes SetSceneMarkers).
    'e927230adacf9075bc14e3dceef6b51a73d9317b78f4f6b1e9bc99ac69f29380': 0x14fd80,
    '17cb0de3dac58feefe00d86b704532e290bfbc200a53aecdec2361b70ab6dab1': 0x14fd60,
    'c9f3b77b65d46dbfc382f6b16e5f44c6dac883f2253c62887fcc165aa6087e4c': 0x14e740,
    'e90c5b368dc9c97b83bdf33954b4b3277e329da756169e8f0c8c21b40205985d': 0x14f0a0,
}
draw_rva = DRAW_RVAS.get(hashlib.sha256((EXE.parent / 'rexgpu-xenos.dll').read_bytes()).hexdigest()) if options.sample_draws else None
if options.sample_draws and draw_rva is None:
    raise SystemExit('Draw diagnostic requires the verified GPU plugin.')
if hashlib.sha256(EXE.read_bytes()).hexdigest() != options.expected_exe_sha256.lower():
    raise SystemExit('This diagnostic requires the verified runtime build; function addresses are build-specific.')
if not (GAME / 'maps' / (options.slot + '.map')).is_file():
    raise SystemExit('Missing staged map for selected slot')
if options.slow_turn_forge and not options.slow_turn_check:
    parser.error('--slow-turn-forge requires --slow-turn-check')
if options.slow_turn_check and (not options.exclusive_input or options.walk_check or options.turn_duration_ms < 1000 or options.turn_duration_ms > 60000 or options.seconds < 170):
    parser.error('Slow turn requires exclusive replay, 170+ seconds, no walk and 1-60 seconds duration')
if options.sample_observer:
    from cache_reader import Cache
    from forge_gulch_boundary import boundary_y
    observer_map = options.dlc_payload / (options.dlc_map + '.map') if options.dlc_payload and options.dlc_map else GAME / 'maps' / (options.slot + '.map')
    cache = Cache(observer_map)
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
if options.trace_console_loader:
    FUNCS.update({0x825984D8: 'console_file_open',
                  0x82205B80: 'console_dependency_check',
                  0x82481E80: 'console_fatal_dispatch',
                  0x821B0290: 'console_load_recovery',
                  0x8222B1D0: 'console_stream_file_open'})
if options.quiet_timing:
    FUNCS.pop(0x82241478)
if options.audio_frames:
    if not 100 <= options.audio_after_seconds < options.seconds - 15:
        parser.error('Audio observation must start during bounded gameplay, at least 15 seconds before watchdog')
    FUNCS[0x82724634] = 'audio_submit'
if options.trace_allocator or options.sample_resource_cache:
    FUNCS[0x822c2058] = 'resource_compact'
    FUNCS[0x822c2480] = 'resource_move'
if options.forge_scenery_check:
    FUNCS[0x822835E0] = 'forge_object_radius'
if options.sample_font_cache:
    FUNCS[0x82201c50] = 'font_character_insert'
if options.trace_memory:
    # Retail XEX import ordinals C6 / BA / BD, resolved through its import records.
    FUNCS.update({0x82723fa4: 'memory_statistics', 0x82723b64: 'physical_allocate',
                  0x82723b94: 'physical_free'})
if options.trace_bsp_seams:
    FUNCS[0x820abe50] = 'bsp_seam_bind'
if options.trace_scenario_objects:
    FUNCS.update({0x82335bc8:'scenario_object_create',0x82346f50:'scenario_object_prepare',
                  0x8232f3d8:'object_new'})
if options.dlc_payload or options.dlc_package or options.dlc_installed_root:
    # Verified original XEX type-1 import record 0x0100025c (xam ordinal 604).
    FUNCS[0x82723d54] = 'content_enumerate'
    FUNCS[0x821f68e8] = 'mapinfo_read'
    FUNCS[0x821f6f48] = 'mapinfo_register'
    if options.trace_dlc_paths:
        FUNCS[0x82206238] = 'cache_path_resolve'
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
if options.profile_seed:
    seed = options.profile_seed.resolve(strict=True)
    seed.relative_to(REPOSITORY)
    destination = RUN / '4D5307E6/profile/User'
    destination.mkdir(parents=True)
    manifest = []
    for name in ('63E83FFE', '63E83FFF'):
        source = (seed / name).resolve(strict=True)
        source.relative_to(REPOSITORY)
        data = source.read_bytes()
        if not 0 < len(data) <= 65536:
            raise SystemExit('Unexpected title-specific profile setting size')
        (destination / name).write_bytes(data)
        manifest.append({'source': str(source), 'name': name, 'bytes': len(data),
                         'sha256': hashlib.sha256(data).hexdigest()})
    (RUN / 'profile-seed.json').write_text(json.dumps(manifest, indent=2) + '\n')
if sum(bool(x) for x in (options.dlc_payload, options.dlc_package, options.dlc_installed_root)) > 1:
    raise SystemExit('Use one DLC installation source per run')
if options.dlc_installed_root:
    installed = options.dlc_installed_root.resolve(strict=True)
    installed.relative_to(REPOSITORY)
    # Reuse immutable content only. Linking an entire previous run also links
    # logs, captures and writable caches, corrupting the previous evidence.
    content_roots = [installed / p for p in ('0000000000000000/4D5307E6/00000002',
                                            '0000000000000000/4D5307E6/Headers/00000002',
                                            '4D5307E6/Headers/00000002')]
    for source in (p for root in content_roots for p in root.rglob('*')):
        if source.is_symlink():
            raise SystemExit('Installed content must not contain symlinks')
        if source.is_file():
            destination = RUN / source.relative_to(installed)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if options.reuse_run and destination.exists():
                if not os.path.samefile(source, destination):
                    raise SystemExit('Reused installed content differs from the requested immutable source')
            else:
                os.link(source, destination)
if options.dlc_payload:
    payload = options.dlc_payload.resolve(strict=True)
    payload.relative_to(REPOSITORY)
    package = RUN / '0000000000000000/4D5307E6/00000002/OpenH3MCustomMaps'
    package.mkdir(parents=True)
    for source in payload.iterdir():
        if not source.is_file() or source.is_symlink():
            raise SystemExit('DLC payload must contain ordinary flat files')
        os.link(source, package / source.name)
if options.shader_cache_seed:
    seed = options.shader_cache_seed.resolve(strict=True)
    seed.relative_to(ROOT)  # Project confinement applies to cache inputs too.
    shutil.copytree(seed, CACHE / 'shaders', dirs_exist_ok=True)
layout_sources = []
if options.saved_layout_library:
    library = options.saved_layout_library.resolve(strict=True)
    library.relative_to(REPOSITORY)
    if not options.layout_menu_check:
        raise SystemExit('Multi-layout discovery currently requires --layout-menu-check')
    layout_sources.extend(sorted(library.glob('*.bin')))
if options.saved_layout and options.saved_layout.resolve(strict=True) not in layout_sources:
    layout_sources.append(options.saved_layout.resolve(strict=True))
for source in layout_sources:
    source.relative_to(REPOSITORY)
    data = source.read_bytes()
    if data[:4] != b'_blf' or data[0x30:0x34] != b'chdr':
        raise SystemExit('Expected native saved-layout BLF')
    identity = struct.unpack_from('>Q', data, 0x40)[0]
    # Original XEX names saved map containers usermap%016lX%lX and their
    # internal file sandbox.map. SDK player zero uses this offline XUID.
    destination = RUN / 'B13EBABEBABEBABE/4D5307E6/00000001' / f'usermap{identity:016X}0'
    destination.mkdir(parents=True, exist_ok=bool(options.reuse_run))
    shutil.copyfile(source, destination / 'sandbox.map')
env = os.environ.copy()
env.update(TEMP=str(RUN / 'temp'), TMP=str(RUN / 'temp'),
           LOCALAPPDATA=str(RUN / 'profile'), APPDATA=str(RUN / 'profile'))
input_steps = ['45000:DOWN+220', '46000:A+250', '55000:UP+220', '56000:A+250']
if options.forge_existing_pair_check or options.slow_turn_forge or options.forge_boundary_check or options.forge_palette_check or options.forge_vehicle_check or options.forge_scenery_check or options.forge_water_check or options.forge_sanctuary_check:
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
island_present = False
force_cove = False
if options.dlc_map or options.dlc_preview_tour:
    # Island sorts immediately after Gulch. Detect its presence instead of
    # silently selecting the wrong map when testing older four-map bundles.
    island_present = options.dlc_map == 'forge_island'
    for directory in (options.dlc_payload, options.dlc_installed_root):
        if directory and any(directory.rglob('forge_island.mapinfo')):
            island_present = True
    if options.dlc_package:
        from verify_dlc_stfs import data_block, read_directory
        with options.dlc_package.open('rb') as package:
            base, directory, _ = read_directory(package)
            island_present |= any(directory[n:n+40].split(b'\0')[0] == b'forge_island.mapinfo' for n in range(0,len(directory),64))
            for n in range(0,len(directory),64):
                if directory[n:n+40].split(b'\0')[0] == b'forge_island.mapinfo':
                    first = int.from_bytes(directory[n+47:n+50], 'little')
                    package.seek(base + data_block(first)*4096 + 0x44)
                    force_cove = package.read(64).decode('utf-16-be').split('\0')[0] == 'Force Cove'
if options.dlc_map:
    if not (options.dlc_payload or options.dlc_package or options.dlc_installed_root):
        raise SystemExit('--dlc-map requires DLC content')
    from dlc_menu_route import menu_route
    direction, steps = menu_route((options.game or options.project) / 'maps/info',
                                  (options.dlc_payload, options.dlc_installed_root),
                                  options.dlc_package, options.dlc_map)
    input_steps = ['45000:DOWN+220', '46000:A+250', '55000:UP+220', '56000:A+250']
    if options.forge_existing_pair_check or options.slow_turn_forge or options.forge_boundary_check or options.forge_palette_check or options.forge_vehicle_check or options.forge_scenery_check or options.forge_water_check or options.forge_sanctuary_check or options.layout_overview_check or options.forge_overview_check:
        input_steps.insert(1, '45500:DOWN+220')
    input_steps += [f'{58000 + n * 700}:{direction}+250' for n in range(steps)]
    # Longer lists must finish navigation before confirming the selected map.
    route_confirm = max(70000, 58000 + steps * 700 + 500)
    route_delay = route_confirm - 70000
    input_steps += [f'{route_confirm}:A+250', f'{72000 + route_delay}:A+250',
                    f'{74000 + route_delay}:DOWN+220', f'{95000 + route_delay}:A+250']
if options.dlc_menu_check:
    if not (options.dlc_payload or options.dlc_package or options.dlc_installed_root):
        raise SystemExit('--dlc-menu-check requires a DLC payload or package')
    if options.dlc_map:
        # Keep navigation to the requested map, but do not accept it/start.
        input_steps = [step for step in input_steps if int(step.split(':')[0]) < route_confirm]
    else:
        input_steps = ['45000:DOWN+220', '46000:A+250', '55000:UP+220', '56000:A+250']
if options.layout_menu_check:
    if not options.saved_layout or not options.dlc_map:
        raise SystemExit('--layout-menu-check needs --saved-layout and --dlc-map')
    input_steps = [step for step in input_steps if int(step.split(':')[0]) <= 70000]
elif options.saved_layout:
    if not options.dlc_map or options.manual_input:
        raise SystemExit('--saved-layout requires a scripted DLC map route')
    # Verified native list: built-in base first, isolated saved layout second.
    input_steps.append('71000:DOWN+200')
    input_steps.sort(key=lambda step: int(step.split(':')[0]))
if options.layout_overview_check:
    if not options.saved_layout or options.layout_menu_check or options.walk_check or options.seconds < 165:
        raise SystemExit('--layout-overview-check requires a saved layout, 165 seconds, and no walk/menu check')
    input_steps.extend(['118000:UP+200', '120000:RB+6000',
                        '127000:RSDOWN+600', '135000:RSRIGHT+1600',
                        '150000:RSRIGHT+1600'])
if options.forge_overview_check:
    if not options.dlc_map or options.manual_input or options.walk_check or options.dlc_menu_check or options.seconds < 170:
        raise SystemExit('--forge-overview-check requires a scripted DLC route, 170 seconds and no walk/menu check')
    if options.dlc_map == 'lockout_classic':
        # Authored indoor spawn faces yaw 249 degrees. Left strafe heads 339
        # through the doorway; main-BSP ray audit clears 12+ units then ascent.
        # Generic forward/ascent is blocked by this room's ceiling.
        input_steps.extend(['118000:UP+200', '120000:LSLEFT+7500',
                            '128000:RB+6000', '135000:RSRIGHT+1100',
                            '137000:RSDOWN+1100'])
    elif options.dlc_map == 'boarding_action':
        # Native 20261025-131026 reaches the central gap at (4.76,-1.61,14.52).
        # Source Basis geometry lies southwest; rise above the hull before
        # aiming there. See work/boarding-action/sky-material-directions.json.
        input_steps.extend(['118000:UP+200', '120000:LSUP+3000',
                            '123000:RB+12000', '136000:RSLEFT+450',
                            '137000:RSUP+550'])
    else:
        input_steps.extend(['118000:UP+200', '120000:LSUP+3000',
                            '123000:RB+6000', '130000:RSDOWN+900'])
if options.dlc_preview_tour:
    if not options.dlc_menu_check:
        raise SystemExit('--dlc-preview-tour requires --dlc-menu-check')
    # Capture at 65000, 85000, 105000, 125000, 145000 ms. First picture
    # checks the signed stock preview; subsequent pictures check custom artwork.
    input_steps += [f'{70000+n*700}:UP+120' for n in range(7 + int(island_present))]
    input_steps += [f'{90000+n*700}:DOWN+120' for n in range(11 + int(island_present))]
    input_steps += [f'{110000+n*700}:DOWN+120' for n in range(2)]
    input_steps += [f'{130000+n*700}:DOWN+120' for n in range(7)]
if options.forge_sanctuary_check:
    if options.dlc_map != 'forge_island' or options.manual_input or options.seconds < 180:
        raise SystemExit('--forge-sanctuary-check requires Force Cove and 180 seconds')
    input_steps.extend(['118000:UP+200', '120000:RB+6500',
                        '119900:LT+55100', '128000:LSUP+30000', '161000:RSLEFT+2000'])
if options.forge_water_check:
    if options.slot != 'sandbox' or options.manual_input or options.walk_check or options.seconds < 180:
        raise SystemExit('--forge-water-check requires scripted Sandbox and a 180-second watchdog')
    input_steps.extend(['118000:UP+200', '120000:RB+8000',
                        '120000:LT+8000', '145000:RSLEFT+800'])
if options.forge_boundary_check:
    # Native 20261021-173147 route probe confirms Forge / Sandbox. From the
    # +X spawn facing, left strafe travels +Y toward the curved split.
    # Halo 3's original manual documents LT as monitor thrust. At ordinary
    # speed the 40-second probe travels only ~87 units of the ~184-unit gap.
    input_steps.extend(['118000:UP+200', '120000:RB+8000',
                        '119900:LT+58100',
                        '130000:LSDOWN+48000' if options.dlc_map == 'forge_island' else '130000:LSLEFT+48000'])
    # Island starts facing Sanctuary (+Y). Backward flight approaches its
    # eastern divider while retaining a view of the island behind the player.
if options.forge_palette_check:
    input_steps.extend(['118000:UP+200', '121000:X+200'])
if options.forge_scenery_check:
    input_steps.extend(['118000:UP+200', '121000:X+200', '122000:RB+200',
                        '123000:RB+200', '124000:RB+200'])
    input_steps.extend(f'{125000+n*500}:DOWN+150' for n in range(options.forge_scenery_index))
    create_time = max(130000, 126000+options.forge_scenery_index*500)
    # Leave time after Advanced Forge release for a native capture within
    # the 180-second watchdog (the replay clock starts after process launch).
    release_time = max(140000, create_time+3000) if forge_test else 160000
    if options.advanced_forge_anchor_check:
        release_time = 154000
    if options.advanced_forge_test_menu:
        release_time = {'resume': 150000, 'lifecycle': 154000, 'rotation': 154000, 'rotation-cancel': 154000}.get(options.advanced_forge_test_menu_case, 146000)
    input_steps.extend([f'{create_time}:A+200', f'{release_time}:A+200'])
    if options.advanced_forge_base_round_check:
        input_steps.extend([f'{release_time+1000}:LSDOWN+3000',f'{release_time+2000}:RB+2500',
                            f'{release_time+4500}:RSDOWN+650',f'{release_time+6000}:LSLEFT+800',
                            f'{release_time+20000}:UP+200'])
    else:
        input_steps.append(f'{release_time+2000}:UP+200')
    if forge_test:
        # Move the held piece so the original Forge placement event executes.
        input_steps.append(f'{131000 if options.advanced_forge_test_menu else max(135000,create_time+1000)}:LSRIGHT+{300 if options.advanced_forge_test_menu else 1000}')
    if options.advanced_forge_test_menu:
        menu_steps = ['132000:X+200', '133000:DOWN+200', '133500:DOWN+200',
                      '134000:DOWN+200', '135000:A+200', '135500:LEFT+200',
                      '136000:A+200', '137000:A+200', '137500:RIGHT+200',
                      '138000:A+200', '139000:A+200', '139500:RIGHT+200',
                      '140000:A+200']
        if options.advanced_forge_test_menu_case in ('rotation', 'rotation-cancel'):
            if not options.saved_layout:
                menu_steps += ['140750:DOWN+180']
            menu_steps += ['141000:DOWN+180', '141250:DOWN+180', '141500:DOWN+180',
                           '141750:DOWN+180', '142000:A+200', '142500:RIGHT+200',
                           '144500:RIGHT+200', '147000:B+200' if options.advanced_forge_test_menu_case == 'rotation-cancel' else '147000:A+200']
        else:
            menu_steps += ['141000:DOWN+200', '141500:A+200', '142000:RIGHT+200', '142500:A+200']
        if options.advanced_forge_test_menu_case == 'lifecycle':
            # Commit one position edit, reopen, preview a second value and
            # cancel it, then reopen again to inspect the retained first value.
            menu_steps += ['143000:B+200', '144000:X+200']
            menu_steps += [f'{145000+n*250}:DOWN+180' for n in range(4)]
            menu_steps += ['146000:A+200', '146500:RIGHT+200', '147000:B+180',
                           '147500:B+180', '148000:X+200']
            menu_steps += [f'{149000+n*250}:DOWN+180' for n in range(4)]
            menu_steps += ['152000:B+200']
        elif options.advanced_forge_test_menu_case == 'resume':
            # Position selection locks the held pose. Scroll to Movement and
            # resume Free dragging through the real native submenu.
            menu_steps += [f'{143000+n*250}:DOWN+180' for n in range(6)]
            menu_steps += ['145000:A+200', '145500:LEFT+200', '146000:A+200', '147000:B+200']
            input_steps.append('148000:LSRIGHT+500')
        elif options.advanced_forge_test_menu_case in ('rotation', 'rotation-cancel'):
            menu_steps += ['148000:B+200']
        else:
            menu_steps += ['144000:B+200']
        input_steps.extend(menu_steps)
if options.forge_delete_check:
    # The ordinary menu route drops at154s and switches to player at156s.
    # Neither belongs in a deletion-only regression; the latter can produce
    # a black transition frame exactly when the post-delete proof is captured.
    input_steps = [step for step in input_steps if int(step.split(':', 1)[0]) < 152000]
    input_steps.append('152000:Y+200')
if options.forge_existing_pair_check:
    # Sustain the pull to measure whether displacement continues accumulating, return, then move the
    # unladen monitor sideways so re-grab hits wall rather than the doorway.
    input_steps.extend(['118000:UP+200',
                        *([f'120000:RB+{options.forge_pair_approach_up_ms}'] if options.forge_pair_approach_up_ms else []),
                        '130000:A+200',
                        *(['132500:RB+3000','135500:LSDOWN+4000'] if options.forge_pair_lift else ['132500:LSDOWN+7000']),
                        '142000:LSUP+7000','150000:A+200','151000:LSRIGHT+500',
                        '153000:A+200','155000:LSLEFT+500','157000:A+200'])
if options.forge_manipulation_check:
    # Keep the established lobby/palette route. Replace only the held phase.
    # A returns through native release and grab; movement uses ordinary input.
    input_steps = [step for step in input_steps if int(step.split(':',1)[0]) < create_time]
    input_steps.extend([f'{create_time}:A+200', f'{create_time+2500}:LSRIGHT+500',
                        f'{create_time+6000}:A+200', f'{create_time+7500}:A+200',
                        f'{create_time+9500}:LSLEFT+500', f'{create_time+12000}:A+200'])
if options.hornet_occlusion_check:
    input_steps.extend(['122500:LSUP+900','125000:RB+1800',
                        '139000:RSRIGHT+1800','149000:RSLEFT+1800'])
if options.forge_vehicle_check:
    # Original Sandbox scenario vehicle palette starts with the stock Banshee.
    # Captures must establish actual category, placement and entry outcomes.
    input_steps.extend(['118000:UP+200', '121000:X+200', '123000:RB+200',
                        '127000:A+200', '129000:A+200', '131000:UP+200',
                        '133000:LSUP+3000', '139000:RB+1800'])
    input_steps.extend(f'{124000+n*200}:DOWN+100' for n in range(options.forge_vehicle_index))
    if options.vehicle_boundary_flight:
        # Aim toward +Y and climb before leveling over the coast. The earlier
        # 500-ms turn relied on a cliff deflection and could dive into water.
        input_steps.extend(['142000:RSLEFT+1600', '142000:RSUP+600',
                            '150000:RSDOWN+600', '143000:LSUP+35000', '143000:LT+35000'])
    else:
        input_steps.append('145000:LSUP+10000')
if options.walk_route != 'default' and not options.walk_check:
    raise SystemExit('--walk-route requires --walk-check')
if options.walk_check:
    if options.manual_input:
        raise SystemExit('--walk-check requires scripted input')
    if options.walk_route == 'lockout-light':
        # Private diagnostic spawn faces the audited light from a solid floor.
        # Leave the camera stationary for paired animation captures.
        pass
    elif options.walk_route == 'lockout-exit':
        # Same leftward doorway direction as the audited Forge overview route;
        # use a shorter on-foot movement and retain the authored camera facing.
        input_steps.append('120000:LSLEFT+3000')
    elif options.walk_route == 'elongation':
        # 3longation's diagnostic spawn faces the shipping wall. Strafe along
        # the belt instead of applying the generic turn into that wall.
        input_steps.extend(['120000:LSLEFT+3000', '126000:LSRIGHT+3000'])
    elif options.saved_layout:
        # Preserve the authored spawn-facing direction. The generic base-map
        # turn faces the sea on Paradiso and a wall on Pinnacle.
        input_steps.append('120000:LSUP+1500')
    elif options.dlc_map == 'chiron':
        # Initial spawn faces north. Channel 12's doorway is west at
        # (7.05, 12.16, 0.17); a left strafe approaches that authored portal.
        # Observer samples must establish traversal, not just input completion.
        input_steps.append('120000:LSLEFT+2000')
    elif options.slot == 'chillout' and options.dlc_map != 'chiron':
        # Prisoner's initial ledge opens south after walking west. Native
        # position samples and source collision sightlines establish this path.
        input_steps.extend(['115000:RT+100', '117000:LSRIGHT+1000',
                            '119000:LSUP+3500', '124000:RSLEFT+1800', '130000:RT+100'])
    else:
        input_steps.extend(['120000:RSRIGHT+1600', '124000:LSUP+1500'])
if options.powerup_check:
    input_steps.extend(['132000:LSUP+3000', '138000:LSRIGHT+900', '143000:RT+100'])
if options.slow_turn_check:
    input_steps.append(f'115000:RSSLOWRIGHT+{options.turn_duration_ms}')
if options.inspection_input:
    import re
    if not options.exclusive_input or options.manual_input:
        raise SystemExit('Inspection input requires exclusive process-local replay')
    steps = options.inspection_input.split(',')
    if len(steps) > 16:
        raise SystemExit('Inspection input is limited to 16 bounded steps')
    for step in steps:
        match = re.fullmatch(r'(\d+):([A-Z]+)\+(\d+)', step)
        if not match:
            raise SystemExit('Invalid inspection input step: ' + step)
        start, length = int(match[1]), int(match[3])
        if start < 100000 or not 0 < length <= 30000 or start + length >= options.seconds * 1000:
            raise SystemExit('Inspection input exceeds the bounded gameplay interval')
    # The existing H3IR encoder validates button names before launching the child.
    input_steps.extend(steps)
if options.forge_spawn_clearance_check:
    if not options.forge_scenery_check or options.advanced_forge_test_position:
        raise SystemExit('Spawn clearance requires ordinary scenery creation without a forced pose')
    def after_ascent(step):
        at, action = step.split(':', 1)
        return f'{int(at) + (6000 if int(at) >= 121000 else 0)}:{action}'
    input_steps = [after_ascent(step) for step in input_steps]
    input_steps.append('118500:RB+6000')
    if options.advanced_forge_test_menu:
        menu_steps = [after_ascent(step) for step in menu_steps]
args = [str(EXE), f'--game_data_root={GAME}',
        f'--user_data_root={RUN}', f'--cache_root={CACHE}',
        f'--log_file={RUN / "trace-runtime.log"}', '--keyboard_controller=false',
        '--input_script=' + ','.join(input_steps), '--input_script_button_state=true',
        '--input_script_keystrokes=false']
if options.video_surface_quality:
    detail, filtering = {'original':(0,-1),'balanced':(1,2),'performance':(2,0)}[options.video_surface_quality]
    args += [f'--texture_detail_reduction={detail}',f'--anisotropic_override={filtering}']
if options.dlc_payload or options.dlc_package or options.dlc_installed_root:
    args += ['--log_level=' + ('info' if options.quiet_timing else 'debug'),
             '--log_max_file_size_mb=5', '--log_max_files=4']
if options.dlc_package:
    package = options.dlc_package.resolve(strict=True)
    package.relative_to(REPOSITORY)
    args += [f'--halo3mp_install_content={package}']
if options.manual_input:
    args = [arg for arg in args if not arg.startswith(('--keyboard_controller=', '--input_script'))]
if forge_test or options.exclusive_input:
    if options.manual_input:
        raise SystemExit('Exclusive replay cannot be combined with manual input')
    from script_input_replay import encode
    replay = RUN / 'forge-input.h3ir'
    # Unlocked menus repeat long held presses; match the established FPS benchmark route.
    if options.fpsunlock:
        input_steps = [step.rsplit('+', 1)[0] + '+' + str(options.menu_press_ms)
                       if int(step.split(':', 1)[0]) <= 95000 else step
                       for step in input_steps]
    if options.menu_route:
        import re
        input_steps = options.menu_route.split(',')
        if len(input_steps) > 24 or any(not re.fullmatch(r'\d+:(UP|DOWN|A|B|START)\+\d+', s) for s in input_steps):
            raise SystemExit('Invalid bounded menu route')
        if any(not 0 < int(s.split(':')[0]) < options.seconds*1000-1000 or not 0 < int(s.rsplit('+',1)[1]) <= 500 for s in input_steps):
            raise SystemExit('Menu route outside bounded run')
    if options.menu_delay_ms:
        input_steps = [str(int(step.split(':', 1)[0]) + options.menu_delay_ms) + ':' + step.split(':', 1)[1]
                       for step in input_steps]
    replay.write_bytes(encode(input_steps))
    args = [arg for arg in args if not arg.startswith('--input_script=')]
    args.append(f'--input_state_replay={replay}')
if forge_test:
    args.append('--halo3mp_smoke_route=advanced-forge-replay')
    if options.advanced_forge_data:
        forge_data = options.advanced_forge_data.resolve(strict=True)
        forge_data.relative_to(REPOSITORY)
        args += [f'--halo3mp_advanced_forge={"false" if options.advanced_forge_test_coordinates else "true"}', f'--halo3mp_advanced_forge_data={forge_data}']
    args += [f'--halo3mp_advanced_forge_trace={RUN / "forge-scene.bin"}']
    if options.advanced_forge_test_position:
        args += [f'--halo3mp_advanced_forge_test_position={options.advanced_forge_test_position}']
    if options.advanced_forge_test_coordinates:
        args += [f'--halo3mp_advanced_forge_test_coordinates={options.advanced_forge_test_coordinates}']
    if options.advanced_forge_test_physics:
        args += [f'--halo3mp_advanced_forge_test_physics={options.advanced_forge_test_physics}']
    if options.advanced_forge_test_menu:
        # Gameplay and native UI consume different controller interfaces.
        # Supply native button events as well as exclusive replay state, only
        # for the menu phase; no OS input or duplicate pre-game navigation.
        args = [arg for arg in args if not arg.startswith('--input_script_keystrokes=')]
        args += ['--input_script_keystrokes=true', '--input_script=' + ','.join(menu_steps)]
if options.font_upload_probe:
    args += [f'--d3d12_upload_probe_path={RUN / "font-uploads.bin"}',
             '--d3d12_upload_probe_address=65826816',
             '--d3d12_upload_probe_size=524288']
if options.diagnostic_no_vsync:
    args += ['--vsync=false']
if options.fpsunlock:
    args.append('--fpsunlock')
if options.diagnostic_async_occlusion:
    args.append('--d3d12_async_occlusion_readback=true')
if options.diagnostic_display_phase_off:
    args.append('--host_output_display_phase=false')
if options.timing_diagnostics:
    args += ['--d3d12_log_present_timing=true', '--d3d12_slow_preparation_ms=8']
capture = options.capture
duration = options.seconds
if options.host_capture_after_ms is not None:
    if not 0 < options.host_capture_after_ms < duration * 1000:
        raise SystemExit('Host capture must be inside the bounded run')
    args += [f'--d3d12_host_capture_path={RUN / "host-frame.bmp"}',
             f'--d3d12_host_capture_after_ms={options.host_capture_after_ms}']
if capture:
    if list(RUN.glob('proof-loaded*.png')):
        raise RuntimeError('Capture destination already contains evidence from another run')
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


expected_map = GAME / 'maps' / (options.slot + '.map')
if options.dlc_map and options.dlc_payload:
    expected_map = options.dlc_payload.resolve(strict=True) / (options.dlc_map + '.map')
if options.dlc_map and options.dlc_installed_root:
    matches = list(options.dlc_installed_root.rglob(options.dlc_map + '.map'))
    if len(matches) != 1:
        raise SystemExit('Expected exactly one installed custom map')
    expected_map = matches[0]
if options.dlc_map and options.dlc_package:
    log('input_package', path=str(options.dlc_package), expected_map=options.dlc_map,
        sha256=hashlib.sha256(options.dlc_package.read_bytes()).hexdigest(),
        executable=str(EXE), seconds_limit=duration)
else:
    log('input_map', path=str(expected_map),
        sha256=hashlib.sha256(expected_map.read_bytes()).hexdigest(),
        executable=str(EXE), seconds_limit=duration)
verified_maps = set()
creation_flags = subprocess.CREATE_NO_WINDOW | (0x2 if options.trace_memory or options.dlc_payload or options.dlc_package or options.dlc_installed_root else 0)
# DEBUG_ONLY_THIS_PROCESS installs observation before any guest startup allocations.
if options.slow_turn_check:
    args.append('--d3d12_present_timing_end_ms=210000')
(RUN / 'launch-command.json').write_text(json.dumps(args, indent=2))
if options.reuse_run:
    # The runtime logger appends. A reused installation must not mix old
    # interaction records into this run's diagnostics or acceptance checks.
    (RUN / 'trace-runtime.log').write_text('')
(RUN / 'launch-clock.json').write_text(json.dumps({'wall_time': time.time(), 'monotonic': time.monotonic()}))
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
audio_address = None
audio_armed = False
audio_blocks = []
audio_driver = None
guest_memory_base = None
guest_r13 = None
observer_sample_time = 0
variant_sample_time = 0
variant_capacity_error = None
object_sample_time = 0
sample_object_tags = {}
sample_scenario_arrays = {}
sample_scenario_index = None
scenario_sampled = False
if options.sample_object_map:
    from cache_reader import Cache
    object_map_path = options.sample_object_map.resolve()
    if not object_map_path.is_relative_to(REPOSITORY):
        raise ValueError('Object sampling cache must stay inside the repository')
    object_cache = Cache(object_map_path)
    sampled_groups = ('mach', 'bloc', 'eqip') if options.sample_equipment_objects else ('mach', 'bloc')
    if options.sample_player_objects:
        sampled_groups += ('bipd',)
    sample_object_tags = {t['salt'] << 16 | i: object_cache.name(i)
                          for i, t in object_cache.tags.items() if t['group'] in sampled_groups}
    sample_scenario_index = next(i for i,t in object_cache.tags.items() if t['group']=='scnr')
    scenario_offset = object_cache.tags[sample_scenario_index]['offset']
    for offset,stride in ((0x5e8,176),(0x5f4,48)):
        rows = object_cache.block(scenario_offset+offset,stride)
        payload = b''.join(object_cache.data[a:a+stride] for a in rows)
        sample_scenario_arrays[offset] = (stride,len(rows),hashlib.sha256(payload).hexdigest())
    object_cache.close()
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
    if not (options.trace_memory or options.dlc_payload or options.dlc_package or options.dlc_installed_root):
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
        if (options.sample_native_variant and guest_memory_base and guest_r13
                and now-started >= 150 and now-variant_sample_time >= 5):
            variant_sample_time = now
            try:
                def variant_word(address):
                    return struct.unpack('>I', read(guest_memory_base+(address & 0xffffffff),4))[0]
                tls = variant_word(guest_r13)
                engine = variant_word(tls+0x64)
                if not 0x10000 <= engine < 0xc0000000:
                    raise ValueError('Native engine pointer outside guest range')
                data = read(guest_memory_base+engine+0x78,0xe090)
                if len(data)!=0xe090 or struct.unpack_from('>H',data,0xf8)[0]!=12:
                    raise ValueError('Not a native H3 version-12 variant')
                (RUN/'native-variant.bin').write_bytes(data)
                scenario_count,slot_count,quota_count=struct.unpack_from('>3H',data,0xfa)
                if not 0<=scenario_count<=slot_count<=640 or quota_count>256:
                    variant_capacity_error = f'Native variant capacity exceeded: scenario={scenario_count}, objects={slot_count}/640, quotas={quota_count}/256'
                    log('native_variant_capacity_failure',detail=variant_capacity_error)
                log('native_variant_sample', map_id=struct.unpack_from('>I',data,0x100)[0],
                    scenario_count=scenario_count,slot_count=slot_count,quota_count=quota_count,
                    occupied_slots=sum(bool(struct.unpack_from('>H',data,0x130+i*0x54)[0]&1) for i in range(640)))
            except (OSError, ValueError) as error:
                log('native_variant_sample_error',detail=str(error))
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
                    selected_partition_margin=(position[1]-float(boundary_y(position[0]))) *
                        (1 if options.dlc_map == 'forge_island' else -1),
                    forward=struct.unpack_from('>3f', data, 40), observer_bytes=data.hex(),
                    soft_ceiling_records=flags)
            except (OSError, ValueError) as error:
                log('observer_sample_error', detail=str(error))
        if (sample_object_tags and guest_memory_base and guest_r13
                and now-started >= 110 and now-object_sample_time >= options.sample_object_interval):
            object_sample_time = now
            try:
                def object_word(address):
                    return struct.unpack('>I', read(guest_memory_base+address, 4))[0]
                if not scenario_sampled:
                    tag_table = object_word(0x827f0f8c)
                    scenario_root = object_word(tag_table+sample_scenario_index*8+4)
                    comparisons = []
                    for offset,(element_size,expected_count,expected_hash) in sample_scenario_arrays.items():
                        n = object_word(scenario_root+offset)
                        pointer = object_word(scenario_root+offset+4)
                        if not 0 <= n <= 4096:
                            raise ValueError('Live scenario object array exceeds diagnostic bound')
                        payload = read(guest_memory_base+pointer,n*element_size) if n else b''
                        actual_hash = hashlib.sha256(payload).hexdigest()
                        comparisons.append(dict(offset=hex(offset),count=n,expected_count=expected_count,
                            sha256=actual_hash,expected_sha256=expected_hash,
                            matches=n==expected_count and actual_hash==expected_hash))
                    log('scenario_object_arrays',root=hex(scenario_root),arrays=comparisons)
                    scenario_sampled = True
                array = object_word(object_word(guest_r13)+0xa8)
                header = read(guest_memory_base+array, 0x48)
                count, stride = struct.unpack_from('>2I', header, 0x20)
                if header[:7] != b'object\0' or not 0 < count <= 4096 or stride != 16:
                    raise ValueError('Unexpected object table header: '+header.hex())
                address = struct.unpack_from('>I', header, 0x44)[0]
                heads = read(guest_memory_base+address, count*stride)
                objects = []
                for index in range(count):
                    salt = struct.unpack_from('>H', heads, index*16)[0]
                    body = struct.unpack_from('>I', heads, index*16+12)[0]
                    if not salt or not 0x80000000 <= body < 0xe0000000:
                        continue
                    try:
                        data = read(guest_memory_base+body, 256)
                    except OSError:
                        continue
                    tag = struct.unpack_from('>I', data)[0]
                    if tag in sample_object_tags:
                        object_header = heads[index*16:(index+1)*16]
                        data_size = struct.unpack_from('>H', object_header, 6)[0]
                        if options.sample_object_body_bytes > 256 and 256 <= data_size <= 65535:
                            try:
                                data = read(guest_memory_base+body, min(data_size, options.sample_object_body_bytes))
                            except OSError:
                                pass  # Retain the readable prefix, never infer missing fields.
                        objects.append(dict(handle=hex(salt << 16 | index),
                                            tag=hex(tag), name=sample_object_tags[tag], body=data.hex(),
                                            object_header=object_header.hex(), allocation_size_candidate=data_size))
                log('machine_crate_snapshot', header=header.hex(), objects=objects)
            except (OSError, ValueError) as error:
                log('object_sample_error', detail=str(error))
        event = C.create_string_buffer(176)
        if not wait_event(event, 100):
            if proc.poll() is not None:
                break
            now = time.monotonic()
            if options.sample_draws and draw_address and not draw_armed and now - started >= options.draw_after_seconds:
                check(kernel.DebugBreakProcess(ph))
            if audio_address and not audio_armed and now - started >= options.audio_after_seconds:
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
        if audio_address and not audio_armed and time.monotonic() - started >= options.audio_after_seconds:
            breakpoint(audio_address)
            audio_armed = True
            log('audio_capture_armed', address=hex(audio_address))
        if options.sample_draws and draw_address and not draw_armed and time.monotonic() - started >= options.draw_after_seconds:
            breakpoint(draw_address)
            draw_armed = True
            log('draw_trace_armed', address=hex(draw_address))
        if code == 3:  # CREATE_PROCESS_DEBUG_EVENT
            image_base = struct.unpack_from('<Q', event, 40)[0]
            for rva, descriptor in rvas.items():
                address = image_base + rva
                entries[address] = descriptor
                if descriptor[1] == 'audio_submit':
                    audio_address = address
                else:
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
                        draw_address = module_base + draw_rva
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
                    elif address == audio_address:
                        # PPCContext order is r3,r0,r1,r2,r4. XAudio submission
                        # receives a 0x4155xxxx driver and six sequential BE-float
                        # channels, 256 samples/channel at 48 kHz (SDK contract).
                        regs = struct.unpack('<5Q', read(rcx, 40))
                        driver, samples = regs[0] & 0xffffffff, regs[4] & 0xffffffff
                        if driver & 0xffff0000 != 0x41550000 or (audio_driver is not None and driver != audio_driver):
                            raise ValueError('Unexpected native audio driver; refusing mixed-client capture')
                        audio_driver = driver
                        audio_blocks.append(read(rdx + samples, 6 * 256 * 4))
                        if len(audio_blocks) >= options.audio_frames:
                            entries.pop(address)
                            log('audio_capture_complete', frames=len(audio_blocks), driver=hex(driver))
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
                        if options.trace_console_loader and (name.startswith('console_') or name == 'load_204da8'):
                            try:
                                extra['guest_arguments'] = [hex(regs[0] & 0xffffffff)] + [
                                    hex(v & 0xffffffff) for v in struct.unpack('<7Q', read(rcx+32, 56))]
                                extra['guest_lr'] = hex(struct.unpack('<Q', read(rcx+256, 8))[0] & 0xffffffff)
                                if name == 'console_file_open':
                                    extra['path'] = guest_string(rdx, record['argument'])
                                    record['console_path'] = extra['path']
                                if name in ('console_load_recovery', 'console_fatal_dispatch'):
                                    state = read(rdx+0x8295fe50, 344)
                                    extra['retry_flags'] = list(state[:4])
                                    extra['retry_count'] = struct.unpack_from('>I', state, 8)[0]
                                    extra['io_completion_words'] = list(struct.unpack_from('>II', state, 336))
                                if name == 'load_204da8':
                                    state = read(rdx+0x829fe260, 13140)
                                    extra['cache_map'] = state[0x18c:0x1ac].split(b'\0')[0].decode('ascii', 'replace')
                                    extra['copy_state'] = struct.unpack_from('>I', state, 12320)[0]
                                    extra['copy_path'] = state[12357:12613].split(b'\0')[0].decode('ascii', 'replace')
                                    extra['copy_bytes'] = struct.unpack_from('>I', state, 12300)[0]
                                    extra['copy_checksum'] = hex(struct.unpack_from('>I', state, 13136)[0])
                            except (OSError, ValueError) as error:
                                extra['console_trace_error'] = str(error)
                        if name in ('scenario_object_create','scenario_object_prepare'):
                            placement = regs[5] & 0xffffffff
                            extra.update(object_type=regs[0]&0xffffffff,scenario_index=regs[4]&0xffff,
                                         placement=hex(placement))
                            try:
                                extra['placement_bytes'] = read(rdx+placement,84).hex()
                            except OSError as error:
                                extra['read_error'] = str(error)
                            record['object_trace'] = extra.copy()
                        elif name == 'object_new':
                            try:
                                extra['tag'] = hex(struct.unpack('>I',read(rdx+record['argument'],4))[0])
                            except OSError as error:
                                extra['read_error'] = str(error)
                            record['object_trace'] = extra.copy()
                        if name == 'bsp_seam_bind':
                            try:
                                def seam_word(at):
                                    return struct.unpack('>I', read(rdx+(at & 0xffffffff), 4))[0]
                                packed = regs[4] & 65535
                                table = seam_word(0x827f0f8c)
                                scenario = seam_word(table+(record['argument'] & 65535)*8+4)
                                bsp_index, cluster_index = packed >> 8, packed & 255
                                extra.update(packed=hex(packed), scenario=hex(scenario),
                                             bsp_index=bsp_index, cluster_index=cluster_index)
                                bsp_count, bsps = seam_word(scenario+20), seam_word(scenario+24)
                                extra['bsp_count'] = bsp_count
                                if bsp_index < bsp_count:
                                    datum = seam_word(bsps+bsp_index*108+12)
                                    bsp = seam_word(table+(datum & 65535)*8+4)
                                    count, clusters = seam_word(bsp+180), seam_word(bsp+184)
                                    extra.update(bsp=hex(bsp), bsp_datum=hex(datum), clusters=hex(clusters), cluster_count=count)
                                    if cluster_index < count:
                                        cluster = clusters+cluster_index*220
                                        count, pointer = seam_word(cluster+160), seam_word(cluster+164)
                                        extra.update(seam_count=count, seam_pointer=hex(pointer))
                                        if count < 128:
                                            extra['seams'] = read(rdx+pointer, count).hex()
                            except OSError as error:
                                extra['seam_read_error'] = str(error)
                        if name == 'forge_object_radius':
                            table = struct.unpack('>I', read(rdx+0x827f0f8c,4))[0]
                            datum = record['argument']
                            entry = read(rdx+table+(datum&65535)*8,8)
                            extra.update(datum=hex(datum),tag_table=hex(table),entry=entry.hex())
                        if name == 'cache_path_resolve':
                            extra['path'] = read(rdx + record['argument'], 256).split(b'\0')[0].decode('ascii', errors='replace')
                        if name == 'mapinfo_register':
                            try:
                                level = read(rdx + record['argument'], 0x54)
                                extra['map_id'] = struct.unpack_from('>I', level, 12)[0]
                                extra['map_title'] = level[20:84].decode('utf-16-be', errors='replace').split('\0')[0]
                                extra['content_root'] = read(rdx + (regs[5] & 0xffffffff), 256).split(b'\0')[0].decode('ascii', errors='replace')
                            except OSError as error:
                                extra['metadata_read_error'] = str(error)
                        if name in ('physical_allocate', 'physical_free', 'content_enumerate'):
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
                                record['map'] = extra['map']
                            except OSError:
                                pass
                        if name != 'hash_verify':
                            log('enter', tid=tid, function=name, argument=hex(record['argument']), **extra)
                    elif pending.get((tid, address)):
                        record = pending[(tid, address)].pop()
                        result = struct.unpack('<Q', read(record['ctx'], 8))[0]
                        extra = record.get('object_trace',{}).copy()
                        if 'console_path' in record:
                            extra['path'] = record['console_path']
                        if record['name'] == 'memory_statistics' and result & 0xffffffff == 0:
                            words = struct.unpack('>26I', read(record['memory']+record['argument'], 104))
                            extra['statistics_words'] = list(words)
                            extra['available_physical_bytes'] = words[3]*4096
                            extra['heap_accounted_physical_bytes'] = (words[1]-words[2]-words[3])*4096
                            extra['accounting_scope'] = 'Physical heap counters only; excludes independent virtual/XEX heaps'
                        if record['name'] == 'header_verify' and result & 0xFF == 0:
                            extra['failure_text'] = guest_string(record['memory'], record['stack'] - 0x120)
                        if record['name'] == 'header_verify' and result & 0xFF:
                            verified_maps.add(record.get('map'))
                        if record['name'] == 'hash_verify':
                            hash_counts['passed' if result & 0xFF else 'failed'] += 1
                            if result & 0xFF == 0:
                                log('hash_failure', tid=tid, argument=hex(record['argument']),
                                    byte_count=record['bytes'])
                        else:
                            log('return', tid=tid, function=record['name'], result=hex(result), **extra)
                        if (options.dlc_map and record['name'] == 'header_verify'
                                and record.get('map') == options.dlc_map and not result & 0xFF):
                            raise RuntimeError('Selected DLC map failed native header validation')
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
                if (address == draw_address and draw_samples < options.draw_sample_limit) or address in entries or any(a == address and records for (_, a), records in pending.items()):
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
            exit_code = struct.unpack_from('<I', event, 16)[0]
            log('exit', code=exit_code)
            continue_event(pid, tid, status)
            if exit_code:
                raise RuntimeError(f'Game exited with failure 0x{exit_code:08x}')
            break
        check(continue_event(pid, tid, status))
    else:
        log('watchdog', seconds_limit=duration)
    if options.dlc_map and not options.dlc_menu_check and not options.layout_menu_check and options.dlc_map not in verified_maps:
        raise RuntimeError('Expected DLC map never passed native header validation; inspect route/logs')
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
    if options.audio_frames:
        import numpy as np
        import wave
        raw = b''.join(audio_blocks)
        (RUN / 'audio-guest.f32be').write_bytes(raw)
        samples = np.frombuffer(raw, dtype='>f4').reshape(-1, 6, 256).transpose(0, 2, 1).reshape(-1, 6)
        if not np.isfinite(samples).all():
            raise ValueError('Non-finite submitted audio samples')
        with wave.open(str(RUN / 'audio-guest.wav'), 'wb') as wav:
            wav.setnchannels(6)
            wav.setsampwidth(2)
            wav.setframerate(48000)
            wav.writeframes(np.rint(np.clip(samples, -1, 1) * 32767).astype('<i2').tobytes())
        (RUN / 'audio-capture.json').write_text(json.dumps({
            'frames': len(audio_blocks), 'requested_frames': options.audio_frames,
            'seconds': len(samples) / 48000, 'channels': ['FL','FR','FC','LFE','BL','BR'],
            'peak': float(np.max(np.abs(samples))) if samples.size else 0,
            'scope': 'Native guest submitted PCM before host gain/downmix; debugger timing is not a performance result.'}, indent=2))
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

if capture:
    requested = len(options.capture_times_ms.split(',')) if options.capture_times_ms else 1
    if len(list(RUN.glob('proof-loaded*.png'))) != requested:
        raise RuntimeError('Native capture incomplete before watchdog; visual validation is not established')
if options.audio_frames and len(audio_blocks) != options.audio_frames:
    raise RuntimeError('Native audio observation incomplete before watchdog')
if variant_capacity_error:
    raise RuntimeError(variant_capacity_error)
