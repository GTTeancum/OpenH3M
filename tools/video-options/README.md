# F4 video controls

F4 opens Video / Performance; Advanced settings retains the existing editor.
The live controls now cover surface textures, filtering, dynamic shadows,
decoration distance, object LOD, cosmetic effects and water detail. Presets
include all of them while leaving display resolution and internal scale alone.

Performance uses Low quality, two fewer surface mip levels and disabled
anisotropic filtering. Balanced uses Medium quality, one fewer mip level and
2x filtering. Original retains map-authored quality, original texture detail
and game filtering. Independently selected values appear as Custom.

Extra FXAA, display resolution and internal scale require saving and restart.
CPU work and GPU execution appear separately in milliseconds per rendered
frame. Save and Restore use the existing configuration system.

See [implementation and test notes](QUALITY-IMPLEMENTATION.md) for native
rendering fields, exact preset math, timing definitions and reproduction.
The new candidate is built inside the repository; historical installation
evidence below refers to the earlier surface-only controls.

## Earlier installed surface controls (2026-10-26)

Deployed to C:/X360/ISOs/H3M/OpenH3M.exe through the existing deployment tool;

installed executable/DLL hashes match the build inventory. Normal bootstrap

retains the existing content/cache roots and leaves diagnostic panel/capture

flags off. No map caches were rebuilt.

Build and process-local test passed: actual GPU cvars, preset values, resolution

independence, config save/reload, restoring defaults across restart, and panel

rendering. Fixed SaveConfig's empty-config early return, which otherwise retained

old saved values after restoring defaults. Native F4 panel was visually inspected.

Bounded stock Last Resort run at Performance surface quality reached gameplay;

stationary scene and HUD inspected in

.local/loading-traces/20261026-142228-24208/proof-loaded.png.

The earlier walk ended facing a wall and is not visual-quality evidence.

No measured performance gain, all-map correctness, audio validation or sustained

30 FPS claim is made from these checks. Extra FXAA is an existing restart-only

backend setting, now exposed separately; changing it was not benchmarked.

## Populated Forge comparison (2026-10-26)

The following is the pre-fix baseline. Subsequent host pacing and GPU-query
changes are deployed and documented in [the performance report](PERFORMANCE-2026-10-26.md):
Paradiso and Battle Canyon now deliver 29.970 FPS at Original quality. Pinnacle
is near 30 with isolated hitches still being diagnosed. Surface presets remain
separate from these runtime improvements.

Paradiso on Force Cove reproduces reported 15 FPS stretches. Full stationary

rotations with installed presentation settings measured Original 17.51 FPS

and Performance 16.46 FPS (matching capture exclusions). Both had ~66.7 ms

median frame intervals and ~67.2 ms p95. Surface presets alone did not solve

this workload; do not claim a 30 FPS fix. Three native Performance captures

were inspected, including authored base/vehicles. Details and JSON summaries:

`work/video-options/boarding-action/README.md`.

The candidate must use the installed bootstrap presentation settings for valid

comparisons; bare build-directory defaults differ. Earlier Boarding Action

30 FPS result lacked that bootstrap and is not representative of the installed

configuration. User redirected testing before its Performance run completed.
