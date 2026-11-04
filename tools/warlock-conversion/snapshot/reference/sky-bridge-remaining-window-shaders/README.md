# Sky Bridge remaining alpha material corrections

Source: Sky Bridge from Halo Online, upstream Halo 3 conversion by GeneralHeed / Priception in [Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190). Original individual map creator unknown. This project provides the Xbox 360/OpenH3M adaptation.

Candidate 32 integrates the five remaining mismatched materials: puddle 12294, interior colored window 12159, colored windows 12412/12416, and exterior window 12220. Their source albedo/bump/specular/Cook-Torrance/environment profiles and alpha blending are retained. The source constants (including negative authored alpha), texture lists, sampler controls, booleans and all eight animation functions / 80 animation consumers pass emitted-cache verification. The native material-texture float is derived from the corresponding source boolean. Previous two water and four decal corrections also pass regression verification, including their 150 animation consumers.

All 132 emitted program payloads, reflection tables and GPR counts for the eleven corrected materials match compiler output. All 485 meshes / 2,116 part records remain identical to source. There are now zero blend-mode mismatches among used BSP materials. This does not prove every pictured card is fixed: screenshot-to-mesh mapping, runtime visual behavior and performance are still unverified.

The stock inventory has no exact templates. Native Armory template 9401 provides the window/puddle program layout; all 12 input interfaces and checked fixed registers match. Exterior window static-SH requires sampler s16. An inventory found 49 original H3 pixel-shader references above s15, with a maximum s18; the compiler is permitted only s0–s16 for this profile. No engine limit or texture removal is involved. Runtime binding remains to be exercised.

The two distortion-on windows have no source sfx_distort entry and no distortion parameters. Keeping their compile-time option produces identical microcode to distortion-off in all 13 compiled lighting entries. Explicit float2 operands fix XDK parsing of the unused distortion body without altering the computation.

Candidate file: work/sky-bridge/zanzibar-32.map, SHA256 17e38f77784aae274466d4693bd3b759bcddc39fa81fb07ad3ab0ed317329f94. Build command: work/sky-bridge/build-feedback-32.ps1. Not deployed or visually accepted. Shared DLC deployment remains on hold during the other chat's Battle Canyon cleanup; do not restore that rejected attempt from prior inventory or backups.
