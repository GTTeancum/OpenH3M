# Chiron TL-34 conversion

Status: candidate 05 installed and accepted. User verified doorway-edge triggering on 2026-10-23; testing stopped at their request.

Use the Halo 3 port in Halo Generational Combat workshop item 2962955878,
`maps/putput.map`; source scenario `custom\levels\multiplayer\putput\putput`.
Cold Storage is only the assembly basis. The separate DLC identity is `chiron`,
map ID 1732, title Chiron TL-34. Preserve stock maps, Prisoner, the other custom
maps, and saved Forge layouts. The user explicitly removed the decorative CE
marine. Existing Halo 3 weapons/equipment use original-disc assets.

## Repeatable build

Run from this repository, using Python 3.12 with `-B`. Keep TEMP/TMP in
`.local/build-temp`. Tool paths below are relative to
`tools/warlock-conversion/snapshot/tools/`.

1. `build_scenario_checkpoint.py --project C:/X360/ISOs/H3M --slot chillout
   --chiron --source D:/SteamLibrary/steamapps/workshop/content/976730/2962955878/maps/putput.map
   --basis C:/X360/ISOs/H3M/maps/chillout.map --xex C:/X360/ISOs/H3M/default.xex
   --sound-bank D:/SteamLibrary/steamapps/workshop/content/976730/2962955878/halo3/fmod/pc/sfx.fsb
   --decoder C:/X360/ISOs/H3M/.local/tools/vgmstream-r2117/vgmstream-cli.exe
   --output work/chiron/chillout-05.map --report work/chiron/build-05.json`.
2. `build_dlc_payload.py --converted work/chiron --stock C:/X360/ISOs/H3M/maps
   --output work/chiron/payload-05 --report work/chiron/payload-05.json
   --map chiron --source-map work/chiron/chillout-05.map`.
3. Hardlink existing bundle entries for the other five maps into the new payload.
   Generate Chiron's five preview BLFs with `build_dlc_previews.py` (the build
   function accepts a names filter; the CLI rebuilds all present map previews).
4. `build_dlc_live.py --payload work/chiron/payload-05
   --output work/chiron/live-05/candidate --report work/chiron/live-05.json`.
   The package is renamed to its content ID; use the report's package path.
5. Validate with `trace_loading.py --dlc-package <reported path> --dlc-map chiron
   --slot chillout --capture --capture-times-ms 135000 --walk-check
   --sample-observer --timing-diagnostics --cache-root work/chiron/prepared-cache
   --seconds 180`, plus project/game/exe/hash arguments from existing run logs.
6. Promote using `promote_layout_bundle.py` only after native installation and
   verification. Preserve the existing profile and one previous-content rollback.

Use fresh numbered output paths when rebuilding; never overwrite a hardlinked
installed map in place. Chiron is 106,651,648 bytes (101.71 MiB). Candidate 05 DLC
SHA256: `8db783e1ec99b166ee11806b0597b2e5161d0c8548f852c0438d5756a733c912`.

## Materials and decals

Chiron enables native H3 shader mappings for custom level surfaces, retaining
textures, normal/detail maps, animation and placements. Opaque diffuse emission
uses the verified alpha-blended native template with a private opaque-alpha base
texture. BC1/BC2/BC3 are decoded for that explicit operation only. The ladder
material still uses the reported fallback; not every surface has been inspected.

The native `unscdf_flag_white` decal texture exists only in Cyberdyne on this disc,
with a stripped resource. After exhausting native donors, Chiron recovers that
same-named MCC bitmap while preserving the native referencing decal and shader.

The authored explosion scorch palette entry uses native static
`levels\shared\decals\human\damage\scorch`. Positions and dynamic weapon impact
effects are unchanged. Run 04's 115-second native capture confirms that the
original ramp-wall scorch no longer has a rectangular backing.

## Wall teleporters

There are 30 custom wall teleporters, paired on channels 0 through 14. They are
not stock H3 pads hidden behind wall visuals. Their custom object has multiplayer
type 9 (two-way teleporter) and retains its model and shield shader. The shield
uses exact native `_2_0_0_0_0_0_3_1_0_0` with authored noise and animation.

