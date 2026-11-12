# Map-fix proofs — 2026-11-11

These are native OpenH3M captures and measurements, not Xbox 360 hardware results. The main LIVE container was refreshed for the installed conveyor and Powerhouse corrections on 2026-11-11; all 77 payload files match the installed files byte-for-byte. Sky Bridge is unchanged. Console loading/performance and system-link testing are not claimed.

## 3longation — corrected, installed and packaged

Both conveyor directions passed their stationary-player transport check: each recorded 79 observer samples with zero near-zero one-second movement intervals; the original red-belt baseline had 13. Red moved X -0.456 to -7.201, blue +0.544 to +7.273, with stable lane and height. All six native captures were inspected individually. A first blue attempt remained in the lobby and was rejected; the retry entered gameplay. The tested candidate was installed on 2026-11-11 with original DLC identity and thumbnails. The identity rewrap changes only 58 header/scenario bytes. Installed SHA-256: `69937d555d172538b62d242527e23a4206fd0f622226fcd47e60d0069c27802c`. Deployment evidence: `work/map-review-20261105/elongation-deployment.json`. The refreshed main LIVE bundle includes this correction and passed full payload/hash-tree verification.

Installed correction: remove the flat/eased opening of the conveyor animation while retaining its endpoints, node paths, duration, scripts, collision and simulation timing.

## Chiron TL-34 — ladder transparency

The ladder now shows the wall through the gaps between rungs instead of opaque black cards. Source ladder artwork is retained; the shader uses native H3 transparency. The pictured native position was valid. Climbing and the full teleporter network were not rerun.

![Chiron: wall visible between ladder rungs](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/map-benchmarks/chiron-ladder-review/spawn-2.png)

## Powerhouse — 18.46% polygon reduction installed

The installed map now has **488,906 triangles**, down from599,560: **110,654 fewer triangles (18.4559%)**. It retains the original vertex positions, normals, UVs and lightmap data. Independent verification found collision byte-identical and no changes to lights, exposure, materials, placements or visibility trees. Only opaque index ranges and their resource descriptors changed.

All three native spawn captures below were inspected individually. No obvious new missing surfaces or gross material defects were observed in these fixed views. This is not a full traversal or silhouette-equivalence test; reduced topology can change interpolation. The deployed DLC identity differs from the tested candidate only in58header/scenario identity bytes. Thumbnail and map metadata are unchanged.

User steering2026-11-11: prioritize known reductions over clean performance baselines while other workloads remain active. The baseline comparison was stopped. **The reduction is verified; an FPS gain and the35FPS target are not claimed.** The loaded trial measured15.946 /25.338 /14.519FPS; Racer Revenge had restarted between earlier comparisons, so these are not an isolated before/after result.

[Preservation audit](C:/X360/ISOs/H3M/.local/OpenH3M-source/work/map-review-20261105/powerhouse-reduction-preservation.json) · [Deployment record](C:/X360/ISOs/H3M/.local/OpenH3M-source/work/map-review-20261105/powerhouse-deployment.json)

![Reduced Powerhouse: outdoor terrace](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/map-benchmarks/powerhouse-reduction-20/spawn-1.png)

![Reduced Powerhouse: outdoor approach](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/map-benchmarks/powerhouse-reduction-20/spawn-2.png)

![Reduced Powerhouse: generator room](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/map-benchmarks/powerhouse-reduction-20/spawn-3.png)

## Resuscitation — base materials

The base panel uses the matching stock H3 diffuse shader instead of an unrelated normal/specular fallback. Both bases were inspected close up at valid native positions; artwork and base geometry remain. This is targeted material evidence, not a complete traversal test.

![Resuscitation blue base close-up](C:/X360/ISOs/H3M/.local/OpenH3M-source/work/map-review-20261105/resuscitation-close-evidence/spawn-1.png)

![Resuscitation red base close-up](C:/X360/ISOs/H3M/.local/OpenH3M-source/work/map-review-20261105/resuscitation-close-evidence/spawn-2.png)

## Rodentia — original exposure and glass

Brightness tuning was removed as instructed. The installed camera values exactly match the source: minimum 2.0, maximum 4.5, target -2.514573097229004. The honeycomb floor is transparent; underlying architecture is visible in the lower part of this capture. Three native positions and five captures were reviewed.

![Rodentia: structure visible through the honeycomb glass](C:/X360/ISOs/H3M/.local/OpenH3M-source/work/map-review-20261105/rodentia-original-lighting-evidence/proof-loaded_155000ms.png)

## Sky Bridge — rain cards and flashing geometry lights

Eight rain-card draw parts (4,350 indices) and their subparts have zero draw counts. Both electrical light-creation events have zero parts; the current installed fields were reread and confirmed. This removes the specified light sources structurally; a still image alone does not prove absence of flashing. Electrical arc particles, other geometry and collision remain. Doorway/outdoor native views were inspected.

![Sky Bridge: doorway without rain-card fill](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/map-benchmarks/sky-weather-review-02/spawn-2.png)

## Preservation and packaging

Sanctuary remains byte-identical to the user-accepted version: `a217699ed82752ae59dca8582e73b0840eea5949544c4990750838687bdc394f`. Forge rotation preview and large-item spawn distance remain separate unchecked tasks.

Current installed/package identity audit (includes conveyor and Powerhouse corrections): [current-proof-audit.json](C:/X360/ISOs/H3M/.local/OpenH3M-source/work/map-review-20261105/current-proof-audit.json). Full packaged-byte comparisons and STFS hash-tree results: [LIVE manifest](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/releases/current-live/manifest.json).

Source map/package authors and conversion attribution are recorded in [map review report](C:/X360/ISOs/H3M/.local/OpenH3M-source/tools/map-review/README.md). These corrections are this project’s Xbox 360/OpenH3M adaptation.

Powerhouse correction pass accepted by the user on 2026-11-11. All six corrections closed for this pass; no claim of measured 35 FPS or Xbox 360 hardware validation.

## Powerhouse Battle Rifle follow-up — 2026-11-11

All five DMR placements now reference the stock Halo 3 Battle Rifle. Native pickup, first-person appearance, 36-to-33 three-round burst and reload to36 verified; Forge spawned an additional BR. All other map bytes except checksums are identical, preserving the accepted18.46% reduction. Installed map and77-file LIVE bundle verified. Weapon PCM captured but not listened to; timed Forge menu/drop images were unavailable. See [targeted correction evidence](POWERHOUSE-BATTLE-RIFLE.md).


## Sky Bridge Battle Rifle follow-up � 2026-11-11

All four DMR placements now use the stock Halo 3 Battle Rifle. The redundant
DMR Forge entry is removed; the existing BR entry remains. Native pickup,
first-person firing, three-round bursts, reload, Forge label and spawned held
model verified. All other bytes except checksums are identical, preserving
accepted weather/geometry corrections. Installed map and seven-file LIVE bundle
match; main bundle remains unchanged. Weapon PCM captured but not listened to;
Xbox360/system-link untested. See [targeted correction evidence](SKY-BRIDGE-BATTLE-RIFLE.md).
