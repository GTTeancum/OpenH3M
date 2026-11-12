# Desolation conversion

Pending final review, 2026-11-04; the user will test in Spartan. The prior goal
has been cleared and Halo 4/Haven is now the active work. The user had moved Sky Bridge to pending final review
and designated the Desolation download as the next source. Downloads is read-only;
all extraction, analysis, conversion, builds and tests stay in this repository.

Current Forge decision (2026-11-04): use **Construct's native gameplay palette
with zero Forge scenery entries**. The user means spawn points, objectives,
weapons and similar gameplay editing. The earlier all-map scenery union was an
incorrect interpretation, not a user requirement. Preserve Desolation's authored
map details; this decision removes scenery from the creation menu, not the map.
Use far fewer images in chat; prefer numeric/text evidence and show only images
needed to resolve an actual visual question.

User decision (2026-11-04): **skip agent traversal tests; the user will playtest
traversal later**. Keep traversal unverified for final human review. Remaining
agent checks concern packaging, native loading, visuals/audio and performance;
do not resume walking, jumping or collision-route tests from older plans.

## Source and attribution

Requested map lineage: Desolation, Halo 2. The supplied artifact is an existing
Halo 3 MCC port, not an original Halo 2 cache. Its exact original-geometry
provenance still needs tracing; the filename alone does not establish fidelity.

