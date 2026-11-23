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
- Glass: Halo 3 has no glass render method group (rmgl); the map cfg "shadergroup" line maps it to a stock Halo 3 glass
  shader (Reflection: Avalanche's side_hall_glass03). Windows and the skylight were empty without it.
- Soft kill volumes: Reach "kill_soft" trigger volumes left out (Halo 3 kills on contact); safe triggers cleared.
- Not converted yet (left out by build_map.sh): sounds, animations, decorators; glass (rmgl) has no Halo 3 group.

## Diagnostic commands
ho2h3 shaderprobe <360 map> [shader]   stock render method layout (TagTool Gen3)
ho2h3 collprobe <360 map> [x y z]      collision / MOPP read back through TagTool; point classification
ho2h3 geomprobe <pak> <360 map> <sbsp> <mesh> [cluster]   source vs converted vertices, parts and indices
ho2h3 objexport <360 map or pak> <folder> [name filter]  structure BSPs as OBJ for Blender (placed instances, materials)
