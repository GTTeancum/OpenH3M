# Warlock conversion: working checkpoint

This preserves the map-side conversion process that produced recognizable Warlock
in the unchanged OpenH3M runtime. The owner tested solo and reported good collision
and visuals on 2026-10-18. This is a checkpoint, not a complete general converter.
No game assets, maps, screenshots, runtime binaries, or generated logs are included.

## Integrated scenario checkpoint

`snapshot/tools/build_scenario_checkpoint.py` combines all BSP material slots,
object, sound, spawn, sky/environment and decal importers into a separate map file. This
command still requires the accepted geometry checkpoint (SHA256 below); it is
not the final seed-independent converter. Material/reflection approximations are
listed in its report. Run with `python -B` from this checkout:

```powershell
python -B tools/warlock-conversion/snapshot/tools/build_scenario_checkpoint.py `
  --project C:/X360/ISOs/H3M `
  --source D:/SteamLibrary/steamapps/workshop/content/976730/2977651586/maps/warlock.map `
  --basis ../candidate/lockout.map --xex ../../default.xex `
  --sound-bank "D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo3/fmod/pc/sfx.fsb" `
  --decoder ../tools/vgmstream-r2117/vgmstream-cli.exe `
  --output ../integrated/lockout.map --report ../reports/scenario-checkpoint.json
```

All generated paths are confined to the declared project's `.local` directory.
The output must not already exist. The command preserves the basis, derives real
resource hashes from the supplied XEX, stages in a temporary sibling, reopens and
checks the serialized cache/tag registry, then renames it into place. Failed
temporary maps are removed; the report records the failed stage and error.
No deployment or native launch is performed. The report lists imported tags,
material approximations, source/output hashes and unfinished conversion scope.

## Restore the working layout

The snapshot deliberately preserves the exact scripts used for the successful map.
Copy snapshot/tools to <disc-root>/.local/tools and snapshot/reference to
<disc-root>/.local/reference; copy snapshot/Run-Warlock.cmd to <disc-root>.
Use an explicitly authorized project directory as disc-root. The current directory
is C:\X360\ISOs\H3M. Python paths derive this root from .local/tools.
Install requirements using a project-local environment and pip cache. Use python -B
and run from disc-root so no bytecode/output escapes the project.

Private prerequisites (not distributed):
- Original Mythic disc data, including default.xex and maps/lockout.map.
- Earlier conversion seed at D:/Programming/GitHub/H3M/game/maps/lockout.map.
  SHA256: a2cf1f69bef10728b380848a2217bb69c2779797929a03beff17c8e64012d558
- MCC Warlock workshop map at
  D:/SteamLibrary/steamapps/workshop/content/976730/2977651586/maps/warlock.map.
- Unchanged runtime at D:/Programming/GitHub/H3M/OpenH3M.exe for manual testing.

These historical paths are hardcoded in the snapshot. Update them for another
installation. The initial seed creation process was lost in the earlier chat;
this checkpoint reconstructs its relocation and material stages, not that seed.
Create .local/reports and .local/candidate before running the pipeline:

    python -B .local/tools/audit_mcc_visual.py
    python -B .local/tools/import_materials.py
    python -B .local/tools/diagnose_loading.py

import_materials invokes relocation first and replaces the candidate in place.
Close OpenH3M before rebuilding. Never use a stock map hardlink as the candidate.
The existing test-game layout uses original disc assets and a hardlink only to the
separate generated candidate. A fresh installation still needs this layout built.
The launcher expects .local/test-game/maps/lockout.map and uses Blackout's slot:
Custom Games > Blackout > Slayer.

Optional focused checks: check_texture_encoding.py, compare_geometry.py and
compare_render_buffers.py. trace_loading.py is an optional Windows child-process
debugger for a matching runtime build. It restores temporary breakpoints, logs
loading failures, and uses a bounded watchdog. --capture uses native game capture;
no desktop capture or OS input is used. Do not assume its fixed addresses or input
script support work on another runtime build.

## Confirmed checkpoint and limits

Final candidate SHA256:
499f0516e016524f7f8a98ca580e4acb66c2b5d58403a5c755e4ed8f23de4279
Size: 210231296 bytes. Primary positions/UVs and index buffers matched source;
packed basis vectors matched within 0.005. Native bounded load observed five hash
passes, zero failures, and no fatal exception. Solo visual/collision acceptance
comes from the owner. Multiplayer, audio, game modes and system link are not verified.

Implemented: fixed retail tag-memory boundary, schema pointer relocation, page and
header hashes, required soft surfaces, Xbox texture tiling/endian conversion,
source diffuse/alpha materials, camera exposure and authored Slayer spawn positions.

Remaining code completion:
- Reconstruct a reproducible source-to-retail geometry/resource pipeline without
  the unavailable earlier seed generator; configurable inputs and one entry point.
- Inventory and handle omitted material slots, normal/detail maps, terrain blending,
  remaining hologram approximations and mip/format support as required by this map.
- Audit and convert remaining scenario objects, game-mode placements, sky/atmosphere,
  decals, lighting and audio dependencies with explicit unsupported-item reporting.
- Make generation transactional, document deployment, and bound/clean generated
  data. Use focused structural checks and at most a minimal native smoke test.
- Do not change OpenH3M or introduce runtime workarounds. Leave exhaustive gameplay
  testing to the owner; do not claim system-link compatibility without evidence.

