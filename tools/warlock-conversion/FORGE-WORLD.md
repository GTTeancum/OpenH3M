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

## Native boundary compilation (2026-10-21)

Previous turn made verified progress (collision/metadata integration). This turn
adds `forge_gulch_containment.py`: preserve all 442 original soft-ceiling triangles
and append 16 inward-facing triangles along the draft split, spanning Z=-40..160.
The offline compiler emits 6,041 bytes of MOPP code for the combined 458 triangles.
The design's water fields remain byte-identical in a scratch-builder check.
Compilation and field checks are not proof that the game enforces the boundary.
The scenario's ignore masks are zeroed for the Gulch profile so bipeds, vehicles
and camera are included; runtime behavior still requires native checks.

The compiler is TagTool's `Tools/mopp.exe`, 283,136 bytes, stored only in ignored
`work/forge-world/tools`. SHA256:
`27e45ec9dc5e06e0f51afb78991d8f8f1ba6cdb057f04e6ef2f0feaa4fcf618e`.
The helper downloads it if absent and rejects any hash mismatch before execution.
It runs hidden, with temporary/profile paths inside this repository, and deletes
its input/output scratch files afterward. Input formatting must use the exact
TagTool `;### vertices ###` / `;### surfaces ###` headings and tab-separated
coordinates/indices; generic headings caused compiler stack-check failures and
were replaced. The compiled native header is 48 bytes plus code and alignment;
the helper emits a retail 64-byte tag header and keeps code bytes unchanged.

Sandbox now skips `stage_player_animations`: its stock Forge palette needs no
MCC custom vehicle/player modes. This preserves the native animation graph and
avoids importing unused modes such as behemoth/shade from the source palette.

The latest full build failure is still the nonlegacy multi-texture sun flare;
no additional full build was run just to rediscover that known failure. All six
Forge tests still pass. Goal stays active; no candidate, deployment or gameplay
claim. Resolve the flare, finish serialization/budget checks, then test native
content and containment through the process-local harness.


## First serialized Gulch candidate (2026-10-21)

The sun flare now has a dedicated retail representation retaining all 18
reflections and their referenced images. The representation reduces curves to
endpoint ranges, uses equal-area circular scales for anisotropic reflections,
and moves the source occlusion reflection first. These are explicit visual
approximations requiring native inspection. Source lighting zone sets and the
empty/null scenario resource grouping also convert through validated schemas.

The root terrain MOPP required actual key relocation after partitioning.
`forge_mopp.py` follows TagTool's branch-local offset semantics:
https://github.com/TheGuardians/TagTool/blob/master/TagTool/Havok/HavokMoppUtil.cs
The input's shape classes 8..12 share 11,541 surface indices; class 13 covers
the remaining 32,920. Their union is exactly all 44,461 original surfaces.
Class 16 references retained instances. The converter verifies this contract,
retains spatial cut/scale/property instructions, removes discarded terminals,
remaps retained surface indices and relocates every branch. Absolute terminal
bases prevent corruption from relative compact encodings. Readback verifies
all intended keys, including instances. Main code grows from 1,106,385 to
1,816,656 bytes; reachable keys decrease from 92,777 to 44,207. No engine
limits or runtime instructions were patched. Resource walking now checks real
bounds rather than rejecting any byte array over an arbitrary million entries.

The first candidate builds successfully in about 31 seconds: 133,881,856 bytes
(127.68 MiB), SHA256
`3f0a41db1c936fcf138306e3d3d4fda5cd0c66bd1c41dd7512b2d224cc676f7f`.
It is staged only as `sandbox.map` in the existing shared installation.
This is file size, not a measured Xbox 360 working-set budget. Nine focused
Forge tests pass. Native selection/gameplay/visuals and boundary behavior are
still under verification; this is not a completed-map claim.

Native route-probe logs, profiles and captures now stay in this repository's
ignored `.local/native-probes`. The existing shared installation and cache
remain the common deployment target; no second game build was created.


## Native candidate check: visual failure, goal still active

