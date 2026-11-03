# Sky Bridge lamp shader build

Experimental Xbox 360 pixel programs for the three static opaque multilayer
lamps in s3d_sky_bridgenew.map. These are compiled and interface-checked but
are integrated into the converter but are not yet verified in the game.

Source package: Halo Online Map Pack For Halo 3,
https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190.
Exact original-map and upstream conversion authorship remains unverified here;
this work is the Xbox 360/OpenH3M shader adaptation, not upstream authorship.
Shader equations come from the local pinned HaloShaderGenerator source cache.
Input hashes identify the existing local compatibility source used by this build.
No game binaries are committed.

Run from the repository using the installed Python with -B:

1. tools/warlock-conversion/snapshot/tools/build_sky_bridge_lamp_shaders.py
2. tools/warlock-conversion/snapshot/reference/sky-bridge-lamp-shaders/plan-routes.py
3. tools/warlock-conversion/snapshot/reference/sky-bridge-lamp-shaders/audit-interface.py

All ten donor entries compile. Their declared inputs match the native Sandbox
_2_8_0_0_0_1_0 template, and checked fixed registers match. Named routes resolve
with added base_map/detail_map parameters for the albedo pass. Shared float
upload blocks are reserved and route collision checks pass. The multiply
overlay replaces the donor's additive overlay in generated pixel code.

The loop is specialized to the authored four groups of four samples. The build
rejects the existing source audit if any of the three lamps has animation or a
different layer count. Integration must repeat that guard against the actual
source material and retain all authored depth, contrast, texture transforms,
colors, intensity and opaque blend mode. The fluorescent layers retain their
nonzero view-dependent depth. Remaining compiler warnings describe unused
input semantics; the potential-infinite-loop warning is gone.

Integration is in sky_bridge_lamp.py and terrain-integration.patch. The patch
records only this change to the preexisting untracked terrain converter. It
clones the donor template and pixel tags, adds the base/detail parameters, and
preserves source values and texture routing. Guards check the actual source
material names, animation count and four-group layer count at conversion time.

The complete-map build bound the first lamp template successfully, then stopped
on fx_lightvolume_building_bridge_rb with nondefault MCC hologram categories.
It has not reached all three lamps or produced a complete cache yet.
Category 7 is distortion; category 8 is soft fade. The source parameter report
mcc-extra-options.json shows active Fresnel/depth fades on sky and light effects,
so silently stripping these options would change the authored rendering.
The playable cache and final LIVE package remain outstanding.
