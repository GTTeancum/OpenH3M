# Sky Bridge screen shader investigation — 2026-11-03

Sky Bridge from Halo Online; upstream Halo 3 conversion by GeneralHeed /
Priception in Halo Online Map Pack For Halo 3:
https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190 .
Original individual creator unspecified. This project supplies the Xbox 360 /
OpenH3M adaptation.

Text-only takeover created the full active goal. No game launch, image import,
desktop input, runtime rebuild, deployment or package replacement occurred.

The source screen_lines shader has three animation functions and 24 consumers:
base_map UV, self_illum_map UV, and self_illum_intensity. Every consumer resolves
to exactly one source template route and one experimental target route, retaining
its function and flags. primary_change_color_blend is zero and has no animation
consumer; the compiler now checks this specific fact before specialization.
The existing material_animation conversion must still run during integration.

Initial compiled material routes collided with native rounded lightmap upload
blocks at c208/c209 (and shared blocks elsewhere). Applying the existing
reserve_shared_source protection before compilation removes these collisions.
Thirteen Xbox 360 pixel programs compile; the donor uses twelve. All twelve
have matching native input declarations and checked fixed registers, no unresolved
named routes, and pass both lightmap/shared float upload safety checks.

Reproduce from repository root with the installed Python 3.12 and -B:
1. Run build-screen-native.py from this directory.
2. Run plan-screen-native.py from this directory.
Both use repository work/sky-bridge/screen-native-01 for generated outputs.
The evidence snapshot contains text metadata only, not assets or shader binaries.

These are shader interface checks, not proof that the user's panels are fixed.
Next: implement a separately guarded twelve-entry screen profile, bind source
textures/constants and preserve animations through material_animation.py; build
a fresh candidate without overwriting candidate 27. Continue deeper performance
analysis with the game closed. Later runtime timing and human visual verification
remain required before updating the LIVE package. Goal remains open.

## Candidate 28 integration

A separately guarded twelve-entry screen binder is now wired into the importer
via OPENH3M_SKY_SCREEN_SHADER_DIR. The narrow importer patch is recorded here;
the preexisting dirty importer is deliberately not staged as a whole.
Candidate 28 built successfully to work/sky-bridge/zanzibar-28.map with report
work/sky-bridge/build-28.json and log work/sky-bridge/build-feedback-28.log.
Candidate 27, installed payloads and LIVE releases remain unchanged.
The prior diffuse-only fix needed variants=[0]*10; its snapshot now includes it.

verify-candidate.py reads the emitted binary. It verifies three function payloads
with endian conversion, all 24 named/staged animation consumers and flags,
exact source float constants and sampler controls, additive blending, and reuse
of stock default_detail (bitmap 19). The source screen bitmap is imported once
and bound to both base and self-illumination slots (bitmap 9733).
These checks passed. No game launch, visual verification or new timing run occurred.

Performance source inspection confirms the synchronous occlusion end path waits
on its submission fence; the existing asynchronous path still ends a submission
for each query. Existing timing remains insufficient to accept either as a fix.
Further diagnosis must preserve actual visibility results and native semantics.