Verified fresh-profile route: Custom Games at 45s DOWN / 46s A; map menu
55s UP / 56s A; five DOWN presses at 58,59,60,61,62s select Sandbox.
65s native capture confirms the highlighted Sandbox entry. Select at 70s A,
72s A, 74s DOWN, start at 95s A. This route is now in `trace_loading.py`.
Both diagnostic tools write beneath this repository's ignored `.local`.

Native runs reached actual Slayer gameplay, with the expected H3 HUD/weapon,
and responded to process-local look/walk. However, the terrain is visibly wrong:
large sky-colored gaps/planes and rocks/trees overhead, with distant mountains
and some ground/water still visible. This fails visual acceptance. Do not treat
the staged Sandbox candidate as ready or the goal as complete.

Evidence (ignored, local only):
- `.local/native-probes/20261021-140601-route-probe`: selected Sandbox at 65s,
  bad gameplay at 132s, runtime log with invalid texture fetch constants.
- `.local/loading-traces/20261021-140925-28496`: bad gameplay already at 113s
  before scripted motion; 132s after turning/walking. Six hash validations pass,
  no failed hashes, Sandbox header authentication/verification returns success.
  Run stopped at its 140-second watchdog. No crash was observed in these runs.

Source and converted player start match exactly:
(-49.5638008,-195.6840057,1.4517200). Source floor surface 9932 crosses this XY
at Z=1.3826152 and remains in the partition. This rules out a lost serialized
start or discarded spawn-floor polygon, but does not prove runtime collision.
Terrain rendering/visibility, bitmap bindings and live collision need diagnosis.
The sky flare approximations, boundary behavior, Forge-camera containment and
actual console memory/frame budgets remain unverified. No engine change was
made. Next tests should resolve this failure rather than collect redundant
loading screenshots. All nine focused Forge tests pass.

## View-dependent terrain investigation (2026-10-21)

The human walked the map and confirms collision is present where tested, while
terrain appears/disappears with viewing direction. Do not describe their movement
as scripted control or infer missing collision from the visual holes.

Negative isolation checks:
- Removing water did not restore terrain (142028 route probe; human drove).
- Replacing terrain materials with stock opaque scorpion-guts material did not
  restore terrain (144704 probe, 116s and 128s native images).
- Source and converted scalar cluster bounds, mesh indices and instance
  transforms agree. Spawn-height leaf queries at Z 1.45, 2, 3, 5 and 10 remain
  retained, assigned to original cluster 0; Z 30 remains retained in cluster 1.
  This does not establish that pruning is correct everywhere.
- Source world mesh 126 contains the Gulch terrain bounds including the spawn.
  Further culling/render-stream diagnosis is required.

Shader graph imports for Forge terrain/water now retain each donor's native
non-bitmap dependency graph rather than silently reusing same-named Sandbox
shader definitions. This alone did not fix missing terrain. Forge sky materials
now use native templates preserving blend/self-illumination, with explicit
reported material/bump aliases when exact templates are absent. Native 142345
captures show clouds/ring instead of opaque sky cards; horizon remains overbright.
Do not claim full sky fidelity or completed terrain rendering.

The full-content candidate is `work/forge-world/sandbox-sky.map`. Flat-material,
no-water and expanded-visibility candidates are temporary isolation builds, not
accepted deployments. Restore the full-content candidate after each diagnostic.
Superseded large map outputs are removed; small reports and selected native
captures remain locally ignored. No original-disc files or engine code changed.

## Research-first correction and stock-water comparison (2026-10-21)

Human instruction: stop iterative speculative builds; research the relevant
working Halo 3 maps before changing the conversion. No new test run or conversion
change followed this instruction. The already-running no-water-pass diagnostic
finished but was never deployed. The full-content sandbox-sky candidate remains
staged; it still fails visual acceptance.

Read-only references: original-disc zanzibar (Last Resort), riverworld (Valhalla),
docks (Longshore), deadlock (High Ground), MCC Forge source, and the generated
candidate. Reproduce from repository root with `python -B` on
`snapshot/tools/audit_forge_water.py` and `audit_forge_water_geometry.py` under this
directory. Reports go to ignored `work/forge-world/water-*-audit.json`.

