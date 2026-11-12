# Forge correction review — 2026-11-11

### Native menu and pitch acceptance — 2026-11-12 13:40

Same candidate `8c04fa7d579a2cd1fa1f958ffa87eb416a65606450720e3c47274284f99ac121`;
PID7756. Native menu selects all three physics modes, previews pitch1 then2,
and accepts2. Final native saved basis yields1.9999999065 degrees. All captures
individually inspected; the edge changes while the menu remains open.
Cancellation and other axes remain unverified. No deployment.

- [Pitch 1 preview](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/loading-traces/20261112-112536-6476/rotation-preview-one.png)
- [Pitch 1 retained with menu open](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/loading-traces/20261112-112536-6476/rotation-preview-one-held.png)
- [Pitch 2 preview](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/loading-traces/20261112-112536-6476/rotation-preview-two.png)

### Physics lifecycle — 2026-11-12 13:35

Same candidate `8c04fa7d579a2cd1fa1f958ffa87eb416a65606450720e3c47274284f99ac121`.
PID19752 passes diagnostic Normal/Fixed/Phased selection, release, same-piece
re-grab and stock-physics restoration on returning to player mode. Native
saved object properties match the ordinary creation reference byte-for-byte.
`physics-validation.json` and `physics-lifecycle-evidence.log` retain the
checks. This does not verify native menu selection, a fresh reload or console
execution. All three captures individually inspected:

- [First release](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/loading-traces/20261112-112536-6476/physics-first-release.png)
- [Phased re-grab](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/loading-traces/20261112-112536-6476/physics-phased-regrab.png)
- [Player mode restored](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/loading-traces/20261112-112536-6476/physics-player-restored.png)

Not deployed. Physics modes remain editing-only under the recorded user decision.

### Airborne creation and re-grab — 2026-11-12 13:28

Candidate `8c04fa7d579a2cd1fa1f958ffa87eb416a65606450720e3c47274284f99ac121`, PID26188.
Base, Round E2A80004 passes create/move/drop/same-piece re-grab/move/drop.
Grab distance remains7.869545; re-grab retains the dropped pose. No forced
pose or physics override. All three captures inspected individually; exterior
stays outside camera although the piece fills much of the view. Ground-level
creation and other pieces remain open. Not deployed.

- [Created and held](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/loading-traces/20261112-112536-6476/creation-held.png)
- [Same piece re-grabbed](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/loading-traces/20261112-112536-6476/creation-regrab.png)
- [Moved back after re-grab](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/loading-traces/20261112-112536-6476/creation-return.png)

Native sequence evidence: `creation-evidence.log` in the same directory.

### Phased overlap recovery — 2026-11-12 13:23

Candidate SHA256: `8c04fa7d579a2cd1fa1f958ffa87eb416a65606450720e3c47274284f99ac121`. Not deployed.

Native run PID12172 in the reused `20261112-112536-6476` directory now moves
the initially overlapping Base, Round approximately 23 units in Phased mode.
Object reference and body positions agree throughout the logged movement;
return movement works and Normal restores dynamic motion4. Native grab logs
identify E2A30034 both before and after release; re-grab retains distance
7.869545. Normal-mode penetration recovery is not established by this pass.
Original H4 magnet selection/alignment remains unchanged, including coincident
snaps, as expressly requested. Compact records: `pose-sync-evidence.log` in
the same run directory.

All three native captures were inspected individually:

- [Held overlap](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/loading-traces/20261112-112536-6476/pose-sync-held.png)
- [Continuous pull-away](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/loading-traces/20261112-112536-6476/pose-sync-pull.png)
- [Re-grab](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/loading-traces/20261112-112536-6476/pose-sync-regrab.png)

The exterior remains outside the camera. Screenshots support appearance;
the native records establish object identity and displacement. Large-item
creation and other object/mode/lifecycle cases remain pending.

### Current Base, Round correction evidence — 2026-11-12

Candidate SHA256: `9afee87e2e7717d243800cae6fc14c6bfe9c3f73c530617314e75d1327190688`. Not deployed.

