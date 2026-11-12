# Halo 4 Forge via ReXGlue

For the current evidence summary and outstanding work, see [STATUS.md](STATUS.md).
The sections below retain the chronological investigation and earlier failures.

Current UI contract (2026-10-28): automatic activation in Forge; press X while
holding an object to use native Physics: Normal / Fixed / Phased. Older F7 panel
instructions below are historical. F7 is now reserved for a pending developer
framerate testing toggle, default off. See STATUS.md for current validation.

Current mathematical adjustments are complete: 135 scenery bindings and 44
source-backed anchorless entries cover all 179 Gulch/Cove scenery entries.
The staged marker pack is 24,688 bytes. Positions, proper marker frames and
search bounds pass numerical checks. In-game testing and subsequent fixes
belong to the user. See [STATUS.md](STATUS.md) for the current scope; older
investigation and test instructions below are historical.

Current native checks use `run_native_check.ps1 -NativeMenu -MenuCase position`
(or `rotation`, `resume`, `lifecycle`). Add `-AutoStartup` to omit enable and
private-data-path overrides. The optional local build stages the three private
H4 inputs in `advanced-forge/` beside its executable; these assets stay ignored
and must not enter a public package. Explicit diagnostic paths still work.
Older persisted paths are a fallback when adjacent inputs are absent.

Original marker-material verification (run with TEMP/TMP under `work/build-temp`):

```powershell
cmake --build work/rexglue-sdk/out/pacing-release --target h4_forge_marker_shader_check h4_forge_marker_shader_gpu -j2
python -B tools/h4-forge/translate_marker_materials.py
python -B tools/h4-forge/verify_marker_shaders.py
```

This uses the scoped `rexglue-sdk-shader-texture-source.patch` in the SDK.
It compares retail microcode execution with generated HLSL in headless WARP.
All generated shaders, texture inputs and results stay private under `work/`.
Passing this check does not establish live particle or visual parity.

User direction (2026-10-23): recompile Halo 4 and use its actual Forge program logic for PC Advanced Forge. Do not implement a bespoke snapping replacement. Running the whole Halo 4 game is not required.

## Reproduce

From the OpenH3M source repository, with TEMP/TMP directed to work/build-temp:

```powershell
& .\work\rexglue-sdk\out\win-amd64\rexglue.exe --log-file work/h4-forge-research/rexglue-codegen.log codegen tools/h4-forge/halo4_manifest.toml
```

Input: private Disc 1 executable at work/h4-forge-research/assets/default.xex; title 4D530919, media 1C9D20BC. SHA256 cc9d2ca4ff8c70eb7ece86729a6da8f0b2a49201ca1a7385cf64dc4666183d6b.
Generated guest C++ stays in ignored work/h4-forge-research/generated. Do not commit executable, maps, decoded images, or generated game code.

Disc 2 reference: work/h4-forge-research/disc2-assets/ca_forge_ravine.map. Its extraction report verifies every STFS data block. ravine-magnets.json contains 734 marker points across 119 models. These are data references, not a substitute for the executable's magnet-selection and placement logic.

Original selection/alignment has now been isolated and executed; the live editor integration is undergoing native validation. Do not declare Advanced Forge implemented from code generation alone. Preserve Halo 3 saved-layout formats, simulation and network behavior.

The abandoned bespoke prototype was removed from the H3 source/build integration before this pass. Its experimental build was never deployed; SDK halo3mp.exe must not be deployed until rebuilt from accepted sources.

## Original-code trace (2026-10-23)

Disassembly establishes the following path, without substituting behavior:

- Magnet enable callback 0x82685EE0 emits Forge event 0x10; sensitivity callback 0x82685F38 emits event 0x11.
- Submission goes through 0x825812D0. Application at 0x824500A8 updates the per-player enable byte (+0x1B3E) and sensitivity (+0x1BF8) within the TLS 0x1C state, player stride 0x150.
- 0x82582250 collects the held object's markers, queries nearby objects, calls marker-pair scoring 0x82582C80, and checks the sensitivity threshold before keeping the candidate.
- 0x82582610 collects up to 32 markers through 0x8226BCA0. The marker-name ID is read from Forge globals by 0x82582A68, rather than embedded as an immediate constant in this routine. Ravine's actual marker-group field confirms sandbox_magnet = 0x193.
- 0x825826B0 updates marker visibility as selected objects or the enabled state change.

These names describe observed behavior; they are not recovered debug symbols. Integration and runtime verification remain outstanding. The initial ReXGlue pass failed on 20 calls to 15 missing entry points. The manifest records those original PPC entry points with shared registers, preserving tail helpers' non-ABI inputs. No stubs were supplied.

`inspect_ppc.py ADDRESS --bytes SIZE` displays original PPC; `--callers` finds direct call/tail-branch references. It uses the private decoded image, never launches the game, and does not generate desktop input.

## ReXGlue extraction status

The corrected pass completed in 380 seconds and emitted 589 files. Warnings concerning other executable regions remain in the private codegen log; this does not establish a runnable full-game recompilation.

