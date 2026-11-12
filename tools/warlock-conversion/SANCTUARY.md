# Sanctuary conversion

Source remake author: Neckzilla, [Sanctuary for Halo 3 MCC](https://steamcommunity.com/sharedfiles/filedetails/?id=2898920291).
Original map: Sanctuary, Halo 2. See MAP-CREDITS.md.

## 2026-11-05 material corrections

The user confirmed candidate07's water fixed in gameplay. Its waterfall and
splash corrections remain in subsequent candidates. The remaining screenshots
show opaque white Forerunner strips and excessive white rock highlights.

Candidate09 restores the renamed `decor_strip_long_a` to the complete stock
Sandbox material, including its multiply blending and native dependencies.
The three dry rough-rock materials and outer-cliff terrain use exact stock H3
shader permutations, preserving source textures, detail normals and constants.
The user approved closest native H3 shading without parallax for four other
materials: `rock_rough_regular_wet`, `outer_cliff_face`, `sanc_cliff_wall`, and
`wet_cliff`. These use the native `_1_2_0_1_7_0_0_0_0_0` shader from armory,
retaining base/detail artwork and normals. Wet-material Fresnel behavior changes;
height textures and parallax controls are omitted. No global lighting change.

Evidence: `work/sanctuary/stock-glyph-rock-audit.json`,
`stock-rock-templates.json`, `build-09.json`, and `deployment-09.json`.
Candidate09 visually accepted by the user on 2026-11-05: "Excellent work. It's perfect now". This closes the reported water, glyph-strip and white rock-highlight
issues. Acceptance is based on the user's gameplay review, not build checks.

Correction candidate 02 (2026-10-25) restores native emissive shaders and adds
+0.65 EV to this map's camera target/bounds. Native run
`20261025-180638-33988` completed its 145-second watchdog. Both 115/130-second
captures inspected: courtyard architecture, sky, vegetation and lit trim render;
the later view is close to a shadowed wall, not broad traversal coverage.
Timing median 33.37 ms, p95 33.76 ms, maximum 50.29 ms; no >100 ms stalls,
capture intervals excluded. Candidate remains undeployed.

Source: installed Halo 3 MCC Workshop 2898920291, maps/sancr.map.
Candidate 01 assembled over the original zanzibar cache; intended independent
DLC identity sanctuary, map ID 1742. Installed after bounded native gameplay, Forge overview and menu/preview checks.

Build uses build_scenario_checkpoint.py with original zanzibar/default.xex,
the installed MCC Halo 3 sfx.fsb and the established vgmstream decoder. Source
does not include a shared-cache or sound-bank override. Output and audit data
are under work/sanctuary. Candidate is 227,819,520 bytes, with 7,681,892 metadata
bytes, 512 collision trees and 319 runtime decals validated. File size does not
certify console runtime memory.

The pond's water options are `_0_1_1_1_2_0_0_0`: textured water, static reflection,
dynamic refraction, painted bank opacity, no global shape and no foam. No exact
shader exists on the disc. Longshore's `_0_1_1_1_2_0_1_3` supplies the same leading
options with painted shape and both foam modes. A private constant RGB (1,1,0)
mask retains unit height/choppiness and zero painted foam. The auto-foam threshold
is set above the authored wave range. Authored water textures, reflection and
animations are retained through the existing adapter. This is a shader mapping,
not a shader/engine patch. Source/donor options and values are recorded in
water-options.json and water-values.json; shader-reference.txt pins the inspected
reference implementation used to check mask semantics. Native pond and surrounding terrain appearance were inspected in the Forge overview.

Campaign waterfall rolling mist and spray reuse their original-disc Valhalla
equivalents and dependencies, per stock H3 policy. The decal importer skips one
unassigned editor placement (index -1), but still rejects invalid runtime indices.
The moss decal uses the existing validated alpha-mask bake with an otherwise
matching native shader option set; bump and tint choices are unchanged.

Proof: `.local/loading-traces/20261025-054900-38764` (gameplay) and
`.local/loading-traces/20261025-055415-21056` (menu/Forge overview); both
finished at the watchdog with 11/11 executable hashes passing. Promotion
`work/sanctuary/promotion-01.json` verified all 63 package files. Water animation,
audio, exhaustive traversal, console memory and system link were not verified.
