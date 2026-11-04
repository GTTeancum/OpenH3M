# Sky Bridge performance attribution preparation

Sky Bridge from Halo Online; upstream H3 conversion by GeneralHeed / Priception,
Halo Online Map Pack For Halo 3:
https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190 . Original
individual creator unspecified. This project supplies the Xbox 360/OpenH3M adaptation.

The wait-attribution SDK patch was applied to the current dirty SDK tree with
--ignore-space-change. cmake --build work/rexglue-sdk/out/pacing-release --target
halo3mp --parallel 4 completed successfully. TEMP/TMP and outputs were confined
to this repository. No game process was launched. No desktop input or images
were imported. The executable and rexruntime.dll hashes stayed unchanged;
rexgpu-xenos.dll was rebuilt. The recorded GPU DLL hash is the new baseline.
The prebuild executable/runtime backups are in work/sky-bridge/wait-attribution-build;
the prebuild GPU DLL was not captured. Do not claim a controlled comparison
with old timing runs. Any new candidate comparison must use the same recorded
executable and complete DLL set and identical runtime settings.

The patch adds diagnostic caller labels only to existing optional wait logging.
It does not optimize anything yet. Required next measurement distinguishes
occlusion-readback, frame-reuse, resolve-synchronous, resolve-cache-miss, and
memexport waits. A static check finds those strings in the compiled GPU DLL;
this is not proof that each path has run.

Candidate 29 is staged privately under work/sky-bridge/payload-29. The existing
five BLF preview containers were copied byte-for-byte without image decoding or
viewing. Its map ID, mapinfo identity, header name, body XOR checksum and salted
header SHA1 pass. Existing release and installed payloads are unchanged.
No LIVE release was regenerated. Visual verification and performance correction
remain required; retain the full active goal.

The bounded-timing.py preparation step completed without launching a game.
Private copies of game assets and candidate-29 DLC, private user/profile/cache
paths, binary-hash guards, payload-hash guard, existing-process check, and a
170-second watchdog are ready. No symlinks/junctions point the game data outside
the repository. The first run uses a fresh cache and must be labeled cold.
Execution remains pending the user's answer about resuming tests after the
explicit handoff instruction to keep the game closed during deeper work.

Final emitted-program verification passed 48 checks: twelve screen and twelve
window programs in both the checkpoint and staged DLC map. Reconstructed debug
plus microcode bytes match audited compiler outputs and manifest SHA256 values
exactly; reflection names/types/slots and GPR counts match too. This closes the
gap between pre-import shader audits and the actual emitted cache. It does not
supply runtime appearance or performance evidence. No launch record exists for
the prepared timing run and no halo3mp process was running at this check.
The user's answer about resuming runtime testing is still pending.

## Authorized bounded runtime measurements

The user explicitly authorized resuming bounded text-only runtime tests.
Two candidate-29 runs completed and the watchdog closed each process within
171 seconds. No captures or desktop input occurred. Both logs contain Sky Bridge
autosave activity; this does not verify visible gameplay. The first wrapper
reported its expected TimeoutExpired after cleanup; the second catches that
expected watchdog exception. Neither exit code 1 is evidence of a game crash.

Synchronous occlusion, cold private cache: median observed interval 200.13 ms;
GPU sum 28.80 ms/frame; 3053 logged occlusion waits totaling 38.79 seconds in
the 110-165 second window. Async occlusion, reused shader cache: median interval
50.057 ms (about 20 FPS), p95 66.5 ms, GPU sum 33.568 ms/frame. No logged
occlusion waits; 1086 resolve-cache-miss waits for 1086 observed frames, median
21.134 ms. These runs share executable/DLL hashes but cache warmth differs.
Do not claim a controlled speedup or 30 FPS acceptance.

Next: distinguish resolve misses caused by missing buffers/size from pending
GPU submissions. Inspect guest feedback address/length and required completion
semantics before changing readback. Keep native exposure/bloom and actual GPU
visibility results. Simply disabling readback or fabricating samples is not a fix.
A logging-only quiet-visibility-query patch is prepared (not applied) because
16172 of 40395 first-run log lines were per-query begin/end chatter.
The actual visual fix and traversal/console performance remain unverified.

## Confirmed resolve-slot defect and correction

The resolve-miss diagnostic run found 1097/1097 measured misses at address
1FC24000, 8192 bytes, with existing mapped 262144-byte buffers. In every case
previous==current submission: repeated resolves to one address rotated both
slots within a single unsubmitted command batch and then waited on that batch.
This is not buffer eviction or insufficient allocation.

rexglue-sdk-resolve-submission-slots.patch reuses the pending write slot for
repeated copies in the same submission, in existing Fast/Some modes only.
Every GPU resolve and copy remains ordered and retained; the last copy wins.
The other slot preserves the prior submission's snapshot. Completion checks,
synchronous fallback for real misses, and Full-mode behavior remain unchanged.
No exposure/bloom processing, guest simulation or map formats are removed.
The wait is eliminated by retaining valid history, not by reading unfinished data.

Both before/after runs use candidate 29, the same warmed private cache, async
occlusion enabled, optional timing logs, and bounded stationary-spawn input.
Only rexgpu-xenos.dll changed for instrumentation then the slot correction;
full binary hashes are in resolve-slot-results.json. Build logs and original
DLL backups remain under work/sky-bridge/resolve-{diagnostics,slots}-build.

After correction: 29.961 observed FPS over 110-165 seconds; median 33.368 ms,
p95 33.92 ms, max 50.389 ms; 18 intervals above 50 ms. GPU median 29.0395 ms,
p95 30.535 ms. Repeated-current-batch misses: zero. One legitimate prior-in-flight
miss still waited 20.683 ms, demonstrating the fence guard remains active.
Before: median 50.0485 ms; all 1097 sampled frames waited, median 21.198 ms.
Both processes ended under 171 seconds. No game remains running.

This establishes stationary host performance improvement, not sustained traversal,
visual acceptance, original-console performance, or system-link verification.
The asynchronous setting is still explicit in tests, not installed as a new
default. The quiet-visibility logging patch remains unapplied, keeping that
variable constant. User visual-check availability has been requested because
this chat cannot import images. LIVE release replacement remains pending.

## Native-observer movement test

Authorized text-only 170-second diagnostic completed with 11 native hash passes,
zero hash failures, and expected Sky Bridge header validation. Source logs:
.local/loading-traces/20261103-171753-31936. No captures or OS input were used.
The existing process-local H3IR route strafed left, turned slowly, then attempted
forward movement. Native observer telemetry confirms 3.41 world units of local
planar movement and 198.39 degrees of cumulative yaw, not a full-map walkthrough.
Observer samples before 114 diagnostic seconds include the menu-to-game transition
and are excluded from movement distance. One partial-memory-read error at 109s
occurred during that transition; subsequent samples were valid.

