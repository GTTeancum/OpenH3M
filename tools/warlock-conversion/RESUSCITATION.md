# Resuscitation / Last Resort experiment

Status: full-palette conversion and resource checks pass. Native loading is
not working yet: the first correctly selected Last Resort run produced a black
capture. This is not a release or a successful gameplay conversion.
The user selected the full authored Forge palette on 2026-10-20.
Warlock's release and launch layout remain separate.

Run from `C:/X360/ISOs/H3M/.local/OpenH3M-source`:

```powershell
python -B tools/warlock-conversion/snapshot/tools/build_scenario_checkpoint.py `
  --project C:/X360/ISOs/H3M --slot zanzibar `
  --source D:/SteamLibrary/steamapps/workshop/content/976730/2898876653/maps/resuscitation.map `
  --basis ../../maps/zanzibar.map --xex ../../default.xex `
  --sound-bank 'D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo3/fmod/pc/sfx.fsb' `
  --decoder ../tools/vgmstream-r2117/vgmstream-cli.exe `
  --output ../resuscitation/zanzibar-01.map `
  --report ../reports/resuscitation-01.json
```

The builder refuses to overwrite an existing output. Failed attempts do not
publish a map. Use a new candidate name after a successful build. All generated
maps, logs, decoder work and reports belong under the project's `.local`.
Do not modify OpenH3M, original disc maps or the XEX.

## First candidate

`.local/resuscitation/zanzibar-01.map`: 114,946,048 bytes (109.62 MiB).
SHA256: `fcd207b2fdbd388520468e210a4153c66b31160b18dd1050949c311ac6bcbe17`.
Original Last Resort is 129,523,712 bytes.

The build uses 8,127,432 bytes of its 8 MiB new-metadata reserve.
Compaction retires 1,322 basis tags and 513 resources, repacking 268 resource
segments. Checks verified all 208 imported native sounds against their disc
codecs/packets, all 268 retained repacked segments (18,478,690 bytes), unchanged
original shared-page descriptors, and all 180 serialized Forge object references.
These checks establish cache contents, not gameplay or visual correctness.

```powershell
python -B tools/warlock-conversion/snapshot/tools/verify_forge_palette.py `
  --source D:/SteamLibrary/steamapps/workshop/content/976730/2898876653/maps/resuscitation.map `
  --map ../resuscitation/zanzibar-01.map --report ../reports/resuscitation-01.json
python -B tools/warlock-conversion/snapshot/tools/verify_native_resources.py `
  --map ../resuscitation/zanzibar-01.map --report ../reports/resuscitation-01.json --disc-maps ../../maps
python -B tools/warlock-conversion/snapshot/tools/verify_compacted_cache.py `
  --map ../resuscitation/zanzibar-01.map --basis ../../maps/zanzibar.map
```

## Scope

The source has 180 Forge entries: 17 vehicles, 27 weapons, 19 equipment,
86 scenery, 3 teleporters, 9 goals and 19 spawners. Compared with Last Resort,
104 unique entries are additional (12 vehicles, 9 weapons, 3 equipment,
80 scenery); some original entries are also removed. Of those additions,
93 have same-named assets elsewhere on the original disc. Names alone do
not establish behavioral or resource equivalence.

The authored map includes 260 scenery placements, 14 vehicles, 36 equipment,
27 weapons, 7 sound scenery and 34 crates. It has one BSP and six zone sets.
Native verification must check the correct map and recognizable scenery,
not merely rendered frames.

## Conversion evidence collected so far

- Terrain native-template discovery now covers templates absent from Last
  Resort. The removed MCC environment-specular constant is omitted only for
  native variants with environment disabled and otherwise matching names.
- Valhalla supplies the native `_0_1_1_1_1_0_1_3` water template.
- The source reflection bitmap has 52 independent cubemap resources. Its
  image-level aggregate offsets must not be applied within those resources.
  Conversion currently uses 64-pixel faces, one mip; visuals are unverified.
- Resuscitation lift child-shape records have `CBCBCBCB` fill in the final
  12 bytes of their 32-byte MCC records. Retail records are 16 bytes with
  no storage for that alignment tail. The converter accepts only the complete
  known fill pattern or zeros, while retaining pointer checks.
- Additional physics flag values were compared against same-named disc
  physics models, requiring all shape-row flags to match before extending
  the supported set. Wraith's 13 polyhedra all use `0x60` in both versions.
- All 183 original-disc vehicle AI-property records have zero in the
  retail-only word at offset 8. All 266 original-disc vehicle tags have empty
  removed posture/dialogue blocks, zero removed camera/actor/lipsync fields,
  and a null integrated-light-toggle reference.
  All 739 retail vehicle seats also have null built-in gunner references.
- All 34 source vehicle phantom records pass layout conversion. Embedded
  child identifiers 1 and 2 match retail Chopper/Warthog/Elephant and Scorpion
  records; these are retained as identifiers rather than relocated offsets.
- Fixed-size function payloads (including exponent opcode 9) follow the
  endian serializers in [TagTool's TagFunction.cs](https://github.com/TheGuardians/TagTool/blob/master/TagTool/Tags/TagFunction.cs).
  Payload lengths remain checked; unknown opcodes still fail.
- A Banshee hull-destruction spline retains a specific unused 16-byte editor
  tail. Preserving that tail produces a byte-for-byte match with the original
  `bunkerworld.map` function after converting its live fields.
- Camera tracks, collision-damage settings and particle-motion schemas
  inherit the Halo 3 definitions in Assembly; they have no MCC override.
  All 84 source particle-motion functions pass the function converter.
- Native sound selection skips stripped resource rows and continues searching
  other original maps before falling back to MCC sound conversion.
- The source camera's color-grading switch is enabled, but its only color
  balance row is disabled. Inactive rows are omitted, retaining retail exposure
  and bloom. Active grading adjustments still reject conversion.
- Vehicle dashboard/energy seat-power glow inputs currently use the existing
  static hologram approximation, recorded per material. This is a visual
  limitation; vehicle placements and Forge entries are retained.

## Loading investigation

The first native attempt selected Blackout because it inherited Warlock's
menu-navigation script; its lobby capture is not map-loading evidence.
The slot-aware script now retains the fresh profile's Last Resort selection.

The correctly selected candidate-01 test is
`.local/loading-traces/20261020-111840-33528`: header authentication/verification
passed, four hashes passed and zero failed, but the 165-second capture was black.
The watchdog closed the process at 180 seconds. A subsequent 150-second run
without screenshots (`20261020-112354-33632`) sampled the main thread in
guest function `0x822c2058`, traversing the resource allocator's linked list.

Candidate 02 adds six equivalent zone-usage and zone-only resource-manifest
entries to match Resuscitation's six scenario zone sets. All six source manifests
were compared and are equivalent, with the same residency masks as the seed.
It remains 114,946,048 bytes; SHA256:
`d8e66bf1ffdbf2251ef323f4485136eb3a18480e67d6789dec32f3f47c8e71f0`.
The play layout currently links candidate 02. Its diagnostic run is
`20261020-113214-30268`, with allocator-list sampling enabled and no capture.

The latest converter also remaps the resource table's BSP reference to the
converted BSP; this was added after candidate 02 was built and needs a fresh
build. No engine changes or load-check bypasses are allowed. Keep the goal
active until the actual map is visible and the final cache has been verified.