Established facts:
- Stock examples use water triangle format 26 / stride 12 and parameter format
  27 / stride 36, as does the converted candidate. MCC triangle format 28 /
  stride 128 is not copied to the candidate.
- Candidate water part ranges and water heights match source exactly. Main
  ocean is near Z=2.1955; puddles near Z=2.417; cave water near Z=4.4034.
- All sampled stock, source and candidate water queryable properties are -1.
  None of their texture constants requests an external mirror target. This is
  a sampler observation, not proof that no shader uses an external texture.
- Stock index buffers place water triangles after ordinary geometry, although
  their part-table water rows come first. Forge source/candidate place water
  triangles first in both. Stock docks demonstrates multiple water parts with
  cumulative corner offsets [0,4056]; Forge [0,591] and [0,6498] use that same
  offset unit. Whether index-buffer ordering is required remains unproven.
- Stock water shares parameter records across triangle corners; this converter
  expands to one parameter per corner. This is an optimization opportunity,
  not evidence of the current rendering failure.

Primary implementation references checked:
https://github.com/TheGuardians/TagTool/blob/master/TagTool/Tags/Definitions/RenderMethod.cs
and the previously retained VertexStreamXbox.cs / VertexStreamHalo3RetailMCC.cs
in snapshot/reference/formats. RenderMethod distinguishes normal bitmap,
mirror and refraction sampler modes. Its queryable-property helper accesses
texture constants: the converter's blanket real-constant remapping warrants a
separate audit, but cannot explain these water materials because all slots are
-1. Do not change it as a supposed fix for this failure.

The earlier no-water test only suppressed counts, leaving water flags and
materials. It therefore did NOT conclusively rule out the water pass. Likewise,
upside-down scenery is a reason to investigate reflection, not a diagnosis.
The user's image proves terrain can render from another view. Current evidence
does not identify a root cause. Expanded-bounds/PVS and flat-material diagnostic
maps are not fixes and are removed after recording their results.

## Broader rendering research, not only water (2026-10-21)

Human clarification: research applies across suspected subsystems, not just
water. Compare working original H3 maps before implementation changes or more
experimental builds. This pass made no conversion/runtime changes and launched
no game.

Read-only `audit_forge_rendering.py` compares Sandbox, Last Resort, Valhalla,
Avalanche, Narrows and Guardian against Forge source/candidate. From repository
root run `python -B tools/warlock-conversion/snapshot/tools/audit_forge_rendering.py`.
`audit_forge_visibility.py` and `audit_forge_shaders.py` run the focused checks.
Reports remain ignored under `work/forge-world`.

Findings:
- Both Forge BSPs preserve all 170 mesh records, including part/subpart ranges,
  buffer slots, mesh flags/types, compression records and per-cluster/instance
  lighting assignments. No out-of-range buffer or part/subpart index range was
  found in the candidate or the six stock references. This is metadata evidence,
  not proof of correct live buffer upload, actual vertex values, or residency.
- Empty per-mesh subpart-visibility arrays occur in all six stock examples too;
  their absence is not evidence of a broken conversion.
- The 170 per-mesh visibility MOPP headers, decoded terminal keys and reorder
  tables match source/candidate. Every decoded key is within its mesh's subpart
  count, also checked against Last Resort. This does not validate the separate
  partitioned collision/leaf/portal visibility path or runtime culling.
- Candidate has a concrete shader-pass mismatch: BSP 0 meshes 16,18,29,111 use
  ambient PRT with material 2 (`forge_halo_rocks`). Source template
  `_0_0_1_1_2_0` supports the pass; its sole exact-named original-disc donor,
  Guardian, has mask 0x2263a and lacks it. Guardian and Last Resort's own mesh /
  shader pairings show no such mismatch. No alternative was substituted yet.
  Resolve compatible native template options/parameter bindings before changing
  the donor. This defect does NOT establish the cause of all missing terrain.
