# Halo 3 Multiplayer — ReXGlue static recompilation

Native x64 recompilation of the retail Halo 3: ODST Disc 2 (Multiplayer) XEX
using the [ReXGlue SDK](https://github.com/rexglue/rexglue-sdk).

## Status

2026-08-16 update: the Release build reaches the Halo 3 Mythic menus with the
3D menu background visible and can enter first-person Custom Games gameplay on
Last Resort/Zanzibar in a window. The repeatable Custom Games proof path uses a
recorded keyboard-controller route replayed as `input_script`, including the
pause before the final `A` press while the map/cache state settles. The
split-screen stress route is now a direct, screenshot-gated Custom Games path:
no menu clamping, no foreground keyboard input, and no foreground/window
capture. A clean manual route also reaches Forge gameplay on Zanzibar, and D-pad
Up toggles Forge build/monitor mode. Use the offline multiplayer surfaces for
testing; Xbox LIVE is intentionally out of scope, while split screen, system
link, Custom Games, Forge, and Theater are in scope.

Known current issues:

- The D3D12 host render-target path is the performance default. Halo 3 MP uses
  `render_target_path_d3d12=rtv` with `gamma_render_target_as_unorm16=false`;
  the newer 16-bit gamma host representation washes the 3D output to white.
  Accurate ROV remains available as a command-line override but is much slower
  on integrated GPUs.
- Generic memexport CPU readback is disabled for Halo 3 MP. The GPU writes are
  preserved, while avoiding synchronous GPU/CPU readback stalls. It can be
  restored for diagnostics with `--readback_memexport=true`.
- GPU logs still report memexport shader translation failures:
  `ShaderTranslator::GatherAluInstructionInformation: Couldn't extract memexport stream constant index`.
  These no longer block the menu background or the Zanzibar gameplay path.
- The prior Zanzibar-load fatal at guest `0x8263D938` is fixed by declaring that
  virtual-call thunk in `halo3mp_manifest.toml`.
- Four-player split-screen is the current validation target. The helper can now
  expose scripted synthetic input for users 0-3, including sticks and triggers,
  so it can stress movement and firing without requiring four physical
  controllers. `-SplitScreenStress` is the long-run stress target for real 2x2
  split-screen gameplay on Last Resort/Zanzibar.
- The original four-player cliff was caused by local-user/sign-in query churn,
  not viewport creation or scripted input. `halo3mp_132.log` measured 843856
  XamUser calls, dominated by 836596 sign-in-state queries, after user mask
  `0xf`; the local-user fast path removes that churn. Current valid four-player
  runs are GPU/backend limited near 29 FPS on a Radeon 780M rather than the old
  3-10 FPS range.
- Treat Theater Lobby runs as invalid for Custom Games/FPS proof. Validate smoke
  logs with `tools/analyze_smoke_log.ps1`, which requires a gameplay map load
  plus an autosave temp before FPS samples are accepted and now reports XamUser
  call summaries by FPS phase. Theater is in scope, but it is not a useful proof
  target until games can be recorded.

Windowed automated input helper:

```bash
.\run_windowed.ps1 -SmokeTest
```

`-SmokeTest` replays the recorded Custom Games/Zanzibar route and logs
host-measured guest-output FPS. By default it does not write captures. Add
`-Capture` only when a visual checkpoint is needed; the one-shot image is a PNG
written from the Rexglue presenter output, not from the foreground desktop or
window.

```bash
powershell -ExecutionPolicy Bypass -File .\tools\analyze_smoke_log.ps1
```

The analyzer reads the newest log by default and fails the run if it cannot
prove that the route reached gameplay. In particular, menu-only or Theater
Lobby runs must not be used as gameplay FPS evidence.

```bash
.\run_windowed.ps1 -OnePlayerStress
```

`-OnePlayerStress` starts the default Custom Games match on Last
Resort/Zanzibar, then drives user 0 with left-stick, right-stick, and
right-trigger input. It is log-only by default; add `-Capture` to write
`out/build/win-amd64-release/halo3mp_smoke_oneplayer_stress.png`.

```bash
.\run_windowed.ps1 -SplitScreenStress
```

`-SplitScreenStress` enables four offline local users with
`--xam_local_user_count=4`, enters the Custom Games lobby from the main menu,
starts the default Slayer match on Last Resort/Zanzibar, pulses virtual `START`
on users 1-3 after gameplay has loaded so they can join in progress, then drives
all four users with left-stick, right-stick, and right-trigger input. It is
log-only by default and emits one-second XamUser summaries for bottleneck
analysis.
Automated launches run the game at Below Normal CPU priority so long smoke tests
remain background-friendly while the desktop is in use.
Add `-Capture` to write
`out/build/win-amd64-release/halo3mp_smoke_splitscreen_stress.png` from the
internal guest-output presenter. Use `-ExtraArgs` to append cvars for A/B
profiling runs, for example:

```bash
.\run_windowed.ps1 -SplitScreenStress -ExtraArgs '--occlusion_query_enable=false'
```

The detailed Halo job-system fiber trace is opt-in via
`--halo3mp_fiber_trace=true`. It is intentionally disabled by default because
the prior trace emitted over 11k `[fiber]` lines during one four-player capture
run and held the route at roughly 3-4 FPS during the bad window. The default
summary (`--halo3mp_fiber_summary_interval=1000`) keeps enough counters to
confirm that the override is active without flooding the log.

For a normal interactive windowed run:

```bash
.\run_windowed.ps1
```

Normal runs expose keyboard controls as user 0's controller and log transitions
so routes can be recreated:

- Arrow keys: D-pad
- WASD: left stick
- Enter/Space: A
- Esc/Backspace: B
- X/Y: X/Y
- P/O: Start/Back
- Q/E: LB/RB

The window title shows host-measured guest-output FPS, outside the in-game HUD.

Historical note from the earlier handoff follows.

Boots through the render path and runs the game's job scheduler. **Does not
reach the in-game menus.** It now stops cleanly and deterministically at a
guest-initiated bug check (below) — 154 log lines, 103 fiber switches, zero
access violations.

Working:

- Retail XEX decrypted (AES-128, `NORMAL`/`BASIC`) and analyzed — Title ID
  `4D5307E6`, base `0x82000000`, entry `0x82598C38`
- 5 guest modules recompiled and registered (~29.6k guest functions total)
- Cross-module guest DLL imports resolved — 161/161
- D3D12 device, shader translation, graphics pipelines, render targets
- Guest `MAIN_THREAD` / `RENDER` / `AUDIO` / `ASYNC_IO` / `NET_DEBUG` threads
- SDL audio submitting frames; XMP music started
- **Vblank interrupts delivered to the guest** (verified: 180+ callbacks)
- **Job-system fiber switching** — 103 cooperative switches, no faults

## Build / Run

```bash
cmake --preset win-amd64-release && cmake --build --preset win-amd64-release
```

```bash
halo3mp.exe --game_data_root=<extracted-disc> --gpu_plugin=xenos
```

`--gpu_plugin=xenos` is required. The Halo 3 MP app defaults D3D12 to the faster
`render_target_path_d3d12=rtv` path and disables 16-bit gamma render-target host
storage to preserve correct menu and world rendering. A validated four-player
Zanzibar stress run averaged 29.0 FPS over its 60-sample tail on a Radeon 780M,
with a 17.8 FPS transient minimum after all four users became active. The D3D12
plugin also caches identical index-buffer bindings within each command list. In
adjacent profiled four-player runs, the cache skipped 19.6% of indexed bindings
and improved the post-activation average from 26.70 to 28.38 FPS. A subsequent
profiler-off confirmation averaged 28.77 FPS with a 23.8 FPS minimum, valid
102-second and 130-second gameplay captures, and no fatal errors. Menus and the
pre-split-screen gameplay interval were near 30 FPS. This is not a locked 30 FPS
result, and brief loading or gameplay dips still occur.
An isolated-cache four-player A/B of DXBC switch-based control flow found no
runtime gain from disabling it: matched post-activation, pre-capture windows
averaged 23.08 FPS with the default and 23.01 FPS without switches. The default
remains enabled; the lower cold-cache figures are not representative of the
warmed 28.77 FPS result above.
Two later quality-neutral D3D12 experiments were also rejected. Specializing
pixel shaders for the active gamma render-target mask had the same 29.6 FPS
median as the legacy branch path and only a noisy 0.30 FPS advantage in a
matched stable window, while an earlier matched window was 0.94 FPS slower.
Disabling submission at primary-buffer boundaries removed mid-frame reopens,
but reduced four-player output to 15.8-20.8 FPS while frame-opening fence waits
rose to roughly 645 ms per second. The existing shader and submission behavior
is retained. With 3D engine utilization reaching 100%, low command-processor
CPU time, and no meaningful benefit from lower output resolution or anisotropy,
the remaining 1-3 FPS below the 30 FPS cap on the integrated Radeon 780M is a
hardware/backend ceiling rather than the former XamUser/sign-in bottleneck.
`game_data_root` must be a **directory** of extracted disc files
(`HostPathDevice` mounted as `game:` / `d:`). Rerun `tools/genstubs.py` after any
`rexglue codegen`.

## Fixes carried here

### 1. Cross-module guest imports (`tools/resolve_imports.py`)

ReXGlue v0.10 resolves `xboxkrnl`/`xam` imports but **not** guest DLL -> guest
DLL function imports; codegen declares those thunks with no bodies so the
modules will not link. `l360` imports 81 from `WavesLibDLL`, `q10` imports 80.

The export table is **not** the PE export directory — it is at the virtual
address in `security_info + 0x160` (`0x8A0A7CEC` for `WavesLibDLL`, inside
`.text`). The PE section headers are stale (`.edata` claims RVA `0xC0000`, past
the `0xB8000` image end). `xex2_export_table` is big-endian:
`imagebaseaddr@0x20, count@0x24, base@0x28, ordOffset[]@0x2C`, with
`addr = ordOffset[ord-base] + (imagebaseaddr << 16)`. Import records encode
`ordinal = value & 0xFFFF`, `type = value >> 24`, read from the decrypted
pre-patch image. 161/161 resolved.

### 2. Guest fiber switching (`src/fiber_switch.cpp`)

`sub_825B5FE0` is a one-instruction thunk `b 0x825B8320`. The blob at
`0x825B8320..0x825B8728` has no internal branches and is Halo 3's job-system
**fiber context switch**: save `r1`/`r14-r31`/`cr`/`lr`/`f14-f31`/VMX to the
TLS-held context, restore the same set from the incoming context in `r3`
(including `mtlr r7` at `0x825B8574`), install the new context pointer, load the
new stack pointer, tail-call `KeSetCurrentStackPointers` (ordinal `0x9B`).

On hardware the final return uses the *restored* `lr`. ReXGlue compiles `blr` to
`return`, so `ctx.lr` is inert: the host returned to the original C caller while
`ctx` held the incoming fiber's registers, leaving `r26` foreign and making
`stw r10,0(r26)` in `sub_822C50B0` write to guest address 0.

The override gives each guest context its own host fiber
(`ConvertThreadToFiber`/`CreateFiber`/`SwitchToFiber`). Suspended state is kept
host-side as a whole `PPCContext`; the guest-visible buffer is also written on
suspend and read on first resume.

| | log lines | access violations | fiber switches |
|---|---|---|---|
| before | 353 | 1 (null write) | n/a |
| after | 154 | **0** | 103 |

### 3. `maps/campaign.map`

The engine opens `d:\maps\campaign.map`; this MP-only disc ships the campaign
descriptor as `maps/info/halo3.campaign`. Copying it to `maps/campaign.map`
clears the failed open. (Kept — it removes a real error, though it did not move
the stopping point.)

### 4. Cache partitions (`src/system/runtime.cpp`)

The SDK deliberately registers no `cache0:`/`cache1:` device. Halo 3 probes
`cache000.map`..`cache014.map` on both. Real writable directories are now
mounted before the `NullDevice`. First-run opens still fail (the title *opens*
rather than creates them), so this did not move the stopping point either, but
the devices are correct to have.

## Current stop — guest bug check

```
[bugcheck] guest KeBugCheck path: r3=0x3 r4=0x1 r5=0x0 r6=0x704d7ed0 r7=0x0 lr=0x825a56a8
```

The worker fiber's job is dispatched by `sub_825B5FF0`:

```
lwz r11,256(r13)   ; KTHREAD
lwz r11,356(r11)   ; current fiber context
lwz r3,0(r11)      ; job argument  <- verified valid (0x827B3AE8)
mtctr r10 ; bctrl  ; job entry, from context r31 (0x8232C830 -> b 0x8232C6F8)
li r3,0 ; bl KeBugCheck   ; if the job ever returns
```

`sub_8232C6F8` is a **bit-stream decoder**: it seeds a 64-bit value from two
`0x8232A888` calls, sets a 32-bit count, then loops extracting 1 bit at a time
via `0x8232A9E8` (mask table at `0x8202AB40`, refill through `0x8232A7C8`),
yielding the fiber via `0x8232C590` each iteration. After 103 yields it panics
with code 3 through `0x825A55F8` -> `sub_825A49B0` -> `KeBugCheck` (ordinal
`0x52`, thunk `0x82723AC4`).

`KeBugCheckEx_entry` flushes `stdout` but not the file logger before
`debug::Break()`, so its `*** STOP` line never reaches the log — which is why
this presents as a bare `0x80000003` with an ntdll RIP. The hook at the bottom
of `src/fiber_switch.cpp` logs and flushes instead.

### Hypotheses tested and eliminated

- **Vblank starvation** — the guest interrupt callback `0x821A4F50` fires
  normally (180+ deliveries). Not it.
- **Bad job argument** — `r3` is a valid pointer; its zeroed fields are
  initialized by the decoder itself. Not it.
- **Wrong fiber context offsets** — `r31`/`r1`/`lr` load correctly
  (`r31=0x8232C830`, `sp=0x704D7FB0`). Not it.
- **Cross-thread fibers** — all 103 switches occur on one thread. Not it (but
  it is a latent bug: Windows fibers are thread-affine, and the vblank callback
  runs on the vsync thread).
- **Suppressing the bug check** — the title continues with broken invariants and
  dies in an access violation inside the fiber entry. Strictly worse; reverted.
- **Non-fatal kernel debug breaks** — produces thousands of retry-loop log lines
  and still dies. Reverted (`git checkout src/kernel/xboxkrnl/xboxkrnl_debug.cpp`).
- **`share_registers`**, **guest SEH**, **writing registers back to the guest
  context buffer** — no effect (see git history).

### Next step

Work out what the decoder is decoding. Its refill source is `0x8232A7C8`;
tracing where that buffer is filled should reveal which asset or stream is
malformed, and whether the producer is another job that never ran.

## Manual work required

Static analysis leaves branch targets outside any discovered function; each is
declared in `halo3mp_manifest.toml` **in the owning module's table**, or the
runtime rejects the mapping and aborts. 14 declared. Classify new ones with
`tools/classify.py`: a target preceded by a `bl` is mid-function and needs
`share_registers = true`.

## Debug build

Release has no PDB. Build with CodeView into a separate directory (links against
the Release SDK):

```bash
cmake -S . -B out/build/dbg -G Ninja -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-march=x86-64-v3 -gcodeview -g" -DCMAKE_EXE_LINKER_FLAGS="-Xlinker /DEBUG:FULL" -DCMAKE_SHARED_LINKER_FLAGS="-Xlinker /DEBUG:FULL"
```

`src/main.cpp` installs a vectored handler writing `halo3mp_fault.txt` (RIP,
module base, RVA, enclosing guest function via `PPCImageConfig.func_mappings`,
and a backtrace with module names). Symbolize against preferred base
`0x140000000`:

```bash
llvm-symbolizer --obj=halo3mp.exe 0x140000000+<rva>
```

`src/system/xmemory.cpp` is patched to log guest `lr`, `last_indirect_target`,
`r1`, `r3` on an unhandled access violation.

## Helper scripts (`tools/`)

`xdvdfs.py` / `extract_all.py` (XDVDFS parse + extract, base `0xFD90000`),
`xexlib.py` (XEX2 header, AES, BASIC decompression), `resolve_imports.py`
(export table + import ordinals), `genstubs.py`, `classify.py`, `dis.py`
(PPC disassembly via the SDK's binutils), `findlongjmp.py`, `addfunc.py`,
`autofix.sh`.
