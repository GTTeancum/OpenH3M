# Halo 2 multiplayer map -> original Xbox 360 Halo 3 (H2EK -> H3EK -> 360)

The route Tombstone (Halo 2 highplains) took, written down while porting Beaver Creek (Halo 2 beavercreek,
user 2026-11-23: "Battle Canyon is out. Beaver Creek 'HD-ish' is in"). Kits: Halo 2 Editing Kit in
`.local\h2ek-source`, Halo 3 Editing Kit in `.local\h3ek-source` (official tools only, run hidden).
Work folder per map: `.local\<map>`. H3 kit folder per map: `levels\test\<map>`.

1. Level geometry: `h2ek tool extract-structure-data scenarios\multi\halo\<map>\<map>` writes
   `data\!extracted\<map>\structure\<map>.ass`; copy to `h3ek data\levels\test\<map>\structure\<map>.ass` and run
   `kit_run.py tool structure levels\test\<map>\structure\<map>.ass` (creates scenario, BSP, lighting info).
   Missing-shader errors list the materials still to make.
2. Materials: material names carry the Halo 2 shader-collection prefix (`bc`, `f_im`, ...;
   `tags\scenarios\shaders\shader_collections.shader_collections` maps prefix -> folder). List the H2 shader tags,
   `h2_export_xml.py`, `h2_shader_inventory.py`, `tombstone_shader_plan.py <inv> <plan> <map>` (Halo 2 template ->
   Halo 3 option set; extend TEMPLATES for new templates), `h2_bitmaps_to_h3.py` for the plan's bitmaps then
   `kit_run.py tool bitmaps levels\test\<map>\bitmaps`, then `kit_run.py swap build-shader <plan>` (MaterialSwap).
   Water: copy a stock Halo 3 `.shader_water` under the H2 name (the kit builds real water geometry).
   Invisible walls: copy stock `objects\multi\shaders\invisible.shader` under the H2 name.
3. Placed rocks/foliage: `h2ek tool extract-render-data <object>` per scenery/crate type, then
   `ass2_add_instances.py <base.ass> <out.ass> <h2_placements.json> <type>=<jms>...` (instanced level geometry;
   material symbols such as `!%` render-only two-sided are kept). Re-import the structure.
4. Gameplay: `h2_export_xml.py` on the scenario, then `h2_gameplay_to_h3.py <scenario.xml> levels\test\<map>\<map>.scenario`:
   spawns, weapons, grenades, powerups and game-mode objects as stock Halo 3 objects (TagEdit, `.local\tombstone\tagedit`).
   Set scenario type multiplayer and a sky (`Block:skies`).
5. Lighting: `bake.py levels\test\<map>\<map> <map> draft|medium ...`; then `tool build-cache-file levels\test\<map>\<map> pc`.
6. 360: `build_scenario_checkpoint.py ... --slot <slot> --stock-materials --source <kit map> --basis <slot map>`, then
   `build_dlc_payload.py`, `build_dlc_previews.py`, `build_dlc_live.py` (see `.local\tombstone\rebuild.sh`).