Run `python -B tools/h4-forge/extract_forge.py` after code generation. It extracts 34 original function bodies (selection, pair scoring, alignment, sensitivity and math/ABI helpers), rejects missing or indirect dependencies, and records each source body hash in ignored `work/h4-forge-research/isolated/extraction.json`. Only declarations and the containing C++ namespace change; the generated function bodies are copied unchanged. Five external calls are explicit scene-data integration boundaries. The extracted unit declares those calls; forge_bridge.cpp supplies data-only adapters over a caller-provided scene snapshot.

Run `tools/h4-forge/compile_isolated.ps1` to compile this extraction. Compilation passed with an empty diagnostics log. The later checks below execute the original routines. Live OpenH3M integration is still pending. H3 and H4 guest address spaces remain separate.

## Executed alignment check

`tools/h4-forge/test_original_alignment.ps1` builds and runs the actual extracted 0x82582AD0 routine in a separate process. The harness reserves a separate guest address space, loads the private original H4 decoded image for constants, and supplies the required per-player state and marker matrices. Unused scene-query callbacks throw if reached; no snapping behavior is implemented by the harness.

Three fixtures pass: identity held rotation, a 90-degree held rotation, and a differently rotated destination marker. Each independently verifies unit quaternion output, preserved held rotation, guest stack restoration, and that applying the returned transform to the held local marker lands on the destination marker within 0.0001 units. This establishes the original alignment behavior under these inputs; it does not establish candidate selection, live editing, or saved-layout compatibility. Results: work/h4-forge-research/isolated/alignment-test.log.

## Original selection and reusable bridge

`extract_config.py` extracts the retail `forg` settings tag from Ravine, verifies marker ID 0x193, and records its source offset/hash. Its five sensitivity multipliers are 0.1, 0.25, 0.5, 0.75 and 1; the original angle threshold is 45 degrees and scoring weight is 0.75. These bytes feed the original tag lookup and routines, rather than new tuning logic.

`test_original_selection.ps1` executes 0x82582250 with the original settings and proves that the nearby marker is selected while the distant marker is not snapped to.

`forge_bridge.h/.cpp` now wraps those same routines in a separate H4 guest memory arena. Callers supply object positions, radii, original-format marker transforms, cursor and held basis. The bridge marshals data and invokes the extracted selection and alignment functions; it does not rank or align candidates itself. It maps the selected compact object index back to the caller's datum. The interface currently requires at most 64 nearby objects and 32 markers per object, matching these original routine buffers; the eventual H3 caller must provide the proper nearby-object set. Thread-local scene context is cleared on exceptions; nested evaluation is rejected.

`test_bridge.ps1` passes near-target, far-target, alternate-candidate, and missing-marker checks. Output: work/h4-forge-research/isolated/bridge-test.log. Live H3 snapshot collection, marker mapping, Forge controls, placement application, and native verification remain outstanding. No new runtime has been deployed.

## Shared OpenH3M build

`OPENH3M_ADVANCED_FORGE=ON` now builds `h4_forge_original` in the existing SDK build, and makes it available to the game target. The option defaults off for ordinary builds without private H4 inputs. `h4_forge_bridge_check` links the same library and passes the scene fixtures inside that build. It also builds the opt-in live placement hook and F7 editor controls; native validation is still required. No separate SDK/game build tree was created.

Build from the repository with LLVM and the installed Visual Studio Ninja directory on PATH, and TEMP/TMP set to work/build-temp:

```powershell
cmake --build work/rexglue-sdk/out/pacing-release --target h4_forge_bridge_check -j2
& ./work/rexglue-sdk/out/win-amd64/h4_forge_bridge_check.exe
```

Native evidence: work/h4-forge-research/isolated/host-check.log. Installed game executable and maps remain untouched.

### Marker binding findings

38 Reach palette names have candidate H4 UNSC-clean counterparts. Names alone do not establish geometry equivalence. The historical variants/target-palette.json has stale datums: current Gulch scenery slot 4 is 0x90002937, not historical 0x9000293B. Read the current scenario palette and labels before binding.

Bank 1x1 current H3 model 0x90002939 has identity root transform and bounds (-1,0),(0,1),(-0.5,0.5). H4 counterpart model 13036 also has identity root transform but bounds (-0.9798829,-0.0014409),(0.0014409,0.9798829),(-0.5022143,0.4762276). H4 marker positions therefore need checking against actual Reach surfaces; do not blindly use name matches as validated anchors. Candidate names are recorded privately in anchor-binding-candidates.json.

## Live integration candidate

`halo3mp/src/advanced_forge.cpp` hooks original H3 placement 0x822837C8 and passes held/candidate scene data to the original H4 bridge. The returned position goes through H3's original placement and variant update. No new saved-layout fields are introduced. Magnets default off; F7 opens the controls. The private input directory is supplied with `halo3mp_advanced_forge_data`.

`export_bindings.py` exports current Gulch/Cove palette bindings to ignored `isolated/markers.bin`; 79 map-specific entries are present. It requires identity model roots and node-zero markers. This is a candidate binding set, not proof that every H4 marker fits the Reach geometry.

