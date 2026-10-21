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

### Source runtime built; traversal-stall investigation remains open (2026-10-20)

This supersedes the build-pending checkpoint above. The runtime was built from
SDK c94f5ebdcb3c9d1a460ca48e04f9758448f8d518 with the existing six patches,
plus local-user-direct, windows-mspack-path and host-frame-pacing. Reproduction:
run snapshot/tools/build_host_runtime.ps1 from this repository. Required shallow
SDK submodules are cli11, libmspack, FFmpeg, tomlplusplus, simde, xxHash, spdlog,
fmt, utfcpp, imgui, sdl3, o1heap, vulkan-headers, vulkan-memory-allocator,
spirv-headers, spirv-tools and glslang. All source/build/temp data stays in work/.
Use the existing SDK checkout, not a second build per map.

The build uses installed clang/clang++, Ninja, Release and -march=x86-64-v2,
with Tracy/tests disabled. Vulkan must be enabled alongside D3D12 because the
unchanged GPU plugin imports Vulkan exports even when D3D12 is selected.
The Windows mspack patch resolves a checked-out text symlink to its real source
folder. The local-user-direct patch restores the signin export required by the
existing executable, using the same local-user activation/state functions.
The final host patch also exports a read-only frame-counter accessor, avoiding
an assumed opcode offset for diagnostics. No guest code, maps or simulation
clock changes were made.

Output: work/rexglue-sdk/out/win-amd64/rexruntime.dll; candidate staging:
work/pacing-runtime (binaries only, shared maps/cache). Runtime SHA256:
260b9b5a478e4e639323eca9025544c8b29c6769f6d8b433a28d134a63005806.
The unchanged EXE/GPU plugin and guest DLLs are used. audit_runtime_imports.py
checked all 10,886 exports with zero missing named imports. pefile's default
8,192-export limit initially produced false missing-import reports; the checker
now explicitly raises that limit and checks completeness. Export compatibility
alone does not verify C++ layout or gameplay, so native gameplay checks follow.

Prisoner run 20261020-202533-baseline, without the diagnostic DLL hook:
899 settled intervals, mean 33.333ms, standard deviation 0.801ms, p05 31.939ms,
p95 34.751ms, p99 35.118ms, no intervals below 25ms or above 41.667ms, no skipped
observations. Guest vblank remained 16.667ms, deviation 0.861ms. Native gameplay
capture at 145 seconds was inspected and shows Prisoner geometry, weapon and HUD.
The adjacent old-runtime baseline's deviation was 15.578ms. This establishes a
large improvement in sampled output cadence, not physical-display verification.

Stock Cold Storage run 20261020-202841-stock-baseline reached the correct original
map (145-second native image inspected). The human walked around and reported
hiccups. Settled output: 863 intervals, mean 34.706ms, deviation 20.634ms,
p05 32.015ms, p95 34.693ms; 7 intervals above 41.667ms. Across the full capture,
there were 10 intervals above 60ms, including 555ms and 662ms at ~122 seconds,
which the settled-window summary alone would omit. The summary tool now records
all >60ms intervals and counter deltas over the complete capture.

During the largest stalls, the guest vblank counter continued steadily and the
sampled guest flip queue was empty (head==tail; issued==completed). Thus the
remaining delay is not simply the original alternating output cadence. This
observation does not distinguish CPU work, GPU preparation, IO or synchronization.
Do not declare the SER8 inadequate or the goal complete from this run.

The initial stock launch restored 456 shaders/507 pipelines; the following
launch restored 493/560. Source confirms persistent pipeline descriptions are
translated and compiled at startup. This supports investigating first-use work,
not claiming it caused every stall. The warm-cache repeat is
20261020-203316-stock-baseline (tool session 73105); verify terminal state and
capture/results before relying on it. Production deployment remains pending.
System-link, other hardware, audio fidelity and physical display cadence have
not been validated by these timing/capture checks.

Warm-repeat result: session 73105 completed normally under its watchdog.
20261020-203316-stock-baseline reached original Cold Storage; the 145-second
native capture was inspected (blue-lit interior, weapon/HUD, active camouflage).
899 settled intervals averaged 33.334ms, deviation 0.913ms, p05 31.620ms,
p95 34.732ms, p99 35.427ms; zero short/long outliers and zero skipped observations.
The entire 110-155-second capture contained no interval above 60ms. Vblank
remained 16.667ms. Startup restored 493 shaders and 560 pipelines.

