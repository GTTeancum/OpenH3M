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
