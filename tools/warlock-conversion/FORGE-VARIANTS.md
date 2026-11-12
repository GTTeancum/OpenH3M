# Reach Forge layouts

User decisions, 2026-10-23: port all five original layouts as selectable saved
Forge layouts sharing the existing map caches. Do not create five duplicate
maps. Preserve Reach Forerunner pieces on both halves; use stock Halo 3 gameplay
assets. The western half's display name is **Force Cove**.

| Original layout | Base map | Source placements |
| --- | --- | ---: |
| Hemorrhage | Forge Gulch | 473 |
| Asylum | Force Cove | 458 |
| Pinnacle | Force Cove | 378 |
| Paradiso | Force Cove | 629 |
| The Cage | Force Cove | 414 |

These counts include Reach game-mode markers and equipment; they are not final
Halo 3 object counts. Paradiso's only placement across the approved divider is
a jetpack pickup. Its structural layout belongs in Cove.

## Source and verified readers

Original read-only source:
`D:\SteamLibrary\steamapps\common\Halo The Master Chief Collection\haloreach`.
Use `maps/forge_halo.map` and the five `map_variants/hr_forgeWorld_*.mvar` files.
The supported cache build is `Jun 21 2023 15:35:31`, version 13.

`snapshot/tools/reach_forge_variant.py` decodes the version-31 Reach layouts.
All five object counts, slots, palette indices and labels agreed with an
independent decoder. The Cage's position comparison differs by less than
0.001 source units because of float rounding over its large world bounds.
`reach_forge_palette.py` resolves the original 145-entry palette and cache tag
addresses. `StringTable` now accepts its section-relative debug addresses.

`reach_resource.py` reads the shipped cache's `play` resource table (segments
at +60), verifies page size/CRC, and converts rigid/ambient-PRT buffers to
retail. Reach index descriptors have an extra word before their byte count.
All 60 render models absent from the H3 workshop source passed resource
conversion: 3,671,374 bytes of uncompressed native geometry. This inventory
includes utilities that will instead bind to stock H3 assets.

`reach-collision-bridge` uses the existing installed TagTool DLL read-only to
expand Reach collision supernodes. `reach_collision.py` writes the expanded
geometry into retail metadata. All 60 collision models serialized with valid
node/plane bounds, totaling 403,360 bytes including alignment.

`reach_physics.py` explicitly translates the 51 missing fixed architectural
physics models. These pass structural conversion. Reach Havok shape type IDs
differ from H3; Reach MCC MOPP headers are 80 bytes rather than H3's 48.
Reach material IDs must be resolved through native global material names.
The generic installed TagTool reader is **not** reliable for Reach object roots
or polyhedron physics layout and must not be used to copy those fields.

Research: Assembly ReachMCC/Halo3 schemas, TagTool collision/physics conversion
sources, Reclaimer MCC headers, HaloMapStudio and BlamNetwork variant formats.
Private source extracts and audit reports remain under
`work/forge-world/variants/`; no extracted assets belong in Git.

## Shared-map candidates and saved-layout format (2026-10-23)

`stage_forge_layout_assets.py` now adds the required architecture, collision,
physics, materials, attached lights and palette entries once per shared map.
Existing palette indices remain stable. The candidates are
`work/forge-world/variants/rigid-fixed/forge_gulch.map` (182,124,544 bytes) and
`forge_island.map` (147,722,240 bytes). Their palette/hash manifests are
`gulch-assets.json` and `cove-assets.json` in the same directory.

`convert_reach_layout.py` writes original H3 uncompressed `mapv` version 12.1
with a 0xE090 native variant, salted tag-datum quotas and unchanged authored
placement vectors. Both candidates retain Sandbox's original RSA identity;
the converter verifies those signature bytes before using its signature hash.
It refuses a different base-map hash or an exceeded native quota/budget.

| Layout | Native placements | Spent / stock Forge budget |
|---|---:|---:|
| Hemorrhage | 254 | 582 / 1500 |
| Asylum | 390 | 975 / 1500 |
| Pinnacle | 301 | 573 / 1500 |
| Paradiso | 390 | 991 / 1500 |
| The Cage | 383 | 851 / 1500 |

Each native BLF is 57,837 bytes. Source-slot coverage and every exclusion are
recorded in `work/forge-world/variants/layouts/*.json`. Structural pieces are
retained. Redundant spawn points are thinned across teams/modes and space to
retain original H3 palette limits. Reach-only armor abilities, health packs,
unsupported mode markers, cinematic markers and scripted safe/kill volumes
are omitted; existing shared-world boundaries remain. Infection havens have
no native H3 counterpart. This is not an exact port of Reach-only modes.
Weapons, vehicles, lifts and teleporters use stock H3 behavior. Reach's Falcon
becomes a Hornet, its Revenant a Prowler and DMR a Battle Rifle.

**Mythic saved-file type is 10.** The external Blam-Network 12070 constant list
duplicates CTF/Slayer and labels usermap as 9. The original Mythic validator at
0x821F9558 classifies 1..9 as game variants and 10 as a map variant. Native
capture `20261023-030317-31588/proof-loaded.png` verifies Asylum appears beneath
Force Cove after using type 10; type 9 was enumerated but omitted by the game.
Do not revert this field based solely on that external constant list.

`build_saved_layouts.py --layout LAYOUT.bin [--layout ...] --profile-id HEX16
--output NEW_DIRECTORY` packages each file as `sandbox.map` in an unsigned CON
saved-game container. Each package is 114,688 bytes. Profile ID must be the
destination profile, not an invented console identity. The current test set
uses the SDK's offline profile B13EBABEBABEBABE and lives in
`work/forge-world/variants/saved-content`. All five passed the actual runtime
STFS reader with every payload byte compared. This is not a signature or
console acceptance test. The LIVE map bundle remains separate.

