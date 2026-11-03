# Sky Bridge authored window adapter

Sky Bridge from Halo Online, converted upstream by GeneralHeed / Priception in
Halo Online Map Pack For Halo 3:
https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190 .
Original individual creator unspecified. This project supplies the Xbox 360 /
OpenH3M adaptation.

Source sbr_window_01 (rmsh 12142) uses default albedo, no bump or specular mask,
Cook-Torrance material lighting, dynamic environment reflections, and alpha blend.
It has no animation functions. Its material texture switch and order3 area
specular switch are enabled; no_dynamic_lights is disabled. Candidate 28 still
mapped it to opaque generic metal with an unrelated Voi panel bump texture.

The stock-map search found no exact ten-option template. Twenty-seven nearby
stock templates use additional bump/specular-mask options. Armory's
_0_2_0_1_1_2_0_3_0_0 supplies the native twelve-entry transparent interface;
custom Xenos pixel programs remove the unwanted bump/specular-mask operations
while retaining source albedo, material texture, lighting, reflection and blend.
The default detail texture is reused from stock H3. Custom window base/material
textures are imported from source; no original disc files are modified.

Compile, reflect, and plan with the three Python scripts here, run from the
repository root with installed Python 3.12 -B and repository TEMP/TMP. Outputs
stay in work/sky-bridge/window-native-01. All twelve interface input declarations
and checked fixed registers pass; named routing has no unresolved values and
passes shared/lightmap register protections. These are structural checks only.

The compiled material switch is a real constant in some programs and a boolean
in dynamic-light programs. Keep the source boolean list and add an explicit real
constant with the same enabled value; do not discard either form.

The separately scoped sky_bridge_window.py binder is enabled through
OPENH3M_SKY_WINDOW_SHADER_DIR. importer-integration.patch captures only this task's
edits to the already dirty importer. A fresh candidate-29 build retains the
candidate-28 screen/diffuse corrections. No installed files or releases change.
Runtime visuals, console acceptance and performance remain unverified.

Candidate 29 completed successfully. Binary verification confirms exact source
window float constants and booleans, sampler controls, texture transform indices,
alpha blending and all twelve program route tables. The full 345-entry BSP audit
finds zero unintended bump-map substitutions. Candidate-28 screen regression
checks still pass (three functions, 24 exact named/staged consumers). Body XOR
and salted header SHA1 both pass. These checks do not prove visible correctness.
