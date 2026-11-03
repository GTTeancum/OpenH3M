# Battle Canyon: fresh authoring-pipeline rebuild

## Current status - 2026-11-03

**User walkthrough rejected final-lighting-02 visual quality (2026-11-03).**
The user reports dusk-level darkness at default brightness and a rock-like band
in the sky. The supplied screenshot shows severely dark terrain/buildings and
a broad gray textured strip across the sky opening. This supersedes any
implication that the installed final bake has acceptable lighting.

Read-only comparison in `reference/user-darkness-sky-audit.json` confirms the
compiled and renamed native scenario bind the converted camera: flags 20,
exposure 0, bounds 0..1.8, target -3.321928, sensitivity 1. The older Workshop
port brightness profile does not target this rebuilt cache. Matching values
establish transport only, not correct brightness or functioning adaptation.
The active sky is the original beavercreek_sky model with 13 material slots;
compiled/native nodes and compression bounds agree. Source sky materials
include rocks, mountains and multiple cloud layers. A material name does not
identify the visible faulty strip; geometry/UV/alpha/texture and exposure
behavior still need tracing. No speculative sky removal, new bake, automated
game run or map replacement was performed for this assessment.


Final Medium lighting dataset 115 and official compilation succeeded after the
documented checkpoint recovery. Installed for user testing, not final acceptance.
The single authorized native test is complete. No further tests or bakes are queued.

Run `.local/loading-traces/20261103-143611-30100` reached the 179-second watchdog:
four header checks passed, zero failed. Its sole requested capture (112000 ms)
was inspected: textured canyon geometry, HUD, rifle and colored rainbow appear;
no former oversized cyan symbols. The opening passage remains dark. Brightness,
map-wide traversal, audible audio and full Forge interactions need user testing.

Host-observed frame changes after 125 seconds: median 33.375 ms, p95 33.902 ms,
p99 65.847 ms, maximum 166.594 ms. Of 595 intervals, 8 exceeded 50 ms and 3
exceeded 100 ms. This does not prove sustained 30 FPS or console performance.

Only the existing installed-corrections Battle Canyon map (DLC ID 1733) was
atomically replaced. Previous hash was rechecked immediately before replacement;
all other bundle files were hash-checked unchanged. Previews and mapinfo remain.
Runtime, bootstrap/settings and stock Last Resort were not modified.

| Artifact | Bytes | SHA256 |
|---|---:|---|
| Official compiled cache | 1122832384 | `e19ae03a645a55645001255ad3f6f47b9199805e83634718bf081d74b56a15f8` |
| Native final-lighting-02 fixture | 158822400 | `4e4679c5502c554da76474820488ff5af477a6f61b2630e48cd7052e14b7ac74` |
| Installed Battle Canyon DLC | 158822400 | `0ffce7a1effe86d1b1ad15f52f03a304fcf52dcc2269f831ebfd556e169940b1` |
| Previous installed map / rollback | 198397952 | `bcd19b4179a5cddcce63a584cffc986a64eb85ff9f3c15d21520e7d8599ba9ab` |

Preparation used existing `build_dlc_payload.py --map battle_canyon --source-map
work/battle-canyon/rebuild/native/final-lighting-02.map`, stock read-only maps,
and separate output `work/battle-canyon/rebuild/native/final-lighting-02-dlc`.
Renamed cache identity, scenario ID, header authentication and tag-memory checks
pass. The user's one-test limit supersedes the older instruction for another
DLC run: loading after the rename is explicitly left to user testing.

Evidence relative to `work/battle-canyon/rebuild`: `installed-final-lighting-02.json`,
`native/final-lighting-02-continuation.json`, `native/final-lighting-02-timing.json`,
`native/final-lighting-02-deployment-preflight.json`, `native/final-lighting-02-dlc.json`,
`forge/compile-check/final-lighting-result.json`, `forge/compile-check/result.json`.
Rollback: `native/installed-before-final-lighting-02.map`. Preserve dataset 115;
do not rerun the completed continuation. Three previously recorded stock
animation-node warnings remain in the compiler report.

Next: user selects Battle Canyon in the existing DLC menu and reviews brightness,
traversal/man-cannons, audio, Forge and frame pacing. Saved-layout reload,
system-link and console performance remain unverified.

