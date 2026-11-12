# Powerhouse conversion

Source is the Halo 3 MCC Halo Online pack 3003239190, `s3d_powerhouse.map`.
Build entry point: `build-powerhouse.ps1`; source pack shared.map and sfx.fsb
are required, with installed MCC Halo 3 audio as a fallback donor.
Build candidates exist and reach native gameplay, but visual defects remain.
Powerhouse has not been accepted or installed; see the latest checks below.

Current selected full candidate: `work/powerhouse/zanzibar-63.map`, staged in
`work/powerhouse/payload-63`. The normal build now prepares the reviewed
river shaders automatically; this map is byte-identical to native-tested59. Default ambient is authored (q=0); only this
map's exposure ceiling changes from 2 to 4 stops and bright-area sensitivity
from 0.3 to 1. OpenH3M now enables small
D3D12 resolve readback for native auto-exposure. Full lighting acceptance is
still open; q=8 and local room-fill experiments are superseded as defaults.

- Confirmed: affine storm-UV repair removes the rectangular sky artifact;
  missing CPU resolve feedback suppressed native auto-exposure, and small
  readback restores it. Native Forge menu, Fusion Coil creation, budget and
  release work. See latest native lighting evidence below.
- Open: waterfall spray and remaining animated effects, audible sound quality, broader traversal,
  probe-lit object consistency and saved-variant checks. Resource ownership and
  stock-page preservation are audited; full semantic asset reuse is not yet signed off.
- Test-only interior payloads relocate spawns and must never be installed.
- Console and System Link behavior have not been tested.

The diffuse-only four-layer terrain permutation has no environment constants
or sampler despite its option bit. Native Bunkerworld has the same four-layer
parameter tables without that inactive bit. The adapter verifies exact tables.

Collision-only shader references include stripped images. The new BSP adapter
omits only optional render references absent from the BSP render-material table,
retaining collision rows and exact named stock H3 physical material assignments.
Conveyor references are excluded. All source Powerhouse physical-material names
resolve at the same native indices. This progressed the build to its next
unsupported shader; native physical behavior is not yet checked.
Evidence: `work/powerhouse/collision-physical-materials.json`,
`work/map-conversion-batch/collision-material-use.json`. Native warehouse contains
an invalid collision render reference; its main BSP does not use that row, so it
alone does not establish active-surface behavior. ManagedDonkey's
`structure_collision_material` explicitly permits INVALID_TAG and stores
`runtime_global_material_index` separately:
https://github.com/twist84/ManagedDonkey/blob/main/game/source/structures/structure_bsp_definitions.hpp

## Shader conversion progress

The computer hologram now maps to native Armory `_0_5_1_0_0_0_1`.
Only its color animates; the scanline texture and overlay UVs are static.
`hologram_overlay.py` checks zero albedo, identity UVs, sampler fields and animation
routes before baking the static multiply overlay/tint in linear color space.
Overlay intensity multiplies the existing illumination intensity. The authored
color animation is remapped by parameter name to native shader registers.
The detail scanline sampler and edge fade remain intact. This is a bounded
512x512 BC3 resampling approximation, not bit-exact source texture sampling.
Ten mip levels are retained. Round-trip decode of every tiled mip passed:
`work/powerhouse/computer-bake-validation.json` (380,928 tiled bytes; maximum
base-level linear RGB error 0.04744, mean 0.000434 against the resampled bake).
Runtime screen appearance is still unverified.

Light volumes use native Guardian `_0_8_1_0_0_4_1`. Four coincident layers,
zero layer depth, unit depth attenuation and unit contrast reproduce the
source simple illumination: native code averages the four equal samples.
The original intensity is unchanged. Disabled source illumination stays zero.
Both overlay operations and their animated UV routes are retained. Additional
native samplers use stock white; no source runtime textures are discarded.

Powerhouse water uses native Valhalla `_0_1_1_1_1_0_1_3`. Its pure RGB color
(20,40,44)/255 is exactly represented by a linear one-pixel watercolor texture
with unit coefficient. The adapter rejects animated or nonrepresentable colors.
Wave/foam animations and authored parameters continue through native routing;
wave arrays use the existing documented native substitution path.

Shader math references saved under `work/powerhouse/`: overlays.fx,
self_illumination.fx, self_illumination_halogram.fx, halogram.fx, from
https://github.com/Beatthezombie/HaloShaderGenerator/tree/5af3671c919e93b802dd6aa0899f6725de70992c/halo_online_shaders

Device-machine light probes now receive the same recursive schema-name
normalization as air/scenery probes; their fields/layout are unchanged.
Particle physics preserves bit 8, omitted by Assembly's schema but present in
stock Armory particles (flags 0x101) and TagTool's shared definition. Audit:
`work/powerhouse/native-pmov-bit8.json`. It was not discarded or guessed away.

The custom DMR now converts its native pickup fields using the original H3
BR UI family (OLD message/sort 4/0). Seven English DMR HUD labels derive from
native BR templates, retaining native control tokens and replacing the weapon
silhouette with literal DMR. This does not replace the custom weapon. The label
round-trip audit is `work/powerhouse/dmr-label-validation.json`; final emitted
cache and native pickup behavior remain unverified.

The residential fan is an authored Gear machine. Its missing native collision
response/padding fields use the zero values found in original H3 fans; source
movement fields are retained. Device probes have passed conversion.

A batch sound audit found thirteen custom ambient tags whose hashes are absent
from all installed bank indexes. Explicit native aliases use computer telemetry,
whirring computers, server loops, human electrical hum, Last Resort turbine,
Valhalla brook/creek/waterfall loops and Longshore pipe pressure. Source looping
sound placements remain. DMR samples are present and remain custom. See
`work/powerhouse/sound-bank-audit.json` and `native-ambient-donors.json`.

Three Powerhouse water-spray particle variants require unsupported shader
variants. They use the stock Valhalla waterfall-spray particle under the native
asset policy; source effects and emitters are retained. Visual appearance needs
native inspection. No Powerhouse map has yet been installed or accepted.


2026-10-25 continuation: stock Valhalla mist now supplies the two atmospheric
waterfall-smoke variants and the named campaign waterfall counterparts. Audit:
`work/powerhouse/native-mist-donors.json`.

The existing Forge Gulch multi-texture sun converter now explicitly accepts
Powerhouse's 27-reflection flare. Every reflection and image remains; its existing
POC approximations (curve endpoints, equal-area circular scaling, occlusion-first
ordering) are recorded in the build report and need native visual review.
Source audits: `sun-flare-audit.json`, `sun-flare-curves.json`.

Horizon band, middle clouds and skydome use Cold Storage's matching hologram
variant with unit center/edge tints, disabling its extra edge-fade contribution.
The equation is color * lerp(edge_tint, center_tint, fade); both endpoints are one.
Authored animation routes are remapped rather than frozen for this adapter.

Heavy clouds use Citadel's original `clouds_2` standard shader template
`_6_0_0_0_0_0_5_3_0_0`. All six textures, eight float constants, albedo overlay,
illumination detail and alpha blend match. Native boolean `no_dynamic_lights`
retains the stock donor's zero setting. This changes shader family and exposes
diffuse lighting, so native sky appearance remains unverified. All six authored
animations are converted. Thunderhead's otherwise missing permutation uses
native simple illumination with zero color/intensity; its albedo is unchanged.

The build passes these dependencies and currently stops at the animated dust
shader `_1_4_1_0_0_0_0`, used by dust devils and valley-floor dust. The source
blends two moving detail textures using base-map alpha. The mask contains all
256 alpha values, so neither detail layer is inactive; removing one or freezing
the effect is not justified. Native shader/material alternatives need further
work. `sky-hologram-audit.json`, `sky-shader-donors.json`, and
`dust-mask-audit.json` preserve the evidence. No emitted map/native check yet.

Forge-name audit found no new palette display-name identifiers relative to the
native basis (`forge-label-audit.json`); this is not an in-game menu check.


2026-10-25 dust implementation: the additive detail-blend material is now split
into two native Zanzibar hologram draws. Static base RGB is weighted by (1-alpha)
and alpha; the two original detail textures retain their independent animation
routes. Exactly two parts and their eight subparts are added to the audited sky
mesh; vertex/index resources and collision are unchanged. Finalization rejects a
material-only conversion without the companion draw parts.

BC3 weight encoding failed a numerical image check and was replaced with ARGB8.
Both 256x256 masks retain nine mip levels, totaling 704,512 resource bytes shared by both
materials. `work/powerhouse/dust-weight-validation.json` records actual native
packed-mip decoding: maximum linear RGB error 0.008801, mean 0.000365 over 65,536
texels with independent test detail samples. This verifies texel-center math,
not native filtering or rendered appearance. BC1/BC3/BC5 output stayed byte-identical
to the prior encoder for square/wide/tall representative chains. Packed ARGB8
layout follows the same Xenia GetPackedMipOffset reference already in
`work/forge-world/reference/texture_util.cc`, using 1x1 blocks and 8-in-32 byte order.

The object and spawn stages passed with the two-draw implementation. The secondary
settlement sun flare now uses the existing endpoint approximation with its root
bitmap; animated isotropic scale endpoints are preserved and reported as an
approximation. The build next stops at active MCC camera lightshafts (flags 18,
intensity 0.15). User preference on omitting that unsupported post effect is pending;
it has not been silently removed. Source bloom/exposure/other common camera fields
remain required. There is still no emitted, installed or visually accepted map.

User approved omitting Powerhouse's MCC sun-lightshafts on 2026-10-25.
AGENTS.md records the narrow exception. The cfxs importer allows only the
Powerhouse camera tag's 0x144 extension and reports the omission explicitly;
other active MCC extensions still reject. A fresh build is now authorized.

Fresh build passed environment and reached decals. Current failure:
`decs:levels\multi\s3d_powerhouse\decals\s3d_docks_rust`, missing exact native
template `shaders\decal_templates\_3_2_0_1_1_0`. See build-01.json/build-run.log.
No cache emitted or deployed yet; next inspect decal options/native donors.


### Decal donor corrections (2026-10-25)

The rust decal uses the same bitmap and identical sampler for diffuse and alpha.
The guarded `_3_2_0_1_1_0` -> `_0_2_0_1_1_0` mapping removes that redundant
sample while retaining multiply blending, specular and bump. Parameter and
binding evidence: `work/powerhouse/rust-decal-{parameter,source}-audit.json`.
Native donor textures are not imported when all slots will be rebound to source
textures; this avoids stale donor resource handles and unnecessary resource bloat.
The edge decal's exact shader is in Shrine's standalone `rmd ` material
`objects\levels\multi\shrine\shaders\beh_stains`. Donor lookup now accepts
that shared postprocess layout as well as embedded `decs` materials. The build
passed both rust decals before reaching the dirt-traffic decal.

Dirt traffic uses separate color/alpha textures, with unit tiling and no sprites.
A guarded `_3_3_0_1_1_0` -> `_6_3_0_1_1_0` mapping retains both textures and
bump: untiled alpha coordinates equal the source coordinates under those checks.
Nonunit tiling, sprites, animations or unexpected transforms fail explicitly.
This mapping is undergoing a build check, not yet native visual acceptance.

Shader reference: HaloShaderGenerator commit
`5af3671c919e93b802dd6aa0899f6725de70992c`, `halo_online_shaders/decal.fx`,
saved at `work/powerhouse/decal.fx`. All 126 Powerhouse-prefixed decal materials
were inventoried against actual original-disc material donors in
`work/powerhouse/decal-donor-preflight.json`; this includes unused source tags,
so it is not a count of remaining placed-decal failures.

Dust validation correction: the reference DETAIL_MULTIPLIER is 4.59479, not 2.
It is shared by source and native draw formulas, so weighted-bitmap generation
is unchanged. Re-running the native packed-ARGB8 roundtrip with that factor gives
max linear RGB error 0.020218 and mean 0.000838. This supersedes the earlier
numerical values above; filtering and native accumulation remain unverified.

Latest build passed the guarded dirt-traffic conversion and stops at
`decs:levels\multi\s3d_powerhouse\decals\s3d_dirt_muck_3`, template
`shaders\decal_templates\_3_3_0_0_1_0`. Build process exited 1; no cache
emitted or installed. Native visual checks are still pending.


### Placed decal audit and compressed-channel combination

`work/powerhouse/audit-placed-decals.py` enumerates both scenario and BSP runtime
placements: 94 used palette entries/posts, 21 shader templates. The previous
126-tag inventory included unused tags. Full constants and bindings are in
`placed-decal-audit.json`.

For `_3_3_0_0_1_0`, the converter now combines authored BC color and alpha blocks
into BC3, without recompression, while retaining bump and the original native
blend/specular choices. It checks all decoded RGB and alpha pixels at each common
mip before accepting the result, including BC1 three-color incompatibility checks.
`validate-decal-combine.py` passed all four placed dirt/pollution materials: eight
common mips, 380,928 bytes per native resource. The source alpha stops at eight
mips while color has ten; the combined image uses the common eight. Color shares
alpha clamp addressing; decal-edge filtering requires native visual inspection.

The same guarded path is selected for Powerhouse's unit-tiled
`_6_3_0_0_1_0` pollution material, whose two samplers are both clamped. Earlier
non-Powerhouse mask conversion stays unchanged. All adapters retain native shader
programs; no engine changes or limits raised. No native visual acceptance yet.

The next build passed all dirt/pollution adapters and reached signage shader
`_3_3_0_0_0_3`. The combined-alpha path now supports diffuse-only bindings and
maps this to stock `_0_3_0_0_0_3`, preserving fully modulated tint instead of
flattening it. Identical full bitmap/sampler bindings reuse the original bitmap.
This signage change is undergoing a build check.

Latest build passed the first fully modulated signage material and exited 1 at
`levels\multi\s3d_powerhouse\decals\s3d_shotcode_backing_large_powerhouse`,
missing `_3_3_0_0_0_2` (partially modulated tint). No emitted cache or deployment.
Next compare its modulation constant with native tint modes and preserve the
reference `tint_and_modulate` formula rather than blindly replacing the mode.


### Partial and unmodulated signage tint

The three placed `_3_3_0_0_0_2` materials have modulation exactly zero or one.
At one, native fully modulated tint is equivalent. At zero, their grayscale tint
is folded into intensity and native tint becomes white. Nonendpoint modulation
and colored zero-endpoint tints fail explicitly. `validate-partial-tint.py`
compares the source/reference formula over 65,536 RGB values for all three:
maximum error 3.47e-18. This verifies tint algebra, not rendered filtering.
The build passed these signs and next reached unmodulated colored signage.

Static unmodulated `_3_3_0_0_0_1` and unit-tiled `_6_3_0_0_0_1` use a linear RGB
tint bake, native unit tint and unchanged intensity. Color scales outside [0,1]
are rejected. Different-size diffuse/alpha images use authored mip levels,
linear RGB bilinear resizing, linear alpha and a full ARGB8 output chain capped
at 512 per axis. The first backing sign is 1,400,832 native resource bytes.
This is a reported resampling/quantization approximation; native visual and
aggregate budget checks remain required. Same-size eligible BC inputs still use
lossless block joining, and identical bindings reuse their original bitmap.
Material reports now distinguish these routes and record tint overrides/scales.

The next build passed unmodulated small colored signage. Circle decals use
`_6_3_0_1_0_2` with zero modulation and map to exact native unmodulated
`_0_3_0_1_0_1`, retaining specular behavior. The two remaining poster families
`_3_3_0_0_1_1` and `_6_3_0_0_1_1` use native `_0_3_0_0_1_1` with unchanged bump
and tint; only alpha combination is adapted. All nine affected circle/poster
materials are static, nonsprite and unit-tiled in the placed-material audit.

The circle donor contains animated overlays. Static decal conversion now omits
donor Entry Points/Passes/Routing Info/Overlays and clears those headers for static
base-cache donors too. These are animation bindings, not shader entrypoint tables
in the template. Animated source decals retain their existing strict path.
A fresh full conversion is running with these corrections.

Latest full build passed every conversion stage, including decals (10.36 seconds)
and the empty source Forge palette. Final scenario coverage now stops on Bipeds
(2). `biped-placement-audit.json` proves both placement palette entries have null
0xffffffff tag references; these are not live decorative character assets.
Next handle these unallocated placements explicitly in object staging/coverage,
without silently skipping any valid biped references. No cache emitted yet.


### First emitted cache

Anonymous biped placements are now handled only when every used reference is
null and every placement unnamed. Existing null-palette omission compacts them
to zero; valid or named bipeds still require explicit support. Powerhouse has two
such rows. Its prematch_camera and podium_camera points preserve all six float
bit patterns and names, with original-only four-byte padding inserted at 0x24.
Evidence: `biped-placement-audit.json`, `camera-conversion-check.json`, and pinned
TagTool Scenario.CutsceneCameraPoint (Original-platform padding).

Build succeeded: 153,141,248 bytes (146.05 MiB), SHA256
`a5ec358cda2bb4b68da19298639c7af52a2b00a466bd2be94e7a8955351b98c3`.
Metadata used 5,244,524 bytes; all 559 serialized runtime decal references pass.
DLC identity powerhouse / Powerhouse / 1746; renamed cache SHA256
`84e89aff1a8b617705170c92c46e782624e2ec284e07553b5deb7f7bff5275de`.
Five previews use the Workshop metadata's Large artwork (powerhousesmall.png).
`payload-01` includes all 77 prior files by hardlink, with seven new files.
The shared installation has not been changed. First process-local native check
is `.local/loading-traces/20261025-094353-18000` (180-second watchdog).
File size is not a measurement of total Xbox 360 memory use.


First native run reached the correct Powerhouse menu/preview and gameplay.
Both captured frames (70500 and 125000 ms) were inspected individually. The
155000-ms capture missed the 180-second process watchdog because guest startup
lagged process time. Harness exited 1 explicitly; no false complete-capture pass.
Gameplay shows expected rocks/industrial roofs and weapon/HUD, but large opaque
sky shapes above the terrain are a visual rejection. Candidate is NOT accepted
or installed. Next investigate sky settlement material/geometry against source
and native donors; `sky-material-review.json` isolates its material reports.
The LIVE candidate at work/powerhouse/FCC831F3C23D326A1639379153865ABB56B0C3A8
is 1,880,883,200 bytes, SHA256
`ae51660fa852a6c6724a8e70564ed05bc9614048c0ebff6064c512059461a4bc`;
header/data/hash-tree integrity passed. That is not gameplay/console acceptance.


### Sky/scenery diagnosis after rejected native capture

`audit-sky-routing.py` compares source and native Citadel clouds: the heavy-cloud
blend/query mode remains alpha blend (3), and source heavy_clouds_mask alpha is
0..60. `audit-emitted-sky.py` maps every sky model material to emitted tags.
The model also contains distant terrain. The generic fallback dropped detail2,
detail3 and detail bump from several rock/mountain materials.
`audit-sky-terrain-donors.py` found original-disc exact shader families for seven
of nine terrain materials. Three have MCC-only nonunit detail-bump strengths
(2.5 for m35_small_rock_custom and 0.5 for ridge_rock/ridge_rock_v2), so blindly
using their native templates is rejected. Four unit/no-detail cases now use the
strict original donor path: sloped_rock_elements, valley_floor,
strip_mine_facility and distant_mountains. Candidate 02 is a diagnostic correction,
not full visual acceptance; remaining detail-strength/fallback work is recorded.
The 2.5 normal is BC3; ridge normals are signed BC5. Preserve the shader formula
bump.xy += detail.xy * coefficient, not a guessed normalized-vector strength.
Reference: pinned HaloShaderGenerator bump_mapping.fx, saved in work/powerhouse.
The first 02 attempt correctly rejected nonunit strength; no map was emitted.
Build-powerhouse.ps1 now takes OutputMap/Report for bounded candidate revisions.

### Candidate 02 native result (2026-10-25)

Candidate 02 is 155,443,200 bytes (148.24 MiB). Its renamed DLC cache SHA256 is
`96fbfe1277dbf02f86f3c51b5b51c55a2063f0fd8aa7a5b25de17562cece0595`.
Trace `.local/loading-traces/20261025-095739-39084` completed its 180-second
watchdog. Both native captures were inspected individually: 70000 ms shows
Powerhouse selected with the correct preview; 120000 ms shows actual gameplay.
Distant surfaces gained detail, but the large smooth shapes above the rocks
remain. The four exact donor mappings do not resolve the main visual defect.
Candidate 02 is NOT accepted or installed. Do not count process exit 0 as visual
acceptance. Remaining sky mesh/material assignment, sampling and unmatched
terrain shader paths need investigation before another candidate.

Cleanup: deleted the rejected 1,880,883,200-byte LIVE file
`work/powerhouse/FCC831F3C23D326A1639379153865ABB56B0C3A8` after checking its
resolved repository path and expected hash. Its integrity report remains;
the earlier file listing above is historical. No candidate 02 LIVE was built.
The accepted shared installation remains unchanged.

### Sampling and mesh audit

