# Native video quality controls

F4 opens Video / Performance. Shadow quality, decoration distance, object LOD,
cosmetic effects and water detail apply live. Performance, Balanced and Original
presets include these controls alongside texture detail and filtering. Resolution
and render scale remain independent and require restart.

## Native renderer integration

`sub_82160F28` first selects Halo 3's current map-authored performance throttle
row, including its split-screen defaults. The host hook adjusts only the current
0x38-byte scratch copy at `0x8285843C`. It does not modify default tables, ptag
assets, map files, saved variants, simulation or network data.

| Control | Original | Medium / Balanced | Low / Performance |
| --- | --- | --- | --- |
| Dynamic shadows | Authored budget and LOD | Budget × 0.75², rounded up; LOD × 0.75 | Budget × 0.5², rounded up; LOD × 0.5 |
| Decoration distance | Authored value | × 0.75 | × 0.5 |
| Object LOD | Authored value | × 0.75 | × 0.5 |
| Cosmetic effect distance | Authored value | × 0.75 | × 0.5 |
| Water detail | Authored value | At most 0.5 | At most 0 |

Positive shadow budgets retain at least one; authored zero remains zero. The
native renderer adapts its shadow selection toward that budget; it is not a hard
per-frame caster limit. Object LOD changes use existing authored alternate models;
objects without an alternate model retain their original mesh. Water
uses the native 0.33/0.66 feature thresholds. Surface shading and underwater fog
are retained. Object disappearance distance, instance distance, decals, light
counts and throttle flags remain unchanged. Values are recomputed from the
native row each frame, so reductions never compound.

