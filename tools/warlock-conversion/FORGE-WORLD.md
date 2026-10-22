# Forge World / Sandbox conversion

Status (2026-10-22): **Forge Gulch runs over Sandbox in the shared installation.**
Terrain visibility and rock detail are fixed; the user confirmed the divider
stops an occupied Banshee and closed that check. Monitor pushback was previously
verified. Three requested automated Forge-menu checks show complete text; the
historical missing-glyph issue is retained as a monitored regression.

Deployed candidate: `sandbox-hard-divider.map`, 138,272,768 bytes (131.867 MiB),
SHA256 `4656e4e708832f8ba876a7a7d16ae4750c5b09b73d4289379893db740746f339`.
The detail-mip candidate is the single rollback. Original disc maps and other
conversions remain intact. **Whole-console Xbox 360 memory acceptance remains
unverified; this is not yet a completed budget-certified port.** Earlier failed
runs below are historical; current evidence and qualifications are at the end.

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
the native signed-node limit of 32,768 planes. Edge count also exceeds the retail index range.
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

## Runtime draw investigation (2026-10-21, ongoing)

`trace_loading.py --sample-draws` now samples native D3D12 IssueDraw state in its
own hash-checked child after 110 seconds. It records at most 1,024 draws, restores
breakpoint bytes, and exits under the existing watchdog. It changes no GPU
registers, guest values, or game files and generates no host input. Entry address
and register-file offsets were identified by matching the local SDK object code
to the installed GPU DLL (SHA256 c9f3b77b65d46dbfc382f6b16e5f44c6dac883f2253c62887fcc165aa6087e4c).

Runs `20261021-154537-1996` and `20261021-155308-33068` confirm submitted terrain
uses a normal view/projection matrix. Camera (-45.2618,-196.0952,2.1297) lies in
cluster 0 in both original and serialized candidate collision trees. All 2,252
instance transforms match the source. Render floor at the authored spawn is
Z=1.38261517765, matching collision. Primary GPU fetch allocation sizes show
mesh 127 submitted repeatedly, while mesh 126 (containing the spawn floor) is
absent from the 1,024-draw sample. This sample is bounded, not a whole-run proof.
The captured image remains bad. Shader prefix matching is exploratory and may
match multiple variants; it is not exact shader identity validation.

A new native-layout difference: original Sandbox, Last Resort, Valhalla,
Avalanche and Guardian all serialize a per-mesh MOPP array in BOTH their BSP
geometry and lighting geometry. Every code blob and reorder table matches
between those two locations. MCC Forge omits the BSP array, retaining it only
in Lbsp. The converter had preserved that omission. `scenario_geometry.py`
now binds an omitted BSP array to the already converted lighting allocation,
with matching BSP/mesh/tree count checks. This adds no duplicate tree payload.
Native verification `20261021-155801-route-probe` FAILED: both captures still
show missing terrain. The matching BSP trees alone did not resolve the failure.


### Native collision encoding and camera classification

Run `20261021-160412-16620` found an observer-result-shaped record at TLS +0x25c,
base +0x1cc, with camera (-45.261806,-196.095169,2.129657). Position is followed
by bytes 00 01 BA 14, then zero velocity/rotation and the matching forward/up
vectors. The first two location bytes suggest BSP 0 / cluster 1, while independent
source and serialized collision queries produce cluster 0 (source leaf 0x6671,
converted leaf 0x63bd). The final two bytes have not been proven a leaf index.
This is a lead to trace, not permission to override the camera's cluster.

All 25 original disc scenario PVS headers have short values (0,8), whereas all
four converted maps have (8,0). The three previously accepted conversions share
that difference; its runtime significance is not established. No speculative PVS
header patch was made.

Direct original-disc collision inspection found a confirmed format mistake:
original Halo 3 surface orientation uses plane-index bit 15, not surface flag 7.
Sandbox has 261 reversed plane indices, Last Resort 1828, Valhalla 905, and
Guardian 889; all four have ZERO surface flag-7 entries. The TagTool generic
SurfaceFlags enum describes later formats here and was insufficient evidence for
retail H3. The Gulch large-to-retail converter now puts all surface/ref planes
below 32768 and moves orientation from source plane bit 31 to retail bit 15.
Further native-code inspection below supersedes the initial unsigned-node assumption. Serialization
readback verifies orientation against the original polygon and plane. The native
visual result of this correction is still under test; do not claim it fixed yet.


### Confirmed signed-plane overflow and native-budget rebuild

The original executable's point-to-leaf routine at 0x820BB5F0 sign-extends the
packed node's low 16-bit plane index at 0x820BB640, then multiplies it by 16.
The collision traversal at 0x822D7AB8 does the same at 0x822D7AF0. Consequently
ALL node plane indices must be below 32768. The old 62600-plane partition was
invalid despite passing the converter's unsigned readback. Original disc maps
already obey this limit. `preflight_collision_budget.py` now reports the signed
limit and `bsp_collision_resource.py` rejects overflow before serialization.
No engine limit or native code was changed.

The preceding surface-orientation correction alone still FAILED visual run
`20261021-161521-29436`: the camera remained assigned to cluster 1. Native
readback confirmed the entire live leaf-to-cluster array matched the file.

`rebuild_forge_collision.py` uses the pinned TagTool collision builder (release
ce2dc6a) through the small `rebuild_collision` bridge. It reconstructs the tree
from the retained original polygons: 26463 surfaces, 41781 edges and 15309
vertices remain byte-equivalent in geometry/material/topology; the rebuilt tree
uses 23931 planes. `forge_visibility_overlay.py` then clips each rebuilt empty
cell against the original cluster-only partition, preserving the authored
cluster classification without importing out-of-Gulch collision. Reference lists
are shared when a leaf splits; resource payloads are not duplicated.

Overlay output: 63662 nodes, 24679 planes, 37646 leaves; authored portal planes
are rebound afterward. 31463 independent polygon-offset/random probes found
zero solid/empty differences versus the rebuilt collision and zero cluster
mismatches in 30108 nonsolid source/output comparisons. This is offline evidence;
native rendering, containment and overall memory acceptance still require their
own evidence. The native result for `sandbox-rebuilt-collision.map` follows below.

Rebuild work and tool caches remain under repository `work/forge-world` and
`.local`. The 27 MB release archive and unused package files were removed after
verification; only 7.4 MB of builder dependencies remain. The slim dependency
set successfully rebuilt the collision again. Output caching is keyed by input,
source spatial data and implementation, with result hashes checked before reuse.

### Native terrain acceptance and repeatable spatial checks

Run `.local/loading-traces/20261021-170528-27160` reached the correct Sandbox
replacement. Both native captures (116000 and 134000 ms) were opened and inspected.
Ground, grassy slopes and cliffs render before and after process-local turning
and walking. The live observer now reports BSP 0 / cluster 0 (`00 00 21ce`),
matching the independently queried source, rather than the prior incorrect
cluster 1. This establishes the missing-terrain fix for the tested views; it
does not establish containment or whole-map performance. No engine change was made.

Run the independent spatial audit without altering rebuild caches:

```powershell
python -B tools/warlock-conversion/snapshot/tools/audit_forge_spatial.py `
  --source D:/SteamLibrary/steamapps/workshop/content/976730/3597611181/maps/forge_halo.map `
  --report work/forge-world/spatial-audit.json
python -B -m unittest discover -s tools/warlock-conversion/snapshot/tools -p 'test_forge*.py' -q
```

The repeated audit checks 31,463 points: zero solid/empty mismatches, zero
cluster mismatches across 30,108 nonsolid comparisons. Its output hash binds it
to the intermediate rebuilt collision. It is a bounded spatial sample, not an
exhaustive or native test. All 17 focused tests pass, including oblique clipping
volume, solid preservation, shared collision references and equal-cluster collapse.

### Remaining rock shading investigation