`work/powerhouse/compare-sky-samplers.py` compares source material sampling to
candidate 02 by matching material slots and texture parameter names. It found
donor filtering retained on valley_floor (source 4, target 0) and
distant_mountains (source 0, target 3). The exact Powerhouse material path now
preserves source image index, address, filtering and external selection, retaining
the donor's name-matched constant-transform index. Unsupported comparison,
padding or animated-sampler routes fail explicitly. Syntax validation passed;
this change has not yet been built or visually verified.

`work/powerhouse/compare-sky-mesh.py` and `sky-mesh-assignment-audit.json` compare
all nine sky meshes. Every original part's material/index range, subpart range,
flags and vertex count matches source. Only mesh 8 has the two intentional extra
dust draws. This rules out accidental part reassignment in metadata, but does
not verify vertex resource conversion, compression bounds or actual shading.
Animation sampler-field differences are recorded, not blindly patched: animation
routes are remapped separately and require semantic comparison.

Candidate 03 subsequently built successfully (`build-03.json`, `zanzibar-03.map`).
The post-build sampler audit (`sky-sampler-comparison-03.json`) confirms that
the valley_floor and distant_mountains filter discrepancies are gone. No native
visual acceptance is claimed. Source and candidate 02 sky compression flags
and all ten bound floats are also bit-exact (`sky-compression-audit.json`).

### Strip-mine material restoration, candidate 04

Pinned shader reference `material_models.fx` identifies material model 0 as
diffuse_only. Its `diffuse_only.fx` ignores the specular-mask argument and returns
zero analytical/specular radiance. With environment mapping disabled, the
strip_mine source variant `_5_2_0_1_0_0_0_0_0_0` can therefore use Bunkerworld's
`_5_2_0_0_0_0_0_0_0_0`. The converter guards the exact source variant. Reference:
https://github.com/Beatthezombie/HaloShaderGenerator/blob/5af3671c919e93b802dd6aa0899f6725de70992c/halo_online_shaders/diffuse_only.fx

Candidate 04 built successfully. `build-04.json` confirms all six source texture
parameters and all constants retained, with unit bump coefficient represented
by the native implicit default. This restores the missing detail layers instead
of substituting the generic three-texture material. It also includes candidate
03's filtering correction. Native test trace is
`.local/loading-traces/20261025-100929-9176`, with captures requested at 70000 and
120000 ms and a 180-second watchdog. Test result still pending at this entry.
`payload-04` contains seven new Powerhouse files and hardlinks to all 77 prior
files. No LIVE package or promotion was performed for this candidate.

Both candidate 04 captures were inspected individually. The menu/preview is
correct and gameplay loads. The strip-mine terrain at right now has restored
layered rock detail; the large smooth shapes at upper left remain. Candidate 04
is still visually rejected, not installed. This is evidence that restoring the
strip-mine material helps the scenery but does not fix the remaining main defect.

`compare-sky-vertices.py` reads source and candidate 02 GPU resources directly:
all nine primary vertex buffers, totaling 17,939 vertices, preserve position and
UV bit patterns exactly after endian conversion. Together with compression and
part audits, this narrows the remaining investigation toward materials; it does
not prove lighting/basis or runtime transforms correct.

Cleanup removed superseded uninstalled `zanzibar-03.map` after matching its
SHA256 to build-03.json; candidate 04 includes its filtering fix. The 155,443,200
bytes recovered and hash are recorded in `work/powerhouse/cleanup-03.json`.

### Ridge isolation and half-strength detail conversion

Diagnostic trace `.local/loading-traces/20261025-101507-30680` reached gameplay
and ended at its 180-second watchdog. Its single native capture was inspected:
zeroing index counts only for sky material indices 10,17,18 removes the large
smooth shapes. Thus the principal shapes belong to distant_ridge_rock,
ridge_rock/ridge_rock_v2, whose fallback materials omit authored layers.
The diagnostic is deliberately incomplete geometry and must never be promoted.
Script/report: `work/powerhouse/diagnose-ridge-materials.py` and
`diagnostic-no-ridges.json`. A rectangular cloud boundary also becomes visible
behind these surfaces; cloud blending still needs assessment after ridge repair.

The two ridge_rock materials use exact native four-layer shaders except for an
MCC-only 0.5 detail-normal coefficient. `normal_strength.py` bakes that factor
into a private signed BC5 copy, retaining all authored mip levels and byte size.
It preserves interpolation modes, checks every valid decoded sample, rejects
normal reconstruction outside the unit XY disk, and enforces a maximum error
of one signed-eight-bit step. Special selector behavior is checked through
decoded output rather than assuming endpoint scaling alone is safe.
Actual top_rock_zbump validation covers 11 source mips, max component error
0.007874015748031538; native 512-sized mip chain is 380,928 bytes. Filtering and
in-game visual fidelity remain unverified. The coefficient-2 distant ridge and
2.5 small-rock material remain unresolved; this adapter does not silently clamp
them. Candidate 05 build is in progress at this entry.

Candidate 05 subsequently built successfully. Its material report validates
both ridge materials with all six textures and all constants represented
(`ridge-build-validation-05.json`). Native visual validation is still pending.
Cleanup of the finished isolation map/payload was rejected by automatic policy;
those diagnostic files remain. Do not treat them as accepted map candidates.

### Candidate 05 result and distant-ridge conversion

Trace `.local/loading-traces/20261025-102140-14428` completed its 180-second
watchdog; the single native gameplay capture was inspected. The right-hand ridge
now has surface detail, but the large smooth left ridge remains. Combined with
the prior isolation, the remaining major surface is distant_ridge_rock.
Powerhouse is still not accepted or installed.

`strong-detail-audit.json` records its two static normal transforms: base 10x
with offset (0.2,0.95), detail 5x with offset (0,0.3), using the same caverock
bitmap and coefficient 2. About 10% of base-mip samples exceed the unit XY disk
if doubled, so the half-strength adapter cannot be reused with clipping.
`fused_ridge_normal.py` instead precomposes the two sampled normal layers,
including the original coefficient, into a native 1024-square V8U8 normal chain.
The output uses the detail transform; the second native normal is neutral.
All four color layers remain authored. Guards require the reviewed bitmap,
frequency ratio, coefficient, static sampling and shared normal reference.

This is explicitly reported as an approximation: 20,000 deterministic random
UV samples at 1024 gave mean angular error 1.188 degrees, p95 3.257, max 11.674
against the unbaked shader formula (`fused-normal-feasibility.json`). Hardware
filtering and native visuals still need checking. The 11-level native payload is
2,801,664 bytes, rather than silently normalizing/clipping the source detail.

The initial V8U8 mip roundtrip caught a 4-KiB subresource alignment omission;
the build was interrupted before using output. TagTool XboxBitmapUtils and
Xenia texture_util both align each subresource to 0x1000. The corrected encoder
passes byte-exact full-chain roundtrips at 32,64,1024 dimensions (6,7,11 levels).
Existing BC/ARGB allocations were already multiples of 4 KiB and are unchanged.
`v8u8-mip-validation.json` records the successful checks. Candidate 06 rebuild
is underway; no native acceptance is claimed.

Candidate 06 subsequently built successfully; its fused-ridge report is marked
as an approximation and retains all named texture/constant inputs
(`fused-ridge-build-validation-06.json`). Native visual check is the next step.

### Candidate 06 native result and remaining small-rock normal encoding

Trace `.local/loading-traces/20261025-103026-19720` completed its 180-second
watchdog. The single requested native capture was inspected: the formerly
smooth large left ridge now has authored surface detail, alongside the repaired
right ridge and strip-mine terrain. This verifies the main ridge-texture repair
at the tested view, not full-map acceptance. Powerhouse remains uninstalled.

`validate-cloud-payload.py` / `heavy-cloud-payload-validation.json` untile the
emitted cloud textures and compare source-selected mips directly. All six base
payloads are byte-identical, including heavy_clouds_mask alpha. This rules out
damaged base-image payloads, not shader-family/blending differences.

`small-rock-normal-channels.json` records the remaining fallback's two linear
BC3 normals. RGB channels have nearly identical distributions around 128 while
alpha differs, consistent with DXT5NM alpha/green encoding. Pinned
HaloShaderGenerator `bump_mapping_util.fx` explicitly uses alpha/green under
DXT5_NORMALS, with 8-bit/6-bit signed-bias reconstruction. This needs a reviewed
decoder and full 2.5-strength composition rather than treating BC3 RGB as normal
XYZ or silently dropping its detail coefficient. The material's original native
Cook-Torrance shader donor exists in Cold Storage; its authored parameters are
in `strong-detail-audit.json`.

### Small rock and broader native material pass (07/08)

Candidate 07 implements the reviewed small-rock alpha/green DXT5NM decoding,
precomposes its 2.5-strength detail, and uses Cold Storage's exact Cook-Torrance
shader family. Native texture chain is 1,400,832 bytes; rectangular 1024x512
V8U8 mip roundtrip is byte-exact. At 20,000 random UVs the precomposed normal has
mean/p95/max angular error 1.852/6.169/24.398 degrees versus evaluating the two
source layers directly. This approximation is recorded rather than claiming
lossless normal filtering (`small-rock-fused-validation.json`).

Trace `.local/loading-traces/20261025-103915-23288` completed. Both captures at
112000/135000 ms were inspected. Initial view retains repaired ridges; the
process-local walk/turn ends facing a nearby wall with conspicuously patterned
fallback shading. This is not a successful broad visual acceptance pass.

Earlier "last fallback" discussion applied only to the sky model's rock
materials. A wider audit finds 141 remaining Powerhouse rmsh entries, of which
99 have exact original-disc shader templates. Parameter preflight clears 56:
source/target texture and float-constant sets match, apart from implicit unit
bump strength; Boolean values also match the selected donors. These are recorded
in `powerhouse_materials.py`, with runtime variant guards. Others remain explicit
fallbacks requiring visual assessment or further conversion.

Candidate 08 built all 56 native mappings with no unrepresented named parameters
(`exact-material-build-validation-08.json`). Three animated materials also retain
their converted functions. Initial build rejected vet_control_panel_screen's
sampler function range; it is now bounds-checked and retained because animation
conversion preserves overlay order while remapping register routes. Animation
reporting no longer falsely labels successfully converted functions as frozen.
Native visual verification of candidate 08 is pending; no promotion occurred.

### Candidate 08 wall regression check

Trace `.local/loading-traces/20261025-104843-44864` completed its 180-second
watchdog. Both native captures (112000 and 135000 ms) were inspected individually,
and the wall view was compared directly with candidate 07. The conspicuous
shiny/distorted pattern is absent in 08; the wall now has muted surface detail.
The initial outdoor view retains the repaired ridge detail and industrial
structures. This is bounded evidence, not whole-map acceptance. A wider Forge
overview check follows; shared installation remains unchanged.

### Wider candidate 08 check and cloud routing repair

Trace `.local/loading-traces/20261025-105323-36576` completed its watchdog.
Both native captures (112000/140000 ms) were inspected individually: exterior
terrain and an interior doorway rendered, but the exterior exposes a straight
rectangular cloud edge. The intended Forge overview remained in player mode;
it is not evidence of successful monitor flight. Candidate 08 is not accepted
or installed.

`cloud-animation-routing-08.json` identifies five lost sampler function ranges:
one on mid-horizon clouds and four on heavy clouds. Functions themselves were
converted (one and six respectively), but the specialized material importer
wrote zero into the sampler animation-range field. The Powerhouse sky path now
retains those ranges after validating their start/count against the function
table. Conversion preserves function order. Candidate 09 is rebuilding; this
is a verified routing repair, not yet proof that the rectangular edge is fixed.

Candidate 09 built successfully. `cloud-animation-validation-09.json` verifies
all five source sampler ranges exactly in the emitted native material records,
with source/native function counts unchanged. Payload/preview reports are
`payload-09.json` and `previews-09.json`; the prior 77 bundle files are hardlinked
into `payload-09`. Native visual verification remains pending. No LIVE package
or installation promotion was performed.

### Candidate 09 visual result; source-derived diffuse correction

Trace `.local/loading-traces/20261025-105957-17800` completed its 180-second
watchdog. Both requested native captures were inspected individually. Exterior
cloud edge remains; interior surfaces, lamps and monitor panels render. The
run remains in player mode, not a successful monitor overview. Animation binding
repair is verified in data, but does not resolve the edge.

Pinned HaloShaderGenerator `material_model_none.fx` was retrieved at revision
5af3671c919e93b802dd6aa0899f6725de70992c. It explicitly sets diffuse radiance to
zero; the native cloud donor instead uses diffuse_only. Its matching
two_detail_overlay albedo multiplies RGB by overlay RGB, while alpha is separate;
self_illumination_detail samples independent textures. Candidate 10 therefore
uses a private black-RGB copy of the overlay bitmap, preserving all BC3 alpha
bytes/mips, to remove only the donor-added diffuse term. Source/shared texture
resources remain unchanged. This is source-derived; native visual verification
is still required and no installation promotion has occurred.

Candidate 10 built and staged in `payload-10` with the prior 77 files hardlinked.
`validate-cloud-diffuse.py` validates actual emitted native bitmap payloads:
all five unaffected cloud textures remain byte-identical to selected source
mips; the private overlay's base alpha blocks are byte-identical and all RGB
blocks decode black. The adapter preserves alpha bytes across the full source
mip chain before the established tiling conversion. Native visual check remains
pending. Reports: `cloud-diffuse-validation-10.json`, `payload-10.json`,
`previews-10.json`. No game process remains running; no LIVE promotion occurred.

### Candidate 10 native check

Trace `.local/loading-traces/20261025-110839-43936` completed its watchdog.
Both requested captures were inspected individually: 112000 ms still shows the
straight cloud-layer edge; 140000 ms shows an outdoor industrial/ridge view,
not the expected interior/monitor overview. No full-map or monitor-flight proof
is claimed. The edge persists after both source-derived cloud repairs.
`cloud-constants-query-10.json` confirms all named constants and blend-query
values match source for the six main cloud layers. Do not attribute the edge
to those values without new evidence. Candidate 10 remains uninstalled.

### Offline localization of the remaining sky discontinuity

`work/powerhouse/project-sky-vertices.py` uses the 112-second observer record
from candidate 10's existing native trace and projects authored source sky
triangles. It writes `sky-edge-projection.json`, including camera data, source
buffer descriptors, candidate vertices and depth-sorted triangle intersections
on both sides of the visible discontinuity. The single source model node has
identity translation/rotation/scale. Projection still assumes world-space sky
placement and horizontal FOV; it is diagnostic evidence, not confirmed draw
attribution or a render reproduction.

The probes cross heavy-cloud triangles `[3,38,1]` and `[37,3,38]`, with the
skydome and lower-cloud dome behind them. Some upper-right probes also hit
ridge geometry. Do not assign the defect to the heavy-cloud shader solely
because the discontinuity appears in the sky; source geometry/placement must
be reconciled with the actual draw before another material substitution.

`compare-sky-sorting.py` checks candidate 10 against source. Both have zero
explicit part-sorting plane records; all nine meshes retain identical mesh
flags, rigid-node indices, vertex/PRT types and index types. This rules out
lost sorting records or changed mesh sorting flags. All nine source meshes
also carry a separate format-14 float3 vertex-color buffer, which the next
draw-data check should include alongside the already-validated primary
position/UV/basis buffers. No cache rebuild, game launch or promotion occurred
during these offline checks.

### Candidate 11: native unlit sky and verified remaining seam

All nine format-14 vertex-color streams (17,939 vertices) compare bit-exact
against source after endian conversion; see `sky-sorting-10.json`.
Four source illumination/additive sky materials now use Guardian's native
`_0_5_1_0_0_0_0` template instead of introducing Cold Storage edge fade.
The added albedo constants are unused by the source-equivalent illumination
path. `unlit-sky-validation-11.json` verifies all source named constants,
semantic sampler transform bindings and animation ranges in the emitted cache.
The generic float-index remapper already handles these bindings. An accidental
second remap produced candidate 12, which failed validation; it is rejected.
Do not stage or deploy candidate 12.

Candidate 11's first native run was stopped by the agent, not a game crash.
The repeat with the established shared shader cache completed its 180-second
watchdog: `.local/loading-traces/20261025-120129-34448`. The native
`proof-loaded.png` was inspected individually: Powerhouse terrain, buildings
and HUD render, but the straight sky discontinuity remains clearly visible.
This does not establish full-map acceptance, monitor flight or audio behavior.
No LIVE bundle or installed map was promoted. Next diagnosis needs actual
sky draw/placement evidence rather than another speculative shader swap.

Automatic approval review rejected cleanup of candidate 11 and its payload
as "blocked by policy" without a specific reason. Those files were retained
and reused for the validated repeat; no alternate deletion method was used.

### Candidate 11 geometry and sky-reference audit

`work/powerhouse/audit-sky-model-metadata.py` compares named scalar fields
recursively using the MCC and retail render-model schemas. String identifiers
are resolved to text before comparison. All 34,420 compared fields match;
the only block-count differences are the documented two dust materials,
two dust parts and eight dust subparts. Resource identifiers, tag references
and opaque data are explicitly excluded from this metadata comparison.
All nine render index buffers also match after endian conversion, including
primitive restart values (67,567 indices total).

Both scenario sky entries reference scenery, have name index -1 and active
BSP mask 1. Their object bounding radii are 30,000 and bounding offsets are
zero. These checks do not prove runtime sky placement or draw ordering.
Evidence is saved in `work/powerhouse/sky-model-metadata-11.json`.
No cache rebuild, native run or installation change was needed for this audit.

The pinned shader reference was also compared across `halogram.fx`,
`shader.fx`, `entry_points.fx`, `blend.fx` and `albedo.fx`. Both families use
`albedo.w` for alpha blending. Two-detail-overlay alpha is
`lerp(detail.a, detail2.a, base.a) * overlay.a`; its RGB overlay is independent
of that alpha. These reference equations do not reveal an additional family
alpha mismatch. They are not proof of the actual compiled native shader's
execution or draw order. No further shader substitution was made.


## Lighting priority — 2026-10-28

The user identified poor lighting as the larger issue; resolve scene readability
before further sky-edge tuning. The current candidate is not accepted or installed.
Source: Powerhouse (Halo Reach lineage, Halo Online version) from
[Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190),
Workshop creators General Heed and Priception (verified 2026-10-28).
The original-Halo-3/OpenH3M adaptation is this project's work.

Candidate 11's active scenario references its converted camera, sky, global
lighting and lightmaps. There are no cluster camera overrides. Its camera flags
and seven exposure fields exactly match the source: auto target -2.7369656563 EV,
bounds 0..2 EV. Independent pinned TagTool decoding of the active scenario's
lightmaps confirms all ten compressed layers match source bytes exactly, and all
54 lightmap compression coefficients match. This rules out missing arrays or
conversion corruption in those checked fields; it does not prove runtime lighting
or material correctness. Evidence: `work/powerhouse/lighting-*-14.json`.

A private diagnostic at `work/powerhouse/payload-lighting-14/powerhouse.map`
raises only that camera's auto target and bounds by 0.75 EV. Its checksum and
salted header hash are refreshed. This is a readability experiment, not an accepted
fix; inspect native output for sky clipping and ground/building detail before
adopting any exposure change. Lightmap, bloom and sky data remain unchanged.


Native result: **reject the +0.75 EV camera-only adjustment**. Both requested
native captures were produced in `.local/loading-traces/20261028-224259-37928`
and inspected. The sky loses highlight detail while shaded rock/building faces
remain excessively dark. Candidate 11's older native capture is the visual
reference; the executable versions differ, so this is not a controlled pixel
comparison. No brightness profile was added and no installed map was replaced.
The earlier run omitted `--capture` and provides no visual evidence. Next work:
trace shaded-surface irradiance/material response and derive a map-specific
lighting correction that preserves sky highlights. Lighting remains open.


## Vertex lighting diagnosis — 2026-10-28

An audit of 204 BSP materials found the examined rock, terrain and outer-wall
lighting multipliers retained from source. In particular, small-rock diffuse
coefficient 0.5 and its zero analytical anti-shadow control are unchanged.
Report: `work/powerhouse/bsp-material-lighting-audit-15.json`.

The active lightmap binds 1,487 instances: 1,315 use per-vertex lighting and 172
use the lightmap texture. Clusters have ten texture bindings and eight unbound
entries. All 1,315 vertex-lighting buffers (913,331 vertices) match source after
component reversal and signed-byte bias conversion, verified independently in
`work/powerhouse/vertex-lighting-audit-16.json`. Matching data still does not
establish acceptable scene lighting.

Private candidate 15 multiplied only the texture C0 luminance scale by 1.5.
Both native captures in `.local/loading-traces/20261028-224949-30800` were inspected:
the dark rocks remained. Do not promote this as a lighting fix; it does not
cover the dominant per-vertex path.

