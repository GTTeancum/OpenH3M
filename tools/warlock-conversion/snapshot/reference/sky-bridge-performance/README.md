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


## Authored water modulation and outdoor rain (2026-11-04)

The saved human player/vehicle pose, camera vectors, FOV and native observer
command remain available for unattended replay. No additional human positioning
is required. The original view still uses the 0.03-unit vehicle-settling guard.
These are reproducible scene inputs, not a complete savestate or reproduction
of the human-reported black flash.

`audit-water-texture-pulse.py RUN` and
`candidate32-water-texture-pulse-result.json` extend run 21's paired water
measurements. All 27 retained BC3 mip levels in the three color textures are
byte-identical to their corresponding source mip levels after native untile
and endian conversion. Two textures intentionally start at source mip 1, as
recorded in the conversion. The analysis reconstructs mesh 7's actual geometry,
UVs and recorded sampler settings, including mirrored addressing, PWL gamma,
and the runtime's enabled half-pixel offset. It reads the existing shader's
`DETAIL_MULTIPLIER` (4.59479), which is squared in this albedo operation.

Across 300 frames, the partial CPU texture model's maximum albedo channel has
correlation 0.98628 with the measured maximum additive-water RGB contribution.
All four complete measured event windows contain corresponding texture-model
dips. The underlying GPU pixel remains lit during those events. This supports
authored water modulation as the explanation of that measured pulse, without
establishing that it is the user's black flash. This is a partial texture model,
not a full shader simulation, GPU texture-content validation or visual verdict.

The saved human camera's native location is BSP 0 / cluster 45 / atmosphere
`skybridge_indoor`, which has no weather effect. Run 20's complete 300-frame
draw trace contains zero submissions of the rain pixel program. A separate
outdoor weather view translates the saved camera/vehicle +12 world units along Y, preserving the
camera orientation and projection. The native observer computes BSP 0 /
cluster 23 / leaf 4153 and `skybridge_outdoor`, which references weather effect
10701. Source and target both author this outdoor rain.

Run 22 reached this translated view but did not arm: the vehicle settled
0.031320516 units from its placement, outside the original 0.03 guard. The
private harness now accepts an explicit `-VehicleTolerance` from 0.03 to 0.1;
weather runs use 0.04. This changes the recording guard only. Run 23's
`-AllDrawTrace` recorded 846111 emitted draws across 300 frames, including 6900
draws of the exact native rain pixel program. `inspect-weather-draws.py` joins
the native location, authored atmosphere and shader identities; the shader has
other particle users, so this discovery alone was insufficient attribution.

Run 24 uses `-RainPassProbe -StageProbe` to record 16 numeric points immediately
before and after the identified shader, plus bounded texture-byte witnesses.
`read-rain-pass-probe.py` identifies both rain assets by actual sampler dimensions
and 512-byte resource prefixes. The 256×48 stock rain texture uses its standard
resource stream with minimum LOD 1; its optional high-resolution stream is not
the captured base binding. The 512×512 texture uses minimum LOD 0. Resource
residency is recorded rather than assumed.

All 6902 submitted rain draws have complete paired measurements: 220864 samples
with no busy, unsupported, incomplete or missing-point events. The 256×48
texture changes 107 sampled points in 100 draws over 88 frames. The 512×512
texture changes 6540 sampled points in 1252 draws over 291 frames. Each has
maximum measured RGB change 5/255. This establishes actual color contribution
from both rain assets in an outdoor atmosphere, not acceptance of rain density,
appearance or the entire viewport. `candidate32-outdoor-rain-result.json`
records hashes, provenance, example values and remaining limits.

The rain-mode native WARP fixture passed all 32 coordinate-coded values,
before-fence-read protection and the frame cap. The integration patch passes
its reverse application check. All private games ended at their 180-second
watchdogs. The shared GPU and installed candidate32 map remain hash-verified
and unchanged. No production adjustment, image capture or performance
acceptance follows from these diagnostics. The black flash, protrusion lighting,
billboard readability and final visual/performance acceptance remain open.

Source: Halo Online Sky Bridge via GeneralHeed / Priception's
[Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190).
The original individual creator is unspecified; this project provides the
Xbox 360/OpenH3M adaptation.

