# Warlock conversion

This pipeline converts the MCC Warlock map into retail Halo 3 Mythic cache
structures in Blackout's slot. It changes map data only. OpenH3M, the original
XEX, and the original disc maps are not modified. Generated assets stay private
under `C:/X360/ISOs/H3M/.local`; Git contains the process and schema definitions.

The next experiment, Resuscitation in Last Resort's slot with its full Forge
palette, is tracked in [RESUSCITATION.md](RESUSCITATION.md). Both maps now load from one shared installation and launcher.

## Binding asset policy

Use original Xbox 360 Halo 3 assets and their native dependencies, visuals and
behavior whenever an equivalent exists anywhere on the disc or in shared resources.
Convert custom/MCC content only where Halo 3 has no equivalent. This applies to
all maps and Forge palettes, including future DLC. No Halo 2-faithful substitutes.
Only an explicit human-user instruction can override this policy; record its scope.
See [repository instructions](../../AGENTS.md).

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
