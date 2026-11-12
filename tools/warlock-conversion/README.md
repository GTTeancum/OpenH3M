# Warlock conversion

For the separate four-map LIVE bundle, native installation, authorized
OpenH3M/RGH signature-check changes, and rollback, see [DLC-BUNDLE.md](DLC-BUNDLE.md).
That experiment gives the custom maps their own identities beside stock maps.
The replacement-map process below remains available as the earlier baseline.
For the 2026-10-22 sharp/grainy texture correction and repeatable incremental
restoration of authored mip chains, see [TEXTURE-MIPS.md](TEXTURE-MIPS.md).

This pipeline converts the MCC Warlock map into retail Halo 3 Mythic cache
structures in Blackout's slot. It changes map data only. OpenH3M, the original
XEX, and the original disc maps are not modified. Generated assets stay private
under `C:/X360/ISOs/H3M/.local`; Git contains the process and schema definitions.

The next experiment, Resuscitation in Last Resort's slot with its full Forge
palette, is tracked in [RESUSCITATION.md](RESUSCITATION.md). Both maps now load from one shared installation and launcher.

## Binding asset policy

For editing-kit-driven authoring before this MCC-to-native stage, see the
[Reach process](REACH-CONVERSION-PROCESS.md) and the new
[Halo 4 process](HALO4-CONVERSION-PROCESS.md). [Haven](HAVEN.md) is the first
Halo 4 workflow target; its official kit source inventory is pending H4EK.

Use original Xbox 360 Halo 3 assets and their native dependencies, visuals and
behavior whenever an equivalent exists anywhere on the disc or in shared resources.
Convert custom/MCC content only where Halo 3 has no equivalent. This applies to
all maps and Forge palettes, including future DLC. No Halo 2-faithful substitutes.
Only an explicit human-user instruction can override this policy; record its scope.
See [repository instructions](../../AGENTS.md).

Before importing any asset type, perform the required
[stock and shared-resource audit](ASSET-REUSE-AUDIT.md). Inventory what the target
already references from `shared.map`, reuse suitable native dependencies, and
check other original H3 maps before declaring an equivalent unavailable.

## MCC source schema versions

MCC format version 13 alone does not identify tag layouts. Older mod packages
can contain materially different scenario, object, model and Forge records.
Do not repair a failed block read with a blanket offset shift or rewrite the
source cache to resemble a newer build.