## Saved-view billboard tracing and candidate33 (2026-11-04)

`candidate33-screen-mips-result.json` records the latest investigation. The
saved player/vehicle pose and native observer command remain available for
unattended replay. In runs 26 and 27, all 1800 billboard draws across 300 frames
match the human recording's camera/projection constants byte for byte. The
native observer result and command also match exactly. This reproduces the
view, not the complete simulation: the original recording was at 607.67 game
seconds, versus 22.5 and 20.1 seconds in these private runs.

`-ScreenPassProbe -StageProbe` selects mesh 144 by its vertex prefix and three
pixel program identities. `read-screen-pass-probe.py` independently joins the
index, vertex and material witnesses and checks paired samples from 16 points
inside the projected billboard. Six authored layers are present. Run 25 lost
its last six pairs because the inactive CPU sequence stopped pending GPU
readbacks from draining; the integration patch fixes that. Runs 26 and 27 each
contain all 1800 pairs / 57600 numeric samples, with no incomplete pairs. The
native WARP fixture passes coordinate values, fence protection and frame cap.

All six materials retain their source animation functions, named consumers and
shared constants. The scanline intensity of 38.72549 is authored. Two texture
chains were discarded by the converter: `crop_01` retained one of nine levels,
and `screen_line_01` retained one of eight. The latter's 128×16 dimensions are
outside the general encoder's supported packed-chain path. A fresh inventory
of all 25 installed stock tag caches found neither named custom texture;
`shared.map` is a resource store whose named owners are in those tag caches.

`restore-screen-mips.py OUTPUT.map` builds a private incremental candidate from
the pinned candidate32 hash. It preserves every authored texel/compressed block
and changes only the two bitmap records and resource bookkeeping. All old raw
data, tag addresses, geometry, materials and gameplay data are unchanged; only
40 bytes change within the original metadata region. The two new resource
payloads total 356352 bytes. Candidate33 is
`1705dc69c655d5a0d1e10e1163d45f7ce9e45743bcd7192efce9306ba371ac3c`.
It is not a release or a full-converter integration.

The 128×16 scanline chain places level zero in the packed tail. Every one of
its 177 BC1 blocks was verified against unchanged `GetPackedMipOffset` and
`GetTiledOffset2D` functions extracted from the active SDK; both completed map
resources also untile to all 17 authored levels exactly. Fixture sources,
outputs and hashes remain in `work/sky-bridge/screen-pass-build`.

Run 27 loads candidate33 with `-Candidate 33` and reaches the exact saved view.
`audit-screen-bindings.py` finds `crop_01` bound with min/max LOD 0/8 and a mip
address 262144 bytes after its base. However, both scanline samplers have
min/max LOD 0/7 and packed mips enabled but **a zero mip address**, across all
300 frames. The active `GetSubresourcesFromFetchConstant` implementation then
restricts the texture to level zero. Thus merely restoring the small scanline
chain has not enabled its filtering. Trace the native bitmap interop and
header-construction path next; do not assume a general host aliasing fix.

The paired color results are complete measurements, not an image, perceptual
readability verdict or performance acceptance. Animation phase differs between
runs, so aggregate differences do not establish an improvement. The original
black flash and protrusion lighting remain unresolved. All private games ended
at their 180-second watchdogs. Shared GPU and installed candidate32 hashes
remain unchanged. No human positioning is needed to repeat this view.

Source: Halo Online Sky Bridge via GeneralHeed / Priception's
[Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190).
The original individual creator is unspecified; this project provides the
Xbox 360/OpenH3M adaptation.

## Native scanline mip addressing and candidate34 (2026-11-04)

`candidate34-screen-header-result.json` records the native cause of candidate33's
zero scanline mip address and the map metadata correction. The optional
`-HeaderTrace` hooks observe bitmap interop and header construction without
changing guest data. Outputs stay in the private run directory and stop after
400 selected descriptors / 2000 rows. `read-bitmap-header-trace.py` verifies the
construction/addressing sequence and joins it to the subsequent GPU fetches.