Private candidate 16 starts from candidate 11 and changes only the C0 RGBE
exponent in those per-vertex buffers. Each 20-byte vertex stores dominant
intensity followed by C0/C1/C2/C3; increasing byte 4 by two signed exponent
steps multiplies C0 by `2^(2/4) = sqrt(2)`. Zero C0 vectors remain zero;
911,287 nonzero vectors changed. Directional coefficients, intensity,
positions, normals, materials, exposure and sky remain unchanged. The compressed
resource page is rebuilt with CRC and salted SHA1 hashes, and cache/header
checksums refreshed. Resource readback matches the intended bytes exactly.
Reproduction: `work/powerhouse/prepare-vertex-ambient-16.py`.

Both native captures in `.local/loading-traces/20261028-225548-33184` were inspected.
Rock detail improves without the exposure experiment's washed-out sky. Building
faces remain too dark, and this spawn/short-turn test does not establish indoor
lighting or consistent illumination of texture-lit geometry and probe-lit objects.
Candidate 16 is a useful tuning experiment, not an accepted conversion. Continue
with coordinated map-specific lighting adjustment and a broader native view;
do not install or claim lighting complete. The sky rectangle also remains open.


## Reproducible ambient calibration — 2026-10-28

The build now accepts `-AmbientQuarterStops` (0..8, default 0) in
`build-powerhouse.ps1`, passed as `--powerhouse-ambient-quarter-stops` to the
assembler. Nonzero values require the exact Powerhouse scenario identity. The
option multiplies C0 by `2^(q/4)` in native static per-vertex RGBE buffers and
the lightmap atlas scale. It does not change exposure, directional SH, dominant
intensity, geometry or other maps. This remains experimental; default builds
preserve the authored lighting. Scenery/device probes are not yet calibrated.

`test_powerhouse_lighting.py` passes four checks: decoded gain and unchanged
other bytes, zero-vector preservation/overflow rejection, atlas isolation, and
source/default confinement. The candidate-17 resource was produced using the
same helpers with q=4 (2x ambient), then read back with checksum validation.
Both captures in `.local/loading-traces/20261028-230111-21356` were inspected:
rock detail improves substantially without the exposure-only washed-out sky.
Walls remain dark and need closer/indoor inspection. This is the current tuning
candidate, not full lighting acceptance; installed maps remain untouched.

Full build reproduction started with:
`build-powerhouse.ps1 -OutputMap work/powerhouse/zanzibar-18.map -Report work/powerhouse/build-18.json -AmbientQuarterStops 4`.
Use the report's actual status before treating that build as successful.


Full builds 18 and 19 completed. Serialized lighting audit of build 19 confirms
all 1,315 buffers / 913,331 vertices match the q=4 transform and atlas C0 is
26.594270706176758 (twice source). `build-lighting-audit-19.json` records this;
full-build native testing remains pending, separate from candidate 17's captures.

Build 18 exposed empty source Forge palettes. The Powerhouse-only empty-palette
fallback now retains native Last Resort entries and its 700-credit budget. It
only applies when all seven source categories are empty; future populated source
palettes are preserved. Build 19 contains 5 vehicles, 18 weapons, 15 equipment,
21 scenery, 3 teleporters, 9 goals and 19 spawners. Every serialized 48-byte row
and budget field matches the stock basis exactly (`forge-palette-audit-19.json`).
This verifies serialized data, not native spawning or complete Forge acceptance.

Current full candidate: `work/powerhouse/zanzibar-19.map`, staged as
`work/powerhouse/payload-19/powerhouse.map`. Next native check should use this
payload, inspect the restored Forge menu/spawning, and move beyond the spawn
view to walls/interiors. The sky seam, effects/water and stock asset-policy audit
remain required; no installed cache has been replaced.


## Native Forge and cloud isolation — 2026-10-28

Candidate 19 native run `.local/loading-traces/20261028-231105-22936` reached
Forge. Both produced captures were inspected sequentially: at 126000 ms the
Scenery tab displays native labels, counts and prices (Fusion Coil $4); at
145000 ms the fusion coil is visible and held, and remaining budget falls from
$530 to $526. This proves the restored menu and this object's creation. The
requested 168000 ms capture was missing at the 185-second watchdog, so the
harness correctly returned failure for incomplete capture coverage. Release,
post-release physics, and the other palette categories remain unverified. Use
a 210-second bound or an earlier release when repeating that last step.

Private diagnostic 20 (`payload-no-cloud-20`) starts from candidate 19, changing
only index counts for sky mesh 1 / heavy-cloud material 3 and its 27 subparts.
Header/content checksums are refreshed. Both native captures in
`.local/loading-traces/20261028-231458-43076` were inspected: the rectangular
sky edge persists. Thus this change is insufficient to remove the seam;
heavy-cloud projection alone did not establish its cause. Do not promote this
diagnostic or omit clouds in the final map. Next isolate the other overlay
layers (mid-horizon, thunderheads, cloud blend and horizon band) against the two
domes. `sky-layer-inventory-20.json` maps each mesh/part to its source material.
This does not constitute actual draw-call attribution. Candidate 19 remains the
complete-geometry base; no installed map was replaced.


## Sky seam isolated to malformed source storm UV — 2026-10-28

Native diagnostics 21/22/23 hid, respectively, the mid-horizon/thunderhead/blend/
horizon overlays, the lower dome, and the main skydome. Both requested captures
from each run were inspected; the rectangle remained. Removing the lower dome
also exposed white gaps, so none of these omissions is suitable for production.
Runs: 20261028-232102-36612, 20261028-232440-21856, 20261028-233033-8612.
Independent TagTool decoding confirms all ten mips of both skydome and far_storm
match source (`skydome-mip-audit-22.json`, `storm-mip-audit-24.json`).

Diagnostic 24 hides only material 6 (s3d_lighting_bolt, using far_storm), mesh 8,
part 0. Both captures in `.local/loading-traces/20261028-233535-27072` show the
rectangle gone. This identifies the responsible billboard; it does not justify
removing it. Candidate 25 tried a mathematically neutral detail-illumination
shader substitution; both captures in 20261028-234157-34364 retained the edge.
That substitution was reverted, restoring the original native Midship shader.

The source billboard has a concrete degenerate UV triangle. Its strip indices
are [0,1,2,2,3,3,4,5], with positions 2=3 and 0=4. Corners A=0, B=1, C=2, D=5
form a parallelogram within two packed-coordinate units. Packed UVs are
A=(10504,28131), B=(18907,56847), C=(18907,56847), D=(18907,28131).
B incorrectly repeats C, collapsing the first triangle's UV area to zero.
The affine correction is B=A+C-D=(10504,56847). Only B's packed U changes.

`powerhouse_sky.py` applies this guarded repair during the exact sky-model
resource conversion. It verifies topology, duplicated strip vertices, affine
positions and the specific UV defect; an already-correct source is left alone.
It preserves positions, normals, other UVs, shaders, textures and effects.
Candidate 26 is building with this repair and the q=4 ambient profile. Do not
claim the seam fixed until native output of that full candidate is inspected.


## Candidate 26 native sky repair confirmed - 2026-10-28

Full candidate 26 retains the original storm shader and full sky geometry.
Both native captures (112000 and 125000 ms) in
`.local/loading-traces/20261028-234713-21648` were inspected sequentially.
The rectangular sky edge is absent in both views. The serialized sky-resource
audit finds exactly two changed bytes (644544 and 644545), changing only
vertex 1 packed U from 18907 to 10504. Positions, normals, indices, all other
UVs, control data and fixups are identical to candidate 19. This establishes
the guarded affine UV repair without deleting the storm billboard.

Current full candidate is `work/powerhouse/zanzibar-26.map`, staged at
`work/powerhouse/payload-26/powerhouse.map`, with the q=4 ambient profile.
The foreground rocks are readable, but distant building walls remain dark;
closer and elevated views are being checked before accepting lighting.
This is not full conversion acceptance. No installed map was replaced.


### Candidate 26 broader lighting check

Native run `.local/loading-traces/20261028-235444-42872` completed its 185-second
watchdog with all three requested captures inspected sequentially. At 122000 ms
the monitor is outside above the rocks, facing the industrial buildings;
the sky rectangle remains absent and terrain is readable. At 133000 and
145000 ms the view is a Spartan inside a building, consistent with a respawn
after the scripted ascent. This is not evidence of successful traversal or
acceptable Forge boundaries. The interior ceiling, walls and floor remain
too dark despite visible ceiling lamps and blue computer illumination.
The q=4 lighting candidate is therefore not accepted. Candidate 27 tests q=8
(four times source ambient, twice candidate 26) while preserving directional
coefficients and exposure; it requires the same native route for comparison.

The historical dust metadata differences are added split draws, not deletions:
`dust_material.py` adds two parts/eight subparts for two additive native draws,
retaining the independent detail animations. Native animated appearance remains
unverified; no additional dust removal was made for candidate 26.


## Candidate 27 lighting comparison - 2026-10-29

Full build 27 uses q=8: C0 ambient is four times source, twice candidate 26.
`build-lighting-audit-27.json` verifies all 1,315 buffers / 913,331 vertices
and atlas C0 53.188541412353516 against the source-preserving candidate 11.
Directional terms and exposure are unchanged. The four ambient-helper tests pass.

Native run `.local/loading-traces/20261028-235950-26432` completed successfully
with all three captures inspected sequentially. At 122000 ms the outdoor
monitor view matches candidate 26 closely: terrain/buildings remain readable
and the sky rectangle remains absent. At 133000 and 145000 ms the Spartan
has respawned in a different interior room from candidate 26. Wall panels,
floor, pipes and trim have visible detail, with darker ceiling regions. This
is useful coverage but is not a matched before/after interior comparison.
The scripted ascent again does not establish successful traversal.

Keep build 27 as the next lighting candidate (`work/powerhouse/zanzibar-27.map`,
`work/powerhouse/payload-27/powerhouse.map`). The default build setting remains
source-preserving until a matched interior check establishes the selected profile.
Remaining focused checks include interior lighting at a controlled viewpoint,
probe-lit objects, normal traversal/Forge release, water/effects/audio and
animated sky/dust. Full conversion and lighting acceptance remain open.
No installed map, source asset, console behavior or shared cache was modified.


## Controlled lighting and shared-resource checks - 2026-10-29

Private `payload-interior-26` and `payload-interior-27` relocate 114 initial/
respawn markers and the fallback start to authored scenery row 12, position
(132.2938385, 246.0163574, 39.7001343), facing -2.854491 radians.
These are diagnostic copies, never installation candidates. Geometry, materials
and lighting are otherwise the corresponding full candidates. Candidate 27
run `.local/loading-traces/20261029-000523-24868` completed with both 110000/
120000 ms captures inspected: the same interior room remains stable, showing
metal uprights, wall panels and the adjacent outdoor courtyard. Candidate 26
is being tested at the identical viewpoint for direct comparison.

Resource audit of full candidate 27 preserves 3,593 stock external resource
records with identical owners, backing files, page descriptors and offsets.
Seven absent records belong to removed stock tags: masterchief_microbump,
two damage-crack textures, cement/tall-grass decorators and their grass/pebble
textures. No retained owner has altered external page descriptors. All native
resource owners resolve. The schema-based follow-up checks 64,863 reference
fields in live tags and finds no references to those seven removed handles;
seven opaque tags (groups <fx>, mffn) are excluded from that schema claim.
Reports: `shared-resource-preservation-27.json`, `shared-resource-aliases-27.json`,
`removed-stock-owner-reference-audit-27.json`. This does not establish the
whole-map semantic-equivalence audit or runtime resource residency. Shared
paths in the private build directory are resolved by the native game's disc
root, not by placing copies beside the private map.


### Selected baked-ambient profile

The q=4 counterpart completed in `.local/loading-traces/20261029-000824-17908`.
Both 110000/120000 ms captures were inspected sequentially and compared with
the identical q=8 interior viewpoint. q=8 reveals more ceiling/wall/doorway
detail while preserving the brighter uprights and exterior. Combined with
the full-map outdoor views, q=8 is selected for continued integration.
`build-powerhouse.ps1` now defaults to 8 quarter stops (4x source C0 ambient);
explicit 0 still produces authored lighting. The generic converter retains
its default 0 and rejects nonzero calibration on other maps. Exposure and
directional coefficients remain untouched. Evidence: `lighting-profile-selection-27.json`.

This settles the selected baked-ambient profile, not every lighting/material
question or full conversion acceptance. Probe-lit objects and remaining
water/effect/gameplay coverage are still required. Use the full payload-27
for further tests; the interior diagnostic copies must never be installed.


### Full-candidate Forge release verified

Full payload-27 native run `.local/loading-traces/20261029-001158-37160`
completed its 210-second watchdog with all three captures inspected in order.
At 126000 ms the native Scenery menu shows Fusion Coil $4 and budget $530.
At 145000 ms the spawned coil is held and budget is $526. At 168000 ms, after
release and returning to Spartan mode, the coil has fallen onto the sloped
ground and tipped onto its side. This closes the previously missed release
check for that stock object, with visible object lighting and ground collision.
It does not claim all palette objects or saved-variant/console/network coverage.
Evidence: `native-forge-evidence-27.json`.

The reusable process-local trace now has a guarded `powerhouse-courtyard`
walk route for the private row-12 diagnostic spawn: approach the left doorway,
step forward, turn left and look down. Coverage must be established from the
requested captures, not inferred from issuing input. Full-map placements are
unchanged; the diagnostic payload is never an installation candidate.


### Courtyard route did not reach water

Run `.local/loading-traces/20261029-001643-40640` completed and all four
114000/123000/131000/143000 ms captures were inspected sequentially.
The first view is the intended interior doorway; after movement the player
is facing a wall at close range, and the final two views remain there.
This does not verify courtyard traversal, water rendering or animation.
The route requires correction before reuse; input execution and complete
capture output are not a passing result. No map geometry was changed.


## Water viewpoint from geometry - 2026-10-29

Source render mesh 454 contains the rough-water material and 2,940 indexed
water corners, spanning (115.5613,225.9045,36.4915) to
(129.5613,256.9587,37.7840). `water-geometry-bounds.json` records decoded
world positions, not an inferred position from the shader name.
`locate-water-view.py` reconstructs main and transformed instance collision
triangles, excludes render-only instances, and tests segment/triangle hits
from nearby authored spawns to the water center. Row 113 has no occluders
on the 3.317-unit sightline; row 12 has six. This explains why a direct
view from the earlier interior was unsuitable.

Private `payload-water-27` uses row 113 position
(122.1687317,239.5111237,37.4652328), facing 0.521236934 radians toward the
water. Production geometry and full-candidate spawns remain unchanged.
The failed `powerhouse-courtyard` replay option was removed from the reusable
trace tool; the historical run remains a recorded failure, not a supported
route. Native water captures are pending.


### Courtyard water rendering and animation verified

Native run `.local/loading-traces/20261029-002341-2236` completed with both
110000/125000 ms captures inspected. The view clearly shows the courtyard
water surface, ripples, shoreline and surrounding lit building surfaces.
A stationary image comparison supplements the visual inspection: the water
rectangle (350,550)-(600,625) changes by mean 2.118 RGB levels, 74.9% of pixels
change by more than one level, and maximum change is 47. The adjacent static
wall rectangle changes by mean 0.0128 with maximum one level and no pixels
over one. Thus the water surface detail changes while the camera/geometry
remain stable; this is stronger evidence than simply seeing a textured plane.
Reports: `native-water-evidence-27.json`, `water-temporal-comparison-27.json`.
This closes this courtyard surface's rendering/animation check, not waterfall
spray, audio, player-water interaction or full conversion acceptance.

### Stock fan candidates require a substitution decision

The stock object scan (`stock-prop-candidates.json`) found warehouse fan_slow/
fan_reallyslow and Cyberdyne jump_fan. `fan-equivalence-audit.json` records
actual model bounds: source residential fan diameter about 1.0884, axis Z;
warehouse fan diameter about 2.5324, axis Y; Cyberdyne fan diameter about 1.0,
axis Y. Each has two nodes. These are candidate equivalents, not proof that
function/markers/animation or authored fit match. The jump-fan gameplay role
must not be imported into a decorative fan. Review the native warehouse Gear
behavior and source placements next; use original H3 if equivalent, applying
only the documented placement basis/scale conversion needed to preserve fit.
The current candidate still contains the source fan and is not accepted under
the complete asset-policy audit. No donor or installed asset was modified.


## Fan fixture equivalence and native inspection - 2026-10-29

`fan-behavior-audit.json` compares native machine fields: both the source
fixture and warehouse fans are Gear machines, flags zero, activation radius
zero; stock transition values differ and would remain stock if substituted.
There are three authored source placements, each horizontal at Z about 44.13.
The source model is not merely a blade rotor: active parts include 175 indices
for the downward light volume and 57 for lamp glass, plus metal and bolts.
`fan-node-material-audit.json` and `fan-active-parts.json` trace these actual
parts. Warehouse's fan_cage/fan model has only two metal materials. Thus it is
not a complete equivalent for the combined source fan/light fixture: a whole-
object substitution would drop supported authored lighting. No substitution
was made merely because both asset names contain 'fan'.

`fan-sightlines.json` finds an unobstructed view from authored spawn row 74 to
the fixture. Private `payload-fan-27` uses that position and facing, retaining
full geometry, resources and original fan placements. Native inspection is
pending. The trace helper now accepts up to 16 explicitly bounded inspection
steps through its existing exclusive H3IR encoder; it rejects manual/host input
and steps outside the late gameplay/watchdog interval. This allows a small
look-up without inventing another map-specific route.


### Combined fan/light fixture retained and animated

Native run `.local/loading-traces/20261029-003254-5224` completed. Both
120000/135000 ms captures were inspected in order: ceiling fan assemblies
remain in their authored recesses, blade positions change, and downward light
volumes are visible. Retain this combined custom fixture because the audited
warehouse ventilation fan lacks its active lamp and light-volume geometry.
This is an equivalence finding under the existing stock-asset policy, not a
new exception to it. Evidence: `native-fan-evidence-27.json` and the part/node/
behavior audits above. No replacement, scaling or placement correction was made.

### Native audio observation added

The trace helper can optionally observe at most 1,500 submitted audio frames
(8 seconds). It arms the existing child-only debugger at the generated guest
import mapping 0x82724634, XAudioSubmitRenderDriverFrame, after a bounded
gameplay delay. The SDK contract is six sequential big-endian float channels,
256 samples/channel, 48 kHz; the helper verifies the driver token and rejects
mixed clients. It retains raw submitted PCM and exports an interleaved six-
channel PCM16 WAV. This is before host gain/downmix and is not a performance
or physical-output-device test. Original instructions execute by the existing
single-step mechanism; audio buffers, guest code files and game behavior are
not patched. A water-view/weapon-audio run is in progress.

Correction to earlier working assumptions: native breakpoint events are in
`loading-trace.jsonl`; the abbreviated stdout log only prints attachment and
terminal status. The fan run records successful Powerhouse header checks and
11 passed / zero failed hashes. Do not infer missing native checks from stdout.


### Native PCM and weapon firing captured

Run `.local/loading-traces/20261029-003921-27452` completed, reading exactly
1,500 native audio submissions over 7.985 wall-clock seconds and retaining
8.0 seconds of six-channel PCM (384,000 samples/channel). Every value is
finite; peak is 0.291643. The SDK reports a two-channel 48 kHz output endpoint.
The original PCM, six-channel WAV, capture metadata and a mono audition copy
are retained inside the native run directory. The audition tool reported that
audio input is unsupported in this session, so no claim of hearing or sound
quality is made. Audio acceptance remains open at that level.

The runtime log records RT=255 at replay 125017 ms through 125812 ms. Native
PCM has a strong transient sequence during this interval, then returns to
the quieter ambient signal. The capture at 126000 ms shows 23 rounds, nine
fewer than the starting 32. An initial small-image reading of 32 was incorrect;
`work/powerhouse/audio-run-ammo-detail.png` is the magnified evidence.
Thus the firing/gameplay response and submitted audio response are established.
The screenshot was inspected; the audio contents were not listened to.
`native-audio-evidence-27.json` records the distinction. All 11 native hash
checks passed. No game or SDK rebuild was needed for this observation.


### Sky animation preservation and limited native view - 2026-10-29

`sky-animation-functions-27.json` compares the emitted sky animation functions,
periods and bindings against the source. The horizon clouds, heavy clouds and
two dust materials retain their authored functions. Static dome/ridge materials
are correctly static. `unlit-sky-validation-27.json` checks the affected native
constant/sampler remapping independently.

Native run `.local/loading-traces/20261029-004746-15164` completed with 11 passed
and zero failed hash checks. Both 125000 and 137137 ms captures were inspected
in order. The observer stayed fixed, but a nearby cliff obscures most of the
sky. These frames do not establish animated cloud/dust motion; that check stays
open. The visible storm area no longer shows the previous rectangular artifact.

