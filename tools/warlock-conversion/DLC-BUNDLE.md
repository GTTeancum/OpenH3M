# Four-map DLC test bundle

Status: payload staged; native discovery under test. Not a completed STFS package.
Console memory certification remains deferred by the user.

## Reference and existing support

User reference: `D:/Programming/GitHub/H3M/Halo 3 - Heroic Map Pack (World) (Addon).zip`.
The ZIP contains one 510,803,968-byte LIVE/STFS package, title 4D5307E6,
marketplace content type 2, display name Halo 3 Heroic Map Pack. Its 23 root
entries include four map caches (including armory2), three mapinfo files,
15 preview BLFs and spa.bin. No shared.map. Inventory is read directly from
the archive with `snapshot/tools/inspect_dlc_reference.py`; no full extraction.
Private report: `work/dlc/reference-inventory.json`.

The current SDK's ContentManager::ListContent enumerates directories beneath
`user_data_root/0000000000000000/4D5307E6/00000002/`. ContentPackage mounts a
directory as a guest content device. InstallContent already parses STFS and
extracts it into that layout, but no caller was found in the current source.
Discovery testing uses this native installed layout before adding an installer.

BLF layout reference: TheGuardians/TagTool, revision
`ce2dc6ac13072b160752af618ea1dc143e2727ac`,
`TagTool/BlamFile/Blf.cs` and `TagTool/Cache/CacheFile/CacheFileHeaderGen3.cs`.
Downloaded source references remain in ignored `work/dlc/reference`.
Retail mapinfo has _blf / levl v3.1 / _eof chunks; metadata names are UTF-16BE.

## Payload preparation

`snapshot/tools/build_dlc_payload.py` copies the four accepted converted maps
once into `work/dlc/payload` and assigns independent identities:

| Map | Cache name | ID | Original replacement |
| --- | --- | --- | --- |
| Warlock | warlock | 1520 | lockout / 520 |
| Resuscitation | resuscitation | 1030 | zanzibar / 30 |
| Prisoner | prisoner | 1600 | chillout / 600 |
| Forge Gulch | forge_gulch | 1730 | sandbox / 730 |

The builder checks stock mapinfo ID collisions and original scenario identity,
changes header name/path and scenario MapId, and emits distinct mapinfo names,
descriptions and DLC flags. Native geometry/resources remain unchanged. It
refuses an existing output directory to avoid silently overwriting evidence.
Manifest: `work/dlc/payload-manifest.json`.

Stock signatures cannot remain valid after metadata edits. Test mapinfo uses
the defined BLF None authentication type; guest acceptance is not assumed.
Existing stock preview references are explicitly temporary placeholders.
The staging directory is NOT a signed retail LIVE package or release artifact.

## Native test isolation

`trace_loading.py --dlc-payload work/dlc/payload --dlc-menu-check` hardlinks the
flat payload into one package under its repo-local run directory. This avoids
another copy of the map payload. `--game C:/X360/ISOs/H3M` reads stock disc maps
so both original and custom identities can coexist. Outputs/profile/cache are
confined to the repository. The recorded process-local route stops at the map
list; native capture and logs must establish discovery before gameplay routes
are selected. No desktop input or OS screenshots.

Pending: prove discovery, validate each custom-map load/visuals, native custom
previews, build one test container, validate container integrity and installation,
record repeatable install/rollback, remove obsolete staging after acceptance.

## Initial discovery evidence (2026-10-22)

All four staged cache scenario IDs and mapinfo IDs/names pass independent reads.
Run 20261022-155104-28096 inspected the native map list at 68 seconds: original
maps are present, but Forge Gulch is absent between Epitaph and Foundry. This is
not a discovery pass. The run ended at its 75-second watchdog.

Debug logging run 20261022-155300-21524 observed an enumerator returning zero
items. Startup import tracing in 20261022-155509-23556 then established the
actual call at 32.343 seconds: XamContentCreateEnumerator arguments begin
user=0, device=1, content_type=1 (saved games), flags=0, count=151. Return is 0.
This does NOT establish rejection of marketplace type 2 or unsigned mapinfo.
Original XEX import ordinal 0x25c has thunk 0x82723d54, called through
0x825b5d88. Aggregate enumerator ordinal 0x279 is absent from this XEX.
Next investigate the game's marketplace discovery path rather than guessing
at bundle filenames or weakening metadata checks. No host runtime changes have
been made for DLC. Only the first discovery run captured an image.
