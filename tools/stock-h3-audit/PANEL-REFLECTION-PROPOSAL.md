# Battle Canyon: three panel reflection choices

Status: user approved stock H3 reflections on 2026-11-04. All three native
materials are assigned and their input/pixel checks passed. Local cluster
cubemap generation and MCC appearance review remain pending.

Keep the Reach panel artwork, normal/detail textures and circular-panel glow.
Use stock H3 shaders whose reflection source comes from H3 Tool's local map
cubemaps, replacing these panels' fixed Reach reflection texture
`d_cubemap_vertical_noise`. Their reflected appearance will change and must be
reviewed in MCC.

| Reach surface | Proposed stock H3 material | Verified original map |
| --- | --- | --- |
| Circular quarter panel, white and red variants | `objects/vehicles/brute_chopper/shaders/brute_chopper_exposed.shader` | Standoff |
| `for_forge_gen_panel_02` | `levels/dlc/armory/shaders/metal_black_ibeam_unwrap.shader` | Rat's Nest (`armory.map`) |

Only the environment-mapping selection differs among the nine shared shader
categories. The remaining albedo, normals, specular mask, lighting model,
illumination, blending and parallax selections match. The stock shaders have
no enabled MCC-only options. This reuses material tags; the vehicle-free Forge
palette remains unchanged.

The original panels have a nonzero reflection contribution, so silently
disabling reflections would lose an active feature. Their fixed Reach cubemap
cannot be retained as the input to the proposed dynamic H3 option. The proposal
does not extend the user's creek-cubemap decision beyond the cliffs.

The available stock-map inventory contains no exact nine-category match,
including variants with first-person settings. This does not establish absence
from every shipped campaign asset. Native map-cache options and unchanged
hashes were checked with unmodified TagTool; the MCC donor tags were checked
against their native inventory hashes. Evidence is in
`work/stock-h3-audit/panel-reflection-proposal-evidence.json`, reproducible with
`inspect_panel_reflection_proposal.py`.

The authored materials retain their Reach artwork and source texture controls
and use stock H3 reflection behavior. Generate cluster cubemaps with official
Tool during the MCC build and inspect the result in the user's MCC walkthrough. This does not approve the MCC version or permit 360 conversion.

H3's dynamic option uses a Tool-generated cubemap for the nearby cluster;
per-pixel uses the explicitly selected bitmap. See the
[official H3 environment-mapping documentation](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/shaders/environmentmapping).


Native assignment evidence: `circle_panels-family/` and `forge_panel-family/`
under `work/stock-h3-audit`, plus the two donor-integrity reports. All eight
family image records passed pixel/mip checks. The circular panels retain 19
selected source functions each; the Forge panel retains 11, plus one scalar
source-default correction through the official editor. Reach's fixed reflection
cube is intentionally not imported for these materials. H3's native local-map
reflection settings replace that input, as approved; no custom roughness mapping
or reflection shader was authored.
