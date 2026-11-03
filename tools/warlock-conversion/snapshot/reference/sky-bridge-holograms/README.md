# Sky Bridge hologram integration

Source: Halo Online Map Pack For Halo 3, s3d_sky_bridgenew.map,
https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190.
Original game lineage and exact upstream conversion authorship remain
unverified here. This is this project's Xbox 360/OpenH3M adaptation.

The geometry stage now completes. The next failure is in object dependencies:
prt3 fx\particles\flare\light_beam_flat_01 needs particle template
_0_8_0_0_1_0_0_0_0_0. The cache has not finished building and no native launch
has occurred. The user's one consolidated launch test remains pending.

build_sky_bridge_holograms.py compiles source-specific profiles with the
installed Xbox 360 XDK. sky_bridge_hologram.py clones native shader metadata
and installs the compiled programs with the complete original parameter order,
texture bindings, animation routing, and original postprocess blend state.
Existing exact stock templates remain on their native path. New profiles use
Sandbox's native halogram graph and checked entry interfaces. Soft profiles
reuse the isolated depth-carrying vertex work from sky-bridge-soft-shaders.

The opaque door and cabin lamp, source sky shaders, additive and multiply
illumination overlays, tutorial-device glow, and layered banners are covered.
The layered shader loops specialize to their authored two or four groups;
build and import guards reject animated or changed layer counts. Other source
animation functions remain live. Scale-X/Y/uniform animation kinds use the
existing native enum and full tag-function converter. Source sampler animation
ranges are carried over along with register/function remapping.

Generated profiles, binaries, assembly and diagnostics remain under
work/sky-bridge/holograms-01. The tracked profiles.json records their source
parameters, material names, shader hashes and interface outcomes. Original
shader math comes from the existing pinned HaloShaderGenerator source cache.
The builder reuses the protected lamp and soft-fade source directories.
No game binaries are committed.

Sky Bridge instance bit 6 is preserved verbatim, without changing bit 5 or any
other field. The supplied schemas disagree about its label, and no scanned
original-disc instance sets it; native rendering behavior is unverified. This
is data preservation, not a claim that its semantics have been established.

Design MOPP keys address soft-ceiling/water records, not BSP collision shape
keys. Stock Cyberdyne already uses 0x10000, which the old generic collision
remapper rejected. The design path now validates instruction bounds but keeps
keys unchanged. Thirty original/source design programs remain byte-identical;
ordinary BSP shape-key remapping and its invalid-key guard still behave as
before. No collision geometry was simplified or rebuilt by this change.

Patch files isolate changes to preexisting dirty converter files. The latest
build-result.json records the completed geometry stage and next object error.