The 128×16 scanline's eight levels share one packed tail starting at offset
zero. Native `82298970` chooses the addressing path using descriptor byte 47.
The generic `826085A8` path supplies a zero mip base when the constructed mip
offset is zero. Run 28 directly records that path, and both later GPU samplers
therefore remain restricted to level zero. This is independent of the saved
camera, which matches the human recording exactly.

Candidate34 selects the native explicit-address path through `82097828`. Its
primary and secondary data references both point to the same 4096-byte resource
allocation. No pixels are duplicated or changed. Run 29 records both addresses
as `0xba2dc000`; later GPU fetches use physical address `0x1a2dc000` for both,
with minimum LOD 0 and maximum LOD 7 throughout all 300 sampled frames. The
other repaired texture, `crop_01`, retains all nine addressable levels. No host
renderer workaround or gameplay change is needed.

Compared with candidate33, only the scanline resource's secondary length,
address-mode flag and secondary fixup change. Its bitmap record and raw mip
bytes remain identical. `restore-screen-mips.py --explicit-tail-addresses`
reconstructs candidate34 from the pinned candidate32 baseline. The result is
194351104 bytes, SHA256
`70e5c7aaed939be2c8c718535d8113deb334cd66ed428bd995c7b8573e93aa59`.

`sky_bridge_screen_mips.py` integrates both texture corrections into the real
material importer after stock/native asset lookup. It is guarded by source map,
exact custom texture names, dimensions, formats, mip counts, pixel hashes and
color curves. Its produced records, control bytes, raw data and fixups match
the runtime-tested candidate34 resources exactly. Actual importer calls also
verify resource creation and repeated-import reuse. No full scenario rebuild
was attempted amid unrelated pending conversion edits. The private candidate34
LIVE package passes container integrity and extracted-payload checks; it has
not been installed or promoted.

Runs 28 and 29 each contain 1800 complete paired billboard draws / 57600 numeric
samples, with exact native observer result/command and camera/projection
matches. Their snapshots both occur at 22.5333 game seconds. This does not
establish identical animation phase throughout the runs or reproduce the human
recording's complete simulation state. Scanline filtering changes the measured
contribution: its peak increment falls, while aggregate brightness and
saturation rise. These measurements do not establish better readability.

A static audit of 255 small multi-level texture descriptors across 25 stock
tag caches found the generic address mode in each. This correction remains
specific to the two audited custom textures. Other captured native headers
are compared by descriptor fields, without claiming named stock attribution.

Both games ended under their 180-second watchdogs. The shared GPU and installed
candidate32 map remain hash-verified and unchanged. No image capture, visual
acceptance, performance acceptance, physical Xbox 360 or system-link test is
claimed. The original black flash and protrusion lighting remain unresolved.
The saved player/vehicle pose and exact camera replay remain available, without
requiring the user to reposition for another test.

Source: Halo Online Sky Bridge via GeneralHeed / Priception's
[Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190).
The original individual creator is unspecified; this project provides the
Xbox 360/OpenH3M adaptation.

## Candidate34 stationary timing and moving-model attribution (2026-11-04)

`-TimingOnly` disables every GPU/draw/header probe and enables host present
timing. It rejects combinations with probe switches. Private runs 30 and 31
use identical initial shader caches and runtime files, including the original
GPU/runtime DLLs and the private pose executable. They compare candidate32 and
candidate34 respectively; both exit at the 180-second watchdog. Native observer
result and command match the saved human state exactly in each snapshot.

`analyze-seated-timing.py LOG_DIRECTORY RUN_DIRECTORY` starts at the first
logged seated-view marker and retains the older startup-inclusive windows.
Candidate32 measures 29.9701 FPS over 17.58 seconds, with median/p95 intervals
33.365/33.961 ms. Candidate34 measures 29.9703 FPS over 19.15 seconds, with
median/p95 33.373/33.872 ms. Maximum intervals are 50.570 and 50.152 ms.
The approximately 3.5-second stall in both startup-inclusive windows precedes
the seated view, during loading/placement. It is not silently discarded from
the report. `candidate34-saved-view-timing-result.json` records both scopes,
cache provenance, clocks and hashes. One run per candidate, unequal interval
lengths, timing logs and the private replay harness limit this comparison;
it does not establish traversal performance or visual acceptance.

