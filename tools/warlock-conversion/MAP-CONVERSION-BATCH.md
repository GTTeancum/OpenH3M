# Map conversion batch

User requested 2026-10-25. Active goal covers all 20 maps; Battle Canyon, Rodentia, Sanctuary, Lockout and 3longation are installed with bounded native gameplay and menu/preview proof; 15 maps remain.

Prefer an existing Halo 3 MCC custom port. Keep prior installed maps and saved layouts. Reuse stock Xbox 360 H3 gameplay assets, maintain original format limits, generate previews, and validate actual gameplay with native captures/process-local harnesses. No OS input. No claims of console validation.

Battle Canyon: user approved simplifying collision while retaining visible geometry. Preserve structural surfaces where feasible and measure deviations. Full collision audit: `work/battle-canyon/collision-audit.json`.

Installed-source preflight: `audit_conversion_batch.py` writes
`work/map-conversion-batch/preflight.json`. Rodentia, Boarding Action, both
Lockout candidates, Elongation, Sanctuary and Powerhouse have standard collision
resources. This only clears the index-format preflight, not full conversion.
Diamondback and Reactor have large trees exceeding signed plane limits; their
surface counts are already below 32,767. Sky Bridge has 42,706 2D tree nodes,
so its tree also needs rebuilding despite its smaller plane/edge counts.

`research_batch_workshop.py` caches public MCC Workshop searches for the ten
unlocated names. First-page results did not identify verified H3 ports; this
does not establish their absence. Leads and exact search URLs are recorded in
`work/map-conversion-batch/workshop-search.json`. Installed original Reach and
H4 multiplayer caches are present, including cex_hangemhigh, cex_damnation,
cex_headlong, 52_ivory_tower, 20_sword_slayer, wraparound, dlc_forge_island,
ca_forge_erosion and ca_forge_bonanza. These are fallback source candidates,
not evidence of an H3-compatible conversion or verified display-name mapping.

| Map | Current state | Installed H3 source candidates |
|---|---|---|
| Battle Canyon | installed; native gameplay and preview verified | 3575686579 |
| Rodentia | installed; native gameplay and preview verified | 3500400217 |
| Boarding Action | Deferred by user; candidate08 visual/performance issues unresolved | 2962955878 |
| Desolation | source research pending | Not located yet |
| High Noon | source research pending | Not located yet |
| Lockout | installed; native gameplay, Forge exterior and preview verified | 2898979693, 3003239190 |
| Elongation | installed; native menu/preview and conveyor/crate behavior verified | 3618057049 |
| Penance | source research pending | Not located yet |
| Breakneck | source research pending | Not located yet |
| Sanctuary | installed; native gameplay, Forge overview and preview verified | 2898920291 |
| Reflection | source research pending | Not located yet |
| Haven | source research pending | Not located yet |
| Sword Base | source research pending | Not located yet |
| Powerhouse | native gameplay reached; opaque sky shapes require correction | 3003239190 |
| Diamondback | H3 source candidates located | 3003239190 |
| Reactor | H3 source candidates located | 3003239190 |
| Sky Bridge | H3 source candidates located | 3003239190 |
| Forge Island | source research pending | Not located yet |
| Erosion | source research pending | Not located yet |
| Impact | source research pending | Not located yet |

Lockout uses the classic snowy H3 port (2898979693), not the alternate lava-themed Halo Online remake. Forge Island means the original H4 map, not Force Cove.

Machine-readable inventory and queue: `work/map-conversion-batch/`. Record exact cache hashes, native proof, package identities, cleanup and unresolved limitations as each map progresses.

Next scripted-map audit: Diamondback has 2,008 active expressions, Reactor
3,209, Sky Bridge 2,475. All salted graph links and opcode names validate.
Sky Bridge has native function/signature matches throughout. Diamondback and
Reactor each use MCC-only `mp_wake_script(string)`: startup scripts request
`bigtastybirds` and `startpelicans`, respectively. Original H3 has `wake` but
with different argument semantics; do not blindly alias these opcodes or drop
the ambient scripts. Reports: `*-script-audit.json` and
`mp-wake-call-sites.json` in `work/map-conversion-batch`. Sky Bridge still needs
runtime-table/parameter conversion audit and its oversized 2D collision tree
rebuilt while preserving surfaces before a full candidate build.

Packaging now supports chained standard STFS directory blocks. The builder, payload verifier and menu harness follow the full directory. Boundary tests with 64, 65 and 171 files passed both byte comparisons and the existing native STFS reader, without rebuilding the engine. Reports: `work/map-conversion-batch/stfs-directory-check/results.json`. The 10-map Lockout bundle subsequently passed native install, menu and gameplay checks.

Further script research: the documented `mp_wake_script` behavior sends a
message from the host to clients to wake a dormant script. A direct substitution
with local `wake` is therefore not behavior-equivalent. Preserve this blocker
until the original runtime's distributed startup behavior is established; no
opcode alias has been added. Reference: https://c20.reclaimers.net/h3/engine/scripting/
(function documentation).

Diamondback collision progress: `work/diamondback/collision-rebuild.json` proves
all 30,379 authored polygons, edges, and vertices unchanged, with exactly the
same reachable surface set. Rebuilt plane count is 27,901 (original 62,263),
2D nodes 2,625, leaves 35,066. This clears the rebuilt collision index counts,
not visibility or complete-map integration. Original visibility overlay is
currently being computed; process session 9181 was verified live. Log is
`work/diamondback/visibility-integration.log`; success produces
`collision-visible.json`, failure records `visibility-integration-error.json`.
Do not restart while that process remains live.

`opposite-plane-audit.json` also rules out exact signed-plane deduplication as
a sufficient repair: Diamondback retains 60,153 canonical planes and Reactor
57,998, above the 32,768 limit. Rebuilding rather than blindly narrowing is
required.

Diamondback visibility overlay completed: 87,821 3D nodes, 28,156 planes,
55,395 leaves, all 41 original cluster IDs retained.
`work/diamondback/collision-visible-validation.json` independently checks packed
node/leaf indices, 3D and 2D acyclicity, leaf reference ranges, and cluster IDs.
The 76,297 references do not overflow the native leaf start index: that field
is 32-bit (`BBHI`), distinct from the 16-bit per-leaf count. Geometry/report
hashes are recorded. Full cache physics/portal/script integration remains.

Reactor's exact collision rebuild also passed with all 27,734 authored surfaces
and identical reachable surface membership: 25,125 planes, 32,204 leaves,
2,785 2D nodes. Report: `work/reactor/collision-rebuild.json`. Original visibility
overlay is running in session 99831; log `work/reactor/visibility-integration.log`.
Poll the existing process before any restart.

Powerhouse's `sky-basis-10.json` independently decodes all nine primary native
vertex buffers. Normal/tangent/binormal component errors are within the native
packed-format precision. This narrows the cloud-edge investigation but is not
a visual fix.

Prepared collision integration is now implemented in `prepared_collision.py`
and selected by exact scenario identity in `build_scenario_checkpoint.py`. It
validates source/rebuild hashes, unchanged collision arrays after visibility
overlay, native index widths, full reachable 3D graph, 2D acyclicity, leaf ranges
and portal-plane mappings before packing native tables. It retains original
surface IDs and MOPP handling. No expensive visibility rebuild occurs at build
time. Both Diamondback (28 portal planes) and Reactor (153 portal planes) passed;
reports are `work/<map>/prepared-validation.json`.

Reactor overlay completed with 74,783 nodes, 25,551 planes and 47,597 leaves;
all 27,734 authored polygons remain. Session 99831 is terminal; no collision
process remains pending.

Repeatable wrappers: `build-diamondback.ps1` and `build-reactor.ps1`. Diamondback's
first integrated attempt passed prepared collision and stopped in runtime setup
at the explicit unaudited-script guard (`work/diamondback/build-01.json` and
`build-run.log`). This does not prove cache-level collision behavior yet.
The next required work is script runtime-table audit and multiplayer wake
semantics, not bypassing the guard.

`native-script-name-audit.json` finds neither MCC-only names nor ordinary wake/
sleep_until names in the original executable image. Since ordinary names are
also absent, this string search cannot establish whether an opcode exists;
inspect the native dispatch implementation before drawing that conclusion.

Retail script dispatch audit (2026-10-25): located the function-pointer table
at VA `0x8275e770` in the original executable, SHA-256
`18816c1da58b1371e440741fadab1df8e6e6ecca7c5b81952f2d23ceec797313`.
All 1,473 XML function definitions match the executable's return type and
formal parameter types. Shipping descriptors use return type/flags at +0/+2,
evaluation and parsing pointers at +4/+8, argument count at +12 and argument
types at +14. Read-only reproducible audit and full result:
`work/map-conversion-batch/script-research/audit-native-dispatch.py` and
`native-dispatch-audit.json`. This validates signatures, not undocumented names
or behavioral equivalence.

Native `wake` evaluator `0x8225dc38` reads a script-index literal, finds its
local thread through `0x8225f0b0`, then calls `0x8225ed80` to update thread
sleep state. This is not evidence of the MCC multiplayer broadcast behavior.
No opcode alias or script-audit bypass has been introduced. Diamondback and
Reactor still require a faithful startup conversion before cache/runtime tests.

Further native/source evidence (2026-10-25):

- `dump-source-scripts.py` writes the two source expression trees under
  `work/map-conversion-batch/script-research/`. Diamondback's startup waits
  30 ticks, then requests `bigtastybirds`; that dormant script starts four
  migrating flocks with 90/900/120-tick gaps. Reactor starts rod setup, requests
  `startpelicans`, positions rods and hides Pelicans. Its requested script loops
  through randomly selected authored Pelican animations. Converting the call
  into a synchronous static call would prevent Reactor's remaining startup
  initialization from running; it is not a valid substitution.
- The actual retail thread initializer is `sub_8225E4D8` in generated
  `halo3mp_recomp.41.cpp`. When `sub_820B7640` returns true, it creates only
  type-1 (dormant) threads; otherwise it creates types 0, 1 and 2. The predicate
  compares byte +20 of TLS slot 128 with 4. This differs from the downloaded
  Halo Online implementation, which selects startup threads on predicted
  clients. Do not infer retail startup behavior from that implementation.
- `audit-stock-script-calls.py` inspected the 24 installed disc-map scenarios;
  it recorded their function calls and found no `wake` call sites or function
  name mismatches. Report: `stock-script-calls.json`. These maps therefore do
  not supply a working multiplayer-wake conversion example.

The ambient scripts remain intact in source, and neither unsupported opcode
has been bypassed. No new cache was deployed during this investigation.

### Extended public-source search (2026-10-25)

The public MCC Workshop search was extended through pages 2 and 3 for all ten
unlocated names. Cached pages and exact URLs are in
`work/map-conversion-batch/research/` and `workshop-search-pages-2-3.json`;
`research-more-pages.py` reproduces the search without redownloading cached
pages. All returned titles were inspected. None identifies an additional exact
requested H3 port. Broad queries return unrelated campaigns and Forge mods;
this is not proof that a port does not exist. The Halo Online map-pack result
is an existing source, not a newly discovered conversion. Original Reach/H4
caches remain fallback candidates, requiring their own format support.

### Original Reach fallback preflight

Five exact original MCC Reach sources are now recorded with SHA256, scenario
names and BSP identities in queue.json (`fallback_source`). High Noon, Penance
and Breakneck each have one BSP; Reflection and Sword Base each have three.
These remain fallback sources; no H3 conversion or native verification is claimed.

The shared Reach collision bridge gained an opt-in `structureBsps` read-only
preflight request. It compiles cleanly, but the installed TagTool BSP
 deserializer fails on all five sources with EndOfStreamException. Existing
collision/render-model requests are unchanged. Do not use that failed BSP
output as conversion evidence or silently ignore the exception.

An independent bounded walk uses Assembly's ReachMCC sbsp.xml pinned at
fd14ef3c46135e9422966c6a64cd926fb0bd23fb. The schema, provenance, exact sources,
logs and script are under `work/map-conversion-batch/reach-preflight`.
Thousands of nested block ranges resolve, but collision MOPP data does not;
Penance additionally fails the unknown block at 0x64. These are reader/schema
failures, not evidence of damaged source maps. Main mesh blocks at 0x284 are
empty in these caches, so resource/alternate geometry storage also needs
explicit handling. Complete original Reach BSP conversion is not yet supported.
No game assets were copied, installed, or uploaded during this preflight.

Reach reader correction: `ReachCache.block` incorrectly applied a 65,536-item
limit to byte arrays as well as structured blocks. High Noon's MOPP program
alone contains 1,580,864 bytes. The reader now validates positive stride and
bounds the count by the remaining mapped-file byte span; it still returns a
lazy range. No output format or engine limits changed. The schema audit now
passes every nested block range in all nine BSPs across the five sources,
including Penance's previously rejected byte block. This proves readable ranges,
not complete semantic conversion or console suitability.

The unsuccessful optional TagTool BSP deserializer addition was removed from
the shared bridge rather than leave a broken production path. Its failure logs
remain as research evidence. The working independent schema audit is retained.

Original H4 MCC fallback inventory is now recorded in
`work/map-conversion-batch/h4-source-inventory.json` and the queue: wraparound,
dlc_forge_island, ca_forge_erosion and ca_forge_bonanza. Each entry records its
read-only installed source path, exact byte count, SHA256 and header scenario
strings. These caches report the April 1 2023 build. No assets were extracted
or copied. This establishes available fallback inputs, not H4-to-H3 conversion
support, and does not supersede the preference for an existing H3 MCC port.

Reach render-geometry correction: main BSP meshes are at 0x450, compression
at 0x45c and the resource datum at 0x4e0. The matching Lbsp lighting tag has
meshes at 0x7c and its resource at 0x10c. Several main BSP resource records
are unused while the lighting geometry owns valid streams. Main and lighting
mesh counts match, but part counts/topology can differ; they must not be
silently interchanged. `audit-render-geometry.py` records those differences
and validates the selected lighting geometry against its own resource.

The selected geometry in eight of nine BSPs passes buffer-reference,
material-index, part-index-range and resource-span checks, with resource salt,
page sizes and CRC checks retained. Sword Base's hidden BSP fails because its
1321-vertex stream refers to an empty primary segment. This remains unresolved.
Formats beyond the existing rigid scenery converter include world vertices,
lighting streams and water streams. These checks establish readable geometry,
not semantic conversion, gameplay, visual acceptance or console memory fit.

A separate Reach MCC world-vertex converter is now implemented in
`reach_world_vertices.py`, pending complete BSP resource integration. It expands
half-float UVs, preserves float XYZ positions and derives the missing binormal
using tangent handedness before packing original H3's 32-byte world format.
The semantic reference is TagTool's Reach ReadWorldVertex; the MCC expansion
is inferred from the source buffer layout and checked against all available
format-1/36-byte buffers. `world-vertices-audit.json` records 159 buffers and
252,289 vertices across the eight readable BSPs: position/UV values are
preserved, and packed normal/tangent errors stay within half a quantization
step. Independent axis/handedness and malformed-input tests pass. Sword Base's
hidden BSP is still rejected, not skipped in production. No map build is
claimed from this isolated converter; lighting, water, BSP metadata and native
visual verification remain outstanding.

Reach resource integration: `reach_resource.convert_render_resource` now accepts
world format 1/stride 36 through the checked world converter. The shared H3
resource assembler accepts an explicit vertex-converter callback; existing
callers retain the same default. Unsupported Reach lighting/water formats still
fail before assembly. Reflection `_001` converted in memory into 896 control
bytes and 357,476 GPU bytes (14 vertex buffers, 8 index buffers). Independent
inspection of its serialized descriptors and payload verifies world XYZ/UV and
all index values/primitives. Exact hashes and the repeatable check are in
`reflection-resource-conversion.json` and `convert-reflection-resource.py`.
The world-vertex, ambient-PRT and packed-lighting unit checks pass. This does
not establish complete BSP metadata translation or native map acceptance.
The retained Reclaimer `MccHaloReachVertexBuffer.xml` independently confirms the
world layout used above: float4 at 0x00, half2 UV at 0x10, normalized short4
normal/tangent at 0x14/0x1c. Its world type number is a mesh vertex type, not
the resource descriptor's format enum. No format numbers were equated by name.

Reach static lighting now has a verified source decoder (`reach_lighting.py`).
TagTool's pinned VmfConversion.cs establishes that descriptor format 6/stride 4
contains packed six-byte VMF probes, with allocation-tail 0xCD padding. The
Lbsp block at 0x48 supplies each buffer index and its half-float HDR scale;
cluster records at 0x54 carry lighting indices and vertex offsets. Treating
these payloads as ordinary four-byte colors would lose directional lighting.

The independent audit verifies the 92-direction table indices, HDR scales,
allocation spans, padding and finite decoded probe values across the five
sources. Penance has 11 nonzero cluster offsets, which must be handled when
writing H3 buffers. Two additional Lbsp tags named `1`/`2` lack valid resources;
the audit reports them as failures, without assuming they are active or safe
to discard. Their scenario references still need investigation. Packed-color
unit checks enumerate all 65,536 combinations of the two indirect-color bytes;
direction/mask, padding and invalid-input checks also pass.

This is source decoding only. VMF-to-SH reduction, native RGBE packing, cluster
padding/flags and lightmap textures remain required before format 6 can be
enabled in the production resource converter. Existing format rejection stays
in place. Reference files and the repeatable audit are under reach-preflight.

VMF-to-SH coefficient translation is implemented in `lighting_coefficients`.
It retains intensity and four signed linear SH RGB terms. A separate PowerShell
oracle calls the existing TagTool.dll implementation (no copied equations in
the oracle) for 15 direction/color cases, including zero direct light and HDR
colors. The Python implementation matches within 2e-6 relative/absolute
tolerance; maximum absolute difference is 4.08028e-5 at HDR magnitudes. This is
numerical agreement, not bit-identical float32 output. The full source lighting
audit now also computes finite 5x3 coefficient sets for all 2,182,394 readable
probes. The two invalid-resource Lbsp tags remain explicitly reported.

Final native signed RGBE packing and resource/cluster integration remain
unfinished. The reference Xbox stream writer is unimplemented, so reference
coefficient agreement alone cannot verify the target buffer byte order.
Scripts/reports: lighting-oracle.ps1, lighting-coefficient-oracle.json,
compare-lighting-coefficients.py and lighting-coefficient-comparison.json.

Native Reach lighting packing and resource integration are now implemented.
`pack_lighting_coefficients` produces five signed RGBE vectors per H3 vertex
(20 bytes, original Xbox ABGR order). An independent reflection-based call into
TagTool's internal ColorConversion methods matches all bytes for 86 test
vectors, including signed values, zero and power-of-two exponent boundaries.
Overflow is rejected. This verifies packing separately from SH float rounding.

