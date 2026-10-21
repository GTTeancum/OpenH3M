# Forge World / Sandbox conversion

Status (2026-10-21): **Forge Gulch started; offline collision tables serialize,
but metadata/physics integration and containment remain incomplete**.
No candidate map has been emitted or deployed. Existing converted maps and the
host runtime are unchanged. The conversion groundwork below is not validated
in gameplay and must not be described as a working port.

## Source and authorized scope

- Ryno's Forge World - Halo 3, Workshop 3597611181.
- Source: `D:/SteamLibrary/steamapps/workshop/content/976730/3597611181/maps/forge_halo.map`.
- User selected Sandbox (`sandbox.map`) as the replacement.
- Source inspection: zero squads, character entries, placed bipeds or scenario
  scripts; two BSPs, one zone with both active. No placed weapons, vehicles,
  equipment or crates. This is the non-AI blank Forge canvas.
- User excludes custom Forge objects and Reach weapons/vehicles. Use the original
  Xbox 360 Sandbox Forge palette, its prices, limits and Forge budget. It already
  supplies the Halo 3 replacements without redundant Reach menu entries.
- Retain authored terrain, water, lighting and environmental effects. Stock H3
  asset policy still applies. Do not raise engine limits, use a separate runtime,
  overwrite original disc maps, or remove collision to obtain a loadable map.
- Source palette has 34 vehicles, 49 weapons, 19 equipment, 111 scenery,
  9 teleporters, 9 goals and 19 spawners. These counts are not retained targets.

## Hardware and format limits

Microsoft lists 512 MB shared GDDR3, 22.4 GB/s main-memory bandwidth, 10 MB eDRAM,
three 3.2 GHz CPU cores and a 500 MHz GPU:
https://ukstories.microsoft.com/features/xbox-360-launched/

These are whole-console specifications, not available map RAM or a disk-file
size target. A valid port needs measured guest resident memory, renderer/resource
allocations and frame delivery, leaving the original engine's headroom intact.
No RAM/performance compliance claim is made from the current preflight.

TagTool's resource definitions distinguish H3 original from MCC: original H3
has no LargeCollisionBsps field, whereas MCC H3 does. Retail collision planes
and edge links have 16-bit indices; the MCC large format uses 32-bit fields.
References checked against primary source:
- https://github.com/TheGuardians/TagTool/blob/master/TagTool/Tags/Resources/StructureBspTagResources.cs
- https://github.com/TheGuardians/TagTool/blob/master/TagTool/Geometry/BspCollisionGeometry/CollisionGeometry.cs
- https://github.com/TheGuardians/TagTool/blob/master/TagTool/Geometry/BspCollisionGeometry/LargeCollisionGeometry.cs

Main source BSP large-collision counts:

| Array | Count |
| --- | ---: |
| 3D nodes | 187,524 |
| Planes | 99,327 |
| Leaves | 99,039 |
| 2D references | 146,080 |
| 2D nodes | 7,354 |
| Surfaces | 44,461 |
| Edges | 69,737 |
| Vertices | 25,264 |

Exact byte-identical plane deduplication leaves **95,361** planes, still above
65,536 addressable values. Edge count also exceeds the retail index range.
The second/shared BSP uses ordinary collision. The main BSP needs a real offline
collision rebuild/partition, with the associated BSP/instance references,
visibility and residency updated consistently. Casting indices, dropping high
indices, disabling collision or adding MCC large-BSP handling to the engine are
not acceptable fixes. No such workaround was applied.

## Reproduction and early rejection

From `C:/X360/ISOs/H3M/.local/OpenH3M-source`:

```powershell
python -B tools/warlock-conversion/snapshot/tools/preflight_collision_budget.py `
  --source D:/SteamLibrary/steamapps/workshop/content/976730/3597611181/maps/forge_halo.map `
  --report work/forge-world/collision-preflight.json
```

The builder also runs this preflight before allocating/converting a Sandbox
candidate and writes the detailed result into the requested report:

