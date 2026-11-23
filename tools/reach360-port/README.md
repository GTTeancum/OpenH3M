# Reach 360 -> Halo 3 360 level porter (Assembly feature)

User mandate, 2026-11-21: port Reflection from Halo Reach directly from the Reach Xbox 360
cache to an original Xbox 360 Halo 3 cache. No MCC tooling (no MCC caches, no H3 Editing
Kit builds, no MCC-based converters). Build it as a new feature in Assembly, not a bespoke
tool; Inject360 is MCC -> 360 and may donate good parts. Level (geometry, collision,
textures, lighting) comes from Reach, with Reach shaders carried onto Halo 3 360 shader
templates where possible. Weapons, vehicles, equipment and Forge items are stock Halo 3.

Map-agnostic (user, 2026-11-21): other Reach 360 maps will be ported with the same converter.
No map-specific logic in the core; per-map choices (target slot/basis map, Halo 3 substitutions
for Reach weapons/vehicles/equipment, any user-approved exceptions) are inputs (a small per-map
config file).

First source: C:\X360\ISOs\Halo Reach\maps\52_ivory_tower.map (Reach retail 360, big-endian,
encrypted name tables; Blamite reads it with names).

## Status 2026-11-22
Reflection (full Reach scenario, Guardian slot) loads and plays in OpenH3M: Slayer starts, the player spawns
with the stock Halo 3 loadout, the main building section (030) renders lit and textured, collision holds.
Build: `bash tools/reach360-port/build_map.sh tools/reach360-port/maps/reflection.cfg <out map>` (about 85 s).
Proof captures: C:\Programming\GitHub\OpenH3M\.local\reflection360\proofs_2026-11-22.

Open: Halo 3 draws only the structure BSP the camera is in. Reach draws every active BSP; Reflection's
outer shell / roof (001) and distant city, terrain and sky dome (000) are separate BSPs, so from inside
030 they are not drawn and those screen areas show stale frames (Halo 3 never clears colour). 000 and 001
convert and render when the camera is inside them (wireframe capture 6). Needs a design decision
(fold 000 / 001 into 030, for example as instanced geometry). Also open: lifts and elevator (removed
for now), sandbags (Halo 3 has them only as scenery: needs a palette move), sounds, CTF flag spawns.

## Where the code lives
- Porter core + command-line runner, inside Assembly's source tree:
  C:\Programming\GitHub\OpenH3M\.local\asset-tools\src\Assembly\src\ReachPort
  (Assembly clone: XboxChaos Assembly, GPL-3.0, pinned fd14ef3). An Assembly UI page will call
  the same core.
- Layouts: ReachPort\Layouts\Reach and \Halo3 are generated from TagTool's definitions, so field
  names agree across the two games; \Halo3Assembly holds Assembly's validated 360 plugins, used for
  the Halo 3 groups where the generated size disagrees (phmo, zone).
- Generator: C:\Programming\GitHub\OpenH3M\tools\reach360-port\plugingen (TagTool used read-only
  as the layout reference). Output also kept in tools\reach360-port\plugins-generated.

Layout validation (generated vs Assembly plugin base sizes): Reach 127 match / 45 differ; Halo 3
124 match / 2 differ. All level-relevant groups match (sbsp, Lbsp, sLdT, bitm, rm*, mode, hlmt,
scen, coll, phmo(Reach), sddt, scnr, bloc, efsc, effe, prt3, ligh, wind, cfxs, skya) except Reach
stli and mach and Halo 3 phmo and zone.

## Build (no downloads; packages come from the local NuGet cache)
- Assembly app: packages copied from %USERPROFILE%\.nuget\packages into src\packages
  (packages.config layout). Local fix: Blamite.csproj lacked its Antlr4.Runtime.Standard
  reference (packages.config listed it); added a HintPath reference.
- AssemblyIconLibrary: MSBuild AssemblyIconLibrary.vcxproj /p:Configuration=Release
  /p:Platform=Win32 /p:PlatformToolset=v143
