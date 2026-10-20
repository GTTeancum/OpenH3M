# Prisoner conversion

Status: candidate 09 is staged. Bright bullet-impact patches are resolved;
the completion goal remains active pending room-wide visual/traversal acceptance.

Source is **Halo Generational Combat**, installed Workshop item `2962955878`,
`D:/SteamLibrary/steamapps/workshop/content/976730/2962955878/maps/prisoner.map`.
The other installed Prisoner (item `3583572796`, H2CE Public Test) uses Halo 2 and
is not the selected source.

The user selected Cold Storage (`chillout.map`) as the replacement. Keep the
single `.local/custom-maps-play` installation alongside Warlock/Blackout and
Resuscitation/Last Resort. Do not change OpenH3M or original disc files.

## Asset decisions

- Apply the repository's stock Halo 3 asset policy to all equivalents, including
  CE/H2-styled guns, grenades, powerups, vehicles and cosmetic faction variants.
  Explicit mappings are in `snapshot/tools/generational_assets.py`.
- Source has 157 Forge entries. On 2026-10-20 the user explicitly requested
  removing health packs, both placed objects and the Forge entry. Their source
  `Health Pack` equipment block (100 health, 100 shield) is MCC-only.
  Expected remaining Forge count: 156.
- Preserve unique authored geometry and objects without stock equivalents.
  Source contains one placed custom jet; do not silently remove it.
- Keep generated assets, reports and logs under the project `.local` directory.
  Failed attempts reuse the same candidate/report names when no map was emitted.

## Reproduction

Run from `.local/OpenH3M-source`:

```powershell
python -B tools/warlock-conversion/snapshot/tools/build_scenario_checkpoint.py `
  --project ../.. --slot chillout `
  --source D:/SteamLibrary/steamapps/workshop/content/976730/2962955878/maps/prisoner.map `
  --basis ../../maps/chillout.map --xex ../../default.xex `
  --sound-bank D:/SteamLibrary/steamapps/workshop/content/976730/2962955878/halo3/fmod/pc/sfx.fsb `
  --decoder ../tools/vgmstream-r2117/vgmstream-cli.exe `
  --output ../prisoner/chillout-09.map --report ../reports/prisoner-09.json
```

The builder rejects an existing output; select a new candidate name after a
successful build. Verify resource handles, the palette after approved omissions,
stock equivalents and loading before staging an accepted candidate.

## Format handling added

- Resolve geometry resource types by the source's type-name table rather than a
  fixed numerical type index.
- Use the existing collision MOPP conversion for BSP breakable-surface records.
- Preserve trigger volumes and scenario light-volume placements/palettes.
- Support legacy identity-range lens curves and constant unit scale ranges.
- Use Cold Storage's native opaque shader prototype with the same template
  options as the existing Blackout prototype.

Visual, sound, collision, Forge and gameplay acceptance must be recorded from
actual checks; successful serialization alone does not establish them.

## Candidate 01

`.local/prisoner/chillout-01.map`, 108,892,160 bytes (103.85 MiB).
SHA256 `60be691efb7cf0775058c77dde475766dd4fff08174b494967fe62ef848b06ad`.
This candidate failed to reach gameplay and has been superseded.

- 156 Forge entries verified after the explicitly approved health-pack removal.
- Four health-pack placements removed: 24 source equipment placements become 20.
  No health-pack tag is imported.
- 37 explicit stock-equivalent mappings verified, including shared destination
  handles for cosmetic weapon/vehicle variants.
- 4,617 typed resource references validated across 5,059 resource slots.
- Header preflight passed for all three installed converted maps.
- Preserved 96 scenery, six weapons, 59 crates, one custom jet, one effect-scenery
  and one light-volume placement. Unused flock/creature palettes are omitted only
  when their placement arrays are empty.
- Broader native player animation graphs replace Cold Storage's restricted
  graphs. The donor still lacks `shade_d`; Shade use is a known outstanding
  animation dependency, also present in the prior Resuscitation work.

No claim of exhaustive Forge behavior, vehicle use, collision or audio testing.
The original disc, Warlock and Resuscitation map binaries remain unchanged.

## Black-screen diagnosis and candidate 02

