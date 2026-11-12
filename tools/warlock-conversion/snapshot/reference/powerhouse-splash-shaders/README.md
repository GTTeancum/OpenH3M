# Powerhouse waterfall splash shader recipe

Reproduces the custom waterfall splash pixel programs from candidate 64,
visually checked in native probe 68. The stock Salvation `salvation_tower`
material supplies the compatible vertex programs and material layout. Its
pixel permutation cannot represent the custom source overlay, so the custom
pixel programs retain six texture slots, named constants and five animation
functions with native additive blending.

The source hashes, compiler identity and H3/Xenos compatibility patch are
shared with `../powerhouse-water-shaders`. The pinned upstream source is
[HaloShaderGenerator revision 5af3671c919e93b802dd6aa0899f6725de70992c](https://github.com/Beatthezombie/HaloShaderGenerator/tree/5af3671c919e93b802dd6aa0899f6725de70992c).
Upstream authorship and notices remain unchanged. This recipe records this
project's Xbox 360 adaptation; generated shader binaries stay private under
`work/`.

Run `tools/warlock-conversion/snapshot/tools/build_powerhouse_water_shaders.py --kind splash`
from the repository root. `build-powerhouse.ps1` invokes it automatically,
unless `OPENH3M_POWERHOUSE_SPLASH_SHADER_DIR` explicitly selects experimental
inputs. The splash wrapper intentionally omits the water-specific
`H3_MATERIAL_TEXTURE_FLOAT` define. Every generated GPU program hash and
integrated parameter binding must match the reviewed recipe. The cache
fingerprint includes the builder, shared inputs and selected recipe.

Native evidence: `work/powerhouse/splash-native-evidence-68.json` and
`splash-visible-rays-68.json`. These verify a visible animated spray patch;
they do not certify overall map lighting or completion of the conversion.
