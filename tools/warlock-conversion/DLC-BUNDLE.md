# Four-map DLC test bundle

Status: one unsigned LIVE/STFS test container built and integrity-validated.
Custom-map discovery, gameplay under DLC identities, and retail acceptance remain
unverified. User instruction: work in LIVE containers for now; no authentication
exceptions are authorized by that instruction.
Console memory certification remains deferred by the user.

## Reference and existing support

User reference: `D:/Programming/GitHub/H3M/Halo 3 - Heroic Map Pack (World) (Addon).zip`.
The ZIP contains one 510,803,968-byte LIVE/STFS package, title 4D5307E6,
marketplace content type 2, display name Halo 3 Heroic Map Pack. Its 23 root
entries include four map caches (including armory2), three mapinfo files,
15 preview BLFs and spa.bin. No shared.map. Inventory is read directly from
the archive with `snapshot/tools/inspect_dlc_reference.py`; no full extraction.
Private report: `work/dlc/reference-inventory.json`.

Read-only integrity validation is repeatable with `snapshot/tools/verify_dlc_stfs.py`
and `--report work/dlc/reference-integrity.json`. It streams the ZIP without
extracting another package copy. The Heroic reference passes header SHA1,
123,961 data-block hashes, and 736 hash tables across three levels. Its header
hash includes padding through the aligned 0xB000 boundary, not just the declared
0xAD0E bytes. An in-memory one-byte corruption of data block 0 is rejected;
the source ZIP stays unchanged. This tool verifies hash integrity only, not
RSA signatures, licensing, directory semantics, or retail acceptance. It supports
single-backing read-only STFS; other layouts are rejected explicitly.

## LIVE container checkpoint (2026-10-22)

Output: `work/dlc/bundle/OpenH3M-Custom-Maps-Test.live` (586,035,200 bytes,
558.89 MiB). One container contains four maps and their four mapinfo files.
No shared.map, duplicate game installation, or extracted reference copy is added.
The new LIVE header identifies Halo 3 (4D5307E6), marketplace content type 2,
and explicitly names the package as a test. Its signature field is zero;
it does not reuse or claim the reference's Microsoft signature.

Build from the existing payload, using a new output path only after reviewing
the old artifact (the builder refuses overwrites):

```powershell
python -B tools/warlock-conversion/snapshot/tools/build_dlc_live.py --payload work/dlc/payload --output work/dlc/bundle/OpenH3M-Custom-Maps-Test.live --report work/dlc/bundle-manifest.json
python -B tools/warlock-conversion/snapshot/tools/verify_dlc_stfs.py work/dlc/bundle/OpenH3M-Custom-Maps-Test.live --payload work/dlc/payload --report work/dlc/bundle-integrity.json
```

The verification passes all 142,221 data blocks and 843 hash tables, traverses
the directory and file allocation chains, checks that no data is missing,
duplicated or orphaned, and compares every payload byte with the staged files.
All four cache SHA256 values match the earlier payload manifest. Package SHA256:
`66979ec810f348d29e99d83db45fc39969244e21598e900f5282df5196275509`.
Content ID: `6D134288C81D8F6488F48EFA74B0CC914D183ADC`.

This checkpoint is not an installation or gameplay pass. The existing mapinfos
still have None authentication and stock preview placeholders. There is no spa.bin
or custom preview BLF in this checkpoint. Do not deploy it as finished retail DLC.
The total bundle size is disk storage for four maps, not measured simultaneous
console memory use. Original disc maps and the shared test installation were
not changed by packaging. Rollback of this checkpoint requires only removing
the generated bundle and its two reports; the source payload remains reusable.

### Native runtime reader check

`snapshot/tools/stfs_probe.cpp` mounts the actual container through the existing
ReXGlue `StfsContainerDevice`, validates LIVE/title/content-type fields, enumerates
its root, and reads every file through the runtime's `File::ReadSync`. It compares
all bytes against staging without extraction or another map copy. The run passed:
8 files, 582,530,628 payload bytes. Evidence: `work/dlc/native-container-check.txt`.
This independently checks the Python writer against the real runtime parser.
It does not invoke the content installer, guest metadata validation, or gameplay.

