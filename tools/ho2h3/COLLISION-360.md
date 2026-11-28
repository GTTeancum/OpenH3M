# Halo 3 360 collision, as the game code does it

Read from the Halo 3 Mythic `default.xex` (title 4D5307E6, media 00D91BBA; image base 0x82000000; unpacked with
`C:\X360\xextool.exe -eu -cu`, disassembled with capstone). Addresses are guest addresses. Status markers:
**read** = the routine was disassembled and followed; **traced** = confirmed in the running game (PC port, which runs the
same code, `--halo3mp_collision_trace=true`, see "Trace" below); **open** = not read yet.

Emulations of these routines live in `CollCheck.cs` (`sphere360`, `vector360`, `refcheck`, `linecheck`, `solidstats`,
`renderbsp`) and were checked against stock Guardian before being used on converted maps.

## Data layouts used by the code (360, big-endian)

Structure BSP tag (`sbsp`, TagTool H3 layout; the code reads these offsets directly):

| offset | field | used by |
|---|---|---|
| 0x004 | ImportVersion | cluster piece walk chooses its route on it (>= 3: cluster MOPP; < 3: instance buckets). Stock maps: 8. ho2h3 maps: 2 |
| 0x030/0x034 | Leaves (1 byte each) | leaf -> cluster: `lbzx [sbsp+0x34][leaf]` |
| 0x054/0x058 | StructureSurfaces | collision surface -> render part (lighting/decal side, 0x8216E9A0) |
| 0x0B4/0x0B8 | Clusters (0xDC each) | |
| 0x0F0/0x0F4 | PathfindingData | element 0's +0x54/+0x58 per-instance table gates AI-path queries (query flag 0x40) |
| 0x1B0/0x1B4 | InstancedGeometryInstances (0x78 each) | |
| 0x2E0 (+0x8) | Geometry meshes (0x4C each) | mesh +0x34/+0x38 = instance buckets (0x10 each; +4/+8 = instance index shorts) |
| 0x37C | CollisionBspResource | |

Cluster (0xDC): +0x74 embedded Havok MOPP BV-tree shape (vtable called at +0xC), +0x90 cluster MOPP code count, +0x9C
mesh index (short).

Instance (0x78): +0x00..0x33 scale + matrix, +0x34 definition index (short), +0x36 flags (short; 0x2 = never collides
with vector tests, 0x4 = skipped by queries with flag 0x400), +0x40 world sphere centre, +0x4C world sphere radius.

Instance definition (0xB8, in the collision resource): +0x14 CollisionInfo (collision geometry, 0x60), +0x50 = its
surface count, +0x74/+0x78 RenderBsp (used instead of CollisionInfo when the piece query has flag 0x10), +0x98/+0x9C
SurfacePlanes, +0xA8 Planes, +0xB0 mesh index.

Collision geometry (0x60): +0x04 3D nodes (8 bytes), +0x10 planes (16), +0x1C leaves (8), +0x28 2D references (4),
+0x34 2D nodes (16), +0x40 surfaces (12), +0x4C edges (12), +0x58 vertices (16).

- 3D node (64-bit): bits 40..63 front child, 16..39 back child, 0..15 plane. The plane is used sign-extended and
  unmasked (`extsh`, times 16): node planes must not carry bit 15. Child with bit 23 set = leaf (`& 0x7FFFFF`);
  0xFFFFFF (-1) = solid.
- Leaf: +0 flags (bit 0 = contains double-sided surfaces), +2 2D reference count, +4 first 2D reference.
- 2D reference: +0 plane (bit 15 = back side), +2 2D node root.
- 2D node: plane (i, j, d), +0xC left child (d <= r / d < 0), +0xE right child (d >= -r / d >= 0); bit 15 = surface leaf.
- Surface: +0 plane (bit 15 = negated), +2 first edge, +4 breakable index (-1 none), +6 / +8 breakable bits, +0xA
  flags byte (0x1 two-sided, 0x2 invisible, 0x4 climbable, 0x8 breakable).