```powershell
python -B tools/warlock-conversion/snapshot/tools/build_scenario_checkpoint.py `
  --project ../.. --slot sandbox `
  --source D:/SteamLibrary/steamapps/workshop/content/976730/3597611181/maps/forge_halo.map `
  --basis ../../maps/sandbox.map --xex ../../default.xex `
  --sound-bank 'D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo3/fmod/pc/sfx.fsb' `
  --decoder ../tools/vgmstream-r2117/vgmstream-cli.exe `
  --output ../forge-world/sandbox-01.map --report ../reports/forge-world-01.json
```

Expected result is explicit rejection at `collision_budget_preflight` and no
output map. Do not bypass this gate. A future collision conversion must replace
this check with validation of its actual transformed output.

## Groundwork retained for the subsequent rebuild

- Multiple BSP/lightmap bindings and BSP-specific decorator resources.
- A restricted two-always-active-BSP residency path. It shares a conservative
  resource union; it does not duplicate payloads. This path has NOT completed
  serialization or runtime validation and is not yet budget evidence.
- Original Sandbox Forge palette/budget retention and no placed gameplay-object
  assumptions checked explicitly, so future source updates fail for review.
- Four-layer terrain binding to the actual four-layer disc shader. Some other
  identically named retail variants only support three layers. Missing native
  specular constants receive documented defaults; all substitutions are reported.
- Budgeted terrain blend masks: use authored mip chains; for BC3 blend maps
  lacking a small mip, resize each linear blend channel independently. Retain
  single-mip inputs up to 1024 pixels; larger masks reduce to 512 pixels.
- Native water template/wave-array substitutions. Terrain/water UV animations
  currently use the existing converter's static approximation. Native object
  probe sampling replaces the MCC-only Eldorado scenario flag.

These shader/lighting/water paths are preliminary, not visual acceptance. The
first build reached the main BSP collision conversion and failed there. Later
stages, shared BSP lighting and actual gameplay remain unverified. Failed builds
reuse the same report and emit no checkpoint; no alternate installation exists.

## Checks and remaining work

Passed: syntax parsing, whitespace checks, two blend-resize regression tests;
the collision preflight accepts the known Warlock, Resuscitation and Prisoner
source collision formats and rejects this Forge World source. These do not
constitute a rebuild/regression gameplay test of the older maps.

Remaining: offline collision reconstruction within retail limits; finish any
subsequent format gaps; validate both BSPs and resource manifests; measure guest
memory against stock maps and original engine allocations; native capture and
correct-content gameplay/Forge checks; install only a valid budgeted candidate
into the existing shared installation. Keep the original source read-only.

## Two-map feasibility check (2026-10-21)

The user names the proposed maps **Forge Gulch** (the Blood Gulch/canyon area)
and **Forge World** (the remaining playable area). Both should retain the whole
visible landscape, with player/vehicle/Forge-camera boundaries preventing access
to the other side. This is a feasibility assessment, not authorization to call
an untested partition complete. The second replacement slot has not been chosen.

`analyze_forge_split.py` reads actual surface edge loops and vertex positions,
then follows the 2D/3D collision references to estimate retained lookup data.
Material names alone are insufficient: gulch talus materials occur outside the
canyon. A provisional intersection of Y <= -20 and X <= 10 covers the main
canyon floor/caves; the complement supplies the other map. The final boundary
needs visual validation and collision-backed containment, including flying
vehicles and Forge movement. This is not a finalized geographic selection.

Surfaces touching the provisional boundary stay on both sides (418 surfaces),
so the estimate does not gain space by throwing away crossing polygons.

| Main-BSP estimate | Forge Gulch | Forge World |
| --- | ---: | ---: |
| Surfaces | 24,973 | 19,906 |
| Edges | 39,364 | 31,255 |
| Retained planes before exact deduplication | 60,956 | 42,206 |
| Exact unique retained planes | 58,796 | 40,296 |
| Planes referenced by signed 2D entries | 22,683 | 18,301 |
| 2D nodes | 3,912 | 3,568 |

Both selections fit the checked 16-bit plane/edge counts. Their 2D reference
planes, surface indices and 2D-node indices also fit signed/flagged index ranges;
a converter must allocate the 2D-referenced planes first and remap every index.
These counts are conservative reference-closure estimates, not serialized valid
retail collision. They exclude new containment geometry and separate instance
and shared-BSP collision. All connected collision, MOPP, visibility and surface
mappings still need consistent rebuilding and validation.