The user confirmed both correctly selected Cold Storage attempts remained black.
They assisted with input but do not want to drive diagnostic runs. Use the
runtime's process-local input script; never host input or desktop automation.
The menu includes entries whose map files are absent from the shared test
installation. Two DOWN steps selected Construct in the unattended candidate-02
run (user observed); three selected Epitaph (native capture). Cold Storage is
before Construct, so use one DOWN. Neither wrong-map run is a Prisoner load
result.

Bounded thread samples in `.local/loading-traces/20261020-150107-22668`
repeatedly found the loading thread in guest `0x820ab9f0`, a packed collision
tree traversal. The BSP resource tree was valid, but 47 custom object collision
trees contained invalid links/cycles. The XML describes retail byte fields;
MCC stores each node as a single little-endian uint64. Convert the whole packed
word to big endian, preserving its two 24-bit children and 16-bit plane.

Candidate 02: `.local/prisoner/chillout-02.map`, 108,892,160 bytes.
SHA256 `07ab9a533e00f195d21109a56bb1941b3bbeb3c25833097d38a93f1e240b4962`.
The shared installation's `maps/chillout.map` is a hardlink to this candidate.
All 782 object collision trees / 56,450 packed nodes pass the new
`verify_collision_trees.py` check; candidate 01 fails it and stock Cold Storage
passes. The builder now runs that check before publishing future outputs.
Resource references, all 156 Forge entries and 37 stock equivalents also pass.

Unattended run `.local/loading-traces/20261020-151411-32808` verified `chillout`
at 102.671 seconds, passed all six observed hashes, and reached first-person
gameplay in the native capture at 135 seconds. The 150-second watchdog ended
the run normally. No human input was needed.

The inspected capture shows textured interior geometry, the stock assault rifle
and HUD. The spawn faces a wall with a strong bright light at the right edge;
this proves the black-screen failure is fixed but does not establish room-wide
visual quality, movement, audio, Forge behavior or vehicle usability. No
interactive desktop control was used. Keep those checks explicitly outstanding.

A second run, `.local/loading-traces/20261020-151918-24344`, used `--walk-check`:
the runtime logged right-stick input at 120 seconds and forward input at 124
seconds. The inspected capture shows a changed view close to a wall; it is not
a room-wide visual proof or a traversal/collision acceptance test. This run
also reached its 150-second watchdog with six successful hashes and no observed
crash. Broader validation remains outstanding.

Candidate 01 and temporary audit scripts were deleted; build reports and
diagnostic logs retain the failure evidence. Completed attempts' duplicate
shader caches were removed. Warlock and Resuscitation were not rebuilt during
this fix.

## Material quality pass (candidate 05)

Candidate: `.local/prisoner/chillout-05.map`, 109,891,584 bytes (104.80 MiB).
SHA256 `82bc085b55f5d29a165d45a636a00b1bb390778932e99b08c208762970e7a8bc`.
Candidate 02 is the retained rollback; intermediate 03/04 builds are disposable.

- Sixteen authored metal, glass, floor-indicator and light materials now use
  matching native Halo 3 shader variants rather than the opaque hall-tile
  fallback. MCC's three trailing options must all be default before matching.
  All texture parameters are represented; a serialized comparison verified
  162 shared float4 constants against the source in candidate 03.
- The custom invisible material reuses `objects/multi/shaders/invisible` from
  the original disc, replacing an incorrectly opaque approximation.
- Donor-specific shader animations are stripped. The two authored floor
  indicators retain static source parameters pending multipass animation
  conversion; unrelated donor blinking must not be inherited.
- Seven metal materials still omit MCC's bump-detail strength parameter. The
  generator's exact shader combination is absent from the disc and retains
  the existing fallback. These are explicitly unresolved quality limitations.
- Builder collision checks pass (782 trees / 56,450 nodes), as do 4,626 typed
  resource references, 38 stock equivalents and all 156 Forge entries.

The candidate-03 native capture restored ceiling detail but still showed a
bright, washed-out spawn view. This pass does not claim lighting is finished.
Candidate-05 native capture was inspected in run
`.local/loading-traces/20261020-153312-18904`: textured geometry, ceiling detail,
stock weapon and HUD render in gameplay. The strong light at the spawn and
washed-out surfaces remain visible; neither invisible-material restoration nor
native shader matching resolved that lighting problem. This is a material
correctness pass, not final visual acceptance. Cold Storage header verification
passed at 102.687 seconds. Candidate 05 is staged in the shared installation.