`snapshot/tools/source_schema.py` selects the retained April 2022 profile for
the verified cache build `Apr 20 2022 11:55:21`; existing contemporary MCC and
Xbox 360 caches retain their schema selection. The older definitions are pinned
to [Assembly ec339292](https://github.com/XboxChaos/Assembly/tree/ec3392924d4cc179b13c2f5218a46c61204b5400/src/Assembly/Plugins/Halo3MCC),
after the schema research/naming update and before the December layout change.
`reference/mcc-2022/manifest.json` records upstream blobs, 31 retained overrides,
19 structurally identical existing schemas reused, and the explicit Halo3
inheritance list. The existing Assembly license applies. The retained overrides
are checked against the upstream Git blob hashes.

Use `load_schema(cache, group)` in source readers; do not select a schema by
map filename. `inventory_conversion.py` and `object_dependencies.py` use it and
validate nested blocks, data bounds and tag datums before reporting. The shared
tests include old palettes, native packed references, invalid references and
independent mutable XML trees. Schema readability does not establish asset
equivalence, conversion support or runtime correctness.

The existing scenario, object, BSP, lightmap, resource, sound and material
readers now select source layouts through this resolver. Older Forge entries
and spawn records use their retained 48/108-byte layouts; 36-byte zone sets do
not read the newer appended four bytes. Known upstream capitalization changes
are normalized in freshly loaded trees after type/offset checks. The pinned
XML files remain untouched. The missing older decal flag names use the same
TagTool definitions already retained in the native/current schemas.

Desolation's older-source conversion now serializes through all existing stages,
passes native metadata/resource checks and enters gameplay in a private run.
Full runtime acceptance remains pending. The first older source and remaining
work are tracked in [DESOLATION.md](DESOLATION.md).
Continue using the existing converter, native-asset audit and acceptance checks.

When a map profile explicitly selects native Forge donor maps, the optional
`stock_forge_donor_maps` policy on the existing stock-palette stage assembles
their entries. Do not interpret "stock palette" as a request for scenery from
every map. `stock_forge_palette.py` defaults to Sandbox for
duplicate identities, retains native prices/limits and records alternatives.
It imports native dependency graphs and publishes missing English display text
once through the existing locale writer. It does not raise the scenario budget
or engine limits. Serialized label/price checks and native menu, creation and
resource-residency checks remain necessary; union inventory alone proves none
of those. Map-specific weapon substitutions and omissions belong in an explicit
profile, with the user's decision recorded, rather than broad name heuristics.
The native map variant has 256 quota rows, independently of its 640 object slots
and monetary budget. A map can load and create an early palette object while
its quota count already exceeds capacity. Desolation exposed exactly that case
(315). Reject oversized palettes before publishing; reserve capacity for placed
assets outside the palette and verify the actual native count. The reusable
`preflight_variant_budget.inspect_quotas` gives a conservative native-data bound.

For reusable donor evidence, `audit_resource_footprint.py --include-resources`
adds resource owners, physical page locations and manifest references to its
normal summary. These references are not a claim of simultaneous residency.
`audit_bitmap_reuse.py` compares authored 2D base payloads against untiled native
donors, including differently named copies. Unsupported/stripped resources are
reported separately; a hash nonmatch does not rule out visual equivalence.
Audited stripped-texture recovery is explicit, source-hash checked and attempted
only after all same-name native donor candidates fail. Preserve the consuming
native shader and bitmap settings, and report that absent original pixels
cannot be compared for bit identity.

## Current build

Current candidate: `.local/integrated/lockout-release.map`, 182,239,232 bytes
(173.80 MiB), down from 372,199,424 bytes (354.96 MiB). The tag heap is 23.56 MiB.
SHA256: `400c6ac9ef1e3454aab016c335511259ddbec139ace00817d49652f29b3e7560`.
Report: `.local/reports/warlock-release.json`.
The root `Run-CustomMaps.cmd` uses `.local/custom-maps-play`, containing both
Warlock (`lockout.map`) and Resuscitation (`zanzibar.map`). They share the engine,
disc assets, persistent cache and player profile. Logs remain per run.
The legacy PowerShell launcher names forward to this same launcher.
Choose **Custom Games > Blackout > Slayer**.

The builder retains the working scenario objects, collision, equipment, cannons,
teleporters and all 162 Forge palette entries. The owner tested those gameplay
features on the earlier expanded build. Runtime loading and visual checks are
recorded separately below; actual-console and system-link testing remain external
acceptance checks.

## Size and visual fixes

* Native retail maps use the same 3,268 external page descriptors. Original
  `mainmenu.map`/`shared.map` references remain byte-for-byte unchanged. Blackout,
  Guardian, Narrows, Construct and Sandbox were compared: each references 346
  mainmenu pages and 2,922 shared pages. Blackout itself is 137.09 MiB; the new
  conversion remains larger because it includes custom geometry and assets.
* 31 newly needed sounds reuse native retail codecs and packets instead of PCM.
  Native sound pages retain the uncompressed streaming codec used on the disc;
  deflating XMA packet pages caused decoder errors and is not supported here.
  Sounds with no matching retail donor retain the explicit PCM conversion.
* Stock textures retain native mip chains. For 72 large single-image textures,
  the separate highest-resolution mip is omitted while lower mips are preserved.
  Custom textures continue through the existing Xbox texture encoder.
* Unreachable basis tags/resources are removed using header globals, imported
  references and retail metadata schemas. Packed four-byte tag references are
  handled explicitly. Live resource fragments are repacked out of mixed pages,
  so retaining one asset no longer retains unrelated Blackout payloads.
* Native simulation definitions are rebuilt from live definitions in their old
  relative order, followed by imported definitions. Both peers must use the same
  converted cache; this is not a system-link certification.
* The new-metadata reserve is 8 MiB instead of 16 MiB, with explicit overflow checks.
* Packed vertex lighting conversion matches all 784 buffers in the accepted
  fallback, removing the neon lighting regression. Converted Warlock terrain and ordinary
  world materials suppress unstable specular/environment contributions that
  produce white floor speckles and reflective artifacts. Layer blending, diffuse
  lighting and normal maps remain. Stock materials, weapons and water retain
  their shading parameters. This is a reported matte-material approximation.
* All 586 BSP runtime decal indices are remapped with the scenario palette.

Remaining POC approximations include selected native shader/reflection substitutes,
frozen shader animation and reduced custom-texture resolution. See the report's
per-material notes. The source custom teleporter receiver omitted its hum; the
converter restores the native receiver's loop attachment, effect marker and
teleporter_active scale binding. The sender loop and pass-through event remain
identical to retail. Activation audio lives in shared.map; the loop packets are
local. Both sets of codec/packet data were compared with the original cache.
Audible teleporter playback still requires an in-game listening check.

## Build

Run from `C:/X360/ISOs/H3M/.local/OpenH3M-source`. Use a fresh output filename;
the builder refuses to overwrite existing maps. No earlier converted seed is needed.

```powershell
python -B tools/warlock-conversion/snapshot/tools/build_scenario_checkpoint.py `
  --project C:/X360/ISOs/H3M `
  --source D:/SteamLibrary/steamapps/workshop/content/976730/2977651586/maps/warlock.map `
  --basis ../../maps/lockout.map --xex ../../default.xex `
  --sound-bank "D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo3/fmod/pc/sfx.fsb" `
  --decoder ../tools/vgmstream-r2117/vgmstream-cli.exe `
  --output ../integrated/lockout-rebuilt.map --report ../reports/warlock-rebuilt.json
```

The report records input/output hashes, material approximations, native donors,
resource compaction, metadata usage and failure stage. Unsupported dependency
layouts fail explicitly. Decoder subprocesses and temporary files stay inside the
project. Original inputs are read-only; output is published only after checks.

## Verify and run

```powershell
python -B tools/warlock-conversion/snapshot/tools/test_lighting_coefficients.py
python -B tools/warlock-conversion/snapshot/tools/verify_native_resources.py `
  --map ../integrated/lockout-release.map `
  --report ../reports/warlock-release.json --disc-maps ../../maps
python -B tools/warlock-conversion/snapshot/tools/verify_compacted_cache.py `
  --map ../integrated/lockout-release.map --basis ../../maps/lockout.map
python -B tools/warlock-conversion/snapshot/tools/verify_teleporter_audio.py `
  --map ../integrated/lockout-release.map `
  --report ../reports/warlock-release.json --disc-maps ../../maps
```

Verification reconstructs native sound streaming segments and compares packets
and codecs to donors, checks retained/repacked original payloads and external page
descriptors, and validates serialized decal references during the build.

Prepare a **new** layout with `warlock_handoff.py prepare --project
C:/X360/ISOs/H3M --game ../warlock-play-new --map ../integrated/lockout-rebuilt.map`.
Layouts use hardlinks: never edit linked maps in place. The versioned
`Run-Warlock.ps1` launcher writes hashes and failure logs under `.local/warlock-runs`.
Its default watchdog is 180 seconds; the root CMD supplies the owner's longer limit.

The bounded native diagnostic requires the verified executable build:

```powershell
python -B tools/warlock-conversion/snapshot/tools/trace_loading.py `
  --project C:/X360/ISOs/H3M --exe D:/Programming/GitHub/H3M/OpenH3M.exe `
  --capture --seconds 165
```

It uses only process-local scripted input, native capture and debugger logging on
its own child. It refuses a parallel instance, records header/resource checks and
unhandled faults, and stops its child at the watchdog. No host UI input is sent.
Each trace records the deployed map SHA256. For repeated checks,
`--shader-cache-seed <prior-run>/cache/shaders` reuses the small shader cache
while keeping the new run logs and game caches separate.
A loading success alone does not establish correct visuals.

Final native evidence: `.local/loading-traces/20261018-204450-14384/`.
The deployed SHA256 above entered Slayer and stayed running to the 180-second
watchdog. `proof-loaded.png` was inspected: the visible floor/ramp has no bright
speckles and the earlier reflective world artifact is absent. Five resource
hash checks passed; no unhandled guest faults or audio decoder errors were logged.
Two preceding cold-start runs stalled before reaching the map and were rejected;
the successful run reused a small shader cache. No teleporter traversal/listening
check or physical Xbox/system-link test is claimed.

## Retention and provenance

Keep the accepted fallback `.local/candidate/lockout.map` and the current deployed
map. Remove superseded generated maps only after exact path/hash checks. Keep
small reports and useful native failure/visual evidence; never commit game assets,
binaries, caches or screenshots. Development history belongs in Git.

Additional dependency schemas come from
[Assembly revision fd14ef3](https://github.com/XboxChaos/Assembly/tree/fd14ef3c46135e9422966c6a64cd926fb0bd23fb/src/Assembly/Plugins/Halo3).
The pinned revision and added schema list are in `snapshot/reference/Assembly-schema-revision.txt`;
the original license is retained in `snapshot/reference/Assembly-LICENSE`.
