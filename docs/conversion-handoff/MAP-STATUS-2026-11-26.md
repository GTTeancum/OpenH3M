# Map status handoff — 2026-11-26

Written for the session taking over map work ("Maps", user: "You're taking over for map work"). This session
stops all map work; it continues only with the Advanced Forge clean-room specification
(`tools/h4-forge/ADVANCED-FORGE.md`, `tools/h4-forge/spec/`). Nothing below is committed.

## Where the user's maps live
- Portable install: `C:\X360\OpenH3M\Spartan.exe` (+ six libraries), disc files in `C:\X360\OpenH3M\game\`.
  No settings file; the program uses `C:\X360\OpenH3M\content\` for everything it writes.
- Installed DLC: `C:\X360\OpenH3M\content\0000000000000000\4D5307E6\00000002\<package file>` — the LIVE container
  files themselves, unchanged (no unpacked folders, no Headers). Saved Reach Forge layouts (CON containers):
  `content\B13EBABEBABEBABE\4D5307E6\00000001\` (B13EBABEBABEBABE = the PC port's offline profile ID).
- Package files (console copies): `C:\Programming\GitHub\OpenH3M\.local\pc-port\packages\` — one current
  package per map (AGENTS.md DLC rule). Downloads copies renamed in `C:\Users\smmel\Downloads\4D5307E6\00000002\`.
- Old bundle and old Sky Bridge set aside (not deleted): `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\dlc\set-aside-20261124\`.
- Package list with content IDs and sources: `tools/warlock-conversion/DLC-INSTALL.md` (its Beaver Creek,
  Reflection and Sword Base rows are superseded by the table below).

## Current package per map (installed set, 23)
| Map | Package | Map ID | Notes |
| --- | --- | --- | --- |
| 3longation | 3longation_20261114_v1 | 1739 | user: drop, replace with Elongation (Maps session) |
| Beaver Creek | BeaverCreek_20261126_v1 | 1758 | renumbered from 1752 (clashed with Reactor); content ID 99865B9F0F8F8AF41E5A935D9451AD6DA1686E36; teleporters broken (user) |
| Boarding Action | BoardingAction_20261115_v1 in content | 1735 | Maps session has Boarding_Action_20261123 (accepted) |
| Chiron TL-34 | Chiron_20261115_v1 in content | 1732 | Maps session has Chiron_20261123 (accepted) |
| Dead Calm | DeadCalm_20261116_v1 | 1753 | |
| Desolation | Desolation_20261124_v1 | 1748 | repackaged from the old bundle |
| Edge | Edge_20261116_v1 | 1754 | |
| Force Cove / Forge Gulch | ForceCove_/ForgeGulch_20261114_v1 | 1731 / 1730 | |
| Foundation, Powerhouse, Prisoner, Relic, Resuscitation, Rodentia, Sanctuary, Warlock | *_2026111x_v1 | 1749 1746 1600 1750 1030 1734 1742 1520 | from Downloads |
| Reactor | Reactor_20261119_v1 | 1752 | was hidden by Beaver Creek's duplicate ID |
| Reflection | Reflection_20261126_v3 | 1756 | renumbered from 1753 (clashed with Dead Calm); content ID C5D9F4F35217379E8FD5A63B3178B71E970B34F7 |
| Sky Bridge | SkyBridge_20261119_v1 | 1747 | stutter in open area (user) |
| Sword Base | SwordBase_20261126_v3 | 1757 | renumbered from 1754 (clashed with Edge); content ID DBC248BF29BA04D049EB7A414A251B58263E3E22 |
| Tombstone | Tombstone_20261121_v1 | 1751 | |
| Void | Void_20261126_v2 | 1755 | -1 scenery crash (user) |

The renumbered Beaver Creek / Reflection / Sword Base containers are installed, but the in-game check that they
now appear (and load) was stopped unrun when map work was handed over: **not verified**.
`build_dlc_payload.py` now records Reactor 1752, Dead Calm 1753, Edge 1754 as `RESERVED_IDS` and refuses duplicates.

## What this session changed that affects map work
- `tools/warlock-conversion/snapshot/tools/compact_native.py` (new): removes stock-map leftovers from finished
  ho2h3 maps (Reflection 155->90 MB, Sword Base 176->100 MB, Void 152->91 MB). Compacted sources:
  `.local/ho2h3out/{reflection,swordbase,void}_compact.map` (+ `_compact.json` lists every removed tag).
- `preflight_variant_budget.py`: treats an empty palette slot (null handle) as "no object" instead of failing.
  **Void's -1 crash: suspect this or compaction.** Static checks found no null entries in Void's map-variant palettes
  and no Sandbox palette entry pointing at a removed tag; display names are intact. Not reproduced in game.
  Compare `void.map` (uncompacted) vs `void_compact.map` in game first.
- PC port (`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\rexglue-sdk\src\system\xam\content_manager.cpp`): lists and
  mounts LIVE container files directly; `--halo3mp_install_content` copies the container unchanged. Original:
  `.local/pc-port/rollback-live-containers/content_manager.cpp.orig`.
- Spartan program (`halo3mp/src/halo3mp_app.h`, work tree and repo): name "Spartan"; user data in `<exe>\content`;
  window title shows "Spartan | FPS: x" only with `--fpsunlock` (installed, **not yet verified**).
- `tools/map-review/speed-review/run_pc_port.py`: `--installed C:/X360/OpenH3M` runs the installed copy in place
  (menu route reads the installed containers' mapinfo), `--forge`, `--user-data-root`.
- Beaver Creek pipeline: `.local/beavercreek/rebuild.sh` (bake + build), `tools/map-review/speed-review/H2-PORT-RECIPE.md`,
  `beavercreek_lights.py`, `beavercreek_fill_lights.py` (8 fill lights already in the lighting info — run once only),
  `h2_sound_scenery_to_h3.py`. Teleporters come from `h2_gameplay_to_h3.py` (not investigated).
- Icebox and Breakneck are dropped (TODO.MD).