## Reference provenance

reference/plugins and reference/mcc contain Halo3/Halo3MCC XML schemas from
https://github.com/XboxChaos/Assembly (dev branch); see Assembly-LICENSE.
The tiling algebra is based on xenia-project/xenia texture_address.h; see
xenia-LICENSE. xexlib.py originated in this repository's halo3mp/tools/xexlib.py.
The private source map is Neckzilla's Warlock workshop item 2977651586.

## Completion work in progress

inventory_conversion.py accepts --source, --candidate and --output paths and writes
an explicit scenario/dependency inventory without extracting assets. Its placement
planner converts records semantically, including changed flag bit positions; it
refuses unmapped strings, nonempty nested blocks and unsupported fields.

2026-10-18 inventory: 120/127 scenery, 14/16 weapons, 22/23 equipment and 6/18
crates can reuse named retail tags. The remaining 22 placements need dependencies
imported (custom props, Automag, powerup, teleporters and jump pads). These counts
are preparation evidence only: the scenario assembly stage still needs to rebuild
palettes and remap name/parent indices before publishing placements to a map.
Actual-source checks preserved transforms and object IDs for all 162 convertible
records, verified retail tag salts and confirmed Create At Rest remaps bit5 to bit8.
The accepted gameplay candidate has not been replaced by this unfinished stage.

The bitmap encoder now supports A8, Y8, XRGB32 and ARGB32 source textures using
lossless ARGB32 expansion and Xbox tiled 8-in-32 storage. This removes the format
blocker for 13 formerly skipped material slots. The selected mip remains capped
at 512 pixels; this is not a full mip-chain implementation. Non-2D textures and
missing requested mips are rejected explicitly. check_uncompressed_textures.py
accepts --source, --material-inventory and --output; actual source data passed
independent address, channel and exact selected-mip roundtrip checks. Native
rendering of these new formats is not yet verified; no candidate was overwritten.

assemble_scenario.py now prepares retail placement arrays, 48-byte palettes and
stable object-name indices with remapped placement references. stage() rejects
unresolved dependencies before touching the builder. Actual source preparation
produced valid palettes for 162 placements; 22 missing object dependencies plus
8 unresolved name references prevent publication. This stage is not integrated
into a generated map yet. object_dependencies.py accepts --source, --candidate,
and --output and traces the eight missing object tags' direct dependencies.
The custom blue powerup and sender reuse existing retail dependency tags; the
Automag additionally requires its own models, animations, projectile, HUD, light
and firing effect. No silent weapon/object substitutions are made.

object_variants.py resolves two custom object tags after comparing their complete
schema-described contents against the corresponding stock MCC tags, including
nested arrays and function payloads. The custom sender is equivalent; the blue
powerup changes only Bounding Radius from 0.30 to 0.35. The resolver reuses the
retail sender and allocates a retail powerup clone with that source radius, while
preserving retail pointers and dependencies. Unexpected differences are errors.
An in-memory assembly check now prepares all 23 equipment and 10/18 crate entries;
remaining custom object dependencies still prevent complete scenario publication.
No new gameplay candidate has been written by this stage.

string_ids.py resolves MCC U13 namespaces from the source header and retail Halo 3
namespaces from Assembly's definition, then translates identifiers by exact table
text. This is required for model regions, attachment markers and object functions.
It rejects missing target strings rather than copying incompatible numeric IDs.
All 18,558 source and 17,704 candidate table indices passed ID/index roundtrips;
actual teleporter_active, teleporter_blocked, effect, one and powerup_pickup_blue
references mapped to their matching retail names. Legacy non-UTF8 bytes are
preserved losslessly. Adding new strings to the retail table remains to implement.
The remaining object graph includes custom render/collision/physics resources,
plus Automag animation and HUD content; those imports are still incomplete.

MetadataConverter in tag_metadata.py now recursively converts described tag
metadata into retail layout: endian-aware scalar fields, semantic flags/enums,
translated string IDs, resolved tag references and allocated nested blocks.
It rejects unresolved resources, opaque data without a handler, nonzero unknown
fields, incompatible field sets and uncovered/overlapping schema bytes. It expects
a scratch builder; callers must discard the whole scratch build on failure.
Actual MCC respawn-point and CTF initial-spawn scenery (256-byte retail roots) and
the standard sender model (392-byte retail root) converted in memory using real
retail dependencies. These checks establish metadata conversion only, not custom
render resource conversion or new gameplay output.

render_buffers.py encodes MCC rigid/world primary vertex buffers into retail
24/32-byte strides, preserving position/UV bits and packing basis vectors into
signed 10:11:11, plus 16-bit index endianness conversion. Against the accepted
candidate: all 495 primary buffers preserve positions/UVs; all 500 index buffers
match byte-for-byte. Maximum basis error versus source was 0.0009783. Basis bytes
need not match the old encoder because rounding differs. Skinned/auxiliary streams,
resource-control assembly and native rendering of new output remain unfinished.
Some stock comparison assets use shared.map pages; resource_reader currently
rejects these explicitly and needs a configurable shared-cache reader.