Lighting status: candidate 27 is the selected q=8 baked-ambient candidate,
not final lighting acceptance. The matched interior pair shows more ceiling,
wall and upright detail than q=4 while retaining deep shadows. Probe-lit object
consistency remains open. No installed map was replaced.


### Object-lighting probe preservation - 2026-10-29

`work/powerhouse/audit-probes-27.py` independently compares named source and
emitted probe fields using each cache's schema and byte order. All 5,429
compared scalar values match: 143 scenery probes and three device-machine
probe records, each containing one sample. The source has zero root airprobes.
The comparison includes positions/bounds, placement identifiers, dominant
light directions/intensities and all 27 SH coefficients per sample; unknown
padding and remapped string IDs are excluded.

`probe-preservation-27.json` establishes that conversion has not lost or
changed those authored values. It does not establish visual consistency with
the q=8 surface adjustment, and does not justify multiplying packed probe
coefficients without decoding their representation.


### Cascade inspection exposes opaque fallback - 2026-10-29

Native run `.local/loading-traces/20261029-005449-18752` used private
`payload-cascade-27`, relocating only spawn markers to authored row 80. Both
120000/137137 ms captures were inspected individually. Spray and mist visibly
change, but the waterfall sheets have opaque dark regions and their surface
detail appears static. This is a failed falling-water material check, not a
waterfall acceptance. All 11 cache hashes pass, which does not resolve visuals.

The build report explains the defect: the five settlement pipe/fall materials
used the generic opaque fallback, omitted detail/overlay samplers and converted
zero animations despite source tables containing 5--11 animations each.
`waterfall-material-equivalence.json` traces actual source BSP parts and stock
Valhalla waterfall parts, including donor texture names and three animations.
`native-waterfall-materials.json` inventories original-disc candidate shaders.
Valhalla's falling-water shader uses a waterfall mask, two scrolling color
samplers, bump and alpha blending; its three active BSP parts contain 1,530
indices. The glass waterfall-base shader is not a falling-water equivalent.

Candidate 28 tests the complete original Valhalla material for these five
falling-water materials via explicit stock aliases. Authored geometry/UVs stay
unchanged; native mask/blending/animation stay stock. Horizontal pool water and
splash/decal materials are excluded. Native inspection is pending.


### Remaining material fallback audit - 2026-10-29

`remaining-fallback-materials-28.json` inventories 113 remaining rmsh fallback
materials in candidate 28, correlating the report with actual source animation
tables. This is not 113 confirmed visual defects; it identifies incomplete
parameter coverage requiring semantic review. Priority cases include the river
water/splash layers and omitted self-illumination on m30_lamp_glass, the two
m30_wire_tech variants, whiteboard/control-panel screens and DMR digits. Several
source materials contain 2--6 animations while the fallback emits none.
The ambient adjustment alone therefore does not establish complete lighting: 
restore supported emission/animation or reuse a semantically equivalent stock
material before signing off those surfaces. Do not compensate with exposure.

Candidate 28 integration audit confirms all five waterfall aliases resolve to
one native owner. All 1,951 lighting/geometry vertex buffers (36,978,576 bytes)
and 453 index buffers (3,609,120 bytes) are bit-exact versus candidate 27.
Evidence: `waterfall-integration-audit-28.json`.


### Native waterfall correction confirmed at courtyard cascade

Candidate 28 native run `.local/loading-traces/20261029-010133-9684` completed
with 11 passed/zero failed hash checks. Both 120000 and 137137 ms captures were
inspected individually at the same authored spawn/facing as candidate 27.
The opaque dark waterfall sheets are gone. Falling-water surfaces are now
transparent with changing detail; spray and mist remain visible. The native
Valhalla material is retained for these five explicit falling-water aliases.
`native-cascade-evidence-28.json` records the focused result. This does not
visually accept the distant/large waterfall views or unrelated river/splash
materials. Candidate 28 is the current working build; no installed map changed.
Missing lamp/screen emission is the next lighting priority, before any further
ambient/exposure adjustment. The overall conversion remains incomplete.


### Native lamp and object shader restoration - 2026-10-29

`remaining-material-donor-audit-28.json` finds 63 matching native program
families among the remaining 113 fallbacks. Parameter/switch preflight narrows
that to 12 matching complete input layouts, now listed by full source path in
`powerhouse_materials.NATIVE_OBJECT_VARIANTS`. This includes control-panel
emission, holo_projector animation, residential lamp emission and associated
object surfaces. The adapter is restricted to the Powerhouse source map and
checks the complete source variant before selecting the native program.
Authored sampler state is now preserved for these object paths as well as BSP
materials. Candidate 29 was an intermediate build before that sampler fix.

Candidate 30 also restores m30_lamp_glass through Sidewinder's native
_0_0_0_1_2_0_5_0_0_0 shader. All four sampler names and 18 constant names match
the source exactly. Its only added option is diffuse-alpha specular masking.
The opaque source has a separate emission mask, so a private base texture with
unit alpha makes the extra mask neutral; decoded RGB and authored mip levels
are retained. Two-lobe lighting, detail emission, tint, intensity and its one
animation remain source-authored. No geometry or ambient gain changes.

`emission-integration-audit-30.json` independently checks actual emitted model
and BSP material references: all 13 changed materials retain bit-exact named
constant values, image/address/filter/external sampler fields, packed sampler
animation selectors and all seven endian-converted animation functions. No
unrepresented source texture/constant remains for these materials. The native
fan/lamp view is pending; this audit alone does not establish visual acceptance.

Whiteboard detail emission still needs an adapter. Its static height scale is
zero, but that field has an animation route, so removing parallax solely from
the static value is not justified. The two m30_wire_tech materials also remain
open. See `lamp-whiteboard-source.json` and `native-rmsh-inventory.json`.


### Native lamp/control-panel emission confirmed

Run `.local/loading-traces/20261029-010855-29576` completed with 11 passed/zero
failed hash checks. Both 120000/137137 ms captures were inspected individually
and compared with candidate 27's same fan-room view. Previously dark ceiling
fan lamp rings now emit cyan light; wall control-panel displays now show their
authored yellow emission. Fan blade motion and downward light volumes remain.
The surrounding room retains the same baked ambient lighting; no exposure or
lighting gain was changed. `native-emission-evidence-30.json` records this
focused visual result. Other object materials still require appropriate visual
coverage; the whiteboard and wire-tech emission adapters remain open.
Candidate 30 is the current full working candidate and has not been installed.


### Boolean-to-real material switch conversion - 2026-10-29

Fifty additional reviewed fallback materials have identical texture and
constant inputs except for native `use_material_texture`: MCC encodes it as
a boolean, original H3 as a real constant. They now use their matching native
programs through the explicit Powerhouse path table. The existing named-switch
converter maps the source bit to four equal 0.0/1.0 components and maps retained
boolean switches by name. It rejects unsupported integer or enabled switches.
No material is selected by a loose filename substring.

Candidate 31 builds successfully. `material-integration-audit-31.json` reads
the actual emitted BSP/model references for all 63 reviewed materials (the 13
from candidate 30 plus 50 more). Source named constants are bit-exact, the extra
native switch matches the actual source boolean, sampler selectors are retained,
and all seven authored animation functions survive. This restores native
lighting/reflection/normal behavior that the generic fallback did not represent.
Native courtyard and upward sky views are pending.

The whiteboard function audit confirms height-scale overlay 5 has endpoints
0.0 and 0.05; the static zero does not disable parallax. Its height-map scale
is also animated. `whiteboard-functions.json` retains all six functions. The
available opaque parallax/detail-emission shader cannot simply be relabeled
additive: the pinned blend.fx distinguishes fog in-scatter and output alpha.
Do not remove the animated parallax or change blend metadata alone and claim
equivalence. Wire-tech height_scale is 0.2 and must also remain active.


### Native courtyard and sky views - candidate 31

Run `.local/loading-traces/20261029-011611-42700` completed with 11 passed/zero
failed hashes. All three requested frames (120000,145000,161137 ms) were
inspected individually. The courtyard shows the corrected surface shading
and retained pool rendering. The later two frames hold the same observer
position and forward vector, looking above the rooftops. Thin cloud wisps
visibly change over 16.137 seconds. Large cloud silhouettes remain broadly
stable, while their surface brightness/detail also changes; this is not an
entirely static sky. The comparison is retained in
`sky-temporal-comparison-31.json`.

The clear upward view reveals blocky fringes along the bright cloud edge.
This remains an open visual defect; animation evidence does not establish
full sky acceptance. Dust-layer motion is also not established by this view.
Candidate 31 remains the working candidate; no installed map was replaced.
All geometry and lighting buffers remain bit-exact versus candidate 30 in
`geometry-integration-audit-31.json`.


### Cloud-edge isolation and mip audit - 2026-10-29

`sky-bitmap-dimensions-31.json` compares source and actual emitted sky texture
dimensions/formats/mip counts. Heavy-cloud inputs retain full authored sizes:
wispy veins 256x256/7 mips, alpha mask 512x512/8 mips, illumination
512x512/10 mips. No downsampling explains the fringe.
`heavy-cloud-mip-audit-31.json` independently decodes every native mip with
the pinned TagTool validator and compares compressed blocks to the source.
All 25 mip hashes match the intended source data; only the previously audited
alpha mask RGB suppression differs intentionally, leaving alpha exact.

Sampler filtering remains source value zero (trilinear), not point sampling.
TagTool's primary definition confirms the enum mapping:
https://raw.githubusercontent.com/TheGuardians/TagTool/master/TagTool/Tags/Definitions/RenderMethod.cs
The exact/native sampler audit reports only named transform-index relocation
and the documented split dust routing. Source cloud mask/illumination previews
were decoded and inspected. Mip corruption and resolution loss are ruled out.

`sky-edge-projection-31.json` projects the captured upward observer through
authored sky geometry. At all four fringe sample points, heavy clouds overlap
cloud_blend, thunderhead, skydome and the lower dome. A private diagnostic
`payload-no-heavy-31` hides only the heavy-cloud mesh (28 part/subpart count
fields), preserving the other layers and production candidate. It must never
be promoted. Its matched upward native test is pending.


### Cloud-layer diagnostic results - candidate 31

Native run `.local/loading-traces/20261029-012536-34676` reached its
210-second watchdog. Both requested upward captures (145000 and 161137 ms)
were inspected individually. The bright-cloud block fringe survives with
heavy-cloud mesh 1 hidden; the thin moving wisps disappear. This rules out
the heavy layer as the cause of the fringe. The diagnostic is not promotable.

`blend-cloud-mip-audit-31.json` and `skydome-mip-audit-31.json` independently
verify all ten native mips of each background texture against source compressed
blocks: all match. Source previews retain visible compression/color banding
at dark cloud edges; this alone does not establish the in-game root cause.
`sky-constants-31.json` records source/native named constant comparisons.
A separate private diagnostic hides only cloud-blend mesh 5 to narrow the
remaining layer; production candidate 31 retains every sky layer.


The cloud-blend isolation run `.local/loading-traces/20261029-013235-584`
completed its 180-second watchdog. Its requested 145000-ms upward frame was
inspected: the left cloud shape and its blocky fringe disappear when mesh 5
is hidden, while the other clouds/wisps remain. The fringe is associated with
cloud_blend; removing it is diagnostic only, not an acceptable production fix.

The previous dimension audit omitted material 4, thunderhead. A complete
check found its BC1 texture reduced from authored 1024x512/11 mips to
512x256/10 mips by the general converter cap. The importer now preserves
1024x512 under an exact Powerhouse source/name/shape guard. This is separate
from the cloud_blend fringe. Candidate 32 is building with that correction;
no installed map has changed. The initial attempt to validate candidate 31
thunderhead with source dimensions failed because native dimensions differed;
it is not evidence of corrupted mip data.

Candidate 32 built successfully. `thunderhead-bitmap-dimensions-32.json`
confirms 1024x512 and all 11 authored mips. Independent pinned TagTool decoding
compares all 11 native compressed mip hashes exactly with source in
`thunderhead-mip-audit-32.json`. `geometry-integration-audit-32.json` confirms
all 1,951 vertex buffers and 453 index buffers remain bit-exact versus 31;
the five native waterfall aliases remain intact. Candidate 32 has not yet
received a native visual test or been installed. Cloud-blend fringe and final
lighting acceptance remain open; the Powerhouse goal remains active.


### Candidate 32 native views and cloud intensity diagnostic

Run `.local/loading-traces/20261029-013741-41832` completed its 210-second
watchdog. All three captures (120000,145000,161137 ms) were inspected
individually. Courtyard water/building materials remain visible; cloud wisps
change across the upward views. Restoring thunderhead resolution does not
remove the distinct cloud_blend fringe. `native-sky-evidence-32.json` records
this limited result.

`sky-sampling-curves-32.json` shows cloud_blend remains linear (curve 3),
skydome remains sRGB (curve 1), and their default detail remains sRGB in both
source and native material. These bindings do not explain a conversion-only
gamma mismatch. A private `payload-cloud-quarter-32` changes only the
cloud_blend intensity from 1 to 0.25; its native comparison is pending. All
geometry, animation and map ambient settings remain unchanged.

`wire-composition-feasibility-32.json` evaluates all ten source detail mips
for the two remaining wire-tech materials. Combining their identically
transformed detail RGB as 4.59479*d1*d2 has no clipping (maximum 0.22460);
alpha must also be multiplied, not discarded. The base-level midpoint
bilinear-product discrepancy is at most 0.008064 and mean 0.000157 for the
three tested offsets; this is a measured approximation, not exact filtering
or a global bound. No production wire adapter is installed yet.


### Wire materials and accepted local cloud brightness correction

The quarter-intensity diagnostic completed its 180-second watchdog in
`.local/loading-traces/20261029-014129-2704`. Its 145000-ms capture was
inspected individually. The cloud shape and wisps remain; the formerly
prominent colored block fringe is substantially less visible. The scoped
cloud_blend intensity gain of 0.25 is now implemented as a Powerhouse lighting
correction, retaining source geometry/mips/animations and other sky layers.
This is an intentional brightness adjustment, not a claim that source BC1
compression artifacts have been eliminated at every view.

Candidate 33 builds both wire-tech materials with the stock Deadlock native
shader `_0_2_0_1_1_2_5_0_1_0`. `powerhouse_wire.py` combines their static,
identically sampled detail maps with product alpha and all ten mips. Native
parallax, bump/specular/environment behavior and animated emission remain.
`wire-integration-audit-33.json` verifies actual BSP references, all retained
constant values, samplers and eight source functions. Maximum linear RGB is
0.224595; maximum sRGB-byte quantization error is 0.001719.

The feasibility audit initially matched residential textures with identical
leaf names. It now uses exact Powerhouse paths and was rerun; the corrected
numbers above agree with the actual material-bound adapter. No production
material used the mistaken feasibility lookup.

Candidate 34 combines the wire adapter and cloud correction, deduplicating
the composed detail resource by content. Its build/audit is pending. No
installed map has changed. Wire materials still require native visual review.

Candidate 34 built successfully. `wire-integration-audit-34.json` confirms
the two actual BSP-bound materials retain all supported constants/samplers
and eight authored functions. `wire-mip-audit-34.json` independently decodes
all ten native ARGB mip levels with pinned TagTool: every hash matches the
composed source pixels; both materials share one bitmap and use unit albedo
tint. `sky-constants-34.json` verifies the emitted cloud intensity is 0.25.
`geometry-integration-audit-34.json` confirms all 1,951 vertex and 453 index
buffers remain bit-exact versus 32, with five stock waterfall aliases intact.
The full candidate is staged in `payload-34`; `payload-water-34` is private
spawn-relocated inspection data. Combined native review, especially the wire
surfaces, remains pending. No installed map has been replaced.


### Candidate 34 native review and candidate 35 distant waterfall

Sky run `.local/loading-traces/20261029-014848-31640` completed with 11 passed
and zero failed hashes. All captures (120000,145000,161137 ms) were inspected:
courtyard water/materials remain visible, cloud wisps change, and the cloud
fringe is reduced in the integrated build. Dust motion remains unverified.

Wire run `.local/loading-traces/20261029-015247-25456` also completed with
11 passed/zero failed hashes. Both captures (120000,137137 ms) were inspected.
The floor wire material shows cyan emission changing over time; the emission
ROI has maximum RGB change 140 versus 3 in the floor control region. This
does not establish all parallax behavior or the second wire variant.

The machinery-room floor/machinery remain too dark. The current ambient
profile is not final lighting acceptance. `wire-lighting-audit-34.json`
resolves instance 343 to per-vertex block 342/buffer 978: 1,224 vertices,
nonzero C0 throughout, minimum roughly 0.0003-0.0004 and mean RGB
(0.1251,0.1004,0.0660) after the q8 adjustment. This is not a missing-light
buffer. The three nearby v2 wire instances use atlas 0 instead, so a future
local correction must account for both lighting routes.

`fallback-active-parts-34.json` finds render-part references for all 48
remaining generic materials; owner placement still needs separate assessment.
`remaining-water-geometry-bounds.json` locates distant river/falls surfaces.
The valley waterfall has 81 parts/288 indices spanning z -7.91 to -0.16;
it is a falling-water sheet, distinct from the horizontal splash material.
Candidate 35 now reuses the shipping Valhalla waterfall for this sixth
falling-water material. Actual BSP bindings in `distant-waterfall-binding-35.json`
resolve to the same native datum, alpha blend 3 and three native animations.
`geometry-integration-audit-35.json` proves all vertex/index buffers remain
bit-exact versus 34. Candidate 35 is staged in `payload-35`, but the distant
waterfall still needs native visual review. No installed map was replaced.


### Machinery-room ambient-fill experiment - candidate 37

`powerhouse_room_lighting.py` adds a source-guarded, opt-in C0 fill inside
world box (119,223.5,40.5)..(129.5,230,47), fading with smoothstep over one
metre at every boundary. It resolves source mesh compression, instance
transforms and lighting bindings; shared buffers with differing weights fail
instead of affecting unrelated instances. Empty clusters have no vertices and
are handled explicitly (the first experimental build 36 stopped on that case).
No exposure, geometry, directional coefficients or atlas samples change.

Build with `-RoomFill 0.25` produced candidate 37; default remains zero.
Three focused tests pass for spatial confinement, C0-only updates, decoded
fill values, zero-fill identity and invalid settings. `room-fill-byte-audit-37.json`
compares actual candidate 35/37 geometry resources: 139 lighting buffers and
109,310 vertices change only four C0 bytes; 2,265 other buffers are bit-exact.
The selected spatial bindings contain 111,848 vertices before quantization.
`room-fill-bindings-37.json` explicitly lists atlas-bound owners not adjusted.

Native run `.local/loading-traces/20261029-020545-18976` completed with 11
passed/zero failed hashes. Both 120000/137137-ms captures were inspected
individually at the same authored spawn/view as candidate 34. Machinery and
wall details improve, but the main floor remains too dark. This is not final
lighting acceptance and is not enabled by default. The staged experimental
payloads are `payload-37` and private spawn-relocated `payload-wire-37`.
The default working candidate remains 35; no installed map was replaced.

Next lighting work must cover atlas-bound surfaces. Pinned primary reference
`lightmap_sampling.fx` (HaloShaderGenerator revision
5af3671c919e93b802dd6aa0899f6725de70992c) was saved under work/powerhouse.
Its C0 decode is (rgb0+rgb1)*2-2, multiplied by alpha0*alpha1*C0_range;
C0 occupies array slices 0/1, with other directional coefficients in slices
2..7. Source URL:
https://raw.githubusercontent.com/Beatthezombie/HaloShaderGenerator/5af3671c919e93b802dd6aa0899f6725de70992c/halo_online_shaders/lightmap_sampling.fx
`room-atlas-bindings-37.json` resolves selected instance texture-coordinate
blocks to format-4/stride-4 buffers. Pinned native VertexStreamXbox.cs reads
these as UShort2N. Do not treat per-vertex fill as covering these atlas owners
or assume object light probes received this adjustment.


## 2026-10-29: experimental atlas room fill (candidate 40)

Lighting remains OPEN. Candidate 40 adds spatial ambient C0 fill to atlas
surfaces as well as candidate 37's per-vertex fill. Default RoomFill stays 0;
working default remains candidate 35. No installed map replaced.

The native shader equation is used to encode paired C0 slices. Full-range
replacement candidate 38 was rejected for compression error; candidate 39
also failed the fixed error gate. Candidate 40 restricts fill to dark interior
blocks, tapers by original brightness, and preserves 49 inaccurate blocks
verbatim instead of increasing error tolerances. It changes 1,414 blocks per
ambient slice (22,624 texels). Maximum decoded C0 error is 0.099582 and mean
masked error 0.014513. This is an approximation, not recovered source light.

Both atlas tests and all three vertex-lighting tests pass. Actual native-map
byte audits preserve all six directional atlas slices and the dominant texture.
Vertex audit confirms only ambient C0 bytes change in 139 buffers / 109,310
vertices; 2,265 other vertex/index buffers remain exact. Evidence:
work/powerhouse/room-atlas-byte-audit-40.json and room-fill-byte-audit-40.json.

