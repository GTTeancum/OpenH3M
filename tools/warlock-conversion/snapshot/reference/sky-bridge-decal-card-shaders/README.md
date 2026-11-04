# Sky Bridge decal-card shader preparation

Source: Sky Bridge from Halo Online, upstream Halo 3 conversion by GeneralHeed / Priception in [Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190). Original individual map creator is not established. This work is the Xbox 360/OpenH3M adaptation.

The four source materials 12453, 12458, 12579 and 12591 use default albedo, no bump, simple alpha testing, texture specular mask, Cook-Torrance, dynamic environment and double-multiply blending. Candidate 29 instead uses an opaque fallback. They cover 14 BSP parts; assignment to individual user screenshots is not yet established.

The stock inventory checked 25 tag-readable disc maps and recorded the separate shared.map resource-cache parse limitation. No exact ten-category native template exists. Armory template 375 provides the native program layout; the adapted shader preserves the source profile. Thirteen Xbox 360 pixel programs compile, of which twelve correspond to the donor's entry set. All twelve input declarations and checked fixed registers match. All material/extern parameter routes resolve, with shared albedo boolean b0 independently proved against native Armory template 9401. Register-reservation guards pass.

The native Cook-Torrance implementation needs the additional use_material_texture float; the future binder must set it consistently with the source boolean as the prior window binder does. Do not drop the source alpha-test map or overwrite source sampler controls. All four source materials have no animation functions.

Status: integrated in candidate 31. Four material verifications pass for all source float constants, source booleans, derived Cook-Torrance switch, sampler controls, non-null texture bindings and all 12 program route tables. All 48 emitted shader payloads, reflection tables and register counts match compiler output. All 485 meshes / 2,116 part records match source. Five materials (four windows and one puddle, 18 parts) still lose their source blend mode and need correction. The two additive water-card corrections remain included.

Candidate: work/sky-bridge/zanzibar-31.map, SHA256 cef37c5ec3ca18c2528994f7a50f1b06bc418068f152222f9b9905ee92588150. Shared installation unchanged. No runtime/visual acceptance or performance claim for this candidate.