- Edge: start, end, forward, reverse, left surface, right surface. Walking a surface's ring: if the edge's right surface
  is this surface, take (end vertex, reverse edge), else (start vertex, forward edge).

## Sphere test - collision BSP (read)

`0x822C7E08` (entry) -> `0x822C7EB8` 3D walk -> `0x822C82E8` 2D walk -> `0x822C83C8` surface. Results: surfaces (+0),
edges (+0x804), vertices (+0x1008), leaves (+0x180C), 256 each.

- 3D walk keeps a stack of node planes passed: `p` for the front child, `p | 0x8000` for the back child (straddling
  both). In a leaf, a 2D reference is used only if its plane field (with bit 15) equals a stack entry.
- Projection: axis = largest normal component; flag = (reference bit 15) != (normal[axis] > 0); table at 0x8203B12C
  gives the two coordinates. Radius padded by 0.0625 by the caller.
- Surface: skipped if breakable and destroyed. Hit if any ring vertex is within the radius, any edge is within it
  (0x820AEE78), or the projected point is inside (every edge cross product >= 0).

## Sphere test - world (read)

`0x8229E940`: per active BSP, the structure sphere test, then for each structure leaf touched: cluster = leaf table
byte; the cluster's mesh instance buckets; each instance: dedupe (0x820C0950), definition has surfaces, optional
pathfinding gate, world sphere overlap, transform into piece space (0x82102468), piece sphere test. Contact planes are
collected by 0x8229E208.

## Vector (line) test - collision BSP (read)

`0x820AE3B0` (entry; r3 = BSP flags) -> `0x822C8890` walk -> `0x822C8C80` leaf surface -> `0x820CA728` 2D point.

- Walk: parametric segment, splits at node planes (near side first), records each leaf crossed.
- Leaf type: solid (-1) = 3, leaf flagged double-sided = 2, otherwise open = 1. Start type 0.
- **A surface is only looked for at a transition:** flag 0x1 and open/double -> solid (test the previous leaf);
  flag 0x2 and solid -> open/double (test this leaf); not flag 0x4 and double -> double. Open -> open tests nothing.
- Leaf surface: the 2D reference whose plane (`& 0x7FFF`) equals the crossing plane; 2D point lookup (d >= 0 right).
- Hit rejected if the surface is invisible and flag 0x8 is set, or breakable and flag 0x10 is set.

Consequence: a one-sided surface is only hit when the space behind it is solid. Halo 3's builder (TagTool
CollisionBSPBuilder's port of the tool algorithm: a region holding only used back faces becomes solid) produces that;
Reach trees carried by Halo Online often do not. Stock Guardian: every piece with one-sided surfaces has solid space,
every piece without solid space is fully two-sided; line test misses 0.2% of sample points (edge effects).

## Vector test - placed pieces (read, traced)

- World test `0x820AD3E0` (about 45 callers): structure test, then for each structure leaf crossed: cluster (leaf
  table) -> `0x8229C388`; then a second cluster list from `0x820ABE50` (open: what it is).
- `0x8229C388` (needs query flag 0x8): ImportVersion >= 3 -> `0x820AE8E8`: requires the cluster MOPP (+0x90 > 0),
  Havok ray cast over the cluster's MOPP (+0x74 shape), callback `0x820C0890` (vtable 0x82001F88) gets shape key =
  instance index -> dedupe -> piece test. ImportVersion < 3 -> the cluster mesh's instance buckets -> piece test.
- Piece test `0x820C0B00`: instance flag 0x2 -> skip; flag 0x400 and instance flag 0x4 -> skip; definition surfaces > 0;
  flag 0x40 pathfinding gate; segment vs world sphere; segment into piece space (0x820AF8F0 / 0x820AF9D0); flag 0x10 and
  RenderBsp present -> RenderBsp instead of CollisionInfo; BSP vector test.
- **Traced (Sword Base, drop at -116.687, 36.371 from z 27):** the game tested cluster 7's pieces with query flags 0x1809,
  0x4809, 0x4819 and BSP flags 3 and 9 (9 = ignore invisible surfaces). Walkway piece 824 was tested about 70 times in
  the first two seconds and never hit; glass 19 and invisible ramp 301 were hit some of the time, wall piece 674 often
  under 0x4809. The player still fell to the floor (camera 22.63).