The isolated native harness accepts `--saved-layout LAYOUT.bin` with a DLC
map. It copies only that save into its private profile, uses the original
`usermap%016lX%lX`/`sandbox.map` naming and selects the second map-list row.
`--layout-menu-check` stops at the saved-layout list. Force Cove sorts before
Forge Gulch: from Last Resort, Cove is eight UP and Gulch seven UP when both
are present. Input remains entirely process-local; captures are native.
`--layout-overview-check` selects Forge, becomes the monitor, rises and turns
for architectural inspection; use at least 165 seconds and native captures at
130000, 145000 and 155000 ms. `--saved-layout-library layouts/` together with
`--layout-menu-check` checks all saves in the base map's list. Ordinary saved
layout walk checks preserve the authored facing instead of turning into a wall.

### Rigid geometry correction and native evidence

The first Asylum gameplay capture (`20261023-030534-35576`, 125000 ms)
exposed distorted newly converted geometry. Reach MCC's 36-byte rigid vertex
is **float4 position + ushort2 UV + short4 normal + short4 tangent**;
H3 MCC's 36-byte rigid record has a different layout. Matching stride is not
format compatibility. `reach_resource.py` now quantizes normalized positions,
preserves UVs, packs the native basis and reconstructs the missing binormal
using Reach position.W's handedness. Reclaimer's
`MccHaloReachVertexBuffer.xml` and TagTool's `VertexStreamReach.cs` document
these differences. The earlier structural resource audit did not detect this
semantic mismatch and is not a visual acceptance result.

All 114,549 rigid vertices across 52 source models passed an independent
position comparison within half a native UNORM16 step (maximum normalized
error 0.000007629511). `rigid-position-audit.json` records it. Corrected Asylum
run `20261023-031954-40076` selected the saved layout, loaded its shared Cove
base and rendered solid authored platforms/walls/arches at 125000 ms. Native
load checks passed. This is a visual/load check, not exhaustive game-mode testing.

`install_saved_layouts.py --manifest saved-content/manifest.json --content-root
REPOSITORY_LOCAL_CONTENT_ROOT` verifies packages, profiles and required base-map
hashes, then copies the small mutable saves into the existing content tree.
It refuses to overwrite changed saves. The SDK's existing discovery handles
them without any engine patch; do not send CON saves to its LIVE-only installer.

## Deployment and bounded native checks — 2026-10-23

Installed all five saves under the existing offline profile in
`work/dlc/installed-current/B13EBABEBABEBABE/4D5307E6/00000001`.
Select the base map, then the named saved layout in its list. Hemorrhage belongs
to Forge Gulch; the other four belong to Force Cove. These are also available
in Forge, not five new entries in the main map list.

The updated LIVE bundle is
`work/forge-world/variants/live-bundle/9E5664F584C3EF95EF79084B2DD1ED49B76806A6`
(797,184,000 bytes; SHA256
`fc4282fcb0b60f436c0289335fc39ac1c4dc22e4a1a3d9912441efa57611a653`).
All 35 files passed the runtime STFS reader's full byte comparison. The Cage
test used the runtime's actual LIVE installer. `promote_layout_bundle.py`
verified the extracted files against the payload and manifest before promotion
into `work/dlc/installed-current`. Unchanged assets are hardlinked, and existing
profiles, disc maps, executable and bootstrap were preserved. The previous
content folder/header are retained at `variants/previous-installed-content`.
`variants/deployment.json` records the active content ID and file hashes.

Native evidence is under `.local/loading-traces/`:

| Layout | Run | Inspected result |
|---|---|---|
| Asylum | 20261023-031954-40076 | Solid authored walls, arches and platforms after rigid-stream fix |
| Pinnacle | 20261023-032703-44576 | Loaded tower and surrounding terrain; short walking check, close view |
| The Cage | 20261023-033502-31740 | Authored platform/wall assembly; short movement stopped against wall |
| Hemorrhage | 20261023-034536-572 | Forge monitor view shows base and vehicles in Gulch; 918 budget remaining |
| Paradiso | 20261023-034855-9688 | Forge monitor view shows island base and vehicles; 509 budget remaining |

Final installed-bundle menu check `20261023-035221-2596/proof-loaded.png`
shows Asylum, Paradiso, Pinnacle and The Cage together beneath Force Cove,
with the existing map preview intact. Hemorrhage was selected and loaded
separately beneath Forge Gulch. The 33 changed/new Python files parsed without
creating bytecode caches; `git diff --check` passed.

These are bounded selection/load/visual checks, not exhaustive multiplayer,
objective-mode, audio, vehicle or collision tests. Native header/resource checks
also passed. Earlier Hemorrhage/Paradiso captures faced a cliff or sea and were
not counted as evidence of authored structures. No Xbox 360 hardware, system
link or complete 512 MiB memory-budget certification was performed.

The CON packages are prepared for the SDK offline profile. For an RGH console,
repackage using its destination profile ID; console acceptance remains untested.
The five packages total 560 KiB and do not contain duplicated map textures.

Cleanup removed the verified duplicate Gulch cache. Automatic approval review
blocked recursive removal of completed-test staging and `installed-candidate`
without a more specific reason. These remain; exact status is recorded in
`variants/cleanup-status.json`. Keep source inputs, current outputs, native
captures/logs and the explicit previous-content rollback.
