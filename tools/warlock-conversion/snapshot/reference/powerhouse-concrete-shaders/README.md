# Powerhouse exterior concrete shaders

Uses the pinned HaloShaderGenerator source and Xenos compatibility patch in the neighboring `powerhouse-water-shaders` reference. Source concrete uses detail blend, texture specular mask, two-lobe Phong and a static cube. The white unit-strength normal mask is reduced to equivalent unmasked detail.

Native Zanzibar template `_1_2_0_2_2_0_0_0_0_0` supplies the vertex programs and draw interfaces. Clone its pixel programs and routes, adding the static cube sampler and source normal strength, environment tint and environment contribution. Retain all authored constants. Do not define `maybe_calc_albedo` for this opaque material: it enables a transparent-only branch through `#ifdef`.

Thirteen pixel entries compile; twelve are used by the native template. The route plan and interface audit cover those twelve. Candidate 95 passed the focused native walkway check: all three captures were individually inspected, concrete detail remained visible beside the walkway and across the water, and a short walk completed. Native hash checks passed 11/11. This does not establish full-map traversal or console validation. This directory stores recipes and audit metadata, not game assets or compiled binaries.
