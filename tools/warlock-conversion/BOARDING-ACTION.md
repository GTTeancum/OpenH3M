# Boarding Action conversion

Status correction, user 2026-11-23: Boarding Action was NOT cancelled; it was re-added and is
installed. The newest installed package seen is the 2026-11-15 "OpenH3M Custom Map Bundle -
Test" container (C:/Users/smmel/Downloads/4D5307E6/00000002/7269FC75124A36F23973AEC27B8C1911BDE54B13).
The cancellation paragraph below is historical and superseded.

Canceled by the user on 2026-11-05 due to too many visual issues. Removed from
the shared installed build, including map, menu metadata and five previews.
Do not resume or reinstall without a new user instruction. Notes below are historical.

Source: installed MCC H3 port, Workshop 2962955878,
`maps/boardingaction.map`; SHA256
`cd65c777dd678a3ee57e3e89db71382cc00893aea0b3eaf4fcc9e56488cc4b05`.
Scenario: `custom\levels\multiplayer\boardingaction\boardingaction`.

User approved removing the unsupported CE health packs on 2026-10-25.
The shared omission mechanism removes placements and Forge entries by exact
asset identity, scoped to this scenario. Candidate 02 removes all 10 health-pack
placements and retains 78 other equipment placements. Source Forge palette has
zero entries; `verify_forge_palette.py` passes all seven categories.

Rebuild with `tools/warlock-conversion/build-boarding-action.ps1`; optional
`-OutputMap` and `-Report` select repository-local outputs. Candidate 02 is
52,678,656 bytes. Build checks cover 362 collision trees, 17,917 packed nodes,
3,082 BSP leaves and 54 runtime decals. Native visual/gameplay acceptance is
separate and remains pending.

DLC identity: boarding_action, map ID 1735, title Boarding Action. Five preview
BLFs derive from the source pack's `images/boardingaction.png`.
`work/boarding-action/payload-02` stages seven new files and hardlinks the prior
77 installed files. It does not include the unaccepted Powerhouse candidate.
No installation promotion has occurred.

## Candidate 02 native check

Trace `.local/loading-traces/20261025-123746-38400` completed its 180-second
watchdog with exit 0. Header authentication identifies boarding_action.
Both 112000 and 140000 ms native captures were inspected individually. They
show the ship interior, numbered surfaces, pickups and H3 HUD/weapon, but
large wall surfaces appear heavily speckled and a bright opening is blown out.
Source-material comparison is required before identifying the cause or accepting
these visuals. The route remained at the spawn viewpoint; teleporter traversal,
weapon pickups, audio and menu preview appearance are not yet verified.
Candidate remains staged only; installed bundle unchanged.

## Material correction, candidates 03–04

Original-disc template inventory found exact native permutations for 17 of the
21 source materials. The scoped Boarding Action path now retains their named
texture/constant bindings, sampler settings and material animations. Candidate
03 reports no omitted texture or constant for those 17 materials. It is
54,546,432 bytes; this is file size, not resident console memory usage.

Trace `.local/loading-traces/20261025-124456-17352` completed its 160-second
watchdog with exit 0. Its single `proof-loaded.png` was inspected: the same
spawn view now has coherent opposite-wall panels instead of the earlier heavy
speckling. This verifies that viewpoint only; traversal, pickups, teleporters,
audio and menu preview acceptance remain outstanding.

Candidate 04 additionally routes `bloodgulch_light_blue` through the existing
Chiron opaque-emission adapter: native diffuse-driven emission with a private
fully opaque base alpha. Its build succeeds and preserves all named texture
and constant inputs. Candidate 04 has not had a native visual check.

Remaining mismatches are the threshold/basis sky materials and
`metal_flat_generic`. The latter uses MCC `cook_torrance_pbr_maps`, confirmed
from the source render-method definition rather than inferred option numbers.
The pinned shader reference is saved in `work/boarding-action/cook_torrance.fx`:
HaloShaderGenerator commit `5af3671c919e93b802dd6aa0899f6725de70992c`.
Its PBR control reads `(R, albedo_blend, environment contribution, G)`;
native Cook–Torrance reads RGBA directly. The authored environment contribution
is 8, so a naive normalized RGBA repack would clamp it. No such lossy adapter
has been implemented. Shader reference alone does not establish equivalence
to the original disc shader. Installed bundle remains unchanged.

