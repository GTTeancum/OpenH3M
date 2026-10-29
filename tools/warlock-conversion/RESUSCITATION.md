# Resuscitation / Last Resort experiment

Status: gameplay regression repair in progress; candidate 06 is not an accepted gameplay build. Candidate 06 loads into Slayer
as Last Resort with the full 180-entry Forge palette. Its native capture was
inspected: blue sky, canyon cliffs, base ramps, vehicles and player HUD are visible.
The user selected the full authored Forge palette on 2026-10-20.
Warlock and Resuscitation share `.local/custom-maps-play` and `Run-CustomMaps.cmd`.

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
At that stage, the play layout linked candidate 02. Its diagnostic run is
`20261020-113214-30268`, with allocator-list sampling enabled and no capture.
That run still stalls in `0x822c2058`. Its sample confirms a cycle: heap
`0xbe154820`, head handle `0x142b0000`, node words
`142b0002 0000080a 00000000 00000000 00000000 00000001`.
The next handle is zero, resolving to the same node indefinitely. The six-zone
fix is necessary table consistency work, but did not fix this loading stall.
The next diagnostic should identify the allocator by its stored name/header
and determine which cache data or allocation size creates the bad list.

The converter also remaps the resource table's BSP reference to the
converted BSP; this was added after candidate 02 and included in candidate 03. No engine changes or load-check bypasses are allowed. Keep the goal
active until the actual map is visible and the final cache has been verified.

Candidate 03 adds the resource BSP-reference remap. It remains 114,946,048
bytes, SHA256 `9d505e1c56945d21d09f45e7fe22fcad9ec3429de2570c618ba6ef1532eb8c87`.
Its serialized BSP reference and six zone records pass focused validation,
but the native test still stalls in the same resource allocator. The Resuscitation layout was then staged with candidate 03.

The unmodified original Last Resort control run
`.local/loading-traces/20261020-114022-33660` uses the same fresh profile,
menu route, shader seed and verified executable. It proceeds past that stall
into decal/effect initialization with continuing GPU work. No screenshot was
requested for this diagnostic, so it is not a visual-success claim. This
narrows the difference to the converted cache rather than the initial menu
selection alone.

## Resource-index compaction (candidate 04)

Candidate 04 retains all 180 Forge entries and packs 5,619 resource slots down
to 5,106 by removing the 513 retired basis resources. It remaps typed asset
references and every resource residency bitset, and clears obsolete Last Resort
prefetch prediction hints. Original shared-page descriptors and sound packets
are preserved. This is a cache conversion change; no runtime patch is used.

The serialized checks pass: 4,710 typed resource references, all 180 Forge
entries, all 208 native sounds, and 268 repacked segments. An independent
candidate-03/04 comparison also verifies all 52 resource-manifest bitsets.
SHA256: `7437ea094c106e1c44e9767430958a55cee2d1e6752449eaf4b3dc5e451637bf`.
Size remains 114,946,048 bytes (109.62 MiB); metadata use is 8,095,496 bytes.

The native candidate-04 run is `20261020-115936-9288`. It gets past the earlier
allocator cycle; its capture shows Resuscitation in Slayer, with canyon cliffs, base ramps,
vehicles and HUD. Inspection found a dark sky and excessive base highlights,
so that candidate was superseded.
The allocator diagnostic shows a 5,483-entry, 20-byte page-state table. Slot
compaction fixes the observed corruption, but the precise allocation-limit
mechanism is not yet established; do not describe 5,483 as a universal resource
limit for other maps.

For reindexed caches, pass their build report to `verify_compacted_cache.py`
using `--report`, and also run `verify_resource_indices.py --map <candidate>`.
Retired candidates 01 and 02 have been removed; their reports and diagnostic
logs remain. Stock Last Resort and the accepted Warlock files are unchanged.


## Current candidate and manual launch

Candidate 06: `.local/resuscitation/zanzibar-06.map`, hardlinked as
`.local/custom-maps-play/maps/zanzibar.map`.
Size: 115,154,944 bytes (109.82 MiB), compared with stock Last Resort's
129,523,712 bytes (123.52 MiB). SHA256:
`488be0a1b7d29807027d6f666ec6b5ee864775e700301f3263ac0d6a90b1a8f1`.
It uses 8,119,212 bytes of the 8 MiB new-metadata reserve.

All 180 Forge entries, 4,715 typed resource references, 208 native sounds and
268 repacked resource segments pass the serialized checks. The packed resource
table contains 5,111 entries. Original shared-page descriptors remain unchanged.

Seven sky materials now use native shader variants with authored self-illumination
textures/constants, rather than the opaque wall fallback. The distant sky terrain
uses the matching unbumped variant because its bump-detail variant is absent from
the original disc. Native donor cloud animation is retained. Custom world
materials use the same diffuse/bump-preserving matte approximation as Warlock.
Vehicle glow, reduced-resolution cubemaps and other reported material approximations
remain part of this proof of concept.