Whole 110-165 runtime-second timing: median 33.363 ms, p95 33.747 ms, average
29.279 FPS. Do not claim sustained 30 FPS from this run. The largest 817.54 ms
interval coincides with initial map/autosave startup and a texture request;
it is retained in the whole-window statistics rather than silently discarded.
Two later hitches (283.56 and 184.01 ms) have explicit pipeline-completion waits
of 237.17 and 158.43 ms for shaders F66F20194CD3428E and 008997509E4D605D.
A repeat of the same route with its newly populated pipeline cache is warranted
before accepting steady movement performance. Eight real in-flight resolve waits
remain; no repeated-current-batch slot failures reappeared.

The observation test establishes native map validation and actual camera motion.
It does not establish panel appearance, native exposure/bloom correctness, audible
audio, console acceptance or network behavior. Human visual availability remains
pending; no LIVE release replacement has occurred.

## Warm movement repeat and private LIVE candidate

The identical process-local movement route was repeated with the existing cache
and unchanged binaries in .local/loading-traces/20261103-172254-27300.
Native validation passed 11 checks with zero failures and no observer errors;
camera movement was 3.40 world units with 198.50 degrees cumulative yaw.
Whole 110-165-second timing averaged 28.443 FPS, median 33.376 ms,
p95 34.029 ms, maximum 1735.132 ms. The largest interval coincided with
map/autosave startup. Two later 106.957/107.606 ms hitches had no matching
pipeline-completion event. The previous two large compilation waits did not
recur, but sustained 30 FPS is still not established. Ten legitimate prior
submission waits remain; zero current-unsubmitted-batch resolve failures.
See candidate29-movement-repeat-summary.json, including all retained samples.

A private LIVE candidate was built under work/sky-bridge/live-candidate-29.
Header/data/hash-tree verification passes (46148 data blocks, 275 hash tables),
and all seven packaged files exactly match payload-29. Signature validation was
not performed. The candidate is explicitly labeled as awaiting visual review;
the existing released package is unchanged. Builder: build-candidate-package.py.

The Halo 3 app now defaults asynchronous occlusion readback on only when the
setting source is default; an explicit override still wins. Real completed GPU
results and the backend's synchronous worker-start failure fallback are retained.
The narrow source snapshot is halo3mp-async-occlusion-default.patch; unrelated
preexisting app-header changes are not included. Build succeeded; new executable
SHA256 a90c7d1d10ec7833e58df4f72ba96a7c65ebab5567cd7ba1032b69f1dd0621ad.
Full before/after binary hashes and backup: work/sky-bridge/async-default-build.
This defaults change is host-only; it does not change Xbox 360 guest simulation.

## Native LIVE installation and default-setting validation

The bounded test .local/loading-traces/20261103-172701-30892 used the native
LIVE installer and rebuilt executable without any async-occlusion CLI override.
All seven extracted payload files match their source SHA256 hashes, all 11
native map/hash checks passed, and async visibility publication was observed.
Watchdog fired at 170 seconds; final hash summary at 170.329 seconds. The game
is closed. candidate29-live-default-summary.json records launch, binaries,
package integrity, installed files, and timing evidence.

Timing collection stopped at the default 155-second diagnostic endpoint, so
actual samples cover 110.009-154.970 seconds, not the entire requested 110-165
analysis range. Observed rate: 26.867 FPS; median 33.4395 ms, p95 50.209 ms,
maximum 1935.137 ms, 99 intervals above 50 ms. One real prior-submission wait
occurred; zero repeated-current-batch failures. This validates installation
and the default setting but does not establish sustained 30 FPS. Startup and
remaining frame pacing need further attribution. No visual/audio acceptance,
physical-console acceptance, or system-link verification is claimed. Human
visual feedback remains outstanding; final release replacement and goal closure
remain pending. No images were imported and no desktop input was sent.

## Visibility logging comparison

Previous turn made concrete progress: native LIVE installation and default-setting
validation. This turn isolated remaining startup versus later pacing and tested
the prepared visibility-query logging patch. analyze-pacing-windows.py reports
fixed 110-155, 115-155, and 120-150 second windows together; no outliers are removed.
The baseline's 120-150 second presentation calls all succeeded (1799 samples),
median 0.171 ms, maximum 1.219 ms. Observed and painted guest-frame counts both
advanced by 858, so repeated host refreshes were not new guest frames.

Applied rexglue-sdk-quiet-visibility-query.patch: Begin/End query INFO messages
become DEBUG messages only. Query writes, returned results, and guest behavior
are unchanged. Build passed. Before/after DLL hashes and backup are retained in
work/sky-bridge/quiet-query-build. The same native LIVE installation, package,
executable, cache, process-local menu route, and timing options were repeated.
Run: .local/loading-traces/20261103-173121-3152. Eleven native hash checks passed;
zero failures; process closed at 170.313 seconds. Zero INFO query chatter lines
remain (previous run had 82524). No capture or host input was used.

120-150 seconds: 29.937 FPS versus prior 28.620; p95 33.837 ms versus 50.112 ms.
115-155 seconds: 29.945 FPS, median 33.3675 ms, p95 33.852, max 50.491 ms.
Whole 110-155 seconds: 29.047 FPS, maximum 1368.307 ms startup hitch retained.
Two legitimate prior-submission resolve waits remain; zero current-batch failures.
This single sequential comparison supports retaining reduced query logging,
without claiming all performance variation is causal or traversal is verified.
Source and evidence: candidate29-before-quiet-pacing.json and
candidate29-quiet-pacing.json. Next independent verification is the same native
observer movement route with this quieter runtime, before visual acceptance.
The private LIVE candidate is still unreleased and the goal remains open.

## Remaining acceptance checks

Candidate 29's source-material and emitted-bytecode checks establish conversion
bindings, not the appearance of the affected panels. Human inspection must check
the framed indoor panels, outdoor courtyard panels, and left corridor from the
Slayer spawn: no opaque black replacement or bright vertical noise, authored
window transparency and screen illumination/animation, and normal exposure/bloom
while moving between indoor and outdoor areas. Also check audible game audio.
This chat cannot import images; a human text report is the required evidence.
Any remaining defect must be reported with location and behavior before promotion.
The private package is not an accepted release. Physical Xbox 360 performance
and system-link remain untested; host evidence cannot establish either.

Runtime reproduction uses the current patched SDK checkout described by
halo3mp/BUILD.md, which explicitly warns that build_host_runtime.ps1 does not
reconstruct the full current baseline. Do not use that older patch stack to
replace the working checkout. Preserve the small-resolve/occlusion baseline,
then resolve-submission-slots, quiet-visibility-query and the app async default;
optional timing patches supply evidence, not guest behavior. Builds and binary
manifests are preserved under work/sky-bridge. A later release handoff must
include runtime requirements: a DLC package alone does not install host fixes.