The original detailed geometry matcher covered BSP and lightmap geometry,
omitting `mode` resources. `trace-model-draws.py` now independently attributes
moving fabric and searchlight geometry using exact index and vertex prefixes
plus pixel-program material references. The original human CPU recording has
3609 unambiguous matching submissions in 43 groups. Nine moving models have
base and lit submissions across all 96 complete observed frames. This recording
uses camera (16.98436,69.54246,0.30509), different from the later GPU recording
and saved replay; their frame identities and surface coverage must not be merged.

The skinned lit vertex program reads constants c240 through c243 directly,
despite having no named vertex reflection entries. Those values remain stable
in each of the 15 observed lit part/pass groups. Referenced bone-palette
matrices are finite: fabric determinants remain within about 0.000002 of one,
and the searchlight remains near 1.089808. Palette indices include zero-weight
entries, and the wider register digest includes inactive slots. These checks
do not execute weighted skinning or establish correct positions, normals,
animation or visible output. Animated simple-light values also vary.

`candidate32-moving-model-attribution-result.json` preserves this expanded
coverage and its limits. The next target is actual skinned-model coverage and
paired output from the fabric and searchlight passes. The original black flash
remains unresolved; these data do not justify changing animation or lighting.
Both games are closed. Shared GPU and installed candidate32 hashes remain
unchanged; no release promotion, image capture or final acceptance occurred.

Source: Halo Online Sky Bridge via GeneralHeed / Priception's
[Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190).
The original individual creator is unspecified; this project provides the
Xbox 360/OpenH3M adaptation.

## Animated-model probes reproduce fabric blackening (2026-11-04)

`candidate32-model-pass-blackening-result.json` records private runs 32 and 33.
`-ModelPassProbe -StageProbe` restricts detailed CPU recording by observed
skinned vertex programs and candidate32 vertex-buffer witnesses. The decoder
then requires exact SHA256 index/vertex prefixes and shader material references.
Sixteen numeric color-0 points are read before and after each selected draw;
initial positions came from projected weighted model vertices. These positions
alone do not prove coverage. The native WARP fixture verifies the selected
coordinates, exact readback values, completed-fence guard and frame cap.

Both runs produce 11308 unambiguous model draws over 300 frames, with 361856
samples, complete pairs, and no busy/unsupported/incomplete events. Eighteen
of 43 model/pass groups actually change a sampled RGBA value. All 9000 base
and lit skinned draws per run match the saved human camera/projection constants
exactly. Native observer command/result snapshots also match. The private
games both terminate at their 180-second watchdogs.

There is now a repeatable blackening event: model 10177
`sbr_panel_fabric_b_anim_01`, mesh 0 part 1, uses material 9821
`sbr_envelope_04_akill`. At (711,197), its dynamic-light pixel program
2673597551499054088 replaces previously lit RGB with zero. This occurs on ten
frames in three windows of four, three and three frames in each run.
The captured guest `RB_BLENDCONTROL0` is `0x00010001` (ONE + ZERO), while
the adjacent opaque dynamic-light draw uses `0x01010101` (ONE + ONE).
This attributes the overwrite to an actual draw and guest blend state;
it does not yet explain why the native material path chooses that state.

Run 33 shifts the existing sparse final-output grid to include the exact same
point. After host gamma/FXAA, its largest RGB channel falls from boundary
values 0.3030–0.3196 to 0.0841–0.1281 during all ten black-write frames and
recovers afterward. `read-fabric-blackening.py` joins these records by frame
within the same run and decodes their actual 10-bit format/component mapping.
The earlier isolated-one-frame near-zero detector reports no pulse: these are
longer dark windows, and later composition contributes nonzero color. That
negative metric does not contradict the measured black overwrite.

The pixel program matches stock template 225, program 227 index 4. Template
entry-point/pass records match original Zanzibar, where that template is used
by LOD weapon materials. No shared template was changed. The next step is
tracing native material-state selection to establish why this alpha-tested
dynamic-light pass replaces the existing light. A global blend override or
removing the animated model would not follow from the evidence.