`audit_terrain_parameters.py` compares compiled constants in Guardian, Avalanche,
Last Resort, Valhalla, MCC Forge World and the converted cache. Converted rock
specular coefficients, powers and tint match the source by parameter name;
the high MCC environment values (7) are omitted because these original-disc
templates have no matching environment constant. They are not accidentally
being fed to another native parameter. Stock rock materials also have nonzero
specular, so their presence alone does not justify globally disabling it.
Next investigate normal/specular texture encoding and native material output.

The source sky explicitly contains `sky_halo/shaders/dome_stars` and
`sky_halo/bitmaps/star_mask`. Dots in the sky are therefore not by themselves
evidence of corruption; retain authored stars. The rock speckles remain under
investigation. Do not use the earlier Warlock matte approximation as proof of
the cause or silently apply it here.

The next comparison found a concrete discrepancy: source `rocks_2dblend_normal`
is 512x512 with 10 mips, and `rocks_lichen_normal` / `rocks_smooth_normal` are
1024x1024 with 11 mips (BC5/DXN). `encode_bitmap_base` intentionally emits only
one mip. Stock Last Resort's `rock_rough_zbump` is 1024x1024 BC5 with 11 mips;
its 90 normal textures and Valhalla's 94 all have multiple levels. Restoring
authored mip chains is the next implementation step, with native readback and
visual comparison required before attributing the speckles to this difference.
Reference implementations for the retail packed mip layout:
- https://github.com/TheGuardians/TagTool/blob/master/TagTool/Bitmaps/Utils/XboxBitmapUtils.cs
- https://github.com/xenia-project/xenia/blob/master/src/xenia/gpu/texture_util.cc

### Confirmed MCC/retail normal encoding difference

Before mip implementation, direct resource inspection found a separate format
bug. All 88 BC5 normal resources inspected in Last Resort and all 93 in Valhalla
use GPU format `0x1a215571` (DXN, tiled, 8-in-16 endian, GPUSIGN_BIAS on XYZW).
The converter emitted `0x1a200171`, with unsigned sampling, and copied MCC signed
endpoints unchanged. TagTool's `BitmapConverterGen3.ConvertDXGIFormats` biases
MCC endpoints by 128 and swaps XY for PC ATI2; original Xbox-to-ATI2 only swaps
XY. Direct MCC-to-Xbox therefore biases the four endpoints without swapping
the channels. Selector bits remain unchanged. The original terrain shader
expects signed XY from the GPU; its PC-only branch supplies that remapping.

`encode_bitmap.py` now performs that conversion and emits the original-disc
sampling format. Existing accepted map files are not rebuilt by this change.
Primary references:
- https://github.com/TheGuardians/TagTool/blob/master/TagTool/Bitmaps/Utils/BitmapConverterGen3.cs
- https://github.com/TheGuardians/TagTool/blob/master/TagTool/Direct3D/Xbox360/D3D.cs

`audit_forge_normal_payload.py` independently computes expected endpoint bytes,
untile-reads the serialized candidate and confirms all three rock normal maps
plus their GPU format. All 19 focused tests pass. Native run
`.local/loading-traces/20261021-171958-31932` inspected both 116000/134000 ms
captures before and after turning/walking. Terrain remains present, and rock
shading changes, but fine grain remains. Do not claim the full shading problem
is solved: mip chains, containment and guest memory acceptance remain open.
The run reached its 140-second watchdog without a reported unhandled crash.

### Authored normal mip chains retained

Forge conversion now retains the authored BC5 normal mip chains below the
existing resolution cap. `xbox_mip_chain.py` implements the original tiled
layout and packed tail. It does not regenerate/compress normal data. The
resource stores the complete chain in one primary segment, with matching
bitmap and interop mip counts. Other conversions keep their current mip policy.
Color/blend/cubemap mip policy has not changed in this step.

The independent pinned TagTool decoder first checked synthetic square and
rectangular textures (512x512, 256x512, 512x256, 128x512), with every decoded
mip matching its input. `audit_forge_mips.py` then checked the serialized map:
all 28 custom normal textures / 264 mips match the MCC source after endpoint
conversion. It builds its small decoder bridge as needed using repository-local
temporary/package directories and verifies the TagTool assembly hash.

```powershell
python -B tools/warlock-conversion/snapshot/tools/audit_forge_mips.py `
  --source D:/SteamLibrary/steamapps/workshop/content/976730/3597611181/maps/forge_halo.map `
  --candidate work/forge-world/sandbox-normal-mips.map `
  --report work/forge-world/mip-payload-audit.json