The older bounded-timing.py now accepts both recorded manifest formats and leaves
the async-readback setting unspecified by default. --async-occlusion and
--no-async-occlusion still allow explicit comparisons. Syntax and argument-parser
checks passed; this helper was not used to launch the current observer test.

## Quiet-runtime native movement verification

The prior turn was progress: it isolated query logging overhead and improved
stationary later-window pacing. The same movement/slow-turn route now completed
with the quieter runtime and async default, without an explicit async CLI flag.
Run .local/loading-traces/20261103-173519-8796 ended at 170.297 seconds;
11 native hash checks passed, zero failed, no observer errors, game closed.
All 19 runtime-manifest files matched before analysis. Observer samples confirm
3.397 world units of local motion and 198.387 degrees cumulative yaw. This is
still a short local route, not full-map traversal or visual verification.

Full 110-165 runtime seconds averaged 28.579 FPS, retaining startup. Fixed later
120-150 window averaged 29.886 FPS, median 33.363 ms, p95 33.827 ms, maximum
84.547 ms. 115-155 window averaged 29.708 FPS. Five genuine prior-submission
resolve waits remain; zero repeated-current-batch failures and zero INFO query
chatter. Largest later hitch contains deferred-commands=44.880 ms and enclosing
output-refresh=46.694 ms; these overlap and must not be added. A second
81.279 ms interval contains several slower deferred-command submissions.
Next performance investigation should attribute time inside deferred-command
execution rather than repeating the same unchanged route or suppressing real
fence waits. Evidence: candidate29-quiet-movement-summary.json. No sustained
full-map 30 FPS, visual/audio acceptance, console, or network claim is made.

## Deferred-command diagnostic and non-reproduction

Previous turn was progress: movement confirmed and a remaining 44.880 ms
replay batch localized. Added optional per-command wall-clock timing under
existing d3d12_log_present_timing, with logging only after batches >=5 ms.
No graphics command or ordering changed. Normal play does not take per-command
timestamps. Narrow SDK snapshot: rexglue-sdk-deferred-replay-timing.patch;
reverse-apply check passed against the live source. Build passed; GPU backup,
log, and binary manifest: work/sky-bridge/deferred-timing-build. Numeric command
IDs are captured from the matching enum in deferred-command-ids.json.

Same authorized native movement route, .local/loading-traces/20261103-174001-9228:
11 hash checks passed, no failures or observer errors, 3.408 world units local
motion, 198.497 degrees yaw. Process ended at 170.297 seconds and is closed.
Full 110-165 window averaged 29.934 FPS; 110-155 averaged 29.926 FPS, p95
33.736 ms, maximum 66.588 ms. Later 115-155 averaged 29.958 FPS, p95 33.728,
maximum 50.497 ms. No replay batch >=5 ms was logged. The previous slow batch
did not reproduce, so this does not identify a defective D3D call or justify
changing draw/barrier behavior. Instrumentation and run variability prevent
attributing this improvement to the diagnostic itself. Keep the probe available
for recurrence; avoid repeated unchanged tests or speculative graphics changes.
See candidate29-deferred-diagnostic-summary.json and analyze-deferred-replay.py.

This establishes near-30 host timing over a bounded local movement route, not
full-map visual/traversal acceptance. Human text feedback has been requested
for the panels, animations and exposure. Candidate remains unreleased; no
change to the existing LIVE release or goal closure. Audio, physical console
and network verification remain outside the evidence gathered so far.

## Human playtest preparation and acceptance audit

human-playtest.ps1 validates all 19 runtime files and seven candidate payload
files against the tested manifests before doing anything. Preparation completed
successfully without -Run and started no process. -Run uses the existing native
trace helper in manual-input mode: no replay, no captures, no timing-instrumented
command replay, original user controls, private repository-local profile/cache,
and a 170-second watchdog. The user selects Custom Games, Sky Bridge, Slayer.
This is ready for the pending human-availability answer; do not launch repeatedly
without an observer or infer visual acceptance from silence. Payload bytes are
identical to those already tested through native LIVE installation.

candidate29-acceptance-audit.json checks the full objective against current
artifacts, including current container SHA256, emitted-program evidence, and
latest native motion/hash/timing results. Completion is not proven: affected
visuals and broader human traversal remain unverified, and release promotion
waits for that acceptance. The goal remains open. The previous turn made
progress through a new diagnostic and non-reproduction evidence; this turn
prepared the concrete manual check and recorded the remaining acceptance gap.
No further unchanged unattended launch is warranted while awaiting that input.

## First manual playtest attempt

User explicitly reported readiness for a bounded human playtest. Ran
human-playtest.ps1 -Run after its runtime/payload hash validation. No replay,
OS input, captures, or image inspection. The child exited with code 0 at
75.890 seconds, before the watchdog. Trace observed mainmenu/shared/zanzibar,
six successful native hash checks and zero failed hashes, but no Sky Bridge
header validation. The helper correctly rejected this as an incomplete target
map test. This is not evidence of a Sky Bridge crash, panel acceptance, or a
failed native hash. No game remains and no automatic relaunch was attempted.
Run: .local/loading-traces/20261103-182842-4264. Evidence:
candidate29-human-attempt01.json. Asked the user whether they closed it, could
not find/load Sky Bridge, or saw an unexpected exit; explanation pending.
Release remains unchanged and the goal is not complete.


## Shared installation correction (supersedes isolated human launcher)

User confirmed closing the first manual attempt before reaching Sky Bridge.
Coordination from the Battle Canyon chat conveyed the explicit user correction:
these maps must not be separate installations, and human play must have no
control harness. The isolated manual-launch route is superseded.

Added candidate 29's seven native-installed files and 332-byte native content
header to work/dlc/installed-corrections, alongside the existing combined map
bundle. Every pre-existing content/header hash was checked before and after;
Battle Canyon remains 3de8ee1d1a18b76b5a7306aac087d3ae267bd6897df440afff30dbc46883a585.
Existing maps, saved content, cache, bootstrap settings, and runtime are preserved.
Sky Bridge is a shared testing candidate, not a visually accepted final release.
Normal OpenH3M.bootstrap.toml already points to this shared content/cache.

The human launcher now starts only the normal C:/X360/ISOs/H3M/OpenH3M.exe,
with no debugger, observation, replay, scripted input, captures, or isolated
content/profile. The user controls from startup. Its bounded shutdown remains
170 seconds. Preparation validates map coexistence and starts no process.

