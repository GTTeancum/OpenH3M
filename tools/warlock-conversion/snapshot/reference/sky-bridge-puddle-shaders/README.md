# Sky Bridge puddle shader preparation

Source: Sky Bridge from Halo Online, upstream Halo 3 conversion GeneralHeed / Priception, [Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190). Original individual creator unknown. This is the Xbox 360/OpenH3M adaptation.

Source material 12294 uses default albedo, masked detail bump, diffuse specular mask, Cook-Torrance, dynamic environment and alpha blending. Native Armory template 9401 differs only in bump method. The stock inventory contains no exact profile. Thirteen Xbox 360 pixel programs compile; twelve donor entries have matching input declarations and checked fixed registers, with no unresolved routes and passing shared-register reservation guards.

Integrated in candidate 32 through sky_bridge_alpha_card.py. Four source animation functions and 40 consumers pass emitted-cache verification. All source constants, booleans, texture sampler controls and the derived material-texture switch pass. Twelve emitted program payloads/reflection/GPR counts match. See ../sky-bridge-remaining-window-shaders/README.md for combined candidate evidence and remaining visual/runtime gates.