## Completion work (candidate 08)

Current staged map: `.local/prisoner/chillout-08.map`, 110,436,352 bytes
(105.32 MiB), SHA256
`a00964d516bb118ce332db9c4ed29ce00f734c897f4bad3a67c938cc19452fca`.
The older staging descriptions above are historical. Keep candidate 02 as the
single rollback while acceptance is pending.

- All 17 authored world materials use native shader combinations. The generator
  uses the native environment-enabled variant with its extra environment tint
  set to zero, preserving source emission without adding reflection.
- Multipass animation routes are remapped by parameter name, shader pass and
  component mask. Both floor indicators and the generator retain all three
  authored animation functions. Serialized verification passes for 180 float4
  constants and all three function payloads.
- Seven omitted MCC bump-detail-strength constants are exactly unity; native
  shaders already apply that strength. Non-unit values now fail explicitly.
- sRGB/XRGB color textures use native AS16 GPU formats and RGB gamma signs;
  linear/normal/lightmap textures retain their data formats. Retail Cold Storage
  controls provide the comparison: BC1 `0x1a207f73`, BC3 `0x1a207f75`, ARGB32
  `0x18287fb2`. MCC sRGB maps to the console gamma sampling approximation.
  Hardware format definitions: https://raw.githubusercontent.com/xenia-project/xenia/master/src/xenia/gpu/xenos.h
- Stock Guardian Shade seat modes are inherited by both native player graphs.
  Native animations/resources remain unmodified; node maps and mode references
  bind the donor graph. The missing-mode lists are now empty. Validation checks
  1,774 Master Chief and 1,987 Elite animation targets and their node mappings.
  This does not constitute an interactive Shade seating test.
- 156 Forge entries, 38 stock equivalents, 4,996 typed resource references and
  all collision trees pass. All three installed maps pass header preflight.
- Native run `20261020-160100-22996` loaded the map, executed process-local
  backward/forward movement and turning, fired six rounds (32 to 26), and ended
  at the watchdog without an observed crash. Its inspected capture is still a
  close wall view and shows bright square bullet-impact patches. These are
  unresolved visual acceptance issues, not a completed proof.

Focused verification commands (same working directory as reproduction):

```powershell
python -B tools/warlock-conversion/snapshot/tools/verify_player_animations.py --map ../prisoner/chillout-08.map
python -B tools/warlock-conversion/snapshot/tools/verify_resource_indices.py --map ../prisoner/chillout-08.map
python -B tools/warlock-conversion/snapshot/tools/verify_material_parameters.py --source D:/SteamLibrary/steamapps/workshop/content/976730/2962955878/maps/prisoner.map --map ../prisoner/chillout-08.map --report ../reports/prisoner-08.json
```

## Candidate 09: native metal impact response

Current map: `.local/prisoner/chillout-09.map`, SHA256
`3b83228400aa242383e82f090fea80f9384748fd9eafad95f9b2efb4f475ca55`.
Only the current candidate and candidate 02 rollback are retained.

The source's unassigned `metal_*` collision surfaces used `default_material`.
They now use stock Halo 3 `hard_metal_thick`; explicit source assignments and
non-metal surfaces are preserved. This is reported per surface in the build.
An untouched Cold Storage control run (`20261020-160814-25588`) showed normal
impact decals, whereas candidate 08 produced bright square patches. Candidate
09's native capture (`20261020-161430-34512`) shows properly cut-out bullet holes
with no bright square backgrounds after firing six rounds. The 150-second run
ended at its watchdog without an observed crash.

All 156 Forge entries, 38 stock equivalents, 4,996 typed resource references,
17 world materials / 180 float4 constants / three authored animations still
pass. The builder now verifies player animation references before publishing.
Focused native-player verification also compared all four imported player
graphs and 902 resource segments to their disc donors; only the explicit Shade
inheritance/lookup additions differ.

Several scripted movement/turn attempts ended facing nearby walls. Those
captures do not demonstrate room-wide quality or traversal. A read-only
`--sample-world` diagnostic in `trace_loading.py` records bounded object/player
table data on the first impact so subsequent navigation can be based on game
state instead of guessing. No host input, capture app, executable edits or
original-disc modifications are used. Completion is still pending.
