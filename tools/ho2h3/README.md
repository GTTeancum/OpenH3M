# ho2h3: Halo Online (ElDewrito) maps -> original Xbox 360 Halo 3

User decision, 2026-11-22: pivot from the direct Reach 360 converter (tools/reach360-port) to a bespoke converter for
the ElDewrito / Halo Online ports of the Reach maps, using any documentation or tools available. This supersedes the
earlier rule that the ElDewrito "Reach Advanced Multiplayer" package is comparison-only.

Source: C:\Programming\GitHub\OpenH3M\.local\reference\eldewrito-reach-amp\reach_advanced_multiplayer_v2.pak
(33 Reach MP / firefight scenarios, TagTool-converted into Halo Online form).

## Why this route
The Halo Online tags are already Halo 3-family: TagTool's Reach port produced instance buckets, per-mesh MOPPs,
Halo 3-style shaders and ODST-style lightmaps. What remains is format work (PC -> 360) and mapping Halo Online's
generated shader templates onto stock Halo 3 360 templates.

## Design
1. Read the package with TagTool (GameCacheModPackage) into TagTool's typed tag definitions.
2. Walk the scenario's dependencies. Package-owned tags are converted; base-cache references (Halo Online's own
   stock content: shader definitions, default bitmaps, stock objects) map onto stock Halo 3 360 tags by name
   (basis map, else another stock map, else dropped and listed). Gameplay stays stock Halo 3 (map cfg, as before).
3. Convert per group on the typed objects: shaders onto stock Halo 3 templates by render method option names;
   ODST-style lightmap BSP tags merged back into the Halo 3 scenario lightmap; render geometry, bitmaps and
   structure resources rewritten for the 360.
4. Serialize with TagTool's TagSerializer (Halo 3 retail, Xbox 360, big-endian) through H3Context into Blamite
   data blocks, and inject into a copy of the basis map with Blamite (compiled in). Post steps (scenario switch,
   BSP zones, Forge palettes, integrity) reuse ReachPort's commands.

## Verified
- TagTool's Halo 3 retail layout matches the 360 data: Reflection's scenario serializes to 0x7B8 bytes and its
  structure BSP to 0x388, the sizes of Assembly's validated Halo 3 360 plugins.
- Reflection depends on 960 tags: 890 in the package, 70 base-cache references (ho2h3 inventory).

## Build
dotnet build tools\ho2h3\ho2h3.csproj -c Release -o .local\asset-tools\temp\ho2h3
(Blamite's sources compile in; TagTool.dll referenced from .local\asset-tools\TagTool.)
bash tools\ho2h3\build_map.sh <map cfg> <output map>   (convert, scenario switch, BSP zones, Forge palettes, zone sets)

## Status, 2026-11-22
Reflection (Guardian slot) loads and is playable in OpenH3M: the player spawns, stands on the floor and carries the
stock Halo 3 assault rifle and HUD (hidden boot test run_ho14). Visible problems left: magenta-tinted surfaces (lighting
not yet checked), harsh sun glare, reflections lost on near-match shaders.

Sword Base (Reach 20_sword_slayer from the same package, cfg tools\reach360-port\maps\swordbase.cfg, Isolation slot)
converted on the first run with no tool changes: 244 materials, 220 of 297 layout objects, 241 ramps; boots and renders
(hidden test run sb3), 2026-11-23.

Batch of 2026-11-23 (private test folder slots): Breakneck (cex_headlong) -> Valhalla/riverworld, Battle Canyon
(cex_beaver_creek) -> High Ground/deadlock, Void (ElDewrito canvas) -> Sandbox, Icebox (Halo Online s3d_turf) -> see below.
- Breakneck: structure collision tree over Halo 3's node limit (51314 > 32767); rebuilt from the same surfaces with
  TagTool's LargeCollisionBSPBuilder (29162 nodes). Boots and renders; one view over the edge showed the sky not drawing
  (before the sky visibility fix).
- Battle Canyon: collision simplified to fit (finding below); boots and renders from the player's view (sky, canyon,
  bases). No Reach health station is in this conversion (checked: none among its converted tags or placements).
