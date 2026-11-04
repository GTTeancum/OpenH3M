# Battle Canyon glass: stock H3 proposal

Status: user approved this approach on 2026-11-04. Blender channel preparation
and native H3 bitmap import passed. All three shader/UV assignments passed
native verification. MCC appearance review remains pending.

Keep the original Reach artwork, repack its existing transparency channel with
Blender's standard compositor, and use stock H3 shaders. Use stock H3 glass
behavior for the exterior's view-angle effect. No painted replacement,
custom shader code, engine change or new converter is proposed.

## Why a decision is needed

The exterior, bridge and tunnel glass use separate Reach transparency and
specular masks. Original H3 alpha blending reads the base texture's alpha;
the Reach base alpha already holds the specular mask. Directly binding these
unchanged textures would use the wrong transparency.

Native source extraction confirms the opacity image is not equivalent to the
base alpha: its RGB values span 75–183, while the base alpha spans 13–237.
Both images are 512x512. The base RGB is uniform (12,12,12); opacity uses
2x UV scale, while the existing specular mask uses 1x scale.

The exterior also enables view-angle opacity (coefficient 1, steepness 3).
Bridge and tunnel set that coefficient to zero. A static channel rearrangement
cannot preserve the exterior's angle-dependent operation by itself.

## Proposed native-tool preparation

1. Preserve both original Reach images and tags. Create a separate working
   image using Blender compositor Separate/Combine Color nodes: original
   base RGB, existing opacity grayscale into alpha. Check color-space handling
   against native Reach exports; do not assume encoded RGB equals linear alpha.
2. For bridge and tunnel, use stock Foundry
   `levels/dlc/warehouse/shaders/ware_glass_overhead_a.shader`. Its original
   360 options support a separate specular-mask texture, per-pixel reflections,
   standard normals, Cook–Torrance and alpha blending. Bind the unchanged Reach
   base image as the separate specular mask, using its original alpha and 1x
   scale. Bind the packed color/opacity image at the source opacity's 2x scale;
   the original constant RGB does not introduce a new color pattern.
3. For exterior glass, use stock Cold Storage
   `levels/dlc/chillout/shaders/chillout_glass_panel.shader`, retaining Reach
   texture inputs and using H3's native glass/Fresnel behavior. This is an H3
   alternative, not a claim that Reach's exterior opacity is reproduced exactly.
4. Import through official H3 Tool. Check saved channels, texture scaling,
   normal inputs and cubemap references. Inspect all three surfaces from both
   sides and several angles during the user's MCC walkthrough. Approval of
   this preparation does not approve the MCC map or authorize 360 conversion.

Original-360 donor vectors and unchanged cache hashes are recorded in
`work/stock-h3-audit/glass-proposal-stock-evidence.json`. The original images
and hashes are in `extra-reach-bitmap-extractions.json`; source functions are
in `pending-material-input-review.json`.

The official H3 native option help explicitly says `specular_mask_texture`
uses the specified bitmap's **alpha** channel (`glass-specular-mask-native-option.xml`).
This agrees with the inspected community source. The web specular-mask page
instead mentions material-texture red; that discrepancy must not cause an
incorrect channel assignment. Native rendered testing remains required.

References: [H3 alpha blending](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/shaders/blendmode),
[H3 glass material model](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/shaders/materialmodel).

User decision (2026-11-04): "Approve this glass approach." The approval covers
this source-channel repacking and stock H3 exterior glass alternative; it does
not approve the MCC map or authorize Xbox 360 conversion.

## Preparation evidence (2026-11-04)

`prepare_glass_channels.py` uses native Blender Separate/Combine Color and
Alpha Convert nodes. Both source bitmaps have native curve 3 (linear), so the
images use Non-Color inputs and Raw output without a gamma transform. Alpha
matches every original opacity pixel exactly. RGB differs by at most 1/255
following Blender's straight/premultiplied conversion and 8-bit output. The
original base alpha is preserved in the unchanged original image for the
separate H3 specular input; no original asset was edited.

`import_glass_channels.py` imports the working image with official H3 Tool as
linear a8y8, 512x512, retaining nine mip levels. All exported native RGBA pixels
match the prepared image exactly. Tool's a8y8 direct-save export fallback was
checked by inspecting the actual output, not accepted from its exit code.

The reproducible compositor scene, images, source hashes, import fields and
pixel comparisons are under `work/stock-h3-audit/glass-channel-preparation/`.
The working texture is assigned to all three glass surfaces. Use
`import_glass_channels.py --verify-only` for subsequent read-only pixel checks.

## Native material assignment (2026-11-04)

The two interior surfaces now use the Foundry donor, and the exterior uses the
Cold Storage donor. All seven family image records passed native pixel/mip
checks; the packed color/opacity image remains separately verified.

`inspect_glass_sources.py` reads the actual Reach tags through unmodified
Foundry/ManagedBlam. `verify_glass_materials.py` compares saved H3 references
and functions against those native source controls: packed base/opacity stays
at 2x, original base alpha as the separate specular mask stays at 1x, and normal
and cubemap inputs/functions remain unchanged. Each source tag hash is checked.

The exterior preserves all three stock Cold Storage Fresnel controls, including
its authored steepness 15. The generic default comparison must not remove that
stock override just because the Reach Cook-Torrance option has an identically
named parameter with default 5. The native verification compares these controls
to the donor directly. No replacement Fresnel function was created.

Evidence: `glass-native-source-controls.json`, `glass-native-bindings.json`,
`glass-material-verification.json`, `glass_interior-family/` and
`glass_exterior-family/` beneath `work/stock-h3-audit`. Transparency sorting,
reflection strength, both-sided viewing and visual similarity still require MCC.
