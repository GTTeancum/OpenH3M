# Forge Island

Forge Island is the western half of the identified non-AI MCC Forge World map.
It retains the island, Sanctuary and waterfall side of the user's revised
2026-10-22 divider. The beach cave and mainland shoreline facing the island
belong to Gulch. Both halves retain the complete surrounding visual geometry.
The previously installed Gulch still has its earlier divider; this addition
does not silently rebuild or replace that accepted map.

The user explicitly extended the Reach Forerunner scenery exception to both
halves on 2026-10-22. Weapons, vehicles and other existing Halo 3 assets remain
stock Halo 3. The CE Magnum and DMR discussion was assessment-only.

## Conversion

Use the shared conversion pipeline with `--slot sandbox --forge-island`.
Sandbox is the original-disc conversion basis, not the deployed map identity.
The DLC identity is `forge_island`, title **Forge Island**, map ID **1731**.
Existing custom IDs and stock maps remain unchanged. No separate engine build
or duplicated game installation is required.

`partition_forge_collision.prepare(..., 'island')` selects the opposite side of
the approved polyline. Rebuilding is mandatory even below the plane limit,
because the rebuilt collision includes the solid two-sided divider. Soft
containment reverses its divider normals to push into Island; the original
outer containment remains unchanged. Visibility, seam mappings and visual
geometry remain shared in design, independently serialized in each map.

`forge_island_spawn.py` checks the source mesh under (50, 50), requires exactly
one upward-facing terrain hit near height 15, and adds 0.35 clearance. It moves
both the authored initial-spawn marker and scenario fallback start. The marker
faces the open coast toward Sanctuary. The source's original start is in Gulch.

Run from the repository root, with outputs and temporary files inside it:

```powershell
$env:TEMP = "$PWD\.local\build-temp"
$env:TMP = $env:TEMP
& C:/Users/smmel/AppData/Local/Programs/Python/Python312/python.exe -B -c "import capstone,sys,runpy; from pathlib import Path; sys.path.insert(0,str(Path('tools/warlock-conversion/snapshot/tools').resolve())); runpy.run_module('build_scenario_checkpoint',run_name='__main__')" `
  --project C:/X360/ISOs/H3M --slot sandbox --forge-island `
  --source D:/SteamLibrary/steamapps/workshop/content/976730/3597611181/maps/forge_halo.map `
  --basis C:/X360/ISOs/H3M/maps/sandbox.map `
  --disc-maps C:/X360/ISOs/H3M/maps --xex C:/X360/ISOs/H3M/default.xex `
  --sound-bank 'D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo3/fmod/pc/sfx.fsb' `
  --decoder ../tools/vgmstream-r2117/vgmstream-cli.exe `
  --output work/forge-world/forge-island-ready.map `
  --report work/forge-world/forge-island-ready.json
```

Choose a fresh output when rebuilding. `build_dlc_payload.py --map forge_island
--source-map work/forge-world/forge-island-ready.map` stages the distinct identity;
its other required arguments are `--converted`, `--stock`, `--output`, and
`--report`. Stage the existing four maps through hardlinks, not another copy.
`build_dlc_previews.build(..., names=['forge_island'])` supplies its five native
preview variants from the installed source-map artwork. Build and verify the
LIVE package with the same tools documented in DLC-BUNDLE.md.

## Material compatibility

The full rebuild exposed `for_forge_gen_panel_04_dark_nocc`, which has no exact
stock shader combination. Native inventory found the resupply-capsule variant
with identical bump/detail, two-lobe lighting and emission, plus diffuse-alpha
specular masking. A private base-map copy with white alpha makes that mask
neutral. RGB remains byte-identical at the converted resolution; other users
of the original bitmap are unchanged. This does not introduce a new shader or
change the engine. The real-source encoding readback and synthetic regression
test cover both properties.

The water update's 30 water and 20 waterfall animation functions are retained,
as are native waterfall blending and the driftwood material fix. The inherited
Forge grid rendering issue remains separate, unresolved work.

## Evidence and limits

- Collision rebuild: 15,366 planes / 32,768 limit; 25,666 leaves, 15,221 surfaces.
- Serialized collision verification: 706 trees, 40,519 packed nodes.
- Map size: 128,659,456 bytes (122.7 MiB).
- 21 focused boundary, encoding, budget, visibility and lighting tests pass.
- Initial native run `20261022-214240-4536`: correct Island menu entry and
  preview; player on solid island terrain; terrain visible after turning and
  walking. All three captures inspected. Eleven observed resource hash checks
  passed. This run used the initial orientation, facing a nearby cliff.
- The first final-package Forge run `20261022-214857-43924` failed during
  startup in native BSP seam traversal (`820ABE50`). It is not acceptance
  evidence. Its fault report and diagnostic trace are retained.
- Diagnostic run `20261022-215550-38580` identified a call with cluster index
  255 against a 15-cluster BSP. The overlay had created 230 nonsolid leaves
  carrying this sentinel for original solid regions. The source and all 26
  stock Halo 3 BSPs have zero such leaves. The converter now represents those
  regions using the native solid-child sentinel, rather than a fabricated
  render-cluster index. The new regression test covers that spatial case;
  serialized BSP leaf tables are also checked against their cluster counts.
  This is a data-conversion correction, not an engine bounds-check bypass.

Console hardware, total 512 MiB residency and system-link are not verified.
Static page inventory is not total runtime memory, and includes streamed pages
that need not coexist. The user's deferred console-memory verification remains
deferred; no native limits are raised.

## Accepted build and activation (2026-10-22)

Final native run `20261022-220533-12624` loaded Forge Island in Forge and
completed its 180-second watchdog without a crash. Both native captures were
inspected: island terrain, Sanctuary, waterfall cliffs, water and distant
landscape were visible. Eleven resource hashes passed, zero failed. During
continued boosted monitor flight toward the divider, position stabilized at
(50.134, -54.783, 60.55), with a positive Island margin of 0.217 units.
This checks monitor containment; an occupied Banshee was not tested on Island.
Evidence: `work/forge-world/island-runtime-validation.json` and the run's native
captures and logs in `.local/loading-traces/20261022-220533-12624`.

Final DLC map SHA256:
`96d62a150eddd1fd343d39b9c76b2e6c1d792dbbe7669a95d773854edac6e9cf`.
The five-map LIVE package is
`work/dlc/bundle/83666D12FEE8D3234F0010D50214FDFFC3F17E3D`
(762,945,536 bytes), SHA256
`4c3aed19c8a61e50b8273eb0b61213e591559258e298df2876755324f3a73e43`.
Native STFS comparison matched all 35 files. Activation verified their hashes
and preserved the previous four maps byte-for-byte. The existing executable
and bootstrap load `work/dlc/installed-current`; no new engine build was made.
The previous valid bundle is retained under `work/dlc/rollback/content`.
See `work/dlc/island-activation.json` and `work/dlc/island-ready-bundle.json`.

Automatic approval review rejected cleanup of superseded candidates as
“blocked by policy.” They remain listed in `work/forge-world/island-cleanup.json`;
cleanup has not been claimed complete or retried through another mechanism.
