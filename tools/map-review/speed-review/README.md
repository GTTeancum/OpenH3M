# Sky Bridge and Reactor speed review — 2026-11-19

Static (file-only) analysis of the console builds the owner plays on a real Xbox 360:
Sky Bridge package `9A23C8B4FAC24082064FF40A08427BA25789DAD4` (map SHA-256 `ff192509…`)
and Reactor package `63E200F7E1B1B9E6122DB19225359F3595B3FB9B` (map SHA-256 `1aa6d277…`).
Nothing was run in the game, in OpenH3M or on a console. No frame rate was measured.

Owner's reports: Sky Bridge slows whenever much of the map is in view; Reactor slows inside
the reactor looking toward the centre. Owner ruled out capture-card measurement and in-game
iterative analysis by the agent.

Working files (ignored by Git) are in `work/speed-review`. The scripts here expect that
folder, `work/speed-review/deps/meshoptimizer.dll` (copied from the earlier
`.local/map-review-deps` build) and `work/speed-review/deps/raycast.dll`
(`clang++ -O2 -std=c++17 -shared -o raycast.dll raycast.cpp`).

## Findings

| Question | Result | Script |
| --- | --- | --- |
| Did conversion damage the zone PVS? | No. Open and doors-closed matrices are identical to the MCC sources for both maps. | `pvs_compare.py` |
| How loose is the PVS? | Typical (median) zone can potentially draw 82% (Sky Bridge) / 97% (Reactor) of all triangles; big stock maps 46–49%. | `load_audit.py`, `pvs_stock.py` |
| How heavy are the maps? | ~635k / ~608k triangles counting each placement once, about Rat's Nest (641k). In play from a typical zone: ~520k / ~590k versus ≤ ~300k on the heaviest stock maps. Draw-part counts are within the stock range. | `load_audit.py` |
| Would splitting multi-zone placements help? | No: 82→80% and 97→93%. | `split_bound.py` |
| Would per-placement pixel fade help? | No: 49% / 65% of placed triangles are in pieces over 4 world units in radius. | `fades.py` |
| Can the PVS be tightened? | No. Sightline sampling through cluster portals against solid opaque geometry confirms only 59 of 907 (Sky Bridge) and 96 of 955 (Reactor) non-adjacent visible pairs as blocked; load moves 82→80% and 97→94%. Not applied. | `vis_extract.py`, `vis_test.py`, `vis_gain.py` |
| Are many triangles permanently buried? | No: 1.8% front-side, 0.7–0.8% both sides, in every placement. Not applied. | `buried.py` |
| How far can simplification go with original vertices kept? | Sky Bridge 1–4% at ≤ 0.02 wu, ~12% even at 0.5 wu. Reactor 15% at 0.01 wu, 21–23% at 0.03 wu, 31% at 0.1 wu. | `reduce.py`, `reduce2.py`, `topology.py` |

Why simplification stalls: 1.34 vertices per triangle but only 0.52 unique positions per
triangle, i.e. ~2.6 vertices per position. Most positions are corners where three or more
UV/normal islands meet and cannot be collapsed without new vertices. Sky Bridge had already
been reduced ~28% by earlier passes.

Conclusion: both maps are roughly twice the stock potentially-visible triangle budget and are
genuinely open. No file-level change found reaches the needed ~45% without visible loss.
Remaining options are deleting content or rebuilding geometry at lower detail in the editing
kit. A plain editing-kit visibility rebuild with the existing portals would reproduce the
same PVS.

## Per-mesh render MOPP (subpart culling tree)

Decoded and validated against stock data (`mopp_validate.py`, `mopp_wide_check.py`,
`mopp_ops.py`), zero mismatches on Rat's Nest, Last Resort, Construct, Guardian, Sky Bridge
and Reactor; Orbital cannot be used because this geometry reader does not fit its buffers.

- The `Per Mesh MOPP` dataref holds two `hkpMoppCode` objects: one over subparts, one over
  parts. Header 0x30 bytes: offset vec3 + scale at +0x10, code size at +0x24, code at +0x30,
  padded to 16. The lightmap (`Lbsp`) copy at `+0x170` is byte-identical.
- Quantised coordinate = (mesh-local position − offset) × scale / 65536, 0–255.
- `0x26/0x27/0x28 lo hi`: bound X/Y/Z. `0x10–0x12 a b off`: split X/Y/Z, left child follows
  with max `a`, right child at `+off` with min `b`. `0x23–0x25 a b lo16 hi16`: same with
  16-bit offsets. Terminals `0x30+k`, `0x50 k8`, `0x51 k16`; keys are direct subpart (or
  part) indices. The reorder table was not needed.
- Rescale ops `0x01–0x04` are common in stock code and were not interpreted.

`reduce2.py` uses this to simplify whole parts, regroup triangles into the existing subpart
slots and regenerate the subpart tree in place (never longer than the original code).
`verify2.py` checks either method. reduce2 output has never been run in the game.

## Reactor test build