This is consistent with cached first-use preparation helping, but not a causal
proof: the previous run included the user's movement and ended in another room,
whereas this repeat used the saved scripted route. Do not claim identical scene
coverage or all-map first-visit smoothness. Keep the goal active; remaining work
is targeted first-use stall diagnosis/preparation and production deployment.
The shared cache must be retained, not discarded as disposable diagnostic data.

Validation this checkpoint: Python AST parsing for all changed diagnostic tools,
PowerShell parser for the runtime build helper, complete export audit and git
whitespace check. No additional game build or map duplication was introduced.

### Targeted first-use diagnostics (2026-10-20)

Added rexglue-sdk-preparation-timing.patch and the optional -GpuDiagnostics flag
on build_host_runtime.ps1. This builds rexgpu-xenos in the same SDK build tree,
with no duplicate map installation. d3d12_slow_preparation_ms defaults to zero
(disabled); a positive value logs shader translation and pipeline preparation
only when a call exceeds that many milliseconds. It records elapsed time and
shader identity, without replacing draws, mutating guest code or changing clocks.

The rebuilt diagnostic pair is staged in work/pacing-runtime; it supersedes
that folder's previous candidate but has NOT been deployed to the normal launcher.
Runtime SHA256 7cd6bbf005f3a34445b69316d6c2299949e0c1cae267c4e3a505713c19bfe01a;
GPU SHA256 0101324fa02937421b38af0cd8f34467c876d9e20bae279ad3fbcbbdca0cd360.
Export audit passed with 10,886 runtime exports and zero missing imports.
The runtime relink included the generated build-version change; source pacing
behavior remains unchanged. Existing original GPU remains available at the
previous external installation (read-only here), hash aed76f757f9c570923e90ec99d26305f368857e972ea9d97b650af1ce806bc94.

check_frame_pacing.py now accepts a confined --cache-root and
--slow-preparation-ms, records GPU hash and launch wall time for log correlation.
summarize_preparation.py reports overlap between >60ms output gaps and the
logged preparation intervals. Overlap alone is not causation: compilation can
occur on worker threads. No-overlap also cannot rule out queued waits or work
below the logging threshold. The new trace's process-start.json uses Windows
creation time because that trace began before the launch-time field was added.

Cold application-cache run 20261020-203853-stock-baseline uses the unchanged
scripted route, a separate .local/pacing/preparation-cache, and a 5ms threshold.
This is NOT a cold driver-cache experiment: persistent driver caches were not
cleared or modified. Native 52-second image confirms Custom Games lobby before
the recorded Cold Storage selection. Verify terminal session 20474 and the
145-second gameplay capture before interpreting the result. Keep the shared
custom-maps-play/cache unchanged throughout this comparison.

Cold-cache diagnostic run completed under its watchdog. Native 145-second image
was inspected: correct blue-lit Cold Storage interior, weapon/HUD and camouflage,
matching the scripted warm-route endpoint. 899 settled intervals: mean 33.333ms,
standard deviation 1.100ms, p05 31.646ms, p95 34.787ms, p99 35.025ms; one interval
below 25ms and one above 41.667ms, no skips. No >60ms gaps in the full capture.
82 preparation events exceeded 5ms; the longest was a 21.514ms pipeline call at
103.207 seconds, and seven logged events ended after 110 seconds. No frame-gap
correlation can be established because this route did not reproduce the large
stalls. This result weakens a blanket 'uncached shaders caused the hiccups'
explanation, but cannot rule out unvisited effects/pipelines or driver caching.

Do not spend another identical warm run: its absence of >60ms stalls cannot
locate the manual walk's earlier half-second pauses. Next work should expand the
process-local traversal/effects coverage or add diagnostics at the actual stall,
then deploy the proven pacing change. The diagnostic GPU plugin is not yet a
production replacement. Shared maps/cache and normal launcher remain unchanged.

### Portable shared installation candidate (2026-10-20)

Added rexglue-sdk-portable-bootstrap.patch. cvar::Init optionally reads an
adjacent <executable>.bootstrap.toml after CLI parsing but before consumers
resolve game/user/cache paths. Command-line values retain precedence. Without
that opt-in file behavior is unchanged. This fixes the existing ordering where
ReXApp resolves its paths before loading its normal TOML. It is host startup
configuration only; original game executable and guest modules are unchanged.

