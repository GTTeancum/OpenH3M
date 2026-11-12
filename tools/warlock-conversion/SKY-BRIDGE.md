# Sky Bridge conversion

Source: Workshop 3003239190, `maps/s3d_sky_bridgenew.map`, H3 MCC.
SHA256 fb96270202d9e8330928727ad4e2aba862f3d40ec4d2cba8005a314bccda93ad.
No playable candidate or installation yet. Shared installed bundle is unchanged.

Script audit passes graph/opcode/signature checks: 2,475 active expressions.
Expression dry-run passes 3,301 capacity slots with 1,084 opcode remappings;
identity tag/string callbacks are diagnostic, not deployable. Reports in
`work/sky-bridge/script-dry-run.json` and the batch audit directory.

Collision has 42,706 2D nodes. Exact duplicate subtree sharing leaves 32,793,
26 above the pipeline's signed limit. Reversed-plane sharing reaches 32,429
but changes exact-on-plane surface selection; rejected. Validation tested
213,530 random points (no differences) plus 42,706 boundary points (18,739
differences). `compact_collision_2d.py` is diagnostic only and is not integrated.

`rebuild_whole_collision.py` feeds every authored polygon to the existing
verified offline builder. Optional memoization shares identical ordered
surface-list/axis/mirror build requests, without reversing planes. It reduces
the rebuilt 2D tree from 35,261 to 27,614 nodes. All polygon records, vertices
and edges are preserved. Visibility overlay fits at 6,409 planes and 20,434
leaves. However, reachability auditing found nine source surfaces absent from
the rebuilt query tree, and three newly reachable ones. The candidate is
rejected; no conversion integration was enabled. These nine polygons have no
exact duplicate vertex sets; do not assume harmless duplication.

Evidence: collision-rebuild.json, collision-surface-coverage.json,
missing-surface-details.json, collision-visible.json under `work/sky-bridge`.
The builder now reports reachability and refuses missing surfaces; preparation
requires this proof. Existing unrelated map builds retain their default compiler
behavior; memoization is opt-in for whole-tree rebuilding.

Next: retain authored 3D nodes/leaves and rebuild only oversized 2D references,
or prove complete equivalent coverage for the rejected surfaces. The builder's
`create_bsp2dnodes` takes projection axis, mirror and ordered surface list;
derive those from each authored reference and preserve its surface membership.
Do not simplify this map's collision or raise engine limits by inference from
the Battle Canyon exception. Reuse the existing offline compiler and tool cache.

## Accepted 2D-only rebuild

`rebuild_collision_references.py` rebuilds each original reference independently
from its original surface membership. The existing offline C# bridge has an
optional reference-input mode; the normal whole-tree entry point is unchanged.
The new result has 29,940 nodes, versus 42,706 authored nodes. Every one of
33,059 references has exactly matching reachable surface membership. Geometry
records compare unchanged. The original 3D nodes, planes, leaves, cluster bytes,
surface/edge identities and MOPP are retained during preparation. Reports carry
source/output SHA256 checks; output is `work/sky-bridge/references.output`.
This establishes conversion preflight, not native gameplay correctness.

Reproduce the collision preparation with:
```powershell
python -B tools/warlock-conversion/snapshot/tools/rebuild_collision_references.py --source D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map --scenario 'levels\multi\s3d_sky_bridgenew\s3d_sky_bridgenew' --work work/sky-bridge
```
Then `tools/warlock-conversion/build-sky-bridge.ps1` runs the shared pipeline.
The importer uses a separate reference-rebuild property so Gulch-specific
scenario/effect/ceiling adjustments never apply to Sky Bridge.

The current build passes runtime/script conversion and stops in geometry on
`shaders\halogram_templates\_0_5_1_0_0_1_0`, used by the authored hologram
screens/banners. No matching original-disc template was found. The full
source/template comparison is `work/sky-bridge/halogram-donor-audit.json`;
some listed tags may be unused. Preserve animation and overlays when adapting.

Four tutorial-family diffuse textures lack smaller mips. Audited format BC1,
fully opaque pixels, dimensions and curve; no stock disc ship_12 equivalent
was found. `missing_color_mips.py` filters color in linear space and encodes
512-max BC1 chains, preserving rectangular aspect ratio. The converter records
this approximation. Missing-mip audit is in the map work directory. The stripped
unsc_ship_06_diff resource is not covered by this adapter.