Launch `C:/X360/ISOs/H3M/Run-CustomMaps.cmd`, then choose **Custom Games >
Last Resort > Slayer**. It launches the unchanged executable at
`D:/Programming/GitHub/H3M/OpenH3M.exe`, with a one-hour watchdog. The manual
launcher reuses `.local/custom-maps-play/cache` and `user` for both maps.
Logs remain under `.local/warlock-runs`; that folder name is historical.
The old root launchers forward to the shared launcher. Automatic approval review
blocked deletion of the unused `.local/resuscitation-play` hardlink layout; it
contains no separate map payload or shader cache. No map or engine was rebuilt. Original assets and the two converted maps are hardlinked.

For a fresh shared layout, prepare Warlock with `warlock_handoff.py prepare`,
then hardlink the converted Resuscitation map into `maps/zanzibar.map` in that
same layout. Use `check --all-maps` to authenticate both staged maps.

Never replace an original disc hardlink in place: remove only the verified
staged link, then create a new hardlink to the generated candidate.

Broad gameplay, every Forge item's behavior, audio listening, physical Xbox 360
and system-link testing remain unverified. No engine or original-disc file was
modified. This is a Last Resort replacement experiment; the later DLC bundle is
not part of this conversion.

Candidate 05's capture (`20261020-121114-27524`) confirmed gameplay and reduced
white material artifacts, but its sky remained dark. Source sky materials used
a custom fog setting while the fallback root retained setting zero. Candidate
06 copies each source sky material's custom fog index as well as its flag.
It was produced by a bounded incremental correction of six fog-index fields;
a complete byte comparison permits only those fields and regenerated checksum
fields to differ from candidate 05. The normal converter includes the same fix,
so future conversions do not require that incremental step. Resource, sound,
Forge and geometry data are unchanged from the verified candidate 05.
Native candidate-06 evidence: `.local/loading-traces/20261020-121636-26244/`.


Final native check: candidate 06 stayed running to the 150-second watchdog.
Its 135-second `proof-loaded.png` was inspected: the sky is blue rather than
black, canyon/base geometry is recognizable, and the earlier white rock
highlights are absent. Some base surfaces remain strongly lit and the ring is
bright; this remains an approximate material conversion rather than a visual
match claim. Four hashes passed, zero failed; no unhandled guest fault was
reported. Interactive movement, Forge spawning and listening tests were not
performed by the agent.

The manual launcher uses the shader seed from this final run. Candidate 06 is
the only retained generated Resuscitation map; candidates 01–05 were removed
after verification. The original stock-control hardlink costs no second asset
copy. Small reports, logs and the useful native captures remain local. Source,
verification tools and repeatable build instructions are committed; game assets
and captures are not committed.


## Gameplay regression and stock-asset correction (2026-10-20)

The owner reported low framerate, no Banshee entry prompt, and a freeze after
holding RB and pushing the Banshee. The run at
`.local/warlock-runs/20261020-124752-15104` stopped GPU/input progress at
12:48:51.842 while vblank continued until the window was closed at 12:49:00.564.
A clean process exit did not mean successful gameplay.

The reused Last Resort player animation graphs lacked `banshee_d` and other
vehicle modes. Matching vehicles now use original-disc native tags and resources;
player graphs come from the stock disc as well. Native Banshee physics scalars
also matched the previous converted model, so that comparison alone did not
explain the freeze. Banshee entry, contact stability and framerate require a
focused gameplay recheck; none is inferred from resource checks or a load capture.

Candidate 08: `.local/resuscitation/zanzibar-08.map`, 151,666,688 bytes (144.64 MiB),
SHA256 `d334b11dd31aed662b0a1a63eb5fa1d438d9cd9a897d6dfa37da8606435f3d39`.
It preserves 180 Forge entries; 4,898 typed resource references validate across
5,294 resource slots. Native comparison verified 16 imported vehicle tags,
154 physics models, 24 animation graphs, 181 render models, 343 bitmaps and
1,105 resource payloads. All 208 native sound codecs/packets match their donors.
This is serialized-data evidence, not gameplay acceptance.

`native_assets.py` searches original maps before converting a missing asset,
rejects stripped donors and records the chosen donor. Shared-page references stay
shared. Local donor pages are trimmed to referenced datarefs without changing
asset bytes or dropping texture mips. The oversized candidate 07 was deleted.
The accepted Warlock map and the engine/disc files remain unchanged.

Native donor player graphs cover Banshee driving/boarding. An audit also found
`shade_d` missing from the broad donor graph; stock Chill/Guardian/Snowbound have
that mode. Do not claim every Forge vehicle is usable until the supplemental
player animation dependency is resolved and checked. Some stock boarding-seat
labels intentionally have no independent player mode; those alone are not failures.

For a bounded user-operated diagnostic, run `trace_loading.py` with
`--manual-input --sample-on-stall --sample-threads --seconds 180 --slot zanzibar`
and the shared `.local/custom-maps-play` layout. It uses only its own child process,
records potential stalls, and sends no desktop or scripted input in manual mode.

