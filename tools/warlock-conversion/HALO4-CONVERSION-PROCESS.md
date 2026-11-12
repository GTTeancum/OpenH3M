# Halo 4 authoring to original Halo 3: WIP process

Started 2026-11-04 by explicit user direction. The first map is **Haven**.
This is a working specification, not a claim that an H4-to-H3 conversion has
already succeeded. Map-specific inputs and evidence belong in [HAVEN.md](HAVEN.md).

**Status, 2026-11-04: on ice at the user's request.** The Haven pilot and this
workflow remain incomplete; no conversion is visually accepted. Documentation
is preserved for a future explicit resume. The user's outstanding priority is
texture/material fidelity. Base/normal bitmap presence and a few working unlit
surfaces do not establish complete H4 texture-layer conversion. In particular,
the current draft leaves source specular/control texture inputs and their
gloss/reflection channel semantics unfinished. Do not treat the temporary
emission/diffuse diagnostic shaders as deliverables or continue lighting work
in place of that priority. See HAVEN.md for candidate4–6 results and the shelved
density investigation; no new bake followed those diagnostics.

## Direction and reusable foundations

Use the official Halo editing kits and documented community tools for as much
of the conversion as possible. Do not manually rebuild the map, replace the
asset exporters/compilers, or start another direct H4-cache-to-H3 converter.
Automation may orchestrate existing commands and supported authoring APIs,
configure documented authoring properties, inventory outputs and verify them.
An unsupported feature is an explicit issue, not permission to fabricate a fix.

Reuse the structure and evidence discipline of
[REACH-CONVERSION-PROCESS.md](REACH-CONVERSION-PROCESS.md). Current successful
unmodified tool setup and H3 authoring commands are documented in
[the fresh stock-H3 preflight](../stock-h3-audit/SOURCE-PREFLIGHT.md).
The deleted/rejected Battle Canyon implementation is not an input. The
Battle Canyon-specific approval sequence, scenery omissions, lift tuning and
other exceptions do not automatically become Halo 4 rules.

The intended path is:

1. Official H4EK editable tags and source evaluation.
2. Unmodified Foundry import into a derived Blender scene, preserving metadata.
3. Existing Halo Asset Blender Development Toolset H3 authoring/export route.
4. Official H3EK geometry import, tag authoring, lighting and MCC cache build.
5. Existing H3 MCC-to-original-H3 pipeline and original stock/shared asset reuse.

Tool support for both ends does not prove every transfer in this chain. Each
boundary needs its own evidence. No working one-click H4-to-H3 path is claimed.

## Prerequisites and versions

| Component | Current evidence | Status |
| --- | --- | --- |
| H4EK, Steam app 1695792 | User installed to Z:/SteamLibrary/steamapps/common/H4EK; Steam build 11571341, tool build 2023.06.27.176405.1-Release | Binaries copied and hash-verified in work/editing-kits/h4ek; official tag API read passed |
| H3EK, Steam app 1695791 | Installed at D:/SteamLibrary/steamapps/common/H3EK; repository work/editing-kits/h3ek already exists | Reuse existing kit; pin executable/source archive hashes before authoring |
| Blender | Existing 4.5.8 LTS retained; isolated portable 5.2.3 LTS added under work/halo4-to-h3/upstream | Separate profiles/dependencies; portable ZIP SHA256 723f08a4401502561eb763cdeacf8745b31e5f3f154d287d3830d97cf75dc2fb |
| Foundry | Existing unmodified 1.1.61, revision 5dc085e4432b6b57b2bf97e02a442ecc6edc985f; released 1.9.19 staged separately | Released tool imports Haven lights/Havok; 1000 source instance transforms match |
| Halo Asset Blender Development Toolset | Existing revision 81e86bf98aee4607a2159ff9a22a223a1a91c9d7 | Full Haven BSP ASS geometry export/readback passes; native shader/collision semantics pending |

