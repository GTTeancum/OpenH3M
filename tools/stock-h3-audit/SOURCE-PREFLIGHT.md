# Fresh Battle Canyon source preflight

Original map/game: Battle Canyon, Halo Reach MCC, originally developed by
Certain Affinity. No community-converted map or rejected rebuild is an input.
Installed original cache: `D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/haloreach/maps/cex_beaver_creek.map`.
Official source-tag input: `work/editing-kits/hrek/tags/levels/dlc/cex_beaver_creek`.

## Tool selection and observed limits

- Unmodified pinned TagTool cannot open this installed Reach cache: `string_id
  set 56` failure. Saved log: `work/stock-h3-audit/reach-source-all-tags.txt`.
  No TagTool fix was authored; the successful H3 inventories remain separate.
- Current [Foundry](https://github.com/ILoveAGoodCrisp/Foundry) requires Blender
  5.2; installed Blender is 4.5. Historical upstream Foundry 1.1.61 declares
  Blender 4.5 support. Unmodified source is pinned at
  `5dc085e4432b6b57b2bf97e02a442ecc6edc985f`, downloaded into
  `work/stock-h3-audit/upstream/Foundry-5dc085e4432b6b57b2bf97e02a442ecc6edc985f`.
  This is source availability, not yet a successful geometry-import test.
- [Halo Asset Blender Development Toolset](https://github.com/General-101/Halo-Asset-Blender-Development-Toolset)
  documents H3 ASS export with limitations, including missing UVW W-coordinate
  support. Do not silently compensate with a bespoke exporter.

## Read-only source inspection

`inspect_reach_source.py` invokes the official ManagedBlam tag API using the
initialization and field-selection pattern from Foundry's `managed_blam`
modules. It only loads, reads references, disposes and stops; no Save call,
binary parser, conversion or geometry generation. Run with installed Blender's
bundled Python (`C:/Program Files/Blender Foundation/Blender 4.5/4.5/python/bin/python.exe`).
Dependencies are isolated in `work/stock-h3-audit/python-packages`.
Pythonnet 3.0.5 and clr_loader 0.2.7.post0 were installed there. The bundled
Foundry wheel set's cffi 1.16 did not satisfy clr_loader's >=1.17 requirement;
pip resolved the dependency from PyPI without editing Foundry.

Successful output: `work/stock-h3-audit/reach-source-references.json`.
One source BSP and one sky scenery reference were read. The BSP has 193 material
slots with 102 unique references: 90 shader, 9 terrain, and one each water,
foliage and glass. This includes the source invalid-shader reference; no
conclusion about whether its faces are visible has been drawn.

Next: inspect source effects and sky dependencies and select stock H3 surface
donors. Standoff remains the first donor; consult other original maps for
missing surface types. A name match is a candidate, not visual validation.
No surface substitutions, fresh scene import, map compilation, or conversion
have been performed. Required features without stock alternatives go to the
user for a decision.

## Additional source and donor evidence

The same official API read now records seven effect-scenery palette entries:
three laser emitters, dripping point, rainbow, mist and sun flare. Each resolves
through an FX anchor model to its corresponding Reach effect. The sky resolves
to `levels/dlc/cex_beaver_creek/beavercreek_sky/beavercreek_sky.model`.
No stock counterpart has yet been established for the rainbow or decorative
lasers. Do not treat a Spartan Laser weapon effect as an established substitute.

Original stock Guardian, Valhalla (`riverworld`) and Sandtrap (`shrine`) tag
inventories are saved beside the Standoff inventory. These were consulted for
water and architectural/terrain alternatives absent from the initial donor.
`surface-donor-candidates.csv` records seven concrete original-stock candidates;
they are not applied mappings or visual approvals. Standoff supplies terrain
and foliage candidates; Valhalla supplies river water, cliff terrain and red/blue
Forerunner surfaces; Guardian supplies an architectural floor candidate.

All seven candidate level-material files were absent from the partial local
editing kit, despite the gameplay palette dependency check passing. Filling in
the official archive's `tags/*` with 7-Zip `-aos` preserves existing files while
adding the missing stock source tags. Extraction log:
`work/stock-h3-audit/h3ek-complete-stock-tags-extract.log`. Verify its terminal
result and candidate presence before relying on the completed kit.

Extraction subsequently exited 0 with `Everything is Ok`; all seven candidate
material files now exist. The log reports 57,442 processed files, 27,973,636,020
bytes; this is not a count of newly created files because existing files were
skipped. Source assets were not uploaded or installed into the live game.

## Background tool readiness

Unmodified Foundry 1.1.61 successfully enabled in Blender 4.5.8 LTS, with its
scene properties registered. Evidence: `foundry-background-check.log` records
`FOUNDRY_BACKGROUND_LOAD_OK 4.5.8 LTS`, process exit 0. This only verifies add-on
loading, not source import, geometry fidelity or export compatibility.

Run `check_foundry.py` through Blender with `--background --factory-startup
--python-exit-code 1 --python`. For that subprocess set APPDATA and LOCALAPPDATA
to `work/stock-h3-audit/profile/roaming` and `profile/local`, BLENDER_USER_CONFIG
to `profile/blender`, and TEMP/TMP to `work/stock-h3-audit/temp` (absolute paths).
The initial load attempt occurred before dependency installation had finished
and failed on missing networkx; after the installer exited successfully the
load check passed without upstream modifications.

On top of the official tag API dependencies, the isolated Python directory
contains networkx 3.4.2, scipy 1.16.0, pillow 11.3.0, pymem 1.13.1 and
py360convert 1.0.4 with their pip-resolved dependencies. Installation output is
`foundry-dependencies.log`. No pymem process-control functionality was invoked.

The user has been asked whether unmatched decorative effects should be omitted
or receive a specific Reach-import proposal if no stock match is found. No
answer is assumed. Geometry authoring and effects remain unchanged.

The user subsequently selected **Bring me an import proposal**. See
`EFFECT-IMPORT-PROPOSAL.md`; that response is not approval to implement it.
The read-only source inspection now records reference field paths inside all
seven Reach effects. No conversion has been performed.

An upstream Foundry BSP import for inspection was started with
`inspect_geometry_foundry.py`. It disables material building, light import and
export-on-save, and requests BSP geometry including collision. The wrapper
contains no geometry conversion logic. Output goes to
`work/stock-h3-audit/reach-source-inspection.blend` only on successful completion.
Check `foundry-geometry-import.log` and the live process before rerunning; a
silent buffered log is not evidence that the importer stopped. Mesh counts,
if produced, are not visual validation.

## Live import diagnosis and H3 export tool

The first inspection import remained live as Blender PID 20836, execution
session 50995. A read-only py-spy 0.4.3 stack capture succeeded and located its
active thread in upstream `utils.connect_verts_on_edge` (line 4778), called by
`ScenarioStructureBspTag.to_blend_objects` at line 302. This routine checks each
mesh vertex against each edge after merging the structure. It explains the
long-running CPU work; the empty redirected log alone was not treated as a
failure. The process was neither restarted nor modified. Evidence:
`work/stock-h3-audit/foundry-live-stack.txt`. Revalidate the live handle before
making any subsequent run decision.

The unmodified General-101 Halo Asset Blender Development Toolset was downloaded
at commit `81e86bf98aee4607a2159ff9a22a223a1a91c9d7` into the repo-local upstream
directory. `check_h3_exporter.py` enabled it in background Blender 4.5.8 LTS,
exit 0, log marker `H3_EXPORTER_BACKGROUND_LOAD_OK`. Use the same isolated
environment as the Foundry check. Its registered export operators include
`export_scene.ass` and `export_scene.jms`. No actual export has been attempted;
registration does not establish compatibility or geometry fidelity.

## Texture mandate clarified by the user

The user explicitly selected **Reach textures, H3 shaders**. Preserve original
Reach surface images; the H3 material donor list supplies shader/setup candidates,
not authorization to replace Reach rock, terrain or building textures with H3
images. The official API read of 102 source materials found 234 distinct direct
bitmap references, saved in `reach-surface-texture-tags.json`.

The user also requested Blender WIP proof images. A separate `--preview` mode
uses Foundry's existing render-only import option for inspection. It does not
replace the ongoing full import or establish collision/export readiness.
`render_wip.py` renders the actual imported scene with Blender Workbench using
a neutral single-color display; these previews must be labelled untextured
source geometry rather than an H3 MCC result. Source bitmap extraction, H3
shader assignment, lighting and MCC validation remain unfinished.

The render-only import completed successfully in roughly two minutes: 1,011
mesh objects, 533,913 polygons, 104 Blender materials. The source BSP SHA256
was unchanged before/after: `5f32272631e5fd419bab35ed37546b353911d9aef4c2d8750d46454698322766`.
Saved scene: `work/stock-h3-audit/reach-render-preview.blend`.
Native Workbench renders: `work/stock-h3-audit/wip/overview.png` and `closer.png`.
Both final images were opened and visually inspected: canyon terrain, bases,
rock arch and foliage geometry are visible. The initial framing included distant
backdrop pieces and was replaced with tighter camera framing. No map geometry
was changed for framing. These are untextured geometry previews; foliage alpha,
surface shading and lighting are not represented faithfully. Neither image
proves full collision import, gameplay or MCC readiness. The separate full
import remains a distinct live job until its process/result says otherwise.

## Full import completed; source-material preview

The full import exited 0 after 15 minutes 4 seconds, creating structure collision
and portals through upstream Foundry. Saved `reach-source-inspection.blend` has
1,131 mesh objects, 546,074 polygons and 108 materials. The source BSP hash
remained unchanged. This establishes import completion, not correct collision
in H3. The former session 50995/PID 20836 is now terminal; do not restart it.

The material preview initially raised 101 identical errors. A diagnostic trace
proved they occurred in the optional node-editor layout stage, which divides
by Blender's zero UI scale in background mode. The automation now invokes
Foundry's existing ShaderTag/ShaderTerrainTag/ShaderFoliageTag/ShaderGlassTag
`to_nodes` methods directly. No upstream implementation was modified, no custom
shader-building logic was introduced, and no replacement nodes were fabricated.
All 101 attempted readers completed without error. The water material is
explicitly skipped because this upstream preview reader substitutes generic
Basic Water; it is not claimed as imported faithfully.

`reach-textured-preview.blend` is a Reach-material inspection scene, not H3
shader assignment. Native Cycles renders use studio lighting for readability,
not source-map lighting. These remain WIP proof only. The source texture
mandate, H3 material target and outstanding effects approval are unchanged.

## H3 authoring path and first stock-shader trial

The next goal turn made authoring progress rather than another WIP-only report.
`inspect_export_scene.py` inspected the full saved Blender scene with both
unmodified add-ons registered. Scene settings are Foundry `scale=blender`,
`forward_direction=y-`; mesh types include 1 structure, 67 portals, 3 water
surfaces and 1,060 default meshes. General-101 does not automatically consume
Foundry metadata. Collision-only face attributes, portal flags, orientation,
scale and material assignments must be configured before exporting. Its README
also states missing UVW W support; do not treat exporter registration as proof
that every source attribute survives. No ASS export has occurred yet.

Correction (2026-11-04): the earlier H3 API probe incorrectly used Reach's
`ManagedBlamSystem.Start`. H3's documented entry point is
`ManagedBlamSystem.InitializeProject(InitializationType.TagsOnly, kitPath)`;
it works in the installed kit. The successful .NET host and native authoring
checks are recorded below. The earlier `NotImplementedException` was not
evidence that H3's authoring API was unavailable. The official `tool.exe`
provides `export-tag-to-xml`, `get-tag-field-value`, `patch-tag-field` and bitmap
commands. `export_shader_donors.ps1` exported all seven candidate stock shaders,
verified their source hashes unchanged and inspected the XML. Export requires
an absolute input tag path; field commands use a tags-relative path including
extension. Tool's XML has an unescaped `<unavailable>` resource placeholder;
the report parser escapes that token in memory only, preserving official output.
The first export attempts produced empty files despite exit 0, so the wrapper
now requires an actual parsed tag document. Evidence is in
`work/stock-h3-audit/h3-shader-xml/` and `h3-shader-xml-evidence.json`.

`inspect_shader_setups.py hrek` read all 102 Reach material authoring setups
through the official Reach API into `hrek-shader-setups.json`. These reveal
different terrain layer configurations; the donor list is still candidates,
not a blanket material substitution.

`author_foliage_trial.ps1` created the first isolated fresh H3 material under
the repository's H3EK `data/levels/custom/battle_canyon_fresh` and matching
`tags` directory. It copies stock Standoff `bunkerworld_treebranch.shader_foliage`
and `bunker_leaf.bitmap` authoring settings, imports the original Reach
`tree_boreal_leaves_diffuse.tiff` with official `bitmap_single`, and assigns that
image to the stock shader's base and alpha-test inputs via `patch-tag-field`.
No custom shader implementation or binary writer is involved. Tag-reference
values must use `path,bitm`: `.bitmap` values report success without updating
the field. This was caught by re-exporting and checking the saved shader, then
corrected. The script now asserts both resulting references.

`verify_foliage_trial.py` confirms that all other exported shader fields match
the stock donor exactly, and original image/bitmap/shader hashes are unchanged.
Official `export-bitmap-tga` returns a 512x512 RGBA image with the source's full
0..255 alpha range. Mean absolute RGBA channel differences from the source are
0.0943, 0.7599, 0.0649, 0.1990 (8-bit units); maxima are 9, 6, 9, 21. Evidence:
`foliage-trial-verification.json`. This is pixel/tag verification only: leaf
appearance, alpha cutoff and wind behavior still require actual rendering and
MCC review. Nothing is installed into MCC or converted to Xbox 360.

Reproduction: run the donor export wrapper; inspect Reach shader setups with
the bundled Blender Python and isolated packages; run the foliage authoring
wrapper only into absent trial targets (it refuses overwrites); run the verifier.
Use the repo-confined environment documented above. Continue with full source
metadata preservation and explicit H3 material setup choices before map compile.

## 2026-11-04: H3 authoring export, terrain trial and refreshed proof

`prepare_h3_authoring_scene.py` now configures the complete original import with
the unmodified Foundry coordinate transform and General-101's native authoring
properties. It preserves geometry counts, configures 1,060 instance names and
67 portals, and parents 115 existing collision proxies. It carries source face
selections into 67 H3 material-flag variants. Remaining physics and face metadata
are enumerated in `work/stock-h3-audit/h3-authoring-scene-report.json`, including
302 instances with separate convex physics proxies. These are outstanding work,
not accepted collision behavior. The scene is `battle-canyon-h3-authoring.blend`.

`export_h3_inspection.py` invokes General-101's unmodified ASS exporter and reader.
The 141,546,547-byte version-7 inspection export reopens with 157 materials,
543 unique objects and 1,247 instances. Source Blender hash and expected object
names were checked. This supersedes the earlier statement that no export had
occurred. It is not an official H3 compile, a verified round-trip rendering, or
MCC acceptance. Material assignments, water UV support, sky and lighting remain.

The stock shader inspection now covers 98 donor candidates. Original Reach
inspection includes 104 tags, including two inherited setups. Candidate input
coverage is recorded by `compare_shader_inputs.py`; matching input names alone
must never select a donor. `inspect_effective_shader_options.py` uses the
existing Foundry readers to resolve active options and default textures.

An inspection mistake was caught: passing strings to the generic ShaderTag
reader forced `.shader` on other shader groups and created placeholder siblings.
The reader now receives an explicit official Bungie TagPath and requires existing
tags. Eleven archive-absent placeholders were removed; two placeholder files at
real original paths were restored from the official `HREK.7z` archive. All 104
referenced original shaders matched archive CRC/size after restoration. The
additional glass `.shader` sibling was separately restored and verified at
13,071 bytes, CRC32 5FBD5D5A. Effective options were inspected again afterward.
Evidence: `reach-source-shader-integrity.json`,
`removed-inspection-placeholder-tags.json`, and `restore-original-*.log`.
No upstream addon was patched.

`author_terrain_trial.py` authors the original main terrain using stock Standoff
`ground.shader_terrain`: ten Reach TIFF images, sixteen texture assignments,
and twelve original uniform-tiling functions. Official Reach GetData exposes
the original function bytes; official H3 `patch-tag-field` sets the existing
function fields. No custom tag writer or shader logic is involved. Saved XML
matches those functions/references and preserves the donor's shader options.
Source-null inputs use corresponding stock H3 neutral textures, not unrelated
Standoff details. Evidence: `terrain-trial-report.json` and `terrain-trial/`.

The bitmap-template check caught three RGB normal images initially imported as
height maps. `correct_terrain_normal_imports.py` reimports those generated trial
bitmaps using official H3 **ZBrush Bump Map (from Bump Map)** usage. Enum fields
require their display string: numeric `17` reported success without changing the
setting. All three saved bitmap XML exports and import logs now confirm the
correct mode. The fresh authoring script applies and checks that setting too.
Official TGA exports preserve dimensions; mean absolute red/green differences
are approximately 1.0 to 7.1 out of 255, while blue differs much more. DXN output
is not byte-identical source RGB. This does not establish correct in-game normal
shading; keep the visual check open. Evidence: `terrain-normal-verification/`.
The donor uses diffuse terrain layers; Reach's source uses specular layers.
That appearance difference also remains explicit for MCC review.

`render_wip.py --authoring` renders the actual prepared scene with Blender
Workbench. It hides portals/collision children and nonrender face flags on
temporary preview mesh copies, without saving those copies into the authoring
scene. The initial capture exposed collision surfaces; the corrected render
filters 1,874 unique nonrender faces. Both final geometry views were inspected:
the central arch, surrounding rock walls and base structures are visible.
These clay views do not establish textures, foliage alpha, sky or lighting.
Native Blender outputs are `wip/h3-authoring-overview.png` and
`wip/h3-authoring-closer.png`. Refreshed textured source previews use the original
Reach readers and preview lighting; they are not H3 shader rendering.
Both refreshed textured views were inspected too: the arch, terrain, trees and
base structures carry source textures. White water surfaces (the deliberately
skipped upstream water fallback) and black rock patches remain visible and
unresolved. Neither view is an appearance acceptance. The material refresh
reported 101 successful readers and zero errors; the render ran in a separate
process because Foundry changes cwd to its editing kit. Pass subsequent script
paths absolutely. The authoring scene SHA256 remained
`62903acc54d4551396c0e3db700de2f5e2adb7d74c90ebe7d082cd09f51fb98c`
after all preview operations.

Still required: finish H3 material assignments and outstanding geometry metadata,
then official import/compile/light, user-driven MCC visual/gameplay review and
explicit approval. No 360 conversion or shared-install changes have occurred.
Rainbow/decorative laser import remains a proposal awaiting user approval.

### Additional terrain authoring and stock shader reuse

The next goal turn completed four additional terrain materials: cliff skybox,
cliff-rock skybox, ramps and cliff boulders. The first three match Standoff's
four-layer diffuse configuration. Cliff boulders match Guardian's three-layer
diffuse configuration. Guardian's original authoring parameter blocks had
different animation layouts and a missing legacy bitmap path, so the fresh
material uses Standoff's existing parameter layout and bitmap import settings,
with the fourth layer disabled through official Tool's option field. Its option
vector exactly matches Guardian and its template is stock `_0_0_0_0_0_0`, verified
in original Xbox 360 Guardian, Valhalla and Sandtrap inventories. No new shader
code, parameter block serializer, or replacement render function was written.

`author_terrain_trial.py --surface NAME` supports these explicit surface choices.
It verifies source/stock category names, source hashes, saved bitmap references
and copied original texture functions. Identical already-imported image bytes
are reused; mismatched or incomplete existing images fail. H3's neutral vector
bitmap was exported through official Tool and confirmed constant over all 4x4
pixels, so differing UV-transform block layouts on that neutral image can be
omitted without inventing a replacement function. Those omissions are recorded.

`apply_terrain_scalar_inputs.py` then assigns original scalar/color functions to
matching active stock inputs and binds the existing stock template. In this
batch it preserves the original Reach global brightness multiplier for all five
terrain materials; retaining the donor's multiplier would have unintentionally
darkened the imported textures. It verifies each saved function and confirms
the selected template in a stock 360 tag inventory. Native Tool block-resize
experimentation reported success without changing the block; it is not a usable
authoring method and no custom block writer was substituted.

The final saved-tag verification covers five terrain materials, 25 distinct
imported images, 77 texture assignments, 57 original tiling functions and five
original brightness functions. All recorded original image/tag hashes remain
unchanged. Evidence: `terrain-saved-input-verification.json`, the four
`ca_bcreek_*-terrain-trial-report.json` files, and `terrain-scalar-inputs/`.
These are authoring-field checks, not rendered appearance or collision approval.

An explicit official `compile-shader ... win` trial attempted to rebuild the
already supplied terrain shader code. It emitted a missing Durango compiler
error and PC/Durango constant-table mismatch errors even though its process
returned zero. This is not a successful compile. The five shared/template
binary tags touched by that attempt were restored from the official H3EK archive
and verified against its CRC and size. Evidence: `terrain-official-compile-shader.log`,
`stock-terrain-restore-archive.txt`, `restore-stock-terrain-binaries.log`, and
`stock-terrain-binaries-restored.json`. Reuse the supplied stock shader binaries;
do not patch shader code or fetch a private console SDK to address this trial.
It does not establish whether the complete official map build succeeds.

Stock option inspection now covers 23 terrain shader candidates and is extended
to the 93 ordinary shader candidates for the next building-material pass.
`inspect_h3_terrain_options.py --kind shader` uses official Tool XML exports;
categories missing from older stock authoring tags are explicitly marked as
defaulted, not silently claimed as source-authored. Source shader inspection
also records function-editor constants through the official Reach API, avoiding
hand-decoding curve data when determining whether a transform is an identity.

`compare_shader_configurations.py` identifies 47 of 90 ordinary Reach surfaces
with candidates matching the nine surface categories (albedo through parallax).
This is deliberately not a full shader match: Reach `misc=default` differs from
H3 `misc=first_person_never`, and Reach wetness/alpha-source and the later H3
categories remain separately reported. The wall-detail shader has Standoff
`bunker_plate_brackets` and `bunker_plate_wall` candidates; the main base-building
and glowing wall-detail setups have no exact nine-category candidate in this
set. Inspect active inputs and animation layouts next. Do not use obsolete
parameter-name overlap or these category matches alone to assign materials.

### Official H3 API and first building material (2026-11-04)

The [ManagedBlam initialization documentation](https://reclaimers.net/general/mod-tools/managed-blam/)
distinguishes H3's `InitializeProject` from Reach's `Start`. `ProbeH3Api.cs`
successfully loaded the stock Standoff wall shader in a .NET Framework x64
host built with `/highentropyva-`. A Python host initialized H3 but stalled at
tag reading and was stopped; it is not the production host. The installed
ManagedBlam DLL is copied unchanged next to the wrappers. No DLL patches,
custom tag serializer or shader implementation were introduced.

`ApplyH3ShaderPlan.cs` uses the official parameter/animation block operations,
reference setters, function-data setters and `TagFile.Save`. The first building
material, `ca_bcreek_bb_walldetail.shader`, reuses stock Standoff
`bunker_plate_wall.shader`. Ten original Reach inputs and eight original
functions are assigned, including separate detail scales X=4 and Y=8. Other
stock H3 inputs remain stock. Native Tool re-export checks references, parameter
types, animation types, input/range names, periods and function bytes.

The official API expands the donor's ten options to thirteen MCC options. The
first ten remain unchanged; appended distortion, soft-fade and miscellaneous
attribute-animation options are all disabled. The matching thirteen-option
template and its compiled shaders already exist in the official kit. No shader
code compilation or Xbox 360 conversion is needed for this authoring step.
The original ten-option counterpart remains recorded for the later approved
conversion stage. This normalization is an explicit MCC/360 difference.

Pixel checks caught unsuitable donor bitmap import settings: the reflection
template forced monochrome, while the detail image imported at brightness 45
instead of its original 116. Original Reach metadata identifies the base and
detail images as linear. `ApplyH3BitmapPlan.cs` sets source gamma 1, linear
storage, matching 2D usage and the native box mip filter through official API
fields. Both images are actually monochrome with alpha, so native A8Y8 retains
their channels exactly. All four RGBA channels match the source in native Tool
exports, including the base alpha range 0..239 and detail alpha range 80..255.

The reflection uses H3's stock DXT5 color format and native cube import. All six
128x128 faces match the occupied cells of the original 512x384 plate, after
accounting for Tool's face rotations, with mean channel errors below 0.44/255.
The source plate's top/bottom cells are in its first column, not the second;
the verifier follows the inspected source layout. No source pixels were edited.
Original source and stock donor hashes remain unchanged.

Reproduce with installed Blender Python: `inspect_wall_bitmaps.py`, build both
`ApplyH3ShaderPlan` and `ApplyH3BitmapPlan` using `build_h3_api.ps1 -Name ...`,
then `author_wall_detail.py` and `verify_wall_detail.py`. All paths are under
`tools/stock-h3-audit`; run from the repository. Evidence is in
`work/stock-h3-audit/wall-detail-trial/`, especially `report.json`,
`source-bitmap-settings.json`, `saved.shader.xml` and `pixel-verification.json`.

Limits: DXN normal direction/strength is still unverified, as are mip appearance,
world-space reflection orientation and the source xRGB versus stock sRGB
reflection response. The native face/pixel checks do not establish those.
Full H3 scene material assignment, official map compilation and user-driven MCC
review remain outstanding. No new Blender appearance claim is made from these
tag checks, and nothing has been converted to 360 or installed.

### Wall-family batch and native texture checks (2026-11-04)

`author_wall_family.py` extends the reviewed stock Standoff wall configuration
to all 38 matching source surfaces, including the first trial. This creates
37 additional ordinary materials, bringing authored material tags to 44
(38 ordinary, five terrain, one foliage). This is not 44 visually accepted
materials. Their nine selected rendering categories match the stock donor;
extra Reach-only inputs and retained stock inputs are listed per material.
There are no inherited parents in this batch and all active source images exist.

The official API saved 530 input assignments and 460 original functions.
Read-back checks include bitmap references, real fields, animation type names,
input/range names, periods and function data. Source alpha functions are retained
as alpha functions, not treated as color functions. Stock options and the
supplied compiled MCC template remain unchanged. The 197 recorded source-image,
source-tag and stock-donor hashes were rechecked unchanged.

The batch contains 77 distinct images: 36 base images, three detail images,
36 normal images and two reflection cubes. Color imports use native A8Y8 only
where all three source color channels are identical; other color inputs use
stock DXT5. Linear inputs retain gamma 1/linear storage. Older xRGB inputs use
the H3 sRGB import path, with that response difference explicitly recorded for
MCC review. An explicit xRGB trial changed source pixels and was not selected.
The first reflection cube keeps its previously verified stock cube import path;
the second cube needs its original linear curve. A generic gamma override on
the first cube failed pixel checks and was removed through the official API.

`verify_wall_family.py` exported and inspected every image. All 39 color/detail
images and twelve cube faces passed the pixel/alpha comparison gate. The highest
mean channel error among color/detail images was 3.285/255. This is compression
and channel evidence, not a visual-quality threshold. Native Tool's direct-save
fallback for uncompressed images is recorded; decoded image contents, sizes and
alpha are checked instead of treating a process exit code as proof. Reusing
exports requires each exported file to be newer than its current tag.

Reproduce: `author_wall_family.py --prepare`, `inspect_wall_bitmaps.py --family`,
build the two official API wrappers, then `author_wall_family.py` and
`verify_wall_family.py`. `--only-bitmap NAME` refreshes one import without
repeating shader authoring. Evidence: `work/stock-h3-audit/wall-family/report.json`,
`pixel-verification.json`, the native XML exports and per-command logs.

Normal fidelity remains unresolved. The already-installed Reach `tool_fast.exe`
supports native `export-bitmap-dds` and `export-bitmap-tga`; it successfully
exported the original wall normal without a Blender reader. The earlier normal
RGB extraction differs from that native XY evidence. An isolated normal import
probe and Microsoft's documented `texconv --reconstruct-z` were tested without
changing any production shader binding. The reconstruction preserved native XY
exactly, but the subsequent stock H3 import still changed the raw XY range.
That is not proof of equivalent normal direction/strength in the H3 shader.
Do not accept normal shading from the color/alpha checks or call the probe a fix.
No custom reconstruction algorithm or shader patch was written.

The unmodified Microsoft utility is pinned to
[DirectXTex may2026](https://github.com/microsoft/DirectXTex/releases/tag/may2026),
at `work/stock-h3-audit/upstream/DirectXTex-may2026/texconv.exe`.
SHA256, checked against GitHub's release asset digest:
`dcfdec10244e02cf5037fba089c55fb7e1326b1c8181742d77d15fa5cb5eef06`.
The [upstream command documentation](https://github.com/microsoft/DirectXTex/wiki/texconv)
describes normal reconstruction. Probe inputs/outputs/logs are in
`wall-family/native-reach/`; they are not a production normal replacement.

The map still needs remaining materials, geometry/physics/lighting metadata,
official map compilation and user-driven MCC review. No 360 conversion or
shared-install write has occurred.

`render_wip.py --textured --buildings` produced two additional native Blender
WIP views of the original base panels and light strips. Both final images were
inspected. The initial generic camera positions were occluded by cliffs; the
camera was moved to the canyon-facing side without hiding or modifying geometry.
The close view clearly shows the entrance, wall-panel textures and strips.
The wider view also exposes below-ground geometry at its lower edge, and preview
shadows remain dark. These are source-material/studio-lighting previews, not H3
shader or gameplay captures. Images: `wip/buildings-overview.png` and
`wip/buildings-closer.png`. The source Blender file remains unchanged at SHA256
`30805ebe52e32b764a143ffe5abf6e60124f0e2cb7964ec1b8295579f171d43d`.

### Stock light strips and physical-material names (2026-11-04)

The additional stock-map search read Construct, The Pit (cyberdyne), High Ground
(deadlock), Epitaph (salvation), Snowbound, Last Resort (zanzibar) and Sandbox.
All seven original cache hashes were unchanged. Together with the earlier
Standoff, Guardian, Valhalla and Sandtrap inventories, 658 original level-shader
paths have corresponding editing-kit tags. Native option inspection finds an
exact match across the nine compared rendering categories for 72 of the 90
ordinary Reach shaders. This is a candidate inventory, not approval of every
candidate or proof that the other 18 have no stock alternative. The search so
far covers level shaders; stock object shader configurations remain to inspect.

`ReadH3ShaderConfigurations.cs`, `inventory_additional_shaders.py` and
`match_stock_shader_inventory.py` record those native options and provenance.
Evidence is in `stock-shader-configurations.json`,
`stock-shader-map-provenance.json`, `expanded-stock-shader-matches.json` and
`additional-stock-map-integrity.json` under `work/stock-h3-audit/`.

Guardian's `guardian_techstrip.shader` supplies the matching stock configuration
for nine red, blue and white light surfaces. Its original Xbox 360 ten-option
vector is `0,0,0,0,0,0,5,0,0,0`; the MCC tag retains that vector and adds three
disabled options. Original-cache read evidence is `guardian-light-options.txt`.
`author_wall_family.py --family lights` saves 70 input assignments and 28 source
functions, using eight unchanged Reach images. All nine materials pass native
field checks. This brings authored tags to 53: 47 ordinary, five terrain and one
foliage. The 29 recorded light-family input/donor hashes remain unchanged.

The official XML exporter omits the 872-byte function block for the white panel's
animated self-illumination detail map. The saved native data is intact. The
authoring wrapper now reopens each saved tag with ManagedBlam and compares every
function byte; the XML omission alone is never accepted as proof. Independent
`--verify` processes rechecked all 47 ordinary shaders after physical-material
updates. The integer input with display name `int/bool` is selected from native
fields because `/` is interpreted as a path separator by `SelectField`; its
saved value is checked in the XML as well.

`verify_wall_family.py --family lights` inspected all eight native texture
exports. Color and alpha passed the existing pixel-comparison gate, with maximum
mean channel error 1.215/255. Six inputs retain linear curves and two legacy xRGB
inputs use the documented H3 sRGB import choice. These textures are not shared
with the earlier wall batch. Evidence is in `lights-family/report.json`,
`pixel-verification.json`, plans, native readbacks and command logs. Light color,
animation and bloom still require actual MCC inspection; Blender source previews
do not establish those results.

The donor-copy audit also caught physical-material names still set to stock
donor defaults, including metal on the distant-cliff shader. The native Reach
reader now inventories outer material-name fields. `author_physical_materials.py`
reads original Standoff's global-material names through unmodified TagTool,
checks every selected name there, then uses `ApplyH3MaterialNames.cs` to assign
only existing H3 names through the official API. The native H3 globals are also
checked before any write. All 52 applicable shaders required a correction:
47 ordinary shaders and five terrain shaders. Their 67 material-name fields now
match the source names exactly, using six existing stock materials. The foliage
source has an empty name, so its selected stock `soft_organic_plant_leafy` remains.
No new physical-material definition or global tag was authored.

Native reopen checks confirm all assignments. The original Standoff cache,
53 original Reach shader tags and H3 globals remain unchanged. Evidence:
`physical-material-plan.json`, `physical-material-report.json`,
`physical-material-evidence.json`, `standoff-global-materials.txt` and its cache
integrity report. **Run `author_physical_materials.py` after any donor-copy
authoring batch**, since copying a donor resets these outer fields. It is an
idempotent native authoring step. Impact effects/audio and terrain material
selection still require MCC gameplay verification.

No map compilation, MCC acceptance, 360 conversion or shared-install change has
occurred. Remaining geometry, material configurations, normal fidelity and
effects review are still open. The native API workflow follows the
[ManagedBlam documentation](https://reclaimers.net/general/mod-tools/managed-blam/).

### Additional panels, illumination and bark (2026-11-04)

The stock inventory now includes ordinary shaders used by objects as well as
level geometry in the same eleven original map inventories: 1,286 unique paths,
all present in the editing kit. This adds five exact nine-category candidates,
bringing the candidate count to 77 of 90 ordinary Reach shaders. The remaining
13 lack a match in this inventory; that does not prove no stock alternative
exists. Existing inventory/match reports were refreshed, and the seven additional
cache hashes again remained unchanged.

`material_families.json` records explicit source lists, stock donors, expected
image counts and active texture roles for eleven reviewed batches. New batches
cover thirteen surfaces: three glowing wall/railing materials, two simple
diffuse surfaces, a light-band material, computer/panel illumination, two
ceiling/panel materials, a wall light, tree bark and a thin light strip. Their
nine stock donors are the existing `monitor_innards`, Standoff `road`,
`light_techbit_cool`, `bunker_tech_computer`, `guardian_int_light_cool`,
`bunker_ceiling`, `monitor_base`, `box_cardboard` and
`deadlock_light_warm_illum` shaders. Original 360 ten-option vectors were checked
against MCC, including the miscellaneous option; the three MCC additions are
disabled. A first-person-sometimes Elite candidate was not selected when a
stock world-light configuration was available. Read-only query evidence is in
`next-materials-*.commands` and `.txt` under `work/stock-h3-audit/`.

The new thirteen shaders have 122 native input assignments and 89 source
functions. All passed native field/function readbacks, including separate
verification after physical-material authoring. The total is now 66 authored
tags: 60 ordinary shaders, five terrain shaders and one foliage shader. This
does not establish final Blender assignments or H3 rendering acceptance.

The batch uses 28 distinct images; 21 are newly imported. Shared images reuse
an existing native tag only when its verified current hash, source pixels and
import settings match. Eleven image references took this reuse path across the
nine batches. A donor that omits an explicit bitmap input uses that input's
native H3 option-default bitmap as the import seed; there is no fabricated tag.
All new color/alpha exports passed the existing comparison gate. New normal
imports still need the normal-fidelity/MCC checks already noted above.

The thin-strip emission import initially had no mipmaps because the stock donor
bitmap set `max mipmap level` to 1. The original Reach texture uses limit 0 and
has eight mip levels. Setting the existing H3 field through the official API
restored all eight levels, and the pixel check passed. The source inspector now
records mip limits/counts; authoring preserves that field and verifies the
resulting count. A complete count audit covered 117 image references / 106
distinct ordinary-family images, with no source/H3 count differences. This
checks mip presence, not rendered mip filtering or normal strength.

Current evidence: `material-family-checkpoint.json`, `family-mipmap-audit.json`,
each `*-family/report.json`, `pixel-verification.json`, native XML exports and
readback logs. All 309 unique recorded source/donor hashes remained unchanged,
and every current imported bitmap still matched its verified native tag hash.
Physical names were reapplied: 64 shaders use exact existing stock names; the
two empty source-name cases retain their selected H3 donor material.

Reproduce a batch with `author_wall_family.py --family NAME --prepare`,
`inspect_wall_bitmaps.py --family --family-name NAME`,
`author_wall_family.py --family NAME`, then
`verify_wall_family.py --family NAME`. Build `ApplyH3BitmapPlan` after updating
the mip-limit wrapper. Run `author_physical_materials.py` after donor-copy batches.

Outstanding: inherited source inputs, the remaining configurations, retained
donor scalar/color defaults where source overrides are absent, normal fidelity,
and final Blender/export shader naming all need resolution before acceptance.
The [exporter's material documentation](https://c20.reclaimers.net/h3/source-data/h3-materials/)
describes native name/collection lookup; setting only Foundry's shader-path
property is insufficient for the ASS export route. Geometry, effects and actual
MCC testing remain pending. No shader code, serializer, engine patch, 360
conversion or shared-install change was introduced.

### Native defaults and inherited source functions (2026-11-04)

The donor-default review is now applied to all 60 ordinary shaders. Native
read-only inspection covered 39 original Reach option tags and 67 H3 option
tags. `ReadH3ShaderConfigurations.cs` also supports option-default inspection;
`inspect_reach_option_defaults.py` reads the corresponding Reach fields. Color
defaults are compared as the API's native channel arrays, with no custom color
decoding or function-data construction.

For 226 inputs without a source override, the relevant native default fields
match exactly between Reach and H3. Unrelated donor overrides are removed for
those inputs, allowing the existing H3 option defaults to apply. Twenty-two
source scalar defaults differ from H3: seventeen `specular_coefficient` values
are 1 instead of 0, four `analytical_specular_contribution` values are 0.1 instead
of 0.5, and one `area_specular_contribution` is 0 instead of 0.5. These values
are entered with the official basic-function editor. The native API generates
the function data; no byte writer, custom curve encoder or shader code is used.

`shader_defaults.py` plans these authoring operations from the inspected native
fields. `ApplyH3ShaderPlan --update` applies them to existing fresh tags, leaving
their texture bindings and physical-material names intact. Native reopen checks
confirm the scalar functions' basic type, value, non-ranged state, input names
and period. Separate verification confirms that all 577 original source
functions remain byte-identical. Current XML exports also confirm unchanged
stock option vectors and corrected physical names. All 106 bitmap tags retain
their previous verified hashes; no textures were reimported for this step.

Seventy-two H3-specific input slots retain the selected stock behavior, including
six engine-supplied dynamic-environment texture slots. They have no corresponding
Reach input name and are not fabricated as source data. Existing per-material
reports distinguish these retained inputs from matching option defaults and
the 22 explicitly authored scalar defaults.

`apply_shader_defaults.py` performs this update and verification for existing
batches. The normal `author_wall_family.py` path now applies the same decisions
before saving new shaders. The `monitor_base` family was reauthored through that
path as a regression check, including its native default function and reuse of
three verified bitmap tags. Physical-material names were reapplied afterward.
The 309 recorded source/donor hashes and all inspected option-tag hashes remained
unchanged. Evidence: `reach-option-defaults.json`, `h3-option-defaults.json`,
`default-correction-inventory.json`, `default-correction-source-hashes.json`,
`default-correction-checkpoint.json`, `default-corrections/` and the refreshed
family reports under `work/stock-h3-audit/`.

The [documented ManagedBlam function-editor operations](https://reclaimers.net/general/mod-tools/managed-blam/)
and the pinned, unmodified Foundry `ShaderTag._setup_function_parameters` method
provide the native authoring path. The H3 API probe confirms that the same basic
function and clamp-value properties are supported by this installed H3 kit.

`inspect_inherited_functions.py` ran inside background Blender with unmodified
Foundry. It checked all seven source shaders with parent templates: 135 effective
functions, of which 71 come from an ancestor. Foundry's own effective-value reader
was compared with its complete function reader on the selected original entry,
including periodic/curve controls and colors, rather than comparing only names.
The report retains the exact original native function bytes and their source
tag/entry provenance. All 22 touched source files remained unchanged. Evidence:
`inherited-function-inspection.json` and `.log`. This establishes function
inheritance for subsequent authoring; it does not yet authorize treating bitmap
inheritance or the remaining shader configurations as resolved.

The native source inspection also exposes non-default texture filter/flag and
sharpening controls. These still need a semantic comparison with H3 controls;
raw numeric fields are not being copied across games without that check. Final
Blender/ASS shader assignment, normals, unresolved materials/effects, geometry
metadata and MCC visual/gameplay review remain open. Native field checks do not
establish the rendered specular response. No new Blender render or MCC capture
was produced in this checkpoint, and the map has not been compiled or converted
to 360.

### Eight additional materials and active source inputs (2026-11-04)

The saved-tag total is now 74: 68 ordinary shaders, five terrain and one foliage.
The new ordinary families are `metal_detail` (four surfaces), `panel_detail`,
`rock_small`, `giant_bark` and `inherited_tech_bank` (one each). Their stock donors
are Salvation's panel-deco trim, the stock tripmine metal, Standoff's tech
monitor, Standoff's tree bark and Standoff's tech bank. Original Xbox 360 option
vectors were compared with the corresponding MCC tags before authoring; the
selected misc option and the additional MCC options are zero. These are native
stock configurations with Reach textures, not newly generated shaders.

`source_shader_inputs.py` selects existing original inputs using the previously
verified Foundry inheritance report. The first parented material is
`ca_bcreek_metal_oni_tech_a_illum_light_a`: four functions originate in its
brushed-aluminum parent template. Their bytes and controls pass native readback.
Its active image references are local to the child; this batch does not establish
rendered correctness for inherited texture controls. Parent/source hash checks
remain mandatory. Source rows with obsolete parameter types are distinguished
from the type declared by the active native option.

Twenty-six previously authored surfaces contained an inactive Reach
`analytical_anti_shadow_control` field. It is absent from their active Reach
option definitions and should not override the H3 setting. Those surfaces were
reauthored using active source inputs only. The selected H3 donor's shadow
control is retained and checked against the donor export. Five new surfaces
also exclude that stale field. This supersedes the earlier 577-function count:
the current 68 ordinary shaders preserve 650 selected source functions, with
253 matching native defaults and 22 scalar defaults entered through the
official function editor.

The tripmine donor contains stale duplicate input entries. The official-API
wrapper now keeps one correctly typed entry per authored input and removes the
other same-name entries from the fresh target only. Native reopen requires
exactly one match. All 68 current ordinary shaders passed this check; no stock
donor was edited. This prevents XML and native readers from inspecting different
entries under the same input name.

Detail normal images use the same official bitmap-import path as base normals.
They are explicitly excluded from color-error acceptance: direction and strength
remain unverified. An existing mip cap may be retained when its verified saved
count equals the source count and all other import settings and source/tag hashes
match. The bitmap metadata lookup was also corrected to use the source path
rather than a shadowed XML variable; newly imported images exercised this check.

The current checkpoint covers 142 image references, 124 unique bitmap tags and
374 source/donor hashes. New color/alpha exports pass the existing pixel check,
all source mip counts match, and all current bitmap hashes match their native
export evidence. Physical names were reapplied through the official API: 71
surfaces use exact existing Standoff names; three empty source names retain
their stock donor choice. Evidence is in `active-input-checkpoint.json`, the
five family reports and pixel-verification files, `*-stock-options.txt`, and
the physical-material evidence under `work/stock-h3-audit`.

Next: finish the remaining material configurations and Blender/ASS assignment,
then geometry metadata and the official H3 MCC compile. Normal fidelity,
texture filtering, effects and actual MCC visual/gameplay testing remain open.
No new Blender preview, MCC run, 360 conversion or shared-install change is
claimed by this saved-field checkpoint.

### Stock search expansion and Blender export bindings (2026-11-04)

The additional stock-cache search now includes every remaining map in the
available original H3 multiplayer installation, plus mainmenu and shared.
Together with the initial four maps, 25 caches supply tag-name inventories.
`shared.map` returned no standalone tag entries; it was hash-checked but this
does not establish a complete shared-resource dependency audit. Native MCC
inspection now covers 2,537 stock-provenance ordinary shader tags. Three
mainmenu player-color shader paths are absent from the kit and remain recorded
as missing. Exact nine-category matches remain 77 of 90 source ordinary
shaders. A separate search through stock ordinary render-method-template names
also found no exact configurations for the same 13 unmatched sources. This
does not authorize stripping their features or inventing replacement shaders.

Five more ordinary materials were authored: the two `sentinel_metal` surfaces,
`forerunner_metal`, and the two `inherited_cook_metal` surfaces. Donors are the
stock Sentinel constructor, Standoff man-cannon metal and Orbital metal backwall.
The expanded inventory supplied the Orbital world-material setup; the earlier
candidate list was restricted to weapon or water materials for those sources.
`prepare_family_donors.py` verifies original-cache option vectors, unchanged
cache/tag hashes, world misc settings and zero additional MCC options, then
exports the native tags. It automates TagTool and official Tool commands only.

The two new parent-template materials preserve 11 and 12 inherited functions
respectively, plus their original inherited detail texture reference. One
native input needed a storage-type review: source `env_tint_color` uses ARGB
storage while the active option declares RGB. The official stock Sentinel
shader uses that same ARGB storage for its active per-pixel environment tint.
Authoring retains this original storage and function bytes rather than rewriting
color data or removing alpha. Other type mismatches still fail the check.

Totals are now 73 ordinary, five terrain and one foliage material. Native
readback verifies 714 selected source functions, 268 matching option defaults
and 23 scalar defaults entered through the official editor. The checkpoint
covers 156 image references / 136 distinct bitmap tags and 415 source/donor
hashes. New native color/alpha exports pass the existing checks; normals remain
unverified. Physical-name authoring now covers 76 exact stock names and three
empty-source cases retaining their donor choice.

`inspect_h3_material_assignments.py` inspected every used Blender face material:
157 material variants, 102 distinct source shader references, no unassigned
faces. The source `invalid.shader` is used by `box003` (six faces) and
`emissive_sun` (32 faces); these are pending metadata/material review, not
silently replaced. Special sky, portal and seamsealer materials retain their
native names.

Following the exporter's documented shader lookup, `assign_h3_materials.py`
sets short material name overrides and stages byte-identical copies of the
reviewed tags in the fresh asset's `export_shaders` directory. It preserves
face flags, geometry and original source shader provenance. No global shader
collection edit is needed: these names are intended for asset-root lookup.
Rerun this staging step after updating an authored tag; exports reject stale
tag copies by hash. The saved working scene is
`work/stock-h3-audit/battle-canyon-h3-materials.blend`.

The unmodified community ASS exporter and reader verified 79 bindings across
115 used material variants. The full ASS remains at 157 materials, 543 unique
objects, 1,247 instances and 247,855 triangles, matching the prior inspection
counts. Another 23 source shaders / 39 used variants remain explicitly pending.
Evidence: `h3-material-assignment-inspection.json`, `h3-material-bindings.json`,
`h3-bound-ass-inspection-report.json`, the family reports, and the refreshed
`active-input-checkpoint.json` under `work/stock-h3-audit`. The optional add-on
lxml bitmap-generation warning does not establish a failed binding; no bitmap
generation was requested in this Blender naming/export step.

Native H3 Tool lookup, map compilation, normal/reflection appearance, unresolved
materials/effects and collision/physics metadata still require work. No MCC
visual acceptance, 360 conversion or shared-install change occurred.

### Complete terrain coverage and approved cliff reflection (2026-11-04)

`inventory_terrain_shaders.py` read 80 stock-provenance terrain tags through the
official H3 API. All nine source terrain configurations now have exact matches
across H3's six categories; Reach's additional default wetness category remains
separate. Read-only inspection and family authoring wrappers now accept the
native `rmtr` group as well as ordinary shaders. No shader code or tag serializer
was introduced. Original-cache option vectors were checked with TagTool before
the selected native donors were used.

Four new surfaces are authored: arch, boulders2, cliff_walls and tunnels. Donors
are Avalanche's rock-boulder terrain, Sandtrap's laminate-gradient terrain and
Last Resort's cliff terrain. The main ground trial was also replaced with Last
Resort's beach terrain configuration. The earlier Standoff setup used diffuse
lighting only on all four ground layers; the selected stock beach configuration
matches the source's specular-enabled four layers. The older trial authoring
and scalar-update scripts now reject/skip this superseded path so they cannot
silently restore the initial options.

The cliff source refers to missing `ca_bcreek_cubemap.bitmap`. It is absent from
the local source tags and from an exact path listing of the official HREK
archive. The original shader's postprocess texture list is empty, so it offers
no compiled fallback reference. The user explicitly approved the existing
Reach `cubemap_creek.bitmap` used by the arch/boulders. That single substitution
is recorded in `material_families.json`, the saved native plan and the family
report. Other missing references still fail instead of receiving a fallback.

The five terrain families preserve 132 original source functions and use 48
matching native defaults. All saved texture references, function bytes and
controls, and stock options pass readback. The 73 ordinary shaders also passed
the updated wrapper's read-only checks. The combined family checkpoint covers
204 image references / 160 distinct bitmap tags and 503 source/donor hashes.
This is family coverage; four earlier terrain shaders and foliage retain their
separate evidence. Normal direction/strength and all rendered lighting remain
unverified in MCC.

One source detail bitmap (`deadlock_rock_granite_detail`) contains six mip levels
despite an unlimited authoring cap. Current H3 Tool initially produced eight.
The native H3 cap includes the base image, while the saved mip count excludes
it: a cap of six produced five, and seven produced the required six. Authoring
now preserves a shorter compiled source chain using the official cap field and
checks the saved count. No pixels or mip levels are manufactured by a custom
processor. The 256x256 source image and its native count remain intact.

There are now 83 authored tags: 73 ordinary, nine terrain and one foliage.
Physical names were reapplied and reopened: 80 use exact stock names and three
retain their selected donor choice because the source name is empty. The
Blender scene has 83 short-name bindings across 121 used material variants;
19 source shaders / 33 used variants are still unresolved. After changes to
native tags, the byte-identical export copies were refreshed.

Fresh native Blender Workbench WIP renders are saved under
`work/stock-h3-audit/wip/h3-authoring-*.png` and `h3-buildings-*.png`. All four
views were inspected: the overall canyon/arch geometry and the base's facade
and doorway details are visible. Workbench renders are deliberately untextured
geometry evidence, not H3 material or brightness acceptance. The building
camera directions now use the same coordinate rotation as the authoring scene.
Rendering uses temporary preview copies and does not save over the working
scene. No desktop capture or input was used.

Evidence: `expanded-stock-terrain-matches.json`, `stock-terrain-configurations.json`,
the five `terrain_*-family` reports and native pixel exports,
`missing-cliff-cubemap-archive.txt`, `active-input-checkpoint.json`,
`h3-material-bindings.json` and native Blender capture-info files under
`work/stock-h3-audit`. Remaining materials/effects, source texture controls,
physics/collision metadata, native map import and MCC validation are still open.

The refreshed unmodified ASS export also passed its reader checks with all 83
bindings present, 157 material variants, 543 unique objects, 1,247 instances and
247,855 triangles. `prepare_family_donors.py` now reads the selected native
option defaults as part of preparation, so new terrain families do not depend
on a separate manual metadata-merge step. This reads official API fields and
does not modify stock tags.

## Seven additional stock material assignments (2026-11-04)

The caustics use Standoff's stock power-drain active shader configuration; the
sky panel uses High Ground's lake shader. The source caustics image is shared
by its two noise inputs and alpha mask. The sky panel uses its original image
for both base color and material texture, with the original material-texture
boolean enabled. These bindings are preserved without channel packing or image
edits. All four native image exports pass color/alpha comparison; normal
direction and reflection orientation still require rendered review.

Four smooth source materials have bump mapping off. Two use Standoff's
`bunker_plate_brackets` shader; two use the stock Sentinel Constructor shader.
The other eight shared categories match. These native donors have standard
bump mapping, so their patterned normal is replaced with the official option's
existing `shaders/default_bitmaps/bitmaps/default_vector.bitmap`. Native Tool
exports verify its DXN format and constant X/Y values of 128. No new normal
texture is generated. Inactive source bump functions are excluded from this
H3-only input. This uses stock H3 shader controls and assets; rendered
highlights remain a specific MCC check.

The decorative trim uses stock `bolt_thrower_shiny`. Its misc option is
`first_person_sometimes`, not `first_person_always`. Original Standoff's Spiker
world render model explicitly references this shader. Preparation now requires
that original-cache witness for this option rather than rejecting all nonzero
misc values. The donor's complete option vector is retained. This establishes
stock world-model use, not acceptance of the new BSP material in MCC.

There are 90 authored tags: 80 ordinary, nine terrain and one foliage. Native
readback covers 812 ordinary source functions, 24 scalar defaults entered with
the official function editor and 284 matching ordinary defaults. Including the
five generic terrain families, the checkpoint verifies 944 source functions,
222 image references / 170 distinct bitmap tags, 543 unchanged source/donor
hashes and no duplicate authored inputs. The four earlier terrain materials and
foliage retain their separate evidence. Physical material names were reapplied:
86 exact source names exist in stock Standoff, and four empty source names
retain their selected stock donor choice.

The refreshed Blender scene has 90 short-name bindings across 137 used variants.
Twelve source shaders / 17 variants remain unresolved: sky rocks/towers, arch
rock, exterior/bridge/tunnel glass, two circular illuminated panels, Forge
panel, river water, shared glass and the source invalid material on two metadata
objects. Two fresh native Workbench base views were inspected individually.
They show actual facade/doorway geometry, not H3 shading or lighting acceptance.

`inspect_stock_water.py` compares all five water shaders in the available
original-360 cache inventories against native MCC tags and verifies the original
cache option vectors and unchanged hashes. Longshore's `dock_water_2` matches
all eight shared Reach river options. Reach also has a separate `detail=repeat`
category; its semantics and the unmodified exporter's UVW limitation remain
open. No water substitution or authored water shader is claimed.

Evidence is in the `caustics`, `sky_panel`, `smooth_phong`, `smooth_cook` and
`deco_trim` family reports, their donor-integrity/native-image logs,
`stock-water-comparison.json`, `active-input-checkpoint.json` and
`h3-material-bindings.json` under `work/stock-h3-audit`. Documentation consulted:
[official H3 material-texture controls](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/shaders/materialtexture)
and [bump mapping controls](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/shaders/bumpmapping).
No MCC map test, approval, Xbox 360 conversion or shared installation change.

The refreshed unmodified ASS exporter and reader passed with all 90 bindings,
157 material variants, 543 unique objects, 1,247 instances and 247,855 triangles.
The bound source blend remained unchanged. Optional upstream `lxml` bitmap-
generation warnings do not validate or invalidate the independently verified
official Tool bitmap imports; this export does not request bitmap generation.

## Arch parallax and remaining-feature review (2026-11-04)

The arch rock now uses Standoff's existing Foundry bridge shader
`objects/levels/dlc/warehouse/shaders/dlc_ware_bridge1.shader`. Its simple
parallax, detail normals, specular mask and material model match the source.
The extra H3 environment reflection is suppressed through the documented
`environment_map_specular_contribution=0` control, entered with the native
function editor. Reach's stored contribution was dormant because its selected
environment option is `none`; copying that dormant 0.2 value into a reflective
H3 donor would incorrectly add reflections. No shader implementation changed.

The original `rock_craggy_parallax.bitmap` existed but had no extracted image.
Unmodified Foundry `BitmapTag.save_to_tiff(blue_channel_fix=False)` extracted it.
The source tag hash is unchanged. Official H3 Tool imported it with its native
Height Map usage, retaining the source pixels and nine mip levels. All five
arch images passed native export checks. The source height-scale function
(approximately 0.01), texture transforms and 13 selected source functions are
preserved. One additional native zero-valued control disables H3 reflections.

The checkpoint now covers 81 ordinary materials, 825 ordinary source functions,
24 scalar default functions and 289 matching ordinary defaults. Combined with
the five generic terrain families: 957 source functions, 227 image references,
171 distinct imported bitmap tags and 551 unchanged source/donor hashes. The
native zero-reflection control is separate from the source/default counts.
Physical names were reapplied: 87 exact stock names and four retained empty
source cases. The Blender scene now has 91 bindings across 138 used variants;
11 source shaders / 16 variants remain pending. The last complete ASS check
covers the previous 90-binding scene; no new full export or map build is claimed.

The original glass opacity image was extracted through the same unmodified
Foundry path. It differs materially from the alpha channel already used for
specular control, and its UV scale is 2 rather than 1. Directly using the
unchanged base image for H3 transparency would be wrong. The detailed
[glass proposal](GLASS-MATERIAL-PROPOSAL.md) records a stock-H3 approach and its
exterior view-angle limitation. The user has been asked to decide; no glass
repacking or shader authoring is authorized by the proposal alone.

Read-only Blender inspection confirms the 38 source `invalid.shader` faces
are not visible artwork: six are sphere-collision-only (`box003`), and 32 are
lightmap-only (`emissive_sun`). Their existing flags are preserved; the latter's
emission metadata still requires native H3 authoring. The three water meshes
have only two UV channels. The documented H3 workflow uses four, so the current
scene is not water-export-ready. Mapping the original wave/shape inputs remains
open; no missing channels or W values have been invented.

An additional read-only inventory found 147 original-cache halogram shader
names, of which 146 exist in the available MCC kit. The missing native tag is
`objects/levels/multi/salvation/shaders/plasma_large_red.shader_halogram`.
None of the inspected candidates matches default albedo, detailed illumination
and alpha blending together for the two sky materials. This does not establish
that stock H3 has no viable sky approach, and no additive-only substitute was
assigned. Native read support now includes the halogram group; no halogram
writer or shader compiler was added.

Evidence: `arch_rock-family`, `arch_rock-donor-integrity.json`,
`arch-rock-original-height-extraction.json`, `extra-reach-bitmap-extractions.json`,
`pending-material-input-review.json`, `pending-geometry-inspection.json`,
`stock-halogram-configurations.json`, `stock-unlit-sky-candidates.json`, and
`active-input-checkpoint.json` under `work/stock-h3-audit`.

References: [native H3 reflection controls](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/shaders/materialmodel),
[native H3 height maps](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/shaders/parallax),
and [the exporter's H3 water workflow](https://reclaimers.net/h3/guides/map-making/level-creation/blender-level-modeling/blender-level-creation-additional-info/).


## Stock unlit sky and approved glass preparation (2026-11-04)

Native inspection of Blackout's and Sandbox's stock `space.shader` tags found
an existing black `albedo_color` function. This is a usable stock setting for
Reach's two unlit sky materials: retain that donor function, keep source alpha
functions unchanged, and keep the separate Reach self-illumination inputs.
The stock H3 diffuse-only model itself still receives diffuse lighting; the
zero base RGB suppresses that contribution. No material code, shader compiler
or function encoder was added. This is an authoring candidate that still needs
actual MCC verification, including distant rocks, transparency and fog.

Both sky materials now use the Blackout donor. Original-360 options and source
cache hashes were checked through TagTool; native MCC donor color/functions
were read through the official API. Native readback preserves the original
source alpha and illumination functions and reuses the donor's black RGB
function. Both original Reach bitmap imports passed pixel and mip checks.
`ReadH3ShaderConfigurations` now optionally reads native animation controls,
colors and function bytes without saving tags. `prepare_family_donors.py`
regenerates the sky witness when preparing the `unlit_sky` family.

The checkpoint now has 93 authored/bound tags (83 ordinary, nine terrain,
one foliage), across 140 used variants. Nine source shaders / 14 variants
remain pending. Ordinary source-function checks cover 836 functions; two
additional stock color controls are counted separately, as is the arch's
zero-reflection control. Including five generic terrain families yields 968
source functions, 229 image references, 173 distinct images and 559 unchanged
source/donor hashes. Physical material names: 87 exact stock matches and six
retained empty-source cases. The full ASS check still covers the earlier
90-binding scene; no updated full export or map build is claimed.

The user approved the glass proposal. Blender prepared the packed image using
its standard compositor nodes after native source inspection confirmed both
images are linear. Every opacity pixel is preserved exactly, with maximum RGB
rounding error 1/255. Official H3 Tool imported the packed image as linear a8y8
with nine mip levels; every exported RGBA pixel matches that prepared image.
Source images and tags remain unchanged. The separate original specular alpha
must still be assigned at its original UV scale when the three glass shaders
are authored. Glass shader assignment, exterior H3 behavior and MCC appearance
remain pending; see [the approved proposal](GLASS-MATERIAL-PROPOSAL.md).

Evidence: `unlit_sky-family`, `unlit_sky-donor-integrity.json`,
`stock-sky-native-functions.json`, `active-input-checkpoint.json`,
`assign_h3_materials-current.log`, and `glass-channel-preparation/` beneath
`work/stock-h3-audit`.

Official documentation: [H3 material model](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/shaders/materialmodel)
and [self-illumination inputs](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/shaders/selfillumination).


## Approved glass and panel assignments (2026-11-04)

All three approved glass surfaces are now authored and bound. Native Reach
inspection and native H3 readback prove the packed opacity texture retains its
2x source transform, while the unchanged original specular alpha remains at 1x.
Normal/cubemap references and source functions are preserved. The exterior uses
the stock Cold Storage Fresnel coefficient, steepness and bias unchanged. Its
steepness override (15) is deliberately retained instead of being removed by a
same-named Reach default (5). These are saved-field checks, not MCC appearance.

The user separately approved stock H3 local reflections for both circular
panels and the Forge panel. The selected Standoff Chopper and Rat's Nest metal
shaders match the other eight shared categories. All artwork/detail/glow inputs
are retained; the old fixed Reach noise cubemap is intentionally replaced by
H3 cluster cubemaps. Official Tool cubemap generation remains an MCC build step.
Native cache options, donor hashes, imported pixels and original mip counts
passed. See [the approved panel decision](PANEL-REFLECTION-PROPOSAL.md).

The Blender scene has 99 authored tags (89 ordinary, nine terrain, one foliage)
bound across 149 used variants. Three source tags / five variants remain:
river water; shared dirty glass (two variants); invalid shader metadata (one
collision-only and one lightmap-only variant). Geometry metadata, collision,
effects, scenario preparation and MCC build/testing remain separate unfinished
work; the material count does not establish a playable map.

The native checkpoint covers 912 ordinary source functions, 29 source-default
scalar corrections and 307 matching ordinary defaults. Including five generic
terrain families gives 1,044 source functions and 355 matching defaults. There
are 244 family image records covering 181 original-image imports; the packed
glass bitmap is checked separately. The checkpoint verifies 602 input/donor
hashes and no duplicate authored input names. Physical materials: 92 exact
stock names and seven retained empty-source cases.

A native Blender Workbench assignment preview is saved at
`work/stock-h3-audit/wip/h3-material-assignments-bridge.png`. Cyan identifies
assigned glass in the actual geometry; these diagnostic colors are not H3
material appearance. The render does not modify the saved authoring scene.
The initial general-base views did not expose the highlighted surfaces, so the
camera was moved to the actual glass-bridge region before choosing the proof.

Evidence: `glass-material-verification.json`, `glass-native-source-controls.json`,
`panel-reflection-proposal-evidence.json`, four material-family reports,
`h3-material-bindings.json`, `active-input-checkpoint.json`, and the WIP capture
metadata under `work/stock-h3-audit`. Full map compilation and MCC acceptance
have not occurred.


The refreshed unmodified ASS export and reader passed with all 99 bound tags,
157 material variants, 543 unique objects, 1,247 instances and 247,855 triangles.
The five unresolved material slots remain explicitly reported. The bound Blender
scene hash stayed `b851b6d8e5add3f6d7c3ae8077948aea8b26752252a7cfc3797c113a08088e33`.
The 141,546,246-byte ASS hash is
`4044c7a02e6b18ecbf78cc7a203a8d2c93d85192441210f8a5a021efc8c99c4e`.
The optional upstream lxml warning concerns bitmap generation, which this
export does not request; the separate official Tool pixel checks are recorded
above. This roundtrip does not waive geometry metadata or map-build requirements.

Remaining metadata follow-up: the original stock inventory contains
`shaders/invalid.shader` in Standoff and 23 other available maps, and the official
H3 kit has its tag. It is a candidate for the two nonvisual surface variants;
their source emission/collision metadata still needs native H3 export mapping.
Only the active Foundry face-property type should be transferred: the inspection
record also includes unrelated default values from other property types.

## Stock nonvisual bindings (2026-11-04)

`prepare_stock_material_bindings.py` verifies the original Standoff option
vector against the unchanged official-kit `shaders/invalid.shader`; the stock
cache hash is checked before and after the read-only TagTool command. Its H3
tag hash is `5456ab171493cd99557f55964c6796970467da67028ad8e84294940520a7a94b`.
This direct reuse is restricted to existing sphere-collision-only/lightmap-only
materials. It is not an available substitute for unresolved visible surfaces.

The saved Blender scene now binds 100 tags across 151 used variants: 99 authored
tags plus this unchanged stock tag. The remaining three variants use water and
shared dirty glass. `verify_nonvisual_materials.py` reopens the saved scene,
checks the byte-identical alias, and calls the unmodified exporter's material
routine to verify the collision flag on six `box003` faces and the lightmap-only
flag on 32 `emissive_sun` faces. No mesh or emission setting is changed.

The same read-only audit records only active source lighting properties:
103 resolution selections, 12 emission selections, one chart group and one
lightmap type (117 records total). These remain unresolved. In particular,
Foundry stores a discrete 1–7 resolution selection while the H3 exporter exposes
a floating-point scale; equivalence must be established before copying values.
The converted scene's sun has stored imported intensity about 0.02 but a
scale-dependent getter about 0.0000185806. A subsequent read-only official
ManagedBlam inspection confirms the original lighting-info entry 5 has power
0.02, focus 0.5, per-unit-area enabled and attenuation cutoff 1500. BSP material
119 references this entry. `inspect_source_lighting.py` records all 193 original
BSP material settings and ten lighting-info entries, with both source hashes
unchanged. H3 units and attenuation still require verification before transfer;
the converted getter must not silently replace the original value.

Evidence: `stock-material-bindings.json`, `invalid-stock-binding.log`,
`h3-material-bindings.json`, `nonvisual-material-verification.json`, and
`verify-nonvisual-ass.log`, plus `original-material-lighting.json`, under
`work/stock-h3-audit`. These are saved-field and
export-control checks; lighting, actual MCC appearance and gameplay are pending.

The refreshed full unmodified ASS export/readback passes with 100 bound tags,
157 material variants, 543 unique objects, 1,247 instances and 247,855 triangles.
Three material slots remain pending. Current scene SHA-256:
`08df3ad55e9c60588ea6930dd5520e4b3d6010def8ff4b36ec6502acdf72b28e`;
ASS SHA-256: `990e82b49897e9370105460d4b2040d3647f474aa76382aee3a00db9e25ae9c2`.
These replace the earlier 99-binding inspection hashes above.
The nonvisual verification also passed against the actual exported triangle
material references. Both variants intentionally share one shader name and use
separate native flag records; the verifier resolves each object's references
rather than assuming the shader name uniquely identifies its face behavior.

## Shared dirty glass assigned (2026-11-04)

The remaining Reach `glass_window_dirty_subdued.shader_glass` now uses stock
Snowbound `levels/multi/snowbound/shaders/cov_glass_mast.shader`. Original 360
options `[0,1,0,2,2,1,0,3,0,0]` match the official H3 kit, whose extra MCC options
are zero. The original cache and donor hashes remain unchanged. This is native
H3 material authoring, not an imported Reach shader program.

Reach's dedicated glass group implicitly supplies alpha blending, with base
alpha selected without Fresnel. The stock H3 ordinary shader retains base-alpha
transparency, default albedo, two-lobe Phong and per-pixel reflections. Its
additional standard-bump and texture-mask inputs use the unchanged stock flat
normal and white bitmap; native exports verify neutral XY and full-white alpha.
The stock option help explicitly defines white mask alpha as unchanged specular
response. No artwork repacking or new normal/specular artwork is needed here.
See the official [H3 blend-mode](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/shaders/blendmode)
and [material-model](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/shaders/materialmodel)
documentation. Reach-only `analytical_roughness` and `env_roughness_offset` are
recorded as source-only inputs; the stock H3 response remains in charge, with no
invented shader behavior. This difference still requires the user's MCC review.

Six existing source functions are preserved byte-for-byte, including 0.35x base
and 3x detail scales, zero diffuse contribution and the reflection tint. The
source's default specular coefficient 1 is entered with the official function
editor; eight equal defaults use native H3 defaults. All three original images
and their mip counts pass native export checks. Mean base-alpha error is
0.0234/255; all cube-face channel mean errors are below 3.41/255.

The first reflection import was rejected: automatic curve selection produced
a darker linear cube and failed the pixel comparison. Pinned Foundry's
`BitmapTag.get_gamma_value` treats original curves 0 and 1 as legacy xRGB, so
the source's zero curve is not evidence of linear artwork. Reimporting through
the existing official H3 sRGB usage controls preserves the extracted colors;
the source TIFF and tag remain unchanged. The pixel verifier and its thresholds
were not relaxed. World-space reflection orientation still awaits MCC.

The bound scene has 101 tags / 153 used material variants, leaving one water
variant unassigned. Four skylight meshes (14 faces) retain two-sided transparent
and breakable flags, verified through the native Blender exporter properties.
`wip/h3-dirty-glass-assignments-skylights.png` is an inspected Workbench render
of two actual skylights highlighted cyan. It proves assignment location, not
transparency, final shading, breakage or MCC acceptance. The saved scene is
unchanged by rendering. The prior full ASS checkpoint remains at 100 tags;
this scene will be exported again after the remaining authoring work.

The updated checkpoint covers 90 ordinary materials, 918 ordinary source
functions, 30 scalar-default corrections and 315 matching ordinary defaults.
Including five generic terrain families: 1,050 source functions and 363 matching
defaults. It checks 247 image records / 184 unique original-image imports,
614 source/donor hashes and no duplicate authored inputs. Physical names: 93
exact stock names and seven retained empty-source cases. The packed glass image
is separately verified as before.

Evidence under `work/stock-h3-audit`: `dirty_glass-donor-integrity.json`,
`dirty_glass-family/report.json`, `dirty_glass-family/pixel-verification.json`,
`dirty-glass-geometry.json`, `h3-material-bindings.json`,
`active-input-checkpoint.json`, and the native WIP capture metadata.

## Native water source audit (2026-11-04)

Longshore's `dock_water_2` remains the stock donor candidate. Its eight shared
option selections match Reach's river. Native H3 option exports show that
`detail_slope_scale_x/y/z` and `detail_slope_steepness` already belong to its
default waveshape option. Reach's additional `detail=repeat` category alone
therefore does not establish an unsupported feature. Saved control behavior
and the final MCC appearance still need verification.

`verify_water_wave_assets.py` uses only official H3 Tool and Reach Tool exports.
Both kits' `rasterizer/water/wave_new/wave_new_displ_water` and
`wave_new_slope_water` contain 16 slices at 128x128. Every decoded top-mip RGBA
pixel matches exactly across all 32 slices. Native metadata also matches:
array depth 16, seven mip levels, DXT1/linear displacement and DXN/unknown-curve
slope. Original tags remain unchanged. Reusing these existing H3-formatted
assets can avoid rebuilding Reach artwork. Lower mip pixels, rendered wave
behavior and original-360 stock provenance are not proven by this comparison.
The available stock-map tag inventories did not contain these exact names;
official H3-kit inclusion is not being described as original-360 provenance.

`inspect_water_source.py` reads original Reach BSP geometry with ManagedBlam.
Native meshes 450, 458 and 468 contain 10, 11 and 21 water vertices and 9, 10
and 23 water faces. It maps each local water vertex to its original mesh vertex
and records both main texture coordinates and the additional water coordinates.
Selected source vertex colors and lightmap coordinates are zero. Foundry
preserves the two texture-coordinate sets in the Blender scene, with its normal
V flip. The exposed additional water records contain float2 coordinates;
the audit does not infer a third component or invent wave/color weights.

The documented [H3 Blender water workflow](https://www.reclaimers.net/h3/guides/map-making/level-creation/blender-level-modeling/blender-level-creation-additional-info/)
uses four UV channels and separate structure-design water physics. Mapping the
two source sets into those controls remains pending. H3's selected foam option
exposes `foam_height` and `foam_pow`, while source `foam_cut` and
`foam_coefficient` have no same-name inputs. Source foam coefficient zero must
not be silently discarded and thereby introduce foam. Resolve native control
semantics before authoring; consult the user for a required unsupported change.

Original river color/shape textures were extracted with unmodified Foundry.
The source foam tag was initially absent from the selectively extracted kit,
but exists in the original HREK archive and has now been extracted inside the
repository. This was not a missing official asset. No water shader, geometry
channels or final material bindings changed in this audit.

Evidence: `h3-effective-water-options.json`, `original-water-geometry.json`,
`water-wave-asset-verification.json`, native XML/TGA exports and logs under
`water-bitmap-pixels`, and `extra-reach-bitmap-extractions.json`, all under
`work/stock-h3-audit`. The saved scene remains at 101 bound tags; water is pending.

## Approved H3 water authored and bound (2026-11-04)

The user approved Longshore's stock H3 water behavior where Reach-only controls
have no counterpart, retaining Reach geometry and artwork. The decision and
remaining limits are in [WATER-MATERIAL-PROPOSAL.md](WATER-MATERIAL-PROPOSAL.md).
The native H3 water tag is authored and bound; geometry channels remain pending.

The read-only official H3 API audit found six Longshore meshes containing 1,555
water vertices. All have `local info` `(10,0,0)`, plus varying velocity fields
and base-coordinate W of zero or 0.5. Reach exposes only its base float2 in the
additional water block. General101's unmodified ASS exporter writes W=0.
These facts constrain the remaining authoring; no extra coordinates or custom
exporter modifications were invented. `InspectH3WaterGeometry.cs` records the
original BSP hash before/after and reads data without saving the tag.

The same native audit records H3 material properties in their actual properties
block. Longshore uses continuous lightmap-resolution values such as 0.001, 0.25,
1 and 6. Foundry's Reach exporter sends its seven-level selection as an integer
with default 3. This does not establish a direct numeric transfer; the 117
lighting metadata records remain unresolved. The initial Python H3 probe was
stopped after its initializer remained live without progress; the existing
working C# API initialization path completed the read successfully. An initial
direct-field lookup was corrected to read H3's actual material-properties block.

Material automation now accepts the official `shader_water` group (`rmw `,
including its significant space). The Longshore donor was rechecked against
the original 360 cache: eight options match, source and donor files unchanged.
The authored river retains 32 source function blobs and one differing shared
scalar default through the native function editor. H3-only donor controls remain
native; Reach-only foam/slope/normal controls are recorded, not reconstructed.
The two matching H3 wave arrays are referenced directly without reimport.

Four image inputs pass native export comparisons: original river color/alpha,
shape, foam, and the previously verified creek cube. The color strip initially
failed under generic DXT5/sRGB import settings. Its original is uncompressed
ARGB; retaining that storage corrected alpha but an explicit gamma override still
changed color. Native H3 Diffuse Map defaults with the override cleared produce
an exact RGBA match to both the extracted TIFF and original Reach Tool export.
The final saved H3 curve is sRGB. No pixels or verifier thresholds were edited.
Shape channel means are below 1.13/255; foam below 0.30/255. Cube-face appearance
and all rendered water behavior remain for MCC review.

The saved scene now binds 102 tags / 154 used variants, with no pending material
slots. `verify_water_bindings.py` checks all current authored/alias hashes and
the river's three meshes / 42 faces. The unmodified exporter emits the documented
water material apostrophe. The two original UV layers remain unchanged; this is
not a final water-geometry export. Physical names remain 93 exact stock matches,
with eight empty-source cases retaining native donors, including water.

Native Blender proof `wip/h3-water-assignments-river.png` was inspected: cyan
river surfaces run between the bases, partly occluded by the actual rock arch.
This is a diagnostic assignment view, not water texture/shading acceptance.
The render leaves the saved scene unchanged. The full ASS checkpoint is still
the earlier 100-tag scene; the broad `active-input-checkpoint.json` remains the
101-tag historical checkpoint. Current river evidence is in `water-family`,
`water-material-binding-verification.json`, `h3-material-bindings.json`,
`water-donor-integrity.json`, and `h3-docks-water-geometry.json` under
`work/stock-h3-audit`. No MCC or 360 acceptance is claimed.

## Water coordinates and original design inspection (2026-11-04)

This checkpoint supersedes the pending-coordinate and 100-tag ASS status above.
The actual 102-tag scene now passes full unmodified ASS export/readback: 157
materials, 543 unique objects, 1,247 instances and 247,855 triangles. A separate
reader check verifies all 42 river triangles / 126 corners, including their
original paired main/shape UVs and all four exported channels. This is format
and data evidence, not a native full-map compile or rendered-water acceptance.

The [c20 H3 water guide](https://www.reclaimers.net/h3/guides/map-making/level-creation/blender-level-modeling/blender-level-creation-additional-info/)
provides a [Blender example](https://drive.google.com/file/d/16Ew77K3itFb0a9lTrIU0-bFo3P14KRde/view).
The downloaded file's SHA-256 is
`830830c7eb3ea17d84dbbf4e29bd1fc437d82c0442cd0e6e7a996c4d76e68589`.
Its author is not independently identified; it is an upstream workflow example,
not this project's map geometry. It was opened with auto-execution disabled and
left unchanged. Native inspection found only one UV layer despite the guide's
four-channel instructions. Official Tool accepts that example, but its compiled
shape coordinates are constant. Successful compilation alone would miss this.

A separate four-channel diagnostic, exported through unmodified General101 and
imported by official H3 Tool, established the mapping. Tool scales the local-info
X by 0.01: authoring 10 produced 0.1, while authoring 1,000 reproduced Longshore's
stock `(10,0,0)`. Channel 2 `(0,0)` retains the native Tool default velocity;
channel 3 supplies shape coordinates, with the native V conversion and W=0.
All four diagnostic vertices were read through the official H3 tag API. This
does not assert that neutral per-vertex velocity reproduces Reach river flow.

The actual saved authoring scene now has:

| UV layer | Content |
| --- | --- |
| 0 | Original Reach main coordinates, unchanged |
| 1 | `(1000,0)`, reproducing stock Longshore local info through Tool |
| 2 | `(0,0)`, native Tool's default velocity |
| 3 | Original Reach water coordinates, unchanged |

Only the three river meshes' UV layers changed. Positions, topology and original
source scene remain unchanged. All 102 material bindings were refreshed and
verified. The current bound scene SHA-256 is
`ab66a8a1a87439a7e5e357fc2b97b2ffbe85dd89b1cf453bd11d087b745a0b5e`;
the full ASS SHA-256 is
`6303a63e33fb7049de315e64a10daada186cd40c3b5cf8dd028afb848268707a`.

Unmodified Foundry also imported the original Reach
`cex_beaver_creek_design.structure_design` into a separate inspection scene:
one water physics surface (28 faces), two planar fog sheets (two faces each),
and one soft ceiling (40 faces). No source tag changed and none of these objects
has been merged into the H3 scene. The imported water properties include flow
direction, velocity, depth and fog; these still need per-instance source and H3
semantic checks. They do not justify treating the neutral render-vertex velocity
as proof of correct physical flow or copying values without unit verification.

Reproduction helpers are `inspect_water_example.py`,
`export_water_workflow_example.py` (baseline and `--four-channels`),
`run_water_workflow_probe.py`, `prepare_water_channels.py`,
`verify_water_bindings.py`, `export_h3_inspection.py`, `verify_water_ass.py`, and
`inspect_structure_design.py`. Blender runs in background with repository-local
profiles/temp paths; use `--disable-autoexec` for the downloaded example.
Official `structure` takes the ASS path relative to the kit's `data` directory.
The first absolute-path attempt logged an error despite exit code zero and was
not accepted. No native importer, exporter, shader or compiler was patched.

Evidence under `work/stock-h3-audit`: `water-channel-workflow-verification.json`,
`water-channel-authoring.json`, `water-material-binding-verification.json`,
`water-ass-verification.json`, `h3-bound-ass-inspection-report.json`, and
`reach-structure-design-inspection.json`, with their native logs. The general
`active-input-checkpoint.json` remains historical. Outstanding work includes
physical water/design compatibility, 117 lighting records, 302 separate convex
physics cases, effect decisions, official map compilation, and user-driven MCC
review. Nothing was installed or converted to Xbox 360.

## Native water physics and soft-ceiling compilation (2026-11-04)

The original Reach structure-design tag was read through the official Reach API.
All 28 water instances have five planes and eight debug triangles, the same
20-world-unit depth (within source float precision), flow vector
`(-0.0416306183,-0.9991330504,0)`, fog color and murkiness. The imported Foundry
surface retains one top triangle per original convex prism. The native source
also has one unnamed acceleration boundary containing 40 triangles and two
planar fog sheets referencing Reach's `traxus_planar.planar_fog_parameters`.

The [official H3 water physics workflow](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/guides/waterphysics)
supports extruded water volumes, a child direction marker and native
structure-design compilation. In Blender, the original imported water triangles
were extruded to their verified original depth, capped and oriented outward.
The existing Foundry coordinate transform was used, matching the main authoring
scene. Every authored prism vertex matches original native debug geometry within
0.000002 world units. The marker's +X axis uses the original unit flow vector.
No custom importer, physics generator, serializer or native tool patch was used.

The first Tool import made one enclosing convex volume from the single mesh.
Further comparison found that the original top triangles fill that same outer
rectangle; a footprint error was not established. The final Blender scene uses
28 separate water objects to preserve the original convex partitioning. Native
H3 consequently creates 28 named groups, `water_physics_00` through `_27`, each
with its own direction marker. Underwater atmosphere settings must reference
these names. The earlier claim that the first import changed the footprint was
corrected; it changed the number of convex pieces.

The soft ceiling keeps its 40 oriented original triangles and native acceleration
type. Its original name was empty; the Foundry fallback name `soft_ceiling` is
used in the documented `+soft_ceiling:soft_ceiling` material. The separate source
inspection retains both fog sheets; neither was silently discarded or assigned
an unapproved H3 appearance. They are absent from this partial design export
until a supported stock H3 solution is established.

Official H3 `structure-design` compiled the actual authored scene successfully.
Fresh official XML export verifies one-to-one correspondence with all 28 source
prisms (six vertices/five planes each), every flow direction, and all 40 ordered
boundary triangles with their oriented planes. Water and soft-ceiling collision
MOPP blocks contain data. XML has six significant digits, so coordinate checks
allow 0.00006 world units of rounding; direction checks use 0.000001. This is
native geometry verification, not proof of in-game physics or appearance.

Current files under `work/stock-h3-audit`:

- `original-structure-design.json`: native original fields and source hash.
- `battle-canyon-h3-structure-design.blend` and
  `h3-structure-design-authoring.json`: saved Blender scene and export provenance.
- `h3-structure-design-verification.json`, `h3-structure-design-native.xml`,
  `h3-structure-design-import.log`: compiled native evidence.
- `wip/h3-structure-design-volumes.png`: inspected native Blender proof, cyan
  water prisms and orange boundary wireframe. Diagnostic colors, not game shading.
  The complete geometry fits the image; the saved scene remains unchanged.

The exported ASS and compiled design reside inside the repository-local H3 kit
under `levels/custom/battle_canyon_rebuild`, with the ASS in `data/.../structure_design`
and native `.structure_design` in `tags/...`. Reproduce with
`inspect_source_design.py`, `prepare_h3_structure_design.py` on the original
inspection blend, `verify_h3_structure_design.py`, and
`render_structure_design_wip.py` on the saved H3 design blend. Runtime profiles,
logs and temporary files remain repository-local.

Water atmosphere/fog and scenario linkage remain unfinished, along with main
scene collision/lighting metadata and effects. This design-only compilation does
not mark step 4 complete or waive full-map compilation, user-driven MCC testing,
explicit MCC approval, or the subsequent 360 gate. No installation changed.

## Native lighting controls verified; differences proposed (2026-11-04)

Original Reach scenario export confirms the resolution-category values
`1, 4, 16, 64, 128, 256, 512`, matching the pinned Foundry definitions. The
original BSP uses categories 1, 2, 3, 4, 5 and 7; its default is category 3.
H3's native material control is a continuous multiplier with default 1.
[LIGHTING-METADATA-PROPOSAL.md](LIGHTING-METADATA-PROPOSAL.md) proposes preserving
relative priorities by dividing the source category value by 16. This is a
documented authoring choice awaiting approval, not an exact texel-allocation
equivalence between the engines.

The proposal also identifies the actual unmapped selections: nine emission
selections use bounce ratio 0.05, one uses 0.5, one 28-face selection uses chart
group 17, and one 2,432-face BSP selection uses per-vertex lighting. The inspected
native H3 material-lighting schema lacks the separate bounce ratio, and the
unmodified ASS material workflow lacks matching chart-group/per-face lighting
controls. The user has been asked to approve H3's native behavior for those
cases. No approval is inferred from silence and no map lighting was changed.

`export_lighting_workflow_probe.py` uses six existing faces from the upstream
Blender example to test shared controls. It leaves that file unchanged and
exports through the pinned unmodified ASS add-on. Official Tool imports all six
materials. `verify_lighting_workflow_probe.py` then exports the actual BSP and
lighting-info tags through native Tool and checks their material links:

- All six proposed multipliers used by Battle Canyon survive unchanged.
- Original RGB, power, quality, focus and power-per-area flags survive, including
  the sun's 0.02 power and the colored strips' 3.0 power.
- Attenuation receives Tool's 0.01 scaling. Source sun cutoff 1,500 becomes 15
  H3 world units; strip cutoff 150 becomes 1.5. This agrees with Foundry's source
  import conversion. Blender's scaled intensity getter is not a native power.

Native XML prints six significant digits; comparisons allow 0.000001 for shared
scalar/color inputs. Tool emits a literal `<unavailable>` in one BSP resource
attribute, making that XML invalid. The verifier escapes only that placeholder
in memory for parsing, leaving the tag and original XML unchanged. Tool's
texture-disposal warning remains in the diagnostic log; native output and
material values, rather than exit code alone, establish these narrow checks.

Evidence: `original-lighting-scenario.xml`, `h3-stock-lighting-info.xml`,
`lighting-workflow-probe.json`, `lighting-workflow-verification.json`,
`lighting-workflow-bsp.xml`, `lighting-workflow-info.xml` and associated native
logs under `work/stock-h3-audit`. The diagnostic kit outputs are under
`levels/custom/bc_lighting_workflow_probe`. It does not establish baked appearance
or mark any unresolved source lighting selection accepted.

## First full native diagnostic and authoring corrections (2026-11-04)

The first full official H3 `structure` diagnostic exposed a missing shader
lookup configuration: short aliases existed in `export_shaders`, but no shader
collection selected that directory. Tool reported unresolved materials alongside
open/degenerate collision edges and repeated defining instances. This run was
deliberately stopped after those concrete failures, not because observation
expired. No BSP, scenario or lighting-info output was accepted. Its complete log
and report remain `h3-full-geometry-unresolved-bindings.log/.json`.

`assign_h3_materials.py` now registers the documented `bcf` collection in the
repository-local kit's `tags/levels/shader_collections.txt`, pointing to
`levels/custom/battle_canyon_fresh/export_shaders`. Existing unrelated entries
are preserved; an existing conflicting `bcf` entry causes failure. All assigned
material names carry that prefix and remain within the native name limit.
Authored shaders and their aliases are unchanged byte-for-byte. A native
`--bound-shaders` diagnostic on the lighting helper verifies six aliases resolve
to the exact expected authored tags, rather than a default or a similarly named
stock shader. Evidence: `bound_shaders-workflow-verification.json` and its XML.

The [official H3 instance-collision workflow](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/art/instanceobjects/collision)
uses one collision child for a shared instance definition. Saved-scene inspection
found 115 collision children across 44 linked definitions; 71 were exact duplicate
definitions, with the same mesh and local/parent-inverse transforms. These were
removed from the H3 authoring scene while retaining one child per definition
and all 1,060 placed render instances. This changes authoring representation,
not the intended repeated collision geometry. The initial scene-preparation
helper was also corrected to create only one child per shared mesh.

The same inspection narrows the outstanding separate Reach physics work to
56 definitions used by 302 instances, with 207 source convex hulls. Twenty-eight
of those definitions have an explicit collision child and 28 use the imported
mesh's collision faces. These have not been declared compatible from counts or
documentation alone; the native output and eventual MCC traversal must verify
them. No replacement hulls or engine changes were invented.

`deduplicate_collision_children.py` records the retained/removed authoring
objects. The water helper then reverified every original main/shape UV and both
native auxiliary channels before refreshing saved-scene provenance. The bound
scene still contains 102 tags / 154 used material variants and no unassigned
slots. Full ASS export/readback is being refreshed for these naming and shared
collision changes. The first diagnostic's geometry failures must be rechecked
with valid materials before attributing them to a particular source defect.

This work does not apply the pending lighting proposal or complete step 4. There
has been no lightmap bake, MCC playtest, installation or Xbox 360 conversion.

The combined authoring/export process subsequently wrote original material names
instead of the bound aliases. The full ASS readback assertion caught this; that
output was not passed to Tool and the previous successful ASS report does not
validate its changed hash. Export is being rerun in a fresh Blender process
opened directly on the saved bound scene. Its early preflight confirms all 154
saved material assignments; final ASS readback still determines acceptance.
`export_h3_inspection.py` now checks bindings before its expensive export as well
as afterward and updates Blender's view layer. Neither upstream add-on was
modified. Current log: `h3-native-saved-binding-export.log`.

## Corrected full import and isolated collision diagnostic (2026-11-04)

The fresh Blender process completed the saved-bound-scene export/readback:
102 tags, 157 material records, 543 unique objects, 1,176 instances and 247,855
triangles. The current ASS SHA-256 is
`aeab8f2a0ec09aeadcc25c937c812c8975fd866e321cd8e0774a7b7baab37b8d`.
The separate water verifier also passed all four UV channels on 42 triangles /
126 corners. This supersedes the pending-export status immediately above.

Official Tool completed the corrected full import in 7m24.477s. It wrote BSP,
lighting-info and scenario tags, but `import_h3_geometry_checkpoint.py` correctly
returned failure: Tool's exit code was zero despite geometry errors. Its report
records 525 issue lines, one plane-builder convergence failure and 46 groups of
open/degenerate edges. Missing shader lookups and multiple defining instances
are absent. No resulting map is accepted, baked, installed or converted.
Evidence: `h3-full-geometry-import.log/.json` and the native
`import_errors/battle_canyon_fresh_battle_canyon*.wrl` files inside the local kit.

Read-only Blender topology inspection confirms all 44 explicit collision meshes
have zero boundary edges and zero zero-area faces. Three contain nonmanifold
edges (definitions 18, 153 and 328). In particular, `boulder_low035`'s collision
mesh has 190 vertices / 338 polygons, consistent winding and no boundary or
nonmanifold edges. Its polygons are not perfectly planar: maximum deviation is
0.006366 authoring units. These facts do not establish native compatibility.

`export_collision_workflow_probe.py` isolates that original render mesh and its
existing collision child in memory, without modifying either mesh or the saved
scene. It adds a diagnostic-only enclosing sky box because Tool rejects an
instance-only structure. The unmodified exporter writes
`data/levels/custom/bc_collision_workflow_probe/structure/boulder.ass` in the
local H3 kit. Native Tool needs Windows backslashes in the relative input path;
an initial forward-slash command was rejected, as was the initial instance-only
probe. Neither was treated as a successful test.

The valid diagnostic imports in 0.925s and reproduces the same 44 edge errors,
six ambiguous connections and overlapping surfaces as the full scene. Native
XML shows that Tool did import a separate collision mesh (190 vertices, 515
edges, 327 surfaces), plus a separate render BSP (378 vertices, 991 edges,
615 surfaces). Therefore the collision child was not simply ignored.

`inspect_collision_workflow_errors.py` compares the native WRL error endpoints
against Blender mesh positions. Of 88 open-edge endpoints, 60 are within 0.001
authoring units of render vertices, versus six for collision-proxy vertices.
This supports investigating render-BSP construction separately; it does not
prove a repair or waive the errors. Both final native edge graphs have zero
negative surface references. The native collision vertex count matches the
source, but positions do not match exactly: the largest nearest-source distance
is 0.018470 world units. Native plane/vertex processing and the original eleven
seamsealer polygons still need examination before collision fidelity is claimed.

Evidence under `work/stock-h3-audit`: `collision-workflow-probe.json`,
`collision-workflow-import.log`, `collision-workflow-bsp.xml`, and
`collision-workflow-error-inspection.json`. XML parsing only escapes Tool's
literal `<unavailable>` placeholder in memory. No upstream exporter, compiler,
engine, serializer or source geometry was patched. The lighting proposal remains
pending; this diagnostic does not apply it or constitute MCC visual acceptance.

## Native boulder authoring correction and lighting approval (2026-11-04)

The user approved the native H3 lighting proposal: "Approve native H3 lighting
approach". The proposal document and to-do now record approval. Transferring the
shared source inputs, baking, and MCC review remain outstanding; older references
to pending approval above are historical.

`inspect_source_collision.py` reads original Reach definition 74 through its
official ManagedBlam API. It has 190 collision vertices, 338 surfaces and no
render BSP. Eleven surfaces have material -1; they are neither invalid nor
invisible. Foundry represents them with the existing +seamsealer material.
The original tag remains unchanged. Evidence: `original-boulder-collision.json`.

The [H3 material controls](https://www.reclaimers.net/h3/source-data/h3-materials/)
include Precise (prevent normal BSP point/triangle adjustment) and Render Only
(exclude those faces from collision). The existing collision-child workflow
still supplies the separate physical surface. Isolated native diagnostics show:

| Authoring setting | Native geometry result |
| --- | --- |
| Original exported settings | 44 open edges, six ambiguous connections, overlapping surfaces |
| Precise | 44 open edges; ambiguity/overlap errors gone |
| Render Only on render faces, unchanged collision child | Open-edge errors gone; ambiguity/overlap remain |
| Both settings, Precise also on collision faces | No geometry errors; separate collision and MOPP retained |

The first Precise diagnostic did not actually export its in-memory property
changes. Readback found no BM_FLAGS records, so that run is not evidence about
Precise behavior. Explicit Blender material/mesh update_tag/update calls make
the unchanged exporter observe the authoring properties; the helper now asserts
the exact exported flags. No upstream add-on or compiler was patched.

`verify_collision_workflow_geometry.py` compares native XML to the original ASS.
Native render positions/UVs are stored in compression-bound coordinates, and
native V uses the opposite origin from Blender/ASS. Applying those documented
coordinate interpretations is essential; comparing raw values gave false
position/UV differences. All 710 triangles match with preserved winding.

| Measured deviation | Original settings | Both native controls |
| --- | ---: | ---: |
| Maximum render vertex distance, world units | 0.0194583 | 0.000174122 |
| Maximum UV distance | 0.000000644 | 0.000000644 |
| Maximum normal-vector distance | 0.00450878 | 0.00450878 |
| Native collision samples to source, world units | 0.0158590 | 0.000038179 |
| Source collision samples to native, world units | 0.0162365 | 0.000038414 |

Collision samples include every vertex and polygon centroid in both directions,
not exhaustive continuous-surface or gameplay testing. Native output has 190
collision vertices, 336 surfaces and 3,502 bytes of MOPP data; its render BSP is
empty, as in the original Reach definition. The remaining render position and
normal differences fail the diagnostic's strict 0.0001 thresholds. They are
recorded explicitly, not relabeled exact preservation or silently waived. UV
and collision-sample checks pass. The normal difference is unchanged from the
baseline; the new controls greatly reduce geometric deviation.

`prepare_boulder_collision_authoring.py` applies only those standard controls to
the one diagnosed boulder in the saved authoring scene. It copies three local
material slots, preserving all vertices, faces and UVs, the original collision
child and material/shader choices. It preserves the exact +seamsealer keyword
when making a local copy; the first material rebind rejected the suffixed name
and no invalid bound scene was accepted. Water UV provenance was rechecked.
Material rebinding now succeeds with 102 tags / 156 used variants / no pending
slots. A fresh-process `--authored` diagnostic reads the saved bound file,
asserts its flags, and imports without geometry errors. Its raw render data,
compression data and complete instance collision definition match the diagnosed
prototype exactly. Texture-disposal warnings remain in Tool's log.

Current authoring SHA-256:
`521054e6461af95406a423f9b255a82fa3649a3bbe3ddc1734d1962684d0b8a9`.
Current bound scene SHA-256:
`fbac8876c297067c0eef6458d0de4bbb7fe8c40c4dd415d84a9a3db138f0c1c2`.
The full-map ASS/import evidence still refers to the earlier scene. Do not pass
it off as the latest export; refresh after authoring the approved lighting inputs.

Native Blender proof was rendered and visually inspected at
`work/stock-h3-audit/wip/h3-boulder-native-geometry-comparison.png`: original ASS
render mesh on the left, actual official-H3 compiled mesh on the right, both in
neutral diagnostic shading. Their visible silhouettes and surface features
match in this view; this does not validate Reach textures, baked lighting,
shadows or MCC gameplay. No desktop capture/control was used.

Evidence includes `collision-workflow*-probe.json`, native import/XML outputs,
the two `*-geometry-comparison.json` reports, `h3-boulder-collision-authoring.json`
and `collision-workflow-authored-equivalence.json`. The helper commands use
`--precise`, `--render-only`, both together, or `--authored` for the saved result.
No blanket application to the other 43 collision-child definitions is implied.

## Approved lighting authored and verified in the full import (2026-11-04)

This checkpoint supersedes the earlier scene hashes and pending-lighting state.
`prepare_h3_lighting_metadata.py --apply` authors the approved shared controls
through Blender's existing H3 material properties. It resolves all 117 original
face-property selections: 103 resolution, 12 emission, one chart group and one
per-face BSP lighting policy. The latter two use the explicitly approved native
H3 behavior. Original Foundry properties remain as provenance.

There are 104 local material variants on 22,690 faces across 99 meshes. All 543
mesh geometry/UV hashes remain unchanged. Source emission values come from the
original native tag readback, not Blender's display-unit getters. Resolution
ratios preserve the approved source categories; source RGB, power, quality,
focus, power-per-area flags and attenuation are assigned through stock controls.
Materials keep their shader paths and prior flags. Rebinding yields 102 tags,
244 used variants and no pending slots.

Fresh-process `verify_h3_lighting_metadata.py` checks saved source selections,
assignments and inputs. Its `--ass` mode checks actual exported triangles by
mesh-local position and material lighting strings, preserving multiplicity;
all 22,690 selected faces pass. The full unmodified ASS export contains 248
material records, 543 unique objects, 1,176 instances and 247,855 triangles.
Water saved bindings and the four-channel, 42-triangle / 126-corner ASS check
also pass against the current bound scene.

Current authoring SHA-256:
`7994103001f05d59b75f86bef74b3786d239e7618b08f1575dcb8c504f8eacdf`.
Current bound scene SHA-256:
`f3a13035fb20c5ace55782818b7e079629a2cb5d627ec4cbaeb92e639cb4bcb8`.
Current full ASS SHA-256:
`4ea660b7b854385f54e3763aabf90c32501aa0cdff67a08e87b18f279aa1c9cf`.

Official full Tool import completed, but remains a failed geometry diagnostic:
498 issue lines include one plane-builder convergence failure and 45
open/degenerate-edge groups. The corrected boulder no longer reports errors.
There are no missing-shader or duplicate-defining-instance errors. Tool's zero
exit code and generated tags are not a clean import or accepted map.

`verify_native_map_lighting.py` reads actual BSP material properties through the
existing official-API inspector and exports the small lighting-info tag through
official Tool. It checks the current scene/ASS/native-output hashes, shader
references, resolution properties and emitting fields. All 104 authored variants
pass, including nine emitting variants. Tool's 0.01 attenuation scaling is
verified again on the full map. This establishes compiled lighting inputs only;
geometry repairs, baking, visual review and gameplay remain open.

Evidence under `work/stock-h3-audit`: `h3-lighting-metadata-plan.json`,
`h3-lighting-metadata-authoring.json`, the saved/bound/ASS verification reports,
`h3-full-geometry-import.json` and log, `h3-full-map-lighting-verification.json`,
`h3-lighting-native-materials.json`, and `h3-full-map-lighting-info.xml`.
The previous full-import evidence is preserved as
`h3-full-geometry-pre-lighting.json` and `.log`.

The expanded read-only original collision inventory covers all 44 definitions
with explicit collision children: 17 have no original render BSP, while 27 have
one. Evidence: `original-proxy-collision-inventory.json`. Do not generalize the
single boulder's Render Only solution to all definitions. The remaining 207
Reach physics hulls still require an established H3 authoring route. The
[Blender guide's object-symbol table](https://www.reclaimers.net/h3/guides/map-making/level-creation/blender-level-modeling/blender-level-creation-additional-info/)
defines `$` for JMI/JMS physics export; it does not by itself establish an ASS
instance-physics override. No such override has been applied or claimed tested.

## World-collision isolation (2026-11-04)

`inspect_source_collision.py --world` reads the original Reach world collision
through its official API. The large collision BSP has 28,302 vertices, 46,178
surfaces, 74,619 edges and 57,058 planes. No edge has a negative surface reference
or coincident endpoints. There are 1,933 material -1 surfaces, 6,625 slip surfaces
and 292 invisible/two-sided surfaces. The original tag hash is unchanged.

Foundry's upstream structure importer combines visible cluster geometry and
source collision-only surfaces. The resulting saved world mesh has 31,342
vertices, 61,874 polygons and 62,664 exported triangles. Its combined topology
has 123 boundary edges and 146 nonmanifold edges, but no zero-area polygons or
inconsistent manifold-edge winding. Those combined counts include different
surface modes and are not alone evidence of bad collision.

`export_world_collision_probe.py` isolates this actual world mesh, optionally
setting the standard Precise material flag in memory. It never saves or repairs
the map scene. The first export check incorrectly equated polygons with triangles;
it rejected the output. The corrected check uses Blender's actual loop triangles.
`verify_world_probe_inputs.py` confirms the baseline and Precise ASS files contain
identical geometry, normals, UVs, face indices and instance transforms. Only
exporter-generated instance IDs are excluded from instance equality; parent
array indices and all other fields are compared. No source geometry was changed.

The isolated baseline reproduces the plane-builder convergence failure, four
degenerate-triangle warnings and 12 open/degenerate edges. Precise eliminates
the convergence failure but leaves three degenerate-triangle warnings, nine
open/degenerate edges, seven degenerate collision-edge errors and one leak.
Neither is a successful repair. These initial probes omit portals and therefore
also exceed native per-cluster vertex/strip limits; they produce no BSP tag.
The subsequent `--precise --portals` diagnostic retains all 67 original portals
to address that diagnostic-induced limitation without altering native limits.

The portal-preserving diagnostic completes in 180 seconds and writes a native
BSP, with neither the plane-builder failure nor per-cluster format-limit errors.
It still fails geometry validation: three degenerate-triangle warnings, nine
open/degenerate edges and seven degenerate collision-edge errors remain, along
with portal leakage and overlapping-surface diagnostics. Its source ASS hash is
`675dc6194eba655ce15cf3f758010b1148fcd41c1952e4237a794306294b939f`;
the resulting diagnostic BSP hash is
`bb80b1819e8a2a6801bf81b4543e5b2b673729166c8d4b0e841e43581d4c0fd4`.

`inspect_world_collision_errors.py` locates native WRL endpoints on the original
saved world mesh, recording nearby source faces/materials/flags. The three
degenerate-triangle warnings match source faces 13787 and 13837 (thin metal-dark
triangles), and a triangle of sky polygon 60268. These faces are not zero-area
Blender polygons; native degeneracy must not be equated with absent source area.
The portal-preserving diagnostic identifies 165 adjacent source faces for further
inspection. Endpoint proximity is not itself a repair or a reason to delete faces.
Next investigate preserving original world collision through the standard
collision-only/render-only authoring controls before considering topology edits.

Evidence: `original-world-collision.json`, `world-collision-*-probe.json`,
`world-collision-*-native.json`, native import logs, and
`world-collision-input-comparison.json` under `work/stock-h3-audit`.
Native error-location reports are `world-collision-precise-error-locations.json`
and `world-collision-precise-portals-error-locations.json`.
The authoritative saved/bound map and full-map import remain at the prior
lighting checkpoint. These diagnostics do not constitute a baked or playable map.

Native Blender close-up: `work/stock-h3-audit/wip/h3-world-thin-triangle-diagnostic.png`.
It shows the actual neighboring source faces around metal triangles 13787 and
13837, with thickened red edge overlays. This is cropped diagnostic geometry in
neutral shading, not the final materials or MCC appearance. The first camera
view was occluded by other world surfaces and was rejected; the final view is
cropped to the relevant source neighborhood and faces its normals. No scene
was saved or exported by `render_world_collision_wip.py`.

## Original world collision through the standard H3 workflow (2026-11-04)

`inspect_world_source_foundry.py` imports the complete original world collision
using unchanged Foundry `StructureCollision.to_object`, in an isolated copy of
the current scene. It does not rebuild collision from the visible triangles.
The initial expected polygon count failed: Foundry's `set_two_sided` combines
146 coincident front/back pairs into 146 two-sided polygons. This explains the
46,178 original surfaces becoming 46,032 Blender faces; no original surface is
unaccounted for. The paired surfaces are invisible/sphere-collision surfaces.

Fresh saved-scene verification checks all 28,302 vertices against Foundry's exact
float32 unit conversion, all original surface vertex sets and winding, shader
references, slip flags and sphere/two-sided selections. It passes. Collision
bounds exactly match the combined world mesh bounds. All 49 material bindings
already exist in the approved H3 material set.

`export_world_source_collision_probe.py` applies standard H3 Precise,
Render Only and Collision Only controls in memory. The original collision
supplies 2,079 nonvisual faces formerly carried in the combined world mesh;
59,795 visible world faces and all 67 portals remain. Original sky polygons
retain +sky; slip and two-sided sphere-collision selections remain explicit.
The unchanged ASS exporter/readback checks the actual output flags and triangle
counts. This is a diagnostic only; the authoritative authoring scene is unchanged.

Official Tool imports the diagnostic in 215.7 seconds with no ERROR lines and
writes an H3 BSP. Its native collision has 28,302 vertices, 74,747 edges, 46,306
surfaces and 50,618 planes, with zero negative surface references on edges.
The earlier plane-builder failure and open/degenerate collision-edge errors
are gone. Thirty-four warning lines remain: 11 collision flags on noncollidable
render copies, two degenerate visible triangles, ten portal-leak warnings and
their paths, and a texture-disposal warning. These are not silently waived.
Remove slip controls from the render-only copies when applying this authoring
split, since the original collision already carries them. Portal behavior still
needs the full surrounding instances; the two thin visible triangles also remain.

Diagnostic scene SHA-256:
`2152e3c7c67ea477e290057e2099ea7e73607712002c9020c2348dd5dc850aa7`.
ASS SHA-256:
`e6aa20d2424ff471e6e8d018fc9be44d12f663d6e6d0274eea2c255fc6309faf`.
Native BSP SHA-256:
`18714bc97cded59b514b1732464b97d7af1b8d7629ba626def1adb3abe655320`.

`inspect_native_world_collision.py` exports official Tool XML and streams its
collision blocks. Tool's XML rounds coordinates, so precise comparison uses
`ReadH3WorldCollision.cs` through the official H3 `InitializeProject` API instead.
The API reader is read-only and checks the tag hash before/after. It reads actual
named flags, rather than assuming Reach and H3 flag layouts match.

`compare_native_world_collision.py` checks every vertex and every polygon
centroid in both directions. Maximum nearest-vertex distance is 0.000489234 H3
world units (about 1.49 mm); this is not entirely explained by the modeled
float32 unit round trip. Maximum centroid distances are 0.00147309 source-to-H3
and 0.00298339 H3-to-source world units. Respectively 368 and 418 centroids exceed
the diagnostic's strict 0.0001 threshold. Four source and two native centroids
find a nearer different shader boundary; all agree on collision flags. Matching
shader/flag surfaces exist nearby, with maximum distance 0.000937149 world units.
These are sampled distance checks, not proof of continuous-surface equivalence.
Do not relabel them exact preservation or MCC collision acceptance.

Evidence under `work/stock-h3-audit`: `world-source-collision-inspection.json`
and `.blend`, `world-source-collision-saved-verification.json`,
`world-collision-source-probe.json`, `world-collision-source-native.json` and
import log, official XML and extracted collision JSON, the native-API report,
and `world-collision-source-comparison.json`. Native API helper compilation uses
the installed .NET Framework x64 compiler, the repository H3 kit's
`bin/ManagedBlam.dll` and System.Web.Extensions; executable/output/profile/temp
paths remain under `work/stock-h3-audit`. No source tag, compiler or exporter was
patched. Applying this standard split to the saved authoring scene must preserve
visible normals/UVs and refresh lighting face-selection provenance before a full
reimport. The main-map import and MCC gates remain incomplete.

## Apply original world collision to the saved map (2026-11-04)

The diagnosed split is now applied to the fresh authoring scene through standard
Blender material controls. `plan_world_collision_authoring.py` first proves that
none of the 2,079 nonvisual faces being replaced carries a lighting assignment.
`prepare_world_collision_authoring.py` preserves source face/corner IDs, removes
those nonvisual faces, and appends the verified original collision. The 59,795
visible world faces use Precise and Render Only; collision-only, sphere-collision
and slip flags are cleared only on their render material copies. The complete
original collision retains its sky, slip and two-sided sphere selections.

All visible positions, normals, UVs, winding and material references survive the
edit and fresh saved-scene reload. No visible face is removed or remeshed.
Lighting face selections are remapped through their retained source IDs; all
117 source records and 22,690 selected faces remain verified. Material copies
increase the used lighting variants from 104 to 113 without changing their
lighting values. Other source meshes retain their geometry/UV hashes. Water
UV checks also pass after rebinding and export.

`verify_world_collision_ass.py` compares the actual exported arrays: all 59,795
visible triangles exactly match the earlier full ASS in positions, normals,
UVs, colors, winding and material names. All 56,580 collision triangles and
their material controls exactly match the successful original-collision
diagnostic. These are input-equality checks, not a claim that H3's compiled
collision is numerically identical to Reach; the earlier native comparison's
documented deviations still apply.

Current files under `work/stock-h3-audit`:

- `battle-canyon-h3-authoring.blend`: SHA-256
  `874b04187bcb5d9b38aba78a7b8fe1dc379ca16716f37d700a6d55df9bbe3688`.
- `battle-canyon-h3-materials.blend`: SHA-256
  `9c0c23f58be644d0ebb6b45a5e0c66365aab3f2c0255852c6a91b1bcd52585d2`.
- `h3-bound-inspection.ass`: SHA-256
  `e784c3b71c6dd969dca77a9028b7451238bf7b66883e646cd2abd9647c28ac64`;
  341 material records, 544 unique objects, 1,177 instances, 301,566 triangles.
- `h3-world-collision-authoring.json`, `world-collision-saved-verification.json`,
  `world-collision-bound-verification.json`, `world-collision-ass-verification.json`
  record the edit, source provenance and preservation checks. Bound shader
  assignments cover 102 tags and 337 used variants, with none pending.
- Native Blender WIP: `wip/h3-world-split-overview.png` and
  `wip/h3-world-split-closer.png`. Both were inspected: they show the base walls,
  ramp/entry and nearby rocks with the nonvisual collision mesh hidden. Neutral
  Workbench shading does not verify final textures, baked lighting or MCC visuals.

The import wrapper now requires current scene/ASS hashes and both world
preservation checks before running official Tool. Original Reach source files,
Foundry, the ASS exporter and the native compiler remain unchanged. Remaining
instance collision/physics and thin-triangle/portal warnings are separate work;
there is still no playable-map acceptance or permission to convert to Xbox 360.

The full official import completed in 7m03.476s and wrote native tags. The world
plane-builder convergence failure is gone. Error lines fall from 64 to 61:
44 instance open/degenerate-edge groups and 17 instance bad-connection errors
remain. Portal-leak warnings fall from 39 to 12; two thin visible triangles still
warn. Other warnings, including similar-instance geometry and outside-map
instances, remain in the full report and are not waived. There are no new missing
shader or duplicate-definition errors. This is still a failed geometry gate.

`verify_native_map_lighting.py` passed after this full import: all 113 lighting
variants, including nine emitting variants, match the expected native fields.
It also verifies unchanged shader hashes and current native output hashes. This
checks compiled inputs only; no lightmap bake or user-driven MCC test occurred.

Current native BSP SHA-256:
`aae76a0c56edb12a181fdc733f1906d97f785564617437586911e226ca6c1168`.
Lighting-info SHA-256:
`d1fdf29cd89910e7fdc51d99f07351093dfc5702611d0802065b1d9c212b46e8`.
Evidence: `h3-full-geometry-import.json` and `.log`,
`h3-full-map-lighting-verification.json`; previous import retained as
`h3-full-geometry-before-world-split.json` and `.log` for comparison.

## Ten additional boulders through standard H3 controls (2026-11-04)

The original collision inventory identifies eleven remaining boulders with no
render BSP and no separate physics hulls, matching the already-diagnosed
`boulder_low035` case. The existing isolated exporter/importer/comparison helpers
now accept a target name; batch wrappers run the same unchanged exporter and
official Tool sequentially. This follows the documented
[H3 instance collision hierarchy](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/art/instanceobjects/collision):
retain each original collision child beneath its render instance. No native
compiler, exporter or collision serialization code is changed.

Precise on both meshes and Render Only on the visible material copies produce
clean isolated imports for ten targets: `boulder_low025`, `boulder_low037`,
`boulder_low023`, `boulder_low029`, `boulder_low031`, `boulder_low043`,
`boulder_low041`, `boulder_low027`, `boulder_low039` and `boulder_low033`.
`boulder_west_lowz002` still reports three collision edges (including a
seamsealer boundary); its map authoring is deliberately unchanged.

Across the ten clean cases, all 8,363 render triangles match with preserved
winding. UV differences are below 0.000001. Native render positions differ by
up to 0.000231850 H3 world units and normal vectors by up to 0.006313263; these
exceed the existing strict diagnostic thresholds and are not relabeled exact.
Four cases (`low037`, `low023`, `low041`, `low027`) also exceed the 0.0001-world-unit
collision sample threshold, with a maximum sampled difference of 0.000232461.
All native outputs retain collision MOPP data and the original absence of a
render BSP. The comparison samples all vertices and polygon centroids in both
directions; it does not prove continuous-surface or gameplay equivalence.

`prepare_boulder_collision_batch.py --apply` copies only those ten cases'
material slots and changes standard flags. All 544 geometry/UV hashes remain
unchanged, as do the target corner normals. Fresh saved-scene checks independently
verify all 20 render/collision objects and 30 material slots, including stored
transforms, parent relationships and other material flags. There are no lighting
face assignments on these meshes. All 117 lighting source records / 22,690 faces
remain checked; the world split and four water channels also still pass.

Current authoring SHA-256:
`935da3230a2a5b4f327dfcce2edcba9155f1ddc059d1072e5eff69285d96245e`.
Current bound-scene SHA-256:
`c132a8eee1bfec9f26fdca113b83a5168ada0cd681a01c279c8e794e5e1c8955`.
Bindings cover 102 tags and 357 used variants, with none pending. Prior fresh
authoring/bound scenes and reports remain under the `boulder-batch-before-`
prefix; these are not files from the rejected rebuild.

Evidence under `work/stock-h3-audit`: `boulder-batch-export.json`,
`boulder-batch-import.json`, `boulder-batch-verification.json`, per-target
`collision-workflow-precise-render-only-*-probe.json`, native XML/import reports
and geometry comparisons, `h3-boulder-batch-authoring.json`, and saved/bound
verification reports. The combined full-map error count must be established
after reimport, not inferred from ten isolated successes.

Blender proof inspected:
`wip/h3-boulder-native-geometry-comparison-boulder_low033.png`, source on the left
and official H3 output on the right. Silhouettes and visible facets match in this
view; neutral shading does not establish material, shadow or MCC acceptance.

Full ASS readback matches all ten diagnosed render/collision inputs exactly,
including normals, UVs, colors, winding, material controls and parent links.
The exported scene still has 544 unique objects, 1,177 instances and 301,566
triangles; its 371 material records reflect the copied controls. ASS SHA-256:
`54eab98bc965b929dea09f59e6a241b9dea1e0020d974636e599cdf5bae33195`.
Lighting/water/world ASS checks also pass. The full import wrapper requires this
current boulder comparison before invoking Tool.

The west-boulder follow-up is read-only. Official Reach API data for definition
418 and native error endpoints identify source vertices 27, 40 and 41: all three
edges surround original collision face 20. Neighbor face 295 uses the same rock
material; face 480 is the seamsealer polygon. Faces 20 and 480 share the exact
original plane. All 499 source polygon vertex sets were matched to the native
source edge loops before assigning these face IDs. The source collision mesh is
closed and has no zero-area faces; the isolated H3 output also has zero negative
surface references, despite Tool's three-error report. This is not permission to
waive the errors or delete the triangle. Investigate the native handling of this
shared-plane material boundary before changing source geometry.
Evidence: `original-instance-collision-418.json`,
`collision-workflow-precise-render-only-boulder_west_lowz002-error-inspection.json`,
and `west-boulder-error-faces.json`.

The full official import completed in 7m14.981s. All ten corrected targets have
zero error lines in the combined scene. Total `-ERROR-` lines fall from 61 to 48:
34 open/degenerate-edge groups and 14 bad-connection errors remain, versus the
previous 44 and 17. The world plane-builder failure stays absent. Twelve portal
leaks and two thin-triangle warnings remain. The wrapper correctly reports
`clean_import_completed: false` despite Tool's return code 0 and written tags.

Post-import native lighting readback again verifies all 113 material variants,
including nine emitting variants, against the current scene and ASS hashes.
Current BSP SHA-256:
`cc61eded55d93be5478b1cb84d983ac67c5962fab0acc57e7889c2a1067227fb`.
Current lighting-info SHA-256:
`04987968afd6c451b80d17f8a7a9e5a5039b55b7d8ea784f63ce40f8c477adb8`.
Full-map evidence is `h3-full-geometry-import.json`/`.log` and
`h3-full-map-lighting-verification.json`. No lightmap bake, MCC test, acceptance,
Xbox 360 conversion or installation took place in this checkpoint.

## Preserve original render-BSP collision on a trim instance (2026-11-04)

The original Reach definition 53 (`teleporter_trimlowside003`) has a separate
collision proxy and one render BSP, with no additional physics hulls. Official
source readback finds 103 render-BSP vertices / 101 surfaces, including 18
seamsealer faces. These sealing faces are not part of the 166-triangle visible
mesh. Unchanged Foundry's instance importer imports the collision proxy but
does not recreate that separate render BSP in the Blender render mesh. This
explains a concrete source difference behind this instance's 38 edge errors;
it is not evidence that every remaining instance has the same cause.

The isolated diagnostic uses unchanged Foundry `InstanceCollision.to_object`
to import that original render BSP. It verifies all source vertices and oriented
polygon edge loops, applies stock H3 Collision Only/Precise material controls,
and joins it to a Render Only copy of the visible mesh using Blender's normal
Join operation. The existing collision child remains. Visible positions,
polygons, UVs and corner normals are unchanged (measured normal delta zero).
The helper rejects unsupported surface flags and definitions with additional
physics; it does not silently approximate them.

The first geometry import cleared the edge errors but warned that tangent
generation was skipped. Native vertex readback confirmed zero tangent/binormal
vectors. Blender Smart UV Project on only the newly imported nonvisual faces
resolves this warning without altering source geometry or visible UVs. The
final import has no geometry errors and no untextured warning; all rendered
vertices have nonzero tangent and binormal vectors. Its remaining warning is
the Tool texture-disposal warning. No texture artwork was created or changed.

Native H3 preserves both collision layers: the collision child compiles to
40 vertices / 52 surfaces with MOPP data; the render BSP has 103 vertices /
102 surfaces and zero boundary edges. All 166 render triangles retain winding.
UV differences are at most 0.000007540. Render position differences reach
0.000112375 world units and normal-vector differences 0.000294406, exceeding
the existing strict diagnostic thresholds; they remain reported failures.
Collision-child vertex/centroid samples differ by at most 0.000046947 world
units. The render BSP's complete vertex/centroid samples, compared within each
matching shader group, differ by at most 0.000072318 world units. Its physical
flags match, and all 18 seamsealer surfaces remain. These sample checks do not
establish continuous-surface equivalence, traversal or MCC appearance.

Diagnostic ASS SHA-256:
`e6c441be1f1ba08ebe89aa2a5b27fe3761d2daefa17554b204406577fdb578bc`.
Native BSP SHA-256:
`a971af301e20bfd2778d8e0a5e05113586a16a734f25be1b00e51c20f8f0baef`.
The dedicated kit asset is `levels/custom/bc_render_bsp_probe_53`, avoiding
accumulated diagnostic BSP entries in the older shared test scenario. The first
run in that older scenario reported failure to add another BSP; its geometry
result alone was not treated as a clean import. The dedicated scenario rerun
has no such error.

Evidence under `work/stock-h3-audit`: `original-instance-collision-53.json`,
`collision-workflow-precise-render-only-original-render-bsp-teleporter_trimlowside003-*`
probe/native/XML/geometry-comparison reports, and
`original-render-bsp-native-comparison.json`. The before-collision-UV reports
are retained separately. `wip/h3-original-render-bsp-comparison-teleporter_trimlowside003.png`
was inspected: the source (left) and compiled H3 (right) retain the same frame
shape and visible trim details in neutral Blender shading.

The authoritative map is unchanged at the previous ten-boulder checkpoint:
34 edge-error groups and 14 bad-connection errors remain in its last full
import. Apply this diagnosed standard authoring approach only after checking
each eligible source definition's collision flags, physics and lighting
provenance. The other 56 definitions' separate physics work remains open.

## Two original render-BSP cases applied; trims held (2026-11-04)

All four original render-BSP definitions without extra physics were tested
individually with unchanged Foundry, Blender Join/Smart UV Project and official
H3 Tool. Definitions 160 (`baseblue_ent`) and 339 (`object372`) pass every
existing strict render-position, UV, normal, collision-child sample and
render-BSP material-group sample check. Both native imports have no errors,
retain nonzero render tangent/binormal vectors, and have closed render-BSP
edges with matching physical flags. Original render-BSP counts are retained:
18 vertices / 15 surfaces for 160 and 20 vertices / 16 surfaces for 339.

Blender Join introduced inverse-transform roundoff on the newly appended
collision vertices for definition 160. Restoring only those vertices to their
original local coordinates before saving preserves the imported source data;
all visible positions, polygon indices, UVs and normals remain untouched.
The helper records the roundoff and the exact original appended arrays.

The first four-case application stopped at definition 261's failed collision
sample check before saving. The authoring hash remained
`935da3230a2a5b4f327dfcce2edcba9155f1ddc059d1072e5eff69285d96245e`.
Both trims remain unchanged: definition 53 exceeds strict render position and
normal thresholds; definition 261 additionally reaches 0.000181339 world units
in collision-child sample distance, above the unchanged 0.0001 threshold.
Their clean isolated Tool imports are not treated as passing those checks.

Only definitions 160 and 339 were then applied. Fresh saved-scene readback
verifies exact visible geometry, UVs, corner normals, transforms and original
collision children, plus the complete appended original render-BSP geometry
and standard material flags. The two pending trims are checked unchanged.
The source authoring SHA-256 is
`0524d3870173dca7af7721973cd4b656f1e40e4b77664fcdc4acf6944560d23c`;
the rebound scene SHA-256 is
`76e65cd69a85fcc51730a7ed8c4b8c78799759c96499820f4c7ce74feb4e127e`.
The unchanged material binding workflow assigns 102 tags / 363 used variants
with no pending slots. Water, lighting and previous world/boulder source
preservation checks remain required around the full export.

Evidence is in `work/stock-h3-audit/h3-render-bsp-authoring.json`,
`render-bsp-saved-verification.json`, the per-target
`collision-workflow-precise-render-only-original-render-bsp-*-*` reports,
and `original-render-bsp-native-comparison-*.json`.
`wip/h3-original-render-bsp-comparison-baseblue_ent.png` was inspected: source
on the left and native compiled H3 geometry on the right retain the same panel
outline and lower lip. This neutral Blender proof does not show H3 materials,
baked lighting or MCC gameplay. No lighting bake, MCC launch, 360 conversion
or installation was performed for this geometry checkpoint.

The full export passes saved-scene, world, ten-boulder, two render-BSP, water
and lighting checks: 1,177 instances, 301,630 triangles, 380 ASS material
records. ASS SHA-256 is
`0a3b1b6aca6adbf509d5595d569f918eccae7b6afd4376c02ec494963f1b2969`.

## Return to playable MCC setup (2026-11-04 user steering)

The user called out excessive diagnostic detail and instructed "Move it
along." Prioritize the full-map build, scenario, source sky and lighting;
retain numeric discrepancies in evidence without expanding isolated checks.
Final acceptance still requires the user's MCC review.

The generated `battle_canyon_fresh.scenario` was still an empty solo template:
one BSP, zero skies, zone sets, starting profiles or starting locations, and
no structure-design link. `PrepareH3Scenario.cs` automates only official
ManagedBlam editor fields to create the multiplayer basics using budget 800,
the stock Standoff starting profile, the original Reach scenario's initial
position/facing and the already compiled original water/soft-ceiling design.
It does not fabricate object placement or make the map playable by itself.
Original source placement evidence is `original-lighting-scenario.xml`.
The sky and completed multiplayer placements remain separate work.

The original sky was imported through unchanged Foundry into
`work/stock-h3-audit/battle-canyon-original-sky.blend`: one mesh with 6,577
vertices, 11,637 faces and 13 source materials. This is the source sky model,
not the background rocks already present in the BSP. Native source SHA-256:
`d525e52bec85f9af2627141c7e80d32c7ac720ea4ef317b3b211fb6b46b088ad`.
Saved scene SHA-256:
`a5569eaf92b9ba80c09d29454d10276837c54fc97291e3e6735aab1b611d94b6`.
H3 shader binding, model compilation and the scenario sky reference remain.
See `original-sky-import.json` for source material references.

Official workflow references: [scenario/sky setup](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/quickstart/process/step5)
and [native lighting calculation](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/quickstart/process/step6).
The repository-local kit's unchanged `calc_lm_farm_local.py` supports `draft`
quality; its outputs remain in the kit under the repository.

The full official geometry import completed in 8m32.021s. Error lines fell
from 48 to 45: 32 open/degenerate-edge groups and 13 bad-connection errors.
Both newly applied definitions have no errors; `object372` retains its
transparent-material/two-sided warning. Twelve portal-leak warnings and other
previous geometry/texture warnings remain. All 113 material-lighting variants,
including nine emitting variants, pass actual native readback. Native BSP
SHA-256: `ddf066af7653c5aabb6efd468517762407a0b0aa854ff7f99d27b85e70f643b7`.
This remains an unaccepted diagnostic compile, not an MCC-ready cache.

After the import, the multiplayer scenario setup was saved and verified via
official Tool XML. It now has all 99 original-360 Standoff Forge choices,
matched individually against their MCC authoring references, display names,
costs and limits; the vehicle category stays empty. The original Reach map ID
10020 and initial location (-1.02144, 0.560463, -0.113322), stock H3 Standoff
starting profile, budget 800, one active BSP zone and the existing fresh
structure-design link all pass saved readback. Scenario SHA-256 is
`69415d853be90a2e573a1ed9ef95017baa5bbb4e4219418316a8008ac3514c15`.
`h3-scenario-basic-setup.json` records this later scenario revision; the full
geometry-import report retains its earlier scenario hash. Actual multiplayer
spawn/object placements, sky, atmosphere and lighting are still unfinished.
Do not infer a playable MCC build from this setup.

## Compiled sky and first stock gameplay placements (2026-11-04)

The original Battle Canyon / Halo Reach MCC sky now has all 13 materials
bound to stock H3 shader configurations. Twelve were newly authored; the
sky-rock material reuses the already verified Blackout setup. The ten new
families in `material_families.json` retain the original Reach artwork and
native source functions. Donors include Orbital lightning, Longshore clouds,
Valhalla's skydome, and existing stock H3 self-illumination shaders.
The zero-diffuse behavior uses existing stock black-RGB functions, preserving
source alpha; no shader implementation was written. All imported sky texture
color/alpha checks pass. The moon legitimately has no additional mip levels.
Reach's lens-flare bitmap preset is absent in H3; its sky shader texture uses
the native H3 Self-Illum import with explicit sRGB and passes pixel comparison.

`export_h3_sky.py` applies the established Blender axis/unit conversion and
uses unchanged Halo Asset Blender Development Toolset JMS 8213 export,
including the source transparent-face authoring flags. Official command:
`tool.exe render levels/custom/battle_canyon_fresh/sky draft`.
Tool completed with 13 materials, 6,577 vertices and 11,637 triangles.
It reports a texture-disposal warning, but no ERROR/FATAL lines. Native rendered
vertex colors and sky animation still require MCC verification.

`PrepareH3Sky.cs` uses official ManagedBlam editor fields to connect the
compiled render model through a stock H3 model/scenery container. The donor's
missile sounds and contrail controllers are cleared because the original Reach
sky has no attachments/functions. The scenario now selects this sky on BSP 0.
`verify_h3_sky.py` checks native saved references and all 13 shader bindings.
Evidence: `h3-sky-export.json`, `h3-sky-render-compile.log`,
`h3-sky-verification.json` in `work/stock-h3-audit`.

Actual Blender proof views are `wip/original-sky-east.png` and
`wip/original-sky-west.png`. Both were inspected: clouds and distant cliffs
are present, with lightning visible at the top of the west view. Foundry's
source-material preview overexposes the cliffs. Black below the isolated sky
is the absence of level geometry in this preview. These are source-artwork
WIP views, not H3 rendering, corrected brightness or visual acceptance.
The original saved sky scene remains unchanged.

`PrepareH3BasicPlacements.cs` adds only the directly matched stock entries:
130 neutral respawn points, 13 weapons and 16 grenades, preserving Reach
positions, rotations, unique IDs and spawn settings. The energy sword uses
H3's energy_blade tag; no Reach weapon tag is imported. All 159 placements
passed saved Tool-XML comparison in `h3-basic-placements-verification.json`,
including stock tag paths, transforms, spawn flags/times and parent indices.
Other scenario sections were unchanged from the sky checkpoint.

Still pending: all game-specific initial starts and objectives, two plasma
rifles (stock lookup beyond Standoff), two DMRs and two grenade launchers
(stock H3 role mappings), remaining scenery/crates/effects, water atmosphere,
draft lighting, and the known geometry/collision failures. These placements
are unfinished work, not approved omissions. There is still no accepted MCC
cache, MCC playtest, Xbox 360 conversion or installation for the fresh build.

## Native H3 gameplay layout and draft-lighting attempt (2026-11-04)

The user selected Battle Rifles for the two DMR placements and Brute Shots for
the two Reach grenade launchers. Guardian provides original-360 witnesses for
the Plasma Rifle and Infection haven missing from the Standoff Forge list;
the invisible respawn marker is also present in original Standoff.
`audit_gameplay_extras.py` uses unchanged TagTool against original Guardian
and MCC Guardian. All three roots have matching immediate dependency names.
The two marker objects differ only in platform structure fields in the inspected
output. Plasma Rifle differences include MCC first-person/font fields and
ejection-port recovery (1000 original, 30 MCC). No compensating weapon patch
was authored: retain the MCC authoring infrastructure now and reuse the
original stock object during the later approved 360 conversion.

`plan_h3_gameplay.py` and `PrepareH3Gameplay.cs` map the source placements to
unmodified stock H3 tags through official editor fields. Saved totals are
662 scenery placements, 19 weapons, 43 crates/goals and 18 equipment entries.
This adds 583 entries to the earlier 159-entry checkpoint. The 500 initial
markers represent the same 92 original start positions: the 52 team and 16
neutral positions use each of seven stock mode-specific tags; the 24 Infection
starts use its stock tag. These extra references supply H3's native mode
filtering without modifying the shared stock tags. They are not 500 newly
invented start locations. H3 team/FFA selection remains a specific MCC test.

The other additions include 16 invisible respawn markers, 16 CTF/Assault
respawn zones, all six remaining weapons, both teleporters, both permanent
grav lifts, and the shared mode goals. CTF's source flag/return marker is
represented by separate stock H3 flag-spawn and return-area objects. The
seven Infection havens have a real stock H3 counterpart and are retained.
The native H3 enum spells team eight as `eigth party`; source and target enum
indices were inspected and the spelling is mapped without changing team 7.
Expanded markers receive distinct editor identifiers. Source identifiers
are scoped by object type, so an unchanged crate and grenade may legitimately
share the numeric identifier; the full typed identities remain unique.

`verify_h3_gameplay.py` compares every added saved placement against original
Tool XML: stock references/hashes, positions, rotations, scale, teams,
boundaries, ordering, spawn settings and parent indices. All checks pass.
The earlier placements, Forge choices, sky, profile and other scenario
sections are unchanged by this authoring step. Scenario SHA-256 before
lighting preparation:
`5bcd802906a1dc446337e6f8ddcf07455bd94bfa05b035370c1613ce44bd5b0e`.
Evidence: `h3-gameplay-plan.json`, `h3-gameplay-saved.xml` and
`h3-gameplay-verification.json` under `work/stock-h3-audit`.

55 source scenery/crate records remain pending, including the 23 Reach-only
Stockpile/Headhunter mode markers submitted for the user's decision in
`GAMEPLAY-MAPPING.md`. They are not approved omissions. The Spartan doll is
the one explicit exclusion under the existing user instruction. The pending
work includes original light fixtures, wheel, rock/health-station appearances,
danger zones and cinematic cameras. Audio/effect-scenery placement is separate.

The thirteen placed lights use three source definitions: omni_1 (three),
spot_5 (six) and spot_7 (four). `inspect_source_lights.py` reads their original
fixture/model/marker references and light tags through official tools without
saving them. Both spots use the Reach Forerunner light-gel bitmap; these
lights have not yet been authored into H3. `original-placed-lights.json` and
the corresponding native XML exports preserve the next inputs.

The first WIP draft-lighting attempt is job `2026110401`, launched with
`run_h3_draft_lighting.py`. It follows the native command order in the kit's
unchanged `calc_lm_farm_local.py`, using a distinct job directory and four
native workers. This is the documented [official H3 lighting workflow](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/quickstart/process/step6).
The original scenario/BSP/lighting-info inputs are checkpointed under
`work/stock-h3-audit/draft-lighting-2026110401`; the live report/log are there.
At this checkpoint `faux_data_sync` is still running and consuming CPU. It
has advanced through chart packing to writing the native lightmap (647
meshes copied). The running job is session 24154, native PID 50448, started
2026-11-04 19:16:44 local. Verify live identity/state before process management.
Poll the existing process/session; do not restart from elapsed time alone.
This attempt uses the current material emitters, with the remaining original
light objects and atmosphere explicitly unfinished. A completed command would
not establish visual correctness or waive the known geometry/collision errors.

`import_original_props.py` imports the original wheel, red-base rock, health
cabinet and health-pack appearance into four separate Blender source scenes
using unchanged Foundry. Each scene retains source render, collision and
physics meshes and markers. These are new imports from the official Reach
kit, not recovered outputs from the rejected build. No H3 object tags or
Reach healing behavior were introduced. Wheel animation remains separate.

`render_prop_wip.py` produced actual Blender source previews of the wheel,
rock and health pack, all individually inspected. The wheel shows its red
center and light strips; the rock retains its brown source surface; the
health pack shows its red H panel and decals. Images are
`wip/original-prop-frunner_wheel.png`,
`wip/original-prop-ff_redbase_rocks02.png` and
`wip/original-prop-health_station.png` under `work/stock-h3-audit`. These
use Foundry's source shaders and neutral preview lights, not H3 rendering
or final map lighting. Original saved scenes remain unchanged by rendering.

Existing authored H3 material families cover eight of the wheel's nine
surfaces and the rock's one surface. Five distinct source materials remain
to author: the thin light strips, cabinet, health-pack body, rubber and
shared UNSC decal. Object compilation/placement, wheel animation and H3
appearance remain unfinished; imported source meshes are not accepted assets.

## Prop materials and native render models (2026-11-04)

All five remaining prop surfaces now use stock H3 setups with original Reach
artwork. `inspect_prop_materials.py` extends the source inventory from actual
Foundry import reports and invokes the existing native input/default and
inheritance readers. Families in `material_families.json`:

| Family | Stock donor |
| --- | --- |
| prop_light_strips | Standoff sky road, diffuse-only |
| prop_health_pack | Stock monitor base |
| prop_health_rubber | Gravity hammer dull surface |
| prop_health_cabinet | Standoff ceiling |
| prop_unsc_decal | Stock human industrial decal |

All five donors occur in original-360 Standoff. Native option vectors match
MCC; the hammer's `first_person_sometimes` setting has an original-cache
world-model material witness. The decal matches all six H3 categories; its
extra Reach parallax and `interier` options are both off. The authoring guard
rejects active unmatched decal options. No shader program was authored.

For each family, the established sequence completes: `prepare_family_donors.py
--family <name>`; `author_wall_family.py --family <name> --prepare`;
`inspect_wall_bitmaps.py --family --family-name <name>`; `author_wall_family.py
--family <name>`; `verify_wall_family.py --family <name>`. Original textures
are extracted using unchanged Foundry `extract_reach_bitmaps.py` as needed.
Native saved inputs/functions and texture comparisons pass (13 family image
entries, including shared images). Source physical-material names are empty;
`author_physical_materials.py --props-only` retains donor defaults and performs
zero material-name writes. Other authored surfaces are untouched.

`export_h3_props.py` binds reviewed shaders and invokes the unchanged JMS 8213
exporter. `compile_h3_props.py` invokes official `tool render ... draft`, then
checks native saved shader references and original triangle counts:

| Native render model | Vertices | Triangles | Shader references |
| --- | ---: | ---: | ---: |
| frunner_wheel | 11,281 | 7,700 | 9 |
| cex_health_cabinet | 518 | 604 | 2 |
| ff_redbase_rocks02 | 1,832 | 3,014 | 1 |

Evidence: `h3-prop-<name>-export.json`, `h3-prop-<name>-compile.log`,
`h3-prop-<name>-render.xml` and `h3-prop-<name>-verification.json` under
`work/stock-h3-audit`. These are render models, not finished objects: native
collision/physics, scenario placement, wheel animation and MCC appearance
remain unfinished. Original source scenes remain unchanged; source collision
and physics meshes are retained in the new authoring scenes.

The health-pack model has 564 faces with Reach's medium-distance detail
culling and 12 transparent faces. `InspectH3PropFlags.cs` reads the actual H3
part flag names: dislikes photons, ignored by lightmapper, has transparent
sorting plane, and is water surface. There is no matching detail-distance
flag. Health-pack export stays stopped pending the user's decision to retain
those details using normal stock H3 object visibility. No geometry is removed;
healing stays excluded. Evidence: `h3-prop-native-flags.log` and
`export-h3-prop-health_station.log`. This is not an approved omission.

Draft job `2026110401` completed data sync (860.7 seconds) and farm begin.
Four direct-lighting workers are live at this checkpoint (session 24154;
PIDs 38232, 48340, 47248, 27340, started 19:33:22 local). Worker 0 reports
`shooting rays away from the plane` errors. Preserve the job and inspect its
existing handles; these errors remain unresolved even if a process later
returns zero. Lighting is not accepted. The running wrapper predates the
added timeout child cleanup: if it times out, revalidate and manage only its
owned children rather than leaving an orphan bake.

## First native MCC cache and prop collision checkpoint (2026-11-04)

Draft job `2026110401` is now terminal: all 31 official commands returned zero.
The earlier live-process entry above is historical. Data sync logged 14,873
out-of-bounds UV errors; the four direct-lighting logs contain 104, 262, 155
and 152 ray errors. These remain unresolved. A successful native return code
is not visual acceptance. `verify_h3_draft_checkpoint.py` checks all 181
scenario sections against the saved gameplay baseline: only the native
`new lightmaps` reference changed; the other 180 sections match exactly,
including gameplay, sky and Forge data.

`build_h3_cache.py` runs the official
`tool_fast.exe build-cache-file levels\custom\battle_canyon_fresh\battle_canyon_fresh x64`
command, following [Microsoft's cache-build workflow](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/quickstart/process/step9).
The first WIP cache compiled in 155.2 seconds, return code 0, with Tool's
`successfully built cache file` message. Output is
`work/editing-kits/h3ek/maps/battle_canyon_fresh.map`, 1,104,592,896 bytes,
SHA-256 `eeff4be6579e67c9ab89b4924f0eb1c5db5b608f83f03f9da71f68bde95d3476`.
This is an unfinished packaging checkpoint, not an installed review build.
Props, effects, atmosphere, audio, lighting/geometry corrections and MCC
visual/gameplay testing remain. No MCC approval or 360 conversion occurred.

Three cache-build errors name animation/render node-count mismatches on the
unchanged stock permanent gravlift, gravity hammer and red powerup. Native
`InspectStockAnimationNodes.cs` confirms the kit references. Unchanged TagTool,
automated by `audit_stock_animation_nodes.py`, checks original Xbox 360
Standoff, shipping MCC Standoff and the fresh cache: all three compiled models
have null animation references and matching node counts of 1, 2 and 1,
respectively. All inspected cache hashes remain unchanged. No custom stock-tag
fix is justified by these warnings; gameplay behavior still requires MCC testing.

`export_h3_prop_collision.py` uses unchanged Blender/JMS 8213 export and
preserves source collision geometry/material names. Official `tool collision`
compiled the wheel, cabinet and red-base rock without warnings/errors; saved
collision error blocks are empty. Input polygon/triangulated face counts are
60/144, 22/48 and 728/750. An initial report incorrectly called polygon counts
triangles; refreshed reports distinguish them and produce identical JMS hashes.
The wheel uses `hard_metal_thick_for`, rock `hard_terrain_stone_rough`, and
cabinet retains the source's literal `default` identifier. The cabinet's final
global-material resolution still needs checking; it has not been retuned.
Physics, object setup/placement, wheel animation and in-game collision remain.

Evidence under `work/stock-h3-audit`: `draft-lighting-2026110401/report.json`
and logs, `cache-build-2026110401/report.json` and `tool.log`,
`h3-draft-checkpoint-verification.json`, `stock-animation-cache-audit.json`,
`h3-prop-<name>-collision-export.json`, native collision XML and compile logs.

## Native prop physics and static object tags (2026-11-04)

`inspect_original_prop_physics.py` follows the original objects' references
with the official Reach API and exports source object/model/physics XML with
Tool. All four source models resolve. The wheel has an animation graph;
the cabinet, red-base rock and health-pack model do not.

`export_h3_prop_physics.py` exports the three already-bound prop scenes through
the unchanged Halo JMS exporter. Each source physics model has one convex
polyhedron and one rigid body, without joints or other shapes. Original
vertices and source physical-material names are retained in Blender inputs.
Official `tool.exe physics levels\custom\battle_canyon_fresh\props\<name>`
produces each H3 physics model. `PrepareH3PropPhysics.cs` preserves the original
motion types through native fields: wheel `box`, cabinet and rock `fixed`.
The cabinet and rock's initial native `box` defaults are saved before editing.

`verify_h3_prop_physics.py` reads the resulting native tags. Vertex counts
are 72, 16 and 64. Render, collision and physics node names/hierarchy agree;
unchanged exporter prefix handling maps the wheel's `b_pedestal` to `pedestal`.
The source-to-native point comparison is **not exact** for wheel/rock: maximum
XML point deviations are 0.0284062 and 0.0284114 world units. Their native bounds
also differ. The cabinet's points match, but Tool warns that its 0.0115-wide
bounding dimension is below 0.0410 and will not be represented accurately.
These differences/warnings are preserved in the report, not fixed by custom
geometry code or waived as accepted collision. No additional isolated
numerical-difference experiments were added; actual collision remains for MCC.

`PrepareH3StaticPropObjects.cs` creates native `.model` and `.crate` tags for
cabinet and red-base rock using the official New/Save workflow. They link the
compiled render/collision/physics tags and preserve the original default
variant/region/permutation. The cabinet source model explicitly maps its
`default` collision material to `hard_metal_thin`; that exact global material
exists in original Standoff and is now assigned in H3. The rock's original
`default` model-material mapping to `hard_terrain_stone_rough` is also retained.
Native XML readback checks all three model links, both crate links, default
variants and material mappings. There are no attachments, functions or health
packs. These fixed props add no entries to the approved stock Forge palette
and import no Reach-only Forge-phasing behavior.

These two object tags are **not yet placed** and are absent from the first
cache. The wheel's object/animation setup, health-pack visibility decision,
source prop placements and actual MCC appearance/collision remain unfinished.
Next connect the static objects to their original placements, then continue
remaining fixtures/effects/atmosphere and resolve the native lighting errors.

Evidence under `work/stock-h3-audit`: `original-prop-native-dependencies.json`,
`original-prop-<name>-{object,model,physics}.xml`,
`h3-prop-<name>-physics-export.json`, native compile logs/physics XML,
`prop-motion-authoring.log`, `h3-prop-physics-verification.json`,
`static-prop-object-authoring.log`, and `h3-static-prop-object-verification.json`.


## Current original-H3 draft — 2026-11-04

The user waived MCC playtest/approval and set a one-hour original-H3 target.
Current source cache job 2026110402 compiled successfully (1,105,653,760 bytes,
SHA256 1ce500cde63d49f220d0eaa47acd7337be12ef26a9817d09ab06fd513d45c04c).
It now includes the original wheel animation, all 13 approved native H3 lights,
four cabinets plus their stock Territories markers, and the red-base rock.
The light gel preserves original decoded RGBA exactly. Unfinished effects,
atmosphere, audio, existing geometry/lightmap warnings and gameplay review remain.

Native preflight found 50,702 world collision planes / 74,765 edges and 765
scenario placements. Standard Blender decimation is being applied only to the
nonvisual world collision; the original scene is retained. Native stock initial
spawns now retain all 16 FFA starts, four per team per mode, and all infection
starts: 625 total scenario placements. This first-review population reduces
initial position choice for larger teams; all normal respawn points remain.
The original scenario is retained in scenario-before-360-start-budget.scenario.
No old Battle Canyon collision or material repairs are used.