`resource_lighting_bindings` resolves HDR scales and cluster prefixes explicitly;
missing/extra bindings or conflicting shared-buffer prefixes fail conversion.
The Reach resource converter preserves complete buffer sets and now handles
world, rigid, static UV, static lighting and ambient PRT formats. Water streams
still require a separate implementation. Prefix vertices use the reference's
0xCD fill; BSP part flags must also be translated before a map can use them.

High Noon's full lighting-owned resource now converts in memory: 1,948 vertex
buffers, 815 index buffers, including 384 lighting buffers / 226,270 probes.
Output is 23,403,298 GPU bytes and 107,308 control bytes. Serialized lighting
counts, strides and spans pass; report/hash in high-noon-resource-conversion.json.
No resource payload copies were retained. Reflection's earlier small resource
still produces the same hashes. This does not prove a complete High Noon map:
BSP metadata, materials, lightmap textures and native verification remain.

Scenario-based resource resolution is now implemented in reach_bsp_source.py.
It follows scnr BSP slots and sLdT lightmap references with datum salt/group
checks, then verifies the resource owner. It does not select lighting by name.
The tags named `2` (Reflection) and `1` (Sword Base) are confirmed empty
lightmap placeholders in those scenario slots: zero lighting meshes and null
resource, with default internal index zero. Active lighting tags must match
the slot index. Placeholder slots retain their BSP and use its own resource;
they are not discarded. Sword Base hidden geometry still fails bounds checks.

Running the shared resolver/converter over all nine BSPs now converts four
complete resources: High Noon, Reflection 000, Reflection 001, and Sword Base
shared. Penance, Breakneck, Reflection 030 and Sword Base main stop at water
format 26/12. Sword Base hidden stops on its absent payload. Reports are in
scenario-geometry-bindings.json and scenario-resource-conversion.json. All
payload conversion occurs in memory; only small reports are retained. This
expands validated resource coverage, not the count of installed maps.

Reach water research: the original format-26 triangle tables survive alongside
MCC's expanded format-28 geometry and format-27 parameters. Across all 14 water
meshes in Penance (10), Breakneck (1), Reflection (2) and Sword Base (1), each
format-26 mesh-index sequence exactly matches the water parts' original index
buffer ranges. Water-index references remain distinct from mesh indices; do
not replace them with sequential corner indices without reconstructing the
parameter table. The audit records both ranges and all buffer identities in
water-triangle-audit.json. The observed adjacent slot relation was used only
for this audit, not adopted as a general resource-lookup rule.

Reach MCC format 27 advertises 24-byte elements here, unlike the H3 MCC
36-byte allocation handled by the existing water converter. Its leading data
contains UV pairs, while format 28 contains expanded floating-point geometry.
TagTool's console Reach ReadWaterTesselatedParameters explicitly substitutes
LocalInfo=(15,0.9) and marks the conversion TODO; that placeholder is not an
authoritative conversion of authored water settings. No guessed local values
or silent H3 water-layout reuse have been enabled. Native format-26 ushort
pair semantics agree between the Reach and H3 reference readers.

Reach mesh metadata audit now covers every selected BSP mesh and records flags,
vertex types, specialized rendering, tessellation and original-H3 index-field
limits in mesh-metadata-audit.json. High Noon has 827 meshes / 2,194 parts;
its part starts/counts fit ushort, and its vertex types are world/rigid only.
It has 46 specialized lightmap-only parts and Reach-specific merged/uncompressed
mesh flags that require semantic translation. A lexical flag conversion from
TagTool is insufficient evidence for silently dropping unmatched behavior.

Penance mesh 165 part 0 has 76,992 indices, exceeding H3's ushort count field.
Reflection BSP 1 mesh 198 has part starts above 65,535 (up to 83,433). These
require mesh/index-range splitting while retaining materials/subparts/lighting
and visibility bindings; do not narrow casts or raise original engine limits.
The geometry-resource conversions alone do not solve these metadata limits.
Subpart analytical-light fields are also recorded for separate interpretation;
non-0xffffffff values are not by themselves proof of active lights.

A reusable triangle-list splitter (`reach_mesh_split.py`) now partitions index
ranges at triangle boundaries within 65,535 entries. It preserves vertex
numbers, triangle ordering, material metadata and part/subpart ownership, with
source-part/subpart identities and source index offsets retained for subsequent
remapping. It rejects invalid topology/ranges instead of narrowing integers.

The actual oversized source meshes pass independent sequence reconstruction:
Penance BSP 0 mesh 165 splits 76,992 indices into 65,535 + 11,457; Reflection
BSP 1 mesh 198 splits 83,469 into 65,535 + 17,934. Every source part/subpart
reconstructs exactly, and all resulting start/count fields fit ushort. Boundary
and malformed-input unit tests also pass. See mesh-split-audit.json.

This utility is not yet installed into output maps. Callers must update all
mesh references, resource bindings, budget vertex counts, visibility trees,
water data and lighting offsets consistently. Existing maps were not changed;
the splitter alone is not evidence that these maps now meet every H3 limit.


2026-10-25 user steering: defer Boarding Action rather than spend further credits
on its current quality/performance issues. Preserve candidate/evidence for later
knowledge. Desolation is next in requested order; prefer an H3 MCC port.

Desolation source research (2026-10-25): identified MythicJaqui H3MO Nexus mod
1897, file5464, version1.0 (2022-05-18), replacing s3d_waterfall. Normal HTTP
request to its files page returns403; requested user download into repository
work/map-conversion-batch/sources. Local Halo2 Uncut derelict_dw3 and H3 CE
Derelict are not that source. Installed Waterfall scenario remains stock-named.
Continue with High Noon while acquisition is pending.

2026-10-25 user decision: skip Desolation for now. Source acquisition is no
longer a pending user request. High Noon is next; Boarding Action also remains
deferred. Neither deferred map counts as completed.

High Noon part serialization (2026-10-25): reach_mesh_parts.py preserves all
2,194 material/sorting/index/subpart/type/vertex fields in original H3 16-byte
records; 46 specialized7 parts already have type5 (LightmapOnly), preserved.
Overflow and unsupported specialized rendering fail explicitly. Native flags
are a required caller argument, not a lexical cast; production flag translation
and mesh integration remain outstanding. high-noon-part-serialization.json is
a field-layout test with zero fixture flags, NOT a playable map validation.
All 2,194 source analytical-light fields are 0xFFBEEF00; earlier non-FFFFFFFF
counts must not be interpreted as proof of active analytical lights.

High Noon lighting metadata (2026-10-25): convert_lighting_tables in
reach_lighting.py serializes 402 native static-lighting rows and 18 cluster
rows, preserving all indices. It validates referenced converted buffers are
native20-byte SH streams and that removed Reach prefix fields have already
been materialized in the stream. Empty buffer rows are retained. Reproduction:
work/map-conversion-batch/reach-preflight/convert-high-noon-resource.py.
Instance light probes, render flags, and full BSP/map integration are still
outstanding; this is not native gameplay proof.

2026-10-25 source override: use straight original-game ports for Boarding Action
(Halo CE), Desolation (Halo 2), Haven (Halo 4), and Sword Base (Halo Reach).
The previous H3 custom-source preference is superseded for these four maps.
Verify the precise source edition before importing; do not silently substitute
a remake. Boarding Action and Desolation remain deferred, and High Noon remains
the active map. Other asset/compatibility constraints remain in force.

Reach BSP integration (2026-10-25): convert_bsp_geometry now returns native
lighting tables alongside each non-placeholder geometry resource. Re-running
the existing five-source/nine-BSP conversion retained four passing resources
and existing water/missing-resource failures. High Noon still needs its two
DualVMF lightmap textures converted (brightness16.1764755), plus 1,138 instance
lighting bindings, 52 instance probes, 30 airprobes and 206 scenery probes.
Exact scope: reach-preflight/high-noon-lighting-scope.json. No full map or native
visual acceptance is implied by the resource/table integration.

High Noon probe conversion (2026-10-25): convert-reach-probes.ps1 uses the
existing TagTool VmfConversion.ConvertHalfLightprobe implementation and writes
original-H3 72-byte big-endian half-float probe coefficients. The source
kind/index, prefix bytes and analytical-light field remain in the interchange
record. All 288 probes (52 instance, 30 air, 206 scenery) have finite coefficients,
correct 72-byte size/padding and unchanged identity fields. Source analytical
indices are 0 for173 and FF BEEF00 for115; interpretation remains outstanding.
Reports: high-noon-probe-native.json and high-noon-probe-verification.json in
reach-preflight. Reference DLL SHA256 is recorded in both. These probes are
not yet installed in a playable map; DualVMF lightmap textures remain pending.

High Noon DualVMF resource reader (2026-10-25): reach_lightmap_source.py
validates and reads the actual MCC lightmap pair:1792x1792, single mip, format44
DXGI83 direction (3,211,264 bytes) and format16 DXGI77 three-layer intensity
(9,633,792 bytes). It checks resource/image dimensions, layer count, fixups and
segment bounds and reads only owned image bytes, not complete shared pages.
Hashes: reach-preflight/high-noon-lightmap-source.json. Retained reference
ReachLightmapConverter.cs at TagTool ce2dc6ac handles original-console inputs
only; the new MCC reader supplies the missing source-data step. VMF decoding,
SH texture compression and native map integration remain pending. No source
textures were falsely relabelled as native H3 coefficient arrays.

High Noon direction texture decoding (2026-10-25):
`reach_lightmap_pixels.py` now decodes unsigned BC5 MonoAlpha, preserving the
log-intensity channel and analytical mask without normal-vector reconstruction.
Decoded the full 1792x1792 source image in memory; retained only its hash/ranges.
128 distributed source blocks plus six endpoint/selector fixtures matched the
installed TagTool decoder byte-for-byte, including two non-block-aligned image
sizes. Reproduce from repository root with Python `-B` on
`work/map-conversion-batch/reach-preflight/check-lightmap-pixels.py`, then run
the adjacent `check-lightmap-pixels.ps1`. Reports: `high-noon-lightmap-pixels.json`
and `lightmap-decoder-verification.json`. This verifies channel decoding only;
three intensity layers, VMF-to-SH texture conversion/compression, and native map
integration still remain. High Noon is not yet a playable converted map.

