# Frame pacing investigation

Status: active; no smoothness fix has been accepted or applied to the normal
launcher. The user reports uneven motion despite the 30 FPS counter. The only
hardware tested is their Beelink SER8. See `../../TODO.MD` for broader optimization
and the requested quality-options menu.

## Capture tools

`snapshot/tools/check_frame_pacing.py` runs the unchanged installed executable
with the existing process-local route to Cold Storage/Prisoner. It has a
165-second watchdog, uses the shared cache, and keeps logs, saves and temporary
files under the project's `.local/pacing` directory. `--stock` reads original
disc maps directly without replacing the installed conversion. `--capture`
requests one native guest-output PNG; it does not capture or drive the desktop.

`--native-timing` uses `native_frame_timing.py` to locate the existing completed
guest-frame counter. One debugger breakpoint at the exported presenter entry
discovers its instance before measurement; the instruction and instruction
pointer are restored and the debugger detaches. Measurement subsequently only
reads the counter roughly every 1ms. No engine files, guest code or game data
are modified. The known counter instruction is checked before use; unsupported
layouts fail. This is not a per-frame debugger breakpoint or screenshot loop.

Timestamps use Windows QueryPerformanceCounter through `time.perf_counter`.
This Python installation's `time.monotonic` uses 15.625ms GetTickCount64; the first
native timing trial (`20261020-172005-baseline`) is therefore invalid for detailed
timing analysis and must not be used to establish a fix.