The shared game build passes with these hooks. Bounded native diagnostics log hook entry, editing/network gates, marker binding, and actual snap events. `trace_loading.py --advanced-forge-data work/h4-forge-research --forge-scenery-check` enables this candidate in the existing process-local route. Installed executable remains unchanged. Outstanding: native snap demonstration, marker fit, saved-layout round-trip, and verification of the offline guard.

### First live hook check

Native run `.local/loading-traces/20261023-225434-41480` reached Forge Gulch (map 1730) and created current Bank 1x1 (definition 0x90002937). Its native `proof-loaded.png` was inspected: the expected bank piece and Forge monitor are visible. Hook logging confirms 0x822837C8 was entered. No snap is established by this run.

Original PPC at 0x82280BFC–0x82280C20 proves the edited-object table stores variant slot indices, then resolves the live datum at engine+0x1AC+slot*0x54. Corrected the adapter's previous direct datum comparison and rebuilt successfully. The process-local check now moves the held piece to trigger placement updates. Next native run must verify this corrected lookup, offline gate and marker binding before a two-piece snap test.

### Live original-code execution

Run `.local/loading-traces/20261023-230440-43200` uses the exclusive H3IR input replay (59 frames, no live controller merging). Native capture inspected: Forge monitor and Bank piece present. The runtime logged map 1730, held datum E2A80004, three original H4 markers, and original H4 evaluation of a one-object scene with no snap. This proves the bridge executes with live data; it does not prove a successful two-piece snap.