- Assembly: MSBuild Assembly\Assembly.csproj /t:Build /p:Configuration=Release
  /p:FrameworkPathOverride=<nuget>\microsoft.netframework.referenceassemblies.net48\<ver>\build\.NETFramework\v4.8
- ReachPort: dotnet build -c Release src\ReachPort\ReachPort.csproj

## Commands (ReachPort.exe)
- inventory <map> [out]   tags reachable from the scenario, by group
- dump <map> <group> <name>   field dump through the porter's layouts
- res <map> <group> <name> [dir]   a tag's resources: definition, fixups, page bytes
- geom <map> <group> <name>   render geometry buffers (GEOM_VERTS=1 prints raw first vertices)
- port <reach map> <h3 basis map> <out map> [--salt f] [--stock-dir d] [--substitute a=b] [--skip k]
       [--set "grp:tag|Block[i]/Field=grp:tag"] [--set "grp:tag|Block=empty"] <grp:tag>...
- graft <basis> <donor> <out> <grp:tag>...   copy stock Halo 3 tags unchanged
- tags <map> <group>   tag names of a group
- zonecheck <map> <grp:tag | 0xresource>...   zone-set activation of a tag's resources
- zonebsps <map> <scenario>   one BSP zone per scenario BSP (build step 3)
- ressizes <map> [first]   per-resource type, parent, page flags and running unique-page total

## Findings
- 2026-11-22 (afternoon) missing level geometry:
  - 26 of 030's materials (and others) are Reach shader_custom (rmcs); Guardian has no "shaders\custom" render
    method definition, so they got no template and Halo 3 skipped those surfaces (floors, ceiling grates, window
    frames). The porter now copies missing stock definitions (custom from Construct, foliage, water) and their
    templates from the stock maps.
  - No instanced geometry was drawn at all (a map with zero instances rendered identically). Halo 3 draws a
    cluster's instances from its cluster mesh's "Instance Buckets" (stock Guardian: every cluster mesh has them);
    TagTool fills them from Reach's Cluster To Instance Group Spheres -> Instance Group To Instance Spheres
    (ConvertInstanceBucketsReach). ClusterMopps.cs does that, plus any instance whose box overlaps the cluster
    (Reach's groups leave some visible ones out). Cluster instanced-geometry MOPPs are rebuilt keyed by instance
    index (Guardian's are; Reach's key instance groups). Draw count from the atrium: 1097 -> 1294.
  - Ruled out (checked against Guardian / converted data): collision-leaf to cluster table, portal planes, PVS
    (forcing all-visible changed nothing), template entry points, material shader presence.
  - Still open: Reflection's lower spawn-room walls and floor (cluster 9 mesh, verified intact by the offline
    renderer, `REACHPORT_FILL=1 wireframe ...`) are not drawn in game; some instances render as long streaks;
    Guardian's per-mesh "Mesh Cluster Visibility" (TagTool PerMeshMoppGenerator) is not generated yet.
  - Fold (Fold.cs, cfg `fold` lines, currently commented out): render-only fold works in the data; folded city
    pieces are not drawn yet. Parked (user: playable areas first).