## Candidates 05–06: cutout sky and material switches

`remaining-material-audit.json` records every decoded mip's channel ranges for
the remaining sky and metal materials. Both sky cutouts contain nonconstant
alpha; removing alpha testing is invalid. Their detail input is a single
opaque sRGB texel, so its linear contribution can be folded into emission color.
The new guarded `boarding_sky_emission.py` adapter uses Lockout's native
alpha-tested simple-emission permutation. It aliases the original base texture
and transform into the emission input, preserves the separate alpha test, and
zeros diffuse RGB to match source from-albedo emission semantics. Reference
equations are in the saved HaloShaderGenerator `work/powerhouse/albedo.fx` and
`self_illumination.fx`. This is a derived conversion requiring visual acceptance,
not an identical shader permutation.

Candidate 05 builds at 55,447,552 bytes. Independent serialized-cache inspection
(`serialized-sky-05.json`) confirms both cutouts retain matching base/emission/
alpha texture identities and transforms, zero diffuse RGB and the derived
0.991833667 emission-color scale. No named textures/constants are omitted.

Native trace `.local/loading-traces/20261025-125736-43500` completed its
160-second watchdog, exit 0. Both native captures (112000 and 135000 ms) were
inspected individually. The initial view retains coherent ship panels; the
turned/walked view ends against a wall. Neither capture exposes the sky, so sky
visual acceptance and teleporter traversal remain unverified. Do not reuse this
generic walk as a sky-validation route.

The source-switch audit also found authored `order3_area_specular` enabled for
steel and panel_strip, disabled for detail_strips. The strict conversion had
retained donor switches. Candidate 06 now remaps Boolean switches by name,
rejects enabled source switches without native equivalents, and fails explicitly
on unsupported integer constants. Its build passes. It has not been run natively;
the remaining PBR metal conversion and targeted native acceptance are outstanding.
No installation promotion occurred.

## Candidate 07: PBR metal controls

The scoped `boarding_metal.py` adapter replaces the generic fallback for
`metal_flat_generic` with Armory's native Cook–Torrance/detail-normal/dynamic-
environment permutation. Source control curve is 5 (sRGB), not linear. Decode
source R/G before writing native specular/roughness channels; measured maximum
linear-byte quantization error is 0.001947485. Native control B is normalized to
one and authored environment contribution 8 is folded into floating-point
`env_tint_color`. The source constant specular-tint texture becomes native tint.
Private opaque base/detail alpha neutralizes the donor's diffuse specular mask.
Original source images remain unchanged. All authored mip levels surviving the
512-pixel budget are retained in these adapted images.

Pinned reference files `work/boarding-action/environment_mapping.fx` and
`specular_mask.fx` come from HaloShaderGenerator commit
`5af3671c919e93b802dd6aa0899f6725de70992c`, alongside the saved Cook–Torrance
reference. Dynamic environment output multiplies control B and environment tint,
supporting the multiplier fold. This does not establish identical original-disc
shader behavior: the MCC PBR reference's dynamic-light multiplier uses its
separate scalar specular tint, whereas its main path samples the tint texture.
The native material uses one constant tint. Candidate remains explicitly marked
an approximation and requires native visual acceptance.

The donor exposes `use_material_texture` as a real constant, while MCC represents
it as a Boolean. Conversion now maps that named switch across representations,
including false values on other Boarding Action materials. It no longer retains
an unrelated donor value. Native `order3_area_specular` remains a Boolean.

Candidate 07 builds successfully: 55,885,824 bytes, all six metal texture inputs
represented, no omitted named real constants. No native run yet. The opaque-alpha
encoder was corrected to decode every BC mip when retaining color mips; a
six-level synthetic BC3 chain with distinct per-level colors verifies the output
against explicit ARGB colors. All four `test_forge_world_budget.py` tests pass.

## Candidate 07 serialized and native checks