Released Foundry 1.9.19 requires Blender 5.2/Python 3.13, while the older pinned
source declares 4.5 support. Do not mix incompatible add-on versions.
The release ZIP was obtained from the author's extension catalog, verified
against its SHA256 (37f58c067c997a565608e06c79c9b59ff0c54502bc74661b49d32fb6d29f3c3c),
and extracted separately. Install its bundled wheels into an isolated 3.13
dependency directory; do not reuse Python 3.11 binary wheels. Blender provides
NumPy; the six release-bundled wheels were installed offline with --no-deps.
Record both package manifests under work/halo4-to-h3/upstream-research.
The pinned importer exposes scenario/BSP/object/decal imports and an H4/H2A
material path. Its Reach lighting import does not establish equivalent H4
support; the concrete limitation below must be resolved against the real source.

Primary references checked 2026-11-04:

- [Official H4EK Steam page](https://store.steampowered.com/app/1695792/Halo_4_Mod_Tools__MCC/).
- [Official release instructions for H4 tools](https://support.halowaypoint.com/hc/en-us/articles/11067636381716-Halo-The-Master-Chief-Collection-MCC-Update-December-2022).
- [Official tool and source-archive overview](https://learn.microsoft.com/en-us/halo-master-chief-collection/general/overview-tools).
- [Official known issues](https://learn.microsoft.com/en-us/halo-master-chief-collection/general/knownissues).
- [Foundry upstream](https://github.com/ILoveAGoodCrisp/Foundry) and
  [pinned version](https://github.com/ILoveAGoodCrisp/Foundry/tree/5dc085e4432b6b57b2bf97e02a442ecc6edc985f).
- [Halo Asset Blender Development Toolset](https://github.com/General-101/Halo-Asset-Blender-Development-Toolset/tree/81e86bf98aee4607a2159ff9a22a223a1a91c9d7).
- [Foundry author's release catalog](https://iloveagoodcrisp.github.io/Foundry/api/v1/extensions/index.json).
- [Blender 5.2 releases](https://download.blender.org/release/Blender5.2/) and
  [official Windows portable-install instructions](https://docs.blender.org/manual/en/5.2/getting_started/installing/windows.html).

## Confinement and source handling

Steam installations and existing game sources are read-only inputs. The user
controls Steam installation; bringing up the requested store page does not
authorize unattended external installation or edits to the Steam library.
After installation, inventory the shipped archive and binaries before selecting
the required files for a repository-local kit workspace. Do not extract a full
kit blindly: measure required size and free space, then include the actual
dependency closure. Keep original archives unchanged and hash selected inputs.

Use work/halo4-to-h3 for task evidence and work/editing-kits for reusable kit
workspaces. All derived scenes, tags, data, caches, profiles, logs, captures and
backups stay in this repository. Set TEMP/TMP, APPDATA/LOCALAPPDATA and Blender
profile paths before executing tools. Verify the kit's own log/output roots;
running an external tool with a repo cwd alone is not proof of confinement.
Do not modify the active H3 source workspace used by another map: use distinct
tag/data namespaces and coordinate any shared-tool changes.

Foundry's tag wrappers are not inherently read-only: their default permits
creating a missing tag and saving it on context exit. Its TagImportMover copies
out-of-project inputs into the active project's tags/_temp directory. Configure
a repository-local H4 project and import from a disposable authoring copy inside
that project's tag root. First inventory existing dependencies through explicit
official TagPath/TagFile.Load calls; fail on missing inputs rather than accepting
new empty tags. Record source and working-tag manifests before and after import,
including newly created paths. Do not point the importer at the Steam tag tree.

No desktop/UI automation, host input or capture app. Use documented command-line
tools, background Blender and supported APIs. Leave interactive editors and
human playtests to the user. Unattended game tests are process-local and bounded
to 180 seconds. Keep native image evidence sparse.

## Five evidence checkpoints

| Checkpoint | Required evidence |
| --- | --- |
| H4 authoring | Exact source scenario/BSPs, dependency closure, materials, placements, effects, lights, collision and helper volumes through the official API/tool readers |
| H4 evaluation/import | Effective material options/defaults and imported scene inventory; units, axes, transforms, UVs, normals, face flags and instance relationships |
| H3 authoring | Supported H3 representation for each active feature; preserved geometry/placement and documented stock gameplay/donor choices |
| H3 compiled output | Actual compiler logs and serialized geometry, collision, material/texture bindings, visibility, lighting and resource use |
| Original H3 output | Existing converter checks, native assets/formats/budgets, loading and sparse actual visual/performance evidence; scope limitations recorded |

For every translation record source path/hash, active use, authored and effective
values, units, target representation, tool commands/version, output evidence,
any lost fields or approximation, and unresolved runtime questions. A warning-
free exit or matching bounds alone does not establish faithful conversion.

## H4-specific questions to resolve through tools

- **Materials:** the pinned Foundry H4 path uses material tags rather than the
  Reach shader path. Inventory the actual H4 material definitions, functions,
  texture/channel packing and effective options. Do not transplant Reach shader
  enum numbers, presume identical parameter meanings, or copy H4 shader programs.
- **Geometry:** compare every imported mesh/instance with the official source
  inventory. Establish units, axes, normals/tangents, UV channels, material IDs,
  render-only/collision-only faces, portals and structure-design helpers. Use
  existing exporters; escalate a concrete unsupported case instead of writing
  replacement geometry generation code.
- **Lighting and atmosphere:** inventory sky/environment, direct and area lights,
  emissive surfaces, probes, exposure, fog and animated effects. Let H3EK evaluate
  and bake the H3 representation. Source lightmap storage is not automatically
  compatible. Label draft previews and explain compiler warnings before relying
  on them. Do not remove unsupported effects without a scoped user decision.
- **Gameplay:** inventory placed objects separately from Forge menus. Apply the
  global [stock/shared audit](ASSET-REUSE-AUDIT.md) across every asset type.
  Native H3 equivalents retain stock behavior, dependencies and budgets. Keep
  unresolved H4-only items, Megalo behavior, ordnance/loadout dependencies and
  movement features explicit; do not implement H4 simulation inside H3.
- **Budgets:** retain native capacities, including Forge's 640 records and 256
  quotas. Do not expand a small map's palette into an all-map scenery union.
  A palette choice for another map is not automatic authorization for Haven.

## Pinned importer findings (static review, 2026-11-04)

Evidence: work/halo4-to-h3/haven/foundry-source-review.json records the reviewed
source file hashes, symbols and line ranges. Paths below are relative to the
pinned Foundry blender/addons/io_scene_foundry directory. This is code review,
not an H4EK execution result or evidence that Haven contains a particular light.

- tools/importer.py, import_scenarios: the H4/H2A (corinth) branch passes no
  lighting-info path to import_bsp. Scenario imports can also skip an invalid
  source scenario, so require expected source counts and named collections.
- managed_blam/scenario_structure_bsp.py, to_blend_objects: corinth reads the
  BSP's emissive-material records; the lighting-info import is in the other
  branch. Enabling tag_import_lights does not make that branch run for H4.
- managed_blam/scenario_structure_lighting_info.py, to_blender: corinth sets
  definitions and objects to empty lists and returns no light objects. Calling
  this helper separately therefore does not recover H4 lighting in this version.
  Its H4 light-writing methods are not evidence of a working H4 light importer.
- managed_blam/__init__.py and utils.py: the creation/save and cross-project
  copy behavior above requires an isolated authoring project and dependency
  checks even when the top-level operation is called an import.

The first official H4EK read now finds 194 generic light definitions and 194
instances in Haven's referenced lighting-info tag; the pinned reader's empty
H4 branch is therefore relevant to this source. These counts do not yet prove
which definitions contribute visible lighting. Inspect their effective fields
and the supported official/tool import routes. If a
different unmodified tool version or source format supplies the missing light
import, pin and verify that route explicitly. Do not silently fabricate light
placements, patch the importer, or accept emissive surfaces as proof that all
source lighting survived. Scenario/object lights and other lighting sources must
be inventoried separately; this finding does not prove they are absent.

## Dependency and import findings (executed, 2026-11-04)

H4 material dependencies must include their material_shader definitions and
referenced material_shader_bank. Loading one material successfully with its
shader definition absent did not prove dependency completeness: after staging
the definition, the official reader failed fatally until the referenced bank
was also staged. Inspect the primary ManagedBlam exception rather than an
importer's later error-handler/undo failure. Haven's exact trace is in HAVEN.md.
Do not fix this failure by altering paths, material tags or the importer.

The old unmodified Foundry imported Haven's render structure, portals and
prefabs, but not its H4 light instances or Havok collision. Its 682 imported
instance objects match the 682 source records whose mesh has render parts;
the other 319 records have no render parts. A matching visible mesh count is
therefore insufficient to establish preserved collision. The official-API
audit_halo4_instances.py records instance/definition/mesh relationships without
decoding or generating geometry.

Released 1.9.19 implements H4 lighting and Havok import. Its first background
run reached the lighting reader but failed in node layout: Blender reports
read-only preferences.system.ui_scale=0 in background mode and the add-on
divides by that value. Changing preferences.view.ui_scale does not initialize
the derived value. Normal command-line application startup reports 1.0.
The unchanged importer succeeds in an initialized application process using only
its Python API, with hidden launch, confined output and a process watchdog.
Schedule the batch script after initialization via bpy.app.timers.register and
quit through bpy.ops.wm.quit_blender after the job. The verified Haven run exits
normally in 27 seconds. Calling quit during startup argument evaluation did
not close the earlier small probe; its 30-second watchdog stopped that process.
This is not authorization for UI automation, host input or patching the add-on.

Do not classify every absent instance record as lost geometry. The official
source and existing Havok reader show Haven's one remaining absent record has
no render parts and no child in any serialized collision group. Preserve that
finding and the original record in the inventory; do not fabricate geometry.
The other 1000 instance names/transforms match the imported scene (maximum
matrix-element discrepancy 2.384185791015625e-7). Light count and placement
checks still do not establish material, lighting appearance or H3 fidelity.

Dependency closure must include materials introduced by prefab BSPs, not only
the main BSP's material list. The first Haven material/sky pass created an
empty material_shader tag for a prefab light material; the before/after
manifest rejected that output. The real shader and its bitmap were present
in H4EK. Quarantine the generated tag as evidence, stage the archive originals,
then repeat the unchanged importer. Never accept the empty tag as a fallback.
The corrected pass preserves all tags and imports the sky/material nodes.
All 452 files in the extracted Foundry release still match the release ZIP.

Reproduction commands from the repository root, after staging dependencies:

```powershell
# Structure, H4 lights and Havok collision:
& ./tools/warlock-conversion/snapshot/tools/import_halo4_source.ps1
# Add material nodes and the source sky; separate output directory:
& ./tools/warlock-conversion/snapshot/tools/import_halo4_source.ps1 -Visuals
```

The launcher confines profiles/temp/output, starts hidden, schedules the
existing importer through Blender's Python API and enforces a 180-second
watchdog. It requires a fresh successful JSON report, unchanged source tags
and a saved scene. Blender's exit code alone is insufficient because timer
callback exceptions can still leave process exit 0. Preserve prior failed
reports before retrying. Source scene images are not gameplay screenshots or
evidence of H3 fidelity.

Read scenario placement flags and enum names through their official API, not
their raw numeric values alone. Foundry's TagFieldFlags has RawValue and
TestBit(name); its value items differ from block-flag items and do not expose
IsSet. The scenario audit records the raw flag value plus named set bits.

### Prefabs and separate structure design

Inspect evaluated collection instances as well as direct scene objects. The
pinned General-101 ASS exporter does not expand Blender collection instances.
Use Blender's `bpy.ops.object.duplicates_make_real` in a derived file, then match
every realized object to the prior evaluated mesh and transform. Verify shared
mesh data, geometry, UVs, normals and metadata before continuing. Do not create
replacement meshes. Haven's 25 prefab placements/62 meshes pass this boundary.

Keep source collision categories explicit. The H4 reader distinguishes physics
objects, physical projectiles and simple projectiles. H3 collision-only and
sphere-collision-only flags do not by themselves establish complete equivalence.
Do not infer H3 support from Reach/H4-only fields in a multi-version schema.
Preserve unresolved geometry while establishing a documented authoring path.

H4 structure-design helpers can be validated independently before full BSP
authoring. Read their original triangles/types through the official API, use
Foundry's unchanged axis/unit transform, configure the existing H3 material
controls and export with General-101. Run official H3 `structure-design` and
`export-tag-to-xml`, then compare every oriented triangle, plane and type and
confirm generated collision data. Use a distinct map namespace. Haven's
60-triangle acceleration ceiling passes; this does not establish BSP, material,
scenario or gameplay acceptance. Follow the official
[H3 soft-ceiling workflow](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/guides/softceilings)
and [instance-collision workflow](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/art/instanceobjects/collision).

Material previews are diagnostics. Record camera, renderer, exposure and omitted
game features, and inspect the actual result. If a preview has a defect, inventory
the selected material-shader definition/defaults, authored inputs, functions and
imported node connections before assigning a cause. Matching blend modes do not
prove matching material behavior. An authored parameter absent from the selected
definition is not automatically active or a conversion requirement.

Read effective function values with the existing Foundry reader and official
function editor before mapping source inputs. Static values can be superseded
by basic constant functions as well as by curves. Preserve original input/range
names and periods; Foundry substitutes `one` for an absent input while building
Blender nodes, so inventory the original field separately. Native editor
evaluation supplies reference samples without a bespoke function decoder.
Do not assume matching serialized data or successful editor loading alone
establishes in-game shader equivalence.

Haven's recognized functions now pass an official H4-to-H3 editor roundtrip:
save into isolated H3 diagnostic shaders, reopen through H3 ManagedBlam, compare
native fields and bytes, and evaluate curves at the original sample points.
Keep names/types explicit: H4 `scale u/v` corresponds to H3 `scale x/y`, while
parameter-type numeric ordinals are not interchangeable. Use native enum names.
H3's RGB-only color editor also requires a separate check of H4 alpha; all
tested Haven color functions have identity alpha. Do not generalize that result
to arbitrary H4 functions. Bound diagnostic batches and processes: the first
aggregate stalled on the 65th parameter; 32-function batches pass without
changing native limits. Keep diagnostic parameter names out of production tags.

Check compiler diagnostics and native collision fields together. Official H3
Tool can return zero and write a BSP despite open-edge errors. One-sided
nonmanifold controls can eliminate those errors while still producing physics;
that is not evidence of a bullet-only mapping. Inspect stock H3 tags through
their native schema before using a flag from a mixed-version schema. Record
unsolved category differences explicitly instead of silently making every
surface solid or removing collision. Isolated neutral-material fixtures are
diagnostics and must not become accepted source geometry/material changes.

### Full-scene authoring and source shader semantics

Keep the source import immutable and author H3 controls in a derived scene.
Use the existing Foundry transform to obtain Halo-space matrices, then configure
Blender object matrices and General-101 export properties. Do not assume that
rescaling mesh data preserves corner normals: thin triangles can acquire large
automatic-normal changes. Haven's verified route leaves mesh coordinates,
split normals, topology, UVs and color attributes untouched and uses uniform
instance scales supported by ASS. Compare world coordinates and normals against
the source before saving; state scale-dependent tolerances explicitly.

Use separate existing native routes for BSP, sky render model, structure design
and lights. An unsaved export scene may share the authoring mesh data while
selecting only the relevant objects. Verify the actual file using the existing
exporter's reader against evaluated Blender meshes, including every corner,
UV set, RGB value, material binding and transform. An empty alpha inventory
on the BSP does not cover a sky excluded from that export. Stable target shader
names are only bindings until their native tags and behavior are verified.

Reuse the bitmap extraction/import/verification pattern from the existing
`extract_reach_bitmaps.py`, `author_wall_family.py` and `verify_wall_family.py`
workflows. H4 uses the Corinth reader and its own usage/curve enums. Configure
a separate Foundry project data directory so new extraction does not overwrite
preview inputs. Record source formats, curves, mip counts and normal conventions;
an existing image does not establish the correct native H3 import settings.
The released extractor can emit both vertical cube faces and an equirectangular
preview: keep them distinct. Verify native cube orientation after import.
Check stock/default bitmap candidates before duplicating payloads. Matching
decoded constants identifies candidates, but does not replace original-H3
resource provenance or shader channel/curve verification.

Compile an isolated neutral-material geometry diagnostic before expensive
material/lightmap authoring. Preserve the ordinary export and verify the probe
with the same geometry reader. Record native instance/definition counts before
and after Tool processing: the input count alone does not prove compliance.
Haven's 1005 definitions grow to 1041 and fail the native 1024 limit. An exit
code of zero is not sufficient; inspect fatal/error messages and fresh tags.
Use bounded subsets to identify added definitions. Do not raise limits, discard
authored geometry, or infer the cause from coincident counts.

For collision errors, inspect source topology and Tool's native diagnostic
geometry together. Keep nearest-coordinate matches distinct from exact matches.
An existing one-sided surface control can make an open proxy compile while
leaving its collision behavior unresolved. Test these controls in an unsaved
derived scene, preserve source faces, and verify native fields before accepting
category mappings. Stop large repeated batches when the compiler reaches its
error-report category limit; that crash is not a new geometry diagnosis.

Stage official H4 shader source from the shipped archive using existing archive
tools and verify the files. Follow selected defines and active calculations;
declared-but-unused inputs and similarly named H3 options are not equivalents.
Inspect texture channels, coordinate transforms, Fresnel terms, alpha, lighting
model and time units. For example, `vertex_alpha_multiplicative=0` in the
constant H4 shader selects vertex alpha directly; it does not disable it.

Validate imported node graphs as well as their exposed inputs. Haven's cloud
preview retains the varying authored RGB values but pads Blender alpha to 1;
the supplied preview shader's fade result is also disconnected from opacity.
The official authoring-preview shader instead uses vertex red as alpha. This
is evidence of a preview mismatch, not authority to patch the tool or assume
native runtime behavior. Configure target materials through supported authoring
controls and independently verify their native channel consumption. Preserve
unresolved features explicitly rather than accepting a plausible-looking
preview. See HAVEN.md for exact source lines, graph evidence and remaining gates.

## First milestones and current gate

Keep this workflow aimed at a complete draft. The user explicitly asked to
avoid getting lost in detail (2026-11-04). Each diagnostic should answer a
specific build/runtime question and record its result before moving on.
Do not spend successive milestones refining previews while the complete
native build is still missing. Preserve unresolved fidelity work as explicit
review items; successful loading alone is not final content acceptance.

If instance limits block compilation, prefer existing DCC authoring operations
over compiler reverse engineering. Exact relinking is safe only when all export
attributes agree. For collision grouping, preserve categories and instance
controls, bound per-definition geometry, use native Blender Join, and verify
source-to-output geometry and native collision. A grouping inventory alone is
not evidence that the grouped map compiles or behaves correctly.

For remaining collision errors, use a subset that reproduces the full log
before comparing authoring controls. Haven's eight failing instances plus the
world/portals reproduce all eleven errors. Precise worsens them and is rejected;
targeted nonmanifold surface controls remove them without changing geometry.
The same controls then pass the full native compile. Keep per-map selections
in its evidence, never as global face-index rules. Native collision surfaces
remain two-sided and physical, so this compiler result does not establish
bullet-only or other cross-engine collision-category behavior.

1. Install/inventory H4EK and verify Haven's editable source/dependencies.
2. Demonstrate a complete source scene import with unmodified Foundry and a
   source-to-import inventory comparison; keep source tags immutable.
3. Demonstrate the existing H3 ASS export/readback on derived source content,
   with explicit metadata/material mapping and no fabricated geometry.
4. Compile a named H3EK draft candidate and inspect real content before final
   lighting or downstream native packaging.
5. Adapt through the existing MCC-to-H3 pipeline, then prepare a review candidate.

Current milestone: H4EK is installed, a repository-local kit is staged, and the
official Corinth.ManagedBlam API has read Haven's main scenario, five child
scenarios, BSP, lighting-info and environment tags without changing source tags.
See HAVEN.md for pinned inputs, exact counts and evidence. The older tool has
completed a partial structural import. The released tool's structure, collision,
light, material-node and sky imports now pass. Prefab realization and the
design-only H3 export/compile/readback boundary pass. Full BSP ASS geometry
export/readback now passes for 1098 instances and 257822 triangles. Official H3
editors preserve all recognized source functions. One source preview exposed
a sky seam, and a concrete cloud-opacity graph mismatch is now documented;
source appearance is not accepted. A full neutral geometry import now fails the
native definition limit and source collision topology. Bounded native Blender
Join now preserves source corners and produces a full neutral BSP at 828
definitions, confirmed through the official API, with 35 portals/eight clusters.
Targeted surface controls now produce zero compiler errors/fatals in the full
neutral BSP, with native readback confirming collision and physics for all
eight formerly failing instances. Warnings remain. Full BSP collision semantics, native shader
mapping, authored gameplay/audio and a successful full-map compile remain open.
All 66 ordinary custom 2D bitmap inputs now import through the existing official
H3 API/Tool workflow, retaining dimensions, mip counts and source compression
families. Source defaults use stock H3 counterparts. Exported-pixel checks flag
seven normal maps for draft shading review; 59 pass the current channel-error
threshold. Keep cubemap/high-precision input handling and these exceptions
explicit while advancing material binding and the complete textured draft.
No complete H3 map or native candidate is claimed.

For H4 material authoring, reuse the existing H3 shader-plan and physical-name
API workflow with a confined per-map namespace. Resolve bitmap inputs against
the imported/stock binding manifest, translate UV animation enum names through
the already verified native function boundary, and remove irrelevant donor
overrides. Verify saved bitmap references as well as scalar/function controls.
Keep source feature gaps explicit in the material report: a draft donor choice
does not establish cross-engine shading equivalence. Bind the draft through
the unchanged ASS exporter and compile it, preserving earlier neutral geometry
evidence. Haven's first 59 opaque bindings implement this stage; see HAVEN.md.

H4 cubemaps extracted by current Foundry are six-face strips. H3's native cube
slicer consumes the cross layout; importing a strip directly can succeed while
silently changing face dimensions. Reuse Foundry's existing orientation helper
to prepare the cross, preserve texel bytes, then verify native face dimensions,
mip counts and all six exported faces. Do not substitute the equirectangular
preview. Keep raw pixel-content checks separate from world-space orientation
and cross-curve color acceptance. RGB10 source artwork extracted to RGBA8 also
requires an explicit precision limitation, even when the H3 import is exact.

For the native scenario, reuse the existing H3 scenario/profile/placement API
setters. Read the main H4 scenario and its children through the official API;
preserve child placement coordinates. Replace scripted spawn roles with stock
H3 mode-specific objects and keep unresolved labels explicit. Expanded markers
need distinct editor IDs but retain the authored positions and teams. Inventory
the original H3 donor cache before copying Forge choices from the editing kit,
and compare identities, names, limits and costs. Verify the saved active zone,
BSP/design links, starting profile and every placement before a cache attempt.
These checks do not establish native spawning behavior or authorize dropping
H4 objectives, ordnance, audio or atmosphere.

The first Haven MCC draft now builds successfully with official H3 Tool.
Read the resulting cache with unchanged TagTool as well as the existing cache
reader: verify the packaged scenario/BSP/design identities, spawn counts and
Forge records against the authoring plan. Record missing sky and placeholder
lighting explicitly; Tool may build a cache with `fake_lightmap` and no sky.
Preserve warnings even when the command exits successfully. This milestone
establishes the kit-to-cache boundary only, not rendering, gameplay or original
Xbox 360 compatibility. Continue toward a complete scene before expanding
material micro-audits. Haven's build/readback evidence is in
`work/halo4-to-h3/haven/scenario-authoring/`.

For a rigid sky, export the existing source mesh through General-101 JMS 8213
with an identity `frame_` root; preserve the verified world transform and vertex
RGB. Use Tool's `collection shader_name` material convention. Full shader paths
in JMS can produce `shaders/invalid` without failing the compile, so require
exact native render-model material-reference readback. Reuse the existing H3
sky-container API authoring path and verify the scenario's active-BSP/default-sky
links. A source red-channel opacity value surviving in JMS RGB does not prove
that H3 consumes it as opacity. Track that shader behavior, scrolling, secondary
emission and lightshaft fades explicitly until actual native rendering verifies
them. Haven's current sky step is a draft and does not clear those requirements.

For lighting, inspect both the BSP and sky model's H4
`scenario_structure_lighting_info` tags. H4 model lighting is separate from the
legacy H3 render-model skylight block. Haven has 194 BSP lights plus 96 sky
directional lights, all static/artistic with constant intensity and attenuation
functions. Author the supported H3 generic-light fields through the official
API and established field setters; retain unresolved source controls explicitly.
Preserve a fresh BSP material-info table and use a separate derived lighting
tag linked from the scenario. Verify every saved light field and prove that
the scenario reference is the only intended scenario change. Direct retention
of numeric power/color values is a draft mapping, not proof of equal rendered
illumination. Follow with the existing official local lightmap bake workflow
and actual renderer review instead of indefinite pre-render calibration.

Haven exposed a separate H3 lightmapper requirement: an otherwise compilable
all-instanced visible scene can fail `faux_data_sync` with "there is no mesh in
the structure". Resolve this through supported geometry authoring, preserving
an existing appropriate source mesh as world render geometry with identical
placement/attributes and collision semantics. Do not invent a helper surface.
Haven uses an existing four-triangle render-only floor piece. Verify unchanged
total geometry, absence of a duplicate instance, native material references and
retained clusters/portals, then refresh the derived lighting tag from the new
BSP before retrying with a new job ID. Successful compilation does not prove
lightmapper acceptance; successful data-sync does not prove lighting quality.

Keep the production BSP basename short before beginning the H3 lightmap farm.
Haven's descriptive probe name produced corrupted derived filenames and a
native data-sync assertion. A verified copy relinked through official APIs as
`haven` completed the same unmodified tool sequence. Preserve failed logs and
clean pre-bake inputs, use a fresh job ID, and verify alias contents/references;
do not patch the lightmapper or treat a zero exit alone as visual acceptance.
After farm finish, run the documented linear-texture and compression steps,
then rebuild the cache and verify that it packages the generated lightmap,
correct sky and expected placements. Retain UV warnings for renderer review.

Also inspect compiled cluster sky indices and actual sky resource payloads.
A valid scenario sky reference is insufficient: Haven's initially unassigned
H3 cluster skies caused Tool to omit sky texture data. Assigning the sole sky
through official cluster fields in a separate draft restored those payloads.
Verify this after the cache build; do not substitute an empty texture or bypass
the resource reader. Use the existing converter's bitmap-size overrides for
authored base-only images that have no smaller mip at its prototype 512px cap.
Keep the native memory budget and visual assessment separate from this fix.

The first native Haven draft uses the established `build_scenario_checkpoint.py`
pipeline with a scoped `--haven-draft` configuration. It selects existing H3
shader permutations and stock gameplay assets, passes the existing collision,
placement and quota guards, and retains complete build/material reports.
Disabled detail normals route to a base-normal-only native permutation; active
layers still require their authored values. Do not silently enable a disabled
layer merely to pass the existing unit-strength check. This configuration is
not a separate H4 binary converter and does not establish final rendering.

When a native draft appears untextured, check actual base/normal resource
payloads and retained mip levels, shader texture bindings/UV transforms, and
primary mesh UVs before changing the light bake. Preserved source UV layers do
not alone prove that the compiled primary stream selected the right layer.
Distinguish stored-data evidence from a live GPU sampling check. A temporary
official-kit from-albedo emission material can isolate texture display from
lighting/reflection response; retain the source bitmap and UVs, verify the
compiled shader option/constants, preserve and restore the original inputs,
and label the result diagnostic rather than a fix or fidelity acceptance.
