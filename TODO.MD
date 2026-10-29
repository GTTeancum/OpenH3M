# Spartan TODO

## Open work at a glance

These numbers are references, not a change to the agreed work priorities. Broader validation is outside this list's scope.

1. **HEAVY-MAP PERFORMANCE** — Fix hitches and improve 30 FPS headroom.
2. **DEVELOPER FRAMERATE UNLOCK** — Add the F7 testing toggle, default off.
4. **STARTUP AND SHADERS** — Reduce loading delays and first-visit stutters.
5. **BATTLE CANYON** — Finish the Reach rebuild.
6. **QUEUED CONVERSIONS** — Resume maps in the agreed order.
7. **SHELVED MAPS** — Retain the four deferred conversions.
8. **FORGE ISLAND** — Keep the Halo 4 conversion pending.
9. **FORCE COVE CULLING** — Investigate the reported hangar visibility.
10. **PACKAGING AND MAINTENANCE** — Maintain shared DLC and repeatable tooling.
11. **PC ↔ XBOX 360 SYSTEM LINK** — Connect one or multiple PCs and consoles.

## 1. Heavy-map performance

The reported problems extend beyond one map. Average FPS alone is insufficient.

- [ ] Improve heavy converted maps to sustain 30 FPS with more CPU/GPU headroom.
- [ ] Diagnose remaining hitches, including Pinnacle's two 83.42 ms displayed holds despite a 29.914 FPS average and 99.62% two-refresh intervals.
- [ ] Investigate command preparation with draw-stage diagnostics.
- [ ] Profile CPU bottlenecks.
- [ ] Profile GPU bottlenecks.
- [ ] Profile memory use.
- [ ] Profile streaming stalls.
- [ ] Preserve original Halo 3 simulation, network semantics, stock assets and Xbox 360-compatible cache formats.

Current performance evidence: [performance investigation](tools/video-options/PERFORMANCE-2026-10-26.md).

## 2. Developer framerate unlock

- [ ] Add a **testing-only framerate unlock toggle** for developer releases.
- [ ] Default the toggle to **off**.
- [ ] F7 switches between normal capped operation and uncapped rendering during a test session.
- [ ] Use uncapped results to measure how fast each map can actually run on the current machine and estimate the improvement needed for less powerful machines.
- [ ] Measure actual rendered frame rate, excluding repeated presentations.
- [ ] Record frame times during uncapped tests.
- [ ] Exclude the toggle from non-developer releases.
- [ ] Preserve Halo 3 gameplay speed, simulation timing and network behavior while removing the rendering limit for measurement.
- [ ] Record map, machine, quality settings and test route with results so comparisons are meaningful.

F7 is available because Advanced Forge now activates automatically and uses the native properties menu.

## 4. Startup and shader preparation

- [ ] Investigate the remaining 3.02-second load-to-gameplay gap; do not describe the entire run as stall-free.
- [ ] Diagnose first-visit shader/pipeline stutters with timing evidence. A fresh-cache recorded walk showed an 82 ms gap overlapping pipeline builds, but this does not explain every stall.
- [ ] Determine what additional preparation is possible for previously unencountered content; known cached combinations do not cover every scene.
- [ ] Keep one shared cache and preserve rendering and simulation behavior during investigation.

## 5. Battle Canyon rebuild

- [ ] Finish the original Reach → H3 Editing Kit/H3 MCC → original Xbox 360 conversion pipeline.
- [ ] Resolve outstanding material semantics.
- [ ] Resolve lighting warnings.
- [ ] Resolve UV warnings.
- [ ] Resolve geometry issues.
- [ ] Resolve helper issues.
- [ ] Finish gameplay integration.
- [ ] Finish audio integration.
- [ ] Finish effect integration.
- [ ] Finish the remaining Forge entries.
- [ ] Complete resource accounting.

Implementation notes: [the conversion process](tools/warlock-conversion/REACH-CONVERSION-PROCESS.md) and [the rebuild notes](tools/battle-canyon-rebuild/README.md).