Both complete visible geometry sections successfully converted **in memory**:
20,146,716 + 1,462,562 bytes of retail geometry. All four lightmap arrays also
encoded successfully, retaining authored dimensions. Combined geometry and
lighting payload: **47,823,678 bytes (45.61 MiB)**, plus 85,968 bytes of geometry
control data. This does not include terrain textures, decorators, stock Forge
objects, collision, audio, tags, render targets or engine memory. It does not
prove visual correctness, frame rate or total 360 memory compliance.

Conclusion: the proposed split removes the immediate index-count obstacle
without deleting visible scenery. Retain it as the preferred conversion plan;
do not claim a complete budget fit or working map until both candidates exist
and their complete allocations and gameplay have been checked.

Reproduce (all output remains ignored inside this repository):

```powershell
python -B tools/warlock-conversion/snapshot/tools/analyze_forge_split.py `
  --source D:/SteamLibrary/steamapps/workshop/content/976730/3597611181/maps/forge_halo.map `
  --cut-y -20 --cut-x 10 --report work/forge-world/split-analysis.json
```

No map, executable, source asset or existing installation was changed by this
assessment. Temporary spatial-array data was removed after the final report.

## Forge Gulch implementation (user sketch, 2026-10-21)

The user selected **Forge Gulch first**, still over Sandbox, and supplied a red
curved split on an aerial image. The right-hand canyon/coast is Gulch; the left
side remains Forge World. Full visual scenery remains a requirement for both.
`forge_gulch_boundary.py` now records a world-coordinate interpretation of that
sketch, replacing the rectangular estimate for this candidate. It includes the
Montana/coastline region that the old X <= 10 cut partly excluded. The island,
beach cave and waterfall are on the World side. This is a geographic draft,
not a claim of user-approved exact coordinates or tested in-game containment.

`plot_forge_split.py` draws actual source terrain with the draft line. Null-shader
collision barriers are hidden only in this planning plot. They are not discarded
from the collision selection. The plot is not an in-game capture or visual proof.

`partition_forge_collision.py` performs an actual **in-memory** conversion of the
selected large collision tables into retail big-endian tables. It retains
crossing polygons intact, remaps every table index, assigns signed-reference
planes first, deduplicates only byte-identical planes, translates surface plane
orientation to the retail flag, and repairs vertex incident-edge references.
It also retains all 18 distinct portal planes, including seven additional unique
planes needed by full-world visibility. Original render data is not edited.

Current main-BSP prototype results:

| Table | Serialized count |
| --- | ---: |
| 3D nodes | 116,852 |
| Planes | 60,946 |
| Leaves | 58,732 |
| 2D references | 86,617 |
| 2D nodes | 4,178 |
| Surfaces | 26,147 |
| Edges | 41,161 |
| Vertices | 15,008 |

Table payload is 3,840,948 bytes, excluding resource headers, instances and added
containment. Every retained polygon's serialized vertex loop, material and plane
orientation passed read-back verification. 257 reversed planes were translated.
2,048 deterministic spatial probes through the decoded packed tree agreed with
the source tree's retained-leaf mapping. Four focused regression tests passed.
These checks do not prove collision response, Havok integration or gameplay.

**Do not wire these tables into a candidate yet.** The existing builder gate
remains enabled. Coupled source data that still needs conversion includes:

- 99,039 leaf-cluster entries, to be remapped to the 58,732 retained leaves.
- 44,461 surface-mapping rows and 52,348 triangle-mapping entries.
- 69,737 edge/seam rows and two seam tables: the cut removes 168/273 and 23/23
  of their original edge references. Shared-BSP seam correspondence must be
  resolved explicitly; stale indices or silently deleting seams is unacceptable.
- 2,199 instanced geometry placements retained for visuals, with collision and
  cluster MOPP bindings still requiring a semantic audit. Existing MOPP format
  conversion accepts all 11 nonempty cluster code blocks, which alone does not
  establish that their keys remain correct after partitioning.
- Collision-backed containment for players, flying vehicles and the Forge camera;
  spawn/camera placement; full candidate serialization, budget and native checks.