`serialized-metal-07.json` independently reads the generated cache and confirms
the converted control bitmap is linear and mipmapped, `use_material_texture`
is 1, order-3 area specular is enabled, and the environment multiplier/tint are
serialized correctly. The seven-category Forge palette verifier also passes
(the source has zero custom palette entries).

Trace `.local/loading-traces/20261025-131026-40228` reached Forge monitor mode,
crossed into the central gap and rose to approximately (4.76,-1.61,14.52).
Its inspected 135000-ms capture shows coherent walls, numbered decks, pickups
and lighting from above. The requested 155000-ms capture did not arrive before
the 175-second watchdog, so the harness returned exit 1 for incomplete capture;
do not report the whole run as passing.

The upward-view follow-up `.local/loading-traces/20261025-131417-19336` requested
one capture and completed exit 0 at the 175-second watchdog. The inspected image
shows the upper hull and starfield. It does NOT expose Threshold/Basis, so it
does not yet validate their cutout materials. Observer position was about
(4.83,-1.61,14.60), direction (-0.693,0.005,0.721). Further sky inspection should
derive the planets' directions from their source mesh/material assignments,
rather than repeat this angle. `route-placements.json` records source spawn and
eight wall-teleporter placements for directed gameplay checks. Teleporter
traversal, pickup behavior, audio and menu preview appearance remain unverified.
Candidate remains staged; the installed bundle is unchanged.

## Candidate 08: portal edge coverage

`teleporter-boundary-audit.json` confirms the same authored wall portal used by
Chiron: cylinder radius 0.2 with model Y bounds -0.4642264 to 0.5220661.
All eight placements inherit that cylinder, leaving visible portal edges outside
its trigger. The established Chiron model-derived box adapter now also applies
to Boarding Action. Candidate 08 builds successfully. Independent serialized
inspection (`serialized-teleporters-08.json`) verifies all eight box shapes,
dimensions (0.4,1.0841321,2,0.5), unchanged transforms and original channel pairs.
It does not establish live traversal. Candidate08 native runs are recorded below.

Source sky research is reproducible with
`work/boarding-action/locate-sky-materials.py`. Its report separates local-space
and rigid-node-translated directions. Basis lies southwest, but the scenario
sky-object transform has not been applied in this projection. Native candidate07
trace `.local/loading-traces/20261025-132036-38944` completed exit 0 with one
inspected capture. The monitor reached (4.77,-1.61,29.52), facing southwest/up.
Galaxy/starfield render, but the hull still occludes the planet. Planet cutout
visual acceptance remains open. Do not repeat this camera path as proof of it.


## Candidate 08 quality rejection and timing evidence (2026-10-25)

The user reports unacceptable visuals and performance. Candidate08 is NOT
accepted or promoted. Source is the Halo 3 MCC Workshop port 2962955878,
`maps/boardingaction.map`, not the Halo CE cache.

Native run `.local/loading-traces/20261025-135533-12324` finished at its watchdog.
The 65-second capture showed the preceding Chiron menu, not Boarding Action;
the 125-second capture showed Boarding Action gameplay. That image establishes
map identity, not visual acceptance. Traversal, audio, planet cutouts and preview
appearance remain unverified.

Timing run `.local/loading-traces/20261025-140050-31912` finished at its
170-second watchdog. `work/boarding-action/presentation-summary-08.json` uses
the existing presentation summarizer. During its 110�155 second logging window,
there were 2445 successful presentation/statistics samples. Of identified
consecutive-image display observations, 180 were four refresh intervals apart,
versus 22 two-refresh observations. Polling missed image IDs: this is evidence
of uneven sampled delivery, not an exhaustive scanout trace or identified cause.
Present-call median was 0.161 ms (max 2.311 ms); that alone does not measure GPU
rendering, simulation, or total frame time. Debug instrumentation and window
visibility are not controlled comparisons against a stock map.

The suspected 384x384 mip-loss explanation was checked and ruled out for the
four custom wall material detail bindings. Source uses stock
`objects\characters\masterchief\bitmaps\masterchief_microbump`.
Candidate08 native tag4792 retains mip byte8 (nine levels), and imported shaders
9239/9256/9259/9262 bind it as bump_detail_map, with source sampler filters
0/4/4/4 preserved. See `work/boarding-action/quality-timing-08.json`.
The generic encoder's NPOT limitation exists but does not establish a defect in
these bindings, because stock asset reuse bypasses that encoder. Do not change
this texture based on the rejected hypothesis. Continue with material constants,
lighting and measured runtime work, retaining the authored source appearance.


