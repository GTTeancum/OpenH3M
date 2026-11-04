# Sky Bridge puddle shader preparation

Source: Sky Bridge from Halo Online, upstream Halo 3 conversion GeneralHeed / Priception, [Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190). Original individual creator unknown. This is the Xbox 360/OpenH3M adaptation.

Source material 12294 uses default albedo, masked detail bump, diffuse specular mask, Cook-Torrance, dynamic environment and alpha blending. Native Armory template 9401 differs only in bump method. The stock inventory contains no exact profile. Thirteen Xbox 360 pixel programs compile; twelve donor entries have matching input declarations and checked fixed registers, with no unresolved routes and passing shared-register reservation guards.

Prepared only: not integrated in candidate 31. Its four source animation functions must be audited and preserved by the binder. Native use_material_texture must be derived from the source boolean. Added bump-detail-mask texture must be copied from source with its sampler controls and transform. Next: integration alongside four remaining window materials, emitted-cache checks, then runtime and human visual verification. No visual or performance claim.