Corrected-clearance native sequence passed snap, ordinary horizontal pull-away, return/re-snap, release, same-piece re-grab and further movement/release. Runtime datumE2A30034 stays consistent; original targetE2A10032 clears during pull and returns on approach. Stopping restores the joint at(-51.569447,-190.0297,3.489226). Re-grab retains distance7.869545. Run launch-clock1794503521.3848536 in the reused staging directory. All three captures were inspected individually; exterior geometry stays outside the camera. Captures alone do not prove motion; native movement/target records establish the sequence, summarized in STATUS.md.

| Stage | Native capture |
|---|---|
| Initial snapped pair | [131 seconds](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/loading-traces/20261112-112536-6476/pair-snap.png) |
| Pulled away, target cleared | [139 seconds](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/loading-traces/20261112-112536-6476/pair-detached.png) |
| Same piece re-grabbed after return and release | [154 seconds](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/loading-traces/20261112-112536-6476/pair-regrab.png) |

The older ground-level pair fixture buried the model's lower extent in terrain. Its failed detachment results below are historical diagnostic evidence, not the current corrected-clearance result. Identical-orientation overlap, creation clearance, other pieces/physics modes and remaining lifecycle gaps are not accepted by this pass.

### Base, Round two-second pull, 2026-11-12

Run .local/loading-traces/20261112-105537-11164 closes the flat-face gap, but the two-second backward pull never clears target E2A10032 and stopping restores the snapped pose. Movement at tick876 reaches approximately Y=-190.6843/Z2.0566, then returns to Y=-190.0297/Z1.4892 at906. Same near-half datum E2A30034 is successfully re-grabbed at1072 after the sideways unladen approach; no camera intersection in individually inspected captures133000/136000/141000. Detachment is NOT accepted. Added diagnostic logging of persistent unsnapped target and actual monitor point alongside submitted target, and lengthened the input hold to measure accumulation/saturation. No custom detachment rule or threshold change. No deployment.


### Base, Round flat-face snap observed, 2026-11-12

Run .local/loading-traces/20261112-105129-9644 successfully grabs near half E2A30034 and selects opposed E2A10032. At tick775 the submitted origin changes from Y=-190.1297 to Y=-190.0297, closing the authored 0.1 flat-face gap. All three captures inspected individually; the exterior remains outside camera and the halves form the joined base. Half-second backward input at849 produces only small displacement, then snaps back at864; this is NOT a detachment pass. After drop, native follow has centered the doorway and the attempted regrab misses scenery (no second pickup event). Extended the approach route to two-second pull/return and an unladen sideways move before regrab. These are ordinary process-local controls, no forced held pose or algorithm changes. Next run pending; no deployment.


### Existing-pair route preparation, 2026-11-12

Added a stock saved-layout fixture containing opposed Base Round halves with a 0.1-unit flat-face gap, and a process-local grab/pull/release/regrab/return input route. Run20261112-104348-19044 entered Custom Games because the new option was absent from both Forge lobby selectors; corrected both predicates. Run20261112-104737-25776 entered Forge but aimed through the central doorway and selected a spawn marker rather than scenery. All six screenshots inspected individually; neither run supports a magnet pass. Moved the saved initial/respawn viewpoint 2.5 units sideways to aim at solid wall. Held-object state and geometry remain unforced; corrected viewpoint has not run yet. No deployment.


### Elevated Base, Round comparison, 2026-11-12

Run .local/loading-traces/20261112-103752-26900 used ordinary monitor ascent before creation, then movement/drop/re-grab/movement/drop. Candidate c01aa81a4afe930d82e69098e6c3b9d8e6909ec52948912b30f03e3b54a52723. Requested/adjusted Z17.03 remains unchanged by collision placement; instead it shifts X by one radius6.295636. All three captures (137000,140000,146000) individually inspected: exterior geometry stays outside the camera, but the large piece occupies much of the view. Same held datum E2A80038 is re-grabbed; distance remains7.869545 and pose is retained. No selected magnet target, so this does not verify Base Round mating. Ground-run upward displacement is an environment-dependent native placement-search result, not a new displacement on re-grab. The source wrapper inspection confirms both H4 and H3 use a -1 collision-filter identity at the nested call; changing that to ignore the monitor without further evidence would be guessed. Retain the native query for now. Next practical coverage remains an approach to an opposed Base Round flat face from clear space. No deployment. Exact-path removal of an older completed run's temporary installation was again rejected by automatic approval review with no specific reason; cleanup remains pending.