Write guards: MaterialSwap.cs and TagEdit.cs only write under the listed `levels\test\<map>\` folders; add the map there.

## Beaver Creek decisions (2026-11-23)
- Sky: stock Halo 3 Valhalla sky (`levels\multi\riverworld\sky\riverworld.scenery`) for the first draft; Halo 2's
  Beaver Creek sky is a reused Coagulation dome. Easy to change.
- Stream water: stock Valhalla water (`riverworld_water_rough.shader_water`) under the Halo 2 name.
- Rocks (23) and bushes (25) folded into the level as instanced geometry; bushes render-only as in Halo 2.
- Gameplay: 87 spawns, 18 weapons, 23 grenade/powerup pickups, 30 game-mode objects (CTF, oddball, assault,
  territories, 5 King of the Hill hills, teleporter pairs on their Halo 2 channels).

## Beaver Creek package (2026-11-24)
- `C:\Programming\GitHub\OpenH3M\.local\pc-port\packages\BeaverCreek_20261124_v2`, content ID
  BEAA2C69975AC8C782C1E05012CBAA13C6079914, map ID 1752 "Beaver Creek" (own DLC identity, built on the Last Resort
  basis). Installed in the PC port with `--halo3mp_install_content` and loaded into Slayer; full 18-point survey taken
  from the installed v1 (same map, earlier preview). Not tested on a console.
- Final (high) bake with: stock Halo 3 foliage for leaves/bushes (`tombstone_shader_plan.py`), ground detail blends,
  red/blue light-panel emissives (`beavercreek_lights.py`), 8 faint white fill lights at Halo 2's lower-room glow
  markers (`beavercreek_fill_lights.py`; the two teleporter markers left to the stock teleporter effects), stream
  sound (`h2_sound_scenery_to_h3.py`), Sandbox Forge palette (`--stock-forge-palette`).

## Beaver Creek teleporters (2026-11-26)
- User report: teleporters visually and functionally broken. Cause: each Halo 2 two-way pad (2way_teleporter scenery
  with a sender flag on it and a receiver flag 0.75 units away) had become a separate stock Halo 3 sender and receiver,
  overlapping, with each receiver beside the other pad's sender.
- Fix (user: "Use H3 teleporters ... match the coordinates of the H2 ones"): one stock Halo 3
  `objects\multi\teleporter_2way\teleporter_2way.crate` at each Halo 2 pad position, (-16.422747,-0.043747,-0.199877)
  and (18.336424,-0.024657,-0.199755), both on channel alpha, facing Halo 2's receiver facings (178.208 / 0). The two
  receiver crates were removed; the unused receiver palette entry stays (removing it would shift later palette indices).
  `h2_gameplay_to_h3.py` now does this for any Halo 2 two-way pad.
- Package `C:\Programming\GitHub\OpenH3M\.local\pc-port\packages\BeaverCreek_20261126_v3`, content ID
  730063E04A449C42BB9A9E1B0DF1B696218DFEAA, map ID 1758. Installed 2026-11-26 in `C:\X360\OpenH3M\content` (replacing
  BeaverCreek_20261126_v1, kept as rollback in `C:\Programming\GitHub\OpenH3M\.local\pc-port\rollback`). Teleporting not tested in game.

## Elongation (fresh Halo 2 port, started 2026-11-26)
User: drop the 3longation (MCC remake) package and make a standard Halo 2 conversion so the conveyor is proper;
"the thing to be sure of with Elongation is that the conveyors move the player". Work folder `.local\elongation`,
kit folder `levels\test\elongation`.
- Geometry: Bungie's `elongation.ass` (h2ek extract-structure-data). The belts are level geometry with material
  `m elongation_conveyor_pro>` (`>` = conveyor); the Halo 3 tool builds conveyor surfaces from it
  (connected_geometry_conveyor_surface_builder; direction from the texture mapping). Check the built BSP's conveyor
  surface count after import, and test a player standing on a belt.
- Crates on the belts: Halo 2 script `elongation_mission.hsc` creates crate_left00-07 / crate_right00-07 every 400
  ticks at each belt start and destroys them in trigger volumes tv_crate_eraser_left/right. They are
  crate_tech_giant blue/red -> stock Halo 3 `objects\gear\human\industrial\crate_tech_giant` (stock-asset policy).
  Two `crate_cushion` objects sit under the spawn points (to check).
- Materials: 21 (15 tex_bump, 4 tex_bump_illum, 1 glass two_alpha_env_illum, 1 tech rack plasma illum). Added to
  `tombstone_shader_plan.py`: glass -> env + alpha blend; tech rack -> plain self-illum (Halo 2 plasma pulse dropped).
  Plan `.local\elongation\shader-plan.json`; 33 textures converted to `data\levels\test\elongation\bitmaps`.
- Write guards: MaterialSwap.cs and TagEdit.cs now allow `levels\test\elongation\` (both recompiled).
- First build `Elongation_20261126_v1` (draft bake, content ID C8208DACC0720B3217E969A30BBE035BBF437D55, map ID 1759):
  converts and loads. Belt test (player placed standing on each belt for 20 s, no input): the player did not move at
  all, so the Halo 3 runtime does not appear to drive bipeds with level conveyor surfaces (the kit builds 7 conveyor
  surfaces; the belt material scrolls at Halo 2's speed). The draft-bake map renders almost black (emissive panels only).
  Steam and fire effect scenery omitted: no exact disc-native particle shaders (converter refuses); sparks kept.
  Two `emergency` light objects and the `crate_cushion` objects are not placed (no Halo 3 counterpart identified).
- 2026-11-27: lighting fixed with 54 baked omni lights at Bungie's fixtures (`elongation_fixture_lights.py`, medium bake):
  hall, panels and belt arrows render (shots in `.local\elongation\run-belts-3`).
- Push zones (user-approved exception, AGENTS.md): invisible `levels\test\elongation\objects\belt_push` crate per belt,
  box 34.5 x 1.2 x 0.25 at belt level, phantom direction max velocity 0.48, acceleration 3. Belt test (player placed
  standing on the blue belt, no input, first benchmark point): moved +0.08 while dropping onto the belt, then held still
  for 19 s. With "use acc as force" set: no movement at all (flag reverted). Halo 3 holds a standing, idle player in
  place against a phantom push; phantoms act on players in the air. Moving platforms (machines) carry standing players
  in Halo 3; the 3longation remake's belts used them. Package `Elongation_20261127_v2` (content ID
  F5EA249D7682B5D6C8D5EC92B5EDB7111190EE68), not installed.
- Lift push (push zone tilted 50 deg up, acceleration 6, max velocity 0.31; package v3): same result, +0.36 while
  landing, then held still. Push zones replaced.
- Why 3longation's platforms stalled (work\elongation\conveyor-script-trees.json in the OpenH3M-source tree): each belt
  is three sliding machines that a script destroys and recreates on timers of about 260, 315 and 333 ticks; they drift
  apart, so at times no moving plank is under the player. Type changes and floor clearance tests kept the recycling
  and still stalled.
- Belt treads (user-approved 2026-11-27, replaces the push zones): one invisible `levels\test\elongation\objects\belt_tread`
  gear machine per belt (gear type and placement as stock Last Resort big_wheel; loops on its own, no script).
  Generator `.local\elongation\study\make_tread.py`: 25 slat boxes 1.5 x 1.2 x 0.07, one physics body per slat node,
  device:position overlay of 626 frames in Bungie's Lockout-elevator layout (frame 0 = default pose); slats move along
  the belt top at 0.48 wu/s (Halo 2's belt speed), drop 0.5 under the floor at the far end, return underneath, rise at
  the start; last frame = first frame, so nothing teleports. Cycle 78.125 s (= position transition time). Placed
  at (-1.25, 1.7, 0) yaw 0 (blue, +x) and (1.25, -1.7, 0) yaw 180 (red, -x). Converter: retail Collision Response
  default 0 added for this machine in tag_metadata.py (big_wheel retail value). Belt measurements from the ASS:
  `.local\elongation\study\ass_belts.py`.
- Package `Elongation_20261127_v4` (content ID 2DC11FD2488B08E4EDDC0D3293C25DF6081E6F4B). Standing-player tests, no
  input: blue moved -11.69 -> -0.55 over 23 one-second samples, red 11.70 -> -3.89 over 32, every sample 0.46-0.50,
  no stalls; height steady (v4 superseded and deleted).
- Belt crates were missing from v1-v5: the kit never compiled Bungie's script, because the scenario's `source files`
  block was empty (stock scenarios carry their .hsc text there; tool build-cache-file then compiles it, "scripts
  successfully compiled"). Added `elongation_mission` (the data .hsc) to `source files` with TagEdit; converter
  allow-list entry added in `scenario_scripts.py` (its opcode/graph audit still runs).
- Halo 3 multiplayer then reset each script-created crate 30 s after creation (abandonment; engine default when the
  placement's abandonment time is 0) and re-created erased crates about 30 s later (spawn time 0 = default). Bungie's
  Halo 2 crates ride about 75 s to the pit. The 24 named belt crates (crates[30..53], crate_tech_giant) now have
  abandonment time 120 and spawn time 32767, so only the script creates them and the pit eraser removes them.
  Tested without the eraser (crates still vanished at 30 s): the eraser is not the cause.
- Package `Elongation_20261127_v7` (content ID FF0E5A46F3012A1583B52D393AA97F42410252A0). Tests with the PC port's
  read-only movement trace (`--halo3mp_benchmark_track_box`, map_benchmark.cpp: player and objects in the box every
  250 ms; the benchmark holds the controller at zero until it completes, so use --benchmark-seconds 5 and send input
  after it): full rides on both belts at 0.48 wu/s, steady height; the player drops into the end pit and respawns (as
  in Halo 2); jumps land back on the belt and ride on (belt speed is not kept in the air, about 0.5 wu lost per jump);
  walking against and with the belt works; red-belt crates over 5 minutes: one every 13.3 s, no extras, every crate
  rides the whole belt into the pit and is erased; blue crates spawn and ride the same; a player walking into an
  oncoming crate is stopped at its face and carried along, the crate keeps its line and speed. 30 FPS (cap)
  throughout. Traces and shots: `.local\elongation\run-ride-blue` (v4 ride), `run-v5-red-jump`, `run-v7-crates`,
  `run-v7-blue`, `run-v7-bump`. Not tested: Xbox 360 hardware, more than one player, explosions on crates.
- Brightness (user 2026-11-27, "pretty dark still"): Halo 2 lit Elongation from its emissive materials (tex_bump_illum
  fixtures/panels) plus sky light through the windows; the port's lighting info had emissive power 0 on all 41
  materials. Bungie's Orbital (spacecamp, a space station with windows) sets emissive power on its fixture materials
  (main warm lamp 32, coloured 2-16) and its space-window glass (40). Set on Elongation's lighting info material info
  (index = ASS material order): fluorescents 12/15 and halogen 14 = 32 (Halo 2 power 1 x 32), hall panels 25/36 = 8
  (Halo 2 0.25), tech rack 9 = 4.8 (Halo 2 0.15), window glass 8 = 40 with Halo 2's sky outdoor ambient colour,
  emissive quality 0.25 on the glass; colours from the Halo 2 shaders; other fields as Orbital. The 54 fixture omni
  lights stay. Cost: the panels (135 sq wu) and glass (129) make direct illumination about 7x slower (draft bake 9 min
  vs under 2); a medium bake did not finish its first stage in 61 min and was stopped. Package
  `Elongation_20261127_v8` (draft bake, content ID CB4612C150BDA5E04D65B160AC15048E9F8864CF): shots
  `.local\elongation\run-v8-light` vs `run-belts-3` at the same three points are far brighter, close to the Halo 2
  preview; belt still carries the player (0.49 wu/s), 30 FPS. Scenario/script identical to v7.
- Installed 2026-11-27 (user approved): `Elongation_20261127_v8` in `C:\X360\OpenH3M\content\0000000000000000\4D5307E6\00000002` replacing
  `3longation_20261114_v1` (moved to `.local\pc-port\rollback`). Installed game shows it in the menu and loads it
  (shot `.local\elongation\run-installed`). Xbox 360 console not installed or tested.