Native run .local/loading-traces/20261029-022512-24224 completed its bounded
180-second run. Individually inspected both 120000 and 137137 ms captures.
Concrete floor on the right and rear wall have clearer detail than candidate
37, but overall interior remains dark. Localized atlas fill is NOT accepted
as a complete lighting fix. Object probes are still authored, and broader
interior/exterior consistency is unverified. Evidence is recorded in
work/powerhouse/native-room-fill-evidence-40.json. Private spawn-relocated
payload-wire-40 must never be installed as the normal map.


## 2026-10-29: camera exposure diagnostics 41/42

The previous turn made progress with atlas C0 fill, but candidate 40 still
left the room too dark. To separate camera exposure from lighting, private
candidate 41 changes only the imported Powerhouse cfxs upper bound 2 -> 4.
Candidate 42 additionally increases its auto brightness target by 1.5 stops.
Both derive from default candidate 35, without experimental room fill.
The source camera has flags 20, range 0..2, target -2.7369656563; native
Cyberdyne uses 0.5..2.5 and native Zanzibar 0..3. Source/converted scenario
and BSP Camera FX palettes are empty, so no cluster overrides were found.

Native bounded runs 20261029-023001-28520 (41) and
20261029-023319-8176 (42) finished. Both captures at 120000 and 137137 ms
were individually inspected for each run: the same room remains dark,
without a useful visible improvement. Neither exposure change is accepted
or added to the production profile. Actual map byte audits isolate the
changed camera fields; all remaining metadata/resources are unchanged.
Scenario camera binding evidence is camera-reference-audit-42.json.

This does not prove the runtime camera values are effective. Trace the
runtime camera/exposure path before further camera tuning; do not infer
that a correctly stored field is applied in the rendered frame. Installed
map and production defaults remain unchanged. Full conversion stays open.


## 2026-10-29: native exposure selection and resolve-readback diagnosis

Private read-only debugger probes identify the native camera chain:
8217AD80 reads scenario+0x6bc; 8217AEC0 selects per-view, cluster, scenario,
then global-default settings based on each parameter's use-default flag.
8217B530 updates exposure. Its auto path reads a half-float brightness value
through 8217B790 (texture CPU lock), decoded by 8217B980.

Bounded native runs 20261029-024330-19096 and 20261029-024720-2580 each
captured four updates, first at 140s then at 165s respectively. Both select
the actual scenario cfxs at 0xbe2ad100, flags20, target -1.2369656563,
range0..4. Every sampled current exposure remains0. The late run is after
settling, not just startup. Each run's requested native capture was inspected:
room remains dark. Evidence: runtime-exposure-probe-42.json.

Runtime readback_resolve defaults to none. D3D12 IssueCopy then resolves to
GPU/shared resources without CPU readback. This is a concrete candidate cause
for missing auto-exposure feedback; enabling readback is diagnostic until
native evidence confirms it. No engine default or production map changed.

Confinement incident: the first copied probe inherited __file__.parents[4]
and created C:/X360/ISOs/H3M/.local/loading-traces/20261029-024138-8656,
outside this repository. Its child was stopped; that run is excluded from
evidence. The copy and its generator now pin this repository explicitly, and
subsequent actual command lines confirm all output roots are within it.
Permission to remove only the accidental folder was requested and remains
pending; do not delete it without the user's explicit answer.


### Confirmed: CPU resolve readback restores auto-exposure

Native same-map/same-executable comparison now confirms a major runtime cause
of the poor-lighting result. Run 20261029-024720-2580 used readback disabled;
all four settled samples at165s had current exposure0. Run
20261029-025032-2184 changed only runtime readback_resolve=fast, using the
same payload-wire-42 and viewpoint. Its four settled samples exceed3.9stops
(last3.9818227291), while selecting the same map cfxs values. The requested
137137ms native capture was inspected individually: concrete floor, walls,
machinery and metal grating are now clearly readable. This confirms that
missing render-texture CPU feedback suppressed native auto-exposure in this
case; it does not establish that all remaining lighting defects are solved.

Evidence: work/powerhouse/resolve-readback-exposure-evidence-42.json.
No engine defaults or installed maps changed. Candidate42 still has diagnostic
camera cap4/target+1.5 and ambientq8, so this is not a final lighting profile.
Next: test original camera values with readback working, reassess whether
ambientq8 is still needed, and implement an efficient readback policy for the
actual exposure texture rather than enabling every expensive readback blindly.
Inspect interior/exterior transition and highlight retention with the corrected
runtime before accepting a map profile. Console lighting must not inherit PC
compensation for missing readback. Local room-fill experiments stay off.


## 2026-10-29: integrated small-readback runtime and authored-lighting profile

The SDK now supports d3d12_readback_resolve_max_bytes (0 unrestricted). GPU
resolves always execute; only optional CPU feedback beyond the size cap is
skipped. Delayed CPU reads check the recorded GPU submission completion and
written size. Missing/in-flight previous buffers fall back to a completed
synchronized copy. Halo3mpApp enables legacy D3D12 fast readback with an8192
byte cap only when shared/legacy modes are default; explicit settings remain
in control. No Vulkan default changed. Incremental patch is preserved at
halo3mp/patches/rexglue-sdk-small-resolve-readback.patch; reverse-check with
--ignore-space-change succeeds against the working SDK. Both GPU/app builds
pass. Exact current binary/patch hashes are in readback-runtime/final-manifest.json.

Native cap8192 runs with original camera (candidate35 q8 and candidate43 q0)
both reach1.98stops. Captures individually inspected: q0 remains too dark at
its authored2-stop ceiling. small-readback-original-camera-evidence.json records
all four samples and native hash results for each. The q8 compensation is no
longer the build default. Per-map camera conversion now raises only Powerhouse's
maximum2->4; minimum, target, speed and other camera bytes are retained, with
source-layout guards. Generic maps are unaffected. RoomFill remains0.

Candidate44 (q0, camera cap4) tested the compiled application defaults without
readback CLI flags. Its interior is readable and reaches3.98stops. Candidate45
is the full converter output of this profile and is BYTE IDENTICAL to44:
profile-build-equivalence-45.json. This validates the production conversion
against the native-tested diagnostic map, not just its report.

Final guarded GPU runtime was then tested outdoors with45 in
.local/loading-traces/20261029-031037-20104. Both120000 and137137ms native
captures individually inspected. Courtyard buildings/materials remain visible;
the upward sky view retains moving-cloud detail. Exposure at165s is about
0.06stops, proving adaptation downward with the sky view. Bright sky/water
highlights in the courtyard view still clip: do NOT mark overall lighting
accepted. Current evidence: default-readback-evidence-45.json. A changing
viewpoint proves exposure responsiveness, not a full indoor/outdoor traversal.

Full default candidate is45/payload-45; private payload-water-45 must never
be installed. Original map, installed runtime and variants are unchanged.
Remaining lighting work is outdoor highlight balance and interior/exterior
consistency with functional native feedback. Other conversion requirements
remain open. The prior accidental external probe directory is still untouched
pending the user's explicit cleanup permission.


## 2026-10-29: selected bright-area sensitivity, candidate 48

Candidate46 changed only bloom threshold0->1.5 (stock Valhalla comparison).
Both native courtyard/sky captures were individually inspected; no useful
highlight improvement. This experiment is rejected. Authored bloom remains.
Candidate47 changes only bright-area sensitivity0.3->1 relative to45.
Byte audit isolates each diagnostic field and preserves every other metadata
and resource byte: highlight-diagnostic-byte-audit.json.

Native47 courtyard/sky run20261029-032136-30384 shows clearer distant mountain
detail and less over-bright water than45. Bright sky regions still clip; this
is not a claim of universal highlight recovery. Interior run
20261029-032527-41564 retains readable floor/machinery and settles at3.98stops;
the sky-view run settles near0.052stops. Every requested capture was inspected
individually, and both native runs finish with11 hash passes/0 failures.
Evidence: sensitivity-profile-evidence-47.json. Source bloom and ambient stay
authored; no emission or material constants were adjusted in this profile.

The converter now applies the sensitivity adjustment with source guards,
in addition to ceiling4. Three camera tests pass: only the two selected
fields change, both map and tag identity are required, and unexpected/nonfinite
source sensitivity rejects. Full build48 is byte-identical to native-tested
candidate47 (profile-build-equivalence-48.json). Full normal payload48 is
staged; private payload-water-48 must never be installed. No installed map or
runtime replaced and no push performed. The global goal remains incomplete;
remaining material/effect/audio/gameplay requirements retain their scope.

This is the current selected exposure profile, not completion of the entire
Powerhouse conversion or proof of all-map/console/System Link behavior.
The external accidental probe directory remains untouched pending permission.

## Candidate49: native computer-screen emission

Build49 retains candidate48's selected exposure profile (authored ambient and
bloom, ceiling4, bright sensitivity1). The vet_computer_screen now uses stock
Cold Storage's _0_1_0_1_2_2_5_0_0_0 shader. Its added diffuse-alpha specular
mask is inert because source specular_coefficient is zero; guards reject a
changed source permutation, nonzero coefficient or animation of that coefficient.
All five named textures and all named constants are retained; the source LCD
animation function is endian-exact and strict native route remapping succeeds.
Evidence: screen-integration-audit-49.json and geometry-integration-audit-49.json.
All1951 BSP vertex buffers and453 index buffers are byte-identical to48.
Three camera regression tests still pass. Remaining fallback inventory is46.

Native run20261029-034350-11052 uses authored spawn82 with diagnostic facing;
both120000/137137ms captures were inspected individually. The control room
is readable and the laptop display visibly emits light. Its small projected
size does not prove subtle LCD motion; visual animation confirmation remains
open. Native resource checks:11 passes/0 failures. The first diagnostic spawn
(run20261029-033942-4232) fell below the platform and is rejected as screen
evidence. See screen-native-evidence-49.json. Normal payload49 is staged;
private payload-screen-49 and payload-screen-b-49 must never be installed.

Whiteboard remains unresolved: its height_scale is animated, so its static
zero value does not authorize dropping distortion. Other material fallbacks,
bright sky clipping and remaining conversion work remain open. No map/runtime
installed or pushed. The Powerhouse goal remains active and incomplete.

## Candidate50: experimental stock splash foam (NOT ACCEPTED)

The distant valley splash has a stock Assembly water-edge candidate. Original
descent.map sky mesh2/part1 uses126 indices of this native additive material.
Its three custom bitmap payloads (base/detail/overlay) are byte-exact across
all mips, with local descent.map resource pages; default_detail is already
stock. Both native animation payloads are exact. Generated BSP has two bound
material references. All1951 vertex and453 index buffers match candidate49.
See native-water-edges-audit-49.json, splash-integration-audit-50.json and
geometry-integration-audit-50.json. Target Zanzibar island_water_edges was
also checked: it is a static rmhg coastline edge with zero animations, rather
than scrolling foam. Remaining generic fallback inventory is45 in build50.

The first native run20261029-035134-29808 was ledge-obstructed; both requested
captures were inspected and rejected as splash evidence. Forge overview run
20261029-035550-21680 reaches an aerial view of the waterfall. Both137137 and
149137ms captures were inspected sequentially. Yellow-green highlights overlap
the foam and bright terrain still clips; donor appearance versus native flare
and exposure contribution needs separation. Do not claim visual acceptance or
resolved splash animation from these frames. Both runs pass11 native resource
hashes with0 failures. See splash-native-evidence-50.json.

Normal payload50 and private payload-valley-50 exist; neither is promoted.
Candidate49 remains selected pending this appearance correction. The source
alias is experimental and currently builds50 behavior. No installed map or
runtime changed, no push, goal active. Next: inspect the donor foam's decoded
color or isolate flare in a private diagnostic before retaining/replacing it.

## Candidate51: reject green Assembly foam; restore candidate49

The color ambiguity is resolved by decoding the native base and detail mips
from descent.map. Bitmap106 is constant green RGB(57,77,24); bitmap107 is
green foam/noise (mean RGB64.40,74.67,32.93). Both decoded images were visually
inspected. These are authored donor colors, not merely Powerhouse lens-flare
contamination. Evidence: native-foam-color-audit-50.json and decoded
native-foam-106.png/native-foam-107.png. Candidate50 is REJECTED.

Removed the Assembly splash alias from production conversion and recorded
why it is unsuitable. Full rebuild51 is byte-identical to selected49, SHA256
16617f257a2b4f3e87ed085d8ffbf527233871b20414276628e6d98cc8046232.
See splash-rejection-rebuild-51.json. No repeat native run is needed for those
identical bytes; candidate49's limits still apply. Existing normal payload49
remains the selected staging. The original splash fallback remains unresolved;
do not mark it fixed, and do not resurrect candidate50 merely because it
preserves native resource/animation bytes. Nothing installed or pushed.

## Missing shader toolchain investigation (after candidate51)

The splash's closest native Salvation shader has matching texture inputs and
entry-point structure, but opaque versus additive is not merely post Blend Mode.
Across20 native opaque/additive pairs, compiled pixel program sets differ
(native-blend-program-audit-51.json). Do not change only the blend integer.

Installed Xbox360 SDK fxc2.0.21256.0 works. A small compiler probe and all13
Powerhouse splash entry points now compile to xps_3_0. Pinned shader reference
Beatthezombie/HaloShaderGenerator commit5af3671c919e93b802dd6aa0899f6725de70992c
was fetched into work/powerhouse/shader-toolchain/reference; archive hash is
in source.json. This is Halo Online reference source, not evidence of automatic
Halo3 ABI compatibility. Original reference files remain unmodified.

The wrapper supplies two unused vertex-only parser declarations and explicit
signed-BC5 rg channels. Both vertex declarations optimize out. The xdk_2907
float light-count path compiles; the integer path fails an i16 binding. The
alpha-blend-source macro is albedo_alpha_without_fresnel; no opacity-Fresnel
parameters remain in compiled reflection. PC is not defined. No compiled
program was imported into a map or runtime. See shader-toolchain/status.json
and splash-entrypoint-compilation.json. All13 are compile results ONLY.

Next work must audit persistent constants (including float simple-light count),
vertex-to-pixel inputs and render-target outputs against original H3; extract
XDK microcode/reflection into native pixl metadata; remap named shader and
animation routes; then test the authored splash in the established aerial view.
Selected49/identical51, installed maps and runtime remain unchanged. Goal active.

## Xbox shader interface correction (no new map candidate)

The initial compile source was not H3-compatible: Halo Online's DX9 path
unrolled only8 simple lights and disabled LDR/HDR output gamma branches.
A separate xenos-source copy now restores the dynamic integer-count loop and
both gamma branches; pinned reference files remain unchanged. The patch and
reproduction script are in shader-toolchain/xenos-compatibility.patch and
prepare-xenos-adapter.py. No xdk_2907 float-count workaround remains.
All13 splash entry points recompile successfully with native integer i0,
80 float registers atc18 (16 lights), and gamma switches b14/b15 where used.
The compiled static-per-pixel code contains the required3D atlas fetches.

Built a file-only native XDK disassembly helper using installed VS2010,
d3dx9/d3d9/xgraphics libraries. It does not create a graphics device or send
input. Original H3 shader objects reconstruct as debug bytes plus microcode.
XDK output uses the same0x102a header: debug-size at4, microcode-size at8.
The native General Purpose Registers field equals PsMaxReg+1 in this donor.

Compared all12 Salvation donor pixel programs against the new compiled code.
All common persistent-register assignments/counts match. Ten input layouts
match exactly; albedo consumes an extra TEXCOORD1.w, and static_per_vertex
uses wider TEXCOORD0/COLOR0 while dropping COLOR1. Do not assume the old
vertex programs supply these components: verify exports or provide compatible
vertex programs before integration. See native-interface-audit.json and
native-salvation-reflection.json. Compilation and interface evidence are
not runtime acceptance. No generated shader has been put into a map yet.

Integration design: clone the donor pixl/rmt2 rather than mutate shared tags;
map compiler reflection names to material constants/textures and native extern
indices per entry; append the source bump_detail_coefficient constant; preserve
source sampler/animation routes via the existing strict remapper. Retain
source additive mode and all authored splash texture/function data. Selected
candidate49/identical51 remains unchanged, with the splash fallback unresolved.

## Candidate52: original splash textures on compiled Xenos shaders (experimental)

Audited Salvation shared vertex exports: original H3 does not export the extra
components consumed by the Halo Online shader source. The Xenos adapter restores
float3 albedo normal and native per-vertex fog COLOR0/1; all12 pixel interfaces
now match. A complete named-route audit also found and corrected the additive
albedo switch (b0, from native Descent reflection) and active-camo factor(c232).
All13 compiler entry points pass;12 material programs are integrated, with
native shared shadow-generation retained. No unresolved parameter bindings.

The experimental adapter clones pixl/rmt2, rebuilds material and extern routes
from compiler reflection, and appends bump_detail_coefficient. Source additive
blend, all6 texture slots, all named constants, and5 endian-exact animation
functions are retained. All12 integrated Xenos shader objects hash exactly to
the compiler manifest. All1951 vertex and453 index buffers match49 unchanged.
Evidence: compiled-splash-integration-audit-52.json, geometry-integration-audit-52.json,
shader-toolchain/native-interface-audit.json, native-vertex-exports.json, and
splash-route-plan.json. POWERHOUSE_SPLASH_SHADER_DIR is not a player setting:
the exact experimental build variable is OPENH3M_POWERHOUSE_SPLASH_SHADER_DIR.
Normal builds keep49/51 behavior without that variable. Native capture acceptance
and compiler packaging remain pending; no promotion/install/push. Goal active.

Candidate52 native runs20261029-044156-32712 and20261029-044557-7668
each passed11 resource hashes with0 failures. Both captures from each run
were inspected individually. These show the upper river channel and long
waterfall, with strongly clipped terrain highlights. They DO NOT establish
splash appearance/animation: the source splash geometry is around(190,268,-2),
about46 units below the observer; the upper white highlight is not that splash.
This also qualifies the earlier candidate50 aerial-view description. Its
rejection based on decoded green donor textures remains valid independently.
See compiled-splash-native-evidence-52.json. Shader remains opt-in.

Lighting diagnostic prepared: payload-valley-floor-52 changes only the camera
minimum exposure0 -> -2; maximum4 and all other authored settings stay intact.
This checks whether the zero-stop lower bound prevents outdoor adaptation from
reducing clipping, while preserving the existing indoor exposure capacity.
The diagnostic is private and not installed. Native exposure sampling pending.

Outdoor exposure-floor diagnostic completed in native run20261029-044947-38288:
11 resource hashes passed,0 failed. All4 sampled exposure returns are between
-0.61784 and-0.61747 stops. Both137137/149137ms captures were inspected; bright
terrain still clips visibly. The negative range works but is insufficient as
a lighting fix. Do not promote this diagnostic or claim lighting completion.
Production camera remains0..4, selected candidate49/identical51; candidate52
compiled splash remains opt-in and visually unaccepted. All native runs ended
within180 seconds. No installed maps/runtime changed and no push.
See exposure-floor-native-evidence-52.json. Next lighting work must separate
material/lightmap highlight intensity and bloom from adaptive exposure; avoid
repeating only the minimum-bound adjustment. Goal remains active.

## Candidate53: restore the valley cliff material

Four rays through clipped capture regions resolve to source mesh229, instance1274,
m30_river_valley_cliffs. Its generic fallback dropped detail_map2/detail_map3
and bump_detail_map and substituted specular lighting for diffuse-only shading.
Source material model0 is DIFFUSE-ONLY, not unlit (correction to commentary).
The source is _5_2_0_1_0_0_0_0_0_0; native _5_2_0_0_0_0_0_0_0_0 preserves
three-detail blending and diffuse-only lighting. The omitted specular mask has
no specular consumer in this opaque, nonreflective material.

Reuse original Zanzibar template83 and all12 unchanged native pixel programs;
Bunkerworld terrain_africa supplies the matching postprocess prototype. All6
texture slots and authored UV transforms are retained. Source detail strength
1.2000000477 is baked into all11 mips using native signed XY (V8U8). Decoded
source and quantized scaled normals stay within the unit disk, so native normal
reconstruction does not nonlinearly alter XY; convex filtering preserves this.
Maximum component rounding error is0.00382456 (less than0.5/127). Encoded
normal bytes rise from1,398,128 to2,796,202. A BC5 endpoint-scaling attempt
failed the strict decoded error bound and was replaced before building53.

cliff-integration-audit-53.json verifies names/transforms and original Zanzibar
program hashes. geometry-integration-audit-53.json verifies all1951 vertex and
453 index buffers against49. Camera remains0..4 stops, sensitivity1, q0;
no negative-floor diagnostic or experimental52 shader is enabled.

