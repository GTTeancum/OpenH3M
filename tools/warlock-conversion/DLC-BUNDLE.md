# Four-map DLC test bundle

Status: OpenH3M test bundle built, installed and verified in gameplay for all four maps.
The shared OpenH3M.exe is deployed; original disc maps remain alongside the DLC.

Target: OpenH3M and RGH/JTAG. The user authorized narrow custom-content
validation changes on 2026-10-22. Retail authentication is not a target.
Gameplay, physics, simulation and networking code are unchanged. Hardware and
system-link testing have not been performed; console memory certification is deferred.

## Current artifacts

All paths below are relative to this repository, except the authorized shared
installation `C:/X360/ISOs/H3M` and the read-only reference ZIP.

- LIVE package: `work/dlc/bundle/F798F5651E96A8D21CE55B7387C4FFC44F8EBAF1`
- Size: 586,035,200 bytes / 558.89 MiB, containing four maps plus four mapinfos.
- SHA256: `990d1ed8f0327c0e41c06d8adea34434fc9f9d1a25738d17245e46f47753fbd4`
- Installed host content: `work/dlc/installed-current/0000000000000000/4D5307E6/00000002/`
- Separate RGH/JTAG XEX candidate: `work/gamedata/default.xex`
- XEX SHA256: `e46be03892b22ba356026369ba51fa557cdf988629ab35e1defd92151e6ec3af`
- Host build: `work/rexglue-sdk/out/win-amd64/halo3mp.exe`
- Host SHA256: `adf48d3fabd2262ea6ddde94e06b15e6b172a6b8e2c4918eedbff1e4a4957077`
- Private reports: `work/dlc/{payload-manifest,bundle-manifest,bundle-integrity}.json`.

| Map | Distinct ID | Cache bytes | Previous replacement |
| --- | ---: | ---: | --- |
| Warlock | 1520 | 182239232 | Blackout / lockout |
| Resuscitation | 1030 | 151502848 | Last Resort / zanzibar |
| Prisoner | 1600 | 110436352 | Cold Storage / chillout |
| Forge Gulch | 1730 | 138272768 | Sandbox |

The bundle has no duplicate shared.map. All original disc maps remain available.
Total package size is disk storage, not simultaneous RAM consumption.
This is a test bundle: custom preview BLFs and release artwork are not included;
the menu may show its generic missing-preview icon. Map names/descriptions are present.

## Format reference and validation

Read-only reference: `D:/Programming/GitHub/H3M/Halo 3 - Heroic Map Pack (World) (Addon).zip`.
Its single LIVE container is 510,803,968 bytes, title 4D5307E6, marketplace type 2.
It contains 23 root entries: four caches, three mapinfos, 15 preview BLFs and
spa.bin. Inventory and hash checks stream the ZIP without extracting its maps.

The new package passes 142,221 data-block hashes and 843 hash tables, directory
and chain checks, and byte-for-byte comparison against staged payload files.
The native SDK STFS reader independently compares all eight files, 582,531,652
payload bytes (`work/dlc/native-container-check.txt`). These are integrity checks,
not Microsoft signature verification. The LIVE signature is intentionally zero.

Use the extensionless content-ID filename. Halo's resolver 0x822061D0 strips at
the first dot: `OpenH3M-Custom-Maps-Test.live:/forge_gulch` was truncated to the
bundle basename. Run 20261022-164812-16024 proved this through native path tracing.
The builder now names its output canonically. SDK installed headers also embed
that filename: reinstall, rather than renaming an extracted content directory.

## Repeatable build

Run commands from this repository. Keep TEMP/TMP in `work/build-temp`.
The tools refuse existing output/report paths; review prior outputs before rebuilding.

```powershell
python -B tools/warlock-conversion/snapshot/tools/build_dlc_payload.py --converted C:/X360/ISOs/H3M/.local/custom-maps-play/maps --stock C:/X360/ISOs/H3M/maps --output work/dlc/payload --report work/dlc/payload-manifest.json
python -B tools/warlock-conversion/snapshot/tools/build_dlc_live.py --payload work/dlc/payload --output work/dlc/bundle/package.pending --report work/dlc/bundle-manifest.json
```

The payload builder changes cache names/paths, scenario IDs and mapinfo identities.
It updates the body XOR checksum for the changed scenario word, then regenerates
the salted header SHA1 using the original XEX resource salt. This is mandatory:
run 20261022-165142-41268 exposed stale header hashes in the first DLC staging.
The container builder returns its actual extensionless output path in the report.

```powershell
python -B tools/warlock-conversion/snapshot/tools/verify_dlc_stfs.py work/dlc/bundle/F798F5651E96A8D21CE55B7387C4FFC44F8EBAF1 --payload work/dlc/payload --report work/dlc/bundle-integrity.json
```

For the native check, put `work/rexglue-sdk/out/win-amd64` on PATH, then run
`work/rexglue-sdk/out/pacing-release/stfs_probe.exe PACKAGE work/dlc/payload`.
The native probe target is added by `snapshot/tools/stfs_probe.cmake`.

## Shared host build and console candidate

`patch_dlc_xex.py SOURCE OUTPUT` only accepts original Mythic XEX SHA256
`18816c1da58b1371e440741fadab1df8e6e6ecca7c5b81952f2d23ceec797313`.
It creates a separate file and verifies the decrypted image differs only here:

- 0x821F6A68: mapinfo signature call becomes `li r3,1`.
- 0x821B111C: cache-header RSA call becomes `li r3,1`.

BLF structure, version/size checks and salted cache-header hashes remain enforced.
The general cryptographic functions and gameplay/network code are unchanged.
The console candidate is untested on hardware and requires the matching Mythic build.
The original shared-installation XEX remains untouched.