Reproduce from the repository root, without writing a map or copying assets:

```powershell
python -B tools/warlock-conversion/snapshot/tools/partition_forge_collision.py `
  --source D:/SteamLibrary/steamapps/workshop/content/976730/3597611181/maps/forge_halo.map `
  --report work/forge-world/gulch-collision.json
python -B tools/warlock-conversion/snapshot/tools/plot_forge_split.py `
  --source D:/SteamLibrary/steamapps/workshop/content/976730/3597611181/maps/forge_halo.map `
  --output work/forge-world/gulch-boundary.png
python -B -m unittest discover -s tools/warlock-conversion/snapshot/tools -p test_forge_partition.py -v
```

Use `analyze_forge_split.py --sketch` to reproduce the two-sided estimate. Its
plane count excludes the seven additional portal planes retained by the actual
prototype. Ignored outputs reuse their existing paths; no second installation,
executable build, source-cache copy or binary collision dump is created.

## Active goal: build integration checkpoint (2026-10-21)

User explicitly requested a goal to get Forge Gulch running. Goal remains active;
no candidate has been emitted or deployed and no native gameplay checked.

The seam issue is addressed by `partition_forge_collision.prepare`: retain both
faces adjacent to every authored main-BSP seam edge. This adds 316 support
surfaces outside the geometric selection while preserving all 296 seam edges
and their order/identities. These support strips are not additional playable
areas; containment is still required. Actual prepared counts are 61,761 planes,
26,463 surfaces, 41,781 edges, 15,309 vertices and 59,173 leaves; table payload
3,899,304 bytes. Polygon round-trips and 2,048 spatial probes pass.

`--forge-gulch` now explicitly prepares this partition instead of rejecting the
source's large format. Other Sandbox builds retain the original preflight gate.
The BSP importer serializes the prepared retail tables and remaps leaf clusters,
surface-mapping rows, edge/seam rows, seam edge indices and portal planes.
Full geometry, existing triangle mappings and instance indices remain intact.
This path completed both BSPs and both lightmap bindings in the build. It is
still a development path, not permission to deploy an unchecked map.

Additional verified format handling: five-word PRT descriptors in lightmap user
data use the existing model descriptor conversion; the single unnamed effect
placement with palette index -1 is omitted only for the Gulch profile. Named
null placements still reject. Six Forge-specific tests and whitespace checks pass.

Latest reproduction from repository root:

```powershell
python -B tools/warlock-conversion/snapshot/tools/build_scenario_checkpoint.py `
  --project ../.. --slot sandbox --forge-gulch `
  --source D:/SteamLibrary/steamapps/workshop/content/976730/3597611181/maps/forge_halo.map `
  --basis ../../maps/sandbox.map --xex ../../default.xex `
  --sound-bank 'D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo3/fmod/pc/sfx.fsb' `
  --decoder ../tools/vgmstream-r2117/vgmstream-cli.exe `
  --output work/forge-world/sandbox-candidate.map `
  --report work/forge-world/build-report.json
```

Latest failure is at environment import, after geometry, placements and spawn
settings passed: `lens:levels\multi\s3d_avalanche\sky\shaders\flare_sun_ava_01`
has occlusion reflection index 10, 18 nonlegacy reflections, individual bitmap
overrides, non-unit X/Y scales and radius/brightness curves. Do not simply ignore
the index or force these through `convert_reflection`'s legacy-only handler.
Original disc maps were searched for the lens; no matching stock sun flare was
found. Existing source sky rendering and flare conversion still need a suitable
retail representation. Source player start (-49.5638,-195.6840,1.45172) is already
in the Gulch. There are no source kill/safe trigger volumes. One source soft
ceiling exists; an added split boundary must constrain the Forge camera too.

Useful primary source for a proper offline MOPP build:
https://github.com/TheGuardians/TagTool/blob/master/TagTool/Havok/CollisionMoppGenerator.cs
uses HavokTool `generate-collision-mopp` with an intermediate vertex/polygon text
file; no tool was downloaded or executed. This may help build native boundary
physics without altering OpenH3M. All remaining memory/native/visual checks from
the goal still apply. Native test routing currently lacks a Sandbox option and
must be extended using only the process-local harness before any run.
