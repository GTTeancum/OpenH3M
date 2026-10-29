# Heavy-map performance work — 2026-10-26

## Verified and deployed

Original surface quality, unchanged native resolution/scale, Beelink SER8 / AMD Radeon 780M, 59.94 Hz display. The shared installation remains C:/X360/ISOs/H3M. Map assets and guest simulation/network behavior were not changed.

| Test | Displayed FPS | Exactly two refreshes | GPU execution mean / p95 |
| --- | ---: | ---: | ---: |
| Paradiso on Force Cove | 29.970 | 1,646 / 1,648 (99.88%) | 22.52 / 26.43 ms |
| Battle Canyon | 29.970 | 1,586 / 1,586 (100%) | 22.48 / 23.71 ms |
| Pinnacle, installed executable | 29.914 | 1,577 / 1,583 (99.62%) | 21.52 / 23.38 ms |
| Pinnacle, diagnostic repeat | 29.970 | 1,647 / 1,647 (100%) | 21.44 / 23.34 ms |

Both complete slow >360-degree rotations, with stationary observer positions. DXGI displayed-present IDs are joined to the actual painted guest-image IDs; no missing images. Screenshot intervals are excluded. Paradiso had one 3-refresh interval followed by one 1-refresh interval; Battle Canyon had none. This is a bounded single-player benchmark, not all-map traversal or split-screen certification.

Baseline Paradiso was ~17.5 FPS with repeated 15 FPS stretches. Surface texture/filter reductions alone did not help. Earlier Boarding Action 30 FPS baseline omitted the installed presentation bootstrap and cannot represent normal installed performance.

Pinnacle separately completed a 360.5-degree installed-executable rotation using the normal bootstrap, without an asynchronous-query CLI override. Both native captures were inspected: authored Forge structures, rock, sky, weapon and HUD render. Two five-refresh (83.42 ms) displayed holds remain, alongside two three/one-refresh pairs. This is not a hitch-free pass. No slow pipeline preparation was logged at the long stall; a diagnostic repeat did not reproduce it. The repeat completed 361 degrees with no capture calls, no dropped images and every displayed interval at two refreshes. No draw-stage stall over 8 ms occurred during its measured turn. Longer texture requests were logged during map entry, before the turn. The first run remains evidence of isolated unexplained hitches; the repeat is not proof that they are permanently eliminated. GPU timing covers the fixed 140-193-second window, not precisely the displayed-image window.

## Changes

1. Keep a late frame's assigned output deadline instead of always delaying it to the next slot. Rebase that deadline to updated display samples to prevent phase drift; reset after long stalls without catch-up bursts.
2. Submit final rendering before host pacing sleeps, allowing GPU execution during the wait.
3. Publish actual visibility-query sample counts asynchronously after their GPU fence completes. Dedicated query slots remain reserved until publication, including split intervals. Normal managed bootstrap enables this only for OpenH3M; generic SDK default remains off. No fake query results or disabled occlusion.
4. Add optional GPU timestamp diagnostics, harvested only from completed fences without additional synchronization. Diagnostics are off in the installed configuration.

Build and tests pass: late-frame deadline, long-stall reset, phase refresh, preset/resolution independence, save/reload/default restoration, panel draw. Native captures inspected on both maps; Battle Canyon reports hidden and visible sample results. Hangar/culling concern is deferred separately in TODO.MD at the user's request.

## Evidence

- Paradiso: .local/loading-traces/20261026-163419-8588
- Battle Canyon: .local/loading-traces/20261026-163833-39272
- Pinnacle installed confirmation: .local/loading-traces/20261026-164750-3552
- Pinnacle diagnostic repeat: .local/loading-traces/20261026-165508-39260 (timing only; visuals inspected in the installed run)
- Summaries: work/video-options/profiling/*-summary.json, *-display.json, *-gpu.json
- Deployment inventory: work/dlc/deployment.json; deployment log: work/video-options/profiling/deployment.log
- Repeatable measurement: trace_loading.py --slow-turn-check --turn-duration-ms 55000 --seconds 210 --exclusive-input --sample-observer --timing-diagnostics. Saved Forge layouts also use --slow-turn-forge and --saved-layout. All input is process-local H3IR. Use the installed bootstrap for candidates; never compare bare build-directory defaults to the user's installed settings.
- analyze_rotation.py validates rotation and reports host-submit intervals; analyze_display.py joins displayed image identities and refresh counts; analyze_gpu.py sums GPU command-list execution per frame. All readers include rotated logs.

## Headroom and remaining work

At Original quality, mean GPU execution leaves about 10.8 ms of a 33.37 ms frame budget; Paradiso p95 leaves about 6.9 ms. This is measured GPU headroom on the SER8, not a promise of the same margin on slower hardware. CPU/GPU time overlap; do not add their waits together or infer an uncapped game FPS from GPU duration alone.

Split-screen and slower-PC coverage remain unverified. Continue with measured overhead reduction and quality controls where needed, keeping resolution independent. Query-submission batching was tested and rejected: submissions fell from 9.53 to 3.39 per frame, but mean GPU execution changed from 22.52 to 22.73 ms with no meaningful cadence gain. Its code and harness flag were reverted; the installed GPU DLL never contained it. Direct-launch confirmation is complete, with the isolated, non-reproducing Pinnacle hitches retained as a follow-up.

## Source preservation

Incremental SDK patches: heavy-map-pacing, gpu-execution-timing, async-occlusion-readback, plus optional draw-stage-timing diagnostics. The retained batch-occlusion-queries patch records a rejected experiment; do not apply it. Apply these only to the established current SDK baseline, in that order. Preserve existing occlusion snapshot, upload coherency, and other prior runtime patches. tools/video-options/build.ps1 rebuilds the shared SDK/runtime/game and runs the tests; never build against a running candidate's DLLs.

Cleanup of three superseded incomplete trace directories was rejected by automatic approval review with "blocked by policy"; those directories remain. No deletion was performed.

The optional draw-stage diagnostics are present in the rebuilt candidate/source, gated by d3d12_log_present_timing. The installed DLL remains the earlier validated build with identical pacing/query behavior and no draw-stage instrumentation. Do not treat candidate DLL hashes as installed DLL hashes.
