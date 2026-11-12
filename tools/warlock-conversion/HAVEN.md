# Haven: Halo 4-to-Halo 3 workflow pilot

**On ice — paused by the user, 2026-11-04.** Documentation only at shutdown;
do not resume conversion, baking or testing without a new user instruction.
The goal is incomplete. No Haven candidate is accepted or ready for final review.
Desolation and Sky Bridge remain pending final review.

The user's latest priority is **textures/material fidelity**, reiterated after
the investigation drifted into lightmap density. That remains the first unresolved
work if explicitly resumed. Do not substitute more lighting diagnostics for it.
The floor material, for example, specifies H4 `specular_map` and
`control_map_spglrf` textures that the current opaque/reflection draft authorer
does not bind to corresponding H3 texture inputs. Control-channel packing,
gloss/reflection masks and several other material features remain incomplete.
These omissions are confirmed authoring gaps, not a proven explanation for
every visible defect. No correction was implemented before shelving.

Checkpoint summary at shelving:

- **Candidate4:** original-H3 gameplay load succeeds; visuals fail (black
  architecture, clipped white/cyan, absent-looking surface detail).
- **Candidate5:** temporary from-albedo emission on five materials reveals
  texture detail on selected surfaces. It proves limited native texture/UV
  functionality, not complete material fidelity or a production fix.
- **Candidate6:** temporary normal-mapped diffuse-only shaders on the same
  five materials. The inspected native capture still has the black central
  surface; an upper-left highlight is reduced. It is also diagnostic only.
  Run `.local/loading-traces/20261104-212100-54360` ended at its 180-second
  watchdog with four hash checks passed. Build evidence is in
  `.local/haven/candidate6/` and `work/halo4-to-h3/haven/diffuse-diagnostic/`.
- Both shader diagnostic builds restored the original authoring shaders and
  MCC cache byte-for-byte, as recorded in their reports. Shared installed maps
  were not replaced by these private Haven candidates.
- The density investigation was **not executed**: no new density authoring
  checkpoint or bake was run. The unused helper was removed and the interrupted
  bake-wrapper edit restored before shelving. The last completed lighting job
  remains `2026110503`.

Retain `candidate4-lightmap-uv-audit.json` and
`candidate4-center-lightmap-trace.json` as ancillary, limited evidence: the
checked baked UV streams vary; a CPU ray into compiled source geometry finds
zero SH coefficients at the central sample. Its selected triangle was measured
at roughly 0.0024 atlas pixel of area. These observations do not prove a density
correction, establish all-map texture correctness, or override the texture-first
direction. No lighting change was validated from them.

All broader gaps remain open: full source material/texture behavior, sky
opacity/animation, atmosphere, missing gameplay/audio content, native visual
acceptance and measured performance. Human traversal/final playtest remains
deferred to the user. The following sections retain historical evidence;
their old imperative wording is not authorization to continue while paused.

Selected 2026-11-04 for the user's new editing-kit-driven goal. Desolation and
Sky Bridge remain pending final review. Haven gives this reusable workflow a
concrete authored multiplayer level to validate; it is not a community MCC
remake or a manually rebuilt stand-in.

Shared process: [HALO4-CONVERSION-PROCESS.md](HALO4-CONVERSION-PROCESS.md).
The user's direction is to use the Halo editing kits and documented tools for
as much as possible, building the H4 counterpart of the Reach WIP process.

Earlier focus (user clarification, 2026-11-04): stay grounded and prioritize a
complete, loadable draft. Tie investigations to demonstrated build blockers;
defer visual refinement until there is real map content to assess. Keep known
feature gaps explicit rather than treating a draft as final acceptance.

Latest user priority: the native draft appears to have no textures. Resolve
that visible failure before a lighting rebake or additional content work.
Candidate4 remains rejected for visual review; the historical checkpoints below
are not acceptance claims. The stationary observer was recovered in
`.local/loading-traces/20261104-204243-50888`: position
`[20.277359,-13.079735,1.732040]`, forward
`[-0.995117,-0.042834,0.088923]`.

The focused texture audit finds the five source-ray-selected materials retain
their base/normal textures, original dimensions and all retained mip blocks in
the native cache. Its 773 primary vertex buffers preserve MCC UV values exactly.
Source UV0 on the visible objects varies across the mesh; UV1 is a constant
secondary layer. These are stored-data checks, not proof of correct live texture
sampling. Evidence: `candidate4-texture-path-audit.json` and
`candidate4-source-uv-audit.json`. A separate official-tool shader diagnostic
uses existing from-albedo emission to isolate texture display from lighting and
reflections on those five materials. It preserves the original tags/cache and
does not rebake the lightmap or serve as a release candidate.

That diagnostic is now complete: candidate5 SHA256
`9b886949747998666ed0231c4e7024bcd69f4673fdcf64c8e1cab1d1699c45f1`,
native run `.local/loading-traces/20261104-210829-45660`, 180-second watchdog,
four hash checks passed. Five compiled shader configurations/constants were
verified through MCC and native caches; the original authoring tags and cache
were restored byte-for-byte. Camera position/forward match candidate4 exactly.
The individually inspected native capture reveals gray tile/ridge detail on
the central sloped strip under the reticle and adjacent right strip; an
upper-left clipped panel gains gray surface detail. Unmodified regions remain
black or clipped white/cyan. Thus native texture sampling works on the checked
surfaces, while their normal shaded result suppresses detail. This does not
identify the exact material/lightmap/exposure cause or accept the overall map.
Evidence: `candidate5-texture-diagnostic-review.json`,
`texture-diagnostic/compiled-shader-check.json` and `native-shader-check.json`.
Source-to-compiled UV0 checks also pass within quantization tolerance on eight
ray-selected meshes; all 827 native compression records match MCC. A ninth
source hit has no compiled primary buffer and is excluded from that claim.

Earlier build: official H3 Tool successfully produced the first private MCC
draft, `work/editing-kits/h3ek/maps/haven_draft.map` (984887296 bytes;
SHA256 `12de5f10b93f3534c6da89ee0e26ddbb69e04d0561b581e5068d509531612191`).
This is an intermediate cache, not an original-H3 or review-ready candidate.
Read-only packaged-cache inspection confirms 9963 tags, the intended BSP and
structure design, 510 spawn markers and all 92 original-cache-derived Forge
records. The cache contains no sky reference and uses `fake_lightmap`.
Complete the missing scene and gameplay content, then add draft lighting;
defer further numerical material refinement until actual rendering can be assessed.

The successful build took 178.875 seconds under the 180-second watchdog.
Its log still reports stock kit model/animation-node mismatches for the gravity
hammer, red powerup and permanent gravity lift. Build success does not clear
those messages or prove their behavior. Keep shared stock tags unchanged;
check the existing original-H3 asset-reuse path before considering corrections.
Evidence: `scenario-authoring/draft-cache-build.json`, its log and
`scenario-authoring/mcc-draft-readback.json`/`.log`. No native runtime or visual
acceptance is claimed, and no game captures were taken for this checkpoint.

### Sky attached to the authoring scenario

The subsequent sky checkpoint now authors eleven draft H3 shaders using the
existing official API wrapper, exports the original sky with unchanged
General-101 JMS 8213, compiles it with official `tool render ... draft`, and
connects a stock H3 sky container to Haven's private scenario. Native XML
readback verifies all eleven exact shader references, 18238 triangles, one
identity root node, sky 0 on BSP 0, and the retained 510 spawn markers. The
stock container's unrelated attachments/functions are removed. Source tags
and the source authoring scene remain unchanged. This does not yet update the
earlier MCC cache; it changes the authoring tags for the next consolidated build.