The searchlight's base/hologram passes also change sampled values, but their
correctness and relation to the reported protrusion remain unresolved. These
private events are not claimed to identify the original human bad frame.
Sixteen points do not establish the full affected surface, and the saved pose
is not a complete simulation savestate. No visual/performance acceptance,
rendering fix or release promotion is claimed. The shared GPU and installed
candidate32 map remain hash-verified and unchanged. The prior human CPU
analysis retains its recorded hash; the expanded first-constant projection
input is preserved separately as `model-draw-analysis-with-constants.json`.

Source: Halo Online Sky Bridge via GeneralHeed / Priception's
[Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190).
The original individual creator is unspecified; this project provides the
Xbox 360/OpenH3M adaptation.

## Native alpha-test setup traced to the fabric overwrite (2026-11-04)

`candidate32-native-blend-cause-result.json` records private runs 34–36.
The saved observer command/result remain byte-exact. All traced base/lit
camera constants match, and all three runs reproduce ten black writes in
three short windows with matching final-output darkening. These are numeric
samples at the affected point, not full-image visual acceptance.

The native material hook disproves a material-binding blend-mode error:
`sub_82465478` returns from dynamic-light entry 9 with additive blending
`0x01010101`. Material 9821's complete 132-byte post block is identical to
the generated map, including flag 2 at +108. After binding,
`sub_821845F8` tests that flag and invokes `sub_8217FDA0(1)`. With the
observed global bypass byte zero, that function calls the blend-enable
setter with zero at `0x8217FDF4`, producing `0x00010001`, then enables
hardware alpha testing. The following draw therefore replaces lit color.

Run 36 joins every one of the ten black fabric draws to its native state
flush using equal command-buffer addresses and complete type-0 packet
bytes. All ten have the consecutive recorded sequence: material bind
returns additive; the native alpha-test setup disables blending; the flush
at `0x82184F28` submits replacement blending; the GPU consumes that packet.
There are no unmatched or ambiguous target joins. CPU and GPU frame
counters are not equated. This establishes the cause of these private
blackening events without inferring it from a frame counter or shader name.

Apply `sky-command-witness-integration.patch` to the private SDK with
`git apply --unidiff-zero`; copy `sky_command_witness.h` beside the existing
D3D12 trace header. The reverse-apply check passed against the tested SDK.

The diagnostics are opt-in (`-BlendTrace`, `-CommandTrace`) and preserve
guest arguments, results and render state. Native records stop at 15 seconds
or 100000 records; run 34 hit the record cap at 2.37 seconds, while the
filtered run 36 reached 10.95 seconds and covered all ten target events.
Run 36 records 17126 relevant state flushes with complete call pairs and
no failed state reads. The GPU trace keeps its existing 300-frame,
15-second, 512-MiB bounds. The native command-witness fixture verifies
wrapped packet reads, nested indirect-buffer scope restoration, exact
blend history, and unchanged source bytes and reader cursors. All private
games terminated at their 180-second watchdogs.

The stock Zanzibar LOD donor also has post flag 2. Removing that flag alone
would remove required alpha testing; changing the shared donor would affect
stock assets. The next correction must retain authored cutout coverage
while preserving additive dynamic lighting on these converted fabric
materials. No rendering fix or promotion is included in this tracing change.
Shared GPU and installed candidate32 map hashes remain unchanged.

Source: Halo Online Sky Bridge via GeneralHeed / Priception's
[Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190).
The original individual creator is unspecified; this project provides the
Xbox 360/OpenH3M adaptation.

## Candidate35: scoped fabric discard correction (2026-11-04)

`candidate35-fabric-cutout-result.json` records the first material correction
and private reproduction37. It is an isolated candidate32-based experiment;
candidate34's billboard mip correction is not included. Only material9821
(`sbr_envelope_04_akill`, source4299) changes. Original template225, pixl227,
and all other 548 `rmsh` postprocess records remain unchanged.

