# Installed custom DLC (player-style install), 2026-11-26

User instructions 2026-11-24/26: deliver maps as DLC packages with readable names (AGENTS.md rule), put them in the
main copy, rename and de-duplicate the Downloads copies, and make the main copy a normal player install rather than a
redirect into a work folder.

## Layout (portable; user 2026-11-26: "Stay out of the Documents folder. It needs to be portable")
- Game: `C:\X360\OpenH3M\Spartan.exe` (+ its six libraries), disc files in `C:\X360\OpenH3M\game\` (default.xex,
  maps, bink, waves, two audio DLLs; copied from the tools' disc source `C:\X360\ISOs\H3M`, which stays unchanged for
  the conversion scripts). No settings file is needed.
- Everything the game writes lives in `C:\X360\OpenH3M\content\`: installed DLC
  (`content\0000000000000000\4D5307E6\00000002\<package file>`, LIVE containers as is; see below), profile, the five saved Reach
  Forge layouts, shader cache. The whole folder can be moved or copied.
- Program change (halo3mp/src/halo3mp_app.h, OnConfigurePaths): with no user_data_root option the user-data folder
  is `<exe folder>\content` (and its cache `content\cache`) instead of `Documents\OpenH3M`; explicit options still
  win. Built 2026-11-26 from the work tree (pacing-release, SHA-256 prefix d8edea0b682dffbf), with this week's
  collision-trace diagnostics, benchmark look-down and 32-point cap removed again (map_benchmark.cpp restored from
  the saved original). Checked by running the installed copy in place with no folder options: log shows user data
  `C:\X360\OpenH3M\content`, the map list shows the custom maps, Beaver Creek loaded; Documents unchanged.
- `Documents\OpenH3M` holds only a `cache` folder from 2026-08-16 that predates this work; nothing of ours is there.
- Package files (for a console): `C:\Programming\GitHub\OpenH3M\.local\pc-port\packages\`, one per map.
- Set aside, not deleted: the old 11-map bundle (E3C2165...) and old Sky Bridge (C337EBA...) in
  `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\dlc\set-aside-20261124\`.
- Test runner: `run_pc_port.py --installed C:/X360/OpenH3M` runs an installed portable copy in place.

## Packages (each installed through the game's own installer and loaded into Slayer; screenshots inspected)
| Package | Content ID | Source |
| --- | --- | --- |
| 3longation_20261114_v1 | 6352229724464757A2081AFAE7252A2BE491618F | Downloads |
| BeaverCreek_20261124_v2 | BEAA2C69975AC8C782C1E05012CBAA13C6079914 | built here (H2-PORT-RECIPE.md) |
| BoardingAction_20261115_v1 | 7269FC75124A36F23973AEC27B8C1911BDE54B13 | Downloads (in progress: lighting) |
| Chiron_20261115_v1 | CE7968D452827FA3EB776C43EF88F64E42102FB9 | Downloads (in progress: lighting) |
| DeadCalm_20261116_v1 | D794C7214E7A715E99B24B4527D2D78C6FF66577 | Downloads (in progress) |
| Desolation_20261124_v1 | 846CBB605538E556159FDE8E6D69518774C2C1A4 | repackaged from the old bundle's installed files |
| Edge_20261116_v1 | 0D3797C19888F275B60632338BFF8BEEC45D3182 | Downloads |
| ForceCove_20261114_v1 | A1C1C6A8F113CB7562594A4E0D7AA1B838318905 | Downloads |
| ForgeGulch_20261114_v1 | 5A4EFBD7F13CC551BBEC52C87821034F9E41F461 | Downloads |
| Foundation_20261114_v1 | 5FEDFB7D57C6CCADE2BB80799D530E576A2427F3 | Downloads |
| Powerhouse_20261114_v1 | 4F62CB2C0CC50B61785606BF601FAD98B9E376E3 | Downloads |
| Prisoner_20261115_v1 | 8ECB38B3BEED5D69738DA8E7F39A1B751B4D6A05 | Downloads |
| Reactor_20261119_v1 | 63E200F7E1B1B9E6122DB19225359F3595B3FB9B | repo (owner's console build; in progress: performance) |
| Reflection_20261126_v2 | 10C4612A6F4C63A24AABAD8B81BAF36D982ACD90 | built here, compacted (map ID 1753) |
| Relic_20261116_v1 | 72401A0BBE988420B3DA483BEC511DFF89A3B6D8 | Downloads |
| Resuscitation_20261114_v1 | DB8A81FF119C892EFB4D414388FF947F69EC2246 | Downloads |
| Rodentia_20261115_v1 | F52ABF6151FA265AF61129E3ED63016138946A1F | Downloads |
| Sanctuary_20261114_v1 | C72EAEF6C5CC46A89AED82CA3A03DA0447A7BD41 | Downloads |
| SkyBridge_20261119_v1 | 9A23C8B4FAC24082064FF40A08427BA25789DAD4 | repo (owner's console build; in progress: performance) |
| SwordBase_20261126_v2 | 73F22A978F0286899A14781277E9B5DE5549BD76 | built here, compacted (map ID 1754) |
| Tombstone_20261121_v1 | (built 2026-11-21 as Tombstone_test; ID not recorded) | repo |
| Void_20261126_v2 | 6D6EB4F96D325E9A35AA5A6601A7616B38ACEB4C | built here, compacted (map ID 1755) |
| Warlock_20261114_v1 | EE364859E0712D7DC5EDC2C6B0B3844A74176C46 | Downloads |

Downloads (`C:\Users\smmel\Downloads\4D5307E6\00000002`): renamed to the same names; older duplicates of Forge Gulch,
Boarding Action, Hang 'Em High, Battle Canyon, Reactor and Sky Bridge sent to the Recycle Bin. Hang 'Em High and
Battle Canyon remain there, not installed (not on the user's list).

## Size compaction (Reflection, Sword Base, Void)
The ho2h3 converter builds inside a full copy of a stock map; the stock map's own tags and pages stayed in the file
and pushed these maps over the original console's 150 MiB DLC cache limit (console_cache_limits.py, 0x09600000).
`snapshot/tools/compact_native.py` runs the warlock pipeline's own compact_basis step on a finished map (keeping the
map's simulation-table order). Reflection 155 -> 90 MB, Sword Base 176 -> 100 MB, Void 152 -> 91 MB.
`preflight_variant_budget.py` now treats an empty palette slot as "no object" (Reflection's own scenario has some);
before compaction the check read the stock map's leftover scenario instead.

Not tested: a real console; system link.

## LIVE containers kept as is, and the Spartan name (2026-11-26)
User: "these should be LIVE containers -- a 1:1 match with 360"; "It's also still building as OpenH3M.exe, not Spartan.exe".
- The install is `C:\X360\OpenH3M\Spartan.exe`; settings file name follows (Spartan.toml). App name "Spartan" in
  halo3mp/src/halo3mp_app.h (work tree and repo); halo3mp/tools/package_release.ps1 now stages Spartan.exe in a
  Spartan-<version>-win-x64 package.
- `content\0000000000000000\4D5307E6\00000002\` holds the 23 LIVE container files themselves (same bytes as the
  packages folder); no unpacked folders, no Headers folder. `content\B13EBABEBABEBABE\4D5307E6\00000001\` holds the five
  saved Reach Forge layouts as their saved-game (CON) container files. B13EBABEBABEBABE is the PC port's built-in offline
  player profile ID (the 360 equivalent of a gamertag's profile folder).
- PC port change (work/rexglue-sdk/src/system/xam/content_manager.cpp; original kept in
  .local/pc-port/rollback-live-containers): the content list also lists container files from their own STFS header
  (content type + title ID), a container file is mounted read-only straight from the file (license bits from its
  header), and `--halo3mp_install_content` copies the container file unchanged instead of unpacking it.
- Checked by running the installed Spartan.exe in place: the log shows "Spartan starting" and user data
  `C:\X360\OpenH3M\content`; the map list shows the custom maps with their previews (read from the containers);
  Relic loaded into Slayer from its container file. Saved layouts as containers are not yet tried in Forge.
