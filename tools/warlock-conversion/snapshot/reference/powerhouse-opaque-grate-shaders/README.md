# Powerhouse opaque floor grate

Retains the source diffuse/detail textures, both normal layers, and authored bump_detail_coefficient=5. The original Halo 3 Bunkerworld `_0_2_0_0_0_0_0_0_0_0` template supplies native vertex programs and draw interfaces. Its native pixel programs have no independently routed MCC detail-strength parameter, so this profile replaces only the pixel programs and their parameter routes. It introduces no parallax, emission, specular or transparency.

All four source texture inputs and all source constants are exact in private candidate103. Twelve native draw interfaces match; thirteen pixel programs compile. All geometry buffers and existing flare records are unchanged from101. Native run103 shows the intended grate through a short movement; all three captures were individually inspected, and source geometry rays identify mesh21/instance61. All11 native hash checks passed. The normal wrapper now prepares this profile; full rebuild remains blocked by the separate flare-placement decision. Adjacent terrain appears black in the first two captures and remains a separate unresolved gameplay-area issue.

Source: Halo Reach Powerhouse via GeneralHeed/Priception's Halo Online to H3 MCC Workshop package3003239190. See ../../../MAP-CREDITS.md for the source link and upstream attribution; this recipe is the original-Xbox360/OpenH3M adaptation.
