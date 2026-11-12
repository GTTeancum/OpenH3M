# Rodentia conversion

Candidate 01 installed with bounded native gameplay and menu proof. Source is Workshop 3500400217,
`maps/rodentia.map`, scenario `blackandfan/levels/multi/rodentia/rodentia`.
The author identifies it as the cut Halo 2 Rat Race reprise ported to Halo 3.
DLC identity rodentia, ID 1734; zanzibar is assembly basis only.

Use the pack's `halo3/maps/shared.map`. Audio resolves explicit banks in order:
`halo3/fmod/pc/sfx.h2maps.fsb`, `sfx.js_kestrel.fsb`, then installed MCC H3
`halo3/fmod/pc/sfx.fsb`. Source overrides win; missing hashes still fail. Ordered
resolution was checked for all 16,810 distinct hashes (source-banks.json).
Decoder and work directories are the established shared repository setup.

Pipeline additions:
- Preserve kill/safe-volume index arrays, validating every index against the
  unchanged trigger-volume array. Both source and target schemas use int16.
- Reuse the verified single-layer terrain adapter by shader options and exact
  parameter checks; it is no longer limited to Battle Canyon's scenario name.
- Skip only unnamed null object-palette placements; named invalid references
  still fail. Keep null light-volume palette slots to preserve index stability.
- Replace dual Needler and tracking rocket launcher with stock Halo 3 weapons,
  as required by the stock-asset policy.
- The H2 powerup flare has no legacy selector but its brightness is constantly
  zero. Preserve this disabled reflection; nonlegacy nonzero brightness remains
  unsupported. No general modern-to-legacy curve approximation was enabled.

Working output/report/log: work/rodentia/zanzibar-01.map, build-01.json,
build-run.log. Check active-run.json before launching another conversion.

Repeat conversion with `tools/warlock-conversion/build-rodentia.ps1` from the
repository. It refuses to overwrite an existing output. Candidate 01 is
135,131,136 bytes (128.87 MiB); metadata uses 4,673,632 bytes. All 445 collision
trees and 2,404 BSP leaves passed serialized validation. No geometry simplification
was needed. This file size is not a measurement of console runtime RAM.

Ambient life preserves both flock palette slots, the authored flock with nested
sources/sinks and the creature palette. Original-disc `flck` and `crea` assets
are reused with their native dependencies. Missing format descriptions were added
from the same pinned Assembly revision as the existing dependency schemas.

Native gameplay: `.local/loading-traces/20261025-053022-16040`. Both captures
(110000 and 145000 ms) were inspected: authored interior, lights, H3 weapon/HUD,
pickup prompt and changed camera position. All 11 hash checks passed. One
transitional observer read failed; 64 other samples succeeded. No exhaustive
traversal, palette behavior or audio verification is claimed.

Native LIVE installation/menu: `.local/loading-traces/20261025-053406-9288`.
The inspected capture shows Rodentia selected with its correct native preview.
Promotion byte-checked all 56 files. Report `work/rodentia/promotion-01.json`;
package `work/rodentia/live-01/CA6C5036591E07EA71F5840DDA88FADD5B1D07B7`.
The previous seven maps and profiles are preserved. Executable unchanged.

Cleanup of the redundant 135,131,136-byte assembly intermediate was rejected
by automatic approval policy; it remains at work/rodentia/zanzibar-01.map.
Other accepted map files are shared through hardlinks, not copied per test.

## Correction pass, 2026-10-25

Source: Blackandfan's Halo 2 Map Pack for Halo 3
(https://steamcommunity.com/sharedfiles/filedetails/?id=3500400217), containing
Rodentia, an H2 remake of CE Rat Race. Earlier remake authorship is unverified.

Candidate 02 restored two authored light materials. Native run
`.local/loading-traces/20261025-181602-40996` completed; both 115/130-second
captures were inspected. Fixtures emit, but the room/ramp remained too dark.
Host frame-change timing: median 33.36 ms, p95 33.93 ms, maximum 100.10 ms;
one interval over 100 ms. This short route is not exhaustive traversal.
Candidate 03 adds a map-specific +0.65 EV adjustment and requires native review.
Two fluorescent three-channel emission materials and the shared autoturret
material still need native shader mapping; see the remaining-emission audit.
No correction candidate has been deployed yet.

Candidate 03 native run `.local/loading-traces/20261025-182933-22784` completed.
Inspected its single `proof-loaded.png` capture (115 seconds): the +0.65 EV
adjustment improves floor/wall readability while retaining fixture highlights.
Timing median 33.37 ms, p95 33.69 ms, maximum 83.37 ms; no >100 ms intervals.
The three-channel fluorescent animations remain unresolved; this visual check
does not claim they are restored. Candidate 03 is 134,688,768 bytes.

### Candidate 04: three-channel fluorescent materials

The two forerunner_fluorescent_bloom materials now use the original-disc
`_0_1_0_1_2_0_2_0_0_0` shader from armory.map. All four source textures, all
source constants and channel_a animation are retained. Unit diffuse coefficient
and zero specular coefficient reduce the added material model to the authored
diffuse-only lighting; its extra diffuse-alpha specular mask has no contribution.
Guard source/donor material switches rather than inheriting unreviewed behavior.

The pinned shader reference used to check the equations is
[HaloShaderGenerator two_lobe_phong.fx](https://github.com/Beatthezombie/HaloShaderGenerator/blob/5af3671c919e93b802dd6aa0899f6725de70992c/halo_online_shaders/two_lobe_phong.fx),
compared with diffuse_only.fx at the same revision. This informs parameter
mapping; the actual executable shaders are copied from original disc assets.

Written-cache readback: work/installed-map-corrections/rodentia-emission-readback.json.
Both generated materials (9248 and9317) have unit diffuse, zero specular, zero
boolean flags and no integer constants. Their source parameter/curve content is
identical, so both match the same two serialized materials. Animation routes
retain channel_a and the source function period and endian-converted curve.
Build04 reports no unrepresented parameters/textures for either material.

Native run20261025-183802-33484: captures115/117 inspected sequentially;
room appearance remains stable, with no visual regression. Timing median33.37ms,
p9533.79ms, max66.77ms, no >100ms. These views do not clearly expose the affected
strips, so their animation is not yet visually verified. Material mesh/cluster
locations are saved in rodentia-fluorescent-locations.json for a targeted check.
Candidate04 remains isolated. Shared autoturret illumination remains unresolved.
