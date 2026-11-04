# Battle Canyon river: stock H3 proposal

Status: user approved stock H3 water behavior on 2026-11-04. This is a
material/authoring decision, not MCC acceptance. Geometry-channel mapping and
visual review remain required.

## Proposed result

Keep the original Reach river geometry, color/shape textures, creek reflection
and wave artwork. Use Longshore's stock H3 water shader and its native response
where Reach-only controls have no H3 counterpart. The river may differ in foam,
ripples, opacity and refraction; the user reviews those differences in actual MCC.

Both wave arrays already exist in the official H3 kit with exact top-mip pixels
and matching dimensions, formats, curves and mip counts. Reuse those assets;
do not rebuild their artwork or implement a Reach shader.

For H3-only vertex inputs, use stock H3 values where supported by the original
donor and the documented Blender workflow. Preserve the original main UVs and
water UVs in the visual/global-shape channels. Do not invent a Reach-equivalent
formula for fields absent from its source. Any remaining field whose purpose
cannot be established stays unresolved, rather than being declared faithful.

## Verified limits

- Original Reach exposes two coordinate sets. H3's documented Blender workflow
  uses four; its second set controls wave displacement and water color.
- Original Longshore has 1,555 water vertices across six meshes. Their native
  `local info` is uniformly `(10, 0, 0)`. Additional native fields include
  position-dependent `water velocity` and a base-coordinate third component of
  zero or 0.5. These are evidence, not an instruction to copy every value blindly.
- The unmodified General101 ASS exporter writes texture-coordinate W as zero.
  This proposal does not authorize patching that exporter, postprocessing ASS
  to fabricate missing coordinates, or claiming an exact Longshore round trip.
- H3 already exposes detail slope scales and steepness. It does not expose the
  source's `foam_cut`, `foam_coefficient`, `slope_scaler` or
  `normal_variation_tweak` in the selected options. Its global option adds only
  engine-provided texture/address inputs, not those missing controls.
- Source foam coefficient is zero. Copying texture slots alone would not prove
  equivalent foam behavior. Under this proposal, native H3 behavior is retained
  and reviewed rather than recreated with a custom shader.

The user's approval permits this stock-H3 material direction, not arbitrary parameter
values, removal of the river, custom shader/compiler code, or any 360 conversion.
MCC testing and explicit MCC approval remain required.

## Evidence

- Official native tags: Reach `ca_bcreek_river.shader_water`; H3 Longshore
  `levels/dlc/docks/shaders/water/dock_water_2.shader_water` and `docks` BSP.
- Repository evidence: `work/stock-h3-audit/h3-docks-water-geometry.json`,
  `original-water-geometry.json`, `water-wave-asset-verification.json`,
  `h3-effective-water-options.json` and `h3-water-option-xml/water_global.render_method_option.xml`.
- [Community author's H3 Blender water workflow](https://www.reclaimers.net/h3/guides/map-making/level-creation/blender-level-modeling/blender-level-creation-additional-info/).
- Pinned unmodified General101 exporter revision
  `81e86bf98aee4607a2159ff9a22a223a1a91c9d7`, `file_ass/build_asset.py`.