Native run20261029-050318-44600:11 resource hashes pass,0 fail;180-second
watchdog. Both137137/149137ms captures inspected individually. Near cliff
white sheen is removed and rock/talus layers show clear detail; distant upper
highlights still clip. Retain this material correction, but do not claim full
lighting or full-map completion. Normal payload53 is selected for continued
conversion; diagnostic payload-valley-53 must never be installed. No installed
map/runtime changed, no push. Evidence: cliff-native-evidence-53.json.

## Experimental water55 rejected; lighting remains open

Candidate55 retains53 geometry and adds opt-in compiled Xenos programs for
030_water_river_bottom and settlement_river_inlet. Named routes, source
textures, constants, animations and program hashes pass the offline audits,
but native run20261029-052825-36616 shows a solid black upper river in both
145000/153000ms captures. Reject55; keep53 selected. The run has716 invalid
texture-fetch warnings versus zero in the53 baseline; the cause is unresolved.
Eleven passing resource hashes do not establish rendering correctness. See
work/powerhouse/water-native-rejection-55.json. Neither experimental water
shaders nor experimental52 splash shaders are enabled by default.

No-flare diagnostic54 produced no useful reduction of upper clipping. Its
Disabled For Debugging bit was not independently proven effective in retail;
this does not establish that flare brightness was absent. A stronger private
diagnostic56 explicitly zeros reflection brightness and camera bloom/bling
intensities while retaining53 exposure, geometry and materials. It must never
be installed. Production sun flares and authored bloom remain retained.

Diagnostic56 native run20261029-053937-29652 completed180 seconds with11
resource hashes passing and zero failures. Both137137/149137ms captures were
inspected individually: upper cliff highlights remain washed out after explicit
zero bloom/bling and reflection-brightness parameters. Not a lighting fix.
Three upper-pixel ray intersections identify the same diffuse-only cliff
material, source mesh229 instance1274. A fourth ray has no BSP intersection.
Investigate the baked-lighting binding and native diffuse-blend output next;
do not select the stripped-effects diagnostic or declare lighting complete.
Evidence: work/powerhouse/light-isolation-native-evidence-56.json and
work/powerhouse/upper-clipping-location-56.json. Candidate53 remains selected.

## Cliff lighting isolation57

Source and candidate53 instance1274 both bind per-vertex block1128, buffer1764
(format6,1677 vertices), with no atlas/probe binding. All converted lighting
bytes match the source component conversion exactly. Upper and lower sunlit
ray samples have similar dominant/C0 intensities; shadow samples are lower.
Source color mip averages remain stable through the smallest levels, with
linear curve3 on all three color textures. These checks do not establish
final shader-output correctness. Evidence: cliff-lighting-byte-audit-57.json,
cliff-pixel-normal-lighting-57.json and cliff-source-mips-57.json.

Private no-atmosphere57 clears only Enable Atmosphere on the imported skya
setting, retaining53 bloom, flares, materials and exposure. Native run
20261029-054505-37248 completed180 seconds;11 hashes pass,zero fail. Both
137137/149137ms captures inspected individually: upper terrain still clips.
Do not promote this diagnostic or remove the authored atmosphere. Next
isolate fixed outdoor exposure with runtime readback to distinguish output
exposure from upstream saturated material/effect contributions. Lighting
remains open and53 remains selected. No installed files changed or push.

## Fixed exposure58 and compiled sampler correction59

Private58 fixes camera exposure to-2 stops without removing atmosphere, bloom
or flares. Native run20261029-054934-28496 completed180 seconds with11
resource hashes passing,zero failures. Runtime samples read approximately
-1.982 stops. Both137137/149137ms captures inspected individually: upper
terrain regains detail but shadowed surfaces are too dark. Do not select a
fixed global exposure as the lighting fix. Evidence: fixed-exposure-native-
evidence-58.json. Candidate53 remains selected.

Experimental compiled shaders had allowed the compiler to auto-assign common
samplers. Native H3 shader reflection and the pinned DX9 sampler enumeration
reserve albedo10,normal11,lightprobe12,dominant13,sceneLDR10,depth11. The
adapted source now explicitly pins those slots, and the integration module
rejects incompatible compiled reflection. Old52/55 experimental inputs fail
this new guard and must be regenerated before use. The corrected water
programs reside in shader-toolchain-water-fixed59; build59 is experimental,
and no visual success is claimed until native inspection. Retain the rejected
55 artifacts for comparison.

Candidate59 native run20261029-055606-18856 completed180 seconds;11
resource hashes pass,zero fail. Both145000/153000ms captures inspected
individually: the upper river now displays pale yellow-green water and surface
texture instead of55's solid black. Fixed sampler slots correct that visible
failure. However719 invalid texture-fetch warnings remain (55 had716), and
the inlet is not yet visually checked. Keep59 experimental and53 selected;
do not claim full water acceptance. The remaining warning cause was not fixed
by this change and must be traced separately. Source textures/constants and
all10 animation functions remain exact;24 compiled program hashes match,
and geometry remains byte-identical to53. Evidence: water-native-evidence-59,
water-integration-audit-59 and geometry-integration-audit-59 JSON files.
No installed files changed or push.

## Fetch diagnostic60: stock armor program identified

A temporary GPU diagnostic reports only32 invalid-fetch observations; it
changes no draw state. All32 identify pixel texture slot0, pixel hash
54411A1FD7924873, vertex hashC2543FD5CD52420B (60-byte program), with no
vertex texture use. The cached3720-byte pixel microcode matches candidate59
stock pixl7107 program7 at physical-data offset192: native template
_3_2_0_1_1_2_0_0_0_1, used by Spartan/Elite armor. It is not either
converted water shader. Earlier zero-versus-many warning comparisons used
different camera routes and do not establish a water-conversion regression.
An identical-route53 baseline is pending.

Run20261029-060223-43560 completed180 seconds with11 resource hashes passing,
zero failures; both145000/153000ms captures inspected, river remains colored
and textured. Original SDK source and GPU DLL restored; DLL hash remains
a262536b7cdb5923995235df1dc618ed89ebceddbf79af1223327b2ab2bf105f. Diagnostic
source/DLL and evidence remain inside work/powerhouse/fetch-diagnostic-60.
The failed initial full-program hash lookup was resolved by comparing actual
GPU microcode against the subrange within the cached shader physical data.

Matching-route baseline61 uses candidate53, original runtime, yaw2.57 and the
same Forge flight as59. Run20261029-060927-39704 reports752 invalid-fetch
warnings, confirming this warning exists without either compiled water shader.
Eleven resource hashes pass,zero fail. Only145000ms capture completed and was
inspected;153000ms did not arrive before the180-second watchdog, so the
harness exits1 and this is not a complete visual pass. Runtime remained active
until the watchdog; do not describe it as a game crash. Record the existing
stock-armor fetch issue separately from water conversion acceptance.
Evidence: work/powerhouse/water-baseline-evidence-61.json.

User answered the pending external-cleanup question: leave
C:\X360\ISOs\H3M\.local\loading-traces\20261029-024138-8656 untouched.
Do not remove or modify that accidentally created external probe folder.

## Inlet62 and working candidate59 selection

Run20261029-061332-44320 uses candidate59 and a private inlet-facing route.
Both142000/147000ms captures inspected individually; the inlet displays
rippled surface detail and highlight/shadow variation, with adjacent mist
visible. Three capture-pixel rays hit settlement_river_inlet first, establishing
which material is visible. Eleven resource hashes pass,zero fail; harness
completed normally under180 seconds. This is not a whole-map lighting or
all-water/effects sign-off. Evidence: inlet-native-evidence-62.json and
inlet-visible-rays-62.json.

Select normal candidate59/payload59 for remaining conversion work. Both
compiled river materials now have native rendering evidence. This build
requires OPENH3M_POWERHOUSE_WATER_SHADER_DIR pointing to
work/powerhouse/shader-toolchain-water-fixed59. Compiler workflow/default
integration remains unfinished; default builds still use the earlier native
fallback. Private spawn-relocated payloads must not be installed. Lighting,
splash/effects and remaining goal requirements stay open. No install or push.

## Default build63: reproducible corrected river shaders

The normal build now invokes snapshot/tools/build_powerhouse_water_shaders.py
when no experimental water-shader directory is supplied. It verifies386 pinned
HaloShaderGenerator source files, applies the checked-in H3/Xenos compatibility
patch, invokes the installed Xbox360 XDK compiler, and requires all13 generated
GPU microcode payloads to match the reviewed59 programs. Reflection must match
the reviewed routes. Source, recipe and output hashes guard the build cache;
missing/changed inputs fail instead of silently falling back. All outputs and
compiler temporary files stay inside the repository. The wrapper restores
caller environment variables after the map build. No generated binary shaders
are added to the recipe directory.

Candidate63 built with no water environment override. Full map SHA256 is
0627bcd20b3f3a90c7f65ad928cdaf0915878f173b476e0203fa49f811fae366, exactly
the same as59. Source constants/animations, both materials and geometry audits
pass. Select63/payload63 for further work; no repeat native run is needed for
a byte-identical map. Compiler input/recipe documentation is in
snapshot/reference/powerhouse-water-shaders/README.md. Evidence:
work/powerhouse/default-build-evidence-63.json. Lighting and the remaining
conversion requirements are still open; no install or push.

Experimental64 additionally rebuilds the waterfall splash shader with the
fixed native sampler slots. All12 interfaces match with zero fixed-register
mismatches/unresolved bindings; integration retains six source texture slots,
all named constants and five animation functions. Its geometry is unchanged
from63. Native spray-base capture is pending;64 is not selected.

Splash64 native run20261029-062808-42968 completed180 seconds with11
resource hashes passing,zero failures. Both142000/147000ms captures
inspected individually. Pixel801,282 is a small bright spray patch beside
the waterfall base; its ray hits settlement_river_valley_waterfall_splash_a
first, ahead of the river and terrain. Other white strips nearer the rocks
are waterfall/inlet surfaces and must not be counted as spray evidence.
The small patch establishes rendering, not close-up appearance or visible
animation. Keep64 experimental pending a closer view. A longer eastward
Forge flight from this diagnostic spawn can reduce the viewing distance;
retain the180-second watchdog and schedule captures before it. Evidence:
splash-native-evidence-64.json and splash-visible-rays-64.json.
Candidate63 remains selected, with corrected river shaders in the default
build. No install or push; lighting and the full goal remain open.

Closer spray probe65 (candidate64), run20261029-063757-8792,
completed180 seconds, exit0,11 resource hashes passed. Both147000/149000ms
captures inspected individually: Spartan weapon and original spawn view,
not the requested Forge flight. Native replay logged every movement frame,
but observer remained at152.415,253.396,37.220. Cause unresolved.
The intended spray point projects outside the frame at823,1299; no spray
appearance/animation acceptance follows from this run. Evidence is
work/powerhouse/splash-native-evidence-65.json. Next use a verified private
diagnostic spawn near the spray or resolve replay consumption before another
flight; do not repeat the unchanged route. Candidate63 remains selected;
no install/push. Full conversion and lighting remain open.

Correction to probe65, established by probe66 and full trajectory review:
replay input DID move the camera in both runs. The final-position-only
diagnosis above was wrong. Both longer flights reached about164.5,264.2,35.5
then returned to spawn. Run66 first capture147000ms shows the death/respawn
countdown;149000ms shows the respawn. An out-of-bounds/kill-volume trigger
is likely but exact trigger is untraced. Do not change replay or gameplay
boundaries based on this probe. Inspect from inside the playable area using
a safe elevated angle or diagnostic field of view. Run20261029-064446-23112
completed with11 hash passes,zero failures; both captures individually
inspected, no splash acceptance. Corrected evidence65 and evidence66 are
in work/powerhouse. Candidate63 remains selected; goal remains open.

Boundary audit67 resolves the failed long spray flights: all8 trigger
volumes and their transforms/extents/kill indices match source exactly.
Kill assignments[0,3,4,5,6,7], safe assignment[1] also match. Safe-volume1
lower face isZ34.502101898; run66 descended toZ34.410186767 before death.
Retain these authored boundaries. Evidence:trigger-volume-audit-67.json.
Short route67 survives at162.7048,262.9532,37.1254; both142000/147000ms
captures inspected. Its diagnostic matg FOV scale0.3 did not change the
observed1.22173047-radian FOV. Left-turn test increased yaw; spray projected
outside frame. No spray acceptance. Probe68 instead changes only private
monitor_editor biped FOV to0.35 and uses measured right-turn direction.
Production FOV and candidate63 remain unchanged. No install/push.

Spray probe68 succeeds: private monitor_editor FOV0.35, normal authored
boundaries, short surviving route. Run20261029-065401-28120 completed
180seconds/exit0 with11 resource hash passes,zero failures. Both142000
and147000ms captures individually inspected. Bright textured spray plume
at510..570,94..140 visibly changes between frames with fixed camera/rocks.
Four rays hit settlement_river_valley_waterfall_splash_a first;450,210
hits waterfall_a and is excluded. This verifies the visible spray patch
and animation, not overall lighting or every viewing angle. Evidence:
splash-native-evidence-68.json and splash-visible-rays-68.json.
Select normal candidate64/payload64 for continued conversion work. Never
install diagnostic zoom/spawn payloads. Default build still produces63;
next integrate the reviewed compiled splash into the reproducible workflow.
Lighting, other effects and the full goal remain open. No install/push.

## Default build69: reproducible river and splash shaders

The normal build now prepares both shader families. Shared pinned source
hashes and H3/Xenos compatibility patch feed separate reviewed recipes;
splash deliberately omits the water-only H3_MATERIAL_TEXTURE_FLOAT define.
The builder verifies13 GPU program hashes and reviewed parameter bindings
for each family. Builder/source/recipe/output hashes protect the cache.
Explicit experimental directories remain supported, and the PowerShell
wrapper restores both caller variables and TEMP/TMP.
Candidate69 SHA256 d79a501a7e9ed85e1a1942743d511ca5d607886988361fae38052f40b15f0969
is byte-identical to native-tested64. Geometry audit confirms1951 vertex
buffers and453 index buffers unchanged. Splash retains all named constants,
six texture slots,five animation functions,twelve integrated pixel programs
and additive blending. No new native run is required for identical bytes.
Select normal69/payload69 for continued work; private zoom/spawn payloads
remain diagnostic only. Evidence:default-build-evidence-69.json,
compiled-splash-integration-audit-69.json,geometry-integration-audit-69.json.
Recipe documentation:snapshot/reference/powerhouse-splash-shaders/README.md.
Lighting,other effects,audio and remaining collision/gameplay/Forge work
remain open under the full goal. No installed map changed; no push.

Lighting diagnostic70 tests indirect C0x2 with exposure target/bounds
shifted-1 stop (range-1..3). This tests balancing indirect versus directional
light instead of global exposure alone. All913331 per-vertex samples across
1315 buffers match exact C0 exponent+4;636 other vertex buffers are unchanged.
Native run20261029-070559-6260 completed180seconds,exit0,11 hash passes,zero
failures. Both137137/149137ms captures individually inspected and compared
with53 valley capture. Measured exposure-0.981943..-0.981992. Shaded rock
texture remains visible and brightness decreases, but upper highlights
remain washed out. Not accepted as a lighting fix; default candidate69
remains selected. Evidence:light-balance-audit-70.json and
light-balance-native-evidence-70.json. Diagnostic payload must not be
installed. Further lighting correction and full conversion remain open.

