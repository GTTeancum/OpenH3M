## Shared construct.map overwritten (2026-11-23) - user will replace it; not agent work

C:\X360\ISOs\H3M\maps\construct.map (one file hard-linked from 37 folders, including the release staging folder
.local\releases\current-live-per-map\console-game and Xenia's game folder) was overwritten with the ho2h3 Sword Base
build by a test copy that wrote through a hard link. No independent original 360 copy exists on C:. Restore it from the
Halo 3 disc / original extraction or a Windows previous version; restoring the one file fixes every link. Test scripts now
delete the link before copying. Sword Base moved to the Isolation slot in the private test folder.

## Priorities (user 2026-11-24)

- Beaver Creek moved up to priority (Halo 2 beavercreek through the Tombstone pipeline; see entry below).
- Advanced Forge clean-room rewrite (user 2026-11-26): fresh implementation from tools/h4-forge/ADVANCED-FORGE.md
  (spec in tools/h4-forge/spec), no Halo 4 code or data; saved layouts stay standard Halo 3 variants.
  Magnets are defined in code. Now: Forge Gulch, Force Cove. Later: other maps incl. Void and Sandbox (stock Sandbox
  items have never had magnets; anchors to author).
- Icebox (ho2h3, s3d_turf) DROPPED (user 2026-11-24). Last build: overlapping decals left out (see below); not play-tested.
- Breakneck (ho2h3, cex_headlong) DROPPED: the visibility fix worked in play, but frame rate is below what is needed;
  dropped "in favor of headlong" (user wording; the exact replacement source is to be confirmed).
- Sword Base: more passes needed later (odd collision spots remain).
- Reflection: the placed-piece collision fix may also explain its stair/ramp collision issues; rebuilt with the fix.

## ho2h3 converted maps - queued issues (user play test 2026-11-23)

- Void Forge crash FIXED 2026-11-24: the converted scenarios' simulation definition table was empty (all converted maps);
  rebuilt and sorted (tools\ho2h3\SimTable.cs). Verified by placing stock and converted items in a traced run.
- Placed-piece collision (all ho2h3 maps) - root cause found and fixed in the converter 2026-11-24: the structure
  physics MOPP had no placed-piece keys (tools\ho2h3\COLLISION-360.md). Sword Base rebuilt: the player now stands on
  the glass atrium ramp where every earlier build fell through (drop test + look-down capture). Other maps not yet
  rebuilt with the fix. User play test 2026-11-24: ramp/walkway collision works on Sword Base; a few odd spots remain (to revisit).
- Reflection stairs: ramps hold at 2 of 3 tested points; Reach's own invisible walking surface (030_cover_walking_surface)
  covers the stairs. Coverage of the step detector is low (Reflection _030: 299 ramps over 3435 step faces).
- Icebox: merged window duplicate removed from draw lists; turf_build_part_28 partly duplicates cluster walls (open).
- Icebox overlapping decals left out (user 2026-11-24): 186 of 615 scenario decals (the fewest that leave no two
  decals overlapping on one plane; ho2h3 decaloverlap, cfg nodecal line). Note: stock maps also overlap decals
  (Guardian 160 pairs, Deadlock 48), so overlap alone may not be the whole cause of the flicker; awaiting play test.
- Breakneck: props lit brightly in dark rooms (user screenshot 2026-11-23); not investigated yet.

- Battle Canyon (ho2h3, High Ground slot in .local\reflection360): PARKED 2026-11-23. Lots of hall of mirrors in play.
  Collision now uses the native draft method (Blender planar dissolve 30 degrees, material delimit, positions unchanged;
  46178 polygons -> 14382 triangles). Hall of mirrors not solved: not cluster visibility (all-visible test unchanged), not
  sky size, not the per-cluster sky index; the "attached sky" list makes a cluster draw sky only. The existing native
  Battle Canyon draft (tools\stock-h3-audit\NATIVE-DRAFT.md) already works on 360 with frame-rate issues; alternative
  assessed for the user: port Halo 2 Beaver Creek from the local H2EK through the Tombstone pipeline. Owner decides.
- Beaver Creek PACKAGED 2026-11-24: .local\pc-port\packages\BeaverCreek_20261124_v2 (final bake, fill lights, foliage,
  Forge palette); installs and plays in the PC port; awaiting user play test. Details: tools\map-review\speed-review\H2-PORT-RECIPE.md.
- Beaver Creek "HD-ish" (user 2026-11-23: Battle Canyon is out, Beaver Creek is in; queued after Icebox and Sword Base,
  not ahead of them): port Halo 2 beavercreek from the local H2EK (\.local\h2ek-source\tags\scenarios\multi\halo\beavercreek)
  through the Tombstone pipeline (H2EK tool extract-import-info / extract-render-data -> H3EK scenario, shader plan from
  H2 bitmaps, sky, bake.py, tool build-cache-file, kit_to_360 / build_scenario_checkpoint; see .local\tombstone\rebuild.sh).
- ho2h3 water (2026-11-23): converted Reach water draws as black patches (Sword Base, Reflection); stock Halo 3 water
  on the same meshes tints the whole view as if underwater. Water is hidden for now (pools show as empty basins).
  Real fix: produce Halo 3 water geometry (water surface part flag / water mesh data) in the converter.
- Sword Base (ho2h3, Isolation slot): hall of mirrors / missing pieces FIXED 2026-11-23 (leaf -> cluster table rebuilt;
  see tools\ho2h3\README.md). Earlier note: hall of mirrors / missing pieces at some
  spawns (survey 2026-11-23: smearing and near-black views next to the gravity lift, whose glow is overblown and may
  be driving the exposure dark). Two active BSPs with no seams between them; ruled out so far: spawns, mesh visibility
  data, cross-BSP PVS, instance flags, bounding spheres.
- Breakneck: the two-sided cleanup broke loading ("players failed to load content") when rebuilt trees needed the
  empty-leaf fallback; such pieces are now left unchanged (fixed). 17 drawable pieces were in no draw list; added.
  Missing-piece reports not yet reproduced.

# Spartan TODO

## Xbox 360 conversion takeover — 2026-11-18

See [conversion closeout](docs/conversion-handoff/README.md) before resuming Sky Bridge, Reactor or Battle Canyon visibility work, or starting the retail Reach Sword Base/Reflection extraction and conversion path. Neither Reach map has verified gameplay; the new cloud converter/checkpoints were lost. This documentation-only closeout does not change the unrelated Spartan/Forge implementation status below.

- [ ] Finish identical-orientation overlap and large-piece creation/physics regressions. Corrected-clearance Base, Round now passes paired snap/pull-away/return/resnap/drop/re-grab; not deployed.

## Forge — Halo 4 scenery manipulation in Spartan

Active scope and evidence: [Scenery manipulation plan](tools/h4-forge/FULL-RE-PLAN.md). Scenery only, all manipulation aspects including movement, rotation, physics and magnets. Stock H3/360 compatibility is mandatory. Everything else stays stock H3; advanced rotation and translation controls remain available. Trait-zone gameplay and unrelated full-editor parity are excluded. Audit the required scenery behavior before replacement implementation.

Current priority (2026-11-12): user parked further RE. Finish and build the existing scenery implementation, then check the reported grab/move/snap/pull-away/release/re-grab flow. Do not resume exhaustive parity auditing or excessive verification.

Current candidate is built with AFM3/H4MP3 data, including the four requested magnet exclusions. It is not deployed or accepted. Original H4 selection, input, movement, rotation, magnets, contact/follow, physics transitions and release are connected to native H3 adapters. A triangular-bank sequence passed snap, pull-away, release, re-grab and re-snap; this does not establish large-piece correctness.

Latest evidence: Base, Round passed the corrected-clearance paired snap, horizontal pull-away, return/resnap, drop, same-piece re-grab and further movement/drop sequence. Elevated solo movement also passed. The old ground fixture started too low relative to model minZ=-1 and confounded detachment with terrain contact. Creation clearance and identical-orientation overlap remain open. See [current evidence](tools/h4-forge/STATUS.md); earlier source-only reports are historical, not current build status.

- [ ] Correct trapped movement after overlapping snaps, including identical-piece cases. User explicitly chose original magnet behavior over a coincident-snap rejection safeguard (2026-11-12); preserve H4 selection/alignment. Native pose-sync correction now allows approximately 23 units of continuous Phased pull-away from the same-facing overlap; Normal-mode penetration recovery remains open. Three current-candidate captures inspected; not deployed.
- [ ] Verify contact/penetration handling and pull-away with other large pieces; Base, Round's corrected-clearance sequence passed.
- [ ] Correct large-item creation and re-grab clearance. Current-candidate airborne Base, Round create/move/drop/same-piece re-grab/move/drop passed with unchanged grab distance and three individually inspected captures. Ground-level creation and other large pieces remain open; see STATUS.md.
- [ ] Fix post-deletion black view: native Bank1x1 record is removed, but final native capture is black. Pitch cancellation restores the original pose and passes; deletion is not accepted. Current native menu selects Normal/Fixed/Phased; pitch preview/acceptance and Base, Round Phased movement/restoration pass. Other axes/pieces, Normal-mode penetration recovery and fresh reload remain open.
- [ ] Finish save/reload coverage for editing-only physics. Current Base, Round Normal/Fixed/Phased sequence, release/re-grab and return-to-player restoration passed; saved property bytes match the ordinary native H3 reference. A fresh reload remains unverified for this candidate. The recorded 2026-10-28 decision prohibits persisting modes or adding companion gameplay behavior.
- [ ] Finish restored-holder/contact/history state handling and parent/child attachment, constraint-rebuild and reconnect cases.
- [ ] Finish marker rendering/lifetime gaps: successful recorded-list reuse/replay, color/combined transfers, partial-resource mapping and multiple captures; verify current rendering in native output.
- [ ] Verify the full grab -> snap -> detach -> release -> re-grab flow before deployment. [Prior review](tools/h4-forge/FORGE-REVIEW-PROOFS.md) is not acceptance of the current candidate.
- [ ] Finish test-staging retention cleanup; automatic approval review blocked removal. Current diagnostics reuse one existing staging directory.

Forge remains largely untested; accepted map visuals do not establish Forge acceptance. Broad RE is parked per the user's implementation priority.

These numbers are references, not a change to the agreed work priorities. Broader validation is outside this list's scope.

1. **HEAVY-MAP PERFORMANCE** — Fix hitches and improve 30 FPS headroom.
10. **PACKAGING AND MAINTENANCE** — Maintain shared DLC and repeatable tooling.

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

## 10. Packaging and maintenance

- [ ] Reconcile the older “three converted maps” packaging item with the current queue.
- [ ] Document a repeatable conversion process using one shared test installation.
- [ ] Enforce artifact retention after every run: one current candidate, one necessary rollback and compact verification evidence; remove temporary test installations and superseded outputs after process exit. Check artifact disk usage before staging another run. See AGENTS.md (2026-11-07).
- [ ] Never commit game assets.

- [ ] Forge detach parity: finish attachment-marker and dependent-child rebuild mapping plus reconnect differences. Override reset/rebuild and connected-body gate are in the built candidate; the remaining attachment cases are unverified.

- [ ] Forge lifecycle: verify event1 editor reset and finish save-restore delivery and surviving-holder recovery. Reset is connected in the built candidate; restoration is not accepted.

- [ ] Finish scenery creation placement: non-phased point correction and definition radius are built, but large-piece native collision placement still fails clearance checks. Authored H4 Phased defaults and nested-query behavior remain open. Verify retained-attachment selection/activation and restored-holder recovery; the legacy Phased disconnect override has been removed.

- Battle Canyon (deferred, user 2026-11-22): remove its four Reach health stations at the next rebuild (rule in AGENTS.md / REACH-CONVERSION-PROCESS.md). Not to be started until Reflection is done.