Host codegen uses the same patched XEX. Apply the saved SDK patches, including
`rexglue-sdk-enumeration-async-result.patch` and `rexglue-sdk-reuse-existing-build.patch`.
Generate from `halo3mp/halo3mp_manifest.toml`, then run `halo3mp/tools/genstubs.py`.
All 161 guest-DLL imports resolve without fallback stubs. Configure the existing
`work/rexglue-sdk/out/pacing-release` with `REXGLUE_EXTERNAL_PROJECTS_FILE` pointing
to `snapshot/tools/openh3m_reuse_sdk.cmake`; build halo3mp and its four guest DLLs.
This reuses one SDK build, rather than creating another game/build silo.

SDK corrections preserve asynchronous enumeration errors, zero-initialize missing
content records, and own deferred content root-name strings. Native installation
and discovery validate these corrections; they are not custom gameplay changes.

## Installation, testing and rollback

`--halo3mp_install_content=PACKAGE` invokes the SDK's native ContentManager installer
before guest launch, checks Halo 3/LIVE/type and canonical filename, and stops on
failure. It installs into the configured user-data root. Afterward ordinary game
startup discovers the content without an installer flag.

The process-local `trace_loading.py` harness accepts `--dlc-package` for initial
installation, then `--dlc-installed-root work/dlc/installed-current` to reuse it
through hardlinks. Add `--dlc-map NAME`, the exact executable SHA256, and native
capture options. It fails if the selected custom header is rejected or never
validated. Visual inspection is still required; a header pass is not gameplay proof.
`--trace-dlc-paths` is an optional verbose diagnosis, not a timing-test setting.

Recorded fresh-profile route: custom games at 45s/46s, map selector at 55s/56s.
The initial selection is Last Resort. Forge Gulch is 7 UP, Prisoner 4 DOWN,
Resuscitation 6 DOWN, Warlock 13 DOWN. Select at 70s/72s, move to Start at 74s,
start at 95s. All input remains inside the game process; no desktop operation.

`deploy_dlc_host.py --install C:/X360/ISOs/H3M --build work/rexglue-sdk/out/win-amd64 --content work/dlc/installed-current`
puts the executable/DLLs beside the disc and configures direct launch against
stock maps plus installed DLC. It retains one rollback set under `work/dlc/rollback`
and a deployment report. Close the game before deployment/rollback. To roll back,
atomically replace the deployed binaries and bootstrap with that saved set; leave
original disc maps/XEX untouched. The old replacement-map setup remains available.

For console testing, copy the LIVE file unchanged under
`Content/0000000000000000/4D5307E6/00000002/` and use the separate matching-build
RGH/JTAG XEX candidate with a backed-up game installation. No hardware result is claimed.

## Runtime evidence

- 20261022-163854-41704: native installation and all four custom IDs registered;
  native map-list capture showed Forge Gulch alongside stock maps, normal text.
- 20261022-164206-39444: wrong filename resolution, loading 0%; not a gameplay pass.
- 20261022-165009-38504: stale installed-header name; deliberately stopped, not a crash.
- 20261022-165142-41268: stale map-header hashes; deliberately stopped after diagnosis.
- 20261022-165537-29544: corrected package, Forge Gulch header/authentication pass;
  native gameplay capture shows terrain, rocks, grass, sky and HUD. Normal watchdog exit.

The final native gameplay checks are recorded below.

Cleanup limitation: automatic approval review blocked recursive removal of the obsolete
`work/dlc/installed` tree with "blocked by policy". It was retained; the verified
installation was moved into `installed-current`, without another map copy. Historical
run content hardlinks may also retain obsolete payload bytes. Logs identify their builds.

- 20261022-165904-40936: route selected stock Orbital; correctly rejected by
  expected-map validation. Longshore had been omitted from the route count.
  Registered metadata confirms Longshore between Last Resort and Narrows; counts corrected.

Independent full-body XOR recomputation passed for all four staged caches after
identity changes. The new salted header hashes also pass preflight.

- 20261022-170213-9244: Prisoner selected and native header/authentication passed,
  normal watchdog exit, but capture did not complete. No visual pass claimed.
  Later runs allow a larger margin for the native capture thread.

- 20261022-170539-33336: Resuscitation selected; header/authentication and resource
  hashes passed, native gameplay capture shows textured rock/ground and normal HUD
  after the short movement route. View is local, not an exhaustive arena inspection.

Staged payload files now hardlink to byte-identical installed files, saving about
556 MiB. Rebuild to new files and atomically replace them; never edit linked
payload/installed files in place. One current LIVE package is retained.

- 20261022-170850-23636: deployed Warlock loaded, but movement ended against a
  surface; close-up capture was not accepted as an arena visual check.
- 20261022-171217-44024: deployed Warlock stationary capture shows the recognizable
  arena, pillars/platforms, foliage, effects and normal HUD. Eleven observed native
  hash checks passed, zero failed; normal watchdog exit.

An independent comparison against accepted replacement files found exactly one
changed body word per map (scenario ID). The shared.map used by both installations
is the same file. Original geometry, textures, objects and gameplay data are preserved.
All rollback files retain the hashes recorded before atomic deployment.

- 20261022-171517-43224: deployed Prisoner, recorded map-specific movement/fire
  route, expected interior/lighting/HUD visible, ammo reduced from 32 to 30.
  Eleven observed native hash checks passed, zero failed; normal watchdog exit.

All four captures were individually inspected. Final machine-readable evidence is
`work/dlc/runtime-validation.json`; deployment hashes/configuration are in
`work/dlc/deployment.json`. This is a bounded test-bundle pass, not exhaustive
gameplay or audio testing. Console hardware and system-link remain untested.
Custom preview artwork is a later release task; the current test menu uses a
generic missing-preview icon. No game assets or captures are committed to Git.