Shader audit71 reads actual source DXBC and stock Xenos bytecode for the
cliff albedo/per-vertex passes. Source compiled records have144-byte stride;
albedo index0 and per-vertex index3 were disassembled with installed tools.
Both albedo shaders implement u=saturate(2a),v=saturate(2a-1),
d=lerp(lerp(d1,d2,u),d3,v),rgb=4.59479*base.rgb*d.rgb. Source also has
debug_tint and conditional p_shader_pc_albedo_lighting; their runtime values
are unverified, so do not treat those branches as authored extra lighting.
Per-vertex shaders share SH constants and final exposure/clamp/gamma
operations. Native normal-length/dominant-light handling still differs;
full numerical equivalence is not established. No demonstrated multiplier
mismatch and no lighting fix selected from this audit. Next investigation
should measure actual normal/lighting and render-target values, rather than
infer correctness from matching template names. Evidence:
cliff-shader-comparison-71.json,cliff-shader-audit-71/*.asm.
Candidate69 unchanged; lighting and full conversion remain open.

Normal attenuation audit72: the native dominant-light factor is
(dot(n,n))^8=length(n)^16. Pinned entry_points.fx explicitly describes
this as attenuation for MSAA normals averaged across polygons, guarded
#ifndef pc. The actual Xenos bytecode has the matching repeated powers.
For unit normals and convex sample averages, length<=1 and factor<=1;
it cannot brighten ideal-domain pixels. Keep this stock behavior.
A nearest8-bit UNORM encode/decode assumption bounds vector error by
sqrt(3)/255 and factor by(1+sqrt(3)/255)^16; this is conditional, not
proof of the actual runtime format/values. Runtime normal/lighting-buffer
values and output conversion remain unmeasured. Evidence:
normal-attenuation-audit-72.json. No shader or runtime patch made;
candidate69 unchanged, lighting/full conversion still open.

Native register probe73 (candidate69) completed180seconds/exit0,11 hash
passes,zero failures. Exact albedo/lighting shader hashes were matched
against runtime cache before bounded read-only instrumentation. Albedo
RT0 is gamma8888,RT1 unsigned2_10_10_10; lighting fetch10 gammaRGB
format50 and fetch11 unsigned format7 agree. Lighting LDR gamma2 is off,
HDR gamma2 on,c0.y=128. Normal quantization is10bit, narrowing the prior
conditional unit-normal rounding bound to(1+sqrt(3)/1023)^16.
Both137137/149137ms captures inspected individually; upper highlights
still wash out. Register-format agreement is not pixel correctness; actual
intermediate pixel values remain unmeasured. Evidence and raw records:
work/powerhouse/lighting-diagnostic-73/evidence.json. Original renderer
source and DLL restored byte-for-byte; DLL SHA a262536b7cdb5923995235df1dc618ed89ebceddbf79af1223327b2ab2bf105f.
No production change or install/push; candidate69/full goal remain open.

Pixel readback74 captures1152x640 normal/color resolves with bounded
CPU feedback for addresses044B0000/04780000,frames4000..4500 only. Native
run20261029-072608-44568 completed180seconds,exit0,11 hash passes,zero
failures. Both137137/149137ms captures individually inspected. Normal
fetch binding confirmed at04780000,format7,8-in-32,unsigned identityRGB.
Six tiled10bit decoded probes have near-unit normals; dominant multiplier
range0.993794..1.018137. This term does not produce a large brightness
increase at those probes. Color address044B0000 is reused by multiple
resolves per frame,so its saved bytes are NOT yet verified pre-lighting
albedo. Next gate readback by albedo render-target state as well as address.
Evidence:work/powerhouse/pixel-diagnostic-74/evidence.json and
normal-probes.json. Original renderer source/DLL restored exactly; no
production map change. Candidate69 and full goal remain open.

Pixel readback correction and run76: both resolve addresses are reused.
The normal conclusion from74 is provisional;75 missed color entirely and
captured later color into the normal address, so75 cannot diagnose lighting.
Run76 gates both addresses on RT1 copy format10,frames4000..4500.
Both native captures inspected individually; upper terrain still washed out.
Six selected-pass albedo probes are unsaturated; normal attenuation factors
0.981755..1.020998 do not explain a large brightness gain at these probes.
This is not a synchronized full-frame lighting reconstruction or a fix.
Original renderer source/DLL restored exactly. Candidate69 unchanged.
Evidence:work/powerhouse/pixel-diagnostic-76/evidence.json.
User instructed leaving external accidental20261029-024138-8656 folder
untouched; no cleanup performed. Full conversion and lighting remain open.

Lighting audit77: six conditional offline SH/albedo calculations predict
unclipped pre-atmosphere values,maximum channel0.4463. Source/native
normal attenuation differences are small at those samples. This calculation
is NOT synchronized end-to-end evidence; exposure is from73 and fog/post
are excluded. Reproducible calculate-lighting-equations-77.py and
compare-cliff-lighting-77.py saved under work/powerhouse.
Stock shared world/rigid vertex programs extracted and disassembled;
candidate69 copies match exactly. Decoding uses exp2(alpha*31.75).
Runtime78 completed180seconds/exit0; both native captures inspected,
upper highlights remain washed out. Lighting vertex hash F66F20194CD3428E;
fog enabled,max thickness1000. Six atmosphere registers233..238 saved,
but extra atmosphere register15 not captured. Runtime cache match is
partial144bytes, not full program identity proof. Next measure lighting
outputs before postprocessing, with selected-pass identity and full fog
constants; do not retune coefficients based solely on conditional77.
Evidence:work/powerhouse/lighting-diagnostic-78/evidence.json. Original
renderer source/DLL restored exactly. Candidate69 unchanged,goal active.

Runtime fetch audit79 resolves the partial-match concern from78: extracted
runtime shader F66F20194CD3428E differs in57 fetch-setup bytes; disassembly
after vertex fetch is identical to stock. Evidence lighting-fetch-audit-79.
Frame80 captures23 separate native resolves,total25,239,552bytes,from
frame4200 with queue completion forced for each copy. Both requested native
captures inspected individually. Albedo resolve2 is unsaturated at allsix
probes. Scene LDR resolve6 already clips upper-cliff red; motion-blur
resolve7 preserves it before bloom. HDR resolve8 remains unsaturated.
Next locate the LDR/HDR divergence among scene draws,including blend/write
state and transparent contributions; final bloom is not the first clipping
stage. No proposed production correction yet. The logged dest/pitch fields
used wrong register addresses and cannot establish formats. Final resolve22
format is unverified; do not claim its rgb10 decoding correct.
Evidence:work/powerhouse/frame-diagnostic-80/evidence.json,resolves.json,
pixel-stages.json. Original renderer source/DLL restored byte-exact.
Candidate69 unchanged; installed maps untouched; full goal remains active.

Frame81 records639draws and23resolves. Opaque cliff379/380 use matching
replacement blending on both outputs. Later transparent draws include
additive effects. Correct copy registers confirm LDR6/7 andHDR8 are8888
with8-in-32 endian and red/blue swap; final22 is2_10_10_10,no endian
swap,and red/blue swap. Corrected final probes saved. Fog-inclusive81
math remains conditional and unsynchronized,not end-to-end proof.
Frame82 TEMPORARILY skips additive transparent scene draws after4000.
Both native captures individually inspected: upper highlights no longer
wash out and cliff detail returns. Matching sampled albedo/normal values
between81/82 support alignment. Upper LDR(300,30) changes255,255,255
to169,117,101. This isolates clipping to additive transparent contributions,
not a proposed permanent omission. Next isolate F7BD75D401A6FEC0 versus
the skipped halogram programs,then correct the responsible effect while
retaining required effects. Prefix-nearest program matches are insufficient
and must not be treated as identity. Full skip counts and evidence saved in
work/powerhouse/frame-diagnostic-82/evidence.json;81evidence adjacent.
Renderer source/DLL restored byte-exact after each run. Candidate69 and
installed maps unchanged. Lighting/full conversion goal still active.

User steering2026-10-29: "Looks fine. Focus on the gameplay area."
Stop pursuing distant sky/valley brightness as the current priority. Preserve
candidate69 visual treatment and focus on playable-area lighting/materials,
traversal/collision,gameplay andForge. This is not broad completion evidence.
Diagnostic83 skipped only F7BD75D401A6FEC0; highlights persist. Bytecode
identity found exactly in pixl9911 compiled1 at128-byte program offset;
previous hardcoded64-byte search missed it. Remaining additive groups map
to the sky model: clouds,horizon,lightning,dust. Diagnostic84 skipped only
the four dust draws; both captures still show bright upper cliffs. Both83
and84 native captures individually inspected. No omission accepted or
installed. Renderer source/DLL restored after84,originalSHA verified.
Prepared private interior69 at authored spawn12 for gameplay-area run85;
only spawn markers/startpoints relocated in private payload. Production
spawn layout preserved. Gameplay-material-backlog-85.json records existing
reported material omissions for prioritization by actual playable views.

Gameplay-area run85 completed180seconds,exit0,11hashpasses/0failures
on unmodified renderer and private interior69 spawn12. Both115137/149137
captures inspected individually. Lit interior ceiling/walls and bright
external doorway visible; stockAR/HUD correct in this view,ammo32to30
confirms firing. Player advances to visible wall; this is not a complete
traversal route. Pre-load observer coordinates were menu/background state;
Powerhouse spawn appears at132.313seconds. No wrong-map conclusion.
Center ray identifies m30_stucco_spackled; all its texture slots retained
according to69report,so close-view blur alone does not prove missingdetail.
Evidence:work/powerhouse/gameplay-interior-evidence-85.json and
interior-material-rays-85.json. Next face leftdoorway and traverse playable
courtyard. No jump/audio/fullcollision or fullconversion completion claim.


### Gameplay doorway test 86

Candidate 69, restored production renderer: inspected all three native captures at 115137, 126137 and 149137 ms individually. The first shows the interior doorway; forward movement reaches the courtyard, then a turn exposes courtyard machinery. Stock AR and HUD remain visible. This verifies only the short doorway crossing, not all collision or gameplay. Evidence: `work/powerhouse/gameplay-doorway-evidence-86.json`. Installed maps remain unchanged.

### Interior concrete detail restoration - candidate 87 pending

The gameplay-area material `m30_concrete_interior` previously fell back to three textures, losing `detail_map2` and `bump_detail_map`. It now selects the stock Armory `concrete_wall_ext` native detail-blend family, retaining all five active texture inputs and authored transforms. Source model is two-lobe Phong, not Blinn-Phong: zero specular coefficient suppresses both specular and environment reflectance, unit diffuse matches diffuse-only, and the white non-inverted detail mask with unit strength reduces to unmasked detail. Source permutation, constants, switches and absence of animations are guarded. Equations, source values, donor identity and reference hashes: `work/powerhouse/concrete-interior-preflight-87.json`. Build and native visual verification remain pending; candidate69 stays selected. This is the OpenH3M adaptation of Reach Powerhouse through GeneralHeed/Priception workshop package3003239190; source attribution remains in MAP-CREDITS.md.

Candidate87 build exited0. Direct generated-cache audit confirms five named bitmap slots and all five transforms matching source, including detail scales20 and10 and authored zero-UV normal transforms. Geometry audit proves1951 vertex and453 index buffers byte-identical to69. Evidence: `concrete-interior-cache-audit-87.json`, `geometry-integration-audit-87.json` in `work/powerhouse`. Native visual verification of87 remains pending;69 remains selected.

Native test87 first attempt failed to reach map within180s: stock runtime spent123931ms creating1421 stored graphics pipelines. No map/material pass claimed. Second attempt uses isolated `work/powerhouse/runtime-cache-87`, seeded with shareable shader bytecode only, to avoid bulk pipeline initialization; process-local controls/captures and production renderer unchanged. Source audit found further native detail-family candidates for garage ceiling and metal transformer: `work/powerhouse/gameplay-material-next-87.json`; not yet implemented.

### Candidate87 focused gameplay result

Second native attempt exited0 with11 native hash passes and0 failures. Individually inspected all three captures:115137ms room view,126137ms downward concrete-floor view,149137ms after walking into the visible wall. Three source-geometry rays identify the visible floor as corrected `m30_concrete_interior` on mesh72/instance364. Movement advances about2.34 world units with stable floor support. Evidence: `work/powerhouse/gameplay-concrete-evidence-87.json` and `concrete-material-rays-87.json`. Candidate87 is the working successor to69 for the concrete detail fix; production spawn placement is unchanged, and the relocated spawn exists only in private test payload. Installed maps remain unchanged. This is a focused material/short-walk pass, not full-map, audio, Forge-save or console/System Link acceptance.

### Candidate89 - garage ceiling and transformer detail layers

Added guarded native Armory shader mappings for `m30_garage_ceiling_settlement` and `m30_metal_transformer`. Garage white non-inverted unit-strength normal mask reduces to unmasked detail; transformer zero two-lobe specular and unit diffuse reduce to diffuse-only. Both retain all five texture inputs and exact authored transforms. Build exited0; `work/powerhouse/detail-cache-audit-89.json` checks actual generated material blocks. `geometry-integration-audit-89.json` confirms1951 vertex/453 index buffers byte-identical to87. Candidate89 SHA256:3e0e3d24ce09f4145577b3a44f0a94f993a19292789ecd3f864216232e7871ed. Candidate88 was an interrupted unchanged-source build after a syntax-edit precheck rejected the edit; it is not a candidate for use.

Transformer source references trace to BSP material64, meshes47/75/270/271; small triangles were initially excluded by the surface locator area threshold. Corrected location evidence: `transformer-reference-89.json`, `transformer-surfaces-89.json`. No model-reference absence claim is used to discard the material. Garage target upper-floor mesh452 is in `detail-surfaces-89.json`. Private relocated-spawn test89 is underway; no visual pass claimed yet. Installed maps unchanged. These remain OpenH3M adaptations of the documented Reach/GeneralHeed-Priception Powerhouse source; MAP-CREDITS.md retains source link and attribution.

Candidate89 native ceiling test exited0: all three captures115137/126137/149137ms inspected individually. Upward capture renders textured garage ceiling with pipes/cables and room lighting; three source-geometry rays identify `m30_garage_ceiling_settlement` as nearest visible surface. Short walk maintains floor support and stops at visible wall. Evidence: `gameplay-ceiling-evidence-89.json`, `ceiling-material-rays-89.json`. Transformer generated-data checks pass; transformer visual check remains open. Candidate89 is the current development candidate, not installed or globally accepted. Full Powerhouse goal remains active.

### Candidate91 - diamondplate detail restoration

Reused Orbital/spacecamp stock `glass_spaceglass_a_opq` shader family `_6_1_0_2_1_2_0_0_0_0` for `m30_diamondplate`, retaining authored base, both detail layers, overlay, bump and material-texture inputs. The donor specular-mask/environment differences are inert under guarded zero specular/environment strengths, disabled material-texture override, and no animations. Build exited0. Direct cache audit verifies all shared named constants and transforms, native use_material_texture=0, and valid bitmap slots: `work/powerhouse/diamondplate-cache-audit-91.json`. Geometry remains byte-identical to89 across1951 vertex/453 index buffers (`geometry-integration-audit-91.json`). SHA256:8b480e9a715fa54862d8291b6f4f64978b07f6393b834fe4368b24b4985629e6. Visual check pending; installed maps unchanged. Source remains the credited Reach Powerhouse/GeneralHeed-Priception workshop3003239190 adaptation documented in MAP-CREDITS.md.

Transformer test90 on candidate89 exited0 and11 native hashes passed, but all three individually inspected captures show a roof overhang instead of the intended equipment. This does NOT establish transformer material appearance. Evidence: `gameplay-transformer-evidence-90.json`. Next view should target ground-level equipment at source meshes270/271. Diamondplate surface positions are in `diamondplate-surfaces-91.json`. Goal remains active with material/gameplay integration work outstanding.

### Material usage audit92 and deferred focused test

Candidate91 private diamondplate walkway payload prepared at source mesh454. Harness attempts92/92b/92c refused because an independent OpenH3M.exe session was active; no test was launched and no capture/result is claimed. Existing session was left untouched. Private cache now seeds from completed local cache89, avoiding the locked shared cache.

`active-material-audit-92.json` traces source BSP part references and authored boolean/real settings for41 reported materials;29 have BSP part references. Materials without BSP references may still be used by render models and are NOT declared unused. Source-disabled material-texture switches and zero specular/environment contributions are distinguished from active missing inputs. Parallax height scales inspected here are nonzero: retain those paths; do not discard them as inactive. `material-priorities-92.json` records findings. `m10_metal_ext_a` has15 BSP part references and lacks detail_map2; parsed native catalog has no exact no-bump/no-emission family. Further equivalence or compiled-native work is needed before mapping it. Installed maps unchanged; Powerhouse goal remains active.

### Walkway result92d and observed gameplay-area brightness defect

After the independent OpenH3M session ended, test92d on candidate91 ran and exited0 with11 native hash passes. Individually inspected115137/126137/149137ms captures. The downward view clearly renders diamondplate tread/detail, confirmed by the center source-geometry ray; the short walk reaches the walkway edge overlooking water. `gameplay-walkway-evidence-92.json` and `walkway-material-rays-92.json` record evidence. This is a focused diamondplate pass.

The same view exposes a large near-white area beside the walkway and beneath the opposite building. Source-geometry rays hit `m30_concrete_ext_settlement` under these pixels, but do NOT establish whether the cause is opaque material, transparent overlay or later lighting. Prioritize this observed gameplay-area defect over small material refinements. Transformer visual check remains unresolved.

Candidate93 implements the High Ground no-normal-map, two-detail shader for `m10_metal_ext_a`, with added simple emission explicitly zeroed and donor animations removed by source animation conversion. Build/data checks passed; all1951 vertex/453 index buffers match91. `metal-exterior-cache-audit-93.json` verifies authored transforms, zero emission and zero animations. SHA256:3f7f82f6c0f9df2b06542fd9d14d4e15802ebe994eadb55449bd0cd97ebdc0cc. Final source-asset audit shows BOTH detail textures are neutral default_detail: this is structural fidelity, NOT evidence of a visible improvement. Do not spend a separate native run on that neutral texture change. Candidate91 remains the latest focused visually checked candidate;93 is built but not visually checked. Installed maps unchanged. Source attribution remains Reach Powerhouse via GeneralHeed/Priception workshop3003239190, with link in MAP-CREDITS.md.

### White gameplay-area surface isolated - test94

Private candidate91 test changed only concrete material9363 specular_coefficient from1 to0. All three native captures individually inspected: the near-white area beside diamondplate and patch beneath opposite building become textured concrete; water remains visible. Test exited0,11 native hash passes. Evidence: `specular-isolation-evidence-94.json`. This identifies concrete specular shading as a cause; zero specular is diagnostic only and must NOT replace authored reflections in the final map. Installed maps unchanged.

Source `m30_concrete_ext_settlement` uses two-lobe Phong, a dedicated mask at9xUV, and static `d_cubemap_vertical_noise`; fallback6109 instead inherited Cook-Torrance roughness0.05 and omitted source mask/static cube/detail inputs. Full source/native audit: `concrete-exterior-source-94.json`, `concrete-exterior-native-94.json`.

Compiled13 exploratory original-Xbox360 pixel programs retaining source detail blend, white-mask-equivalent unit normal detail, texture specular mask, two-lobe Phong and per-pixel static environment mapping. Reused pinned HaloShaderGenerator5af3671/Xenos source adapter; no new shader dependency downloaded. `concrete-native-94/compilation.json`, `route-plan.json`, `native-interface-audit.json`:12 native Zanzibar `_1_2_0_2_2_0_0_0_0_0` entry interfaces match, fixed-register mismatches0, unresolved parameter routes0. Opaque shaders omit maybe_calc_albedo entirely (ifdef, not a numeric conditional). These programs are NOT integrated/native-rendered yet. Next: bind new static environment sampler and three source real inputs (detail strength, env tint, env contribution), clone native template/programs, preserve authored settings, build and inspect. Source map attribution remains Reach Powerhouse via GeneralHeed/Priception workshop3003239190; see MAP-CREDITS.md.


### Gameplay-area concrete correction95 and reproducible recipe

User accepted the background and prioritized the gameplay area. Candidate95 integrates twelve compiled original-Xbox360 pixel programs for exterior concrete, retaining the native vertex interfaces and all authored material constants, detail layers, specular mask and static cube. Source white/unit normal mask is reduced algebraically. Diagnostic zero specular was NOT adopted. All1951 vertex and453 index buffers match93 exactly. Generated-cache audit: compiled-concrete-integration-audit-95.json.

Native run .local/loading-traces/20261102-220219-31996 exited0,11/11 hash checks. Individually inspected all three captures: foreground and opposite concrete banks retain texture, diamondplate remains visible, water and shaded openings render through the short walkway movement. Evidence: work/powerhouse/gameplay-concrete-evidence-95.json. This is focused gameplay-area material evidence, not full-map traversal or console validation. Installed maps unchanged; goal remains active.

Reproducible recipe lives in snapshot/reference/powerhouse-concrete-shaders; build_powerhouse_water_shaders.py --kind concrete reproduces all13 source entries with reviewed microcode hashes and matching native parameter routes. Normal build-powerhouse.ps1 now prepares this recipe automatically. Source attribution: Reach Powerhouse via GeneralHeed/Priception, Workshop3003239190 (link in MAP-CREDITS.md); this project supplies the Xbox360/OpenH3M adaptation.

Candidate96 normal-wrapper rebuild passed: all authored concrete constants and twelve embedded programs verified; all1951 vertex/453 index buffers are byte-identical to native-tested95. Compiler enforces reviewed microcode hashes; only compiler debug records may differ. Private payload-96 staged; not separately run in-game. SHA256: a55646d2b346375d068c17427ae19613e726ef221511754c358f85f2bbbe22b3. Candidate95 remains the direct native visual evidence.

Candidate96 SHA256 also matches95 exactly: the normal-wrapper output is byte-for-byte identical to the native-tested map, including shader debug records.

### Gameplay focus and optional river candidate97

Previous goal turn made progress: fixed concrete is native-tested and normal build96 matches95 exactly. Candidate97 restores settlement_river color/normal layers and four animations; generated constants/programs and unchanged geometry verified. Source geometry inspection then placed these river surfaces in the distant valley, outside current gameplay focus. River support remains opt-in only (OPENH3M_POWERHOUSE_RIVER_SHADER_DIR), not enabled by the normal build and not visually verified. Do not divert native runs to this background work. Private candidate97 is not the selected gameplay candidate.

Circular grates are confirmed on playable floors. Candidate98 uses native Docks vertex/draw interfaces with source Cook-Torrance, static cube, normal mapping, alpha cutouts and simple parallax. All12 used shader interfaces match. Cook-Torrance lookup externs traced to native Armory; no_dynamic_lights is a name-routed material boolean, not fixed-register state. Native verification pending. Source: Reach Powerhouse via GeneralHeed/Priception Workshop3003239190, link in MAP-CREDITS.md.

### Gameplay floor grate98

Native run .local/loading-traces/20261102-222059-28408 exited0;11 native hash checks passed. All115137/126137/149137ms captures were inspected individually. Perforated floor, openings and surface detail remain visible through the short walk; observer stays on the floor. Source geometry rays identify mesh105/instance869/m30_metal_grate_circular_floor in three probes. Evidence: gameplay-grate-evidence-98.json and grate-material-rays-98.json. Both circular grate materials retain all seven source textures, all source constants and source booleans including the float-mapped material texture switch. Twelve embedded programs per material verified, and all geometry buffers match96. Candidate98 SHA256727a1dfd51023688b1f58f8366bb1657292b5b1ab9894a62806c28659351b9b7. This is a focused floor-placement result, not every-placement/full-map/console validation.

Normal build now prepares the reviewed grate recipe automatically. Candidate99 rebuild checks reproducibility. Spatial inventory98 distinguishes distant river from playable buildings; gameplay-material-preflight-99.json audits native donor availability and source settings for remaining materials at playable elevations. TODO.MD now follows the user's accepted background and gameplay-area priority. Installed maps unchanged; goal active.

### Candidate99 rebuild regression from shared lens-layout correction

Candidate99 exited1 during environment conversion: forge_sun_flare.py now rejects nonzero MCC axis offsets after the original-H3 reflection-layout correction documented in REACH-CONVERSION-PROCESS.md. This shared correction landed after successful98. The normal-wrapper rebuild is NOT verified and99 is not a candidate. Preserve the corrected bitmap-index/rotation layout; do not restore the corrupt old packing or silently drop axis offsets. flare-axis-preflight-99.json records all27 primary-source reflection flags/rotations/offsets; most have world-space flag0x800 and nonzero axis offsets, while secondary flare offsets are zero. Resolve their original-H3 representation before the next normal build. Native98 remains valid focused grate evidence, not proof that current full build succeeds. No outside files or installed maps modified. Goal remains active; this is the first occurrence of this build blocker, and source research remains possible.

### Native flare research and independent window-floor preparation100

Previous turn classified as progress: grate implementation and native evidence98, plus reproducible build failure99. Current source still enforces the corrected lens layout. Original executable reads were inspected directly (sub_82471B78 and sub_82472380); pointer provenance confirms bitmap index+4 and rotation+8. Stock audit inspected1015 reflection records across disc maps: +2/+6 are zero in every record, not evidence of a usable axis-offset field. flare-curves-preflight-100.json shows nonzero-axis primary reflections have active radii/brightness, so they cannot be dismissed as inactive. A user clarification is pending: allow original-H3 placement while retaining flare appearance inputs, or require exact MCC offsets. Do not infer consent from elapsed time. No axis-drop bypass was added, and no new full map built.

Independent gameplay progress: windowbox_subfloor_a has five texture inputs and active simple parallax. Its default gray_50_percent_linear bitmap is actually one linear ARGB32 texel555555ff, green85/255=1/3. Thus height=(1/3-1/2)*0.1=-1/60 before multiplying tangent-space view direction; it is not neutral despite its name. Existing fallback loses this behavior. Compiled13 original-Xbox360 entries preserving detail normals and simple parallax; twelve native Bunkerworld _0_2_0_0_0_0_0_0_0_0 interfaces match with zero unresolved routes/fixed-register mismatches. Files: window-native-100, window-height-preflight-100.json, window-preflight-100.json. Integration is opt-in OPENH3M_POWERHOUSE_WINDOW_SHADER_DIR only; source syntax checked, but no generated-map or native appearance claim. Normal build does not enable this unfinished profile. Goal remains active and independent gameplay work is still possible. Source attribution remains Reach Powerhouse via GeneralHeed/Priception Workshop3003239190; link in MAP-CREDITS.md.

### Private window-material integration101; visibility retest102

The full rebuild remains blocked by the pending flare-placement clarification. Independent material testing uses a private targeted patch over native-tested98, not a flare guard bypass. build-window-patch-101.py imports only windowbox_subfloor_a and replaces its existing BSP slot56; no render-model slots reference it. All source constants, five textures and twelve embedded shader programs verified. All1951 vertex/453 index buffers and all42 pre-existing lens roots/reflections are byte-identical to98. The native stock gray_50_percent_linear bitmap record is retained exactly; it is an engine-provided default with no cache pixel resource, so the audit does not claim a native GPU pixel readback. Candidate101 SHA25657e08b131302a20769c7704f47f0ca7e4c38a975408c83f2c2165cd99eb90142.

Native run101 (.local/loading-traces/20261102-224405-3232) exited0 with11 hash passes. All three captures individually inspected: the intended target is obscured by a nearby wall. Do NOT count this as material visual acceptance. Source geometry rays then found one clear sightline from existing spawn117.8840027,244.1369934,41.3517990 toward mesh111/instance899; evidence window-clear-sightlines-102.json. Retest102 is running with the same map in a new private view payload. Native-window-102.log and its process/session are authoritative for completion; do not duplicate an active run.

Reproducible window recipe and interface metadata are in snapshot/reference/powerhouse-window-shaders. --kind window reproduces all13 compiled program microcode hashes. Normal build does not yet enable the window profile. Goal remains active. Source attribution: Reach Powerhouse via GeneralHeed/Priception Workshop3003239190 (MAP-CREDITS.md).

### Completed focused window retest102

Retest102 (.local/loading-traces/20261102-225008-8496) exited0 with11 hash passes. All three captures individually inspected: the intended recessed grid and trim render through the short movement. Source diffuse texture independently decoded and inspected; its panes are authored dark. Evidence: gameplay-window-evidence-102.json. This supersedes pending retest status above; it does not claim pixel-perfect parallax or all-placement coverage. The window recipe now reproduces all13 microcode hashes and the normal wrapper prepares it. Full map rebuild remains blocked by the separate pending flare-placement decision.

### Gameplay opaque grate103 and adjacent terrain follow-up

Candidate103 privately patches101 BSP slot43: restores the second normal layer and authored detail strength5 for m30_metal_grate_circular_floor_opaque. All four source textures/constants and twelve embedded programs verified;1951 vertex/453 index buffers and42 existing lens records remain byte-exact. SHA2563eeff3526e736edb9efe616ed9a8ac255e2aaccdd799d7d194ca461a316d8551. Reproducible opaque-grate recipe matches13 microcode hashes; normal wrapper now prepares it. Full normal rebuild still awaits the flare-placement decision.

Native run .local/loading-traces/20261102-230047-32480 exited0 with11 hash passes. All three captures individually inspected: opaque circular grate renders through short movement. Source ray700,110 identifies mesh21/instance61. Evidence gameplay-opaque-grate-evidence-103.json and opaque-grate-material-rays-103.json. Adjacent terrain is black in the first two captures; rays200,400 and500,550 identify 30_settlement_040_ground_new, mesh454. Investigate this next within the gameplay area; do not treat surrounding scene as accepted. Corrugated metal remains unfinished: source self-illumination9 is Simple_Four_Change_Color with object_change_color_quaternary, not a constant white glow. Goal active; no installed maps changed. Source attribution remains Reach Powerhouse via GeneralHeed/Priception Workshop3003239190 (MAP-CREDITS.md).

### Terrain investigation105 - no fix established

Candidate103 remains selected. terrain-draw-routes-105.json proves the affected terrain template specialized programs, entry tables, parameter names, routes and pass states match Bunkerworld. The new read-only verify_terrain_draw_routes.py is committed locally as5a35027. terrain-native-atlas-105.json decodes all8 lightprobe and2 dominant layers exactly to source; compression vectors and cluster12 binding match. terrain-native-streams-105.json verifies mesh454 primary world and lightmap UV streams against source conversion. These are generated-cache checks, not live GPU fetch proof.

Private material-isolation105 changes only BSP slot192 to the already-tested exterior concrete material (slot173), plus header authentication updates, over payload-walkway-103. No geometry/lightmap/flare changes. Native run20261103-082258-15796 is inconclusive: both generated captures115137/126137ms were individually inspected, but the downward input did not take effect, so the original black-patch view was not reproduced. Third capture missing;180-second watchdog fired, harness exit wait timed out, and subsequent PID6944 check confirmed process absent. No native hash-summary success or terrain fix is claimed. terrain-isolation-evidence-105.json records limitations and source rays. Next verify map-ready timing and repeat stationary matched view; avoid concurrent heavy ray tracing during native capture. All work stayed in repository; installed maps unchanged. Full rebuild still awaits the flare decision. Source: Reach Powerhouse via GeneralHeed/Priception, Halo Online Map Pack for Halo3, https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190; this project is its Xbox360/OpenH3M adaptation.

### Terrain material-path isolation106/108/109b

Completed matched downward-view comparison. Native106 with concrete substituted only in BSP slot192 renders textured/lit ground; unchanged103 in108 renders the same ground black. Captured camera directions differ by less than1e-7 and positions by0.000194 world units. Both exit0 with11/11 native hash passes. Each single native capture was individually inspected. terrain-material-comparison-108.json records the result. Native replay time starts after process launch: the early observer reading was not the completed capture camera;106 succeeds despite the earlier timing concern. Redundant107 was cancelled before capture.

Diagnostic109 changes only terrain9517 blend bitmap reference to existing stock color_white. First run failed capture completion before watchdog;109b exits0 with11/11 passes and its individually inspected single capture still shows black ground. Neither concrete substitution nor white blending is a production correction. Material root/postprocess flags and options also match source and native donor (terrain-root-state-108.json). Existing invalid-texture-fetch warnings occur in both the successful concrete diagnostic and unchanged terrain, so those warnings alone are not the terrain cause. No test process remains. Three native captures total were generated and individually inspected this turn.

Next inspect actual terrain draw bindings/lighting output. Current GPU DLL SHA256a262536b7cdb5923995235df1dc618ed89ebceddbf79af1223327b2ab2bf105f lacks a verified trace_loading draw entry: resolve its symbol/member offsets before sampling. Candidate103 remains selected; full rebuild still awaits the flare decision; no install/push/console/SystemLink claim. Attribution: Reach Powerhouse via GeneralHeed/Priception, Halo Online Map Pack For Halo3, https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190; this project supplies its Xbox360/OpenH3M adaptation.

Full retained-mip audit109 passes:13 textures and117 mips match selected source blocks after required signed-DXN conversion. Reproducer: snapshot/tools/verify_terrain_texture_mips.py; report work/powerhouse/terrain-all-mips-109.json. This rules out missing/misplaced cache mip blocks under the converter layout, not runtime sampler/LOD binding.

### Terrain lightmap register correction114

Native112/113 tracing identified a four-register material upload collision: opaque-grate albedo parameters c208/c209 cleared persistent lightmap scales c210/c211. Candidate114 reserves complete c208..c215 blocks during XDK compilation; those material parameters move to c233/c234. The native capture at .local/loading-traces/20261103-092225-22068/proof-loaded.png was individually inspected against108: previously black ground is visibly textured and lit. All1024 observed draws retain correct scales, including terrain static-per-pixel sample480. Eleven hash checks pass; harness exits0 after180-second watchdog (not a natural game exit). All geometry buffers and42 existing lens tags match101. All13 programs reproduce and12 interfaces match. No installation or full-map completion. Other custom profiles also use these protected blocks and need correction/validation. See terrain-correction-evidence-114.json and the tracked powerhouse-terrain-investigation.json. Full rebuild remains gated by the flare-layout decision.

### Broader lightmap protection115

Private candidate115 protects all five remaining custom profiles: concrete, grate, window, water and splash. Original pinned recipes reproduced;65 programs compiled and60 native interfaces passed, with no remaining material routes in c208..c215. Exact baseline signatures matched7 pixel tags and7 templates; original metadata outside shader fields and raw asset payload remain unchanged. SHA2560d913ca99912706b917b05fe19b43b22dd3ee4d95e02a7ace72c04948dbdb51c.

Terrain run20261103-093302-1892 capture individually inspected: adjacent ground remains textured/lit and1024 sampled draws retain lightmap values. Window run20261103-093725-32056 capture individually inspected but intended window outside frame; repeat recovered downward camera sequence. Water run20261103-094042-4172 reached intended area but no capture completed before180-second watchdog, harness exit1; visuals unverified. All three runs passed11 integrity checks. Only two images were produced and both inspected. No animation, parallax motion, audio, traversal, Forge, performance, console or System Link completion claim. No process remains.

Production recipe promotion deferred; candidate114 remains the earlier focused accepted terrain reference,115 a broader private candidate. Full rebuild still gated by flare-layout decision; no installation or push. Evidence: snapshot/reference/powerhouse-lightmap-safe-115.json. Attribution: Reach Powerhouse via General Heed/Priception, Halo Online Map Pack For Halo 3, https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190; this project supplies Xbox360/OpenH3M adaptation.

### Focused shader retests118-120 and corrugated binding

Three native captures generated and individually inspected, each under180-second watchdog; all runs passed11 integrity checks and harness exit0. This supersedes the incorrect outside-frame interpretation of116: source mesh111/instance899 and baseline102 identify the central roof arch as the window. Distant118 remains too dark to resolve reliably; closer120 clearly shows recessed window grid and trim. Static surface rendering confirmed, moving parallax unverified. Water119 capture completed without draw sampling; foreground terrain remains lit and water visible, but strong reflection obscures detail. Splash and full water appearance remain unaccepted. Evidence: snapshot/reference/powerhouse-lightmap-safe-retests-120.json.

Corrugated source self-illumination9 uses simple illumination with self_illum_color supplied by object_change_color_quaternary and intensity8. New verifier confirms native external usage10/source18 against explicit entry/pass mappings in Armory and Bunkerworld (ten shader entries each). Runtime BSP-instance color value is not yet established; do not substitute a constant glow. No option9 donor found in25 readable inventories; shared.map parser failure prevents an exhaustive availability claim. Evidence: snapshot/reference/powerhouse-corrugated-binding-investigation.json. No material rewrite, recipe promotion, installation or push this turn. Full rebuild still gated by flare-layout decision. Attribution: Reach Powerhouse via General Heed/Priception, Halo Online Map Pack For Halo 3, https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190; this project supplies Xbox360/OpenH3M adaptation.

### Corrugated material121-124

Private patch over115 changes BSP material slot110, preserving source constants and boolean switches, all1951 vertex/453 index buffers and42 lens records. Thirteen XDK programs reproduce; twelve native interfaces pass. Fourth-color self-illumination uses native external usage10/source18 atc102, intensity8; no fabricated material color. Complete source reflection cube restored: six faces x seven mips exact; six2D inputs have24 retained mips exact.

Three captures121,123,baseline122 individually inspected. Panels render in123 with no obvious stationary regression against matched115 baseline122. All runs passed11 integrity checks, harness exit0 after180-second watchdog; no process remains.123 trace:4096 draws,15 matching material draws; lighting pass receives fourth color(0,0,0,1), intensity8 and six-face64px cube with mip range0-6. Lightmap scales stable throughout.

Further reflected-global upload-block audit found45 material overlaps in121/123, including final simple-light and active-camo blocks. Revised candidate124 removes all identified overlaps;13 programs reproduce and12 interfaces pass, but124 has not been run natively. Its shader allocation differs from123, so earlier captures are not acceptance of124. Other profiles also need wider protection: concrete46,grate47,window7,water48,splash49 overlapping routes. Evidence: snapshot/reference/powerhouse-corrugated-evidence-124.json and powerhouse-corrugated-shaders. Workspace integration patch preserves only this turn's edits to previously dirty/untracked conversion helpers. No normal full rebuild, installation or push. Flare decision still gates full rebuild. Attribution: Reach Powerhouse via General Heed/Priception, Halo Online Map Pack For Halo3, https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190; this project supplies Xbox360/OpenH3M adaptation.

### Shared-register candidate125 (2026-11-03)

All seven custom shader profiles reproduce:91 programs,84 interfaces,zero reflected shared-block overlaps. Candidate125 preserves other original metadata and raw asset payload. Focused native corrugated and terrain captures pass; terrain remains lit/textured. River127 shows an overlook, so water/splash motion remains unverified. See snapshot/reference/powerhouse-shared-register-evidence-125.json. Full rebuild still awaits flare-layout decision; no installation or push.

Source: Halo Reach Powerhouse, General Heed / Priception, Halo Online Map Pack For Halo 3 (https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190). This project provides the Xbox360/OpenH3M adaptation.

### Animation register repair130 (2026-11-03)

- [ ] Native-test candidate130 water/splash animation. Fixed150 stale animation register bindings left by shader relocation; direct repair and updated patch pipeline produce identical maps, with zero remaining mismatches. Source constants and15 animation functions remain exact. Candidate125 captures show water visibility but do not prove animation; splash129 captures moved. See powerhouse-animation-register-evidence-130.json.

The previous static acceptance did not cover animation routing. Candidate130 only changes150 animation destination registers in125; template constant identities and function indices are preserved. Updated patcher reproduces the same output from124. Native verification remains required.

Source: Halo Reach Powerhouse, General Heed / Priception, Halo Online Map Pack For Halo 3 (https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190). Xbox360/OpenH3M adaptation by this project.

### Candidate130 focused splash motion verified (native133)

- [x] Candidate130 focused splash appearance/motion verified in native run133: both frames inspected, stationary camera, four geometry rays identify splash. All1788 rmsh animation-route uses align; source bindings/functions and1951 vertex/453 index buffers plus42 flare records preserved. See powerhouse-splash-motion-evidence-133.json.
- [ ] Finish water bottom/inlet motion, moving parallax and broader gameplay/audio/Forge validation. Full rebuild remains gated by flare-placement clarification.

Run132 produced only one capture before the180-second watchdog; no motion acceptance. Run133 produced both frames and completed its watchdog with11 hash checks passing. Camera is stable from150.469 through179.609seconds. Four geometry rays hit the splash material first. Source named animation targets, kinds, inputs, ranges, periods and all15 functions across water/splash remain exact. Candidate130 is not whole-map acceptance; the diagnostic monitor FOV is0.35.

Source: Halo Reach Powerhouse, General Heed / Priception, Halo Online Map Pack For Halo 3 (https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190). This project supplies the Xbox360/OpenH3M adaptation.

### Stock height texture recovery137

Native135 proves two window albedo draws leave height sampler2 unbound while retaining scale0.1. Earlier101 assumption of an engine-created default was incorrect: target resource is stripped. Native Armory/Bunkerworld donors have resident local resources containing555555ff, matching MCC source. Candidate137 imports the Armory resource and repoints only window height binding; the normal material importer now recovers this audited stripped default. Adds one four-byte texture in a4096-byte aligned resource page; no shader math changes. Geometry1951vertex/453index buffers and42 lens records preserved. Native verification pending. Terrain136 passed actual capture and1024 stable lightmap draws. No install/push/full rebuild; flare gate unchanged.

Source: Halo Reach Powerhouse, General Heed / Priception, Halo Online Map Pack For Halo 3 (https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190). This project provides Xbox360/OpenH3M adaptation.

Candidate137 rejected: native138 crashed on load with access violation. Candidate139 repeats the identical texture repair with2MiB instead of8MiB metadata reserve (actual allocation1689864bytes); native140 passes180seconds/11hashes and binds1x1 ARGB32 height texture with ff555555 guest storage, unsigned linear sampling and scale0.1 in two matching albedo draws. This verifies binding, not moving visual parallax. Both metadata sizes satisfy the original XEX header address-range check; no64MiB tag-limit claim. Smaller reservation correlates with successful loading; exact crash cause not isolated. Candidate139 selected for next focused visual check.

### Candidate139 window appearance verified; motion remains open (native141)

- [ ] Verify distinct candidate139 window parallax in a magnified view. Native141: both frames individually inspected; window appearance passes at two nearby viewpoints, six geometry rays identify the material, and two albedo draws retain correct height binding. Small strafe stays on roof/in frame but does not establish parallax motion. See powerhouse-window-appearance-evidence-141.json.

Native141 completed its180-second watchdog with11 hash checks passing. Both captured frames were inspected sequentially. A100ms strafe kept the window on screen and the player on the roof. Six geometry probes first hit windowbox_subfloor_a; two albedo draws bind the recovered stock1x1 linear height texel at source scale0.1. This proves appearance at these views, not distinct parallax motion. Next use a magnified diagnostic view and surface-registered comparison without changing production height scale.

Source: Halo Reach Powerhouse, General Heed / Priception, Halo Online Map Pack For Halo 3 (https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190). This project supplies the Xbox360/OpenH3M adaptation.

### Candidate139 focused window parallax verified (native143/145)

- [x] Candidate139 focused window parallax verified in native143/145: three frames individually inspected; GPU-projection surface registration measures2px versus source prediction1.8px and non-parallax metal control0.25px. Authored height scale/texel preserved. See powerhouse-window-parallax-evidence-145.json.

All three captures inspected individually. The larger diagnostic viewpoint separation is0.3496world units atFOV0.45. GPU-based registration separates expected1.8pixel parallax from perspective: observed2.0pixel shift, metal control0.25pixel. Earlier FOV-only estimates were invalid. No production geometry, material or authored inputs changed this turn. Full rebuild still awaits flare placement; no install or push.

Source: Halo Reach Powerhouse, General Heed / Priception, Halo Online Map Pack For Halo 3 (https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190). This project supplies the Xbox360/OpenH3M adaptation.

### Candidate139 inlet motion verified (native147)

- [x] Candidate139 focused inlet appearance/motion verified in native147: both frames inspected, stationary camera, three rays identify inlet and eight matching GPU draws retain water inputs. Source functions/constants and150 animation routes verified. See powerhouse-inlet-motion-evidence-147.json.
- [ ] Finish river-bottom motion and broader gameplay/audio/Forge validation. Full rebuild remains gated by flare-placement clarification.
The historical inlet route was rerun against139 using a spawn-only diagnostic fixture. Both native captures were inspected individually. Camera is stable from152.11 to179.11seconds across19 observations. Three rays using live GPU projection first hit settlement_river_inlet; a fourth identifies the left cliff control. Fine water pattern changes visibly; normal-map inputs are present in eight matching entry3 draws. All15 source functions across water/splash remain exact;150 animation-route uses have no stale registers. River-bottom motion remains open. No install or push.

Source: Halo Reach Powerhouse, General Heed / Priception, Halo Online Map Pack For Halo 3 (https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190). This project supplies the Xbox360/OpenH3M adaptation.

### Candidate139 river-bottom motion verified (native149)

- [x] Candidate139 focused river-bottom motion verified in native149: both frames individually inspected; camera stationary, three rays identify the river bottom and11 draws match its source inputs. Separate inlet draw excluded. See powerhouse-river-bottom-motion-evidence-149.json.
- [ ] Complete broader traversal/collision, lighting/atmosphere, other water/effects, audio, Forge and performance validation. Full rebuild remains gated by flare-placement clarification; console/System Link untested.
Both captures inspected individually. Camera stays identical from147.125 to179.125seconds across28 samples; three rays using actual GPU projection first hit030_water_river_bottom, with a separately identified cliff control. Fine river pattern changes while the cliff remains stable. Eleven matching water draws use source-preserved bump scales(12,6)/(3,1.5); the separate inlet draw is excluded from that count. The same139 hash retains the source constants/functions and aligned150 animation routes verified in147. Both custom river-material motion checks are complete, not whole-map acceptance. No install or push.

Source: Halo Reach Powerhouse, General Heed / Priception, Halo Online Map Pack For Halo 3 (https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190). This project supplies the Xbox360/OpenH3M adaptation.

### Final LIVE DLC - user playtest release2026-11-03

- [x] Powerhouse accepted by user and packaged as final standalone Xbox360 LIVE DLC on2026-11-03. Seven payload files verified byte-for-byte; STFS hash tree passes. Release: .local/releases/powerhouse-final-20261103/Powerhouse-LIVE-DLC.zip. Further corrections follow user playtest feedback; nothing installed or pushed.

Uses the exact candidate139 authored-spawn map from native150, not a relocated diagnostic fixture. Final package content ID:DFF845E9BD59F60A62D3B39F76AEE7831366B3C1. Package SHA256:3cf677ec798f0e3af1423144ce62104f1bb1904353c68aef063b427d65aaf2be. Standard LIVE/STFS, Halo3 title4D5307E6, DLC type00000002, unsigned for OpenH3M/RGH/JTAG. User accepted completion and cleared the goal; historical unverified items are not additional release gates. Feedback will drive follow-up corrections.

Source: Powerhouse(Halo Reach / Halo Online lineage), General Heed / Priception, Halo Online Map Pack For Halo3, https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190. This project supplies the Xbox360/OpenH3M adaptation.