## Havok side of placed pieces (read, H3 Editing Kit sapien.exe x64, RTTI names)

- `c_cluster_collision_instanced_geometry_shape` (vtable rva 0xFCDE28, container vtable at +32, 0xFCDE70),
  wrapped by `c_cluster_collision_instanced_geometry_mopp_bv_tree_shape` (0xFB6C60): one per cluster.
- Child shape for key k (container getChildShape, rva 0x6B7BF0): asserts k < instance count, builds a
  `c_instanced_geometry_shape` (vtable 0xFCDFF0) holding the structure BSP and the instance index (key = instance index).
- `c_instanced_geometry_shape` has only: getAabb (0x6B7FA0: instance -> definition -> collision geometry bounds, plus the
  render BSP if present, through the instance transform), castRay (0x6B7AB0: asserts
  `instance_index_from_key(body.getShapeKey())==m_instance_index`, hands the ray to the collector), and an
  "unreachable" slot. No convex/support functions: Havok cannot run contact agents against it; it serves ray casts and
  AABB queries only. Ray hits go to `c_instanced_geometry_ray_hit_collector` (vtable 0xFB6D28), which runs Bungie's
  collision BSP vector test on the piece.
- On the 360 the same route is `0x820AE8E8` -> callback `0x820C0890` -> piece test `0x820C0B00` (above).

## Placed-piece physics at load and in Havok contacts (read, 360)

Tag layout of an instance's `bsp physics` element (0x70, TagTool CollisionBspPhysicsDefinition): +0x00 geometry shape
(vtable +0x00, type +0x0C, container vtable +0x10, AABB centre +0x20, AABB half extents +0x30, model +0x40, geometry
pointer +0x44, structure BSP index +0x48, shape type +0x49, key +0x4A, scale +0x4C), +0x50 MOPP BV-tree shape (vtable,
type +0x5C, child container +0x60/+0x64, MOPP code pointer +0x68, scale +0x6C).

- Structure BSP load, `0x821D14E8` (function table 0x82063280): (1) every instance definition's MOPP code block
  (+0x80) fixed up (0x82106850); (2) every instance with a bsp physics element: `0x82274180` writes in place only the
  geometry shape's vtables (0x82040C24 / 0x82040C44), Havok type 2, geometry pointer (+0x44 = definition +0x14), the MOPP
  shape's vtables (0x8200138C / 0x820150F8), type 0x1B and MOPP code pointer (definition +0x80 element). **AABB, scales,
  BSP index, shape type and key are used exactly as stored in the map** (stock values are written by the tool's
  post-process, sapien 0x45E85B / 0x6B8950 / 0x6A4A80: AABB from the definition's collision vertices, scale stored as
  0 when exactly 1); (3) every cluster: `0x822742A0` builds the cluster shape only if the cluster MOPP count
  (+0x90) > 0: vtables 0x82040CE8 / 0x820011A8 at +0x48, hkpMoppBvTreeShape at +0x74 over the cluster MOPP.
- Cluster shape child (`0x820C07D8`): a ray-only instanced-geometry shape (vtable 0x820022E4, structure BSP + key);
  its other container slots trap. Clusters serve ray casts (0x820AE8E8 route).
- Contact expansion `0x82270F48` (function tables 0x820013DC, 0x82066008): takes shape keys whose top three bits are
  0x40000000 (instance = low 16 bits; stock cluster MOPP leaves hold plain instance indices, so the tag bit is added at
  run time - converted maps match stock here); skips definitions with more than 0x2000 surfaces; builds the instance
  transform (0x82113120); queries the instance's own MOPP shape (bsp physics +0x50, vtable slot 9 = `0x82114A08`) and
  re-keys hits as 0x60000000 | surface << 16 | instance.
- `0x82114A08` (MOPP shape query): scale +0x6C == 0 means unscaled (no division); otherwise the query box is divided by
  it. Converted maps store 0: harmless.
