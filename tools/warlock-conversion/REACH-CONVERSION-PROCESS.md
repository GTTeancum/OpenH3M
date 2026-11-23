# Reach authoring to original Halo 3: process and evidence

Updated 2026-11-21. This is a living process specification, not a claim that
the pipeline or Battle Canyon is complete. Update it as evidence changes.

## Latest recorded build state

The earlier Battle Canyon implementation and its dedicated rebuild directory
were retired. Current fresh-work state and tool evidence live in
[SOURCE-PREFLIGHT.md](../stock-h3-audit/SOURCE-PREFLIGHT.md), following the
[user-approved fresh sequence](../stock-h3-audit/REBUILD-PLAN.md). Earlier
draft-preview/integration results are historical and do not establish acceptance
of the fresh work. Do not restore the rejected implementation from old notes.

The related [Halo 4-to-H3 WIP process](HALO4-CONVERSION-PROCESS.md) reuses this
document's evidence checkpoints and existing tools. Reach-specific decisions
and map-specific exceptions do not automatically apply to Halo 4.

## Scope and invariants

- Original editable Reach assets are inputs. Preserve originals; derive H3
  authoring data separately. Record exact source, author/contributors, revision,
  file hash, tool versions and any preprocessing.
- Reuse original Xbox 360 H3 gameplay assets when equivalents exist, including
  dependencies and behavior. Kit availability alone does not establish that an
  asset shipped on the original disc. Inspect disc/shared resources too.
- Preserve visible geometry and authored placement. Collision simplification
  is a separate change; Battle Canyon has explicit user authorization for it.
- No engine workaround for this map conversion. Preserve original formats,
  simulation and network semantics; compatibility is not verified system link.
- A missing reference is not permission to remove an object or effect. Record
  whether it is active, optional, unsupported or unresolved, and why.
- Keep all generated files, caches, temporary directories, logs and captures
  inside this repository. Steam kits and original disc data are read-only inputs.
- Retain the installed maps until a replacement is actually accepted. Never
  distribute original game assets through source commits.

## Reusable user decisions (2026-10-28)

The user clarified that decisions made while rebuilding Battle Canyon belong
in this shared process wherever they apply to other Reach conversions. The
rules below apply to Reach-to-original-H3 conversions overall; Battle Canyon
paths, counts and generated reports are implementation examples, not scope limits.

- **Forge armor abilities:** replace the Reach armor-ability category with stock
  Halo 3 equipment. Do not implement armor lock, evade, hologram, jetpack or
  sprint in the original H3 core. Use native equipment references, behavior,
  menu labels, costs and limits; audit native donors rather than assuming MCC
  authoring palettes contain only shipping H3 entries.
- **Health stations (user 2026-11-22, supersedes keeping them as nonfunctional
  scenery):** remove Reach health stations and their placements in every Reach-to-H3
  conversion. Battle Canyon's four come out at its next rebuild. This rule concerns
  Reach health stations; it does not change the earlier removal of CE-style packs in
  Prisoner and Boarding Action.
- **Gravity lifts:** start with the stock H3 equivalent. If its force or exit
  direction does not suit the authored passage, copying relevant Reach item
  values into supported H3 fields is authorized. Establish field meanings,
  coordinate conventions and units first, then verify traversal. This is a
  narrow item-tuning exception, not permission to change the engine, raise
  limits or retune unrelated stock assets. It is not a shader workaround.
- **Stock/shared reuse:** audit every asset type already used by the target,
  including actual references into `shared.map`, before custom import. Reuse
  suitable native assets and dependencies; check other original H3 maps too.
  This includes audio, textures, shaders, models, animation, physics, effects
  and gameplay objects. Preserve shared resource references and avoid duplicate
  payloads. See [the required asset audit](ASSET-REUSE-AUDIT.md) for evidence and
  native-output checks. This rule also applies beyond Reach conversions.

Maintain reusable decisions here as they are clarified. Map notes should link
to the rule and record implementation/evidence separately; do not require the
same user decision again merely because the next map has a different name.
Unrelated map-specific exceptions remain scoped as recorded. A temporary pause
to research the tools is not a permanent non-test restriction on this process.

## The five checkpoints

| Checkpoint | What it establishes | What it does not establish |
| --- | --- | --- |
| Reach authoring | Editable scene/tag intent: geometry, placement, parameters, inheritance and functions | Which values are active after defaults, preprocessing and compilation |
| Reach evaluation | Effective settings calculated by official tools, including composite editor controls | Full gameplay/render behavior; tool diagnostics are not a game run |
| H3 authoring | Explicit translation into H3-supported fields and asset references | That H3 evaluates those fields as intended |
| H3 compiled output | Actual MCC cache bindings, constants, geometry, collision, visibility and resources | That the native converter preserves them, or that runtime is correct |
| Original-H3 output | Native layouts, reference remapping, resource encoding and donor-program bindings | Console memory residency, system link, frame rate or visual acceptance |

These are checkpoints for one asset, not five independent builds. Track the
first boundary where its meaning changes. Fix that boundary rather than
compensating downstream with brightness, geometry offsets or shader guesses.

For game semantics, source-of-truth order: active evaluated tool output and the relevant shader
implementation; then active authored fields/inheritance; then stock examples
using the same feature and official documentation. Old editor fields, matching
names, a successful converter report and a screenshot are not interchangeable
proof. If these sources disagree, retain the disagreement until explained.
Foundry and General-101 source establish what those community exporters do;
they are not independent proof of game-engine behavior. Check the installed
kit version and active path when applying older official documentation.

## Evidence record for each translation

For each feature or asset, record:

1. Source path/revision and active use (placement, material, dependency or mode).
2. Authored value, inherited/default value, effective value, units and formula.
3. H3 representation and the reason it is equivalent or approximate.
4. Source evaluator evidence and target evaluator evidence with report paths.
5. Compiled-cache evidence and native-output evidence, when available.
6. Lost/added fields, unsupported behavior and approved substitutions.
7. Status: verified at a named boundary, provisional, unresolved, or rejected.
8. Remaining runtime questions. Do not label a whole asset verified from one field.

Group reusable translations by feature. Keep map-specific artistic adjustments
separate. A change that makes one screenshot attractive is not automatically a
Reach conversion rule.

## Workflow and gates

### 1. Acquire and inventory

Resolve the source's provenance before selecting a cache or scene. Record the
original game's authorship separately from community extraction/preparation and
this project's adaptation. Inventory scene objects, unique meshes, materials,
lights, portals, collision proxies, helper volumes and placements. Traverse
dependencies by exact paths, distinguishing active references from unused
palette entries and inactive shader parameters.

Perform the [stock/shared asset audit](ASSET-REUSE-AUDIT.md) for every asset type
before custom imports. Trace what the stock target already references from
`shared.map`, check other original H3 maps, and record selected native donors,
resource locations and unresolved matches. Recheck actual reuse and duplication
in the final native cache. An audio-only inventory does not satisfy this gate.

Gate: every used source dependency has an identified source or an explicit open
issue. Do not treat a file's absence from one extracted subset as proof that it
does not exist. Do not treat missing unused assets as a reason to import whole
archives. Pin tools and avoid duplicate full installations/build silos.

### 2. Establish geometry semantics before export

Foundry properties are not automatically understood by General-101 ASS. Audit
coordinate axes, unit scale, instance transforms, normal/tangent orientation,
handedness, UV channels, vertex colors, material indices and shared meshes.
Translate face masks, render/collision modes, transparency, shadow casting,
emissive settings, portal flags, lighting policies and lightmap-resolution
values by meaning, not raw enum number.

Bake unsupported nonuniform transforms only on derived data and compare
world-space vertices. Apply unit conversion to both mesh vertices and instance
translations. Keep water, planar fog, soft ceilings and lighting helpers out of
ordinary geometry unless their intended representation is established.

Gate: compare source and compiled bounds, topology/material assignments and
representative transforms. A bounds match alone cannot prove all vertices or
normals correct. Separately document collision reduction, protected surfaces
and error metrics. A maximum vertex distance is not a complete surface-error
or traversal measurement.

### 3. Translate materials from evaluated settings

For each active permutation, establish category/option names, parent references,
default values, switches and static or animated functions. Evaluate composite
controls with the source tools before translating. Compare destination tool
evaluation, not just copied tag fields.

Audit texture interpretation as well as bytes: color space, channel packing,
signed normal formats, normal strength/combination, alpha purpose, image index,
cubemap layout, mip levels, UV transforms, filtering, addressing and animation.
Record which source parameters are inactive for the chosen permutation.

Choose native shader donors by actual program/permutation capability. A matching
template name does not establish identical semantics across games. Map textures,
constants, switches and animation routes explicitly; do not inherit arbitrary
metal/rock donor values. Record neutral added inputs and missing layers. Do not
copy MCC shader programs into the original H3 cache.

Gate: no unexplained active parameter loss or generic fallback. Any approximation
must identify the feature it changes and why H3 cannot represent it directly.
Brightness changes cannot repair incorrect reflectance or texture interpretation.

### 4. Establish lighting inputs before baking

Compare sky-model light lists, light directions/intensities/units, area/emissive
lights, cluster sky assignments, instance lighting policies, lightmap scales,
chart generation, shadow flags and probe locations. Preserve camera exposure,
bloom and atmospheric settings with their shipping H3 schemaâ€”not an obsolete
kit layout selected only because its tag group matches.

Trace every UV warning to the affected mesh/channel and every shader
postprocess failure to its stage and effect. Do not erase secondary UVs without
establishing their purpose. Confirm source placement coordinates before baking;
lighting probes depend on the final placement set and object identities.

Gate: explained compiler warnings, valid bake inputs and documented resolution/
memory choices. A successful draft bake is not a correct final lightmap. Matching
converted lightmap pixels proves transport, not the correctness of the bake.

For an early playable preview, the official H3 farm driver accepts `direct_only`
as well as `draft` quality. Use an explicitly identified preview rather than
requiring a multi-hour final-quality bake before inspecting the map in-game.
Prefer `draft` when speed is the priority: the [official quality guide](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/art/lightmap/qualitysettings)
states that it uses one sun ray versus 64 in `direct_only`; both omit bounced
light. Direct-only improves shadow edges but is not the fastest preview setting.
Keep failed or expensive farm datasets separate: H3EK's farm job identifier
must be a positive number, not a descriptive directory name. Record the selected
quality and dataset, preserve the official stage sequence, and require successful
finish/texture compression before using outputs. Preview lighting does not
establish final lighting quality or resolve a failed higher-quality bake.

### 5. Translate scenario behavior

Inventory placements and Forge entries independently. Map weapons, equipment,
vehicles and stock gameplay features to verified original H3 assets. Compare
attachment markers, lift force volumes/directions, collision shapes, sounds,
effects, spawning rules, teams, mode masks and object IDs. Reach labels/scripts
do not become H3 behavior merely by surviving tag conversion.