Resource now accepts an explicit shared_paths mapping for retail shared pages.
It reads only the requested compressed byte range from an explicitly mapped
cache, uses that cache's raw-section base, and retains size/CRC checks. Embedded
map paths cannot open host files implicitly. The original shared.map successfully
provided the stock first-person assault-rifle resource for comparison.
Skinned primary vertices (format3) now convert 44 -> 32 bytes, preserving the
four bone indices and four weights without swapping. A matching 2,918-vertex
source/retail assault rifle confirmed exact position/UV and bone-field layouts.
All eight custom/Automag model primary streams converted in memory, including
skinned Automag and receiver streams. Auxiliary PRT streams still need decoding;
the source/retail comparison did not justify treating them as raw endian swaps.
No candidate map was generated or deployed by these checks.

render_resource.py assembles complete render-resource payloads (control records,
raw buffers, fixups and interops) without writing a map. All eight custom/Automag
models now convert in memory, including ambient and quadratic PRT auxiliary
streams; their indices and pointer bounds passed focused checks. Ambient
quantization error stayed within half an 8-bit normalized step. Static per-pixel,
static per-vertex and linear PRT conversions are also implemented; native use is
not yet verified. Zone/play registration, tag graph assembly and manifests remain.
The auxiliary format descriptions were checked against TheGuardians/TagTool
VertexStreamHalo3RetailMCC.cs, VertexStreamXbox.cs and VertexElementStream.cs;
reference copies and TagTool-LICENSE are included alongside the existing sources.

cache_registry.py now registers new tags and resource pages, compresses payloads,
calculates salted full/first/last SHA1 plus complemented CRC32, emits zone/play
records and marks new resource/owner bits in the selected static BSP manifest.
It resolves resource type indices by their actual string names and updates required
resource size. An isolated serialized-map check reopened a newly registered tarp
render resource with exact control bytes, fixups and decoded GPU data, valid page
CRC, matching owner reference, required-resource bit and fixed tag-memory end.
The temporary validation map was removed; the accepted candidate was untouched.
Native loading, complete custom tag graphs and scenario publication remain pending.

TagImporter now walks dependencies, reserves tags before recursion, converts model
resources through CacheRegistry and prevents finalization after any failure.
WritableStringTable appends missing names while preserving existing string IDs;
MapBuilder can grow the debug section and adjusts resource/metadata/localization
physical masks. A serialized check preserved every existing string, added
`tarp_box_stack`, and reread the original BSP resource with CRC verification.
The temporary check map was removed. Zero high MCC instance-mask words can now
be omitted when converting to retail's shorter mask; nonzero high words reject.
The tarp import now reaches its custom tarp_cover shader. A dedicated material
handler is needed; generic copying of MCC shader postprocess resources is rejected.
The complete dependency graph and final map remain unfinished.

MaterialImporter now handles custom rmsh/rmfl and bitmap dependencies through the
resource registry. It imports base/detail/normal textures and matches float
constants by rmt2 parameter names rather than source array positions. Exact MCC
shader variants are not generally available in the retail cache: the existing
proof templates are used, and the report lists every unrepresented texture and
constant. This is an explicit visual approximation, not shader parity.
The tarp-box render model now imports through the full dependency/resource path,
including its material and observed 20-byte PRT-info descriptor. The enclosing
object import reaches collision BSP physics, where MCC/retail layouts differ and
still require a dedicated handler. Incomplete graphs remain unpublishable.

collision_physics.py translates MCC 64-bit collision shape headers into retail
32-bit layouts, including the extra MCC large-BSP runtime pointer omitted by the
older XML offsets. AABB, shape references, scale and model references are rebuilt;
runtime pointers must be null. MOPP headers/data are allocated and supported
32-bit terminal keys translated back to retail bit placement; unsupported opcodes
or nonrepresentable keys fail. Shape/layout references are included from TagTool.
Retail model variant/state padding is initialized for the explicitly supported
stateless variants. All three tarp props now complete in-memory graph import:
12 object/model/collision tags plus material/bitmap dependencies, covering seven
previously missing scenery placements. Native behavior remains unverified.

Physics dependency checkpoint:
- Added guarded MCC-to-retail rigid body, polyhedron, list, child-shape and
  phantom conversion. Runtime pointers must be null; polyhedron self offsets
  are rebased to the retail stride and the root 64-bit-layout flag is cleared.
- Compared 13 stock receiver/jump-pad records against original salvation.map:
  12 were byte-identical after string ID translation. The list differs only in
  a source radius rounding bit after normalizing its homogeneous center w to
  retail zero. No map output was written during this check.
- The complete Warlock jump-pad dependency graph now imports in memory. The
  receiver passes physics and scalar identity-function conversion, then stops
  at its effect dependency. Other function curve formats remain explicit errors.
- Added Assembly phmo schemas and retail effe schema, plus TagTool TagFunction
  format reference (same upstream repositories/licenses listed above).
- These changes are not deployed to the user-tested candidate. Effects,
  Automag, remaining scenario/environment content and pipeline integration are
  still outstanding; this is not a code-complete claim.

Receiver and Automag animation checkpoint:
- Both receiver and jump-pad complete dependency graphs import together in a
  scratch builder. Shared effe/jmad/ligh/jpt! layouts follow Assembly's explicit
  Halo3MCC -> Halo3 plugin fallback; only verified absent overrides use it.
- Added animation resource conversion for codecs 1, 3, 4, 6 and 8, retaining
  compressed samples/keyframes and converting header, sample and flag endianness.
  All 31 Automag world/first-person animation members convert (2 world, 15 human,
  14 elite). Other codecs and movement payloads reject explicitly.