Retail addresses were verified against the local PPC code: throttle setter
`8246F638`, updater `82160F28`, water consumer `8221E000`, decoration consumer
`8217F178`, effect consumer `82159BA8`, shadow consumer `8218F1F8`.
The [ManagedDonkey throttle declaration](https://github.com/twist84/ManagedDonkey/blob/main/game/source/rasterizer/rasterizer_performance_throttles.hpp)
supplied semantic names; its executable addresses are not used.

## Timing and persistence

- **CPU work** is Windows process CPU consumption across all threads per native
  rendered frame, averaged over 30 samples. It excludes sleeping and can exceed
  wall time because threads execute in parallel. It is not CPU critical-path
  latency and must not be added to GPU time.
- **GPU execution** uses D3D12 timestamps around guest command submissions,
  summed by frame after their fences complete. No extra fence wait is introduced.
  Ring-wrap completion is sorted by submission; missing timestamps invalidate
  the affected frame. Presentation and host UI costs are excluded.
- Stale or unavailable measurements display a waiting/unavailable message.
- Save uses the existing application configuration. TOML strings now use the
  TOML formatter, preserving Windows paths, quotes and control characters.
- Restore defaults resets only the video controls. The original SDK filtering
  default is 4x, so restored defaults may show Custom rather than Original.

## Build and evidence

Apply `halo3mp/patches/rexglue-sdk-video-quality-metrics.patch` after the existing
video-options and GPU-execution-timing SDK patches. The earlier heavy-map and
asynchronous-occlusion work remains part of this checkout's baseline. Reuse
`work/rexglue-sdk/out/pacing-release`; `tools/video-options/build.ps1` builds the
runtime, GPU plugin, application and focused settings check.

The check covers native scaling, untouched fields, split-screen defaults,
disabled authored features, GPU frame aggregation and gaps, presets, resolution
independence, mixed config reload, escaped strings and default restoration.

`tools/video-options/sweep.py --game <original-disc-directory>` runs one
180-second Last Resort sweep with an isolated repository-local profile. It uses
exclusive process-local replay, a stationary turn, firing, native guest captures
and one native host backbuffer capture. It does not send desktop input. The
debug-only sweep cycles presets, mixed saved settings and restored defaults;
ordinary launches leave it disabled.

The initial run exposed invalid Windows-path serialization; that defect was
fixed before the corrected sweep. The initial movement route ended against a
wall and is not evidence for distant geometry or water.

### Corrected combined run, 2026-10-28

Evidence is in `work/video-options/remaining/sweep-20261028-212103/`.
The build and focused settings check passed. The 180-second watchdog ended the
test deliberately; return code 1 records that termination, not a game crash.

The native renderer logged all five phases at 12-second intervals. Balanced
selected a shadow budget of 3, 0.525 shadow LOD, 0.75 decoration/object/effect values and
0.5 water. Performance selected a budget of 2, 0.35 shadow LOD, 0.5 distances and
0 water. Mixed settings reloaded successfully (`saved_custom_reload=true`),
and restoring defaults produced `original_exact=true` for the full native row.

All 11 saved guest captures were inspected in chronological order, followed by
the host menu capture. They show the native HUD, weapon, architecture, foliage,
turning, firing and reloading through the changes. The menu displays every new
control without clipping and reports CPU work 60.94 ms/frame and GPU execution
20.31 ms/frame in its captured frame. These are different measurements, not
additive frame latency or a performance comparison.

The spawn is enclosed by factory walls: **water appearance and specific distant
LOD/shadow transitions are not visually confirmed by this route**. Their live
native settings and restoration were confirmed; all-map visual correctness and
performance gains are not claimed. No broader validation tasks were added to
the TODO list. Item #3 was reopened because those missing visual checks are
part of this task, not broader validation.

### Focused beach comparisons, 2026-10-28

`beach_fixture.py <original-disc-directory> --objects` creates a private Last
Resort cache under `work/video-options/remaining/beach-fixture-objects`. It
repositions spawn markers and existing stock object placements only. The
original disc, models, shaders, physics and authored LOD thresholds are unchanged.
The source is Bungie's original Halo 3 ODST Multiplayer Disc Last Resort; this
is a diagnostic scene arrangement, not a converted map or shipped variant.

`sweep.py --game <fixture-directory> --visual-confirmation` uses exclusive
process-local replay and native application captures, with a 250-second watchdog.
It changes one quality control at a time, restores Original between changes,
and repeats shadow comparisons after the scene has settled. The debug-only
render witnesses preserve all guest arguments and results.

Run `work/video-options/remaining/sweep-20261028-214603` established:

- All nine guest captures and the host backbuffer capture were inspected in
  sequence. The observer stayed at (14.361, 24.841, -0.355), facing
  (-0.900, 0.426, 0.089), throughout the comparisons.
- The four visible stock rifles changed silhouette at Low object detail and
  returned at Original. Their native selector `82315E70` changed from 1 to 0
  and back at measured distances 6.368–9.118, with authored threshold 10.
  The nearby held weapon remained at 1. Stock Mongooses have no alternate LOD
  model, so the earlier vehicle-only comparison could not establish this.
- Visible ocean and shoreline rendering survived Original, Low, Medium and
  restoration. Native water draw `82462F88` switched from entry point 3 to 4
  at Low and returned to 3 at Original/Medium. Over the first three seconds
  of Low, it recorded 89 basic draws and one transitional full draw. Medium
  retained tessellation but disabled interaction (flags 0,1). The stationary
  scene does not establish a visible interaction-ripple difference.
- Low shadows reduced native shadow submissions from approximately five per
  frame to three, and restored them afterward. This establishes consumption
  of the budget, not yet a clear ground-shadow visual difference. The initial
  capture includes the round-start banner; settled repeated captures are
  required before calling that visual check complete.

The follow-up `sweep-20261028-215214` repeated Original → Low → Original → Low
→ Original shadows after the scene had settled. All thirteen guest captures
and the final host capture were inspected in order, with enlarged views of the
Mongoose body. The small pixel differences do not convincingly separate shadow
quality from normal rendering variation, so visual shadow confirmation remains
open. Native submissions repeated
455 → 278 → 436 → 278 over approximately 90 frames per observation, while
other quality settings and the observer were unchanged. The native adaptive
budget explains why a budget of 2 can still render about three casters per frame.

The initial interaction attempt `sweep-20261028-215746` hit a shoreline rock;
its six captures were inspected but do not confirm water interaction. The
`--water` fixture moves only the test spawn to an unobstructed shoreline position.
`sweep.py --water-interaction` uses native replay to aim down and fire matched
bursts during the water phases; it never injects host input.

Run `sweep-20261028-220111` used the open shoreline fixture. All six guest
captures and the final host capture were inspected sequentially. Low water
visibly flattened the nearshore surface detail at 155000 ms; the detail returned
at Original (165000 ms), remained at Medium (175000 ms), and survived restoration
again (185000 ms). Native draw witnesses confirm entry point 4 at Low and 3
otherwise. The camera stayed at approximately (6.294, 29.007, -1.843). These
captures establish the visible water-quality change; they do not independently
isolate individual bullet-induced ripples. The 210-second watchdog ended normally.

The rebuilt executable and focused settings check pass, and the SDK patch passes
its reverse-application check. TODO #3 and the goal remain open solely for the
inconclusive visual shadow comparison and any resulting correction. Native
render counters alone are not being treated as a completed visual check.

### Completed shadow comparison and final audit, 2026-10-28

The final run `work/video-options/remaining/sweep-20261028-221014` resolves the
remaining shadow check. `beach_fixture.py <disc-directory> --shadows` repositions
six existing vehicle slots using the original Warthog palette entry, and turns
the private test spawn toward open sand. This is a diagnostic arrangement,
including some suspended/partly buried placements, not a playable map release.
No stock model, shader, physics tag or installed cache is changed.

`sweep.py --game <shadow-fixture> --shadow-confirmation` runs Original → Low →
Original → Medium → Original → diagnostic world-shadows-off → Original. The
off control is explicitly debug-only and requires exclusive native input replay;
it is not an additional user quality setting. All eight guest captures, followed
by the host backbuffer capture, were inspected sequentially. After the initial
aim adjustment, the observer remained at (14.361, 24.841, -0.355), facing
(-0.953, -0.202, -0.227).

The central Warthog's projected shadow is absent at Low (115000 ms), visible
again at Original (125000 ms), absent at Medium (135000 ms), and visible again
at Original (145000 ms). The diagnostic off capture (155000 ms) removes world
shadow coverage, including vehicle self-shadowing; restoring Original
(165000 ms and the final host capture) restores it. Static map shading remains.
The later 175000 ms Original capture also shows that Halo 3's adaptive budget
can vary a particular caster's visibility over time. The setting is a budget
and shadow-detail scale, not a promise that one chosen vehicle always casts.

Read-only witnesses now distinguish a shadow attempt from reaching the native
shadow-map setup/draw path (`8218E788`). In successive three-second observation
windows, Low recorded 285 maps, Original 438, Medium 361, Original 449,
diagnostic world-shadows-off 90, and restored Original 450. Each window covered
about 90 native frames. The remaining one map per frame in the off control is
outside the world-shadow-budget loop. Per-object projected LOD also scales
correctly (for example 0.46074 Original, 0.23037 Low, 0.34556 Medium).
These traces support the visible changes; they are not their sole evidence.

| Requirement | Final evidence |
| --- | --- |
| Live controls, presets, save/reload and defaults | Native combined run `sweep-20261028-212103`, `saved_custom_reload=true`, all native fields restored with `original_exact=true`; menu capture shows every control without clipping. |
| CPU and GPU timing readouts | Same native menu and phase logs; actual process CPU time and completed D3D12 timestamp samples. Focused tests cover frame aggregation and missing samples. |
| Visible distant object LOD | `sweep-20261028-214603`: four stock rifles visibly switch authored models and restore; native selector changes 1 → 0 → 1. |
| Visible water quality | `sweep-20261028-220111`: Low flattens nearshore detail, Medium/Original restore it; native full/basic water draw path follows the setting. |
| Visible dynamic shadows | Final vehicle comparison above, including Low, Medium, restoration and diagnostic coverage control. |
| Preserve simulation and saved variants | Production writes are limited to the current renderer-throttle scratch row; no simulation, network, map or variant serialization hook is changed. Fixture changes are private test placements only. This does not claim tested console/System Link operation. |
| Repeatable build and integration | Application rebuild succeeded; final `video_settings_check` passed; incremental SDK patch passes reverse-application verification. |

The 190-second watchdog ended the final run as designed. The implementation
needed no further rendering correction after the serialization fix; the missing
evidence required suitable visible geometry and camera placement. TODO #3 is
complete and removed from the open list. The candidate build was tested inside
the repository; this run does not claim deployment to an external installation.