The first JMS attempt used full shader paths, which Tool silently replaced
with `shaders/invalid` despite a successful geometry compile. Exact native
material readback caught this. The corrected export uses the existing
`collection shader_name` convention (`haven_h4 h4_sky_...`); the second native
readback verifies every expected binding. Both attempt logs remain in work.

This sky is explicitly a draft: source artwork, base tint and brightness are
bound, but scrolling, vertex-red opacity, lightshaft view/distance fades and
the towers' secondary animated emission still need matching. Those are final
fidelity requirements, not accepted omissions. The 96 sky lights and atmosphere
also remain separate native authoring work. Native rendered visibility, scale,
clipping and appearance have not been checked. No images were taken.

Reproduction helpers: `author_halo4_sky_draft.py`, `export_halo4_h3_sky.py`,
`PrepareHavenSky.cs` (scoped reuse of `PrepareH3Sky.cs`) and
`verify_halo4_h3_sky.py`. Evidence under the Haven work directory:
`material-authoring/sky-draft/report.json`, `haven-h3-sky-export-bound.json`,
`haven-h3-sky-bound-compile.json`, `haven-h3-sky-verification.json` and
`h3-authoring/sky-*.log`/`.xml`. Preserve the guarded authoring outputs before
intentional reruns; scenario backup is `h3-authoring/scenario-before-sky-setup.scenario`.

### Source lights authored for the draft bake

Official Corinth API reads now inventory the original BSP lighting tag, sky
model lighting tag, fog, atmosphere globals and camera effects. The BSP supplies
194 static artistic lights (109 point, 84 spot, one directional); the sky model
supplies another 96 static artistic directional lights. These are H4 generic
light records, not legacy H3 render-model skylights. Source tags remain unchanged.

`plan_halo4_lighting.py --sky` and `PrepareHavenLighting.cs` reuse the existing H3
field setters to author all 290 definitions/instances into
`levels/custom/haven_h4/haven_lighting_with_sky.scenario_structure_lighting_info`.
The scenario now references that separate tag. Original position, forward/up,
color and artistic intensity values are retained; cone angles convert degrees
to radians, source attenuation start/end become H3 far attenuation bounds, and
source cone/aspect map to circle/1. All inputs are static constant functions,
with no gobo or lens-flare dependency. Directional lights use no distance
attenuation. Source indirect amplification, jitter, sun and dynamic-only controls
are retained as unresolved metadata where H3's generic-light schema lacks fields.
This is not a claim of equal cross-engine illumination or attenuation response.