- Added HUD flag-width translation, alpha color fields, weapon range fields,
  and simple constant/identity/transition functions used by lights/vibration.
- Automag metadata uses retail Magnum pickup-message index/sort order and damage
  reporting category. MCC's optional centered-crosshair offset is omitted in
  favor of the ordinary weapon offset. These are explicit compatibility notes,
  not claims of identical UI. Retail-only collision sound/aged weapon are null.
- The Automag graph now reaches its custom silenced gunshot. New sound tags
  deliberately reject pending audio conversion and ugh! table rebasing; copying
  their MCC indices would be invalid. Existing same-name retail sounds still reuse
  the retail tag. No partial Automag map can be finalized after that error.
- Checks were in memory; the private report is .local/reports/
  receiver-jump-animation-import.json. No runtime changes, map writes or captures.
  Gameplay, animation playback and audio remain unverified by this checkpoint.
- New format sources are Assembly Engines.xml and TagTool animation resource/codec
  implementations, under their already included upstream licenses.

Automag audio checkpoint:
- The custom silenced gunshot has an empty MCC resource page; its four permutation
  hashes resolve to the installed halo3/fmod/pc/sfx.fsb, not embedded map audio.
- fmod_audio.py reads the 280-byte .info index and decodes a selected hash with an
  explicitly supplied vgmstream CLI. It pipes WAV to memory, converts PCM16 to
  big endian, uses a bounded timeout, and redirects temp paths to the supplied
  repository-local working directory. No sound playback or extracted bank copy.
- All four hashes decode to stereo 48 kHz: 64320, 60995, 57891 and 70433 frames.
  The private report is .local/reports/automag-audio-decode.json. This proves
  decoding/format, not audible in-game playback.
- CacheRegistry now accepts the native sound-resource convention: zero serialized
  control bytes and one data-pointer fixup at offset 12. Compared with the native
  magnum sound resource. Sound-table rebasing/integration remains outstanding.
- Local decoder: vgmstream r2117 win64 from the official GitHub release, installed
  under .local/tools/vgmstream-r2117. Its downloaded ZIP was removed after setup.
  Binaries and audio assets are not versioned. Future callers must supply their
  own decoder path; no machine-specific decoder path is embedded in source.
- Reference additions: Assembly ugh! schemas and TagTool FMOD index/bank and sound
  converter sources, retaining the licenses already included in this snapshot.

Retail sound-table checkpoint:
- sound_importer.py appends decoded PCM sounds to ugh! codec, playback, scale,
  import-name, pitch-parameter, pitch-range, permutation, runtime-flag and chunk
  tables. Existing entries retain their indices. MCC's packed 20-bit permutation
  index is converted to the retail count/index fields with representability checks.
- The Automag imports its shot plus indoor/outdoor tails: three sounds, ten
  permutations, stereo/quad 48 kHz PCM16 big endian. The supplied bank/decoder
  remains optional; unresolved sounds fail explicitly when none is supplied.
- Focused in-memory finalization checked ten chunk references, frame bounds,
  runtime-flag references and unchanged prefixes of every modified retail table.
  Private results: .local/reports/automag-sound-tables.json. No map was deployed,
  and native PCM playback is not yet verified. Localized/promoted sounds and
  nonempty encoded-permutation sections remain unsupported with explicit errors.
- The full Automag graph advances to its muzzle-flash particle postprocess.
  Its matching native particle shader template exists, but binding the source
  parameters to retail shader data remains to implement; MCC compiled shader
  resource data must not be copied into the retail cache.
- Added the paired Assembly particle schemas. Missing documented particle runtime
  flags were filled from TagTool Particle.cs (comments identify these additions).
  PitchRange.cs and SoundCacheFileGestalt.cs document the sound index packing.

Primary object assembly checkpoint:
- The complete Automag graph now imports: its muzzle-flash particle binds to the
  exact existing retail template, transfers all named textures/constants and
  sampler fields, and retains native shader routing rather than MCC shader code.
- Added identity/constant/transition/multispline function conversion, including
  ranged functions and color outputs. Unsupported spline sections still fail.
- Corrected effect root runtime-flag positions using TagTool's distinct MCC and
  original enums. Assembly's shared effe layout had incorrectly implied identical
  flag semantics. Both effect schemas now document the explicit platform mapping.
  Particle movement Wind bit 8 was also verified against the native magnum.
  MCC's enhanced-graphics near-fade override is omitted in retail.
- stage_primary_objects(importer) imports every used primary palette entry,
  applies the verified sender/powerup variants, and stages the complete arrays.
  Focused combined finalization succeeds with 127 scenery, 16 weapons, 23 equipment,
  18 crates and 17 object names; zero unresolved entries, 37 new metadata tags.
  Private evidence: .local/reports/primary-object-assembly.json.
- This remains an in-memory checkpoint. No candidate map was replaced or run.
  Simulation registration, other scenario/environment blocks, remaining material
  work and the reproducible source-to-retail entry point remain outstanding.

Spawn and simulation checkpoint:
- Registry finalization preserves the retail Simulation Definition Table and
  appends new gameplay/effect definition tags in allocation order. Existing
  network-definition indices stay unchanged; this does not prove system-link.
