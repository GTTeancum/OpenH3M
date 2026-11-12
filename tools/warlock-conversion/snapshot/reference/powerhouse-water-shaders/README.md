# Powerhouse water shader recipe

This recipe reproduces the two custom river materials tested in Powerhouse
candidate 59. It does not replace existing stock Halo 3 assets. Native Armory
`water_puddle` supplies the compatible material layout and native vertex
programs; compiled pixel programs retain the custom source's specular-mask
mode and detail-normal strength.

The input is [HaloShaderGenerator revision
5af3671c919e93b802dd6aa0899f6725de70992c](https://github.com/Beatthezombie/HaloShaderGenerator/tree/5af3671c919e93b802dd6aa0899f6725de70992c),
cached under `work/powerhouse/shader-toolchain/reference/halo_online_shaders`.
`recipe.json` pins every input file and records the archive digest. Original
source attribution and notices remain in that cache. The compatibility patch
contains this project's H3/Xenos adaptations; upstream authorship is unchanged.

Run `tools/warlock-conversion/snapshot/tools/build_powerhouse_water_shaders.py`
from the repository root with the installed Xbox 360 XDK compiler. The normal `build-powerhouse.ps1`
invokes it automatically. Output and compiler temporary files stay in the
repository. An existing `OPENH3M_POWERHOUSE_WATER_SHADER_DIR` explicitly overrides
the default output directory for conversion experiments.

The build checks generated GPU microcode against all 13 reviewed programs and
checks reflection against the reviewed material routes. Twelve programs are
integrated per material; the native shared shadow program remains in use.
Generated binary shaders are private build artifacts, not files in this recipe.
Missing or changed inputs fail explicitly; the build must not silently return
to the earlier material fallback.

Native evidence: `work/powerhouse/water-native-evidence-59.json` and
`work/powerhouse/inlet-native-evidence-62.json`. These cover the two river
materials, not completion of Powerhouse's lighting, other effects or gameplay.
