Sky Bridge unlit premultiplied soft smoke

Source variant _5_10_0_0_0_1_0_1_0_0 has no exact original-disc donor. Compile its original options to Xbox 360, retaining sprite alpha, palette, fog, depth fade and dual LDR/HDR exports. Base/alpha transforms are identity because neither source nor native parameter tables contain these added shader-source parameters. No SSR output exists in native Halo 3. Explicit depth_fade_range c100 matches native routing. All nine reflected parameters match the native donor and all five pixel input declarations match.

Use the per-pixel-lighting native donor _5_10_0_1_0_1_1_1_0_0 vertex graph; its vertex stage does not apply per-vertex lighting. The replacement pixel program retains source lighting=none and black_point=off. The extra normal input is unused. Material root options and flags are preserved. The source variant is scoped to s3d_sky_bridgenew.map. Build20 started before final donor selection; it is not a release candidate. Native runtime appearance untested.

Source: Sky Bridge, Halo Online; General Heed / Priception, Halo Online Map Pack For Halo 3: https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190. This project supplies Xbox 360/OpenH3M adaptation.

Build20 passed the unlit-smoke importer and reached soft_smoke_large_n2. Its _5_10_0_2_0_1_0_1_0_0 variant reuses native _5_10_0_2_0_1_1_1_0_0 only after the existing verifier proves every source emitter black point is zero. This preserves native per-vertex lighting. Build21 uses both conversions and the corrected unlit donor.