Seven installed runtime files differ from the tested runtime bundle. Verified
rollback copies and staged replacements are ready inside work/sky-bridge;
installed runtime and bootstrap are untouched. Explicit permission for replacing
the seven files outside the repository has been requested under the user's
repository-confinement instruction. Launcher refuses a performance playtest
until those runtime hashes match; it must not substitute a separate install.

Coordination evidence for the Battle Canyon owner:
work/sky-bridge/shared-install-coordination.json (latest live record), with a
tracked snapshot shared-install-coordination.json here. It includes protected
file hashes, added content/header, runtime comparison, rollback/staging paths,
and pending status. No game was launched during reconciliation. Menu coexistence
still requires normal-launch observation; filesystem coexistence is verified.

## Authorized shared runtime installation

User explicitly approved replacing the seven shared runtime files after the
reason and outside-repository scope were explained. Rechecked that no game
process was running, all installed runtime hashes still matched the recorded
baseline, every staged file matched the tested build, and all rollback files
matched the original installed versions. Replaced the seven targets under
C:/X360/ISOs/H3M using per-file atomic replacement from repository staging.
All seven resulting hashes match the tested bundle. The existing bootstrap
hash is unchanged; all recorded prior content/header hashes and candidate 29
payload hashes remain unchanged, including the protected Battle Canyon map.
No saves/cache/settings were written and no game was launched. The shared
manual launcher preparation check passes. The latest coordination JSON records
the applied state and backup location. Normal OpenH3M now uses the tested
runtime with the common installed map tree; visual/menu acceptance still awaits
the user's normal manual playtest. Goal is not complete.


## Restarted goal: widespread non-colliding cards remain

User supplied six new screenshots and reports widespread striped and solid-black
cards without collision; map otherwise seems generally fine. This is negative
visual acceptance for candidate 29, not approval to promote it. User accidentally
deleted the goal and explicitly requested restart; the full correction,
performance, verification and shared LIVE deployment objective is active again.
The supplied attachments are now explicit evidence; no other images or source
chats are imported. Human launch remains shared, manual and untimed by default.

candidate29-renewed-card-feedback.json records each supplied view and initial
material candidates. Current source also preserves HO/MCC instance bit 6 as an
opaque flag; its native effect is unproven. Investigate geometry/material
membership and transparent light-volume/decal paths as well as render flags.
Do not hide all non-colliding geometry or assume these are portals. Existing
screen/window shader audits proved binary bindings, not correct rendering;
the user's new observations supersede any implication of visual success.

## Complete mesh-part and blend-mode audit

Previous turn made progress by restoring the goal and recording the new human
failure report. audit-card-blends.py now reads actual source/target BSP material
bindings and compares all fields of all 2116 parts across 485 lightmap meshes.
Every part field matches exactly, including render method slot, sorting index,
index range, subparts, part type and flags. This narrows the investigation but
does not establish identical runtime interpretation of every flag.

Eleven used materials have different Blend Mode values (postprocessing +0x68):
source nonzero -> target opaque zero, affecting 40 parts. They are puddles,
two settlement_pipe_small_water materials, four sbr_window_02 variants and four
sbr_decals materials. The water cards also lost their authored self-illumination
profile through generic metal fallback. These are concrete conversion losses;
mesh-to-screenshot attribution is still needed. Merely changing the blend field
is insufficient because the selected native pixel programs and option bindings
also differ. Next implementation must preserve the actual source profiles and
transparent-pass behavior, using stock native interfaces where available.

Evidence: card-blend-mismatches.json; full named source/target parameter audit
in work/sky-bridge/card-material-geometry-audit.json. The latter was saved
successfully before an optional display formatter encountered unnamed cloned
templates; the committed audit handles those without assuming tag names exist.
The independent sbr_window_glass_01 material uses 36 opaque parts in both source
and target, so its name alone is not grounds to force transparency. Light-volume
part types and flags also match source. No installed data or runtime was changed,
no game was launched or controlled, and no image was imported by a tool.


## Candidate 30: authored additive water cards

Previous turn established eleven blend losses. Source rmdf categories now prove
both settlement_pipe_small_water materials use two_detail_overlay, detail bump,
from-diffuse specular mask, two-lobe Phong, dynamic environment, from-albedo
self-illumination, and additive blending; distortion/soft-fade are disabled.
They use rain-drop and pipe-mask textures with five/ten animation functions.
Stock inventory found no exact template in 25 readable tagged maps; Salvation
provides the close native _6_2_0_1_2_2_0_0_0_0 donor. shared.map is a resource
cache and cannot be read as an ordinary tagged map by this reader; its parse
error is retained, not reported as an empty tag inventory.

Compiled 13 Xbox 360 pixel programs; donor consumes 12. All donor input
signatures and fixed-register comparisons pass. Added persistent b0/c12
bindings are independently proven against Salvation's native transparent/
emissive template 74, including absence from material/external route uploads.
All 150 named animation consumers are audited; no animation was specialized
away. Scoped binder and opt-in OPENH3M_SKY_WATER_CARD_SHADER_DIR dispatch are
implemented. Dirty importer edits are captured as a narrow integration patch.

Candidate 30 built successfully after correcting a JSON int/string-key audit
comparison (first build stopped before output). Both emitted materials have
exact source constants, booleans, sampler controls, function bytes and all
50/100 remapped animation routes; additive blend is restored. Twenty-four
emitted shader payloads, reflection tables and GPR counts match compilation.
Candidate SHA256: 75afb6db7e220f43805f65afa70246d06482dfb4f5c4f3d5ec88bc2fe282aae7.
Artifacts and reproducible tools: ../sky-bridge-water-card-shaders. This addresses
eight parts; nine other blend-mismatched materials remain. The framed stripe
surfaces still need geometry attribution. Candidate 30 is not installed,
packaged or visually accepted. Shared installation and the user's running game
were not changed; no images were imported, and no game was launched/controlled.


## Candidate 32 package and manual playtest

Candidate 32 corrects the eleven established material blend mismatches. Full shader/material evidence is in ../sky-bridge-remaining-window-shaders. The private LIVE container 232B0F442A3DF5C347F2E59D16AF5FB6E4E5D4BD passes header/hash-tree/data verification and all seven files match payload-32. SHA256: 3e450c34cb08a223df33c26077bf7b5ba6466817236e5a3f15b8f1540b3ecd8c. Signatures/physical console/system link are not verified.

The other chat reported research-only activity and no concurrent shared writes. Only Sky Bridge's existing installed map was replaced, preserving its menu entry/content directory and all 92 other content files. Runtime and bootstrap hashes are unchanged. The old Sky Bridge map alone is backed up in work/sky-bridge/candidate32-install-backup. No Battle Canyon assets were copied, restored or combined into this package. Its reported rejection/cleanup plan supersedes treating the earlier preservation inventory as acceptance; coordinate before future writes.