```

Native run `.local/loading-traces/20261021-172724-37480` reached gameplay;
both 116000/134000 ms captures were inspected before and after turning/walking.
Terrain and surrounding scenery remain present. The texture change introduces
no observed loading/rendering regression in this route. Static captures do not
prove temporal shimmer eliminated; do not claim that. Fine visual texture remains.
The 140-second run ended at its watchdog without a reported unhandled crash.

Current file growth is 1,507,328 bytes compared with the single-mip normal build.
The 28 normal resources occupy 8,617,984 uncompressed tiled bytes in total.
This is a resource subtotal, not a whole-console resident-memory measurement.
Containment and overall Xbox 360 budget acceptance remain unverified.


### Repeatable containment diagnostics and memory accounting limits

`trace_loading.py --slot sandbox --forge-boundary-check --sample-observer
--seconds 180` selects Forge with two initial Down presses, then Sandbox with
five map-list Down presses. Native route probe
`.local/native-probes/20261021-173147-route-probe` showed Forge / Sandbox at
73500 ms and monitor gameplay at 134000 ms. D-pad Up switches to monitor;
RB ascends, LT supplies thrust, and left strafe travels toward the curved split
from the initial +X-facing spawn. The original Halo 3 manual documents these
monitor controls: https://halo.wiki.gallery/images/d/da/H3_Manual.pdf .
All input remains inside the game process.

Observer telemetry reads the verified original observer record through TLS
+0x25c, record +0x1cc. Positive `gulch_margin` is inside the requested split.
The loading cinematic camera before gameplay is not a containment result.
Sampling occurs outside the debugger's idle-only branch so busy debug-event
traffic cannot silently suppress position evidence.

The ordinary-speed run `20261021-173903-35764` traveled about 87 units of the
184-unit approach. Boosted run `20261021-174239-30716` approached within 12.8
units, but changed height/position near terrain and input ended before reaching
the split. Neither establishes that the boundary holds. The next diagnostic
uses thrust during ascent and maintains strafe until 178 seconds to test above
that terrain; it still uses the existing deployed map and 180-second watchdog.

`audit_gulch_containment.py` verifies all 16 added triangle planes, winding,
requested XY segments, vertical extent, scenario object-category flags and
compiled MOPP presence. Current result passes with 6,041 MOPP bytes. This is a
serialization check, explicitly not native containment proof. Original XEX
initialization at 0x822470A0 enables all 128 ceilings through a separate TLS
+0x284 bitset; lookup at 0x822486E0 uses it. Consequently the serialized zero
runtime field is not evidence of disabled ceilings. No speculative flag patch
was made.

Memory-accounting exclusions established from the local SDK source:
- `src/system/xmemory.cpp` precommits the full 512 MiB physical arena. Host
  committed/working-set bytes are not a measure of occupied guest allocations.
- Its physical heaps share a 512 MiB parent, but virtual/XEX heaps are separate;
  physical capacity alone does not prove total retail memory acceptance.
- `MmQueryStatistics_entry` in `src/kernel/xboxkrnl/xboxkrnl_memory.cpp` derives
  available pages from heap counters, but hardcodes many other fields, including
  title physical pages. Those placeholder fields cannot be used as measurements.
- ManagedDonkey's physical-memory constants describe a different PC build and
  cannot serve as original Xbox 360 limits.

Budget acceptance therefore remains open pending actual allocation accounting;
the 138,219,520-byte cache size is not a substitute.


The elevated boosted test `20261021-174620-22872` completed at the 180-second
watchdog. At 168.203 seconds the monitor was (-45.143, -14.858, 42.104),
2.465 units inside the split. With left strafe and LT still held, it was
(-50.346, -7.623, 42.104) at 172.203 and then followed the line toward
(-53.962, -4.937, 44.790) at 177.203. The signed margin remained approximately
-0.8 units while input pressed outward: native acceleration deflected the
monitor along the curved split instead of allowing continued +Y flight.
Input ended at 178 seconds; the final 179.203 sample was (-56.133, -3.975,
45.461), margin -0.572. This supports soft monitor containment at the tested
segment and bend, with finite penetration inherent in an acceleration boundary.
It does not prove all segments, endpoint/height coverage, bipeds or vehicles.
No map/engine changes or new screenshots were made for this diagnostic.

All 19 focused Forge tests and the serialized containment audit pass. The
observer diagnostic now reads the scenario index once before launch, avoiding
repeated cache parsing during the run.


### Closed-shell comparison exposes and fixes a bottom bypass

Original Sandbox's 144 acceleration triangles form a closed shell (216 unique
edges, each shared twice). Last Resort's 438 acceleration triangles likewise
form a closed shell (657 shared edges). Forge World's retained 442 triangles
also form a closed shell (663 shared edges), extending from
(-130.399, -266.344, -147.355) to (184.757, 278.253, 75.231).
These are serialized original/native triangle measurements, not visual guesses.

The former divider ran from Z=-40 to 160. It therefore did not partition the
entire closed shell: space below -40 was a possible bypass. The builder now
extends the divider four units past the original shell wherever necessary,
retaining at least the previous vertical extent. For this source the bottom
is -151.355 and the top remains 160. It also rejects a source whose X bounds
extend beyond the fixed split endpoints. The four-unit overlap exceeds the
measured sub-unit soft-boundary penetration; no gameplay tuning changes.

The independent serialized audit checks closed-shell edge incidence, endpoint
coverage, vertical overlap and every divider triangle. It rejects the previous
`sandbox-normal-mips.map` for inadequate vertical overlap and passes the new
`sandbox-contained.map`. Compiled MOPP shrinks from 6,041 to 5,956 bytes; total
cache size remains 138,219,520 bytes. Three regression tests exercise deep/tall
shells and incompatible source extents; all 22 focused tests pass. Native
biped/vehicle verification and whole-console budget acceptance remain open.


Native regression run `.local/loading-traces/20261021-175150-33548` used the
new deployed candidate and completed its 180-second watchdog with no recorded
observer errors. The sustained outward monitor approach again deflected along
the curve; deepest measured margin was -0.880 units, recovering to -0.546 at
179.25 seconds. The 174000 ms native capture was inspected: foreground terrain,
distant mountains, sky and Forge HUD are present, but a conspicuous bright
patch at the waterline remains. This is not full visual acceptance. The newly
extended lower portion is verified geometrically, not yet by an underwater
native traversal. The previous single-mip-normal candidate (136,712,192 bytes)
was removed; the immediately previous normal-mip candidate remains for rollback.


### Authored sky animation correction

A new read-only comparison against the original-disc donors and MCC source
identified donor material animation leakage. The converter copied donor shader
programs and postprocess animation routes, then replaced constants/textures.
This gave `horizon_flats` a donor self-illumination animation ranging from 0 to
32, although its source has no animation and uses intensity 1. `dome_stars`
and `mountains_wisps` inherited donor color/brightness controls (including an
intensity range 3 to 15); clouds inherited four donor scrolling functions
instead of their two authored functions. These are verified serialized defects,
not an inference from the bright screenshot alone.

Forge sky materials now clear donor animation tables and convert only authored
source functions/routes using the existing semantic register remapper. The
remapper accepts an absent retail entry only when the corresponding source
animation pass contains zero routes. Puffy clouds have exactly such an empty
entry (index 10). Nonempty mismatches still fail instead of discarding animation.
This change is scoped to Forge sky materials; previous conversions are not rebuilt.

`audit_forge_sky_animations.py` locates the converted sky model through its build
report, pairs all 12 model materials with their authored counterparts, compares
function types, input/range variables, periods and endian-converted payloads,
and rejects donor routing on unanimated materials. The old contained build fails
on cloud animation count; the corrected build passes with three authored
functions total. The serialized containment audit and all 22 focused Forge tests
also pass. Native visual acceptance is recorded separately below.

The water investigation did not justify a speculative constant change. Serialized
source/candidate reflection values agree. The reference shader's automatic-foam
formula supports the existing high foam-height suppression, although this PC
reference is not proof of identical Xbox bytecode:
https://raw.githubusercontent.com/Beatthezombie/HaloShaderGenerator/master/halo_online_shaders/water_shading.fx
Current parameter comparison is retained in `work/forge-world/water-current-audit.json`.


Reproduce the authored sky comparison from repository root:

```powershell
python -B tools/warlock-conversion/snapshot/tools/audit_forge_sky_animations.py `
  --source D:/SteamLibrary/steamapps/workshop/content/976730/3597611181/maps/forge_halo.map `
  --candidate work/forge-world/sandbox-sky-animation.map `
  --build-report work/forge-world/sky-animation-report.json `
  --report work/forge-world/sky-animation-audit.json
