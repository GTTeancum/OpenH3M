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

Current status (2026-11-04): fresh Reach-to-H3 MCC authoring, step 4 of the
approved process. The earlier implementation was rejected and is not an input.
No MCC acceptance or Xbox 360 conversion has occurred for this fresh build.

- [x] Advance after Claude's cleanup, per the user's "Just move on" instruction; do not reuse the rejected work. Residual history/shared code was disclosed, not certified erased.
- [x] Inventory original Xbox 360 Standoff and select its 99-entry vehicle-free Forge palette.
- [x] Compare stock and MCC dependencies; record MCC-only additions and stock alternatives before authoring.
- [x] Extract original Reach geometry/textures through mod tools and deliver native Blender WIP proof views.
- [ ] Finish fresh Blender geometry metadata, collision/physics and H3 material assignments. Nine terrain, one foliage and 89 ordinary materials have saved-field checks; these are not visual acceptance.
- [x] Bind 99 authored tags and one unchanged stock nonvisual tag through short Blender export names (100 tags / 151 used variants). Water and shared dirty glass remain pending across three variants; native map import is not yet ready.
- [x] Author the four remaining terrain surfaces with exact stock H3 configurations; replace the initial ground trial with the matching four-layer specular setup. The user approved the existing Reach creek cubemap for the missing cliff reflection texture.
- [x] Preserve stock H3 physical-material choices: 92 authored surfaces use exact source names present in original Standoff; seven empty source names retain their selected stock material. Verify impact behavior in MCC.
- [x] Review defaults in all 89 ordinary shaders: 307 inputs use matching native defaults; 29 differing source scalar defaults are preserved through the official function editor. The 912 selected source functions pass native readback checks, including three parent-template materials.
- [x] Exclude inactive Reach shadow-control entries and retain stock H3 settings. Corrected 26 previously authored surfaces; five new surfaces use the same rule. Saved authored inputs have no duplicate names.
- [x] Bind caustics, sky panel, decorative trim and four smooth materials using stock H3 donors. Smooth surfaces use H3's verified flat normal default; trim uses a shader verified on the stock Spiker world model.
- [x] Compare five original-360 water donors. Longshore's second water shader matches eight shared options; Reach's separate detail setting and water-coordinate export remain unresolved.
- [x] Preserve arch-rock parallax using the stock Foundry bridge shader from Standoff, the original Reach height texture and H3's zero-reflection control.
- [x] Obtain the user's approval for [glass channel repacking and stock H3 exterior glass](tools/stock-h3-audit/GLASS-MATERIAL-PROPOSAL.md). The three glass shaders are assigned; native checks preserve 2x transparency and 1x specular scale, plus the exterior donor's original Fresnel controls.
- [x] Bind both sky rock/tower materials using Blackout's stock sky setup: retain its zero-RGB base function and the original Reach alpha and separate self-illumination. MCC appearance remains unverified.
- [x] Apply the approved [stock H3 panel reflections](tools/stock-h3-audit/PANEL-REFLECTION-PROPOSAL.md) to the two circular panels and Forge panel; retain Reach artwork/detail/glow. Native source and pixel checks passed.
- [ ] Generate the required local H3 cluster cubemaps with official Tool during MCC preparation and review panel reflections in MCC.
- [ ] Finish the remaining shared dirty-glass material and water material, plus collision-only/lightmap-only metadata.
- [x] Verify Standoff's stock invalid tag and bind it only to the six collision-only box faces and 32 lightmap-only sun faces. Native exporter flag checks passed; this does not resolve emission metadata.
- [ ] Resolve 117 source lighting records: 103 lightmap-resolution selections, 12 emission selections, one chart group and one lightmap type. Confirm source units and resolution semantics before transfer.
- [ ] Resolve water coordinates: source meshes have two UV channels; the documented H3 workflow needs four. Preserve collision-only and lightmap-only invalid-material surfaces and finish their metadata.
- [x] Refresh the full unmodified ASS export/readback with 100 bound tags: 1,247 instances and 247,855 triangles; three unresolved material slots remain explicitly pending.
- [ ] Verify imported texture color/alpha, normals, reflections and original texture controls against their source inputs.
- [ ] Resolve remaining material/effect gaps with stock H3 assets; obtain the user's decision on the rainbow/decorative-laser import proposal before importing those effects.
- [ ] Import, compile and light using official H3 MCC tools.
- [ ] Test in actual MCC with the user driving: compare Reach appearance; inspect sky, flicker/clipping, collision, traversal, audio, gameplay and Forge.
- [ ] Obtain explicit user approval of the MCC version before ANY Xbox 360 conversion.
- [ ] Apply the established MCC-to-H3 Xbox 360 process with the verified stock asset list.
- [ ] Verify converted visuals, behavior, performance and native limits, then coordinate deployment into the shared installation.

Process: [approved nine steps](tools/stock-h3-audit/REBUILD-PLAN.md).
Evidence and limitations: [fresh source/authoring preflight](tools/stock-h3-audit/SOURCE-PREFLIGHT.md).

## 6. Queued map conversions

Desolation is active by user request (2026-11-04). Sky Bridge is pending final review. Preserve the remaining queue order, existing installed maps and shared DLC bundle. Reflection's duplicate entry was intentionally removed.

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

Pending user feedback

### 4. Sky Bridge

Pending final review (2026-11-04). Candidate36 remains installed; corrected LIVE archive and visual/performance evidence are retained.

### 5. Desolation

Active goal (2026-11-04), using the source selected by the user in Downloads.

- [x] Locate and hash the H3MO archive; extract its map into repository-local work storage and verify the MCC U13 cache and scenario.
- [ ] Complete source geometry/dependency and stock-H3 asset audits before conversion.
- [ ] Convert, validate and prepare Desolation for review through the existing Halo 3/OpenH3M pipeline.

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