- Geometry shape child (surface) `0x82270B78` -> `0x82115768`: shape type 2 and key < 0x2000 -> breakable check keyed
  0x60000000 | surface << 16 | instance (uses stored BSP index +0x48 and key +0x4A); surface shape takes scale +0x4C,
  and a scale of exactly 0 leaves vertices unscaled. Converted maps store 0: harmless.
- Geometry shape getAabb `0x822712F0`: stored centre +0x20 and half extents +0x30 through the transform. Converted maps
  store zeros (stock: filled). Which Havok paths call it for placed pieces: open.

## Root cause of "walkways have zero collision" (2026-11-24)

The player is a Havok body; its contacts with the level come from the structure BSP's environment body. Its shape is
the environment surface collection with the **structure physics MOPP** (sbsp Physics CollisionMoppCodes) as its BV tree
(sapien 0x4423B0 / 0x4425A0, built by hkpMoppUtility over the collection's keys). The collection's keys
(sapien 0x6A6240 first key, 0x6A6520 next key, 0x6A5EA0 child shape):

- `key >> 29 == 1`: structure surface (stock 0x2005xxxx);
- `key >> 29 == 2`: placed piece, `0x40000000 | instance index`, one for **every instance whose definition has at least
  one collision surface**; child shape = the instance's bsp physics MOPP shape under the instance transform; its extent
  in the MOPP is that child's AABB = the bsp physics AABB (+0x20 / +0x30, geometry getAabb 0x822712F0 on the 360)
  through the transform;
- `key >> 29 == 3`: one surface of a placed piece, `0x60000000 | surface << 16 | instance` (what 0x82270F48 produces when
  it expands a placed-piece key through the piece's own MOPP).

Stock maps: Guardian's structure MOPP holds 8856 structure keys + 454 placed-piece keys (479 instances, 25 without
collision); Isolation 12816 + 359. **ho2h3 maps: structure keys only** (Sword Base 3427 + 0): ClusterMopps.BuildStructure
rebuilds the structure MOPP over structure surfaces alone, so no placed piece can ever touch the player. The bsp physics
AABBs are also zero, which would collapse each piece's MOPP entry to a point once entries exist.

This also explains the earlier test where stock Guardian with every cluster MOPP blanked still held the player: cluster
MOPPs serve ray casts only; contacts come through the structure MOPP.

Fix (converter): (1) bsp physics AABB = bounds of the definition's collision vertices times the instance scale (tool
constructor sapien 0x6A4A80; scale stored as 0 when exactly 1); (2) structure physics MOPP over the structure surfaces
plus one primitive per colliding instance (its bsp physics box through the instance transform), keyed as stock. TagTool's
mopp.exe keys primitives by input order only (`--useShapeKeys` is a Havok compiler setting), so the mixed key layout
needs the generated code's keys remapped.

Fix built 2026-11-24 (InstancePhysics.cs box rule, ClusterMopps.BuildStructure placed-piece entries, MoppRekey.cs):
Sword Base structure MOPP 3427 structure + 1368 placed-piece keys. Drop test at (-116.687, 36.371) from z 27 (glass
atrium ramp, surface z 24.49): every earlier build fell to the floor (camera 22.63); fixed build holds (camera 25.14 and
25.09 in two runs), and the look-down capture (`--halo3mp_benchmark_look_down=true`, PC port developer option) shows the
player on the glass panel with the floor below. A second point (-126.506, 27.218 from 28.5) was inconclusive (the
player was moved about 24 units from the point within a second, as on a respawn).

## Player movement (in progress)

- Biped movement is `c_character_physics_component` (character_physics.cpp, mode dispatch around sapien 0x48FC90..
  0x4920A0) with per-mode files; ground mode (character_physics_mode_ground.cpp, sapien 0x4B4DF0..0x4B7700) works with
  contact points, clip planes (k_maximum_clip_planes_count) and a ground plane.
- Bungie's "collision features" (collision_features.cpp, sapien 0x663190..0x6666E0: spheres, cylinders, prisms built from
  surfaces, edges and vertices near a volume) are the volume query family; 360 counterpart of the gather is the world
  sphere test `0x8229E940` (contact planes via 0x8229E208). Which of these ground mode calls: being established from the
  call graph.