## Lighting colour investigation (2026-11-23, candidate cool-01, staged only)

User request: remove the yellow cast, return the original's cooler colours. Input: the
2026-11-15 package above (map SHA256 d0066723...), extracted to
`.local/lighting-colour/boarding-action/source-payload` (map removed after use).

Findings:
- Baked lightmap is not warm: term-0 log-mean red/green 0.778, blue/green 1.094; dominant
  light blue/green 1.14. Halo CE original lightmap (MCC halo1 boardingaction.map): red/green
  0.90, blue/green 0.87. The port's bake is already bluer than CE; matching CE would make it
  warmer, so it is unchanged.
- No camera effect, global screen effect or placed lights in the scenario.
- The scenario sky-atmosphere sun colour is orange (0.902, 0.655, 0.502; intensity 1.2).
  Halo CE's own sky tag (HCEEK `levels/test/boardingaction/boardingaction space.sky`) has a
  near-white sun (0.918, 0.922, 0.839, power 1.4) and a blue fill (0.196, 0.220, 0.396).

User reference screenshots (Halo CE, 2026-11-23) show neutral grey hull and clean white
panels; the port renders a green-olive cast (screen dark-area red/green 0.76-0.79 vs reference
0.91-0.98). A CE-lightmap match (red x1.157, blue x0.795, candidate 02) fixed red but turned
the spawn-room wall yellow (blue/green 0.66), so the balance was fitted to the reference
screenshots instead.

Candidate cool-03 (rejected 01: fog-only, no visible change; 02: too little blue):
`lightmap_color_balance.py --gains 1.33 1 1.05 --atmosphere-chroma 0.9176 0.9216 0.8392
--leave-vertex-lighting`. All five lightmap layer pairs rebalanced in place (pages fit their
slots); 85 scenery probes scaled; fog sun set to Halo CE's sky-sun balance at the same luminance.
20 per-vertex-lit mesh buffers keep their old colour (tool does not edit vertex lighting yet).
Package `.local/lighting-colour/boarding-action/live-03/Boarding_Action_20261123` (content ID
6819951E2B5FE806DBCDD88799BCE634907D0D6F). Health-pack removal untouched (same map). Not installed.

PC-port hidden runs, same three views before (`run-before-c`) and after (`run-after-03`), all valid,
~30 FPS; sheet with the user's references: `.local/lighting-colour/boarding-action/boarding-before-after.png`.
Dark-area red/green after 0.92-0.98 (reference 0.91-0.98), blue/green 0.80-1.08 (reference
0.88-0.95). Remaining differences: references are brighter overall; the spawn-room panel wall
keeps a slight olive tint (blue/green 0.80). Not checked on a real Xbox 360.

### Candidate cool-04: colour + brightness (supersedes cool-03)

User request 2026-11-23: also match the references' brightness. Same command as cool-03 plus
`--brightness 1.6`: the five lightmap ranges (SH 0-3, dominant) and the 85 scenery probes are
multiplied by 1.6; the decode is linear in those ranges, so no texels are requantized.
Package `.local/lighting-colour/boarding-action/live-04/Boarding_Action_20261123` (content ID
9BCB498743057149CF6D5A49AB89E90B2060C9C0). Not installed. Run `run-after-04`, same views, valid,
~29 FPS. Screen average level 21-32 (before 14-22; reference overviews 21-29). Sheet updated.
Remaining: lit white panels on the upper deck show a faint pink tinge; the 20 per-vertex-lit
mesh buffers keep their old colour and brightness; not checked on a real Xbox 360.

Installed 2026-11-23 at the user's request into the console release set
`C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/releases/console-repair-candidate` (combined Content
folder and a new per-map `maps/boarding_action` folder). Rollback: the unchanged 2026-11-15
package in the user's Downloads folder. Copying to the console is the user's step.

Accepted 2026-11-26: the user reports Boarding Action passes with candidate cool-04 (Boarding_Action_20261123).