Removed reproducible input files and rejected whole-tree binary intermediates;
reports/logs and accepted 2D output remain. No game cache has been deployed.

## Material progress

Native templates now cover additive screen/detail overlays with neutral extra
edge fade, and additive-detail overlays with zero-amplitude extra warp. Original
animation routes are remapped for both. Sky alpha-blend/from-albedo materials
use the matching native standard-shader permutation with identical parameter
lists. Static lamp multiply overlays map to native self-illumination detail;
four static horizontal lamps use a white detail sample. Tint and intensity
compensation preserves their equations. The native Armory detail shader contains
4.59479, matching the primary shader source's DETAIL_MULTIPLIER; compensation
uses that value, not 2. Evidence: native-detail-constant-audit.json,
multiply-overlay-audit.json and native-alpha-sky-donors.json in map work folder.

Source equations: HaloShaderGenerator revision
5af3671c919e93b802dd6aa0899f6725de70992c, halo_online_shaders/overlays.fx,
self_illumination.fx, albedo.fx and warp.fx. The first three are retained under
work/powerhouse; warp.fx under work/sky-bridge. Warp amounts of zero leave
coordinates unchanged; unit edge/center tints leave color unchanged.

Latest build passes these adapters and stops at another native-template gap:
`shaders\halogram_templates\_0_8_0_0_0_3_0`. Rendering is not yet verified.

The next gap is isolated to three lighting materials: ceiling_lamp_01,
fluorescent_lamp_cold, and fluorescent_lamp_ceiling_cold. Their source parameters
are recorded in `work/sky-bridge/opaque-multilayer-lamps.json`. All are static,
but the latter two have nonzero layer depth (0.1); flattening them to a simple
illumination sample would lose view-dependent layer behavior. Existing native
multilayer/multiply candidates use additive rather than opaque blending, which
is not an equivalent substitution. No such substitution has been made.

### Expanded lamp donor and pixel audit

`work/sky-bridge/audit-native-multilayer.py` scans original disc render-method
 templates across both standard-shader and halogram families. Results are
`native-multilayer-all-families.json` (83 template occurrences). Do not equate
option number 8 across families: standard-shader candidates lack the layer
parameters, whereas halogram candidates expose depth/contrast/layer count.
An opaque halogram candidate `_2_8_0_0_0_1_0` exists, but has additive overlay,
not the source multiply overlay. It therefore does not directly clear the gap.

Decoded source overlay and self-illumination textures are recorded in
`opaque-lamp-overlay-pixels.json` and `opaque-lamp-layer-pixels.json`. All three
lamps use nonuniform RGB textures. The ceiling lamp ranges from roughly
(115,109,115) to white; the fluorescent textures span black to white. Their
opaque alpha does not eliminate depth: the pinned multilayer shader sums
shifted samples rather than alpha-compositing layers. Thus neither a constant
overlay tint nor an alpha-based collapse is justified. No source texture,
geometry, installed cache, or rendering behavior was changed by these audits.

## Final LIVE DLC for user playtest - 2026-11-03

Release: `.local/releases/sky-bridge-final-20261103/Sky-Bridge-LIVE-DLC.zip`. Content ID18AAC99766DAA98EB738DC5BDAD0065415607031, title4D5307E6, DLC type00000002. Native LIVE/STFS, unsigned for OpenH3M/RGH/JTAG Xbox360. Seven payload files match; container/ZIP integrity passes. No install or push.

Candidate27 passed the practical Slayer launch check at authored spawn: two native captures inspected individually, game running through180-second watchdog,11 hash checks passed/0 failed. Candidate26 crashed on shared writable vertex shader headers;27 gives private headers while preserving all3841 shader programs. Launch acceptance only; full traversal/audio/Forge/System Link and physical-console testing are not claimed. Small dark seams/speckles visible at spawn remain for playtest feedback.

User approved original Halo3 flare/camera behavior; SSAO/lightshafts omitted, exposure/bloom retained. The Forge-effects instruction was conditional; no blanket omission was applied. Pending user feedback.

Source: Sky Bridge, Halo Online; General Heed / Priception, [Halo Online Map Pack For Halo3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190). This project supplies Xbox360/OpenH3M adaptation.
