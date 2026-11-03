# Battle Canyon conversion

Current installation (2026-11-03): fresh Reach authoring-pipeline rebuild with
final Medium lighting, DLC ID 1733, installed for user testing. See
`../battle-canyon-rebuild/README.md` for final hashes, provenance and limits.
The Ryno source-port and October 25 installation notes below are historical;
that cache has been replaced, with a repository-local rollback copy preserved.

Source port credit: **Ryno**, [Remember Reach – Halo 3 Multiplayer Pack](https://steamcommunity.com/sharedfiles/filedetails/?id=3575686579).
Original map: Battle Canyon, Halo: Reach Anniversary map pack. See MAP-CREDITS.md.

Installed 2026-10-25; bounded native gameplay and menu/preview verified. See acceptance evidence at the end.

Source: Remember Reach - Halo 3 Multiplayer Pack, Workshop 3575686579,
`D:/SteamLibrary/steamapps/workshop/content/976730/3575686579/maps/cex_beavercreek.map`.
The mod declares Engine Halo3, scenario `levels\multi\cex_beavercreek\cex_beavercreek`.
Source size: 241,586,176 bytes. Read-only MCC H3 shared.map is required.

Separate DLC identity: battle_canyon, Battle Canyon, ID 1733.
Last Resort (zanzibar) is only the assembly basis; preserve all installed maps
and saved Forge layouts. Use original H3 Ghost, Mongoose, machine-gun turret
and Battle Rifle in place of the Reach/H2 wrappers. Retain authored geometry
and placements and the Forge palette with native equivalents.

## Format differences

This Workshop cache uses nonzero U13 section masks for debug data, tags and
resource pages. Its page/segment tables are in play, while older supported
Workshop maps embed them in zone. Readers now support both arrangements.
Shared files are supplied explicitly with --mcc-shared and opened read-only;
page sizes and CRCs are checked. A bounded in-memory page cache avoids
repeated shared-page decompression without creating extracted asset copies.
A prior Chiron bitmap was compared against the old reader and matched exactly.

The source sets MCC-only Eldorado object lighting. The profile uses native H3
probe sampling, preserving geometry and probes. The split-resource editor
array contains only a null decal reference; active references still reject.

Native terrain/surface shader inventories are saved in work/battle-canyon.
The source one-layer terrain variant has no exact disc template. Shrine's
one-layer variant retains its material with zero added environment tint.
One V16U16 normal texture is quantized to native signed V8U8 after mip selection;
tile/untile validation measured max component error 0.003937. This path currently
outputs one mip and needs visual review for distant texture aliasing.

## Build

Run inside this repository with Python 3.12 -B and TEMP/TMP=.local/build-temp.
Use build_scenario_checkpoint.py with --project C:/X360/ISOs/H3M --slot zanzibar
--battle-canyon --mcc-shared pointing to Workshop 3575686579/halo3/maps/shared.map,
--source as above, --basis C:/X360/ISOs/H3M/maps/zanzibar.map,
--xex C:/X360/ISOs/H3M/default.xex, the pack's halo3/fmod/pc/sfx.fsb,
and the existing vgmstream decoder. Current target: work/battle-canyon/zanzibar-01.map;
report: work/battle-canyon/build-01.json. Failed pre-serialization attempts do not
create a map; reuse this target until it exists. Never overwrite a hardlinked map.

Next: finish conversion, generate native preview BLFs, add to the existing LIVE
bundle using hardlinks for unchanged entries, then verify the exact native map
identity and actual gameplay/visuals. No engine changes are part of this conversion.

## Collision reduction prototype (2026-10-25)

User approved simplifying collision while preserving visuals. The original mesh
has 49,616 surfaces, 80,781 edges and 39,062 distinct surface planes (50,241 planes
including spatial-tree planes). Its polygons cannot simply be narrowed to H3.

`simplify_battle_collision.py` now generates an intermediate mesh, using pinned
fast-simplification 0.2.0 installed only under work/battle-canyon/python-deps.
It reduces only cliff walls, terrain and tunnels. Ramps, distant cliffs, bases,
special/breakable surfaces and all other polygons stay exact. No render data is
modified. Material-border coordinates are checked exactly after float32 rounding.

Current intermediate: work/battle-canyon/collision-reduced.npz and matching JSON.
30,609 surfaces, 50,066 unique vertex-pair edges, 19,426 vertices; 20,589 original
polygons untouched. Source has 15 vertex pairs with multiple distinct edges;
the output retains exactly their original unchanged owners. These are not newly
introduced nonmanifold connections and must retain original edge pairing when
constructing the retail topology. No open edges were introduced.

Sampled deviation upper bounds, in engine world units (not a full continuous
Hausdorff proof): cliffs max 0.07849, terrain max 0.02713, tunnels max 0.02656.
Every source vertex/triangle center and output vertex/triangle center was checked.
No numeric unit-to-meter conversion is assumed. All 989 tested border vertices
are unchanged. The initial reduction also simplified ramps/skybox and was rejected;
the current intermediate supersedes it at the same ignored working path.

Next: construct retail topology preserving original multi-edge pairing, rebuild
collision and authored visibility, rebuild/validate physics acceleration for the
changed faces, then resume map serialization and native tests. Polygon/edge counts
alone do not prove the final BSP tree fits. This is not installed or playable yet.

Reproduce with Python -B, the source above and --shared pointing to MCC H3 shared.map:
`simplify_battle_collision.py --source <source> --shared <shared>
--output work/battle-canyon/collision-reduced.npz`.

Retail topology/tree milestone (2026-10-25):
`battle_collision_topology.py --source <source> --shared <shared>
--reduced work/battle-canyon/collision-reduced.npz
--output work/battle-canyon/collision.input` reconstructs oriented edges,
preserving original edge identities for coincident two-sided polygons.
Round-trip validation checks every polygon loop. The result contains 50,081
actual edge records; the smaller earlier count was unique vertex pairs.
20,607 final polygons match original vertex loops exactly (including 18
triangles retained by simplification); their original planes are retained.

The existing shared Rebuild.dll successfully generated collision.output:
59,975 nodes, 23,268 planes, 28,243 leaves, 68,043 2D references,
13,046 2D nodes, 30,609 surfaces, 50,081 edges, 19,426 vertices.
Surface/plane/edge/vertex index limits pass; all input surface attributes,
planes, edges and vertices survive tree generation unchanged.
This is still an intermediate: authored visibility overlay, metadata mappings
and updated physics acceleration remain necessary before map serialization.
No Battle Canyon map has been deployed or gameplay-verified.

Physics milestone (2026-10-25): `audit_battle_physics.py` verifies one source
scene MOPP (525,327 bytes), class 13 covering all 49,616 terrain surfaces and
class 16 covering 792 instance indices. The metadata contains 1,173 instance
placements; the resource's 558 entries are definitions, not placement count.
The prior Forge key-partition assumption is not applied to Canyon.

`battle_collision_mopp.py --tree work/battle-canyon/collision.output
--source <source> --output work/battle-canyon/terrain-mopp.bin` compiles every
reduced polygon using the existing pinned offline compiler. Generated terrain
code is 322,090 bytes. Its four coordinate-domain floats exactly equal the
source MOPP, allowing a branch-local merge with the original instance subtree.
All original instance keys remain, old terrain terminals are removed, and all
30,609 new terrain keys are verified. The merged intermediate is 1,619,898 bytes
because branch relocation uses explicit jumps/absolute keys; further compaction
is possible, but correctness/integration comes first. Native behavior remains
unverified. Existing three Forge MOPP tests pass after extracting the shared
key relocation helper. This merged artifact is not installed.

`battle_collision_visibility.py` overlays authored render-cluster cells onto
the rebuilt tree, retaining collision geometry and reference arrays. Current
run is still processing (exec session 37512, Python PID 2864, started 04:17
local); resume/poll that handle before launching another. Its log is
work/battle-canyon/visibility.log. After completion, inspect reported counts,
integrate per-surface render mappings/seam edges/portal planes and the merged
MOPP, then serialize and run the native validation. Do not mistake intermediate
collision artifacts for a completed map.

The visibility run completed successfully: 89,561 nodes, 27,618 planes,
56,747 leaves. `prepare_battle_collision.py` now integrates it and the rebuilt
physics into the existing --battle-canyon build. All 47 portal planes already
fit the output plane table. There are no authored seam mappings; all 80,781
original edge metadata entries are null pairs, so new edges retain null pairs.
The render-link table contains 65,233 references after regrouping, within the
retail start-index limit. All 49,616 original surfaces' render references are
retained. Exact polygons retain their own references; simplified polygons
receive nearest same-material polygon-center groups. This lookup approximation
needs native decal verification; rendered mesh data remains unchanged.

Full assembly now passes the geometry stage. The object stage exposed unnamed
placements referencing null palette datums (Scenery, Weapons, Crates); these
empty source placeholders are now omitted only for the Canyon profile. Named
null placements still fail. Next failure was glass_window physics Shape+6=107.
TagTool's PhysicsModel.Shape identifies this as RuntimeMaterialType, despite
Assembly's Flags label. The source local material is brittle_glass and the
stock Last Resort global material table places brittle_glass at 107. Unknown
values now resolve through the shape's local material name and the target's
global material table, rather than expanding the guessed flag-value whitelist.
Existing model-physics and MOPP regression tests pass. Native gameplay and
packaging are still pending.

The subsequent object dependency was an A8Y8 (format 3) gravity-lift mask.
`encode_bitmap.py` now expands its luminance/alpha bytes losslessly into native
ARGB32 before tiling. Byte order is verified against TagTool
`TagTool/Bitmaps/Utils/BitmapDecoder.cs` at commit
ce2dc6ac13072b160752af618ea1dc143e2727ac (DecodeA8Y8); the reference copy is in
work/battle-canyon/BitmapDecoder.cs. All 65,536 possible luminance/alpha pairs
were checked. Current full-build output remains zanzibar-01.map; failed runs
have not serialized that file, so the same working path is reused safely.

The fifth-spartan prop exposed the same schema issue with runtime material 16:
its explicit global-name string is unset, but its local material name is
soft_organic_cloth. Stock Last Resort confirms index 16 has that exact name.
The resolver now accepts the local name only when it resolves uniquely in the
stock global table. It still rejects unknown materials; no guessed numeric
substitute or permissive flag-mask change was made.

Effect integration (2026-10-25): the source's plasma particles use animation
functions referenced by sampler-local ranges, without constant-register routes.
`effect_animation.py` now counts those preserved sampler references when checking
for orphan functions; out-of-range references still fail. The source audit is
work/battle-canyon/effect-animation-audit.json.

Legacy laser/rainbow flare curves have equal scalar scale bounds but nonzero
editor header parameters. `lens_reflections.py` retains their constant radius/
brightness ranges; the supported linear-spline payload remains checked.
TagTool's ScalarFunctionHeader and ScaleOutput reference is saved at
work/battle-canyon/TagFunction.cs, from commit ce2dc6ac13072b160752af618ea1dc143e2727ac.
No animated nonconstant curve is silently reduced by this change.

Original-disc particle audit found no exact water_spray shader variant, but
Valhalla's stock waterfall water_spray supplies the existing H3 equivalent.
The explicit alias reuses that complete particle and dependencies; it does not
invent a custom shader permutation. Audit: work/battle-canyon/particle-donors.json.

sun_flare_01 contains one legacy reflection, simple-box occlusion flag 0x10,
and an invalid selected reflection index 26. A narrowly checked conversion
normalizes this to retail's sole reflection zero while preserving the reflection
itself and the other fields. This correction requires native visual inspection.

Placement integration (2026-10-25): scenario string IDs now use the same source-
text-to-retail-table translation as imported tags, preserving authored variant
names and markers. Callers without a translator still reject nonzero IDs.
Object, spawn and environment stages completed after this correction.

Decal audit across the original disc found no `_0_0_0_0_0_0` shader used by
Battle Canyon's classic-map picture. Armory has `_0_3_0_0_0_0` with identical
parameters and unchanged pre-lighting/specular/bump options. The adapter retains
the image in a private fully opaque texture and uses native alpha blending.
Source/disc category names confirm only opaque versus alpha_blend differs.
Audits: work/battle-canyon/decal-options.json and decal-donors.json.
Decal serialization now completes; native appearance remains unverified.

Forge integration applies stock Halo 3 equivalents to MCC silenced SMG,
Automag, red plasma rifle and H2A camo/overshield entries. Palette entries stay;
their object dependencies use native SMG, Magnum, plasma rifle and powerups.
This follows the global stock-asset rule and avoids importing shared MCC
resources for weapons already represented in Halo 3. Import failures now add
the deepest failing tag's identity to the traceback for diagnosis.

Shared-cache correction: use the pack's own `3575686579/halo3/maps/shared.map`,
not installed MCC shared.map. Page zero verified 701,114,558 decompressed bytes
and CRC 0x7f838644; work/battle-canyon/shared-page-check.json records the check.
The pack override is in its nested halo3/maps folder, separate from its custom
map caches. No resource integrity check was bypassed.

All authored stages and all seven Forge categories completed with the pack shared
cache. Residency audit found seven zone manifests differing only in their Name
string ID: bitsets, sizes, ownership and hierarchy data are identical. The
converter now ignores only Name for equivalence comparison and translates each
name separately when publishing native manifests. Source evidence is
work/battle-canyon/residency-source.json. No residency masks were broadened.

First serialized candidate: work/battle-canyon/zanzibar-01.map, 197,513,216
bytes (188.36 MiB), SHA256
0ef6e9748934f04ccabf93659902031fc42b27f8a81edef85b6d0893e801aba3.
Reopen validation checks 415 collision trees, 56,747 BSP leaves and 143 runtime
decals. Native check 01 is separate; serialization is not gameplay acceptance.

Resource audit: 31,260,672 tag bytes; deduplicated required-base pages across
all manifests total 323,895,038 bytes. Including optional physical pages for
required resources gives 402,914,030 bytes. All referenced pages total
525,165,294 bytes, including shared and streamed resources. These are not
simultaneous residency counters and exclude runtime overhead; do not claim
the full console 512 MiB budget verified from these totals. Report:
work/battle-canyon/resource-footprint-01.json.

## Installed candidate 01

Gameplay trace `.local/loading-traces/20261025-050807-16968` loaded the new
battle_canyon identity, passed 11/11 resource hashes and ran to its 180-second
watchdog. Native captures at 110/145 seconds show the canyon/rock arch and the
base reached by the walking replay. This was a bounded route, not exhaustive
collision, Forge palette, sound or gameplay verification.

LIVE package menu trace `.local/loading-traces/20261025-051305-14524` verified
Battle Canyon selected by name with the correct native image preview. The native
installer's extracted files were byte-checked against all 49 payload entries.
Promotion: work/battle-canyon/promotion-01.json. Installed content ID:
7C4E476BACE9D635C27A21F2D8EE263885DCFA53. Existing six maps and saved profiles
are preserved; executable and disc maps are unchanged. The previous bundle is
retained as a rollback. Native extraction duplicates were replaced with hardlinks.

Correction check 2026-10-25: native run `20261025-175507-1292` used the accepted
map with the isolated split-occlusion renderer. Both 115/140-second captures were
inspected: canyon and base rendered, visible lighting remained, and the base-wall
view had no blue flare bleed. Logs contain hidden (0) and visible (126) sample
results, with no occlusion disable/fallback message. This checks real visibility
results rather than merely suppressing all flares. The renderer is not yet
deployed; map brightness/emission corrections are still separate candidates.

The intermediate zanzibar-01.map was removed after promotion (197,513,216 bytes
reclaimed); the accepted battle_canyon.map remains in payload-01 and installation
through hardlinks. Rebuild instructions regenerate the intermediate if needed.

### Candidate 02 brightness and mip correction

Source remains Ryno's Remember Reach H3 port of Reach Battle Canyon:
https://steamcommunity.com/sharedfiles/filedetails/?id=3575686579 .
`work/battle-canyon/zanzibar-02.map` built successfully (197,656,576 bytes).
Fixed V16U16 normal encoding to quantize every retained mip, rather than only
the largest level. Regression `test_normal_mip_conversion.py` passes and
checks smaller levels, selection and signed endpoints.

Native run `.local/loading-traces/20261025-181952-19820` completed with the
split-occlusion-query DLL. Both 115/140-second captures inspected: readable
canyon/rock arch and base doorway; no blue flare through the inspected wall.
Cached host frame-change timing: median 33.36 ms, p95 33.72 ms, max 50.19 ms,
zero intervals over 100 ms. Previous cold route had pipeline compilation
waits and four intervals over 100 ms. This establishes improvement on the
recorded route, not exhaustive traversal or console performance.
Remaining emission mappings include the circular Forerunner panels, gravlift
shell and shared autoturret. Not deployed yet.

### Circular-panel correction candidate 03 (2026-10-25)

Native dynamic-environment shader routing now binds the authored static cube to
both cube samplers. LOD0 and radiance compensation preserve static reflections
while retaining animated illumination. Native programs stay unchanged. Written
cache checks pass for both panels, including their scrolling curves; native
visual validation remains pending. Candidate: 197,804,032 bytes. Not deployed.

Origin: Halo Reach Anniversary Battle Canyon. Upstream Halo 3 MCC port:
Ryno's [Remember Reach pack](https://steamcommunity.com/sharedfiles/filedetails/?id=3575686579).

## Authored decal / collision correction (in progress)

The GPU capture at the reported cliff edge showed dirt/grass overlays passing
on one side of a triangle boundary and failing depth on the other. Reconstructed
post-transform vertices matched reduced collision surface 23422 within 0.000001
world units. Its source surface is 25795; one vertex had moved during reduction.
The visible terrain was unchanged. This establishes a collision/overlay
intersection rather than a lighting-only fault.

`battle_decal_protection.py` reserves original collision polygons beneath the
143 authored decals before simplifying the remaining terrain. It uses the
runtime maximum radius and conservative handling of zero placement scale;
polygon bounds touching the sphere are retained in full. The field definitions
agree with [TagTool's decal system](https://github.com/TheGuardians/TagTool/blob/master/TagTool/Tags/Definitions/DecalSystem.cs)
and [runtime decal structure](https://github.com/TheGuardians/TagTool/blob/master/TagTool/Tags/Definitions/ScenarioStructureBsp.cs).
Native visual verification is still required; schema agreement alone does not
prove projection coverage.

Candidate intermediates use `collision-decal-protected` prefixes, leaving the
previous intermediates available. Generate with `simplify_battle_collision.py
--protect-decals --fraction 0.14`, then the existing topology, tree, visibility
and MOPP steps. Pass `--battle-protect-decals` alongside `--battle-canyon` when
assembling the map. Integration rejects any protected polygon whose original
oriented vertex identities were lost.

Offline evidence: 32,351 surfaces, 27,687 planes after visibility overlay,
54,246 leaves, 9,617 2D nodes, 53,377 edges and 20,980 vertices. All original
12,257 protected polygons retain exact positions and winding; all 32,351 physics
surface keys and 792 original instance keys are present. Visible geometry is
not edited. Reduction elsewhere is stronger than the prior candidate and needs
native traversal verification. These counts establish format limits, not total
Xbox 360 memory residency. Candidate target is `work/battle-canyon/zanzibar-06.map`;
no claim of native acceptance or deployment until its check is complete.
