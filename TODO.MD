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
- [ ] Finish fresh Blender geometry metadata, collision/physics and H3 material assignments. Nine terrain, one foliage and 90 ordinary materials have saved-field checks; these are not visual acceptance.
- [x] Bind 101 authored tags and one unchanged stock nonvisual tag through short Blender export names (102 tags / 357 used variants after boulder collision authoring). No material slots remain unassigned; water UV and separate design geometry checks pass. Water atmosphere, scenario linkage and remaining geometry metadata are pending.
- [x] Register the native `bcf` shader collection and prefix exported material names. Six aliases resolve to the exact expected tags; the full-scene reimport now reports no missing-shader or duplicate-definition errors.
- [x] Retain one collision child per linked instance definition: 71 identical copies removed, 44 shared definitions retained. The 302 instances with separate Reach physics represent 56 definitions / 207 convex hulls and still need native collision resolution.
- [x] Author the four remaining terrain surfaces with exact stock H3 configurations; replace the initial ground trial with the matching four-layer specular setup. The user approved the existing Reach creek cubemap for the missing cliff reflection texture.
- [x] Preserve stock H3 physical-material choices: 93 authored surfaces use exact source names present in original Standoff; eight empty source names retain their selected stock material, including water. Verify impact behavior in MCC.
- [x] Review defaults in all 90 ordinary shaders: 315 inputs use matching native defaults; 30 differing source scalar defaults are preserved through the official function editor. The 918 selected source functions pass native readback checks, including three parent-template materials.
- [x] Exclude inactive Reach shadow-control entries and retain stock H3 settings. Corrected 26 previously authored surfaces; five new surfaces use the same rule. Saved authored inputs have no duplicate names.
- [x] Bind caustics, sky panel, decorative trim and four smooth materials using stock H3 donors. Smooth surfaces use H3's verified flat normal default; trim uses a shader verified on the stock Spiker world model.
- [x] Compare five original-360 water donors. Longshore's second water shader matches eight shared options. Native H3 options already expose detail scale/steepness; absence of Reach's separate category does not establish a missing feature.
- [x] Compare both official H3/Reach wave arrays through native Tool exports: all 32 top-mip slices match exactly, as do dimensions, formats, mip counts and curves. This does not establish original-360 stock availability or rendered water behavior.
- [x] Preserve arch-rock parallax using the stock Foundry bridge shader from Standoff, the original Reach height texture and H3's zero-reflection control.
- [x] Obtain the user's approval for [glass channel repacking and stock H3 exterior glass](tools/stock-h3-audit/GLASS-MATERIAL-PROPOSAL.md). The three glass shaders are assigned; native checks preserve 2x transparency and 1x specular scale, plus the exterior donor's original Fresnel controls.
- [x] Bind both sky rock/tower materials using Blackout's stock sky setup: retain its zero-RGB base function and the original Reach alpha and separate self-illumination. MCC appearance remains unverified.
- [x] Apply the approved [stock H3 panel reflections](tools/stock-h3-audit/PANEL-REFLECTION-PROPOSAL.md) to the two circular panels and Forge panel; retain Reach artwork/detail/glow. Native source and pixel checks passed.
- [ ] Generate the required local H3 cluster cubemaps with official Tool during MCC preparation and review panel reflections in MCC.
- [x] Bind shared dirty glass to stock Snowbound glass with unchanged Reach artwork/base alpha, native white specular mask and flat normal. All three image checks pass; four skylight meshes retain two-sided transparency and breakable flags. Native Blender assignment WIP captured; actual appearance and breaking remain for MCC.
- [x] Apply approved stock H3 water behavior using Longshore's donor and Reach artwork. Native checks verify 32 source functions and all four imported images; the river color/alpha strip matches exactly after retaining uncompressed storage and native Tool color defaults. Four authored UV channels pass saved-scene and ASS checks; rendered behavior remains for MCC.
- [x] Finish collision-only/lightmap-only lighting metadata; compiled inputs are verified, with baking and MCC appearance still pending.
- [x] Verify Standoff's stock invalid tag and bind it only to the six collision-only box faces and 32 lightmap-only sun faces. Native exporter flag checks passed; this does not resolve emission metadata.
- [x] Resolve 117 source lighting records using the approved native H3 approach: 103 lightmap-resolution selections, 12 emission selections, one chart group and one lightmap type. Saved-scene and ASS checks verify 22,690 selected faces; current official full-map import/readback verifies all 113 lighting variants, including nine emitting variants. Visible world geometry and UVs are preserved through collision separation; other mesh hashes remain unchanged.
- [x] Verify shared H3 lighting inputs through native import: six proposed priority multipliers, original emission RGB/power/quality/focus, power-per-area flags and 0.01 attenuation scaling pass. Original Reach scenario confirms the seven resolution categories.
- [x] Obtain approval for [native H3 lighting behavior](tools/stock-h3-audit/LIGHTING-METADATA-PROPOSAL.md) where Reach bounce ratios, chart grouping and per-face BSP lighting have no matching standard authoring control. Approved 2026-11-04 and applied; baking and reviewing the result in MCC remain.
- [x] Author and verify four water coordinate channels: preserve both original Reach UV sets, reproduce Longshore local info via Tool's measured 0.01 scaling, and retain native default per-vertex velocity. Full ASS readback checks all 42 river triangles / 126 corners. This does not validate physical flow or MCC appearance.
- [x] Inspect original Reach structure design through unmodified Foundry: one water physics surface, two fog sheets and one soft ceiling saved separately; source tag unchanged.
- [x] Author and compile original water physics and the soft ceiling through Blender/official H3 Tool. Native readback matches all 28 convex volumes, flow directions, depth, and 40 oriented boundary triangles; collision data is present. Native Tool requires separate water objects to retain the original convex pieces.
- [ ] Finish water atmosphere and fog: map underwater settings to the 28 native H3 water-group names, resolve the two original planar fog sheets, and link the design to the fresh scenario. Verify behavior in user-driven MCC; render-vertex velocity does not establish physical flow.
- [x] Refresh full ASS export/readback after boulder collision authoring: 102 tags, 357 used variants, 1,177 instances and 301,566 triangles. All four river UV channels pass the 42-triangle / 126-corner check; all 22,690 lighting-selected faces pass actual ASS assignment checks.
- [ ] Resolve full native geometry import errors. The latest official import completes in 7m15s and preserves all 113 lighting variants. The world plane-builder failure remains absent; 34 instance open/degenerate-edge groups and 14 bad-connection errors remain, down from 44 and 17. Twelve portal-leak warnings and two thin-triangle warnings remain. All eleven corrected boulders report no errors; missing-shader and duplicate-definition errors remain absent. These diagnostic outputs are not an accepted build.
- [x] Isolate boulder_low035 without modifying source geometry: a subsecond native import reproduces its 44 edge errors. Native output contains the separate 190-vertex collision mesh and a distinct render BSP; error endpoints predominantly match the render mesh. Resolve render-BSP and collision fidelity separately before choosing repairs.
- [x] Apply documented Precise/material Render Only controls to boulder_low035 only, retaining its original collision child. Saved authoring reproduces the diagnosed native geometry exactly and imports without geometry errors. All 710 render triangles retain winding, UVs match within XML precision, and collision samples improve substantially. Small native position/normal differences remain above strict comparison thresholds; native Blender proof captured, MCC acceptance pending. Other definitions remain unresolved.
- [x] Inventory original native collision structure for all 44 definitions with collision children: 17 have no render BSP, 27 retain one. Preserve that distinction when resolving remaining errors; do not apply the boulder controls indiscriminately. Separate Reach physics hulls still need a verified standard H3 workflow.
- [x] Test the eleven remaining boulders with no source render BSP or extra physics. Ten isolated imports have no collision errors; apply their standard Precise/Render Only controls while retaining original collision children. Fresh saved checks preserve all geometry, normals, UVs, transforms and other flags; full ASS matches the diagnosed inputs. Native numeric differences remain documented for MCC. The west boulder still has three collision errors in isolation and remains unchanged in the map.
- [x] Confirm the ten additional boulder corrections in the full official import: zero errors for those targets, and total error lines fall from 61 to 48. Locate the west-boulder failure at original collision triangle 20 beside seamsealer face 480 on the same source plane; investigate that material boundary before geometry edits.
- [x] Diagnose trim definition 53's missing original render-BSP sealing faces. Isolated standard Blender/H3 authoring retains both collision layers and removes its 38 edge errors; hidden-face UV unwrapping restores native tangent generation while visible UVs stay unchanged. Native geometry/material checks and Blender proof completed; numeric differences remain documented. Applying this approach to eligible saved-map definitions and handling separate physics remain open.
- [x] Isolate the original world mesh and test native Precise controls with its 67 portals. The initial diagnostic removes the plane-builder failure but leaves collision errors. Native error locations identify two thin metal triangles and one sky polygon; the subsequent original-collision workflow resolves the collision errors without deleting visible geometry.
- [x] Test complete original world collision through unchanged Foundry and H3 collision-only/render-only authoring. Saved source geometry, winding, materials and flags verify; the official diagnostic has no collision errors or open native edges. Sampled native deviations and six nearby material-boundary mismatches remain documented.
- [x] Apply that standard world split to the main saved scene. All 59,795 visible triangles exactly match the earlier ASS in positions, normals, UVs, colors, winding and materials; all 56,580 collision triangles match the successful diagnostic. Lighting selections remain intact, and render-only slip flags are cleared. Two native Blender proof views inspected. Visible-triangle/portal warnings and other instance collision/physics remain open.
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