- Candidate converts six foliage-material part uses from rmfl to rmsh; record
  this separately from terrain rendering and evaluate the existing approximation.
- Main Forge BSP contains 2199 instances vs Last Resort's 1130; this comparison
  is workload context, not a proven engine-limit violation or console RAM budget.

Primary implementation references reviewed alongside original disc data:
https://github.com/TheGuardians/TagTool/blob/master/TagTool/Geometry/RenderGeometry/RenderGeometry.cs
https://github.com/TheGuardians/TagTool/blob/master/TagTool/Tags/Definitions/ScenarioStructureBsp.cs
They distinguish mesh visibility MOPPs/subpart bounds from BSP leaf/portal data.
Next research priorities: compatible rock shader pass, partitioned leaf/portal
semantics, live resource binding/visibility selection, and remaining sky/lighting
approximations. Do not treat matching serialized fields as visual acceptance.

## Evidence-based visibility and rock-lighting corrections (2026-10-21)

`forge_visibility_partition.py` now preserves source render-cluster classification
while dropping out-of-Gulch collision surfaces. The prior surface-only pruning
lost 18 of 13,887 sampled nonsolid points 0.65 units above retained upward-facing
polygons. It did not lose any of 96 sampled near-camera points at the spawn;
therefore this defect was not presented as the established cause of the initial
bad view. All 18 failing points now recover their original cluster in decoded
retail tables (`preserved-visibility-audit.json`).

Only subtrees without retained collision can simplify. Empty leaves of the same
cluster share a representative; different clusters retain separating nodes.
Discarded solid regions within those subtrees may become empty, as intended for
removed outside collision. Subtrees supporting retained collision retain their
solid branches. Source nonsolid leaf cluster identities are preserved. The new
tables use 119,622 nodes, 62,600 planes and 59,185 leaves (12 empty cluster leaves),
within original index widths. All 26,463 retained surface loops still roundtrip;
2,048 spatial readback samples pass. No engine limits were raised.

For `forge_halo_rocks`, Cold Storage's native `_0_0_1_1_1_0` template supplies
ambient PRT, unlike Guardian's exact-named `_0_0_1_1_2_0`. Stock option definitions
show the difference enables material 2. The source blue blend channel, ignored
when material 2 is off, contains BC3 noise up to 8/255. Clear only the blue RGB565
endpoint bits before tiling, so the extra material receives zero weight. Red,
green and alpha decode unchanged, including alpha and interpolation edge cases.
Unused material-2 bindings reuse valid material-0 values; no assets are added
for that unused layer. The original active layers retain their normalization.
Primary shader implementation corroborating active-channel normalization:
https://github.com/Beatthezombie/HaloShaderGenerator/blob/master/halo_online_shaders/terrain.fx
This is Halo Online reference source, not proof of Xbox shader bytecode identity;
actual donor categories, parameters and pass coverage were inspected from the
original Cold Storage cache. The new shader audit reports zero missing required
PRT passes, vs four formerly. The mapping and masked channel are reported.

Fourteen focused Forge tests pass. Rebuilt candidate:
`work/forge-world/sandbox-visibility-prt.map`, 137,646,080 bytes.
Render metadata and per-mesh visibility trees still match source. Audits accept
an optional candidate-map argument so they validate the actual new output.
Only this candidate was built and staged for the runtime check after research.
No engine code, original disc files, or other installed maps changed.

Native validation `20261021-153032-route-probe` FAILED visual acceptance.
Both native captures (116000 and 134000 ms, with a process-local turn between)
still show missing terrain and inverted scenery. The two verified offline
corrections do not resolve the main rendering failure. Do not call this fixed.
No further speculative candidate was built.

Independent payload readback (`audit_forge_positions.py`) compares primary
position/UV bit patterns directly between MCC and the decoded candidate, without
calling the encoder. All 166 primary buffers / 146,012 vertices match. Together
with matching compression metadata, this rules out altered stored primary
positions as the explanation; it does not validate live transforms, resource
binding, visibility selection, or water/reflection render state. The next step
is to trace those runtime paths against a stock map before changing more data.