- stage_spawn_settings imports the authored starting profile, fallback starting
  location and five spawn-influence records. Warlock's empty Spawn Data record
  becomes the corresponding zeroed retail record; nonempty overrides still reject.
  MCC editor-folder padding is omitted only for the observed neutral values.
- Combined object/spawn finalization preserves all 1192 existing simulation
  definitions and appends 11 valid new datums (1203 total). Verified the unchanged
  prefix, appended uniqueness and tag salts in memory. Private report:
  .local/reports/spawn-and-simulation.json. No map deployment or runtime claim.
- Next populated placement groups: 66 Sound Scenery and 6 Effect Scenery, each
  with six palette dependencies absent from Blackout. Effect placement record
  layouts already convert; sound placement records need rangef scalar support.
  Ambient sound/effect graphs, decals, atmosphere and other environment work remain.

Ambient sound placement checkpoint:
- Added ssce/efsc schemas and the verified shared Halo3 lsnd layout. The six
  source sound-scenery graphs import successfully with their looping/detail
  sound dependencies and source placement distance/cone overrides.
- stage_primary_objects now accepts include_sound_scenery and
  include_effect_scenery switches. Placement planning and object-name mapping
  use the selected groups; failures include the first unresolved records.
- Combined in-memory finalization includes all 184 primary placements plus
  66 Sound Scenery placements (six palette entries), spawn settings and network
  definitions. Eleven new sound tags contain 54 decoded permutations in total.
  Private evidence: .local/reports/ambient-sound-assembly.json. Not deployed;
  looping behavior, spatial audio and playback remain user/runtime validation.
- Six effect-scenery dependencies were probed. Remaining failures include a
  missing exact native particle template and water-ripple render-method handling.
  Added documented particle animation flags (Disable Frame Blending and bit 3)
  from TagTool Particle.cs. No effect placement was silently omitted from output.
- No decoded audio files, extra maps, captures or temporary extracted banks were
  created. The reusable decoder installation remains under the workspace .local.

Effect placement checkpoint:
- All 256 authored object placements now stage together: 184 primary objects,
  66 sound scenery and six effect scenery. The effect palette compacts to its
  three actually used entries. No unresolved placements in the combined build.
- Added the shared rwrd water-ripple layout and periodic/remaining multispline
  function payload conversion. All work remains in memory; candidate unchanged.
- Two missing particle shader variants use explicit, reported proof-of-concept
  aliases after checking for an exact native match first. Falling-stream particles
  allow LDR+HDR instead of LDR-only; splash particles use alpha blend instead of
  premultiplied alpha. Texture/constant names must match exactly. Root option
  values, blend constants/state and LDR runtime flag are updated consistently.
  These visual approximations remain unverified in-game and may change brightness
  or edge blending. They are not silently presented as exact shader conversion.
- Private combined report: .local/reports/all-object-assembly.json. No screenshots,
  game launches, decoded-audio files or new map files were needed this checkpoint.
- Environment/sky/decals, map materials and the final seed-independent pipeline
  remain outstanding; successful object assembly is not final completion.

Sky and acoustic environment checkpoint:
- Added explicit environment staging for Skies, Atmosphere, Acoustics Palette,
  Scenario Cluster Data and the Sky Parameters reference. The cluster data binds
  to the existing converted retail BSP by index; mismatched BSP counts reject.
- Added paired-platform static per-vertex float3 color endian conversion (format
  14), allowing the source sky model's full render resource to import. Sky materials
  still follow the existing reported native-shader approximation policy.
- Added verified shared skya/snde schemas. Both source reverb definitions and the
  Guardian background sound graph import through the existing sound-table path.
- Combined in-memory finalization now includes all 256 object placements, spawn
  settings, one sky, two atmosphere entries, two acoustic entries and one cluster
  environment block. It imports 73 metadata tags and 19 sound tags, using about
  1.93 MB of metadata reserve. Private report:
  .local/reports/objects-and-environment.json. No map output/deployment or captures.
- Sky appearance, background audio/reverb and cluster behavior remain unverified
  in-game. Decals, remaining material/global-lighting work and the reproducible
  seed-independent build/deployment entry point remain outstanding.

Decal conversion checkpoint:
- `stage_decals()` imports all 51 used decal definitions and stages all 586
  placements with a compact palette. It refuses unresolved dependencies before
  replacing scenario arrays. Added MCC/retail decal schemas and documented flags.
- Exact native shader templates are reused where available. Explicit aliases
  cover missing tint and render-pass variants; no MCC shader bytecode is copied.
- Foliage keeps its alpha cutouts. Identical untiled masks share base alpha;
  independent masks are baked into tiled diffuse color. The POC bake uses nearest
  sampling, a 512-pixel limit and one mip. Normal-map UV scale retains authored
  tiling. RGB shares mask sampler behavior, fully modulated tint becomes
  unmodulated, and MCC transparent decals use the native pre-lighting pass.
  Sprite atlases and unsupported sampler routing reject explicitly.