The private template keeps the native vertex programs, shader interfaces,
parameter routes, GPR counts and every original pixel ALU/fetch instruction
byte. Each of twelve pixel programs receives one `KILL_GT` before its final
exports. The existing unused literal `c252.w` holds the observed alpha
threshold, bits `0x3f008081`. For finite alpha this implements the recorded
hardware greater-or-equal test. The material's hardware-alpha flag can then
be cleared without losing this comparison, so its dynamic-light pass retains
the additive blend state established by material binding.

The installed Xbox360 SDK assembles and validates the new native shader
headers and scheduling. Its text round trip normalizes some unused original
instruction fields; the builder restores every original instruction byte
and control-flow word except the final EXEC's incremented count. A second
official disassembly/assembly validates the restored result. No runtime
render-state override is used. The reproducible sequence, from repository
root with outputs in `work/sky-bridge/fabric-cutout-build`, is:

1. `build-fabric-shader-tool.cmd` builds the SDK assembly utility with the
   installed VS2010 toolchain. It sets repository-local TEMP/TMP paths.
2. `extract-fabric-programs.py` and `disassemble-fabric-programs.py` preserve
   the twelve native inputs and their official disassembly privately.
3. `build-fabric-cutout.py` assembles the private programs and writes the new
   `payload-35/sky_bridge.map`; it rejects an existing output.
4. `verify-fabric-cutout.py` checks the unchanged donor/material interfaces,
   773 finite threshold cases, decoded discard operations and unchanged
   alpha texture resources. The 512x512 native base mip has 41144 texels
   below threshold and 221000 at or above it, so cutouts are required.

Run37 records 11272 attributed model draws with complete before/after pairs,
360704 numeric samples and no unmatched draws. The selected fabric part
uses three of the twelve new pixel programs. Its ten dynamic-light draws
have blend `0x01010101`, alpha-test disabled, and the expected threshold
literal uploaded. At (711,197), none overwrites lit RGB with black. The
comparison run36 has ten such overwrites with blend `0x00010001`.
All 300 final-output samples at that point stay above max-RGB 0.3030;
run36 has ten below 0.2 and reaches 0.0880. The saved observer command/result
and all 8970 traced base/lit camera matrices are exact. The replay stopped
at its 180-second watchdog; native loading passed all eleven header checks.

Use `trace-match-program-slices.py --shader-index` with the candidate35
index; using candidate32's shader index would miss the private programs.
`trace-model-draws.py` now selects the map from the run configuration and
verifies its recorded hash. `compare-fabric-cutout.py` retains paired samples,
native blend/alpha state and threshold constants for runs36/37.

This establishes a correction for the sampled fabric contribution, not full
visual acceptance. Cutout edges, global shadow paths, other affected
materials, the searchlight protrusion and advertisement readability still
need checking. NaN alpha rejection differs from the hardware comparison;
the authored texture alpha and witnessed exposure path are finite. Physical
Xbox360, system link and production performance remain unverified. No shared
runtime, installed map or LIVE package changed, and no release was promoted.

Source: Halo Online Sky Bridge via GeneralHeed / Priception's
[Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190).
The original individual creator is unspecified; this project provides the
Xbox 360/OpenH3M adaptation.

## Candidate35: measured cutout coverage and unresolved searchlight (2026-11-04)

`candidate35-fabric-coverage-result.json` records private replays 38/39, using
the saved human player/vehicle pose and native observer command. Both runs
cover 300 frames and terminate at their 180-second watchdogs. The original
candidate32 reproduces ten fabric black overwrites; candidate35 records zero.
The native observer command/result match exactly, as do all 9000 and 8985
traced base/lit camera matrices respectively. Eleven native map-header checks
pass in each run. These diagnostics do not establish production performance.

The opt-in `sky_coverage_probe.h` places an independent D3D12 occlusion query
around each actual selected draw. It never changes guest draw state or nests
an active game visibility query. Its 16384 slots are used once, read only after
their submission fence completes, and drained after recording stops. The
128-KiB readback contains sample counts, not images. Existing draw recording
limits remain 300 frames, 15 seconds or 512 MiB. `-CoverageTrace` requires
`-ModelPassProbe` and is rejected in timing-only runs. Copy the header beside
the private SDK's existing trace headers and apply
`sky-coverage-probe-integration.patch` with `git apply --unidiff-zero`;
reverse-apply verification passed.