Apply the [reusable user decisions](#reusable-user-decisions-2026-10-28) to armor
abilities, health stations, lift tuning and shared-asset reuse. Record their
application per map without reclassifying those rules as map-specific exceptions.

Avoid multiplying placements to emulate mode flags when one native object can
express the rule. Enforce native array/index limits before compilation. Explicitly
list unsupported modes, health behavior, audio, effects and palette entries;
do not silently omit them or count decorative equivalents as functional ones.

Gate: every intended gameplay element has a supported representation or a
documented unresolved decision. Full palette policy remains binding where required.

### 6. Compile H3, then audit native conversion

Use official H3 structure/render/collision/physics tools and the official
lightmapping pipeline. Check the compiler's explicit success record and required
outputs: zero exit status alone is insufficient. Record candidate hashes and
input revisions so evidence cannot accidentally refer to a different build.

Native conversion must verify tag layouts, endian conversion, resource pages,
bitmap encoding, strings, references, collision trees, animation routing,
shader donors and shared-resource reuse. Inventory duplicated resources and
avoidable resident data. Preserve map identity and the other installed maps.

Gate: compiled/static checks support exactly what they measure. File size does
not equal peak RAM; the console's 512 MiB is shared by code and other runtime
allocations. PC placeholder counters cannot certify console residency. Stock
comparisons are useful evidence, not a complete memory budget or FPS guarantee.

### 7. Runtime validation and deployment

Use a bounded process-local harness and the game's native capture facilities. No
desktop takeover or OS input. Verify the correct map/mode, actual movement,
visual surfaces, occlusion, water, effects, audio, traversal and gameplay.
Collect frame times on a defined route; rendered frames or a window title are
not proof of correct content or sustained performance. Use a small number of
targeted captures to answer questions remaining after static analysis.

Deploy only an accepted candidate, with reproducible steps, credits and the
known limitations recorded. Keep rollback evidence without accumulating redundant
full maps or installs. Cleanup must be explicit and confined; a previous policy
rejection of obsolete-candidate deletion remains unresolved and must not be bypassed.

## Battle Canyon evidence ledger

Paths below are relative to `work/battle-canyon/rebuild/` unless specified.

| Finding | Evidence | Scope/limitation |
| --- | --- | --- |
| Pinned authoring source and exporter | `source/provenance.json` | Crisp/community preparation; original Reach map, not Ryno's compiled H3 port |
| Foundry `y-` requires +90Â° Z for this export; units include translations | `tools/battle-canyon-rebuild/export_geometry.py`, `audit_coordinates.py` | Six BSP bounds match; not a universal hard-coded rotation for every scene |
| Protected collision and section partitioning | `collision-simplification.json`, `plan_decal_protection.py`, `protect_collision.py` | Render terrain retained; traversal still unverified |
| Old camera schema omitted active exposure/bloom fields | `prepare_camera.py`, `reference/camera-corrected.json` | Shipping Zanzibar layout preserves fields; overall lighting not accepted |
| Generic native metal fallback lost material features | `reference/native-material-coverage.json`, `native/native-materials-05.json` | 93/103 ordinary materials have exact native permutations; exact permutation alone is not full fidelity |
| Reach composite rock specular colors were not expanded by H3 | `reach-ca_bcreek_arch_rock-evaluated.log`, `h3-rock-adapted-inspect.log` | Arch tint/exponent now match evaluated source; remaining reflectance and screenshot attribution unresolved |
| Terrain wall layer 0 really evaluates to power 1, environment contribution 5 | `reach-ca_bcreek_cliff_walls-evaluated.log` | Do not call these values corruption; investigate environment-path differences |
| Lightmap transport matches H3 compiler output | `reference/lightmap-pixel-audit-04.json` | Ten layers checked; does not validate authored UVs or illumination |
| Duplicate initial spawns overflowed native variant storage | `prepare_spawn_marker.py`, native preflight and candidate reports | 751 reduced to 343 using shared masks; native capacity 640; remaining content must fit too |
| Walk check ended against a wall | repo `.local/loading-traces/20261028-073901-3436/loading-trace.jsonl` | Not outdoor lighting/traversal acceptance |
| Four source meshes have second UV channels; sampled warning unmatched | `reference/lightmap-source-uvs.json` | No basis yet for deleting or replacing UV channels |

The new color adapter's automatic target-evaluator assertions were added after
its last full invocation. The arch shader was manually checked with H3's evaluator
after correcting color animation type; do not claim all three shaders passed
the newly added assertions. `compile-reflectance-06.log` proves only MCC cache
compilation. It does not prove a native or visual fix.

## Open questions, in investigation order

1. Finish active material-semantic mapping: Reach roughness/analytical power,
   terrain/environment behavior, normal interpretation, foliage wind and the
   remaining detail-normal layers. Identify the exact visible rock/material
   before attributing the user's screenshot to an ordinary or terrain shader.
2. Resolve lightmap UV warnings and shader-postprocess failures. Establish
   correct lighting inputs and policies before choosing another bake quality.
3. Complete visibility, water/fog/helper-volume and geometry-semantic audits.
4. Complete remaining placements, lift equivalence, audio/effects and Forge
   palette mappings. See `objective-pending.json`, `geometry-stage-pending.json`
   and `placed-dependencies.json`; historical counts can become stale.
5. Establish resource/budget accounting and reusable conversion rules, then
   determine deployment readiness. Targeted diagnostics may resolve individual
   questions at any stage; they do not require every open question to be closed.

## Tool map and reproducibility

Repository: `C:/X360/ISOs/H3M/.local/OpenH3M-source`.
Source kit staging: `work/editing-kits/hrek`; target: `work/editing-kits/h3ek`.
Scripts: `tools/battle-canyon-rebuild`; generated evidence: `work/battle-canyon/rebuild`.

| Stage | Existing entry points | Important restriction |
| --- | --- | --- |
| Scene inventory/preparation | `inspect.ps1`, `audit.ps1`, `prepare_scene.py` | Preparation mutates derived data; not a read-only audit |
| Geometry/material bindings | `export_geometry.py`, `bind_materials.py`, `compile_structure.ps1` | Validate transforms and semantics before export/compile |
| Tag and option adaptation | `plan_materials.py`, `resolve_material_options.py`, `tagbridge.rs`, `convert_dependencies.py` | Reports do not establish semantic fidelity; scripts may write tags |
| Evaluated shader inspection | kit `tool_fast.exe inspect-shader <tag-path-without-extension>` | Runs in staged kit; can write logs; repo-local TEMP/TMP required |
| Authored tag reading | `blam-tag-shell.exe -g <game> inspect ... --full --json` | Definitions and paths must match game; keep outputs in repo |
| Extra assets/scenario | `prepare_extra_assets.py`, `compile_props.py`, `plan_gameplay.py`, `plan_objectives.py`, `stage_decals.py` | Plans have unresolved entries; not a complete automated recipe |
| Camera/rock adaptations | `prepare_camera.py`, `prepare_rock_reflectance.py` | Existing targeted adaptations, not universal Reach rules |
| Lighting | `lightmap.py` wrapping official `calc_lm_farm_local.py` | Completed placements needed before final bake |
| MCC/native cache | official `build-cache-file`, `build_native.ps1` | Candidate report/hash needed for any acceptance claim |
| Runtime | `check_native.ps1`, process-local `trace_loading.py` | Match the harness route and captures to the intended checks |

There is not yet a verified, end-to-end one-command Reach conversion recipe.
The table identifies existing tools without pretending that their historical
execution order is a finished general pipeline. Before reuse, resolve open
semantics and make each stage's inputs, outputs and invalidation rules explicit.
Geometry changes invalidate compiled geometry and associated lighting; placement
changes can invalidate probes/IDs; material changes invalidate compiled shader
data and may affect baked lighting; native-only encoding changes require a new
native artifact even if the MCC cache is unchanged.

## Primary references and attribution

- [HaloReachScenarios](https://github.com/ILoveAGoodCrisp/HaloReachScenarios),
  Crisp/community; Battle Canyon scene revision `aa35d15ff50db13da39685ad537430ad78492778`.
- [General-101 Halo Asset Blender Development Toolset](https://github.com/General-101/Halo-Asset-Blender-Development-Toolset),
  Steven Garcia/General-101 and repository contributors; revision
  `6577fae3045c3d9ae8aa689ed7bb98b3196cf22c`.
- [blam-tags](https://github.com/Zoephie/blam-tags), revision
  `5d0509fb75eadb96ac7774542ca0b2c10aed7b00`; definitions revision recorded in the Battle Canyon README.
- Installed Microsoft Reach/H3 Mod Tools: evaluator output and original shader
  source tags. Inspect the active shader path before relying on an old include.
- [Microsoft H3 instance-object documentation](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/art/instanceobjects/instanceobjectshome).
- [Microsoft H3 material-model documentation](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/shaders/materialmodel).

Keep map credits in `MAP-CREDITS.md`. Ryno's Remember Reach H3 MCC conversion
is the previous Battle Canyon source/comparison, not the author of this fresh
Reach-authoring adaptation. Preserve original map and source-preparation credits
separately from OpenH3M/Xbox 360 conversion work.

## Documentation review: narrowed unknowns (2026-10-28)

### Native objects outside stock Forge menus

Audit the level's complete object tag index, not only its Forge menu. Battle
Canyon's second pass found eight additional native choices this way: five
sandbag wall forms, the small barricade, single industrial crate and military
pallet. Reach's sandbag entries are crates, whereas their original H3 counterparts
are scenery; preserve the native H3 object type and behavior. When an object
has no native Forge menu record, distinguish its menu authoring from asset reuse:
the current adapter retains the source menu cost/limit and requires an existing
native string label. This does not prove resource residency or placement behavior;
those remain separate checks. Evidence and implementation:
`tools/battle-canyon-rebuild/audit_native_forge_objects.py` and
`work/battle-canyon/rebuild/forge/native-object-inventory.json`.

This review records findings, not a new operating restriction. The learning
break does not change the build/test process or add an approval requirement.
No map assets, conversion code or runtime were changed during this review.

### Draft lighting is a known limitation, not an unexplained fidelity result

[Official lightmap quality documentation](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/art/lightmap/qualitysettings)
explains that draft omits bounced lighting and uses sparse direct-light sampling.
Low introduces bounced illumination; higher settings improve sampling further.
The existing `lightmap-aligned-draft.log` explicitly records `quality setting:
draft` (line 98741 at this review). Running every farm stage does not imply that
the selected quality enables all lighting contributions.

Status: the bake-quality limitation is established. Its contribution to the
observed dark areas is a strong explanation, not proof that it is the only
cause. Do not infer incorrect authored brightness from this draft result.
Invalid UVs and postprocess failures still require their own explanations.

### Reach analytical roughness has an explicit source formula

The staged Reach source
`work/editing-kits/hrek/tags/shaders/templated/materials/power_roughness_conversion.hlsl_include`
contains the active expression `0.27291 * pow(max(roughness, 0.01), -1.3973)`
for its C-side roughness-to-power conversion. The file also contains older,
commented alternatives; those are not the active expression. For authored
analytical roughness 0.3, this yields 1.467702, matching the official Reach
arch-rock evaluator's printed `analytical_power = 1.468`.

`two_lobe_phong.hlsl_include` uses analytical_power for analytical highlights;
`shared_specular.hlsl_include` separately carries roughness and angle-dependent
colors. H3's evaluated arch shader instead exposes normal/glancing powers
55/10. Thus copying the old source power fields does not reproduce Reach's
active analytical path. The computation is now understood; a faithful H3
representation across area and analytical lighting is not yet established.
Do not equate a formula match with a complete material conversion.

### Environment reflections have additional dependencies and platform encoding

[Official H3 environment mapping documentation](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/shaders/environmentmapping)
identifies dynamic reflections as cluster cubemaps generated by Tool, with a
roughness-scale control. Reach's staged `environment_mapping.hlsl_include`
calculates reflection LOD from base roughness plus an offset, not merely a
same-named H3 scale. It also contains a non-Xenon adjustment for dynamic cube
samples and explicitly notes Xenon's exponent adjustment.

Status: check actual environment mode, generated cluster cubemaps, mip selection
and texture encoding together. A correct scalar or cubemap pixel payload alone
is insufficient. This is an additional investigation path, not evidence that
Battle Canyon currently has a cubemap encoding defect. A large authored
reflection contribution is not automatically corruption.

### Specular-mask channels can explain a plastic surface independently of tint

[Official H3 specular-mask documentation](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/shaders/specularmask)
warns that an unmasked highlight can look plastic. Diffuse-based masking reads
the base-map alpha. This gives a concrete audit: compare the active mask option
and that channel through both conversions, including any alpha-forcing step.
The documentation's separate-texture description has ambiguous parameter naming;
use the selected shader implementation to settle its exact source/channel.

Status: relevant mechanism established; missing masks on the screenshot's rock
are not established. Identify its shader before applying this explanation.

### Instance lighting and UV sharing must be examined together

[Official instance lightmap resolution documentation](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/art/lightmap/instanceresolution)
describes a default 64x64 instance lightmap and resolution multipliers, with
shared UV coordinates across a definition's instances. The separate
[instance-object documentation](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/art/instanceobjects/instanceobjectshome)
distinguishes per-pixel, per-vertex and single-probe modes; shared per-pixel
instances compete for the structure lightmap allocation.

Status: do not assume every partitioned terrain instance has suitable lighting
resolution because export succeeded. Follow its compiled policy, definition
sharing, generated UVs and atlas allocation. The documented defaults are not a
measurement of the current atlas and do not diagnose the out-of-bounds warnings.

### Lighting-region support can reduce later bake work

[Official lighting-region documentation](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/art/lightmap/regions)
describes region-limited lightmapping and reuse of the previous valid lighting
outside the region. The staged official `calc_lm_farm_local.py` already accepts
a light_group argument. Our wrapper currently passes all.

Status: a supported way to narrow future bake work exists. It requires a valid
baseline and correctly authored regions; it cannot repair a globally invalid
bake or justify stale lighting after structural changes. No regions or scripts
were changed in this review.

### Dynamic lights have documented cost and shadow limitations

[Official H3 dynamic-light documentation](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/individual/dynamiclights)
distinguishes cheap non-shadow-casting lights from expensive shadow-capable
lights and their extra render passes. Marker local X is the light direction.

Status: map the source attachment orientation and light class before assuming
a light should be occluded or adding expensive lights to compensate for dark
baked lighting. Lens flares, emissive surfaces and dynamic lights are different
paths; this does not diagnose the previously reported flare-through-wall issue.

### Remaining gaps after this review

The documentation narrows the causes but does not resolve the exact UV-warning
mesh/channel, shader-postprocess failures, screenshot material identity, all
normal-map formats, visibility/helper semantics, gameplay/audio mappings, or
complete resource residency. Those remain explicit open questions. The next
investigation should reconcile these source/tool facts with active compiled
assets before another map-specific adjustment.


## Extended source review (2026-10-28)

This pass cross-checked the pinned Foundry/exporter sources, official H3 docs,
existing scene inventory, Reach scenario fields and prior compiler logs. The
small evidence record is
`work/battle-canyon/rebuild/reference/documentation-review-20261028.json`;
it includes source hashes. No map was rebuilt or accepted in this review.

### Light units: verified current values versus reusable bridge gaps

Foundry `reference/utils.py::calc_light_intensity` returns SUN energy unchanged.
For other Reach lights its formula, with Blender export scale squared, reduces
to energy / 300. `scene.py::scale_items` and the scene property's default select
Blender scale when the saved scene has no explicit scale override.

The saved Battle Canyon inventory contains 729 authored lights: 695 POINT and
34 SPOT, no SUN. All 729 have positive authored cutoff distances and their
energy / 300 agrees with the stored intensity within 0.00001. The export report
also contains 729 light records. These are scene/bake lights, not the separately
counted 13 scenario light-scenery placements. Neither count measures runtime
shadow-casting light cost.

The current bridge divides every light's energy by 300. This matches the
recorded current non-sun intensities, but would be wrong for a SUN object.
Foundry also supports automatic attenuation when distances are unset. The
bridge does not implement that behavior; no current light in this inventory
uses a nonpositive cutoff. Keep these as general bridge limitations, not
established causes of Battle Canyon's darkness. Matching intensity does not
verify cone shape, color interpretation, orientation or compiled attenuation.

### Emissive surfaces: exclude stale power here; retain bounce-ratio gap

Foundry's mesh light-intensity getter evaluates current emissive energy, and
its export process computes automatic attenuation when cutoff is unset. Our
bridge instead uses `light_intensity_value` and the saved distances directly.
In this inventory, all 102 object-level emissive records have positive cutoff
and matching power / 300 versus stored intensity. Shared meshes repeat in
this count; it is not 102 independent materials or unique emissive faces.
Thus stale stored power and missing automatic falloff are not supported as
current causes by these records.

However, Foundry exports `material_lighting_bounce_ratio`, while our
`export_geometry.py::settings` does not map it. Recorded ratios include 0.05,
0.5 and 1.0. General-101's `file_ass/process_scene.py` writes basic power,
color, quality, per-unit-area, focus and attenuation but no corresponding
bounce-ratio field in those records. H3 equivalence is unresolved: establish
whether it belongs in another target field or is an unsupported approximation.
Do not silently substitute primary intensity for bounced-light contribution.
The focus conversion itself agrees algebraically: radians / pi equals
Foundry's degrees / 180.

### Color conversion is field-specific

Foundry exports emissive color with `utils.color_4p_int`: each RGB component is
raised to 1/2.2, scaled by 255 and truncated to an integer, with alpha 255.
Its translucency tint uses `color_3p_int`, which scales/truncates without that
power conversion. Both functions are in the pinned `reference/utils.py`.
General-101 writes ASS emissive RGB as floating-point values, and our bridge
copies the source components directly into those values.

This establishes different serialization paths, not a proven gamma defect:
H3's ASS importer may expect linear values where Reach's intermediate expects
encoded integers. Compare evaluated/compiled colors at the importer boundary
before adding a gamma adjustment. One global color conversion would be
unsupported by the source evidence. Also distinguish the function's actual
power-2.2 approximation from the standard piecewise sRGB transfer function.

### Lightmap buckets are scenario settings, not universal constants

Foundry exports an enum identifier for face resolution. The raw Blender
inventory uses indices 0..6; the property identifiers are strings 1..7. Do not
introduce an off-by-one correction just because these representations differ.
The actual Reach scenario's `lightmap setting` block contains the seven values
1, 4, 16, 64, 128, 256, 512, agreeing with the bridge's table for this map.
Foundry explicitly allows scenario-level changes to those buckets. Therefore
hard-coding that table is not a general Reach conversion rule.

The further division by 16 into H3 ASS material scale remains a provisional
translation, not a measured equality of texel density. General-101 documents
that destination field as a scale with default 1, while H3 instance resolution
and per-face allocation are distinct controls. Confirm compiled chart density
and allocation before treating the arithmetic as proof. Avoid describing Reach
bucket values as literal bitmap dimensions.

Evidence: `reference/reach-scenario-full.json` structure-BSP lightmap settings;
`reference/mesh.py` enum property; `reference/constants.py` description;
General-101 `global_ui/material_ui.py::lightmap_res`; our `settings` function.

### Shader failures: a narrower comparison is available

The earlier corrected-draft and aligned-draft logs contain the same 43 shader
paths reporting `render_method_group::postprocess_tag_proc` failure. In the
saved 113-material audit, the dominant template
`_0_1_0_1_2_1_0_0_0_0_0_0_0` has 35 recorded failures, but three materials using
that template are absent from the error list: `ca_bcreek_metal_beams`,
`ca_bcreek_panel_deco_trim2`, and `ca_bcreek_panel_tower_b`.

This rules out treating the template identifier alone as a sufficient failure
classifier. Compare active inputs, dependencies, functions and processing
context between these materials before replacing the template. Absence from
an error list is not proof that a material was processed successfully or even
exercised. The audit's `failed: false` must be read with that limitation.
A successful later cache compile does not explain the lightmapper's failures.

### Separate source bitmap authoring from compiled normal sampling

The [official H3 bump-mapping page](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/shaders/bumpmapping)
describes grayscale height-map authoring and the bitmap bump-height setting.
That is not a license to reinterpret all compiled bump textures as grayscale.
Reach's supplied `templated/bump_mapping.hlsl_include::sample_bumpmap` samples
components, reconstructs Z as sqrt(1 - saturate(dot(XY, XY))), and normalizes;
its platform branch explicitly mentions Xenon compressed normal behavior.

For each texture, follow source import usage/format, compiled channels, sampler
interpretation and tangent frame through the H3/native path. The source
implementation establishes this distinction, not correctness of our converted
normal textures. Normal/decode equivalence remains open.

### Transparency can change lighting as well as visible blending

The [official H3 lightmap translucency examples](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/art/lightmap/translucency)
show different baked results for two-sided tint, alpha blending/testing and
multiply/additive modes. A copied transparency flag is therefore not only a
runtime appearance concern. Compare both face-side flags and active shader
blend/alpha behavior before a final bake. Our bridge maps two-sidedness and
one-sided transparency independently; the current object inventory contains
no object with both explicit overrides, so their combined translation is a
general unverified case, not an identified current defect.

### UV diagnostics identify two different populations

The aligned-draft log contains 24,114 out-of-bounds UV errors across 125 plate
sections, associated with each preceding `starting resolve for plate mesh`
header. Plate 0 has none of those errors. Its separate problem is chart
allocation: 78,730 charts into 1024x1024, with 282,682 of 290,958 faces reported
as too small during resolve. Plate 0 reports 566 instances. Plate 1, where the
first sampled error occurs, reports 3,734 faces and zero instances.

These log categories are not yet mapped to exact source objects; zero in this
log's instance field does not establish a mesh's authored class. Still, the
separation means the atlas-density problem and out-of-bounds errors should not
be treated as one measured defect with one assumed fix. The evidence record
stores counts by plate without retaining another full log copy.

General-101's `process_mesh_export_uv` exports each existing UV layer in order;
it does not synthesize or validate a lightmap channel there. The prior source
UV audit only compared one error coordinate (with an optional V flip); its lack
of a match does not exclude transformations, evaluated geometry, chart
processing or other warning coordinates. Trace plate/definition identity and
actual compiled channels next. Neither a global UV deletion nor a global atlas
increase follows from the current evidence.

### Follow-through with the installed tools (2026-10-28)

The findings below supersede the open-question status of the preceding review.
They come from official tool evaluation/XML exports, compiled tags, existing
lightmap data and independent readback of the native cache. No material tuning,
replacement bake, map deployment or game run was performed during this pass.
That describes this investigation, not a restriction on the conversion workflow.

#### Confirmed bridge errors: emitter range and light shape

The authored emissive cutoff 4.572 metres is converted by `export_geometry.py`
to 1.5 before writing `BM_LIGHTING_ATTEN`. The H3 import result, confirmed by
official `export-tag-to-xml`, is **0.015 world units**, not the intended 1.5.
The importer applies the ASS-to-world-unit factor of 0.01. Our generic lights
already use the correct ASS distance scale (metres / 0.03048); the emissive
path uses metres / 3.048 and therefore shrinks the enabled range another 100x.
Another emitter becomes 0.0075 instead of 0.75. Correct the intermediate units,
not the source artist's cutoff or light intensity. This establishes a bridge
error; it does not quantify its contribution to a particular rendered pixel.

Reach's corresponding material flag is named `reserved{use attenuation}`;
H3's bit 0 is `use attenuation`. Do not copy these flags by ordinal and assume
their evaluation semantics are identical. Our H3 emitter explicitly enables it.

Foundry's stored Blender shape index is 0=circle, 1=rectangle. The bridge copies
that integer into ASS. The official H3 result reverses the intended shape:
all 51 source/target light definitions differ by name, including 14 spot-light
definitions. **Reach and H3 compiled enums themselves agree** (rectangle,
circle); the mismatch is the authoring-to-ASS boundary. Map symbolic shapes,
not raw Blender enum indices. The 37 omni definitions have the same enum
mismatch, but that alone does not prove a visible effect on omni lights.
All 51 definition intensities agree. Spot angles use degrees in the Reach XML
and radians in H3; that unit difference is not itself corruption.

Evidence: `reference/h3-lighting-official.xml`, `reach-lighting-official.xml`,
`investigate-official-lighting-comparison.json`; Foundry `light.py`, both kit
`scenario_structure_lighting_info` schemas, and the bridge `settings`/light
export paths. References in this section are relative to
`work/battle-canyon/rebuild/`.

#### UV warning traced through the actual runtime binding

The first logged pair (-1.963593, -0.287433) exactly matches faux-data mesh 0,
raw vertex 0, **lightmap texcoord**. Its ordinary texture UV is
(0.904439, 0.573125). This is instance definition 0, used by
`!battle_canyon_terrain_00`, not cluster 0. Its pre-faux lightmap UV was (0,0):
the offending coordinates are generated lightmap-processing data, not proof
of an invalid source diffuse UV layer.

That instance uses per-pixel shared lighting and lightmap-coordinate block 0.
The separate shared stream contains 3,282 vertices, all within the unit square.
Its first coordinates are (0.316645,0.964481). The compiled MCC stream is vertex
buffer 611, with (0.316640,0.964477) after UShort2N quantization. These are
normalized unsigned 16-bit coordinates, **not half floats**.

Independent cache readback establishes:

- All 567 static-per-pixel coordinate buffers match native output byte-for-byte
  after endian conversion.
- All 566 per-instance buffer bindings match in MCC `Lbsp` and native `sLdT`.
  The native BSP's empty duplicate table is not the binding to compare.
- All 1,255 instance-lighting records match between those caches.

The follow-up maps **all 24,114 diagnostics across all 125 warning plates**:
all three logged UV pairs in every diagnostic occur in the matched faux
base-mesh stream, allowing for vertex reordering and six-decimal log precision.
All matched meshes' instances use per-pixel shared lighting and a valid
separate UV block. There are 123 uniquely identified plates; plates 183 and
229 each match meshes 454 and 545, which share the relevant coordinates and
both use shared lighting. This is coordinate membership, not a claim that the
logged triangle indices survive subsequent vertex/triangle reordering.

The warnings therefore concern base-mesh coordinates rather than the separately
bound shared stream. They do not establish a native UV-conversion defect.
The shared atlas's chart-density loss remains an independent issue. Do not
delete source UVs on the strength of these warnings.

Evidence: `investigate-faux-vertex0.json`, `investigate-faux-shared-uv0.json`,
`investigate-lbsp-shared-uv0.json`, `investigate-payload-equivalence.json`,
`investigate-warning-plate-candidates.json`, `investigate-all-warning-coordinates.json`.
Repeat the cache audit with `tools/battle-canyon-rebuild/audit_research_payloads.py`.
Repeat the complete logged-coordinate check with
`tools/battle-canyon-rebuild/audit_lightmap_warning_coordinates.py`.
It compares current MCC revision 06 against native revision 05; exact matches
establish the stated payload equivalence, not whole-cache identity.

#### Allocation and apparently missing lighting

Official `tool_fast faux_stats` reports 26 clusters and 566 shared-plate
instances sharing 1,048,576 plate probes; 510 per-vertex instances use 405,045
probe values. It reports no separate-bitmap instances, 126 single-instance
probes, and 53 instances with no lightmap data. All 53 have **zero render parts
and vertex-buffer index -1**. They include collision boxes/spheres; they are
not 53 visible objects accidentally left dark.

The supplied Reach lightmap is 1536x1536: one direction image and three
intensity slices. H3's generated arrays are 1024x1024 with eight lightprobe
and two dominant-intensity slices. These represent different lighting bases;
their slice counts cannot be treated as equivalent spatial resolution.
The actual H3 allocation, the earlier 282,682 too-small faces and the 78,730
charts are now measured facts. Dividing Reach's resolution bucket by 16 is
still not a demonstrated density-preserving translation. The installed data
supplies endpoints, not an inverse chart-allocation formula or a universal
Reach-to-H3 multiplier.

Evidence: `investigate-faux-stats.log`, `investigate-no-lightmap-instances.json`,
`investigate-instance-definition-map.json`,
`investigate-reach-lightmap-dimensions.json`, `lightmap-pixel-audit-04.json`.

#### Normal textures and tangent frames survive native conversion

All 50 distinct Battle Canyon DXN base-mip payloads were independently matched
in native revision 05 after selecting the retained mip (maximum dimension 512),
biasing the signed MCC endpoints by 128 and untile/readback. Their native GPU
fetch word is uniformly `0x1a215571`, matching the stock DXN interpretation.
This check covers base mips, not every lower mip or material sampler binding.

Across all 575 primary geometry buffers, the maximum normal/binormal/tangent
component difference is 0.000978265, consistent with the expected 10:11:11
packing precision. There is no bulk normal sign flip or axis swap in these
payloads. This does not establish that the original authored tangent frame or
the selected material/detail strength is artistically correct.

The supplied H3 `bump_mapping_fx.hlsl_include` reconstructs Z from sampled XY,
then normalizes, as the Reach implementation does. Its explicit PC DX9
`BUMP_CONVERT` branch is not a reason to apply another bias to native textures;
the Xenon path relies on the fetch interpretation. Detail normals add scaled
XY before normalization. Read the active option before changing bump strength.

#### Historical shader errors versus current evaluation

All **43** paths in the prior lightmapper failure set now report
`Postprocessed: 1` under official H3 `inspect-shader`, with no missing-tag or
error messages. The command requires an extensionless render-method path;
passing `.shader` yields a cannot-load warning even with exit code zero.
Earlier failure logs also explicitly show invalid-tag removal, same-path
replacement and a missing cubemap replaced with `rasterizer\\invalid.bitmap`.

The current evaluator succeeds; the saved historical lightmapper run did not.
Neither proves which internal postprocess condition failed in that older run.
The distributed tool reports only the failing procedure, and its CPU source
is not included. It would be incorrect to claim either that the current bake
is clean or that changing a template is the demonstrated remedy. This is a
historical processing-context limitation, separate from current shader validity.
Evidence: `investigate-all-failed-shaders-evaluated.json`, individual
`investigate-eval-*.log`, and `h3ek/reports/reports_00/debug_full.txt`.

#### Bounce ratio, color domain, and the wet-clay screenshot

H3 has no counterpart to Reach's per-emitter `bounce ratio` in its material
lighting record or ASS representation. H3's PRT bounce count, photon fidelity,
surface diffuse scale and overall light scale control different operations;
none is a documented drop-in equivalent. Keep the source ratios (.05, .5, 1)
in the conversion report as an approximation requirement. Do not multiply
primary light power by those ratios or rename another field to conceal loss.

Official XML now proves the color boundary: source generic-light RGB
(0.588235,0.898039,0.984314) becomes H3
(0.311181,0.789314,0.965815), matching the Blender-linear values. The H3 import
preserves those values; it does not automatically restore Reach's encoded RGB.
The same issue appears in emitter colors. This establishes different stored
domains. The supplied schemas, exporter and runtime shader sources do not
establish the CPU lightmapper's expected transfer function for each input.
A global gamma correction remains unjustified. The runtime SH/material model
is described in [Bungie's lighting paper](https://advances.realtimerendering.com/s2008/SIGGRAPH-Lighting%20of%20Halo%203.pdf),
which does not specify that authoring/import color contract.

The user's wet-clay image matches the saved native capture
`.local/loading-traces/20261028-073338-3764/proof-loaded_112000ms.png`.
Its trace records the cache identity but no camera transform, depth, primitive
ID or material ID. Mod-tool tag inspection cannot uniquely assign a screenshot
pixel to a material without that correspondence. The arch-rock evaluator's
roughness/power difference remains real, but assigning that material to the
bright screenshot patch is not yet proven. A material-identifying capture or
reconstructed camera/geometry intersection is needed for that claim; more
specular guesses are not an alternative.

These limits distinguish missing observations from fields already available
in the tools. The investigation has not certified a corrected Battle Canyon.


### Further material-contract finding (2026-10-28)

The supplied shader implementations establish an additional mismatch even after
matching evaluated tint constants. Reach `shared_specular.hlsl_include` lines
51-59 blends albedo into the normal tint **before** Fresnel interpolation. H3
`two_lobe_phong_fx.hlsl_include` lines 43-50 blends albedo **after** interpolation.
With Fresnel weight f, albedo blend a, texture albedo A and tints N/G:

- Reach: `(1-f)*((1-a)*N+a*A)+f*G`.
- H3: `(1-a)*((1-f)*N+f*G)+a*A`.
- Their difference with identical fields is `a*f*(A-G)`.

The official arch-rock evaluators both report a=0.6. At grazing incidence
Reach tends to G; H3 still includes 60% of the per-pixel albedo. Thus matching
the tint/exponent fields does not establish matching reflectance. Constant
tints alone cannot reproduce this for arbitrary textured albedo at all angles.
This is a demonstrated semantic difference, not yet attribution of the bright
patch in the user's capture.

Reach's analytical branch directly uses analytical_power (evaluated 1.468),
while its area-light branch passes roughness (evaluated 0.5) to dual-vMF. H3
uses the view-interpolated 55/10 power for both its analytical and area terms.
Setting both powers to 1.468 would match one exponent while changing area
lighting; it is not a complete translation. The current arch evaluator lists
no environment-map sampler, so cubemap LOD edits are not a demonstrated remedy
for that specific material. Other rock materials require their own active-option
inspection. Source hashes and equations are saved in
`reference/reflectance-contract-comparison.json` under the rebuild work folder.

The same evaluator comparison narrows the issue per material: small rock uses
albedo blend 0.42 and no environment-map sampler; distant cliffs use blend 0
and a cubemap. The tint-order difference therefore affects the first two,
while it cancels for distant cliffs.

For distant cliffs the installed sources establish a separate, concrete
reflection-detail mismatch. Reach's per-pixel environment option uses
`max(0, (0 + (env_roughness_offset - 0.5)*2)*4)` outside PC DX9. The official
evaluator reports offset=1, giving LOD 4 for ordinary rendering (impostor
capture adds 7). Original H3's corresponding non-PC branch samples LOD 0.
Thus a direct cubemap copy preserves the image but not the selected blur level.
The H3 per-pixel option has no evaluated roughness-offset parameter; changing
material power cannot change that hardcoded sampling level. A source-derived
cubemap adaptation is a possible asset-only remedy, but has not been authored
or validated here. Do not add the MCC-only custom-map option to claim original
360 compatibility. These facts come from active option/evaluator correspondence,
not from attributing the screenshot to distant cliffs.

### Blocker origin differences verified from official authoring

When reusing H3 collision blockers for Reach Forge objects, compare the model's
physics shapes and local transforms, not just names or bounding spheres.
The Battle Canyon audit found ten matching stock box dimensions/radii/rotations
and fixed motion types, but Reach's boxes were raised above the object origin
while H3's were centered on it. Preserve authored placement by transforming the
source-minus-target local offset through the placement orientation and scale;
do not edit stock H3 physics to compensate. Verify render alignment separately.
A matching box does not prove equivalence for other shapes: Reach wall_s is a
polyhedron and remains unresolved. Reproducible evidence: Battle Canyon's
`audit_structure_blockers.py` and `forge/structure-blocker-audit.json`.

### Recompiled prop collision-material binding

A generic Reach-to-H3 model conversion can leave the H3 model material block
empty even when H3EK has correctly compiled collision geometry with named
materials. Before staging, reconstruct the model material bindings from the
compiled collision model, verify each global-material name exists in H3 globals,
and leave damage sections unassigned for nondestructible props. Verify render
shader references independently. Battle Canyon's blue-base rock and wall props
exercise this through stage_forge_map_props.py; runtime contact effects still
need checking after cache compilation.

### Scenario name-table references

When a rebuilt scenario omits the source object-name or editor-folder tables,
clear those indices on every copied placement type, including sound scenery.
Preserve references only when the corresponding table has actually been carried
over/remapped. Validate each nonnegative object-name index against the target
table before compilation. H3EK can clear stale indices while still producing a
cache, so successful compilation alone does not establish correct authoring.
Battle Canyon's combined compile exposed this on ambient-sound placements;
plan_objectives.py and verify_combined_scenario.py now handle and check it.

### Unassigned sound-scenery placeholders

Reach authoring may contain sound placements whose palette index is -1. Such a
record has no assigned audio asset. Omit these empty records when assembling the
H3 scenario, record the excluded source indices, and verify every assigned
placement against its original transform/playback fields after index compaction.
Do not map -1 to the final palette entry or relax native converter index checks.
Keep source-index-derived object IDs stable when removing empty records.

### Compiler-written lens function variants

When translating compiled H3 MCC lens reflections back to original H3, compare
function semantics rather than editor allocation bytes. A unit constant can
store its second bound as zero or one; accept only verified unit encodings.
Type8Section has three unused bytes following its opcode (see the local
TagFunction.cs Type8Section.Read reference). Do not require a particular debug
padding pattern in those bytes. Continue validating section length/count,
opcode and coefficients, and keep rejecting unsupported anisotropic scaling or
nonrepresentable curves. Battle Canyon's verify_flare_conversion.py exercises
padding variations and semantic-field mutation rejection against the compiled
candidate; this check does not replace visual validation.

## Forge light authoring and sphere export findings

Seven additional Reach Forge light colors use named halogram choices that map
to the existing original-disc Sandbox template `_2_1_1_0_0_0_1`. Verify actual
disc-template presence instead of assuming a shader supported by H3EK shipped
on Xbox 360. Keep source material parameters and compare complete animated
function bytes, not merely their sizes. MCC-only distortion/soft-fade choices
are off for these sources. Compiler-generated Reach postprocess routing must
be cleared for H3EK regeneration; never retain a partly truncated routing table.
The source bitmap sharpening setting is zero and has no target field.

The light functions preserve color, intensity and flashing. Reach's Inline
renderer selection/version, attenuation start distance and angular falloff
speed have no direct H3 authoring fields. Record these differences explicitly;
shared parameter equality is not evidence of identical rendered falloff.

The blam-tags sphere exporter read radius from the element root even though
H3/Reach authoring stores it at `sphere shape/radius`. This emitted zero-radius
JMS spheres and stopped the official physics compiler. The repository patch
`../battle-canyon-rebuild/blam-tags-sphere-export.patch` reads the nested radius
and translated-sphere center, retaining the older root-radius fallback. Apply
it to the local blam-tags checkout and rebuild blam-tag-shell before exports.
Verify output scale: 0.3 world units becomes approximately 30 JMS units, then
0.3 again in the H3EK-compiled physics tag. Do not substitute a polyhedron or a
nearby stock shape to hide an exporter error.

JMS does not retain the original rigid-body motion setting. The light markers
are fixed in Reach; H3EK initially creates box motion. Restore fixed motion
from the audited source and verify it after compilation, along with sphere
count, radius and center. Bind collision material `energy` to the existing H3
global material. The source's unused impostor is omitted (policy is never),
and H3 cannot encode Reach's phased-in-Forge object bit. These differences
remain in the object staging evidence. Neither compiler success nor bytewise
function preservation establishes native visual/Forge acceptance.

Check the final MCC-to-original-H3 stage as well: the specialized halogram
importer previously validated flashing functions but then froze them. For the
exact `_2_1_1_0_0_0_1` permutation with unchanged constant/texture ordering,
it now invokes the existing material-animation register mapper. That mapper
requires every function and route to be represented and rejects ambiguous
register matches. Animated sampler ranges remain explicitly unsupported on
this path. Read back the emitted native cache, including complete converted
function payloads, periods and nonempty routes; Battle Canyon's
`verify_forge_light_animation.py` records this evidence for both flashing
markers. Runtime flashing/falloff still needs visual verification.

## Stock lift menu reuse

Inspect every physics force region and its shape/material binding before
classifying a cannon as player-only or vehicle-capable. H3's Forge cannon
has a player region that ignores vehicles and a separate vehicle region
with nonzero force. Battle Canyon's `audit_stock_forge_lifts.py` records the
native polyhedron → material → phantom-type chain and authoring hashes.
The original H3 permanent lift is an equipment tag already used in the stock
scenery Forge menu. Preserve that object group; do not rebuild it as a crate
to satisfy a conversion helper's incomplete extension whitelist. Under the
stock-asset policy these choices retain H3 tuning and visuals, with differences
recorded explicitly. Menu replacement does not authorize retuning placed lifts.

## Evaluator prerequisites for inherited Forge materials

Recover referenced source bitmap tags before trusting evaluated sampler output.
Reach's `inspect-shader` can succeed while substituting default diffuse, normal
and detail textures for locally missing dependencies. Compare the evaluated
bindings against the authored child and its parent chain, not only the tool's
exit code. A missing reference in the original archive still needs an
active/inactive parameter audit; its presence in an unused authoring parameter
does not by itself require a replacement bitmap.

Forge panel children can contain -1 for every option, inheriting their actual
shader choices from a metal parent. Resolve inheritance and locks before
mapping category names into H3; treating -1 as option zero changes material
behavior. Battle Canyon's pending dependency inventory and 40 official Reach
evaluations provide reusable evidence for these shader families.

Parameter inheritance is finer than whole records: a child may supply only
UV animation for `detail_map` while the parent supplies its bitmap. Copying the
child record and discarding the parent reference loses that texture despite
byte-perfect animation preservation. Bind the evaluated inherited bitmap
explicitly, without clearing the child's animated parameters. In tagbridge,
use a reference-field override for this operation; bitmap-parameter overrides
are intentionally constant replacements and clear animation.

Reach's composite specular authoring also requires expansion into explicit H3
specular coefficient, specular tint and Fresnel color where the target does not
expand it. Compare official Reach and H3 evaluations after translation. For the
13 native-template-compatible Forge metal shaders, these corrections eliminate
all differences in shared constants and textures. This does not establish
equivalence of source-only roughness/Fresnel/environment/wetness calculations
or runtime appearance; retain those differences for separate shader analysis.

Reach glass is a distinct shader family, while original H3 can express glass
through ordinary shader permutations. Preserve the source render-method
authoring, explicitly select the H3 definition/options, and let official H3
tools regenerate postprocess data. Do not copy a glass-family option array
directly into an ordinary shader. Expand composite tint parameters into the
names used by the selected target material model; those names differ between
Cook-Torrance and two-lobe Phong. Preserve separate alpha functions, including
values above one, until the shader's own opacity calculation.

A missing exact native permutation can sometimes use an existing permutation
with an algebraically neutral extra input. Prove this from official HLSL and
the actual resource: a texture-driven specular mask equals an unmasked value
of one only when all sampled alpha values are one, including every mip.
Battle Canyon's Forge-glass staging verifies this for stock H3 `alpha_white`
and uses an existing Cold Storage template. Shared compiled constants/textures
match Reach, but this alone does not establish whole-shader equivalence.

Environment roughness controls are not interchangeable: Reach applies an
offset to roughness before choosing reflection LOD, whereas H3 multiplies its
derived roughness by a scale. Derive the intended LOD from the source values
and actual branch before mapping it. Preserve documented differences in probe
encoding/blending, light kernels, generated animation routes and wetness;
compiler success and equal parameter names do not resolve them automatically.

For object physics, distinguish compiled Havok core vertices from authoring
surface vertices. H3's physics compiler may shrink an already-shrunken exported
core again, and JMS export does not necessarily retain fixed-body motion.
Compare source/target shape arrays, dimensions, margins, transforms, body motion,
materials and constraints after compilation. Battle Canyon's remaining palette
audit found both problems despite all 87 geometry compile commands succeeding.
Restoring the margin through plane expansion recovers simple box-like hulls but
failed bounds checks for 17 of 43 convex-bearing models; it is not a universal
conversion recipe. Degenerate hulls and complex shrink behavior need explicit
handling. Bounds equality is necessary evidence, not proof of complete hull
or gameplay equivalence.

Physics JMS material labels also carry body scope. Do not repeat a physical
material name in the permutation/region slot: that can split one authored body
into multiple bodies or change region behavior. Derive named scope from source
rigid-body membership, traversing list/MOPP wrappers to leaf shapes; duplicate
JMS material slots where one local material serves several scopes. Verify named
node/region/permutation identities and leaf membership after official compilation,
then restore authored motion using that mapping. Global-material references are
separate tag metadata, not substitutes for local material identifiers or scope.
Avoid empty JMS name lines, which can shift parsing while Tool still exits zero.

A changed convex count does not necessarily mean lost collision: H3 may emit
a triangle primitive for a source three-point convex hull. Compare all shape
types and their body references. In the two Battle Canyon Forge bunkers, seven
such primitives retain their margin but shrink vertices toward their centroid
by one radius. Inverting that measured equation before official compilation
recovers the source triangle vertex sets; verify the actual compiled vertices,
radius and extrusion state. Keep this rule limited to the proven triangle case.
Long shape names can collide after compilation, so use geometry and ownership
as well as names when establishing correspondence.

Compare full-dimensional convex cores by mutual halfspace containment when
compiler output has different vertex lists: redundant vertices can disappear
without changing the surface. Matching AABBs is insufficient. Empty shape
arrays are not successful geometry checks. Check margins and body bindings
separately from core-surface equality.

After official physics compilation, restore explicit source global-material
bindings by verified local material identity. JMS local names do not preserve
these bindings automatically. Validate every nonempty destination name against
the actual H3 globals material table; do not silently substitute an unknown
Reach material. Preserve blank bindings and reject ambiguous same-local-name
mappings. Verify that this repair changes no geometry, motion or compiler-owned
physics fields. Battle Canyon's isolated repair restores 23 bindings, including
Forerunner metal, without treating that metadata repair as whole-model acceptance.

The official H3 physics compiler's measured convex shrink commonly operates
component-wise toward the AABB center, clamping each coordinate there, rather
than moving supporting planes inward. For an affected core, reconstruct
authoring coordinates as `p + radius * sign(p - center)`; preserve coordinates
at the center. Apply this only where original source-to-compiled measurements
establish that behavior, and preserve hulls proven unchanged by compilation.
Recompile and compare actual core surfaces and radii: Battle Canyon's first
37-model pass succeeds, including complex rock hulls. This does not authorize
the same treatment for triangle primitives or the remaining unmatched hulls,
nor establish correct body metadata or runtime behavior on its own.

Near-identical source coordinate planes can also destabilize official convex
construction: two Forge bridges lost a rail corner with only float-level plane
differences. A tightly bounded coordinate normalization before the measured
inverse recovered all six bridge hulls. Record every change and verify final
surfaces against the untouched source at the original tolerance; do not relax
acceptance or apply mesh-wide rounding without evidence. Combine geometry,
body-motion and material repairs only after checking their source/output hashes
and named body membership, and compare opaque MOPP data byte-for-byte when only
metadata is supposed to change.

For thin convex cores, a volume-hull construction failure is not itself a
geometry mismatch. Compare in the affine span when possible; mutual nearest
vertex distances also bound the Hausdorff distance between the convex sets.
This conservative fallback verifies unchanged near-planar cores without
inventing thickness. When compilation changes primitive type, carry the verified
source-to-target shape mapping into body-membership checks: comparing raw type
indices or truncated names would reject valid conversion or hide a wrong binding.

Check primitive rotations as well as dimensions. The folding chair's Reach
box matrices compiled transposed from exported JMS quaternions; conjugating
those quaternions before official compilation restores source matrices and
geometry. Establish the transpose relationship and verify all resulting box
transforms/radii; do not apply this correction blindly to convex vertices,
nodes, capsules or unrelated export paths.

Where the user has explicitly authorized collision simplification, distinguish
bounded accepted simplification from exact source reconstruction. Measure actual
surface deviation and volume change, preserve visible geometry, fingerprint the
accepted output and retain the discrepancy in the report. This can avoid
unnecessary repeated compilation for sub-margin rock differences, but does not
authorize simplification on other projects or broaden the user's permission.

For H3 render compilation, use lowercase shader-collection abbreviations and
inspect the resulting render model's actual material references. Tool can write
a render tag after reporting missing shader errors; file existence and exit zero
are not sufficient. Exported JMS can repeat one shader across permutation-scoped
material slots, so do not index a deduplicated dependency list by JMS slot index.
Preserve the slots and map their shader identities explicitly.

Do not let missing inactive shader-authoring references block conversion as if
they were sampled textures. Establish inactivity from the selected options and
official evaluated sampler list. The Forge base panel stores a missing separate
specular-mask bitmap while actually using diffuse alpha; clearing only that
stale reference leaves evaluated shared constants/textures unchanged. Record
the removal, retain the untouched source and continue rejecting missing active
inputs. A parameter's presence in an authoring block alone does not prove use.

When matching a shader's arithmetic, also match where each input comes from.
Reach primary-colored detail illumination and H3 constant-colored detail
illumination have the same texture product but different color bindings.
Official H3 render-method options demonstrate externally supplied object colors;
an isolated option can select that source without rewriting shader arithmetic.
However, original-H3 conversion must also establish the native shader's constant
register route. Merely changing the authoring option or importing a matching
fixed-color template does not prove dynamic object colors survive.

### Reusing compiled H3 illumination programs

For Reach primary-change-color illumination, compare evaluated shader equations
and routing rather than assuming the enum values correspond across engines.
The H3 detail-illumination program can receive primary object color through its
extern routing. In the Battle Canyon authoring adaptation, seven pass ranges
move the self_illum_color route from pixel constants to primary-color externs;
program references and unrelated routes are preserved. The extern enum is
resolved by name and read back, not copied numerically from a different schema.
A neutral gray detail texture preserves the one-texture illumination product
without halving an animated intensity. Preserve animation bytes and compare
actual official-tool evaluation. A successful MCC authoring template does not
establish the corresponding Xbox 360 register routing or runtime appearance;
those need their own native conversion and verification.

### Rigid-body metadata after official physics compilation

Match bodies by node, region and permutation identity after verifying shape
membership; compiler body indices can reorder. Compare all shared body fields,
not just motion and mass. The official H3 compiler can lose an authored local
center-of-mass offset even when the generated geometry and other metadata match.
Restore that field through the named vector schema and verify unrelated fields
and actual MOPP bytes remain unchanged. Preserve separate geometry evidence.

Do not infer semantic equivalence from nearly identical water-physics names:
Reach describes absolute AABB overrides, H3 describes AABB offsets. Zero/default
on both sides needs no adaptation; nonzero values require a geometry-aware
translation. Reach's extra per-axis inertia scales also need explicit review,
though the current Battle Canyon pending objects all use zero/default values.

### Disabled terrain layer dependencies

Resolve terrain material categories from official evaluated output before
chasing missing bitmap references. Reach Forge rocks have two active layers
and two explicitly disabled layers, but still retain bitmap names on all four.
The inactive names can include unavailable development-map assets. Clear only
the references belonging to proven disabled layers in an isolated source copy;
preserve active parameters and animation bytes. Match the H3 categories by name,
confirm a native compiled donor, and compare official H3 evaluated constants and
textures. This does not establish equivalence for Reach-only wetness fields or
replace the final native visual check.

### Shader inheritance includes animation subrecords

A child parameter record can replace the bitmap while inheriting an otherwise
empty animation block from the parent. Whole-record dictionary merging loses
UV scale and color in that case. Preserve complete parent function records when
the child supplies no animated overrides, then compare official evaluated
output. Parent lock presence alone also does not prove which value the compiler
uses: the tested chair and mine-light shaders evaluate to their child values.
Record exact exceptions from evaluated evidence; do not generalize an assumed
lock precedence to other assets. Duplicate names and partial nonempty animation
blocks require their own evaluation rather than silently dropping records.

### Simple prop vitality representation

Reach model damage info/maximum vitality does not automatically land in H3's
new damage info/body/maximum vitality. Inspect nonzero source values even when
conversion returns a valid model. For simple props with zero flags, no damage
subblocks and unassigned section links, create the native H3 damage-info row and
map vitality, indirect material and reporting enums by name. Preserve unrelated
fields and test native damage behavior separately. Complex section/response
models need fuller mapping; do not apply the simple-prop adapter to them.


### Distinguish missing authoring references from active resources

Before importing a missing bitmap or replacing a material, inspect the shader
with the official target Tool evaluator. Shipped authoring tags can retain dead
parameters pointing to absent development textures. Only clear such references
in staged copies when the evaluated shader does not use the parameter or bitmap;
retain all selected options, constants, and active texture references. Generated
postprocess blocks may name old templates and should be regenerated by the target
compiler, not treated as authored material intent. Authoring dependency closure
is not proof of native shader availability or appearance.

Search stock dependencies by semantic identity as well as exact source path:
Reach camping-stool material effects use a path without `havok`, while H3 places
the corresponding stock effects under that directory. Reuse the H3 effects and
its dependencies rather than converting Reach sound/effect content unnecessarily.


### Reuse converted Forge objects across maps

User instruction, 2026-10-28: preserve completed Forge object conversions for
future maps rather than repeating the export, physics, material and metadata
work. Consult `tools/reach-forge-library/README.md` and verify `catalog.json`
before converting an object again. Reuse matching source/dependency identities;
keep map placements and menu settings separate. The catalog records hashes and
paths without duplicating assets. Protect its artifacts and correction evidence
from routine cleanup, and keep native-unverified objects visibly unverified.

Missing authoring attachments can also be stale: Battle Canyon's two Reach
crenellation objects reference absent ext.light files in HREK, but the original
compiled Reach map retains the three attachment records with null light datums.
The staged conversion now matches those null references while preserving markers
and all other object fields. Use compiled tag-field evidence, not missing name
strings alone, before making this kind of correction.


### Official H3EK list-child physics serialization

MCC child-shape records are 32 bytes; original H3 records are 16 bytes.
PhysicsModel.ListShape identifies a platform-width shape reference followed by
CollisionFilter, ShapeSize and NumChildShapes. Preserve the latter three fields
at their target offsets. Official H3EK output can leave arbitrary contents in
MCC's final 12 bytes, including fragments of UTF-16 names and old geometry data;
these bytes have no target storage and must not be treated as required zero
runtime pointers. Continue rejecting the shape pointer's nonzero high word.
`model_physics.py` handles this conversion; `test_model_physics.py` verifies
compiler-tail omission, preservation of meaningful words and pointer rejection.
Battle Canyon evidence: `forge/remaining-objects/mcc-child-padding.json`.


### Native primary-color emission routing

For Reach change-color detail emission authored through the custom H3EK primary
option, use the native H3 detail-emission shader program rather than trying to
find the project's custom template name on disc. `forge_primary_color.py` clones
only the native template routing: self_illum_color moves from pixel real constants
to extern pixel real constants, retaining its register/component mask and using
H3 change-color-primary extern 14. Other routes, shader programs and constants
remain unchanged. Derived templates are shared per donor. The adapter rejects
ambiguous/missing registers and packed-route overflow. Focused routing tests pass;
native visual verification is still required. This is map-data conversion, not an
engine change. The initial supported permutation is _0_2_0_1_1_2_5_0_0_0.


Triangle physics uses a 144-byte MCC record and a 128-byte original-H3 record.
The shared converter now maps fields by the paired layouts, including the
welding settings and all vertex/extrusion components. The pre-PointA alignment
gap has no authored fields and is zeroed in the output. Runtime pointers remain
required-null. Triangle user data is a self-offset: compiled covered-bunker rows
use 0, 144, 288, etc.; convert it to 0, 128, 256, etc. for the retail stride,
rejecting nonintegral source offsets.
Global material resolution follows the same mapping as other shape types.
The focused test checks coordinates/welding fields at their target offsets and
rejects a populated 64-bit runtime pointer.


### Diffuse-alpha blending and redundant specular masks (2026-10-28)

Official Reach `shaders/shared/blend.hlsl_include`,
`calc_alpha_blend_opacity`, initializes opacity to albedo alpha and specular
scale to one; `albedo_alpha_without_fresnel` bypasses further modification.
Official H3 `shaders/blend_fx.hlsl_include` outputs albedo alpha for alpha
blending. H3 `material_models_fx.hlsl_include` enables BLEND_FRESNEL for
glass only. Therefore the dice-hole Cook-Torrance material can omit Reach's
separate blend-source category without adding a Fresnel transparency effect.
This is not a blanket permission to omit that category on other modes.

Reach specular_mask_mult_diffuse multiplies diffuse alpha by mask alpha.
The dice-spec BC1 bitmap has alpha one in all nine stored mip levels (checked
from block endpoints and indices), permitting exact reduction to H3's
specular_mask_from_diffuse. RGB contents are not the mask channel.

Official H3 evaluation of dice-hole and land-mine-light now succeeds with no
differing shared constants or shared texture bindings. Reach-only constants
remain separately reported. Neither exact original-H3 native template was
found in the installed map inventory: authoring success does not establish
native compatibility. Evidence: Battle Canyon forge/prop-materials
authoring-plan.json, native-template-inventory.json, and
h3-evaluation-comparison.json. The evaluator's explicit
--include-unavailable-native option permits this diagnosis but records
native_template_available=false; it does not authorize deployment.


### Native shader substitutions must preserve side effects (2026-10-28)

H3 self_illumination_fx defines from_albedo as emission = albedo * color *
intensity, then explicitly zeros the inout albedo. Simple and detail illumination
return emission without zeroing albedo. Thus matching emission RGB alone does
not preserve the final lit surface. Nor is globally setting diffuse_coefficient
to zero equivalent: the separate dynamic-light entry does not call the
self-illumination function. Any donor substitution must account for each entry
point, not only its method name or static preview.

The Battle Canyon audit nearest-native-programs.json enumerates native donors
within two category changes. Land-mine light has donors differing only in
illumination (off, three-channel, detail, simple), but none is automatically
equivalent. Dice-hole has no donor within one category change; nearest options
also alter blending, parallax, masks or lighting. This evidence narrows the
translation work without authorizing silent feature removal.

Reach portable-shield scenery has two damage sections, recharge, functions and
attachments. The H3 Zanzibar battle_shield crate does not have the corresponding
damage model. Similar naming is insufficient to select it as an equivalent.
See forge/prop-materials/portable-shield-stock-object-audit.json.


### Reach Forge land mines (2026-10-28 implementation of stock policy)

Use original H3's deployed tripmine for Reach's Forge land-mine hazard entry.
Distinguish the deployed `objects/equipment/tripmine/tripmine.equipment`
from its pickup shell `tripmine_equipment`: they are different native objects.
Retain H3 behavior and tuning rather than converting Reach mine shaders,
geometry and detonation rules. Verify an actual original-map donor; an H3EK
authoring file alone is insufficient (tripmine_permanent was not in the
installed original-map inventory). Record the behavior substitution and test
Forge placement/arming. This implements the existing user stock-asset rule,
not an exception allowing arbitrary replacements.


For Reach portable-shield Forge choices, the original-H3 deployable cover is
the stock counterpart under the same asset policy. Use the deployed native
object, not the equipment pickup, and preserve H3 behavior. The multiplayer
variant expires after 30 seconds; document that difference from Reach's
persistent shield and verify Forge placement. Do not confuse the Zanzibar
battle_shield crate with a functioning energy shield.


### Forge menu completeness checks

A complete reference palette is insufficient: retain the source scenario's
Forge spending budget and verify actual object placement. A newly authored
H3 scenario defaults to zero and can show every entry while refusing creation.
Track this separately from engine object limits and physical memory.

Verify every menu label against the native sandbox UI's locale table, not
only string-ID presence or a fixed list of custom names. Import missing
authored localized strings after ID relocation; stock donor menu names can
also be absent from the chosen destination map.


### Forge counterparts: use the native editor-supported object

A stock deployed effect object is not automatically a usable Forge menu item.
Battle Canyon run `20261028-224642-34528` created H3 `instantcover_mp`,
but it produced no saved variant placement and no visible usable cover. Its
multiplayer-object block is empty. The conversion now uses the stock Forge
Deployable Cover pickup, retaining its normal collection, activation and
30-second deployed shield behavior. Do not modify stock gameplay or add
editor hooks to force a deployed effect into the palette. Check actual native
Forge donors, persistence and visible placement independently of tag existence.
The absent metadata is a lead, not proof of the visual failure cause.


### Surface fallbacks can hide emission and animation loss

A renderable generic opaque material is not proof of material completion.
Compare actual source animation tables and required sampler/constant names
against the emitted material. Powerhouse's falling-water fallback emitted zero
animations and dropped blending; other fallbacks omitted lamp/screen emission.
Check active BSP/model part usage before deciding impact. Prefer an equivalent
shipping H3 material and its native behavior; otherwise adapt the unsupported
material explicitly. Preserve authored geometry and inspect the real native
output. Brightness changes do not replace missing emission or transparency.

### Missing shader permutations: native Xenos compilation investigation

Installed Xbox360 fxc can compile the retained Halo Online shader-reference
source into Xenos programs (Powerhouse:13 splash entry points). This is not
yet a supported import path. Compile success does not prove H3 persistent
registers, vertex/pixel interface, extern bindings or render targets match.
Keep source identity and macro definitions pinned; audit those interfaces,
construct native pixl/rmt2 routes and verify actual rendering before reuse.
Opaque/additive native shader pairs have different compiled programs; changing
only a material blend integer is not a faithful permutation conversion.
See POWERHOUSE.md and work/powerhouse/shader-toolchain/status.json.


### Reach Forge dice: approved normal-map adaptation (2026-10-29)

The user approved retaining the dice, its textures, normal-mapped pips and
physics while omitting view-dependent parallax depth. Apply this to reuse of
this dice object, not to arbitrary Reach materials. The pip material retains
alpha blending; do not replace it with an opaque square. The source
environment-reflection contribution is constant zero and may be eliminated
without changing its visible contribution. The conversion checks the exact
constant function and official Reach evaluation before selecting the original
H3 no-environment, no-parallax alpha-blend shader. Runtime appearance still
requires verification.


### Dice disposition update - 2026-10-29

The user subsequently requested omitting the dice from Battle Canyon. Exclude
it from this map's Forge palette and compiled dependency closure. Retain the
normal-mapped, parallax-free conversion as unfinished reusable reference work;
its failed native appearance check is not acceptance. This omission is not a
blanket instruction to remove dice from every future Reach conversion.


### Original H3 lens reflection layout correction (2026-11-02)

The vendored original-H3 lens schema had incorrect offsets in its 48-byte
reflection record. Original executable `sub_82471B78` reads the bitmap image
index as a halfword at +4; `sub_82472380` reads rotation as a float at +8.
Preserve flags at +0, padding at +2/+6, bitmap index at +4, rotation at +8,
radius at +12, brightness at +20, modulation at +28 and color at +32.
Do not pack MCC axis offset into this record: nonzero values now require
separate research rather than silent corruption. Both generic and specialized
sun-flare writers use the corrected layout. Existing generated maps must be
rebuilt before they benefit. This is a cache conversion fix, no engine patch.

Battle Canyon rainbow rotation 90 degrees was previously written at +4,
causing image index 0x42b4 (17076) from a one-image bitmap. GPU draw trace
20261102-220627-28408, draws 2913/2914, uses the lens shader but retains all
six sampler words from preceding world draw 2912: a 256x256 format53 texture
instead of the rainbow's 128x128 DXT1 texture. This explains the cyan symbols.
All 41 compiled flare records pass conversion, with nonzero image-index and
90-degree rotation regression checks against the executable's offsets.
Native visual acceptance is recorded separately in the Battle Canyon notes.


### Native H3 emitter offset evaluation (2026-11-02)

Original executable `sub_821537F0` resolves the 752-byte emitter definition,
calls `sub_82153C20` once before its emission-count loop, then calls
`sub_82154138` for each new particle. `sub_82153C20` evaluates the translation
property at emitter +24 through `sub_82153E60`, interpolates the two Cartesian
endpoint vectors at property +32/+44 and stores the result in the emitter
instance at +28. The individual particle setup `sub_821546F8` selects the
shape using the emitter +4 byte and does not reevaluate that +24 property.
Thus a line emitter with a particle-random translation cannot be assumed to
sample an independent perpendicular coordinate for each spawned particle.
The previously suggested shortcut is not established by the schema's input
enum; this native call order is evidence against that proposed implementation.

Evidence: Battle Canyon `placed-effects/native-emitter-code-index.json`,
`native-emitter-transform-82153C20.txt`, `native-particle-spawn-82154138.txt`,
and `native-emission-821546F8.txt`, extracted read-only from generated original
executable functions. No emitter authoring or engine change was made.
The three source plane emitters remain unresolved; retaining sprayer defaults
is still not an accepted shape conversion.


- User decision, 2026-11-03: omit Battle Canyon's three unsupported ambient
  mist/drip plane emitters rather than approximate them with H3 line emitters.
  They belong to ca_bc_mist (two emitter layers) and ca_beaver_dripping_point
  (one emitter), occurring in eight effect-scenery placements in total. Preserve
  the rainbow, sun flare and laser effects. This omission is specific to these
  Battle Canyon effects; it does not authorize stripping other maps' atmosphere.


### Final bake and deployment handoff (2026-11-03)

Reusable lesson from Battle Canyon: the working kit scenario may lag behind
the combined scenario used for cache compilation. Bake the reviewed combined
scenario and its dependency overlays, not whichever scenario happens to be in
the kit. Hash the staged scenario before invoking the official lightmapper;
record the quality, farm dataset, worker count and result hashes. Keep the
same overlay active through the subsequent official cache compilation.

`tools/battle-canyon-rebuild/compile_forge_candidate.py` implements this
transaction for Battle Canyon. It backs up existing overlay targets, prior
cache and top-level lighting files before mutation. Successful lighting is
retained for future compiles; temporary scenario/dependency overlays and prior
kit cache are restored. On failure, existing backed-up inputs are restored.
The current wrapper does not promise removal of every newly generated lighting
file on failure; inspect the failed transaction before retrying. Do not run
another authoring mutation or compile against that kit while the transaction
is active. A stale manifest alone is not evidence that workers have stopped.

A queued continuation must wait on the exact live process handle, require
successful exit and restored overlays, then match bake/compiler scenario
hashes and the compiled cache hash before conversion. Successful compilation
is separate from native acceptance: inspect actual lighting, retained effects,
geometry, traversal, audible behavior and measured frame pacing. Use only
process-local input and native captures. Avoid timing measurements while the
lightmapper or another game is competing for resources.

For DLC, validate both the assembly-slot candidate and the renamed DLC cache.
The existing `build_dlc_payload.py` changes header identity, scenario map ID,
checksum and header authentication. Preserve the existing menu preview assets
and other bundle members. Recheck current installed hashes before replacement,
especially when another chat is working in the shared installation. Use atomic
replacement so rollback/hardlinked fixtures retain their old data. A map-only
update does not require redeploying host binaries or overwriting bootstrap
settings. Record the accepted source/native/DLC hashes and precise test scope.

Keep file size and resource accounting distinct from resident memory usage.
A PC gameplay pass does not by itself certify the console's total 512 MiB
budget or PC-to-console system-link behavior.

### Native bitmap names do not prove resident pixels (2026-11-03)

Before reusing a native bitmap for a runtime sampler, check its zone resource control and referenced page. A same-named target tag may retain editor metadata after its pixels were stripped; do not infer that the engine creates a default texture from an invalid resource handle. Search original-disc donors for intact resources and preserve their native data before considering custom recovery. Keep actual render targets/generated textures separate from this check. Powerhouse linear-gray recovery is deliberately scoped to the audited static1x1 ARGB32 linear texture; Armory supplies the exact source-matching texel. See snapshot/reference/powerhouse-native-gray-evidence-137.json.

### Native view-dependent material validation

For subtle parallax, preserve authored height inputs and inspect every requested native frame. Distinguish perspective from material motion using source geometry and the actual native draw projection, with a nearby parallax-disabled control. Observer FOV alone may not reproduce the game projection. In Powerhouse143/145, an FOV-only model produced a common3.5pixel residual on both surfaces; live GPU VS c0..c3 removed it, revealing window motion consistent with the unchanged source formula. Treat numeric registration as supporting evidence alongside inspected native content, correct resources and source parameter fidelity. Do not amplify production effects merely to pass a test. See snapshot/reference/powerhouse-window-parallax-evidence-145.json.


### Preserve authored vertex RGB through JMS (2026-11-03)

A valid JMS geometry export can still lose vertex colors. The installed blam-tags
read_vertex path sets color=None, which its writer serializes as zero RGB. Check
the original raw vertex color fields and the compiled H3 vertex stream whenever
a source mesh uses vertex-color lighting. Match vertices by geometry/UV rather
than array ordinal because the official compiler may reorder them. Battle
Canyon sky repair restores all 3683 nonzero original colors among 6577 vertices,
then verifies every RGB float in the native GPU resource. Its postprocessor and
upstream patch are under tools/battle-canyon-rebuild. Preserve geometry, material
bindings and sky-light records independently; matching bounds alone cannot
establish sky appearance. This finding is separate from exposure calibration.


### Imported DMR replacement and Forge deduplication (2026-11-11)

The exact imported weapon `priception\objects\weapons\rifle\dmr\dmr`
resolves to the original Halo 3 Battle Rifle and its full native dependency graph.
Do not retain custom DMR gameplay tuning or override the stock BR HUD labels.
When the authored Forge weapon palette already contains the stock BR, remove
that redundant DMR row instead of exposing two BR entries or a misleading DMR
label. Preserve all other authored rows, prices and limits. The alias and label
guard are shared conversion rules; Sky Bridge supplies the source-palette
regression check. Existing accepted caches can redirect the scenario reference
without relocating unrelated data; retain simulation wire indices and verify
all other bytes except checksums. See `../map-review/POWERHOUSE-BATTLE-RIFLE.md`
and `../map-review/SKY-BRIDGE-BATTLE-RIFLE.md` for map-specific evidence.

### Native resource-header layout and console cache limits (2026-11-12)

Repacking the `play` resource pages also invalidates the stock optimized
resource-header layout. The original Mythic loader's `82203C58` returns that
layout only when cache-header byte `0x142` is set. `8222C818` reconstructs pages
from the structure at `0x49C`: count at `+18`, starting resource IO offset at
`+20`, codec GUID at `+24`, then 28-byte records at `+40`. Each record's first
word packs compressed length in the upper 30 bits and flags in the low two;
the second word is decoded length, followed by a 20-byte salted hash. Page
offsets advance by compressed length rounded up to 4096. The same structure
also retains the basis map's optimized zone masks.

Do not leave this alternate layout enabled after changing the underlying
resources. `MapBuilder.finish` now clears byte `0x142` before recomputing the
header hash, selecting the current native `play`/`zone` tables. This changes
map data, not the executable. The 3longation repair candidate changes only
this byte and its salted header hash; its map body is byte-identical. The
original enabled records in that map reproduce a decompression failure and
a hash mismatch. Evidence is in `work/elongation-console-diagnostic/`.
This establishes a file defect, not observation of the console's failing branch.

The console export must also honor the original cached-file size gate.
`82206388` permits at most `0x09600000` bytes (150 MiB) for multiplayer maps;
`82206030` gives cache slots 3..12 the same capacity. When caching is unavailable,
the first function relaxes the limit to INT32_MAX. The host runtime deliberately
leaves `cache0:` unmounted, so its successful direct-file loads do not prove
this gate or the cache-copy path. The per-map console exporter now checks sizes
before creating output. Passing this check does not establish total memory
residency, console loading, gameplay, or network compatibility.

### Lossless console-size repair audit (2026-11-12)

Do not equate all resource-table entries with active gameplay dependencies.
A conservative dependency audit can identify obsolete basis assets after a
Forge palette replacement. Start from native header globals, retain opaque
tag groups, traverse full schema tag references, and preserve every unnamed
import as an additional root when names/provenance are incomplete. Residency
owner/resource bitsets and the simulation definition catalog are bookkeeping,
not independent evidence that an otherwise unreachable asset is used. Review
saved-layout and dynamic references before removal; a graph report alone is
not runtime acceptance.

The Forge Gulch candidate retires 309 unreachable named basis tags while
preserving every unnamed import, all retained tag indices and virtual addresses.
Only retired tag-table rows, retired resource locations, corresponding manifest
bits, and local page offsets/unused descriptors change in metadata. Compressed
retained-page bytes are compared exactly, then independently decoded and checked
against their CRC and three salted hashes. Identical compressed pages share
one stored copy without changing resource/page indices. This reduces its cache
from 182124544 to 146726912 bytes, below the 157286400-byte gate. This is a
map-only candidate; native host and hardware results belong in its manifest.
See tools/map-review/compact_gulch_console_candidate.py and
work/elongation-console-diagnostic/gulch-protected-unused-tags.json.

Do not assume a new sibling resource file in a LIVE package will load: native
82205C70 resolves shared filenames against 15 already registered cache-header
slots, and 821C1C60 requires that lookup before opening the resource source.
No arbitrary companion-file registration route has been established. Original
shared.map must remain unchanged.


## Direct Reach 360 cache to Halo 3 360 cache (ReachPort, 2026-11-21)

A second route alongside the authoring pipeline above: Reach retail Xbox 360 map files converted directly into
original Halo 3 Xbox 360 caches by the ReachPort feature in Assembly (no MCC tools). Implementation, commands
and Reflection's details: [tools/reach360-port/README.md](../reach360-port/README.md). The scope rules, the
reusable user decisions and step 5 of this document apply to this route unchanged.

**Documented baseline (user instruction 2026-11-21).** Follow the human-written documentation; where it has a
gap, stop and report. Reading Reach: Reclaimer (Gravemind2401). Converting Reach into a Halo 3-family engine:
TagTool (TheGuardians) - only TagTool, not values taken from its outputs. TagTool targets Halo Online
(ElDewrito, with Reach compatibility patches), so its engine-specific steps (Reach compatibility flags,
generated shader templates, per-mesh MOPPs, sky drawn regardless of cluster sky index) do not carry to 360 and
are gaps to report. A finished TagTool conversion (ElDewrito "Reach Advanced Multiplayer") may be used to compare
output, never as a source.

**What is converted.** The map: structure, collision, culling data, lighting, materials, sky, scenery and
placements. Gameplay is stock Halo 3: Reach weapons, equipment (armor abilities included), vehicles and bipeds
are not converted; placements use the per-map table of verified stock assets; other references are cleared and
listed in the build's unresolved report. Reach audio and animation are not converted until a stock-reuse audit or
a documented conversion is in place; their references are listed, not silently dropped. Forge palettes are the
basis map's stock Halo 3 sandbox blocks.

**Reusable findings.**
- Vertex formats (world, rigid, rigid compressed 0x1C/UDecN4), instance mesh and compression indices and index
  ranges agree with Reclaimer; normals and tangents use the same packed encoding on both consoles.
- Shader float constants: Reach names the four floats "Constant a/b/c/d", Halo 3 "Constant" + "Constant w"; a name
  matcher drops them and every surface renders black. Carry the span as floats.
- Static per-vertex lighting (Reach 6-byte VMF records) and instanced-geometry light probes need TagTool's VMF ->
  SH conversion (VmfConversion); raw copies read as garbage. Halo 3's per-vertex entry links Reach's "Vertex
  Buffer Index Reach"; cluster per-vertex links are kept alongside the lightmap image.
- Shader animation routing follows TagTool's ShaderFunctionHelper: routing entry = register, template parameter
  index, function index; one pass per valid entry point of the Halo 3 template. Copying a template's routing reads
  past the shader's function list and faults the game.
- A structure pairs with its lightmap BSP by index in the scenario lightmap's Per Pixel references, not by name
  (Reflection's third structure pairs with an unnamed Lbsp). A lightmap BSP without render meshes leaves the
  structure's own geometry in place.
- Reach-only shader groups take TagTool's documented stock default (rmgl -> a stock glass rmsh); copying a stock
  tag between Halo 3 maps carries its bitmap resources the way Assembly's "extract with resources" does.
- Atmosphere (sky_atm_parameters) is generated from Reach's atmosphere globals and fog with TagTool's code and its
  Postprocess step, not translated from Reach's tag.
- Halo 3 never clears its colour targets; screen areas no geometry covers show stale frames. A missing sky shows
  this way.
- Culling can be checked with the debug wireframe switch of the separate probe build
  (tools/reach360-port/debug): a camera outside every cluster draws the whole map, so a "no culling" view usually
  means the camera is outside the level.
- Props, invisible walls and spawn objects are stock Halo 3 objects (user 2026-11-22: "Stage 2 being Halo 3
  props/objects/invisibles was always the mandate"): each Reach object is matched to a stock Halo 3 object of
  the same object kind in the map's cfg (`object` lines); Reach props with no Halo 3 equivalent stay as still
  scenery, so Reach physics models are not converted. Game-mode marker props are replaced by the Halo 3
  game-mode objects the scenario rules create. Ambient fish are removed. A Halo 3 equivalent of another object
  kind (Halo 3 sandbags are scenery, Reach's are crates) needs its placements moved between palettes.
- Copying a stock tag between Halo 3 maps must take only its own resource bytes, never the donor's whole
  resource page (stock pages hold many resources; one is 93 MB). Halo 3 loads a map's required resources in
  index order within a fixed budget and silently skips the rest, which later shows up as a null read.
- Each structure BSP needs its own BSP zone in the zone tag (BSP reference plus Default / Static / Dynamic
  manifests); a basis slot such as Guardian has one.
- Reach soft kill volumes ("don't kill immediately") are left out: Halo 3 has no soft kill and would kill on
  contact. Hard kill volumes are kept; safe volumes are cleared as TagTool does.
- Render method definitions the basis map lacks (Reach shader_custom -> Halo 3 "shaders\custom", foliage, water)
  are copied from the stock map that has them, with their templates; otherwise those surfaces are silently skipped.
- Halo 3 draws a cluster's instanced geometry only from the cluster mesh's instance buckets; build them with
  TagTool's ConvertInstanceBucketsReach (cluster -> instance groups -> instances) plus overlapping instances, and
  key cluster instanced-geometry MOPPs by instance index as stock Halo 3 does.
- Halo 3 draws only the structure BSP the camera is in; Reach draws every active BSP. Reach maps that keep
  their shell, roof or distant scenery in separate BSPs (Reflection's 000 and 001) need those BSPs folded into
  the playable one. Open design item.
