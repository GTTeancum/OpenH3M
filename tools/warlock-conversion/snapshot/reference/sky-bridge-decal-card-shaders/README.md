# Sky Bridge decal-card shader preparation

Source: Sky Bridge from Halo Online, upstream Halo 3 conversion by GeneralHeed / Priception in [Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190). Original individual map creator is not established. This work is the Xbox 360/OpenH3M adaptation.

The four source materials 12453, 12458, 12579 and 12591 use default albedo, no bump, simple alpha testing, texture specular mask, Cook-Torrance, dynamic environment and double-multiply blending. Candidate 29 instead uses an opaque fallback. They cover 14 BSP parts; assignment to individual user screenshots is not yet established.

The stock inventory checked 25 tag-readable disc maps and recorded the separate shared.map resource-cache parse limitation. No exact ten-category native template exists. Armory template 375 provides the native program layout; the adapted shader preserves the source profile. Thirteen Xbox 360 pixel programs compile, of which twelve correspond to the donor's entry set. All twelve input declarations and checked fixed registers match. All material/extern parameter routes resolve, with shared albedo boolean b0 independently proved against native Armory template 9401. Register-reservation guards pass.

The native Cook-Torrance implementation needs the additional use_material_texture float; the future binder must set it consistently with the source boolean as the prior window binder does. Do not drop the source alpha-test map or overwrite source sampler controls. All four source materials have no animation functions.

Status: prepared and interface-checked only. No importer integration, emitted-cache validation, runtime validation or visual acceptance yet. Candidate 30 remains the latest generated map; shared installation is unchanged. Next: integrate this scoped profile, then the remaining puddle/window profiles; build candidate 31 and verify source constants, textures, blend/alpha settings and emitted programs. Window distortion option requires further source-entry investigation; do not discard it based on its name.