All 11308 and 11292 queries join unambiguously to the recorded model draws,
with no missing, active-guest-query, capacity, or readback failures. The
paired color probes also complete without missing before/after samples.
`read-coverage-probe.py` decodes each run. `compare-coverage-probes.py` matches
referenced camera/decode/bone constants and selected raster/depth state,
while checking index/vertex witnesses. For model 10177 part 1, all 605 matching
input keys have identical aggregate passing coverage: 297 albedo, 298 static,
and 10 dynamic-light comparisons. Their respective sample ranges are
2323–2349,850–873, and850–870. Equal totals do not prove an identical pixel
mask, and unmatched inputs remain unpaired.

`build-coverage-probe-test.cmd` builds the native WARP fixture with outputs
and TEMP/TMP confined to the repository. Set `OPENH3M_SKY_COVERAGE_TRACE=1`
and `OPENH3M_SKY_TRACE_DIR` to a fresh directory under
`work/sky-bridge/fabric-coverage-build` before running `gpu-test.exe`.
The test verifies 64 samples for a full 8x8 draw, zero for the identical draw
rejected by the depth comparison, skipping an active guest query, refusing
reads before fence completion, and draining after the trace's sequence
becomes zero. These checks pass. The optional D3D12 debug layer is absent
on this machine; debug-message validation was explicitly skipped.

`audit-fabric-shadow.py` follows material 9821 through root definition 15,
alpha-test option 1, and global pixel library 63 to shadow program 1. Candidate32
and35 retain identical routing and native program bytes. Official SDK
disassembly confirms the shared program already discards texture alpha
below 0.5. This preserves a shadow cutout path, but does not prove identical
runtime shadow edges: the former additional hardware comparison used
approximately 0.501960814 and has not been measured in that path.

The coverage queries reveal a separate question about searchlight model 10122.
Its body and lamp face have 19–27 and7–10 passing albedo samples, but all their
later static/dynamic lighting draws have zero passing samples across both
300-frame runs. Its beam has0–317. At the sampled point (501,175), the albedo
body/face contribute, while their later lighting does not. The cause is not
yet identified; ordinary intervening occlusion, depth/stencil rejection,
shader discard, and distinct vertex-shader outputs still need separating.
No depth override, suppressed animation, or searchlight correction is made.

`audit-searchlight-inputs.py` confirms that the source 100-frame, three-node
`device:position` animation survives conversion: 356 converted codec 6 bytes,
60 control bytes and all fixups match exactly. All 300 frames also have
identical referenced position inputs across the three body/face passes.
Shader literal slots differ as required by the different native programs;
the audit does not execute them or establish correct animated geometry.
The captured depth comparison is reversed-depth GREATER_EQUAL, not EQUAL.
Authored animation alone does not explain away the user's reported flicker.

The next causal trace must distinguish those searchlight rejection paths.
Candidate34 billboard mip addressing still needs combining with candidate35;
advertisement readability, rain appearance, traversal/audio, performance,
physical Xbox 360 and system link remain unverified. Shared GPU and installed
candidate32 map hashes are unchanged. No release was promoted.

Source: Halo Online Sky Bridge via GeneralHeed / Priception's
[Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190).
The original individual creator is unspecified; this project provides the
Xbox 360/OpenH3M adaptation.

## Searchlight depth rejection isolated (2026-11-04)

`candidate35-searchlight-depth-result.json` records private replays 40/41.
The new `sky_depth_test_probe.h` tests four pipeline variants immediately
before each selected actual draw: original tests, depth comparison ALWAYS,
stencil disabled, and both bypassed. Every variant disables all color,
depth and stencil writes and uses KEEP for every stencil operation. The
original pipeline is restored before the normal draw. No guest memory,
material flags, normal draw state, or game visibility query is modified.
These diagnostic variants are not proposed rendering fixes.

