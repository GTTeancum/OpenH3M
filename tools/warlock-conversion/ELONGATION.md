# 3longation conversion

Source is the requested Halo 3 custom 3longation, Workshop 3618057049,
maps/h2_elongation.map. Full conversion has not yet been implemented.

This map has 57 scripts, 7 globals, 8 machines and 4 flocks. Continuous scripts
include crate recycling and blue/red conveyor behavior. Do not remove these to
make a static map load. The existing pipeline correctly stops at active scripts.

Read-only audit: audit_scenario_scripts.py; report work/elongation/script-audit.json.
All actual engine function references have matching Xbox 360 H3 signatures.
The source uses MCC U14 opcodes, confirmed against compiled function-name strings;
U13 has mismatches. Script-call name nodes must be distinguished from builtin
function nodes by their parent expression's Script Index flag. The U14 audit has
zero opcode-name mismatches across 2,287 allocated expressions.

Graph audit now validates every script/global root, next-expression link and
group/script-call child handle against both the destination slot and allocation
salt. The source passes all 2,287 non-null links with zero invalid handles.
Node layout and group flags were checked against TagTool revision
ce2dc6ac13072b160752af618ea1dc143e2727ac (TagTool/Scripting/HsSyntaxNode.cs).
This validates source links, not execution or the yet-unimplemented translator.

`script_expressions.py` now translates expression headers, builtin function
indices, external globals and literal byte order, preserving expression slots and
handles. It uses the literal opcode's stored type rather than its potentially
cast result type: named-object literals cast to `object` still occupy two bytes.
External `global_playtest_mode` remaps from MCC 0x40E to retail 0x413.
Legacy code-page bytes in literal messages are preserved without ASCII decoding.
Tag and string-ID values require explicit relocation callbacks.

The source encoding check passes all 3,109 slots (2,287 allocated), including
986 changed opcode fields, unchanged links and explicit named-object/global
byte checks. Report: work/elongation/expression-encoding-check.json.
This check deliberately identity-maps tag/string IDs; its bytes are not a usable
cache. Scenario staging now uses real tag/string-ID relocation callbacks and
preserves script/global root handles, nested parameter declarations, references
and the source script-string allocation. Parameter indices and declared types
are checked per script. Native Last Resort confirms the external-global bytes
`ffff8413` and the scalar-width conventions.

`build-elongation.ps1` passes runtime/script staging, geometry, objects and spawn
conversion. Codec 7 in the cov_flee animation is now handled as reverse word
keyframes, following TagTool's KeyframeLightlyQuantizedCodec and
ReverseKeyframeLightlyQuantizedCodec at the pinned revision above. The actual
322-frame member passes comparison of every stored key index and pose component;
report: work/elongation/word-keyframe-check.json. No resampling or node reversal
is performed during conversion; the original decoder interprets its codec ID.

Conveyor/security-light retail collision response defaults to zero, matching
original Warehouse/High Ground machinery (native-machine-donors.json and
native-door-donors.json). Source machine types and motion remain intact.
The eight placements have zero appearance variant and change-color masks;
dormant 0xFF000000 color words are ignored. Active overrides still reject.
Retail schema now names machine flag bits 7/8 per TagTool's shared Scenario
definition, so authored Ignores AI is preserved rather than dropped.

Flock metadata uses Assembly's verified inherited H3 schema. The MCC creature
schema was obtained from Assembly at work/elongation/creature-schema-revision.txt.
Flood-clump debris uses Cold Storage's original opaque particle family under
the stock-H3 asset rule; the source effect emitters/timing remain intact.
Native creature AI padding is zero in all 26 audited disc rows. Creature sphere
and pill layouts are byte-for-byte identical to their phmo counterparts in both
schemas, so they use the existing physics conversion.
The debug `basic` bitmap has a stripped resource in its sole retail donor,
Valhalla. Its same-named MCC 64x64 BC1 image is recovered with a strict native/
source dimension-format check, following the existing Chiron recovery path.
Reports: ambient-native-donors.json, creature-ai-padding.json,
basic-bitmap-audit.json in work/elongation.