The normal shared game was launched for manual review, with no input harness, capture, or shutdown timer. Timing logs are enabled in the repository and are not an automatic stop timer. human-candidate32.ps1 validates only unless passed -Run. candidate32-human-launch.json records the initial PID and log path; revalidate the process instead of treating this record as proof it remains live. A user report on indoor streaked panels, hanging black cards, corridor rectangle, window transparency and screen animation is pending. Neither launch nor successful structural checks establishes visual acceptance.

Attribution: Sky Bridge from Halo Online; upstream H3 conversion GeneralHeed / Priception, Halo Online Map Pack For Halo 3, https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190 . Original individual creator unspecified; this project supplies Xbox 360/OpenH3M adaptation.

## Numeric probe and saved reproduction view, 2026-11-03

The user confirmed that the surface flickered during the second recording.
`candidate32-pixel-probe-result.json` records 300 complete 144-point GPU sample
grids and 2122 emitted candidate draws. No sampled point showed a black pulse.
This is an unresolved coverage/stage limitation, not a negative reproduction
result. The material draw states do not establish a rendering cause.

The user cannot remain available for repeated manual tests and requested saving
the player vectors and coordinates for unattended repetition. `save-live-view.py`
captured the existing process at a verified native frame entry, restored its
single debugger breakpoint, and detached without changing guest state. The
private snapshot is under
`work/sky-bridge/pixel-probe-20261103-203123/reproduction-view-full/`.
It includes full player/Mongoose records, observer state, map variant, and bounded
TLS blocks. No host input, window control, screenshot or image capture was used.

`candidate32-flicker-reproduction-view.json`, produced by `decode-live-view.py`,
contains the portable pose. The seated player's position is relative to its
parent node; the Mongoose world position is (16.75514984, 69.34661102,
-0.43672475). Camera position (16.41066551, 67.99089050, 0.30618051) exactly
matches the recorded GPU draw constants. Forward/up bases pass normalization
and orthogonality checks. Do not copy raw pointers or object handles into a new
session, or describe this diagnostic snapshot as a complete save state.
Unattended replay has not yet been validated.

The finished diagnostic session was closed after the snapshot. The original
shared GPU DLL was restored and SHA256 verified as
979f402022ec045b0ff319f396e34cd04b0a049458e2b55e83456b25709caace.
No new rendering fix or release promotion occurred. The correction goal remains
open. Attribution is unchanged from the source credit above.

## Unattended reproduction harness

`sky_reproduction.h` is an opt-in diagnostic, included by video_quality.cpp.
It requires an exclusive process-local input replay, the Sky Bridge map, and
a pose directory confined to this repository. It moves fresh native objects
through 8232E8B8, turns toward the Mongoose using measured camera feedback,
and holds the game's RB state until native seat attachment is verified.
Simulation, lights, weather and animation continue normally. It never sends
host input. `write-reproduction-pose.py` regenerates pose.bin from the saved
JSON; `run-reproduction.ps1` launches a private seven-file runtime with a
180-second watchdog and only payload-32 exposed as custom content.

Source tracing corrected the observer allocation: 82213440 allocates 3880
bytes at TLS+0x2cc; 82098CD0 returns user 0's result at +0x110 (user stride
968). The old TLS+0x25c/+0x1cc reader reached the same address through an
adjacent allocation in the human recording. The preserved snapshot proves
both routes resolve to 0xa5f0109c, so the captured vectors are valid. Updated
capture/decoding tools use or validate the proper allocation. Other projects'
older diagnostic readers have not been modified by this work.

The early ptag hook did not restore the actual rendered camera: reproduction-03
seated the player but all 1725 candidate draws retained a different default
vehicle view. That recording is rejected as a reproduction of the human view.
The harness now overrides the observer result after 8213BC50 finishes both
82213198's basis update and 822136F0's collision adjustment. Every new recording
must pass `check-reproduction-camera.py`, which compares all candidate draws'
camera/projection constants against the human recording. Camera equality does
not establish that the flicker itself has been reproduced.

The original 16x9 full-frame grid geometrically intersected mesh 183 at only
two points and mesh 184 at one. `trace-sample-coverage.py` uses the actual
vertex-program transform and triangle lists to measure this; visibility and
occlusion remain separate questions. The probe now accepts an explicit region;
the harness concentrates its 144 samples within (0.54,0.255)-(0.93,0.425).
A native D3D12 WARP fixture verified all 144 coordinate-coded values for a
non-default region, fence-completion behavior, and the existing recording
limit. The probe still produces numeric data only, before presentation
gamma/FXAA. No image or desktop capture is involved.

`candidate32-unattended-reproduction-result.json` records reproduction-04:
all 1763 attributed material draws across 300 frames match the human camera
and projection constants bit-for-bit. Native seating succeeds; suspension
settling leaves a measured 0.0235-unit vehicle-position difference. The final
vehicle orientation and complete simulation state are not independently matched.
The process completed its bounded recording and closed at the 180-second
watchdog. Shared runtime files were not replaced by these private tests.

The denser probe records 43,200 values across 300 complete frames, covering
20 candidate-mesh-183 points and 45 candidate-mesh-184 points geometrically.
No point crosses the defined near-black threshold; the largest one-frame
max-RGB decrease is 0.13783 at pixel (720,193), frame 2920. This verifies the
repeatable viewpoint and improved coverage, not a reproduction or explanation
of the reported black flicker. Keep the correction goal open and trace the
bad frame/stage before applying any rendering change. Billboard readability,
visible outdoor rain, and final performance acceptance remain unverified.

## Per-draw and final guest-output numeric probes

`candidate32-stage-probe-result.json` records private reproductions 05 and 06.
Both reproduce the saved camera/projection exactly in all 1762 attributed
draws across 300 frames. The player is seated natively; simulation continues.
The original shared GPU DLL remains restored and hash-verified. Both private
games closed under their 180-second watchdogs. No further manual positioning
is needed for this view.

`sky_stage_probe.h` records sixteen isolated color-0 values immediately before
and after the identified albedo, static-lighting and dynamic-lighting draws.
Each run produced 56,384 values with complete before/after pairs. All sample
identities match the CPU draw trace's sequence, frame, shader and index count.
The decoder checks incomplete pairs, mismatched resources and nonfinite values.
Values are raw render-target channels, not necessarily final colors. Unchanged
values alone do not prove a draw invisible or a pass inactive.

The optional second pixel probe records 144 numeric values after host gamma
and FXAA into `presented.csv`. This is the native guest-output resource before
presenter scaling and desktop composition. Run 06 recorded 43,200 complete
values at each stage; their frame, coordinate and submission keys agree.
No screenshot, image import, desktop capture or host input was used.