- Mask-coordinate semantics were checked against the `sample_diffuse` function
  in [HaloShaderGenerator's decal shader](https://github.com/Beatthezombie/HaloShaderGenerator/blob/master/halo_online_shaders/decal.fx).
  `snapshot/reference/formats/DecalSystem.cs` is the TagTool structure reference.
- Focused checks verify independent mask alpha, diffuse tiling, all 586 placement
  transforms and palette bounds, plus combined object/environment finalization.
  Private report: `.local/reports/objects-environment-decals.json`. This remains
  in-memory verification; decal appearance is not yet verified in-game, and the
  accepted candidate has not been replaced. Final pipeline work remains open.

Environment control checkpoint:
- Environment staging now binds Warlock's Camera Effects, Global Lighting and
  Performance Throttles, and explicitly copies/nulls Global Screen Effect. It
  also stages the empty Camera FX Palette, one cubemap position and 19 airprobes.
  Cubemap positions alone do not establish converted reflection bitmap content.
- Retail exposure/bloom fields, per-object minimum luminance and all four
  performance profiles preserve source values. MCC-only camera extensions are
  omitted only when marked use-default and grading blocks are empty; active
  overrides reject. MCC anisotropy is omitted only at the observed default 1.
  These limitations are included in the dependency import report.
- Verified 70 camera fields/lighting rows/performance profiles against source
  values and finalized the environment graph in memory. Private metadata report:
  `.local/reports/environment-controls.json`. No output map or runtime changes;
  lighting appearance and reflection content still require final integration.

BSP material integration checkpoint:
- `stage_bsp_materials()` follows the scenario's active BSP binding, rather than
  choosing the first BSP tag (the accepted cache also contains unused stock BSP
  metadata). It preserves material-slot order and all physics/property bytes.
- 109 shader/foliage slots now use named base, normal, detail and alpha texture
  parameters through the existing retail shader approximation. This includes
  formerly skipped A8/Y8/ARGB slots; unrepresented parameters remain reported.
- The other 18 slots (10 terrain, six hologram, two water) explicitly retain the
  accepted checkpoint material and are listed as unfinished specialized work.
  A matching material count is required before any BSP references are patched.
- Focused checks passed for all 127 slots' preserved physics/property bytes and
  retained references. The integration command now runs this stage first so
  subsequent object/environment imports can reuse converted texture resources.
  Native appearance remains unverified; no accepted map or runtime was changed.

Native terrain shader dependency checkpoint:
- All four terrain templates used by Warlock exist on the original Mythic disc:
  sandbox `_0_1_1_0_0_0`, docks `_0_2_1_1_1_2`, chill `_0_2_1_1_2_0`, and
  sidewinder `_0_1_1_1_1_2`. These can supply original Xbox 360 shader programs.
- `native_shaders.py` imports retail shader-definition/template dependency graphs
  and relocates native shader info/data. It preserves bytecode and relative debug
  structures, initializes runtime info following Assembly's shader injection
  strategy, and rejects unsupported dependencies and invalid data bounds.
- Layout reference: `reference/formats/H3_Layouts_Shaders.xml`; algorithm reference:
  [Assembly ThirdGenShaderStreamer](https://github.com/XboxChaos/Assembly/blob/dev/src/Blamite/Blam/ThirdGen/Shaders/ThirdGenShaderStreamer.cs).
- A combined in-memory import of the four variants produced 25 tags. All 67 newly
  relocated shader payloads and their debug data matched the disc byte-for-byte.
  Private metadata report: `.local/reports/native-terrain-shaders.json`.
  Binding Warlock terrain textures/constants remains pending; these donor graphs
  are not yet used by the integration command or verified in-game.

Terrain material integration:
- The integration command now imports all ten placed terrain materials using
  the four matching original-disc templates. `--disc-maps` selects the read-only
  donor directory (default: `<project>/maps`). All texture/constant parameter names
  and ordering must match before binding. Terrain layer blending, layer normal
  maps, detail maps and authored constants are retained; the normal texture
  conversion still uses the documented single-mip/512-pixel POC policy.
- Material type indices are resolved by name against retail globals instead of
  copying MCC indices. No geometry or material-slot ordering changes.
- Three materials' observed 300-second normal-map scrolling overlays are frozen
  at their authored initial transform. This explicit POC approximation is reported;
  other animation functions, sampler comparisons, sub-images and routing reject.
- `terrain_materials.py` provides this binding stage. Specialized BSP work now
  remains for six hologram and two water slots. Native terrain appearance is not
  yet verified; metadata conversion is not a claim of final visual parity.

Hologram integration checkpoint:
- `DiscMaterialImporter` (in `terrain_materials.py`) now also binds all six BSP
  holograms. Sandbox provides the exact seven-category layered hologram variant;
  stock Lockout supplies the plasma light-cone variant. The two extra MCC
  categories must be default zero before being omitted.
- Source textures, colors and float constants replace the old stock-color
  substitutions. The native layered shader also requires an integer
  `layers_of_4` constant; this is derived from the source's exact integral float
  value (six for the five layered holograms), with bounds/integrality checks.
- Five holograms' periodic brightness is frozen at authored constant values for
  this POC and reported explicitly. Other overlay types reject. The light cone
  has no overlays and transfers its matching shader parameters directly.
- Only the two water BSP material slots remain on retained checkpoint materials.
  No claim of native visual verification accompanies this code checkpoint.

Native water bitmap dependency checkpoint:
- `native_bitmap_resource.py` copies original retail texture resources, including
  array/cube formats and all mips, without routing them through the 2D MCC encoder.
  Required and optional mip segments are copied at their declared byte lengths,
  combined into one resident page, and their resource fixups are relocated.
  This avoids copying unrelated trailing shared-page data. Unknown controls,
  interleaved layouts, resource salts and unexpected fixups reject.
- The native shader dependency importer now supports these bitmap resources with
  an explicit shared-cache mapping. A full wave-displacement bitmap tag/resource
  import finalized successfully in memory. Independent segment comparisons for
  displacement and slope arrays plus a cubemap preserved all bytes and control
  metadata. Private report: `.local/reports/native-water-bitmaps.json`.
- Water shader binding is still pending: neither source variant exists exactly
  on the disc, so foam/bank-alpha differences require an explicit mapping. This
  dependency checkpoint does not yet replace the two retained water materials.

Water geometry prerequisite:
- The earlier geometry comparison verified formats 1/2 and ordinary index
  buffers; it did not establish water-buffer correctness or reproducibility.
  MCC format 28 has 128-byte expanded records, while the accepted native cache
  uses 12-byte triangle-index records. Their counts also differ. This is not
  evidence that the accepted scene is broken, but it rules out a direct endian
  copy as the seed-independent conversion strategy.
- Format 27 water tessellation parameters are nine float words on both platforms.
  `render_buffers.py` now converts them while preserving every float bit pattern;
  all five source buffers passed that check. Format 28 still rejects explicitly
  until reconstruction from mesh topology is implemented.
- Private diagnostic: `.local/reports/water-geometry-gap.json`. Water shader
  binding remains deferred while this geometry prerequisite is addressed. The
  accepted geometry and latest integrated map were not overwritten by this check.

Water topology reconstruction (supersedes the format-27 direct-copy note above):
- Actual MCC buffer data is packed at six float words per corner despite the
  descriptor advertising a nine-word allocation. The general direct converter
  now rejects formats 27/28. `water_buffers.py` selects the source mesh's water
  parts and expands those six words into the native nine-word layout with padding.
- Triangle records are rebuilt from the ordinary mesh index buffer, interleaving
  mesh vertex indices with compact water-corner indices. Their correct native
  format is **26**, not MCC's expanded format 28. The reconstruction uses source
  topology and parameters only, not the historical converted seed.
- All ten rebuilt water buffers (five parameter buffers and five triangle buffers)
  match the accepted cache's descriptors and payloads byte-for-byte. This explains
  the earlier count differences and establishes the required conversion path.
- `convert_render_resource(source, water_buffers)` now accepts this complete
  reconstruction and rejects missing/partial water bindings. The full source BSP
  render resource converts successfully, producing 51,810,478 raw bytes in memory.
  Private report: `.local/reports/water-reconstruction.json`. No map was replaced.
- Remaining integration: water shaders, then complete source-to-retail BSP/collision
  metadata assembly and the final seed-independent command/deployment handoff.

Water shader integration checkpoint:
- `water_materials.py` binds both source water materials to the closest native
  Zanzibar/Docks variants. All 127 BSP slots now have an explicit conversion;
  the command no longer retains old material references for unsupported groups.
- Original-disc wave displacement/slope arrays retain all native mips. Source
  2D foam/color/shape textures and matching named constants transfer. Reflection
  cubemaps use the donor water material's original-disc reflection rather than
  the unsupported MCC cube texture; each substitution is reported by name.
- POC differences: all water animation overlays use static authored values;
  pure-water depth bank fade becomes uniform opacity. Its extra painted foam is
  disabled with a black shape texture; the stream's extra automatic foam uses a
  high threshold. Source transforms/queryable indices are remapped by parameter
  name. Unknown variants, animation types and sampler modes reject.
- Foam/bank semantics were checked against [HaloShaderGenerator water shading](https://github.com/Beatthezombie/HaloShaderGenerator/blob/master/halo_online_shaders/water_shading.fx).
  This remains a conversion checkpoint, not proof of native water appearance or
  motion fidelity. Seed-independent BSP/collision assembly is still unfinished.
# Source BSP geometry binding checkpoint

`lightmap_importer.py` now creates retail `sLdT` metadata from MCC's separate
lighting tag and binds a supplied geometry resource. It imports all 19 root
airprobes and 127 scenery probes, preserving object unique IDs; validates cached
per-BSP probe subsets (including the MCC all-BSP airprobe-mask sentinel); and
converts packed mesh MOPPs. `encode_lightmap_array` converts the two single-mip
BC3 arrays at their authored 1024x1024 size, with eight and two slices. Both
bitmap records, resource controls and all 10,485,760 tiled pixel bytes matched
the accepted arrays exactly. In-memory lightmap assembly/finalization passed
using the accepted geometry resource as its supplied binding. The arrays were
regenerated from MCC, not reused from the seed. Final scenario activation and
removal of bitmap-root/prototype seed assumptions remain outstanding.

Lightmap investigation: retail embeds each 0x1B4 BSP-lighting record in `sLdT`,
whereas MCC uses separate `Lbsp` tags. The main render resource is shared with
the BSP. The MCC per-BSP scenery probes are a subset of the root scenery probes;
its airprobe rows differ in the manual BSP mask and need explicit reconciliation.
`collision_physics.convert_packed_mopp` now converts the aligned 48-byte headers
and bytecode in per-mesh lightmap MOPP data. All 503 mesh records (733,168 bytes)
matched the accepted map byte-for-byte after conversion. It clears stale source
allocation padding and rejects truncated data or resident runtime pointers.
The model importer also uses this handler for populated per-mesh MOPP data.
Lightmap root assembly and array-texture conversion remain unfinished.

`bsp_importer.py` now assembles a new BSP with real dependency imports and
three registered resources: decorator instances (83,760 raw bytes), source
render geometry including water (51,810,478), and collision (8,737,928).
It reserves the BSP owner before importing its self-references and routes
terrain/hologram/water shaders through their dedicated converters. Failures
invalidate the importer, preventing publication of a partial graph.
The focused in-memory assembly/finalization succeeded with 112 added tag
records, 114,161,307 staged raw bytes (including dependent textures/audio) and
4,326,632 metadata bytes. Explicit FMOD bank/decoder inputs are required for
the BSP's referenced ambient sounds. No map file was written or deployed.
The checkpoint CLI does not yet activate this new BSP; scenario/lightmap
binding and stock-based prototype removal remain unfinished.

Root metadata checkpoint: `bsp_metadata.py` now normalizes the MCC root field
names and separate serialization flag, converts instance physics and root MOPP
blocks, and moves cache-file resource arrays into retail metadata. It rejects
populated resource pathfinding, duplicate metadata/resource arrays, out-of-range
surface indices and unconsumed fixups. Instance bit 5 is retained at the same
position as the accepted map (the original XML lacks its label).
Full metadata traversal produces the 904-byte retail root. Focused comparison
matched all 39,757 edge/seam pairs, 22,368 surface mappings, 37,930 triangle
mappings, 1,178 instance flags and 494 instance physics shapes to the accepted
map. This traversal used placeholder tag/resource callbacks and is NOT a
deployable map: real dependency binding/resource registration remains next.

Decorator dependencies: `TagImporter` now supports the inherited Assembly H3
`dctr` schema, format-24 decorator meshes (20-byte MCC to 16-byte retail), and
BC2/DXT3 textures. The native BC2 resource value `0x1a200153` was checked in
stock lockout's `fx\particles\material\_bitmaps\fragments_chitin` bitmap.
The existing 512-pixel/base-mip bitmap limit still applies. All 28 source
decorator sets imported and the registry finalized in memory (52 dependency
metadata records, 1,532,773 staged raw bytes). No map was written or deployed.
This completes the dependency importer checkpoint; BSP assembly still must
register the instance resource and bind the imported decorator sets.

Decorator follow-up: all 400 source groups now validate their MCC model-start
boundaries against model selectors already encoded in the high byte of each
TinyPosition variant. The redundant boundary lists can then be omitted from
the 48-byte retail groups. All 54 cluster physics records convert and match
the accepted map; this supersedes the 33-cluster rejection noted below.
Format-20 conversion preserves ushort positions/model-scale values and converts
biased orientation bytes and packed color. Focused checks covered all 5,235
instances in 28 buffers (1,168 control bytes, 83,760 raw bytes). Empty index
buffer tables are now handled without requiring a nonexistent fixup.
Decorator-set tag dependencies and final resource registration remain to be
integrated; this is not a native visual test or a complete decorator import.
Stream layouts were checked against TagTool's `VertexStreamHalo3RetailMCC.cs`
and `VertexStreamXbox.cs` in its Geometry/RenderGeometry/VertexBuffer directory.

`bsp_metadata.py` adds an explicit 0x118-to-0xDC cluster layout adapter,
including runtime-pointer checks, owner relocation and collision MOPP conversion.
It is invoked by `MetadataConverter` for BSP metadata. Focused conversion passed
for 21 Warlock clusters and their physics fields matched the accepted map.
The other 33 clusters reject populated MCC decorator model-start lists: these
need a dedicated conversion. Source has 400 decorator groups; the accepted map
has zero. Full BSP conversion is therefore still incomplete, and this checkpoint
does not silently discard the source decorators.

`snapshot/tools/bsp_collision_resource.py` now converts the MCC structure BSP
collision resource directly. It relocates control/raw blocks, converts collision
arrays and instance headers, narrows surface-map indices with overflow checks,
and translates MOPP headers/code. Unsupported populated large-BSP, extra Havok,
render-BSP, breakable and small-surface blocks fail explicitly; every source
fixup must be consumed. This is an in-memory converter, not yet wired into the
final stock-based build.

Focused comparison against the user-accepted map matched all main-BSP and 449
instance collision arrays/scalars, plus all 133 MOPP headers/code blocks.
Output: 91,264 control bytes, 8,737,928 raw bytes, 1,599 fixups. No native run or
new map file was needed. Layout references include the bundled H3 `sbsp.xml`
schemas and [TagTool collision definitions](https://github.com/TheGuardians/TagTool/tree/master/TagTool/Geometry/BspCollisionGeometry).
The serialized triangle/section pairs are 4 bytes in both H3 cache formats;
TagTool's expanded in-memory mapping class must not be treated as their stride.

`snapshot/tools/bsp_source.py` resolves the active scenario BSP through its
`sLdT` lightmap and matching `Lbsp` BSP index. It validates tag salts and resource
ownership/type before converting render buffers, including reconstructed water.
No resource or tag index is hardcoded. The Warlock source resolves resource
`0xed430be0` and produces 87,208 control bytes and 51,810,478 raw bytes,
with all ten water buffers reconstructed. An out-of-range BSP index is rejected.
This helper currently returns in-memory data; stock-based BSP metadata,
collision resource assembly and final integration remain unfinished. No generated
map was deployed or native-tested for this checkpoint.