The distant Phantom bolt uses the native distant-Hornet additive bolt particle,
retaining authored emitter placement/timing/tint. Texture changes from fiery to
clean spark as a stock-H3 equivalent; black-point shader approximation is avoided.
Two script-referenced cutscene flags now preserve names/positions/facing in the
retail layout, with original four-byte padding and no MCC editor-folder field.

Build succeeded: work/elongation/zanzibar-01.map, 72,691,712 bytes (69.32 MiB),
SHA256 fb602ac63ed62815cde67f24a9a52e2779af953c34428fe0e2d2039fefc35ffd.
DLC identity: elongation / 3longation / 1739. Five previews use the source mod's
declared Large image. The 11-map, 77-file LIVE candidate is
work/elongation/live-01/5A284CBB40C0DCD92C1FD8911BA1579EB285B552;
its header/data/hash-tree integrity checks pass. Existing payload files are
hardlinked from Lockout's accepted bundle, not duplicated into another build.
The installed bundle is unchanged. Native load check
.local/loading-traces/20261025-082535-40864 reached 3longation gameplay through
the LIVE installer and map list; proof-loaded.png was inspected. It shows the
expected industrial shipping hall, conveyor lane, crate, walls/doors, lighting
and HUD. The process reached its 180-second watchdog without a load crash.
This static capture does not prove conveyor motion or crate recycling.
The emitted cache also validates all 2,287 handles and all six conveyor
name-to-machine links (emitted-script-check.json).

The process-local menu harness now delays confirmation for routes longer than
17 steps; 3longation requires 18 UP selections from Last Resort in this bundle.

Still required: native visual/behavioral checks of conveyors/crate recycling,
preview/menu verification, and promotion after acceptance. Console/system-link
behavior remains unverified.

Follow-up diagnostic run `.local/loading-traces/20261025-083536-30476` sampled
machine/crate bodies every five seconds using the existing TLS object table.
The six conveyor instances change allocation handles, matching the authored
destroy/create cycles. Crate bodies move in both lane directions, with large
position changes consistent with scripted returns. Raw evidence and trajectories:
`work/elongation/conveyor-live-check.json`; decoded source expression trees:
`work/elongation/conveyor-script-trees.json`. Position offset 0x54 is inferred
from authored placements and live motion, not an independently recovered layout.
The 135000ms native capture was inspected and shows the expected shipping hall,
conveyor lane and crate. The 180-second wall watchdog expired before the second
165000ms guest-time capture; harness correctly reported incomplete capture.
No promotion occurred. Next: complete the bounded visual pair and menu check.

Accepted follow-up: `.local/loading-traces/20261025-084006-44680` completed
the 180-second watchdog with all three requested native captures. The 70500ms
capture shows selected 3LONGATION, its source preview and description alongside
stock and other custom maps. The 125000ms and 140000ms captures were inspected
sequentially: the same shipping hall renders correctly and crates change position
along the conveyor. Read-only object snapshots additionally show conveyor handle
replacement and moving/returning crates. This is bounded behavior coverage,
not exhaustive multiplayer testing or console certification.

Promoted into the shared 11-map bundle: `work/elongation/promotion-01.json`.
All 77 native-installed files match payload hashes; profiles and engine preserved.
Previous bundle retained at `work/elongation/previous-installed-content`.
Diagnostic content copies were hash-verified and hardlinked to the installation;
`work/elongation/diagnostic-dedup.json` records cleanup. Logs/captures retained.

## Correction candidates, 2026-10-25

The earlier crate-motion checks did not establish visible conveyor animation.
The source conveyor shader has three translation functions (7-second period),
but the generic converted material had none. The converter now selects its
exact original-disc shader permutation, retaining height/material textures and
all three animation functions. Candidate 02 native captures in
`.local/loading-traces/20261025-172203-40468` at 115/117 seconds were inspected:
the yellow belt arrows move relative to the static hall, as do the crates.

Candidate 04 combines this with exact native emission shaders and an explicit
map-specific +0.65 EV auto-exposure target/bounds adjustment. Build report:
`work/elongation/build-04.json`. Native run
`.local/loading-traces/20261025-173756-25312` completed its 150-second watchdog;
both 115/130-second captures were inspected. The hall still appears too dark,
so brightness is not accepted. The generic movement replay ends against a wall;
it is not adequate traversal-performance evidence. No correction candidate has
been deployed. Continue brightness tuning and use a map-specific walking route.