- 2026-11-22 load-crash chain (each fixed, in order):
  - Reach physics models (phmo) crashed the load: Reach props are now stock Halo 3 objects (cfg `object`
    lines) or still scenery, so Reach phmo is not converted (build_map.sh general rule).
  - Grafted stock tags dangled sound references (sounds are not grafted): cleared with a log line.
  - The zone tag had one BSP zone (Guardian's): `zonebsps` gives one BSP reference and Default / Static /
    Dynamic BSP zone manifest per scenario BSP (ZoneBsps.cs). Not sufficient on its own.
  - The real cause of the 821AA0D8 null read: the resource budget. Halo 3 loads required resources in index
    order; resources past the budget are never loaded. Grafting copied each donor's whole resource page
    (one stock bitmap page is up to 93 MB; four grafted props added 330 MB). Graft now cuts each resource's
    own byte range into its own page (shared.map pages stay referenced). Map resources: 605 MB -> 260 MB
    (stock Guardian 178 MB). Probe hook 821AA0D8 in debug\collision_probe.cpp logs the resource table.
  - Reach soft kill volumes ("don't kill immediately") kill instantly in Halo 3 (no soft-kill flag; TagTool
    relies on Halo Online's Reach patch): left out, hard kills kept; safe triggers cleared as TagTool does.
- structure_bsp_tag_resources flags take Halo 3's value (0x4 on every stock map; Reach 001 had 0x2).
- Reach keeps a level's placed instances, collision and instance definitions in the structure's
  collision resource (structure_bsp_tag_resources), not in the sbsp tag: the sbsp's
  "Instanced Geometry Instances" block is empty, "Instance Names" has the count (Reflection 030:
  1131). TagTool reports the same.
- Resource definitions use internal D3D pointers that Assembly's XML layout format cannot
  express; they are read in code, with the generated resource layouts as reference
  (plugins-generated\ReachResources, \Halo3Resources).

- Fields Halo 3 and Reach name per game ("Object Type / Halo3 Retail" vs "/ Halo Reach", mesh "Flags" vs
  "Flags Reach", "Type" vs "Reach Type") are paired by their unversioned name; enums and flags carry by option /
  bit name from the source value. Without this the Reflection sky scenery read as object type 0 (biped).
- A block's single leftover data field on each side is paired (Reach shader overlay "Function" = Halo 3
  "Animation Function"); an animated shader parameter with an empty curve crashes when drawn.
- Mesh vertex types Reach adds (rigid/skinned compressed, tessellated) become the Halo 3 type the converter
  writes; a mesh marked PRT without a PRT vertex buffer is set to no PRT (Reach sky meshes).
- Reach world vertices are float4 position (w = bitangent sign) + half2 texcoord + normal + tangent (28);
  Halo 3 world is float3 + float2 + normal + tangent + binormal (32). Reach rigid keeps the bitangent sign
  in position w. (TagTool VertexStreamReach / VertexStreamXbox.)
- Stock Halo 3 shaders mostly leave the postprocess entry points / passes / routing empty; Reach shaders
  carry 24 entry points (Halo 3 has 18, same first 18).
- Test status 2026-11-21: Reflection sky (scenery, model, 11 shaders, 17 bitmaps, 3 grafted templates) runs
  as Guardian's sky on the PC port, hidden desktop, no crash.

- Structure BSP assembly (ReachBsp.cs): the sbsp "Geometry" is replaced by its Lbsp's "Geometry" before
  translation (Reach's final cluster/instance meshes live in the Lbsp and its geometry resource); the placed
  instances (Reach: structure_bsp_cache_file_tag_resources "Instanced Geometry Instances", element 0x9C =
  the Reach sbsp layout's) are spliced into the sbsp's own block; after translation instances get their names
  (Reach "Instanced Geometry Instance Names"), Lightmap Texcoord Block Index -1, and a Halo 3 "Bsp Physics"
  entry (geometry shape type 2 over the definition's collision box, MOPP tree shape type 0x1B, refcount 128,
  scale, bsp index = the Lbsp "Bsp Index", shape key = definition index) unless render-only.
- Collision resource (ResDefPort.cs): generic resource-definition translation with the generated resource
  layouts (structs with pointers in the definition, leaf arrays in page data, pointers as resource fixups).
  Reflection 030: 1 collision BSP, 196 instance definitions (159 with collision vertices; Halo 3 bounding
  spheres computed from them).
- Still missing for a playable BSP: Halo 3 cluster "Instanced Geometry Physics" MOPP (Reach keeps
  cluster->instance-group and group->instance MOPPs instead; TagTool's generator shells out to a Havok tool
  that is not available), mesh cluster visibility, structure surfaces / seam edges, lighting (Reach dual-VMF
  lightmaps -> Halo 3 SH sLdT), cluster cubemap positions, decorators, the scenario.
- Test 2026-11-21: Reflection 030 swapped into Guardian's scenario (Lightmap cleared) loads and runs with no
  crash; the player does not spawn (Guardian's spawn points are outside Reflection), so nothing visible yet.

- Reach collision BSPs descend through "Bsp3d Supernodes" (15 axis-aligned planes each) before the ordinary
  nodes; Halo 3 starts at node 0. Supernodes.cs expands them into ordinary nodes (TagTool's
  SupernodeToNodeConverter method, small-BSP encoding), verified by sampling: Reflection 030, 49 BSPs, 116,000
  of 116,000 points give the same leaf. Without it every point reads as outside and nobody can spawn.
  `ReachPort bspprobe <map> <sbsp> x y z` walks a structure's collision tree for a point.
- Halo 3 havok data (TagTool's Reach port does the same): cluster "Instanced Geometry Physics / Mopp Codes" =
  the Reach cache-file "Cluster Mopp Code" chosen by the cluster's "Instance Imposter Cluster Mopp Index";
  instance definitions without MOPP codes get one from TagTool\Tools\mopp.exe generate-collision-mopp
  (MoppGen.cs; 156 of 196 for Reflection 030). Cluster MOPP terminals are instance indices (shape key type 2):
  the game reads that instance's "Bsp Physics", so every instance a cluster MOPP reaches needs one.
- Global material indices are remapped by material name (GlobalMaterials.cs: 201 Reach -> 244 Halo 3, 190 by
  name, 11 by parent).
- Injected resource pages: primary data is written like stock "required" pages (flags 0x11, unknown1 0),
  high-resolution bitmap data like streamed pages (0x1, -1). Ported resources are marked required in every zone
  set (ZoneFix.cs) and their sizes added to the zone manifests' totals.
- Reach keeps three more structure tables in the cache-file resource (Surface Planes, Planes, Edge To Seams);
  they are spliced into the Halo 3 tag's Structure Surfaces / Structure Surface To Triangle Mapping / Edge To
  Seam Edge (same element layouts). Cluster indices into structure palettes Halo 3 keeps in the tag (background
  sound, weather, atmosphere, camera fx, acoustics) that point past an empty palette are cleared to none.
- Writer check (`ReachPort restest`): stock Guardian with its own collision resource passed through ResDefPort
  and injected as a new resource runs normally (player placed, standing). Guardian with Reflection's converted
  collision resource also loads without a fault.
- Reflection BSP 001 (2 clusters) in Guardian's scenario: no fault; the player spawns, falls and respawns.
- Crash found 2026-11-21 with a diagnostic build (tools
each360-port\debug: collision_probe.cpp hooks 821164D8
  and 82113C48; build_probe via REXGLUE_EXTERNAL_PROJECTS_FILE=probe_build.cmake, all outputs redirected into
  .local\pc-port-probeuild\out; run with run_stock_map.py --build). For an instance contact Halo 3 passes the
  instance "Bsp Physics / Geometry Shape / Model" (0x40) to the surface-material lookup as a model tag; the
  converter had written the scale there (stock maps hold leftovers such as 0 or ~1.0), so a scale of 1.0000005
  became tag 4 (globals), whose material block is empty, and the game faulted. Now -1 (none): the lookup uses
  the structure's collision materials. Reflection 030 then runs on the installed game without a fault.
- Structure MOPP: regenerated from the converted structure collision with mopp.exe (all surfaces in order, invalid
  ones as degenerate triangles so leaf numbers stay surface numbers) and prefixed with a 32-bit re-offset
  (opcode 0x0B) of 0x20050000: stock Halo 3 structure MOPP leaves are shape keys 0x2005_0000 | surface (type 1;
  0x4000_0000 | n are instance keys). Reach's breakable-surface MOPP and key table are dropped.
- Decorators are not converted yet: the converted ones crashed object creation and the camera's cluster setup;
  the structure's decorator list and every cluster's decorator grids are dropped together.
- Runtime decals get Reach's scale (vector2 -> Halo 3 uniform scale). Their palette index refers to the
  scenario's decal palette, so they are only valid once the Reflection scenario is ported; in Guardian-scenario
  tests they and the clusters' runtime decal counts are cleared.
- Guardian-scenario tests must also clear Guardian's Scenario Safe Triggers (players outside it die at once:
  "You fell to your death"), Scenario Kill Triggers and Soft Ceilings.
- Symbolised crashes: the probe build links a PDB (.local\pc-port-probeuild\out\halo3mp.pdb); `llvm-symbolizer
  --obj=<that halo3mp.exe> <0x140000000 + rva>` gives the generated source line, whose comment is the guest
  instruction.
- Lighting (ReachLightmap.cs, tools
each360-port\lmconvert): each Reach Lbsp becomes a Halo 3 sLdT "Lightmaps"
  entry (same layout by name: cluster / instance lighting tables, render-geometry copy, the two lightmap bitmaps).
  The lightmap textures are converted with TagTool's own ReachLightmapConverter (dual-VMF -> linear SH, 4 coefficient
  maps x 2 DXT5 layers + 2-layer intensity, five scales; lmconvert writes them, `port --lightmaps <dir>` uses them)
  and written like stock Halo 3 lightmaps (2D array, one level, DXT5, slices tiled and stacked, fetch 0x1A200154,
  Coefficients Map Scale 0-4 from the converter). Entry flags 7. Reflection 030: 1792x1792 (26 MB SH + 6 MB
  intensity); 000: 256x256. Static per-vertex lighting and instanced-geometry light probes follow TagTool's documented
  steps (see "Documented baseline" below): lmconvert writes <lbsp>.spv.bin / .probes.bin, GeometryPort swaps the
  converted per-vertex buffers in (Halo 3 format 6, stride 0x14), ReachLightmap links Halo 3 "Vertex Buffer Index" to
  Reach "Vertex Buffer Index Reach", keeps the cluster per-vertex links, and writes the probes.
- Surface -> triangle links repacked (Reach (triangle << 12) | cluster -> Halo 3 triangle, cluster halves); 5,856
  of 35,078 point at triangles above 65,535 (mesh splitting still to do).
- Status 2026-11-21 15:30: Reflection 030 runs in Guardian's scenario with its converted lightmap; with a stock
  glowing shader on every material the whole arena geometry draws, so geometry and drawing work. With the real
  shaders it is black: the lighting values do not reach the surfaces yet (open: lightmap texture coordinates /
  sampling or encoding). Object light probes are still zero (Reach VMF probes not yet converted to Halo 3 SH).
  The lobby cluster (7) view still does not clear.
- Status 2026-11-21 evening: Reflection 030 renders lit and textured. The black surfaces were every shader float
  constant arriving as zero: Reach names the four floats "Constant a/b/c/d", Halo 3 "Constant" (vector3) + "Constant w",
  so the name matcher dropped them. Translator.Match now carries a block's remaining unmatched float fields when both
  sides cover the same contiguous span.
- Shader animation routing follows TagTool (ShaderFunctionHelper.GetAnimatedParameters / BuildAnimatedParameters):
  routing entry = register (u16), template parameter index (u8), function/overlay index (u8); one pass per valid
  Halo 3 entry point. Copying the template's routing instead read past the overlay block (guest fault 82183020).
  Gap: TagTool generates new templates for Halo Online; on 360 only existing Halo 3 templates exist, so a Reach
  parameter missing from the chosen template is not animated (logged "not in the Halo 3 template").
- Reach-only shader groups: `--substitute grp:reach=grp:stock` may change group (rmgl -> rmsh) and grafts the stock
  tag from the stock maps; references get the new group code (Translator.GroupOverride). Reflection uses TagTool's
  default glass, levels\dlc\sidewinder\shaders\side_hall_glass03 (maps\reflection.cfg).
- Camera fx (cfxs) from Reach: anti-bloom and bloom intensity set to "use default" (TagTool's Reach rule).
- Scenario: maps\reflection.cfg (per-map choices: basis, Reach -> Halo 3 weapon/equipment table, spawn objects, glass
  substitute) and scenario_sets.py (map-agnostic) move the basis scenario's spawns / weapons / equipment onto the
  Reach placements and disable the rest (palette index -1).
- Debug wireframe (probe build only, tools\reach360-port\debug): `--d3d12_debug_wireframe=true` draws every
  depth-tested draw as white wireframe with the game's culling intact; colour targets are cleared to black per frame
  (Halo 3 never clears them, which is also why uncovered screen areas show stale frames in normal rendering).
  `--d3d12_debug_draw_count=true` logs scene draws per frame; `--d3d12_debug_draw_log_frame=N` logs one frame's draws.
  Culling verified in Reflection: 16 draws facing a lobby wall, 178 lobby facing the atrium, 273 in the atrium.

## Documented baseline (user instruction 2026-11-21: follow it; stop and report where it has a gap)
- Reading Reach: Reclaimer (Gravemind2401/Reclaimer), Resources\HaloReachVertexBuffer.xml and HaloReach\*.cs.
  Checked: vertex formats (world, rigid, rigid compressed 0x1C/UDecN4), instance -> mesh / compression indices,
  index ranges. All agree with ReachPort.
- Converting Reach to a Halo 3-family engine: TagTool (TheGuardians/TagTool, master ce2dc6a), Porting\Gen3\
  PortingContextGen3.Lighting/Bsp/Shader/Scenario.cs, Lighting\VmfConversion.cs, Shaders\ShaderFunctions\
  ShaderFunctionHelper.cs, Geometry\RenderGeometry\VertexStreamXbox/Reach.cs. Local copies (reference only):
  .local\reference\tagtool. Its target is Halo Online (PC, ElDewrito with Reach compatibility patches), so
  engine-specific steps (CompatibilityFlags Reach, generated templates, per-mesh MOPPs) do not carry to 360.
- A finished TagTool conversion of Reflection for ElDewrito 0.7.1: "Reach Advanced Multiplayer" (AMP Collective,
  dewsha.re mod 242), .local\reference\eldewrito-reach-amp. Read with tools\reach360-port\pakread (TagTool's
  ModPackage reader; package-owned tags only, no ElDewrito base cache needed).
- Test helpers used: scratch scripts ran `port` with `--set` edits that swap the BSP into Guardian's scenario,
  move Guardian's spawn scenery to Reflection's spawn positions, and run `run_stock_map.py` with the
  map-benchmark probe (it logs "placed ..." only when a player unit exists).

## Architecture
1. Read Reach 360 tags through Blamite with the generated Reach layouts.
2. Convert in memory to Halo 3 360 tag layout and Halo 3 360 resource formats: render geometry
   (world vertices, index buffers, mesh/part limits, cluster splitting), structure/collision BSP
   and MOPP, static lighting (Reach VMF -> H3 SH), Reach rm* materials -> H3 360 templates by
   parameter, Reach 360 bitmaps (already Xenos tiled) re-headered.
3. Write with Blamite's TagContainerInjector (tags, data blocks, resources, pages) into a copy of
   a stock H3 360 map; scenario rebuilt on that map with H3 gameplay objects.
4. Cache integrity (page CRC, salted SHA-1, header digests) - reuse Inject360's Integrity.
5. Verify unattended in the PC port (hidden desktop) before handing anything over.

## Prior art (MCC-sourced, logic reusable, readers not)
tools\warlock-conversion\MAP-CONVERSION-BATCH.md (Reflection sections) and
snapshot\tools\reach_*.py: mesh split, cluster split, VMF->SH lighting, collision/MOPP bridge,
water buffers. Blockers recorded there: no H3 bump-wave water template; full cache assembly
never finished; black-screen runtime test.
