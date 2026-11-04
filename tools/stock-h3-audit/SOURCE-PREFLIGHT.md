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

H3's installed `ManagedBlamSystem.Start` throws `NotImplementedException` for
both overloads. Do not keep retrying or patch that DLL. The official `tool.exe`
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