`work/speed-review/release/Reactor-Triangle-Cut-Test-20261119.zip`, container
`4C7EB882ADAAA99C328D84FE3196252B9F89870F`, map SHA-256
`1540c433bc7b826d8302f7bb84add69e20d23d460b9bff7ea69d491761248356`, map ID 1752 unchanged.

Built with the Powerhouse-proven per-subpart method (`reduce.py --tolerance 0.03 --ratio 0.35
--lock-border 1`), so culling trees are untouched. 576,128 → 457,276 stored triangles
(20.6%); 607,523 → 493,813 counting each placement once (18.7%). `verify2.py`: tag data
identical except part counts, subpart ranges and the geometry page descriptor; geometry payload
identical except reduced index ranges; collision resource identical; each subpart draws only
vertices its original subpart used. `check_pages.py`: 980 local pages pass. `build_dlc_live.py`
reproduces the previous Reactor container byte for byte from its extracted payload, and the
new container's STFS hash tree verifies. `preview.py` (flat-shaded ray renders, not the game
renderer) shows no holes and < 0.03% of pixels displaced by more than 15 cm in eight views
around zone 2; those views are the exterior dome, not the reactor interior.

The map file is ~25 MB larger: the rebuilt geometry page deflates 0.5% worse than the
original and is appended, leaving the old page unreferenced.

The container file inside the zip is named `Reactor_20261119` at the owner's request (map
names instead of content-ID hashes); a map-name file name is unconfirmed on console.

Not done: any game, emulator or console run; Sky Bridge build.

## Sky Bridge follow-up

The same proven method on Sky Bridge gives 4.7% at 0.03 wu and 6.3% at 0.06 wu (stored
triangles), so no build was made. `pieces.py` groups placed triangles by instance name: 463
name families, the top 45 hold 64%, and they are structural (`sbr_column*` about 14% over
roughly 55 placements, roofs, frames, bridges, balconies, `turf_skyscraper` backdrop about 4%,
two `tut_ladder_solid_06_short_wide` at about 6,300 triangles each). There is no single
decorative culprit to delete.

Credits: Reactor and Sky Bridge, Halo Online; Halo Online Map Pack For Halo 3 by General Heed /
Priception, https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190. Individual
original authors unspecified. Xbox 360/OpenH3M adaptation by this project.


## Sky Bridge test build and the failed heavy cut

A seam-ignoring mode was added to `reduce2.py` (`--weld`: positions welded, each output corner
reuses the best-matching original vertex, preferring one UV island per triangle) and tried on
40 column and ladder meshes (`pick_meshes.py`, pattern `column|ladder`, at least 600 triangles).
It removed 0.85% of the map at 0.03 wu and 0.90% at 0.06 wu, so it was dropped. `debug_mesh.py`
on mesh 75 (`sbr_column_011`, 14,096 triangles) shows why: in its main part 99% of welded edges
are shared by three or more triangles, because the surface is stored twice, back to back.
`duplicates.py`: back-to-back copies are 6.5% of Sky Bridge's stored opaque triangles and 1.7%
of Reactor's; same-facing duplicates are negligible. `components.py`: separate elements up to
30 cm across hold about 1% of triangles on either map, so deleting small detail is not a lever
either.

`work/speed-review/release-sb/Sky-Bridge-Small-Cut-Test-20261119.zip`, container file
`Sky_Bridge_20261119` (content ID `F8D910DA0468B95BAD8DDF14C6B93923674BEB93`), map SHA-256
`1e964315447e2f498fb23801be36fad197a7d1d3e84ab00cdf9457d2c25b8829`, map ID 1747 unchanged.
Same proven method and settings as the Reactor build. 570,261 -> 543,199 stored triangles
(4.7%); 635,132 -> 608,108 counting each placement once (4.3%). `verify2.py`, `check_pages.py`
(1,157 local pages), packager round trip against `9A23C8B4...` and STFS verification all pass.
`preview.py` around zone 16: no holes, < 0.02% of pixels displaced by more than 15 cm.
Never run in the game, an emulator or on a console.

## Neighbourhood merge build, kit-15 (2026-11-26) — rejected
All 961 placed pieces merged by material per 10-world-unit cell (`ass_merge.py --combine-cell 1000 --max-uses 100000
--max-group-triangles 12000`; 20,000 overflowed the kit's 65,535-index mesh limit), kit import, draft bake, kit build,
360 conversion (`kit_to_360.sh`, now falling back to MCC's own Halo 3 shared map and sound bank since the Halo Online
Workshop pack is no longer installed). Pain views 35.2 / 32.6 / 32.4 FPS uncapped vs 37.0 / 32.7 / 31.4 for the
installed build; draws per frame ~4,050 vs ~2,880 and indices ~4.9 M vs ~3.0 M. The merge increased the work. Cause not
yet established (candidates: combined pieces drawn in addition to their emptied originals, or lost per-piece culling).
Note: earlier kit-13's higher FPS came from a missing lightmap ("adding fake-o lightmap"), not from its geometry.