Exposure profiles are isolated by source cache filename and camera tag path in
`snapshot/tools/map_exposure.py`; unrelated maps and stock cameras are unchanged.

Candidate 05 uses +1 EV, reaching stock Cyberdyne's -3.321928 auto target.
User accepted this lighting level on 2026-10-25: "This lighting level is much
more acceptable." Retain this per-map exposure setting during remaining fixes.
Run `.local/loading-traces/20261025-174252-20296` completed its 150-second
watchdog. Both 115/123-second captures were inspected: the shipping hall is
brighter, and the explicit `--walk-route elongation` strafes to the adjacent
conveyor corridor. The latter capture also shows several light flares through
the wall: the occlusion defect is not restricted to Battle Canyon.

Performance is not accepted. Candidate 04's stationary 110–120s window has
median 66.65 ms / p95 66.96 ms image-change intervals and 122 logged GPU
submission waits; candidate 02's same window had none. Candidate 05 improves
to median 33.41 ms but p95 remains 66.72 ms. This is an association with the
combined material/exposure change, not proof of which shader causes it.
The new `summarize_present_timing.py` retains long stalls and reports skipped
guest frames; capture-intersecting intervals are excluded explicitly.

Next investigation: instrument host occlusion fallback/disable paths. A single
logged zero-sample query proves only that one interval resolved; it does not
prove later intervals avoid the visible-sample fallback. Avoid tuning Battle
Canyon's flare bounds before separating this shared runtime issue.

Diagnostic run `20261025-174731-22676` confirms a shared host failure:
at 17:49:28.339 the renderer logs `disable: end without active query 03F90C80`.
This permanently disables real occlusion and restores fake visible samples.
The earlier zero-sample success does not establish ongoing correctness.
`EndSubmission` currently ends and clears active queries without retaining their
results across command-list boundaries. Next fix must preserve query intervals
across those boundaries, rather than changing map flare appearance or accepting
fake counts. Diagnostic DLL remains isolated in the correction fixture.

The split-query implementation passed the same route in
`20261025-175133-28324`: both native captures inspected, wall-facing light bleed
absent, and a two-segment query resolved without the previous disable/fallback.
Timing over the 110s-onward window: median 33.37 ms, p95 33.82 ms, p99 50.15 ms,
maximum 67.07 ms, no >100 ms stalls (capture intervals excluded). This is a
bounded route result. Unobstructed-flare visibility and Battle Canyon still need
verification before deployment; do not equate all-zero queries with correctness.

`halo3mp/patches/rexglue-sdk-installed-map-corrections.patch` preserves the
current cumulative command-processor/header changes, including earlier local
timing/index-binding edits and the original snapshot fix. It is an alternative
cumulative patch against this SDK checkout's HEAD, not an additional patch to
apply on top of the separate snapshot/index-binding patches.

### Candidate 06: remaining light materials restored

Source: TBeezie's 3longation, an H3 remake of Halo 2 Elongation:
https://steamcommunity.com/sharedfiles/filedetails/?id=3618057049 .

Candidate `work/elongation/zanzibar-06.map` is 75,616,256 bytes. It retains
accepted +1 EV and the conveyor fix. The three remaining light materials
(panel_mech_strips_hazard_stripe, panel_tech_rack, light_halogen) use the
original-disc resupply-capsule shader combination. A private opaque base alpha
neutralizes its additional specular mask, retaining unmasked source behavior.
Color mip chains are preserved. Build report 06 shows no unrepresented textures
or constants for those materials, and no remaining self-illumination omissions.

Native run `.local/loading-traces/20261025-182608-10852`: both captures at
115/117 seconds inspected in order. Ceiling lights emit; hall surfaces remain
readable; belt arrows visibly advance against stationary architecture, as do
crates. This confirms the conveyor fix survives the material update.
Host frame-change median 33.36 ms, p95 33.76 ms, maximum 50.41 ms, no intervals
over 100 ms. This is the bounded harness route, not an exhaustive map playtest.
Candidate remains isolated pending the full correction bundle deployment.
