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

Current status (2026-11-04): original-H3 candidate3 built and installed in the
shared installation at 21:31 local, about 41 minutes into the user's one-hour
window. MCC playtest/approval was explicitly waived. The game is open with
normal user controls. Native menu captures pass; map loading, appearance,
traversal, audio and gameplay still require the user's manual review.

The source includes all 13 approved native H3 lights, original wheel animation,
four cabinets with stock Territories markers and the red-base rock. Native
limits pass: 625/640 placed objects, 99 Forge palette entries, 108/256 maximum
quota entries, one small world collision BSP and no large/Havok BSP blocks.
Collision simplification preserves visible world geometry but retains portal
and geometry warnings; incomplete effects/atmosphere/audio remain. See
[native draft and launch instructions](tools/stock-h3-audit/NATIVE-DRAFT.md).

- [x] Advance after Claude's cleanup, per the user's "Just move on" instruction; do not reuse the rejected work. Residual history/shared code was disclosed, not certified erased.
- [x] Inventory original Xbox 360 Standoff and select its 99-entry vehicle-free Forge palette.
- [x] Compare stock and MCC dependencies; record MCC-only additions and stock alternatives before authoring.
- [x] Extract original Reach geometry/textures through mod tools and deliver native Blender WIP proof views.
- [ ] Finish fresh Blender geometry metadata, collision/physics and H3 material assignments. Nine terrain, one foliage and 90 ordinary materials have saved-field checks; these are not visual acceptance.
- [x] Bind 101 authored tags and one unchanged stock nonvisual tag through short Blender export names (102 tags / 363 used variants after two original render-BSP cases). No BSP material slots remain unassigned; water UV and separate design geometry checks pass. Sky binding and scenario linkage now pass native checks; water atmosphere and remaining geometry metadata are pending.
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
- [x] Refresh full ASS export/readback after two original render-BSP cases: 102 tags, 363 used variants, 1,177 instances and 301,630 triangles. All four river UV channels pass the 42-triangle / 126-corner check; all 22,690 lighting-selected faces pass actual ASS assignment checks. World geometry, ten corrected boulders and both new cases match their diagnosed inputs.
- [ ] Resolve full native geometry import errors. The latest official import completes in 8m32s and preserves all 113 lighting variants. The world plane-builder failure remains absent; 32 instance open/degenerate-edge groups and 13 bad-connection errors remain (45 error lines, previously 48). Twelve portal-leak warnings remain. All eleven corrected boulders and both newly corrected render-BSP cases report no errors; missing-shader and duplicate-definition errors remain absent. These diagnostic outputs are not an accepted build.
- [x] Isolate boulder_low035 without modifying source geometry: a subsecond native import reproduces its 44 edge errors. Native output contains the separate 190-vertex collision mesh and a distinct render BSP; error endpoints predominantly match the render mesh. Resolve render-BSP and collision fidelity separately before choosing repairs.
- [x] Apply documented Precise/material Render Only controls to boulder_low035 only, retaining its original collision child. Saved authoring reproduces the diagnosed native geometry exactly and imports without geometry errors. All 710 render triangles retain winding, UVs match within XML precision, and collision samples improve substantially. Small native position/normal differences remain above strict comparison thresholds; native Blender proof captured, MCC acceptance pending. Other definitions remain unresolved.
- [x] Inventory original native collision structure for all 44 definitions with collision children: 17 have no render BSP, 27 retain one. Preserve that distinction when resolving remaining errors; do not apply the boulder controls indiscriminately. Separate Reach physics hulls still need a verified standard H3 workflow.
- [x] Test the eleven remaining boulders with no source render BSP or extra physics. Ten isolated imports have no collision errors; apply their standard Precise/Render Only controls while retaining original collision children. Fresh saved checks preserve all geometry, normals, UVs, transforms and other flags; full ASS matches the diagnosed inputs. Native numeric differences remain documented for MCC. The west boulder still has three collision errors in isolation and remains unchanged in the map.
- [x] Confirm the ten additional boulder corrections in the full official import: zero errors for those targets, and total error lines fall from 61 to 48. Locate the west-boulder failure at original collision triangle 20 beside seamsealer face 480 on the same source plane; investigate that material boundary before geometry edits.
- [x] Diagnose trim definition 53's missing original render-BSP sealing faces. Isolated standard Blender/H3 authoring retains both collision layers and removes its 38 edge errors; hidden-face UV unwrapping restores native tangent generation while visible UVs stay unchanged. Native geometry/material checks and Blender proof completed; numeric differences remain documented. Applying this approach to eligible saved-map definitions and handling separate physics remain open.
- [x] Apply original render-BSP geometry for baseblue_ent and object372 through unchanged Foundry/Blender tools. Saved geometry and full ASS preserve both original collision layers and all visible geometry. Both isolated native cases pass the existing comparisons. The two trims remain unchanged with numeric discrepancies documented.
- [x] Import the separate original Reach sky model through unchanged Foundry, bind all 13 materials to stock H3 configurations, export standard JMS 8213 and compile with official Tool: 6,577 vertices and 11,637 triangles. Native readback verifies all shader references and the active scenario sky. Two actual Blender source-artwork WIP views inspected; their cliffs are overexposed in preview shading, so H3 appearance is not accepted.
- [x] Set up the fresh multiplayer scenario through official ManagedBlam: original Reach initial start/map ID, stock Standoff starting profile, budget 800, all 99 approved vehicle-free Forge choices with matching costs/limits, one active BSP zone, and the compiled water/soft-ceiling design link. Native saved readback passes.
- [x] Place 130 original neutral respawn points, 13 directly matched stock H3 weapons and 16 stock H3 grenades. Verify every position, rotation, spawn setting, stock reference and unique ID through native Tool XML; other scenario sections remain unchanged.
- [x] Audit Guardian's stock Plasma Rifle, invisible respawn marker and Infection haven against MCC. Immediate dependency names match; platform-only fields and the Plasma Rifle's ejection-port recovery difference are recorded. User selected Battle Rifles for the two DMRs and Brute Shots for the two Reach grenade launchers.
- [x] Author and verify the remaining stock gameplay mappings: all 19 weapons, 146 ordinary/invisible respawn points, 500 mode-specific initial markers at the 92 original start positions, 16 CTF/Assault zones, 43 goal/teleporter objects and two permanent grav lifts. Native saved transforms, teams, boundaries and spawn settings pass; H3 mode/team selection and gameplay require MCC testing.
- [x] Import the original wheel, red-base rock, health cabinet and health-pack appearance through unchanged Foundry, retaining their render/collision/physics geometry. Inspect three native Blender source-artwork proof renders; health stations retain appearance without healing.
- [x] Author all five remaining prop materials with stock Standoff shader configurations and Reach textures. Native input/function and texture checks pass, including the shared UNSC decal. Compile wheel, cabinet and red-base rock render models with official Tool; shader bindings and original triangle counts pass. Collision/physics, object placement and wheel animation remain.
- [x] Compile original wheel, cabinet and red-base rock collision with standard JMS/official Tool: no native warnings/errors. Preserve 144, 48 and 750 triangulated faces; refreshed report wording leaves JMS hashes unchanged. Cabinet source material `default` resolves through its original model mapping below; in-game collision remains unverified.
- [x] Build the first WIP MCC cache with official Tool: 1,104,592,896 bytes, successful return. Native lighting changes only the scenario lightmap reference; all other 180 sections match. Three stock animation warnings match compiled animation references/node counts in original 360 and shipping MCC Standoff; no custom fix applied. This unfinished cache is not installed or accepted.
- [x] Compile the wheel, cabinet and rock physics with standard JMS/official Tool; preserve source motion types (wheel box, cabinet/rock fixed). Native nodes/counts/material identifiers match. Cabinet has a thin-hull accuracy warning; wheel/rock native points and bounds differ. These are recorded for MCC collision review, not accepted as exact preservation.
- [x] Create native cabinet/rock model and crate tags, with saved reference/variant checks. Resolve cabinet `default` to its original `hard_metal_thin`, verified in stock Standoff. Objects are not yet placed or included in the first cache; wheel animation and health-pack decision remain.
- [ ] Resolve the health-pack's 564 faces marked for Reach medium-distance detail culling. H3 native part fields have no counterpart; using stock H3 object visibility is proposed to the user, not approved. Export is stopped at this compatibility check.
- [ ] Decide the 23 Stockpile/Headhunter-only markers in [GAMEPLAY-MAPPING.md](tools/stock-h3-audit/GAMEPLAY-MAPPING.md). Omission is proposed, not approved. The seven stock-compatible Infection havens stay; the previously rejected Spartan doll is excluded under the existing instruction.
- [ ] Finish the remaining source scenery/objects/effects, 13 light fixtures, water atmosphere and draft lighting. The three used light definitions and their original fixture references are now read through official tools. Native draft job `2026110401` completed all 31 commands. Data sync reports 14,873 out-of-bounds UV errors; direct lighting reports 673 ray errors. Both and the known geometry/collision failures remain unresolved. No lighting job is running.
- [x] Isolate the original world mesh and test native Precise controls with its 67 portals. The initial diagnostic removes the plane-builder failure but leaves collision errors. Native error locations identify two thin metal triangles and one sky polygon; the subsequent original-collision workflow resolves the collision errors without deleting visible geometry.
- [x] Test complete original world collision through unchanged Foundry and H3 collision-only/render-only authoring. Saved source geometry, winding, materials and flags verify; the official diagnostic has no collision errors or open native edges. Sampled native deviations and six nearby material-boundary mismatches remain documented.
- [x] Apply that standard world split to the main saved scene. All 59,795 visible triangles exactly match the earlier ASS in positions, normals, UVs, colors, winding and materials; all 56,580 collision triangles match the successful diagnostic. Lighting selections remain intact, and render-only slip flags are cleared. Two native Blender proof views inspected. Visible-triangle/portal warnings and other instance collision/physics remain open.
- [ ] Verify imported texture color/alpha, normals, reflections and original texture controls against their source inputs.
- [ ] Resolve remaining material/effect gaps with stock H3 assets; obtain the user's decision on the rainbow/decorative-laser import proposal before importing those effects.
- [ ] Import, compile and light using official H3 MCC tools.
- MCC playtest skipped by the explicit November 4 override; perform the user-driven review in original H3.
- MCC approval gate waived by the explicit November 4 override; this is not visual acceptance.
- [x] Convert and package native candidate3 using the shared converter and original stock assets. Added generic RenderBsp array serialization from the documented H3 layout; the nested-array relocation test passes.
- [x] Verify native format/capacity/header/package integrity and deploy as a distinct Battle Canyon entry in the existing shared installation. Existing custom bundles remain.
- [ ] User-driven native map loading, visual, traversal, audio, gameplay and Forge acceptance. Main-menu rendering alone is not a map pass.

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