Candidate 08 native load check: `.local/loading-traces/20261020-131318-22108`.
Both header-authentication calls returned success; resource hashes passed 4/4.
The 135-second native capture was inspected and shows the authored desert canyon,
base ramps, vehicle placement and first-person HUD. Rendering continued through
the 150-second watchdog. A brief loading pause was sampled at 107 seconds and
then resumed; it is not evidence of the reported gameplay freeze.

Candidate 08 user-operated diagnostic: `.local/loading-traces/20261020-131606-29440`.
The user reported a crash while boosting a Ghost trapped under another tank and
suggested damage as a possible trigger. The harness logged its 180-second watchdog
and terminated its child at approximately 13:19:07; controller and GPU activity
continued through that time, with no recorded unhandled exception or sustained
stall. Therefore this run does not establish a boost/damage crash or successful
vehicle validation. Clarify whether gameplay froze before the timed shutdown.

User clarification: the Ghost session simply closed, with no preceding freeze or
other abnormal behavior. This matches the harness watchdog termination; do not
classify this session as a Ghost boost, collision, or damage crash. The earlier
reported freeze remains unverified by this bounded run. Vehicle entry coverage
and performance acceptance were not explicitly confirmed by this clarification.

## Forge additions reassessment (2026-10-20)

The earlier 11-item list meant no exact (tag group, name) match, not 11 genuinely
new assets. Broader disc inventory and model-variant inspection found:

- Soccer ball: native `vehi` object in armory and other maps; source uses `bloc`.
  Candidate 08 already reuses its native model, collision, physics and materials,
  but still converts the source object wrapper. Full native object selection is
  pending; group differences must be handled explicitly in palette verification.
- Troop Warthog and wrecked-turret Warthog: native Warthog model has `troop` and
  `wrecked_turret` variants (also default, gauss, wrecked, no_turret). Native troop
  child vehicle exists. These are stock asset variants, not new custom vehicles.
- Anti-air Wraith: native Wraith model has `anti_air`; native anti-air child vehicle
  and weapon exist. This is a stock asset variant, not a new custom vehicle.
- Candidate 08 still converts the three variant vehicle root tags. Native model
  availability alone does not prove native seat, weapon or damage configuration.
  Resolve native variant assembly before claiming policy compliance for them.
- No alternate object donor was found on the installed Mythic multiplayer disc
  for Spectre, silenced SMG, Automag, red plasma rifle, auto-turret, Covenant ramp
  or the map-specific credits object. These seven remain donor-unresolved; this
  does not establish absence from Halo 3 campaign or another game/disc.

All 26 ordinary map tag inventories were checked, including mainmenu. shared.map
is a resource cache and cannot be read as a normal named-tag inventory by Cache;
its resource payloads are addressed through donor map tags, not alternate object
names. No additional campaign cache is present in this project's maps directory.
This reassessment changes documentation only, not the active map build.

## Candidate 09: four approved stock Forge equivalents

User requested restoring factory versions of the soccer ball, troop Warthog,
wrecked-turret Warthog and anti-air Wraith, while holding the seven unresolved
items unchanged. `NativeAssets.import_named` now maps these explicitly:

- Soccer ball references the native `vehi` object, replacing the MCC `bloc` root.
- The three vehicles clone their complete relocated stock vehicle roots and
  select the native `troop`, `wrecked_turret`, or `anti_air` model variant.
  Native model variant child objects supply the appropriate troop attachment,
  chaingun, or anti-air turrets. No source vehicle tuning, seats, weapons or damage
  fields are copied into these replacement roots.
- The other seven unresolved palette entries remain as previously converted.

Candidate: `.local/resuscitation/zanzibar-09.map`, 151,502,848 bytes (144.48 MiB),
SHA256 `329fd851df4bd9e03853b771cc9b362e5cb66908d021a3d844eeba0f808b2291`.
All 180 Forge references pass verification, including the intentional soccer-ball
object group change. `verify_stock_equivalents.py` verifies complete root equality
with stock except the selected model variant, checks native variant children and
requires the soccer ball to reference the native object itself. Resource
compaction validates 4,895 references across 5,291 resource slots.
The single shared installation now points Last Resort to candidate 09; Warlock
and the OpenH3M executable are unchanged. Candidate 08 remains the rollback.

Candidate 09 native load check: `.local/loading-traces/20261020-142530-24608`.
Inspected its native capture: the authored desert canyon, base ramps, vehicles,
first-person weapon and HUD are present. Existing bright sky-ring/base materials
remain; this change does not address them. This run checks loading and visible
map content, not spawning/driving each of the four replacements or audio.
Native metadata/resource verification passed (17 vehicles, 154 physics models,
24 animation graphs, 181 render models, 343 bitmaps and 1,105 resource segments).
Removed obsolete candidate 06; candidate 08 remains the rollback.
