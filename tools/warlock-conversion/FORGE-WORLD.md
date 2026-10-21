# Forge World / Sandbox conversion

Status (2026-10-21): **incomplete, blocked at retail collision representation**.
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