snapshot/tools/deploy_host_runtime.py installs only seven host/translated-module
binaries at the project root and writes OpenH3M.bootstrap.toml, referencing the
existing .local/custom-maps-play game/cache/user folders. It rejects unmanaged
binary/config replacements and any running OpenH3M process. Legacy CMD wrappers
are redirected to the root EXE. The intended user entry is now OpenH3M.exe itself;
no separate map builds, map copying or outside-repository deployment is required.
Deployment records live in .local/runtime-deployment.json. Source staging remains
work/pacing-runtime until verification finishes, then it can be removed.

Candidate runtime SHA256 55cf5019c50e10cf710311f09c4136953d8476813f0a01e47142d84d76c43e66;
GPU SHA256 86e51b5811ee38bfbf7a7b4d5f75367ec62abfc209800e2d1d7a724127163048.
The GPU includes the opt-in preparation logger (off for normal launches).
Import audit passed. The normal OpenH3M.exe hash remains ec4d57ee4f654095bd5e512ffe650d65ac514b0fb8f21d5c7b09e61e689c3406.

check_frame_pacing.py --portable-paths validates and uses the bootstrap settings
without --game_data_root/--user_data_root/--cache_root overrides. Its new
--effects-route adds in-process movement, firing and grenades at 127-150 seconds,
using the existing bounded test harness. No host desktop input is generated.
Run 20261020-204512-baseline (session 7607) is testing the root EXE with Prisoner,
the shared cache, bootstrap paths and preparation logging. Inspect its native
capture and counters before claiming successful deployment. The user feedback
about longer Cold Storage traversal hiccups remains unresolved.

Portable/effects validation FAILED: 20261020-204512-baseline exited around
138 seconds with `[FATAL] Call to invalid or unregistered function at guest
address 0x8263D8F8` on the game thread. The sampler then reported WinError 299
because its process memory disappeared. This is not a successful timing run.
There is no 145-second gameplay capture. The 52-second native image was inspected
and showed the expected Custom Games lobby; logs reached chillout map loading,
but that is insufficient to verify the expected rendered gameplay content.
The late log also contains physical-controller analog values, so do not assume
the entire path was isolated from incidental controller state.

The newly installed seven binaries and managed bootstrap TOML were removed
only after their hashes matched this turn's deployment manifest. Previous
launchers still point to the prior D: installation; original disc files/maps
were not altered. .local/runtime-deployment.json records withdrawal and reason.
This removes the redundant ~binary-set copy and prevents presenting the failed
candidate as a working direct-launch install. work/pacing-runtime retains the
candidate for diagnosis. The deployment helper and bootstrap patch are saved
but NOT validated for normal use.

Next: determine whether 0x8263D8F8 is missing translated registration/code or
whether a bad target is being called, including comparison against the original
runtime on the same effects route. Do not stub out the original game function
or skip gameplay as a workaround. The helper now records any harness error and
the child's exit status before cleanup, so subsequent exits are attributable.
Goal remains active; smoothness improvement alone is not a successful deployment.

### Missing original virtual-call wrapper (2026-10-20)

Read the original default.xex in memory through snapshot/tools/xexlib.py; no disc
file was changed and no full extracted image was saved. Xex.image() is a mapped
image: use guest_address-image_base, NOT PE raw-file section offsets. The complete
body at 0x8263D8F8 is nine instructions:

    lwz r3,4(r3)
    mr r4,r5
    mr r5,r6
    mr r6,r7
    mr r7,r9
    lwz r11,0(r3)
    lwz r11,0x1c(r11)
    mtctr r11
    bctr

The existing BUILD.md already records a similar missed wrapper at 0x8263D938.
The manifest now explicitly declares 0x8263D8F8 for future full code generation.
rexglue-sdk-halo3-virtual-adapter.patch supplies the exact wrapper for the current
unchanged EXE only when indirect resolution fails AND all nine original opcode
words match in guest memory. Existing registrations win. It performs the original
big-endian 32-bit loads and register moves, preserves CR/LR, updates CTR and
branches to the original target via the dispatcher. It never substitutes a dummy
return or changes game rules. The guarded byte sequence was checked against all
36 original XEX bytes. This is a compatibility repair, not a pacing shortcut.