The source patch is `sky-stage-probe-integration.patch`, applied after the
existing numeric pixel-probe integration. Use `git apply --ignore-space-change`
for the SDK's mixed source line endings; a scratch application reproduced all
three current SDK edits exactly after newline normalization. Copy `sky_draw_trace.h`,
`sky_pixel_probe.h` and `sky_stage_probe.h` into the SDK's D3D12 source folder.
The launcher enables these additions only with `-StageProbe` and
`-PresentedProbe`; all output stays inside the selected repository run folder.
The stage probe stops after 300 frame IDs, 15 seconds or 100,000 written rows;
pending fence-complete records can drain afterward. The two final-output
probes retain their independent 300-frame/15-second bounds.

Native D3D12 WARP fixtures verified all 32 coordinate-coded RGBA16F values
across the stage probe's two phases, and all 144 RGBA8 values from the final
output probe. Both check that readback waits for completion and stops at the
frame limit. Stage closure was specifically tested after CPU tracing becomes
inactive. The final-output fixture also checks the independent output file.
Build and fixture artifacts remain under
`work/sky-bridge/stage-probe-build/`. The viewport coverage analysis now rejects
unsupported live viewport/scissor mappings instead of assuming screen mapping.

Twelve of thirteen mesh-184 albedo points changed by that draw have bit-stable
post-draw RGB across 299 complete albedo frames. The other point, (720,193),
varies. Its static-pass dips at frames 3016, 3079 and 3166 in run 06 survive into
the same-frame final guest output, but remain above black. No fixed sample
meets the defined near-black pulse threshold. These observations do not yet
reproduce or explain the user's regional black flash; no rendering change or
release acceptance follows. Per-draw copy barriers can affect timing, and
sparse coverage or a differing simulation state may still conceal the symptom.

Re-run analysis with `check-reproduction-camera.py`, `read-stage-probe.py`,
and `read-pixel-probe.py`. For `presented.csv`, supply
`--stage after_host_effects`. Next trace the varying point through preceding
depth/geometry writes and improve coverage of the reported region before
altering rendering. Billboard readability, visible outdoor rain and final
performance acceptance remain pending. Source credit is unchanged above.

## Full-region numeric coverage and human-recording comparison

`candidate32-region-probe-result.json` records reproductions 07 and 08. The
new `sky_region_probe.h` reads every texel in the native guest-output region
x=[518,1152), y=[64,320), after gamma/FXAA. Arrays remain in process memory;
only 32 aggregate tile rows per frame and each tile's largest isolated change
are persisted. There is no image file or desktop capture. Both runs contain
300 complete frames and 48,691,200 pixel contributions. The per-draw stage
probe was disabled for these runs. Both private games exited at 180 seconds;
the shared runtime and installed map remain unchanged.

The fixture `sky-region-probe-gpu-test.cpp` uses native D3D12 WARP with a known
16-pixel black patch for one frame, recovery, and a deliberate missing frame.
All 800 pixel contributions and the exact region partition pass verification;
the missing frame resets temporal history. Fence and frame-limit checks pass.
The fixture and build evidence are under `work/sky-bridge/region-probe-build/`;
`sky-region-probe-build.json` records hashes and thresholds. Apply
`sky-region-probe-integration.patch` after the stage-probe patch, and copy the
new header into the SDK D3D12 source folder. The launcher adds `-RegionProbe`.
`read-region-probe.py` validates the recorded tile partition and temporal IDs.

No pixel within the measured region reaches the near-black threshold in either
private run. In the right subregion x=[756,1073), y=[128,256), the greatest
isolated max-channel decrease is 10/1023; no pixel meets the larger fall/pulse
threshold. Larger changes occur farther left. This means the changing sample
at (720,193) is insufficient evidence for the reported circled flash. Its
albedo and static-lighting draws sometimes write the pixel and sometimes leave
it unchanged despite stable position-producing constants and reflected albedo
constants/sampler descriptors. Earlier depth/geometry writes and actual texture
contents remain unmeasured; no defect is attributed to those stages yet.

Run 08 uses `-PixelRegion '0,0,1,1'` to restore the original human recording's
144 sample coordinates. `compare-pixel-recordings.py` compares decoded RGB
distributions at identical coordinates. Ten upper-right points have overlapping
RGB ranges and at most 12/1023 median-channel difference. Lower-body/player
points differ more, so this is not a claim of identical simulation state or
full visual equivalence. Camera/projection checks pass for all 1762 attributed
draws in run 07 and all 1761 in run 08, across 300 frames each.

The user's confirmed flash remains unresolved. The next unmeasured stage is
the application's native presenter: scaling/sharpening, final UI composition,
then the swapchain back buffer. Its existing paint-submission fence provides
an observation point before RTV-to-PRESENT in d3d12_presenter.cpp. Extend
numeric statistics there without desktop capture; do not infer a renderer fix
from the absence of the symptom in these private runs. Source credits and
remaining weather, billboard, performance and final-promotion requirements
remain unchanged.

## Application presentation and saved-profile replay

`candidate32-presenter-probe-result.json` records runs 09 and 11. Each contains
300 guest frames and 899 consecutive application paint submissions. The new
swapchain observation covers every texel in x=[576,1280), y=[72,360), after
scaling/sharpening and application UI composition, before DXGI Present. Its
182,274,048 pixel contributions per run contain no isolated near-black pulse.
The right-side tiles have no qualifying falls or pulses. This does not explain
or invalidate the user's confirmed flash; desktop composition is unmeasured.
The swapchain recordings contain 451 and 450 distinct aggregate frames,
respectively; their output changes during recording rather than remaining
stale. This is not a claim that the animated content is visually correct.

All 1761 attributed draws in run 09 and 1759 in run 11 match the saved camera
and projection exactly across 300 frames each. A separate full-history check
of the original human trace found one camera/projection matrix across all
1660 attributed draws and 300 frames. This verifies repeatable positioning,
not a complete simulation-state restore. The player enters the Mongoose using
native process-local controls; no further manual positioning is needed.

Run 11 seeds private copies of the original 272-byte and 304-byte title-specific
profile settings. The new `-ProfileSeed` option accepts the source `profile/User`
directory; the harness copies only `63E83FFE` and `63E83FFF`, validates repository
confinement and records their hashes. It does not copy saved layouts or other
DLC. The profile-only replay also contains no measured black pulse. Original
profile settings and shader-cache hashes remain unchanged.