### Creation-query result, 2026-11-12

Log-only run .local/loading-traces/20261112-103220-15116: requested Z2.0212421, H4 prefix Z2.020146, native collision-placement result Z14.611418. The rise is exactly 2 * radius6.295636. It happens inside native822836D8/8226E590, before object creation/grab; neither snapping nor grab projection introduces it. Original H4 Base Round source chain verified read-only in ca_forge_ravine.map: mode12753 -> hlmt12752 -> bloc12751. Source radius6.8537383, multiplayer block count1, flags at record+28 are0x20000 (Phased bit1 clear). Therefore bypassing collision on an assumed authored Phased flag would be incorrect. Next discriminating check is creation in clear airborne space using the existing ascent route, rather than another guessed magnet fixture offset. Current ground-level setup remains a failed visual case. Nothing deployed.


### Base, Round placement boundary, 2026-11-12

Run .local/loading-traces/20261112-102738-27040 confirms the selected body is already at (-49.5292,-195.87717,15.016592) BEFORE grab initialization, while monitor is (-49.56363,-195.68459,2.01905) looking horizontally along +Y. Radius6.295636, initialized distance7.869545. Thus the excessive height predates magnet selection and re-grab. Follow then turns the monitor upward; regrab does not cause the original height change. All three native captures individually inspected, reproducing the same obstructed view. Added creation-query input/adjusted/output logging to isolate the existing native collision placement boundary. No guessed position offset applied. No deployment.


### Base, Round regression, 2026-11-12

Run .local/loading-traces/20261112-102249-26112, same candidate as the triangular-bank pass. All three captures inspected individually: the large piece fills the camera from creation onward. No target was selected (zero candidates). Held E2A80038 is at approximately (-49.53,-193.21,14.61), far above the saved target. Release/regrab retained its pose but this is NOT a visual or magnet acceptance. Creation/initial grab placement needs diagnosis before changing snapping. Added bounded grab-event logging of held point, monitor point/forward, runtime radius and initialized distance to distinguish collision placement from grab projection. No deployment.


### Native two-piece result, 2026-11-12

Run .local/loading-traces/20261112-101817-25776 used candidate SHA256 10b6fe0679fff6e9800b2ef2ea0a354ca051e759722359d6ebc8b34f9b20f8ac. Target E2A10032 selected at tick773, movement submitted unsnapped pose at848, target cleared at868. Same held E2A80038 re-grabbed at999 without distance jump. Return reacquired target at1063 and aligned at1103. All three native captures inspected individually: first two separated pieces, final opposed banks meeting at lower tips without coincident stacking. This supports this sequence only; Base, Round and arbitrary orientations remain open. No lifecycle failure. No deployment. Automatic approval review rejected the combined evidence-update/temporary-installation-cleanup command; cleanup remains pending.


## Current implementation check — 2026-11-12

Further RE is parked. Candidate is built but not deployed. Native run `.local/loading-traces/20261112-095716-15940` completed the ordinary-input large-piece creation/movement/drop/re-grab/movement/drop sequence on Forge Gulch. Runtime logs show original pickup/drop/pickup/drop events and no original-lifecycle failure. All three native captures (137000, 144000, 147000 ms) were inspected individually: the edge-on large wall remains at the same apparent distance on re-grab and the background moves during the subsequent strafe. This does not prove arbitrary orientations or magnet behavior. Two-piece snapping/pull-away is next; overall acceptance remains open.

The preceding run `.local/loading-traces/20261112-095326-26692` failed with `Unexpected original target submission`. The bridge used stale monitor index64 while current private mapping uses67. Corrected the check to use `monitorIndex`, rebuilt, and repeated the identical route. This run uses no forced object pose. Exact current binary identities are in `work/build-temp/forge-candidate.json`.

The historical failed review below remains for context.


**User review failed.** Overlapping magnet snaps, inability to pull away, and camera intersection after re-grabbing were reported after deployment. The targeted tests below did not cover the complete interaction and do not establish a working Forge system. All three issues are reopened.