The optional presentation measurements use the official standalone
[PresentMon 2.6.0](https://github.com/GameTechDev/PresentMon/releases/tag/v2.6.0)
console executable at `.local/tools/PresentMon-2.6.0-x64.exe`, PID-filtered to the
owned game with input tracking disabled. There is no overlay, hotkey, screen
takeover or persistent system setting. Window occlusion changes display delivery;
the native counter is needed to measure game-frame production independently.
PresentMon is a private diagnostic dependency, not part of the engine or Git.

From the conversion repository:

```powershell
python -B tools/warlock-conversion/snapshot/tools/check_frame_pacing.py --project ../.. --exe D:/Programming/GitHub/H3M/OpenH3M.exe --mode baseline --native-timing
python -B tools/warlock-conversion/snapshot/tools/summarize_frame_pacing.py ../pacing/RUN-DIRECTORY
```

The summary uses samples from 125 seconds onward; it does not verify the scene. It reports skipped
counter increments and polling gaps rather than concealing sampling uncertainty.
Native timing by itself does not prove visual correctness, simulation speed or
smooth display delivery. Inspect native output and compare equivalent routes.

## Evidence so far

- Prisoner is candidate 10, SHA256
  `c14c7d8fe5f810bdec1873e620caadd11803702d6c120bee4de053456609e460`.
- `20261020-171311-baseline`: inspected native PNG confirms Prisoner gameplay.
  Host presentations occur about 90 times/sec while new game output is about
  30/sec. Host presents alone are not a measure of unique game frames.
- `20261020-171635-no-tearing`: native gameplay image inspected; disabling
  `d3d12_allow_variable_refresh_rate_and_tearing` did not establish a pacing fix.
  Display results were affected by composed presentation/occlusion.
- `20261020-172315-baseline`: first valid high-resolution native capture.
  898 settled-gameplay intervals, zero skipped frames, mean 33.390ms,
  standard deviation 14.924ms, p05 14.305ms, p50 33.176ms, p95 51.969ms.
  Maximum observed polling gap was 25.363ms; inspect raw polling gaps when
  interpreting individual outliers. Hundreds of short/long intervals motivate
  the investigation, rather than a single slow sample.
- `20261020-172642-ui-thread`: `host_present_from_non_ui_thread=false` did
  not resolve the irregularity: 898 intervals, mean 33.314ms, standard deviation
  14.385ms, p05 14.301ms, p95 51.952ms, zero skipped frames, maximum observation
  gap 4.364ms. No production default has changed. The setting is documented in the
  [runtime presenter source](https://github.com/rexglue/rexglue-sdk/blob/main/src/ui/presenter.cpp).
- The harness also supports an `honor-timers` experiment: disable the owned
  child's `PROCESS_POWER_THROTTLING_IGNORE_TIMER_RESOLUTION` policy through
  [SetProcessInformation](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setprocessinformation).
  This honors existing timer requests even when Windows occludes the game. It
  does not request a global timer change, change game speed, or persist beyond
  the process. This experiment has not yet established a fix.

Remaining acceptance: compare native timings with stock Cold Storage, identify
a repeatable improvement without changing the engine or game simulation, inspect
the resulting native output, and document/deploy only the validated settings.


## Subsequent experiments and route failures

- Original Cold Storage run `20261020-172944-stock-baseline`: native image
  verified. 900 intervals, mean 33.332ms, standard deviation 11.317ms,
  p05 15.539ms, p95 51.644ms; no skipped frames, max polling gap 2.642ms.
  Irregularity exists with original disc assets, not just converted maps.
- `20261020-173248-honor-timers`: honoring the child's timer resolution while
  occluded did not fix pacing (mean 33.463ms, deviation 13.012ms).
- `vsync=false` changes virtual-vblank delivery and GPU waits. It is diagnostic
  only; simulation speed and scene must be checked independently.
- `20261020-173547-vblank-unthrottled` lacked a native content capture.
  Its apparent improvement is withdrawn: subsequent runs reached File Share.
- Native keystroke-only navigation was not consumed. 40ms button pulses failed
  too: `20261020-174539-9380` showed Matchmaking selected at 52 seconds and
  File Share at 135 seconds. Both native images were inspected.
- An extra A at 30 seconds failed in `20261020-174941-36136`: its native
  52-second image showed the Matchmaking lobby selector. The owned run was
  stopped, and that speculative startup press was removed.
- No no-vsync route is validated. Do not launch further full timing runs until
  its starting state and navigation are established. No production fix applied.
- Loading tracer supports project-local shared cache reuse, bounded multiple
  native captures, and candidate game-time globals at bullet impacts. Candidate
  layout matches initialized=1, rate=30, length=1/30, speed=1; tick deltas must
  validate the candidate before drawing simulation-speed conclusions.

## Recorded working route and limits

The original button-state route remains in both scripts. It reached native-
image-verified Prisoner and stock Cold Storage with default vsync. It is timed,
not state-aware, and has not been validated under changed virtual-vblank timing.

| Script time | Process-local input |
| --- | --- |
| 45s | Down (120ms pacing runner / 220ms loading tracer) |
| 46s | A (250ms) |
| 55s | Up (120ms pacing runner / 220ms loading tracer) |
| 56s | A (250ms) |
| 58-67s | Up once per second (120ms each), top of map list |
| 68s | Down (120ms), Cold Storage follows Blackout |
| 70s, 72s | A (250ms each) |
| 74s | Down (220ms) |
| 95s | A (250ms), launch match |

Required destination: Custom Games, Cold Storage (Prisoner replacement).
Matchmaking, File Share, and other map slots invalidate the test. Input logs
alone do not establish menu state. Verify native content before gameplay
measurement and stop an owned run when the route is wrong. No desktop input.


### Short route probes (2026-10-20)

`probe_native_route.py` confines each short native run and captures to `.local`,
reuses the shared cache, checks the executable hash, refuses concurrent games,
and kills its owned child at its watchdog. It uses only the existing native
input script and guest-output capture. No timing claims come from this tool.

- `20261020-175245-route-probe`: connect the synthetic controller at startup
  with a 1ms right-stick pulse, then original Down/A at 45/46 seconds. Native
  captures at 40 and 52 seconds both remained on main-menu Matchmaking.
- `20261020-175411-route-probe`: native captures showed the Bungie intro at
  18 and 22 seconds, then main menu at 26 seconds. Inputs during intro cannot
  be treated as menu navigation.
- `20261020-175456-route-probe`: Down held for one second at 35 seconds left
  Matchmaking selected (37-second capture); A at 38 seconds entered its lobby
  (42-second capture).
- `20261020-175554-route-probe`: analog left-stick Down at 30 seconds also
  left Matchmaking selected (32-second capture); A at 34 seconds entered its
  lobby (38-second capture).

All above probes used vsync=false. These captures disqualify that setting as
an accepted fix: navigation behavior has not been preserved. Startup controller
connection and shorter/longer digital pulses did not correct it. Stop guessing
full routes under this option. Current focus is settings retaining normal vblank.

Explicit SDL_TIMER_RESOLUTION=1 had not actually been measured previously;
assuming its default was active is insufficient. A bounded normal-vblank trial
now tests this separately from the earlier honor-existing-timer policy trial.
New pacing captures include both the early lobby and final scene so a route
failure can be detected before measurement completes.


### Explicit timer-resolution result

`20261020-175715-sdl-timer` reached the Custom Games lobby at 52 seconds and
Prisoner gameplay at 145 seconds; both native images were inspected. The normal
recorded route was unchanged. SDL_TIMER_RESOLUTION=1 did not fix pacing:
899 intervals, no skips, mean 33.312ms, deviation 14.778ms, p05 15.114ms,
p95 51.701ms, p99 52.540ms. There were 320 intervals below 25ms and 319 above
41.667ms. Maximum polling gap was only 1.910ms, substantially below the observed
variation. A read-only NtQueryTimerResolution during the run reported 1ms current
system resolution; that query alone does not prove per-process timer behavior.

No settings have been adopted for production. No engine or disc assets changed.
Remaining work: locate the source of short/long frame delivery under normal
vblank and validate a compatible fix; current tools measure output production,
not simulation or physical-display smoothness by themselves.


### GPU progress discovery (2026-10-20)

`20261020-180209-baseline`: native captures verified Custom Games lobby and
Prisoner gameplay. Guest output remained uneven: 899 intervals, mean 33.334ms,
standard deviation 14.626ms, p05 14.727ms, p95 51.962ms, zero missed increments.

The second discovery breakpoint observed the installed GPU worker at RVA
0x1552b (`inc dword ptr [rax+0x78]`). It was restored before measurement. The
counter advanced roughly 90 times/second, not 60. Inspection established it is
shared GPU progress: the swap path also increments it (installed RVA 0x1a7f3).
The upstream [command processor implementation](https://github.com/rexglue/rexglue-sdk/blob/main/src/graphics/command_processor.cpp)
likewise increments counter_ after IssueSwap and writes it for EVENT_WRITE_SHD.
This is NOT evidence of a 90Hz virtual display or an irregular vblank timer.

The raw discovery file retains its original `vblank.csv` name for provenance;
its regenerated summary explicitly labels the combined metric. New captures use
`--gpu-progress-timing` and `gpu-progress.csv`. The tool checks the GPU DLL hash
and instruction signature before discovery and polls read-only during timing.
No pure-vblank or simulation-tick conclusion is justified by this counter.

Next diagnosis must separate the virtual clock from the swap increments or
validate an existing compatible video-mode setting. Do not adopt no-vsync or
change engine code based on this mixed counter.


### Fractional refresh and offline clock estimate

`20261020-180652-ntsc-refresh` used the existing
`--video_mode_refresh_rate=59.94` setting with vsync enabled. Native captures
verified Custom Games and Prisoner. This did not fix pacing: 898 intervals,
mean 33.385ms, deviation 14.727ms, p05 14.205ms, p95 51.987ms; zero missed
increments, maximum polling gap 1.942ms. Production refresh is unchanged.

An exploratory offline subtraction on `20261020-180209-baseline` matched all
900 output events to a GPU-progress increment within 3ms. Subtracting those
left 1799 residual events, mean spacing 16.6668ms, deviation 0.8517ms,
p05 15.262ms and p95 18.186ms. Saved as `exploratory-residual.json` in that run.
This suggests the virtual clock itself is substantially steadier than output,
but matching/subtraction is not a direct vblank trace and cannot prove causality.

The installed guest interrupt wrapper at executable RVA 0x44d4510 has its own
atomic counter (RVA 0x4611c40), but logs show it combines source=0 and source=1
interrupts. It therefore cannot replace the mixed GPU counter as a pure-vblank
measurement. The wrapper calls the original translated callback at RVA
0x1f2c330. Any further callback investigation must distinguish interrupt sources.
No engine source, binaries, guest memory values, or map assets were altered.


### Direct guest vblank measurement

Read-only disassembly distinguishes the source-0 interrupt branch (original
callback at executable RVA 0x1f2c330) from source-1 GPU events. Source 0 calls
the handler at RVA 0x1c7c0e0; it increments the big-endian device counter at
+0x4094. `--guest-vblank-timing` discovers the device and guest-memory base with
one restored handler breakpoint before the measurement window, then polls only
memory. Executable hash and handler signature are checked before use.

`20261020-181153-baseline`: native lobby and Prisoner gameplay images inspected.
Guest vblank: 1799 single increments, mean 16.667ms, deviation 0.951ms,
p05 15.477ms, p95 17.753ms, no non-single increments, max polling gap 2.373ms.
In the same window frame output: mean 33.312ms, deviation 15.741ms,
p05 14.203ms, p95 52.020ms, no missed increments. This directly places the
large variation after guest vblank delivery rather than in that clock itself.
It does not yet identify which downstream component causes the variation.

The installed application's default anisotropic_override=3 forces 4x filtering
(per the installed flag description). A diagnostic filtering-off trial tests
GPU workload by setting it to 0; it is not a production change or a claim about
what every original game texture requests. Existing PresentMon GPU-busy data
motivates this test, but repeated host presents limit per-game-frame attribution.


`20261020-181501-filtering-off` reached verified Prisoner gameplay but did not
fix pacing: mean 33.315ms, deviation 14.838ms, p05 15.141ms, p95 51.799ms,
zero skipped output increments, maximum polling gap 1.954ms. PresentMon GPU-busy
sum over the 30-second window was 19918ms versus 19581ms for the adjacent direct-
vblank baseline; p95 was 22.42ms versus 22.90ms. This did not materially reduce
measured GPU work, so it neither fixes pacing nor conclusively rules out GPU
workload as a contributor. Default filtering remains unchanged. Further timer
or filtering guesses are not supported by these results; investigate downstream
frame scheduling/synchronization using the direct vblank measurement as control.


### Guest frame-queue progress and authorization boundary

The same source-0 handler advances its queue index at device+0x40a8 (native
increment/store at executable RVAs 0x1c7c4fc and 0x1c7c531). The read-only sampler
now records this adjacent field as guest-flip.csv, without another breakpoint.
The name describes guest queue progress, NOT physical display flips.

`20261020-181907-baseline`: both native images verified the correct lobby and
Prisoner gameplay. Queue progress: 898 intervals, mean 33.316ms, deviation
12.797ms, p05 17.058ms, p95 49.559ms, no missed queue increments. Guest vblank
in the same run: mean 16.665ms, deviation 0.769ms; one observation skipped an
increment (maximum polling gap 8.324ms). Output still varied roughly 15/52ms.
Thus substantial irregularity exists in guest frame scheduling/queue progress
before physical-display presentation. This does not yet identify a single
faulty instruction or prove a particular runtime patch will fix it.

Inspected upstream host VdSwap substitutes an emulated swap packet for the
console command sequence; it is a relevant investigation point, not by itself
proof of a bug. The runtime exposes both GPU backend implementations internally,
but the inspected app invokes LoadGpuPlugin with the default backend; no usable
backend-selection configuration was established. No backend switch was attempted.

Tested settings have not supplied a validated fix. A user decision has been
requested before investigating/implementing a host-runtime correction, because
AGENTS.md and the active goal explicitly prohibit modifying OpenH3M. Original
360 gameplay, assets and future system-link compatibility must remain preserved.
This is the first turn awaiting that scope decision; goal remains active and
incomplete. No engine changes are authorized by this note or by the request.

### User authorization clarified (2026-10-20)

The user clarified that the preceding refusal was a misunderstanding and explicitly authorized engine patches, provided the core stays Xbox 360-compatible. Host-runtime frame pacing work is now within scope. Preserve original gameplay, simulation rate, map formats, stock asset behavior, and system-link semantics; do not alter the core to hide presentation timing problems. No smoothness fix or cross-console compatibility validation is claimed by this authorization.


### Presentation queue deadlines (2026-10-20)

Run `20261020-195153-baseline` used the unchanged installed executable and shared
cache. Native 52-second capture verified Custom Games; native 145-second capture
verified Prisoner gameplay. Watchdog ended the owned process normally for this
harness; no host input or desktop capture was used.

The sampler now reads a single bounded 160-byte device snapshot from +0x4094
through +0x4130. Read-only disassembly establishes a 16-entry presentation ring
at +0x40ac (buffer, target-vblank pairs), consumer +0x412c, producer +0x4130.
Original translated handler `0x825bf658` (installed native RVA 0x1c7c0e0)
compares the head entry target to the current vblank, increments completed
+0x40a8, advances the consumer and may loop through further eligible entries.
The producer is original function `0x825bf758` (native RVA 0x2d28d40).
It also has a direct completion branch, bypassing ring insertion when the
computed target equals current vblank (branch at native RVA 0x2d29724).
These are observations of original code, not proposed guest-code patches.

Settled window: output mean 33.333ms, deviation 15.046ms, p05 14.286ms,
p95 52.046ms, zero skipped output observations. Vblank mean 16.667ms,
deviation 0.902ms, zero skipped increments. Completion observations: 318
one-vblank intervals, 263 two-vblank intervals, 318 three-vblank intervals.
The ring retained 593 distinct entries with no conflicting sampled targets;
target spacing was predominantly 2 or 4 vblanks. This is NOT the complete
presentation-request cadence: direct completions bypass the ring. Therefore a
patch that only smooths ring consumption is not yet justified. The sampler
also records last requested target (+0x409c) and issued count (+0x40a4) for the
next targeted run; those two columns were added after this run and are not
claimed as measured here. Snapshots are not atomic across guest threads.

Next investigation: trace the producer's target calculation and its presentation
callback, correlate direct vs queued requests with host VdSwap handling, then
patch the host boundary while retaining the guest's interval and simulation.
No host fix has been deployed or validated. Do not substitute a steady title-bar
FPS or a generic sleep for smooth-motion validation.

Build preparation: materialized the existing tracked halo3mp sources in the
same sparse checkout, and fetched SDK source into ignored work/rexglue-sdk,
commit c94f5ebdcb3c9d1a460ca48e04f9758448f8d518, for inspection. This is upstream
reference, NOT asserted to match the installed runtime. No submodule download,
SDK build, generated guest-code copy, or second game installation was created.

### Request interval and host-only prototype (2026-10-20)

`20261020-195749-baseline` was aborted by the diagnostic address guard before
measurement: the writeback buffer uses a high physical-memory alias. Fixed the
sampler to apply the same extra 4 KiB address offset used by the installed
translated PPC memory-access code for addresses >= 0xe0000000. This failed run
supplies no performance evidence.

`20261020-195954-baseline` completed; the native 145-second image was inspected
and shows Prisoner gameplay. Output mean 33.313ms, deviation 15.578ms; vblank
mean 16.666ms, deviation 0.829ms. All 2141 settled writeback samples retained
argument 0x10a: interval bits 8..11 = 1, cutoff low byte = 10 percent. These are
samples, not an exhaustive interrupt history. Present callback device+0x408c
was zero; the vblank callback +0x4090 was 2185621112. Consecutive observed
request target spacings: 345 at one vblank, 210 at two, 344 at three. Thus the
requested interval field is stable while computed deadlines are irregular.

Read-only decoding of original default.xex confirms D3D function 0x825bf758
computes max(previous_target + interval, current_vblank), advancing by one
vblank when late in the current refresh according to the cutoff. It then
performs the direct/queued completion behavior described above. Original code
and assets remain unchanged. This does not prove a defect in that original
algorithm, or authorize replacing its simulation logic.

A 4608-byte native host presentation probe now builds from
snapshot/tools/host_pacing_probe.cpp using build_host_pacing_probe.ps1, with all
outputs and compiler temporary files in ignored work/pacing-probe. It attempts
30 Hz host output pacing only after 110 seconds, keeping the menu route and
all guest code intact. It is an experiment, not a validated fix or shipping
hook. It has NOT been loaded into a game yet, and does not establish smoothness,
performance, input latency, simulation speed or system-link compatibility.
The launcher integration must hash-check the runtime and install only in an
owned process with the primary thread suspended before game threads start;
never patch a live user session or install across executing prologue bytes.
Next: implement safe owned-child loading (or equivalent stopped-thread setup),
measure this candidate against the saved baseline, reject it if it reduces
sustained throughput or merely redistributes stalls, then convert any proven
behavior into an ordinary runtime source patch. Do not ship the diagnostic hook.

### First successful host pacing experiment (2026-10-20)

`20261020-200751-host-probe-baseline` completed in the owned process. The native
145-second image was inspected: Prisoner gameplay, ground-floor interior,
active camouflage and weapon/HUD visible. The fixed route reached the map;
no desktop input/capture was used. This static image verifies scene content,
not motion quality or simulation speed by itself.

The launcher loads the diagnostic DLL while the owned child runs, but its
PrepareProbe only allocates its trampoline/state. The normal discovery debugger
then stops all threads at the single producer's RefreshGuestOutput entry and
arms the 15-byte detour there, rewinding that thread to the entry. This replaces
the earlier planned suspended-start loading method. Module addresses account
for ASLR and forwarded LoadLibraryW; signatures are checked. Only the owned
child's memory is changed. Its executable and installed DLL files are unchanged.

Probe DLL SHA256 ab55b375f3a49542a44895352b7653afa6faffa5bf41a123499e3a69b7d1c4e5.
Armed at 15.219 seconds; pacing activates about 95 seconds after preparation.
1349 paced calls, zero late schedule resets. The settled 899 intervals averaged
33.334ms (30 FPS), deviation 2.645ms, p05 30.103ms, p95 36.462ms, p99 37.199ms;
4 intervals below 25ms and 4 above 41.667ms, no skipped output observations.
Adjacent baseline had deviation 15.578ms, p05 14.206ms, p95 52.078ms and
345 short/344 long intervals. Vblank remained 16.666ms with deviation 0.868ms.
Guest queue completion still varied (deviation 12.796ms), consistent with the
probe pacing host output rather than changing guest deadlines. Simulation rate,
physical display cadence, input latency and system-link are not established by
these counters. Keep those limitations explicit; goal is not complete.

The probe's 1,418,079 wait calls expose excessive short Sleep(0) polling.
The production candidate instead uses blocking std::this_thread::sleep_until.
`halo3mp/patches/rexglue-sdk-host-frame-pacing.patch` layers after the existing
presenter-host-tools patch. It adds host_guest_output_fps (OpenH3M-specific
30 FPS default, 0 disables), serial-producer thread-local state (no extra SDK
class-layout change), blank-output/reset handling and no catch-up bursts after
real stalls. This source candidate has NOT yet been built or tested in-game.
It is not identical to the probe; the final runtime needs its own measurement.

SDK v0.10.0 source c94f5ebdcb3c9d1a460ca48e04f9758448f8d518 now has all six
existing halo3mp SDK patches applied with --ignore-space-change (Windows CRLF
otherwise prevents matching), followed by the host pacing patch. Only required
D3D12 runtime submodules were fetched shallowly; no Vulkan/test/profiling trees.
A Release CMake configuration is in progress in work/rexglue-sdk/out/pacing-release
(tool session 68054 at this checkpoint). Compiler TEMP/TMP is work/build-temp;
Ninja and clang are installed system tools. Configure flags: Ninja, Release,
clang/clang++, REXGLUE_ENABLE_TRACY=OFF, REXGLUE_BUILD_TESTS=OFF,
REXGLUE_USE_VULKAN=OFF, CMAKE_EXPORT_NO_PACKAGE_REGISTRY=ON. Revalidate that live
session before taking further action. Build target rexruntime first; preserve
existing game EXE, maps, GPU plugin and shared cache unless evidence requires
additional ABI-matched components. No production binaries have been replaced.