High Noon full lightmap adapter (2026-10-25): `ReachMccLightmapBridge.cs`
feeds linear MCC textures to the installed TagTool VMF decoder, SH conversion,
and dual-BC3 compressor. It preserves the reference intensity decoder's
truncating interpolation (different from MonoAlpha's rounding). The adapter
compiles under the installed PowerShell runtime; its full 1792x1792 build
completed in 523 seconds. All converted coefficients passed finite-value checks.
`convert-high-noon-lightmap.py` now includes native texture packing through
`encode_lightmap_pixels`, full-layer untile comparison, and intermediate cleanup.
The first invocation predated that packing addition; its completed BC3 files
were packed separately without repeating compression. All ten layers round-trip
byte-for-byte through native tiling. Native resources total 32,112,640 bytes
(25,690,112 coefficient + 6,422,528 intensity), retaining authored resolution.
Reports and native bitmap records/control/payloads are in
`work/map-conversion-batch/reach-preflight/high-noon-lightmap/`. Source extracts
and duplicate linear outputs were removed after validation. This is lightmap
resource completion only: native tag/scenario integration, runtime compatibility,
and visual verification are still outstanding. High Noon remains incomplete.

High Noon lighting bindings (2026-10-25): `reach_lightmap_output.py` now
validates the native bitmap pair before registration through the existing
`MaterialImporter.bitmap_resource` allocator and creates the nine native
24-byte luminance-scale records (216 bytes, source scales in the first five
records). `high-noon-lightmap/binding-verification.json` records validation of
both actual resources, their checksums/GPU layouts and the scale bytes. This
registration helper is ready for the Reach importer; it has not installed a
full lighting tag. Reach instance analytical-light metadata still requires
translation: High Noon has 1,138 instance rows, with analytical fields 0 on
462 rows and 0xffbeef00 on 676 rows. Their meaning must not be silently discarded.

High Noon instance binding conversion (2026-10-25): the shared Reach geometry
conversion now emits all 1,138 native 8-byte instance-lighting records, checking
their references against 402 static rows and 52 instance probes. Exact source
image/static/probe indices round-trip; the 1,138 Reach analytical fields are
retained separately in `instance_analytical`, pending behavior translation.
The full resource check passed with unchanged GPU payload SHA256
870ab6796c262ab6c19c6ddcf94ecd82cf900bdc072285324bb113d472bc5cbd.
Reproduce with `reach-preflight/convert-high-noon-resource.py`. This still does
not establish a playable cache or resolve analytical-light behavior.

High Noon mesh serialization (2026-10-25): `reach_mesh_metadata.py` serializes
827 native 76-byte mesh records, 2,194 parts/subparts and 938 instance buckets.
It validates part/subpart containment, native ushort ranges and converted
resource buffer references. `convert-high-noon-meshes.py` verified source buffer
indices and every subpart range against staged output; report:
`reach-preflight/high-noon-mesh-metadata.json`. Flag mapping follows the retained
TagTool `RenderGeometryConverter.ConvertHaloReach` lexical mapping. Unmapped
Reach flags, analytical fields and lighting policies are reported explicitly;
their visual equivalence is not proven. This is a metadata candidate, not an
installed/playable map. Material conversion, full geometry/tag assembly and
native visual verification remain.

High Noon material planning (2026-10-25): inventoried all 246 BSP material
slots, resolving 103 unique shaders (74 standard, 25 terrain, 4 hologram).
After verifying the shared render-method offsets against pinned Assembly
ReachMCC rmtr/rmhg schemas, extended the parameter reader/planner to those
classes. Against Construct standard/hologram and Sandbox terrain category
names, 84 shaders have exact semantic option plans. Remaining requirements:
13 animations (existing routing adapter needs application), five glass shaders
using Reach alpha-Fresnel selection, one palettized-plasma shader, and one
multiplied diffuse/specular mask (existing bake adapter). Counts can overlap.
Three glass shaders have zero opacity-Fresnel coefficient; two have nonzero
coefficient and bias, so a blanket alpha-mode alias would lose behavior.
`reach-preflight/plan-high-noon-materials.py` produces the full parameter and
dependency inventory in `high-noon-material-plan.json`. Option-name matching
does not prove compiled template availability, staging, or rendered equivalence.

High Noon native shader donor search (2026-10-25): searched all installed
native multiplayer caches, excluding shared/mainmenu/campaign. Found 22 of 30
template variants selected by the semantic plans (including plans with pending
animation/alpha work). Validated each found template's salted vertex/pixel
shader references and recorded entry-point masks, texture names and constants.
Eight missing variants and nearby native candidates are explicit in
`reach-preflight/high-noon-shader-donors.json`; recreate with
`find-high-noon-shader-donors.py`. Nearby variants are research leads only:
environment, alpha, bump and illumination differences cannot be substituted
merely because their option numbers are close. No material/runtime acceptance
or additional installed map follows from this inventory.

High Noon specialized material staging (2026-10-25): extended ReachMaterials
and NativeEffectPost for native terrain/hologram roots and routing. Terrain
global-material indices are rebuilt by name; shared uint SingleMaterial is
preserved separately, following TagTool ShaderTerrain. In-memory staging passed
for ca_heh_blue_wall_b_blend (Shrine terrain donor) and the animated
ca_heh_forerunner_halogram (Cold Storage donor, one converted animation).
See `reach-preflight/stage-high-noon-materials.py` and its staging report.
Added square, unsplit Reach color cubemap reading; all six 256x256 base faces
of ca_heh_cube_center round-trip through native tiling. The current cube encoder
retains only the base mip (source has nine), so this candidate is NOT visually
accepted: source roughness/mip behavior and unrepresented terrain parameters
(including blend_map/env_roughness_offset) need handling before installation.
No map was saved/deployed by these staging checks.

High Noon cubemap mip preservation (2026-10-25): resolved the base-only cube
limitation above. `xbox_mip_chain.tile_cube_chain` writes mip-major six-face
storage and a packed tail per face; Reach materials enable this path while
existing callers retain their previous default. All nine authored mips of
ca_heh_cube_center are retained at 256x256 base resolution (393,216 native bytes).
The independent TagTool XboxBitmapUtils decoder recovered exact source bytes
for all 54 face/mip combinations. Reproduce with
`reach-preflight/check-high-noon-cube-mips.py` then its adjacent PowerShell
script; report `high-noon-cube-mip-verification.json`. Disposable binary check
data was removed. This validates layout and content preservation, not the
unfinished material's rendered appearance; other terrain parameters remain open.

High Noon sampler conversion (2026-10-25): ReachMaterials now preserves each
bound source texture's U/V address modes and translates the packed Reach filter
byte into the native H3 filter enum, instead of retaining the prototype donor's
sampling settings. TagTool at pinned ce2dc6ac13072b160752af618ea1dc143e2727ac,
`TagTool/Tags/Definitions/RenderMethod.cs` and
`TagTool/Shaders/ShaderConverter/ShaderConverter.cs`, supplies the layout and
conversion precedent (FilterModePacked.FilterMode). Source 0xa0 becomes native
trilinear 0; its upper anisotropy nibble is not a native filter enum. Unsupported
comparison/lightprobe filtering and invalid address values fail explicitly.
The material staging check reads back serialized native texture rows: all five
terrain and three animated hologram bindings match source address/filter modes,
including clamp/clamp on the terrain cubemap. Both materials still stage; no
cache deployed or rendered appearance accepted. Source references:
https://github.com/TheGuardians/TagTool/tree/ce2dc6ac13072b160752af618ea1dc143e2727ac/TagTool

High Noon full specialized-material staging (2026-10-25): expanded the same
check from two examples to all 29 BSP terrain/hologram materials. All 25 terrain
materials and one hologram stage, with 322 serialized sampler bindings checked.
These remain metadata/resource checks, not visual acceptance; unrepresented
terrain constants remain reported. Three hologram issues are now isolated:
ca_heh_fx_halogram lacks native template _0_8_0_0_0_1_0;
ca_heh_forcefield uses unsupported palettized_plasma;
ca_heh_forerunner_holo_ani fails animation relocation. A focused rerun identifies
entry 14, pixel constants, layer_depth: source route (36614,6,0), no matching
target route. Do not omit the animation. The next step is comparing native
layer_depth routing across shader stages and alternative exact-template donors.
`stage-high-noon-materials.py [material_basename]` supports a focused rerun in
a separate selected report without replacing the full inventory. No map saved
or installed; all staged resources were discarded from memory after checking.

High Noon hologram routing and discrete constants (2026-10-25):
`reach-preflight/audit-hologram-routes.py` compares actual source routes with
every original-disc exact-template donor. Both mainmenu and midship have
layer_depth in pixel routes for entries 3-8 but omit it in entry 14; Reach
includes that animated parameter in entry 14. It is not a vertex/pixel stage
swap, and selecting the other donor alone cannot fix this incompatibility.
Evidence is `high-noon-hologram-routes.json`; no route is silently discarded.
Separately fixed ReachMaterials retaining prototype integer/boolean values:
these are now bound by parameter name, with checked float-to-integer promotion
for Reach layers_of_4 following the established terrain_materials conversion.
Unknown native values and non-integral/out-of-range layer counts fail explicitly.
A focused real-material staging run for ca_heh_forerunner_halogram reads back
the emitted H3 integer value layers_of_4=4 and verifies it against the authored
source. Its animation and texture checks also pass. The full 29-material report
predates this discrete-constant fix; the selected report is the latest check.
No additional map accepted/deployed, and the animated holo_ani remains open.

High Noon texture transform binding (2026-10-25): ReachMaterials now reads
each source texture's transform constant and function span, validates their
bounds, relocates the constant by name into the native template, and preserves
source function indices (convert_material_animation retains function order).
Donor transform/overlay metadata is no longer implicitly retained. Missing
native transform parameters, signed-byte overflow, and texture animations
without converted register routes stop conversion explicitly. Focused staging
passed for ca_heh_forerunner_halogram and ca_heh_blue_wall_b_blend; the checker
reads back each emitted constant name and overlay span as well as sampler bytes.
Both tested materials have zero texture overlay spans; nonzero spans remain
unverified in a staged High Noon material. The separate animated depth-register
incompatibility remains unresolved. No rendered or gameplay acceptance implied.

High Noon multilayer depth research (2026-10-25): traced the missing entry-14
parameter beyond tag metadata. TagTool's pinned ShaderGenerator submodule is
Beatthezombie/HaloShaderGenerator revision 9c7536ee729c6e24ac0dda6675bc0a209ea2fa98.
Retained `entry_points.fx`, `self_illumination_halogram.fx`, and `halogram.fx`
under reach-preflight. The reference static_per_vertex_color_ps passes zero
view_dir_none (unless APPLY_FIXES is enabled); multilayer sampling multiplies
its offset by view_dir.xy * layer_depth. This explains why the native donor's
entry 14 has no layer_depth binding. This reference is explanatory evidence,
not a claim that regenerated PC shaders establish Xbox bytecode equivalence.
The real-cache routing audit confirms both native donors omit that binding.
The source material occurs at BSP slot 162, Lbsp mesh 291 part 0: transparent,
rigid vertex format, no PRT, Reach lighting policy 1, flags 0x184. Actual runtime
pass selection still needs establishing; do not assume entry 14 is unused.
No shader route or authored effect has been dropped as a workaround.
Reference source:
https://github.com/Beatthezombie/HaloShaderGenerator/blob/9c7536ee729c6e24ac0dda6675bc0a209ea2fa98/halo_online_shaders/entry_points.fx

High Noon collision source reader (2026-10-25): added bounded
reach_bsp_collision_source.py and reproducible
reach-preflight/inventory-high-noon-collision.py. The scenario-selected BSP
owns collision resource 0xfd17026a at root+0x518. The resource contains one main
collision BSP, no large BSPs, and 809 instance definitions. Main geometry:
53,927 nodes, 480 supernodes, 19,878 planes, 28,002 leaves, 44,883 2D references,
14,999 2D nodes, 17,653 surfaces, 30,620 edges, 12,951 vertices. All 810 geometry
headers and referenced array spans read within resource bounds; none exceeds
the checked H3 plane/surface/edge/vertex/2D-node widths before expansion.
This does not yet certify native collision: supernodes require expansion,
Reach stitched/convex physics requires conversion, and index/topology validation
and native MOPP building remain. No geometry was simplified or deployed.
Layouts are pinned TagTool StructureBspTagResources.cs, CollisionGeometry.cs,
InstancedGeometry.cs, retained in reach-preflight for the adapter.

High Noon main collision tree expansion (2026-10-25): the compact Reach
geometry fixture now runs through installed TagTool ResourceDeserializer,
ResizeCollisionBSP, and SupernodeToNodeConverter without changing source files.
Expanded output has 56,426 ordinary nodes and 27,078 planes, within original
H3 plane-index width. All output node/leaf/plane references are bounds checked;
leaf/surface counts stay unchanged. Independent Python traversal compares the
Reach supernode tree with the expanded ordinary tree: all 45,902 classifications
match, including two nearby probes per authored vertex (25,902 probes), with
32,733 nonempty leaf results. This proves the checked tree transformation,
not assembled native physics or gameplay. Instance collision and MOPP remain.
Reproduce in reach-preflight: expand-high-noon-collision.py,
expand-high-noon-collision.ps1, verify-high-noon-tree.py. Latest report is
high-noon-expanded-tree-verification.json; expanded nodes/planes are retained
in high-noon-expanded-tree.bin (884,664 bytes). The disposable 2.24 MB input
fixture was removed after verification and is recreated by the exporter.

High Noon instance tree expansion (2026-10-25): 628 of the 809 definitions
have collision surfaces; 417 contain Reach supernodes. All 417 now expand via
the same reference bridge, with original planes and leaf/surface counts checked
unchanged and output references/plane widths validated. Independent traversal
matched all 261,360 classifications, including nearby points around every
instance vertex; 157,446 classified into leaves, with no absent source paths.
Run expand-high-noon-instances.py, expand-high-noon-instances.ps1, then
verify-high-noon-instances.py. Output is high-noon-instance-trees.bin, verification
is high-noon-instance-tree-verification.json. The 12.8 MB disposable input was
removed. This does not convert all physics: 82 definitions have MOPP blocks,
13 have convex-polyhedron data, and stitched-physics flags must still be handled
when assembling the native resource. No instance geometry was removed and no
map was deployed. Do not equate tree verification with gameplay acceptance.

High Noon native collision arrays (2026-10-25): added reach_collision_geometry.py
to combine verified expanded nodes/planes with original surfaces, leaves, 2D
trees, edges and vertices. All 810 geometry records serialize successfully into
native H3 byte order. Reach plane-negation flags become the native signed plane
index bit; unsupported surface flags fail rather than disappearing. Bounds are
checked for every tree, leaf span, surface plane/edge, edge connection and vertex
edge reference; empty leaf spans retain their 0xffffffff start sentinel.
`reach-preflight/convert-high-noon-collision-arrays.py` verifies expanded-file
hashes, stages all records, and independently decodes native edges/vertices/
references/2D nodes/leaves to compare with source values. The report is
high-noon-collision-array-conversion.json. Payloads are staged only in memory;
no duplicate binary archive or installed cache was created. Full resource
assembly still requires instance/MOPP/convex-physics adaptation and surface-to-
render mappings; this is not yet a playable-map or console acceptance result.

High Noon instance MOPP conversion (2026-10-25): corrected the source reader's
MOPP stride from H3's 64 bytes to Reach MCC's 96 bytes (Assembly ReachMCC sbsp
Collision MOPP Codes). CodeInfo is at +32, allocation size/capacity at +56,
and the bytecode tag block at +80. The earlier header rejection was a reader
layout error, not bad source pointers. Added reach_physics.convert_tag_mopp:
validate source allocation, pointers, build types and unmapped metadata; emit
native 64-byte headers with bounds, count/capacity and build type preserved.
All 82 real instance blocks pass header conversion and the existing retail
opcode parser; bytecode remains byte-for-byte unchanged. Readback validates
native bounds and allocation fields against source. Reproduce with
reach-preflight/audit-high-noon-mopp.py; report high-noon-mopp-audit.json.
The caller still must allocate each code block and attach its native +52
pointer fixup in the final resource. No runtime physics acceptance is claimed.

High Noon collision-to-render mappings (2026-10-25): added
reach_collision_geometry.convert_surface_mappings. Actual Reach mapping words
use triangle=value>>12 and cluster=value&0xfff, per pinned TagTool
TagDeserializer.DeserializePlaneReference; H3 instead stores two ushorts.
Source int/int surface spans become H3 ushort/short spans with bounds checks
and explicit rejection of overflow. All 809 instance definitions pass this
conversion, alongside the main BSP geometry: 810/810 staged. The updated
convert-high-noon-collision-arrays.py decodes every native mapping, reconstructs
the source packed word exactly, and compares every surface range to its source.
No lossy index truncation, mesh splitting, or gameplay changes were introduced.
This check does not yet validate each triangle against its referenced rendered
mesh; complete resource integration and native gameplay remain outstanding.

High Noon mesh-reference verification (2026-10-25): the follow-up
reach-preflight/verify-high-noon-surface-meshes.py checks all 224,297 instance
surface mappings against their actual mesh index buffer, vertex count and part
ranges. All pass; every cluster field is zero. The first verifier incorrectly
treated TriangleIndex as a triangle ordinal. Pinned TagTool
ce2dc6ac13072b160752af618ea1dc143e2727ac, GenerateStructureSurfacesCommand.cs,
explicitly writes TriangleIndex = triangle.Index + 2. Using that final-index
position, every reference is aligned to a valid three-index triangle. The
converter itself already preserves the value and required no correction.
Report: high-noon-surface-mesh-verification.json. Spatial correspondence and
runtime behavior remain untested; this is not a playable-map acceptance.

Remaining physics distinction: 13 instance definitions (83, 199, 380, 389,
396, 424, 443, 552, 611, 617, 619, 620, 693) have convex polyhedra but no MOPP.
All also have collision surfaces, though their surface counts range from 6 to
1,859; do not assume the convex and detailed representations are interchangeable.
The same pinned TagTool PortingContextGen3.BspCollision.cs retains these shapes
in Halo Online ExtraData. Original H3's 184-byte instance definition has no such
extension. Therefore that Halo Online route cannot simply be copied into the
360 resource or omitted. Investigate native H3 shape representation/generation
before assembling the complete physics resource. TagTool CollisionMoppGenerator
offers a generate-collision-mopp tool path; suitability for the original H3
physics contract has not yet been established.

High Noon convex-source audit (2026-10-25): corrected the resource reader's
polyhedron stride from 128 to 160 bytes. Reach MCC's 64-bit HkConvexVerticesShape
occupies 0x90 bytes; the material follows at 0x90, with 16-byte alignment to
0xa0. The source pointer spacing agrees. The older class-level size annotation
alone does not describe the expanded MCC layout. Added
reach-preflight/audit-high-noon-convex.py, which validates all 13 actual shapes:
runtime pointers, shape type, allocation counts, vertex bounds, plane
containment and material references. Every hull has 8 or 12 vertices and 6–12
planes; maximum positive plane distance is below 1.81e-7, consistent with float
rounding. All retain their authored 0.0164 convex radius. Referenced materials
identify metal beams, hall doors, hall panels and Forerunner trim (not an
assumed glass-only exception). Report: high-noon-convex-audit.json. Refreshed
collision inventory still reports 810 geometries within native index widths.
Original H3 InstancedGeometryPhysics contains GeometryShape and MoppBvTreeShape,
where Reach additionally supports DecomposedPoopShape referencing these hulls.
H3 phmo supports convex shapes, but routing these BSP hulls through that path
requires placement/ownership integration; no equivalent native BSP behavior
has been established or deployed yet. No shapes were dropped or approximated.

High Noon native convex payloads (2026-10-25): inspected installed native
construct.map and sandbox.map phmo tags. Sandbox sand_wall uses motion type 5
(Fixed), shape reference type 4 (Polyhedron), Havok type 8, reference count 128,
self-offset 32 and radius 0.01640000008046627. This matches the source hull
radius exactly and establishes an existing native fixed-convex representation.
Added reach_convex_shape.convert_bsp_hull to translate the 160-byte Reach BSP
record into the 96-byte H3 phmo shape portion, with a caller-supplied self-offset
and separately endian-converted vector/plane arrays. Unknown source state is
rejected. All 13 actual hulls stage successfully; readback preserves every
vector/plane bit, AABB, radius and allocation count. Updated convex audit records
the native shape digest and result. No redundant binary archive is written.
This is payload conversion, not complete phmo/scenery construction: authored
material properties, fixed bodies, instance transforms, ownership and avoidance
of duplicate physics still need integration and native gameplay verification.

High Noon hull placement integration data (2026-10-25): added
reach_bsp_instances.read_instances for Reach's 156-byte resource-resident
placements (StructureBspCacheFileTagResources root+72). The owner-checked
pathfinding resource 0xfd1803c4 contains 1,138 placements. All 13 convex
definitions are used, by 14 placements: definition 552 occurs twice. The saved
high-noon-hull-placements.json preserves each source matrix, scale, flags,
bounds, policies and physics reference; it links each to its converted hull.
All 14 are collidable and contain exactly one convex child and no geometry
child. MCC's instance-physics MOPP structure occupies 128 bytes before those
child tagblocks, rather than the console layout's 80 bytes. Each child matches
the corresponding hull center within 1e-6, its half extents plus convex radius,
and its placement scale. Both copies of definition 552 are retained. Reproduce
with reach-preflight/prepare-high-noon-hull-placements.py. This supplies the
authored placement/ownership input; native scenery/body construction and
duplicate-physics avoidance remain necessary before runtime verification.

High Noon hull material resolution (2026-10-25): added
reach_bsp_materials.resolve_collision_materials and connected it to the hull
placement preparation. All four used BSP material slots have exact H3 name
matches: slots 1/30/64 resolve to hard_metal_thick_for (native index 86), and
slot 4 to hard_metal_solid_for (99). Native Sandbox friction/restitution/density
are respectively 0.8/0.35/6500 and 0.85/0.4/10000. These values come from the
actual native matg, not the unrelated sand_wall donor's material prefix.
Reach's corresponding rows contain zero coefficients; copying those directly
would bypass material inheritance. The resolver uses stock H3 properties per
the binding asset policy, rejects absent exact names, and validates indices and
coefficients. high-noon-hull-placements.json now links all 14 placements to
resolved native materials. Fixed-body/object construction remains pending.

High Noon fixed-body physics staging (2026-10-25): added
reach_fixed_hull.stage_fixed_hull. It uses the native Sandbox sand_wall's
single fixed convex wrapper, rejects unrelated donor physics blocks, replaces
the hull/vectors/planes and material, and rebuilds the enclosing sphere (rounded
outward to f32) and center. This is fixed-only: stock inactive mass/inertia
defaults are retained, not offered as a dynamic-body mass calculation. Existing
base-cache node/region references remain valid under MapBuilder's address
preservation. Material phantom index is -1, with no phantom allocation.
stage-high-noon-hull-physics.py stages all 13 complete phmo roots and child
arrays into the real native MapBuilder. Readback verifies fixed motion, convex
shape reference, all hull bits, materials, array pointers and retained node/
region references. The base metadata is unchanged. Total added metadata,
including roots and alignment: 12,776 bytes. Report:
high-noon-fixed-physics-staging.json. No map binary saved or installed. Model/
scenery wrappers, the 14 scenario placements, duplicate BSP-physics suppression
and actual runtime verification still need integration.

High Noon collision-object candidates (2026-10-25): added
reach_hull_object.stage_hull_object using the base Sandbox wall's fixed native
bloc/hlmt wrappers. Each candidate links its new phmo, retains the single native
model node, updates object/model bounds from the new hull, removes the donor's
render/collision/animation/LOD references and Forge multiplayer properties.
The authored BSP geometry remains responsible for rendering and detailed ray
collision. No extra visible mesh or texture data is added. The original maps
inspected do not provide a render-null fixed-body example, so this wrapper is
explicitly a runtime-unverified candidate, not an accepted engine behavior.
Updated stage-high-noon-hull-physics.py registers and reads back all 39 tags
(13 each bloc/hlmt/phmo), verifies the full reference chains and absence of
donor render/collision references, then verifies the existing hull/material
checks. Added metadata is now 21,932 bytes; base metadata remains unchanged.
No installed cache changed. Scenario placements, matching BSP-Havok suppression
and native visual/physics verification are still pending.

High Noon native hull placements (2026-10-25): added
reach_hull_placements.append_hull_placements. All 14 authored instances have
exact identity rotation and unit scale, so no approximate Euler conversion is
needed. The adapter explicitly rejects other poses pending their own handling.
It appends 13 native crate palette entries and 14 placements, preserves existing
arrays, scans all scenario object arrays for occupied unique IDs, and assigns
unused IDs. Records retain source positions exactly, bind to BSP zero, create
at rest, remain neutral, and disable game-type replacement. Returned source
instance indices identify the precise future BSP-Havok suppression set; this
function does not apply that suppression itself.
The fixed-physics staging harness now exercises this against a cloned native
Sandbox scenario in the same builder, then reads every placement and palette
link back. All 14 positions/scales/rotations and object links match, and all
pre-existing crate records/palette bytes are unchanged. Total staging metadata
is 60,448 bytes including cloned scenario and copied existing arrays (not a
final High Noon map-memory estimate). No installed map was modified. Wrapper
runtime behavior, source-Havok replacement and full map integration remain open.

High Noon hull native investigation (2026-10-25): the temporary Sandbox fixture
contains 13 new bloc/hlmt/phmo chains and 14 appended placements. It shares
unchanged disc files by hardlink and uses the existing installed executable.
Run .local/loading-traces/20261025-161521-44588 reached visually correct Sandbox
gameplay (proof-loaded.png), but all five object snapshots contained zero new
hull objects. This is not runtime acceptance of the wrappers.
The follow-up run 20261025-162339-38828 used the identical candidate SHA256
01f7f26232f64e199ed455eda95f219219873e68360234c3de545b727c2eea7c,
with added read-only scenario diagnostics and no additional screenshot.
The live crate array (183 records) and palette (90 records) match the candidate
byte-for-byte by SHA256; both object snapshots still contain zero new hulls.
Thus stale/wrong scenario data is excluded, while placement eligibility and
object/model creation remain to be traced. Collision response is unverified;
do not suppress source Havok or deploy these wrappers yet.
trace_loading.py now records scenario_object_arrays when --sample-object-map
is supplied. work/map-conversion-batch/reach-preflight/check-high-noon-hull-run.py
produces compact hull-run-<run>.json reports tied to the candidate hash.
Both harnesses reached their watchdog and exited. The fixture is retained for
the object-creation investigation; remove it once superseded, preserving these
compact reports. No installed map was changed.

High Noon placement rejection traced (2026-10-25): native run
20261025-162850-21684 traced 82335BC8 (scenario creation), 82346F50
(placement preparation), and 8232F3D8 (object_new). Only original crate
indices 0..168 reached preparation; appended indices 169..182 did not.
Original function 82347CA8 loads the compiled attach mask at placement +0x50,
intersects it with the active BSP mask and skips creation when the result is
zero. The candidate incorrectly populated only the manual editor mask +0x32.
reach_hull_placements now populates both masks with bit zero, matching the
single-BSP assignment; staging verifies both fields. This changes cache data,
not engine code. Runtime acceptance of the corrected candidate remains pending.
Added --trace-scenario-objects to the existing process-local diagnostic.
Automatic approval review rejected recursive removal of hull-native-test with
"blocked by policy". The folder was left intact; --replace-native-cache safely
reuses it, refusing replacement if sandbox.map is linked to the installed map.
No additional cache copy or executable build is created.

Corrected hull native result: run 20261025-163227-29648 reaches all 14 appended
placements. Each original placement-preparation call returns 1; each creation
call returns a distinct valid object handle. Snapshots at 110, 115 and 120 seconds
contain all 14 hull objects, each with a non-null Havok component and physics
flags 0x280 (connected to physics and at rest). The compiled BSP attach-mask fix
therefore resolves the observed creation failure. Exact candidate hash, creation
events and component handles are retained in reach-preflight/
hull-run-20261025-163227-29648.json. The run exits at its 125-second watchdog.
This proves object/physics-component creation and short-run persistence, not
collision response, authored High Noon visuals, or full-map integration. Keep
source BSP Havok intact until replacement behavior is verified. The only full
candidate cache remains in the reused fixture; old candidates were overwritten.

High Noon native collision section assembly (2026-10-25): added reusable
reach_collision_sections.CollisionSections and reach_instance_bounds.
stage-high-noon-collision-sections.py packs all 810 collision geometries,
82 MOPPs and 809 surface-mapping tables into one native arena, then reads every
array/header/code block back through the emitted fixups and compares it with
the converted source. Result: 121,848 control bytes, 17,822,192 raw bytes and
6,360 checked fixups. These are section sizes, not total map RAM usage.
All 809 definitions have authored Reach placements. Their world AABB corners
are transformed back through each placement's verified orthogonal basis and
scale, unioned in definition space, then enclosed by outward-rounded float32
spheres. Authored collision vertices are included too: some extend slightly
beyond render AABBs. All 128,193 instance collision vertices are enclosed with
no tolerance allowance. Visible geometry is unchanged. Verified expanded-tree
hashes are required before assembly. The compact result is
work/map-conversion-batch/reach-preflight/high-noon-collision-sections.json.
The arena is built in memory, avoiding another large intermediate artifact.
Native instance header/root assembly and the explicit convex replacement
handoff remain pending; this is not yet a publishable BSP resource or map.

High Noon collision resource root/header assembly (2026-10-25): added
reach_collision_resource.assemble_collision_resource. Native layout was
cross-checked against Sandbox (8 definitions), Last Resort (336) and Guardian
(212). Their trailing definition float is 0 or 1; all 1,138 authored High Noon
placements specify lightmap resolution 1.0. Repeated definitions must agree on
that value. Native headers preserve checksums, mesh/compression indices, verified
definition bounds, and this authored scale. Sections now write directly into
the root's 96-byte main and 184-byte instance headers without orphan copies.
The assembled candidate has 154,256 control bytes, 17,822,192 raw bytes and
6,362 fixups. Every geometry array, MOPP header/code, surface mapping and scalar
header field was independently read back from the assembled root and compared
against the previously verified sections/source. The raw hash remains
cff062198fb17a99c4afbdb1882f6da7f3bd3192d9eb28d05fbf574c8046d50b;
control hash is 750fdaf3187ab738d328948dc57b2534a25f0655f593ce4b578fcb08d1dc285d.
All 13 Reach convex header/vector/plane payloads are returned intact as explicit
external-physics obligations; mismatched or absent handoffs are rejected. Reach
compiler flags are retained in that report rather than guessed into unrelated
native fields. The separate BSP instance/physics resource, convex replacement
integration, material bindings and full-map runtime verification remain open.
No installed cache was changed and no large intermediate binary was saved.

### 2026-10-25: High Noon geometry-instance physics wrappers

- Continued from the prior acknowledgement turn (no implementation progress in that turn). Read pinned TagTool `PortingContextGen3.Bsp.cs` and `.BspPathfinding.cs` at revision `ce2dc6ac13072b160752af618ea1dc143e2727ac`. Its Reach conversion rebuilds the CMoppBvTreeShape as native type 27 with source MoppScale; cached code size/info are not copied to native serialized fields. This reference targets Halo Online and is not by itself proof of retail H3 compatibility.
- Added reusable `snapshot/tools/reach_instance_physics.py`: bounded Reach MCC geometry-child reader and 112-byte retail H3 physics-wrapper staging. Validates child kind, collection type, zero runtime pointers, owner, source instance key and finite dimensions. Retains the original 128-byte MOPP header in returned obligations and explicitly requires MOPP binding verification. Convex children are rejected here and continue through the separate fixed-hull adapter.
- Ran `python -B work/map-conversion-batch/reach-preflight/audit-high-noon-instance-physics.py`: all 850 geometry wrappers passed exact bounds/identity/scale comparisons; 14 convex placements remain separately handled; 274 instances have no physics. Output is 95,200 bytes in memory, SHA256 `d3af40ffea6aeb6bee04cbe023d386bc9e03210efbbcb77c7547ea632e325cf8`.
- Fixed serialized fields matched all 1,161 inspected original H3 geometry wrappers (Sandbox 13, Last Resort 694, Guardian 454). Compact report: `work/map-conversion-batch/reach-preflight/high-noon-instance-physics.json`. No installed cache mutation, engine build, or extra runtime test.
- Remaining: resolve retail runtime MOPP associations/environment keys and assemble native placements with the collision/resource outputs. Source per-instance headers contain 530 distinct cached code sizes; the 82 definition MOPPs are not yet proven to cover the 850 geometry placements. Full High Noon gameplay, collision response and visuals remain unverified. Do not report this structural check as a completed map.

### 2026-10-25: resolve missing High Noon instance MOPPs

- Prior goal turn made implementation progress (850 wrapper conversions). Follow-up source association audit proved 291 geometry placements match a definition MOPP's cached size and CodeInfo exactly. The remaining 559 placements reference 533 definitions with flag bit 16 and no definition MOPP. This matches the pinned TagTool StitchedPhysics interpretation; it is no longer an undifferentiated missing-data problem.
- Added `reach-preflight/audit-high-noon-mopp-associations.py` and compact report. Read pinned `StructureBspTagResources.cs` and `InstancedGeometry.cs`; Reach has no extra HavokData block in this resource root.
- Added `reach-preflight/rebuild-high-noon-instance-mopps.py --all`. Uses the existing SHA-pinned `work/forge-world/tools/mopp.exe` compiler, explicit repository cwd and repository TEMP/TMP/APPDATA/LOCALAPPDATA, 180-second per-process watchdog, no host input. Inputs preserve every original float vertex and oriented surface loop. One shared input/log avoids 533 redundant text/log files. All 533 outputs compiled; each reachable terminal-key set equals its complete source surface table. No collision simplification.
- Rebuilt CodeInfo is used with its own code; original cached CodeInfo is not substituted. For example definition 1 has the same 1,903-byte code size but small float differences in CodeInfo. Byte identity with original stitched acceleration is not claimed.
- Added optional rebuilt MOPPs to `reach_collision_resource.assemble_collision_resource` and `CollisionSections.generated_mopp`. Rejects replacing existing MOPPs or definitions without reviewed stitched flag; checks complete surface coverage and native allocation bounds. Original 82 MOPPs remain unchanged.
- Ran `stage-high-noon-collision-sections.py --rebuilt`: verified all 533 rebuilt headers/code through native fixups, all 810 geometry arrays, all 809 surface mappings and scalar fields, and all 850 geometry physics placements now resolve to exactly one definition MOPP. All 13 separate convex handoffs retained. Report `high-noon-collision-sections-rebuilt.json`.
- Full assembled resource: 188,368 control bytes, 18,730,592 raw bytes, 7,428 fixups; +942,512 bytes over prior assembly. Control SHA256 `3a6f3eed8fc17f03588180f871ff8abf776d8e286830e886f5d0cf1121fc30a0`; raw SHA256 `2edc52e8967f952ce235f7ffa5d4756377e8f40eee772e53687123163243d729`.
- This resolves missing per-definition acceleration structurally, not complete physics gameplay. Next integrate native placement records/environment MOPP and convex replacement suppression, then the rest of BSP/scenario/materials. Spatial/runtime validation remains required. No deployed map or new engine build this turn; full batch goal remains incomplete.

### 2026-10-25: High Noon environment MOPP translation

- Prior goal turn made implementation progress (533 rebuilt definition MOPPs). Inspecting the actual scene MOPP exposed 131,494 terminals: class 13 main surfaces, class 16 direct instances, and Reach stitched keys with top three bits 3. For stitched geometry, low 16 bits identify the instance and bits 16–28 identify the surface. Every decoded index is in bounds; all 559 geometry instances cover their full source surface sets. The other 14 stitched entries exactly match independently verified convex replacement placements (their key subindices are not treated as polygon surface coverage).
- `audit-high-noon-environment-keys.py` records this evidence. There are 290 direct geometry instances, 559 stitched geometry instances, 14 convex replacements and 17,653 main surfaces. Geometry instance 680 has physics data but no source scene-MOPP entry; preserve that source omission rather than inventing coverage.
- Added reusable `reach_environment_mopp.py`: preserve authored spatial branch tests, convert stitched polygon terminals to native instance candidates, and remove only explicitly handed-off convex placements from this tree. The independent native convex objects must be installed in the final scenario to supply their broadphase coverage. Caller still must bind the rebuilt definition MOPPs and native geometry placement wrappers.
- Extended `forge_mopp.relocate_keys` with opt-in `clear_source_bases`. All rewritten surviving terminals already receive an absolute base. Clearing superseded source reoffset operands avoids leaving Reach key encodings behind; native terminal keys are written directly. Initial two-stage retail conversion rejected residual Reach base constants, leading to this correction. Existing default relocation behavior is unchanged.
- Full source conversion passed reachable-terminal multiset verification and branch relocation checks. Output `high-noon-native-environment-mopp.bin`: 2,818,752 bytes, 131,480 terminals, SHA256 `eb9b3344ee8ba4cc32bf5bfa734f746e5b2ffa3a0dd10f084b15f75927f3b5d2`. Retains source CodeInfo `[-2749.787353515625, -1471.486328125, -728.453369140625, 5604.1025390625]`. Source code was 1,580,864 bytes; expansion comes from explicit branch relocation and absolute keys. Repeated instance candidates remain; runtime cost is unmeasured and must be assessed in the assembled map.
- Four focused MOPP tests passed, including inherited foreign bases, branch-local deltas, removal of one branch and preservation of the other. This proves key/control-flow bookkeeping, not native spatial or gameplay correctness. Native placement metadata, final scene-header linkage, rendering/material assembly and full gameplay checks remain. No installation modified or engine built.

### Reflection water UV recovery (2026-10-26)

- Added `snapshot/tools/reach_water_parameters.py`: recover original indexed
  water UVs from MCC expanded corner data. The format-27 descriptor's 24-byte
  stride is allocation metadata, not the meaningful packed float2 stride.
- Read-only audit `work/map-conversion-batch/reach-preflight/audit-water-parameters.py`
  verifies Reflection BSP1 meshes198/218: 221/50 original water UV entries,
  all708/138 triangle corners match exactly through original format-26 indices.
  The8-byte layout has zero conflicts; interpreting UVs every24bytes creates
  64/11 conflicting original indices. Every nonzero allocation byte belongs to
  a recovered corner UV; there is no hidden local-info field in this allocation.
- Decoder rejects malformed allocation sizes, nonfinite UVs, conflicting indexed
  values, unexplained nonzero trailing data and sparse original indices.
- This is not yet a complete native water conversion. H3's local-info fields
  still need a justified mapping from Reach material/geometry semantics.
  The retained TagTool Reach reader explicitly substitutes placeholder15/.9;
  those values are not treated as authoritative source data. Next investigate
  water shader inputs/material behavior, then integrate with mesh splitting and
  resource emission. No generated map or installed bundle changed in this pass.

### Reflection native collision arrays and water material audit (2026-10-26)

- Original source: Bungie's Reflection from Halo Reach, MCC U13 cache
  `haloreach/maps/52_ivory_tower.map`; direct adaptation, not an upstream H3
  custom-map conversion. This pass changes no installed map.
- Added Reach `rmw ` parameter reading using the shared RenderMethod layout.
  Primary confirmation: TagTool ShaderWater.cs at ce2dc6ac13072b160752af618ea1dc143e2727ac
  declares no additional fields. Full source parameters are retained in
  work/map-conversion-batch/reach-preflight/reflection-water-materials.json.
- Both Reflection water materials select bump waves, pure color, static
  reflection, dynamic refraction, no bank alpha, no global shape, auto foam,
  repeat detail. The five compiled native water templates found across the
  installed H3 disc maps all use default displacement waves. There is no exact
  bump donor in that set; do not substitute one and call it faithful. Audit:
  reflection-water-donors.json and audit-reflection-water-materials.py.
- Retained HaloShaderGenerator water_shading.fx identifies H3 local-info.x as
  wave displacement scaling, y as depth affecting shallow-water ripples and
  depth-based bank/global shape. This is comparative shader-source evidence,
  not proof of a native compiled shader's instructions. Reach's raw schema
  stores only Base Texcoord in water vertices; missing H3 fields cannot be
  recovered as hidden floats from the MCC UV allocation. Next investigate a
  supported bump shader path or an explicitly derived equivalent parameter
  representation, without hardcoding TagTool's placeholder15/.9.
- All three scenario-bound collision resources audited, including owner/salt:
  194,197,7 geometries; none exceed H3 source index widths. Reused the pinned
  ReachBspTreeBridge for63 compressed trees (main and instance geometries),
  with keys `(bsp_index << 16) | (instance_index+1)`, zero for each main tree.
  Independent source/expanded traversal:74,458 classifications match,
  including39,730 leaf hits and no absent branches. Expanded output SHA256:
  2e743ad53f0414b207a6924a6d95b1bfb7f87f88e813502e8b8f2baca34535dc.
- All398 native collision array conversions now pass structural/index checks,
  including expanded plane counts, without simplifying visible or collision
  surfaces. Result: reflection-collision-array-conversion.json. This does not
  yet include native instance physics, complete BSP resource assembly or game
  verification. The compact fixtures remain for integration; no duplicate map
  builds were created.
- Reproduction from repository root: Python -B inventory-reflection-collision.py;
  expand-high-noon-instances.ps1 -Prefix reflection;
  Python -B verify-high-noon-instances.py --prefix reflection;
  Python -B inventory-reflection-collision.py --expanded. Scripts reside under
  work/map-conversion-batch/reach-preflight; PowerShell redirects temp to
  .local/build-temp. The existing High Noon defaults remain unchanged.

### Reflection resource assembly and multi-BSP physics (2026-10-26)

- Extended native collision assembly to retain RenderBsp blocks at instance+116
  and BreakableSurfaceBits at+140. Render geometry uses the same validated native
  geometry writer; breakable bitvectors are preserved as endian-converted uint32.
  Pinned InstancedGeometry.cs establishes both fields/layouts; installed TagTool
  reflection confirms SupportedBitfieldStruct.BitvectorData is Int32 (size4).
- Accepted the additional observed compiler flag combinations5,16,18,21 while
  preserving their exact values in the obligation report. No physical geometry,
  convex hull or physics requirement is discarded based on these flags.
- Found7 additional render-collision geometries (1 inBSP0,6 inBSP1). Six needed
  supernode expansion. Replaced the earlier compact fixture in place, not copied:
  69 expanded trees now pass79,144 independent spatial classifications including
  42,789 leaf hits, no absent branches. Output SHA256 is now
  204595dfffc3958596237e48f00374a8a9ee0b9c5dd20e281ee73f29d15b4736.
  Render fixture keys use bit31 plus BSP<<16, definition<<8, render ordinal.
- stage-reflection-collision.py assembles and reads back all3 native resources:
  BSP0 control35,824/raw720,656 bytes; BSP1 control36,976/raw3,327,472;
  BSP2 control1,248/raw531,400. All405 geometry arrays and3 breakable words
  roundtrip. Convex payloads remain explicit external obligations. This is not
  a playable map and does not establish final resource residency or physics.
- Geometry physics helper now accepts/validates an explicit source BSP index,
  retaining that index in the emitted native child. Reflection's98 geometry
  wrappers refer toBSP1, so the previous single-BSP0 assertion rejected them.
  All98 now pass source/native identity/bounds/scale readback. Also inventoried
  455 convex placements (118/333/4) and1,897 instances without per-instance
  physics (1191/700/6); these are not automatically discarded.
- High Noon regression:810 geometry sections,82 source MOPPs and533 rebuilt
  MOPPs pass;850 geometry wrappers still pass, including stock-field comparisons
  with1,161 native wrappers across Sandbox/Last Resort/Guardian.
- Reports: reflection-collision-resources.json, reflection-instance-physics.json,
  reflection-collision-array-conversion.json under reach-preflight. Next finish
  Reflection convex placement/physics integration and MOPP bindings, alongside
  outstanding bump-water material/render-resource and full scenario work.

### Reflection compound hull adapter (2026-10-26)

- Added convert_definition_hulls in reach_convex_shape.py. It consumes every
  component of each concatenated definition, verifies all vector/plane spans,
  rejects unowned tails and retains per-component material/shape self-offsets.
- Reflection contains646 convex hulls across174 definitions (22/148/4 definitions,
  122/516/8 hulls across its three BSPs), up to29 components in one definition.
  All source plane/vector words match emitted big-endian payload words exactly.
  All materials resolve by name to stock H3 material coefficients.
- Two initial fixed1e-5 plane checks failed on original geometry. The subsequent
  half-ULP calculation did NOT explain all excursions: source hull construction
  has additional fitting error. No geometry was repaired or tolerance silently
  increased. Audit records original containment/quantization residuals separately
  and proves exact source/native geometry equality as the conversion invariant.
  Do not report ideal mathematical plane containment as passing.
- Native comparison audit found Sandbox sand_wall_halfdoor uses one fixed body,
  a list shape and three polyhedron children. Added reach_compound_hull.py using
  that exact structure, with dynamic child/material counts, preserved component
  geometry and outward-rounded aggregate bounds. One compound body per source
  definition avoids multiplying scenario objects for each hull component.
- audit-reflection-convex.py --stage builds all174 physics roots in memory and
  reads back646 component shapes, all concatenated arrays, child indices/counts,
  and native list counts. No test map or duplicate runtime is emitted. Single
  hulls use the unchanged existing adapter. Reports: reflection-convex-audit.json
  and native-compound-physics.json. Compound Havok runtime acceptance is NOT yet
  verified; object linkage, authored transformed placements, BSP masks, MOPP
  bindings and complete Reflection integration remain next steps.

### Reflection compound object/placement linkage (2026-10-26)

- Added stage_compound_hull_object sharing the existing stock collision-only
  model/object wrapper. No separate object is created per hull component.
- Added reach_instance_pose.py using the retained TagTool
  MapVariantGenerator.Vectors3dFromEulerAngles convention. Source matrices are
  checked for finite proper rotations, projected to the closest rotation to
  remove float32 nonorthogonality near gimbal poles, inverted with atan2, packed
  to float32 angles and compared back to the ORIGINAL authored basis. All455
  placements pass; max basis error7.152557373046875e-7. No shear/reflection accepted.
- Extended append_hull_placements to preserve scale, Euler orientation and
  per-placement BSP selection (both manual and compiled attach masks, plus origin
  BSP). Existing High Noon callers retain BSP0/default behavior. Calls remain
  per-BSP so local definition/index identifiers cannot collide across resources.
- prepare-reflection-hull-placements.py verifies455 single convex-child wrappers
  and their source hull arrays. Reach child bounds are scale-applied local bounds;
  every component vertex after authored uniform scale is enclosed. This is
  distinct from the unscaled definition shape used in the native object.
- stage-reflection-hull-objects.py stages174 objects and455 placements across all
  three BSPs in one in-memory builder:836,768 bytes of metadata. Checks object
  palette links, unique IDs across BSPs, both masks, originBSP, position, scale,
  reconstructed orientation and unchanged stock donor metadata. Output report:
  reflection-hull-object-stage.json. No cache/second executable was emitted.
- Existing High Noon hull staging regression passes13 objects/14 placements.
  Native Havok behavior remains unverified for the new compound/rotated/scaled
  cases; this is not a complete Reflection build. Continue full physics/MOPP,
  rendering/material and scenario assembly before claiming gameplay success.

### Reflection environment physics integration (2026-10-26)

Source: Bungie's Reflection, direct MCC Reach `52_ivory_tower.map`; no upstream
H3 custom port is used. This project's Xbox 360 adaptation remains unfinished.

- `rebuild-reflection-instance-mopps.py` compiled eight missing definition trees
  for nine geometry placements without altering their collision polygons.
  `stage-reflection-collision.py` now inserts those trees, verifies their hashes,
  and reads back native code and quantization info from all three resources.
- `audit-reflection-environment-keys.py` checks the three source environment
  trees against their actual per-BSP placements. Classes8–12 share a surface
  subset, disjoint from class13, matching the established Forge World scheme.
  Four absent surfaces (two each in BSP1/2) explicitly carry source Invalid
  flag16; the conversion accepts only that declared exclusion, not arbitrary
  missing surfaces. Seven direct keys in BSP0 reference confirmed convex
  replacements. Both direct and stitched convex keys are removed only when
  an explicit replacement obligation exists.
- Native environment trees contain810/25,978/12,505 terminals and occupy
  33,148/595,936/259,683 bytes. Terminal keys survive conversion/read-back with
  expected multiplicities. Source spatial branch structure is relocated;
  spatial/runtime behavior has not yet been tested in the game.
- Generated trees and reports remain under `work/map-conversion-batch/reach-preflight`.
  No installed map or executable changed. Complete scenario/resource linkage,
  water/render conversion and native visual/gameplay validation remain required.

### Reflection placed-geometry MOPP binding (2026-10-26)

Added `reach_instance_physics.bind_geometry_physics` and integrated it into
`stage-reflection-collision.py`. Each serialized geometry wrapper now checks
its actual native definition/MOPP lookup, code bytes and quantization info.
Existing source wrapper cached code signatures must match their source
collision definition; rebuilt trees are allowed only for previously reviewed
missing-MOPP definitions. Runtime pointers remain zero. Placement indices and
BSP identities must be preserved when the final BSP metadata is assembled.

All98 Reflection geometry placements pass:89 retained source trees and9
placements using8 rebuilt trees. This verifies resource association, not native
physics execution. The complete map's render/water/scenario assembly and
in-game acceptance remain outstanding. No installed files changed.

### Reflection water-depth evidence (2026-10-26)

`measure-reflection-water-depth.py` now measures downward intersections from
actual water mesh vertices against source main collision plus transformed,
physics-bearing instanced collision. Water positions and geometry are unchanged.
This is diagnostic data, not a fabricated native water parameter stream.

- Mesh198:229 distinct geometry vertices;214 have a lower collision hit,
  measured depth0.004453–0.719727 map units;15 have no hit.
- Mesh218:50 vertices;36 have a lower hit, depth0.044602–0.151254;14 have no hit.
- Source water-index/UV counts differ from distinct geometry vertices; any final
  local-info reconstruction must retain per-corner geometry associations rather
  than assume a one-to-one UV index/depth mapping.
- No-hit vertices remain unresolved. Do not fill them with TagTool's placeholder
  local-info values or claim these measurements reproduce Reach shader behavior.
  Compare visible floor geometry next, since collision need not describe every
  decorative surface. Shader adaptation remains required: installed H3 water
  templates use displacement-wave shading; Reflection uses animated bump waves.
  Retained `work/sanctuary/water_shading.fx` explicitly distinguishes those pixel
  paths, so zeroing displacement alone would not preserve source bump shading.

### Reflection native water render candidate (2026-10-26)

Extended the depth diagnostic with signed nearest collision distances and a
separate world-render triangle query. The29 no-lower-hit vertices have collision
surfaces above them; world-render queries do not resolve those missing depths.
This alone does not prove every such vertex is visually occluded.

Added `reach_water_buffers.rebuild_water_buffers` and explicit water-buffer
support in the Reach render resource converter. It preserves authored triangle
vertex indices and UVs, gives each corner its own native parameter entry (so
shared UV indices cannot merge different depths), and requires complete supplied
depths. It supplies no default depths. Geometric displacement scale is zero to
preserve the authored non-displaced surface; a native H3 animated water material
is still required under the stock-H3-equivalent policy.

`stage-reflection-water-render.py` successfully assembles the whole water-bearing
BSP render resource:42,848 control bytes and6,476,424 GPU bytes. Both water meshes
(708 and138 corners) pass native descriptor/payload read-back. Existing unused
format26 triangle buffers are endian-converted, while MCC expanded format28
buffers become native triangle-pair buffers.

The stage script explicitly uses zero-depth *candidate* values for the29 vertices
with no lower collision hit and a surface above them. These values are not
recovered Reach authoring data and require native visual acceptance. Its report
lists every affected mesh/vertex. Shader adaptation, mesh metadata (including
large-mesh splitting), full cache assembly and in-game validation remain open.
No installed files changed; this is not a completed Reflection map.

### Reflection draw-range and collision-reference limits (2026-10-26)

Added an explicit draw-range relocation candidate: moving opaque part3 to the
end preserves all51 part/subpart identities, all original triangle sequences,
and both water offsets while fitting native start/count fields. Extended the
mesh serializer for verified water tables and the known water specialized type.
The water-bearing BSP's220 meshes/580 parts/625 subparts now serialize and its
relocated index buffer/metadata pass read-back checks in the diagnostic stage.

**This candidate is NOT sufficient for the full map.** The subsequent cache-file
surface-mapping audit finds cluster2 has more distinct triangle-end references
than the21845-triangle capacity of H3's ushort end-index field. These references
are index-buffer end offsets, not triangle ordinals (retained TagTool
GenerateStructureSurfaces convention). Index relocation alone cannot cure that
capacity limit. `reflection-mesh-relocation.json` records the exact distinct count
and marks sufficient_for_full_map=false. A mesh/cluster split with corresponding
collision-reference and visibility updates remains necessary. Do not deploy the
relocation-only candidate or drop mappings to claim compatibility. Other serialized
metadata flags/lighting policies and native water shader adaptation also remain
explicit open work. No installed files changed.

### Reflection spatial cluster split candidate (2026-10-26)

`plan-reflection-cluster-split.py` verifies the actual cluster table: cluster2
owns mesh198. It searches spatial planes using original world-vertex positions,
rejects cuts that duplicate water or nonstandard/transparent triangle draws,
and bounds each resulting mesh by H3's triangle-end-index capacity.

The chosen source-X plane is -32.93963623046875. It yields8667 and19458 triangles,
with302 opaque boundary triangles retained in both sets. No original triangle
is changed or lost; no water/transparent triangle is duplicated. All27465 source
collision references remap to the exact same vertex triples within ushort end
indices. This is a conservative triangle partition, not terrain simplification.

`reach_mesh_split.select_triangle_ranges` builds each side's actual index ranges
and part/subpart records while preserving material and source draw identities.
Native serialization succeeds:38/48 parts and subparts,52,002/116,748 index bytes,
and912/1,152 bytes of part/subpart metadata. Source counts/budget vertex bounds
are retained conservatively. The candidate report lists the selected source
triangle indices so portal/visibility/lighting work can use this exact partition.

Still required: split cluster bounds and portal connectivity, classify collision
leaves, update visibility/decorator/lightmap dependencies and integrate both meshes
and collision mappings into a complete cache. No native runtime acceptance or
installation is claimed. The earlier relocation-only route remains insufficient.

### Reflection split portals and leaf classification (2026-10-26)

`reach_cluster_portals` clips the original parent cluster's portals by the chosen
plane, preserving their orientation, flags and external neighbors. Two portals
are divided; adding the internal connection changes34 portals to37 and24 clusters
to25. The internal portal conservatively spans the original cluster bounds.
`stage-reflection-portals.py` verifies polygon area conservation and graph
contraction back to the original external connections, then serializes3,568 bytes
of native portal records/vertices. This is offline evidence; visibility and audio
behavior still require integration/runtime review.

`reach_cluster_leaves` adds a spatial branch to each original leaf classified in
cluster2, retaining each leaf's exact collision references on both sides. The
native plane index6209 is shared with the new internal portal. It adds8,384 nodes
and leaves, without altering collision surfaces. The new resource contains29,308
nodes,6,210 planes and18,078 leaves. `stage-reflection-leaf-split.py` verifies21,320
positions against the original expanded tree: collision leaf identity/content
matches after aliasing, and4,439 sampled positions select the new cluster.

The collision assembler now accepts an explicit main-geometry override.
`stage-reflection-collision.py` installs the verified split tree/leaf arrays and
reads the resulting arrays back, retaining all98 geometry MOPP binding checks.
The water-bearing BSP's raw collision resource grows from3,350,240 to3,484,400
bytes (134,160 bytes). The matching18,078-byte leaf-cluster table must be installed
alongside it; the stage report records that obligation and its hash.

Remaining: visibility/lighting/decorator dependencies, final cluster metadata,
water shader adaptation and complete cache/native acceptance. Nothing deployed.
Primary structure reference: TheGuardians/TagTool, commit
ce2dc6ac13072b160752af618ea1dc143e2727ac,
TagTool/Tags/Definitions/ScenarioStructureBsp.cs; retained Reach/H3 plugin schemas
supply the checked concrete cache offsets.

### Reflection split lighting bindings (2026-10-26)

`convert_lighting_tables` now accepts an explicit output-to-source cluster map,
rejecting absent references and lost source bindings. The water-render stage
checks Reflection's24 original bindings plus appended cluster24 mapped to source2.
The original bindings,358 static rows and1,131 instance rows remain byte-identical;
only a four-byte cluster binding is added. Invalid remaps are rejected.

Source cluster2 uses lightmap image0 and no static per-vertex SH buffer. Its
lightmap-coordinate buffer317 has43,360 vertices. The two planned mesh halves
reference14,391 and29,514 distinct original vertex indices respectively; all fit
that same converted coordinate buffer. This preserves the original coordinate
indexing rather than generating lighting or duplicating the atlas. Evidence:
`work/map-conversion-batch/reach-preflight/reflection-split-lighting-stage.json`.

This is a binding-stage check, not completed lighting or mesh integration.
Lightmap image conversion, split mesh emission, visibility dependencies, native
water material and full-cache runtime acceptance remain. No installed map changed.
Source remains Bungie's Reflection from MCC Halo Reach, with no upstream custom
H3 conversion author; this project's adaptation is separate.

### Reflection split render resource and mesh records (2026-10-26)

The Reach resource converter now supports resized triangle-list replacements and
appended index buffers. Reflection's spatial subsets read back exactly in slots196
and220 (8,667/19,458 triangles). All geometry, lightmap-coordinate, lighting and
water-parameter buffers retain their previous bytes. GPU payload grows1,828 bytes
to6,478,252; control size is42,884 bytes. No full geometry buffer duplication.

`reach_split_mesh_metadata` emits the two native mesh records at198/220, retaining
vertex IDs and source material/subpart identities. Water parts cross the split
as noncontiguous triangle subsets even though no water triangle is duplicated.
Their corner-pair stream is therefore reordered, retaining each original
geometry/parameter pair exactly once; per-part start offsets follow that order.
The depth/UV parameter stream remains unchanged. Stage checks pass for221 mesh
records and every emitted draw range.

An unresolved dependency was exposed: source secondary index slot197 contains
2,832 bytes entirely0xCD (ushort0xCDCD). It appears to be runtime water scratch
storage, not authored topology; runtime ownership/use has NOT been established.
Offline records retain that reference explicitly, with
`secondary_runtime_ownership_verified=false` and `mesh_metadata_integrated=false`.
Do not deploy these records until scratch allocation/sharing is resolved from
engine/reference evidence. Visibility, cluster/collision integration, lightmap
images, water material and runtime acceptance also remain. Report:
`work/map-conversion-batch/reach-preflight/reflection-split-render-stage.json`.

### Reflection secondary water allocation resolved against disc maps (2026-10-26)

Read-only audit of23 water meshes in original360 Zanzibar, Riverworld, Docks and
Deadlock finds the same invariant in every case: one independently owned secondary
index buffer per mesh, triangle-list primitive, all0xCD allocation contents, and
four bytes per authored water corner. This supplies a direct native format oracle;
the0xCD words must not be interpreted as authored vertex references.

Reflection's split now uses separate secondary slots197 and221. Each retains
the original2,832-byte capacity because the split meshes currently share offsets
into one reordered corner stream. This conservative capacity retains the original
address range instead of assuming runtime writes are rebased. Read-back verifies
both fills and disjoint GPU byte ranges. Vertex/lighting/depth/UV data remain
unchanged. Total staged GPU payload6,481,088 bytes (+4,664 versus relocation-only
candidate, including alignment); control42,920 bytes. Native water behavior remains
unverified, but sharing the secondary destination is no longer an integration risk.

Evidence and reproduction: `audit-native-water-secondary.py`,
`native-water-secondary-audit.json`, and `stage-reflection-water-render.py` under
`work/map-conversion-batch/reach-preflight`. This supersedes the earlier shared
secondary-binding candidate. No deployed map or runtime executable changed.

### Reflection split surface mappings serialized (2026-10-26)

`convert_surface_mappings` and `CollisionSections.mappings` now accept an explicit
cluster triangle-destination table. A split-cluster reference without a destination
fails rather than retaining an oversized index. Other clusters keep their exact
references; existing callers use the unchanged default behavior.

The Reflection water-render stage now builds the source-cluster2 destinations
from the actual source triangle centroid and the established split plane, using
the same per-side triangle ordering as the emitted index buffers. It serializes
the native mapping sections with resource fixups and reads back all35,078
references. All27,465 affected references resolve to the exact original ordered
vertex triples. The remaining references and all19,311 surface start/count spans
are unchanged. Section storage:40 control bytes,217,560 raw bytes,two fixups.

Evidence: `reflection-split-surface-mappings.json` under the Reach preflight
directory. These are completed mapping sections, not the full placement resource;
pathfinding/seam/instance integration and full-map native validation remain.
No map was deployed. Source: Bungie's Reflection, MCC Halo Reach; no upstream
custom H3 conversion author.

### Reflection native BSP surface/seam destinations (2026-10-26)

Original360 H3 stores edge/seam pairs, surface spans and surface/triangle mappings
in sbsp metadata at0x18,0x54 and0x60, respectively. The earlier mapping resource
section stage is useful read-back evidence, but is not the correct final retail
destination. `reach_bsp_metadata_sections.surface_sections` now converts all three
arrays directly for those native metadata fields; `install_surface_sections`
populates caller-owned roots and rejects competing arrays.

All three Reflection cache-file resources have zero pathfinding records, so no
pathfinding conversion or omission is necessary. Nonempty pathfinding fails
explicitly. The native metadata destination/read-back check preserves every seam
pair, with edge/surface/reference counts respectively:
- BSP0:1,164 /674 /453;9,164 payload bytes.
- BSP1:36,667 /19,311 /35,078;364,224 payload bytes, including split remapping.
- BSP2:9,488 /4,927 /8,726;92,564 payload bytes.

The stage uses a root envelope to verify these fields and pointers; it does not
claim a completed BSP root. Other cluster/visibility/physics fields remain to be
assembled. Evidence: `reflection-bsp-surface-sections.json`; checked native layout
sources: retained retail `reference/plugins/sbsp.xml` and `bsp_metadata.py`.
No installation changed.

### Reflection cluster dependencies and cubemap positions (2026-10-26)

Checked the actual cluster structures against TagTool's pinned
ScenarioStructureBsp.cs (ce2dc6ac13072b160752af618ea1dc143e2727ac); a read-only
cluster excerpt is retained in reach-preflight/TagTool-Cluster-reference.cs.
Reflection has1/24/2 clusters across its three BSPs. Cheap-light references and
PVS object identifier/reference arrays are empty, but this does NOT establish
that scenario-wide PVS is empty or that visibility integration is complete.

The split source cluster2 has103 decorator groups,31 cubemaps,two seam indices,
six runtime decals and cluster MOPP index0. Whole-record duplication would be
incorrect. MCC decorator groups carry nonempty model-start arrays, so these need
semantic conversion/partitioning, not truncation to the shorter H3 structure.
Cluster physics MOPP references remain an integration obligation.

All55 cubemaps in BSP1 have exactly one Reach reference point.
`reach_cluster_cubemaps.convert_cluster_cubemaps` now writes H3's inline position
and two short indices, preserving positions exactly and accepting an explicit
scenario/bitmap index remapper. All55 native records pass source-value read-back.
Multiple/empty reference-point arrays fail explicitly instead of inventing a
position. Scenario/bitmap indices are not yet remapped or installed.

Evidence: `reflection-cluster-dependencies.json`, generated by
`audit-reflection-cluster-dependencies.py`. Source map remains Bungie's Reflection
from MCC Halo Reach; this is this project's native adaptation, not an upstream
H3 custom port. No installed map changed.

### Reflection decorator group partition and encoding check (2026-10-26)

The decorator resource at BSP+0x314 contains eight format20/stride16 TinyPosition
buffers. Existing `bsp_metadata.decorator_group` documents the MCC model-start
table check: each vertex selector must equal bisect_right(model starts,index).
Reflection's109 groups/6,695 placements pass that exact check, so those model
boundaries are redundant draw metadata, not lost authored model selection.

`reach_decorators.convert_group` emits native48-byte group records and splits
consecutive instance runs by decoded position relative to the established plane.
It preserves source vertex offsets and conservative group bounds, without copying
vertices. The candidate has137 groups and assigns every placement exactly once.
This metadata stage does not establish full decorator conversion.

The existing native TinyPosition converter rejects orientation byte255 in49
referenced vertices (zero unreferenced affected vertices). This is real authored
data, not unused padding. Do not clamp or discard it without establishing the
Reach MCC orientation encoding. Resource conversion remains incomplete and the
stage explicitly reports `native_vertices_verified=false`. Evidence:
`stage-reflection-decorators.py` and `reflection-decorator-stage.json`.

### Reflection decorator orientation endpoint resolved (2026-10-26)

Pinned TagTool VertexStreamFactory selects VertexStreamHalo3RetailMCC for MCC
Reach. ReadTinyNormal decodes reversed bytes as b/127-1, and the native
VertexElementStream.NormalizeSByte clamps before encoding. The earlier rejection
of byte255 was overly strict: its proper signed endpoint is+127, not wrapped-128.
`render_buffers.convert_vertices` now handles that endpoint. Exhaustive byte-domain
verification checks all256 inputs and confirms0..254 are unchanged.

Reflection's decorator resource now converts successfully: eight buffers,
107,120 GPU bytes, SHA256
87d476108ab154ee22f1d336a6d89e2cba0e50733bd7011fcff8a1795e8718ec.
Every referenced placement passes position/model-selector, orientation and color
read-back; all6,695 placements remain assigned exactly once across137 native
groups. The49 endpoint-affected placements are retained. The earlier orientation
failure is resolved; palette assets, complete cluster integration and native
rendered acceptance remain open. No installation changed.

Primary references: TheGuardians/TagTool commit
ce2dc6ac13072b160752af618ea1dc143e2727ac,
TagTool/Geometry/RenderGeometry/VertexBuffer/VertexStreamFactory.cs and
VertexElementStream.cs; retained MCC reader and decorator-orientation-reference.md.

### Reflection split scenario PVS (2026-10-26)

`audit-reflection-pvs.py` reads the actual scenario zone set: mask7,version11,
flags0, BSP cluster counts1/24/2. Open/closed visibility matrices contain one
target vector per BSP; every vector is one dword. Portal/device arrays are empty.
The scenario does have seam-cluster mappings; empty per-cluster PVS object lists
must not be mistaken for an empty scenario PVS.

`reach_pvs_split.split_zone` extends authored visibility conservatively: append
cluster24 as an alias of source cluster2, both as an observer row and a target bit
in every relevant BSP row. Existing visibility restrictions are preserved, not
replaced with an all-visible mask. Sky/audio rows and Reach seam references are
extended consistently in the intermediate representation. Sparse BSP masks and
unexpected widths/padding fail explicitly.

`stage-reflection-pvs.py` serializes the common native nested matrix layout and
reads it back, checking all1,568 observer/target visibility relations for both
open/closed matrices against the corresponding original relation. Counts are now
1/25/2. Reach-to-H3 zone seam mapping format, native PVS version/checksum handling,
scenario installation and runtime acceptance remain incomplete. Reports:
reflection-source-pvs.json,reflection-split-pvs.json,reflection-split-pvs-stage.json.
No map deployed. Source remains Bungie's Reflection (MCC Halo Reach).

### Original-disc PVS writer validation (2026-10-26)

The earlier version/flags description needs qualification: the complete32-bit
word is11 in Reach and8 in all24 installed original H3 scenarios. Treating the
native word as independent big-endian shorts produces version0/flags8. Preserve
the observed native word explicitly, rather than copying the Reach half-fields.
ManagedDonkey scenario_definitions.hpp also describes this field as int32 version.

`native_zone_pvs.serialize_zone` now writes the complete44-byte native zone and
84-byte BSP records, nested visibility matrices, sky indices, multiple-sky/audio
bitvectors, checksum words and native single-byte cluster mapping lists. It
rejects unconverted Reach mappings/version values. Empty device-portal rows are
preserved as native24-byte records; nonempty associations remain unsupported.

`verify-native-pvs.py` reads actual original-disc data, serializes it to a new
address space, reads it back and compares every parsed field.23 maps pass,
including nonempty native cluster mapping lists in descent/shrine. Deadlock's
one nonempty device association is explicitly excluded and recorded, not treated
as a passing test. Report: native-pvs-roundtrip.json. All donors are single-BSP;
this does not prove Reflection's multi-BSP seam translation. That translation,
checksum policy, integration and runtime verification still remain. No deployed
map or executable changed.

### Reflection mapping semantics and atlas conversion follow-up (2026-10-26)

`audit-native-seam-links.py` disproves equating native PVS cluster-mapping lists
with physical BSP seam lists: descent and shrine have nonempty PVS mappings but
zero seam identifiers and zero cluster seam indices. Those mapping lengths also
do not equal cluster portal counts. Preserve the distinction; the TagTool field
name alone does not establish how Reach root/attached/connected lists translate.
Report: native-seam-links.json. Engine-consumer semantics remain unresolved.

`convert-reflection-lightmaps.py` now selects every atlas by actual scenario BSP
binding and invokes the existing reference VMF-to-SH converter, then native Xenos
tiling/read-back and bitmap-resource validation. It retains only validated native
resources, removing the exact reproducible input and compressed intermediates.
The shared PowerShell compiler now explicitly references System.Console.dll,
required by the bridge's existing progress callback. This is a build-reference
fix, not a lighting equation change. Final results are recorded in
reflection-lightmaps-stage.json only after all BSPs finish. No runtime acceptance
or map deployment is implied by successful atlas conversion.

The Reflection atlas run completed successfully: BSP0 has a256x256 atlas and
BSP1 a1792x1792 atlas; BSP2 is the authored lighting placeholder. All20 output
texture layers pass native tiling round-trip and bitmap/control/hash validation.
Total native texture payload is32,768,000 bytes (31.25MiB). This is the lighting
texture allocation alone, not a claim about whole-map console memory. Input
BC5/BC3 and duplicate linear compressed intermediates were removed after
validation. Main-atlas native SHA256 values:
- linear SH: dccd817b3f6dc540111488cfc55d63b5bbd5eb27d0253ff4437dd4f4bee02e58
- dominant intensity: b08763a62da3e4431a8872fbb850a5de3de57246f1e40869b120e22504202cb6

Both atlas pairs retain the reference conversion's per-coefficient scales and
source brightness. Lighting-tag integration and native visual verification remain
unfinished. Source: Bungie's Reflection, direct MCC Halo Reach cache; no upstream
H3 custom-port author applies.

### Reflection native atlas registration (2026-10-26)

`reach_lightmap_output.install_native_lightmap_atlas` now installs both registered
bitmap references and all nine native coefficient-scale records into the
original0x1B4-byte BSP lighting structure. It rejects populated atlas fields and
preserves the header, geometry and all probe/binding fields owned by the enclosing
importer. It does not claim to convert those other fields.

`stage-reflection-atlas-registration.py` exercises the production MapBuilder,
CacheRegistry and MaterialImporter.bitmap_resource paths on a read-only stock
Cold Storage basis, with the original executable's resource salt. Both atlas
pairs register successfully. Read-back verifies bitmap tag salts/groups, image
records, resource ownership, control blocks and complete decompression of all four
resource pages against the validated native texture bytes. Native payload totals
32,768,000 bytes; compressed staging occupies14,432,828 bytes including alignment.
The check is entirely in memory except its small JSON report; no duplicate cache
or deployment is created. Report: reflection-atlas-registration.json.

Full lighting records remain incomplete: source instance probes/analytical fields,
geometry binding, root probe tables and scenario integration must be handled
before runtime verification. The atlas installer alone is not a playable map.

### Reflection instance probe conversion (2026-10-26)

`reach_instance_probes` reads all authored36-byte Reach instance probes, validates
placement-to-probe indices, and validates the existing reference bridge's native
72-byte output while preserving row identity/order. Conversion uses pinned
TagTool VmfConversion.ConvertHalfLightprobe, not an approximate replacement.
`convert-reflection-instance-probes.py` stages918 probes for BSP0 (1,309 instance
lighting rows) and623 for BSP1 (1,131 rows). Every probe is referenced; all
placement references are in bounds. BSP2's source placeholder has no probes.
All1,541 native records have finite half coefficients and zero native padding.
Native probe payload totals110,952 bytes. Source/converted JSON intermediates
are removed after successful validation; compact native binaries and the binding
report remain.

The source analytical-light values are retained explicitly in
reflection-instance-probes-stage.json, including per-instance values. Probe
values are0 or4290703104; their native adaptation is not resolved merely by
converting the VMF coefficients. Do not silently drop them or mark the complete
lighting tag ready. Native BSP0 probe SHA256:
b6d3fb3b2a94dcfd4749ffa6170fb2f5e2d60d88f62ff32b08926640351574c9;
BSP1:563c652d51c9bf5178477f8eea67a4e6c8e097b7f153364bdcf9aada79de0baf.
Scenario integration and rendered verification remain open. Source remains
Bungie's Reflection from MCC Halo Reach, without an upstream H3 custom port.

### Reflection analytical-light interpretation lead (2026-10-26)

Primary implementation research found a consumer-oriented interpretation in
KyleThmpsn/sundial commit3f180dfbbe77101c77383c62eedb30e01bfdbccb,
crates/parhelion-import/src/halo_reach/level/lighting.rs:
https://github.com/KyleThmpsn/sundial/blob/3f180dfbbe77101c77383c62eedb30e01bfdbccb/crates/parhelion-import/src/halo_reach/level/lighting.rs
It identifies0xFFBEEF00 as sky selection and0 as disabled analytical intensity;
this is separate from baked VMF coefficients. This is an implementation reference,
not our independent verification of the original MCC consumer.

`audit-reflection-analytical.py` resolves the actual source sky chain, with no
invented fallback. Reflection has one sky, sky_bright_hazy. Its render-model
direction is(0.5566700101,0.6634100080,0.5), length0.99999717, and intensity is
(2.364706278,3.0,2.800000429). Probe IDs divide into928 zero and613 sky-selected;
instance lighting rows into1,391 zero and1,049 sky-selected. No other identifier
is present. Evidence: reflection-analytical-audit.json. These values must not be
classified as unused padding or silently dropped. Native H3 adaptation still
needs to preserve the selection distinction.

Pinned TagTool PortingContextGen3.Lighting.cs converts Reach instance/air/scenery
probes using ConvertHalfLightprobe but explicitly notes outstanding probe issues;
that path alone does not establish correct analytical-light adaptation or rendered
acceptance. This qualifies the earlier coefficient-conversion stage: successful
finite output establishes structural validity, not complete visual fidelity.

### Reflection BSP-local environment probes (2026-10-26)

Pinned TagTool's runtime schema enumeration confirms MCC Reach Lbsp fields:
Airprobes+0x12C, SceneryLightProbes+0x138, MachineLightProbes+0x144. Reflection's
root sLdT air/scenery/machine tables are empty; these local records therefore
must be moved into the original H3 root tables, not discarded as duplicate caches.
BSP0/BSP2 have none. BSP1 contains40 air probes,223 scenery probes and one machine
with one nested probe.

`convert-reflection-environment-probes.py` converts all264 using the existing
reference bridge. It preserves source identity/order and analytical selection,
serializes native92-byte air,80-byte scenery and84-byte machine probe records,
and retains the machine's object ID/bounds prefix separately for later pointer
allocation. Native payload is21,604 bytes excluding that32-byte machine prefix.
Source prefix numeric values are endian-converted, not byte-swapped wholesale.
Destination string/object ID remapping, native root allocation, analytical-light
adaptation and runtime acceptance remain open. Report:
reflection-environment-probes-stage.json. Duplicate JSON intermediates are removed
only after successful validation; original cache remains read-only.

### Reflection root environment-probe layout (2026-10-26)

`reach_environment_probes.install_environment_probes` links validated converted
payloads into original H3 sLdT root offsets0x28/0x34/0x40, including machine child
probe allocations. Caller-supplied prefix remapping is mandatory for airprobe
string/BSP fields and scenario object identifiers. Payload hashes, widths and
analytical-selection counts are validated before allocation. Unrelated root
fields are preserved. Analytical selections are returned for the enclosing
lighting adapter, not silently interpreted as native fields.

`stage-reflection-environment-root.py` reads back all40 air/223 scenery/one machine
records and its nested probe from the new native pointer layout and compares them
to the converted source payloads. Total staging metadata21,764 bytes including
root/alignment. Identity remappers are deliberately used only in this in-memory
layout check: destination object/string remapping and complete scenario integration
remain unverified. No runnable cache is written or deployed. Evidence:
reflection-environment-root-stage.json.

### Reflection probe identifier binding (2026-10-26)

`bind-reflection-probe-identifiers.py` now uses real StringTable and
WritableStringTable instances against a read-only stock Cold Storage basis.
All40 airprobe names resolve and remap by text;13 native strings are appended
in the in-memory builder, with name round-trip verification. Probe BSP flags
remain explicitly unresolved (all source flags words are65535).

Source object checks caught a scenario-schema mismatch: TagTool's HaloReach/MCC
enumeration suggests scenery+0x11C/machines+0x1A0, but those blocks are empty in
this cache. The retained reach-scnr.xml offsets+0xFC/+0x180 contain258 scenery
placements and one machine with the expected identifiers. Use actual-cache
evidence rather than blindly applying the reference library's version layout.
This finding concerns scenario root offsets, not the independently checked Lbsp
probe table offsets.

Of224 scenery/machine probe-owner records,223 match the source scenario exactly.
One identifier,f5a4017b00010601, has no matching unique ID in those placement
tables. It is retained and explicitly reported as unresolved, not silently
deleted or bound to another object. Report:reflection-probe-identifiers.json.
No destination scenario is installed; actual placement preservation, the unmatched
owner, airprobe BSP-flag adaptation and analytical lighting remain open.

### Reflection native lighting-table linkage (2026-10-26)

The later airprobe audit corrects the prefix to three floats, one uint32 name
and two uint16 fields, rather than two uint32 fields. Local all-BSP sentinel
probes are assigned their owning BSP bit when moved to the root (BSP1: mask2).
The unmatched scenery identifier occurs only in its probe record in the entire
source cache; it is preserved as a source orphan, without inventing a placement.
These supersede the unresolved prefix/orphan findings above. Runtime behavior
and actual destination placement integration remain unverified.

`reach_lighting.install_lighting_tables` now allocates the native per-vertex,
cluster, instance and instance-probe tables at BSP lighting offsets
0x100/0x10C/0x118/0x124. It checks sizes, references and probe encoding before
allocation, preserves unrelated fields, and returns analytical selections for
separate adaptation. This joins previously separate converted table payloads
to the native BSP lighting record; it does not complete the lightmap importer.

The Reflection water/render integration check now installs the real split main
BSP lighting tables and converted probes and reads every allocated table back.
Evidence: work/map-conversion-batch/reach-preflight/
reflection-lighting-table-installation.json. Analytical-light adaptation,
complete BSP/scenario integration and native rendered acceptance remain open.
No executable or installed map was changed.

### Reflection auxiliary geometry linkage (2026-10-26)

`reach_geometry_tables.install_geometry_tables` carries compression bounds,
transparent sorting spheres, PRT user descriptors and per-instance lightmap
coordinate references into native H3 BSP lighting records. Layout references:
TagTool ce2dc6ac, Geometry/RenderGeometry/RenderGeometry.cs and
RenderGeometryCompression.cs, alongside the retained cache plugins.
Reach's two trailing compression floats are padding and are zero in Reflection.
The 64 user descriptors reference one identical PRT payload; the writer shares
that allocation. Native coordinate buffers are format4, stride4.

BSP0:193 compression records,1309 instance entries,13 coordinate-bound instances.
BSP1:196 compression records,11 sorting spheres,1131 instance entries,
172 coordinate-bound instances. Source index order is retained. The main water
integration check verifies all1131 destination coordinate references; BSP0's
check reads back its compression/sorting and all1309 coordinate entries.
Reports:reflection-geometry-tables.json and reflection-geometry-tables-bsp0.json
in the existing reach-preflight directory. Unsupported nonempty auxiliary
blocks fail explicitly. Main BSP's three Reach water bounds are returned for
separate adaptation, not silently dropped or claimed native-compatible.
This remains offline integration, not a deployed/playable Reflection cache.

### Reflection combined native geometry/lighting record (2026-10-26)

`reach_geometry_output.install_native_geometry` links mesh metadata and auxiliary
tables into a native lighting BSP and registers its converted geometry through
the existing CacheRegistry. Nested meshes use the same MapBuilder allocator;
resource ownership/salts/pages use the shared production path. Atlas and lighting
tables already in the record are preserved. Unmapped runtime flags fail.

`stage-reflection-native-lighting.py` joins BSP0's two atlas textures,918 instance
probes,1309 instance lighting entries and194 meshes in one record. It verifies
1117 nested mesh records reside within native allocations, validates the resource
owner/control, and decompresses the registered geometry page to compare every
byte with the converted12,609,678-byte payload. Metadata allocated:171,352 bytes.
Evidence:reflection-native-lighting-integration.json. No runnable cache is saved.

Header adaptation remains explicit: Reach's active Lbsp flags are0x147, including
surface-to-triangle mapping pruned and optimized-for-less-DP bits absent from the
native plugin. The integration check uses a header sentinel and does not silently
copy those bits or claim they are handled. Complete BSP/scenario integration,
analytical lighting, water adaptation and runtime acceptance remain outstanding.

### Reflection main-BSP native integration and header policy (2026-10-26)

The main water/render stage now also runs the shared MapBuilder/CacheRegistry
integration path: atlas textures,25 cluster lighting bindings,623 probes and221
meshes occupy one native lighting record/address space. Both split meshes' part
and subpart ranges are read back through actual native pointers, including the
distinct secondary water buffers. The registered geometry page decompresses to
the exact6,481,088-byte converted payload. Metadata used:159,708 bytes.
Evidence:reflection-native-main-lighting-integration.json.

`install_lightmap_header` validates source BSP index/checksum before writing the
native header. Pinned TagTool ScenarioLightmapBspData.ScenarioLightmapBspFlags
and both retained plugins agree bits0..4 are the H3 flags; Reach bits6 and8
describe source pruning/draw optimization. The rebuilt native output retains
flags7 and reports source-only build flags0x140 rather than encoding them as
native flags. Other Reach flags fail pending adaptation. Source checksums match
both active BSPs exactly. The caller supplies the destination structure checksum;
the current checks preserve source values, requiring the eventual BSP writer to
use matching values. Placeholder BSP2 is rejected by this active-lightmap path.
Both combined integration checks pass with real headers, superseding the earlier
header-sentinel limitation. Water bounds, analytical lighting, full scenario/BSP
integration and rendered gameplay remain unresolved; no deployment occurred.

### Reflection source water bounds accounted for (2026-10-26)

`reach_water_buffers.validate_water_bounds` now checks every source water part
against its Reach bounding record before rebuilding topology. Actual cache data
uses interleaved X min/max,Y min/max,Z min/max, despite the reference class's
two-point field naming. All three records (mesh198 parts0/1,mesh218 part0) match
their indexed visible vertices exactly in X/Y and expand Z by0.15 on each side
(float tolerance2e-5). There are no unaccounted water parts or extra surfaces.

Native H3 RenderGeometry has no equivalent water-box table. The source boxes
are retained in the integration report with their rendered bounds; native water
draw topology is preserved by the existing partition/permutation checks. This
accounts for the source metadata but does not prove runtime visibility or shader
equivalence. Unexpected bounds, missing/duplicate part ownership and resource
span errors fail. The combined main-BSP integration still passes. Evidence:
reflection-water-bounds-audit.json and reflection-native-main-lighting-integration.json.

### Reflection cluster MOPP conversion (2026-10-26)

The resource cache's root+48 contains13 cluster MOPPs:1/10/2 by BSP.
Cluster+0x42 references all of them, with-1 for clusters without one.
`reach_cluster_mopps` now converts their96-byte Reach headers to64-byte native
headers, allocates code with native pointers and checks that all reachable local
keys and multiplicities survive unchanged. All13 headers/code arrays read back
from the real MapBuilder. Total code:4105 bytes. Evidence:
reflection-cluster-mopp-audit.json and reflection-cluster-mopps-stage.json.

The keys are small local ranges, not global placement IDs: the main split
cluster's MOPP has62 terminals while its mesh has160 instance buckets containing
883 placements. Do not assume a direct placement mapping or synthesize keys from
the split geometry. The pinned TagTool BspPathfinding conversion copies the
referenced MOPP into the native cluster physics wrapper; its local lookup and
split-cluster handling still need verification before that wrapper is installed.
This change converts the source records but does not claim complete physics or
runtime acceptance. No map was deployed.

### Reflection native cluster collision lookup resolved (2026-10-26)

The original H3 executable resolves the ambiguity above. Collector vtable
0x82001f88 calls sub_820C0890, which forwards the hit key to sub_820C0B00.
That function directly indexes the BSP placement array at +436 with key*120,
then its definition array with definition*184. There is no group indirection.
Reach's cluster keys cannot be installed unchanged into this consumer.

The caller sub_8229C388 explicitly selects this MOPP path for BSP import
version >=3; for earlier versions it traverses cluster mesh instance buckets
and calls the SAME placement collision function with each global instance ID.
This is native game functionality, requiring no engine change. Pinned TagTool
PortingContextGen3.Bsp.cs independently selects import version 2 for Reach and
rebuilds its buckets from cluster groups.

Reflection already has authored buckets. The new reach_instance_buckets
validator checks their indices and matching placement mesh/definition against
all three source resources, and requires coverage of every cluster-group
placement. All 27 source clusters pass. Some main-BSP buckets include additional
authored instances (for example cluster 2 has 883 versus 881 grouped instances);
retain these rather than deleting them based on imposter-group membership.
Cluster group counts also match the previously observed local MOPP key ranges.

convert_bsp_geometry now runs this validation and returns the required native
import version 2 with its provenance. Final BSP assembly MUST set that version
and preserve the bucket records, including both children of the split mesh.
The old cluster-MOPP conversion remains inspection-only; do not install it.
The integrated BSP0 geometry/lightmap allocation check still passes. Evidence:
reflection-instance-bucket-lookup.json, h3-cluster-key-collector.txt, and
reflection-native-lighting-integration.json under the ignored preflight directory.
Full BSP assembly and runtime collision/performance remain unverified; this
does not claim Reflection is playable or deployed.

### Reflection BSP geometry and bucket linkage (2026-10-26)

The native allocator stages now install the verified geometry into the reserved
BSP owner itself: original sbsp+0x2e0 receives the same 0x84-byte geometry record
as lighting BSP+0x130, and sbsp+4 is set to import version 2. This shares the mesh
and resource references without a second geometry allocation. Both fields read
back from the actual MapBuilder tag address.

`reach_instance_buckets.install_native_bsp_geometry` traverses native bucket
pointers and compares every (mesh, definition, placement) reference, including
multiplicity, against validated source buckets. It requires coverage of all
source clusters. The main BSP supplies 25 destination bindings, including both
children of source cluster 2; each child preserves the original complete bucket
set. BSP0 verifies 1309 references. Both integrated allocation stages pass.

This installs only the BSP geometry and lookup selection. Cluster records,
placements/physics, other BSP fields, scenario integration and final runtime
acceptance are still separate work. The reports deliberately retain
full_bsp_installed=false and runtime_verified=false. No map was deployed.

### Reflection combined BSP collision/geometry assembly (2026-10-26)

`reach_bsp_metadata_sections.install_collision_resource` now registers the native
collision resource under its BSP owner and installs the matching leaf-cluster
array, original world bounds, checksum and native resource-use fields. It checks
the leaf array against the converted collision header's leaf count and rejects
invalid cluster IDs before allocation. All three Reflection resources passed
real registry/page and metadata readback: 676/18078/3091 leaves, with 1/25/2
clusters respectively. The main count includes the verified split.

Both active lighting/geometry stages now consume those collision assemblies
in memory and install them into the SAME native BSP as the render geometry.
They also install surface ranges, triangle mappings and edge/seam mappings;
the main BSP uses the remapped split triangle references. Checks confirm shared
tag ownership, matching BSP/lightmap checksums, intact leaves/surface arrays and
render geometry. Combined metadata allocations: BSP0 183156 bytes; main BSP
554760 bytes. No extra cache copies or binary staging files were introduced.

Evidence: reflection-collision-resources.json,
reflection-native-lighting-integration.json and
reflection-native-main-lighting-integration.json. These remain partial roots:
placement/physics records, cluster metadata, other scenario integration and
runtime verification are unfinished. Nothing was deployed.

### Reflection native placement records (2026-10-26)

Added explicit 156-byte Reach to 120-byte native placement serialization in
reach_bsp_instances. It preserves placement order, transforms, definition IDs,
the supported seam word and checksum; maps shared/per-vertex/probe lighting
policies; requires translated names, explicit coordinate slots, cubemap samples
and complete geometry/convex physics handoffs. It rejects missing physics
coverage rather than silently removing it. Reach-only placement flag bits are
reported separately; native fade overrides remain 0/0 (scenario/default fade applies).

Do not memcpy the source sphere tail: native +80 is the placement checksum,
while Reach has an additional float before its separate checksum at +120.
The original H3 plugin and Cold Storage records confirm +80 is not a useful
float (some values are tiny/huge bit interpretations). Native sphere center
and radius use the first four Reach sphere values.

The BSP0 combined stage now installs all 1309 native placement records into
its real BSP tag, translates their names through WritableStringTable, and
preserves all 13 per-instance lightmap-coordinate bindings. Every transform,
name and checksum reads back correctly. Its 118 convex-physics placements
remain explicit external-object handoffs; they are NOT yet installed in this
combined stage. BSP0 has no geometry-MOPP placement wrappers and no cubemap
samples. Combined metadata is 340248 bytes. Evidence:
reflection-native-lighting-integration.json. Main-BSP cubemap remapping and
placement integration remain; no map deployment/runtime claim.

### Reflection convex objects joined to BSP assembly (2026-10-26)

The existing hull-object stage now accepts a caller-owned registry/scenario and
selected BSPs. It checks each staged source placement against the current Reach
resource (all read fields), requires exact coverage of live convex-physics
placements, and retains its pose, BSP-mask, palette/object and unique-ID readback
checks. Borrowed builders remain open; no duplicate output cache is created.

The two combined active-BSP stages now use stock Sandbox as their allocation
basis so sand_wall/sand_wall_halfdoor fixed-body donors exist in the SAME cache.
Each creates a native scenario tag scaffold and appends its actual convex bodies:
BSP0: 22 object definitions / 118 placements; main BSP: 148 / 333. The sets match
the source physics handoffs exactly. BSP0's render placement records therefore
now have their external convex counterparts allocated in the same registry.
Metadata totals are 475056 and 1039312 bytes respectively. No on-disk cache copies
were added; these are in-memory assembly checks, not installed maps.

Evidence: the two reflection-native-*-lighting-integration.json reports. The
scenario scaffolds still need complete source scenario assembly, and the main
BSP placement records/cubemaps and remaining cluster metadata are unfinished.
Native Havok behavior remains unverified. The third BSP's four convex placements
remain covered by the standalone all-BSP hull stage, not this combined assembly.

### Reflection main placements and authored cubemaps (2026-10-26)

The main combined BSP now contains all 1131 native placements, 98 verified
geometry-MOPP wrappers, and their 333 external convex object counterparts.
Transforms, source checksums, translated names, coordinate slots, physics data
and cubemap sample indices read back from the native records.

The scenario's main BSP cubemap tag contains 51 images, each 32x32 ARGB with
6 mip levels. `import_cubemap_group` imports all images into ONE native bitmap
tag in source order, retaining all faces/mips and per-image resources. Native
tiled data totals 2506752 bytes. Instance samples retain their cached source
image index as a native single-image sample (same index in both slots, blend 0).
1126 main samples also resolve through their source cluster locator; the other
five contain all-zero locators but valid cached bitmap 0, which is preserved.
BSP2 has one sample referencing this main-BSP group; its later integration must
use the same image numbering rather than duplicate/reorder the group.

Main metadata is 1190688 bytes. Evidence:
reflection-native-main-lighting-integration.json. The imported bitmap group
still needs its final scenario BSP reference. Cluster metadata and full scenario
assembly remain incomplete, and no runtime rendering claim or deployment is made.
Clarification: native instance fade values 0/0 are zero overrides, not proof that
fading is disabled; native scenario/default thresholds still apply.

### Reflection native cluster/portal assembly (2026-10-26)

The main combined BSP now installs 25 native cluster records and 37 portals,
using the already verified split graph and bounds. Its 137 converted decorator
groups are attached to their correct cluster sides, with source seam bytes and
cubemap positions/indices retained. Native mesh bindings, bounds and portal
incidence read back correctly. Cheap-light/PVS/predicted-resource fields are
empty in this source; nonempty unhandled values are rejected.

The empty cluster physics header follows original armory.map (shape collection
type 2, reference count 128, null BSP reference, no MOPP shape). Collision uses
the verified native version-2 placement buckets. Source acoustics/environment
indices are preserved pending their destination tables; the report explicitly
marks them not remapped. Native-only sound/weather fields use stock defaults.

The buffer-only decorator geometry is also registered under the same BSP:
source metadata tables are all empty, so only its flags and native render
resource are needed. This adds 107120 raw bytes; its eight palette tags still
need import. Evidence: reflection-native-main-lighting-integration.json.
This remains incomplete assembly, with no runtime/deployment claim.

### Reflection decorator selector validation (2026-10-26)

Source remains Bungie's Reflection from MCC Reach `52_ivory_tower.map`,
not an upstream Halo 3 custom conversion. `reach_decorators.palette_usage`
now resolves the actual per-vertex model selectors against the source palette
and checks the model-start tables and buffer bounds. All 6695 placements pass:
orchid 174, yellow flowers 45, white flowers 437, grass 890, short grass 4880,
bamboo leaves 234, cedar 16, heather 19. Orchid, yellow flowers, grass and
bamboo reference selector 2; white flowers also reference selector 1.

The native palette installer retains palette order and selectors, validates
native tag salts/types and model counts, and rejects incomplete bindings or
an undersized donor instead of silently clamping/modulo-remapping selectors.
The staging check reads the installed palette bytes back using a real Valhalla
wildgrass tag, and proves that a real one-model flower donor is rejected for
the three-selector grass set without altering the BSP root. These are format
checks, not approval of either asset as Reflection's final donor.

Original-disc metadata inventory found 131 distinct decorator names, including
stock grass, flowers, leaves and shrubs. No exact Reflection palette names
were found. The resource-only shared.map is not readable as a normal tag cache;
this inventory does not claim shared resource payloads are absent. Donor visual
and selector compatibility still needs resolution. No foliage was dropped,
no runnable cache was written, and runtime visuals remain unverified.
Evidence: work/map-conversion-batch/reach-preflight/reflection-decorator-stage.json
and stock-decorator-inventory.json; repeat selector/installer check with
stage-reflection-decorators.py from the repository root.

### Reflection scenario cubemap table (2026-10-26)

The combined native main-BSP stage now installs the complete source scenario
cubemap table into its native scenario scaffold. MCC Reach U13's 0x7b8 table
contains 51 records of 32 bytes; native H3 uses 16-byte records at 0x788.
Field semantics were checked against TheGuardians/TagTool Scenario.cs,
ScenarioCubemapBlock, revision ce2dc6ac13072b160752af618ea1dc143e2727ac:
https://github.com/TheGuardians/TagTool/blob/ce2dc6ac13072b160752af618ea1dc143e2727ac/TagTool/Tags/Definitions/Scenario.cs

All 51 positions and resolutions read back from the native allocation exactly.
All 55 cluster memberships agree with source scenario sample positions and
reference-point indices. Only 36 distinct scenario entries are referenced by
clusters; retaining the full table preserves the other 15 and avoids renumbering
cached indices. Unsupported multiple reference points are rejected explicitly.
The complete staging check passed with 1209344 bytes of added metadata.
Evidence: reflection-native-main-lighting-integration.json, scenario_cubemaps.

The native bitmap group still needs its final scenario BSP reference; BSP,
material/environment and full scenario assembly remain incomplete. No runtime
validation or deployment is claimed. Original map/source author: Bungie,
Reflection from MCC Halo Reach; this project performs the native H3 adaptation.

### Reflection shared-cache assembly (2026-10-26)

The BSP0 and main-BSP stages can now borrow a single native registry, scenario,
string table and converted collision set. This removes their previous isolated
allocations: both geometry/lightmap/collision graphs and convex placements now
coexist in one in-memory cache. String staging happens once, after both stages,
so new names cannot reuse IDs assigned independently by the other stage.
The standalone stage entry points remain available.

`stage-reflection-combined.py` verifies 2440 instance names after both imports,
checks both BSP/lighting geometry links and checks all 451 collision-object IDs
and compiled BSP masks (118 BSP0, 333 BSP1). All checks passed. The combined
allocation contains 518 added tags, 60 added resources, 2418 added strings,
1704240 bytes of metadata and 27954899 compressed resource bytes. These are
partial-build allocation measurements, not final map size or runtime RAM usage.
The source remains Bungie's Reflection in MCC Reach, adapted here to native H3.

Evidence: work/map-conversion-batch/reach-preflight/reflection-combined-stage.json.
No executable or installed cache changed. BSP2, remaining BSP cluster/material
and environment data, complete scenario linking and native validation still
remain; this is not a completed or deployed conversion.

### Reflection third BSP in the shared build (2026-10-26)

The placeholder lighting tag for BSP2 does not mean the BSP can be discarded.
Its own geometry resource is now installed alongside BSP0 and BSP1, with eight
meshes, 357476 raw render bytes, collision/leaves/surface mappings, ten authored
instances and four convex collision objects. Its cached cubemap sample retains
the index into BSP1's imported group. Final scenario binding of that group is
still required.

The initial strict serializer correctly stopped at Reach part bit 1. Primary
TagTool VmfConversion.cs explains that this bit disables static per-vertex
lighting for a part. This BSP has no static lighting tables, no lightmap images,
no lightmap resource and no bound lighting streams. The placeholder adapter
therefore permits omission of that redundant source flag only after checking
those conditions. Other mesh conversions retain the strict rejection. It does
not synthesize lighting or register the geometry scratch record as a lightmap.
Native visual acceptance remains required.

Combined checks cover all 2450 instance names and 455 unique collision-object
IDs, preserving BSP memberships 118/333/4. The third geometry resource is checked
for correct owner and decompressed byte-for-byte after native registration.
The combined partial build uses 1902016 metadata bytes and 28439838 compressed
resource bytes, with 531 added tags and 62 added resources. This is not a final
map size or a console RAM measurement. Source/author: Bungie's Reflection from
MCC Reach; native H3 adaptation by this project.

Evidence: reflection-combined-stage.json and its placeholder_bsp section.
Remaining work includes clusters for BSP0/2, materials, decorators, environment,
scenario linking and native gameplay/visual/performance verification. Nothing
was deployed or changed in the installed executable.

### Reflection remaining cluster records connected (2026-10-26)

BSP0's one cluster and BSP2's two clusters/one portal are now installed in the
same native build as the main BSP's 25 clusters/37 portals. The unsplit path
uses the original adjacency lists and rejects any nonempty decorator groups
unless converted payloads are explicitly supplied. Source and destination
bounds, mesh bindings, adjacency lists, portal plane/flags/bounds and every
portal vertex were read back and compared successfully.

The combined build now contains all 28 destination clusters and 38 portals.
Environment indices are still explicitly marked unremapped until their tables
are converted; this does not establish completed PVS/seam/scenario integration
or correct runtime visibility. Metadata allocation is 1902872 bytes. Original
source/author remains Bungie's Reflection, MCC Reach. No installed files changed.
Evidence: reflection-combined-stage.json, clusters entries 0, 1 and 2.

### Reflection scenario environment properties (2026-10-26)

The shared scenario now contains native cluster-property records referencing
all three converted BSP datums and their actual structure checksums. Each
per-cluster acoustics, atmosphere, camera-effect and weather array follows the
same destination ordering as the BSP clusters, including the split child.
Source centroids are retained in that ordering; BSP2's absent source centroid
table remains explicitly reported rather than invented.

Primary TagTool Gen4.Scenario.ScenarioClusterDataBlock, also used for Reach,
identifies source +0x20 as DefaultAcousticPalette, not generic padding:
https://github.com/TheGuardians/TagTool/blob/ce2dc6ac13072b160752af618ea1dc143e2727ac/TagTool/Tags/Definitions/Gen4/Scenario.cs
Reflection uses default 3 and override 4. The adapter resolves default values
before writing H3's acoustics array and verifies every effective value against
the compiled source cluster. Atmosphere/camera indices also agree. All combined
checks pass. Missing source BSP2 centroid handling still needs native acceptance.

These records retain palette ordinals, but their referenced environment palette
assets are not yet installed; reports explicitly retain that unresolved state.
This is metadata integration, not verified audio, atmosphere or gameplay.
Evidence: reflection-combined-stage.json, scenario_clusters. Source and original
author: Bungie's Reflection from MCC Reach, adapted here to native Halo 3.
### Reflection shared environment integration (2026-10-26)

Source: Bungie's original Reflection, Halo Reach MCC `52_ivory_tower.map`;
no upstream Halo 3 conversion author. This project performs the native adaptation.

Production `reach_probe_bindings.py` now stages the previously checked probe
owner/name mappings into the combined builder and string table. The standalone
binder calls the same implementation. The combined stage checks translated names
after all imports and retains analytical selections for subsequent adaptation.
It stages 40 air probes, 223 scenery probes and one machine probe group, resolves
223 source owners and preserves the reported source orphan f5a4017b00010601.
Unresolved or ambiguous ownership fails the stage. Scenario placements with
preserved IDs still need installation.

The final combined run exited 0: metadata 1,925,916 bytes, compressed added
resources 28,439,838 bytes, 533 added tags, 62 resources, 2,437 added strings.
These are allocation measurements, not full map size or console peak memory.
The city and jay_stone_room reverbs use unchanged stock H3 payloads. Other
environment dependencies remain unresolved.

Reproduce using Python312 -B with
`work/map-conversion-batch/reach-preflight/stage-reflection-combined.py` from the
repository. Its JSON report remains in that directory. No game run, image,
deployment or additional resource copy was produced by this step.

The lighting root remains staged but unlinked: the third BSP has no baked source
lightmap and its native slot representation needs resolution. All 24 inspected
original multiplayer caches have one BSP and one active lightmap record, so they
do not establish the missing-lightmap behavior. Materials, environment and final
scenario integration remain incomplete.

Primary sound-layout reference: TagTool SoundEnvironment.cs at commit
ce2dc6ac13072b160752af618ea1dc143e2727ac. Reach snde is 0x38, H3 is 0x48;
twelve common floats begin at 0 and 8 respectively. Reflection's additional Reach
low-pass fields are zero. Hospital and atrium presets do not exactly match the
available stock H3 presets. The acoustics palette tail discrepancy is unresolved;
do not copy its word at +100 as flags, since multiple entries contain float 1.0.

### Reflection absent-lightmap resolution (2026-10-26)

The native executable resolves the missing BSP-lightmap case; it does not
require an invented third record. `sub_821513B8` (generated recomp.73.cpp)
iterates 436-byte sLdT records and compares each signed index at +2 with the
requested BSP; it returns null when absent. `sub_8216F8F0` (recomp.30.cpp)
rejects null, mismatched BSP checksum, mismatched mesh count or missing textures.
`sub_822C4CA8` (recomp.81.cpp) calls that guard and returns BSP+0x2e0 geometry
when lighting is unavailable, otherwise lightmap+0x130. The other direct callers
in recomp.21.cpp check null and recomp.86.cpp also uses the guard. No engine
modification is needed for the placeholder BSP.

`reach_scenario_lightmap.py` installs the two active converted records (BSPs 0
and 1), keeps BSP 2's own geometry fallback, retains the staged environment
probe arrays and registers/links the native sLdT tag at scenario+0x6f0. It checks
BSP indices, tag groups/salts, checksums, identical shared geometry descriptors,
both texture dependencies and full output-record/reference readback. It rejects
missing lighting for any source BSP not explicitly marked as a placeholder.
This supersedes the preceding unresolved-slot note, but not the remaining
analytical-lighting, materials, environment, scenario and runtime validation work.

Combined assembly after this change exited 0. The report identifies lit BSPs
[0, 1], unlit BSP [2], successful root/reference/record readback and retained
probe arrays. Metadata is 1,926,888 bytes, 534 added tags, 62 added resources;
compressed added resources remain 28,439,838 bytes. No native run or deployment
has occurred. These values still do not certify the console memory budget.

### Reflection material integration (2026-10-26)

Source remains original Bungie Reflection from Reach MCC, without an upstream
H3 conversion. The complete three-BSP material inventory has 163 unique shaders:
123 rmsh, 20 rmcs, 10 rmhg, six rmgl, two water, one terrain and one foliage.
79 have matching original-disc template names. That is not proof of equivalent
parameters: only 13 currently pass the discrete-parameter binding checks.

`reach_materials.discrete_parameters` now reads defaults from the actual selected
Reach rmop tags (0x60 records, type/value +8/+36) and explicit material overrides
(0x3c records, +4/+28). Compiled constants take precedence; missing compiled
integer/boolean constants use an authored override or selected declaration.
Conflicting declarations, duplicate overrides, type mismatches and undeclared
native switches fail. This resolves no_dynamic_lights=false without guessing.
The first remaining switch mismatch is order3_area_specular, not declared by
the source material. It is deliberately not assigned an arbitrary value.

Primary layout evidence: TheGuardians/TagTool, commit
ce2dc6ac13072b160752af618ea1dc143e2727ac, Tags/Definitions/RenderMethodOption.cs
and RenderMethod.cs. The shader importer now also consults configured stock
NativeAssets for exact-name bitmaps before converting Reach payloads.

The isolated material stage imported 13 materials, exit 0, with 137,188 bytes
of metadata and 2,820,382 bytes of compressed resources. This is an allocation
test, not visual verification. Unrepresented Reach VMF lookup textures and other
constants remain listed in reflection-material-stage.json; do not call the
materials visually equivalent based on the template-name check.

Reproduce the inventory with audit-reflection-materials.py, then stage with
stage-reflection-materials.py, both under work/map-conversion-batch/reach-preflight.
The stage accepts a borrowed registry/string table for combined assembly.
No duplicate game installation or standalone map file is created.

### Reflection native material defaults and animation routing (2026-10-26)

The earlier order3_area_specular requirement is resolved as an explicit
approximation: use the stock H3 default false when Reach has no authored
declaration. This selects order-2 SH area specular, consistent with converted
linear-SH lightmaps; it does not zero the authored area-specular contribution.
Compiled/declared source values retain precedence. The importer reports this
adaptation only for templates that actually expose the switch. Original Sandbox
rmop records independently confirm boolean type 4 and default value 0.

Reference: 343Industries/forge-docs commit 678af9cb24d56782d66689118c53dcc738911b7e,
forge/halo-mcc/H3/Shaders/MaterialModel.md (default off) and Order3AreaSpecular.md.
This is not a claim that Reach VMF and H3 SH specular are visually identical.

Fan animation exposed another concrete difference: source entry 14
(Static_Per_Vertex_Color) binds base_map to pixel real register 36609; the native
armory template has no base_map real-constant consumer in either stage of that
pass. The converter now omits that pass-specific route only after validating
the source route and proving absence from BOTH native real-constant stages.
It does not count that omission as representing the function: all functions
must still occur in retained routes. A stage migration or conflicting mapping
continues to fail. Omissions are recorded per material. Fan retains 3 functions;
antenna lights retain 1 and glass_oni_tiler retains 6.

Reach format 22 / DXGI 51 2D normal textures are now accepted by the existing
native signed V8U8 encoder. Other DXGI pairings remain rejected, and normal-map
cube support is not inferred. Reference: TagTool BitmapFormat.V8U8 and Microsoft
DXGI_FORMAT_R8G8_SNORM=51:
https://learn.microsoft.com/en-us/windows/win32/api/dxgiformat/ne-dxgiformat-dxgi_format

Isolated material stage passed all 79 template candidates, using 610,068 metadata
bytes and 17,504,683 compressed resource bytes. 84 other materials remain
unresolved. Shared assembly staging reserve was raised from 2 MiB to 4 MiB based
on measured geometry plus material allocations; no native engine limits changed.
Material tables and runtime visual verification remain incomplete.


### Reflection: existing multiplied-mask adapter integrated

Reflection (Bungie, Halo Reach; direct MCC 52_ivory_tower.map source, no upstream
H3 conversion author) now stages 81 of 163 BSP materials in the shared assembly.
The two additional materials are wall_panel_t_chromedome_b and
glass_rail_wall_opaque under levels/solo/m50/shaders. Both use the existing
static default-albedo diffuse-times-specular alpha bake and original-disc H3
texture-mask programs (guardian.map and armory.map respectively). The planner
records this as an adaptation, not an exact source shader match. Other albedo
combinations and animated multiplied masks are not treated as supported.

Corrected baked-mask binding: previously the bitmap override skipped texture
metadata conversion, potentially leaving donor sampling/transform indices. It
now retains authored sampler settings and explicitly binds the new periodic
specular_mask_texture constant, with no donor animation span. Static baking
rejects animated source materials rather than silently freezing their masks.
The combined stage reads back both target texture records, validates bitmap
salts/groups, wrap mode, transform indices, zero animation spans and finite
positive periodic scales. These are structural checks, not visual approval.

Combined stage passed: 2,601,348 metadata bytes, 46,287,275 compressed added resource bytes, 814 added tags and 199 added resources. 82 materials remain unresolved. Material tables, final scenario integration, native gameplay/visual checks and deployment remain incomplete.

### Reflection: glass/custom/foliage source-class investigation

Expanded the parameter reader to accept rmgl, rmcs and rmfl after checking
TagTool ShaderGlass.cs, ShaderCustom.cs and ShaderFoliage.cs at commit
ce2dc6ac13072b160752af618ea1dc143e2727ac. Each inherits RenderMethod and adds a
4-byte global-material StringId. This is reader support, not permission to
serialize these classes unchanged to H3.

The refreshed material plan now reports actual semantic options for all 27
previously opaque class failures. No additional materials were imported:
81 staged / 82 unresolved remains authoritative. Six glass materials have no
native glass definition in the original-disc catalog. Twenty custom materials
include window_room self-illumination, absent from the H3 custom option list;
others have valid semantic categories but no matching stock compiled template.
Construct's native custom program is _10_2_0_2_1_0_1_3_0_0, not a blanket donor
for Reflection's window boxes. Do not replace them with that program by index.

Bamboo foliage is source simple/from_texture/flat plus simple wetness; H3
foliage exposes default/(none or simple)/default and no wetness category.
The source alpha_test_map equals the base bitmap and uses the same transform.
Source BSP 1 mesh 126 part 0 is its sole BSP use: rigid vertex type 1, vertex
buffer 199 only, mesh flags 40, part flags 516, lighting policy 1. No separate
static-lighting stream is bound. Source wind amplitude is zero. Its native
lighting entry point still needs confirmation; do not force per-pixel foliage.
The published H3 foliage.fx explicitly produces a red warning for that path.
Bunkerworld has native foliage template _0_1_0, but merely finding the template
does not establish lighting/material equivalence.

Primary shader reference:
https://github.com/halohlsl/Halo3-Shader-Source/blob/257ca5f9e1149a31dbfb6a7c9141bd232f590e5b/hlsl/foliage.fx
Inspection data: work/map-conversion-batch/reach-preflight/reflection-special-materials.json.
No engine change, candidate deployment or new visual verification in this pass.

### Reflection: scenario BSP table integration

Added reach_scenario_bsps.py and connected it to the shared offline assembly.
It emits H3's 108-byte scenario BSP records from Reach's 172-byte records,
validates tag groups/salts and ordinal coverage, and reads back the resulting
array and scenario pointer. It preserves ambient minima, vertex sink, sky/fade
fields and cloned-BSP masks. Flags are mapped by semantics: notably Reach
NoAiAttachment bit 9 becomes H3 bit 10, and NotMultiplayerPlayableSpace bit 10
becomes H3 bit 11. Copying these flags numerically would be incorrect.

References: retained H3/Reach scnr.xml plus TagTool Scenario.StructureBspBlock
at ce2dc6ac13072b160752af618ea1dc143e2727ac. The latter identifies Reach bit 9
which the older plugin calls unknown. Authoring size hints map by named pixel
extent (sub-256 hints use H3's smallest 256 hint); bitmap dimensions/resources
are not resized or reallocated by this step.

Main BSP 1 now references its converted 51-image cubemap bitmap. BSP 0's source
reference is rasterizer/invalid, a 64x256 2D sentinel, NOT an unconverted cube.
Reuse Sandbox's existing rasterizer/invalid bitmap under the stock asset policy.
BSP 2 has no source cubemap reference and retains a null reference. The cubemap
importer's type guard caught the sentinel before an invalid cube was imported.

Structure-lighting stli dependencies and structure designs remain explicitly
pending; the module does not silently declare those complete. Reach-only shared
BSP/cubemap flags and source lightmap-settings bytes are recorded for subsequent
integration. This stage does not yet save/deploy a playable map.

Combined integration passed: three BSP records read back, native flags 0xC00/0x400/0xC00, stock invalid-bitmap reused, no new texture allocation. 2,601,684 metadata bytes; 46,287,275 compressed added resource bytes. 81 materials remain staged and 82 pending. Runtime verification and deployment remain false.

### Reflection PVS: native mapping consumer identified

Original executable accessor sub_82165140 (generated file 37) selects the active
zone's 84-byte BSP PVS record and its +72 mapping array, then returns the selected
cluster's count and pointer. Callers sub_82164B70 (file 17) and sub_822C5A50
(file 65) read each entry with lbzx and combine that unsigned byte with the
observer's unchanged BSP byte. These are SAME-BSP cluster links. This resolves
what the native field can represent, but does not yet identify which Reach
root/attached/connected relation should populate it. Cross-BSP pairs cannot be
flattened into it. Both callers separately call sub_820abe50 for additional
cluster references; its data/semantics are the next integration lead.

Corrected native_zone_pvs.serialize_zone to use unsigned mapping bytes and reject
out-of-range local cluster indices. The stock round-trip reader now agrees with
the executable's unsigned loads. All 23 previously supported original-disc zones
still round-trip. A 201-cluster fixture round-trips a link to cluster 200, and a
link to nonexistent cluster 201 is rejected. Deadlock's nonempty device-portal
association remains explicitly excluded. This does not establish Reflection PVS
integration or native visual correctness. Compact instruction evidence and Reach
cross-BSP relation counts are in reflection-native-pvs-consumer.json.

### Reflection: physical seam topology established

Traced original sub_820ABE50 (generated file 92): it reads the source cluster's
+160 seam-index list, then the original runtime seam table (516-byte entries,
not ManagedDonkey/Halo Online's expanded 644-byte entries). It pairs BSP sides
and returns neighboring BSP/cluster references. This confirms that cross-BSP
connections are separate from the unsigned same-BSP PVS links.

New reach_seam_topology.py and stage-reflection-seams.py read all 12 source seam
ordinals across the three BSPs. Paired occupied records have matching identifiers
and one cluster per side. Their 16 directed connections exactly equal Reach's
PVS attached-cluster relation, with no missing or extra links. Both source
scenario structure-seam tag references are null; the BSP seam records are not.

The proposed split remap assigns seam 0's main-BSP centroid to appended cluster
24; seam 1 remains in cluster 2. All 16 connections survive when the appended
cluster is collapsed back to its original identity. This verifies graph
preservation, NOT that entire seam geometry lies on the chosen side. The next
checks are seam-edge geometry against the partition, collision-edge relocation,
and original native seam initialization. None is silently marked verified.
Report: reflection-seam-topology-stage.json. No cache deployment or runtime test.

### Reflection: seam installation and original initializer traced

Combined assembly now installs all 12 native seam ordinals in each of three
BSPs and reconstructs each cluster's seam incidence after the split. Entire
seam-edge bounds confirm seam 0 belongs to child 24 and seam 1 remains in
parent 2; neither crosses the partition. Converted collision edges and vertices
match source numbering and geometry byte-for-byte after endian conversion.
Native seam records and cluster incidence read back successfully. Metadata is
2,607,828 bytes; compressed added resources remain 46,287,275 bytes.

Original executable sub_821C66A0 (generated file 29) initializes cross-BSP
connections from scenario BSP references and BSP +12 seam records, using
40-byte source records, matching 16-byte identifiers and spatial centroid
matching into 516-byte runtime records. It does not read a scenario structure
seam tag in this routine. This removes the assumption that the null Reach
scenario seam tag alone prevents these connections. The routine permits two
BSP sides and up to 32 cluster entries per seam; the current source has only
one cluster per occupied side. Ten occupied paired seam ordinals have identical
identifiers; nine centroid pairs coincide exactly, and seam 6 has squared
distance 5.4147676564753056e-08. The executable's comparison threshold still
needs extraction before claiming the latter passes its spatial match.
Instruction evidence and pair measurements: reflection-native-seam-initializer.json.

This is offline integration and original-code evidence, not execution proof.
Native seam initialization, local PVS mapping translation, remaining materials,
full cache assembly, native visual verification and deployment remain pending.
Source remains Bungie's Reflection from Halo Reach MCC 52_ivory_tower.map,
a direct Reach conversion rather than an upstream H3 remake.

### Reflection: original seam tolerance and audio-table distinction

Read original work/gamedata/default.xex in memory via Xex.image(), without an
extracted copy. sub_821C66A0's float at 0x820596EC is 0.04000000283122063
(squared distance). All ten occupied seam pairs pass, including seam 6.
reach_seam_topology.paired_connections now enforces that original tolerance;
stage-reflection-seams.py passes with the guard. Evidence was added to
reflection-native-seam-initializer.json. This remains static evidence rather
than a native-runtime test.

Stock table audit (native-pvs-local-links.json) found the BSP PVS +72 list empty
in 22 of 24 disc scenarios. Descent has two nonempty rows and Shrine has three.
The native scnr plugin names this field Cluster Audio Cluster Neighbors.
Its caller behavior preserves BSP identity, consistent with the earlier
unsigned-byte findings. Reach's +60 root/attached/connected seam relations
are therefore not established as equivalent to this native audio table.
Do not populate the audio table by flattening or projecting those relations.
Research native audio-neighbor construction/Reach audio data separately;
physical cross-BSP connectivity already has its dedicated seam implementation.