`verify_halo4_lighting.py --sky` checks all 4060 saved fields against the plan
(allowing Tool XML's six-significant-digit formatting) and proves that the
scenario changed only its lighting-info reference. The earlier 194-light
checkpoint and scenario backup remain. The compiled BSP's original lighting
tag is unchanged. A later geometry/material re-export must refresh the derived
lighting tag's material-info table from that new BSP before baking; do not reuse
a stale table merely because the light counts match.

Evidence: `haven-lighting-source.json`, `haven-sky-lighting-source.json`,
`h3-authoring/native-lighting-with-sky-plan.json`, corresponding author/readback
XML/log files, and `haven-h3-lighting-with-sky-verification.json`. Neither a bake
nor a new cache/runtime test has run at this checkpoint. Material emission,
native fog/exposure mapping and sky shader effects remain unfinished. Proceed
to a named draft bake using the existing local H3 lightmap workflow and a unique
Haven job directory; keep the resulting view explicitly provisional.

### World-render requirement and first bake retry

The first official lightmap data-sync job (`2026110501`) stopped with
`LIGHTMAPPER FAILED: there is no mesh in the structure!`. The H4 source has
world collision/portals but entirely instanced visible geometry. A successful
cache/structure compile had not established compatibility with H3's lightmapper.

The existing Blender/General-101 export now accepts `--world-render` alongside
the opaque/reflection draft flags. It classifies the existing four-triangle
`nave_shape244` floor piece (`%!*hvn_0607`) as world render geometry. It preserves
its authored transform, topology, normals, UVs, RGB and shader and carries the
original render-only/no-collision behavior into native face controls. No new
geometry is introduced. Export totals remain exactly 258018 triangles and
774054 corners. Prior native readback confirms the source instance was already
render-only, noncollidable and had no physics block.

The consolidated BSP `haven_one_sided_joined_surfaces_opaque_draft_reflections_worldrender`
compiles in 117.75 seconds, with zero compiler errors/fatals and the same 5154
warning lines. It has 881 instances/827 definitions, retaining eight clusters
and 35 portals; the selected piece occurs as world geometry rather than a
duplicate instance. Two world subclusters now exist. All 35 prepared reflection
shader replacements pass native reference readback. Collision surface, edge
and vertex totals remain 1688/3220/1492, though BSP partition nodes/planes change;
this is not a claim of tested physical collision behavior.

The scenario links that BSP and `haven_lighting_worldrender`, which copies the
new BSP's material-info table and reauthors all 290 lights. Readback again
verifies 4060 light fields and confines scenario changes to BSP/lighting links
(plus Tool's derived XML display label). The earlier tags and backups remain.

`run_halo4_draft_lighting.py --world-render` uses official
`calc_lm_farm_local.py` command order with four workers and the separate Haven
job `2026110502`. It has passed the former no-world-mesh failure and reached
actual lightmap chart packing, but then failed while writing lighting data;
see the short-name retry below. No runtime review is claimed.
Evidence: `haven-world-render-checkpoint.json`, revised
ASS/native import reports, `h3-api/worldrender-inventory.json` and
`haven-h3-lighting-worldrender-verification.json`.

### Draft lighting completed with short tag names

Job `2026110502` failed after 135 seconds in data-sync. Its log contains corrupted
filenames derived from the long BSP stem, failed probe/tag writes and the
`wrapped_arrays.h:1083 m_live_object` assertion. `PrepareHavenBake.cs` copies
verified pre-bake backups to short names (`haven_preview.scenario`,
`haven.scenario_structure_bsp`, `haven.scenario_structure_lighting_info`) and
uses official tag APIs to relink them. The BSP and 290-light tag are byte-identical
to their clean inputs. XML comparison permits only scenario identity, those two
references and the derived display label. Earlier tags and failed job remain.

`run_halo4_draft_lighting.py --short-names` completed all official stages in
job `2026110503`, including farm finish, linear textures, DXT5 compression and
compression merge. Finish reports 835 copied meshes and a 1024x1024x9 lighting
array; the scenario now references real generated lighting. The original BSP
and authored lighting input hashes remain unchanged. Evidence:
`haven-short-bake-verification.json`, `draft-lighting-2026110503/report.json`
and individual native logs. This establishes bake completion, not illumination
quality: data-sync still reports out-of-bounds UV triangles. Inspect their actual
rendered effect before deciding whether another authoring pass is required.

`build_halo4_preview_cache.py` packages this consolidated sky/geometry/lighting
checkpoint with unchanged official Tool. Its result is recorded separately in
`preview-cache/report.json`; the earlier `haven_draft.map` remains preserved.
Native conversion, actual visual content and remaining gameplay/audio/fog/sky
feature fidelity are still unverified. No captures were taken for the bake.

The consolidated `haven_preview.map` compiled in 107.672 seconds, 993181696
bytes, SHA256 `95f302fa9ba82db0a5496e8e8f8862925c89fd23c078290a36277f169b7cca01`.
Packaged readback verifies its real `haven_preview_faux_lightmap`, sky object,
510 placements and passing original-H3 collision/placement limits. These are
packaging checks, not rendered acceptance.

`build_halo4_native_draft.py --candidate N` invokes the existing conversion
pipeline with a scoped `--haven-draft` configuration. Stock objects/dependencies
retain the existing native reuse path; custom shader drafts select exact
original-H3 permutations and named parameters rather than the generic metal
prototype. Candidate1 stopped on zero-strength detail normals; those explicitly
disabled layers now select the stock base-normal-only permutation. Candidate2
passes geometry, objects and spawns, then fails on missing sky bitmap payloads.
Its source cache contains sky tags but all eight cluster sky indices are -1;
the first sky bitmap resource has no control/raw payload. Do not claim that a
sky reference alone proves its visible geometry or textures were packaged.

`PrepareHavenSkyVisibility.cs` creates separate `haven_sky` BSP and
`haven_skyview` scenario tags, assigning the sole scenario sky to all eight H3
clusters through official fields. Save/reopen verifies the indices. Original
baked tags remain unchanged. Source H4 API readback has no corresponding cluster
sky index, and an empty sky-owner-cluster block; H3 visibility is explicit draft
authoring here, not a copied H4 field. `build_halo4_preview_cache.py --sky-visible`
records the new build in `sky-cache/`. Native shader/bitmap behavior and final
sky visibility remain subject to actual rendering checks.

The sky-visible cache now builds successfully and readback confirms all eight
cluster indices are 0. Its first previously absent sky texture now has the full
2097152-byte payload and 68-byte resource control. Candidate3 exposed a separate
generic 512px conversion cap on a 2048x1024 source sky image with no smaller mip.
The Haven configuration now uses the existing per-bitmap size override to retain
authored 2D dimensions (bounded at 4096); it does not invent missing mip levels.

Candidate4 is the first serialized original-H3 draft:
`.local/haven/candidate4/zanzibar.map`, 72392704 bytes,
SHA256 `39b8f2465ac502b3b0089abbc9ab7c820fb19847c6064abfe1665d55f85655b3`.
The existing pipeline passes scenario coverage, collision-tree verification
(491 trees, 24779 packed nodes, 1504 BSP leaves), and conservative Forge quota
bound 93/256 with all 92 palette entries. It retains 510 source-derived spawn
markers. Read-only native asset verification passes 167 metadata records and
668 resource segments against original disc donors. This is a draft build,
not final material acceptance: its 76 material records include 46 marked
approximate, including existing cube-resolution/parameter limitations.

`prepare_halo4_native_run.py --candidate 4` reuses the established private
runtime and immutable disc-hardlink layout. The first stationary native test
uses the existing `trace_loading.py` route, 180-second watchdog, no host input,
and one guest-native capture at 155 seconds. Runtime/visual results are recorded
separately after the run, not inferred from map serialization.

First native run completed under its 180-second watchdog:
`.local/loading-traces/20261104-203455-53288`. Four native hash checks passed,
none failed. The one guest-native capture was inspected individually and shows
the stock first-person rifle/HUD, Slayer indicator and map architecture.
**Visual review fails:** much of the architecture is almost black while other
regions clip to white/cyan. This establishes a native gameplay load, not correct
rendering, lighting, sky behavior, stability, audio or traversal. No performance
claim is made. Trace the affected surfaces/materials/lightmap before tuning
values or expanding content. Review evidence: `candidate4-native-review.json`.
All 92 imported native sound codecs/packets also match disc donors, but that
does not verify audible playback or the still-missing H4 ambience.

Earlier bitmap checkpoint: all 66 ordinary custom 2D images now import through
official H3 Tool and ManagedBlam, with source dimensions and mip counts retained.
Decoded exported-pixel checks pass the current channel-error threshold for 59;
seven normal maps exceed it (maximum mean XY error 6.664/255). These are explicit
draft shading follow-ups, not accepted rendering or a reason to halt material
binding. No engine appearance has been verified. Four cubemaps and one
higher-precision glass image remain separate inputs to resolve.

Three constant-white source defaults map to original H3 `color_white`; the flat
normal maps to original H3 `default_vector`. Existing TagTool extracted both
from the unchanged original Construct cache. The CTX1 flat normal decodes to
(129,128), versus source (128,128), so this is stock-equivalent reuse rather
than byte identity. Downstream packaging must reuse stock dependencies; shared
resource page provenance remains pending. Evidence is in
`haven-stock-bitmap-bindings.json`, `bitmap-import/ordinary-2d.json` and
`bitmap-import/ordinary-2d-pixel-verification.json` under the Haven work directory.
Next milestone remains the complete textured draft, using existing shader
authoring and the compiled geometry; do not expand this checkpoint into another
general-purpose converter or exhaustive pre-render investigation.

### Opaque material authoring checkpoint

`author_halo4_opaque_draft.py` uses Haven-scoped copies of the existing
`ApplyH3ShaderPlan` and `ApplyH3MaterialNames` official API wrappers. It authors
59 opaque shader tags, verifies their bitmap references and function readback,
and assigns source physical-material names that exist in stock H3. Source tags
and stock shader donors remain unchanged. Unused concrete donor parameters are
removed, and the donor detail pattern is replaced by H3's neutral detail.

This is deliberately an intermediate binding: H3 two-lobe Phong has not been
accepted as matching H4 Blinn. Reflection, control-map channel interpretation,
self illumination, vertex occlusion/alpha and normal-detail distance fades
remain explicitly listed per material. Sixteen non-opaque-family materials
remain deferred, including separate sky materials. These gaps must be resolved
before final acceptance; neither native API success nor a BSP compile proves
appearance. Evidence: `material-authoring/opaque-draft/report.json`, the native
plan readbacks and `physical-materials-applied.json` in the Haven work directory.

The existing geometry export now accepts `--opaque-draft` together with
`--geometry-probe --one-sided-probe --join-collision-probe --error-surface-probe`.
It retains the verified geometry and uses the `hvndraft` shader collection.
Export/readback passes for 885 objects, 258018 triangles and 774054 corners;
all 59 authored source materials are represented. Five other BSP material
sources and the unbound collision assignment still use explicit neutral
placeholders. Sky remains a separate asset. Compile this named intermediate
through `import_halo4_geometry_probe.py
haven_one_sided_joined_surfaces_opaque_draft` before inspecting native bindings.

That intermediate now compiles in 144.516 seconds with zero errors/fatals and
5154 warning lines. Official API readback finds all 59 authored shader references
in 113 material slots (68 distinct references, including placeholders). Its
882 native instances and 828 collision definitions match the neutral checkpoint
exactly; 35 portals/eight clusters remain. The API read did not change the BSP.
Evidence: `haven-opaque-material-checkpoint.json` and
`h3-api/opaque-draft-inventory.json`. This establishes successful native material
binding, not rendered correctness, a lighting bake or a playable map candidate.

### Reflection inputs and draft bindings

All 75 recognized bitmap inputs now have either an imported H3 representation
(71 custom images) or a recorded stock-default binding (four). This is input
coverage, not visual acceptance. `prepare_halo4_cube_crosses.py` uses released
Foundry's MCC cube-face orientation helper and TIFF writer to arrange the four
cube strips into H3's cross layout, without filtering texels. Reloaded cross
tiles match exactly. Direct strip import was rejected: H3 sliced its width by
four and produced 32-pixel faces instead of 128. That isolated tag is unused.

`import_halo4_bitmaps.py --cube-pilot`, then `--special`, imports all four
crosses at their original face sizes and mip counts and imports the glass
circuits image uncompressed. Tool exports six faces for each cube. Pixel-content
checks pass for two cubes and the extracted glass artwork; two compressed cubes
exceed the current raw-channel threshold. These checks search face rotations
and therefore do not establish world-space orientation. The released extractor
reduces the glass's RGB10 source to RGBA8; preserve that precision limitation.
The native-default curve comparison (`--cube-defaults`) is retained separately;
its raw-channel differences across different saved curves are not a colorimetric
acceptance test. The reflection draft uses the explicit-sRGB imports.

`author_halo4_opaque_draft.py --reflections` now creates 35 separate native
reflective shader drafts, carrying source cubemap references, tint/intensity
functions, base/normal inputs and stock physical names through API readback.
Source tags and stock donors remain unchanged. Reflection masks/Fresnel,
control-map packing, glow and final shading response remain pending. These
replacement shaders are not yet bound into a newly compiled BSP. The exporter
accepts `--reflection-draft` alongside `--opaque-draft` to select them during
the next consolidated export. Keep the previous 59-material compiled draft.

Evidence: `haven-cube-cross-sources.json`, `bitmap-import/special.json`,
`bitmap-import/special-pixel-verification.json`,
`material-authoring/reflection-draft/report.json` and
`haven-reflection-input-checkpoint.json`. No new game captures were taken.

### Native scenario and spawning draft

`plan_halo4_scenario.py` reads the existing official H4 scenario inventory and
fresh read-only TagTool inventories of the original Construct cache. The cache
hash remains unchanged. `PrepareHavenScenario.cs` reuses the existing official
H3 profile/placement setters; it creates only
`levels/custom/haven_h4/haven_draft.scenario` in the staged kit.

The scenario links the compiled opaque-material BSP, its lighting-info tag and
Haven's compiled structure design, with one active BSP zone. It retains the H4
main scenario's initial position (-1.8729233, 3.7394955, 5.4557223) and facing,
and copies Construct's stock H3 starting profile. All 92 Construct Forge entries
are checked against the original cache for object identity, name, cost and
maximum count before copying: three vehicles, 22 weapons, 15 equipment, 21
scenery, three teleporters, nine goals and 19 spawning entries. These are Forge
choices, not additional objects placed around Haven.

The authored 73 ordinary and 16 invisible respawn points keep their source
positions. The 85 initial points expand into stock H3 mode-specific markers:
29 Flood-labelled locations use Infection markers, and 56 team/FFA locations
use the seven corresponding stock initial-spawn tags. Total: 510 native stock
spawn objects from 174 source records. API readback checks every selected
transform/team/control and object ID; Tool XML verifies the BSP/design/lighting
links, active zone, profile and all Forge entries. Original spawn locations are
not multiplied or scaled. H3's stock natural-respawn weight is taken from an
actual Construct respawn placement.

Twenty source spawn-zone/cinematic records remain listed for separate mapping.
Objective/ordnance gameplay, remaining source objects, audio and actual
mode/team spawning behavior remain unverified. The private editor draft copies
Construct's map ID (300) and budget (500); it is not a release identity or an
installed replacement. Evidence lives under `scenario-authoring/`, including
`scenario-plan.json`, `native-scenario-readback.json` and
`native-scenario-verification.json`.

The first cache attempt follows the [official H3 cache-building workflow](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/quickstart/quickstartoverview):
`tool.exe build-cache-file levels\custom\haven_h4\haven_draft x64`, from the
repository-local H3 kit. Read `scenario-authoring/draft-cache-build.json` and
its log for the result. A cache artifact alone cannot establish visual or
gameplay acceptance; sky, lighting and remaining material/content work continue.

## Source and attribution

Original map/game: Haven, Halo 4. Current reference input is the user's installed
official MCC Halo 4 content. No community port is the selected source; exact
individual geometry authorship has not been established by this preflight.
The editable input is the official H4EK source installed by the user. This
project's work is the subsequent H4-to-H3/OpenH3M adaptation, not original map
authorship. Tool authorship remains with the official kit developers, Crisp/
Foundry contributors and General-101/toolset contributors.

- Cache: D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo4/maps/wraparound.map
- Cache bytes: 167190528.
- Cache SHA256: fa6bdbbd3903f5c17555b3afbe2db7fa069eae2ff96d35ca9b31bb5ab155bd3d.
- Paired mapinfo: maps/info/wraparound.mapinfo, 73497 bytes.
- Mapinfo SHA256: 3b99a875246e2fbb145543a032ca0951d5d06e7ae43c66cf89e28bd6e7441447.
- The paired mapinfo contains the UTF-16BE title Haven at byte 68. This verifies
  the supplied cache/metadata identity; no new cache decoder was implemented.
- Official archive: Z:/SteamLibrary/steamapps/common/H4EK/H4EK.7z,
  9598520866 bytes, SHA256
  c7214d90c37557ecaf4215e35ef6c3a2f578e83d35eae5c15f7bceffacbf941f.
- Steam build 11571341, depot 1701250 manifest 2225106932614327627;
  shipped build_tag.txt: 2023.06.27.176405.1-Release.
- Editable main scenario verified in the archive and opened through the official
  API: tags/levels/multi/wraparound/wraparound.scenario. Its referenced BSP is
  wraparound_000.scenario_structure_bsp; five referenced child scenarios contain
  audio, spawns, ordnance and game-mode content.

Evidence: work/halo4-to-h3/haven/environment.json, produced by the read-only
snapshot/tools/inspect_halo4_environment.py. It inventories Steam manifests,
hashes existing inputs and records tool choices; it does not convert assets.

## Prerequisites

H3EK and HREK are installed. Existing repository-local H3EK and the pinned
Foundry/General-101 sources will be reused; see the shared process for versions.
H4EK (Steam app 1695792) is now installed at
Z:/SteamLibrary/steamapps/common/H4EK. The user performed the Steam installation;
the manifest reports fully installed and the content log reports No Error.
The kit's 86 non-archive files were copied into work/editing-kits/h4ek and
SHA256-verified (349228262 bytes). Steam files remain read-only inputs.

At preflight the repository drive C: had about 48 GiB free and Steam library
Z: about 506 GiB free. These are snapshots, not promised capacity. Inventory the
kit archive before extracting; all project-created files still belong inside
the repository, and external Steam source installations remain read-only.

## Official source preflight

The archive lists 88142 files and 37684097545 unpacked bytes. Initial selection:
Haven's level namespace, its shared sky namespace, related source scripts,
mapinfo and shipped authoring support files. Exactly 123 files / 258729119 bytes
were extracted and verified against archive sizes/CRC plus recorded SHA256.
The resulting local kit had 209 files / 607957381 bytes before API execution.
7-Zip's log reports more processed files/bytes because the archive is solid;
that is not the number of selected files written to the kit.

snapshot/tools/inspect_halo4_source.py reuses the Reach preflight's official
TagFile.Load/reference-walking pattern with the Corinth namespace shown by
unmodified Foundry. It uses explicit existing paths, makes no Save/New calls,
and checks the complete seed-tag hash manifest before and after inspection.
Run it with Blender 4.5's bundled Python, existing isolated python-packages,
repository-local profiles/temp and the repository kit as its working directory.

The first run exited 0 with all source tags unchanged. It read 13 scene-level
tags with no missing references in its deliberately limited traversal scope:

- Main scenario and five children; one referenced BSP, one structure-design tag
  and one sky placement. The child scenarios must be included in later placement
  and sound inventories; reading only the main scenario would omit content.
- BSP: 8 clusters, 35 portals, 1001 instanced-geometry placements, 67 material
  slots, 62 collision-material slots and 3 emissive-material records.
- Referenced BSP lighting-info: 194 generic light definitions and 194 instances.
  The pinned Foundry import does not recover these automatically. Their active
  contribution and supported target representation still need verification.
- The scene inventory exposes 280 unique tag references. 255 are outside the
  initial extraction. A subsequent pass extracted 251 of these (5189917 bytes)
  from the same official archive for inspection. Three referenced HSC files and
  wraparound_000.scenario_wetness_bsp_data are absent at those tag paths in the
  archive; their relevance and any alternative source locations need checking.
  This is not a completed material/object dependency closure.

Evidence under work/halo4-to-h3/haven: h4ek-tool-files.json,
h4ek-archive-summary.json, h4ek-seed-manifest.json, h4ek-seed-extract.log,
haven-source-inventory.json, its stdout/stderr logs, and
haven-direct-missing-references.json. These files establish source availability
and API reading; they do not establish geometry import fidelity or gameplay.

## Structural import and dependency trace

After the direct references, staged 84 geometry dependencies (75217347 bytes):
69 bitmaps, eight material_shader tags and seven prefab BSPs. Reading those
shaders through the official API identified the shared dependency
shaders/material_shaders/materials.material_shader_bank (313329997 bytes).
Its extraction report includes archive CRC/size and SHA256 verification.

The material mp_forerunner_floortile_02c failed in the official reader with
tag_groups.cpp(517), tagHandle.IsValid(), while the shader definitions were
present and their bank absent. Both slash conventions failed identically.
After staging the referenced bank, the same read and the unchanged old Foundry
import passed. Evidence: material-control.log, material-control-after-bank.json,
h4ek-material-shader-dependencies-report.json and import-attempt1 under the
Haven work directory. No source tag or importer was patched.

Old Foundry 1.1.61 structural import: 744 scene objects, 719 meshes, 209290
polygons, 35 portals, seven prefab definitions and 25 prefab collection instances;
zero imported lights. Run time 41.16 seconds, source tag tree unchanged.
Evidence: haven-source-geometry.blend and haven-geometry-import-report.json.
Material previews, sky and scenario objects were deliberately outside this
structural preflight; these outputs are not a complete source scene.

Official API instance audit: 990 definitions, 998 render mesh records, 1001
instance records. Exactly 682 instances reference meshes with render parts;
319 have no render parts. This explains the old import's 682 instance objects.
Names among the 319 include customcollision_162 and customcollision_155, but
names alone do not prove complete collision. The older importer lacks the H4
Havok import needed to verify that data. Evidence: haven-instance-audit.json
and haven-instance-audit-summary.json; source tags unchanged.

Other unresolved source references include the authored typo
shaders/default_bitmaps/bitmaps/defaault_normal.bitmap and seven prefab
instance_imposter_definition/lighting-info pairs absent from the shipped archive.
These are tracked as unavailable references, not replaced with empty tags.

## Current status

The installation prerequisite is resolved and official source inspection passes.
The pinned Foundry source review found that its H4 BSP import reads emissive
materials but skips the lighting-info import, and its separate H4 lighting-info
reader returns no light objects. This is a tool limitation, not a finding about
which lights Haven uses. The shared process records the exact source evidence
and requires a supported import route before claiming a complete scene.

Released Foundry 1.9.19 and portable Blender 5.2.3 are isolated in the repository
for their existing H4 light/Havok import support. A background import reached
the light reader but failed because its node layout divides by Blender's zero
background display scale. The unchanged importer succeeds after normal
application initialization (scale 1.0), using a scheduled Python batch with no
UI/host input. It exits normally in 27 seconds with source tags unchanged.

Released import evidence: foundry-1.9.19/application under the Haven work root.
1256 objects, 1037 meshes, 240759 polygons; 682 render-instance objects, 318
collision-instance objects, 35 portals, one structure and one boundary object.
All 194 source BSP light instances are present: 109 point, 84 spot, one sun.
Material previews, sky and scenario objects remain outside this checkpoint.

The official source has one metadata record without imported geometry:
instance 518, pcylindershape111, definition 512. Its mesh has no render parts;
the unchanged Havok reader also finds no child with source index 518 in any
of the three nonempty serialized collision groups. The groups contain 40
invisible-wall, 31423 player-collision and 171551 bullet-collision faces.
No missing primitive was invented. haven-havok-audit.json records this result.

verify_halo4_instance_import.py reads the saved scene and compares every
source placement using Foundry's own coordinate transform helpers. All 1000
imported names/transforms match, with maximum matrix-element error
2.384185791015625e-7; the one absent record is explained above. Evidence:
haven-instance-import-comparison.json. This verifies placement, not complete
face coverage, material/light appearance, H3 compatibility or gameplay.

### Source materials and sky checkpoint

The corrected material/sky import is saved separately in
foundry-1.9.19/application-visuals. It contains 1354 objects, 1038 meshes,
258997 polygons, 79 Blender materials and 76 loaded image datablocks (plus
the empty Blender Render Result). There are 290 light instances: the prior
194 BSP lights plus 96 sun-type records from the official sky lighting-info.
These are source authoring records, not 97 real celestial suns or a verified
H3 lighting setup. No rendered appearance has been accepted.

The first material/sky pass is preserved in application-visuals-attempt1 and
was rejected: it created a 4418-byte empty
shaders/material_shaders/materials/srf_forerunner_lewis_lights.material_shader.
The real dependency comes from forerunner_lights_01.material in a prefab.
The generated tag is quarantined under rejected-created-tags; its SHA256 is
70ea52e3a93514bc818acf213712de837d98e3678bc3921063ba761f008438f2.
Official API inspection of all 75 staged materials then identified that shader
and forerunner_lights_diff.bitmap. Both archive originals were extracted and
verified (1831664 bytes combined). The corrected pass completed in 25.44 seconds
with the tag tree unchanged. See h4ek-all-staged-material-dependencies-report.json.
Sky inspection also staged three shader definitions and light_rays_dust_diff.bitmap
(1994082 bytes combined); those shaders use the already verified shared bank.

### Authored scenario inventory

audit_halo4_scenario.py now records placements, transforms, named flags/enums,
palettes, spawn/objective data and acoustics from all six source scenarios.
No tags changed. Evidence: haven-scenario-authoring-inventory.json.

- Main: one lightbeam scenery placement and two invisible smart man-cannons.
- Spawns: 85 initial points, 73 respawn points, 16 invisible respawn points,
  12 respawn zones, four weak anti-respawn zones and four cinematic cameras.
- Ordnance: nine initial and 26 random drop points, with 17 authored drop sets.
  These need explicit stock-H3 gameplay mapping, not H4 simulation in H3.
- Audio: 28 sound-scenery records; 16 resolve to five palette assets and 12
  use invalid palette index -1. The latter are records, not 12 audible emitters.
- Game-mode children: 25 ca_blam device-machine records, 22 circle/beacon crate
  records and five flag stands. Active mode/flag semantics remain to be mapped;
  their mere presence does not establish that all are visible in normal play.

The existing unmodified General-101 H3 exporter also enables under isolated
Blender 5.2.3 (h3-tool-check/load.log). This is tool readiness only, not a
successful H3 export or compile.

The full H3 BSP/map has not been compiled and no map/runtime is installed. The
design-only H3 compilation below is the first verified native authoring boundary.
Next is resolving source appearance/face metadata, mapping authored gameplay
and audio, and compiling the complete H3 authoring scene.
Material, lighting, gameplay-role and Forge-template choices remain to be
established from those actual inputs rather than copied from another map.

### Prefab realization and collision categories

The expanded scene contains 25 prefab collection placements whose 62 meshes
are absent from Blender's direct scene-object list. The pinned General-101
ASS exporter iterates that list and does not expand collection instances.
`realize_halo4_prefabs.py` therefore uses Blender's existing Make Instances Real
operator in a derived scene. All 62 placements match the evaluated source:
33 render meshes and 29 collision meshes, sharing 16 unchanged mesh datablocks.
Geometry, UV/attribute, normal, material-slot and metadata checks pass; maximum
matrix-element discrepancy is 2.384185791015625e-7. There are no remaining
collection instances. The original source blend is unchanged.

Evidence: `haven-prefab-realization.json` and
`h3-authoring/haven-prefabs-realized.blend` (1416 scene objects).
The source inspection is `h4-authoring-scene-inspection.json`.

Collision is not yet an accepted H3 mapping. Foundry describes H4's invisible
walls as physics-object collision, player collision as physics plus physical
projectiles, and bullet collision as simple-projectile collision. H3's existing
exporter exposes collision-only and sphere-collision-only materials, but no
equivalent bullet-only authoring control has been established. Do not collapse
all three categories into ordinary collidable geometry or discard a category.
H3 instance collision children also have shared-definition semantics; the
Reach map's particular collision corrections are not blanket Haven decisions.

### First official H3 compile: soft ceiling

`inspect_halo4_design.py` reads the source design through Corinth.ManagedBlam:
one acceleration-type ceiling named `ceiling1`, 60 triangles, no water volumes.
`prepare_halo4_h3_design.py` uses Foundry's coordinate transformation and the
existing H3 material `+soft_ceiling:ceiling1`, then exports through unchanged
General-101 ASS v7. Every triangle preserves its order and winding; maximum
authoring vertex error is 3.814697265625e-6 world units. No geometry was invented.

`verify_halo4_h3_design.py` invokes official H3 Tool's `structure-design` and
`export-tag-to-xml` commands in the separate `levels/custom/haven_h4` namespace.
The native tag contains the same 60 oriented triangles and acceleration type,
plus 579 bytes of generated collision MOPP data. Maximum coordinate/plane
deviation in Tool's six-significant-digit XML is 4.5098876952920364e-5, below
the declared 0.00006 presentation tolerance. This is not a claim of bit equality.
Source tags remain unchanged. Tool matches the installed official executable:
SHA256 `1dcf51ec39bdf61b6a6ae40917908cf23a247bfedb7a4bff07124f508ee0f3b5`.

Evidence: `haven-source-design.json`, `haven-h3-design-authoring.json`,
`haven-h3-design-verification.json` and `h3-authoring/design-*.log`.
The native tag is `work/editing-kits/h3ek/tags/levels/custom/haven_h4/haven.structure_design`.
Full BSP collision, scenario linkage, game behavior and a playable candidate
remain unverified. A design-tag compile does not satisfy those requirements.

### Sparse source appearance and material audit

One 960x540 native Blender Cycles preview was rendered and inspected from the
source player-start location, with a diagnostic 1.7-metre eye-height offset.
Textured light-grey architecture, blue/white illuminated strips and clouds are
visible. This particular outward-facing view covers only a narrow gap and has
a visible vertical sky seam; it is not an accepted map-wide appearance review.
The preview uses imported source nodes/lights and AgX exposure 0, with no H4
lightmaps, post effects or scenario objects. Collision/portal/design helpers are
hidden only in the unsaved preview. No game or desktop capture was taken.
Evidence: `haven-source-preview.json` and `h3-authoring/haven-source-preview.png`.

`audit_halo4_materials.py` reads all 75 used materials with the official API and
unmodified Foundry parameter readers: 12 material-shader families, 1408 defined
inputs and 982 function records attached to recognized authored inputs. All
75 imported blend-mode selectors match their source material tags. In
particular, the 11 sky materials retain their opaque/alpha/additive modes;
there is no evidence that the seam comes from a simple blend-mode mismatch.
`Color` vertex data and both UV channels are present on the 18238-polygon sky
mesh. Function evaluation, vertex-alpha behavior and source-renderer equivalence
still need investigation. Parameters absent from the selected shader definition
are listed separately; they are not automatically treated as active inputs.
Evidence: `haven-material-input-audit.json`; source tags and blend unchanged.

### Native collision probes and stock comparison

`export_halo4_collision_probe.py` exports the original two-triangle
`nave_io_56|nave_30|nave_30` bullet surface through unchanged General-101,
with an isolated diagnostic enclosure and neutral stock shader. Neither the
fixture nor its material assignment is saved into Haven. Ordinary, one-sided
nonmanifold and sphere-only controls were compiled with official H3 Tool and
read back through its XML exporter and official ManagedBlam API.

The ordinary variant reports four open/degenerate edges and two leaky
connections despite exit code zero. It is a failed geometry check. One-sided
nonmanifold compiles without geometry errors, but retains `collidable`, two
collision surfaces, one physics entry and one MOPP. Sphere-only likewise has
physical collision; its surfaces additionally carry `invisible`. These results
do not establish the needed bullet-only behavior. Do not mistake the one-sided
nonmanifold control for a fix to visual alpha or a category-equivalent mapping.

`ReadH3InstanceCollision.cs` inventories 4791 instances from official H3
Guardian, Snowbound, Zanzibar, Bunkerworld, Warehouse and Spacecamp tags.
None in this sample has nonempty collision geometry with physics absent or
`collidable` disabled. Some definitions have separate render BSPs, whose query
semantics remain unverified. The official H3 instance schema exposes no
`NoPhysics` flag; a similarly named field in a multi-version third-party schema
does not establish native H3 support. This sample is not proof of impossibility.
All nine diagnostic/stock tags were unchanged by the read-only inventory.

Evidence: `haven-h3-collision-probe.json`,
`haven-h3-collision-probe-native.json`, `h3-authoring/collision-probe/`, and
`h3-api/instance-collision-inventory.json`. No collision mapping is accepted yet.

### Effective material functions

`audit_halo4_material_functions.py` reads the recognized authored functions
using unchanged Foundry 1.9.19 and official Corinth function editors, without
decoding their binary representation. All 982 records across 75 materials
were read: 980 basic non-ranged constants and two scalar curves. The curves
drive `si_intensity` for `wa_front _tower` (1.3 seconds) and `wa_tower_middle`
(3 seconds). Native scalar evaluations and curve controls are recorded; this
is not a claim that all material animation is represented by these two curves.
Shader-specific scroll-rate inputs still need mapping as well.

The sky vertex-alpha multiplicative input is actually zero in both affected
sky materials: the authored function on `wa_bigclouds_bottom` is constant zero,
and `wa_topclouds_fade` uses the zero shader default. That observation alone
does not explain the seam or authorize discarding vertex alpha.

Evidence: `haven-material-function-audit.json`; source tags and blend unchanged.
H3 function compatibility, shader feature mapping and appearance acceptance
remain separate checks.

`VerifyH4FunctionsInH3.cs` and `verify_halo4_material_functions.py` now pass the
official H3 editor compatibility boundary for every recognized source function:
71 distinct data payloads, 72 combinations including type/input/range/period,
covering all 982 records. Three isolated diagnostic shaders are saved and
reopened through H3 ManagedBlam. Function bytes, types, input/range names,
periods, graph counts, ranges and RGB colors match; both curves reproduce all
260 native H4 reference samples with zero error. Source color-function alpha
is required to be 1 because H3's GameColor API exposes RGB only.

Two concrete boundary differences are handled explicitly: H4 texture `scale u`
and `scale v` map to H3's `scale x` and `scale y`, as in Foundry's existing UV
function reader; parameter types are selected by native enum names, not H4
numeric ordinals. An initial aggregate probe stalled while adding its 65th
parameter, before saving. It was stopped; the reproducible probe uses at most
32 parameters per diagnostic tag and a 30-second per-process timeout.

Evidence: `h3-api/material-functions-readback.json`, the three numbered plans,
native readbacks and logs. The neutral stock shader donor is unchanged. These
probe shaders have diagnostic parameter names and are never production map
dependencies. Passing this boundary permits reuse of these functions through
the official API; it does not prove that H3's shader feature calculations,
texture channels, sky opacity, time behavior or rendered appearance match H4.

### Full authoring scene and geometry export

`prepare_halo4_h3_scene.py` now saves the derived full authoring scene as
`h3-authoring/haven-h3-authoring.blend`, SHA256
`df2403030516b47300205630e164c731f3a7de8ccf0b52483a8cbc5354d19e9f`.
All 1100 mesh objects remain: 715 default, 347 collision, 35 portals, one
structure, one sky and one design surface. The 1043 unique mesh datablocks,
shared mesh links, topology, UVs, vertex colors and source material assignments
are preserved. Source lights and other scene objects remain in the file.

Axis/unit authoring uses unchanged Foundry `halo_transforms` to set native
Blender object matrices in H3 ASS units. Mesh coordinates are not rescaled.
An earlier unsaved attempt using mesh-data scaling changed automatic corner
normals on thin triangles; that output was rejected. The saved approach has
maximum world-normal vector error 3.591767189858541e-7. Maximum world-position
error over the full scene, including its large sky, is 0.001092256479991045 WU;
each object passes its recorded extent-dependent tolerance. This is not an
assertion of bit-identical world coordinates.

Existing General-101 controls encode 7701 render/collision-only face selections,
3690 no-shadow selections and 21 two-sided selections. The 31406 source global
material selections remain recorded pending physical-material bindings. Source
bullet/play/invisible collision categories and three source emissive face
records remain explicitly unresolved; the script does not replace them with
an assumed H3 equivalent. The 122 material variants retain the source nodes.
Planned `havenh4 mNNN` bindings are stable names, not authored shader tags.
Evidence: `haven-h3-authoring-scene.json` and `h3-authoring/prepare-full-scene.log`.

`export_halo4_h3_scene.py` invokes unchanged General-101 in an unsaved export
scene sharing the original mesh datablocks. The separate sky, design and light
paths are excluded only from this BSP export. The resulting ASS 7 intermediate
is `h3-authoring/haven-bsp-unbound.ass`, 161201787 bytes, SHA256
`ca92fa99214007eaceea816e75c4ffe9d111bc9eba92505dfe0881c04ff72ed5`.
It contains 1098 instances plus the scene root, 1041 unique meshes, 146 material
entries and 257822 triangles. Existing General-101 readback verifies all 773466
corners against Blender's evaluated export meshes: positions, normals, UVs,
RGB values, material names and instance transforms. Maximum normal error is
8.231806349783991e-11; maximum matrix-element error is 7.62939453125e-6.
There are no zero-normal fallbacks. This comparison is against evaluated
triangulated meshes, not an additional claim about every premodifier normal.

No active vertex-color attribute occurs in the BSP selection. The empty ASS
alpha inventory therefore says nothing about the separately exported sky.
Optional PIL/lxml registration warnings did not affect this geometry export;
image import was not exercised. Evidence: `haven-h3-ass-verification.json`.
Shader tags are still unbound, collision semantics remain pending, and this
ASS is not an accepted full H3 BSP or playable content. The separate neutral
geometry diagnostic below now records the native compiler's failures.

### Native geometry diagnostics

`export_halo4_h3_scene.py --geometry-probe` exports the full geometry using
byte-identical copies of stock H3 `levels/shared/shaders/simple/grey.shader`
in the isolated `haven_geometry_probe` namespace. The ordinary authoring blend
and unbound ASS remain unchanged. `import_halo4_geometry_probe.py` invokes the
unchanged official H3 Tool with a 180-second watchdog and separate logs.

The full diagnostic retains all 257822 triangles and passes the same corner
and transform readback. Tool changes 1062 instances/1005 definitions into
1098 instances/1041 definitions, then rejects the native 1024-definition limit.
Tool returns exit code zero despite this fatal import failure. This is not an
accepted BSP, and the native limit is not being raised.

World-only probes retain all 35 portals and produce eight clusters. Both the
original uniform object transforms and an unsaved Blender Apply Transforms
comparison report the same six open/degenerate world edges. Neither produces
extra instance definitions. The two-triangle instance and largest source
instance each remain one definition in isolation. A first-500-instance probe
grows from 488 to 492 definitions, then reaches Tool's error-report category
limit after many open-surface errors. This localizes part of the definition
growth without establishing its cause; large repeated error batches are not
useful evidence.

`inspect_halo4_world_errors.py` locates the six Tool WRL diagnostic edges on
the original `structure_collision` mesh. The source itself has two boundary
edges and six nonmanifold edges. The reported edges surround source faces 594
and 1209, each sharing two edges with three faces and one boundary edge. This
is a nearest-coordinate diagnostic, not exact native/source vertex equality:
two compiled endpoints differ by approximately 1.5292 ASS units (0.015292 WU).
No faces have been removed or repaired.

An isolated `hvn_0000` probe uses the existing General-101/H3
`transparent_1_sided` authoring control on its unchanged 84 source faces. Its
previous 31-edge/bad-connection errors disappear; the six world errors remain.
This result establishes an applicable compiler control, not collision-category
or gameplay equivalence. The source scene is unchanged, and no global one-sided
mapping is accepted.

The first 250 instances compile far enough for official ManagedBlam readback
under the same one-sided diagnostic. The 238 input definitions become 242.
The four added instances are `!hvn_0026_merged`, `!hvn_0027_merged`,
`!hvn_0121_merged` and `!hvn_0127_merged`; all are render-only with no collision
surfaces or physics. Their source objects are collision-role meshes. Applying
the existing collision-only face control to all collision-role faces preserves
the same four additions and 242 definitions. This comparison does not solve
the definition limit; do not report the suspected missing role mapping as its
proven cause. The subset still has world/proxy collision errors.

Native readback of isolated `hvn_0000` confirms 58 collision surfaces, one MOPP,
one physics entry and `collidable=true`. Its compiled surfaces carry H3's
`two sided` flag. This reinforces the distinction between a compiler's
one-sided authoring control and accepted physical/projectile behavior.
Evidence: `h3-api/geometry-subset-inventory.json`,
`h3-api/geometry-role-inventory.json` and the two
`haven-range_0000_0250_*-probe-native.json` reports. These readbacks do not save
tags, and the ordinary full authoring blend/ASS hashes remain unchanged.

The official `structure` usage exposes only the ASS filename, with no merge
switch. Exact mesh-data relinking finds zero duplicates when positions,
topology, normals, UVs, colors, material bindings and roles must match. Do not
keep pursuing that optimization. `audit_halo4_collision_groups.py` instead
identifies 15 collision groups (256 objects) sharing exact transforms, source
collision categories and instance prefixes. The largest contains 224 play
collision objects/25585 polygons. This provides a concrete standard Blender
Join candidate without collapsing categories or changing visible geometry.
It is only an inventory: bound group sizes, verify all resulting geometry and
native compilation before adoption. Evidence: `haven-collision-join-groups.json`.
The prepared plan contains 43 batches capped at eight objects/2048 source
polygons each (actual maximum 2041), reducing object count by 213 if accepted.
This is not yet a measured native definition reduction. The exact-relink
export finishes with zero links and is byte-identical to the earlier full
neutral ASS, so repeating its native compile would add no evidence.

`halo4_join_collision.py` now applies those 43 batches using native Blender
Join in an unsaved derived scene. All batches pass a multiset comparison of
face corners: exact local positions, UVs, colors and material bindings, with
normals compared at six decimal places. Each batch shares an exact world
matrix; the operation temporarily uses identity matrices to avoid introducing
an inverse-transform rounding step, then restores the shared matrix. All
source collision categories and instance prefixes stay separate. The result
has 885 mesh objects. This does not yet establish native collision behavior.

The first full export with one-sided diagnostics reached its 180-second
watchdog after the Join checks. Its logs are retained as `joined.*.log`.
The wrapper now reuses identical one-sided material variants and creates them
only for used slots; unchanged upstream exporter/tool code is still used.
The subsequent bounded run has separate `joined-shared-materials.*.log` logs.

That run passes full ASS readback: 885 objects, 831 unique meshes, 258018
unique-definition triangles and 774054 corners. The triangle inventory differs
from the original unique-definition total because grouping changes shared
definitions; the per-placement Join comparison preserves source faces.
ASS SHA256: `34ecfcc64abd179380a3cd7e8567f07b3e80234412f6c150a7aa6b3c106483a6`.
Official Tool finishes in 167.016 seconds and writes the full neutral BSP.
It reports 795 input instance definitions and 828 output definitions, below
the native 1024 limit; official ManagedBlam independently reopens 882 instances
and 828 definitions. All 35 portals/eight clusters remain in the Tool report.

The definition-limit blocker is resolved for this diagnostic path. Eleven
actual error lines remain: world edges plus open/ambiguous collision on
`hvn_0025`, `0026`, `0027`, `0029`, `0417`, `0706`, `0755` and `0773`.
There are also duplicate/overlap and neutral-material warnings. The one-sided
controls remain diagnostic, and the full BSP is not accepted as collision-
correct or playable. Source/ASS hashes and native tag readback are verified.
Evidence: `haven-joined-geometry-checkpoint.json`, the
`haven-haven_one_sided_joined-probe-*.json` reports and
`h3-api/joined-inventory.json`. This is the concrete full-draft geometry path;
do not resume investigation of the already-resolved definition limit.

### Remaining collision surface controls

The 44-object diagnostic keeps the eight reported instances, world mesh and
35 portals after the same verified grouping. It reproduces all eleven full-map
error lines. Testing the existing Precise flag increases this to 61 error
lines; that setting is rejected for these inputs. Existing nonmanifold
one-sided flags on the eight reported instances and only world faces 594/1209
instead remove all error lines, preserving 35 portals/eight clusters. Geometry
is unchanged. This follows the existing tool's material controls, without
topology repair, triangle deletion or compiler changes.

Evidence: `haven-collision-surface-comparison.json` and the
`haven-haven_one_sided_joined_errors*-probe-*.json` reports. The full export with
those same targeted flags passes 774054-corner readback, SHA256
`003ca222f00a4aca2008afde44b59c8d566f767a10fa81a9a79e3216f60c985a`.
Its report records the exact eight instance IDs and two world face IDs. Native
full-map result and physical/projectile behavior are separate acceptance gates.

The full-map geometry comparison now passes: official Tool finishes in
155.453 seconds, writes the neutral BSP and reports zero errors/fatals/assertions.
It still emits 5154 warning lines, including source duplicate/overlap warnings
and neutral-material diagnostics; this is not a warning-free import. Native
readback confirms 828 definitions/882 instances, while the compiler retains
35 portals/eight clusters. All eight previously failing instances now have
nonempty collision surfaces, one physics entry and `collidable=true`; their
compiled surfaces are flagged two-sided. Their surface counts are 596, 50, 50,
592, 64, 216, 376 and 54 in the recorded instance order.

Evidence: `haven-geometry-compile-checkpoint.json`,
`haven-haven_one_sided_joined_surfaces-probe-native.json`, and
`h3-api/surface-controls-inventory.json`. Source and ASS hashes are verified.
This clears the geometry compiler gate; it does not verify physical/projectile
category equivalence, actual material appearance, gameplay or a playable map.
Next carry these supported authoring controls into the bound draft and reuse
the existing material/bitmap, scenario and native packaging workflows.

### Bitmap inputs for the bound draft

`prepare_halo4_bitmap_sources.py` reuses unchanged Foundry 1.9.19
`BitmapTag.save_to_tiff` and official Corinth metadata. A separate project data
directory at `work/halo4-to-h3/haven/bitmap-sources` preserves earlier preview
images. All 75 recognized effective bitmap references extract successfully;
all source tag hashes remain unchanged. There are 43 diffuse, 19 normal, nine
specular and four cube inputs. Source curves are 56 linear and 19 legacy xRGB;
formats include DXT1, DXT5, DXN, ARGB8, one RGB10A2 and one V8U8. This inventory
does not establish which declared inputs each compiled shader actually samples.

Normal inputs bypass the upstream extractor's color-space conversion. Color
inputs use its existing conversion behavior, recorded alongside source curves.
Cubemaps retain both the vertical face image and the preview equirectangular
image; the latter is not a native H3 cube import. No custom decoder or pixel
editing is used. H3 format, curve, mip and normal-direction checks remain open.
Evidence: `haven-bitmap-sources.json` and `h3-authoring/bitmap-sources.*.log`.

Official H3 Tool exports eight unchanged stock default-bitmap candidates.
Native Blender Non-Color reads find identical constant white RGBA values for
H4 `default_control`, `default_diff` and `default_spec` versus H3 `color_white`.
This is candidate evidence only: original-disc/shared-resource identity and
shader channel/curve compatibility must pass before reuse is accepted. No
exact candidate match is claimed for the normal map, cube or light texture.
Evidence: `stock-bitmap-candidates/inventory.json` and
`haven-default-bitmap-comparison.json`. No images are added to chat.

Evidence: `haven-native-geometry-diagnostics.json`,
`haven-world-error-locations.json`, the individual `*-probe-ass.json` and
`*-probe-native.json` reports, and `h3-authoring/geometry-probe/`. All native
results in this section are diagnostics with `geometry_accepted=false`.

### Official shader source and cloud opacity evidence

`stage_halo4_shader_sources.py` extracts the official material shader source
through 7-Zip into `work/editing-kits/h4ek/data/shaders/material_shaders`.
All 758 selected files (2670829 bytes) match archive CRC/size and have recorded
SHA256 values in `h4-shader-source-staging.json`. Neither Steam content nor tool
source is patched. These files supply feature semantics beyond parameter names.

`audit_halo4_sky_color.py` and `verify_halo4_sky_opacity.py` now establish a
specific discrepancy in the imported preview, without another render:

- `srf_constant_core.fxh:333` uses
  `lerp(vertex_alpha, vertex_alpha * texture_alpha, multiplicative)`. Both
  affected sky materials have multiplicative zero, selecting vertex alpha.
- `wa_bigclouds_bottom` has 1994 polygons and 1387 referenced vertices with
  11 distinct red values spanning 0..1. `wa_topclouds_fade` has 358 polygons
  and 268 referenced vertices with three red values spanning 0..1. Their
  imported Blender alpha values are all 1. Foundry's raw RGB import pads that
  fourth component rather than interpreting its shader meaning.
- Official `include/deform.fxh:70` uses authored vertex red as alpha in the
  authoring-preview path. Its native path starts with packed position.w
  (`:101`); the packed native stream has not yet been compared to authored red.
- The imported `srf_constant_vertalpha` node group's float `Mix` computes the
  fade but has no outgoing connection. Its blending-group alpha input instead
  receives `Mix.014`, an RGB addition. Independently, its `vertex alpha output`
  subgroup reads Blender alpha, which is the padded constant 1 here.

Evidence: `haven-sky-color-audit.json` records all 11 sky materials and their
recursive node graphs; `haven-sky-opacity-evidence.json` checks the relevant
wiring, source statements/hashes and effective parameters. This proves the
imported opacity calculation differs from the official shader. It does not
prove the observed seam has only this cause, or that an H3 sky fix is complete.
The source scene remains unchanged. Preserve the red-channel fade through the
target authoring path and verify actual H3 shader consumption; ASS/JMS RGB
serialization alone is insufficient evidence.

Other source-derived mapping requirements now explicit: Blinn variants use
control-map R for specular modulation, G for gloss, B for reflection and A for
self illumination when their corresponding features are compiled; reflection
also uses cubemap alpha. Constant shaders are unlit and have separate source
scroll calculations. `srf_forerunner_lewis_lights.fx` perturbs UVs using two
scrolling samples before a third texture lookup, so two ordinary scrolling
layers are not automatically equivalent. Lightshaft clouds apply normal/view
and distance fades. Native `ps_time.z` units and supported H3 counterparts still
require verification. No source effect is silently omitted or replaced.