Source: Battle Canyon, Halo: Reach Anniversary; Crisp/community
[HaloReachScenarios](https://github.com/ILoveAGoodCrisp/HaloReachScenarios), commit
`aa35d15ff50db13da39685ad537430ad78492778`, scene
`data/levels/dlc/cex_beaver_creek/cex_beaver_creek.blend`, original Reach tags and
official H3EK compilation. Crisp/community prepared the authoring scene; this
project supplies H3/360 adaptation. Ryno's Remember Reach port is the replaced
historical installation, not this rebuild's input. See MAP-CREDITS.md.

Retained decisions: nonfunctional health-station scenery; no Spartan doll or dice;
stock H3 equipment instead of armor abilities; eight specified mist/drip placements
omitted; rainbow/sun/laser effects retained. Reusable Forge library preserved.

## Pre-final candidate evidence

Latest native build: `native/forge-integration-16.map`, 155,635,712 bytes,
SHA256 `ad75c010984d9302bc6cc7d4850bd20121117db0b7c3ee81b53f1dc2015ccacf`.
User-authorized ambient omission: eight mist/drip placements and their two
palette entries removed; six retained placements/five types. Official compile
and native cache checks pass. 106 Forge scenery entries retained, dice omitted.
Retains the verified lens-field correction from integration-15. Native opening-view check
passed; not deployed. Draft lighting remains pending final bake.

Integration-15 passed the floating-symbol and stock tripmine placement checks;
see the dated records below. It predates the ambient omission.

Previous integration-14 was identical to integration-12 and still displayed
oversized blue symbols. Its run `20261029-082511-23496` was not a visual pass.

User update 2026-10-29: omit the dice. The regenerated authoring palette has
106 entries, no dice, zero unresolved choices and an explicit omission record.
Integration-13 below is historical and still contains dice; do not deploy it.
The omission supersedes further dice debugging for Battle Canyon.


`native/forge-integration-13.map` is a historical, superseded draft candidate:
149.50 MiB (156,758,016 bytes), SHA256 `edad04e38f3f1459d134920c309b3f2bfd3761249ce92145a37a066c90c950a5`.
It includes 435 placed objects, 71 assigned stock-audio placements, 14 effect
placements, and Forge menus with 19 weapons, 15 equipment, 107 scenery, three
teleporters, nine goals and 19 spawners. Source vehicle menu is empty. The source Forge palette has no unresolved implementation choices in
`forge/scenery-verification.json`; this is not runtime acceptance. The dice
uses normal-mapped pips without parallax under the explicit user decision. Land mine references the native H3 tripmine;
portable shield now uses the native Forge Deployable Cover pickup rather than
its directly deployed effect object. This is a pickup/activation substitution,
not a persistent Reach shield. Draft lighting remains unchanged.

Integration-13 passed official compilation and saved-cache menu validation.
Native run `.local/loading-traces/20261029-062240-612` completed its 179-second
watchdog. All three captures (140000, 145000, 165000 ms) were inspected in order:
the dice is not visible while held or after release. This is a FAILED visual
check, not accepted reusable appearance. Object datum `0x900027b4` exists in
eight snapshots from 140 through 175 seconds, and the native variant records
slot 350, flags `0x83`. Thus creation and placement registration succeed; the
rendering cause remains unresolved. The native crate's bounding radius is zero;
compare original authoring and compiled model bounds before proposing a fix.
Evidence: `dice-placement-audit.json` in that run. Installed map unchanged.

Integration-12 passed the official H3EK compile and finished native menu checks
(106 scenery entries, $5,000 spending budget, no missing labels). The compiler's
three existing stock animation-node warnings remain recorded in the compile
report. Native run `.local/loading-traces/20261028-230406-43600` completed its
179-second watchdog. All three captures were inspected sequentially: the menu
shows the restored light labels and Deployable Cover; the stock pickup is
visible while held with the green Forge hand; it remains visible at floor
level after release. Budget changes from $4,722 to $4,720. The native variant
contains its new slot 350, flags `0x83`, datum `0xf64614d0`. Evidence is saved
as `cover-placement-audit.json` in that run. Collection/activation and an actual
saved-layout reload remain unverified; this is a Forge placement pass only.

Integration-11 restores the Reach-authored $5,000 spending budget and imports
missing English Forge labels from the compiled source. Its finished-cache menu
verifier passes. Native run `.local/loading-traces/20261028-223600-23484`
completed its 179-second watchdog; all three captures were inspected. The menu
closed, the remaining budget read $4,722, and the radius hook received the
expected cover datum `0xf65314dd`. No cover was visible in the captures, so this
is not a placement pass. Read-only equipment-table and native-variant sampling
are enabled for the next scenery check to distinguish creation failure from
an invisible or misplaced object. The installed accepted map remains unchanged.

Follow-up run `.local/loading-traces/20261028-224642-34528` completed the
179-second watchdog. Read-only object snapshots establish that stock cover
`0xf65314dd` exists from 145 through 170 seconds. All three native captures
were inspected and still show no cover. The final native variant contains
no occupied placement referencing that cover; its header retains 350 slots.
The stock cover has zero multiplayer-object metadata records, unlike the
stock deployed tripmine (one). Thus creation itself succeeds; direct Forge
integration, persistence and visible placement remain unresolved. Do not
claim that adding metadata alone fixes the visual issue. Evidence is saved
in that run's `cover-creation-audit.json`, raw object snapshots and native variant.

`check_native.ps1` reuses an existing isolated fixture only after checking its
required files and verifying every file is still a hardlink to the expected
candidate or original input. A stale fixture fails instead of overwriting an
accepted map or creating another duplicate staging build. Equipment sampling
is opt-in; the shared trace tool's default machine/crate scope is unchanged.
Integration-09 reached actual Battle Canyon gameplay in native run
`.local/loading-traces/20261028-214936-28436`. All three native captures
(112000, 135000 and 160000 ms) were inspected: the first still contains
oversized blue glyphs; later close-rock views do not. This does not establish
Forge-object behavior, full traversal or performance acceptance.
The previous integration-06 runtime check also revealed
oversized blue glyph-like shapes in the first capture (world-space placement
is not established). This is an
isolated candidate, not the installed accepted replacement.

Integration-08 includes the stock space crate and seven additional Forge lights.
Integration-07 silently froze the two flashing marker materials despite retaining
their authoring functions. The native importer now uses the existing strict
register-remapping converter for their exact native halogram permutation.
`verify_forge_light_animation.py forge-integration-08` reads the finished cache:
both markers retain two functions with exact converted payloads/periods and
nonempty register routes. The evidence is
`forge/forge-integration-08-light-animation.json`; visible flashing remains
unverified. Animated sampler ranges are rejected pending explicit support.

The user walked draft-preview-09 and reported traversal and tried gameplay
working, with man cannons launching high enough. Keep their force unchanged.
Their green appearance remains a visual review item. This satisfies the
walkthrough prerequisite; remaining conversion corrections still precede the
final bake. The user only discovered WASD, so this is not complete input testing.

The imported anamorphic and rainbow flare bitmap resources have now been
compared using the converter's actual mip-preservation settings. Both match
the expected encoded pixels, resource controls and image records byte for byte
(including all three rainbow mips). The earlier rainbow control mismatch came
from auditing against a single-mip encoding; it is not evidence of a broken
resource. This rules out that specific payload discrepancy, not runtime texture
binding or the cause of the blue glyphs. Evidence:
`placed-effects/flare-bitmap-resource-check.json`.

A controlled native comparison disabled only nine imported lens-reflection
flag bytes. The 112-second shapes persisted; 135/160-second captures had the
normal grenade HUD. All 99 HUD definition/animation tags also match preview09
when allocation pointers are normalized. Do not diagnose these shapes as
flare texture corruption or visible editor objects from a still image alone.
Transient rendering state/capture timing remains under investigation. See
`forge/integration-06-visual-review.json` and `forge/hud-preview-comparison.json`.
The diagnostic was not deployed. Its temporary map/deployment await cleanup;
automatic policy rejected their removal.


Current sequencing, user 2026-10-28: lighting goes last. The user must first
walk around the updated map using existing Draft lighting, with remaining
conversion corrections addressed before the final bake. Low job 114 was stopped
during farm initialization at the user's correction; it is not completed lighting.

User decision, 2026-10-28: remove the decorative Spartan doll. The objective
planner now excludes it. `remove_doll.py` removes the existing staged placement
and palette entry, remaps remaining crate indices, and verifies all other
scenario fields are unchanged. Historical doll/audio recovery notes below are
superseded; that recovery is no longer a prerequisite. Existing Draft lighting
is retained for the preview; cache compilation must be repeated after removal.

### Staged Forge update after integration-06

Later update after integration-08: `audit_stock_forge_lifts.py` proves stock
Sandbox menu counterparts for the Reach permanent lift and vehicle cannon.
The permanent lift uses H3's existing `gravlift_permanent.equipment`; the
vehicle cannon converges on the already selected native Forge cannon. Its
player-force region ignores vehicles, but its separate `phantom05` polyhedron
uses material 3 / phantom type 2, which accepts vehicles and has nonzero force.
Do not infer vehicle support from the player region alone. All original H3
tuning, appearance, durability and menu cost/limits remain unchanged; placed
and user-tested cannons are untouched. Evidence: `forge/stock-forge-lifts.json`.
The scenario writer now accepts the equipment tag group in the scenery menu,
as the original Sandbox menu already does. Authoring readback has 63 entries,
44 unresolved choices, zero missing roots and unchanged unrelated scenario
fields. This staged update is not yet included in native integration-08.

`assemble_forge_scenery.py` now stages 55 scenery entries with 53 unresolved
source choices. This is not yet compiled into integration-06. The Reach space
crate selects the original H3 Orbital/spacecamp crate under the native-asset
policy. `audit_stock_space_crate.py` verifies eight collision vertices per asset,
records the best upright quarter-turn comparison (maximum centered vertex
error 0.020872 world units), checks authoring hashes and confirms the native
map donor. Native H3 fixed motion, dimensions, orientation and materials remain
unchanged. Only the menu is affected, not authored placements. Readback proves
other scenario fields unchanged. See `forge/stock-space-crate.json`.

Do not substitute `crate_multi_single` solely because of its similar name:
its half extents are 0.2076 versus Reach crate_multi's approximately 0.4326.
Likewise Zanzibar's battle_shield is not the Reach portable shield: the latter
has shield vitality/depletion functions and shield-up/down sound attachments.
These entries remain unresolved. Source/target evidence is retained in
`forge/stock-counterpart-roots.json` and `forge/stock-counterpart-physics.json`.

### Remaining palette dependency preparation

`extract_remaining_forge_geometry.py` has exported all 44 pending original
models (23,476,083 bytes of JMS), retaining source/output hashes. It resumes
unchanged exports instead of duplicating work. `compile_remaining_forge_physics.py`
successfully compiled 87 collision/physics outputs in the isolated H3EK
`_battle_canyon_forge` namespace. The blocker has no source collision-model
reference and therefore only a physics output. None is bound into the map yet.

`audit_remaining_forge_physics.py` compares actual source and compiled tags.
It found 39 rigid-body motion differences and 232 convex AABB-extent differences
across the 44 models. In particular, a fixed platform becomes box-motion and
its core extents shrink by a second 0.0164 margin when exported runtime vertices
are fed directly into H3's authoring compiler. Do not accept compiler exit zero
as proof of faithful physics. Source render geometry is untouched.

`prepare_convex_margin_check.py` reconstructs an expanded authoring hull from
its supporting planes and source radius, then compares H3's compiled bounds.
The flat-platform representative recovers its source center/extents exactly.
The broader 43-model convex pass passes the bounds check for 26 and rejects 17;
two rejected bunker hulls are degenerate three-point shapes. Plane expansion
is therefore NOT a general accepted inverse for this compiler's shrink behavior.
The remaining complex hulls require analysis of the compiler/export convention,
not looser tolerances or repeated guessed scaling. Even passing bounds alone
does not prove full hull or rigid-body equivalence. Isolated results are under
`_battle_canyon_margin_check`; no candidate map uses them.
Evidence: `forge/remaining-geometry/{extraction,physics-compilation,
physics-source-comparison,convex-margin-batch}.json` and per-model margin reports.

Follow-up: `audit_convex_shrink_transform.py` compares complete packed vertex
sets, respecting each hull's actual vertex count. Of 179 hulls in models with
matching counts, only 29 fit the measured per-axis affine transform within
1e-5; two are already unchanged. Both bunkers change hull count during H3
compilation. Thus neither universal plane expansion nor universal axis scaling
is established. The thin third hull in `ff_plat_1x1_short` already matched the
source before expansion; expanding it introduced the large X/Y discrepancy.
Use `convex-shrink-transform.json`; do not accept the previous 26 bounds passes
as complete vertex/hull equivalence.

`restore_remaining_forge_motion.py` separately restores source motion only when
body count and node/region/permutation/shape identities agree. It restored 35
bodies and verified motion for 40 models, with every unrelated flattened field
unchanged. Portable shield, Bridge 2x1, Crenellation Full and Teleporter Frame
need explicit body mapping. `motion-restoration.json` records this result.
The geometry compile script recognizes these verified post-compile hashes so
resuming it does not discard restored motion; a resume check launched no new
compiler jobs. All outputs remain isolated from the map.

A read-only structural conversion comparison for the short platform is retained
in `semantic-check-report.json`. Its converter explicitly warns against treating
foreign compiled physics as ready for H3; eight Reach list enabled-child fields
have no target field. No directly converted physics has been accepted or deployed.

Body regrouping is now explained and corrected in isolated compiler outputs.
The exporter's `read_phmo_materials` repeats the local material name in JMS's
second material field, where H3 interprets permutation/region labels. Different
materials therefore split Bridge 2x1, Crenellation Full and Teleporter Frame
into unintended bodies and mislabel the portable shield's regions.
`prepare_forge_physics_labels.py` traces body ownership through list/MOPP
containers, duplicates material slots as needed by scope, and writes the
original permutation/region names while leaving geometry coordinates unchanged.
It prepares all 44 models. Preserve local material names in the first field;
global-material references are distinct metadata and still require restoration.
An empty global name cannot be written as a JMS material line: the parser skips
it and misreads later counts despite returning exit code zero.

`check_forge_body_labels.py` compiles the four previously mismatched cases in
`_battle_canyon_body_check`. It compares named node/region/permutation identities
and complete named leaf-shape membership, then restores the matching source
motion. All four pass, with two bodies for the portable shield and one for each
structure. This supersedes their unresolved motion-mapping status above, but
does not fix their remaining hull or material metadata differences. Evidence:
`body-labels.json` and `body-labels-verification.json` under the geometry stage.

The bunker count mismatch is now explained: H3 represents seven source
three-point convex hulls as triangle primitives (one Low, six Covered), with
the same radius and no extrusion. `verify_bunker_triangle_shapes.py` proves
their initial vertex motion matches a step of one radius toward the vertex
centroid. Total primitive count is preserved; this is not evidence of dropped
collision. It also finds collisions among long compiled convex names, so names
alone cannot establish one-to-one hull mapping for these models.

`restore_bunker_triangle_geometry.py` solves the inverse centroid-shrink
equation for those seven authoring triangles, retains corrected JMS body labels,
and invokes official H3 physics compilation. All seven resulting vertex sets
match Reach within 1e-6 and retain the exact original radius with no extrusion.
The isolated `_battle_canyon_triangle_check` outputs still need the other convex
hulls and metadata corrected; no whole-model acceptance is claimed. Evidence:
`bunker-triangle-verification.json` and `bunker-triangle-restoration.json`.

The subsequent `audit_convex_surface_equivalence.py` compares convex sets using
both sets' supporting planes, rather than requiring identical vertex lists.
Every source vertex must lie within every target halfspace and vice versa;
this permits harmless redundant-vertex removal. The current expanded-plane
outputs pass for only 20 of 179 tested hulls. Empty convex arrays are recorded
as untested, not passes. Neither the earlier bounds passes nor vertex-list
differences establish surface equivalence by themselves. The report is
`forge/remaining-geometry/convex-surface-equivalence.json`.

`restore_forge_physics_materials.py` repairs explicit global-material names in
44 isolated authoring copies, using the corrected four body-mapping outputs
where available. It restores 23 bindings across 20 models. All four requested
nonempty global names exist in the installed original H3 globals material list;
blank source bindings remain blank. Matching uses local material identity and
rejects ambiguous or unsupported mappings. Readback verifies all other flattened
fields unchanged and separately extracts and byte-compares compiler MOPP data
(eight nonempty payloads; the remaining payloads are empty). Evidence:
`forge/remaining-geometry/material-restoration.json`.
These copies remain under `material-restored`, are not deployed, and do not
resolve the outstanding convex geometry or other physics metadata differences.

The next measured transform resolves most of that geometry discrepancy.
`audit_convex_shrink_transform.py` now tests component-wise movement toward the
AABB center, clamped at the center, by the source convex radius. This predicts
172 of 179 compiled convex surfaces (133 identical vertex sets; redundant
vertex removal explains most of the difference). Two further hulls were already
unchanged. This is a measured compiler behavior, not uniform axis scaling or
normal/plane shrink.

`restore_forge_convex_coordinates.py` selects only whole models explained by
that evidence, inverts the component movement before official H3 compilation,
and preserves unchanged hulls. All 37 selected models passed mutual surface
containment and exact radius checks after compilation, including three complex
rock models. Corrected body labels are retained in the JMS inputs. These isolated
`_battle_canyon_coordinate_check` outputs still require body/material metadata
restoration and integration; they are not yet map-ready or runtime-tested.
The two bridge exceptions, brace, flat rock, and both bunkers remain outside
this pass. Evidence: `forge/remaining-geometry/coordinate-restoration.json`.

Both bridge exceptions subsequently pass the explicit
`restore_forge_convex_coordinates.py --bridge-precision-check` path. Their
nominally shared coordinate planes differ by only a few float ulps; H3 removed
a rail corner in the initial compilation. Before applying the measured inverse,
this path merges coordinate clusters spanning at most 8e-6. It then verifies
all six compiled hull surfaces against the untouched Reach source with the
original 1e-5 tolerance, plus exact radii. No tolerance was relaxed. The actual
coordinate changes are recorded in `bridge-precision-restoration.json`.

`restore_forge_physics_materials.py --corrected-geometry` now combines the
39 passing model outputs with named body/leaf membership verification, source
motion, and explicit H3-supported material bindings. Input SHA256 checks reject
stale geometry evidence. The resulting `geometry-metadata-restored` authoring
copies restore 35 body motions and 20 material bindings across 17 models.
All unrelated fields and actual MOPP bytes remain unchanged. See
`geometry-metadata-restoration.json`. These are staged physics components:
remaining body metadata, four exceptional convex-bearing models, the box-only
chair, full render/model integration and runtime acceptance are separate.

Subsequent combined pass: both bunkers now reproduce all 53 convex surfaces
and seven triangle vertex sets/radii. `restore_bunker_triangle_geometry.py
--all-hulls` combines the proven triangle inverse, component-wise convex
inverse, bounded shared-plane normalization, and preservation of unchanged
cores. Three unchanged, extremely thin cores defeat Qhull volume construction;
mutual vertex proximity provides a conservative convex-set distance bound
without changing the geometry or tolerance. Shape correspondence follows the
compiled ordering with triangles removed and checks name prefixes and surfaces;
long truncated names alone are not used to map bodies.

The brace also passes all eight surfaces through the same bounded precision
path. Flat rock still fails two of 30 hulls (indices 6 and 15, errors about
0.001211 and 0.000843); it remains excluded. The combined metadata stage now
contains 42 models, 38 restored body motions and 22 restored material bindings.
Bunker body checks explicitly map source convex leaves to the verified target
convex/triangle leaves before comparing named body membership. Compiler MOPP
payloads are unchanged by metadata restoration. Evidence:
`bunker-full-restoration.json`, `remaining-precision-restoration.json`, and
`geometry-metadata-restoration.json`. The flat rock and box-only chair still
need geometry acceptance; remaining body metadata and complete object/render
integration remain outstanding for this staged set.

All 44 pending models now have geometry plus motion/material corrections
combined in `geometry-metadata-restored`. The chair's three source box matrices
were transposed by export/compilation. `restore_forge_chair_boxes.py` proves
that relationship, conjugates the JMS quaternions and verifies official H3
output rotations, translations, half-extents and radii against the source.

Flat rock is explicitly accepted as a bounded collision simplification under
the user's Battle Canyon rock/terrain simplification instruction, not labeled
exact geometry. Its 28 other hulls pass the original tolerance. The two remaining
hulls have maximum inward surface deviations of 0.00121144 and 0.00092654 world
units, with outward deviation below 5e-8 and unchanged 0.0164 collision radius.
Their volume losses are about 0.10% and 0.0016%. Visible render geometry is
untouched. `measure_flat_rock_deviation.py` measures vertex-to-convex-set distance
using constrained projection in both directions, fingerprints the actual input,
and guards these measured bounds. This is not a blanket tolerance increase.
See `chair-box-restoration.json` and `flat-rock-deviation.json`; the combined
metadata report labels the rock's simplification separately. Remaining body
metadata, render/model integration, full palette behavior and runtime checks
are still required before these components become an accepted map.

`compile_remaining_forge_render.py` now stages official render builds only when
all intended material tags exist. It preserves repeated JMS material slots used
by different permutations, resolves each by unambiguous source shader basename,
and verifies the compiled material references. Shader-collection abbreviations
must use lowercase: the initial mixed-case aliases produced missing-shader
errors even though Tool wrote a render tag. Those failed outputs were replaced
by successful builds with the intended references. Both `crate_multi` and
`wall_s` now compile; 42 models await material tags. The resumable report records
source JMS, material and output hashes in `remaining-geometry/render-compilation.json`.
This is render-component progress, not object integration or visual acceptance.

The base Forge panel's missing `panels_test.bitmap` is not an active dependency:
official Reach evaluation selects specular-from-diffuse and has no separate
specular-mask sampler. Material preparation now clears that unavailable inactive
reference in its isolated flattened authoring copy, retaining the original
source. It records the removal and rejects missing active textures as before.
The shared family now stages 17 shaders; 14 have exact native template matches
and pass official H3 evaluation with unchanged shared constants/textures.
Two change-color-detail mappings remain unresolved, and three staged permutations
still lack exact original-disc shader templates. See the updated authoring plan
and `h3-evaluation-comparison.json`. The native illuminated-template inventory
also confirms the available detail and times-diffuse branches; choosing an
alternative requires preserving their actual color/texture behavior, not merely
selecting a similarly named option.

Primary-color illumination investigation: official H3 `illum_detail` computes
the same two-texture product used by Reach `change_color_detail`, but normally
multiplies it by an authored constant color. H3's other official options prove
that `self_illum_color` can instead be supplied by an object change-color extern.
`prepare_forge_primary_illumination.py` prepares isolated option/definition
copies selecting primary change color while retaining the original detail pixel
function and all other fields. It uses the named enum and verifies readback,
rather than assuming a numeric extern index from another definition listing.
Evidence: `forge/primary-illumination/definition-verification.json`.
This is an authoring route, not a deployed fix: official shader evaluation and
explicit original-H3 native constant-register routing still need verification.
Do not silently freeze Forge illumination to a constant color or treat the
existing native template's fixed-color route as equivalent to this extern route.

The isolated primary-panel compiler evaluation did not pass. H3EK attempted
to generate the custom definition's template, then reported an unavailable
Durango shader compiler DLL and exited abnormally. `evaluation.json` and
`h3-primary-panel-evaluated.log` retain that failure; do not count this material
as evaluated or ready. The supplied standard template
`_0_2_0_1_1_2_5_0_0_0_0_0_0` does exist and has precompiled platform shader data.
Reusing that program would require a verified per-object external-color route
in the template, separately for MCC and original H3; copying its fixed-color
routing unchanged would not implement the requested color behavior. The
isolated panel also records dynamic-versus-per-pixel environment adaptation
and neutral detail/intensity choices, which remain unaccepted. No candidate
map or installed runtime was changed by this compiler investigation.

`audit_pending_forge_dependencies.py` inventories the 44 remaining objects,
their render/collision/physics references, object behavior, model damage,
40 unique shaders, parent chains and bitmap users. It records source hashes
in `forge/pending-dependencies.json`; it does not mark these objects converted.
Use `extract_missing_forge_sources.py` for exact missing archive members with
no overwrite, then refresh the audit. The bitmap pass recovered 48 of 67
references; 19 are absent from the supplied original archive and need
active/inactive parameter reconciliation, not invented replacements.

`evaluate_pending_forge_shaders.py` captured all 40 official Reach
`inspect-shader` evaluations in `forge/source-evaluations`. Process success
does not prove authored textures were loaded: an initial panel evaluation
substituted default diffuse/normal/detail textures while their local sources
were absent. After recovery, `forge-panel-reach-evaluated.log` resolves the
authored panel diffuse, normal and scratch detail. Its child options are all
-1 and inherit the Forerunner metal parent; mapping -1 directly to zero loses
that behavior. These evaluations precede H3 authoring/native template matching.

### Seven additional Forge lights

### Shared Forge architecture material staging

Forge glass donor audit: `audit_forge_glass_templates.py` inventories 98 original
H3 alpha-blended shader permutations without cache-read errors. The direct
two-lobe-Phong/dynamic-environment/standard-bump candidate
`_0_1_0_0_2_2_0_3_0_0` is absent. Cold Storage (`chillout.map`) contains
`_0_1_0_2_2_2_0_3_0_0`, which differs only by a texture-driven specular mask.
Official H3 `specular_mask_fx` samples that texture's alpha; a verified constant
alpha-one stock bitmap would make this mask algebraically equivalent to the
unmasked value 1. This is a donor lead, not yet a selected or verified glass
conversion. Verify the bitmap and Reach/H3 lighting/opacity equations first.
Reach's dedicated glass entry explicitly uses alpha blending and zero area
specular contribution; its evaluated albedo alpha is 2 and must not be silently
clamped during authoring. Evidence lives in `forge/glass/`, including the
original HLSL extracts and `native-template-inventory.json`.

`prepare_forge_glass.py` now stages the glass as an H3 ordinary shader using
that native permutation. The stock `alpha_white` authoring bitmap's BC1 blocks
prove alpha one for every texel in all three mips. All 12 original authoring
function payloads survive byte-for-byte, including the separate alpha/color
functions. `evaluate_forge_glass.py` installs only its owned authoring files and
uses official H3 `inspect-shader`: all shared constants and texture references
match Reach, alpha remains 2, and blend mode remains alpha-blended. The first
evaluation exposed white specular tints; explicitly expanding the source
composite into H3's normal/glancing tint parameters corrected them.

Official shader equations also establish Reach's base dynamic-reflection LOD
as `max(0, (.1 + (0-.5)*2)*4) = 0`. H3's default scale would blur this reflection;
the staged material explicitly uses `env_roughness_scale=0` to preserve that
base LOD. This does not equate the engines' probe blend offsets, intensity,
analytical light kernels or wetness. Reach's evaluation reports one animated
parameter versus H3's zero, despite preserved source authoring payloads; its
generated binding still needs reconciliation before declaring behavior equal.
No new geometry/cache or runtime acceptance is implied by this authoring pass.
Evidence: `forge/glass/authoring-verification.json`, `h3-evaluation.json`, and
the Reach/H3 environment and Phong HLSL extracts in the same directory.

`prepare_forge_architecture_materials.py` uses the official evaluated Reach
options, maps categories by name and flattens complete inherited parameter
records. Sixteen shaders and 17 bitmap tags were prepared under
`forge/architecture-materials/tags`. Thirteen native-template-compatible
shaders and their bitmaps are now in H3EK authoring for compiler evaluation;
the map does not yet reference the new structures. This is not native runtime
acceptance. All 16 parameter/function readbacks passed. Foreign
generated postprocess blocks are cleared entirely for H3EK regeneration.
Five shaders have Reach detail sharpening mode 8 without a target field;
the verification report preserves that explicit rendered-filtering difference.

`evaluate_forge_architecture_h3.py` evaluated those 13 materials in official
H3EK. Its first comparison found three incorrect specular constants and lost
inherited detail textures. The preparation now explicitly expands the evaluated
Reach specular coefficient/tint/Fresnel color and binds the evaluated inherited
bitmap while preserving the child's UV function bytes. Whole-parameter merging
is insufficient when the child overrides UV scale but leaves its bitmap null.
Use tagbridge reference-field overrides here: its bitmap-parameter override
intentionally clears animation and therefore would destroy the authored scale.
The final `h3-evaluation-comparison.json` has zero differences in shared
constants or textures for all 13. Source-only roughness/Fresnel/environment and
wetness terms remain explicit differences requiring shader-level reconciliation.

Thirteen materials select native permutation `_0_2_0_1_1_1_0_0_0_0`, present
in sidewinder, spacecamp and zanzibar. The other three staged materials need
native shader adaptation: two select H3EK self-illumination option 11, absent
from the disc maps, and one selects an unavailable two-detail permutation.
The option-11 authoring mapping is algebraically derived from official HLSL
(primary color blend 1), not proof of original H3 availability.
`native-template-inventory.json` records native names after checking the three
extra MCC categories are all zero. `native-change-color-templates.json`
finds no original-disc shader templates with self-illumination option >=9.

Three further source materials remain outside these 16: the two vertical
panel shaders use Reach `change_color_detail` with no direct H3 option, and
the shared Forge panel base references missing `panels_test` specular data.
Resolve active use before substituting it. See `authoring-plan.json`,
`conversion-report.json`, `verification.json` and extracted official HLSL.

The staged menu now has 62 entries and 46 unresolved source choices. Integration-06
still contains the earlier 54-entry menu. `prepare_forge_light_metadata.py`
verifies all 14 color/intensity function payloads for green, orange, purple,
yellow, white, flashing red and flashing yellow. `prepare_forge_light_shaders.py`
verifies authored marker parameters/animations and original Sandbox shader
support. `compile_forge_lights.py` compiles all seven original render/collision/
physics models using H3EK; `stage_forge_lights.py` binds models, light attachments
and energy materials. The shared process document records the sphere-export
repair, fixed-motion restoration and explicit unsupported Reach fields.

Evidence is in `forge/lights/light-verification.json`, `shader-verification.json`,
`geometry-compilation.json` and `staging.json`. `assemble_forge_scenery.py` readback
verifies other scenario fields unchanged; `prepare_forge_labels.py` appends 30
English labels total while preserving 393 original records. These additions
require the combined cache compile and native visual/Forge check; they are not
installed or accepted merely because the geometry compiler succeeded.

## Process reference

`prepare_forge_labels.py` builds an isolated sandbox locale tag under
`forge/locale/tags`: eight explicit English labels, preserving the existing
393 locale records and complete original text-data prefix. Readback verifies
the appended strings and offsets; other languages remain unassigned for these
new labels. `scenario_forge.py` now transfers those eight labels from the
compiled source's locale table for the fresh Battle Canyon route only. That
transfer still needs the assembled MCC cache/native build check; the current
walkthrough cache has no new Forge entries. Stage the isolated locale tag
together with the assembled scenario before that compile. Evidence:
`forge/locale/verification.json`; no live runtime assets were changed.

### Human walkthrough, 2026-10-28

The user walked around the updated Draft preview and reported that it seemed
fine and everything tried worked. Man cannons launch high enough; retain their
current forces. The user observed a green appearance on the cannons under the
current lighting, which remains a visual-review item. Only WASD controls were
discovered during this run, so this does not establish complete input, combat,
Forge, all-mode or performance acceptance. The requested walkthrough-before-
final-bake step has occurred. Lighting still goes last, after remaining conversion
work and corrections; this feedback is not a request to start a bake immediately.

The isolated scenery menu now also includes the approved decorative health
station: 37 total entries, 18 unresolved source scenery/gadget choices.
Assembly checks the referenced tag is scenery (runtime type 6), with no device
fields, healing entries, functions, attachments or widgets. The Reach menu cost
25 and limit 8 are retained. Its intended English label is
`Health Station (Decorative)`; locale integration and runtime Forge behavior
remain pending and are recorded in the menu report. This is a custom decorative
exception, not a stock-H3 asset or a functional health station. The user's
running walkthrough is unchanged.

The next isolated Forge update selects the native H3 `man_cannon_forge` for
Reach's ordinary/heavy/light Forge cannon choices, following the stock-H3
asset/tuning rule. These converge to one H3 menu entry; Reach strength variants
are not claimed preserved. Current scenery menu: 36 entries, 19 unresolved
source choices. Vehicle cannon and gravity-lift choices remain separate.
`audit_forge_object_metadata.py` checks the eight non-menu stock additions:
the three crates have multiplayer properties, but the five sandbag scenery
tags do not. `forge/non-menu-object-metadata.json` records the exact blocks.
Their Forge placement, manipulation and saved-variant reload remain unverified;
do not infer successful behavior solely from menu serialization or asset presence.

The isolated Forge scenery assembly now contains 35 native entries (previously
27), with 22 unresolved source scenery/gadget choices. A full native object-index
audit adds five H3 scenery sandbag forms, the small barricade, single industrial
crate and military pallet even though they lack native Forge menu entries.
For those eight additions, original H3 objects/labels are retained and Reach
menu cost/limits are recorded explicitly; no native menu values are invented.
Full readback verified the menu and preserved unrelated scenario fields.
All selected authoring roots are available. This remains an isolated candidate,
not a change to the user's running `draft-preview-09` walkthrough.

### Reflection-corrected Draft preview 09 (2026-10-28)

The staged reflection changes compiled and converted to `native/draft-preview-09.map`
(SHA-256 `75d90684a6d708560e611801525a28f6048702ba2c3e53aa5a511c6c4a526715`).
Native run `.local/loading-traces/20261028-155329-40932` reached gameplay and
completed its 175-second watchdog. All three native images were inspected.
The passage, close rock and base wall remain very dark; these views do not
establish visible improvement in the reflection corrections. No full-map visual
acceptance or deployment is implied. Timing in the same 110ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“170 second window:
median 33.37 ms, p95 33.73 ms, maximum 50.53 ms, with capture intervals excluded.
This run is smoother than preview 08, but cache warm-up/run variation prevents
attributing that difference to material changes. Traversal remains unverified.

Cleanup removed the four superseded native diagnostic map binaries
`lit-decals-01`, `aligned-02`, `bounded-03`, `camera-04` and their staged map
hardlinks. Reports remain; `native-materials-05` and previews 08/09 remain.
Exact removed paths are recorded in `reference/obsolete-preview-cleanup.json`.

Further emitter investigation extracted the official H3EK particle spawn,
update, state and property shader sources into ignored
`placed-effects/particle-source-h3`. The spawn shader reads and writes an
already assembled particle state (DX11 copies the spawn-state buffer); it does
not generate the emitter shape or translational offset. The examined update
shader advances position using velocity. These sources therefore do not prove
per-particle translational-offset evaluation or the proposed plane substitute.

### Doll-free Draft preview result (2026-10-28)

After that preview, `verify_lighting_import.py` revalidated 51 local light
definitions and 12 emissive records using official H3 XML export.
`prepare_rock_reflectance.py` then staged the previously researched small-rock
analytical power and distant-cliff reflection mip correction, with official
H3 `inspect-shader` checks. `prepare_terrain_reflection.py --stage` also staged
the validated lowest-mip stock-cubemap derivative for cliff terrain, preserving
the stock bitmap itself and all evaluated numeric constants. These authoring
changes are **not present in draft-preview-08**, have not received native visual
acceptance, and need the next cache compile. No lighting bake was started for
these changes. Draft omits bounce; its dark shadowed surfaces must not alone
be used to justify changing authored light intensities.

`draft-preview-08.map` compiled and converted successfully: 102.37 MiB,
SHA-256 `9d5a351c26f1e56c526d3fd7b676f6b74795cdba1818a1422563f1170ce6f0ca`.
The MCC source tag index contains neither `fifthspartan` nor `ca_doll`.
Native run `.local/loading-traces/20261028-154419-6956` reached Battle Canyon
gameplay. All three native captures (112/135/160 seconds) were inspected:
the canyon passage, nearby rock and base wall render during rotation. The
upper rock lacks the previously reported intense wet-clay highlight in the
first view, but the passage and base wall remain too dark. This is not final
material/lighting acceptance or full traversal coverage. No installed map was
replaced. The authored Forge/effect assembly is still separate from this preview.

`draft-preview-08-timing.json` measures the 110ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“170 second window, excluding
capture intervals: median 33.37 ms, p95 50.15 ms, maximum 317.17 ms. These are
host-observed image changes, not proof of stable 30 FPS or console performance.
Further work must address lighting, complete assembly, traversal and pacing;
the completed Draft bake should not be repeated merely to recompile a scenario.

### Current preview route (2026-10-28)

The medium farm started at 10:51 and failed at approximately 15:04 during final
gather. All four `fgather` logs assert `ref.type>=0 && ref.type<k_faux_object_count`
in `faux_hive.cpp:558`. Dataset `work/editing-kits/h3ek/faux/111` retains the
completed direct-lighting, photon/radiance and exit-illumination work. Its old
06:36 final-gather blobs predate this failed run and must not be treated as its
successful outputs. No final-quality acceptance is implied.

For the user's requested quick in-game preview, run:

```powershell
python -B tools/battle-canyon-rebuild/lightmap.py --quality draft --workers 4 --blob-id 113
```

Dataset 113 is the active draft attempt; the wrapper refuses to overwrite an
existing nondefault dataset. Choose a new numeric ID for a genuinely new run,
and revalidate any live process before restarting. The official driver's only
adaptation is its job ID; a source hash and settings are saved alongside the
generated driver. `direct_only` was initially tried in dataset 112, then stopped
after the official quality guide established that Draft uses fewer rays and is
the appropriate quickest preview. Dataset 111 was not restarted or overwritten.

`finish_preview.py` waits on a specified bake process handle, requires the farm's
completion record, compiles a fresh MCC cache, invokes `build_native.ps1`, and
runs `check_native.ps1`. It refuses failed/stale lighting and requires explicit
cache compilation success. Its native check uses the installed hash-pinned
OpenH3M executable, because the development output has independently changed.
Runtime output/captures remain inside the repository. The resulting captures
and timing require inspection before any acceptance/deployment claim; this
preview does not include the unfinished isolated Forge/effect assembly.

See [Reach conversion process](../warlock-conversion/REACH-CONVERSION-PROCESS.md)
for the evidence ledger and unresolved semantic questions.

The [required stock/shared asset audit](../warlock-conversion/ASSET-REUSE-AUDIT.md)
applies to every asset group before import. The audio recovery notes below are
historical staging work, not authorization to bypass existing H3 equivalents.
`audit_stock_audio.py` and `plan_stock_audio.py` now select native replacements
for nine ambient types (71 assigned placements) and the dripping-water sound. Eight
ambient types have resolved original-disc sound resources; standing water uses
the stock H3 campaign authoring asset and H3 bank fallback described below.
The wheel now uses Last Resort's unchanged `zanzibar_base_turbine_close`
scenery/looping sound as the stock H3 rotating-machinery equivalent. Its loop
resolves to original `zanzibar.map` audio resources; the stock looping track
has no start/end sounds and retains its -5 dB track gain. This is a role-based
stock replacement, not a claim that its timbre matches Reach's wheel recording.
The assembly plan now contains nine substitutions covering all 71 assigned placements,
with zero unresolved ambient roles. Isolated scenario readback verified all
nine palette references and all 73 placement records (IDs reassigned and
palette indices remapped, preserving transforms and other authored fields).
Two records have type -1 and remain unassigned. The earlier inventory incorrectly
used Python's negative indexing to count them against the last palette entry;
both inventory scripts now handle this sentinel explicitly, and the readback
check requires the substituted entries to equal the set actually used.
The assembly now compacts the sound palette from 11 to nine entries, dropping
the unused old `ca_beaver_wheel` and `ca_beaver_wheel_far` references. This avoids
dependency inclusion from obsolete palette entries even when no placed object
uses them. Readback checks the complete old-to-new index mapping, preserves
both -1 records, and compares all other placement fields.
`plan_objectives.py` uses the stock selection report directly and requires
complete coverage of all assigned placements. It no longer requires the old
Reach ambience import/staging report to build the scenario. Therefore a fresh
run need not import the 32 superseded Reach samples as a prerequisite.

`audit_scenario_palette_usage.py` audits all ten authored placement categories.
Only the two sound-scenery records have unassigned (-1) indices; there are no
other out-of-range placement indices. Its report separates unused palette
entries from placed objects, so dependency counts are not mistaken for content.

The eight pending scenery records (273ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“280, palette entry 29) resolve to
`objects/multi/spawning/danger_zone.scenery`. The official Reach tag identifies
multiplayer type 20 as `danger zone`, with `only visible in editor` and
`candy monitor should ignore`, normal weight 10000, and no attached effects,
damage tags or functions. These are distinct from Reach's separate `kill volume`
type. Original H3 assigns type 20 to `territory area`; copying the numeric type
is invalid. The source tag is captured in `reference/danger-zone-source.json`.
An equivalent H3 spawning behavior is still unresolved; the markers have not
been relabeled as kill volumes or accepted as ordinary scenery.
`build_native.ps1` no longer supplies the earlier 32-sample Reach ambience bank;
the custom doll bank remains separate. Historical recovered ambience files are
not inputs to the final native conversion.
The active bake and
installed map have not been changed. Other asset groups still require the
shared-resource audit; audio coverage alone does not meet that requirement.

`verify_effect_assembly.py` creates an isolated scenario from the objective
plan plus all 14 authored effect-scenery records and seven used palette entries.
Readback verifies placement fields unchanged except remapped palette indices,
new unique IDs and cleared editor-only references. Its assembled object count
is 438/640, including the effects; this is an object-count check, not a memory
budget claim. Evidence and the candidate plan are in
`placed-effects/placement-verification.json` and `placed-effects/scenario-plan.json`.
The bake scenario is hash-checked unchanged. Effect conversion losses remain
listed in the report and must be resolved before final staging; the original
objective-only plan does not yet include these effect placements.

`audit_effect_emission.py`, now run by effect preparation, resolves eight
axis-scale omissions as identity transforms with unchanged H3 shape names.
It identifies three genuine failures: both `ca_bc_mist` emitters and the
`ca_beaver_dripping_point` emitter use Reach planes, but the converter produces
H3 sprayers. Their nonuniform scales are respectively (0,7,3) and (0,6,6).
See `placed-effects/emission-geometry-audit.json`; do not accept these defaults.
The official H3 enum offers sprayer, disc, globe, implode, tube, halo, impact
contour/area, debris, line and breakable surface; it has no plane/custom-point
choice. H3's translational-offset property exposes particle-random inputs and
two vector interpolants, but the schema alone does not establish when that
property is evaluated. A line plus randomized perpendicular offset is therefore
only a candidate until runtime/source evidence proves per-particle evaluation.
`audit_stock_emitter_offsets.rs` subsequently scanned 1,575 staged H3 effect
tags with zero read errors. Most of its 443 particle-input hits are inactive
constant mappings; their presence alone is not evidence of varying offsets.
An initially promising example was stock
`objects/equipment/instantcover/fx/shield_collapse.effect`, event 0, particle
systems 2 and 3, emitter 0: input/range variable particle correlation 4,
mapping type 1 flags 40 with stored endpoints 0..1, and unequal offset vectors.
For system 2 those endpoints are (-0.035,0,0) and (0,0,0).
Correction after decoding function flags: 40 is GPU + EXCLUSION, not RANGE.
The constant function therefore does not prove consumption of the particle
range variable. Tripmine's two other nontrivial mappings use system random;
their stored particle-correlation modifier is disabled. The audit now checks
active inputs and flags instead of treating those stored names as behavior.
Neither example establishes per-particle offset evaluation. Exclusion behavior,
line shape extent/orientation and independence of random coordinates remain
unresolved. Evidence: `placed-effects/stock-emitter-offsets.json`.
Embedded stock tags store the offset endpoints as Cartesian real points;
the separately dumped schema's spherical-editor structure is not a safe basis
for writing those fields. Read the actual target tag's field type.

For an active bake, run `lightmap_status.py`. The official workers write actual
per-operation percentages to `faux/111/farm_log_<worker>.txt`, separately from
the warning-heavy `logs/dillum*.txt` files. The helper matches live processes
to the staged H3 tool and excludes progress logs older than `main.blob`.
These percentages describe the current operation, never total bake completion.
Do not restart a working bake just because the parent log is quiet.

Stock-effect reuse order: run `audit_shared_assets.py`,
`compare_stock_effect_bitmaps.py`, `verify_stock_effect_anchor.py`, and `plan_stock_audio.py` before
`prepare_placed_effects.py`. Preparation excludes verified stock replacements
from custom conversion and applies `reuse_stock_effect_assets.py` automatically.
The remaining plasma shader options cannot be mapped by name to H3's ordinary
palettized option. Official Reach `effects/beam` computes
`abs(noise_a-noise_b)` from two independently transformed maps, then shifts
the palette index using alpha. H3's beam shader samples one map's red channel
as the index. `audit_beam_uv_animation.py` reads the actual function blobs:
the first noise map has constant unit scale and zero translation; only the
second map's X translation is nonconstant (type 8 curve, one-second period).
The three entries per map are not three moving channels. A static precombined
bitmap cannot simply be scrolled in place of both maps: the stationary
`hunter_beam` red channel varies along X in 71 of 128 rows (maximum span 255).
That rules out the invariant-background shortcut; see
`placed-effects/beam-static-texture-invariance.json`. Reach's particle `palettized_2d_plasma` additionally
uses depth alpha as the palette's second coordinate. These source functions
are in `placed-effects/shader-source/hrek-beam.hlsl`,
`hrek-particle_render.hlsl` and `h3ek-beam_fx.hlsl`.
Original `riverworld.map` does contain `levels/multi/riverworld/fx/tower_pulse`
scenery/effect plus a projectile effect/contrail. It is an available stock
visual-component candidate only. `compare_tower_donor.py` rejects whole-effect
substitution: it launches projectiles, including damage, rather than looping
the authored beam system.
Five textures have exactly matching decoded RGBA pixels: smoke_fiery_large,
basic_trail, beam, flaming_trail and spark_fiery. The source uses relocated paths;
matching filenames alone were not used as proof. Two flare textures differ and
are not included in that substitution set. Seven isolated staged tags were
updated on the first run, including the splash's native H3 drip-sound reference.
The original disc tags and active lighting-bake inputs are unchanged.

`verify_stock_effect_anchor.py` proves the Reach `fx_anchor` and stock H3
`null_up` helper have identical root and attachment-marker translation,
rotation and scale; the native donor exists in `chill.map`. Reusing that model
eliminates the missing Reach impostor dependency and custom helper geometry.
After these substitutions the effect preparation has 43 jobs, no missing
dependencies in its inventory and no conversion errors. Semantic losses remain;
those counts do not establish that the effects are ready for deployment.

`adapt_effect_occlusion.py` explicitly quantizes the five Reach flare inner-radius
scales to the nearest value in original H3's native enum: 0.1 to 1/8, 0.2 to 1/4,
and 0.05 to 1/16. This is a documented approximation, not exact preservation.
All other inspected fields, including occlusion flags, offsets and fading, are
unchanged. The preparation script applies this step and removes superseded
generated tag files from its isolated staging directory.

Stock mist/drip research also established a misleading name: `ca_bc_mist`
actually emits Timberland particulate particles with turbulence, not the mist
particles used by Valhalla's waterfall. Do not replace it with generic waterfall
mist solely by filename. H3's stock dripping effects use line emitters; Reach's
authored drip/mist plane shapes and axis scaling still need explicit translation.
`compare_atmosphere.py` reads the authored mapping blobs rather than the zeroed
runtime constant caches. `ca_bc_mist` has two layers: 10 particles/sec at sizes
0.01ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“0.08 and 5/sec at sizes 1ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“2, both with 6ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“8 second lifetimes. Its two systems
use plane emitters with radius 0.25 and axis scale (0,7,3). Stock Orbital large/
huge dust uses globe emission, 10/sec, 4ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“15 second lifetimes and sizes only
0.003ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“0.007; Sandtrap's weather dust uses flood-spore particles at 3/sec. These
are not interchangeable whole-effect donors: replacing the source with them
would discard the large translucent layer. No such substitution was made.
Evidence: `placed-effects/atmosphere-comparison.json` and
`stock-atmosphere-inventory.json`. The constant-function decoder reports the
stored output interval separately from a non-ranged constant; it does not
interpret a zero runtime cache as a zero authored value.

`audit_effect_shader_options.py` resolves particle/beam options through the
official Reach and H3 render-method category definitions. Preparation now writes
six embedded method bindings using existing H3 templates (five direct option
translations and the additive-rainbow adaptation below), with
`render_targets=ldr_and_hdr` as H3's added default and only inactive Reach-only
`warp=none`/`depth_fade=off` categories omitted. Readback in
`placed-effects/shader-binding-verification.json` confirms the six option arrays
and template references. This does not claim the remaining methods are supported.
`verify_effect_bindings.py` now performs that readback on every preparation run,
checking each embedded method's entire option array, template reference and
template-file existence. The preparation run verified all six current bindings.
The rainbow's otherwise compatible permutation lacks a staged H3 template;
the full official `H3EK.7z` archive was also queried for
`tags\shaders\particle_templates\_0_1_0_0_0_1_0_0_0_0.*` and contains no files
for that permutation. It is not merely missing from the partial extraction.
`audit_native_effect_templates.py` additionally enumerated 141 particle/beam
template paths across the available original H3 level caches, with zero read
errors and no exact rainbow match. The available additive, depth-faded variant
`_0_1_2_0_0_1_0_0_0_0` selects `distortion_expensive`, not ordinary rendering;
it cannot be selected as an equivalent solely because it supports depth fade.
The rainbow's authored `depth_fade_range` animation blob is a 32-byte scalar
constant (type 1, flags 0x24, output minimum/maximum both 1.0). The displayed
static real field is 0.0, but that does not make depth fade inactive: the
animated value takes precedence. Official H3 particle shader source computes
`saturate((scene_depth - particle_depth) / range)` and multiplies alpha by it.
The earlier inference that this necessarily changes visible intersections was
incomplete: the blend step must also be considered. Official Reach diffuse-only
sampling does not use depth_alpha, and both kits' ordinary render-target
conversion preserves RGB without premultiplying alpha. Microsoft's
[H3 blend-mode documentation](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/shaders/blendmode)
describes additive blending as RGB-based. The isolated rainbow now binds
`_0_1_0_0_0_0_0_0_0_0`, preserving additive RGB with the alpha-only depth fade
disabled. The preparation script asserts the full original option combination;
this is not a general fallback for alpha-blended, lit, palettized or distortion
effects. Native visual acceptance and any ancillary alpha-buffer implications
remain to be checked. The extracted blob and method inspection are in
`placed-effects/rainbow-depth-range.bin` and `rainbow-source-method.json`.
Reach's `palettized_plasma`, `palettized_2d_plasma` and sphere warp also remain
unresolved. Official shader source extracted into the ignored
`placed-effects/shader-source` directory shows these are real additional sampling
operations, not renamed H3 options; do not alias them to plain palettized shading
without an explicit adaptation.

`audit_effect_bitmap_sampling.py` checks all 14 custom effect bitmaps and runs
automatically after effect preparation. Their complete processed pixel payloads
are byte-identical before/after conversion, including mip data and the three
`a16b16g16r16` flare textures. No 8-bit preview is used as precision evidence.
The Reach `Lens Flare gamma 2.2` usage is an authoring preset: these actual
textures already carry the runtime `linear` curve, preserved by conversion.
The stock H3 `light_volume_glow` and `simple_flare` use `Diffuse Map` usage too,
although their own pixels use xRGB. Do not apply those stock curves to the
custom linear pixels or perform a second gamma correction. Reach's tight-bound
quad optimization remains unsupported; its absence does not justify changing
texture color. Scratch pixel exports are removed immediately after hashing.

The expanded ambient selection uses stock H3 energy-beam and open-breeze
scenery for the four distant-energy placements and one ledge-wind placement.
The 27 standing-water placements use the existing H3 `010_jungle` standing-water
asset, not the Reach `ca_water_standing` import. Its original-disc resource is
absent from the available Mythic level-cache inventory; the official H3 authoring
tag's five permutation names all resolve in the existing H3 MCC sound bank.
The native converter therefore needs its existing audio-encoding fallback for
this one family. This is not a claim of native XMA/shared-page reuse for it.
Decoded Reach/H3 samples have the same names but different lengths/hashes;
`compare_standing_water_audio.py` records that distinction rather than asserting
byte identity. Stock H3 playback settings remain unchanged.

`verify_stock_audio_assembly.py` checks an isolated scenario: all eight palette
substitutions resolve, and all 73 sound-scenery placement records are unchanged
apart from reassigned unique IDs. Neither the active-bake scenario nor the
installed map is overwritten by that verification.

The sections below are a chronological work log, including superseded counts
and intermediate claims. They are not a verified end-to-end recipe. The last
MCC intermediate compilation finished (`compile-reflectance-06.log`); its new
rock settings have not been validated in a native candidate. No replacement
is accepted or deployed. All three rock shaders pass the evaluated tint/exponent checks; the subsequent
source audit establishes additional reflectance differences those checks do not
cover. Corrected lighting authoring has been reimported, but not yet rebaked.
The two authored props are now included. Overall reflectance, lighting and
content remain incomplete.

User authorized 2026-10-27. This supersedes using Ryno's compiled H3 MCC
Battle Canyon cache as the source for the replacement. Keep that installed
version until the new map passes native visual/gameplay checks.

## Source and tools

- Original environment: Battle Canyon, Halo: Reach Anniversary map pack.
- Prepared authoring scene: [Crisp/community HaloReachScenarios](https://github.com/ILoveAGoodCrisp/HaloReachScenarios),
  `data/levels/dlc/cex_beaver_creek/cex_beaver_creek.blend`.
- Pinned source commit: `aa35d15ff50db13da39685ad537430ad78492778`
  (2025-09-07, "cex_beaver_creek fixed all portal leaks"). This revision
  opens cleanly in installed Blender 4.5.8. Current upstream was authored with
  Blender 5.1 and produced compatibility warnings in 4.5; it is not the input.
- Source geometry was prepared using Foundry. Retain its authored object,
  material, face, collision, portal and lighting metadata during H3 adaptation.
- H3 ASS export: [General-101 / Steven Garcia's Halo Asset Blender Development Toolset](https://github.com/General-101/Halo-Asset-Blender-Development-Toolset).
  Repository-local checkout and exact revision are recorded in the provenance.
- H3 tags, collision/visibility compilation, lightmaps and MCC cache: official
  Halo 3 Editing Kit. Then use the existing MCC-to-original-H3 converter for
  the OpenH3M/360 output. Preserve native limits and stock H3 gameplay assets.

The previous installed H3 source was Ryno's Remember Reach pack, Workshop
3575686579. It is a comparison reference, not the new build input. Preserve
both source attributions distinctly; this rebuild is not an update by Ryno.

## Historical initial state (superseded by later evidence below)

Source acquired, hashed and inspected headlessly with automatic scripts
disabled. A derived authoring scene now has its ten nonuniform portal scales
baked, with each world-space vertex checked against its original position
(maximum allowed drift 0.0001 source units). The original scene is unchanged.
ASS export and official H3 structure import now succeed. The successful import
reports 34 clusters, 57 portals, 14,540 collision surfaces and 8,110 collision
vertices. No playable cache, completed lightmap, native visual validation or
replacement deployment is claimed yet.

The main terrain has separate visible and collision meshes. Visible triangles
are spatially partitioned into sections of at most 6,000 faces to respect H3's
32,767-vertex and 16,384-strip section limits; they are not decimated. Collision
is simplified under the user's authorization. Its measured maximum new-vertex
distance to the original surface is 0.157 metres; this is not a complete
surface-error or traversal measurement. Source sky/sealing faces stay in the
main BSP, not the visible instances.

`export_geometry.py` translates Foundry face flags, collision proxies, instance
lighting modes and authoring units to General-101 ASS. Blender-scale sources
need a 1/0.03048 conversion on vertices AND instance translations. The
exporter's custom scale alone does not scale translations. `bind_materials.py`
gives each used material an explicit shader-collection directory, avoiding
ambiguous global shader-name searches.

Tag adaptation uses the existing [blam-tags](https://github.com/Zoephie/blam-tags)
converter, revision `5d0509fb75eadb96ac7774542ca0b2c10aed7b00`, with definitions
revision `0b21715e93110a28aaf53bc7122bba5d96b496aa`. `tagbridge.rs` is a headless
wrapper around that converter. Reports record every loss or unsupported field.
201 available bitmap dependencies have been converted without re-encoding
their pixels; bitmap usage enums still need review. 25 referenced bitmap paths
are absent from the supplied Reach kit and are explicitly listed, not silently
replaced. 100 shader tags have been translated; the Reach-only glass group binds
to stock H3 glass. These are intermediate tags, not visually accepted assets.

`plan_materials.py` maps category/option names between games. An authored option
of -1 means default index 0, not the last Python list entry. This is confirmed
by the source arch material's compiled template. `resolve_material_options.py`
sets H3 option counts and canonical H3 template references. Ten shaders need
five permutations absent from the stock kit; `audit_templates.py` reports
native alternatives without silently selecting one. Official `compile-shader`
requires unshipped shader source/compiler dependencies, so its failure is not
evidence that these permutations compiled successfully. The touched stock
terrain template was restored from the official archive.

Inventory: 1,386 mesh objects, 729 lights, 117 materials. Includes 67 portal
meshes, one structure mesh, four water-surface meshes, two planar-fog volumes
and one boundary surface. The main structure has 61,868 polygons before H3
compilation; this is not a claim about final collision index counts. Face
overrides include render/collision modes, lightmap scale, emissive lighting,
and transparency. The ASS exporter does not automatically interpret Foundry
properties; map and audit those authoring settings before exporting. Preserve
instance sharing and vertex attributes, and do not export helper volumes as
ordinary visible/collidable geometry.

Reach Editing Kit found at `Z:/SteamLibrary/steamapps/common/HREK`, with its
tags still in `HREK.7z`. Archive inspection confirms 400 Battle Canyon files
(314,279,619 bytes uncompressed). Nothing has been extracted there or modified.
Original MCC Reach cache exists at
`D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/haloreach/maps/cex_beaver_creek.map`.

H3EK installation completed at `D:/SteamLibrary/steamapps/common/H3EK`.
The compiler, dependencies and selected stock tags are staged inside
`work/editing-kits/h3ek`; official `tool_fast.exe` runs successfully there.
The selected tag set is 30,401 files / 6,222,757,569 bytes, excluding unrelated
campaign levels, dialogue and music. The original archive remains in Steam's
installation; it was not duplicated. Reach's Battle Canyon tags are staged
under `work/editing-kits/hrek` (364 files / 311,917,323 bytes before shared
shader dependencies). Archive progress totals include solid-block processing;
actual staged file counts, not those totals, measure disk usage.

`audit.ps1` loads the real General-101 exporter in headless Blender and checks
the source's face masks and shader dependencies. All face masks match their
stored counts; 756 unique meshes retain instance sharing. Ten instances have
nonuniform scale and require baking before ASS export. Ten used shader tags
live outside the Battle Canyon directory; their exact paths are recorded in
`export-audit.json`. Unused Foundry grid materials are not dependencies.

Those ten shared shader tags have now been extracted. The prepared-scene
audit reports zero missing used shader tags, zero nonuniform scales and no
face-mask errors. Repeat preparation with `audit.ps1 -Prepare`, then verify
with `audit.ps1 -Prepared`. `preparation-report.json` records each correction;
`source/cex_beaver_creek_h3_prepared.blend` is the derived input. This fixes
export compatibility of the portal transforms, not a verified in-game bug.

Remaining semantic translations are explicit: face modes, emissive settings,
Reach lightmap-resolution enum values, chart groups and per-vertex/per-pixel
lighting. Do not treat raw stored enum indices as physical values. H3 instance
names and lighting prefixes are documented in Microsoft's
[original instance-object documentation](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/art/instanceobjects/instanceobjectshome).
Remaining translations and pending entries are recorded by the export; an
imported BSP alone is not a compiled or verified replacement map.

## Confinement and reproduction

All project-created files are under `work/battle-canyon/rebuild`. Source hash,
repository commit and toolset revision are in `source/provenance.json`.
`scene-inventory.json` and `inspect-scene.log` record the successful read.

Use `inspect.ps1` from the project repository to repeat the read-only inventory.
It uses Blender background mode, a repository-local configuration, temporary
directory and scripts/extensions directories. It does not drive desktop input
or save the source blend. No user Blender configuration is loaded or changed.

Next: prepare H3-compatible scene metadata and material connections, compile
with H3EK, lightmap and verify the MCC intermediate, then convert and validate
the native candidate. Specifically inspect the reported rock/ground layering,
flare occlusion, water and full-turn frame pacing before replacement deployment.

### Current rebuild evidence (2026-10-27, continuing)

- The coordinate-correct protected-collision import succeeds: 14,094 collision surfaces,
  7,998 collision vertices, 44 portals and 26 clusters. Rendered terrain was
  spatially partitioned for index limits, not simplified.
- `plan_decal_protection.py` reads original Reach authoring decal bounds.
  `protect_collision.py` freezes all 5,707 terrain triangles covered by those
  bounds during reduction and verifies exact face coordinates afterward.
  The source contains 143 positive-radius placements and one zero-radius
  classic-screen entry, which is explicitly recorded rather than invented.
- All 729 authored scene lights retain their source intensities (energy/300).
  `restore_sky_lights.py` repairs the existing JMS export's empty SKYLIGHT
  section. Official H3 `render-sky` then imports all 101 original sky lights.
- 112 adapted shader tags now reference available native H3 permutations;
  the explicit neutral parameter adjustments are recorded in
  `shader-option-resolutions.json` and still require native visual review.
- `plan_gameplay.py` maps weapon equivalents to stock H3 tags. Objective
  planning translates Reach labels to H3 mode-specific objects; unresolved
  placements remain in `objective-pending.json`, not silently accepted.
- `lightmap.py` runs Microsoft's unchanged `calc_lm_farm_local.py` inside the
  repository with four workers. The aligned draft bake completed, but is not a final visual
  validation. No replacement has been deployed.

### Coordinate correction and native checkpoint (2026-10-28)

The first native `lit-decals-01` checkpoint loaded but failed visual review.
It is diagnostic evidence only and must not be deployed. Comparing all six
compiled BSP bounds with the original Reach BSP identified a missing export
rotation: Foundry's default `y-` scene requires +90 degrees around Z to produce
Halo's +X-forward coordinates. General-101 does not interpret this Foundry
property automatically. `export_geometry.py` now applies the documented
Foundry transform before collision protection, partitioning and ASS export.
`audit_coordinates.py` confirms zero difference on all six world bounds.
This is a source-coordinate correction, not a gameplay camera workaround.

Repeat geometry export with `audit.ps1 -Prepared -ExportGeometry`, then run
`compile_structure.ps1`. That wrapper requires the compiler's explicit
structure-import success message and passes the coordinate audit; a zero
process exit alone is insufficient. Run `stage_decals.py` to restore authored
placements after structure compilation, then `lightmap.py --quality draft`.
The corrected lighting input accepts all 15 air probes and all 659 scenery
probes; the unaligned input accepted only 3 and 190 respectively.

Seven original decal systems and their ten bitmaps have been adapted to
available H3 decal permutations. The plan retains all 144 authored placements.
Final runtime projection coverage still needs checking after the corrected
bake. Thirteen original light placements use H3-compiled helper models with
their original marker orientation. Four Reach crate-based CTF respawn markers
are translated into native H3 scenery markers while retaining their transforms
and team/boundary fields. `objective-pending.json` records the remaining entries.

`extract_placed_dependencies.py` selectively extracts original placement
dependencies, records existing H3 reuse candidates, and lists missing source
references explicitly. It does not copy Reach shader programs into H3 or treat
an absent reference as successfully converted. `placed-dependencies.json` is
the dependency audit, not a completion report.

### Native validation corrections (2026-10-28)

- `aligned-02` crashed in scenario-object preparation after a corrupt variant
  lookup. Diagnostic tracing found a weapon index of 7319 and a null placement.
  Duplicating shared initial spawns into seven mode-specific objects produced
  751 scenario objects, overflowing the original 640-entry variant array.
  `prepare_spawn_marker.py` retains the stock H3 spawn marker with a shared mode
  mask; placement masks restrict the original infection-only spawns. The total
  is now 343. Both authoring and native conversion reject counts above 640.
  `bounded-03` and `camera-04` completed the 175-second process-local check.
- `prepare_camera.py` explicitly selects Zanzibar's shipping camera-effects
  layout. The older H3EK `globals/default` layout lacks exposure brightness,
  delay, sensitivity and bloom colors. The original Reach values now survive.
  Reach's highlight bloom is not H3's bloom threshold, so that field uses H3's
  default. This fixes a conversion loss; captures still fail lighting review.
- `audit_forge_lightmaps.py` independently decoded all ten layers of the two
  converted lighting arrays for `camera-04`. Compressed pixels and compression
  coefficients match the official H3 compiler output exactly. This establishes
  texture transport, not correct authored lighting.
- `audit_native_materials.py` inventories original disc material donors. Of 103
  custom ordinary materials, 93 have exact shipping H3 permutations. The fresh
  profile previously fell through to a generic metal prototype, dropping sky
  emission and normal layers. The new profile explicitly imports the native
  programs and maps named textures, constants, switches and animations. It
  rejects missing donors rather than silently falling back. Neutral added
  normals/reflection and the three missing detail-normal layers are separately
  reported. Generic kit glass uses Ghost Town's stock H3 window material.
  `native-materials-05` is a diagnostic candidate, not an accepted deployment.

The aligned draft lightmapper still reports shader-postprocess failures and
UV-bound warnings; investigate their affected stages before a final bake.
Final bake must use the completed placement set so scenery probes match object
IDs. Remaining objects, audio/effects, Forge entries, native traversal and
visual/performance verification are unfinished. No installed map was replaced.

### Evaluated Reach rock reflectance (2026-10-28)

The user identified a wet-clay appearance on lit rocks. Official Reach
`tool_fast inspect-shader` confirms that its composite `specular_color_by_angle`
parameter evaluates to black normal-incidence tint, RGB (95,104,91)/255 grazing
tint, and Fresnel exponent 7 for the arch rock. Merely copying the editor
parameter into H3 leaves both runtime tints white and exponent 5.
`prepare_rock_reflectance.py` evaluates three ordinary rock shaders with the
Reach tool and authors explicit H3 colors/exponents through tagbridge. The
H3 compiler now evaluates the arch rock colors and exponent identically.
The script checks target compiler values, not just serialized fields. Run it
after generic shader conversion and before cache compilation.

This does not establish a complete reflectance fix: Reach roughness/analytical
power differs from H3's two-lobe power controls. Terrain cliff parameters are
a separate case: Reach's own evaluated cliff-wall layer 0 really uses specular
power 1 and environment contribution 5. Do not classify those values as
conversion corruption or blanket-disable terrain reflections without following
the active shader path. Primary shader-source tags were selectively extracted
from the installed HREK archive (454 files, 2.16 MB), entirely within the repo.
`reference/rock-reflectance-adaptation.json` and evaluator logs record evidence.

The generic walk check 20261028-073901-3436 ended against a wall; its dark capture
is not evidence of outdoor lighting quality. UV source audit finds only four
meshes with second channels and no exact match for the sampled lightmapper
warning. The follow-through below subsequently located the first warning in
generated lightmap coordinates and checked the active compiled stream instead.
No replacement deployed.


### Extended documentation review (2026-10-28)

See [the process reference](../warlock-conversion/REACH-CONVERSION-PROCESS.md#extended-source-review-2026-10-28)
for the source review of lighting units, emissive bounce ratios, scenario
resolution buckets, shader-failure comparisons and normal-map interpretation.
Existing logs separate plate-0 chart-density loss from out-of-bounds errors on
125 other plate sections. Existing inventory excludes stale emissive power and
unset light cutoff as current causes. These findings narrow investigation;
they do not validate a new map. Compact counts and source hashes are in
`work/battle-canyon/rebuild/reference/documentation-review-20261028.json`.

### Mod-tool follow-through (2026-10-28)

The [updated process reference](../warlock-conversion/REACH-CONVERSION-PROCESS.md#follow-through-with-the-installed-tools-2026-10-28)
records the seven investigations, evidence paths and limits of the conclusions.

- Official lighting XML exposes an extra 100x reduction in the bridge's emissive
  attenuation distances. Generic-light distances use a different, correct ASS
  scale. This is an intermediate-unit error, not an intensity-tuning problem.
- Foundry's circle/rectangle indices are copied into ASS without translation.
  All 51 light-definition shapes differ from the original, including 14 spot
  definitions. Reach/H3 compiled enums agree; the authoring boundary differs.
- The first UV warning belongs to generated mesh-0 lightmap UVs. Its terrain
  instance actually uses shared stream 0, buffer 611, with valid normalized UVs.
  Follow-through matched all three coordinate pairs in all 24,114 warnings
  across 125 plates to base-mesh data; every candidate uses a separate shared
  stream. Two plates have identical-coordinate candidates, both with that policy.
- Independent cache readback matches all 567 lightmap UV buffers, all 566 shared
  bindings, all 1,255 instance-lighting records, and all 50 DXN normal base mips.
  All 575 primary geometry buffers retain tangent-frame components within
  0.000978265 packing error. Current MCC 06/native 05 geometry equivalence is
  established by these matches; material revisions are not assumed identical.
- Official `faux_stats` reports 53 instances without lighting. All 53 have no
  render parts or vertex buffer, so this is not evidence of unlit visible props.
- All 43 historically failing shaders now successfully evaluate in official H3
  `inspect-shader`. The older lightmapper's internal failure condition remains
  unidentified; current evaluator success does not validate that older bake.
- Reach's actual lightmap dimensions are 1536x1536; the current H3 arrays are
  1024x1024. Different lighting representations prevent a simple slice-count or
  resolution-bucket equivalence. The H3 chart-density loss is measured.
- Reach emitter bounce ratio has no direct H3 lighting-record/ASS counterpart.
  Color serialization differences are measured, but the CPU lightmapper's color
  contract is not specified by the supplied sources. The historical wet-clay
  capture lacks camera/material-ID data needed to identify its exact material.

Repeat the serialized payload check from the repository with
`python -B tools/battle-canyon-rebuild/audit_research_payloads.py`.
It writes only `work/battle-canyon/rebuild/reference/investigate-payload-equivalence.json`.
The complete saved UV-warning audit is repeatable with
`python -B tools/battle-canyon-rebuild/audit_lightmap_warning_coordinates.py`;
its large intermediate tag dump stays in memory, and only a compact report is saved.
Official tool calls use the staged kit as working directory and repository-local
TEMP/TMP. `inspect-shader` takes an extensionless tag path; XML export requires
an absolute tag input path. Exit code zero alone is insufficient for either.

No new material edits, bake, deployment or game run occurred in this research
pass. The confirmed bridge errors are implementation findings, not a claim
that Battle Canyon's appearance has been corrected.


### Verified lighting bridge corrections (2026-10-28)

`export_geometry.py` now translates Foundry's circle/rectangle indices into ASS
order and applies the same coordinate scale to emissive ranges as geometry.
The prepared scene was exported and reimported through official H3EK.
`verify_lighting_import.py` confirms all 51 light definitions match Reach's
shapes, all 12 emissive ranges are corrected by 100, and other compared lighting
fields are unchanged. First cutoff is 1.5 world units. The coordinate audit
still has zero world-bounds error. Evidence: `lighting-import-verification.json`.
Scenario assembly and the three-rock evaluated-tint check completed afterward.
These are authoring/import checks, not final bake or gameplay acceptance.

Further source inspection found a different albedo/Fresnel blend order and
separate Reach analytical/area controls; see the process reference's material
contract finding. Matching tint fields alone does not prove matching shading.
Four prop metadata tags are staged in `staged-prop-tags` only; their conversion
losses and missing material mapping remain unresolved and they are not deployed.


### Authored prop closure and audio recovery (2026-10-28)

`stage_rock_prop.py` restores the red-base rock metadata and its original
`hard_terrain_stone_rough` model-material mapping, which the generic converter
lost by selecting Reach's old material block. It checks source acceleration
scales and unassigned damage sections before staging.
`stage_decorative_prop.py` includes the original fifth-Spartan decorative prop,
its compiled render/collision/physics models, and its material-effects table.
That table converted without unsupported fields or lost references and binds
the existing stock H3 cloth sounds. No silent removal of its contact effects.

The HREK doll sound exposes zero-filled MS ADPCM/XMA sample fields and a null
pageable resource. Those extracted buffers are unusable and were not imported.
`recover_prop_audio.py` locates all four original permutations by their exact
`data\sound\materials\havok\ca_doll` names in the installed Reach sound
bank, decodes to local 16-bit WAV, and runs official H3EK
`sounds-single-layer sound/materials/havok/ca_doll object_impacts -bank:battle_canyon`.
The staged kit requires the original archive's
`fmod/pc/class_quality_settings_pc.csv` (1,069 bytes). Its absence prevents bank
creation even though tag import reports success. The 22,848-byte generated
`sfx.battle_canyon.fsb` contains all four permutations, independently decoded
back to nonzero PCM. This is payload verification, not an audible in-game check.
The native build wrapper now supplies this additional bank explicitly.
Reference syntax: https://c20.reclaimers.net/h3/h3-ek/h3-tool/#sounds-single-layer ;
actual acceptance evidence is `doll-sound-import.log` and
`reference/prop-audio-h3-verification.json`.

The rebuilt scenario now has 345/640 placements. Remaining explicit pending
placements: two gravity lifts and eight Reach danger-zone markers. Lift
comparison recorded 35 H3EK candidates, including MCC-only entries that must
not be mistaken for original-disc donors. The installed disc index scan
confirms Construct and Guardian lift identities; shared.map is resource data
and was not parsed as a standalone scenario tag index. Candidate force-volume
parameters differ, so no donor has been chosen merely by name.
No final lighting bake, native gameplay acceptance, or deployment in this pass.


### Stock gravity-lift placement (2026-10-28)

The two authored base lifts now reference the original H3 Citadel
`objects/levels/dlc/descent/base_gravlift_descent/base_gravlift_descent.crate`,
confirmed present in the original `descent.map` tag index. Source lift entrance
to exit marker span is approximately 2.256 world units; this donor spans 2.574.
Guardian's short minilift and Construct's 8-9-unit shafts are different fits.
`align_stock_lifts.py` derives placement yaw from the exit marker's forward
vector and translation from entrance-marker coincidence, without changing the
stock asset, forces, audio or scale. It checks identity root nodes and reads
back the authored placement. Current entrance errors are below 0.000001 world
units. Donor exit differences are 0.1495 horizontally and 0.3177 vertically.
Those differences require actual clearance/traversal checks; the donor is not
yet accepted from alignment alone. Evidence: `stock-lift-alignment.json`.

`stage_decals.py` calls this alignment after assembling scenario blocks, making
restaging deterministic instead of accumulating offsets. The local tag shell
needed real-point/Euler-vector setters; the 17-line addition is saved in
`blam-shell-vector-fields.patch`. Apply it in the pinned local blam-tags checkout
and rebuild `blam-tag-shell` using the repository-local Rust toolchain/Cargo
cache and `work/battle-canyon/rebuild/blam-target` output. No engine edits.

Current object count is 347/640. The eight pending Reach danger-zone markers
remain explicit: H3's multiplayer-object enum has no danger-zone type. Do not
map numeric type 20 directly; H3 type 20 means territory area. This distinction
needs a behavior-preserving treatment, not an enum cast.

A new official **medium** lighting bake started with corrected light shapes,
emissive distances, both authored props and aligned stock lift placements.
Log: `lightmap-medium-corrected.log`. Its output is not accepted merely because
it starts or emits intermediate files. Final native visual, audio, traversal
and performance validation remain outstanding.

User clarification on the two gravity lifts: relevant Reach force/exit values
may be copied if needed to fit the passages, using native H3 item fields and
without engine changes. The stock candidate is retained for the first native
check; exact stock tuning is no longer an approval blocker for these lifts.
The user subsequently clarified that this is a reusable Reach-to-H3 decision;
see the [shared decisions](../warlock-conversion/REACH-CONVERSION-PROCESS.md#reusable-user-decisions-2026-10-28).

The native check now enables the existing read-only `--sample-observer` probe
alongside the bounded three native captures. This records camera position and
forward vector from the targeted process so future material/geometry attribution
can use coordinates rather than guessing from screenshots. The legacy probe
also emits Gulch boundary margins; those margins have no meaning on Battle
Canyon and must not be used as validation here. Probe addresses remain tied
to the check wrapper's verified executable hash.

### Health stations: decorative conversion decision (2026-10-28)

Retain all four authored health-station appearances as nonfunctional scenery,
per the user's reusable Reach health-station decision in the
[shared process](../warlock-conversion/REACH-CONVERSION-PROCESS.md#reusable-user-decisions-2026-10-28).
At this historical checkpoint implementation was pending; the then-current
medium lighting bake does not include these four scenery replacements.

Inspection of the original Reach `health_station.device_control` establishes
that its visible model is `objects/equipment/health_pack/health_pack.model`.
Its control type is `health station`, triggered by player touch, with action
string `device_health` and `pickup_health.sound` on activation. These device
fields must not survive in the decorative replacement: use an H3 scenery tag,
retain the original model appearance and all four authored transforms, and
omit healing, interaction prompts and pickup audio. Do not use an invisible
or removed control as a substitute for preserving the visible station.

Verify the model's geometry/material dependencies separately before assembly;
the station tag itself is only a reference to that model. Rebuild the scenario
with four scenery placements and include them in the placement budget and
final lighting/visual verification. Do not describe this policy decision as
an implemented or tested conversion.

`prepare_health_station.py` now prepares the original model, three render
material slots (body, rubber and UNSC decal), eight bitmap references and all
four placement transforms under `work/battle-canyon/rebuild/health-station`.
Geometry extraction reports 964 render triangles, 44 collision triangles and
one physics convex. No active-bake inputs or installed game files are changed.
The generated report records native template availability for all three slots.

The rubber material inherits eight parameter records from
`spartan_rubber_template.shader`. Generic conversion drops that parent reference.
`flatten_shader_parameters.rs` copies the complete missing records, including
animated functions, into a staging copy before conversion; Python readback
asserts their equality. It rejects parent chains and locked parent settings.
Build this example using the same pinned blam-tags checkout/toolchain as the
other helpers. The original Reach source remains unchanged. Do not copy the
scalar `real` values alone: they can be zero while animated parameters carry
the authored value.

The missing `spartan_test_illum.bitmap` is an inactive leftover: the rubber
shader selects self illumination `off` (Reach's definition uses
`calc_self_illumination_none_ps`). Its unused reference is bound to stock H3
black; active body illumination is retained. Native shader compilation,
model-material metadata restoration, creation of the nonfunctional scenery tag,
scenario assembly and in-game appearance checks remain outstanding.

Subsequent health-station preparation now creates a genuine H3 scenery tag,
with runtime type 6 checked against stock `shotgun.scenery`, no device fields,
and empty functions/attachments/widgets/health-pack blocks. Its original
`hard_metal_thin` model material is restored. `compile_health_station.py`
successfully compiled render, collision and physics through H3EK; the collision
compiler reports 26 surfaces, 48 edges and 24 vertices. All three shader
inspection logs contain their compiled entry-point tables.

`plan_objectives.py` appends four scenery placements copied from the original
control transforms. An isolated `health-station/placement-check.scenario`
readback verified all four positions/rotations/scales exactly, scenery object
type 6 and zero control placements. The planned total is now 351/640. The
active-bake scenario has not been changed: these additions require the next
scenario assembly and final lighting/native appearance checks. Compilation
and isolated readback do not establish in-game visibility or lighting quality.

### Medium-bake ray-plane diagnostic investigation

The active medium bake logs `shooting rays away from the plane!` during direct
illumination rasterization. Its four workers remained live with increasing CPU
time. Old pcast/radest/extillum/fgather logs in `faux/111/logs` predate this run;
their presence does not prove that the current run reached those stages.

`audit_ass_normals.rs` read all 261,030 exported triangles. No nonfinite geometry,
zero-length corner normals or nonpositive/nonfinite instance scales were found.
Nine meshes contain opposed corner normals or a degenerate triangle.
`audit_source_normals.py` checks those meshes in the original Reach Blender
source without saving changes. Opposed-normal counts match in seven of the
eight affected meshes; the reactor emitter base has two in source versus one
in export. The source comparison does not justify a blanket normal repair or
establish that normals cause this diagnostic.

`audit_lightmapper_diagnostic.py` statically inspects the unmodified official
tool, recording its SHA-256 and the diagnostic's containing unwind span.
At `0x1401ec904`ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“`0x1401ec968`, the branch calculates ray-plane parameter
`t = (d - dot(n, origin)) / dot(n, direction)` (zero denominator yields zero).
The warning path tests nonpositive `t`; after logging it rejoins processing at
`0x1401ec9d6`, rather than aborting there. This establishes the branch condition,
not which authored surface produces it or whether the final bake is acceptable.
No geometry, lights or compiler binary were changed to silence the message.

### Authored ambient sound recovery (2026-10-28)

`prepare_ambient_audio.py` inventories all 73 source sound-scenery placements:
nine scenery tags, nine looping tags and nine sound tags. The 18 scenery/looping
metadata tags convert with zero unsupported fields, dropped references or
truncations. Their nine sound tags reference 32 exact named permutations found
in the installed original Reach MCC `haloreach/fmod/pc/sfx.fsb` bank.

Run `recover_ambient_audio.py`, then `restore_ambient_playback.py`, then
`stage_ambient_audio.py` before regenerating `plan_objectives.py`.
The recovery imports original recordings through H3EK, rebuilds the dedicated
`sfx.battle_canyon_ambient.fsb`, and decodes all 32 compiled samples to verify
nonzero audio. Its size is 1,422,368 bytes; the existing four doll samples stay
in their separate bank without duplication. The native build wrapper supplies
both banks. No original disc sound bank is modified.

Incremental imports encountered FSBank error 7 even though tags were imported.
The [documented FMOD-bank recovery procedure](https://c20.reclaimers.net/h3/guides/sounds/rebuild-fmod-banks/)
uses `report-sounds` and `export-fmod-banks`; the script follows that procedure
and requires successful full-bank decoding afterward. It tolerates only that
specific interim bank error, not arbitrary importer errors. Reach's
`ambient_nature_details` class maps by name to H3's supported `ambient_nature`.

`copy_tag_scalars.rs` restores explicit compatible playback fields onto the
officially compiled sound tags. Readback verifies gain, pitch, attenuation,
pitch-range settings and per-permutation gain/skip values, while other inspected
fields remain unchanged. This preserves the fluorescent pitch of -800, distant
energy pitch of +500 and under-glass pitch of +200, rather than importer defaults.
Reimporting audio must be followed by restoring these playback settings again.

An isolated scenario assembly verifies all 73 ambient placement records against
the translated source, apart from deliberately reassigned unique object IDs.
The plan now counts sound/effect scenery toward the conservative native capacity
check: current planned total 424/640. Active-bake scenario inputs remain at their
previous assembly. Native audible playback, final scene assembly and full-map
validation are still outstanding.

### Valhalla tower donor comparison (2026-10-28)

`python -B tools/battle-canyon-rebuild/compare_tower_donor.py` compares the
original H3EK tower effect with the authored Reach laser effects and records
source hashes and timing in `placed-effects/tower-donor-comparison.json`.
Valhalla launches two projectiles (including a damage projectile), with a
non-looping half-second event. Battle Canyon uses looping beam systems.
Do not substitute the complete Valhalla effect: that changes both behavior
and potentially damage. Individual visual components remain candidates,
not established shader equivalents. The selective donor extraction contains
only 10 files totaling 118,867 bytes; the archive extraction summary was not
the size of the extracted selection.

### Combined scenario checks

`verify_effect_assembly.py` now runs `verify_combined_scenario.py` after
assembling the isolated candidate. This checks every planned scalar edit and
cross-type field copy, palette indices, unique IDs across all object classes,
and the original 640-object capacity. The current assembly has 438 objects;
2,208 edits and 80 cross-type copies match the plan. Two sound records remain
explicitly unassigned, as in the source.

`audit_combined_dependencies.py` follows references with the isolated effect
tags ahead of the staged H3EK tags, recording missing assets and parse errors
in `placed-effects/combined-dependency-audit.json`. This is an authoring
reference check, not native resource availability or visual validation. Neither
check modifies active bake inputs or the installed map.

The first combined dependency audit traced 3,684 tags without parse errors.
Its 217 missing references include authoring-only or inactive shader parameters
and must not all be treated as active runtime omissions. It identified a
concrete missing gel bitmap referenced by custom spotlights 5 and 7.
`prepare_spotlight_gel.py` converts that map-specific texture into isolated
`supplemental-tags/tags`, checks conversion losses and compares decoded base-mip
RGBA pixels against Reach. The pixels match; native light projection remains
to be checked. The dependency resolver now includes this staging directory.
The active bake inputs have not been changed.

`classify_missing_references.py` checks missing bitmap parameter names against
all available platform sampler lists in the selected authoring templates. The
first pass found 136 reference uses absent from those lists, 101 without enough
template evidence, and three uses present in the template (including a repeated
plasma-pistol dependency). This is not a blanket waiver for missing tags.
For `ca_bcreek_cliff_walls`, the absent `ca_bcreek_cubemap` is actually replaced
by `shaders/default_bitmaps/bitmaps/default_dynamic_cube_map` in the official
Reach evaluation (`reach-ca_bcreek_cliff_walls-evaluated.log`, texture14).
Compare H3 evaluated behavior against that fallback before adding an invented
cubemap. The other active use belongs to an MCC plasma-pistol PBR shader;
its relevance must be checked against native stock-weapon substitution.

After adding the isolated gel and removing duplicate graph traversal, the
reference audit visits 3,685 tags with no parse errors and 216 distinct missing
paths. The refreshed sampler classification has 130 unused-by-template uses,
84 unavailable-template cases, and two selected-sampler uses (cliff cubemap
and MCC plasma pistol). Counts describe references, not runtime failures.

An isolated H3 `inspect-shader` run now confirms the same named dynamic-cubemap
fallback as Reach for cliff terrain; the original shader hash is unchanged.
`reference/cliff-terrain-reflection-audit.json` records both evaluator outputs.
Reach evaluates `env_roughness_offset=25`; H3 has no same-named constant.
The kits' default cubemap pixels also differ. Neither finding alone proves
the native visual cause. Confirm the selected environment sampling path before
applying a blur or brightness adjustment. No terrain override was made.

### Battle Canyon Forge equipment decision (2026-10-28)

The assembly chain also runs `assemble_forge_teleporters.py` after weapons.
It selects the original Zanzibar sender, receiver and two-way menu entries,
matches their references, labels, costs and limits against H3EK, and checks that
all unrelated scenario fields remain unchanged. Its isolated output is
`work/battle-canyon/rebuild/forge/teleporters-candidate.scenario`; evidence is
`forge/teleporters-verification.json`. The field-copy helper explicitly supports
these three menu blocks. This does not establish runtime Forge behavior.

The user explicitly chose to replace Reach's armor-ability category with stock
Halo 3 equipment. The user clarified that this applies to Reach conversions
overall. `AGENTS.md` and the [shared process decisions](../warlock-conversion/REACH-CONVERSION-PROCESS.md#reusable-user-decisions-2026-10-28)
record the rule; the following is Battle Canyon's implementation evidence.
`assemble_forge_equipment.py` reads the original `zanzibar.map` Forge equipment
menu and matches all 15 entries against the official H3 authoring scenario.
It preserves the native references, labels, prices and maximum counts. The
three extra campaign equipment entries in the MCC authoring file are not part
of that native menu and are not imported.

The menu contains four grenade types, bubble shield, power drain, trip mine,
gravity lift, regenerator, radar jammer, flare, deployable cover, overshield,
active camouflage and custom powerup. Reach armor abilities are not implemented.
`copy_forge_equipment.rs` copies the four named fields explicitly because the
authoring donor and assembled scenario use different block-layout versions.
Readback matches the donor entries and all unrelated scenario fields remain
unchanged. `verify_effect_assembly.py` invokes this step automatically, producing
`work/battle-canyon/rebuild/forge/equipment-candidate.scenario` and its
`equipment-verification.json`. This is isolated assembly, not deployment or
completion of the remaining Forge categories.

`audit_forge_palette.py` inventories all 161 Reach palette variants across nine
categories against installed native map object identities. Its output keeps
unresolved mappings explicit; matching basenames are candidates only.

`assemble_forge_weapons.py` follows the equipment step. It maps all 22 authored
non-grenade weapon/turret choices from the human and Covenant categories onto
19 distinct native H3 entries, using the existing gameplay substitutions and
stock H3 mounted turrets. Grenades are already in the equipment menu. Duplicate
equivalents merge into one menu entry. Original `sandbox.map` supplies the
labels, prices and maximum counts; the MCC authoring donor has different limits
(for example shotgun16 versus original8), so native values explicitly override
those fields. Readback verifies the complete resulting menu and unchanged
unrelated scenario fields. Output: `forge/weapons-candidate.scenario`, with
source-to-target coverage in `forge/weapons-verification.json`.

The authoring donor is extracted narrowly with 7-Zip from H3EK.7z into
`work/battle-canyon/rebuild/forge/stock-donor`, selecting only
`tags\levels\dlc\sandbox\sandbox.scenario`. No additional game install is
created. The reusable field-copy helper accepts only the audited equipment,
weapon, teleporter, goal and spawner menu blocks. Remaining Forge categories
are still pending.

`audit_native_forge_menus.py` reads all seven menu blocks from installed native
caches, retaining cache/scenario identity, object reference, label, price and
maximum count. The initial inventory contains 2,341 entries across 24 maps and
308 unique object references. It is a donor lookup, not proof that differently
named Reach/H3 objects behave identically or that their resources are resident.
For example, H3 already has the six screen filters and golf props under different
paths; Reach golf ball is a crate while H3's menu references a vehicle.

`assemble_forge_objectives.py` follows teleporters and exposes the nine original
Sandbox mode-specific goal entries, preserving their native limits and costs.
Reach's three generic objective shapes are not copied as H3 objective type
numbers. Authored placement translation remains handled separately by
`plan_objectives.py`. The result is `forge/goals-candidate.scenario` and
`forge/goals-verification.json`; readback proves all nine menu entries and
unchanged unrelated fields. Native Forge operation remains unverified.

`assemble_forge_spawners.py` then supplies the 19 native Sandbox initial spawn,
respawn and respawn-zone menu entries through the same named-field copier.
Output is `forge/spawners-candidate.scenario`, with readback evidence in
`forge/spawners-verification.json`. The source cinematic-camera entry, weak/anti
zone semantics and editable safe/soft-safe/kill/soft-kill volumes remain
unresolved; adding the native menu does not declare those source features done.
The complete assembly chain checks 2,208 placement edits, 80 cross-type copies,
438 placed objects and all five copied menu blocks. None of these serialization
checks substitutes for native visual, traversal or performance validation.

`assemble_forge_scenery.py` adds 27 audited native scenery-menu entries after
spawners. This includes identical-path props and explicit H3 counterparts for
Covenant barriers/batteries/crates, six screen filters, golf/soccer props, the
damage sphere and red/blue lights. Original cache menu records supply references,
labels, prices and limits; `write_forge_scenery.rs` writes them through the H3
authoring schema. Full menu readback and unrelated-field equality are checked.
`forge/scenery-verification.json` retains the per-entry donor and 30 unresolved
scenery/gadget choices. Structure categories are also unfinished.

`recover_forge_stock_assets.py` recovers missing official H3EK dependencies into
`forge/stock-assets/tags`, stopping at already staged authoring tags. The first
bounded recovery produced 19 files totaling 160,844 bytes, with no missing
references at that boundary. It deliberately does not copy an existing tag's
entire dependency graph; the combined audit remains responsible for that graph.
An earlier broad walk reached campaign scenario dependencies and was stopped;
its generated copies were removed. Nothing was installed over live bake inputs.
The final isolated scenario in this chain is `forge/scenery-candidate.scenario`.

### Invisible blocker audit (2026-10-28)

`audit_structure_blockers.py` records original Reach and official H3 authoring
crate/model/physics fields with file hashes and native cache donor identities in
`work/battle-canyon/rebuild/forge/structure-blocker-audit.json`.
Ten corresponding box blockers have equal box half-extents, convex radius,
rotation and fixed motion type. Their local origins differ: Reach raises the
collision box by 0.5, 1 or 2 units; H3 centers it at zero. Therefore an existing
Reach placement cannot retain the same transform when replaced by its stock H3
counterpart. Apply the rotated local offset when converting placements, after
checking model/render alignment; preserve native H3 physics. Do not derive the
offset from the object's bounding sphere (box_xxl demonstrates a different
bounding offset than the physics translation).
Reach wall_s uses a polyhedron, and no corresponding H3 authoring tag was found
in the staged kit or targeted archive extraction. It remains unresolved.
These findings do not establish complete visual or runtime equivalence, nor
shared-resource reuse. No menu substitution was made by this audit.

### Stock blocker palette assembly (2026-10-28)

The ten audited box blockers now use original H3 crate/model/physics identities
in the isolated scenery menu. Source and donor hashes (including inspected
render/model/physics dependencies) are checked before selecting the mappings.
This modifies menu choices only, not existing placement transforms. The render
models have small marker bounds; these are collision blockers, not visible wall
meshes. The source-local physics offset remains relevant to any authored
placement conversion.

The complete isolated assembly chain passed after this addition: 47 scenery
entries and 18 English labels, with all 393 existing English-locale records and
original UTF-8 data preserved. The palette report now includes the previously
unassembled structure groups, so its 62 unresolved choices include those groups
rather than indicating a regression from the earlier scenery/gadget-only count.
Stock root recovery reported no missing authoring roots. Existing staged asset
dependency closure and native runtime placement remain unverified. No live map
or bake inputs were changed. Evidence: forge/combined-assembly-check.log,
forge/scenery-verification.json, forge/locale/verification.json.

### Map-specific Forge prop geometry (2026-10-28)

`compile_props.py --include-forge` now extracts original Reach geometry and runs
H3EK render, collision and physics compilation for blue-base rocks01, blue-base
rocks02 and the Forerunner wall, in addition to the existing red-base rock.
All four completed. They reuse the already translated rock-small/panel-wall-c
materials. The compiler check accepts both first creation and successful physics
updates, so rerunning no longer incorrectly fails on an existing physics tag.

`prepare_forge_prop_metadata.py` converts the three added model/crate pairs into
`forge/map-props/tags` for review. Their source acceleration axes are all unity,
maximum vitality is zero and unsupported damage-section links are unassigned.
Conversion reports retain the Reach impostor/shadow-bias/Forge-phased limitations.
These six metadata tags are not yet staged into the map or menu: model material
bindings, dependency closure and runtime behavior still require completion.
The doll remains excluded. No lighting bake or live-map deployment occurred.

### Map-specific Forge prop integration (2026-10-28)

`stage_forge_map_props.py` binds each compiled collision material to an existing
H3 global material: rock01 uses hard_terrain_stone_rough; rock02 and the wall use
hard_metal_thick_for. The generic model conversion had an empty material block;
the staging step reconstructs it from compiled collision material names and
checks those names against H3 globals. Render shader references and compiled
render/collision/physics references are checked before metadata is staged.

The three objects are now in the isolated Forge menu with authored Reach costs
and limits, guarded by model/crate hashes. Scenery assembly verifies 50 entries;
59 source choices remain unresolved across all scenery/gadget/structure groups.
Locale verification now covers 21 added English labels while preserving all
393 original records and UTF-8 data. Native conversion includes these label IDs
only for the fresh Battle Canyon path. Compiled-cache and runtime validation
remain pending; installed maps and lighting are unchanged.

### Forge dependency closure and red-base reuse (2026-10-28)

`audit_combined_dependencies.py --forge` now traces the assembled Forge scenario
with locale/supplemental/effect/official-tag/isolated-stock lookup roots. The first
50-entry audit parsed 4,952 tags without parser errors and found 299 unresolved
references across the full candidate; it is not a clean-build claim. The three
new prop chains each reach 91 identities and have only one unresolved reference:
shaders/shader_templates/_0_1_0_0_0_0_0_0_0_1.render_method_template. Verify this
shader template in H3EK-compiled output; do not blanket-remove missing references.
Per-prop reachability summaries now accompany full audit results.

The existing red-base rock used by the playable scenario is now also exposed
in Forge by the same tag identity, avoiding duplicate geometry. Its stone
material, model references and metadata hashes are verified. Current assembly
has 51 scenery entries, 22 added English labels and 58 unresolved source choices.
The previous 50-entry dependency report predates this menu addition; rerun it
for the next candidate. Future audit reports include the candidate SHA256.
No new map cache, lighting bake or deployment was performed in this step.

### Compiled prop shader resolution and Forge lifts (2026-10-28)

`verify_compiled_prop_shaders.py` checks actual MCC tag references and salts in
the current H3EK cache. Both prop shaders resolve to valid compiled templates:
panel_wall_c uses _0_1_0_1_2_1_0_0_0_0_0_0_0; rock_small uses
_0_2_0_0_2_0_0_0_0_0_0_0_0. Thus their common missing authoring template reference
is not the template actually used by the compiled draft. Evidence is cache-hash
bound; it does not verify the newly added Forge props at runtime.

Both map-specific Reach gravity-lift menu choices now resolve to the unchanged
stock Citadel base_gravlift_descent, the same donor already used in the authored
map and covered by the user's launch-height walkthrough. The two source color
variants share one H3 choice under the stock-asset rule. This does not validate
Forge manipulation. The isolated scenery menu now has 52 entries, 23 added
English labels and 56 unresolved source choices. Installed cache and lighting
remain unchanged.

### Reach/Sandbox structure shape inventory (2026-10-28)

`audit_forge_structure_shapes.py` follows each object to its model and physics
model in the official authoring kits. It records hashes, shape extents, centers,
transforms and motion types for 79 Reach/Sandbox candidates with no missing
metadata dependencies. No mapping is inferred solely from these bounding boxes.
For example, Reach ff_plat_1x1 has polyhedron half-extents approximately
(0.49159, 0.49159, 0.48360), while H3 sand_block is approximately
(0.48360, 0.48360, 0.48360). H3 sand_large_cube instead measures approximately
(0.88310, 0.88360, 0.88360). Names alone would select the wrong dimensions.
Use shape geometry and intended role when choosing stock structure donors;
polyhedron AABB agreement alone does not establish exact collision equivalence.
Evidence: forge/structure-shapes.json. Existing maps and bake inputs unchanged.

### Solid-box donor verification (2026-10-28)

`verify_stock_structure_boxes.py` reads packed Havok convex vertices and requires
all eight bounding-box corners, rather than accepting matching AABBs. Reach's
ff_plat_1x1 and H3 sand_block pass; their native size differences are recorded
and remain unmodified under the stock-asset policy. The Forge menu now maps that
source choice to the original Sandbox entry, including native cost and limit.
Physics hashes gate the mapping. Current assembly: 53 scenery entries, 55
unresolved source choices; locale preservation check passed.

The ff_plat_2x2_short -> sand_block_large candidate was rejected: H3's ten-vertex
shape lacks expected solid-box corners (maximum closest-vertex corner distance
0.983599931), even though its AABB dimensions match. It requires a different
stock counterpart or separate conversion. No substitute was applied for it.
No authored placement, installed cache or lighting bake changed.

### Batch single-convex comparison (2026-10-28)

`compare_forge_convex_shapes.py` compares all 49 single-convex candidates using
actual packed convex vertices (or transformed box corners), after recentering
and testing four upright quarter-turns. The remaining 30 compound/other shapes
are explicitly excluded from this metric. This comparison measures symmetric
vertex-set distance, not surface Hausdorff distance or full visual equivalence.
No automatic substitutions are made from the nearest-neighbor report.

Besides the already selected 1x1 block, the only additional candidate below
0.025 units was ff_plat_2x1_flat -> stock Sandbox sand_bridge: both have eight
collision vertices, equal convex radii, no relative quarter-turn and a maximum
coordinate vertex-set error of 0.014391825. Their origins differ and are recorded.
The isolated Forge menu now uses that native solid-platform counterpart with
unchanged H3 appearance/dimensions/physics/cost/limit. It does not replace any
existing authored placement. Hashes and explicit comparison assertions guard
the mapping. Assembly and locale-preservation checks passed: 54 scenery entries,
54 unresolved source choices, 23 added English labels. No bake or deployment.

### Combined authoring compiler check (2026-10-28)

`compile_forge_candidate.py` temporarily overlays the assembled Forge scenario,
locale and effect/supplemental dependencies, compiles with existing Draft lighting,
then restores explicit overlays and the previous MCC cache with hash checks.
The completed check took 141 seconds and produced forge/compile-check/battle_canyon.map
(1,096,294,400 bytes, MCC compiler output, not the 360 cache). This is not a
console memory/residency figure or a deployable acceptance result. Installed maps
were untouched; no lighting bake ran. Keep this single candidate for the next
conversion diagnostic rather than accumulating duplicate builds.

The compiler exposed stale Reach object-name indices on sound scenery. The plan
now explicitly clears names and editor-folder indices on all 73 sound placements,
as it already does for other translated object types. verify_combined_scenario.py
now rejects invalid name indices against the actual target object-name count.
Regenerated combined assembly passed 2,347 edit checks across 437 objects with
zero errors. The retained compiled candidate predates this name correction;
its diagnostics remain evidence of the original fault, not proof of the fix at
runtime. Current isolated assembly contains the correction.

### Original-H3 integration: null audio placeholders (2026-10-28)

`build_native.ps1` now accepts an optional repository-confined -Source cache,
so the combined MCC candidate can be tested without replacing the normal input.
The first conversion stopped at two sound-scenery records with type -1. These
records have no assigned sound and are source placeholders, not missing audio.
The conversion plan now excludes only those two records and retains all 71
assigned sound placements, using stable source-derived unique IDs.

verify_stock_audio_assembly.py independently compares each retained source record
with its compacted target record. Transforms and playback fields match exactly;
only palette indices, unique IDs and stale name/editor-folder references change.
Nine stock audio palette references are verified. The core converter's invalid
palette-index validation was not weakened. Combined assembly and locale checks
passed after regeneration. The single combined compile-check cache is being
refreshed in place for the next native conversion diagnostic; no deployment or
lighting bake is implied by this check.

### Walkthrough feedback and flare counterpart selection (2026-10-28)

The user walked draft-preview-09 and reported traversal and tried gameplay working,
including adequate man-cannon launch height. Keep launch forces unchanged. Green
cannon appearance remains a visual check; this feedback does not establish its
cause. Final lighting remains last, after remaining conversion corrections.

The combined Forge/effect native conversion exposed three Reach flare bitmaps in
unsupported format 28. The batch format audit found ten other unsupported-format
names already present in the native basis, plus these three absent Reach paths.
reuse_stock_effect_assets.py now selects the official H3 light-volume glow,
simple flare and anamorphic flare counterparts. Glow and simple flare have native
Zanzibar resources; they are not pixel-identical to Reach, and simple flare uses
H3's 128-square resolution rather than Reach's 256-square resolution. This is
stock-asset reuse, not a claim of identical rendering. The official H3EK
anamorphic texture exists, but no compiled bitmap donor was found across the
installed original multiplayer maps. Its authoring hash and that limitation are
recorded in placed-effects/stock-reuse.json. Native compilation and visual checks
remain necessary; the installed walkthrough build has not been replaced.

The refreshed combined MCC candidate compiled successfully (SHA256
f51436490d2ec6a288e2a2b3cc45f2138b1721229e945f09b69729077cd2969a).
All explicit compiler overlays and the previous MCC cache were restored.
Native forge-integration-03 passed the previous format-28 failure and stopped at
levels\dlc\cex_beaver_creek\fx\ca_bc_towerflare: non-unit reflection X/Y
scaling is not represented by the original-H3 reflection converter. Investigate
actual authored curves and original-H3 flare representation before changing it;
do not neutralize scales or bypass validation merely to get a cache. No native
candidate was deployed. Log: forge/native-integration-03.log.

### Compiled flare parser correction (2026-10-28)

The integration-03 error message was misleading: ca_bc_towerflare has unit X/Y
scale, encoded as opcode 1 / flags 0x24 with both stored bounds equal to 1.
The converter accepted the equivalent form with the unused second bound zero,
but not this compiler encoding. It now accepts that exact additional constant.

The batch audit also identified variable unused padding in Type8Section, rather
than different curve coefficients. work/battle-canyon/TagFunction.cs,
TagFunctionType8Data.Type8Section.Read, explicitly reads the three bytes after
the section opcode as Unused1/2/3. The legacy reflection adapter now ignores only
those three bytes while validating the section size/count/opcode and all three
coefficient words. verify_flare_conversion.py checks padding variations, rejects
mutations of each semantic field, and verifies all 41 compiled reflections.
All 41 pass, including the three Battle Canyon custom tower/laser/sun flares.
This establishes metadata conversion only, not native visual acceptance.

Native integration-04 then passed the flare stage and stopped at the already
identified unsupported Reach particle shader used by plasma_cyan_large:
shaders\particle_templates\_0_8_0_0_1_1_1_0_0_0. Do not alias that numeric
permutation to a plain H3 shader. The prior official-source comparison establishes
additional plasma/depth sampling. stock-particle-candidates.json now records
original-disc plasma, mist and drip particle names and donor maps for checking
stock component reuse before implementing a custom adaptation. No deployment,
lighting bake, or cannon force change occurred.

### Native blue plasma component reuse (2026-10-28)

compare_plasma_components.py inspects the official Reach plasma_cyan_large,
the two custom vertical plasma strips, and original H3 plasma_noise / long
variants. It records source hashes, authoring fields and actual native-cache
donors. The centered screen-facing cyan particle now uses unchanged original
H3 fx/particles/energy/plasma_noise. Both are centered screen-facing plasma
components with no attached, collision or death effect and no model. H3 uses
its native blue palette, textures and animation; no pixel-equivalence claim.
The long variant is not selected: it has a direction-aligned billboard and an
offset origin. Parent effect emitter fields are retained; three staged parent
references changed. Re-running the step reports zero changes. Preparation now
excludes those reused branches before tracing custom dependencies.

The combined MCC cache compiled (SHA256
dda18a7c38a423cf6ff1085c5eea2214662bcd3aba89bd4e2c4ef21c5e93df84).
Native integration-05 passed that component and then reached plasma_beam_alt,
which uses the unsupported Reach shader but has a vertical billboard. It must
not inherit the screen-facing substitution. Both custom vertical particles
remain unresolved, as do the two authored beam systems. Original Citadel
beam authoring was extracted read-only under placed-effects/stock-beam-authoring:
its streak is direction-aligned with offset (-.25,0), ember screen-facing, and
ring velocity-horizontal. Stock light_beam / light_beam_wide are also direction-
aligned (origins (0,-.5)/(0,0)); these observations rule out treating them as
identical drop-in vertical particles. The extracted set is about 1.9 MiB.
No additional lighting bake, deployment or gameplay retuning occurred.

### Vertical plasma material adaptation (2026-10-28)

A complete native multiplayer-particle scan found only six vertical-billboard
names: dirt/snow impact crests, Spartan/Elite shield-collapse, air-door blast,
and storm lightning. native-vertical-particles.json records their centers and
maps. None is a matching blue plasma strip. The Citadel beam is 25 units long
while Reach's authored beam is 75 units; beam-dimensions-comparison.json records
the actual mapping headers. These are not interchangeable whole geometry assets.

adapt_vertical_plasma.py now retains the two custom plasma_beam particles'
vertical billboard, centered origin and every non-material authoring field,
while copying the unchanged official H3 plasma_noise material. This explicitly
adopts stock H3 texture/palette/animation instead of Reach sphere-warp and
scene-depth palette lookup; it is not a shader-equivalence claim. Parent emitter
curves and positions are untouched. copy_render_method.rs uses blam-tags to copy
named structs, blocks, arrays and scalar/data fields. It rejects array truncation;
the known six-to-eight compiler-owned query table expansion initializes new
slots to -1. The preparation readback compares all authored material options,
references, parameters and animation fields with the stock donor, and every
non-material field before/after. Both particles passed. Evidence is
placed-effects/vertical-plasma-adaptation.json. The reproducible preparation
chain applies this after stock-reference reuse. Both source/helper files live
under tools/battle-canyon-rebuild; the executable build is in the ignored work
folder. Native compilation/visual validation is still pending; do not label
these adapted visuals accepted yet. The two continuous beam systems remain
unresolved and must be handled before another combined build.

### Continuous beams and combined native build (2026-10-28)

adapt_continuous_beams.py copies the two unchanged original H3 Citadel beam
materials into both custom Reach beam systems. The donor uses energy_trail
and the Valhalla tower-beam palette. This deliberately adopts native H3 surface
animation rather than claiming equivalence to Reach's two-noise plasma shader.
Readback verifies every non-material field unchanged, including the authored
75-unit lengths, profile geometry, tint, timing and placement. The native donor
has 25-unit beams; those geometry fields were NOT copied. Stock beam shaders
_2_8_1_0 and _0_8_0_0 are independently present in descent.map.

NativeEffectPost now searches beam-system embedded postprocess blocks alongside
its existing particle/material donor search, using the existing native 0x208
beam-row / +0x2c postprocess layout. It imports exact original shader routing,
not MCC compiled shaders. The combined MCC candidate compiled successfully
(SHA256 b7eba955f93dbd8d928dc62c0ef64388f9bbae3a5d4fce8482b654bf635693df),
and forge-integration-06 completed original-H3 conversion. Metadata checks pass,
435 objects fit the 640-object format limit, and no large collision BSP blocks
are required. Map filesize is not a complete console RAM measurement.
Runtime check is separate; these build results do not establish visual quality.


### Combined candidate runtime check (2026-10-28)

The 175-second process-local run completed at
.local/loading-traces/20261028-172942-40684. All three native captures were
inspected (112/135/160 seconds). Terrain, base, weapon and HUD render. The first
view additionally shows oversized blue glyph-like shapes over the canyon: this
is a visible regression, not accepted output. The other two views show the
close rock and base wall under dark Draft lighting. These camera views do not
adequately frame the continuous beams, so their animation/appearance remains
unverified. forge/integration-06-visual-review.json records the scope and gaps.
No candidate was deployed or marked complete. Stock null_up render-model
material references fx/null_object/shaders/invisible.shader; identical anchor
frames alone do not establish correct runtime visibility/material binding.
Trace the glyph regression before another runtime attempt, rather than masking
it by removing authored effect placements.

### Shared Forge material and render integration (2026-10-28)

Official H3 tool evaluation now succeeds for all 19 prepared shared Forge metal
shaders. Every constant and texture name shared with the original Reach evaluated
output has matching values. Source-only fields and different lighting programs
remain recorded in forge/architecture-materials/h3-evaluation-comparison.json;
this is not proof of identical runtime shading.

The two-detail panel retains both source detail textures and their animations,
using the original-H3 dynamic-environment Cook-Torrance permutation found in
native-two-detail-templates.json. Illuminated panels use a supplied compiled H3
program with an isolated authoring template: seven passes route self_illum_color
from primary object color. One-texture illumination uses a neutral gray detail
texture without changing the source intensity animation. This avoids requiring
an unavailable compiler for a newly generated shader program. Xbox 360 routing
for that custom authoring template remains a separate unfinished conversion step.

compile_remaining_forge_render.py now completes 34 of the 44 pending models,
up from 12. Each compiled render model's material reference set matches its
prepared source bindings exactly; no missing-material fallback is accepted.
Ten models still await material tags. Geometry/LOD/marker fidelity, full object
integration and actual native appearance remain separate outstanding checks.
No new map was deployed and no final lighting bake was started.

### Pending Forge body-property reconciliation (2026-10-28)

The named-body audit covers 45 rigid bodies across all 44 staged pending models,
using the verified geometry-metadata outputs and their hashes. Mass, damping,
motion and all other shared body properties match except ten bounding-sphere
radii (largest absolute difference 0.00000190735 units). The one material
behavior discrepancy was the portable shield's authored center-of-mass offset:
Reach (0,-0.1,-0.4), compiled H3 (0,0,0). The restoration step now preserves that
local real-vector field by matched node/region/permutation identity. Readback
proves only the intended properties changed; actual MOPP bytes remain identical.
The reproducible shell patch now supports finite real_vector_3d input as well
as points and angles. No native executable or installed map changed.

Reach-only per-axis inertia scales, proxy collision group and runtime Havok
mask are all zero/default in these bodies. Reach water-physics fields describe
absolute override bounds, whereas H3's similarly named fields describe offsets;
they must not be blindly aliased. All six fields are zero on both sides for
every audited body, so no water-bound conversion is needed here. Evidence:
forge/remaining-geometry/restored-body-properties.json. This reconciles body
metadata, not full object behavior or native runtime validation.

### Remaining Forge rock materials (2026-10-28)

The four Forge rock models now compile with their original two-layer terrain
material. audit_forge_rock_material.py resolves the official evaluated Reach
categories by name and finds exact original-H3 template
shaders/terrain_templates/_0_0_1_1_2_0 in Guardian (tag 8177). Both active layers
retain all textures, constants and animation payloads. Layers 2 and 3 are
explicitly off in Reach's evaluated options; their eight unused bitmap
references are cleared only in the staged copy, removing nonexistent Forge
Gulch dependencies without changing active layers or source tags.

prepare_forge_rock_material.py verifies converted parameter records and actual
function bytes, then evaluates with official H3 Tool. Shared evaluated texture
and constant differences are zero. Reach wet_material_dim_coefficient and
wet_material_dim_tint remain source-only and are recorded, not claimed as
native equivalents. Native appearance/resource conversion still requires checks.
The render-compilation report now has 38 successful models and six deferred:
land mine, dice, portable shield, folding chair, small space crate, health cabinet.
These are staged authoring results, not installed runtime acceptance.

### Batched remaining prop materials (2026-10-28)

The shared material preparer/evaluator now accepts --remaining-props, reusing
the established parameter/animation preservation rather than creating separate
per-object adapters. Six ordinary prop shaders pass official H3 evaluation with
zero differing shared constants or textures; all six exact native permutations
were found in original disc caches. Missing self-illumination and flat environment
references are removed only when evaluated options explicitly disable those
samplers. The health cabinet's composite Phong power and normal/glancing tints
are expanded into explicit H3 fields, avoiding H3 defaults of white and power 10.
Float readback compares the exact stored float32 representation.

Small space crate and health cabinet render models now compile; total 40/44.
Remaining material blockers: land-mine and chair parent locks, the dice's
multiplied specular mask, and the shield's halogram materials. Parent locks are
not silently discarded. Full object integration and native validation remain.
Evidence: forge/prop-materials/{authoring-plan,native-template-inventory,
h3-evaluation-comparison}.json and remaining-geometry/render-compilation.json.

### Parent shader records and inherited animation blocks (2026-10-28)

Official Reach evaluation resolves the land-mine-light environment contribution
to the child's 1.0 (parent 4.0), and the folding chair to the child's .25
(parent .5). Those exact named exceptions now preserve child function bytes;
other conflicting parent locks remain rejected. Nonconflicting locked fields
are inherited intact. Duplicate parent parameter names are collapsed to the
last record, matching the preparation dictionary; official evaluation checks
the resulting effective values rather than treating this as a universal rule.

The folding chair also revealed component inheritance: its child albedo color,
detail bitmap and detail-bump bitmap records have empty animation blocks while
the parent supplies color .906 and UV scales 32/16. The helper now inherits
complete parent animation records only when the child animation block is empty.
Child animated overrides remain intact. Python verifies the merged records and
actual function bytes. Both selected H3 material evaluations now match shared
Reach textures/constants exactly. Chair render compilation passes: 41/44 models.
Land-mine light authoring is prepared but its exact native shader permutation
is missing; dice mask and shield halogram adaptations also remain outstanding.

### Batch object/model integration (2026-10-28)

prepare_remaining_forge_objects.py now converts 82 metadata tags for the 41
compiled objects into forge/remaining-objects, retaining their original identities.
It assembles hash-verified render, collision and corrected physics outputs and
checks every object/model/geometry reference. Nothing is deployed to the kit or
installed map by this step. The metadata report retains 20 kinds of unsupported
fields for value/behavior review; successful conversion is not acceptance.

bind_remaining_forge_materials.py explicitly maps Reach's model materials block
to H3's materials block, preserving local names, global names and unassigned
damage sections. It checks all other model fields unchanged. Low bunker's two
identical source material names compile to one entry; every source and target
surface index is checked in range, proving equivalent material lookup. Other
collision material tables match exactly. All 41 material tables are bound.
Resource hashes in bindings.json describe pre-material-binding metadata; the
updated model hashes are in material-bindings.json. Remaining work includes
unsupported nondefault gameplay fields, dependencies, native integration and
runtime validation, plus the three unfinished render-material sets.

### Prop damage metadata (2026-10-28)

The unsupported-field value audit is saved in remaining-objects/unsupported-source-values.json.
The folding chair and multi-crate had nonzero Reach vitality (25 and 380), but
no corresponding H3 damage-info row after generic conversion. The focused
restore_forge_prop_vitality.py maps that simple source representation into H3's
new damage info/body/maximum vitality, preserving indirect material and damage
reporting by enum name. Both have zero flags, no damage subblocks, and unassigned
section links; the adapter rejects other cases. Readback verifies exact values
and all unrelated fields unchanged. Native damage behavior remains unverified.
Run after material binding; vitality-restoration.json contains final model hashes.

Other outstanding field differences include .5 vertical/angular acceleration on
two crates (H3 has one acceleration scalar), Reach impostors, per-object shadow
biases, and phased-Forge flags. These were not silently marked equivalent.

### Assembled object dependency closure (2026-10-28)

audit_combined_dependencies.py --remaining-objects now walks the 41 assembled
object roots through their real staged/native authoring references. The first
pass found 12 missing paths. Three original attachment lights have now been
converted in one batch with prepare_forge_light_metadata.py --attachments:
bridge, 2x2 angled platform and yellow railing light. All shared light fields
and actual color/intensity function bytes match; Reach-only attenuation/angular
falloff values remain recorded. These are frustum/Screenspace lights, unlike
the earlier sphere/Inline palette lights, and their native appearance is not yet
verified. The closure now covers 433 tags with nine missing paths and no parse
errors. Two referenced crenellation ext.light files remain absent after checking
the official Reach archive. Remaining missing entries include material effects,
inactive development bitmap references and compiler template references; do not
categorize them all as equivalent blockers or remove attachments without evidence.


### Remaining Forge object dependency cleanup — 2026-10-28

The isolated 41-object dependency graph now traces 438 tags without parsing
errors and has two unresolved references, down from nine. This is authoring
closure progress, not native acceptance or complete object integration.

- `recover_remaining_stock_effects.py` maps the folding chair material-effects
  reference to the original H3 camping-stool effects under `objects/havok`.
  All five dependencies resolve; unrelated object fields are unchanged.
- `clean_inactive_stock_shader_references.py` uses official H3 Tool evaluation
  to verify that four missing bitmap parameters are inactive (two in stock
  panel_crate_multi, two in stock invis). It clears them only in isolated copies.
  It also clears stale generated postprocess blocks in those copies and invalid;
  combined compilation must regenerate those blocks from unchanged options.
  The invis shader evaluates with zero textures, additive black albedo.
- Exact archive extraction and complete archive-name inspection confirm that
  ff_crenel_full/ext.light and ff_crenel_notch/ext.light are absent from HREK.
  They remain unresolved. Original MCC Reach Battle Canyon contains the object
  names but no matching ext light name strings. That name evidence alone does
  not prove how compiled attachments behave; do not fabricate replacement lights
  or remove attachments on that basis alone.

Evidence: `work/battle-canyon/rebuild/forge/remaining-objects/` contains
`stock-effect-reuse.json`, `inactive-stock-references.json`,
`exact-dependency-recovery.json`, archive reference matches,
`reach-cache-crenel-names.json`, and refreshed `dependency-audit.json`.
Run the effect reuse step after regenerating object metadata; its patch would
otherwise be reset. Run shader cleanup before installing the staged object
batch. Installed map and runtime remain unchanged.

Source for this rebuild: Bungie's original Halo Reach Battle Canyon authoring
and official editing kits, not the earlier third-party H3 MCC conversion.
These scripts perform this project's H3/OpenH3M adaptation.


### Combined Forge expansion and reuse library — 2026-10-28

`resolve_crenel_light_references.py` confirms three null attachment datums in
original MCC Reach Battle Canyon and clears only their stale staged light refs.
The 41-object dependency audit now covers 438 tags with no missing paths/errors.
`stage_remaining_forge_objects.py` verifies final corrected model/resource hashes
and registers the batch for temporary compiler overlays. Scenery assembly now
contains 104 entries, with land mine, dice and portable shield still unresolved.
71 English labels are supplied; 393 existing locale records are preserved.

The expanded official H3EK compile passed in 191.9 seconds using Draft lighting:
`forge/compile-check/battle_canyon.map`, 1,119,698,944 bytes,
SHA256 `227ca4a54129a91f253c320133ffeaefabbca94078c8a77de90216c786b4080e`.
This is the intermediate MCC cache, not the final 360 map size or RAM footprint.
The compiler reports three stock animation/node-count mismatches; native donor
reuse must still be checked. Compiler overlays and the preceding MCC cache were
restored. No runtime deployment or visual acceptance is implied.

The reusable library at `tools/reach-forge-library/` indexes 41 objects and 438
existing artifacts with hashes, without copying them. Protect these assets and
correction evidence during cleanup. New maps should verify and reuse this work.


Native integration-09 conversion status: first run stopped on official H3EK
list-child tail contents. The shared model_physics adapter now preserves
CollisionFilter/ShapeSize and omits the MCC-only 12-byte tail while retaining
runtime-pointer rejection; three focused tests pass. The next run passed that
point and stopped on the already-known missing original-H3 donor/routing for
`shaders\battle_canyon_forge_primary_templates\_0_2_0_1_1_2_5_0_0_0`, used by
for_forge_gen_panel_04_light. No native integration-09 map was accepted or
installed. Both processes exited; no compiler transaction remains active.
The shared reuse catalog correctly remains native-unverified.


### Native integration-09 conversion completed

The 104-entry Forge candidate now converts successfully to original H3 format.
The new primary-color routing adapter reuses the native Armory detail-emission
shader program. Inspection of the saved cache confirms seven passes route register
234 to primary-color extern 14, shared by four panel materials. The existing
flashing-light verifier also confirms both markers retain their two animation
functions and register bindings. Six focused routing/physics tests pass.

All 526 specialized physics records in the new object batch passed a layout-only
preflight, followed by successful full conversion (including string relocation).
Evidence: `forge/remaining-objects/native-physics-layout-preflight.json`,
`forge/forge-integration-09-primary-routes.json`,
`forge/forge-integration-09-light-animation.json`, and the native conversion report.
No runtime acceptance, final bake or installed replacement is claimed.


### Integration-09 presentation timing (2026-10-28)

Existing run `.local/loading-traces/20261028-214936-28436` contains both
rotated runtime logs. Sorting host-present records by QPC and measuring changes
in guest_painted yields 29.84 observed FPS for elapsed_ms 115000-145000,
median 33.37 ms, p95 50.05 ms, maximum 67.06 ms; 55 of 894 intervals exceed
50 ms. For 150000-170000: 29.95 FPS, median 33.36 ms, p95 50.09 ms, maximum
50.42 ms. These are host observations of painted guest IDs, not simulation
or GPU-only durations, and do not prove sustained smooth 30 FPS. The
observer was stationary with scripted rotation; this is not full traversal
or a full Forge stress test. Evidence: painted-frame-timing-summary.json
in that run directory. No additional launch was required for this analysis.

The existing official compile-shader failure used pc/DX11/durango profiles;
it does not provide an Xbox 360 compiler route. The currently inspected H3EK
bin has pc_shader_compiler.dll. Do not treat MCC shader compilation as native
Xbox 360 bytecode generation. Native material completion remains outstanding.


### Forge land-mine entry uses stock H3 tripmine (2026-10-28)

The standing stock-H3 gameplay-asset policy resolves the Reach land-mine
entry to the native deployed tripmine, rather than rebuilding its Reach
geometry and unsupported illumination program. The authoring assembly now has
105 scenery entries and two unresolved choices (dice, portable shield).
`assemble_forge_scenery.py` verifies Armory contains the exact eqip identity
objects/equipment/tripmine/tripmine and uses the stock tripmine menu's label,
maximum and price. This is the deployed mine, not tripmine_equipment's pickup
shell. H3 arming, trigger, lifetime, damage, model, effects and audio are retained.
These are explicitly H3 semantics, not a claim of identical Reach behavior.
Existing placed objects were not changed. No new cache was compiled or deployed
by this assembly update; integration-09 still has 104 scenery entries.
Scenery readback passed with no missing authoring roots and all unrelated
scenario fields unchanged. Locale preparation preserved 393 existing labels
and the existing 71 additions. Native placement/arming remains to be verified.
Evidence: forge/scenery-verification.json, prop-materials/native-tripmine-donors.json
and prop-materials/landmine-stock-tripmine-audit.json. The unused permanent
authoring variant was inspected but is NOT selected (no native donor found).


### Stock deployed cover and 106-entry compile (2026-10-28)

Reach portable-shield Forge scenery now uses native H3 multiplayer deployed
cover (`objects/equipment/instantcover/instantcover_mp.equipment`), verified
in Armory. This follows the standing stock-H3 asset policy. It is distinct
from the ineffective Zanzibar battle-shield candidate and from the equipment
pickup shell. Native H3 shield appearance, collision, damage, audio and effects
are retained; its 30-second multiplayer lifetime replaces Reach's persistent
recharging behavior. This difference is explicit, not a claim of equivalence
in tuning. No placed map objects were changed.

Scenery assembly/readback: 106 entries, one unresolved choice (dice), zero
missing authoring roots. Official H3EK compile passed in 122.25 seconds;
MCC cache SHA256 8207eec2e873a3914dbf3b8db2e76d8bbc40d7849e553dd6e09f053a20528f4e,
1,119,698,944 bytes. Existing three stock animation/node-count warnings remain
listed in compile-check/result.json. Compiler overlays/cache were restored.
Native conversion and Forge placement checks are separate requirements.
Evidence: prop-materials/stock-deployed-cover-audit.json and
forge/scenery-verification.json.

Native integration-10 completed at 155,652,096 bytes (148.44 MiB), unchanged
size from integration-09. Saved-cache inspection finds deployed tripmine eqip
3040 and deployed multiplayer cover eqip 5341. Their presence alone is not
Forge placement/behavior proof. See forge/forge-integration-10-stock-hazards.json.
No installed-map replacement has been made.


### Native Forge check exposed budget and locale omissions (2026-10-28)

Run `.local/loading-traces/20261028-222456-29664` selected Deployable Cover
in the actual Scenery menu. Both captures (150000 and 165000 ms) were inspected.
They show a $0 budget and no placed cover; the later UP input moves menu
selection because placement never succeeded. This is a failed placement check,
not evidence of cover behavior. The third scheduled capture did not arrive
before the 179-second watchdog; the harness correctly rejected completeness.
Future check_native.ps1 Forge captures use 145000/155000/165000 ms.

Cause 1: the fresh H3 scenario retained its initial sandbox budget of zero;
Reach authoring has 5000. assemble_forge_scenery.py now reads that source
value, writes it to the candidate and verifies it, while preserving all other
non-palette fields. This is spending currency, not a RAM-limit change.

Cause 2: native scenario_forge.py used an outdated fixed custom-label list.
The source locale already has the new labels, but 64 scenery identifiers in
integration-10 lack localization in the native sandbox UI. The converter now
compares every converted menu label against that UI's actual locale-ID set
and imports missing authored English labels through stage_labels. It still
rejects missing or ambiguous source strings. Evidence:
forge/integration-10-missing-labels.json. Rebuild and native checks remain
necessary before either correction is accepted.


### Dice native-program audit

`audit_dice_native_shader.py` extracts and disassembles the original Armory
parallax/alpha-test template without modifying it. Ten of its twelve compiled
pixel programs contain an explicit `kill_gt`; the other two do not. This
confirms that the nearest template cannot be adopted by changing only its
blend state. Official `alpha_test_fx.hlsl_include` additionally samples a
separate transformed alpha-test texture, whereas the required alpha-blend
path outputs `albedo.w`. Removing kill instructions alone is therefore not
a proven replacement either. Outputs and hashes are retained under
`forge/prop-materials/dice-native-shader-audit`; no native shader was patched.


### Dice addition, 2026-10-29

User-approved normal-mapped pips replace only view-dependent parallax. The
shader preserves diffuse alpha and normal textures; H3 evaluation reports zero
changed shared constants/textures and an available original H3 shader donor.
The inactive environment contribution is checked against its exact constant
function and Reach evaluation. Dice render/physics/collision metadata is added
incrementally; the previous 41 library objects and 438 artifacts passed their
unchanged hash check. The library now contains 42 objects and 452 artifacts.
The source palette has 107 scenery entries and zero unresolved source choices;
this is implementation coverage, not blanket runtime acceptance.

The combined official H3EK compile passed in 170.55 seconds, retaining the three
previous stock-animation node warnings. Dice source acceleration scales are
1.5 on all three axes; the H3 scalar is also 1.5. Source impostor policy is
never; the model material table has been transferred. Reach shadow bias fields
remain absent in H3 and are retained in the explicit source-field audit.
Lighting is still Draft. Native conversion and appearance checks follow.


Dice omission compile, 2026-10-29: official H3EK compile succeeded in 146.92
seconds. MCC cache SHA256 `22d164afb42c00aa5185e2ca4e884865af5f246fc9fdd5d4d73c4ab14e7e7cb7`,
1,119,698,944 bytes. The same three preexisting animation-node diagnostics remain.
106 menu entries verified, dice absent, one explicit user-approved omission,
zero unresolved menu choices. Native rebuilding/deployment remains outstanding.


### Blue-symbol isolation, 2026-11-02

The latest 14 candidate is unchanged from the 2026-10-29 test. Saved-cache
inspection of imported particle postprocess bindings is recorded in
`placed-effects/native-particle-bindings.json`. Custom plasma binds native
plasma noise/gradient textures, not HUD textures. The two private bitmaps used
by drips and mist match freshly encoded official MCC inputs byte for byte,
including resource controls: `particle-bitmap-resource-check.json`. This rules
out those stored-payload substitutions, not incorrect runtime sampling.

`native/diagnostic-no-placed-effects.map` changes only the scenario's effect
scenery count from 14 to zero and the required checksum/header authentication.
Its recorded byte diff confirms precisely one non-header byte changed
(offset `0x887009f`). This is a disposable causal-isolation test, never a
production fix or deployable candidate. Original effects remain in authoring
and integration-14. Native run `20261102-210837-32208` reached its 179-second watchdog but
failed the capture-completeness check: only 112000 and 135000 ms captures exist.
Both were inspected in order. The matching opening view at 112 seconds has no
oversized blue symbols, unlike integration-14. The later close-rock view also
has none. Suppressing placed effects removes the reproduced opening-view
artifact; the individual effect remains unidentified. This is limited causal
evidence, not a successful full run or authorization to omit production effects.


### Shared effect-helper investigation

All seven converted effect scenery definitions reference the same stock H3
`fx\null_object\null_up\null_up` model. The marker audit proved attachment
transforms, but did not prove invisibility. Its render model still has one
mesh and a one-mesh permutation. The imported `fx\null_object\shaders\invisible`
material has the same options, zero-alpha constant and postprocess flags as
its actual shrine.map donor (`_2_0_0_0_0_0_0_3_0_0`). This is a candidate to
isolate, not yet the established cause.

`diagnostic-anchor-no-draw.map` restores all original effect placements and
changes only that helper permutation's mesh count from one to zero, plus
checksums. Nodes, markers, resources, materials and effect attachments remain.
Its JSON records the exact changed field. The completed result is recorded
below; this diagnostic is not a deployable fix.


Rainbow sprite audit: `placed-effects/rainbow-sprite-metadata-audit.json`
records one compiled source sequence with one sprite, versus zero native
sequences. `MaterialImporter.bitmap_resource` deliberately initializes these
blocks empty. Pixel/control checks do not cover sprite UV or registration
metadata. This is a confirmed omission, not yet the proven blue-symbol cause.
Camera-space placement ratios are in `opening-camera-effect-projection.json`;
they do not account for bounds or occlusion. The helper diagnostic result
is recorded below.


Helper-only result, run `20261102-212319-30488`: 112000 and 135000 ms captures
were inspected sequentially. Oversized blue symbols remain in the opening
view with the helper permutation suppressed; helper geometry is therefore
not the sufficient cause. The 160000 ms capture did not arrive before the
179-second watchdog, and the harness failed its completeness check. No full
run acceptance. User independently supplied the same visible symbols during
this diagnostic. Retain normal helper geometry in production.

Stock lens sequence audit (`stock-lens-sprite-sequences.json`) found zero
sequence-bearing lens bitmaps among the parsed original multiplayer maps
(excluding shared, campaign and mainmenu). The source rainbow sequence loss
alone does not establish runtime incompatibility. The earlier no-custom-flares
diagnostic was re-read: its reflection flag is correctly 0x100 (disabled for
debugging), not merely zero. Do not repeat that test based on a mistaken flag
interpretation.


### Effect attachment isolation (2026-11-02)

`isolate_placed_effects.py` creates diagnostic-only caches from the exact
integration-14 hash. It zeros selected efsc attachment counts, retaining all
14 placements, all helper models, resource pages and geometry. It asserts
that every non-header changed byte belongs to an intended attachment count.
The checksummed output and byte-diff manifest are stored together. This is
causal isolation, not permission to omit authored production effects.

`diagnostic-laser-attachments-only.map` retains palette 0/1/2 (tower lasers)
and mutes attachments for 3/4/5/6 (drips, rainbow, mist, sun). Exactly four
non-header bytes change. Run `20261102-213604-27652` completed and all three
captures were inspected sequentially: no symbols in the matching opening view
or later views.

Read-only follow-up checked all seven placed-effect attachment groups and
their immediate effect parts: all runtime base groups match the referenced
beam/lens tags, including tag salts. No wrongly typed HUD reference was found.
Beam postprocess bindings use energy_trail, spark_fiery and imported gradients;
all inspected sampler external-texture modes are zero. This extends the prior
particle binding audit; it does not establish correct runtime binding.

`diagnostic-rainbow-attachment-only.map` retains only palette 4's attachment
while keeping all helper models and placements. Run `20261102-213920-22644`
completed; all three captures inspected sequentially. The opening view
reproduces the exact oversized cyan X/ring symbols; later views are clear.
This identifies the rainbow attachment as sufficient to produce the defect.
It does not yet establish the faulty bitmap/runtime field.

`stock-lens-bitmap-formats.json` records 1,015 bitmap usages reached from stock
multiplayer lens tags: 933 Y8, 81 format 38, one AY8. All root flags are 0x10;
the imported rainbow is DXT1 with root flags 0x50. The related Halo Online
lens shader source samples full color, so monochrome stock assets alone are
NOT proof that a color bitmap is unsupported in original H3.

`diagnostic-rainbow-native-bitmap-flags.map` changes only the rainbow root
flags from 0x50 to the stock 0x10 (one non-header byte), restoring all effects.
Its result is pending. This tests the extra Can Be Sampled bit independently
of compression, pixels, resource allocation, flare geometry and other effects.

Bitmap-flag diagnostic result: `20261102-214625-15376` completed; all three
captures inspected sequentially. Exact cyan symbols remain at 112 seconds.
The later views are clear. Clearing Can Be Sampled does not fix the defect;
no production change justified.

`check_native.ps1 -SampleDraws` now exposes the existing bounded GPU-state
sampler. Its launch refused the installed rexgpu-xenos.dll SHA256
`e927230adacf9075bc14e3dceef6b51a73d9317b78f4f6b1e9bc99ac69f29380`
because its IssueDraw RVA is not verified. The existing COFF/unwind resolver
matched neither the current SDK DLL nor the deployed DLL against the available
object. No breakpoint address was guessed, no whitelist bypass was added, and
that draw-sampled game did not launch. Verify the deployed plugin's function
location and state layout before enabling this read-only sampler. Timing from
draw-sampled runs must not be reported as normal performance.

Cleanup of `diagnostic-laser-attachments-only.map` and its matching hardlinked
game fixture was rejected by automatic approval review (blocked by policy).
Both remain; do not retry their deletion by another method. Evidence JSON and
captures remain. No map or runtime deployment occurred during this isolation.


### Installed GPU trace resolution (2026-11-02)

`resolve_installed_draw.py` resolves the deployed plugin via its class RTTI,
vtable and function unwind table. Current COFF's IssueDraw is slot 21; the
source diff contains exactly one added virtual method, SetSceneMarkers, before
IssueDraw. The deployed plugin uses slot 20, RVA 0x14fd80. Its instructions
independently match IssueDraw: register file at this+0x20, RB_MODECONTROL at
register byte offset 0x8820, copy-mode 6 tail-call to slot 21, vertex shader
at this+0xf0 and pixel shader at this+0xf8. The installed hash alone is added
to trace_loading.py's verified address table. No DLL rebuild/deployment.
Evidence: `placed-effects/installed-draw-symbol.json`.

Draw-sampled run `20261102-215707-5920` completed; all three native captures
inspected sequentially. The symbols remain in the opening view. Its 1,024
draws span 110.000�110.578 seconds and end during world rendering; none uses
an explicit postprocess shader. Forty captured shader hashes independently
match native map bytecode (XXH3 of big-endian microcode). This confirms the
shader-header interpretation rather than a guessed ID. The lens shader's
known hash is 22f534a68b158263. Evidence: `draw-hash-validation.json` and
`lens-pixel-shader-hashes.json`. The 1,024-state sample does not yet establish
what texture the lens draw uses. `-SampleDraws` now requests a bounded 4,096
states to reach the later passes; default general harness limit remains 1,024.


### Original H3 lens reflection layout correction (2026-11-02)

The vendored original-H3 lens schema had incorrect offsets in its 48-byte
reflection record. Original executable `sub_82471B78` reads the bitmap image
index as a halfword at +4; `sub_82472380` reads rotation as a float at +8.
Preserve flags at +0, padding at +2/+6, bitmap index at +4, rotation at +8,
radius at +12, brightness at +20, modulation at +28 and color at +32.
Do not pack MCC axis offset into this record: nonzero values now require
separate research rather than silent corruption. Both generic and specialized
sun-flare writers use the corrected layout. Existing generated maps must be
rebuilt before they benefit. This is a cache conversion fix, no engine patch.

Battle Canyon rainbow rotation 90 degrees was previously written at +4,
causing image index 0x42b4 (17076) from a one-image bitmap. GPU draw trace
20261102-220627-28408, draws 2913/2914, uses the lens shader but retains all
six sampler words from preceding world draw 2912: a 256x256 format53 texture
instead of the rainbow's 128x128 DXT1 texture. This explains the cyan symbols.
All 41 compiled flare records pass conversion, with nonzero image-index and
90-degree rotation regression checks against the executable's offsets.
Native visual acceptance is recorded separately in the Battle Canyon notes.


### Flare correction candidate 15 (2026-11-02)

Full rebuild `native/forge-integration-15.map`: 155,652,096 bytes, SHA256
`2324918890c93911322dcbbaa2594f42c7972a293ff9840fcb72f11bc5383447`.
All effects retained. Serialized rainbow reflection now has bitmap index 0
at +4 and rotation 90 at +8. Audit: `forge-integration-15-flare-verification.json`.
The 41-record audit also tests nonzero bitmap 7 plus 90-degree rotation.
The GPU diagnostic's three captures (112/135/160 seconds) were inspected in
order: symbols in the opening view only, later canyon views clear.

Candidate 15 native check declined to launch after its 60-second guard because
another halo3mp session (PID 8492) was running. That process was not interrupted.
Visual acceptance of the fix remains pending; no deployment or final lighting
bake was performed. Resume `check_native.ps1 -Candidate forge-integration-15`
when the other session ends. Original source credit: Bungie, Halo Reach Battle
Canyon, rebuilt from original Reach authoring through H3EK; not the Ryno port.


### Candidate 15 native visual result (2026-11-02)

Run `.local/loading-traces/20261102-222441-9088` completed its 179-second
watchdog. All three native captures were inspected sequentially: 112 seconds
shows the actual colored rainbow in place of the oversized cyan symbols;
135 and 160 seconds retain the canyon/structure views without those symbols.
All effects stayed enabled. This verifies the reported floating-symbol fix.
All 49 native flare reflections also reference an in-range image in a valid
bitmap tag (`forge-integration-15-all-flare-indices.json`).

Timing was summarized across both rotated runtime logs in `present-summary.json`,
excluding capture intervals. This narrow slow-turn check does not certify full
map traversal, Forge-object behavior, audio or console performance. Draft
lighting, mist/drip emitter geometry and the other recorded acceptance work
remain outstanding. Installed map remains unchanged.


### Native H3 emitter offset evaluation (2026-11-02)

Original executable `sub_821537F0` resolves the 752-byte emitter definition,
calls `sub_82153C20` once before its emission-count loop, then calls
`sub_82154138` for each new particle. `sub_82153C20` evaluates the translation
property at emitter +24 through `sub_82153E60`, interpolates the two Cartesian
endpoint vectors at property +32/+44 and stores the result in the emitter
instance at +28. The individual particle setup `sub_821546F8` selects the
shape using the emitter +4 byte and does not reevaluate that +24 property.
Thus a line emitter with a particle-random translation cannot be assumed to
sample an independent perpendicular coordinate for each spawned particle.
The previously suggested shortcut is not established by the schema's input
enum; this native call order is evidence against that proposed implementation.

Evidence: Battle Canyon `placed-effects/native-emitter-code-index.json`,
`native-emitter-transform-82153C20.txt`, `native-particle-spawn-82154138.txt`,
and `native-emission-821546F8.txt`, extracted read-only from generated original
executable functions. No emitter authoring or engine change was made.
The three source plane emitters remain unresolved; retaining sprayer defaults
is still not an accepted shape conversion.


### Tripmine Forge check and crate scale audit (2026-11-02)

Candidate 15 run `20261102-223407-28840` selected scenery entry 1 (stock H3
tripmine). Both available native captures, 140/145 seconds, were inspected
in sequence: the small stock mine is visible inside the green Forge hand;
budget is $4720. Object snapshots identify tag `0xed560be0`, handle
`0xe46c0048`, from 135 through 175 seconds. The requested 165-second capture
is absent, so the harness correctly failed overall visual acceptance.
No release/activation/save-reload pass is claimed. Evidence:
`tripmine-object-audit.json` and `native-variant.bin` in that run.
Host-present records stop at elapsed 154861.749 ms, but GPU submissions continue
through frame 4691 at the watchdog. This is not evidence of a frozen simulation;
the missing capture requires presentation/capture diagnosis, not a speculative
map change. No repeated test or engine edit was made on that evidence.

The two crates' actual authored acceleration values were reread: both
crate_multi and space_crate_small use horizontal=vertical=angular=0.5. Their
converted H3 object acceleration scale is also 0.5. Thus there is no differing
source-axis value to recover; however angular response equivalence still needs
engine semantics, not merely equal numbers. Evidence:
`forge/remaining-objects/acceleration-scale-comparison.json`.
The reusable library verifier passes all 42 objects and 452 dependency files.

User decision requested: approximate the three Reach plane emitters using
parallel H3 line emitters with unchanged total particle rate, omit them, or
continue exact-reproduction research. No approximation has been applied while
that decision is pending.


### Missing final Forge capture: scheduling cause (2026-11-02)

`StartCaptureThread` in halo3mp_app.h sleeps the difference between requested
timestamps after each preceding capture finishes. It does not subtract texture
readback/PNG-write time. Run 20261102-223407-28840 wrote the nominal 140-second
frame at 22:36:39.367 and 145-second frame at 22:36:49.482, from a 22:34:07
launch. The next 20-second sleep alone would exceed the 179-second watchdog.
This establishes why the last request cannot complete in that run.
`check_native.ps1 -CaptureTimesMs 164000` now supports a validated single late
frame without changing the installed runtime or extending the watchdog.


### Tripmine release verified (2026-11-02)

Candidate 15 run `20261102-224016-14744` completed the 179-second watchdog
and its single 164-second native capture. The capture was inspected: player
mode is active, with the stock tripmine visibly resting/glowing on the floor
after Forge release. Earlier 140/145-second captures established its held
appearance. `tripmine-placement-audit.json` records the occupied native variant
placement and tag, independently of the screenshot. This passes Forge creation
and release; activation/damage and an actual saved-layout reload remain untested.
No map or runtime deployment. The emitter-translation decision remains pending.


### Final lighting input audit (2026-11-02)

`final-lighting-input-audit.json` proves the restored kit scenario is not the
combined candidate. Kit SHA256 starts `00dd1b00`: 268 scenery, zero effect
scenery and zero sound scenery. Combined SHA256
`b714b34f248a359305cdb074e995bb22be687417e6d23cb43644e23fd62e7225` has
272 scenery, 14 effect scenery and 71 sound scenery. Both have 43 crates and
16 equipment. Compiling the candidate restores the older kit scenario afterward.

Therefore final lighting must stage the same combined scenario and reviewed
dependency overlays as compile_forge_candidate.py before running the official
farm, preserve the resulting lighting artifacts, and restore unrelated kit
inputs afterward. Do not run lightmap.py against the currently restored scenario
and assume it represents the completed map.

`lightmap.py --expected-scenario-sha256 HASH` now checks the actual scenario
before invoking any official bake stage. The negative check with the current
combined hash rejected the old kit input as expected; no bake process started.
Use the current reviewed scenario hash, not a permanently pinned historical
hash. Final bake remains after conversion corrections, per user sequencing.


### Ambient omission authorized and assembled (2026-11-03)

User chose to omit the three unsupported ambient plane emitters. Their two
effect-scenery types were used by eight placements: drip source indices 4-9
and mist indices 11-12. `verify_effect_assembly.py` excludes those placements
and their unused palette entries on every regeneration. It preserves and
checks all fields of the six retained placements (source indices 0,1,2,3,10,13),
remapping their five palette references and unique IDs. Rainbow, lasers and
sun flare remain. No engine changes or line-emitter approximation.

The combined scenario has 427 objects, no duplicate IDs, no unassigned object
types and no invalid palette references. Forge menus retain 106 scenery entries,
19 weapons and 15 equipment. The emission audit distinguishes the three
user-omitted emitters from the eight retained identity-scale cases; zero
unresolved geometry remains among retained emitters. This is a source/map
omission, not a claim the old converted sprayers were correct.


### Omission compiled and converted (2026-11-03)

Official H3EK compile passed in 190.2 seconds, with the same three recorded
stock animation-node warnings. `ambient-omission-compiled.json` proves neither
omitted effect name is present in the compiled cache and the five retained
effect-scenery tags are laser, skyward laser, alternate laser, rainbow and sun.
The converter produced integration-16: 9,670 tags, 155,635,712 bytes; its native
scenario contains exactly six effect placements and five palette entries.
Native header authentication and tag-memory checks pass. Evidence:
`native/forge-integration-16-omission-verification.json`.
The final scenario hash is now
`8fa6dfa4b3431a1dfbe818530f98f190531df033b3e0dc01a95dbb2f16eb584a`;
use this reviewed candidate (or its subsequently verified successor) when
staging final lighting, not the pre-omission hash. No final bake or deployment.


### Integration-16 native check (2026-11-03)

Run `.local/loading-traces/20261103-061919-20384` completed the 179-second
watchdog. Its one requested native capture was inspected: actual Battle Canyon
gameplay, intact canyon geometry/HUD and the colored rainbow; no oversized
cyan symbols. This confirms loading and the retained flare correction after
the omission. The compiled-cache/tag audit establishes absence of the omitted
effects; the opening screenshot alone cannot establish map-wide absence.
Draft lighting remains dark and is not final acceptance. Installed map unchanged.
The emitter decision is resolved; it is no longer a conversion blocker.


### Final lighting started (2026-11-03)

Command: `python -B tools/battle-canyon-rebuild/compile_forge_candidate.py
--lighting-quality medium --lighting-blob-id 115 --lighting-workers 4`.
The compiler wrapper now stages the exact combined scenario/dependency overlay
for the official farm before compiling the resulting cache. It hashes the
scenario before any bake stage, backs up existing top-level lighting inputs
and records the transaction in `forge/compile-check/active-transaction.json`.
On bake failure the existing lighting inputs are restored; on success new
lighting stays in the kit for reproducible subsequent compiles. Temporary
scenario/dependency overlays and the prior MCC cache are restored in either
case. Backups are cleaned after successful restoration; the library is untouched.

Live work started in farm dataset 115 at Medium quality with four workers.
`final-lighting-start.json` records actual staged hash and backup size.
`final-lighting.log` and native `faux/115/farm_log_*.txt` contain progress;
`final-lighting-result.json` is written only after all official stages succeed.
Do not restart or overwrite dataset 115 while its parent/worker processes live.
No new final cache, native acceptance or deployment is implied by starting it.


### Automatic continuation after final bake (2026-11-03)

The queued `finish_final_candidate.py --pid 26640 --blob-id 115 --candidate
final-lighting-01` holds a handle to this exact compiler process, waits for
successful exit and restored transaction, then checks the reviewed scenario
hash, bake/compiler results and compiled cache hash. It runs native conversion
and one process-local capture check at 112 seconds. State and output are in
`native/final-lighting-01-continuation.json` and the adjacent continuation log.
Do not start a second continuation for this candidate. A completed capture
still needs visual inspection, traversal and timing review before deployment;
the continuation never deploys or declares acceptance automatically.


### Deployment target verified (2026-11-03)

The current direct-launch bootstrap selects `work/dlc/installed-corrections`.
Its Battle Canyon DLC entry is ID 1733, in content directory
`0000000000000000/4D5307E6/00000002/E3C216511E5A0ED8A2E37F70BC65E407C481C510`.
The installed map is 198,397,952 bytes, SHA256
`bcd19b4179a5cddcce63a584cffc986a64eb85ff9f3c15d21520e7d8599ba9ab`.
Evidence: `work/battle-canyon/rebuild/installed-before-final.json`.
Draft-preview-09 was the isolated walkthrough fixture; do not describe it as
the installed DLC. Original `maps/zanzibar.map` remains the stock assembly
basis, not the final deployment target.

After final native acceptance, use existing `build_dlc_payload.py` with
`--map battle_canyon --source-map` pointing to the accepted candidate. It
updates the cache identity, scenario ID, checksum and header authentication
for ID 1733. Preserve the existing preview BLFs and other bundle entries.
Verify the renamed DLC identity in the native host before installing it;
a successful Last Resort fixture run alone does not verify DLC loading.
Avoid `deploy_dlc_host.py` for a map-only update: it also replaces runtime
binaries and bootstrap settings. Preserve concurrent Powerhouse work and
recheck the installed bundle before any atomic map/package replacement.


### Final-lighting 115 failure diagnosis (2026-11-03)

The medium bake completed direct illumination, photon casting, radiance and
exit illumination, then all final-gather workers failed with the same
`faux_hive.cpp:558` invalid-reference assertion. No final native test or
deployment occurred. The overlay transaction restored the prior kit inputs.
Keep dataset 115: its completed stages may be reusable after the cause is
resolved; do not restart the complete bake blindly.

Read-only crash-dump analysis locates the failing return at `0x1401e1e09`.
The input reference is `0x1913` (instanced geometry instance 25), and the
lookup returns `0xffffffff`. Its position exactly matches BSP instance 25,
`?teleporter_trimlowside003`, using per-vertex lighting. A census of all
1,255 hive instances finds exactly two null references at object offset
0xd8: that instance and instance 549, `?under_ground_towner`; both are
per-vertex. The other 509 per-vertex instances have non-null references,
so per-vertex lighting alone is not established as the cause. The meaning
of offset 0xd8 still needs tracing; it must not be described as a material
reference without evidence. Evidence: `reference/final-gather-115-*.json`.

User limit: after lighting completes, run one native validation test, then
hand the build to the user for testing. Do not add another native test matrix.

The dump and original tool lookup now establish offset 0xd8 as the cluster
reference: type 7 is CLUSTER; its offset 0x88 leads to type 6 STRUCTURE.
All 26 clusters reference the same structure (0x6). The failing final-gather
lookup needs that owning structure. `repair_final_gather_115.py` validates
the exact dataset hash and two unique serialized records, backs up main.blob,
and routes those two null references through cluster 0 to the same structure.
Only eight bake-metadata bytes change; no runtime tags, geometry, materials
or visibility are changed. Evidence: final-gather-115-repair-plan.json and
faux/115/cluster-repair.json. This is a narrow checkpoint recovery, not a
general rule to assign arbitrary runtime clusters. Preserve the evidence.

Resume command: `compile_forge_candidate.py --lighting-quality medium
--lighting-blob-id 115 --lighting-workers 4 --lighting-resume-final-gather`.
The wrapper validates repaired checkpoint/scenario/settings and resumes only
final gather, merge, finish and texture processing. Previous successful farm
stages remain intact; failed gather logs are archived. The exact continuation
for candidate final-lighting-02 performs the single authorized native test.
Recovery is not accepted until the official stages and compiler succeed.


### User-review correction: lost sky vertex colors (2026-11-03)

The source Reach sky mesh carries vertex RGB. The installed blam-tags JMS
exporter's `read_vertex` unconditionally sets `color: None`, and its JMS writer
serializes that as zero RGB. The old H3 model consequently has zero colors on
all 6,577 vertices. This is an established conversion loss, not a judgment that
the authored rock or cloud layers should be removed. The remaining gray-band
appearance still requires visual review after this correction.

`restore_sky_vertex_colors.py` stages a repaired JMS from the original Reach
raw vertices. Every one of 34,911 exported corners was matched by position,
normal and UV; all 11,637 triangle/material assignments were checked. Only RGB
lines changed: 21,654 corners become nonzero. Geometry, material bindings and
101 authored sky lights retain their original text. The generic exporter fix
is preserved in `blam-tags-jms-vertex-colors.patch`; `git apply --check` passes
against the installed source checkout. It has not been applied or rebuilt;
the checked JMS repair uses the installed tools and is the implemented route.

The repaired JMS was copied into the isolated H3EK data directory
`levels/mod_levels/bc_sky_rgb_repair/beavercreek_sky/render/beavercreek_sky.JMS`.
Official command, from the H3EK directory with repository-local TEMP/TMP:
`tool_fast.exe render-sky levels\mod_levels\bc_sky_rgb_repair\beavercreek_sky`.
`verify_sky_vertex_colors.py` matches all 6,577 compiled vertices to original
Reach geometry and RGB, accounting for compiler vertex reordering. All 3,683
nonzero source vertices are restored; maximum RGB error is 5.83e-11. Nodes,
material references, compression bounds, meshes, index stream and 101 sky-light
records are identical to the previous H3 model.

Reproduction, from the repository (Python -B, TEMP/TMP within rebuild/temp):

1. Run `restore_sky_vertex_colors.py`, copy its staged JMS to the isolated
   directory above, and run the official render-sky command.
2. Run `verify_sky_vertex_colors.py`.
3. Run `compile_forge_candidate.py --stage-directory
   work/battle-canyon/rebuild/forge/sky-color-01 --restored-sky-colors`.
   Explicit staging directories must be fresh. This overlays only the verified
   render model in addition to the normal combined-scenario inputs, then restores
   the prior kit tags/cache. There is no lighting option and no new bake.
4. Run `build_native.ps1 -Candidate sky-color-01 -Source
   work/battle-canyon/rebuild/forge/sky-color-01/battle_canyon.map`.
5. Run `verify_native_sky_colors.py --compiled
   work/battle-canyon/rebuild/forge/sky-color-01/battle_canyon.map --native
   work/battle-canyon/rebuild/native/sky-color-01.map --report
   work/battle-canyon/rebuild/sky-color-repair/native-verification.json`.
6. For the separate brightness candidate, run `prepare_exposure_candidate.py
   --source work/battle-canyon/rebuild/native/sky-color-01.map --output
   work/battle-canyon/rebuild/native/sky-exposure-01.map`, then the existing
   build_dlc_payload.py workflow for Battle Canyon ID 1733.

The corrected official compile passed in 288.8 seconds with the same three
stock animation-node warnings. Both final baked lightmap bitmap payloads are
identical to final-lighting-02. Actual native GPU RGB (format 14) matches every
compiled float for all 6,577 vertices; 3,683 are nonzero. Evidence lives under
`work/battle-canyon/rebuild/sky-color-repair`, with compile evidence under
`forge/sky-color-01`. No new game or control harness was run.

Brightness remains a calibration candidate: `prepare_exposure_candidate.py`
raises only this map's adaptation ceiling from 1.8 to 4 stops. Minimum 0,
log2 target -3.321928, sensitivity, speed, bloom and all baked resources remain
unchanged. Full file comparison allows only the ceiling word and its checksum/
header-authentication updates. This does not establish that exposure was at
its ceiling during the user's screenshot, or prove the darkness resolved.

| Candidate | SHA256 |
|---|---|
| Corrected official cache | `09cda89e33d1a5e745dced64713b7fc3ba8a8fd9fd20260ed158871aab9bac28` |
| Sky RGB native candidate | `9104e8d211234cebfcc7dfb02542427a76a589aab93d41852a99cb3de204ffb1` |
| Sky RGB + exposure native candidate | `b3fb0afed54b3dd74e10e05d979dcea1b9f9f5e2a9988443b1e6d7c5c2b61c55` |
| DLC user-test payload, 158855168 bytes | `3de8ee1d1a18b76b5a7306aac087d3ae267bd6897df440afff30dbc46883a585` |

A file-only installer is queued on the current human game process (PID 5704).
It does not control, stop or relaunch the game. Consult
`native/sky-exposure-01-installation.json` for actual status; a queued installer
is not deployment. Once the game exits, it requires the previous installed hash
`0ffce7a1effe86d1b1ad15f52f03a304fcf52dcc2269f831ebfd556e169940b1`, backs it up,
atomically replaces only battle_canyon.map and hashes every other bundle file
unchanged. Concurrent map changes cause rejection. Runtime/settings, preview
BLFs, mapinfo, other maps and stock Last Resort are preserved. This is deployment
for user review, not final visual or performance acceptance.


The queued sky-exposure-01 installation completed after PID 5704 exited.
The installed file was independently rehashed as
`3de8ee1d1a18b76b5a7306aac087d3ae267bd6897df440afff30dbc46883a585`;
the installer reports all other bundle files unchanged. Following the user's
standing launch request, a plain game process was opened with no arguments,
input harness, capture or watchdog. Its launch record is
`work/battle-canyon/rebuild/sky-exposure-01-user-play/launch.json`.
Brightness, sky appearance, traversal and performance acceptance remain pending;
installation and process startup do not prove those requirements.


### Reach visual reference comparison (2026-11-03)

Original map/game: Battle Canyon, Halo: Reach Anniversary Map Pack (Xbox 360).
This comparison uses original-game images, not the superseded H3 MCC custom
port. The rebuild authoring source and adaptation credits above remain unchanged.

References inspected individually:
- Official 2011 promotional screenshot, archived by Halopedia:
  https://www.halopedia.org/File:Battle_canyon.jpg
  Local evidence: work/battle-canyon/rebuild/reference-comparison/reach-press.jpg
  SHA256: 6d1cc49ce5465cbd9dd6d39f37b0fa865e2a412514f2e1488822fd77220c2574
- Xbox 360 gameplay screenshot, contributed by Kennyannydenny to MobyGames:
  https://www.mobygames.com/game/72479/halo-reach-anniversary-map-pack/screenshots/xbox360/900119/
  Local evidence: work/battle-canyon/rebuild/reference-comparison/reach-main-area.png
  SHA256: a0f4c7ea5b5b421aa24afbc6923485b128ac6e4fb37ea764dfed80aa39df576f

Both show warm daylight, readable brown rock and green foliage in shadow,
and atmospheric separation of distant geometry. Compared with the user's
pre-correction gameplay screenshot, the rebuild has extensive near-black
terrain, foliage and base surfaces. The bright hazy background in the press
reference contrasts with the gray band in that gameplay screenshot. Distant
mountains are legitimate source scenery; this comparison does not identify
the exact material or geometry responsible for the gray band.

Viewpoints and exposure settings are unmatched. No numeric exposure multiplier
or gamma diagnosis follows from these images. They establish a visual target,
not proof that sky-exposure-01 passes or fails: the later user screenshot shows
Player Details, not the corrected map. Current-candidate in-map imagery remains
required before further lighting tuning or visual acceptance.