## 6. Queued map conversions

The conversion goal is paused; preserve this order for when work resumes. Keep existing installed maps and the shared DLC bundle intact. Reflection's duplicate entry was intentionally removed.

### 1. Reflection (Reach)

- [ ] Finish scenario integration.
- [ ] Finish physics integration.
- [ ] Finish visibility integration.
- [ ] Finish multi-BSP integration.
- [ ] Finish BSP-root integration.
- [ ] Finish lighting-tag integration.
- [ ] Resolve native H3 water materials; the authored bump-water shader has no exact compiled donor in the installed H3 maps.

### 2. Sword Base (Reach)

- [ ] Resolve water rendering.
- [ ] Restore the missing hidden-BSP payload.

### 3. Powerhouse

- [ ] Correct sky rendering on the H3 MCC candidate that reaches gameplay.
- [ ] Correct cloud rendering.

### 4. Sky Bridge

- [ ] Finish lamp shaders on the H3 MCC conversion.
- [ ] Finish hologram shaders.

### 5. Desolation

- [ ] Inspect the located H3MO archive before conversion.
- [ ] Confirm the source against the current source policy.

### 6. High Noon (Reach)

- [ ] Complete collision conversion.
- [ ] Complete physics conversion.
- [ ] Complete the remaining map conversion.

### 7. Boarding Action

- [ ] Finish Boarding Action using the H3 MCC conversion if it meets the agreed 30 FPS, visual and frame-pacing requirements; otherwise revisit the original CE route.

### 8. Erosion (Halo 4)

- [ ] Convert the inventoried source.

### 9. Impact (Halo 4)

- [ ] Convert the inventoried source.

### 10. Haven (Halo 4)

- [ ] Convert the inventoried source.

Source decisions and attribution remain governed by repository instructions and [map credits](tools/warlock-conversion/MAP-CREDITS.md). Historical evidence remains in [the conversion batch notes](tools/warlock-conversion/MAP-CONVERSION-BATCH.md) and `work/map-conversion-batch/queue.json`; their older ordering does not supersede this list.

## 7. Shelved maps

### Penance (Reach)

Source located.

- [ ] Resolve water conversion.
- [ ] Resolve remaining format issues.

### Breakneck (Reach)

Source located.

- [ ] Resolve water conversion.
- [ ] Resolve remaining format issues.

### Diamondback and Reactor

- [ ] **Diamondback:** multiplayer scripts remain unresolved on the H3 MCC conversion.
- [ ] **Reactor:** multiplayer scripts remain unresolved on the H3 MCC conversion.

These four maps remain shelved by the user's 2026-10-26 decision.

## 8. Forge Island

The Halo 4 source is inventoried. This map was omitted from the revised priority list and was not one of the four explicitly shelved maps.

- [ ] Convert Forge Island once the user assigns it a priority; keep it unscheduled for now.

## 9. Force Cove culling

During the Paradiso/Force Cove rotation test, the user saw the hangar from the Cove side of Forge World and suspected geometry was being drawn when it should be culled.

- [ ] Compare the reported view with the intended shared scenery.
- [ ] Check terrain occlusion.
- [ ] Check visibility data.
- [ ] Compare behavior with the asynchronous-query candidate.
- [ ] Identify the cause of the reported visibility.

The cause is unconfirmed. This remains deferred: the user requested a TODO note only.

## 10. Packaging and maintenance

- [ ] Reconcile the older “three converted maps” packaging item with the current queue.
- [ ] Package ready conversions as shared DLC rather than stock-map replacements.
- [ ] Document a repeatable conversion process using one shared test installation.
- [ ] Remove superseded outputs when appropriate, retaining necessary rollback and diagnostic evidence inside the repository.
- [ ] Never commit game assets.

## 11. PC ↔ Xbox 360 System Link

- [ ] Support System Link between a PC and an Xbox 360.
- [ ] Support mixed sessions with multiple PCs and/or Xbox 360 consoles.
- [ ] Support hosting and joining from either platform using native Halo 3 network behavior.