- Icebox (Halo Online s3d_turf, cfg icebox.cfg, source C:\Games\ElDewrito\maps\tags.dat): Citadel/fortress slot.
  Needed the base-game source mode and the physics MOPP byte-order fix; boots and renders.
- Void prototype, changes made (user: "take liberties with Void, just mark down what you had to change"): the canvas
  has no floor collision (4 degenerate surfaces), no spawn points and no objects, so void.cfg places a floor of 16
  Forge World flat 5x5 platforms (20 x 20 m, top at z 1.8), 8 stock respawn points and 2 assault rifles + 2 battle
  rifles at the origin ("place" cfg lines, Placements.Extra). Forge menu (user 2026-11-23: Forge World objects only,
  not Sandbox's): the scenery palette is the Reach Forge World building pieces from ElDewrito's forge globals
  (forge_palette cfg line, ForgePalette.cs); teleporters, man cannons, lifts, lights and doors are left to the stock
  Halo 3 gameplay palettes, which stay shared from the basis. Basis scenario is levels\dlc\sandbox\sandbox.

Test copies into a game folder must delete the destination first: stock map files in the test folders are hard links to the
shared install, and a plain copy writes through the link (this overwrote the shared construct.map, 2026-11-23).

## Findings (each one a crash or fault fixed in the converter; all general, not Reflection-specific)
- Shaders: Halo Online option names (HaloShaderGenerator method/option enums) matched to the stock Halo 3 render
  method definition by name; closest stock template chosen (blend mode and alpha test weighted highest), constants
  laid out in the stock template's own order by name, stock option defaults for the rest (Shaders.cs). Reflection:
  168 materials, 41 exact templates; misc "always_calc_albedo" is Halo 3's first_person_never.
- Per-game value fields: TagTool keeps object type, sound class, script type and similar as one field per game
  (GameObjectType16 ...). Reading Halo Online fills only that field; the Halo 3 field is filled by enum member name
  (TagFixups). Without it every object became a biped and the map crashed on load (null function call).
- Scripts: Halo Online script function/type numbering differs from Halo 3; scenario scripts left out for now.
- Container addresses: one window per tag sized to the tag (fixed 16 MB windows wrapped 32 bits past 240 tags and
  scrambled blocks between tags; symptom: garbage seam records, crash in the seam initializer 0x821C66A0).
- Data references (byte[] / TagData): TagTool writes them straight into its tag stream, not as blocks; H3Context now
  turns each into a block (symptom: every function curve all zeros or missing; crash in the curve evaluator 0x820FA3B0).
- Function curves: byte-swapped field by field to big-endian with TagTool's own parser (TagFunction).
- Level collision: Halo Online stores it as large collision BSPs, absent in Halo 3; shrunk back with TagTool's
  ResizeCollisionBSP (symptom: no collision, null read in the point classifier 0x820AB9F0).
- Mesh part offsets: Halo 3 stores a part's first index and index count in 16 bits, Halo Online in 32. Reflection's
  atrium mesh has 83469 indices, so every part past 65535 wrapped and drew the wrong triangles (long slabs across the
  room; TagTool only warns). Each such mesh's index buffer is rebuilt with parts in ascending size so all start below
  65536 (GeometryConvert.FixPartOffsets). Checked by exporting the converted map to Blender (objexport) and in game.
- Lightmap textures: Halo Online keeps each section's lightmap layer stack as a 3D texture (Reflection 030: 1792x1792x8
  DXT5); stock Halo 3 uses texture arrays (Guardian 1024x1024x8). They were skipped ("not converted yet"), so every
  lightmapped surface was black or garbage. Each slice is now recoded and tiled as 2D, slices concatenated, written as
  an array; control word matches Guardian's (0x1A200154).