## How shipped Halo 3-engine levels author collision (2026-11-27)

Source ASS files in the kit (`.local\h3ek-source\data\levels\multi\s3d_sky_bridgenew` and `s3d_reactor`,
`*.original.ass`, professionally authored for the H3 MCC engine), classified by material symbol (world-space faces;
"step riser" = near-vertical face 0.08-0.5 tall):

| | Sky Bridge tris | risers | Reactor tris | risers |
|---|---|---|---|---|
| render only `!` | 796781 | 670 | 561856 | 1719 |
| collision only `@` | 53018 | 6 | 91254 | 144 |
| render + collision | 42336 | 4 | 110800 | 12 |
| sphere collision only `*` | 288 | 0 | 2191 | 0 |

Steps are drawn, not collided with: the detailed meshes are render-only and a separate, much simpler collision-only
mesh (ramps over stairs, flat ledges) is what tool builds the collision BSP, physics MOPP and pathfinding from.
Sphere-only `*` surfaces (players and vehicles collide, projectiles pass) are used sparingly. Reflection's converted
collision instead carries the Halo Online collision as-is (030: 3435 step faces) with Reach's invisible walking surface
over part of the stairs and generated wedges (Ramps.cs) over the rest. Classifier: scratch `asscls.py` (ass_io).

## Reflection in the Reach Editing Kit (HREK, 2026-11-27)

Reach's own Reflection is `levels\multi\52_ivory_tower` (tags extracted from HREK.7z into `.local\asset-kit-hrek`).

- No level source is recoverable: HREK `tool extract-import-info` on the BSP reports the import files were never zipped
  into the tag ("legacy .gr2 import process").
- Bungie authored dedicated collision pieces (BSP 030 instances, flags from `tool export-tag-to-xml`):
  `030_cover_walking_surface` (stair cover, collidable + seam colliding), `physics_collision_only`,
  `rail_sphere_collision_only`, `fountain_physics_collision`. These are Reach's equivalents of H3's collision-only `@`
  and sphere-only `*` geometry. Every other piece is flagged either "collidable" or "render only"
  (030: 375 collidable, 296 render only, 224 render only planar; 000: 1128 render only, 118 collidable).
- Reach placed-piece physics is Havok convex pieces (`tool structure-dump-instance-physics-stats`: poly counts per
  instance; BSP content policy "convex decomposition enabled"), not Halo 3's per-surface collision BSP.
- Water (koi ponds, fountains, waterfall) is render geometry with water shaders (`raw water append` data), the same
  concept as Halo 3, where the tool builds water from water-shader geometry.
- `tool export-structure-mesh-obj` writes one unlabelled mesh to stdout (no materials or pieces): not usable as source.

The established route for Reach levels is Reach tags -> Foundry -> Blender -> H3EK tool (REACH-CONVERSION-PROCESS.md,
Battle Canyon rebuild), which keeps these markings as H3 material symbols and lets the H3 tool build collision, physics,
pathfinding and water.

## Open

- Which queries move the player, and what the movement code does with hits (why hits on 19 / 301 / 674 did not stop
  the fall). Not read.
- What else ImportVersion changes (only the cluster walk branch is known).
- `0x822C8EE0` (extra check on the double-sided transition), `0x820ABE50` (second cluster list).
- The official H3EK tool's own tree build (only TagTool's port read).
- Whether the drop spot is on a walking surface of 824 (its floor faces are mostly hittable per `linecheck floors`).

## Trace

Developer build of the PC port (`C:\X360\ISOs\H3M\.local\OpenH3M-source\halo3mp\src\collision_trace.cpp`, developer
builds only, off by default): wraps 0x820AD3E0, 0x8229C388, 0x820C0B00, 0x820AE3B0 and logs aggregated calls once a
second as `[collision-trace]` lines. Benchmark points must be inside the port's source folder
(`...\OpenH3M-source\.local\map-benchmarks`).
