# Sky Bridge soft-fade conversion

Source: Halo Online Map Pack For Halo 3, s3d_sky_bridgenew.map,
https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190.
Exact original-map and upstream conversion authorship remains unverified here.
These files implement this project's Xbox 360/OpenH3M adaptation.

The converter now passes fx_lightvolume_building_bridge_rb, including its
animation routes. It next stops at _0_1_0_0_0_1_0, used by holo_lighting_door
and cabin_lamp_red_base. No playable cache or LIVE package exists yet. The
user requested one consolidated launch test after the build, not a sequence
of isolated gameplay checks. No native launch has been performed.

This profile compiles ten pixel programs and nine vertex programs (world,
rigid, skinned; dynamic light, cinematic light, vertex color). Native shared
vertex constants retain their original registers. Only this material's rmdf
and glvs are cloned; the stock donor and other materials stay unchanged.
The added depth input is TEXCOORD0.z and two projection coefficients travel
through TEXCOORD7. All other native input semantics are retained.

Depth is reconstructed from the actual native View_Projection matrix:
projected_z = a + b / clip_w; clip_w = b / (sampled_z - a).
This avoids importing MCC's fixed reverse-depth projection constants.
The depth sampler has external texture binding 3, separate from the fixed
normal sampler. Parameter routes retain source soft-fade booleans, Fresnel
power, depth range, additive overlay, illumination and edge fade.

The source DXBC inspection shows soft fade is unused in the static passes
but used by dynamic and vertex-color passes. Two other source materials have
all extra options compiled out; all remaining ones must retain their active
fade passes. The source-options report contains compiled program hashes and
used/unused parameter declarations, not game shader binaries.

The compiler uses the existing protected lamp source directory as its starting
point. Its deform adaptation excludes the additional Halo Online squish and
binormal correction absent from the native donor. Vertex constant reflection
is checked against the corresponding native programs before injection.
Projection reconstruction passes 72 arithmetic cases, covering standard and
reverse depth, three camera translations and three near/far ranges. This
is not in-game verification. The depth/viewport path still needs the requested
consolidated launch check.

Scripts run from the repository with installed Python -B; generated data goes
to work/sky-bridge/soft-native-01. compile.py rebuilds programs. The reflection,
route and interface scripts generate their respective work reports. The stored
compilation manifest, normalized interface audit and vertex plan correspond
to the current compiled bytes and are checked again by sky_bridge_soft.py.
terrain-integration.patch isolates edits to the preexisting untracked converter.