Run 10 attempted both the original profile and full shared shader cache. The
native log reports 1500 graphics pipelines created in 84731 milliseconds before
input replay began. Sky Bridge header loads succeeded, but the 180-second
watchdog expired before the view settled. No probes armed; this attempt provides
no symptom result. `compare-shader-caches.py` instead confirms that all 278
replay shader programs and 304 pipeline descriptions are byte-identical to
entries in the larger original cache. Extra cache entries and compilation
timing differ; cache equality for common entries does not prove identical
runtime behavior.

Apply `sky-presenter-probe-integration.patch` after the existing region patch,
and copy the updated `sky_region_probe.h` into the SDK D3D12 source directory.
The presenter is linked into **rexruntime.dll**, so rebuild it as well as
rexgpu-xenos.dll. Both new integration patches, including
`sky-profile-seed-integration.patch` for the loading harness, were applied in
repository-local scratch trees and reproduced the current sources exactly
after newline normalization. The generic loading harness has unrelated work;
only its narrow profile-seeding patch is committed here.

The launcher enables the final-buffer probe with `-SwapchainProbe`.
`read-region-probe.py --swapchain` validates its output. The probe uses the
existing paint fence, eight readback slots and a limit of 900 paint submission
IDs or 15 seconds. It writes 32 aggregate tile rows per submission, including
format, dimensions and monotonic timestamp. Pixel arrays remain in process
memory. Native WARP fixtures verified the known 16-pixel black flash, recovery,
frame-gap handling and readback completion for R10G10B10A2, RGBA8 and BGRA8.
Build and fixture evidence is recorded in `sky-presenter-probe-build.json`.
Instrumentation can affect timing; these runs are not performance acceptance.
Both games closed at their 180-second watchdogs. The shared GPU remains restored
and hash-verified; no rendering fix or release promotion was made.

The next comparison must examine native environment/effect state and elapsed
gameplay time, plus the original versus diagnostic runtime changes. Do not
change lighting, shaders or visibility without a measured bad frame.

`candidate32-weather-dependency-result.json` traces the authored outdoor rain:
source atmosphere 7596 references weather effect 7598, converted to atmosphere
10699 and effect 10701 with valid particle, shader-template and bitmap references.
Both particle emitters retain the Tube shape. Source flags 0x4800 become 0x0800
because bit 14 is the MCC enhanced-graphics near-fade option. Bit 13, the weather
GPU-occlusion flag, is absent in both source systems. This conversion difference
does not establish a weather defect. The map is authored to have outdoor rain;
visible particle behavior remains unverified. Billboard readability and final
visual/performance acceptance also remain pending. Source: Halo Online Sky
Bridge via GeneralHeed / Priception's [Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190).
The original individual map creator is unspecified; this project provides the
Xbox 360/OpenH3M adaptation.

## Native state and later recording window

`candidate32-native-state-result.json` records runs 12–14. The replay reaches
the seated view at 7.5 gameplay seconds. The original human recording's file
timestamps and later saved game clock suggest a window around 22.9–33.2
gameplay seconds, assuming continuous simulation between recording and snapshot.
That estimate is not a game-clock measurement at the reported bad frame.

`-ArmDelayMs 15000` moves the replay's recording start to 22.5 gameplay seconds.
Run 13 then captured 300 guest frames and 899 paint submissions, with all 1762
attributed draw cameras exactly matching the human recording. No measured
pixel in the stated region reached near-black, and no qualifying fall occurred
in the right-side tiles. This later window still does not reproduce the flash.

`sky_state_snapshot.h` saves one bounded, versioned native-state snapshot before
arming the probes. It uses the existing hook in `video_quality.cpp` at native
function entry `0x82160F28`, matching the original human snapshot. An initial
run captured at observer update instead: its TLS context differed, so run 12's
effect-table differences must not be treated as a renderer-state comparison.
Runs 13 and 14 use the matching entry. `compare-native-state.py` validates the
file trailer and compares portable fields; it never restores pointers or data.

All 450 object identities and 447 transforms match. The three differences are
the moved Mongoose, seated player and attached weapon. Native variant counts
match; its object-row difference is confined to row 2, plus metadata bytes.
The source and private runtime's driver-seat-power values are both enabled
and 1.0. Native `sub_820F99E0`, the retail string table and the vehicle attachment
definition identify that value as the Mongoose headlight control.

Run 14 uses the original GPU/runtime DLLs and captures complete effect, light
and particle tables, plus full biped/vehicle bodies. `inspect-native-effects.py`
checks nonzero salt rows against the table count and validates tag references.
Weather effect 10701 occupies effect slot 376 and is referenced by particle
system slots 155 and 156. This establishes native weather instantiation; GPU
emission and visible rain contribution remain unverified. The older human
snapshot contains only four complete light records and one partial record,
so its additional light allocations cannot be identified from that payload.
Differences in later light/particle counts do not attribute the flash.

Each run closed under the 180-second watchdog. Snapshot payload is bounded to
16 MiB; all bytes stay inside the private repository run. No image, desktop
capture, host input, shared-runtime write or rendering correction was made.
Next broaden numeric coverage beyond the current region while reducing the
number of enabled probe stages, preserving the exact view and measured start
time. Billboard readability, actual rain rendering, lighting flicker and final
visual/performance acceptance remain open. Source credits are unchanged above.

## Full viewport and native observer input

`candidate32-full-viewport-result.json` records runs 15–17. The launcher now
supports `-RegionOnly -FullViewport` with exactly one of `-RegionProbe` or
`-SwapchainProbe`. This disables the CPU draw and isolated-pixel probes and
measures every texel of the chosen game-owned output buffer. Each run writes
its diagnostic configuration before launching; it refuses existing evidence.

Run 15 recorded all 300 guest frames at 1152×640, totaling 221,184,000 pixel
contributions. Run 16 recorded 862 application paint submissions at 1280×720,
totaling 794,419,200 contributions before its 15-second recording limit.
Neither has missing frame IDs or incomplete tiles. Near-black pixel counts
remain 131 and 113, respectively, and there are no isolated near-black pulses.
Relative brightness falls do occur and remain in the report. Their presence
does not establish a rendering defect; absence of near-black pulses does not
invalidate the human report. Desktop composition is outside these probes.

The earlier replay overwrote the final 112-byte observer result. The saved
native snapshot exposed a concrete difference: the final camera matched, but
the preceding native command still faced along the vehicle. The new optional
`-NativeObserver` mode writes 64 numeric command bytes before `sub_82214BC0` and
leaves the final result to the native basis, collision and BSP-location code.
`write-observer-command.py RUN` extracts those inputs. It resolves TLS+0x2cc
against the actual captured allocation; the old human observer blob starts
188 bytes before it. No saved pointers or object handles are restored.

Run 17 verifies that native computation recreates the recorded position,
orientation and projection exactly: all 1759 attributed draw matrices match
across 300 frames. Its 300 full guest-output frames again contain no isolated
near-black pulse, with a constant 131 near-black pixels. This is repeatable
positioning, not reproduction of the reported defect or performance acceptance.