Candidate tested: `work/rexglue-sdk/out/win-amd64/halo3mp.exe`.
SHA256: `DE9CB33E45F1A582BCAC9820FB760511C478F3685436055B2A51B432F6345998`.
Deployed to C:/X360/ISOs/H3M/OpenH3M.exe on 2026-11-11 at the user's request, with matching runtime libraries and the verified marker pack (SHA256 341FB93C4D3DB26BF08EEBD6EE2B97AA0DEDA4C737E9C102B847D3AEE2BE6661). DLC unchanged.

## Results

- Numeric rotation changes update the object while the native menu remains open. Accept retains the edit; Back restores the full original pose and coordinate-lock state.
- Newly created Gulch/Cove scenery uses at least `2 * native placement radius + 1` distance, without reducing an existing larger distance. A narrowly scoped held-object correction preserves distances above the native ten-unit cap during push/pull. Release/world/object changes clear this temporary state.
- Small Bank 1x1 retains its original spawn distance: no clearance write occurred in the final run. Its visible placement is clear of the camera.
- Controls checks passed for preview, accept/cancel, Free/Precise state and stale selection rejection. The final native run also verifies pitch 0 -> 1 -> 2 -> 0 in actual object basis records.

## Native evidence

All screenshots in these proof runs were inspected individually. Paths below are relative to this repository's `.local/loading-traces/`.

| Test | Run | Evidence |
| --- | --- | --- |
| Cove rotation and acceptance | `20261111-185541-33216` | Five captures; pitch 0 -> 1 -> 2 before closing, accepted transform retained. Numeric implementation is the same as the final candidate. |
| Gulch cancellation | `20261111-190002-18360` | Five captures; pitch -12 -> -11 -> -10, Back restores the original basis. |
| Gulch airborne Arch Brace | `20261111-190449-33148` | Three captures; complete arch clear of camera. Initial distance 5.8909955 -> 9.09753. |
| Gulch Arena Wall | `20261111-191138-10180` | Three captures; held wall clear of camera. Initial distance 4.994842 -> 16.6285. |
| Cove Arena Wall and native push/pull | `20261111-191903-26196` | Three captures show unobstructed final placement. Runtime log confirms native ten-unit saturation repaired to 16.3685 during inward input; native pose records show movement. Captures arrived together after movement, so they do NOT prove its visual sequence. |
| Final-candidate Bank 1x1 regression | `20261111-192457-3164` | Five captures; unchanged small-item spawn, visible pitch 0 -> 1 -> 2 and Back to 0. Native CSV confirms the corresponding basis matrices. No spawn-clearance write. |

Final-candidate visual sequence:

- [Initial placement](../../.local/loading-traces/20261111-192457-3164/proof-loaded_136500ms.png)
- [Pitch 0](../../.local/loading-traces/20261111-192457-3164/proof-loaded_148200ms.png)
- [Pitch 1, menu still open](../../.local/loading-traces/20261111-192457-3164/proof-loaded_149500ms.png)
- [Pitch 2, menu still open](../../.local/loading-traces/20261111-192457-3164/proof-loaded_151500ms.png)
- [Back restores original pose](../../.local/loading-traces/20261111-192457-3164/proof-loaded_155500ms.png)
- [Cove large wall clearance](../../.local/loading-traces/20261111-191903-26196/proof-loaded_143000ms.png)
- [Gulch arch clearance](../../.local/loading-traces/20261111-190449-33148/proof-loaded_136500ms.png)

## Scope and remaining work

Only process-local input replay and native game captures were used; at most one game instance. Original collision/tag data, normal re-grab, saved-layout format and game timing are unchanged by these fixes. This is targeted correction verification, not exhaustive palette, system-link or console validation. No claim that every Forge feature has been tested.

Deployed for user review; fresh interactive acceptance remains pending. Automatic approval review rejected both the directory cleanup and a narrower verified-hardlink-only cleanup with `blocked by policy`. Temporary staging hardlinks and diagnostic evidence remain; map hardlinks do not allocate duplicate map payloads. No bypass was attempted. Retention cleanup is unfinished and prevents declaring the complete goal achieved.