Two independent trigger issues were found:

- 23 source placements override the object defaults with a zero-radius sphere.
- The object's source default is a cylinder of radius 0.2, whereas its wall spans
  local Y -0.464226 to +0.522066. Edge approaches can miss the narrow cylinder.

Candidate 04 restored default cylinders only. It was superseded before deployment
following the user's edge-approach report. Candidate 05 uses H3's oriented box on
all 30 placements and the private custom tag defaults (including newly forged
instances). Box dimensions are X 0.4, Y 1.084132, +height 2, -height 0.5. Width is
derived from the actual render-model compression bounds with 0.02 edge clearance;
original depth and height coverage are preserved. Placement position, rotation,
scale and channel are unchanged. No stock teleporter tags or engine behavior are
modified. `teleporter-verify-05.json` verifies serialized coverage of all model
corners and exact preservation of positions/channels for all 30 instances.

Box dimension interpretation was checked against ManagedDonkey's boundary renderer:
https://github.com/twist84/ManagedDonkey/blob/main/game/source/objects/multiplayer_game_objects.cpp
It uses full X width and full Y length, divided by two for local bounds.

## Timing and evidence

Run 03 recorded gameplay pipeline compilation up to 3023.584 ms. This explains
some first-encounter hitches, not necessarily every reported pause.
`merge_native_shader_cache.py` deduplicates compatible native cache records while
preserving existing-map records. It rejects mismatched headers/hash collisions
and reports any incomplete watchdog-truncated final record it excludes.

Prepared cache originally merged `work/dlc/cache` plus runs 01/02. Run 04 loaded
628 shaders and prepared 732 pipelines at startup (19.068 seconds), then logged
no preparation >=8 ms after gameplay began on that covered route. Run 05 visited
additional rooms and compiled additional pipelines; those records are retained
in the prepared cache. Do not claim exhaustive prewarming or stutter-free play.

Native evidence under `.local/loading-traces`:

- `20261023-211122-34644`: correct menu identity/preview; original decal defect.
- `20261023-211621-31528`: animated portal after shader mapping correction.
- `20261023-212233-40076`: pipeline stall measurements.
- `20261023-212941-44452`: visually corrected scorch and cached-route timing.
- `20261023-213632-35156`: candidate 04, 11 hash checks passed; multiple observed
  room-to-room jumps, including repeat trips through a pair. User input may have
  contributed. This does not establish successful traversal of every portal.

Native menu selection is 13 UP steps from Last Resort in the six-map bundle.
The scripted strafe assumes the initially observed spawn; validate observer data
instead of assuming input implies traversal. The capture timer starts after
runtime preparation, while the watchdog begins at launch. Leave startup margin.
The executable remains unchanged, pinned SHA256
`e3f60b3d3efee1ff244bfa83e3be06112d4220808db6d356020a65fce5a3670c`.

## Cleanup and limits

Automatic approval review rejected cleanup of obsolete Chiron candidates and
extracted test content as "blocked by policy". These remain in `work/chiron` and
loading-trace directories; do not claim cleanup complete or bypass the rejection
with another deletion mechanism. Original disc assets remain unchanged. These
PC checks do not certify console memory residency or system-link compatibility.

## Accepted installation

Run 06 (`20261023-214505-17200`) loaded candidate 05, passed all 11 resource hash
checks and produced the inspected native portal capture. The user verified the
doorway edges and said "Job done". No additional test runs were performed.

Promotion report: `work/chiron/promotion.json`. Installed content ID:
`8EC0EDDF0F6E421EBB6E3126343A0CC4C708407A` in `work/dlc/installed-current`.
The existing bootstrap already points there; launch `C:/X360/ISOs/H3M/OpenH3M.exe`
as usual. Other maps, saved-layout profiles, executable and original disc files
were preserved. One previous bundle remains in `work/chiron/previous-installed-content`.