The prior run established local simulation=1 and network-type=1. The guard now requires simulation=1 at game globals+0x14, rather than incorrectly requiring network-type=0. Original PPC reads that simulation field; [ManagedDonkey game.cpp](https://github.com/twist84/ManagedDonkey/blob/master/game/source/game/game.cpp) identifies local=1 and networked simulation=2..5. Disassembly evidence is retained in isolated/h3-simulation-gate.txt.

Original H3 placement accepts absent forward/up arguments and preserves the existing variant axes (82283850..8228388C). The adapter now mirrors that data handling for translation-only events. This latest correction still needs a native run. Remaining verification includes continuous held movement versus release placement, two-piece snapping, marker fit, UI controls, saved-layout round-trip, and installed-build deployment.

### Two-piece fixture and black-screen correction

The first saved diagnostic layout omitted player initial/respawn objects. Run `.local/loading-traces/20261023-231053-39092` remained on a black scoreboard despite a live render loop. Its native capture was inspected and rejected. The exclusive input replay intentionally excludes live controls; that alone did not establish the cause of the black scene.

`build_snap_fixture.py` now retains stock initial/respawn records from the verified Hemorrhage conversion and places them at Gulch's authored spawn. Run `.local/loading-traces/20261023-231508-34624` subsequently reached Forge gameplay (native capture inspected), bound three Bank markers, and evaluated the original H4 routine continuously through the original H3 live-pose call 0x8232E8B8. Final placement remains hooked at 0x822837C8.

The captured two-object scene is `forge-scene.bin` in that run. `h4_forge_bridge_check.exe <scene.bin>` reproduces the no-snap result offline. Its nearest marker pair is 1.040388 units apart: the first target position was outside snap range. Translating only the diagnostic target to a 0.1-unit marker gap produced an original-H4 snap offline. This adjusted scenario is isolated/adjacent-scene.bin; the fixture builder now uses that measured target pose. Native snapping is still unverified.

`scene_snapshot.h` defines a private diagnostic AFS1 file; it is not embedded in H3 layouts. The harness saves a bounded latest nearby scene and supports exclusive H3IR replay. Future diagnostic windows identify that live controls are disabled. No installed map/executable was changed.

### Deterministic live snap evidence and remaining release issue

Run `.local/loading-traces/20261023-232458-43324` uses an explicit process-local diagnostic drag request (-44.7924538,-197.9406281,2.582953). The request is applied before marker collection/selection, requires exclusive replay and tracing, and never changes H4's selection result. The normal camera route previously left a 0.695-unit closest marker gap; this controlled input avoids timing guesses.

The original H4 routine repeatedly selected target E2A10032 for held E2A80038 in live Forge. Native `proof-loaded.png` inspected: both Bank pieces are present. The captured scene replay also reports snap=true with output approximately (-44.7929,-197.841,2.58295). This proves controlled in-game snapping, not unrestricted user editing or stable placement after release.

The read-only native variant snapshot after H3 placement was exported by `export_native_variant.py` to isolated/snap-result.bin. The wrapper clears runtime object/helper handles and gamestate indices, preserving the native v12 layout data; no Advanced Forge metadata is included. Actual reload is still pending. The captured final Bank has a tilted orientation, and the closest marker residual is approximately 0.383 units, rather than coincidence. Investigate normal H3 post-release physics versus an integration error; do not mark stable release verified.

The editor toggle now uses atomic state initialized from its startup option, avoiding concurrent reads/writes of the plain cvar. The visible sensitivity control uses qualitative snap-distance labels. These latest UI changes compile but still need verification.

### Single evaluation per native placement

Original H3 disassembly at 822838A0 updates the saved variant before its
8228390C call to the live-pose routine. The adapter now uses a thread-local
placement scope to skip the nested live hook. Direct editor preview calls
still evaluate normally. This prevents two independent H4 evaluations (or two
diagnostic drag overrides) from changing the pose across the save boundary.
The original H3 placement, physics and simulation calls remain intact.

When tracing, `forge-scene.bin.placement.csv` retains the latest 128 final-placement
evaluations: check number, object datum, variant slot, snapped flag, requested
position (3), input basis (9), H4 output position (3), and output quaternion (4).
These are diagnostic files only, never embedded in a saved layout. A successful
build does not establish that release alignment is fixed; native evidence is
required.

Native run `.local/loading-traces/20261023-233426-17488` confirmed identical
identity orientation from H4 and the held input. During the run the native
saved position matched H4 output to 0.000001 units. The final snapshot later
changed position and tilted; suppressing nested evaluation alone therefore
does not resolve the release issue. Capture requested at 175 seconds did not
finish before the 180-second watchdog, and this run is not visual validation.
`inspect_placement.py` compares the bounded placement CSV with the native
snapshot; private output is isolated/release-analysis.json.

The next build retains a rolling placement history instead of the first 128
records, and records `.native.csv` for changed native poses of the last edited
object even after its edited slot clears. Columns: original caller address,
object datum, variant slot, position (3), forward (3), up (3). It keeps at most
128 changed poses. This will identify the native caller responsible for the
post-snap movement. This additional instrumentation compiles but has not yet
been run. No installed executable has been replaced.

### Release caller identified

Run `.local/loading-traces/20261023-233925-2748` records the exact identity-axis
snap followed by changed poses from return address 0x822840CC. Original PPC
at 822840A8/822840B0 reads the live object's orientation/position before passing
that pose to 822837C8. Thus the later tilted saved pose arrives from native H3
object-state synchronization, not H4 changing the original snap quaternion.
This does not by itself isolate the precise collision impulse. The former
same-facing Bank fixture is geometrically suspect: its center-to-edge marker
connection overlaps the triangular footprints.

An offline captured-scene check with the target bank rotated 180 degrees and
its diagonal marker opposed still snaps through unchanged H4 code. The fixture
builder now uses that joint with a 0.1-unit approach gap. Its live release
verification remains outstanding. The original map and physics are unchanged.

The 165-second capture again missed the watchdog because native timing begins
about 16 seconds after process creation. No visual verification is claimed for
this run. Advanced Forge's diagnostic release is now at replay time 140 seconds
(with movement at 135); use capture time 150 seconds within the 180-second
process watchdog. The altered fixture and route still require a native run.

### Opposed-bank native result

Run `.local/loading-traces/20261023-234328-42904` completed its 180-second
watchdog with the requested native capture. `proof-loaded.png` was inspected:
Forge Gulch is visible in player mode with both bank pieces present after
release. They are not a clean aligned assembly. Native pose history again
shows subsequent changed orientation through 0x822840CC. Opposing the banks
therefore did not remove the observed movement; do not treat the earlier
footprint-overlap hypothesis as an established cause. Next isolate marker fit
against actual Reach collision geometry and ordinary release behavior on a
flat supporting surface. Do not change stock gravity to force a pass.

The earlier release/capture schedule works. Native snapping, placement-write
agreement and the later object-sync caller are established; stable assembly,
UI behavior and saved-layout reload remain unverified.

### Collision and release-state audit

`audit_marker_geometry.py` reads all 79 current bindings and saves original H3
polyhedron vertices/planes, shape radii, rigid-body motion types, and the H4
anchors to isolated/marker-geometry.json. Bank 1x1 has one node-zero rigid body,
flags 0, motion type 5 (Fixed in the paired H3 schema). Its collision shape is
a four-vertex tetrahedron with radius 0.0164. Therefore ordinary authored
dynamic gravity is not an established explanation for the live release motion.
The audit reports raw local shapes; additional body transforms must be resolved
before claiming a complete geometric-fit audit for every piece.

Original 82284078 is called both by drop paths and the deferred-object loop at
82283B64 (engine list E4A8, count E8A8). The native trace now appends its caller
address to each changed-pose row, distinguishing those paths without changing
original state. This additional diagnostic still requires a native run.

### Native Fixed-piece release candidate

Run `.local/loading-traces/20261023-235115-33720` completed with a native capture
(inspected: gameplay and both pieces after release). The final provenance
column identifies return address 0x82283B68, the original deferred-object loop.
The drift therefore occurs while the piece is still in H3's settling queue.

Original 82283CF8 removes a queued object and invokes 8227E770, which invokes
8232EB28 with false. Disassembly confirms 8232EB28 clears the force-dynamic bit
(object physics flags bit 20) and calls the original physics rebuild. This is
an existing H3 editor transition, not a custom physics implementation.

The candidate hooks normal release 8227FDF8: only after a current original-H4
snap, for a binding whose authored rigid bodies are all Fixed and whose object
flags permit restoring that state, it calls original 82283CF8 on the matching
queue entry. Throws (original threshold at 8202496C), dynamic pieces, disabled
magnets and nonlocal simulation bypass this finalization. Original H4 still
supplies the snap transform; no coordinates or saved-format fields are added.

Private binding format is now AFM2: the prior entry header plus a uint32
native-Fixed eligibility field before marker records. Regenerate bindings with
export_bindings.py. The 79-entry metadata is 13,712 bytes. Most entries have
Fixed rigid bodies; Arena Window and Walkway Small Cover on each map have Box
motion and are excluded. Build passes; live release validation of this candidate
is outstanding. Installed executable remains unchanged.

### Fixed release verified

Run `.local/loading-traces/20261023-235710-35312` invokes native fixed-object
cleanup and records no subsequent deferred-loop drift. Its inspected native
capture shows the two bank pieces connected after return to player mode. The
last native saved pose matches the last H4 result: position difference below
0.000001 units and basis difference below 0.000001. Transforming the original
H4 anchors by the two saved H3 poses gives a minimum marker residual of
0.0000027795 units. A small orientation change before drop is retained by H4's
original alignment rule; the final snap accounts for that orientation.

`inspect_placement.py` now computes this saved-marker residual directly from
the captured scene and native variant, rather than assuming identical initial
axes. `run_native_check.ps1 -Mode snap` repeats the bounded native test;
`-Mode reload` loads isolated/snap-result.bin without enabling Advanced Forge
or providing private H4 data. The latter run is in progress and must be checked
before claiming saved-layout round-trip validation.

### Native layout reload verified

Run `.local/loading-traces/20261024-000119-37616` loaded the exported
`snap-result.bin` into ordinary Slayer without Advanced Forge options or private
H4 data. The native capture was inspected: Forge Gulch gameplay, Slayer HUD,
and both bank pieces in their saved assembly are visible. The camera differs
from the Forge release run because the reload route does not move the monitor.
This establishes a basic native layout reload; it is not an Xbox hardware or
system-link test, nor verification of every marker binding or editor control.

Remaining completion work: test user-facing editor controls, validate marker
fit beyond the Bank fixture, verify applicable disabled/network guards, remove
unneeded diagnostic overhead, and deploy only after the final candidate passes
its relevant checks. The accepted installed game has not yet been replaced.

### Whole-binding coordinate audit

`audit_binding_bounds.py` compares each actual H3 model's compression bounds
with its original H4 counterpart. Results are in isolated/binding-bounds.json.
Several name matches have materially different local coordinates: H4 Dish is
a positive-X half-disc, while Reach Dish is a negative-Y half-disc; Arch Brace
has roughly a one-unit X/Z origin shift; Bank 2x1 lies on the opposite Y side.
All five inspected H4 roots (Dish, Dish Door, Base Round, Arch Brace, Bank 2x1)
have identity transforms, so these differences are in authored geometry rather
than an unhandled default node transform. Bounds alone cannot determine a
unique registration or prove equivalent shapes.

Do not claim all 79 raw-coordinate bindings validated. The Bank 1x1 live/reload
proof remains valid; coordinate adaptations for other pieces need evidence
from actual corresponding geometry. The loader now rejects nonfinite bounds
or markers, non-unit marker quaternions, duplicate bindings and trailing data
before those values reach the original H4 routine.

### Evidence-backed anchor coordinate adapters

`audit_h4_collision.py` extracts collision polyhedra from 42 original H4 models
using the Gen4 physics structure layout, validating vertex/plane block counts.
`compare_collision_frames.py` proposes horizontal rotations/translations by
comparing both actual collision meshes. It never applies its candidates;
reskins can differ and symmetric shapes produce ambiguous registrations.

Three reviewed entries in `anchor_frames.json` are applied by the binding
exporter: Bank 2x1 reflects Y and translates its original nominal planes onto
Reach's; Dish and Dish Door rotate 270 degrees around Z with separate front/base
origin corrections. `anchor_frames.py` transforms marker positions and proper
rotation frames, including reflection conjugation. Original H4 selection,
scoring and alignment code is unchanged. Map assets are unchanged.

`check_anchor_frames.py` passes measured Bank construction-plane and outward
normal checks, plus Dish front/base plane and normal checks. These validate
coordinate data, not rendered/native behavior of every adapted object. Bank
1x1 metadata is untouched, preserving the already verified snap/reload fixture.
Other frame differences remain under review; controls and final deployment
remain outstanding. No broad fit claim follows from the three adapters.

### Process-local editor controls check

`forge_controls.h` contains the same panel drawing/control code used by the
actual game dialog and `h4_forge_controls_check`. The latter creates a headless
ImGui context and delivers key/mouse events only to its own ImGui IO; it uses
no OS window, keyboard, mouse or controller injection. Ini/log output is disabled.
The test passes F7 open/close, checkbox enable/disable, and lowest/highest snap
distance selection using real widget interactions. This proves control state
behavior and draw-data creation, not a native visual screenshot of the overlay.

Build target `h4_forge_controls_check` in the existing shared SDK build; run
work/rexglue-sdk/out/win-amd64/h4_forge_controls_check.exe from the repository.
Game build also passes. The native disabled-mode saved-layout reload remains
the evidence that ordinary gameplay does not require loading private H4 data.

### Mirrored Bank 2x1 native verification

`build_snap_fixture.py --bank 2x1` creates an independent 57,837-byte native
fixture, retaining the verified spawn records. `run_native_check.ps1 -Mode snap
-Bank 2x1` selects current palette index 6 (definition 90002948), preserving the
original Bank 1x1 fixture and route.

Run `.local/loading-traces/20261024-001808-17972` reached gameplay, executed
original H4 selection/alignment with the adapted markers, and invoked original
H3 Fixed-object cleanup. Its native capture was inspected: larger Bank 2x1
pieces remain connected in player mode after release. The saved-pose marker
residual is 0.00000018433 units (isolated/bank2x1-release-analysis.json). This
validates the Y-reflection adapter for this fixture, not every possible joint.

`verify_original.py` separately confirms all 34 integrated function bodies
still exactly match their ReXGlue output and recorded hashes. Output is retained
in isolated/original-integrity.log. Dish adaptations and other binding frames
still need their relevant checks before a broad completion claim.

### Dish release and normal-startup preparation (2026-10-24)

Run `.local/loading-traces/20261024-002509-26384` completed its watchdog.
The native capture was inspected: player-mode Forge gameplay and paired Dish
pieces are visible from underneath. This verifies this placement, not every
surface or possible joint. Final saved marker separation is 0.0000043008 units.
The saved pose matches the LAST H4 evaluation within 0.000000211 units and
axes within 0.000000001. Earlier evaluations used a different held orientation;
comparing them to the final snapshot incorrectly suggests drift. Original H4
preserved the changed orientation and realigned the marker. Full evidence:
`work/h4-forge-research/isolated/dish-release-analysis.json`.

The existing `deploy_dlc_host.py` now accepts `--advanced-forge-data
work/h4-forge-research`. It validates private inputs before installation changes,
writes their absolute location into normal executable bootstrap configuration,
and leaves magnets off until enabled with F7. It does not copy H4 inputs into
DLC/layouts or enable test replay, forced drag, or tracing. Generated settings
passed TOML parsing and these property checks without deployment.
Installed executable remains unchanged. Direct-launch validation/deployment,
Dish Door and remaining object-frame matches remain outstanding.

### Installed editor build (2026-10-24)

Advanced Forge is now deployed at `C:/X360/ISOs/H3M/OpenH3M.exe`.
Executable SHA256: 0f4321582aa754691ac23b38cb9b1b838ec88945b9e28a8e17dfbda950ebf604.
The existing shared SDK libraries were deployed with it; DLC caches and layouts
were not rebuilt or changed. Deployment inventory: `work/dlc/deployment.json`.
Private H4 data remains inside this repository and is referenced by bootstrap
configuration. No launch script is necessary. Start the executable normally,
enter offline Forge, press F7 and enable Magnets (Halo 4); select snap distance
there. F7 hides the panel. Magnets default off on startup.

Normal-bootstrap launch was checked with native output capture only, no input
replay or forced drag. `isolated/direct-launch/startup.png` was inspected:
correct Halo 3 Mythic main-menu scene and readable text. The 60-second watchdog
closed the diagnostic process. This proves normal startup, not live F7 overlay
appearance or audio. The same compiled ImGui control check passed F7 open/close,
enable/disable and distance endpoints again after installation. Earlier native
Forge snaps and ordinary saved-layout reload provide gameplay evidence.

Remaining: review unverified object-coordinate bindings, Dish Door adaptation,
and live overlay visual evidence. No physical Xbox 360 or system-link test has
been performed; the editor is gated to local simulation and saves native H3
layout records with no H4 metadata embedded.

### Native host panel visual verification (2026-10-24)

`halo3mp/patches/rexglue-sdk-host-ui-capture.patch` adds an optional one-shot
capture of the application's own final D3D12 backbuffer after host UI drawing.
It copies into readback memory on the application's queue, waits on its existing
submission fence, and writes a top-down BGRA BMP. It does not read the desktop,
enumerate windows or inject input. Normal runs leave the path empty and perform
no readback/allocation. Options: `--d3d12_host_capture_path=<absolute BMP path>`
and `--d3d12_host_capture_after_ms=30000`. Keep the destination in this repository.
`--halo3mp_advanced_forge_panel=true` exposes the panel at startup without input;
normal default is hidden and F7 toggles visibility.

Shared SDK/game build passed. A bounded 60-second run with no input produced
`work/h4-forge-research/isolated/panel-check/panel.bmp`. The complete native frame
was inspected: Advanced Forge panel, magnet checkbox, Medium distance slider,
Off status, counters and F7 instructions are visible over the correct main-menu
background. This resolves the prior live overlay appearance gap. Interactive
widget behavior was separately verified with the shared process-local ImGui test.
The watchdog closed this run. The tested build was then deployed through the
existing deployment tool; capture/panel-startup flags are not persisted to the
installation. Inventory: `work/dlc/deployment.json`.

### Batched construction-origin corrections (2026-10-24)

Geometry review found three additional data errors: Arch Brace uses a rotated
and displaced construction frame; Crenel Notch and Bunker Covered have half-unit
vertical origin differences. `anchor_frames.json` records the source measurements
and corrections. The Arch Brace X/Z transformed render extents agree within
0.001 units; all three corrected base planes agree within 0.00001 units on both
map palettes. Collision registrations independently support these corrections;
the 0.0164 collision skin is deliberately excluded from construction offsets.
`check_anchor_frames.py` checks these independent render-bound relationships
and unit quaternion preservation, alongside the earlier bank/Dish checks.

`export_bindings.py` regenerated the same 79 entries in the same 13,712-byte
private file. No map/cache/layout or original H4 program changed. The installed
editor references this file and reads it on first magnet use in a fresh process.
These three adaptations have geometry evidence, not new in-game visual evidence.
Remaining ambiguous registrations must not be automatically applied from the
nearest-neighbor score alone. Original-code integrity (34 bodies) and original
bridge near/far/alternate/missing-marker tests passed after the data update.


### Arch Brace native release check (2026-10-24)

`run_native_check.ps1 -Mode snap -Bank arch` reuses the shared executable,
cache and layout builder. The fixture selects verified current palette index 2,
definition 9000291B, and starts the opposed construction ends with a 0.1-unit gap.
Run `.local/loading-traces/20261024-004222-26220` reached Forge gameplay, executed
original H4 snapping and original H3 fixed-object release, then ended at its
180-second watchdog. The last saved pose matches H4 within 0.000000184 units;
marker separation is 0.0000056287 units, and axes differ below 0.000000001.
Details: `isolated/arch-release-analysis.json`.

The actual native capture was inspected: expected Gulch environment, player-mode
Forge HUD and Arch Brace geometry are present. The close viewpoint obscures part
of the connection, so this image does not establish the complete visible seam.
The numerical result establishes native placement retention and marker coincidence;
it does not establish every construction joint or resolve unrelated material
appearance. Remaining object-specific fit work is not covered by this run.

### Scene-depth anchor renderer (2026-10-28)

Apply `halo3mp/patches/rexglue-sdk-scene-marker-depth.patch` after the existing
query snapshot, batch-query, asynchronous-readback and guest-draw-scope patches.
Build the shared `halo3mp` and `rexgpu-xenos` targets. The editor publishes
transient marker positions to the renderer; marker visibility is evaluated
against the native same-frame scene depth. No map or saved-layout data changes.
The old ImGui circle drawing function has been removed. Original H4 pixel
materials are integrated below; particle sizing/lifecycle/compositing remain
provisional.

`run_native_check.ps1 -Anchors -AutoStartup` requests native captures at replay
136/140 seconds and holds the object through 154 seconds. Host capture timing
may differ; inspect its actual state rather than assuming it is held.
Inspect all images and the final saved pose;
successful dispatch logs alone are not acceptance. Run
`20261028-103931-16968` passes scenery-anchor occlusion and placement retention.
See `PARITY-2026-10-28.md` for exact evidence and renderer coverage limits.

### Original marker material inputs (2026-10-28)

The user accepted the current anchor visuals on 2026-10-28. The steps below
retain reproducibility; further particle-fidelity work is no longer required.
Pipeline/resource creation runs asynchronously, with nonblocking adoption on
the render thread. See the latest parity evidence for timings and limitations.

After the existing checksum-verified marker-page extraction, run
`python -B tools/h4-forge/decode_marker_bitmaps.py` and
`python -B tools/h4-forge/extract_marker_shaders.py`. These produce private
decoded textures and exact retail shader microcode beneath the research tree.
Build `h4_forge_shader_disasm` in the shared SDK build. For each entry in
`isolated/marker-shaders/extracted.json`, invoke it with the entry's `kind`,
absolute input path, and an output path ending in `.ucode.txt` beside the input.
Then run `python -B tools/h4-forge/verify_marker_assets.py`.

The offline shader tool creates no device/window/input and disables automatic
SDK shader dumping. All commands must use this repository as their working
directory and keep TEMP/TMP/build outputs inside it. Passing these checks proves
source extraction/decoding, not final particle appearance or live animation.

After the original pixel-program translation and execution checks, run
`translate_marker_fade.py 331`, `translate_marker_fade.py 16`, and
`verify_marker_fade.py` with the repository Python and `-B`. Build the shared
`h4_forge_marker_shader_check`, `h4_forge_marker_shader_gpu` and
`h4_forge_marker_compile` tools first. Then run
`python -B tools/h4-forge/pack_marker_material.py`. It requires the validated
shader hashes and packs the programs with all five decoded textures into
private version-2 `isolated/marker-material.bin` containing precompiled programs.
No source compilation occurs during live marker drawing. Apply
`halo3mp/patches/rexglue-sdk-scene-marker-material.patch` after the depth patch.
The optional `h4_forge_runtime_data` build target stages the private pack beside
the executable; it must not be committed or published with game assets. Rebuild
the shared game/SDK targets and use the native anchor route above. The pack
currently supplies canonical interpolants with verified original near/far fade
blocks; it does not implement particle life, world size, curve inputs or HDR
composition. `h4_forge_marker_pipeline_check` accepts the private pack path and
checks actual packaged output for fading/occlusion in single/MSAA modes without
a window. Native capture still provides the live visual acceptance evidence.

For original particle-curve research, rerun `extract_forge.py` and
`verify_original.py`, then `./tools/h4-forge/check_marker_curves.ps1` from the
repository. The checker compiles a process-local executable, reads the original
image/functions in a private arena, and writes CSV/JSON below the ignored
research directory. It creates no game window, GPU device or host input.
Constant/identity outputs are independently checked; complex curves are
reported with original-code hashes and finite-output checks. This is not a
substitute for live particle-lifecycle or visual verification.

### Spartan window branding (2026-10-28)

The user's request relayed from "Check Spartan name availability" is implemented
in the shared build. `rexglue-sdk-window-display-name.patch` adds an overridable
display name distinct from the persistent app identity. The game overrides it
with `Spartan`; both initial creation/build-stamp titles and ongoing FPS titles
use that display name. Automated-test and FPS suffixes remain intact. Existing
OpenH3M profile/cache/config paths and executable filenames stay compatible.
The repository remains `https://github.com/GTTeancum/OpenH3M` at the same local
path. SDK/game compilation and patch reverse-apply checks pass; no desktop
inspection or outside-repository installation was performed for this update.

### Native menu scenery coverage

The menu replay accepts every supported scenery fixture. For Arch Brace, run
`./tools/h4-forge/run_native_check.ps1 -Bank arch -NativeMenu -AutoStartup`.
Validate with `verify_physics_run.py RUN --reference REFERENCE_VARIANT
--modes normal,fixed,phased --native-menu --native-position --automatic
--adjacent-inputs`, using the earlier Arch Brace native snapshot as reference.
Inspect both native captures separately. Export the result with
`export_native_variant.py RUN/native-variant.bin
work/h4-forge-research/isolated/arch-menu-result.bin`, then use
`./tools/h4-forge/run_native_check.ps1 -Mode reload -Result arch-menu` and
`verify_native_reload.py EDITED_RUN RELOAD_RUN` for ordinary Slayer reload.
These are repository-confined process-local tests, not console hardware tests.

### Controlled overlap checks

Run `./tools/h4-forge/run_native_check.ps1 -Bank 2x1 -Overlap -Physics phased`
(or `normal` / `fixed`) for the bounded overlap/release route. It uses a separate
`overlap-fixture-2x1.bin`, exact coordinate input, and the existing read-only
object sampler. Check the result with `inspect_overlap_run.py RUN --bank 2x1
--expect phased` and `verify_physics_run.py RUN --reference REFERENCE_VARIANT
--modes phased`; use the matching mode for each run. Inspect both native PNGs.
Export a Phased result to `work/h4-forge-research/isolated/overlap-result.bin`
with `export_native_variant.py`, then use `run_native_check.ps1 -Mode reload
-Result overlap` for ordinary Slayer reload with read-only live-object sampling.
All paths, temporary files and captures stay inside this repository. The
intersection checker requires NumPy/SciPy from the existing repository toolchain.

### Base, Round and anchor storage

Anchor definitions are PC editor data, not map assets or saved-object fields.
`anchor_frames.json` describes reviewed H4-to-Reach coordinate adaptations;
`export_bindings.py` writes the private `isolated/markers.bin` table. C++ loads
that table and looks up each object by map ID and tag datum. This is currently
an explicit map-specific lookup, not automatic model discovery: a new/rebuilt
map needs updated bindings, even when it reuses a known piece. New geometry
needs a suitable anchor definition. No automatic cross-map identity matching
is claimed.

Base, Round's H4 flat face is at Y=-3.25 facing -Y, whereas the existing Reach
piece's flat face is at Y=0 facing +Y. Its construction radius is 5.5 rather
than 6. The adapter rotates 180 degrees, scales XY by 11/12 about the flat-face
center, and offsets Z by -0.1 to match the base. It preserves the original ten
anchors and H4 selection/alignment functions. It changes no `.map` geometry,
collision, physics or serialized variant format.

`check_base_round.py` feeds all ten raw/adapted anchors to the original bridge.
The raw set incorrectly snaps the opposed halves 0.350150 units away from
the intended origin; the adapted set closes the 0.1-unit starting gap to
within 0.0003 units and preserves the intended orientation.
`run_native_check.ps1 -Bank base-round` uses the known player spawn and the
Hemorrhage base location, then raises the process-local monitor for inspection.
Inspect both native PNGs and use `check_base_round.py --native-run RUN` to
check the released pair's poses in the ordinary H3 snapshot.
