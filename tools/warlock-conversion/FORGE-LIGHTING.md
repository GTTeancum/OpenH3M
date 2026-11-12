# Forge vehicle occlusion and Coliseum materials

## Causes established on 2026-10-22

The Hornet's seven lens-flare tags retain the original Shrine donor's occlusion
flags, distances and radii. The problem is in the host GPU query implementation,
not a map-side no-occlusion flag. Native diagnostic run
`20261022-222845-37836` recorded BEGIN address `1FC01020` and END address
`1FC01000`. The renderer incorrectly required these addresses to be equal,
disabled real queries and used the fixed visible-sample fallback. The SDK's own
`xe_gpu_depth_sample_counts` definition specifies separate snapshots whose counts
are subtracted by guest D3D.

`halo3mp/patches/rexglue-sdk-occlusion-query-snapshots.patch` accepts the distinct
END destination and writes a zero BEGIN baseline because host D3D12 queries
already produce interval counts. It logs the first hidden and first visible
result. Original vehicle effects, guest code and gameplay/network behavior are
unchanged. Apply this patch to the existing patched SDK and incrementally build
`rexgpu-xenos`; deploy only that DLL after native validation.

The Coliseum's source materials had fallen through to the generic opaque
prototype, dropping reflection, two-lobe lighting and self-illumination settings.
An original-disc inventory found exact native templates for eight architecture
materials, including wall, hall, base, panel and pipe. Two trim materials use
Cyberdyne's native single-bump/self-illumination combination, preserving emission
but omitting their secondary bump layer. The source glass material is unchanged.
Evidence: `work/forge-world/sanctuary-material-oracle.json` and
`sanctuary-near-shader-oracle.json`.

Visual reference: Bungie's original [Coliseum gameplay screenshot](https://www.halopedia.org/File:HR_ForgeWorld_Coliseum.jpg),
credited to its Incompetent Cartographer article. It shows illuminated vertical
wall panels and a bright floor edge. This is the Reach room itself, not a Forge
remake or Infinite recreation.

## Repeatable map patch

Run `snapshot/tools/patch_forge_architecture.py` from the repository root, with
TEMP/TMP under `.local/build-temp`. Supply `--map forge_gulch` or `forge_island`,
`--basis` pointing to the accepted DLC map, `--source` pointing to the identified
non-AI MCC Forge World cache, `--disc C:/X360/ISOs/H3M/maps`,
`--xex C:/X360/ISOs/H3M/default.xex`, and fresh repository-local `--output` and
`--report` paths. The tool pins the accepted basis hashes and preserves material
datums while appending native shader dependencies. It uses the same material
adapter as full future conversions. It does not repartition terrain or move the
production spawn.

Both patched maps preserve their scenario, BSP and lightmap roots and every
vehicle/lens root byte-for-byte (1 scenario, 2 BSPs, 1 lightmap, 24 vehicles and
58 lens tags per map). See `work/forge-world/architecture-preservation.json`.
Island is 136,687,616 bytes; Gulch is 175,185,920 bytes. The architecture update
adds approximately 7.7 MiB per cache. Existing unrelated maps and previews are
hardlinked into staging, avoiding new copies.

## Verification record

- Six focused lighting/normal/budget tests passed; SDK patch reverse-application
  check and incremental GPU build passed.
- `20261022-223439-25252`: real zero-sample occlusion results; perimeter lights
  visibly restored. The flight route reached the entrance roof, so this was not
  an adequate interior view. Its late second capture missed the watchdog.
- `20261022-224037-7532`: temporary diagnostic spawn at (65, 220, 45), facing the
  entrance. Native capture inspected; perimeter glow, floor, doorway and outdoor
  scene visible. Eleven resource hashes passed. Production spawn is unchanged.
- Console and system-link validation remain outside this host-only rendering
  check; no console memory limit is raised.