```

`audit_forge_water.py` now accepts an explicit candidate path and defaults to the
shared deployed Sandbox map instead of referencing a deleted historical build.


Native run `.local/loading-traces/20261021-180203-10088` completed its 180-second
watchdog. Its 174000 ms capture was inspected against the same-route capture
from `20261021-175150-33548`: the yellow/white waterline glow becomes blue-white
mist, and the excessively bright stars become subdued. Terrain, mountains,
clouds, ring and Forge HUD remain visible. This establishes donor animation
leakage as the cause of the observed excess glow at this viewpoint. It does not
establish complete visual fidelity from a single view; the mist card edge is
still visible. Monitor deflection remains intact, minimum signed margin -0.869
and final position (-56.125, -4.004, 45.456); no observer errors were recorded.
No engine, water constants, geometry or simulation tuning changed in this fix.
The preceding contained build is retained for rollback; the older normal-mip
candidate is removed to keep only current and immediately previous candidates.


### Guest allocation observer

`trace_loading.py --trace-memory` resolves three original retail imports through
the XEX import records: ordinal C6 / 0x82723FA4 (`MmQueryStatistics`), BA /
0x82723B64 (`MmAllocatePhysicalMemoryEx`), BD / 0x82723B94 (`MmFreePhysicalMemory`).
The installed runtime's hash guard still applies. Memory tracing now starts with
DEBUG_ONLY_THIS_PROCESS so startup allocations are observed before guest code
runs. The ordinary late-attach route remains unchanged for other diagnostics.
Only the launched game process is inspected; no desktop input or engine patch.

Successful statistics calls record the original returned words and derive the
physical heap total from total pages minus kernel/available pages, following the
runtime implementation. Placeholder title.physical_pages is not used. At five-
second intervals after 105 seconds, VirtualQueryEx measures unique committed
backing for guest virtual ranges 0..0x7F000000 and XEX 0x80000000..0x90000000.
The 0x7F000000 GPU alias and 0x90000000 XEX alias are excluded, as are the three
physical aliases and the precommitted physical arena. This is explicitly not
Windows process RSS. Allocator event totals are diagnostic: an unmatched free
must be treated as incomplete event accounting, not silently ignored as zero.


The first complete startup trace is
`.local/loading-traces/20261021-181003-19620` (135-second watchdog). It recorded
58 successful statistics calls, physical heap peak 489,107,456 bytes and six
stable gameplay-time virtual/XEX backing samples of 11,227,136 + 40,108,032
bytes. There were no observed physical allocation/free calls after the final
statistics snapshot at 37.421 seconds and no observed failed allocations.
The combined components are 540,442,624 bytes, but include the runtime's
16,777,216-byte physical writeback reservation and other runtime/debug support.
The runtime's kernel allowance is itself a placeholder. This is not a retail
budget failure/pass determination. A stock disc baseline is required.

`summarize_guest_memory.py` preserves these scopes and emits an explicit false
retail verification flag rather than promoting the totals to a console claim.
It also reports one unmatched free in the event stream. Software breakpoint
single-stepping can miss concurrent calls; event sums must not replace the native
heap-counter snapshots. Occupancy inside the game's fixed resource pool remains
a separate question.


Stock disc Sandbox baseline `.local/loading-traces/20261021-181324-24996`
completed at 135 seconds and produced exactly the same physical heap peak
489,107,456 bytes and virtual/XEX backing 51,335,168 bytes as Forge Gulch.
Both have 58 statistics samples, no later observed physical allocation calls,
no observed failed physical allocations, and the same unmatched free event.
The measured excess over 512 MiB is therefore also present in unchanged stock
Sandbox under this runtime, rather than an increase introduced by Forge Gulch.
This comparison establishes no increased backing allocation in the tested flow;
it does not measure used space/fragmentation inside the fixed game resource pool
or certify the console budget. No baseline installation copy was created: the
original disc root was read directly, with all output/profile/cache paths kept
inside the authorized project directories.

During the baseline the user reported corrupted menu text. The main menu map
and English font package in original/shared roots have identical SHA256 hashes.
A normal late-attach capture run is checking the reported visual failure before
attributing it to startup observer timing. Do not count the baseline's menu
rendering as verified from successful loading/logs.


Normal-run menu check `.local/loading-traces/20261021-181554-37316` uses the
shared converted installation with ordinary late debugger attachment, not the
startup memory observer. Native captures at 40000 and 73000 ms were both
inspected: main menu and Custom Games / Sandbox lobby text are readable,
including labels, player count, loading text and controller prompts. This does
not reproduce the user's reported corruption and is not a claimed fix. Font
package hash is 7ad74e0c5a97b2bc1654c629e2700c5a7d7d0cbd316a0bf47494769678db3296;
mainmenu.map hash is d1a8ef6074c7be74579af4a70bbf9173496bf14bddde0d53af66fc88657081df
in both original/shared roots. The affected menu/session is pending clarification.

### Static resource footprint comparison (2026-10-21)

`audit_resource_footprint.py` inventories retail `zone` resources and `play`
locations, deduplicating nonempty physical pages by source file and block offset.
It includes shared resources, skips retail empty pages that reuse the next page's
block offset, and rejects inconsistent descriptions/indices. It also inventories
resource bitsets for each manifest. Manifest page totals include both required
and optional locations and are NOT measured resident bytes. No asset extraction,
new map candidate, or runtime change is involved.

Reproduce from repository root:

```powershell
python -B tools/warlock-conversion/snapshot/tools/audit_resource_footprint.py work/forge-world/sandbox-sky-animation.map ../../maps/sandbox.map ../../maps/shrine.map ../../maps/sidewinder.map ../../maps/zanzibar.map --report work/forge-world/resource-footprint.json
```

| Cache | Tag memory bytes | All referenced uncompressed page bytes |
| --- | ---: | ---: |
| Forge Gulch current | 31,588,352 | 483,172,152 |
| Original Sandbox | 19,005,440 | 434,424,996 |
| Original Valhalla | 19,070,976 | 420,193,454 |
| Original Avalanche | 21,823,488 | 470,618,780 |
| Original Last Resort | 18,677,760 | 419,006,296 |

Gulch local required-page inventory is 143.55 MiB versus Sandbox 65.24 MiB;
shared required-page inventory is 133.03 versus 131.72 MiB. The material increase
is local converted resources, not duplicated shared stock objects. This points
budget investigation at local geometry/lighting/textures. The largest local
pages include BSP render data (20,146,716 bytes), BSP collision data (9,466,766),
and bitmap owners 0x9000287e/0x9000287f (18,874,368 and 4,718,592 bytes).
The latter contain 1536x1536 type-3/format-16 bitmap records; semantic role and
safe optimization must be established from their references before changing them.

These inventories exclude simulation, framebuffers, staging, alignment and
allocator overhead; some listed pages are streamed and need not coexist.
They neither prove a 360 budget failure nor certify fit. Runtime pool occupancy
and vehicle/player containment remain open. Menu corruption remains unreproduced.

### Lighting resource oracle and independent layer verification

The two unnamed large bitmap resources from the footprint inventory are now
identified by their `sLdT` references: 0x9000287e is the main BSP's eight-layer
lightprobe array, and 0x9000287f is its two-layer dominant-light array. Their
1536x1536 BC3 payloads total 22.5 MiB. The second BSP's 512x512 pair adds 2.5 MiB.
An inventory of all 24 original playable maps (excluding mainmenu/shared) finds
1024x1024 BC3, one mip, eight lightprobe layers and two dominant layers in every
map: 10 MiB per stock map. This establishes an optimization lead, not a proven
1024 hardware limit or authorization to discard lighting layers.

`audit_forge_lightmaps.py` follows the actual source/target BSP lightmap bindings,
checks all 54 compression coefficients per BSP, and independently decodes every
layer through pinned TagTool. All 20 layer hashes exactly match the source BC3
bytes, including the 1536x1536 arrays. Thus no layer-order, tiling, truncation or
coefficient discrepancy was found. Visual fidelity and runtime pool occupancy
are separate requirements. No deployed cache changed during this audit.

```powershell
python -B tools/warlock-conversion/snapshot/tools/audit_forge_lightmaps.py --source D:/SteamLibrary/steamapps/workshop/content/976730/3597611181/maps/forge_halo.map --candidate work/forge-world/sandbox-sky-animation.map --stock-dir ../../maps --report work/forge-world/lightmap-byte-audit.json
```

The existing `validate_bitmap_mips` helper must be rebuilt after updating its
source. It now optionally accepts depth, bitmap type and layer index after its
existing arguments; existing normal-map callers retain the 2D/layer-zero defaults.
Audit scratch payloads are removed in `finally`. Future conversion reports now
record each imported lightmap's semantic role, source name, target datum,
dimensions, layer count and tiled size, so resource owners remain traceable even
when serialized imported tags do not have names.

### Forge palette reproduces missing menu glyphs

`trace_loading.py --forge-palette-check --slot sandbox` uses the previously
verified Forge lobby route, switches to monitor with D-pad Up at 118000 ms and
opens creation with X at 121000 ms. The 124000 ms native capture shows the Weapons
palette, with LB/RB category controls; this is now a reproducible menu checkpoint.
The flag rejects simultaneous manual, walking or boundary routes. No OS input.

- Gulch `.local/loading-traces/20261021-182855-31292/proof-loaded.png`: visible
  missing glyphs in OBJECT (J), Done (D), Summary (u), category pagination and
  dollar/hash symbols. Terrain and monitor HUD are present. This reproduces the
  user's menu-text report and supersedes the earlier 'unreproduced' status.
- Untouched original Sandbox `.local/loading-traces/20261021-183129-10644/proof-loaded.png`:
  identical route, runtime, shared host cache and capture time; all of those
  palette labels/symbols render correctly. Original Sandbox structures, weapons,
  lighting and monitor HUD are visible, confirming the correct stock content.
- Both child runs finished at their 135-second watchdog. English font-package
  hashes were rechecked identical. The map conversion/data or resulting resource
  pressure is therefore the next investigation target; these two runs do not
  establish which mechanism is responsible. Do not replace the font package or
  declare a global font/runtime defect from this evidence.

Reproduce Gulch with the normal shared installation; append
`--game C:/X360/ISOs/H3M` for original-disc stock baseline. Use
`--capture --capture-times-ms 124000 --seconds 135` and the existing shared cache.
Player/vehicle containment is still unverified: this check opens the creation
palette only and does not spawn or drive a vehicle.

### Font-cache investigation and limits of the menu comparison

The serialized localization tail is identical between stock Sandbox and current
Gulch: 1,208,320 bytes, SHA256
`ee6c03113d078122c90be2cd8bb0946a1324adf5b0189d8345c46f058b567d56`.
All 33 original `unic` tag roots (80 bytes each) are also unchanged. This rules
out changed localized string content in those sections, not other runtime causes.

A later Gulch run `20261021-202057-26640` rendered the complete Forge palette at
129000 ms. Another run `20261021-202345-22260` had the same missing glyphs at both
124000 and 129000 ms. Thus the issue is intermittent across runs; it is not
proven to resolve simply by waiting, and the earlier stock comparison does not
prove deterministic conversion corruption. Neither run is a fix.

Original XEX code identifies the font cache at TLS+0xF4, with an LRU heap at
cache+0xC and packed character arena at cache+0x10. Functions 0x82201C50,
0x82201EC0 and 0x822C2058 establish the 24-byte nodes, shifted offsets, character
header and empty/unavailable-character behavior. The related Halo Online
reference was used only for orientation, not addresses or Xbox layout:
https://github.com/twist84/ManagedDonkey/blob/main/game/source/text/font_cache.cpp

`font_cache_probe.py` bounds reads, detects cycles/oversized payloads and reports
character keys, metrics, packed-pixel hashes and hardware-block records. Four
synthetic parser tests cover user-virtual storage, empty characters, cycles,
allocation truncation and null pointers. Initial runtime attempts used the loader
thread's TLS and returned a null font-cache pointer; they produced no character
measurements and must not be treated as evidence about glyph contents. The
harness now captures a separate TLS context at original character insertion.

Character-insertion probe run `20261021-202645-30136` completed its 135-second
watchdog. The 124-second snapshot read 329 character records; none had an empty
packed payload. Font 1 characters #, $, 7, D, J, f and u all had nonempty metrics,
packed bytes and assigned hardware-block records. The 129-second capture still
shows missing J/D/#/$ and some numeric 8s, while f/u/7 are visible. This points
toward upload/drawing state; it does not prove a specific GPU-cache defect because
the snapshot and image are five seconds apart and CPU bytes have not yet been
compared with actual GPU atlas contents.

The second snapshot found TLS+F4 null after a later insertion callback. To avoid
following a different thread context, the harness now retains the last nonnull
cache address observed at insertion, separately from the general loader context.
This final address-retention change needs native verification on the next run.
No map, font package, executable or GPU DLL was changed. Four parser tests pass.

### CPU atlas contains the missing glyph regions

`font_cache_probe.py` now follows original texture references at hardware cache
0x827DC538+0x18/+0x1C. Native upload code 0x8246C1E4..0x8246C3C0 establishes the
bitmap dimensions, 16-bit linear row writes and texture-unlock path. The texture
fetch fields are interpreted using the installed SDK's `xenos.h`; dimension,
format, tiling, pitch and glyph-rectangle bounds are checked. It reads CPU-visible
physical memory only, not host GPU texture contents. Hardware-slot keys must
match the cached character key before a rectangle is measured.

Run `.local/loading-traces/20261021-203304-22872` completed at 135 seconds. Both
124.016 and 128.016 second snapshots succeeded with the pinned cache address
0x82990800 and 329 character records. Atlas is a 512x512 linear format-15 texture,
512-pixel pitch, CPU alias 0xA3EC6000, descriptor 0x4071A1D0. Font-1 #/$/7/8/A/B/D/
J/O/f/u regions all have matching hardware keys and nonzero bytes; each region's
SHA256 is identical across the two snapshots. Examples: J has 352 nonzero bytes,
D 386, # 440, dollar 396. The 129-second native capture still lacks J/D/#/dollar
and numeric 8 glyphs. Therefore the failure remains after CPU character data and
CPU atlas population, pointing to synchronization/upload/drawing. Exact GPU
contents and alpha-channel correctness have not yet been measured; this does
not certify the responsible host code or justify a speculative engine patch.

The atlas probe adds one synthetic row-pitch/rectangle test; all five font-probe
tests pass. Output contains hashes/counts/metadata, no exported font image or
new installation. Current deployed map, runtime and GPU DLL remain unchanged.

### Native resource residency comparison (2026-10-21)

`trace_loading.py --sample-resource-cache` observes the original resource page
table from compact/move calls and reads its LRU allocation list every five
seconds from 105 seconds. `resource_heap_probe.py` maps fields from original
XEX 822C2058 and 8229819C/822981D8; it does not import PC-build capacities.
Bounds, datum salts, links, overlaps, cycles and changing heap headers are
checked. Five focused tests pass, including fragmented free-space accounting.

Gulch run `20261021-204234-34676` produced six valid samples: 1,180 allocations,
230,277,120 occupied bytes (219.609 MiB). From 110 seconds its pool capacity is
340,856,832 bytes (325.066 MiB), with 110,579,712 free bytes (105.457 MiB), all
in one contiguous extent. The first sample has slightly less capacity/free
space, but identical occupancy. This measures resident resource allocations,
not the 460.8 MiB inventory of every referenced resource page.

Original Sandbox run `20261021-204500-36868` reaches 237,494,272 occupied bytes
(226.492 MiB), capacity 288,829,440 (275.449 MiB), and 51,335,168 free bytes
(48.957 MiB) at 120/125/130 seconds. Its 115-second sample was rejected because
the heap changed while reading; do not treat that sample as zero or valid.
The 129-second native capture was inspected: original Sandbox architecture,
first-person weapon and Slayer HUD are visible. Both runs ended at their
135-second watchdogs. Gulch used the previously verified route without a new
capture; these readings do not independently reverify its visuals.

`work/forge-world/resource-residency-comparison.json` retains input map hashes,
samples and the rejected sample. The new evidence rules out exhaustion and
fragmentation of this resource pool in the measured Gulch starting scene.
It does NOT certify total retail 512 MiB usage, all camera regions, vehicle
loads, or a populated Forge budget. Existing total-backing comparison and this
pool measurement are separate scopes. No map, runtime or GPU binary changed.

### Fixed rock lines: cliff-detail mip correction (2026-10-21)

The user reports vertical lines fixed on rock faces and suspects detail rather
than diffuse. Readback of candidate bitmap 10034 confirms that the BC1 base
payload exactly matches source `forge_halo_cliff_detail_detail` (512 squared),
but the previous candidate retained only one of its ten authored mip levels.
Original Last Resort `zan_cliffs_detail_dif` is also 512 squared with ten levels;
Cold Storage's comparable flood detail textures have eight/ten. The rock
material's detail transform remains the source-authored (250,250,0,0).

Forge conversion now opts that shared cliff-detail texture into the existing
native packed BC mip encoder. No diffuse edits, new textures, transform changes
or detail suppression are applied. `audit_forge_mips.py --include-cliff-detail`
independently verifies all 274 levels across 29 textures against source bytes,
using the pinned TagTool decoder. This includes the ten BC1 detail levels;
the normal-only audit remains the default for older candidates.

New candidate `work/forge-world/sandbox-detail-mips.map` is 138,252,288 bytes
(32 KiB above the previous map), SHA256
`f86e6ef34bc418b0aea1c3d7328034a3c57b213bac068f7b47572ed1a9c6d16a`.
The detail resource grows from 131,072 to 192,512 resident bytes (60 KiB).
Build verification checks 710 collision trees / 42,237 packed nodes; all 22
focused Forge tests pass. This repairs a demonstrated sampling discrepancy;
it does not by itself prove the reported fixed lines are gone.

Native run `20261021-205614-3120` loaded the deployed detail-mip candidate and
ended at its 140-second watchdog. Both 116000/134000 ms native captures were
inspected sequentially: expected Gulch terrain, weapon/HUD and the changed
camera position are visible; cliff detail appears less grainy, and terrain
remains present after turning/walking. Vertical features remain visible, so
the user's fixed-line report is still open; these captures do not establish
that every feature is either authored rock structure or a conversion defect.
Only the current detail-mip map and previous sky-animation map are retained;
the older contained candidate is superseded. No engine or GPU changes.

### Vertex fidelity and first vehicle check (2026-10-21)

`audit_forge_vertex_payload.py` reads source and serialized candidate resources
without invoking the converter. Across the two BSPs it checks 137+29 primary
buffers / 120,027+25,985 vertices: position/UV bits are identical after endian
decoding, and normal/tangent/binormal component error stays within half of one
native quantization step (maximum 0.000978265). This excludes introduced UV
changes in these streams; it does not certify source seams, shader evaluation,
lightmap/PRT streams, or reconstructed water. Report:
`work/forge-world/vertex-payload-audit.json`, with both map hashes.

`trace_loading.py --forge-vehicle-check --seconds 165` adds a process-local
route from Forge creation to attempted Banshee entry/flight. Original Sandbox's
scenario vehicle palette starts with `objects/vehicles/banshee/banshee`.
Run `20261021-210121-20500` on the deployed detail-mip candidate ended at its
165-second watchdog. All three native captures were inspected sequentially:
125000 ms shows a created Banshee and Forge budget 1480, 142000 ms shows the
occupied Banshee in third-person at the cliff, and 160000 ms shows it flying
over water facing the distant shore. Capture timing and observer wall-clock
times are separate clocks; do not assume exact frame/sample correspondence.

Observer samples move from approximately (-41.18,-196.06,2.70) at 140 seconds
to (27.46,-191.54,23.25) at 164 seconds. This proves creation, entry and flight,
not collision/containment acceptance: the seaward path after the cliff needs
checking against source/converted collision before calling it valid. It did
not approach the curved split at Y roughly -20 to -55. Resource occupancy
remains 230,338,560 bytes, with 110,579,712 free bytes in the stable late
samples. Two changing-heap samples were rejected, not treated as valid.
Fixed rock lines, menu glyphs and full budget/containment acceptance remain open.

User confirmation, 2026-10-21: **rock lines are fixed** with the detail-mip
candidate. This supersedes the earlier open visual-line observations. Keep
the authored mip correction; no further rock-material alteration is needed
for that report.

`audit_forge_camera_collision.py` compares the recorded observer segments from
140 seconds in run `20261021-210121-20500` against source and converted main
BSP collision. In the path's XYZ bounds plus one unit, all 400 triangle
positions match exactly, and neither mesh has a segment intersection. The
earlier exploratory Y-only corridor contained 1,614 triangles; the repeatable
audit uses tighter XYZ bounds. Report `banshee-camera-collision-audit.json`
records map and trace hashes. This is evidence against lost main-BSP surfaces
on that path, not proof about the vehicle's swept shape, center, or instance
collision. Three analytic tests cover crossing from either side, missing the
triangle while crossing its plane, parallel paths and paths too short to hit.

### Boosted vehicle containment fails (2026-10-21)

Run `20261021-210937-16988` used `--forge-vehicle-check
--vehicle-boundary-flight --seconds 180` on the unchanged detail-mip candidate.
The process-local route creates and enters the stock Banshee, turns at 142 s,
then holds forward and boost from 143 to 178 s. The 180-second watchdog ended
the run. Only the 160000 ms native capture was produced and inspected: it
shows an occupied, boosting Banshee with surrounding terrain. The requested
176000 ms capture is absent; it must not be counted as visual evidence.

Observer samples independently establish a substantial crossing: at 165.281 s
the Gulch margin is +11.55 units, at 170.297 s it is -41.73, and at 179.297 s
it is -146.91 (position 71.30, 91.91, 41.30). This is far beyond third-person
camera offset. **Vehicle containment fails.** The earlier monitor pushback
check was not sufficient acceptance for the shared boundary. Late resource
occupancy remains 230,338,560 bytes with 110,579,712 bytes free in the measured
resource pool; that is not certification of the full console memory budget.

Microsoft's [Halo 3 soft-ceiling guide](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/guides/softceilings)
distinguishes pushback from hard collision. Its introductory vehicle wording
is inconsistent with its later discussion, so it is not a reliable basis for
assuming vehicle enforcement. Next investigate original-disc collision-only
barriers and their native surface/physics setup before implementing the split
as hard collision. Do not change stock Banshee behavior or engine physics to
compensate. The rock-line issue remains closed by human confirmation.

### Original-disc hard-boundary research (2026-10-21)

`audit_native_barriers.py` now records map SHA256, main collision surfaces,
their render-triangle mapping counts, material indices, and reachable native
physics keys. It validates native key/table bounds. Run against original
`sandbox`, `shrine` (Valhalla), `sidewinder` (Avalanche), `zanzibar` (Last
Resort), and `snowbound`; report `work/forge-world/stock-barrier-research.json`.
The current candidate comparison is `gulch-barrier-research.json`.

| Map | No render triangles and material index -1 |
| --- | ---: |
| Sandbox | 176 |
| Valhalla | 1,722 |
| Avalanche | 1,583 |
| Last Resort | 191 |
| Snowbound | 456 |
| Current Gulch main BSP | 0 |

Sandbox's large outer-wall/ceiling examples have surface flags 0, no render
mapping, material -1, and physics keys of family 1 with subshapes 0 through 4.
For example, surface 4 spans X -166.21..25.49, Y 132.53, Z -15.18..123.73;
surface 7 is a ceiling at Z 123.73. Do not identify these through the
`Invisible` flag: stock surfaces with that flag include ordinary material
assignments, and the large shell surfaces do not have it. Avalanche and Last
Resort also contain no-material surfaces using subshape 5. These are observed
serialized layouts, not an assertion that every unmapped surface is a map
boundary or that all subshape families are interchangeable.

Native keys encode family in bits 29..31, subshape in bits 16..18, and surface
or instance index in bits 0..15. Interpreting native keys using MCC's 26-bit
index mask incorrectly mixes the subshape into the surface index. The audit
uses the native layout. Cluster MOPPs contain instance indices in the sampled
stock/candidate clusters; the root BSP MOPP contains surface and instance
families. A main-mesh divider therefore needs matching root physics-tree
coverage and zero render mappings, not merely additional collision polygons.

The [TagTool collision MOPP generator](https://github.com/TheGuardians/TagTool/blob/master/TagTool/Havok/CollisionMoppGenerator.cs)
provides the offline polygon compiler input format, but does not establish
the runtime meaning/geometry of the root BSP's subshape families. That is the
remaining implementation research before inserting a solid divider. No
unverified boundary patch was deployed, and the current rock-fixed map stays
installed. No engine, stock vehicle, or gameplay tuning was changed.

### Hard-divider implementation (2026-10-21; occupied vehicle confirmed)

Original `default.xex` SHA256
`18816c1da58b1371e440741fadab1df8e6e6ecca7c5b81952f2d23ceec797313`
resolves the physics-key question: at 0x822738B0..0x822738E4, family 1
extracts bits 16..28 and compares them with the object collision-category
mapping at 0x82270378. Value 5 skips that comparison. The equivalent gate
appears at 0x821153C4..0x821153F8. Thus the observed 0..4/5 variants are
category selectors in these gates, not evidence of five different polygon
shapes. The family-1 surface lookup at 0x82113F84..0x821140D4 uses the low
16-bit index. Read-only disassembly is retained locally as
`reference/native-bsp-shape-filter.txt`.

`forge_gulch_hard_boundary.py` adds 16 two-sided collision triangles along the
same eight-segment curve, with no material or render-triangle mapping. Existing
surface and edge indices remain stable. The collision tree is rebuilt and
overlaid with authored visibility cells as before. The main physics MOPP keeps
the existing subtree byte-for-byte and adds a conservative branch for the 16
new surfaces using category 5. Overlapping Z splits cover the BSP's complete
world-Z bounds, checked against the original MOPP coordinate domain. This
adds up to 16 narrow-phase candidates per query; runtime cost and containment
must be measured, not inferred from terminal-key coverage. The existing soft
divider remains for gentle pushback.

The offline TagTool builder rejected the first attempt due to its empty-leaf
verifier: it initializes an empty leaf's reference index to UINT_MAX, then
rejects it as out of range before its explicit empty-leaf check. The local
compiler now includes hash-pinned builder source with one narrow correction:
accept count 0/index UINT_MAX together. Other validation stays active. This
changes the offline converter only, not OpenH3M or the original game. Source
and diagnostic helper downloads remain ignored and hash-checked; diagnostic
outputs stay beside the repo-local compiler.

Focused tests cover crossing every divider segment in both directions at
four elevations, the no-material assignment, old/new MOPP key preservation
through retail translation, and rejection of uncovered MOPP coordinate bounds.
Passing these does not prove vehicle/Forge containment, over/under/end escape
prevention, or visual correctness. The native acceptance run is still required.

Candidate `sandbox-hard-divider.map` is 138,272,768 bytes (20 KiB above the
rock-fixed candidate), SHA256
`4656e4e708832f8ba876a7a7d16ae4750c5b09b73d4289379893db740746f339`.
The serialized audit finds exactly 16 new null-material/unrendered surfaces,
each with category-5 physics keys, and still 2,152 instance keys. Rebuilt
collision/visibility contains 65,635 nodes, 24,950 planes and 39,215 leaves.
`hard-divider-spatial-audit.json` records 31,479 probes / 30,115 non-solid
cluster checks, with no solid-space or cluster mismatches. All 28 focused
Forge tests pass. This candidate is staged for native acceptance; the
rock-fixed candidate remains the rollback.

Native run `20261021-214014-26272` ended normally at the 180-second watchdog
with all six tracked hash checks passing. Both 160000/169000 ms captures were
inspected sequentially: occupied boosting Banshee over water, then at/below
water level. The route descended and ended at (120.94,-80.83,0.67), still
24.87 units inside the divider. **This is inconclusive for containment**,
not a pass. Late measured resource occupancy was 230,375,424 bytes, with
110,579,712 free bytes. The follow-up route turns farther toward +Y, climbs,
then levels before the coast; it must reach the divider to be accepted.
Only the hard-divider candidate and the human-confirmed detail-mip rollback
are retained; the older sky-animation map was removed after a confinement
check. No additional installation or engine build was created.


### Human acceptance of the occupied-vehicle divider (2026-10-21)

The user drove run `20261021-214420-25492` and explicitly confirmed:
"It stopped the occupied Banshee." The user then closed this part of the task.
This establishes the requested occupied-Banshee divider behavior; do not repeat
that acceptance run or describe it as an automated flight. The sampled viewpoint
approached the Y=-55 segment and stopped alongside it. Both native captures were
inspected: the later captures show the player on foot, so the occupied-vehicle
result is attributed to the human's direct observation, not those still images.
The deployed candidate remains `sandbox-hard-divider.map` with the hash above.
The rock lines are also human-confirmed fixed. Move on to the remaining menu
rendering issue and whole-console memory accounting. Do not interpret this
acceptance as an exhaustive survey of every boundary or worst-case Forge load.


### Current candidate budget checkpoint after divider acceptance

Refreshed `work/forge-world/current-resource-footprint.json` against original
Sandbox and Avalanche. Current file size is 138,272,768 bytes (131.867 MiB),
tag allocation 31,588,352 bytes (30.125 MiB, exactly 12 MiB above Sandbox), and
all referenced uncompressed pages 483,273,176 bytes (460.885 MiB). The page
inventory includes optional/streamed resources and must not be added as if it
were simultaneous residency. It is not a whole-console memory total.

The accepted user-driven run `20261021-214420-25492` has eleven valid resource
samples, peak occupied 230,375,424 bytes (219.703 MiB), minimum free 109,727,744
bytes, and all six final hash checks passing. Thus this flight did not exhaust
the resource pool. Original Sandbox's previously measured occupancy is
237,494,272 bytes; these are different workloads, not a worst-case guarantee.

Source inspection reconfirms why the existing whole-memory observer cannot
certify retail fit: `MmQueryStatistics_entry` in the host SDK supplies placeholder
kernel/title counters and the host's virtual/XEX heaps have independent backing.
`xmemory.cpp` also reserves 16 MiB for GPU writeback before title startup.
Subtracting that reservation alone would be an unjustified console pass. Retain
`retail_console_budget_verified: false` until accounting includes actual retail
system overhead and the title's simultaneous allocations. No budgets or engine
behavior were increased or changed to obtain these numbers.


### Font pixel-component diagnostic (2026-10-21)

The read-only font probe now records raw physical-order nibble histograms for
format-15 (4:4:4:4) glyph rectangles, plus fetch endian and swizzle fields. This
avoids treating nonzero RGB bytes as proof of nonzero alpha. Five parser tests
pass, including asymmetric per-component values and native row-pitch handling.
No image payload is exported by this probe and no engine binary changed.

Run `20261021-215352-10124` completed at 135 seconds with six hash checks passing.
At 124.078 and 128.078 seconds, the atlas had endian mode 1, swizzle 1546, and
matching hardware keys. Raw component nonzero pixel counts were identical in
both samples: J=(38,173,173,173), D=(81,191,191,191), #=(73,220,220,220),
$=(72,198,198,198), 8=(81,192,192,192). These rule out an entirely zero component
in those CPU rectangles at the sampled times, not a GPU upload/drawing failure.

The single native capture `proof-loaded.png` was inspected and shows an occupied
Ghost, terrain and HUD, not the requested Forge creation palette. Accordingly
this run is NOT menu reproduction or visual acceptance evidence. Physical
controller values are present in the runtime input log. Do not label this as an
automated menu pass or conclude that missing glyphs are fixed. GPU-side atlas
contents and the actual failing menu draw remain unresolved.


### Combined automated diagnostic run (2026-10-21)

User requested consolidated diagnostics with process-local automated control,
not a user-driven session. Run `20261021-215909-18632` combined the Forge palette
route, startup allocation observation, resource/CPU-font snapshots, 1,024 GPU
draw register records, bounded thread/stall samples and native capture. The
new `--draw-after-seconds 130` option schedules draw sampling after palette open.
All outputs remain local; draw registers are automatically compressed and the
uncompressed copy removed after readback verification.

The 125000-ms capture was inspected: the correct Weapons palette is open over
Gulch, with OBJECT, Done, Summary, #, $, and 8 all visible. This is a readable
menu under consolidated diagnostics, not proof of a fix. No map or executable
changed. The requested 170000-ms capture is absent, so there is no later visual
acceptance. The 180-second watchdog ended the child; all eleven tracked hashes
passed. Two thread reads were partial and one resource snapshot changed during
reading; these rejected observations are retained explicitly.

Offline inspection of all 1,024 recorded draw states finds no texture fetch
bound to the sampled CPU font-atlas base 0x03EC6000. Thus these draws do not
establish GPU font contents. Future draw diagnostics must target the atlas
binding rather than assume the first N scene draws include the menu. Do not
repeat the same broad draw sampling. Summary:
`.local/loading-traces/20261021-215909-18632/combined-diagnostic-summary.json`.

Current-candidate startup statistics match the earlier stock Sandbox baseline:
489,107,456 physical heap bytes and 51,335,168 unique virtual/XEX bytes. There
were no observed failed physical allocations. Resource occupancy remains
230,375,424 bytes. `work/forge-world/guest-memory-current-diagnostics.json`
preserves incomplete-event/runtime-accounting qualifications; retail 512 MiB
verification remains false. The diagnostic slowdown means this run is unsuitable
for performance acceptance.


### Three requested harness comparisons (2026-10-22)

Exactly three automated runs completed on unchanged hard-divider map SHA256
`4656e4e708832f8ba876a7a7d16ae4750c5b09b73d4289379893db740746f339`,
using the same executable, GPU DLL and shared cache. Earlier harness behavior
was reproduced through the existing options; no older engine/map was deployed.

| Harness configuration | Native run | Capture | Result |
| --- | --- | --- | --- |
| Earlier palette-only, late attach | 20261022-061128-16468 | 124000 ms | Complete palette text |
| Earlier CPU font probe, late attach | 20261022-061354-18916 | 129000 ms | Complete palette text |
| Combined startup memory/font/resource/draw/thread diagnostics | 20261022-061643-34524 | 125000 ms | Complete palette text |

All three `proof-loaded.png` captures were inspected individually in order.
Each shows Gulch terrain, monitor HUD and the Weapons creation palette, with
OBJECT, Done, Summary, #, $, and the numeral 8 present. First two watchdogs
ended at 135 seconds with 6/6 hashes passing; combined ended at 180 seconds
with 11/11 passing. Font runs each collected two snapshots; combined also
collected 1,024 draw records, automatically compressed by the harness.

Combined-run diagnostic exclusions: resource snapshot at 110.016 seconds changed
while being read; snapshot at 115.110 reported unexpected capacity/unit; a
thread read at 117.953 was partial. These are rejected measurements, not valid
zero readings or proof of an actual game allocation failure. The first two
runs logged no diagnostic errors. Local machine-readable comparison:
`work/forge-world/three-harness-menu-check-20261022.json`.

The historical missing-glyph fault did not reproduce in any of these three
runs, including the earlier lighter harness settings. No rendering fix was
introduced, so causation remains unknown. Stop repeating this menu checkpoint
without new evidence of failure; preserve the historical issue as a monitored
regression. These captures do not certify whole-console memory or performance.


### Required versus optional resource demand (2026-10-22)

Extended the existing offline footprint audit to union resource-page identities
across every manifest. This deduplicates overlap between global/static/dynamic
BSP manifests and separates required physical pages from optional physical pages
of resources selected by required bitsets. Alternative manifests are included,
so this remains a conservative inventory, not a simultaneous-residency claim.
No assets, gameplay limits or runtime allocations were changed; no game rerun.

| Map | Required-selected resources, required physical pages | Same resources including optional pages | Streamed-selected page union |
| --- | ---: | ---: | ---: |
| Current Gulch | 219.428 MiB | 329.506 MiB | 131.379 MiB |
| Original Sandbox | 139.696 MiB | 274.943 MiB | 139.357 MiB |
| Original Avalanche | 171.583 MiB | 303.952 MiB | 144.865 MiB |

Columns overlap and MUST NOT be summed. Gulch's 219.428 MiB required-page
inventory is close to the measured 219.703 MiB allocation occupancy, consistent
with that starting scene holding the required pages plus allocation rounding.
This is evidence against treating the entire 460.885 MiB reference inventory
as required simultaneous residency. It is not proof of page-by-page residency.
The 110.078 MiB difference to the second column is optional physical-page demand,
not an additional mandatory allocation. The current 105.457 MiB free resource
extent does not accommodate every such page at once; native streaming/eviction
behavior remains relevant. Do not remove authored content or raise the pool to
force that conservative inventory resident.

The whole-console gate still needs retail memory accounting: PC physical/virtual
heap statistics have known placeholders and independent backing. Neither the
near match above nor a successful PC run is a substitute for that gate. Current
static results are in `work/forge-world/current-resource-footprint.json`.


### Text-glitch investigation: corrected font alias address (2026-10-22)

This supersedes the earlier CPU-atlas and "no font draws" conclusions. The
original texture header contains encoded address 0xE3EC6000. Retail lock path
82475BA8 -> 8217B810 -> 8217B8B8 -> 82155D10 translates it to physical
0x03EC7000, not 0x03EC6000. Instructions 82155DB0..82155DC4 implement the bias;
the SDK also explicitly applies a 4-KiB offset to E-range physical aliases.
Read-only disassembly: `work/forge-world/native-font-lock.txt`.

The CPU font probe incorrectly masked away the alias without applying its bias,
reading one page before the glyph pixels. Nonzero-byte counts, glyph-region
hashes and nibble histograms from those old probes therefore do NOT establish
correct glyph pixels or alpha. Packed character data and hardware-slot records
were independent reads and remain valid. The probe now translates the alias
correctly and bounds the physical extent. Its five tests pass, including a
fixture whose pixels exist only at the corrected address.

Re-reading saved GPU records using physical 0x03EC7000 finds the font atlas
bindings previously missed by the incorrect address filter. The 512x512,
format-15 fetch has word 1 = 0x03EC704F. Corrected binding records are saved in
`work/forge-world/font-address-correction.json`. Thus a new broad draw run is
unnecessary. This fixes our diagnostic addressing, NOT the user's rendering
fault. The three readable captures remain valid; GPU pixel contents and the
failing glyph draw still need diagnosis with the corrected address.

The user has redirected active work to the text glitch; do not divert into
memory-budget work while this investigation is active.


### Text glitch reproduced with corrected pixel addressing (2026-10-22)

One targeted font-probe run, `20261022-103051-32368`, sampled the corrected
physical atlas 0x03EC7000 at 124.093 and 128.093 seconds. The native 129000-ms
capture was inspected: Gulch Weapons palette is open, J is absent from OBJECT,
# and dollar symbols are missing, and the budget text is absent. D in Done and
numeral 8 are visible this time. This is a verified recurrence after the three
clean runs, so the text issue is active, not merely a monitored regression.

All sampled glyph keys match their hardware slots. At the CORRECT address, J,
#, $, D, 8 and A have nonzero components and identical per-glyph hashes across
both snapshots. J has 38 nonzero high-nibble pixels, # 73 and $ 72; the other
three components cover their full glyph rectangles. Therefore an entirely blank
CPU glyph rectangle does not explain this occurrence. No font package, map,
executable or GPU DLL changed; six integrity checks passed and no diagnostic
errors occurred. Local concise evidence:
`.local/loading-traces/20261022-103051-32368/corrected-font-summary.json`.

Source review identifies a candidate lost-invalidation window: shared-memory
upload sets validity and enables CPU-write callbacks before copying data;
texture-specific watches are registered later by CommitPreparedTextureLoad /
MakeUpToDateAndWatch. A write between those operations needs to be tracked
through page validity and texture dirty state. This is a hypothesis, NOT a
confirmed cause, and no speculative engine patch was deployed. The next
instrumentation must distinguish actual GPU atlas/upload contents from CPU
contents and verify the missing glyph draw, using the corrected address.


### Bounded staging-upload recorder (2026-10-22)

`halo3mp/patches/rexglue-sdk-upload-probe.patch` adds disabled-by-default host
D3D12 diagnostics. It records the exact staging bytes passed to CopyBufferRegion,
clipped to a configured physical range (at most 1 MiB), capped at 32 MiB per
process. It changes no game logic, map format or texture data. Records are four
little-endian uint32 words (magic 0x31505546, sequence, address, length), followed
by the submitted bytes. The native logger reports sequence/address/length and
explicit write/limit failures. This is upload staging evidence, NOT GPU texture
readback. Defaults generate no files.

The harness's opt-in `--font-upload-probe` confines the output to the run folder
and selects the verified 0x03EC7000 / 512-KiB font range. It requires the diagnostic
GPU plugin; do not combine it with old-plugin hardcoded GPU draw addresses.
Build used the existing SDK tree and `out/pacing-release` target `rexgpu-xenos`;
only shared_memory.cpp recompiled. There was no separate game installation.

Run `20261022-103802-27776` used a temporary diagnostic renderer and the existing
process-local Forge palette route. The 129000-ms native capture was inspected:
all menu letters/symbols are present. Twenty upload records cover the entire
524,288-byte atlas. `compare_font_uploads.py` reconstructs overlapping uploads
in order, checks record/range/rectangle bounds, and compares them with the last
correctly addressed CPU glyph snapshot. All 81 comparable glyphs match exactly,
including J/#/$/8/D/A. Report: `font-upload-comparison.json` in the run directory.
This establishes a good-upload reference; the failure did not reproduce under
this additional instrumentation and remains unfixed.

The wrapper restored and SHA256-verified the normal GPU DLL in `finally`:
`c9f3b77b65d46dbfc382f6b16e5f44c6dac883f2253c62887fcc165aa6087e4c`.
After verifying the restored binary, its temporary backup was removed inside
the repository. The map and executable were unchanged. The diagnostic plugin
remains only in the existing build output for further focused investigation.
