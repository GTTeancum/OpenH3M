# Reflection rebuild from the Reach Editing Kit (2026-11-27)

User direction 2026-11-27: Reflection's stair/ramp/pond/ledge collision must come from Bungie's own authoring, built by the
official Halo 3 tool ("No bespoke stuff. Figure out from HREK"); loaded from the kit files on this PC (no download).
Replaces the ho2h3 (Halo Online cache) route for this map, including its generated stair ramps (tools\ho2h3\Ramps.cs).

Source: Halo: Reach `levels\multi\52_ivory_tower` (Bungie), tags extracted from the official HREK.7z into
`C:\Programming\GitHub\OpenH3M\.local\asset-kit-hrek`. Findings: `tools\ho2h3\COLLISION-360.md` (HREK section).

## Steps (all outputs in `C:\Programming\GitHub\OpenH3M\.local\reflection-rebuild`)

1. `python launch.py import_reach.py` - unchanged Foundry 1.9.19 (portable Blender 5.2.3, both in the earlier workspace
   `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\halo4-to-h3\upstream`) imports the scenario: 3 BSPs, 2904 objects,
   926716 polygons, 13 water surfaces, 35 portals. Source tags unchanged. -> `reflection-reach-source.blend`.
   Bungie's collision authoring arrives as Foundry face modes: `030_cover_walking_surface` (354 faces) and
   `rail_sphere_collision_only` (395) sphere-collision-only, 39 pieces with proxy collision, render-only faces, water.
2. `python launch.py prepare_h3_scene.py 1600 -- 030 --instance-materials m52_bamboo_trim_zen` - Battle Canyon's
   translation (tools\stock-h3-audit\prepare_h3_authoring_scene.py): Foundry transform back to game units, instance policy
   prefixes, proxy collision as '@' collision children, face modes as H3 material flags; unchanged General-101 exporter
   (81e86bf) writes `reflection_030.ass`.
   - Halo 3 limits a cluster's structure section to 32767 vertices (Reach does not): the first import failed with
     cluster 16 at 43198. The bamboo trim (26000 vertices of the structure) is the decorative detail: its visible faces
     become 56 render-only instances (24-unit area groups), and the structure keeps the same faces as collision-only, so
     the collision is Reach's. Trim faces that were render-only in Reach get no collision. (As collidable instances the
     open trim pieces raised one error category each and the tool asserted "too many error report categories".)
3. Copy the ASS to `.local\h3ek-source\data\levels\test\reflection\structure\` and run `tool structure` there.
   Per-vertex (PRT) instances need a Direct3D device, which the private desktop lacks (assert compute_prt.cpp #64
   g_device_9): run tool windowless on the normal desktop (CREATE_NO_WINDOW), as bake.py does.
4. `python reach_gameplay_to_h3.py <scenario.xml> levels\test\reflection\reflection.scenario <sky>` - multiplayer type,
   sky, Reach's 74 initial spawns -> starting locations, 147 respawn points -> stock H3 respawn points (TagEdit; its
   write guard now includes `levels\test\reflection\`). Weapons and game modes: not yet.
5. Draft bake (`tools\map-review\speed-review\bake.py ... reflection_030 draft`), then cache build and 360 conversion as
   for Elongation (`.local\elongation\rebuild.sh`).

## Open

- Materials: none yet (every material reports "unable to find shader"); Reach shaders to translate (Battle Canyon process,
  REACH-CONVERSION-PROCESS.md section 3). Sky is a stand-in (Guardian's).
- BSPs 000 (city background) and 001 not exported yet; Reach seams dropped (H3 loads BSPs without seams).
- 333 Reach convex physics proxies not used (H3 builds instance physics from collision).
- Water surfaces exported as geometry; their H3 water shader is still to be made.