Recording is opt-in with `-DepthTestTrace -CoverageTrace -ModelPassProbe -StageProbe`. It accepts only the witnessed searchlight body/face draw sizes
and six known pixel programs, excludes memexport and non-host render targets,
and refuses an active guest visibility query. There are at most 8192
single-use queries and 128 registered pipelines, within the existing trace
and 180-second process limits. Copy the header to the private SDK and apply
`sky-depth-test-probe-integration.patch` with `git apply --unidiff-zero`.
Reverse-apply verification passed. `read-depth-test-probe.py` joins all four
variants to exact recorded draw identities and actual coverage counts.

The WARP fixture built by `build-depth-test-probe-test.cmd` verifies the
four-count patterns 64/64/64/64 when all tests pass, 0/64/0/64 when only depth
rejects, and 0/0/64/64 when only stencil rejects. Actual subsequent guest
draws retain expected coverage 64/0/0. A float-color sample proves the
diagnostic writes no color, and the normal draw afterward proves its pipeline
was restored. Guest-query, memexport and non-host guards prevent diagnostic
draws; the completed-fence drain also passes. The optional debug layer is
unavailable and remains explicitly unverified. An initial depth-only fixture
exposed that disabling both tests with no pixel shader can skip rasterization;
the final probe uses depth ALWAYS while retaining the original depth-enable
state, which keeps that test meaningful.

Run40 records 300 frames, 11297 attributed actual draws and 7192 variant
queries for 1798 searchlight draws. The first frame begins after the albedo
pass; every recorded draw has all four variants. No pairs, queries or
identities are missing. Every static body draw has 0 passing samples under
the original tests, 0 with only stencil bypassed, and 24–32 with depth
bypassed. Static and dynamic lamp-face draws similarly go from 0 to 7–10.
The actual lighting draws agree with the read-only original-test variant in
all 300 frames. This establishes depth rejection; it does not identify the
prior depth writer or distinguish correct occlusion from a depth mismatch.
Albedo body counts differ when depth writes are disabled, as self-occlusion
can change within that draw; the decoder keeps that distinction explicit.

The body dynamic-light pass remains zero under all four variants. Its native
pixel program contains no discard, hardware alpha testing is disabled, and
the captured draw enables six user clip planes. The native vertex program's
weighted position/projection sequence and the host clip-plane implementation
were inspected. `audit-searchlight-clip-planes.py` reconstructs its 383 used
vertices mathematically: every frame has planes excluding the entire body,
with the closest excluding margin still below -4.93. This is consistent with
native light-volume clipping. It is float64 offline arithmetic, not captured
GPU vertex output, and does not establish correct authored lighting.

The extra queries preserve actual coverage for every matched geometry input
against run39, including 607 matching fabric-part keys. The fabric correction
still records zero black overwrites, and 18 of 43 model/pass groups change a
sampled color. All 8990 traced base/lit camera matrices and the native observer
command/result remain exact.

Run41 changes only the private bootstrap setting
`depth_float24_convert_in_pixel_shader=true`; rounding remains at its false
default. The guest requests D24FS8, while the normal host path uses float32
without this per-pixel conversion. This is a controlled precision experiment,
not a release candidate. It fails: all 43 traced model/pass groups have zero
actual coverage and zero sampled color contribution across 300 frames.
Depth ALWAYS restores diagnostic searchlight coverage, but ordinary draws
remain rejected. All 496 matched fabric input keys differ from run40. Zero
black-write events in this run are therefore not a successful correction.
The setting is rejected; preserve run41 as evidence and use run40/default
settings for further work. Both binaries are identical, both observer/camera
checks pass, and both runs finish at their 180-second watchdogs with 11 native
header checks passed.

The next trace needs sparse stored-depth values and actual fragment depths
around the searchlight passes, then attribution of the rejecting depth writer.
Do not disable depth testing or infer an animation defect from these results.
The measured searchlight is not yet conclusively tied to the protrusion in
the original human report. No full visual/performance acceptance, physical
Xbox 360 or system-link verification is claimed. Candidate34's billboard
correction remains separate; shared runtime, installed map and LIVE package
are unchanged, and no release was promoted.

Source: Halo Online Sky Bridge via GeneralHeed / Priception's
[Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190).
The original individual creator is unspecified; this project provides the
Xbox 360/OpenH3M adaptation.
