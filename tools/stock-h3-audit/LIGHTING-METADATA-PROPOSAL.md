# Battle Canyon: native H3 baked-lighting proposal

Status: proposed, not approved. This concerns the fresh Reach-to-H3 MCC rebuild.
It does not change the MCC review gate or authorize any 360 conversion.

## Preserve

Keep the original emitting faces, sun geometry, emission colors, power, focus,
quality and attenuation where the native H3 import has matching controls.
Verify actual imported values and units before binding the scene; do not copy
Blender's display-unit getters as raw native power or distance.

The original scenario defines lightmap categories as 1, 4, 16, 64, 128, 256 and
512, with category 3 (16) as the default. H3 exposes a continuous priority
multiplier, whose default is 1. Proposed H3 priorities preserve the source ratios:

| Reach category | Source setting | H3 multiplier |
| --- | --- | --- |
| 1 | 1 | 0.0625 |
| 2 | 4 | 0.25 |
| 3 | 16 | 1 |
| 4 | 64 | 4 |
| 5 | 128 | 8 |
| 6 | 256 | 16 |
| 7 | 512 | 32 |

This is an authoring choice preserving relative priorities, not an assertion
that the two lightmappers will allocate identical texels or produce identical
lighting. The overall lightmap budget remains an H3 setting and must be reviewed
before baking and checked for the later 360 conversion.

## Use native H3 behavior for the unmatched controls

- Ten of the twelve imported emission selections use Reach's separate bounce
  ratio (nine at 0.05 and one at 0.5). The inspected H3 material-lighting schema
  has no corresponding ratio. Keep their shared emission inputs and use H3's
  normal indirect lighting. Colored light spill may change.
- One 28-face source selection uses Reach lightmap chart group 17. Let H3's
  standard importer/lightmapper pack those faces; do not fabricate an equivalent
  group or write a custom lightmap packer.
- One 2,432-face source BSP selection requests per-vertex lighting. The existing
  unmodified H3 ASS material workflow has no matching per-face control. Use H3's
  normal BSP lighting policy, retaining all geometry. This may change lightmap
  allocation and visual smoothness. Instance lighting policies remain separate.

Approval would allow those native H3 differences, followed by the user's MCC
review. It would not authorize removing lights, inventing replacement geometry,
retuning brightness to hide defects, patching the exporter/compiler, or claiming
visual fidelity from field checks. Any additional unmapped setting stays open.

## Evidence

- Original official Reach kit: `cex_beaver_creek.scenario`, its BSP and
  `scenario_structure_lighting_info`; read-only native evidence under
  `work/stock-h3-audit/original-material-lighting.json`,
  `original-lighting-scenario.xml` and `export-scene-inspection.json`.
- Official H3 kit: Longshore `docks.scenario_structure_lighting_info`, exported
  by native Tool to `work/stock-h3-audit/h3-stock-lighting-info.xml`.
- Unmodified Foundry `props/mesh.py` and `constants.py` document the source
  categories; General101 `global_ui/material_ui.py` and
  `file_ass/process_scene.py` expose/write the H3 material controls.
- [Official H3 structure lightmap budget controls](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/art/lightmap/structureresolution).

Native import/readback now passes on the upstream diagnostic scene. All six
priority values actually used by this map (0.0625, 0.25, 1, 4, 8 and 32) survive
official Tool import. Source RGB, power, quality, focus and power-per-area flags
are preserved; Tool scales attenuation distances by 0.01. For example, the
source sun's authoring cutoff 1,500 becomes 15 native H3 world units, matching
the existing Foundry distance conversion. Evidence is
`work/stock-h3-audit/lighting-workflow-verification.json` and the two native XML
exports. No map lighting has been changed by this diagnostic, and the proposal
remains pending user approval.