- Object layout: ElDewrito keeps a map's multiplayer objects in the map file's built-in map variant, not the scenario
  (Reflection: 301 objects vs 2 scenery + 3 crates). Placements.cs turns each into a scenario placement of the stock
  Halo 3 object (cfg substitutions apply) with position, facing, team, spawn time, game-mode flags and boundary; stock
  Guardian defaults (scale 0, source editor, attach flag 1, item flag 0x100, engine flags 0 = all, neutral items).
  Object type must be set in every per-game field. Reflection: 246 placed, 50 left out (ElDewrito Forge blocks etc.).
- Materials whose Halo Online template is not in the package: the value order is rebuilt from the stock options with the
  same names, Halo Online's shader generator, or the stock order minus surplus entries, accepted only where counts match
  and every value fits its slot (texture transforms vs colours). Alpha-tested templates get the alpha test flag
  (TagTool clears it for Halo Online). Fixes the bamboo leaves (were opaque squares).
- Geometry and collision resources go in always-loaded pages (0x11), as stock; textures stream.
- Mesh cluster visibility: Halo Online leaves most entries empty and the rest in post-Halo 3 MOPP encoding; left out
  (symptom: bad write in 0x82167508). Generating it for Halo 3 is open.
- Physics (player fell through the floor and was "killed by the Guardians"):
  * instance definition MOPPs regenerated with TagTool's MOPP tool (Tools\mopp.exe) for every instance with surfaces;
  * cluster instance MOPPs built over instance world boxes, keys = instance index, plus instance buckets where the
    source has none (ClusterMopps.cs, same rule as ReachPort);
  * structure physics MOPP rebuilt: one primitive per collision surface, keys 0x20050000 + surface index as stock
    Guardian (Halo Online's keys use another layout). Checked by decoding keys (collprobe).
- Cluster instance MOPPs size each instance by its render compression bounds and its collision vertices: collision-only
  pieces (Reflection's invisible stair ramps, empty render mesh) were left out of every cluster MOPP, so stairs had to
  be jumped. Instance buckets skip pieces with nothing to draw.
- Camera effects: Reach's tuning (exposure range -1..2, bloom intensity 0.4) gives heavy glare in Halo 3; Reflection's
  cfg substitutes stock Guardian's camera fx.
- Collision surface facing: Halo Online (from Reach on) marks a negated plane with surface flag 0x80; Halo 3 negates
  through the plane index's high bit. Folded in as TagTool's own builders do (set 0x8000, clear the flag) for the
  structure and every instance: Reflection 5323 surfaces. Without it ramps and edges faced the wrong way (stairs and the
  pool needed jumping). Checked: every surface's winding agrees with its signed plane (stock Guardian: all agree).
- Stair ramps (Ramps.cs): Halo 3 bipeds cannot climb real steps and Reach levels have ramps only in places (Reflection:
  a collision-only "walking surface" instance covers most stairs; 290 of 471 stair treads). Every vertical collision face
  0.08-0.5 tall (more inside map cfg ramp_zone areas) with floor in front, a walkable top behind and no ramp already
  above gets a closed 35-degree wedge, added to the BSP's collision-only instance (its own coordinates) whose collision
  BSP is rebuilt with TagTool's LargeCollisionBSPBuilder. Reflection 030: 299 wedges. Checked: a test player placed on
  an existing ramp rests on the ramp, not the step below. 000 and 001 have no collision-only instance to hold ramps.
- Glass: Halo 3 has no glass render method group (rmgl); the map cfg "shadergroup" line maps it to a stock Halo 3 glass
  shader (Reflection: Avalanche's side_hall_glass03). Windows and the skylight were empty without it.
- Soft kill volumes: Reach "kill_soft" trigger volumes left out (Halo 3 kills on contact); safe triggers cleared.
- Physics model MOPP data (phmo byte array, one 48-byte Havok header + code per MOPP) stays in the source byte order
  unless swapped: header fields to big-endian, code bytes unchanged (TagTool's ConvertHkpMoppData treats the Halo 3
  target as little-endian too). Symptom: read fault in the physics model loader 0x821D00C8 (Icebox's electric cart).
- Sky visibility: Reach (so Halo Online) leaves clusters it judges sky-less at visible sky -1; Halo 3 draws no sky from
  them and open sky shows as hall of mirrors. Stock maps mark every cluster (Guardian 26/26, High Ground 42/43); with a
  single sky every cluster now sees it (Battle Canyon 5 clusters, Reflection 4).
- Level collision over Halo 3's limits even with a rebuilt tree (Battle Canyon: 46178 surfaces, tree 98404 nodes;
  limits 32767): CollisionSimplify.cs fans the surfaces into triangles, simplifies the whole mesh with meshoptimizer
  (the native library TagTool ships; one mesh so no cracks open between materials), re-tags each triangle with the
  most common (material, flags) at its corners, rebuilds edges and surfaces, lets TagTool merge coplanar neighbours and
  build the tree, and keeps the least simplification that fits (Battle Canyon: 56882 -> 12510 triangles, 32221 nodes;
  authorised by the 2026-10-25 Battle Canyon rule; render geometry untouched). TagTool's tree verifier rejects every
  empty leaf (its range test fails on the 0xFFFFFFFF its next test requires), so the tree is taken from the builder,
  checked with empty leaves allowed, and pruned with the builder's own step. Edges a simplified mesh would give three
  surfaces are kept as separate pieces, not dropped (no holes).
- Object layout, map pieces: layout objects with no stock Halo 3 tag of the same name and no cfg substitute (scenery,
  crates, machines, controls) can be converted and placed (Placements.Roots/IsConverted), opt-in with
  HO2H3_VARIANT_PIECES=1: as is, Sword Base's crashed-Pelican gibs hang in mid-air and Reflection gets ElDewrito reforge
  blocks, so they stay left out by default.
- Two-sided collision (TwoSided.cs): Reach stores each two-sided surface as a pair (the surface and a coincident copy with
  the plane negated); stock Halo 3 stores one surface with the two-sided flag (Guardian: 592 two-sided invisible surfaces,
  no copies). The copies are removed and the geometry rebuilt (Sword Base: 1469 copies, 143 geometries). These pairs make
  Reach's invisible "sphere only" walking surfaces over stairs and glass bridges, where the player fell through
  (user play test 2026-11-23). Ramps and rebuilds use the empty-leaf-tolerant tree check (CollisionSimplify.GenerateBsp).
- Forge palette (ForgePalette.cs, cfg forge_palette <forg tag> ; <object regex> ; <block> [; keep_stock]): ElDewrito keeps
  its Forge menu in multiplayer\forge_globals; matching objects are converted and listed in the scenario's sandbox
  block, replacing the stock entries unless keep_stock. Void: 140 Forge World building pieces.
  Display names (ElDewrito's palette names, Halo 3 style) are written into the map's sandbox string list
  (ui\halox\sandbox_ui\strings, every language; ho2h3 addlocale). Budget: cfg forge_budget (Void: 10000, Reach Forge
  World's). Prices and limits: cfg forge_prices, a palette read from the Reach MCC maps (ho2h3 reachpal, read only;
  .local
eferenceorge_world_palette.json, Forge World first, then every Reach MP map). One piece has no Reach price:
  Breakneck's ff_shoring (map scenery ElDewrito made placeable) is priced as Forge World's brace (50, max 300).
- Halo Online base game (tags.dat) as a source: ho_pak may name a tags.dat; tags that exist in stock Halo 3 by name are
  taken from Halo 3 (stock asset policy). The base maps' .map files carry a default map variant whose object indices
  were written against another tags.dat build (Icebox's point at waterfalls and ElDewrito reforge blocks), so it is
  unused by default (HO2H3_BASE_VARIANT=1 to read it); the base scenarios carry their own objects.
- Stock name lookup can skip damaged stock files: HO2H3_EXCLUDE_STOCK=construct.map (the shared construct.map holds a
  Sword Base test build since 2026-11-23). build_map.sh stops when the conversion fails (it used to re-finish the old
  output) and keeps the converter's console output in <output>.convert.txt.
- Leaf -> cluster table (LeafClusters.cs, Halo3Limits.cs): Halo 3 finds the camera's cluster by walking the structure
  collision BSP to a leaf and reading the sbsp Leaves block, so that block needs one entry per collision leaf, in the
  tree's own order (stock Guardian 11305/11305). Every Halo Online source checked matches (Sword Base 3308/3308,
  Breakneck 28538/28538, Battle Canyon 80846/80846). The converter used to rebuild the structure tree (TagTool's
  collision_bsp_check_counts caps 3D nodes and leaves at 32767, so Breakneck's 51314-node tree was rebuilt; the two-sided
  cleanup rebuilt Sword Base's), after which the table could only be approximated (Breakneck: 9594 of 17018 leaves
  guessed by nearest cluster) and the camera landed in the wrong cluster: hall of mirrors and missing pieces (user play
  tests 2026-11-23). Halo 3's own limits are far higher (24-bit node children; stock Sidewinder 92248 nodes / 46686
  leaves, Snowbound 82567 / 44216), so the structure tree is now kept as shipped (Halo3Limits.Fits / Shrink, which also
  keeps the 3D node plane negation TagTool's shrink drops) and the two-sided cleanup leaves the structure BSP alone
  (HO2H3_TWOSIDED_STRUCTURE=1 restores the old behaviour). Every build checks the table against the source's own tree
  and table over the whole map (a point grid plus points on both sides of every collision surface) and logs the count of
  points that land in a different cluster: Sword Base 0 of 2.78 million, Breakneck 0 of 3.15 million, Reflection 0 of
  5.6 million (2026-11-23). If a rebuild is ever unavoidable, the table is rebuilt with the source tree as the oracle and
  the mismatch count is logged as CHECK.
- Visibility data check (ho2h3 viscompare): cluster portals (sides, flags, vertices, and the collision plane each one
  names, compared by value), each cluster's portal list and the scenario's potentially-visible sets, source against
  converted map. Sword Base and Breakneck: identical (2026-11-23), also in the builds that showed the hall of mirrors, so
  the leaf table was the cause there.
- Instance bounding spheres (InstanceSpheres.cs): stock Halo 3 gives every instanced-geometry definition a sphere around
  its geometry (Guardian, all 193 collidable definitions: centre = middle of the render mesh's compression box, radius =
  half that box's diagonal) and every instance that sphere in world space. Halo Online's Reach ports leave the
  definition's sphere at radius 0 (Sword Base: all 439 collidable definitions); stair ramps also outgrew their host's
  sphere. Suspected cause of walkways players fall through (Sword Base) and ramps that change nothing (Reflection),
  user play tests 2026-11-23. Each definition's sphere now holds its render box and its collision vertices.
- Collision check (ho2h3 collcheck <source> <sbsp> <converted map> <sbsp>): every upward-facing collision surface of the
  source, in world space, tested against the converted map's collision the way the collision BSP is walked (3D BSP to the
  crossed plane, 2D BSP of that plane in the leaves on both sides, sidedness). Control run on the source itself first.
  Sword Base as played 2026-11-23: 0 of 44735 surfaces lost, so the data was complete and the fault was in what decides
  whether a piece is tested.
- Two-sided pairs are now removed in place (TwoSided.cs): the source's own tree is kept and its 2D BSP leaves that named a
  removed negated copy name the partner surface; nothing is rebuilt, so nothing fails (Sword Base 2026-11-23: 1650
  copies removed, 0 failures; the old rebuild left 122 pieces unchanged) and the structure's leaf table stays valid.
  HO2H3_TWOSIDED_REBUILD=1 restores the rebuild. Not confirmed to change the Sword Base walkway fall-through.
- Cluster instance MOPPs register each member instance as one primitive through its box's eight corners (was one
  triangle across the box). Not confirmed to change the Sword Base walkway fall-through.
- Model object data (Convert.cs): stock Forge objects' models carry one auto-generated entry (radius = object bounding
  radius, offset = render model bounds centre); converted models now get one. Did not fix the Void Forge crash.
- Drawn duplicates (map cfg "nodraw <sbsp> <instance,...>"): Icebox's merged window copy 1148 duplicates pieces
  1149-1159 at the same place (195.39 vs 195.4 square units); each piece's vertices are compressed against its own
  bounds in the 360 format, so the copies fight. Found with a coplanar-overlap check over objexport's render geometry
  restricted to instances in draw lists (1687 overlapping pairs; the rest are partial overlaps such as turf_build_part_28
  against cluster meshes, still open).
- In-game drop tests (map benchmark points: the player is placed at a point and the camera logged): only valid where the
  player actually falls; placed above a surface the player often stays where placed (camera = point + 0.72), and placed
  inside stacked pieces the player is pushed through. Sword Base (-116.687, 36.371): falls through four stacked walkway
  pieces (glass, sphere-only ramp, solid ramp, wall trim) to the floor at 22.0 in every build so far.
- Simulation definition table (SimTable.cs) - the Void Forge crash, fixed 2026-11-24: Forge creation resolves the item
  through the scenario's simulation definition table (a 12-bit index found by binary search over the 32-bit tag handles,
  comparator a - b: sub_82425660 -> sub_82105770 / sub_8234D568; decoded by sub_824256E0). Halo Online's scenarios convert
  with an empty table (every converted map: 0 entries; stock Sandbox 1580), so every item resolved to -1 and
  forge_object_radius (0x822835E0) read tag -1 (crash at guest address 0x40). The table is rebuilt from the palette, the
  slot's own stock table and the converted simulated groups, sorted by handle as a signed number. Verified with
  trace_loading.py --slot sandbox: stock vehicle and converted scenery items 0 and 4 are created, no crash. Found by
  mapping the crash frames to guest functions through the executable's guest -> host registration table.
- Halo 3 360 collision as read from the game code (layouts, sphere and line tests, placed-piece routes, live trace, open
  items): COLLISION-360.md. InstanceTrees.cs rebuilds placed-piece trees with Halo 3's builder (see there).
- Placed-piece (instanced geometry) collision - what is established (2026-11-24, from the H3 Editing Kit and the 360 game):
  - Test method: one benchmark drop per run (only the first point of a run gets physics; later points stay frozen where
    placed). Stock Guardian walkway (10.306, -0.909) from 17.6: lands at camera 17.18. Every converted map tested
    (Sword Base, Breakneck, Icebox) falls through placed pieces.
  - Official tags (tool export-tag-to-xml on beavercreek.scenario_structure_bsp, .localsset-tools	emp\h3ek-xml):
    instance bsp_physics holds "center"/"half extent" (local box of the definition; written by the tool) and runtime
    slots "structure_bsp_index", "collision geometry shape type", "instance index" (-1/0/-1 in tags; stock 360 caches
    hold bsp index, 2, the instance index). Instance offset 0x50 is "checksum" (TagTool reads it as the upper radius
    bound; InstanceSpheres.cs must not write it). Definitions: checksum, sphere, collision info, render bsp, mopp codes,
    breakable surface sets, (MCC only: small surfaces), large surfaces, surface to triangle mapping, mesh, compression,
    lightmap scale (360 layout 0xB8, TagTool's matches; 360 code reads +0x98/+0xA4/+0xB0).
  - Per-cluster instance collision is built at load (tool.exe 0x92cb80, collision_instanced_geometry.cpp: "couldn't build
    mopp code for cluster #%d, cluster instances won't be collidable"). Children of a cluster's shape = the instances in
    that cluster's render mesh instance buckets (tool 0xb8d260: cluster +0xd8 mesh index -> mesh instance buckets ->
    instance -> definition; counted when the definition has collision surfaces and vertices and its last surface is not
    flagged invalid 0x10). Child bounds come from the definition's collision vertices through the instance transform
    (tool 0xb8cde0/0xb8c7b0), not from the stored bsp_physics box. The stored cluster MOPP is not needed on the 360
    either: stock Guardian with every cluster MOPP blanked (ho2h3 blankclustermopp, copy only) still holds the player.
  - Not explained yet: Sword Base walkway pieces are in their cluster's buckets and still let the player through; the
    360 runtime path may differ from the MCC tool's. Open lead: find the 360 counterpart of the cluster child enumeration
    and narrowphase in the recompiled game (cluster stride 220, mesh index +0x9C, mesh stride 76, instance stride 120,
    definition stride 184).
- Scenario decals project onto collision geometry (Halo 3 decal system flags "use primary collision only", "don't collide
  with instances"; H3EK tool strings). Icebox: 594 of 615 decals lie within 3 mm of a drawn surface; their decal system
  fields (pass, angles, shader options) match stock Halo 3's, so the decals themselves convert correctly.
- Two-sided cleanup only keeps rebuilds whose tree TagTool's builder verifies itself: trees that needed the empty-leaf
  fallback made Breakneck fail to load ("players failed to load content").
- Not converted yet (left out by build_map.sh): sounds, animations, decorators; glass (rmgl) has no Halo 3 group.

## Diagnostic commands
ho2h3 collcheck <src> <sbsp> <360 map> <sbsp> [list]   whole-map collision check (see above)
ho2h3 viscompare <src> <sbsp> <scnr> <360 map> <sbsp> <scnr>   portals / portal planes / PVS, source against converted
ho2h3 points <map> <sbsp> <piece regex | #instance> <count> [slope]   benchmark points on walkable surfaces of pieces
ho2h3 decalcheck <src> <sbsp> <scnr> [out]   which surface each scenario decal sits on (and not-for-render pieces)
ho2h3 decaloverlap <src> <scnr> [out|-] [sbsp]   scenario decals overlapping on one plane (footprint = decal radius x
    scale, projected along the decal's z axis); with sbsp: the clusters' decal ranges. Map cfg "nodecal <scenario> <i,j,...>"
    leaves source decals out and renumbers the BSP clusters' runtime decal ranges (they index the scenario decal block).
ho2h3 physprobe <map> <sbsp> twosided | instdump <name> | defspheres [n] | leafcount   collision / instance data
ho2h3 physprobe <map> <scnr> mpobj [x] | placed | placedump <block> <i,j> | nulltags [min index] | decs   Forge and decal data
HO2H3_RAMP_POINTS=<file> (build): writes a test point on every added ramp (ramp height and bare floor height)
ho2h3 shaderprobe <360 map> [shader]   stock render method layout (TagTool Gen3)
ho2h3 collprobe <360 map> [x y z]      collision / MOPP read back through TagTool; point classification
ho2h3 addr <360 map> <hex address>      tag whose data holds a guest address; "1" lists tag data size by group
ho2h3 physprobe <src> <phmo> phmo | <scnr> sandbox | <regex> bounds <group>   physics shapes, sandbox palettes, render bounds
ho2h3 geomprobe <pak> <360 map> <sbsp> <mesh> [cluster]   source vs converted vertices, parts and indices
ho2h3 objexport <360 map or pak> <folder> [name filter]  structure BSPs as OBJ for Blender (placed instances, materials)
