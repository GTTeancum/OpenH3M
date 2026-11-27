# Spartan Advanced Forge (clean-room)

Advanced Forge editing for Forge Gulch (map 1730) and Force Cove (map 1731), written only from the
clean-room specification `tools/h4-forge/ADVANCED-FORGE.md` (sections in `tools/h4-forge/spec/`). It
contains no Halo 4 program code, no Halo 4 data and no Halo 4 shaders or textures. Saved layouts are
ordinary Halo 3 map variants: every editor value is transient and discarded on release.

Replaces the previous implementation (recompiled Halo 4 functions fed by a Halo 4 program image and
data pack), kept for rollback, outside the build, in `halo3mp/rollback/h4-bridge-advanced-forge/`.

## Files

| File | Role |
| --- | --- |
| `forge_core.h/.cpp` | The behaviour: input shaping, rotation and snap, hold distance, held update, magnets (search, score, align), soft-ceiling contact selection, keyframe body drive, monitor camera follow and obstruction smoothing, physics state table, coordinate panel, spawn pull. Plain host values only. |
| `forge_magnets.cpp` | Per-piece magnet tables in source code (543 magnets, 89 pieces), generated from spec 06 section 7. Bound by piece name to the installed maps' Forge palettes. |
| `forge_marker_material.cpp/.h` | Our own marker look (spec 07): procedural plasma ring + ray burst particles, world-size, distance fades, depth-tested. Compiled at start-up with D3DCompile. |
| `forge_native_tick.cpp` | Halo 3's own Forge per-player update (copied from Spartan's recompiled Halo 3 code) with a hand-off at its held block. |
| `../advanced_forge.cpp` | Halo 3 integration: reads the world into the core, applies results through Halo 3 services. |
| `../advanced_forge_menu.inl` | Rows added to Halo 3's Item Properties screen. |

Generators (`halo3mp/tools/forge/`): `generate_magnet_tables.py` (spec 06 + `palettes.json` ->
`forge_magnets.cpp`), `extract_palettes.py` (installed LIVE packages -> `palettes.json`),
`generate_native_tick.py` (recompiled Halo 3 -> `forge_native_tick.cpp`), `test_forge_core.cpp`
(standalone checks against the spec's own sample values). Re-run `extract_palettes.py` and
`generate_magnet_tables.py` whenever the Forge Gulch / Force Cove packages are rebuilt.

Renderer change: `halo3mp/patches/rexglue-sdk-scene-marker-forge.patch` (world-size marker sprites,
depth coverage when no depth clear is recorded, repeated same-camera token keeps its snapshot).

## Controls (Halo 3's own buttons, as tested)

A grabs/drops; right trigger held = manipulate (right stick rotates yaw/pitch, left stick forward
pulls the piece closer, sideways rolls); without the trigger the left stick moves the piece and the
right stick turns the view. X on a piece opens Item Properties with the added rows: Physics, Magnets,
Magnet Strength, Rotation Snap, and (while the piece is held) X, Y, Z, Pitch, Yaw, Roll. Magnets and
rotation snap start off (spec).

## Ravine map values (spec 03/04/05 "Ravine values", in `forge::ravine`)

- Sticks: Ravine dead zones (4095 per axis, then 4095 radial) and the two response curves are applied
  to the raw controller sticks (recorded as Halo 3's poll passes them to its own dead-zone routine,
  which is left unchanged for everything else). Right stick gets the square-to-circle correction.
  Triggers carry no dead zone or curve; Halo 3's trigger analog is used.
- Camera obstruction rays: row 27 lets every object kind block (crates, scenery, machines, items,
  units, vehicles, projectiles) plus front-facing structure surfaces; invisible walls and bullet-only
  surfaces would not block in Halo 4, but which Halo 3 surfaces those are is per-material (spec R9).
- Aim ray: Ravine's held pieces sit on layers the aim ray sees, so the held piece is not excluded.
- Spawn height offset h = 0.0. Creation still uses Halo 3's own clearance search after the spec's
  pull toward the player (overview, "Grab"); the H4 18-direction search is not implemented.

## Choices and limits to review

- Magnets apply to Forge scenery pieces; Halo 3 builds the Forge blocks as crate-type objects, so
  scenery and crate pieces with a table carry magnets. Weapons, vehicles etc. never do.
- Only scenery/crate pieces use the Advanced Forge held lifecycle; weapons and vehicles keep stock
  Halo 3 movement (same scope as the previous implementation).
- The installed Force Cove package holds only the 40 shared pieces; the 49 Cove-only pieces' tables
  are in source but unbound until a package containing them is installed.
- Spec 06's user decision asks for re-deriving Arena Window #1/#15 and eight numerically checked
  pieces from our mesh; positions are currently the spec's audited values (no mesh extraction yet).
- Coordinate panel follows the spec literally: a commit rewrites the whole orientation from whole
  degrees and positions on the 0.1 grid, and the held update lets the target lead the piece by at
  most 0.5 units per tick, so a large typed jump travels only that far.
- The looping marker sound (spec 07 Q9) and Halo 4's exposure/bloom (Q7) are not reproduced.
- Magnet Strength labels (Lowest .. Highest) are ours; Halo 4's labels were not in the spec.

## Proof

Standalone: `tools/forge/test_forge_core.cpp` checks the core against the spec's own numbers (pitch
curve hex samples, stick curve table, dead zones, Euler/quaternion conventions, rule D, rotation rate,
snap at the half step, movement speed and precision, lead cap, bounds, magnet snap / pull-away /
snap range / 45-degree rule, input shaping, monitor follow, camera obstruction smoothing, physics
table, coordinate rounding).

In game (hidden runs, `run_pc_port.py --installed C:/X360/OpenH3M --forge`, evidence in
`C:/Programming/GitHub/OpenH3M/.local/forge-tests/`): `p3-pullaway` (snap to the exact magnet, then
stick past half releases it, piece moves 3.5 units and stays), `p4-snap-phased` (90-degree snap, Phased
held = keyframed, drop = frozen without settling), `p5-normal` (Normal drop settles, dequeued, kept),
`p6-gulch` (snap and pull-away on Forge Gulch), `r15-markers` (markers drawn), `r18-coords` (X row
live in 0.1 steps), `e4-underground` and `v1-delete` (a piece dropped below the ground settles outside the playable
space and is deleted; on screen the budget refunds one piece and the palette count returns to 49 of
50), `e5-obstruct` and `v2-obstruct` (focus outside the level: obstruction rays from the piece toward
the player hit rocks, the clear fraction falls to about 0.78 and the screenshots one second apart show
the camera jump about 1.4 units closer, then hold), `s7-walls` (hidden `--build` run with its own save
folder: two Wall 2x2 snapped exactly 2.00 apart and saved with Halo 3's Save As New Map; saved 2.01
apart) and `s8-reload` (the saved layout chosen from the map list loads with both walls; the grabbed
wall reads exactly the saved position). Save precision: Halo 3 stores each position axis as one of
65,535 steps across the map variant's world bounds. Force Cove's bounds are about 12 km wide, so a
step is about 18 cm across and 2 cm vertically. `v3-stock-save` (Advanced Forge switched off) lands
on the same grid as `s7-walls`, so the rounding is Halo 3's, not ours; snapped seams can open by up
to one step after a reload (user 2026-11-27: accepted, map bounds left as they are). The code writes
nothing into the map variant itself (its writes are Halo 3 runtime fields after the variant block).

Diagnostic option `halo3mp_advanced_forge_test_offset=dx,dy,dz` (with
`halo3mp_advanced_forge_trace`) places a grabbed piece beside the last dropped one.