`compare-native-observer.py` also exposes a remaining difference. Six result
words at camera+0x10 through +0x24 are zero in the human snapshot but nonzero
in run 17. `82214BC0` reads their inputs at user+496 and user+536, negating the
first triple. The numeric command override occurs after preceding native
interpolation, so it does not align these motion-related inputs. The next
trace should follow `82214930` and the subsequent native update stages before
claiming complete observer-state equivalence. Do not treat a matching camera
matrix as proof that all view-dependent simulation state matches.

All three processes closed under their 180-second watchdogs. The shared GPU
DLL remains restored and hash-verified; no production renderer or map changed.
The player/vehicle coordinates, basis vectors, camera and native command remain
saved for unattended tests. No further manual positioning is required.
Source credits are unchanged above; this is the Xbox 360/OpenH3M adaptation.

## Native interpolation and late rendering events

`candidate32-late-render-event-result.json` records runs 18–19. Source tracing
of `82214930` and its caller identifies the current command at user+380, target
at user+12 and difference output at user+912. The saved human target equals its
current command. `-NativeObserver` now supplies that numeric target before
native interpolation, guarded by all three user-0 pointers and seat ownership.
It no longer overwrites the interpolated command at `82214BC0`.

Both new snapshots match the entire saved 112-byte observer result and the
64-byte current/target command exactly, including the previously differing
motion triples. All attributed draw camera matrices also match: 1754 draws in
run 18 and 1757 in run 19, each spanning 300 frames. Native collision/location
calculation still runs. The three object-transform differences remain, so this
is not a complete native savestate restore.

The full-viewport measurements also contain relative brightness drops that
the near-black threshold does not capture. `trace-sample-coverage.py
--region-events RUN/region.csv` checks their coordinates against the actual
traced triangles. Run 18 contains 695 distinct worst-change coordinates;
43 overlap mesh 183 and 14 overlap mesh 184. This establishes geometric
coverage, not visible ownership or correspondence to the human-circled area.

Run 19 samples the observed coordinates around candidate draws and a 16×9
numeric patch covering (714,210) at the final guest source and after host
gamma/FXAA. No image is saved. The updated 16-point stage probe passed its native
WARP fixture: all 32 coordinate-coded values across both phases were exact;
premature read and frame-cap checks passed. Its actual recording contains
1757 complete paired draws, 56224 samples and no missing point sets or nonfinite
values. Both final-output probes contain 300 samples at the selected point.

`trace-correlate-point.py RUN` joins frames directly. At (714,210), final output
drops for one frame at 3435, 3499, 3559 and 3615, separated by 64, 60 and 56 guest
frames. Peak channel values fall to about 59–61% of the darker neighboring
frame. Every sampled candidate albedo/static/dynamic before/after color at that
point is constant across the entire recording. The final guest source already
contains the change before host gamma/FXAA. This bounds the measured change to
later guest rendering or resource/resolve work; it does not identify its cause
or prove it is the exact black flash reported by the user.

Next trace later color-target changes at this point with shader/resource
identity and draw order, including resolve/postprocessing boundaries. Do not
infer a material or lighting correction from the negative near-black tests.
The shared GPU and installed map hashes remain unchanged; both runs ended at
their 180-second watchdogs. No performance or visual release acceptance is
claimed. Billboard readability and visible outdoor rain remain open. Source
credits are unchanged above.

## Later-draw attribution and paired water measurements

`candidate32-water-pulse-attribution-result.json` records runs 20–21. Both
replay snapshots again match the complete human observer result and command.
The player/vehicle coordinates and view vectors remain saved for unattended
reproduction; no further human positioning is required. This is still not a
complete savestate: three object transforms differ slightly.

`-LatePassProbe -StageProbe` samples (714,210) after supported color-0 draws
and records all shader identities with compact register deltas. Run 20 records
852956 submitted draws across 300 frames. Its point probe reaches its row cap
after 172 frames, with 403766 completed samples, 4270 busy observations and
2567 unsupported targets. Pending readback slots can complete after the row
limit. This is incomplete discovery coverage, not a claim to observe every
draw. `read-late-pass-probe.py` joins samples to actual emitted sequences.

Two covered event windows change strongly after pixel shader
11015601269670120444, an exact microcode match for the converted animated water
materials. `-WaterPassProbe -StageProbe` therefore captures paired observations
immediately around that shader's draws, with full register and buffer-prefix
evidence. Run 21 contains 2400 complete pairs across 300 frames, 4800 numeric
samples, and no missing pairs or busy/unsupported events. Its five final-output
decreases include four complete before/event/after stage windows; the first
event precedes the start of stage coverage by one neighboring frame.

`trace-match-geometry.py` and `trace-analyze-geometry-state.py` uniquely identify
all 2400 submitted water draws. The former now reads current target material
IDs from the candidate32 BSP table: an older audit has stable source names and
slots but stale target IDs. Two 84-index draws share an index pattern, so their
vertex bytes are required to distinguish them. The changing draw is mesh 7,
part 0, material slot 19 / tag 9415, source `settlement_pipe_small_water_02`.
Mesh 15's corresponding draw does not change this point.

`read-water-pass-probe.py` verifies paired resource/draw identity and correlates
the results with final output. At frame 3445, for example, the underlying pixel
is approximately (0.271,0.267,0.310) both before and during the event. The water
draw changes it to (0.278,0.275,0.318), whereas the adjacent frames end near
(0.439,0.416,0.494). The water contributes much less light for that frame; it
does not replace the underlying pixel with black. Texture descriptors remain
fixed in the four complete event windows. The changing reflected non-light
parameters are five animated texture-coordinate offsets. These observations
do not establish that all shader inputs or sampled texture contents are right.

The measured water pulse is **not yet established as the human-reported black
flash**. No shader, lighting, map or production-runtime correction follows from
this result. Continue tracing that distinction and authored water behavior;
billboard readability, visible outdoor rain and protrusion lighting remain open.
The native WARP fixture passed in legacy, all-draw and paired-water modes with
exact coordinate-coded values, fence ordering and frame-cap checks. The compact
CPU recorder fixture passed its declared register-range and delta checks.
`sky-late-pass-probe-integration.patch` records the narrow SDK integration.

Both private game runs ended under their 180-second watchdogs. The original
shared GPU and installed candidate32 map remain hash-verified and unchanged.
No screenshots, desktop input or performance acceptance are claimed. Source:
Halo Online Sky Bridge via GeneralHeed / Priception's
[Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190).
The original individual creator is unspecified; this project provides the
Xbox 360/OpenH3M adaptation.