The installed shader cache now retains 632 shaders and 749 pipeline records,
including the newly visited rooms and all previous installed cache records.
Final merge report: `work/chiron/final-cache.json`; no incomplete tails excluded.
Previous two cache files are retained in `work/chiron/previous-shader-cache`.
This improves repeat visits; no exhaustive hitch-free claim was made.


## Lighting colour correction (2026-11-23, candidate cool-04, staged only)

User request 2026-11-23: remove the yellow cast and return the original's cooler
light colour. Per-map lighting correction is authorized (AGENTS.md brightness rule).

Cause: the HGC source port's own lighting. Camera colours are neutral and the
scenario's global screen effect only adds gamma +0.15 (neutral filter). The baked
per-pixel lightmap is warm in all five of its layers: SH terms 0-3 (ranges 161,
186, 201, 203) and dominant-light intensity (range 341); the ranges sit 0x18 apart
at Lbsp+0x08 (Compression Vectors 0,2,4,6,8 x). Decoded with `decode_bpp16_luvw`
(lightmap_sampling.fx), term 0 has log-mean blue/green 0.364, red/green 0.774;
dominant intensity mean blue/green 0.367. Original Halo CE Chiron (MCC
`halo1/maps/putput.map`, read-only; lightmap padding colours 0xFFE0/0xF800
excluded) has blue/green 0.555, red/green 0.786: about 1.5x more blue, red equal.
The four map-private placed light types are also warm (#deb52e yellow
shadow-casting frustum light x4, #e7a281, #b56442, #cba695).

The HGC Workshop source (2962955878) is no longer on D:, so this is a post-build
edit of the console-repair-candidate `chiron.map` (SHA256 33d66a13...) with
`snapshot/tools/lightmap_color_balance.py --gains 1 1 1.5 --light-chroma 0.87 1 0.93`:

- Lightmap: blue x1.5 in all eight SH layers and both dominant layers. Red, green,
  alpha (luminance), indices, sizes and tiling are bit-identical. Decoded term-0
  blue/green after: 0.548 (target 0.555); mean blue error 0.9% of green. Pages
  rewritten in their own slots (4,777,628 / 4,780,032 and 1,099,422 / 1,105,920 bytes).
- 102 scenery probes: blue SH and dominant colour x1.5. These are big-endian half
  floats although the Assembly plugin labels them int16 (an int16 scaling produced
  saturated blue objects in a rejected intermediate).
- Placed lights: colour balance set to Halo CE's brightest lightmap colour (0xEFFE,
  linear 0.87:1:0.93) keeping each light's luminance: #b0bcb6, #a9b4ae, #747b77,
  #a5b0aa. Intensity, falloff, shape and placements unchanged. Stock/shared lights
  (weapons, effects, teleporter green light) are untouched.
- Page CRC/salted SHA1s, body XOR and both metadata digests refreshed (the input's
  metadata digests were already stale; its header digest reproduces with the retail
  salt). RSA signature not regenerated.

Native check, PC port hidden desktop, fixed points `.local/lighting-colour/chiron/points.txt`:
before `run-before`, after `run-after-04`, side by side in
`.local/lighting-colour/chiron/chiron-before-after.png`. All three points valid,
30 FPS both runs. Screen blue/green at the three spots: 0.71->0.91, 0.53->0.72,
0.58->0.77; screen brightness unchanged. The left of spot 2 keeps a mild tan,
consistent with the wall texture's own colour (textures were not changed).

Package: `.local/lighting-colour/chiron/live-04/Chiron_20261123` (content ID
7FB4424F7E9462C8D7C567CC4CF93DC83F8A1A46; rename back to the content ID if the
console does not list a map-named file). It replaces the console-repair-candidate
Chiron package; do not install both. Not checked on a
real Xbox 360; rest of the map beyond three spots not inspected.

Installed 2026-11-23 at the user's request into the console release set
`C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/releases/console-repair-candidate` (combined
and per-map Content folders, payload `chiron.map` regenerated byte-identically); previous
package kept in its `rollback-chiron-20261123`. Copying to the console is the user's step.

Accepted 2026-11-26: the user reports Chiron TL-34 passes with the lighting-colour package (Chiron_20261123).
