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