Reuse the existing SDK build (the hook retains the earlier font-test target):

```powershell
$env:TEMP = (Resolve-Path work/build-temp).Path
$env:TMP = $env:TEMP
$env:PATH = 'C:\Program Files\LLVM\bin;' + (Resolve-Path work/rexglue-sdk/out/win-amd64).Path + ';' + $env:PATH
$hook = (Resolve-Path tools/warlock-conversion/snapshot/tools/stfs_probe.cmake).Path
cmake -S work/rexglue-sdk -B work/rexglue-sdk/out/pacing-release "-DCMAKE_PROJECT_INCLUDE:FILEPATH=$hook"
cmake --build work/rexglue-sdk/out/pacing-release --target stfs_probe -j 2
& work/rexglue-sdk/out/pacing-release/stfs_probe.exe work/dlc/bundle/OpenH3M-Custom-Maps-Test.live work/dlc/payload
```

The native reader probe is excluded from normal builds, has no UI or input
simulation, and uses only bounded read buffers. It changes no deployed runtime.
The SDK installer itself extracts files and writes a sidecar content header;
its presence is not proof that the current OpenH3M executable invokes it.
An installer integration remains unverified and does not resolve the independent
mapinfo authentication requirement described below.

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
Only the first discovery run captured an image. Absence at that list position
does not prove global absence: staged metadata currently retains stock map indices.

## Discovery findings and console requirement

User clarification: this DLC must also run on a real Xbox 360. The available
test console is RGH, but the bundle must meet retail sideloading requirements.
RGH is test hardware, not permission to bypass requirements. A host-only loader,
modified game authentication checks, or RGH-only acceptance is not a solution.
Research and establish the applicable retail custom-DLC sideloading route before
choosing packaging or changing content checks. No authentication exception is
authorized. Distinguish console acceptance of a container from Halo 3 acceptance
of its custom map metadata; both need evidence for the proposed route.
Console memory certification remains deferred, distinct from loading support.

Initial retail-route research (2026-10-22): the Customs Creators Collective
[FAQ](https://customscreatorscollective.wordpress.com/faq/) documents retail
Rock Band 3 customs with specific disc/update requirements. This is evidence
for that game's custom-content route, not Halo 3 cache acceptance. The
[PeerPressure project](https://github.com/grimdoomer/Xbox360PeerPressure)
describes a softmod; physical retail hardware running a softmod is not proof
of acceptance with original checks intact. No Halo 3 retail route meeting
the user's requirement has yet been established. Do not treat an unsuccessful
search as proof that none exists.

Original XEX disassembly in `work/dlc/mapinfo-disassembly.txt` establishes a
second authentication layer inside the game, separate from the STFS container:
the mapinfo reader requires an EOF chunk of size 0x111 at 0x821F6A40 and requests
authentication type 3 at 0x821F6A54 before calling 0x823C3C68. Only successful
validation reaches level registration at 0x821F6AA8. The staged None-authentication
mapinfos do not meet this requirement. Changing container packaging alone does
not resolve this. No custom metadata loader or authentication bypass is implemented.

Host API corrections are saved in
`halo3mp/patches/rexglue-sdk-enumeration-async-result.patch`:

- Async enumeration wraps the underlying error in FUNCTION_FAILED while retaining
  its extended HRESULT. Native tracing then advanced from saved games to DLC.
- Missing content headers now take the directory-metadata fallback instead of
  interpreting FILE_NOT_FOUND as success and exposing an uninitialized record.
- Deferred content opening owns its root-name string instead of retaining a
  view into a guest stack buffer.

The last correction has compiled but has not been runtime-validated. These fixes
do not establish custom-map discovery, gameplay, or real-console acceptance.
The test harness now reports nonzero guest process exits as failures.

Before declaring the bundle complete, verify both container handling and in-game
mapinfo acceptance for the selected console configuration. Keep the four distinct
map identities and stock maps together; do not substitute replacement-map loading
as proof of DLC support.