Build helper applies this patch after portable-bootstrap. The host runtime/GPU
pair rebuilt successfully in the same incremental tree. Integrated verification
is still required before deployment. Original-runtime comparison is
20261020-205213-baseline, tool session 87017: original EXE/runtime from the existing
D: installation, project-local game/log/cache paths, and the extended effects
route. Verify the terminal result rather than inferring completion from this note.

Original-runtime comparison 20261020-205213-baseline completed under its watchdog
without this crash. Native 145-second image was inspected: Prisoner ground-floor
interior, weapon/HUD and an actual grenade-throw animation. It retained uneven
cadence: 899 settled intervals, mean 33.335ms, deviation 14.718ms, p05 14.257ms,
p95 51.922ms, 314 short/313 long intervals; one 67.466ms gap in the full capture.
This run did not prove the original runtime reaches the missing-wrapper path.
Do not claim the crash was reproduced in it. The installed EXE contains the
nearby known 8263D938 mapping address but no literal 8263D8F8 address; that binary
scan is supporting evidence, not a complete code-generation audit.

Current staged repaired-runtime SHA256:
4e9b1c46b4795b5e42fcadd2265554c98e00f4a79baf453a90617dd845eda3d4.
Complete import audit passed. Repair verification run is
20261020-205514-baseline, session 83945: same process-local effects script,
shared maps/cache, ordinary ephemeral test profile, threshold logging and native
captures. No production installation was replaced. Check native capture, fatal
logs, timing and whether the byte-verified registration message occurred before
claiming the missing-wrapper path has been exercised successfully.

Repaired candidate run 20261020-205514-baseline completed under its watchdog.
The 145-second native image was inspected: correct Prisoner interior, weapon/HUD,
bullet impacts and a thrown grenade, closely matching the original-runtime route.
899 settled intervals averaged 33.334ms, deviation 1.024ms, p05 31.650ms,
p95 34.681ms, p99 35.953ms; zero intervals above 41.667ms, zero >60ms full-capture
gaps, no skipped frames. Guest vblank remained 16.666ms. No fatal log entry.
There was NO byte-verified registration message, so this run did not exercise
the missing-wrapper repair. Static opcode/semantic verification is not a claim
of in-game crash-path reproduction. Preparation logging recorded 134 events;
no output hitch existed to correlate.

The repaired candidate is now staged again at the project root with the shared
bootstrap paths, 5MB log rotation and three retained log files. GPU SHA256:
bf2a7b68df8035b8bba59774e4323fdf26081ea15d3ac89ef87fd0365e9f1c40.
Legacy root CMD wrappers now reference the root EXE; unlike the earlier failed
deployment, a rollback would need to restore those wrapper EXE references too.
Direct-launch/shared-profile validation is 20261020-205857-baseline, session
87191, using --portable-paths --effects-route. Do not treat staging as success;
inspect its terminal state, native image, counter report and fatal/registration
logs. The normal entry is intended to be C:\X360\ISOs\H3M\OpenH3M.exe only after
this validation. Original disc assets remain unchanged.

Direct-launch verification 20261020-205857-baseline completed under its watchdog.
The native 145-second image was inspected: correct Prisoner interior, weapon/HUD,
impacts and grenade-throw animation. It used the root EXE with NO game/user/cache
CLI overrides, confirming the bootstrap found the shared installation/profile.
899 settled intervals: mean 33.333ms, deviation 0.806ms, p05 31.940ms,
p95 34.708ms, p99 34.948ms, zero short/long outliers, zero >60ms full-capture gaps
and no skipped frames. Guest vblank remained 16.667ms. No fatal entry and no
missing-wrapper registration message; that exact rare crash path remains
unexercised despite the successful route. Normal root EXE deployment is now
validated for this bounded flow. No system-link or physical-display claim.

Attempted cleanup of duplicate work/pacing-runtime binaries was rejected by
automatic approval review ('blocked by policy') before execution. No cleanup
commands ran and no files were removed. Do not retry by another mechanism.
The staging directory remains alongside the deployed root binaries; the shared
maps/cache are still single copies. .local/runtime-deployment.json records the
successful route and this cleanup blocker. Intermittent manual Cold Storage
hitching and runtime exercise of the repaired wrapper are still outstanding;
the goal remains active. Source and process changes are committed locally only.