Source package: MythicJaqui's
[Halo 3 Desolation Map Port (H3MO)](https://www.nexusmods.com/halothemasterchiefcollection/mods/1897),
Nexus mod 1897, version 1.0, updated 2022-05-18. The author page identifies it as a
Waterfall replacement in a larger multiplayer overhaul, and credits Krevil for
the Halo Infinite HUD and Mackaye99 for the MA5K model. Page checked 2026-11-04.
This project's work is the subsequent Xbox 360/OpenH3M adaptation; upstream port
authorship remains MythicJaqui's. Original individual map authorship is not
established by the package page.

The user's latest instruction selects this downloaded package as the current
starting point, superseding the old deferral/source-acquisition state. Original
Xbox 360 Halo 3 stock-asset reuse and gameplay rules remain binding. In particular,
the overhaul's custom HUD/weapons are not approval to replace stock Halo 3 assets.
No publication or asset upload is part of this preflight.

## Verified input

- Archive: `C:/Users/smmel/Downloads/Halo 3 Desolation Map Port (H3MO)-1897-1-0-1652899630.rar`
- Archive size: 1251575010 bytes.
- Archive SHA256: `414189e01acc187fd51d2c3e22ef05b92176ca9382bc4f4d8b6b1af944800208`.
- Members: `halo3/maps/s3d_waterfall.map`, `halo3/fmod/pc/sfx.fsb` and
  `halo3/fmod/pc/sfx.fsb.info`, under the `Halo 3 Desolation` directory.
- Extracted map: `work/desolation/source/Halo 3 Desolation/halo3/maps/s3d_waterfall.map`.
- Map size: 664530944 bytes.
- Map SHA256: `aaf0129aab5aee63a52cacac27657cd85ac7c810b0768b0e386c16e76543333f`.
- Little-endian `daeh` header, version 13; header build date 2022-04-20.
- Existing MCC reader parses 12,000 tags. Scenario 8 and BSP 10246 both have the
  path `levels\multi\derelict\derelict`.

The map, audio index and `sfx.fsb` bank were extracted using the installed Windows
tar tool into `work/desolation/source`. No Downloads source files, installed maps
or runtime binaries were changed.

## Initial checks and next work

`work/desolation/source-preflight.json` contains header identity, hashes, tag
counts and relevant names. `work/desolation/collision-preflight.json` passes the
existing collision-format check: one small collision BSP, no large collision
BSPs, no collision instances and no Havok blocks. This is format evidence only,
not a playable candidate or proof of memory/rendering/performance acceptance.

## Older MCC layout: traced and readable

The existing scenario/dependency audits originally failed with an invalid zero
pointer. The source is the `Apr 20 2022 11:55:21` MCC build. Its scenario root is
0x7B8 bytes, with the BSP block at 0x14, 0x30-byte object/Forge palettes and a
0x24-byte zone-set record. The current schema is 0x780 bytes, with the BSP block
at 0x18, 0x10-byte object palettes, 0x1C-byte Forge entries and 0x28-byte zone sets.
This cannot be repaired by applying one offset adjustment.

Assembly's December 2022 update explains the scenario changes; July 2023 adds
further object/model changes. The existing shared tools now have build-specific
schema selection using the pre-December definitions, not a new converter or a
rewritten source cache. See the shared [MCC schema guidance](README.md#mcc-source-schema-versions).

Read-only evidence in `work/desolation`:

- `scenario-inventory.json`: all 614 scenario block headers, 1,388 rows, 312
  tag references and two data references validate with no errors.
- `object-dependencies.json`: 32 unresolved direct placement-object identities
  and their dependencies are inventoried and structurally validated. This is
  a comparison with Last Resort only, not the required all-disc reuse audit.
- `script-capacity-audit.json`: no scripts, globals or script references;
  all 512 expression slots are inactive capacity. No opcode translation needed.
- `schema-regression.json`: the current Sky Bridge MCC scenario and original
  Last Resort scenario also pass structural validation with their existing layouts.

The source has 122 scenery placements, 43 weapons, 30 equipment and 66 crates;
120/17/30/31 respectively can already be resolved by the existing placement
planner against Last Resort. Two custom tower objects, map lights/lifts, custom
overhaul weapons and ambient sentinels need further tracing. Same-name matches
here establish only a placement plan; native dependency/resource reuse still
needs its own evidence. Two biped placements also require inspection.

The source Forge palettes contain 23 vehicles, 62 weapons, 25 equipment, four
scenery, one teleporter, nine goals and 20 spawners. User decision, 2026-11-04:
**stock Halo 3 Forge palette**, excluding overhaul-only Forge items. The later
clarification selects Construct as the gameplay template and excludes scenery.
Preserve native H3 dependencies, behavior, prices and original format/budget
limits. Do not import the overhaul's gameplay changes just because tags parse.

`forge-and-placements.json` inventories the native selection across all 24 maps:
15 vehicle, 24 weapon, 15 equipment, 220 scenery, six teleporter, nine goal and
19 spawner identities. These 308 entries were assembled in candidate2, which
was rejected after native tracing found 315 quotas against a 256-entry capacity.
Do not reuse that selection. Sandbox alone has
11/24/15/64/3/9/19 respectively;
therefore merely copying Last Resort's or Sandbox's palette does not cover the
all-map inventory. Alternate native prices/limits are retained in the report.
The Last Resort basis lacks localized menu labels for 145 union entries; copy
the corresponding native UI text while relocating the palette, rather than
displaying internal tag names. This historical inventory is not the current
Desolation selection.
User decisions, 2026-11-04: **use stock H3 weapons throughout**, preserving
placed weapon positions; **remove corpses**. The two authored dead-biped
placements (Brute and Grunt) are omitted, including their palette dependencies.
The package replaces their models with overhaul variants and the multiplayer
donor set lacks stock equivalents; campaign assets are no longer required.
Map-specific weapon equivalents are explicit in `desolation_assets.py`, including
DMR to battle rifle, needle rifle to carbine and railgun to Spartan laser.

## Assembly progress and donor evidence

All evidence below is repository-local in `work/desolation`. The initial checks
use the existing converter stages and real source/native caches with in-memory
builders. Full serialized candidate evidence follows in the next section.

- `runtime-stage.json`: zone/PVS/audibility, trigger and editor-folder staging
  passes. The older zone-set record remains 36 bytes.
- `geometry-resource.json`: the BSP geometry is traced through its lightmap
  binding to resource `0xf71015ad`; two vertex buffers, one index buffer,
  eight fixups and three interops convert. No water buffers were reconstructed.
- `lightmap-stage.json`: both authored 1024x1024 arrays (eight SH layers and
  two dominant-light layers) and two scenery probes convert.
- `geometry-stage.json`: complete BSP/material/collision/lightmap stage passes;
  ambient loop and detail sounds reuse original Guardian assets.
- `environment-stage.json`: combined runtime, geometry, spawn, environment,
  map-object dependency and decal stages pass. The map's towers, lifts, lights,
  sky and sentinel flock dependencies remain present; 65 placed decals and 65
  BSP runtime decal entries resolve through 27 palette entries. In-memory
  staging uses 887,972 new metadata bytes and 28,406,613 appended raw bytes;
  these are neither final cache size nor runtime RAM usage.
- `variant-budget.json`: 263 source placements versus the native 640-record
  limit. This does not establish rendering performance or resource residency.
- `donor-candidates.json`: scenario dependency closure, including Forge/editor
  palettes, across 24 original maps. It records 1,274 native-candidate boundaries
  and 2,199 remaining source records, with no structural-read errors. Candidate
  names alone do not establish final equivalence; the closure still includes
  overhaul items now excluded by the Forge decision.
- `stock-target-resources.json`: 4,715 Last Resort resource records, including
  owners, physical page/shared-file locations and every manifest reference;
  4,318 are manifest-referenced. No claim of simultaneous loading is made.
- `map-bitmap-reuse.json`: 31 map-namespaced 2D textures compared against 1,579
  distinct native payloads; no exact base matches. Two lightmap arrays are
  outside this audit's 2D scope. Fifty-four stripped/invalid donor records are
  reported separately. This is not proof that no visual equivalent exists.

The native `old_oil_huge` decal uses `ustdamage_old_oil` in its actual compiled
postprocess texture table. Its same-name original-map texture candidates have
stripped/invalid resources. `decal-dependencies.json` traces the consumer;
`oil-bitmap-reuse.json` finds no exact base match among 168 comparable native
payloads. The audited MCC copy retains 512x512 BC1 data, ten mip levels and curve
3. `desolation_assets.py` pins the full pixel SHA256. The existing native importer
now supports a narrow, explicit recovery of that unavailable storage, keeping
the native bitmap root and consuming shader. No image is fabricated or decal
removed. The stripped original pixels cannot be checked for bit identity.

The older decal schema needed the already-known native decal flag names and
one capitalization normalization. Animated decal parameter data now goes
through the existing checked tag-function converter. Eighteen focused tests
pass across source-schema selection, old/current Forge/spawn records and
audited bitmap recovery, including rejection of changed/unaudited data.

## Historical candidate2: rejected Forge quota overflow

`build-desolation.ps1 -Candidate 2` invokes the existing
`build_scenario_checkpoint.py --desolation --slot zanzibar` pipeline, enabling the
identified older schema, explicit weapon aliases, corpse omissions, full stock
Forge selection and audited oil-texture recovery. Candidate1 stopped before
publication on two invalid guessed donor paths; candidate2 uses the actual stock
Mauler (`excavator`) and Brute Shot (`support_low`) identities.

- Cache: `.local/desolation/candidate2/zanzibar.map`, 174866432 bytes.
- SHA256: `b0e360e35e948997dae76863ff3adb1490f8d37d5d7721c44af2f742a64ba736`.
- Build report: `.local/desolation/candidate2/build.json`; log:
  `work/desolation/build-candidate2.log`.
- 11883216 metadata bytes and 134218077 appended raw bytes. These are file/build
  measurements, not console RAM use.
- Scenario: 122 scenery, 43 weapons, 30 equipment, 66 crates, zero bipeds.
  Scenario coverage and native header authentication pass; 961 collision trees,
  56233 packed nodes, 10023 BSP leaves and 65 runtime decals validate.
- `candidate2-policy-verification.json` checks the serialized result against the
  original inputs: all 43 weapon positions/rotations/scales are unchanged, all
  46 weapon tags retain native metadata and referenced identities, both corpse
  placements are absent, and all 308 Forge entries retain donor limits/prices
  and actual English display text. The native Last Resort Forge budget remains
  700; 100 unique missing English labels were added. Other languages unverified.
- `candidate2-native-assets.log`: 25 animation graphs, 506 bitmaps, 354 models,
  281 physics models and 22 vehicles pass the existing native metadata verifier;
  1803 resource segments match their donors.
- `candidate2-native-sounds.log`: 231 native sounds retain identical codecs and
  packets. `candidate2-compaction.log`: 403 retained/repacked segments totaling
  25534760 bytes match; original shared-page descriptors remain unchanged.
- All 18 focused schema/record/bitmap-recovery tests pass after integration.

The private runtime layout is `work/desolation/candidate2-run`; runtime hashes
and native asset links are recorded in `preparation.json`. Installed maps,
profiles and shared runtime files have not been changed. Native loading,
traversal, visuals, audible audio, Forge creation and measured performance are
still under validation. No LIVE DLC or release acceptance yet.

Three private 180-second runs reached Slayer/Forge. Seventeen native captures
were inspected sequentially before the user requested substantially fewer
images. The first run completed only five of its six requested frames; it is
explicitly rejected as a complete capture schedule. Later six-frame runs show
readable equipment/scenery menus and one stock Sandbox wall created/released.
The wall is also present in the native v12 variant at slot 261, quota 54, with
its original $5 cost. **That local success does not validate the palette:** the
same native variant declares 315 quotas, exceeding its fixed 256-row array.
Candidate2 must not be packaged or installed. See
`work/desolation/candidate2-forge-creation-review.json`.

Short candidate2 opening-view timing was 29.97 FPS, p95 33.65 ms. Movement tests
covered only a few units and often ended against a wall; these are not full-map
performance/traversal acceptance. Two seconds of native six-channel PCM were
recorded, without a listening/content acceptance claim.

## Current candidate3: Construct gameplay palette

`build-desolation.ps1 -Candidate 3` uses only original `construct.map` as the
Forge template and excludes its Scenery category. Native counts are 3 vehicles,
22 weapons, 15 equipment, **0 scenery**, 3 teleporters, 9 objectives and 19
spawners: 71 entries. Native prices, limits and English text are retained. The
authored 122 scenery placements and all other map details remain present;
43 weapon positions remain unchanged and the two corpses remain absent.

- Cache: `.local/desolation/candidate3/zanzibar.map`, 73084928 bytes.
- SHA256: `a9fe558fd5609f5af36a0587760181db72959b853b3cd5572453c90791fd3414`.
- Metadata: 5042440 bytes; 8537 tags. These are build measurements, not RAM use.
- `candidate3-policy-verification.json` checks all placement decisions and
  compares all 36 weapon tags with their stock metadata/references.
- `candidate3-native-assets.log`: 12 animation graphs, 80 bitmaps, 41 models,
  29 physics models, 2 vehicles and 1040 native resource segments verified.
  `candidate3-native-sounds.log`: 96 imported stock sound codecs/packets match.
- New pre-publication quota guard counts palette entries plus a conservative
  bound for distinct placed assets outside the palette. Candidate3 is 71+16=87
  against 256; actual native counts are still checked at runtime. The regression
  check rejects candidate2 (upper bound 323) and accepts original Construct.
- Existing Last Resort basis budget remains 700. No native capacity is raised.

Private runtime: `work/desolation/candidate3-run`. Two 180-second runs used one
menu capture each. The first reached the empty Goals category and did not create
an object; it is not accepted as a spawn/objective check. The corrected route
opens **Spawners (6 of 7)** with readable `Respawn Point`, 16 remaining and $0
cost. Native records then prove one new respawn point at slot 261, quota 43,
position `(14.17844, 14.22967, 8.10809)`, native maximum 100 and zero cost.
The native variant has **79 quotas / 256**, 261 authored slots and 262 total
slots, with maximum budget 700 and spent budget 552. This resolves candidate2's
overflow without changing native capacity.

Evidence: `work/desolation/candidate3-runtime-review.json`, native run
`.local/loading-traces/20261104-140447-21828`. Four native hash checks pass.
Forward movement covers 9.17 world units. The approximately eight-second timing
window is 29.84 FPS, p95 33.79 ms, with three intervals above 50 ms; this diagnostic
run includes resource/debugger observations and does **not** establish sustained
30 FPS acceptance. Three resource snapshots were discarded because the heap
changed during reading; they are recorded rather than treated as valid samples.
At this stage, objective-specific Forge sessions, audio listening, performance
without diagnostic overhead, save/reload and LIVE loading were pending. The DLC
and warm timing results below resolve loading and opening-view performance;
traversal remains deferred to the user's later playtest.
Both Forge test processes exited after their watchdogs.

Next: validate the distinct LIVE candidate and prepare final review, leaving
traversal to the user's playtest. The extracted source cache stays immutable.
Unattended native runs use process-local input and a maximum 180-second watchdog;
visual proof uses the game's own captures. No desktop input or capture app.

## Candidate3 LIVE staging

The existing DLC pipeline registers `desolation`, map ID **1748**, independently
of Last Resort and the other converted maps. Registry IDs are unique and the
original 36 mapinfo records have no conflicting ID. Staging changes only the
cache header and scenario map ID; all remaining candidate3 bytes are identical.

- Payload: `work/desolation/candidate3-dlc/payload`.
- Map SHA256: `8687d2a3c0148c7621165fb87dc24f168e323d1d48d453f881a6cfd9d9e9228a`.
- LIVE: `work/desolation/candidate3-dlc/bundle/846CBB605538E556159FDE8E6D69518774C2C1A4`.
- LIVE SHA256: `3a0bb910ffe59cb6e082a346cefd2ae3ca4fe793fd76ef278fa689bbf03ecc83`;
  73658368 bytes, seven files.
- All STFS hashes, file chains and payload bytes pass the existing verifier.
  The actual runtime STFS reader independently reads and compares all seven
  files (`native-stfs.log`). Native cache header/tag-memory preflight passes.
- Five native preview BLFs use the previously inspected native opening-view
  capture from candidate2. It shows the authored arena and stock HUD, with no
  Forge menu. The rejected candidate2 cache is **not** packaged. This is a
  review preview from this adaptation, not artwork attributed to the upstream
  author. Source path/hash are recorded in `previews.json`.
- `console/default.xex` is a separate output of the existing version-checked
  custom-content patch, byte-identical to the current codegen input. SHA256:
  `0d73d4ef8544be05a4b08027255fa5ba246286018c1f1b92253113db04726940`.
  Original XEX, maps and installed content remain unchanged. RGH/JTAG hardware
  execution and system-link compatibility have not been tested.

Reproduction: `work/desolation/build-candidate3-dlc.py` calls the existing
payload, native preview and LIVE builders, verifies the identity-only cache
changes and compares the complete container payload. It refuses an existing
output directory. General preview tooling now accepts explicit `--map` and
`--image MAP=PATH` inputs for registered maps without Workshop artwork; source
hashes remain part of the report.

### Native DLC review evidence

`.local/loading-traces/20261104-141856-38756` installs the LIVE package through
the native content manager into its isolated profile. All seven installed files
match the packaged payload; 11 native resource/hash checks pass with zero failures.
The two captures were inspected individually: Desolation appears alphabetically
between Construct and Epitaph with its actual preview, and the loaded opening
view shows the central tower, forest canopy, vines, reflective floor, blue object
lighting and stock HUD/weapon. The side walls are dark. This is opening-view
evidence, not an all-viewpoint or animation acceptance claim.

The first stationary timing window measured 29.90 FPS over 44.98 seconds, p95
33.78 ms, with one 135.07 ms interval and one 50.09 ms interval. The retained
outlier log shows output-mailbox/paint-lock waits and a subsequent resolve wait;
it does not establish one root cause. No timing intervals were discarded and
neither image capture overlaps the measured window.

The warm installed-content repeat,
`.local/loading-traces/20261104-142416-45384`, measured **29.98 FPS over 39.99
seconds**, median 33.37 ms, p95 33.81 ms, maximum 34.75 ms, **zero intervals over
50 ms** and no skipped painted-frame numbers. No screenshots or traversal inputs
were used. The timing window ends before the audio debugger is armed or either
firing input occurs. Both runs finish under their 180-second watchdogs. This
supports 30 FPS pacing in the stationary opening view only, not full-map or
console performance. The first run's hitch remains recorded, not declared fixed.

The repeat also records six seconds / 1125 blocks of native six-channel PCM,
including two process-local trigger presses. Samples are finite, peak 0.28373,
with nonzero front/rear channels. The raw submitted PCM and six-channel WAV are
retained in the trace directory. A mono listening copy is under
`work/desolation/candidate3-dlc/audio-review-mono.wav` (and MP3); it is an
equal-weight downmix without normalization or denoising. This chat cannot hear
audio input, so actual sound content/mix acceptance remains pending human review.
Nonzero PCM alone is not recorded as audio acceptance.

Reports: `candidate3-dlc/native-review.json`, `warm-audio-review.json`,
`pacing-outliers.json`, `preview-validation.json` and `console-xex.json` under
`work/desolation`. Native preview dimensions, JPEG structure and SHA1 EOF checks
pass for all five variants. Missing explicit artwork and unregistered image-map
identities are rejected by the generalized preview builder.

### Later human playtest

`tools/warlock-conversion/launch-desolation-review.ps1` is prepared for the user's
later review. It checks the LIVE and seven runtime hashes, installs only into
`work/desolation/manual-review/profile`, and launches normal controls with no
replay or shutdown timer. Its `-ValidateOnly` mode passed without launching a
game. Select **Desolation** from the ordinary map list. The shared installation,
stock map files, existing saves and installed DLC are not overwritten.

Pending human checks: traversal (explicitly deferred by the user), sound/mix,
views and animated effects beyond the opening scene, objective-specific Forge
editing, and save/reload. RGH/JTAG hardware and system-link testing remain
unverified. The LIVE package is a review candidate, not a final release.

### Complete native Forge object audit

`work/desolation/audit-native-gameplay.py` now compares all **71 selected Forge
objects** in the final DLC cache against their actual original-H3 donors. Every
schema scalar and nested block matches after relocating pointers, while tag
references and string IDs are checked by resolved identity. This expands the
earlier weapon and resource checks to equipment, vehicles, objectives, spawn
markers and teleporters. No gameplay tuning or native type/mode flag differences
were found. Report: `candidate3-dlc/native-gameplay-audit.json`.

All nine goal markers retain their original game-mode masks: two CTF, two
Assault, and one each for Juggernaut, King of the Hill, Oddball, Territories and
VIP. None enables Slayer. This is consistent with the empty Goals category in
the default Forge session; it is not independent proof of runtime filtering in
each objective mode. Do not broaden the native masks to populate that category.

### Deleted private review archive

User decision, 2026-11-04: delete the review ZIP; the user will test in Spartan.
The ZIP was deleted and its absence verified. The private map, LIVE package and
manual launcher remain available. The following archive details are historical.

`work/desolation/candidate3-dlc/Desolation-candidate3-review.zip` contained the
LIVE file in its standard Content/title/type directory, the separate console
candidate, attribution/review instructions, two existing native proof frames,
the audio listening copy and the verification reports. Size: 55918847 bytes.
SHA256: `2bdcb1b9805470b35fb7e2b61a74a6eb6a4ef7d5c651cba34255ecf3ceed78e8`.
All 19 archived entries were read back and compared with their source hashes.
`review-manifest.json` and `review-archive.json` record the exact contents.
Nothing was deployed outside the repository or uploaded.

The final preservation check rehashes the original Downloads archive, extracted
MCC cache, stock Last Resort cache and original Mythic XEX. All four match their
initial hashes (`source-preservation.json`). The manual launcher again passes
`-ValidateOnly`. Human sound and broader visual feedback is requested for the
user's later playtest; no final audio/visual release acceptance is claimed.
