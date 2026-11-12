# Halo 4 Forge original-behavior findings

This is an incomplete reverse-engineering record, not an implementation or completion certificate. Function labels are addresses from the private original H4 executable; descriptive names below are inferred from the cited operations. Generated sources live under `work/h4-forge-research/generated/`.

## Discovery and provenance

`audit_forge_flow.py` indexed 73,876 original generated functions and retained 80 functions in the two-caller neighborhood of the expanded Forge/control roots. Direct-call indexing misses indirect callbacks and is not exhaustive Forge discovery. The compact result is `work/h4-forge-research/isolated/full-re-callgraph.json`; it records source filenames, lines, body hashes, direct callers/callees and unresolved fields.

The script independently checked all 21 dispatch table entries for `824500A8` against the original decoded executable bytes at `82450128`. It does not assign unproved meanings to event IDs.

Event-arm calls now follow the generated assembly's branch edges through shared tails and stop at returns/external tail branches. The earlier textual span method incorrectly attributed an unreachable visibility call to no-op event 18. Assertions now check that event 18 has no calls and event 16 retains its visibility call. This checks the dispatch inventory, not gameplay correctness.

## Editor event transport and state

- `825812D0` transports the original event packet. The event type is a halfword at packet +0x108; the player index is at +0x104. Its submission path branches on the original game/session state. Calls include `82800D50` and `82851F28`; those transport semantics still need audit.
- `824500A8` dispatches event IDs 0 through 20. Events 1, 3 and 5 take an extra validity check before dispatch. Event 18 exits without applying a handler. The remaining events are not thereby proved implemented in Spartan.
- The Forge per-player editor record used throughout these paths is `*(TLS+0x1c) + 0x1aec + (player & 0xffff)*0x150`.
- Event 13 applies coordinate data after object validation (`82451908`) and updates the held transform. This corresponds to the earlier extracted coordinate event; complete persistence/authority semantics remain open.
- Event 14, producer `82685E88`, updates rotation-snap mode at editor +0xe0 (menu binding verified below). If the prior mode and byte +0x51 are nonzero and the new mode is nonzero, it copies nine floats from +0x88 into +0x58. It then clears +0x51.
- Event 16, producer `82685EE0`, updates magnet enable at editor +0x52 and handles marker visibility on change. Event 17, producer `82685F38`, writes sensitivity to editor +0x10c.
- Current `Bridge::Evaluate` zeros the whole synthetic per-player record every evaluation and supplies only selected fields. This cannot be treated as complete H4 editor-state integration; the original mode/transition dependencies above must be accounted for.

## Placement and magnet call paths

Two original paths reach the shared magnet application function:

1. `8244D0E0 -> 8244A8D8 -> 8244EED8`.
2. `82451FC0 -> 8244B860 -> 8244EED8`.

Their distinctions and complete upstream control semantics remain under audit. In both, `8244EED8` checks enable byte +0x52, runs selection `82582250`, retains the candidate for visibility, then checks `82582178`. Alignment `82582AD0` runs only when selection returns 2 and that predicate returns false. It writes the resulting transform to the caller's output and invokes `8244A118` for visibility.

The current Spartan bridge calls selection and alignment but omits `82582178` and bypasses those enclosing paths. This is a confirmed integration gap, not yet proof that it alone causes every reported sticky snap.

`82582178` resolves the player's unit through the original player/object tables, reads three floats at unit +0x544/+0x548/+0x54c, and returns whether their magnitude exceeds configuration +0x24, falling back to original constant 0.5. The vector's producer and units remain unresolved. Supplying raw controller input or naming it velocity without tracing its producer would be an assumption.

### Vector producer traced; input semantics still open

`822562A8` (`halo4_recomp.180.cpp`) resolves its object datum through TLS +0x1150 and the object-header data pointer at +12, matching the base lookup used by the predicate. It consumes a second-argument packet whose three floats at +0x20/+0x24/+0x28 feed object +0x544/+0x548/+0x54c. Its branch at `82256A8C` copies those values directly. Other branches blend/normalize the vector using existing object state and transform it into +0x568/+0x56c/+0x570. Therefore substituting raw host stick values is not established equivalent.

Direct callers include `8225CE30`, `822D2868`, `822F3240`, `823619F8`, `82A6F0B8` and `82A71AC8`. `822D2868` supplies a packet array with 152-byte stride; `822F3240` first invokes an indirect packet-producing callback. `8225CE30` also reaches this routine from its player iteration. These producer paths and their monitor-specific branches still need tracing before assigning units or an H3 field mapping.

`82A26BE8` is another confirmed writer through the object table: it uses argument 1 +36 as the unit datum, copies two floats from argument 2 into +0x544/+0x548, zeros +0x54c, scales the vector, and conditionally copies it to +0x550/+0x554/+0x558. Its callers are `82A27E48` and `82A27F28`; relevance to the monitor path is unproved. Literal offset matches in weapon and UI constructors are not evidence of unit-control semantics.

## Original grab and distance policy

`824511B0` checks/relinquishes a different currently held object, validates the requested object via `82451908` and `824519C0`, then calls `82450E10`. That function initializes held/editor state via `82449ED8`, obtains the object transform, computes an initial projected distance into editor +0x1c, and calls `82452738` with the held object. This is a grab path, not a palette-create-only exception.

`82452738` is also called by `8244D0E0`. Its floating-point instruction sequence establishes the following policy for a valid held object:

- Optionally subtract player-record +0x764 multiplied by original constant 0.3 when player-record byte +0x760 is nonzero. These input-field semantics still need their producer traced.
- Read radius from the held object's +0x4c field.
- Compute lower bound `L = max(radius * 1.25, radius + 0.4)`.
- Obtain multiplier M from `82452C28`: configured field +0x54 if greater than 0.0001, otherwise 5.
- Obtain maximum D from `82452BB8`: configured field +0x50 if greater than 0.0001, otherwise 22.
- Compute upper bound `U = min(M * L, D)` and output `min(max(adjusted_distance, L), U)` using the original single-precision instructions. Do not substitute a clamp implementation that assumes L <= U without proving it for all inputs.
- Without a held object, `82452AD8` supplies configured default distance +0x48 if greater than 0.0001, otherwise 5.

Constants 0.3, 0.4, 1.25, 5 and 22 were read from the original decoded image at 82128A1C, 82128B04, 82128F30, 82128A10 and 8212915C respectively. Config lookup is through the original Forge globals resolver `82340E60`; Ravine's actual values are verified below. Other maps/configurations are not yet covered.

This differs from the deployed Spartan `2*radius+1` spawn-only minimum. That workaround is not an implementation of the original H4 policy and is not the basis for the replacement.

### Verified retail Ravine configuration

`audit_forge_globals.py` independently resolves the original cache tag/group tables, verifies the `forg` identity and prior extraction's 80-byte hash, then reads the complete 88-byte structure. It writes only `isolated/full-re-globals.json`; no runtime configuration is changed. The local TagTool Gen4 schema provides corroborating field names and the 0x58 structure size; original consumers remain the authority for behavior. The original 80-byte extraction omitted fields +0x50/+0x54.

| Offset | Field | Ravine value |
| --- | --- | --- |
| +0x24 | Throttle sensitivity (magnet suppression predicate) | 0.5 |
| +0x28 through +0x38 | Five magnet factors | 0.1, 0.25, 0.5, 0.75, 1 |
| +0x3c | Magnet angle | 45 degrees |
| +0x40 | Magnet offset influence | 0.75 |
| +0x44 | Object grab range | 7.5 |
| +0x48 | Default focal distance | 7.5 |
| +0x4c | Minimum focal distance | 2 |
| +0x50 | Maximum focal distance | 22 |
| +0x54 | Focal distance multiplier | 5 |

Full structure SHA256: `0aa93e946f5ba028c26b21e4d892dd6996512c302e5eea87221e39756c9777a7`. Default distance 7.5 differs from the executable's fallback 5. The minimum-distance field's separate consumers still need tracing: do not insert it into `82452738` merely because its schema name sounds applicable. These values are for this verified retail Ravine cache, not a claim about every H4 map.

## Held-object lifecycle and release

- `82449ED8` (`halo4_recomp.101.cpp`) changes the editor's held datum. On transition from a different datum to -1, it resets held/target fields +0/+4/+0x18, restores the configured default distance at +0x1c, resets offsets and selected transform fields, clears +0x50/+0x51, and invalidates three fields at +0x100/+0x104/+0x108. It does **not** zero the entire editor record: magnet enable +0x52, mode +0xe0 and sensitivity +0x10c are not cleared by that reset block.
- On every call it clears +0x118 and +0x51, stores the requested held datum, and, for the locally relevant player, updates marker visibility through `825826B0` using the previous held/target identities. On nonempty grabs it also computes additional relative state. That computation still needs its complete semantic mapping.
- Event 4 invokes `82451500` (`halo4_recomp.144.cpp`) with an object datum and payload byte +4. It first requires the supplied object to equal the held datum. If editor +0x118 is set, it passes saved data at +0x138/+0x120/+0x144 to `8281EF50` before calling `82451250`. These fields must be carried across updates rather than fabricated anew each frame; their exact transform semantics remain open.
- `82451250` (`halo4_recomp.11.cpp`) resets the held state via `82449ED8(...,-1)`, then checks session and placement eligibility. On a failed `82451DA8` check outside session type 4, it invokes `82450CD8`. Otherwise it updates variant flags, applies one of two placement/physics paths, recalculates the state through `8244A180 -> 8244A2A0`, and performs player/local updates. It is not simply a transform write followed by clearing a host boolean.
- `82450CD8` (`halo4_recomp.120.cpp`, event 1) validates the object, iterates player records and clears any matching held datum through `82449ED8`, updates variant bookkeeping outside session type 4, then calls `82936B78`. The final object-operation semantics and replication need audit before treating this as a complete deletion specification.
- Event 5 (`824515C8`, `halo4_recomp.212.cpp`) validates the object, reads its variant slot, obtains and updates the variant record through `823C5C28`/`823C5DD0`, compares the before/after `8244A180` state, and reapplies `8244A2A0` when it differs. The property byte meanings and menu bindings remain open.

`8244A180` uses the variant record's +62 masks 0x80/0x40 together with held/other predicates to return states 0 through 3. Do not equate these four internal states directly with three visible Normal/Fixed/Phased options without following the UI and physics consumers. `82451DA8` combines multiple world/placement checks; its result must not be replaced with an arbitrary overlap threshold.

## Reproduced overlap defect

`check_coincident_snap.py` now resolves exact identities from `marker-bindings.json`, reads the installed AFM2 marker pack, and checks Base Round and Arena Wall on both map palettes (1730 and 1731), with both same and opposed orientations. It fails on missing expected bindings rather than silently skipping a case. All eight cases snap to the target origin with identity held rotation in the isolated current bridge. Same-orientation cases therefore reproduce coincident geometry. Results remain diagnostic failures, not passing regressions. The valid opposed Base Round seam explains why the earlier single fixture did not expose the same-orientation failure.

## Native tools menu and additional behavior

`audit_forge_menu.py` reads the retail Ravine string table using the existing namespace map, verifies callback pointers against the original executable image, and checks the generated constructor/setter instructions. It retains `isolated/full-re-menu.json`, including source hashes. Its 132 Forge/snap identifiers are discovery leads, **not** 132 proven reachable features.

### Rotation snap: resolved menu-to-event binding

Constructor `8268A290` (`halo4_recomp.66.cpp`) creates a control at +0xac with label `0x805c6` (`forge_tools_snap`), description `0x805ca`, list pointer to constructor +56 and vtable `821432A0`. Vtable slot +72 points to `82685E88`, whose setter emits event 14 only when the selected value changes. The constructor builds values 0 through 5, mapped to `snap_off`, `snap_90`, `snap_45`, `snap_30`, `snap_15`, and `snap_5` respectively. It initializes the control value to 5; this is the **constructor value**, not yet proof of the final loaded/default player preference. Event 14's editor +0xe0 field can now be named rotation-snap mode. Angular quantization and its interaction with magnet orientation still need their consumers traced.

### Rotation-snap consumer and isolated execution

Both placement functions `8244A8D8` (`halo4_recomp.194.cpp`) and `8244B860` (`halo4_recomp.147.cpp`) copy the editor transform at +0x54 into a temporary 52-byte transform. They quantize it only when rotation-snap mode +0xe0 and byte +0x51 are both nonzero. The mode indexes the original integer table at `833F195C`: `[0,90,45,30,15,5]`, multiplied by the original radians-per-degree constant at `82128A20`.

`82451A38` (`halo4_recomp.282.cpp`) obtains an angle triple using original basis conversion routines, then for each angle computes `q = angle / increment`, adds +0.5 for nonnegative q or -0.5 for negative q, truncates toward zero and multiplies by the increment. Thus the instruction-level tie rule is away from zero; conversion and float rounding can affect whether an input reaches an exact tie. It rebuilds the basis and its cross-product axis. Position and scale are not modified by this routine.

The callers compare all nine quantized basis values with cached basis +0x88, using original epsilon at `82128A54` (approximately 0.0001). If any differs by at least that epsilon they copy the quantized 52-byte transform back to +0x54 and update the cached nine values. Both then invoke magnet application `8244EED8` on the temporary transform. Quantization therefore precedes magnet alignment; treating those as interchangeable final transforms would change the original sequence. The callers end with different downstream transform/physics functions (`82452930` versus `8249B418`); those distinctions remain under audit.

`audit_rotation_snap.py` extracts the original quantizer unchanged, checks its dependencies against the existing extraction and verifies the image angle table/constants. `test_rotation_snap.cpp` executes it in isolated guest memory. The test checks five nonzero modes, all three axes and signed inputs on either side of half-step boundaries: 131 cases pass, including position/scale preservation and restored guest stack. Pitch cases outside its principal interval are explicitly excluded. Original angle/basis helpers are reused for fixture construction and expected basis conversion, so this is a quantization test, not an independent proof of those helpers, Euler singularities or full editor behavior. Zero mode is a caller bypass, not a valid zero increment supplied to this routine. Exact ties and combined-axis/gimbal cases remain untested.

Evidence: `isolated/full-re-rotation.json`, `isolated/rotation-test.log`; source bodies verified against the generated originals with `verify_original.py`. No Spartan runtime or shared installation changes.

### Tool action bindings

| Action | Constructor/control | Original callback | Event |
| --- | --- | --- | --- |
| Delete all of type | 8268A290 +196, vtable 8214313C +52 | 82685C50 | 8 |
| Delete all of palette | Container +224, nested control +240; vtable 82143174 +68 | 82686F58 | 9 |
| Duplicate object | +516, vtable 821431F4 +52 | 82685CA8 | 10 |
| Lock/unlock object | +536, vtable 8214322C +52 | 82685DA0 | 11 |
| Unlock all | +556, vtable 82143264 +52 | 82685E50 | 12 |

The lock control's constructor initializes its label field to -1 and assigns the lock-description identifier; its dynamic lock/unlock label updater remains to be traced. The callback checks object ownership and inverts `82449C30` into the event's requested lock byte. Event 11's handler `82450C00` changes property byte +51 via the variant getter/setter and releases the object if it is being locked while held. Event 12's `823C6550` iterates live objects with valid variant slots, clears record byte +51 for eligible records and notifies the change. Two object-header flag exclusions remain to be named.

Delete-all is filtered, not an unconditional purge. Event 8's `823C5670` iterates 651 records (stride 76), matches type and additional property values, skips records whose byte +51 is nonzero, and applies an additional four-byte matching rule except for internal types 32 through 35. Event 9's `823C5770` similarly skips locked records, resolves the palette by scenario counts, and skips a palette flag before deleting through `823C53F0`. The exact property names and protected palette flag remain open. `82686FD0` emits event 9 once per scenario palette; its delete-everything menu reachability still needs the enclosing binding verified.

Additional string-identified candidates to audit include spawn-at-start, hide, shape dimensions, team, labels, teleporter filtering (players/vehicle categories/projectiles), trait-zone channel, location names, primary color, min/max counts, symmetry, Megalo-active control, and lightmap-burn progress. Some may be content-specific or unused. Determine actual callback/tag/runtime support and H3 compatibility before proposing implementation or omission.

## Player/monitor and editor-state transitions

Static provenance for this section is recorded by `audit_editor_transition.py` in `isolated/full-re-transition.json` (13 original functions, body hashes, source lines and direct calls). Original image strings at `821312C8` and `821312D8` verify the names `forge_mode_play` and `forge_mode_edit`; they are used on opposite branches of `8244BEC8`.

Event 2 dispatches `8244BE08`. That wrapper compares requested mode with `82449A60`'s computed edit-state predicate. The predicate requires editor +0x14 to equal 1 **and** a valid player unit whose tag equals `8246B098`'s configured editor-unit tag. A stored mode bit by itself is insufficient. If a change is needed, request 1 invokes `8244F8A8`, otherwise `8244FC48`. Only a successful return commits the mode through `8244BEC8`. After committing play mode, a valid held datum is released through `82451500(player, held, 0)`.

`8244BEC8` stores the mode at editor +0x14, performs mode-specific local callbacks and signals, then calls `823C9B48` with 0 for play or 1 for edit. `823C9B48` may override that argument to 1 when `82372010` counts more than one locally relevant player. On change it visits all 651 variant object slots and calls `82939B70` and `82939C98` with the inverse flag before storing variant state +728. Those helpers change object flags and invoke further state/physics updates. This is additional world-object behavior coupled to the mode transition, not merely HUD/menu switching. Exact downstream flag semantics remain open.

The enter path `8244F8A8` requires a current player unit and a predicate check, obtains the configured editor-unit tag through `8246B098`, prepares a creation structure and calls `82933B30`. Failed creation returns false without the wrapper committing mode. Successful creation updates the old unit, reassigns player control through `82357E90`, adjusts position/orientation using original object helpers, and transfers two scalar properties outside session type 4. The scalar properties are not named health/shields until their helpers are independently mapped.

The exit path `8244FC48` locates the retained player object through `8244FFE8`, reverses old-object flags where available, captures current controlled-object state, invokes `82936B78`, and reassigns control through `82357E90`. For a valid restored object it restores movement/transform-related state and player updates, again transferring those scalar properties outside session type 4. `8244FFE8` selects an object with +1180 == -1, +1184 matching the player and +2044 == -1; ownership/attachment field names still need confirmation. The exit routine's terminal return is true even on several missing-object paths: do not invent a stricter success condition while porting.

Other callers must be preserved: `8244C580` attempts editor-unit creation when stored mode is 1 outside session type 4 and requests play mode on failure; `8244C6D8` requests play mode outside that session type before invoking `8244C620`. The surrounding lifecycle and input producer remain open, as do replication and multiple-local-player behavior. No native transition tests or H3 adapter equivalence are claimed by this static audit.

## Physics menu, held state and model-dependent application

`audit_physics_states.py` verifies the constructor `82687088`, original retail string identifiers and seven source function hashes. The physics control at constructor +640 points to the list at +208 and the property halfword at +138, with mask 0xc0. The list values are `0 = physics_normal`, `0x40 = physics_fixed`, `0xc0 = physics_phased`. This is not the same numbering as the runtime selector below.

`82449B18` searches player editor records for the supplied held object and returns its holder or -1. `82469630` follows object -> model -> physics model, then scans 192-byte bodies for motion byte +28 equal to 4. The local Gen4 PhysicsModel schema identifies 4 as **Keyframed**, 5 as Fixed. Therefore this predicate must not be named “has fixed body” or reused as a generic immovability check. It returns true if any scanned body matches.

`8244A180` selects runtime states as follows (valid variant slot required):

| Property | Held by a player | Not held |
| --- | --- | --- |
| Normal | 1 | 1 if special predicate `8244A5F0` is true, otherwise 0 |
| Fixed | 1 | 0 with a keyframed model body, otherwise 3 |
| Phased | 2 | 0 with a keyframed model body, otherwise 3 |

A non-variant object returns 0. `8244A5F0` additionally depends on game/global state and an object's runtime attachment block; its complete meaning remains unresolved. This table has been executed using the **unchanged original selector** in `test_physics_selector.cpp`: all 24 combinations of three properties, held/unheld, keyframed/no-keyframed and special/no-special pass, plus the non-variant case. World-query results are supplied as explicit data boundaries; this does not test the query implementations, application routine, networking or actual collision. Evidence: `isolated/full-re-physics.json` and `isolated/physics-selector-test.log`.

`8244A2A0` applies those states only after valid model/physics references are found. For the object's 64-bit flags at +0x100, state 0 clears masks 0x40/0x200000/0x400000; state 1 clears 0x40/0x400000 and sets 0x200000; state 3 sets 0x40 and clears 0x200000/0x400000. State 2 clears 0x40 and sets both 0x200000/0x400000 only for a locally relevant holder, clearing both otherwise. These are observed masks, not yet fully named collision properties.

The application routine then invokes `82388C68` or `82388A08` depending on body/state conditions, conditionally sets mask 0x400, and compensates held-object grab-offset fields for any position change caused by the operation. It adjusts editor +0x38/+0x3c/+0x40, resets +0x28 to zero and +0x24 to one. Omitting this compensation when changing physics can move the held object unexpectedly. H3's corresponding body update and offset semantics must be mapped before integration.

## Variant records, budget eligibility and live property updates

Original H4 functions establish a 651-slot, 76-byte object record array at variant +5356. Properties occupy 24 bytes at record +52; lock state is byte +51, outside the properties. `823C1D00` initializes the record with invalid indices at +2, +4 and +48, property defaults +12=8, +14=-1, +18=-1 and +20=-1, and lock byte zero. `823C2AE8` copies only the 24-byte properties, not the complete record.

`823C5C28` copies full records. Session type 4 explicitly checks slot 0..650; other sessions test the occupied bit before copying and initialize the output on failure. The latter branch does not itself provide the same explicit slot bounds check. `823C5DD0` validates the slot, copies 76 bytes, clears variant bytes +729/+730 for an occupied record, then invokes `823C6FA8` and `823C5858`. Thus the setter has live side effects and cannot be replaced with a byte copy alone.

`823C6FA8` visits runtime objects sharing the slot except the record's stored datum and calls `823C6B28`. That routine selects/applies physics (`8244A180` / `8244A2A0`), updates runtime properties, translates individual property flag bits, and dispatches type-specific fields. Types 32, 33 and 34 have separate extension copies; other branches include type-dependent byte +22/+23 handling. Their feature names, complete adapter semantics and network effects remain open. This establishes a real runtime consumer of the additional properties, not merely unused menu strings.

`823C5858` updates the recorded runtime object's pose through `823C5930` and `82932E28`. `823C5930` recursively resolves the signed parent slot at record +48 when not -1, builds the parent's basis and transforms the child's position and two basis vectors. Parent-relative placement must therefore be preserved; stored positions are not universally world coordinates. Helper equivalence, malformed-parent handling and serialization remain unverified.

Budget getter `823C5160` exposes variant +724 current and +720 maximum, returning their ratio only when maximum is positive. Eligibility `8244EF80` combines optional world-placement checks with a palette quota and budget test. `823C3498` searches quota definitions for the object's tag, scanning 72-byte entries and comparing tag field +16. `823C3700` resolves a 24-byte definition through palette/container indices. Eligibility rejects a missing quota, compares placed count byte +2 in variant +54832 + 3*quota against positive definition limit +16, and rejects definition cost +20 plus current budget above maximum. Full quota accounting, create/delete transactions and the palette resolver remain open.

H3 comparison: local TagTool `BlamFile/MapVariant.cs` defines 640 objects of 84 bytes, with 24-byte properties at +60. Spartan's existing slot iteration and native reload verifier agree on the H3 stride and capacity. Matching property byte counts do not imply matching layouts or semantics. Integration must translate audited fields and retain H3 serialization; it must not copy H4 records or silently raise H3's capacity. No native save/load parity is claimed.

## Movement producer chain and magnet threshold execution

`audit_movement_gate.py` records six original function hashes and extracts the unchanged `82582178`. `test_movement_gate.cpp` executes 216 cases covering all three axes, signed magnitudes below/at/above threshold, absent configuration, invalid tag, null resolver and valid configured thresholds, plus a combined-axis case. All pass; stack, saved r31, LR and resolver arguments/call counts are checked. The predicate is **strictly magnitude > threshold**; equality leaves alignment eligible. The magnitude combines all three components. The only substituted function is the configuration lookup; this is predicate evidence, not a complete native detach test. Evidence: `isolated/full-re-movement.json` and `isolated/movement-gate-test.log`.

The player path is now narrowed beyond the generic packet consumer. `8225CE30` takes a 256-byte per-player input record from input array +16 +256*player index, makes a local copy, passes it through `82368CE0`, conditional filtering and `8235DC98`/`822D6EE8`, then calls `823619F8` when the input type and unit mode match. Its separate direct call to `822562A8` is a different branch with an initialized packet; it must not be confused with the normal player packet producer.

`823619F8` constructs the 152-byte unit packet at stack +96. Input floats +28/+32 become unit-packet +32/+36; packet +40 starts at zero. It then calls `82361880(player, unit, player_input, packet+32)` before sending that packet to `822562A8`. Thus the vector inspected by the magnet predicate has an explicit player-control producer. Upstream device mapping and filtering are still open.

`82361880` may leave the vector alone for a selected equipment/tag branch. Otherwise it queries `82221B08`. Result 16 adds one to Z for input halfword +52 bit0 and subtracts one for bit1 (both cancel). Result 8 sets Z to -1 when the tested input flag is set, otherwise adds input +60 and subtracts +56. It also zeros X/Y when the player-state float at +2096 is zero. These are observed operations; button names are not yet assigned. `82221B08` returns 16 for the ordinary unattached path; a valid parent/seat chain can tail-call `822B3FF0` instead. This narrows the monitor path without assuming every controlled unit uses the same vertical controls.

Finally `822562A8` either copies packet +32/+36/+40 into unit +1348/+1352/+1356 directly or filters them using its unit/attachment state and movement coefficients. Its direct-copy branch is taken when unit +1156 is -1, +1180 is not -1, or the resolved control definition's leading halfword is 2. Confirming which condition applies to the configured H4 monitor remains necessary before choosing the H3 adapter. Raw stick magnitude and physical object velocity are not established substitutes for this processed vector.

## Placement update, bounds and physics target submission

`audit_placement_flow.py` records ten original function bodies, verifies nine scalar constants from the image, and checks ordering in both placement functions. It is static evidence, not an executed physics test. Report: `isolated/full-re-placement.json`.

`8244A8D8` and `8244B860` update the target translation at editor +124/+128/+132. Both derive horizontal movement from the controlled unit's facing and processed movement vector, and include its vertical component. A unit flag selects a 0.1 multiplier instead of 1; further scaling includes the unit tag field +1428, unit scalar +2168, constant 4 and the tick interval. Those tag/flag names are still unresolved. The first path also adds a displacement obtained through `8244B338`; it must not be collapsed into the second path without tracing that helper and branch selection.

Both paths call `82282580` with variant +696 before and after limiting the target displacement. That helper clamps X/Y/Z against three min/max pairs (24 bytes). Both call `8221CA38`, which limits vector magnitude to its supplied maximum and returns whether it changed it. They conditionally attenuate movement by a nonnegative dot product against a previous-target direction, and remove the component into a normal returned by `82235650`. The conditions differ: `8244A8D8` includes an extra global/editor-byte condition and only switches its limit to 0.5 for an actual removed component; `8244B860` sets 0.5 whenever that normal-query branch succeeds. The alternate positive-motion limit is 3 times the computed unit scaling. Full world-query semantics remain open.

After those operations, both copy the 52-byte editor transform, optionally quantize rotation and update cached orientation, apply magnet selection/movement suppression/alignment, then submit to physics with scalar 0.2. The selection wrapper always calls the visibility updater even when magnets are disabled, selection fails or movement suppresses alignment; disabled magnets pass candidate -1, while movement suppression retains the selected candidate identity. Detachment therefore does not imply clearing all selection/visibility state.

`82452930` resolves the object's physics instance, checks its body index, and forwards to `8249B418`. It has an additional object-type/body-flag path that updates object orientation, calls `822AAB18`, and replaces the submitted basis with an image-resident basis. `8244B860` calls `8249B418` directly for body zero. `8249B418` converts the target transform, computes reciprocal of the supplied scalar, invokes the original physics routines with current body transform +288 and related state +352, then sets object flags +256 mask 0x40000000. A direct world-pose assignment is not established equivalent to these target updates. Physics helper names and H3 mapping remain unverified.

The previously missing minimum-focal-distance consumer is `82451FC0`. It reads `82452B48`, which returns config +76 when greater than epsilon and otherwise 2. This path uses **L=max(minimum_focal_distance, tag_radius+0.4)** and **U=min(multiplier*L, maximum_distance)** before clamping editor distance +28. This differs from `82452738`'s runtime-radius lower bound; preserve both policies until caller conditions are fully resolved. When player byte +1888 is set, `82451FC0` calls rotation helper `8244B518` with player +1900/+1904/-1896, marks editor rotation byte +81, clears grab offset +56/+60/+64 and scalar +36 for nontrivial rotation, and subtracts player +1892 times 0.3 from distance. It then calls `8244B860` and proceeds through a separate controlled-unit physics adjustment. The producer of these player fields, branch selection and the later controlled-unit adjustment remain open.

## Placement dispatcher and coupled controlled-unit update

The expanded `audit_placement_flow.py` now records fourteen original bodies and verifies dispatcher ordering plus two image switch bytes. `8244D0E0` first requires the edit-state predicate, a held datum and the player predicate `822ED938` before applying placement. Its movement branch requires the held object to have no parent (+36 == -1), a valid physics instance (+240 != -1), and physics-instance flags +16 mask4. This is distinct from the earlier target-selection checks, which resolve attachment parents, variant/palette eligibility and object-type flags. The human meaning of `822ED938` remains to be traced rather than assumed to be network authority.

At that branch, global byte **8407EFFA** selects the two paths. Zero calls `8244A7D0`, subtracts editor +40 from +36 with a zero floor, calls `82452738`, then `8244A8D8` and `8244AF48`. Nonzero calls `82451FC0`. The original image contains zero at 8407EFFA; this proves the image default, not that no runtime writer changes it. No direct image pointer references were found, and the symbol/name and runtime writers remain unresolved. It is not a per-object Normal/Fixed/Phased selector.

`8244A7D0` consumes the same rotation input fields as the alternate path, calls `8244B518`, and accumulates its result into editor +81. If rotation changed or global byte **8407EFFB** is nonzero, and editor +40 is zero, it seeds +40 from the tick interval times the original scalar at 821289E0+48. The dispatcher then decays editor +36 with this value. Image byte 8407EFFB is also zero. This persistent scalar state cannot be discarded on each magnet evaluation.

`8244B338`, called by the main placement path when its initial vector magnitude exceeds epsilon, queries two positions through `824BEAD0` and `822410D0`. Let delta be the latter minus the former, and d its length. If d minus editor +32 exceeds 1, it overwrites the supplied vector with delta * ((d-editor32)/d); otherwise it writes zero. This is a distance-dependent correction, not a constant grab offset. The exact semantic names of the two queried positions remain open.

After submitting the held object's target, `8244AF48` computes a separate controlled-unit target using `824BEA10`, world queries and current unit position. It bounds a displacement to length2, optionally projects it away from a player-state normal, derives an orientation with a near-zero fallback, and calls `82452930` on the controlled unit with another original scalar. It then conditionally updates local-view state through `823FC348`, writes editor +32 from the resulting distance limited by its retained distance value, and updates directional history +276. Its world-query conditions and transform helper semantics still require auditing. This is evidence that held-object movement and controlled-unit/camera behavior form a coupled update; porting only the magnet-aligned object transform omits that behavior.

## Rotation eligibility, analog shaping and player placement gate

`822ED938` is now traced rather than labeled network authority by inference. It requires TLS +140's byte +104 to be nonzero, resolves the supplied player datum through `822714E0` using the player table, and compares six bytes at player +20 with TLS-block +105..110. All six must match. Missing enabled state or missing player returns false. The identity's name and its producer are still open; adapter code must preserve the actual identity rule rather than substitute an arbitrary local/host flag.

`8244B518` rejects an invalid held datum or a nonzero result from `8244A6A8`. The latter is a blocking predicate despite its positive-looking conditions. Zero (rotation allowed) requires a qualifying object type, object flags +256 mask0x100, a valid physics instance, and the body conditions below. For positive body count, every body must have motion byte +232 different from5 and physics-instance flags +16 mask0x80 must be clear. Zero body count passes those body conditions. A selected matrix of two object types, flag states, valid/invalid instance, zero/one/two bodies and body motion values executes the **unchanged original predicate** with no substituted callees: all96 cases pass. This covers the chosen matrix, not all object types or live physics. Evidence: `test_rotation_gate.cpp`, `isolated/rotation-gate-test.log`, and source hashes in `isolated/full-re-placement.json`.

For permitted rotation, `8244B518` constructs axes from the controlled unit vector +1260/+1264/+1268 and image-resident reference vectors, normalizes the view-derived axes, then weights the three input components as input*abs(input)*the original scalar at821289E0+48. It combines these weighted axes, normalizes the result, and multiplies the resulting magnitude by the tick interval. Only an angle above epsilon applies. It computes sine/cosine and an axis rotation through the original helpers, temporarily replaces translation +124/+128/+132 while composing the transform at editor +84, then restores those translation words exactly. The boolean result marks that rotation was applied. This establishes signed-square analog response and orientation-only composition; full basis/axis equivalence and native combined-input testing remain open.

## Creation and duplication transactions

`audit_creation_flow.py` records seven original functions and checks the successful creation call order. It is static evidence; allocation failure, replication and native workflows remain untested.

Event0 clears editor offset +56/+60/+64 and scalars +36/+40 before checking session type4. Outside type4 it passes packet palette indices +0/+4/+8, position +12 and default basis vectors to `824506D8`. That function returns without creating if the player already holds an object. Otherwise it resolves the quota and selected tag, checks `8244EF80` with a position, allocates a record through `823C5F58`, creates its runtime object through `823C6350`, and, for a valid runtime variant slot, calls the existing grab path `824511B0`. It then refreshes quota state and notifies the slot. Eligibility failure and record/runtime creation failure issue different feedback IDs (0x78004A versus0x780049); their display strings remain unresolved.

`823C5F58` checks the selected tag, positive quota limit and current count, then requests a free slot through `823C55E8`. It writes quota index at record +2, palette-item index +50, position +8, basis +20/+32 and scalar1 at +44. It initializes properties through `823C7378` and refreshes quota accounting. `823C6350` converts the record to a creation structure using `823C6678`, resolves the actual object tag, requires tag field +148 to be valid, applies creation flag0x100 according to its argument, and invokes `82933B30`. Success writes the runtime object's variant slot +62, applies record properties through `823C6B28`, invokes further world/notification helpers and returns the datum. The allocator, conversion, defaults and failure rollback still need tracing.

Event10 chooses the currently held object, otherwise the current target, for `82450970` eligibility. It releases that object with `82451500` (or `82451478` in session type4), clears the same offset/scalar state as event0, and outside type4 calls `82450AF8` using the packet's object and position. Do not assume the eligibility-selected datum and packet datum are interchangeable without checking the event producer. `82450970` additionally checks an editor-global count below32, valid player/object/variant, a slot in0..650, valid palette/container/item indices, then quota/budget eligibility without a position. The count's meaning is still unnamed.

`82450AF8` obtains the original record's basis if available, creates via `824506D8`, and if a newly held datum and original record both exist, copies the original24-byte properties through `824515C8`. It does not blindly copy the complete76-byte record or lock byte. `82451478` requires the specified datum to be currently held and valid, calls release `82451250`, then `823C5AB0`; the latter's effect remains open.

`823C5278` is the quota refresh consumer: outside session type4 it scans651 record quota indices (217 iterations of three76-byte records), accumulating a byte count. A change and successful `8222EB20` predicate trigger updates of quota bytes +1/+2, clamping through `8244A538`, total-cost recomputation `823C51D0` and a state-change notification. It always notifies the quota after the non-type4 path. This scan does not explicitly check the occupied bit: allocator/deletion invalidation of the quota index is part of the invariant that must be audited. Byte-width arithmetic and session conditions must not be silently replaced with a guessed counter policy.

## Slot allocation, recursive deletion and budget invariants

`823C55E8` scans slots0..650 in ascending order for a cleared occupied bit, calls `823C1D80` on the first free record, and returns that index. Full capacity returns -1. `823C1D80` clears the76-byte record, installs the invalid index/default-property values, sets occupied bit1 and sets property halfword +10 bits4 and8. Therefore allocation precedes tag-specific property initialization and runtime creation; failed creation cannot be assumed to leave no allocated record. The creation caller does not visibly free it on failure, so the downstream failure path still needs tracing.

`823C53F0` retains the old quota index, walks matching runtime objects by variant slot, conditionally calls `82936B78`, and clears their runtime slot +62 even on branches that skip that object operation. Its skip rules include a supplied excluded datum, object type/attachment state and `82258050`; those semantics remain open. It then clears the variant record and restores invalid indices/defaults, including quota index -1. After notification it scans all651 records and recursively processes each occupied child whose parent slot +48 matches the removed slot. Finally it refreshes the old quota when valid. This proves the quota-index invalidation relied on by the recount, and establishes recursive child deletion rather than orphaning children. It does not prove cycle handling or complete networking behavior.

`8244A538` normalizes the three-byte quota data. Let n be placed count byte2, a byte0, b byte1, and c the signed supplied definition limit when1..255, otherwise255. It leaves n unchanged, writes byte0=min(a,n), and writes byte1=min(max(b,n),max(c,n)). In particular, an existing count above the definition cap is retained rather than reduced. The unchanged original function passes1512 selected edge combinations, including limits -1,0,1,32,254,255,256 and count/min/max values0,1,31,32,254,255. Count and adjacent-byte preservation are checked. Evidence: `test_quota_clamp.cpp`, `isolated/quota-clamp-test.log`; this does not test the full editor lifecycle.

`823C51D0` recomputes current budget outside session type4 by scanning the signed quota count at variant +690. Each positive definition cost +20 is multiplied by placed count byte2; nonpositive costs contribute nothing. The sum uses original32-bit integer multiply/add semantics, is capped to signed maximum at variant +720, and stored at +724. Session type4 leaves it untouched. H3 integration must preserve meaningful quota behavior while respecting its own layout; native capacity/create/delete/budget and save/load sequences remain unverified.

## Tag-derived defaults and record-to-runtime conversion

`823C7378` resolves the object's multiplayer block at tag +392. Its flags halfword +28 bit1 sets both physics bits0x40/0x80 in properties +10; when absent it clears both. The local Gen4 `Object.MultiplayerObjectBlock` schema names this bit **PhasedPhysicsInForge**, consistent with the already traced Phased menu value0xC0. Thus default physics is tag-derived, not universally Normal.

The same initializer converts four boundary dimensions through `829D7760`, copies default spawn time (block +24) into property byte13, and multiplayer type (block byte1) into property byte9. `829D7760` multiplies each float dimension by256, truncates toward zero, stores the low16 bits in property halfwords0/2/4/6, and copies the boundary-shape byte into property8. It initializes its cached scale from original image constant821289E0+572=256. No saturating clamp is present in the observed conversion; input-range validation remains a separate concern.

The local Gen4 enum supplies meaningful names for the previously anonymous type branches:1 Weapon,12 Dispenser,20 NamedLocationArea,31 TraitZone,32 InitialOrdnanceDropPoint,33 RandomOrdnanceDropPoint,34 ObjectiveOrdnanceDropPoint and35 PersonalOrdnanceDropPoint. This schema is supporting evidence for names; original code establishes the actual behavior. Default Weapon byte22 is2; Dispenser byte22 is255; NamedLocationArea/TraitZone byte22 is0. Ordinary default branches copy tag teleporter-passability byte2 into property23. Initial ordnance clears property14 and halfword16; random ordnance initializes bytes14..21 to255; objective ordnance additionally initializes byte13 to255. Personal ordnance bypasses that ordinary tail. These types require explicit compatibility mapping rather than copying identical-size H3 property structures.

`823C6678` resolves the selected palette tag and initializes a runtime creation structure through `8297C8E0`. An invalid resulting tag returns false. Otherwise it copies palette override +20 into creation +12 when neither0 nor-1, record position/basis into creation +28/+40/+52, and record scalar +44 into creation +88. `823C6828` expands properties into that creation structure: boundary conversion, packed flag mapping, quota min/max, type, color, team, spawn time and type-specific fields. Types32..35 route to `8242B288`; TraitZone and NamedLocationArea have distinct byte22 consumers. Complete naming of every packed flag and ordnance payload remains open.

After property expansion, `823C6678` checks the two basis vectors through `822B41F8`, which checks each vector and rejects a nonfinite or insufficiently orthogonal dot product. Failed validation substitutes original default basis vectors rather than failing the entire object creation. It then calls `8297C338`, a further game-mode/type eligibility filter, and returns its boolean result. The filter and object constructor remain incompletely traced. No observed call in this conversion path explicitly clears the preallocated variant slot on failure; do not claim transactional rollback until downstream behavior is established.

## Creation filter stages and remaining evidence boundaries

`8297C338` starts with acceptance=true. If `82373220` is false it returns true without the filter stages below. `82373220` is the short-circuit OR of three game predicates (`8222AAD0`, `82293F20`, `82265430`); their names are not assigned here.

For the applicable game state, the creation metadata at aligned(creation+471) is filtered in stages. Byte128 values1/2 are compared with the result/inverse of the game variant's vtable callback +48, unless `8222EB20` bypasses this comparison. Nonzero low6 bits of byte129 restrict acceptance using a bit selected by the active game-engine vtable callback +0. Byte131 mask4 requests the game-engine callback +192 with the creation structure. Failed acceptance skips subsequent filters.

For a valid tag, game-options byte +984 mask2 gates metadata byte131 mask8. When the tag has multiplayer data, the other options bits independently reject multiplayer types: missing bit0 rejects Grenade(type2), missing bit2 rejects Equipment(type5), missing bit3 rejects Powerup(type4), missing bit4 rejects Turret(type10). Each restriction ANDs with acceptance; these are game configuration controls, not a blanket restriction on what Forge can create. Callback behavior, game-predicate naming and metadata producers still need mapping.

The `8222EB20` bypass is itself constrained: the editor/game global index at TLS+28 -> +50364 must be1..5, its original table entry must be nonzero, `82265430` must succeed and `821DF530` must return1. It cannot safely be stubbed as universally true merely because Forge is active.

Static tracing now identifies the call/field behavior through allocation, property defaults, runtime-creation setup and its filter. Remaining evidence work has different boundaries: (1) indirect game-engine callbacks and original object-constructor failure effects need source resolution or an original-code execution harness; (2) H3 equivalents for world queries, physics target submission and player input need direct H3 source tracing; (3) camera/grab/snap/detach, menus and save/load still need complete interaction tests and native capture. Existing predicate tests prove only their documented functions. None establishes the user-reported defects fixed. The full original-behavior audit remains incomplete, so production replacement remains deferred.

## Remaining event handlers and input producers

Static provenance: `audit_remaining_events.py`, output `isolated/full-re-remaining-events.json` records ten original function bodies and hashes. This is source tracing, not an executed editor sequence.

Event6 passes packet words0/4/8 to `82451680` as tag, requested minimum and requested maximum. After quota/definition lookup, an increased maximum is accepted only when current cost plus the increase times definition cost is strictly below the budget maximum. Equality retains the old maximum. This differs from ordinary creation eligibility, which permits equality. It writes the requested minimum, clamps through `8244A538`, notifies the quota, recomputes cost and signals mask0x10000000. Caller validation of the quota index remains an invariant to check.

Event7 invokes `823E7DD0(-1, 0, 22)`, rather than passing arbitrary packet arguments. That shared handler updates player/team scoring state, evaluates round limits, invokes transition helpers and clears associated player/team slots. Other reason branches in the shared routine are not automatically Forge features. The meaning of reason22 and the triggering UI action remain unconfirmed.

Event19 passes packet word0 plus the four-byte-aligned address `(packet+7)&~3` to `82451750`. For indices0..3, it resets then applies a256-byte configuration to both live state (`TLS+28 -> +12788+256*index`) and variant state (`variant+55724+256*index`), then signals mask0x40000000. Reset `822EF3D8` initializes structured defaults; application `822D5908` processes subblocks at0,64,180,208,236. A null source after reset leaves defaults. Producer `82714570` emits this event after accepted settings changes with setting identifiers180..183, using identifier minus180 as the slot and copying the live configuration into the packet. Exact configuration names and complete field semantics remain open; do not label these arbitrary byte copies or claim save serialization verified.

Event20 is part of the edit-to-play input path. In `8244CAC8`, the action at input-state offset32 emits event20 when `82449A60` reports edit mode; otherwise it emits event2 with requested mode1. After event20, the per-player editor byte83 is set by `82451800`, which starts `825FECE0(1)` and updates controlled-unit/view transforms under the identity gate. The input loop later observes byte83 plus global operation state zero, clears byte83 and emits event2 with requested mode0. Thus the original mode switch waits for an intermediate operation; it does not directly substitute event2 at the first button press. The menu callback `8278CF20` likewise chooses event20 versus event2 according to editor mode. The operation's purpose, failure/cancellation behavior and device-button mapping remain open; its function must not yet be called a lightmap rebuild on inference alone.

The same input producer resolves the earlier duplicate-datum ambiguity for this path: `8244CAC8` selects held datum when valid, otherwise targeted datum, into r28; checks `82450970(player,r28,0,0,0)`; then puts that exact r28 into event10 packet word0. Position comes from editor offsets44/48/52. This proves identity consistency for this producer, not all possible UI/network producers. The action is gated by valid target, no previously consumed action and `8244CA78` returning false. The handler's release/create/property-copy ordering remains as previously traced.

## Event20 identified: Forge lightmap baking lifecycle

The operation is now positively identified, rather than inferred from its timing: `825FEDB0` passes original image string at0x8213A370, `c:\midnight\main\shared\engine\source\blofeld\render\forge_light_baker.cpp`, to a scoped diagnostic helper. `82600478` opens string ID0x805EE, decoded from the original Ravine string table as `forge_lightmap_burn_in_progress_background`. Both reference the same global operation state at base0x834BF420 +105340. Provenance for five additional original functions and the source string is included in `full-re-remaining-events.json`.

`825FFCE8` clears its candidate count at+8048 and enumerates objects with type mask2048. It requires a valid object model, render model, render-model reference at+372 and a runtime object flag. It records152-byte entries starting+8056, including object datum and variant slot. The quick-query argument returns true after the first accepted object; the full enumeration caps at640, returning false if another iteration reaches that cap. The code writes invalid index -1 to runtime object halfword620 on a flag-rejected branch. The Gen4 render-model schema identifies the final tag reference as ForgeLightmapAtlases (`rmla`); complete runtime flag and atlas data semantics still need mapping.

Observed state progression:

- Start `825FECE0(1)` only operates while state0; a positive quick candidate query writes state1. Its false-argument branch writes state4.
- Update `82600478`: state1 opens the progress UI and writes2. State2 waits for UI readiness (or missing UI) before writing3. State4 also advances to3 under its external predicate. State0 releases a UI handle. State12 assigns object halfword620 to each retained candidate index and returns state0.
- `821D6EE0` handles state3 by first clearing it to0, performing the full candidate enumeration, resolving resources, and preparing data. Successful preparation writes5. Some failure/empty branches leave0, so return to play cannot be treated as proof that a bake succeeded.
- `825FEDB0` processes states5..11 when its renderer/configuration prerequisites are present; missing prerequisites reset0. It invokes `82603D88`; false resets0. At state11 it releases temporary render resources, marks result availability, resets progress counters, changes to12 and visits world objects through `8261FF10`.
- `82603D88` requires two renderer tag references at+976/+992. State5 sets up render state and advances6. State6 calls `82602C98` and advances7 when ready;7 invokes `82603870` then8;8 waits for `82603368` before9;9 invokes `826035F8` then10;10 checks additional scene/render prerequisites and `826060A0` before11. `825FF2E8` bounds continued processing. Individual pass meanings and its time-budget predicate remain unresolved.

This establishes a real render-dependent feature coupled to edit/play switching. Spartan currently has no identified Forge light-baker adapter; searching its host sources did not find one. Absence of a search match is not proof that stock H3 has no related lighting mechanism. H3 rendering, object lighting and save-format boundaries must be traced before proposing an implementation or asking for a concrete compatibility exception. Do not insert a fake delay, skip the operation silently, or claim an ordinary map lightmap rebuild is equivalent. No native bake/parity test has been performed.

## Magnet pair diagnostics: rotation preservation and overlap boundary

The selection fixture now directly executes original pair validator `82582E38` and alignment `82582AD0` for synthetic target-marker yaw0/90/180 degrees, identity held basis, distance0.1 and the original configuration. All three return accepted1, distance squared0.01, identity output quaternion and position(0.1,0,0). Near/far selection checks also pass. Evidence: `test_original_selection.cpp` and overwritten compact `isolated/selection-test.log`. All70 extracted original bodies were verified against generated source before rebuilding. Five unused external callbacks now throw if reached; the stale fixture previously failed to link after the extraction grew. These synthetic inputs do not validate the installed markers or reproduce complete H4 gameplay.

The actual alignment body explains why a simple marker-normal rejection would not be a source-backed correction. `82582AD0` first computes a candidate quaternion from target world rotation, a fixed rotation and inverse source local rotation. It then reads the held transform from editor+84, substituting the cached basis+136 when rotation mode+224 and dirty byte81 are both nonzero. It converts candidate and held quaternions to three Euler values through `82331BC8`; then copies all three held Euler values at stack96/100/104 over candidate values at80/84/88 before converting back through `82264A58`. Finally it positions the held object by subtracting its rotated source local marker position from the target world marker position. The observed identity results follow this explicit orientation-preservation sequence. Full multi-axis/gimbal behavior remains untested.

`82582E38` compares the held orientation reconstructed from marker world/local transforms with this returned alignment quaternion through `8232F8D8` (twice arccos of absolute clamped quaternion dot). It accepts only when angle is strictly below configured angular threshold and marker distance squared is strictly below configured radius-derived threshold squared. It does not directly compare opposing marker normals or test occupied volumes. `82582C80` ranks accepted pairs using weighted reciprocal squared distances to the editor point and between markers, with0.0001 added; it uses strict greater-than replacement and preserves iteration tie order. The held-marker distance accumulator is incremented by epsilon on each accepted target pair, so a mathematically simplified implementation must not silently remove this original ordering detail.

`82582250` selects snap state2 when score improves and the selected marker separation is strictly inside the radius-derived threshold. Otherwise, until any state2 result exists, it can return state1 for a nearby object's center within the original squared-distance bound4. State1 is marker visibility/candidate selection, not a snap. `82582610` walks to the root parent before retrieving up to32 markers; the current adapter directly supplies markers for the requested object. Parent/root behavior therefore also needs mapping.

Consequently the reproduced overlap cannot be assigned to a missing opposite-normal condition in this original pair routine. Next trace the surrounding movement/physics submission, object parenting and marker-data construction against H3. A custom overlap rejection might change H4 behavior and is not authorized as a substitute for that audit. No runtime fix or collision-parity claim is made here.

## Live application boundary: H4 physics target versus H3 pose replacement

Current `halo3mp/src/advanced_forge.cpp` hooks H3 `822837C8` and `8232E8B8`. On a snap it overwrites the supplied position and substitutes position/forward/up arguments through `PoseArguments`, then calls the original H3 callee. This is not the H4 enclosing movement controller. Provenance is recorded in `audit_physics_boundary.py` / `isolated/full-re-physics-boundary.json`, including the current adapter hash and seven original function hashes.

H3 `822837C8` reads the object's variant record, replaces supplied pose components, writes it through `821E25B0`, then invokes `8232E8B8`. The latter copies supplied vectors into local storage, calls `8210C1A8`, then `8232E698`. `8232E698` directly writes position at object+84 and basis at+96/+108, with a coordinate-range check for unparented objects, followed by world/physics notification helpers. This proves a direct pose mutation; downstream collision notifications must not be assumed to retroactively provide the H4 controller's behavior. Parenting, helper semantics and collision outcomes still need tracing.

H4 `82452930` selects the active physics body and passes the desired transform plus time parameter to `8249B418`. That routine computes reciprocal time, converts the transform, obtains the body at instance+48 +60*bodyIndex -> +52, prepares target data through `82C023E8` using body position+288 and rotation+352, and invokes `82C01FB8`. It then marks the owning object's flags with0x40000000. Invalid physics/body selection skips this path.

`82C01FB8` compares target/current position and has a large-error branch calling `82CD40A8`; it is therefore not exclusively a velocity controller in every case. Its ordinary path uses position error, quaternion error, current body vectors+432/+448 and time-scaled gains. It caps correction magnitudes using supplied fields+64/+68, adds corrections to current vectors, and invokes motion vtable slots+64/+68 after `82CD55F0` when changes exceed tolerance. This establishes a controller/physics submission boundary rather than an unconditional final pose copy. Exact callback names, exceptional direct relocation, contact solving and H3 equivalents remain open.

The current H3 override therefore bypasses this H4 target-controller path. Combined with the missing movement-suppression predicate, this is an evidenced integration mismatch relevant to overlapping and sticky snaps. It is not yet a demonstrated complete root cause or a passing fix. The next integration design must map the controller to H3 world/body interfaces and account for Normal/Fixed/Phased behavior, instead of layering an invented marker-normal or overlap filter onto direct pose writes. Original H3 variant serialization remains the output format; accepted map/runtime work is unchanged.

## H3 controller counterpart located

A search by instruction-sequence similarity located H3 `82629000` (`halo3mp_recomp.4.cpp`). Reading the complete body confirms matching target-error, quaternion-error, correction-cap and motion-callback structure with H4 `82C01FB8`; the similarity score itself is only discovery evidence. H3 has no direct generated call to this function, although it is registered as a callable original routine. Indirect callers and its actual existing runtime uses remain unproven.

The observed H4/H3 body-field correspondence is position288/224, quaternion352/288, linear vector432/384, angular vector448/400, and embedded motion object224/160. Linear/angular setters use H4 vtable slots64/68 versus H3 slots60/64. H4 activation helper `82CD55F0` corresponds structurally to H3 `82651968`; the large-error pose helper is `82CD40A8` versus `8265FD48`. These are source-observed field/call correspondences, not permission to reinterpret an H3 body as H4 memory.

Both controllers take target data with position0, quaternion16 and linear/angular target vectors32/48, plus gain vectors0/16/32/48 and scalar correction limits64/68 and relocation threshold72. Both compute positional and quaternion error, scale corrections by time and gains, cap magnitudes, then add them to existing body vectors. Both contain a large-error relocation branch. H4 additionally suppresses some callbacks for changes below a tolerance and examines a body-derived threshold; H3's final setters are unconditional. Therefore invoking H3's routine directly is not automatically exact H4 parity. The integration should preserve H4 control decisions and translate at the body access/motion-callback boundary, with original-code comparisons covering both ordinary correction and relocation paths.

H4 target builder `82C023E8` writes current position/rotation into the target data and computes requested linear/angular vectors from desired minus current transform and reciprocal time. It normalizes the relative quaternion, handles small rotation separately, chooses the shortest signed angular direction and writes the resulting angular vector. This explains why merely feeding desired position into the controller's position field would not match the existing H4 caller. Its numerical edge cases and the H3 transform/unit conversions remain to be tested.

This finding supplies a concrete H3 physics integration route without inventing a new collision rule. Next work is an isolated original-controller comparison with explicit body/callback adapters, followed by complete held-object state-machine integration. It does not establish native collision, released-object settling, network behavior or save/load correctness.

## Executed original physics-controller boundary

`extract_controller_test.py` extracts unchanged `82C01FB8` and its two original register save/restore helpers. Only external dispatch is redirected to test callbacks. `test_controller.cpp` loads the original image constants, supplies a synthetic body/motion table and captures activation, velocity setters and relocation. Unexpected callback addresses or receivers throw. Output is retained in `isolated/controller-test.log`; no game process or installed files are involved.

Eighteen cases cover each linear axis, requested speed -5/0/+5, time steps0.1/0.2 and a correction limit2. Nonzero cases reach signed limit2*dt on the requested axis with no cross-axis change, one linear callback, no angular callback and no relocation. Zero cases produce no motion callback. A separate position-error case crosses the relocation threshold and invokes relocation once, transferring target position10 into the synthetic body's current position. Original stack restoration is checked for the linear cases.

The first execution terminated with host floating-point exception0xC000008F: the zero-initialized PPC FPSCR was not seeded from the host before the original SIMD flush-mode changes. Calling `fpscr.loadFromHost()` at test entry corrected the fixture; original controller instructions were not modified. This is an isolated-test setup correction, not a production renderer change.

These checks establish selected arithmetic and callback behavior, not H3 adapter equivalence. Rotation, near-threshold callback suppression, original target-builder output, arbitrary body orientations, actual motion activation/contact response, and complete Forge state sequences remain unverified. Relocation and callback implementations are explicitly simulated and cannot establish collision correctness. The H3 body/motion adapter and native sequence tests are still required.

## Controller rotation, braking and tolerance tests

The same original-controller fixture now additionally passes24 angular cases: three axes, angles -0.5/-0.01/+0.01/+0.5 radians and both signs of each equivalent quaternion. Under the fixture gains and0.2-second step, the expected angular correction is clamp(10*sin(angle/2),-0.4,+0.4) on the selected axis. Each has one angular callback/activation, no linear callback, no cross-axis component and no relocation. This checks both capped and uncapped corrections and shortest-sign equivalence; it does not cover arbitrary initial multi-axis orientation.

A15-update sequence starts with linear velocity5 and zero target velocity. It brakes by at most0.4 per update, reaches zero and emits no additional callback after settling. A matching nonzero current/target velocity3 is retained with no callback. Two additional cases read the original callback tolerance at0x82000E04 and verify that half the tolerance suppresses a linear setter while twice the tolerance invokes it. Equality and all floating-point boundary cases are not covered. All new invocations check stack restoration.

Reproduction: `tools/h4-forge/test_controller.ps1` regenerates the unchanged extracted function, rebuilds the single retained fixture and overwrites its compact result log. It restores temporary-directory environment variables afterward. All18 prior linear cases and the relocation case continue to pass. Body activation, motion setters and relocation remain simulated: this establishes controller arithmetic and callback decisions, not actual H3 collision-world integration or native Forge interaction correctness. Original target-builder output, multi-axis transforms and real H3 callbacks remain next integration-test gaps.

## Executed transform-to-controller chain

The fixture now extracts and runs original target builder `82C023E8` followed by original controller `82C01FB8`, including the original acos wrapper/implementation and register helpers. Extraction resolves the dependency closure (six functions), and the runner first checks all70 reusable original bodies against their generated-source hashes. No replacement trigonometric function or guessed target-building formula runs in place of the original code.

Twenty-four chained cases cover three axes, displacements -0.01/+1, angular displacements -0.01/+0.5 radians and both equivalent quaternion signs, using identity current orientation and reciprocal time5. Builder outputs are checked against displacement*5 and angle*5, with tolerances1e-5 and1e-3 respectively; the latter allows the original reciprocal-square-root/acos approximation. The builder retains the current transform, rather than copying the desired transform into target position/orientation. The controller then produces the expected capped linear/angular velocities without relocation. Earlier linear, angular, relocation, braking and tolerance checks still pass.

This connects requested transforms to controller callbacks in original executable logic. It also narrows the relocation finding: although the generic controller contains a large-error branch, this tested Forge-style builder feeds current position into that comparison, producing zero initial positional error. The desired displacement is represented in the target velocity instead. Concurrent world/body changes and other callers can differ; do not claim relocation impossible globally. Actual H3 body adaptation, nonidentity/multi-axis current orientations, native contacts and editor lifecycle remain unverified.

## Native activation boundary and motion-type incompatibility

The complete activation helpers are now traced and executed: H4 `82CD55F0`, H3 `82651968`. Both skip waking when island-state bits4..5 are nonzero, when the body has their fixed-motion value, or when body world pointer+8 is null. H4 reads island pointer+200 / island flags+38 / motion type+232, while H3 uses+144 / +40 / +168. Crucially the fixed-motion value is5 in H4 and7 in H3. Numeric motion values must not be copied across generations.

On activation H4 clears halfwords+234/+236, wakes through `82CE1B98`, then calls `824A5118` on body+224 with world bytes813..815. H3 clears+170/+172, wakes through `8265B720`, then calls `8226B190` on body+160 with world bytes733..735. The adapter should call the native H3 helper on the real H3 body; it must not copy H4 island pointers or reinterpret its motion enum. This does not yet prove matching world wake effects.

`test_activation.cpp` executes both unchanged original helpers across144 cases (two engines, four island-state combinations, nine motion types, world present/absent). It checks the actual gate, halfword preservation/reset, callback arguments and order, stack, LR and nonvolatile r31 restoration. Wake/setup callbacks are simulated. It specifically exercises the differing type5/type7 behavior. Null island pointers, all flag bits and actual world scheduling are not covered. The shared controller runner regenerates and runs both fixtures, retaining only their current binaries/logs.

Relocation wrappers are also traced: H4 `82CD40A8` calls motion vtable slot56 on body+224 then `82CD3ED0`; H3 `8265FD48` calls slot52 on body+160 then `8265FB88`. Any native relocation adapter must preserve that post-transform synchronization call. Its downstream world/shape update semantics and live execution remain open. No production code or installed build was changed.

## Original variant serialization entry points

`823C3930` writes the H4 variant stream and `823C3D30` reads it. Provenance and static capacity/version assertions are in `audit_save_flow.py` / `isolated/full-re-save.json`. The writer first invokes metadata codec `823A90D8`; it then writes version from+688 in8 bits, two32-bit fields at+732/+736, quota count+690 in9 bits, field+692 in32 bits, boolean fields+729/+730, six32-bit bounds values from+696, and budget max/current+720/+724 in32 bits each. It encodes the block at+740 through `823CA8C8`, then all651 object slots through `823C97D8`, quota triplets through `823C1F00`, and four256-byte configurations starting+55724 through five subblock codecs.

The reader decodes metadata through `823AA698` and requires version exactly50. It accepts quota count0..256, decodes corresponding fields/block, visits651 object records, reads quota triplets up to the declared count and clears remaining triplets to256. It decodes the same four configuration blocks. Its returned boolean is tied to the observed version/quota checks; downstream stream-error handling must be audited separately. This function alone does not prove robust rejection of all malformed input.

Object writer `823C97D8` writes a single absent bit for an unoccupied slot. An occupied record writes presence, two flag bits, quota index through `823CB048`, palette item through `823CB118`, position through `82814708` with precision argument21 and variant bounds, basis through `823CB1E8`, parent index plus1 in10 bits, scalar+44 through a6-bit real codec, lock byte51 as one bit, and properties+52 through `823C7530`. Runtime datum+4 is not written by this object codec. Exact quantization ranges and helper encodings remain open; precision argument21 must not be represented as an unquantized float.

Reader `823C9A08` first clears76 bytes, restores invalid runtime datum/quota/parent defaults, and initializes property defaults. Presence gates further reads. It decodes corresponding flags, quota, item, bounded position, basis, parent, scalar, lock and properties using paired helpers. This proves that lock state and the four configurations are serialized; they are not merely transient UI state. Object parenting must remain coherent when translating to H3's smaller slot capacity.

H4 version50 /651-record serialization must not replace H3's native saved format. H3 field-level correspondence for lock, scale and these configurations still needs explicit resolution; matching byte sizes are insufficient. No H4 round-trip, malformed-stream test or native H3 load test was executed in this audit step. The codec entry points now provide concrete roots for those checks instead of relying on runtime record layout alone.

## Native H3 save boundary

Original H3 decoder `821E01E0` is now included in the reproducible save audit. It bounds variant objects at640 and quotas at256, and walks84-byte records. Occupied records decode16-bit flags, a32-bit quota index, an optional64-bit parent identifier, bounded position and forward/up axes. The parent identifier is not H4's numeric parent slot; a slot-index copy is invalid.

The decoded H3 properties occupy record offsets60..83: engine flags60 (16 bits), placement flags62, team63, shared storage64, spawn time65, object type66, boundary shape67, then radius/width68, length72 and positive/negative heights76/80. Shape-dependent dimensions use16-bit real decoding. The separate TagTool H3 schema agrees with these fields. This decoder has no dedicated per-instance scalar or lock field, and no equivalent of the four H4 configuration blocks was identified here. This is an integration gap, not authorization to repurpose spare flags or change native H3 serialization. Writer tracing and an executed native save/load round-trip remain open.

H4 property writer `823C7530` and reader `823C7C88` are also recorded by hash. They use a type-dependent property union rather than a raw24-byte copy: after a boundary helper, type at property offset9 is encoded in6 bits and the halfword at10 in10 bits. Types32..35 take distinct branches; type35 skips the subsequent common payload. The ordinary branch uses dedicated codecs for offsets12,14 and18..21, then further type-specific encodings for22/23. Consequently equal in-memory property sizes do not establish field or wire compatibility. Full helper widths, meanings and round-trip tests remain open. No installed files or production Forge behavior changed in this audit.

## Executed property encoding helpers

`test_property.ps1` extracts four unchanged original functions and executes30,098 cases across every buffer alignment where the entire encoded value fits. It verifies exact bits, bit counters, preservation of the existing prefix, stack, LR and nonvolatile registers. A further266 cases verify the requested external flush arguments for the two single-write encoders with a full buffer. The flush callback only records requests: actual flushing, compound writes crossing the buffer boundary, decoding and native variant round-trips are explicitly untested. Source hashes and the single current result log are retained under the isolated research directory.

- `823B5938`: signed byte plus1 in4 bits; tested domain-1..8. Used for property offset12.
- `823CACB0`: byte255 becomes a single1 bit; otherwise0 followed by the8-bit byte. All256 byte values tested. Used for offsets18..21.
- `823CAD80`: (byte+1) modulo256 in8 bits. All256 values tested;255 encodes zero. Used for type20's offset22.
- `822F0788`: signed byte-1 becomes a single1 bit; otherwise0 followed by3 bits. Tested domain-1..7. Used for ordinary properties offset14. Values outside that range have not been asserted valid.

Boundary writer `829D7080` was additionally traced, not executed: shape byte+8 uses2 bits. Shape1 writes halfword+0; shape2 writes+0,+4 and absolute signed+6; shape3 writes+0,+2,+4 and absolute signed+6. Each dimension occupies16 bits. Shape0 has no dimensions. The negative-height magnitude conversion and differing dimension representation mean the H3 float boundary fields require conversion rather than copying. The signed-32768 edge and paired reader still require execution checks.

## Original grab / held reset / re-grab sequence executed

`test_grab.ps1` now extracts and executes unchanged `82450E10`, `82449ED8`, `82452738` and their original register-save/restore helpers. The fixture runs300 sequences (600 grabs): first grab, original held reset to released, changed view-distance input, second grab and reset. Coverage spans three view axes, five radii0.1/1/4/10/20, five projected distances-2/0/3/12/30, the player-offset compensation flag off/on, and local/non-local identity results.

Every grab checks the original projected distance and radius clamp, selected datum, pose callback count, stored object-position snapshot, and retention of magnet-enabled byte82, rotation mode224 and sensitivity268. Every release reset checks invalid selected datum and restored default focal distance. Stack/LR are checked after each call. The second grab uses a changed projection, so retaining the old grab distance cannot satisfy the expected result. Non-view axes contain large values to distinguish projection from Euclidean distance.

The fixture supplies controlled world/configuration services: unparented scenery, valid physics handle, in-bounds pose, fixed view axes, configuration multiplier5/max22/default7.5. Local identity has no selected monitor and no replication recipients. It does not execute the complete release event, real physics, visibility effects, multiplayer, parent detachment, weapon/vehicle branches or live H3. Unexpected calls on excluded branches fail explicitly. This is original lifecycle arithmetic/state evidence, not native proof that the reported bug is fixed.

The tested clamp order includes large radii where max22 is below the radius-derived minimum; original behavior returns22. Do not silently alter this ordering into a different clearance policy. The production `advanced_forge.cpp` hook still explicitly limits its workaround to the palette-create caller and excludes re-grab. No production implementation was changed by this fixture.

## Executed original release handler and rejection branches

The retained grab fixture now additionally extracts original `82451500` (release event) and `82451250` (release transaction), with the original register helpers. It replaces the earlier direct held-reset invocation with the actual release event. The expanded1200 sequences execute2400 grabs and2400 release events, including pose-restore byte280 off/on and release argument r5 off/on in addition to the previous axes/radii/distances/compensation/locality combinations.

When byte280 is set, the test checks that original release calls `8281EF50` while the selected datum is still present, with position at editor+324 and basis vectors at+288/+312. The callback is an argument/order probe, not real pose restoration. Then the original transaction clears held state. With r5 true and the fixture's zero property flags, it sets property bit0x40 through the variant setter and selects the corresponding two physics callbacks. With r5 false it takes the alternate callbacks, including `8244F300`. World effects of those callbacks remain simulated, so these checks establish branch selection and ordering only.

Six additional executed cases cover invalid placement deletion in session0, bypass of that deletion in session4, ordinary eligible release, stale datum mismatch, null object resolution, and an attached parent's bypass of root physics updates. The invalid-placement delete probe verifies held state was cleared before deletion. Stale datum and null resolution retain the selected datum and perform no tested physics callbacks. The parent case does not test real parent transform or detach behavior. Property bit0x80 forcing the r5 path, recipient replication, actual restoration, multiplayer and native H3 physics remain open.

Reproduction remains `test_grab.ps1`, overwriting its existing extracted source, binary and compact log. No extra build copies or installed runtime changes were made. The earlier300-sequence result describes the prior reset-only scope; this1200-sequence run supersedes it for the selected release path, without closing native parity or the full RE ledger.

## Control-type selector: default monitor path versus VTOL

`822B3FF0`, reached from `82221B08` only for the qualifying parent/seat chain, resolves a vehicle object. With runtime override byte3856 set, it returns signed byte3857. Otherwise it scans15 tag blocks at tag+1556 with12-byte stride and returns the first nonempty block index, default16 if all are empty or resolution fails. The installed Gen4 TagTool schema independently gives object size0x204 + unit size0x40C + vehicle flags4 =1556, followed by exactly15 physics-type blocks. Index8 is `TypeVtol`. `audit_movement_gate.py` now verifies these offsets/order against the checked-in local schema and records original selector provenance.

Thus the observed result8 branch in `82361880` is a vehicle/VTOL-specific control path (subject to the runtime override), not the default monitor control path. `82221B08` returns16 when the player has no unit, the unit's seat halfword44 is invalid, the parent does not meet the type/controlled-child checks, or the vehicle selector falls back. For an unattached monitor, result16 applies: input halfword52 bit0 adds1 to Z, bit1 subtracts1, both cancel. The equipment exception can still bypass this processing. The current player-state gate can zero X/Y afterward; button names and downstream filtering are not established by this selector trace.

This removes a potential erroneous adapter choice: do not feed the VTOL analog fields56/60 into ordinary monitor detachment. Original movement-predicate tests remain valid, but complete packet-producer execution and H3 equivalent fields remain unverified. A broad opcode-similarity search produced no strong H3 match; none of its candidates was accepted as a counterpart. No production behavior changed.

## Player-controlled units bypass H4 AI movement smoothing

Original player-unit assignment `82357E90` resolves the player from TLS+24 with4144-byte stride. On a change, the previous controlled unit gets owner+1180=-1 and previous owner+1184=player; the new unit gets owner+1180=player and previous owner+1184=-1, and player+36 becomes the new unit datum. These writes give the previously unnamed+1180 field an explicit ownership producer.

Consequently a successfully assigned, player-controlled monitor satisfies `822562A8`'s +1180 != -1 branch to82256A8C, which copies packet movement+32/+36/+40 into unit+1348/+1352/+1356. It bypasses the AI/control-definition smoothing branch even if an actor datum exists. This narrows the monitor behavior from the earlier open question: the magnet predicate sees the player-control vector after `82361880` preprocessing, not physical velocity. The branch still requires current ownership; do not apply this conclusion to unassigned AI units or ownership transitions without checking state.

H3 assignment counterpart `821E9028` was located and its body inspected. It resolves TLS+96, player stride880, controlled unit at player+40; old unit owner+380=-1 / previous owner+384=player, new unit owner+380=player / previous owner+384=-1. Its object table is TLS+168. The ownership semantics match, but surrounding side effects and layout differ. `audit_movement_gate.py` records both original bodies and asserts the specific ownership writes. This is a useful anchor for H3 input mapping, not permission to infer movement-field offsets by subtracting a constant.

H3 movement-vector consumers/producers remain unresolved. Candidate searches for offsets412 and548 did not establish an equivalent and no production adapter uses them. Next trace from the actual H3 player-input producer into its controlled-unit update, then execute the complete H4 preprocessing/copy/predicate chain and compare the mapped H3 path. No runtime code changed in this source audit.

## H3 control-vector producer and unit write identified

`821EC0E0` builds the native H3 unit-control packet at stack+128. Player-action floats+20/+24 become packet+20/+24; Z starts zero, action halfword+40 bit0 sets it to the original one constant, and bit1 subtracts one. Both vertical bits cancel. The routine invokes `820B8608(unit, packet)`. That function resolves the native object table through TLS+168 and copies exactly packet+20/+24/+28 into unit+496/+500/+504. It also writes triggers, aiming/facing data and flags; the movement triplet is not an inferred offset shift from H4.

Caller `820B6EA0` invokes this producer only when the action record's first word is1 and its context byte+4 matches unit+520. It supplies player+40 as the controlled-unit datum. These gates matter: do not unconditionally treat arbitrary action buffers as current monitor controls. Exact editor context entry and tick ordering relative to the Forge placement hook still need validation.

This establishes the candidate adapter mapping for the player-controlled paths: H4 processed control triplet+1348/+1352/+1356 corresponds to H3 native control triplet+496/+500/+504. H4's human-ownership branch copies its packet directly, while this H3 writer does the same. Read actual native fields after the producer, rather than host input or physical velocity. Complete producer execution, context transitions, update ordering and native detach behavior remain unverified, so this mapping has not yet been installed.

A primary-source community header was used only as a discovery aid: https://github.com/twist84/ManagedDonkey/blob/main/game/source/units/units.hpp names throttle/control-throttle fields for its own version. That version's layout was not copied. All H3 offsets above were independently checked in the original generated executable functions; the reproducible movement audit now records their hashes and specific load/store assertions. Earlier unsuccessful searches at412/548 are superseded by this trace.

## Executed H3 input producer to original H4 movement gate

`test_input_chain.ps1` extracts unchanged H3 `821EC0E0`, `820B8510`, `820B8608` and original register helpers, plus H4 `82582178`. It loads the existing H3/H4 guest images into separate isolated memory regions and uses their actual constant data. The H3 packet producer and packet initializer execute; the writer's actual movement stores execute. Only orientation conversion, libc memset and the final world-notification callback are supplied by the fixture. The notification arguments are checked.

The adapter boundary copies the proven12-byte triplet from H3 unit+496 to H4 unit+1348 in separate fixture unit records. Original H4 predicate then evaluates it using the absent-config fallback0.5. Three hundred cases cover X/Y values-1,-0.5,0,0.5,1, four vertical bit combinations, and movement -> stopped -> resumed phases. Checks include all three produced vector components, strict greater-than threshold behavior, vertical cancellation, one world notification per write, stack and LR. All pass. No raw host input is injected.

This proves the selected H3 producer/write semantics and that those native field values drive the original H4 gate as expected. It does not execute H4's upstream packet producer, H3 action context selection, actual marker alignment suppression, tick ordering, native physics, stale-datum behavior or user-visible detachment. Those integration gaps remain explicit. The fixture retains one extracted source, executable and compact log, and leaves production code and installed files unchanged.

## Correction: H3 mode-event dispatch is not the held-preview update

The shared pose-setter hook's comment incorrectly called the direct invocation at82280B60 a held-object preview. Original `82280948` shows that this invocation receives player+40 (the controlled unit), while its separate held-object updates resolve the edited variant slot and call `822837C8`. The comment in `advanced_forge.cpp` is corrected; executable behavior is unchanged. Any earlier proof relying on that caller as held-preview evidence is invalid and must be replaced with the actual held-object update path.

`82280948` is reached indirectly: guest-image engine object827A33B8 points to table82040D68, whose slot288 contains82280948. `824424D8` resolves a valid player/unit, obtains the active engine through820B07F0, reads its table and invokes slot288 with an event type and packet. `82280948` accepts event type33 and dispatches packet subtype0..7. The subtype branch at822809C4 tests mode transition, can apply a held variant pose, then uses player+40 for the direct native pose call before calling82280720. These operations must not be conflated with continuous dragging.

Static provenance and original table bytes are recorded in `isolated/h3-placement-dispatch.json`. Direct-call graph searches miss this indirect edge. The main update820B37D0 calls820B6610 before820B6EA0, but each can reach placement-related work on different branches; that alone does not prove the input age for continuous held movement. The real held update and dispatch ordering remain next, followed by native sequence evidence. No game was launched or installed code changed.

## Next audit work

Trace the movement/input packet producers and monitor branch, the two placement paths, rotation-snap consumers, complete grab/release lifecycle, property bindings and protected-delete rules. Extend discovery through indirect callbacks, palette/budget and saved-variant paths. Resolve the additional feature candidates against real consumers and H3 compatibility. Only after the original behavior specification is complete should Spartan integration be replaced. Native full interaction verification remains mandatory afterward.


## H3 continuous held update: original call boundary

Static audit `tools/h4-forge/audit_h3_held_update.py` records six original bodies and validates the original image pointer at engine vtable82040D68 +104 ->82282378. This wrapper calls82281A98 for a player with a controlled unit. Its indirect dispatcher and relative ordering against unit input processing remain unresolved; no runtime ordering claim follows from the pointer alone.

82281A98 resolves the held variant record and editor object, applies eligibility checks, and calls8227FA50. For active player adjustment byte764 it also calls8227F768 using floats772/776/780 and adjusts the per-player scalar from float768. The subsequent inactive transition calls82284078 once and clears engine byte58520 +playerIndex. This is distinct from the mode-event controlled-unit relocation at82280B60.

8227FA50 branches on8227F578. Its ordinary physics branch computes linear/angular control and calls820F29C8; BOTH branches then reach822837C8 (the final call has null orientation pointers). Thus it is incorrect to describe this function as exclusively a physics or exclusively a direct-pose path.8227F768 first calls8227FA50; its ordinary branch shapes rotation input and submits820F29C8, while the alternate branch constructs orientation and calls822837C8 with a null position pointer.82281A98 additionally has a conditional large-displacement correction through822837C8 before its regular movement call. Any adapter must distinguish these calls rather than assuming one pose callback per frame.

8227F578 checks object type/body availability and body motion classes6/7 before returning its branch selection; a true result alone must not be named a Forge menu mode.820F29C8 calls8232EA98 and820F2AE0, with additional nonzero-motion activation calls. Complete setter semantics and engine ordering remain open.

Validation: the static audit passed, verifying call presence and the original vtable pointer. This is source evidence only, not an executed drag sequence. No executable behavior or deployed files changed in this step.


## H3 engine dispatch and tick-stage ordering resolved statically

Follow-up to the preceding held-update audit:82219898 is the indirect caller. It reads engine kind from TLS100 +81228, selects the engine object from827E6980, then invokes vtable slot104 with the player datum. Original image entry5 points to827A33B8, whose vtable is82040D68; slot104 is82282378.820D3E40 iterates players through820B7750 and invokes82219898, which reaches82282378 ->82281A98 for Forge. No guessed interface slot is needed.

The original tick820B37D0, after its update-enabled gate, calls820B6EA0,821B4170,821C9818,820B8840,820E3B10, then820D3E40 without an intervening conditional branch. Therefore the unit input-processing stage precedes this continuous Forge update within that tick.820B6EA0 conditionally invokes821EC0E0 after action validity, live-unit, control-context and other gates; a missing/filtered action does NOT imply a fresh movement vector. Its alternate control path initializes a packet and writes through820B8608 as well. Intervening subsystem effects on the vector, exceptional context paths and native moving/stopping/detaching remain unverified.

Updated audit verifies ten original function bodies, pointer table ->engine object ->vtable ->slot, the indirect-call instruction sequence, and stage call ordering. It passes. This closes the previously unidentified indirect dispatcher and static stage-order question, not runtime field lifetime or functional magnet parity. No production behavior changed.


## Executed H4 monitor input processor and unit-writer boundary

Extended `extract_input_chain.py`/`test_input_chain.cpp` to extract and execute unchanged82361880,82221B08 and822562A8 plus their original register save/restore helpers.600 cases exercise unattached control type16 with five values on each horizontal axis, four vertical flag combinations, XY enabled/disabled, and initial Z -0.25/0/0.25. Original processor preserves or suppresses XY according to player field2096; vertical buttons add/subtract1 and cancel when both held. Stack/LR checked.

For each processed triplet, two writer cases exercise no AI datum and an AI datum with assigned-human owner1180=0. The fixture explicitly copies the processor result into packet32/36/40; it does NOT execute the enclosing packet producer823619F8. The unchanged writer822562A8 overwrites stale7.0 controls, records previous-request fields1372/1376/1380, and transforms to world fields1384/1388/1392 using a simulated identity basis. Then unchanged82582178 evaluates the actual unit1348/1352/1356 values. All1200 writer/predicate chains pass, including the strict0.5 threshold boundary and horizontal suppression. This executes the formerly static direct-copy ownership finding.

Equipment resolver is simulated absent; unexpected equipment/vehicle/AI-smoothing branches throw. Object basis and world notification are simulated. Default configuration fallback0.5 is used. These are controlled original-function tests, not native game execution or a complete input/packet path. VTOL controls, equipment overrides, full producer823619F8, real transforms and native magnet detach remain open. Existing300 H3 producer/writer-to-H4-predicate cases also still pass. One fixture binary/log and hash manifest are updated in place; production code/install unchanged.


## H4 enclosing input producer executed through the movement gate

The input-chain fixture now includes unchanged823619F8 and packet initializer8229D0F8. The original producer copies action28/32 into packet32/36, initializes packet40 to0, calls82361880 on that triplet, then calls822562A8. Thus the new test no longer manually copies a processed vector across the packet boundary. Earlier1200 boundary-isolated cases remain useful as distinct writer ownership coverage.

1800 additional cases pass: five horizontal values per axis, four vertical flag combinations, XY enabled/disabled, action byte232 values0/1/2, and moving -> stopped -> resumed. Tests verify unit1348/1352/1356, original magnet predicate output, stack/LR, and player halfword1160 behavior (retained for mode0, cleared for1, set for2 on the unattached branch). This verifies the original producer/initializer/processor/writer call chain for the selected ordinary human-monitor path.

Explicit test services: equipment override absent; session query0; action extension no-op; unit capability query false; orientation conversion and object basis identity; notification checked by datum; memset implemented directly. Animation/vehicle/AI-smoothing branches throw if reached. Attached vehicle, equipment override, special session/action extensions, real orientation conversion and native snap behavior are not covered. All earlier600 processor,1200 writer-boundary and300 H3-adapter cases remain passing in the same bounded fixture build/log. No production changes or deployment.


## Executed magnet caller after original input chain

Extended the same fixture with unchanged8244EED8,8244A118 and quaternion-to-matrix82282728. The1800 enclosing-input cases now invoke the real caller after the real input chain, retaining candidate state across each moving/stopped/resumed triple. Candidate service82582250 is explicitly simulated as result2/datum7; alignment geometry82582AD0 returns a controlled identity quaternion and position101/102/103. They are not original-world geometry tests.

Verified: movement above0.5 suppresses alignment and leaves all52 bytes of the requested transform untouched; stopping/threshold equality permits alignment and the original matrix conversion/translation writes. The selected candidate is retained in editor+4 even when alignment is suppressed. Local and nonlocal visibility paths are exercised via a controlled822ED938 result.

The first test failed because it expected visibility service825826B0 to receive the NEW candidate. Original8244A118 loads held/candidate from TLS editor6892/6896 BEFORE storing the new candidate to passed editor+4, then sends the previously loaded pair to visibility. Corrected the fixture expectation from that instruction ordering; subsequent runs pass, including retained candidate across consecutive frames. This is a real adapter requirement: clearing candidate state when movement suppresses alignment would not match this caller. Actual visibility service and candidate search/alignment geometry remain separate coverage; physics submission and native detach are not proven by this test. Production/install unchanged.


## Executed physics-instance submission through original controller

Extended controller extraction with unchanged8249B418,82301320,82C95448,82C01E90 and register helpers. The wrapper now executes its actual transform conversion, matrix-to-quaternion conversion, body-table selection (60-byte stride, pointer+52), reciprocal time, gain setup, target builder82C023E8 and controller82C01FB8. Only the existing external motion/activation/relocation callbacks remain simulated.

48 submission cases pass: body indices0/1, all three axes, displacement -1/0/0.01/1, intervals0.1/0.2. Non-selected body pointers deliberately differ, and callback receiver checks reject wrong-body selection. Tests start at translated positions(2,3,4), verify expected signed velocity corrections using the original limit constant, unchanged current positions, no angular update/relocation, original stack/LR restoration, and preservation of existing64-bit object flags while ORing0x40000000. The previously tested controller/target-builder and activation suites still pass. This closes the manual transform/body/gain setup gap for these wrapper cases; no collision-world or native-game evidence is implied.

Still open:82452930 object/physics-instance resolver and its special orientation path, mixed-axis rotation through the submission wrapper, invalid instance/body paths, full placement-update-to-controller sequences and H3 body/collision integration. No production/deployment change.


## Executed object-to-physics resolver

Controller fixture now extracts unchanged82452930 and its original52-byte transform copy. Each previous48 physics-instance submission case is also run from an object datum through its actual physics instance lookup, signed body-index selection, then8249B418 ->82C023E8 ->82C01FB8. Total96 submission cases pass. Original global83625160 points to the synthetic physics datum table; original176-byte instance addressing and60-byte body-record addressing are exercised. Ordinary object type1 avoids the separate type0 special-orientation branch, whose callbacks explicitly throw if reached.

Five additional original rejection cases pass: object physics datum -1, resolved instance address zero, signed body index -1, index equal to body count2, and index127. They preserve owner flags and stack/LR and emit no motion/activation/relocation callbacks. This confirms actual early returns rather than a test-side validity filter. The existing144 H3/H4 activation checks also pass.

Special orientation handling, rotated/mixed-axis wrapper cases, genuine physics-world contacts and full held-object update integration remain open. This is stronger original-function evidence, not a native defect fix or deployment.


## Executed special orientation branch in object resolver

Controller fixture now includes unchanged8257FB98 and8229D390 rather than throwing on special orientation. Original global833F7EAC points to82125188, whose vector is(0,0,1). For type0 objects,82452930 scans every60-byte body record for byte56 bit0; a qualifying flag on another body also enables this branch. It projects the desired forward direction onto XY, normalizes it, falls back to original(1,0,0) for a vanishing projection, and stores forward at object112 and UP at124. It then replaces the physics submission basis with the original identity basis. It does not submit the object's flattened yaw as the rigid-body rotation.

24 cases pass: object types0/1; no body flag, first-body flag, second-body flag; four facing directions including a pure vertical direction. Original normalization and matrix operations execute. The simulated822AAB18 notification checks the previous forward vector and the already-written new forward vector. Special cases yield no angular motion from an identity body; ordinary cases bypass the notification. Stack/LR and original body selection are checked.

Initial fixture expectation mislabeled object124 as the helper's side vector. Reading the actual source offsets showed it copies helper+24 (UP), skipping helper+12 (side). Corrected the expectation; no original code changed. This resolves that specific field-layout ambiguity. World notification effects, real collision/world contacts, general mixed-axis adapter equivalence and native held-object sequences remain open. Existing submission/rejection/controller and144 activation cases pass. No deployment.


## Executed persistent held update through physics submission

Controller fixture now extracts unchanged8244A8D8, bounds clamp82282580, magnitude limiter8221CA38, normalization8228ACE8, magnet caller8244EED8, predicate82582178, visibility setter8244A118 and conversion82282728 alongside previously extracted physics functions.30 original functions are included in this fixture.

Six four-tick sequences (positive/negative X/Y/Z) pass. A distinct controlled-unit datum3 supplies processed movement while held datum2 resolves to the synthetic physics body. Tick interval0.05, original unit scaling1, no unit slow flag and stationary held body produce target positions0.2 ->0.4 ->0.5 along the selected signed axis; stopping input on tick4 retains0.5. The unchanged main function performs both bounds clamps, the0.5 displacement limit, copies the editor transform, runs the original disabled-magnet caller, resolves the object/body and submits through the original target builder/controller. Expected target velocity follows target displacement /0.2. Stack/LR, no angular change/relocation and candidate invalidation for disabled magnets are checked.

World services explicitly controlled: queried held velocity zero, held position from synthetic body, variant bounds +/-100, special projection predicate false, contact-normal query false, visibility-local query false. Tick count1 avoids the periodic body-query branch. Correction/rotation/selection helpers throw if unexpectedly reached. The body position remains stationary deliberately; this tests persistent target accumulation and controller submission, not simulated collision/physical motion. Magnets-enabled selection/alignment, body-query cadence, contact correction, coupled monitor/camera movement and native sequences remain open. Earlier controller/resolver/orientation/activation tests also pass. No production behavior/deployment changed.


## Connected held-update snap/detach sequence with original alignment

Extended the controller fixture to use unchanged82582AD0 and its original math dependencies rather than a simulated alignment.45 original functions now execute in this fixture. Candidate lookup82582250 is still a controlled service: identity local marker at0, world marker at signed0.8 on the selected axis, candidate datum7, result2. Actual scene enumeration/visibility/contact response are not supplied by this fixture.

Six enabled-magnet sequences of six ticks now pass in addition to the earlier24 disabled ticks (60 total). With unit input +/-1, editor target advances0.2 then0.4; stopping input on tick3 preserves editor target0.4 while actual original alignment submits0.8 to physics. Resuming movement on tick4 advances editor target to its0.5 limit and bypasses alignment, submitting0.5. Stopping again snaps submission back to0.8 while retaining editor0.5. Disabling magnets on tick6 submits retained0.5 and clears candidate to -1. Signed behavior is checked on all three axes; selection runs exactly five times per enabled sequence.

This connects original held update, both bounds clamps, displacement limit, movement gate, alignment/quaternion conversion, visibility setter, object/body resolver, target builder and physics controller. It demonstrates that the persistent editor target and temporary snapped physics target are distinct. Overwriting the former with every snapped result would not preserve this original sequence. Checks inspect target position, resulting velocity, candidate identity, stack/LR and absence of unintended angular/relocation callbacks.

Still simulated: candidate query, held velocity/position query, variant provider, special/contact predicates, locality query and external physics effects. Body position is intentionally stationary to isolate target-state behavior. This does not prove physical pull-away, real-marker overlap handling, camera coupling or native Spartan parity. No production/deployment change.


## Original selection/scoring joined to held-update chain

Replaced the simulated82582250 result with the unchanged original selector and its scoring/pair-validation dependencies.58 original functions now execute in the controller fixture. Scene adapters supply one eligible datum7, identity local/world marker records and object positions/radii; the original selector decides whether and how to select it. Config resolver returns original forge-globals bytes rather than guessed thresholds. Original alignment and all previously connected placement/physics operations remain in the chain.

Enabled sequences now run nine ticks per signed axis, alongside the24 disabled-magnet ticks, for78 total. Near marker distance is0.1 (changed from the previous forced0.8 result to exercise actual near selection). The sequence covers movement, stopping/snap, resumed movement/unsnap, stopping again, disable, re-enable with marker at3, no scene candidate, then near-candidate reacquisition. Persistent editor target remains0.5 after its limit is reached; snap submission changes to0.1 only when selection and movement gating permit. Empty enumeration clears candidate and returning near geometry reacquires it.

An initial expectation that distance3 would clear the candidate failed: the original selector retained datum7 while declining alignment. Reading82582444 confirms the fallback candidate path is distinct from result2 alignment. Updated the fixture to check this retained non-snapping candidate, and added a separate empty-enumeration tick to test actual candidate loss. No original code was altered. Selection enumeration count is checked across enabled/disabled transitions.

Remaining synthetic boundaries: scene enumeration/eligibility/marker extraction, config resolver, world queries and motion effects. Multiple candidates/real marker packs, moving world/contact response, camera coupling and native Spartan defects remain unverified. Previous controller/resolver/orientation/activation checks pass. No deployment.


## Camera-point helpers and root-position lookup

Placement audit now records26 original functions, adding824BE840/824BEA10/824BEAD0,821D6D90,8244B758 and position helpers.824BE840 resolves held datum from TLS editor6892 and forms a point from8293A3B0(held) + editor36 * editor56/60/64. It obtains a basis-relative offset through8244B758 using controlled-unit direction1212/1216/1220, and places editor28 into its result's distance field36. Optional mode1 invokes824BEB50 before constructing the result; that branch remains open.

Both wrappers824BEA10 and824BEAD0 apply821D6D90 to that point, offset and direction/up basis.824BEA10 additionally subtracts direction * distance, returning distance in f1;824BEAD0 does not apply that subtraction.8244B338 compares the latter point with the controlled object's position: only when separation minus editor32 exceeds1 does it supply a correction. These are source-backed expressions; they establish coupled held-object/editor/view state rather than justify naming every helper a raw eye-position query.

8244B758 derives its offset using the clamped difference between direction Z and editor276, an angle function, a global curve and held-object tag field32, then multiplies the original up vector. Curve meaning and exact view integration are not yet resolved. It is not a constant clearance offset.

822410D0's ordinary fallback calls8225EA20: unattached objects return fields100/104/108. Attached objects transform that local position using the parent node matrix; an alternate flagged path exists. The connected controller fixture now executes both original functions for the unattached root path rather than supplying a position callback. Parent/alternate branches throw if reached; fixture parent datums are explicitly -1. All78 held-update ticks and prior controller/activation cases pass with60 original functions. Body/world positions stay synthetic and stationary; camera coupling itself remains unexecuted. No production/deployment change.


## Executed original camera point and distance backoff

Controller fixture now executes824BE840,824BEA10,824BEAD0,8244B758,821D6D90,822E15E0 and822C8040 with original math helpers (68 original functions total).72 cases pass: six signed axis directions, distances2/7.5/22, editor offset scales0/2 and both point wrappers. The fixture supplies held position(10,20,30), offset vector(0.5,-0.25,1), tag scalar32=2 and curve output0.25. Independently computed expectations check basis-relative offset application, vertical-view fallback, forward output, returned distance, stack/LR and the subtraction of forward*distance only in824BEA10.

The curve service verifies its actual argument pointer and normalized input before returning the controlled value. Its pointer originates at global8405D340 ->+256 ->+16, sharing the global root already used elsewhere; an initial fixture typo used8406D340 and was corrected after the pointer assertion failed. Original code was unchanged. Scene position and curve response remain simulated, and optional824BEB50 correction throws if reached. Neither the curve itself nor the complete monitor/controller/world update is established by these camera-helper cases. Prior placement/physics/activation suites pass; no deployment.


## Executed camera-to-monitor distance correction

Added unchanged8244B338 to the connected original-code fixture, replacing its previously throwing boundary.72 cases execute through original824BEAD0 camera construction and822410D0/8225EA20 controlled-unit position lookup. Six signed axes, retained editor32 distances2/7.5 and separation excesses -1/0/0.5/1/1.25/3 verify the exact threshold: excess must be strictly greater than1. Output becomes the direction times excess, not a constant clearance adjustment; at/below threshold all three output fields are explicitly reset from poisoned99 values to zero. Stack/LR checks pass.

Scene/curve services remain controlled, and the test isolates this correction with camera offset scale and tag offset scalar zero. Original code is unchanged;69 original functions now execute in the controller fixture. Earlier placement, camera, physics and activation suites pass. The normal placement test still supplies zero held velocity, so the nonzero-velocity branch invoking this correction inside8244A8D8 remains untested as a combined sequence. Full coupled monitor physics/native re-grab remains open. No deployment.


## Coupled monitor submission and camera prediction (source evidence)

Mapped8244AF48: mode1 camera helper supplies a backed-off point and direction/distance; the monitor update reconstructs the focal point, performs a world query, limits monitor displacement to2, conditionally removes the inward normal component, builds the transform through8221B258 and submits through82452930 with original0.05 time. It writes editor32 as the minimum of resulting separation and retained distance, and conditionally updates editor276 directional history. World-query semantics, local-view update and complete execution remain open.

Mode1 invokes824BEB50. Its linear prediction uses queried velocity, a0.001 predicted-distance threshold, and a scale capped at1 from cached editor8/12/16 versus current root position. The small-distance path loads original zero; valid physics/body state additionally enables a transformed angular-motion correction. Original constants0,1,0.05 and0.001 are now verified from image bytes by the placement audit.

Velocity query82260CF0 has three paths: object flag0x400 supplies a global vector; eligible valid physics instances use body linear/angular queries; otherwise object136/140/144 and148/152/156 are copied. Prediction preserves incoming time in f29, but its threshold calculation also reads f1 after this query. Floating-register effects of the query dependencies must be established before treating a test stub that preserves f1 as original behavior. This is an explicit unresolved boundary, not an executed prediction test.

Placement audit now records29 unchanged function bodies with provenance and call ordering. No production behavior, native test result or deployment is claimed by this source pass.


## Original velocity query executed through source selection

Replaced the zero-velocity stub in the controller fixture with unchanged82260CF0, parent resolver82260C98, eligibility82260E80 and body-vector readers82260AF8/822302F8. Fixture now extracts74 original functions. All previous held-update, controller, camera and correction cases pass with this original query.

48 new cases cover fallback object vectors, valid physics-body vectors, object flag0x400 forced-zero vectors, fixed body type5, each combination of nullable linear/angular outputs, and direct/parent-resolved objects. Outputs, untouched absent outputs, stack/LR and f1 preservation are checked. This resolves the f1 uncertainty for these exercised paths. Physics eligibility dependency82260F08 is controlled true with argument4 checked; alternate82260F70 throws if reached. It does not establish all eligibility/world conditions.

No original function behavior was edited. Full camera prediction and coupled monitor execution remain next; no native Forge parity or deployment is claimed.


## Linear camera prediction executed and wrapper distinction confirmed

Fixture now extracts79 original functions, including824BEB50 and its original matrix math.720 cases exercise signed axes, zero/below/at/above-threshold speeds, time intervals0.125/0.5 and cached-position gaps0/0.0005/0.05/2. Each case runs direct prediction,824BEA10 with mode1, or824BEAD0. Expected linear displacement is zero at/below the0.001 predicted-distance threshold, otherwise limited to the cached/current root-position gap. Original velocity query and root-position lookup execute. Frame/LR and all output coordinates are checked.

The first wrapper expectation failed:824BEAD0 explicitly passes mode0 to824BE840 regardless of extra caller registers; it never requests prediction.824BEA10 forwards its r6 mode and includes prediction before distance backoff. Corrected the test expectation from this source evidence, leaving original code unchanged. This distinction matters when connecting8244B338 correction and8244AF48 monitor movement.

An initial extractor boundary also mistakenly replaced an existing original matrix helper with a throw; the existing held-update regression caught it. Restored original math dependency extraction. The full controller/camera suite and144 activation cases pass. Bodies have no physics instance in these new prediction cases: angular correction services82243068 and8249B1F8 still throw if reached. Full angular prediction, coupled monitor/world execution and native defects remain unresolved. No production changes or deployment.


## Angular camera prediction connected to original orientation and physics point

Added unchanged82243068,8229D4E0 and8249B1F8 to the controller fixture (82 original functions).288 cases execute angular prediction directly and through mode1 camera backoff: all signed axes, rates0/0.6/pi, times0.125/0.5, identity/90-degree yaw orientations, and linear motion off/on. Independent Rodrigues rotation expectations check all coordinates and stack/LR. The original root orientation lookup, angle/quaternion conversions, physics-point lookup, angular normalization and quaternion point rotation execute.

The first yaw expectation assumed inverse orientation and failed.82264A58 is an Euler-angle-to-quaternion conversion, not a matrix inverse;8232F830 applies quaternion rotation. The physics point(1,2,3) under positive90-degree yaw becomes(-2,1,3), not(2,-1,3). Corrected the independent expectation from the actual source operations; no original code was modified. Earlier notes calling this an inverse/conversion are superseded by this evidence.

The exercised8249B1F8 branch copies first-body fields368/372/376; its flag-dependent resource/node branch remains open.82243068's ordinary root path copies forward/up through8229D4E0; the alternate8281F4E0 service throws if reached. World state remains synthetic and stationary. Combined linear/angular correction and wrapper ordering now pass, as do existing controller/camera and144 activation cases. Full8244AF48 monitor update, contacts and native re-grab/detachment/overlap behavior remain unverified. No deployment.


## Coupled monitor update executed through original physics submission

Added unchanged8244AF48,8221B258 and8221B030 (85 original functions in fixture).90 cases connect the full monitor-update entry to original mode1 camera helpers, orientation construction, object/body resolution, target builder and controller. Signed X/Y/Z displacement requests0/0.5/2/3/10 verify the two-unit displacement cap. Contact modes absent/inward/outward verify original normal projection using controlled player152/156/160. Independent expectations check resulting controller velocity, editor32 retained distance, query flag80, stack and LR.

Monitor datum3 and held datum2 remain distinct. The monitor resolves to the synthetic physics body, while the held object has no physics instance and zero velocity. Query82415970 returns false;824F5CF0 throws if reached. Local-view slot is explicitly -1, so823FC348 remains an unexecuted sink. The body's position is stationary and callbacks store requested velocities: these are original-code integration tests, not collision-world motion or native gameplay proof. Existing prediction/controller suites and144 activation cases pass.

Remaining work includes true world-query smoothing, local-view update, combined held/monitor motion over time, dispatcher/input/grab lifecycle integration, and native parity. No production behavior changed and no deployment occurred.


## Monitor world-query branch joined to original smoothing

Added unchanged824F5CF0 (86 original functions). Monitor suite now runs180 cases, adding query-hit versus query-miss for each prior displacement/contact case.82415970 remains a controlled boolean and its deeper geometry traversal is not executed;824F5F78 supplies target fraction0.25 and upper bound1. Original smoothing starts from zero state with dt0.05, using image stiffness25: fraction0.0078125 and velocity0.3125. Assertions check state228/232, held/monitor identities256/260, query flag80, shortened retained distance and resulting controller submission.

Static824F5CF0 also shows stiffness75 for the other response branch, a hold timer at state+8, zero-time direct target assignment, and an upper-bound clamp that resets velocity/timer. These additional transitions still need execution. The query helper82415970 traverses active world structures and object/geometry filters; those services are not replaced with a claim of collision correctness. Existing suites and144 activation cases pass. Native motion/contact/camera behavior and all reported Forge defects remain unverified; no deployment.


## Seven-ray obstruction selection connected to monitor smoothing

Replaced the824F5F78 fraction stub with the unchanged original function and original direction/basis/rotation/distance math (94 extracted functions). It traces the center segment, constructs three offset vectors and queries their positive/negative sides for six additional segments. Center fraction becomes the upper limit; nearest qualifying surrounding hit determines the target fraction. It also retains a point at state+12 and validity byte+24, testing whether a prior point remains within the segment/cone and nearest-distance constraints.

The180 monitor cases now execute this selection before original smoothing. The deeper824F5E28 ray service supplies center fraction1 and surrounding fraction0.25 with interpolated hit positions. Every hit-path case checks exactly seven queries, held/monitor datum arguments2/3, retained-point validity editor252, original smoothing state and resulting retained distance/controller submission. Query-miss cases issue no rays. Existing suites and144 activation cases pass.

This establishes original ray construction/selection for the initial unretained-point case, not real geometry intersection. Cached-point reuse/invalidation, varied ray results, degenerate segment, low-level824F5E28 traversal and outer82415970 geometry query remain open. No production behavior or deployment changed.


## Executed obstruction cache lifecycle

294 original824F5F78 steps now cover six signed axes, each of seven rays as the sole hit, and seven successive states: hit at0.25; no fresh hit but retained0.25; origin moves0.5 and retained fraction becomes0.2; origin moves beyond cached point and invalidates it; new0.6 hit reacquires; shortened segment rejects cached point; zero-length segment returns without querying or overwriting caller output sentinels. Cached world coordinates stay fixed during retention. Center-ray upper bound is checked independently from selected target fraction, along with validity, query counts, stack and LR.

These cases use zero-width cone configuration to isolate longitudinal cache behavior. Nonzero cone lateral validity, multiple competing hit distances and real ray/world traversal remain open. Original ray-selection function and its math execute; individual intersections remain synthetic. Full controller/camera suites and144 activation checks pass. No production or deployment changes.


## Original single-ray request wrapper replaces synthetic boundary

Added unchanged824F5E28 (95 original functions). Connected camera/monitor/cache tests now build the actual request: type27 at+0,64-bit mask at+4, start+12,end+24, exclusion datums+36/+40 and byte count+292. It initializes output point to end, rejects segments below its original squared-length threshold, calls82417550 and copies result fraction+4 and point+8 only on hit. A miss preserves the caller's fraction, unlike the earlier ray stub which always wrote1.

The synthetic boundary is now82417550 itself, and checks original request type and the two exclusion identities. Existing180 monitor updates,294 cache steps and all earlier suites pass;144 activation cases also pass. No real collision traversal is claimed. Exact H3 collision-service counterpart remains unidentified: simple constant27 searches did not establish a matching wrapper. This must be mapped by request semantics/call flow, not an address guess. No production or deployment change.


## Collision dispatch ownership boundary and H3 search status

Placement audit now records32 original functions and verifies82417550 call ordering plus both atomic-decrement exits. Entry824AA580 obtains shared-world access; a readiness field gates query context construction82416438, dispatch824A9D68 and result conversion82416DF8, with conditional82416AD0 handling. Both ready/not-ready paths decrement the shared counter using atomic operations. Exact ownership API semantics still require caller/service tracing; it is not safe to identify a replacement from a ray-result shape alone.

The audit records actual request offsets and miss semantics and removes stale claims that camera prediction/monitor paths have never executed (their controlled execution is documented separately). H3 source searches and inspection of constant27 candidates did not identify the corresponding collision service; those candidates are not accepted mappings. Native H3 Forge update call flow remains the next source trail. No additional runtime tests or production changes in this source-mapping pass.


## H3 native placement-validity search found from Forge caller

Extended the H3 update audit from10 to14 original bodies. Actual82281A98 calls822836D8 before a pose write in its discrepancy-handling branch.822836D8 obtains a tag-derived scalar via822835E0, calls8226E590 with four attempts, copies successful output into the requested point, then applies a variant-record gate whose field semantics remain unresolved.8226E590 clamps its radius input, multiplies radius between attempts and invokes8226E6C8. The latter constructs/query physics shapes and calls820AE5C0 twice for point checks. This is an identified H3 placement-search boundary, not yet an equivalent of H4's camera ray service.

8227E460, initially investigated as a possible camera helper, computes object32 vector minus the root-position query820A9E58; it does not trace rays. The next useful H3 point-query source trail is820AE5C0 from8226E6C8. Audit validates the actual call relationships and four-attempt argument. No native behavior or collision-service parity is claimed; no production change/deployment.


## H3 point and object-query chain identified

H3 audit now records19 original functions.820AE5C0 accepts mask64 in r3, point r4, exclusion datums r5/r6 and optional reason output r7. It traverses16 active world structures, geometry and object candidates; observed reason assignments1/3/4 differ from H4's richer output structure. Matching parameter roles do not establish flag/result compatibility.

Following shared filter helper820AED80 identified object callback820AEC70, whose vtable entry is confirmed from original image82000D2C. Constructor820AEA78 installs table82000D28 and is called by820AD3E0. Crucially, original Forge helper82281268 calls820AD3E0 and82281A98 calls82281268. Audit now verifies this actual Forge-to-collision chain rather than relying on a constant/signature match.

Next boundary work is820AD3E0 argument/result mapping and its flags against H4 requests. This is a stronger candidate integration point, not a verified drop-in adapter. No native collision test, production change or deployment.


## H3 ray arguments and H4 runtime mask initialization

Original Forge82281268 passes820AD3E0 a64-bit mask0x001000090000099D, mode byte0, start pointer r5, displacement pointer r6, three filter/identity inputs r7/r8/r9 and result buffer r10. Its miss path explicitly computes start+displacement; collision service reconstructs hit point=start+fraction*displacement. Result fraction+4 and point+8 are confirmed; Forge also copies fields+36 and+60. Buffer writes extend through+92. Detailed filter/normal/result semantics and flags still require mapping. H4 wrapper endpoints therefore require explicit conversion before calling this H3 service.

H4 monitor mask global845548B8 is zero in the static image but original startup83292E30 builds0x0000100900000000 at845548B0 and83292E50 copies it to845548B8. Added both unchanged initializers to the controller fixture (97 original functions); every simulated collision entry now checks the actual initialized mask. Do not copy either H3/H4 mask across engines without resolving meanings.

All connected controller/camera/cache and activation suites pass with initialized mask. No actual geometry traversal, production adapter or deployment.


## Original H3 collision filter executed

Added unchanged H3 function820AF170 and its original save/restore helpers in a separate namespace of the existing controller fixture.392 cases cover14 object categories, category-mask enabled/disabled, header flag0x10, no exclusion, and all three slots containing either the direct candidate or its parent. Original filter rejects all direct matches, walks parent field16 and rejects ancestor matches in these cases. Low mask word bit(type+1) enables each category. Stack/LR and boolean result are checked.

The source has a specialized parent/seat exception for selected categories; fixture sets seat index582=-1 to exclude that branch. Additional high-word flag checks and hierarchy semantics remain open. This proves native H3 filter handling for the exercised inputs, not complete H4/H3 flag equivalence or world collision. Original H4 query/context construction82416438 still stores its request pointer for callbacks; corresponding H4 rejection semantics need mapping. Existing H4 suites and144 activation checks pass. No production/deployment change.


## H4 exclusion callback executed and compared with H3

Original callback-table bytes from82416438 lead to82416640, now included unchanged in the fixture (98 H4 functions).12 cases cover exclusion counts0/1/2/3 and unrelated/direct/ancestor identity. The callback resolves shape metadata to an object and walks parent field36 while comparing the request exclusion list. These ordinary rejection cases match the H3 filter's tested direct/ancestor behavior, with different parent layout and argument representation.

Explicit synthetic boundaries: upstream callback accepts; typed metadata8198 yields datum2; object resolver supplies datums2/3; object-state exception predicates return false. Fixture checks callback byte result and stack/LR. Source also includes shape-type filtering, physics-instance flag gating and object-state exceptions after an exclusion match. Those remain unmapped and are not covered by the12 cases. Existing suites and144 activation checks pass. No claim of full filter parity, no production/deployment changes.


## H4 exclusion exception predicates replace stubs

Added unchanged82415E10,82259C00 and824150C8 (101 H4 functions). Expanded callback suite to48 cases: prior exclusion counts/identities crossed with ordinary type0, eligible type1 without child, child with invalid seat-reference field, and child with valid seat-reference field. Header/type, tag pointer, child/sibling links and parent seat records are synthetic; original predicates and traversal execute. A valid tested child-seat configuration permits an otherwise excluded object. Invalid/missing child states continue rejecting it.

82259C00 gates by object type and tag520 flags;824150C8 resolves parent36, seat index44 and parent tag seat-array1368 stride364 field74. This source-backed exception must not be replaced by unconditional ancestry rejection. Category3 branch82415E10 delegates to8224DED0; that dependency still throws if reached. Shape metadata/object resolver/upstream filter remain controlled. Existing suites and144 activation cases pass. No full native filter parity claim or deployment.


## Initialized Forge camera mask excludes object-shape branch

Expanded H4 filter tests to96 cases by crossing the existing48 with low mask word0 (actual initialized camera) and1 (object-enabled diagnostic). All pass. Added four direct checks with initialized0x0000100900000000 for shape types0/1/2/5: callback rejects type2 before metadata/exclusion traversal, while other tested types pass this callback when upstream approves. This does not assert they pass every world filter.

Important scope correction: earlier exclusion/seat tests intentionally enabled the low-word object bit; they establish general callback behavior, not a branch reached by the initialized Forge camera mask. Camera integration should first map geometry behavior for its actual mask rather than include object tests merely because H3's native Forge aiming ray includes them. The H3 aiming-ray literal0x001000090000099D is not the camera's H4 mask.

Category3 exception dependency8224E530 was traced to8230DE48 result==4, but is not executed here and does not gate the default camera mask. It remains in broader filter coverage. Existing suites and144 activation cases pass. No production/deployment change.


## Collision result initialization and nearest-hit merge

Static audit now records35 original functions, including824169F8 (initial result),82416DF8 (candidate processing) and82416AD0 (geometry result merge). The latter replaces a previous result only when the incoming fraction is strictly smaller; equal-distance geometry preserves the earlier result. It interpolates the hit point, writes the normal/plane, starts with type0 and invalid object identity, and changes type to3 for typed metadata8199 value1. Request bytes296/297 enable additional material/geometry metadata; the camera wrapper clears both. Full native traversal remains unexecuted.

Corrected stale machine-readable audit output that still described the H3 service as unidentified:82281268 ->820AD3E0 ->820AEA78 is the candidate H3 service, with displacement rather than endpoint input and different filter masks. Identification does not prove equivalence. H3 helper820ADFE0 maps input bits11..16 to output bits0..5; semantic names and the corresponding H4 geometry filter are still unresolved, so this evidence does not justify copying masks between engines.

Re-ran audit_placement_flow.py successfully. These are static source checks, not new live interaction tests. No production changes or deployment.


## Original world hit collector executed

Context vtable82000F08 slot0 resolves from original image bytes to822528D8. Extracted that unchanged collector and helper82D824C8 into the existing controller fixture (103 H4 bodies).58 steps cover shape types0/2/5, parent depths0/1/3, nearer/farther/equal hit fractions and object counts0/255/256/257. Type2 roots append object datum/fraction pairs to context384 with count2432, capped at256, without replacing the geometry minimum. Other tested roots retain only strictly nearer geometry; equal hits preserve prior data. Original helper stores child keys in reverse ancestry order followed by-1, and collector saves the root atcontext96. Synthetic metadata returns object2; shape hierarchy and hit data are controlled. Native world traversal remains unexecuted.

Also traced824A9D68 to its physics-world virtual dispatch atslot100 and batch-query callback table82132444; callback824A9478 forwards through the supplied filter atinterface20 slot4 before transforming endpoints to shape space and invoking the shape query atslot24. This connects the previously tested82416640 callback to world traversal, but upstream world filter semantics remain open. No copied masks or production changes.

Controller suite and144 original H3/H4 activation cases passed. Reused existing outputs; no live game instance or deployment.


## Original edit input connected to retained-distance clamp

Traced82368CE0 (file181), called by8225CE30 after copying a256-byte input packet to a local buffer. It calls82232AC8 and requires both success and a non-invalid returned held datum, plus packet56 strictly greater than original0.1. Active input writes player1888=1. Packet28/32 are mutually exclusive by dominant absolute axis: only strict abs(28)>abs(32) selects player1892; ties select player1896. Both packet fields are consumed to zero. Optional packet40 selects the same dominant-axis rule for packet44/48 into player1900/1904; when false those fields are retained. Inactive gating clears player1888 without clearing stale player scalar values or consuming the packet.

82452738 uses player1892 only with player1888 active, subtracting input*0.3 before the already mapped radius/config clamp.8244A7D0 instead routes player1900/1904 and negated1896 into rotation8244B518; it is not the distance consumer. Added unchanged82368CE0 to the grab fixture and connected it to unchanged82452738.768 steps cover gate success/failure/invalid datum, threshold0/0.1/0.11/1, signed axes/ties, optional rotation, and repeated processing after consumption. First expectation incorrectly retained the secondary movement axis when the primary won; original branch tracing corrected the expectation to zero. All768 steps now pass, alongside1200 original grab/release/regrab sequences and6 release rejection cases. Eligibility and config services remain controlled; native input timing remains open.

82232AC8 traced statically: validates player, game index1..5 and a mode table/predicate, player availability flags, session predicate821DF530==1, and Forge predicate82449A60; on success optional output is editor held datum at game+6892+playerIndex*336. This is not a controlled-unit lookup. Upstream device mapping and full gate execution still require verification. No production changes or deployment.


## Original edit-input eligibility replaces simulated gate

Grab fixture now extracts unchanged82232AC8,82265430,821DF530,8222AAD0 and82449A60 plus save/restore helpers.17 explicit cases exercise invalid player, mode index0/1/5/6, null/inactive session, either session activation byte, session type1/3/4, session64 value, editor mode0/1/2, missing controlled unit, matching/mismatching monitor tag, player flagbit3 and absent held object. Success writes the actual editor held datum; rejection preserves the caller's output sentinel. Forge eligibility can succeed with held datum-1, but82368CE0 separately rejects that value. Monitor tag lookup8246B098 remains controlled at42; player/session/object memory is synthetic.

All768 edit-input-to-distance steps now execute this original gate chain instead of the prior boolean adapter.1200 grab/release/regrab sequences and6 release rejection cases also pass. This removes the simulated eligibility boundary for the exercised cases; it does not verify upstream device input, networking or live state transitions. Reused existing fixture binaries/logs; no production/deployment change.


## H3 edit-input adapter boundary identified

H3 producer821F04C0 (file40) resolves TLS96 player stride880, gates through820B06A0 and packet44>0.1, copies packet20/24 to player768/772, optionally copies32/36 to776/780, sets active764 and consumes20/24. Unlike H4's82368CE0 it retains both axes without dominant-axis selection. H3 held update82281A98 reads these fields after its movement/placement work: rotation consumes776/780/negated772, and distance adds768*0.3 before its native clamp (upper10). H4 clamps after subtracting1892*0.3 and performs the update before held-object/monitor submission. Original H3 image constants0.1,0.3 and10 verified.

This is a concrete integration difference, not permission to negate input blindly: upstream packet sign/physical-control correspondence remains unverified. Adapter must preserve H4 dominant-axis selection and consumption, and avoid processing the same input again through H3's original distance update. Added producer and source assertions to audit_h3_held_update.py (20 bodies), updated its JSON with the mapping and remaining gap. Static audit passes. No production changes or native parity claim.


## Forge packet consumption precedes ordinary unit processing

H3 tick820B37D0 calls820B6EA0 on its frame packet;820B6EA0 copies116 bytes to local stack160, calls821F04C0 with that local packet, applies intervening context filters, and conditionally passes the same local packet to821EC0E0. H4 tick82370150 calls8225CE30 on its frame packet;8225CE30 copies256 bytes to local stack144, calls82368CE0, applies context filters, and conditionally passes the same local packet to823619F8. Both ordinary producer calls are gated by action type/control mode; call ordering does not imply unconditional execution.

This identifies the pre-consumption integration boundary and proves the Forge edits affect the packet subsequently supplied to movement processing. It does not establish physical controller-axis direction: earlier opposite distance-consumer signs remain a semantic difference pending upstream mapping. H4 frame packet also flows through821F35F0/82309638 before this stage; these are not yet a resolved device-input path. Added call ordering, shared stack-packet offsets, copy sizes and H4 source hash to the existing H3 integration audit; it passes. No production behavior changes.


## Intervening packet filters narrowed; device signs still open

8235DC98 (file121) aliases input asr5 and stores only packet8 (64-bit action bits) and64 (32-bit action bits), with persistent player120/128 masks/state and player flag updates. It has no float stores.822D6EE8 (file98) keeps input asr27, never stores through that pointer, copies prior local-player packet168 to424 and incoming256 bytes to168, then updates auxiliary local-player counters/state. These direct paths do not invert the movement floats. Intervening reset/context branches in8225CE30 remain separate obligations.

821F35F0 (file42) clears/acquires the large frame packet through821E8018 and session dispatch;82309638 (file56) performs session-dependent processing/recording and publishes the packet pointer. Neither inspected function establishes a physical device-axis producer, so physical sign equivalence remains unresolved. Broad offset-only candidate searches were not used as semantic evidence.

Expanded audit_movement_gate.py to12 H4 functions with hashes, explicit packet-write checks and these limits. Removed stale open entries that incorrectly described already executed producer/writer fixtures as unexecuted; full native detachment remains open. Audit passes. No production changes or deployment.


## Action reset and context preservation traced

Added unchanged822C5470 to the grab fixture.12 cases across four word-aligned addresses and three poisoned byte patterns verify clearing of analog fields28/32/44/48/56/60 and action fields8/64, invalid identity/reference defaults, and guards outside the256-byte buffer. The memory-clear primitive8224A558 is a checked256-byte test adapter. Existing17 eligibility cases,768 connected input steps,1200 grab/release/regrab sequences and6 release cases pass.

8225CE30 has two calls to this reset after82368CE0 and before8235DC98/822D6EE8. The first is selected by a per-player bit in TLS132 structure+4. Both preserve packet0,4,16,20,24. The second, gated by bit36 of controlled-unit+16, also preserves packet64 and nine words96..128. Neither restores movement28/32, look44/48 or trigger56/60. Forge player fields already written by82368CE0 are outside the reset packet: do not infer that clearing the packet also clears those editor inputs. Full context-gated producer/held-update sequences remain unexecuted.

Added reset provenance/order assertions to movement audit (13 H4 functions). Device-level axis direction remains open; this work narrows post-Forge packet behavior without claiming a physical sign mapping. No production changes or deployment.


## Rotation-input camera-offset decay state executed

Added unchanged8244A7D0 to the grab fixture.48 cases cover input active/inactive, rotation applied/rejected, global8407EFFB forced off/on, existing decay0/0.2 and dt0.016/0.05/0.1. Original function forwards1900/1904/negated1896 to rotation8244B518, ORs its success into editor81, and initializes editor40 to5*dt only when decay is zero and rotation succeeded or the global is enabled. Nonzero decay remains unchanged. Rotation transform is a checked test boundary; this does not execute full rotation/physics. Dispatcher8244D0E0 subsequently reduces editor36 by editor40, floors atzero, then clamps distance and submits held/monitor updates.

Existing grab/reset/eligibility/input suites pass. Direct literal-access searches found only the known readers for8407EFFA/B, and the original image contains no big-endian stored pointers to either exact address. This limited negative result does not rule out indirect/overlapping writes or runtime mutation, and does not establish either switch as a debug-only setting. Alternate path remains in coverage. No production changes/deployment.


## Original analog rotation replaces transform stub

Grab fixture now extracts unchanged8244B518,8244A6A8 and math8228ACE8/82265E28/82265C30/822C1398/8226BFC0, with original save/restore helpers. The prior rotation stub is removed. All48 rotation-input/offset-decay cases now execute actual eligibility, signed-square input shaping, axis normalization, trigonometry and matrix composition. With controlled view+X, input1900=0.5,1904=-0.75,1896=0.25 produces angular vector(-0.3125,-2.8125,-1.25), multiplied bydt. Each output basis component is checked against independently computed Rodrigues rotation; scale1 and translation(11,12,13) remain unchanged and basis remains orthonormal. Missing held datum and inactive-input cases preserve identity; forced decay can initialize without rotation.

Initial connected run failed because the formerly stubbed fixture supplied no eligible physics state. Original8244A6A8 correctly rejected it. Fixture now supplies object flag0x100, valid instance and a non-fixed body with instance flags clear; original gate executes. No original function or expected gating rule was patched to force success. The physics data remains synthetic and this is not a native contact/rotation test. Existing grab/reset/eligibility/distance tests pass.

Earlier48-case statement that rotation transform was controlled is superseded by this connected evidence. Different view directions, input magnitudes, angle threshold and full held-world rotation remain additional coverage obligations. No production changes or deployment.


## Analog rotation across view axes and existing poses

384 additional original8244B518 cases cover six signed cardinal views, eight input triplets (zero, positive/negative single axis, combined axes, vertical cancellation and tiny magnitude), dt0/0.00001/0.016/0.05 and identity/90-degree-yaw starting orientations. Independent Rodrigues composition checks every basis component plus returned changed flag, unchanged scale/translation, stack and LR. Synthetic eligible physics state remains required; world motion is not integrated.

Source normalization8228ACE8 leaves vectors below0.0001 untouched and returns length0. A vertical view makes cross(worldUp,view) zero, so that rotation contribution stays zero rather than acquiring a fabricated fallback axis. The angular vector is5*(signedSquare(input1)*worldDown + signedSquare(input2)*normalizedCross(worldUp,view) + signedSquare(input3)*normalizedView). The function applies rotation only when returned vector length*dt is strictly greater than original0.0001. Existing pose is composed with this rotation, retaining translation and scale. Tests include cancellation and values on either side of the small-angle region, but do not claim exhaustive float-boundary or arbitrary-view coverage.

All existing grab, release, reset, eligibility, decay and distance-input suites pass. These extend original-code evidence and do not establish native Forge rotation parity. No production/deployment change.


## Four saved configuration identities — static linkage, 2026-11-11

`audit_trait_config.py` resolves the earlier unnamed four configurations using original resolver `825B16B0` (file147), its image jump table at `825B16D4`, event19 producer `82714570` (file43), initialization `8244C210` (file217), and the local TagTool Gen4 settings enum. Setting IDs180..183 correspond to TraitZoneAlphaPlayerTraits, TraitZoneBravoPlayerTraits, TraitZoneCharliePlayerTraits and TraitZoneDeltaPlayerTraits. The schema supplies these names; it does not independently establish UI reachability or localized visible labels.

The original jump-table entries select branches `825B1820/1834/1848/185C`, each resolving TLS28 plus respectively12788,13044,13300,13556. Initialization resets and applies four256-byte blocks from variant offsets55724,55980,56236,56492. The earlier event19 producer and persistence findings therefore concern trait-zone channel configurations, not unidentified generic map settings. The audit checks all four branches and records original-body and schema hashes in the reused `isolated/full-re-trait-config.json`.

Validation: the static audit passes. No game was launched, no native save/load round-trip was performed, and no production behavior changed. Zone membership, overlapping-zone precedence, complete trait field semantics, actual menu reachability and H3-compatible persistence remain open. This does not authorize dropping trait-zone behavior or altering native H3 saves.


## Trait-zone membership aggregation and precedence — 2026-11-11

Original `8246BBC0` (file74), called by `8246B290` (file171), supplies the runtime consumer missing from the preceding configuration audit. It walks a zone list, reads each object's multiplayer block using object halfword486, checks the signed team field at block28 through `8242FAF0` and the current mode's virtual slot232, and calls boundary helpers `8298FCB8`/`8298FA30` against the player's controlled object. Those helpers and the list producer still need semantic/executed coverage; this tracing does not prove boundary shapes or edge inclusivity.

For a qualifying zone it reads channel byte47, accepts only0..3, and sets one byte in a four-byte local presence array. After traversal it fetches the map variant with `823C2020` and loops channels0,1,2,3, applying variant+55724+256*channel through `822D5908` with force=false. Thus duplicate zones on one channel are deduplicated before merging, and application order is Alpha through Delta regardless of linked-list traversal order. It is not a nearest-zone or last-enumerated-zone winner policy.

Merging is field-selective. For example `822D5BB0` applies the movement block's nonzero enum bytes20..25, and `82432290` applies only floats whose source mask bits0..3 are set when force=false. Later active channels override earlier explicit values; unspecified values preserve accumulated values. Appearance `822D5C80` additionally uses low-bit flags and -2 sentinels, so a blanket nonzero-byte copy is incorrect. Complete field naming and weapon block semantics remain open.

Caller order matters: `8246B290` invokes mode virtual slot132 before zones and slot136 afterward, followed by `8246BA00`, powerup-related `8246B628`, and `8246B8F0`. Therefore Delta is last among trait-zone channels, not necessarily the final authority over all player traits. The extended static audit passes and retains hashes/caller linkage in full-re-trait-config.json. No original-code execution or live zone overlap test was performed in this pass; no production change or deployment.


## Trait-zone point membership and boundary predicates — 2026-11-11

Original `8298FCB8` (file4) clears an80-byte descriptor and resolves the zone object's multiplayer block via halfword486; missing block65535 leaves a zero descriptor. Builder `8298FD50` (file83) copies its dimensions and shape, resolves a transform (with parent/type and attachment-related branches), optionally resolves a marker, and can obtain default boundary data from the object's tag if the instance shape is0. The parent and marker branches are traced structurally, not yet semantically or dynamically verified. Shape2 recenters asymmetric upper/lower extents and computes a bounding sphere; shape3 delegates descriptor preparation to `82990070`, still open.

Membership `8298FA30` (file164) rejects invalid object datum-1. Object-header type0 selects two point samples derived from `822E9E08`, original world-up/down vectors and object float3884. Other types use one point returned by `82260B58`. It tests samples sequentially and returns true on the first inside point. This is not a capsule/volume intersection, nor does this function itself walk a seated player's parent vehicle. Semantics of the position-producing helpers and seated-player behavior remain unverified.

`8298F920` (file77) dispatches signed shape1 to sphere,2 to cylinder,3 to box; other values reject. The local Gen4 Object.cs boundary enum independently supplies these names. Cylinder and box first pass a bounding-sphere check, then the shape-specific predicate. Sphere `8258BAB8` compares squared distance <= radius squared. Cylinder `8258BB20` checks axial displacement against half height then radial distance squared against radius squared. Box `8258BCB8` projects point-center onto normalized basis axes and compares absolute distances against half dimensions. The original image constant at82128A54 is float9.999999747378752e-05: dimensions at or below that threshold reject. Finite positive geometry includes exact surface equality. This is static branch evidence, not executed floating-point boundary validation.

The trait audit now hashes seven additional original bodies and checks sample-loop linkage, dispatch, relevant edge branches and image constants. Audit passes. Native membership, attachment handling, box descriptor generation and complete overlap transitions remain open. No production edits, game launch or deployment.


## Rotated box recentering and sample-position dependencies — 2026-11-11

Original box builder `82990070` (file106) computes h=(abs(top)+abs(bottom))/2 and displacement=abs(top)-h, transforms world-up using descriptor transform+24 through `822C9EB0`, then adds that direction times displacement to center+64. It stores h into both upper/lower extents and sets bounding radius to sqrt((width/2)^2+(length/2)^2+h^2). `822C9EB0` (file144) transforms a direction with scale and basis, without translation. This resolves the box descriptor step previously left open; original builder sets the descriptor transform scale to1. The world-up pointer and half constant are present in the original image.

Single-point producer `82260B58` (file54) is not simply a read of the input object's position. It calls `82260C98` (file93), which follows parent+36 until object flags+256 contain0x100 or no parent remains. It then attempts a physics-derived position; if that path cannot supply one, it copies the resolved object's position64..72. The returned point therefore can derive from an ancestor. Physics helpers and category-specific body selection remain unverified.

Biped sample producer `822E9E08` (file112) uses tag fields1824..1836, object transform, stance-related helpers and a mode argument. The zone caller passes mode0. It outputs the tag radius at its r6 pointer and a nonnegative height-like quantity at r5, but the zone caller uses the radius output plus object float3884 for its two tests. With the original world-down/up constants, those points are base-radius*up and base+(object3884-radius)*up. Do not replace this with an assumed eye point, raw origin or entire capsule intersection. Helper-derived base position, seating and animation interactions still need validation.

Extended static audit passes, hashes these five original helper bodies, and records recentering/parent rules. No executable or native behavior tests were performed this pass. Full trait-zone behavior remains open; no production edits or deployment.


## Nonzero obstruction-cone execution — 2026-11-11

Extended the existing controller fixture (no new generated installation) with756 original `824F5F78` steps: six signed axes, origin scales0/.25/1, angles.1/.3 radians, each of seven rays as sole hit, and three consecutive stages (hit, retained point without fresh intersection,20-unit transverse camera displacement invalidating that point). The original ray wrapper executes and the existing controlled intersection adapter records all seven request endpoints. Independent checks establish end spread=segmentLength*sin(angle), start spread=originScale*endSpread, and offsets perpendicular to the segment. Each step checks upper/selected fractions, cached world coordinates, validity byte, query count, stack and LR.

All756 steps pass, as do the existing controller suites and144 activation cases. Original-body verification passes70 common bodies; extraction still uses103 controller/target-builder bodies. Current log: isolated/controller-test.log. This closes the previously unexecuted nonzero-width retention/lateral-invalidation cases for these fixtures, not arbitrary cone angles, exact lateral thresholds, competing intersections, moving collision geometry or native collision-world parity. World intersections remain controlled.

Current production inspection reconfirms Bridge::Evaluate resets its synthetic editor record each evaluation and calls selection/alignment without original movement suppression, while advanced_forge.cpp still uses spawn-only radius*2+1 clearance and a native-ten-unit-cap workaround. These remain implementation gaps; passing the research fixture does not fix deployed magnets or re-grab behavior. No production edits or deployment this pass.


## Held-body feedback through moving marker positions — 2026-11-11

Extended the existing78-tick held-update test with a second78-tick run that integrates returned body velocity using a controlled .05-second step and updates the synthetic object's position and marker world position before the next tick. No original body changes: `8244A8D8`, selection/scoring/alignment, movement suppression and physics submission/controller still execute. Independent expected controller velocity now uses (expected target - current body position)/.2 instead of assuming a stationary origin. The explicit unsnapped editor target remains distinct from the snapped physics target.

All156 ticks pass across six signed directions, magnets on/off, movement/stop/snap, resume/pull-away, disable, out-of-range candidate, candidate loss and reacquisition. The updated fixture verifies these transitions while feeding the resulting motion back into marker lookup rather than freezing the object at the origin. All other controller suites and144 activation checks also pass. Existing generated outputs/logs were reused.

Limit: this is a synthetic collision-free integrator, not original Havok simulation; it does not model contacts, attached objects, moving targets, live input or network replication. Camera/monitor and grab/release suites remain separately exercised, so this is not an end-to-end native grab/re-grab proof. No production hooks or installed files changed.


## Moving snap-target feedback sequence — 2026-11-11

Added54 held-update ticks to the same fixture: six signed directions through nine stages, with both held-body velocity feedback and a changing target marker position. Target position advances .02 per tick while active, with the established explicit out-of-range/lost/reacquired stages. Original selection/alignment/controller follows the changing target on stopped/snap ticks; resumed movement returns to the distinct accumulated free-drag target. Assertions independently check that retained editor target does not drift with the moving snap target, controller velocity uses current body-to-target error, and candidate identity survives or clears at the expected stages.

All210 held-update ticks pass (78 stationary,78 moving-held,54 moving-held/moving-target); remaining controller and144 activation checks also pass. This strengthens the continuous-state requirement for the replacement bridge, whose current per-evaluation editor reset remains incompatible. Synthetic markers/scene and collision-free velocity integration remain explicit limitations. No native interaction sequence, production edit or deployment occurred.


## Player dispatcher gates around the coupled placement path — 2026-11-11

Original `8244D0E0` (file196), beyond the previously recorded call order, gates the coupled update on editor eligibility, valid held datum, ownership predicate `822ED938`, no parent at held-object36, valid physics instance at240, and bit0x4 in instance flags16. Instance records use176-byte stride here. Branches D514..D628 establish these conditions; parented objects and nonmatching physics flags do not run this coupled local path. This is separate from inner controller activation/motion-type checks. It must not be replaced by an unconditional per-object pose hook.

Ownership predicate `822ED938` (file91) requires TLS140 structure byte104 enabled, resolves a valid player via `822714E0`, and compares six identity bytes105..110 against player20..25. It does not merely test a player index or assume player0. Identity naming and network ownership transitions remain open.

For the default switch path the original order remains rotation processing, editor36=max(editor36-editor40,0), distance clamp, held-object update, monitor update. Afterwards, if still holding an object, `8225EA20` refreshes the cached held point at editor8..16. That post-update write affects later prediction and must be preserved when connecting the separately tested functions. Session-specific surrounding callbacks, preview selection, parented handling and complete dispatcher execution remain open.

Extended audit_placement_flow.py checks the ownership/parent/physics branch evidence and records the gate contract; static audit passes. This does not execute the dispatcher or close the full interaction proof. No production edits or deployment.


## H3 player ownership and integration entry correspondence — 2026-11-11

Original H3 `821F0688` compares the same six-byte player identity20..25 as H4 `822ED938`. H3 uses TLS124 local structure enabled108/identity109..114 and TLS96 player stride880; H4 uses TLS140 enabled104/identity105..110 and validated player stride4144. The controller fixture now executes both unchanged functions in separate namespaces across224 paired cases (16 slots, enabled/disabled, exact match or mismatch at each byte), plus H4 null-player rejection. All pass, including stack/LR preservation. H4 datum lookup is controlled; H3 direct indexing requires a valid caller-owned player slot. This is not a networking/system-link test.

H3 `8227E5A0` gates editor state through TLS100 halfword57748 and validates player40 controlled-unit tag against `82261480`. H3 held resolution in `82281A98` uses engine+57752+4*player for the variant slot, then engine+428+84*slot for its datum. `82282378` invokes this update when player40 is valid, then retains additional local-view/session/object work. Its existing vtable104 entry is therefore a confirmed per-player entry point, not authorization to replace the whole callback with only magnet evaluation. H3's parent restriction in this region is conditional on session mode; H4's coupled local path requires no parent. Complete session correspondence remains open.

The H3 static audit now records22 original bodies and these adapter boundaries. All controller suites and144 activation cases pass after the ownership additions. No production changes or deployment; connected dispatcher and native lifecycle verification remain outstanding.


## Executed H3/H4 controller comparison — 2026-11-11

The existing controller extraction now also includes unchanged H3 `82629000` and its register helpers in the H3 namespace. Explicit adapters map H3 position224/quaternion288/linear384/angular400/motion160 and setter slots60/64 to the already-tested H4 layouts. Callbacks copy outputs and record activation/relocation; they do not run native Havok.

162 paired original-code cases cover three axes, requested linear speed -2/0/+2, angular target quaternion angle -.4/0/+.4, timesteps .05/.2, and positional error0/.1/10 (including relocation). Initial orientation is identity and initial velocities zero. Output position and linear/angular vectors agree within1e-4 in these cases; relocation counts and register frames agree. Callback counts differ in87 cases, consistent with H4's suppression versus H3's unconditional final writes. This supports sharing body-operation primitives, not substituting H3's full routine for H4's decisions.

The first fixture attempt incorrectly assumed the engines' constant pages did not overlap, yielding H4 zero velocities versus H3 nonzero. Inspection located H4 constants in the same first page as H3 constants. The fixture now switches the original first4096-byte page before each respective call; the numerical mismatch disappeared. Original bodies are unchanged. Remaining H4 image bytes stay intact. Final controller suite and144 activation checks pass; current controller-test.log is retained.

Arbitrary orientations, nonzero initial velocities, exact tolerance boundaries, real sleep/wake/contact effects and native integration remain open. No production changes or deployment.


## Controller comparison with existing motion and compound orientation — 2026-11-11

Expanded the paired original-controller suite from162 to486 cases. The added profiles initialize nonzero linear(.3,.4,-.2) and angular(.1,-.2,.3) vectors plus a normalized quaternion for a .7-radian rotation about(1,2,3), tested with both quaternion signs. These use the existing signed targets, two timesteps and three positional errors including relocation. The fixture now also compares final orientation, in addition to position, linear/angular output, relocation counts and stack/LR.

All486 numerical comparisons pass at the stated tolerances;195 cases differ in callback counts. This confirms the selected cross-version field mapping under existing motion and a compound initial orientation, while preserving the earlier conclusion that H3's controller is not a drop-in replacement for H4's callback decisions. Other controller suites and144 activation checks pass. World wake/setter/relocation remain simulated; contacts, sleep behavior and native integration remain unverified.

A user decision is pending for H4 trait-zone compatibility: adding Spartan-only gameplay/companion metadata versus preserving stock H3/360 behavior with trait-zone gameplay unsupported. Neither option has been selected; no implementation or export assumption is authorized by the question. Full RE coverage remains in scope.


## Scenery-only scope and original H3 motion writes

User clarification supersedes the full-editor scope: all aspects of scenery manipulation are required; everything else stays stock H3, with advanced rotation and translation controls available. Stock H3/360 compatibility is mandatory; trait-zone gameplay is excluded. See the controlling scope in FULL-RE-PLAN.md.

Controller fixture now executes unchanged H3 sub_82662340 and sub_82662350 instead of copying velocity vectors in test callbacks. Original bodies write motion+224 and motion+240 (body+384/+400 with motion at body+160). The original image contains nine adjacent references to this setter pair, at first-slot addresses 82001BF8,82001C60,82016458,820164C0,82016530,820165A0,82016608,82016670,820166E0. Constructor/vtable receiver validation remains outstanding; these references alone do not prove every live motion type uses these setters. All486 paired controller cases still pass, with195 callback-count differences retained. Wake/relocation and the world remain simulated; no native placement fix or deployment is claimed.


## Stock H3 motion submission boundary

Inspected original 820F29C8 and its callees, rather than treating the body setters as a complete object API. 820F29C8 first calls8232EA98 (r6=0), then820F2AE0 (r6=1), conditionally820F2DD0 for nonzero requested motion, followed by820F2A78 and820F2EC8. 8232EA98 copies nullable linear/angular triplets into object+120/+132, assembles update bits16/32 and calls820B8768 when appropriate. Thus a direct motion-body setter does not reproduce this object-level contract.

820F2AE0 resolves object physics datum+160, uses144-byte physics-instance records and72-byte body entries, skips body motion types6/7, and calls820F8DC0/820FAED0 for nullable linear/angular requests. Type1 uses the instance's selected body; other object types iterate all bodies. There are additional object+172 and instance flags/eligibility branches. 820F2EC8 handles parent/header state and may call82333308. Exact downstream synchronization semantics and native execution remain open; do not claim network parity from static flags.

Integration consequence: keep the stock H3 object state/notification boundary and explicit per-body routing when implementing scenery control. Simply calling the numerically similar H3 controller or writing body velocities is insufficient. audit_h3_held_update.py now checks25 original bodies, including this call order, field writes and routing. Static audit passes; no production changes or deployment.


## Original movement predicate integrated into the isolated bridge

forge_bridge now accepts a processedMovement triplet and executes original82582178 after successful candidate selection, before alignment, matching the audited8244EED8 ordering. Candidate identity survives movement suppression. Private H4 player/unit records resolve the triplet at unit1348/1352/1356; scene objects0..63 remain separate from private monitor index64. No handwritten threshold or replacement movement rule was introduced. extract_forge.py now includes the unchanged predicate; verify_original.py confirms all71 extracted bodies match ReXGlue.

The bridge suite passes12 new positive/zero/negative/zero sequences across all three axes, checking retained candidate and stop/resume alignment, plus its existing selection, visibility, coordinates and physics-property tests. These are isolated scene tests, not a proof of native detachment. The live H3 caller does not yet populate processedMovement, whose default is zero; installed behavior has not changed. Live adapter ownership/field lifetime and unsnapped-target integration remain required before deployment. Coincident snapping and re-grab clearance are not fixed by this step.


## Scoped live H3 input adapter (candidate only)

The original82281A98 hook now captures the current player's controlled-unit processed movement from TLS96 player table, stride880, player+40, then salt-validated object header and unit+496/+500/+504. An RAII scope limits the sample to that held-update invocation and restores prior state across nested calls. Scene construction uses the sample only for the matched held-slot owner; menu placements outside that invocation retain stationary semantics. Existing original ownership/session checks still decide whether placement is reached. No raw host input, timing change, map change or saved-format extension was added.

Candidate halo3mp build succeeds. Existing original input-chain tests pass, including300 H3 producer/writer-to-H4 predicate cases. Bridge selection/visibility/coordinate/property tests pass. These do not execute the new scope in a live game: player identity, timing, unsnapped target retention and actual detach remain native-validation requirements. No deployment.

Private scene diagnostics now write AFS2 with the processedMovement triplet so replay cannot silently turn a moving scene into a stationary one. AFS1 remains readable with zero movement. Both moving AFS2 and stationary legacy replay are checked by the bridge fixture. These are repository test artifacts, not Halo3 saved content or companion gameplay metadata.


Original H3 grab8227E810 (generated file75) establishes engine+0xe1d8+4*player from the length of its reconstructed held point minus controlled-unit position, then clamps using original constants820228AC and82024334 (10 and2). This differs from the H4 projected-distance/size-config policy already tested. The existing spawn-only override does not address this re-grab clamp. Replacement must account for both initialization and subsequent native held-distance saturation, not merely widen the palette-create path. Native movement-gate test is running separately; no grab replacement yet.


## 2026-11-12: sequencing correction and original distance API

The native movement-gate run `.local/loading-traces/20261111-235654-1908` was explicitly stopped on user instruction at122.578seconds, before the scheduled captures. Its forced exit is not a product crash or a passing test. Finish scenery RE and implementation before any further tests. No test or build was run after that instruction.

Added Bridge::ConstrainHeldDistance, which invokes unchanged original82452738 and its original configuration getters in private H4 memory. Inputs are requested distance, runtime radius, active flag and already-mapped H4 processed distance input; no device-axis inference is made. Missing held object uses the original default-distance path. This entry is not yet wired into live grab/re-grab or push/pull. It does not replace original projection, persistent offset state or coupled object/monitor physics, all of which still need integration.

Updated extract_config.py and bridge loader to consume the full88-byte Ravine Forge settings. The previous80-byte extraction omitted maximum-distance and multiplier fields. Regenerated the private data from the original source cache: SHA256 0aa93e946f5ba028c26b21e4d892dd6996512c302e5eea87221e39756c9777a7; legacy80-byte SHA remains9c205c82650d8e536523651118290feeee07156308bbc5bea078eb825de1b228. Metadata records both. extract_forge.py now extracts75 unchanged bodies including the distance routine and getters. This is source extraction/implementation, not new test evidence. The config audit's length handling was updated for both legacy and complete metadata, but not run. Installed data/build remain untouched.


## Persistent target ownership and rotation writeback boundary

Re-read complete original8244A8D8 while preparing the session integration. The transform at editor+84 is persistent; its translation at+124/+128/+132 accumulates processed monitor movement plus the velocity-derived correction, is clamped to variant bounds, is limited relative to the current held-object point, and is clamped again. At8244AD88 onward the function copies52 bytes of that transform into a stack submission transform. Original8244EED8 modifies the stack copy;82452930 submits that copy. Snapped position must never become the persistent editor translation merely because the visible object moved.

Rotation quantization has a distinct writeback rule: with nonzero rotation-step setting224 and rotation flag81,82451A38 quantizes the submission transform. The nine basis components are compared against editor136..168 using the original epsilon. A changed quantized basis causes the full52-byte transform to be copied back to editor84 and updates the nine-component remembered basis. This happens before magnets. Therefore a blanket policy of never writing a submission transform back would also be wrong: quantized rotation can update persistent state, magnet alignment cannot.

This source distinction determines the replacement state design: retain original editor state across ticks, keep physical/snapped submission separate, and preserve original conditional quantization writeback. The current scene-only Evaluate reset must be superseded by that complete session path rather than removed on its own. No tests/builds executed.


## Original physics-state selection entry and H3 per-body boundary

Implemented Bridge::SelectPhysicsState using unchanged8244A180. The host supplies held ownership, original keyframed/special predicate results and variant presence; private variant/object records supply the menu property word. The selector itself derives the original four-state result. It is not connected to ApplyPhysics yet: genuine H3 predicate counterparts and state application are required first. extract_forge.py now includes76 bodies and14 explicit data boundaries. No compilation or tests were run.

Source inspection of H3 per-body wrappers820F8DC0 (file91) and820FAED0 (file41) narrows a crucial distinction from820F2AE0: the object-wide writer skips motion classes6 and7, whereas each per-body wrapper rejects7 only. The angular wrapper additionally honors body-entry byte68 bit1. Both copy the requested XYZ into an aligned four-component vector with the original zero fourth component, then call82253588/82253418. These call original activation82651968 and dispatch the motion receiver body+160 through virtual slots60/64 respectively. Therefore keyframed body control cannot be routed blindly through the object-wide writer, and angular body constraints must not be lost by using raw velocity stores. No class-name equivalence or live parity beyond the established source layout is claimed.

Re-read8244A2A0: its four-state application modifies flags, rebuilds/creates physics as needed, then compensates the editor grab offset for the resulting object-point displacement and resets its decay. Merely switching frozen/disconnected flags omits this compensation and can change the held point. Live replacement remains unfinished; installed build unchanged.


## Physics selector predicate distinctions — 2026-11-12

Original82469630 checks the authored physics-model tag, not current Havok motion: it traverses object tag+148 ->model+60 ->physics-model block92/96, scans192-byte bodies and returns true if ANY byte at body+28 is4. H3's existing AuthoredPhysics helper instead recognizes ALL176-byte bodies with short+26 equal5 (fixed). These predicates are not interchangeable. Added AuthoredKeyframedBody for the H3 stock tag chain already used by AuthoredPhysics, scanning for any short+26 equal4; missing tags/empty bodies are false and invalid address ranges remain unavailable rather than silently dynamic. The local H3 PhysicsModel schema confirms0xB0 bodies and enum Keyframed4/Fixed5. This helper is not wired into live mode application yet and has not been built/tested.

The previously labelled "special-body" predicate8244A5F0 is not purely a body predicate. It requires game state TLS28+50364 within1..5 with a nonnull entry in table835719E0; active session predicate82265430 (TLS48 with first/second byte set and session word24 equal4);821DF530 returning1; and a valid object's multiplayer block (offset in object halfword486), whose halfword20 has bit0x4000. The runtime flag is not directly the tag's small MultiplayerObjectFlags enum. Its producer and H3 correspondence remain open. Renamed the bridge input to normalStateOverride and corrected the boundary description to avoid treating this as a guessed physical classification.

No tests, builds, game launches or deployment.


## Deferred-release state correspondence — source trace, 2026-11-12

Source inspection only; no build, test or deployment.

H4 `8244A5F0` is not an authored-body classification. Its object-side condition is multiplayer block +20 bit `0x4000`, additionally gated by game/session state. `8244F300` sets that flag while appending to the deferred-release queue (TLS28 game +12780 count, +12268 datums, +12396 vectors; capacity32). Release transaction `82451250` calls this enqueue path. `8244F5D8` removes an entry, swaps the final datum/vector into the gap, clears the flag and notifies through `827FC618`; the grab path `82450E10` calls it with search index -1. `8244F400` advances this queue each tick. Thus the selector override depends on release lifecycle, not merely the menu physics value.

H3 has a corresponding queue: TLS100 engine +59560 count, +58536 datums and +58792 vectors. Tick `82283A30` processes it. Source `halo3mp/generated/default/halo3mp_recomp.98.cpp`, function `82283B90`, establishes removal/search and swap-last behavior. It resolves the multiplayer block through object +340 and clears block +0 bit `0x0800`, then invokes `820B8768(datum,4096)`. This is the native H3 queue flag; do not transplant H4 offsets or bits.

`82283CF8` (generated file45) wraps that removal with additional eligibility, release-state, placement and invalid-position cleanup calls. It is not interchangeable with the raw dequeue routine. Remaining work: trace the H3 enqueue writer and state predicates before wiring the selector override, then preserve native H3 notifications and lifecycle in the scenery adapter. These correspondences do not establish completed implementation or tested behavior.


### H3 release enqueue and eligibility — source trace, 2026-11-12

`82283950` (H3 generated file61) is the native enqueue writer: it calls `8227EB28`, returns if already eligible/queued, rejects count >=64, increments engine +59560, stores the datum at +58536 +4*index, initializes the vector at +58792 +12*index, sets multiplayer block +0 bit0x0800 and notifies `820B8768(datum,4096)`. `82280D80` and `82280F98` initialize/reset the64 datum slots to -1 and count to zero.

The native predicate `8227EB28` (file103) is stronger than a raw queue lookup: engine +81228 must be1..10 with a non-null entry in the original table, TLS128 session +16 must equal2, the short session subtype at +568 must equal5, and the datum must occur in the queue. Therefore the adapter must retain native context eligibility rather than infer the H4 normal-state override from the flag or queue membership alone. This completes the enqueue/dequeue correspondence; state application remains open.

### Physics rebuild boundary — source trace, 2026-11-12

Re-reading H4 `8244A2A0` confirms the four-state flag table already recorded above. Its state2 depends on holder ownership, and its post-rebuild offset compensation must accompany the state change. Current production `ApplyPhysics` still freezes both Fixed and Phased and forces dynamics for every explicit mode, so it does not implement this table. Do not treat the available isolated selector API as completed native integration.

H3 `8232EB28` (file77) is not an unconditional force-dynamic setter: it first rejects object definitions whose flag at +2 has bit11 set, returns when the requested bit20 already matches, and otherwise changes object +172 bit20 and tail-calls `821CB8D8(datum,0)`. The adapter must respect this authored restriction.

H3 rebuild `821CB8D8` (file12) resolves a144-byte physics instance, preserves instance flag bit3, removes/recreates through `82262688` and `82261C20`, and runs `821CB6D8` before additional object-state handling. H4 `82388A08` (file152) resolves a176-byte instance, preserves a different instance flag (bit2), removes/recreates through `8249AFD0` and `8249A070`, runs `82388700`, additionally handles affected child objects, and finishes through `8248F448`. Thus passing H4 flags directly to H3 rebuild is invalid. H4 missing-instance path `82388C68(datum,1,1)` separately permits creation; the current H3 runtime setter does not establish an equivalent missing-instance path.

Next implementation prerequisite: trace the body-creation consumers of the H4 state masks and corresponding H3 creation inputs, then integrate selector, rebuild/create, holder-offset compensation and deferred release as one lifecycle. No tests, builds, launches or deployment were performed in this source pass.


### Body creation: Phased requires keyframed bodies — source trace, 2026-11-12

H4 rebuild dispatch `8249A070` (file100) routes ordinary scenery to `824A1578`, which calls `824A1610` (file287) to derive per-body motion classes. For the unparented scenery path, `824A1610` tests object +256 bit6 (frozen) and bit22. Frozen selects runtime motion5; when not frozen, bit22 selects runtime motion4. The authored-body conversion maps authored keyframed4 to runtime4 and authored fixed5 to runtime5. Therefore the locally owned Phased state's bit22 is a keyframed-motion request, not evidence that the object should be disconnected from the physics world. Existing production disconnect behavior is not source-backed parity and remains to be replaced in the complete adapter. Parent/inactive-root rules and per-body forced-keyframe flag0x40 precede or override this selection and must be preserved.

H3 rebuild dispatch `82261C20` (file48) routes ordinary scenery to `82267A88` (file79). That routine prepares a per-body motion array from the authored short at body +26, with fixed runtime7 and keyframed runtime6. Its argument r4 forces fixed, while r5 requests keyframed for eligible non-fixed bodies, subject to node flags. `82267DD8` (file22) consumes this array and passes the selected class on the stack to `822698A0` (file45), which constructs the body.

`822698A0` reads incoming motion at entry-stack +92 (internal frame544, load636). Native object bit20 changes fixed runtime7 to dynamic runtime4 and updates related collision/group arguments. Native object bit6 then forces runtime7; degenerate mass information also forces fixed unless the requested motion is keyframed6. This shows why simply setting the existing force-dynamic bit cannot reproduce H4 Phased. A native keyframed6 creation path exists, but the adapter must supply it at the correct stage, preserve eligibility and body flags, and pair it with the original controller/offset lifecycle.

Source-backed creation chains now located:
- H4: `82388A08 -> 8249A070 -> 824A1578 -> 824A1610 -> 824A1C30`, followed by body installation.
- H3: `821CB8D8 -> 82261C20 -> 82267A88 -> 82267DD8 -> 822698A0`.

Outstanding: H4 forced-dynamic handling for authored fixed bodies, corresponding body/group construction semantics, missing-instance creation, and coordinated scenery-only integration. No native behavior change or test result is claimed by this trace.


### Original physics transition added to production bridge — 2026-11-12

`forge_bridge.h/.cpp` now exposes `TransitionPhysics` and a native body adapter boundary. It executes unchanged original `8244A2A0` in the private H4 arena rather than rewriting its four-state flag table or offset arithmetic. Host data supplies holder ownership, model/instance availability, initial original-layout flags, point and retained offset/scale/decay. At the original create/rebuild call, the adapter receives the requested H4 flags and creation choice; it returns translated post-operation flags, native instance availability and the new object point. Original code then performs frozen-state bookkeeping and holder-offset compensation. H4 flag words remain private; the API explicitly prohibits copying them into H3 objects or saves.

The extractor now includes77 unchanged original functions and18 explicit world boundaries. The new boundaries are object-point query, local-holder ownership, instance creation and rebuild. Private tag slots1/2/3 preserve Forge globals in slot0. Re-entry into the private arena during a body callback is rejected. Existing native `ApplyPhysics` is deliberately not wired to this API until the body mapping and remaining held-controller lifecycle are complete. This is implementation progress, not a native fix, build result or passing test.

Further source trace locates H4 final body construction at `824A39A0`, called by `824A1C30` (file7). The body motion is passed as a byte at caller stack +87, with a separate body configuration byte at +95. The analogous H3 constructor `822698A0` receives motion as a word at caller stack +92. These layouts are not interchangeable. Next: finish H4 fixed-to-dynamic creation handling and map it into the native callback without bypassing H3 body/group rules.

No builds, tests, game launches or deployments were run. Only original-source extraction and source edits were performed.


### Native scenery body adapter implementation — 2026-11-12

H4 `824A39A0` (file32) resolves the remaining force-dynamic branch: when object bit21 is set and incoming motion is fixed5, it selects dynamic3 or keyframed4 according to bit22 and updates the collision/group category. Degenerate mass forces fixed except for keyframed4. This confirms the mode must be selected before dependent body configuration, not by changing a completed body after creation.

H3 missing-instance creation is `821CBB88` (file108), corresponding to H4 `82388C68`: it takes object, creation mode and force flag, checks native creation eligibility, and dispatches through the original create path. Native rebuild remains `821CB8D8`.

Added `RebuildSceneryPhysics` in `advanced_forge.cpp` as the native callback for the original transition API. It validates the salted object, scenery/crate type, unparented state and authored override restriction; maps only H4 frozen6/force-dynamic21 into native H3 frozen6/force-dynamic20; invokes original native create/rebuild once; and returns the original object-point query, actual flags and instance availability for H4 offset compensation. Other native flag bits remain untouched.

For H4 keyframed requests, a thread-local, datum-scoped hook at native `82267DD8` temporarily supplies runtime6 in the per-body motion array. This occurs before compound-shape, collision-group and final body construction decisions. The original motion array is restored after each call, including unwinding. The native64-entry capacity is enforced. Ordinary H3 creation and other objects bypass the override.

The callback is not yet connected to live `ApplyPhysics`; holder state/offset persistence, activation/release ordering and downstream contact semantics remain to integrate. No claim of a functional fix: source only, unbuilt and untested under the user's sequencing instruction.


### Held-state storage: native ray point is not an H4 grab offset — 2026-11-12

Source review of H3 `8227E810` (file75), `822800B0` (file106), `8227E460` (file1) and `82281268` (file43) resolves a critical integration distinction. H3 engine +57880 +12*player stores the camera-ray result: `82281268` writes the hit point returned by `820AD3E0`, or camera origin plus direction*distance on a miss. Engine +58072 +12*player stores the corresponding hit normal/fallback normal; +58264 +12*player stores the direction. These fields must not be treated as H4 editor +56 grab-offset storage.

`8227E460` returns object raw position (+32) minus the original `820A9E58` point. H3 grab `8227E810` adds that vector to the stored ray point, subtracts monitor point (`820CF158`), computes Euclidean length, and writes the distance at engine +57816 +4*player, clamped to native2..10. This differs from original H4's projected distance and persistent offset/scale/decay state. Copying H4 offset compensation into H3's ray point would corrupt the next ray/placement step.

`822800B0` validates the variant slot and exclusive holder, performs the native attachment/variant transaction, assigns the slot at +57752 +4*player, and invokes native raw dequeue `82283B90(datum,-1)`. Retain this native ownership/save transaction; keep the H4 manipulation state separately and initialize it from the original H4 grab path.

Implementation dependency clarified: per-player original H4 editor state must carry the retained offset, scale/decay and unsnapped transform. The native transition adapter's result belongs there, not in the native ray-point array. The original held tick must consume that state before the current direct-pose path can be replaced. No behavior or tests were run during this source inspection.


### Persistent held-state physics boundary — 2026-11-12

Added `HeldEditorState`, holding the exact336 original per-player editor bytes, and `TransitionHeldPhysics`. The state requires an explicit original initialization result; default zeroing is not represented as a valid grab. The transition reads original scale/decay at36/40 and offset56..64, executes the original physics transition with the native adapter, and commits only those original fields. In particular, it preserves the persistent unsnapped transform at84 and the original preferences and cached fields. Native holder presence must agree with the original held-datum sentinel. This is the storage/physics boundary; full original grab initialization and held-tick wiring remain incomplete.

Re-reading original `82449ED8` and its helper `8225EA20` (file30) revealed that the latter copies exactly three words from unparented object +100/+104/+108 into editor +8..16. For parented objects it transforms that vector through a parent-node transform via `822633F0`. The historical grab fixture's16-byte zero fill is not an adequate model of this field and cannot establish full initialization parity. Do not name it object identity or initialize it by guessing. Preserve the actual original query in the production grab integration.

The original grab path `82450E10` selects/reset state, dequeues release, selects/applies physics, then initializes persistent transform and projected distance. Native `822800B0` must retain its ownership/variant transaction; the new original editor state belongs alongside it. No builds, tests, launches or deployment were performed.


### Original editor constructor integrated — 2026-11-12

H4 initialization `8244C210` (file217) invokes `82449DD8` for each of16 editor records at game+6892+336*player. `82449DD8` (file129) sets original held/candidate/index sentinels, configured default distance, offset/decay fields, rotation defaults, magnet preference byte82, sensitivity word268 and control flags. It does not clear all336 bytes. The original image pointers at833F7EA0 and833F7E98 both resolve to82125110, whose three words are zero; retain these original pointers/constants rather than fixture replacements.

`Bridge::InitializeHeldEditorState` now executes that unchanged constructor over explicit caller-provided backing bytes and returns the entire initialized state, preserving fields the constructor does not write. It requires a lifecycle-event sink and forwards the original `forge_mode_init` event; original selection uses `forge_mode_pickup_item` and `forge_mode_drop_item`. These strings were read from the original image at82131288/82131298/821312B0. The native event sink cannot reenter the shared private arena. Constructor/selection callers do not consume the returned event handle.

Source extraction now contains78 unchanged original functions with19 external boundaries. This implements original editor construction, not the full grab operation. Original grab/reset world adapters, per-player live ownership and the persistent held update remain to wire. No build, test or deployment was performed.


### Original held selection/reset integrated — 2026-11-12

Added `Bridge::SelectHeldObject`, executing unchanged `82449ED8` over a supplied persistent336-byte editor record. It supports the original16 player slots, preserves native datum IDs at the world boundary, and copies back the full original result. The original routine retains preferences, resets only its documented release fields, updates the object reference vector, performs local-holder focus calculations and emits the original pickup/drop events. Original `825826B0` continues to handle marker visibility; the host receives the resulting native datum set without helper objects entering the saved world.

New `HeldSelectionWorld` callbacks explicitly supply the original object-point query, three-float object reference vector, local holder status, focus lookup and lifecycle event sink. Reference vectors are written as exactly12 bytes, matching original8225EA20, not the historical fixture's16-byte zero fill. Missing callbacks are rejected; no synthetic world answers are substituted. Callback re-entry is rejected through the existing arena guards.

Extraction now includes80 unchanged bodies and21 explicit world boundaries. This completes the original selection/reset stage in the bridge, not the full grab transaction: `82450E10` still requires its native attachment/variant/dequeue/physics/pose/projected-distance sequence and the continuous held update. The live production path remains unchanged and unverified. No builds, tests or deployment.


### Correction: body point and object origin are different queries — 2026-11-12

Direct source comparison corrects an earlier mapping assumption in the new, unwired native adapter. H4 `8225EA20` copies object +100..108 (or transforms it through the parent); H3 `820A9E58` copies object +84..92 (or transforms through the parent). These are counterpart object-origin queries. H4 `82251B38` confirms +100..108 becomes transform translation +40..48, while +112/+124 supplies the basis. The earlier generic reference-vector name should be understood as this origin query.

H4 `82260B58` instead resolves the root, checks physics eligibility, selects the instance's body index and calls `8228FD18` for its point, falling back to object +64..72. It is not equivalent to H3 `820A9E58`. H4 grab pose helper `82452820` similarly selects the physics-body transform through `822AD348`, with a specific character branch, then falls back to object transform `82251B38`.

Corrected `RebuildSceneryPhysics`: it no longer calls `820A9E58` as the post-rebuild point. It requires an explicit native physics-point adapter, rejects a missing adapter before mutation, and rejects nonfinite returned coordinates. The body-point selection and pose-query mapping remain prerequisites to live wiring; no fallback is invented. This correction supersedes the earlier note claiming that native820A9E58 was an adequate transition-point query.

No builds or tests were performed. The changed native adapter remains unwired.


### Native body-point mapping resolved — 2026-11-12

H3 `820AFA98` (file69) is the scenery counterpart of H4 `82260B58`: it traverses to the root, applies native physics-access eligibility (`82336770`), resolves the144-byte instance and signed selected-body index +12, calls `820AFBC0`, and otherwise returns the root's +32..40 fallback point. H4 uses instance176, index24 and fallback64..72. The extra H4 character-body selection branch is outside the scenery adapter. Native physics-access/thread eligibility is retained rather than replaced with H4 TLS offsets.

H3 `820AFBC0` (file82) corresponds directly to H4 `8228FD18` (file132). Both check instance bit8, fixed motion (H3 7 / H4 5), a valid authored-body index and its local center. In that case they transform the authored center by the body transform. Otherwise they read the live body center (H3 +256..264 / H4 +320..328). This is distinct from body transform translation (H3 +224 / H4 +288).

Added native vector wrappers that validate salted object handles, reserve guest-call stack scratch, call the original reader and reject nonfinite results. `NativePhysicsPoint` uses820AFA98; `NativeObjectOrigin` uses820A9E58. `RebuildSceneryPhysics` now uses the proven point reader directly, resolving the explicitly missing adapter from the previous entry. It remains unwired to live Forge while the full grab/held lifecycle is unfinished.

H4 transform reader `822AD348` copies the three basis columns and translation from body +240 into a52-byte scale/basis/translation structure. The matching H3 transform reader remains the next source boundary to locate. No builds, tests, launches or deployment.


### Native scenery grab-transform adapter � 2026-11-12

Source inspection identifies H3 `820FFAB0` (generated file97) as H4 `822AD348` (file160): selected body entry stride72/pointer64 versus stride60/pointer52; transform at body176 versus240. Both emit the52-byte scale/basis/translation structure. H3 `82118140` (file102) independently demonstrates the signed selected-index12/count36 checks and fallback through `820D8FA0`. Its final `821181F0` operation is not a pose query and is not reused.

H3 `820D8FA0` (file98) is the object-transform counterpart of H4 `82251B38`: basis from object96/108, translation84, optional parent-node composition through820ACF80. These readers are distinct from the body-center query already mapped.

Added unwired `NativeSceneryGrabPose` implementing the scenery branch of original H4 `82452820`: resolve native instance from object160 through pool828E62B4 (144-byte records), validate selected index, call original820FFAB0, otherwise call original820D8FA0. The adapter restricts types to scenery/crate, so it does not fabricate the H4 character-specific branch. It validates native ranges and finite returned values; it does not inject substitute transforms on invalid data. Full grab orchestration and persistent held updates remain incomplete.

Source-only work; no builds, tests, launches or deployment.


### Grab bounds integrated; initialization ordering retained — 2026-11-12

Re-read the entire original82450E10 (file43). Its post-physics sequence is conditional on instance body-count52 being nonzero. It reads the selected-body/object-fallback pose into editor84, clamps ONLY translation124 using variant bounds696 through82282580, then computes distance from cached editor44 minus the monitor point projected onto the orientation returned by82243068. It clamps that projected distance with82452738 and copies the held body's point to68. The distance is not Euclidean camera-to-object distance and is not derived from the clamped transform translation. The local recipient notification loop follows these writes. These distinct stages must remain ordered during live integration.

Added `Bridge::ConstrainGrabPose`, executing unchanged original82282580 on caller-supplied native variant min/max pairs. It returns a clamped52-byte transform representation while preserving scale/basis; it neither commits persistent editor state early nor substitutes arbitrary world limits. Source extraction now includes81 unchanged functions and21 world boundaries. Native bounds sourcing, monitor orientation mapping, complete grab orchestration and continuous held/release integration remain open.

Original82243068 (file123) first attempts the optional attachment-orientation service8281F4E0 when object304/308 enable it, falling back to8229D4E0. Treating raw camera angles as its result is not yet justified. This is the next source boundary for projected grab distance. No builds, tests, launches or deployment.


### Native monitor orientation reader mapped — 2026-11-12

H4 `8229D4E0` (file118), the ordinary fallback of82243068, corresponds to H3 `820B1928` (file15). Both accept datum plus optional forward/up outputs. Unparented H4 vectors112/124 map to H3 vectors96/108. Parented H4 uses parent36, node57 and node-array offset446; H3 uses parent16, signed node20 and signed node-array offset316. Both compose each vector through the selected52-byte parent-node transform. Calling H3's original reader preserves its own signed-field behavior.

Added unwired `NativeObjectOrientation`, calling820B1928 with separate forward/up guest buffers and finite-result validation. This supplies stock H3 monitor orientation to projected-distance initialization; it does not substitute held-object orientation or host camera angles. H4's optional8281F4E0 branch is not claimed equivalent to this reader. Importing that service into non-scenery monitor/gameplay is outside the user's narrowed stock-H3 mandate; any future adapter requiring that H4-specific branch must handle it explicitly.

Full grab ordering, persistent held update and release integration remain incomplete. No builds, tests, launches or deployment.


### Grab placement-state initialization connected — 2026-11-12

Added `GrabPlacement` and `Bridge::InitializeGrabPlacement` for the post-physics placement-state portion of82450E10. It requires the selected native datum to match the persistent editor, preserves the original bodyless early exit, uses original82282580 for pose translation bounds and original82452738 for radius/config/input distance. Inputs are explicitly post-physics world queries; this API does not supply synthetic bounds, monitor orientation or attachment answers.

The small projection adapter follows the inspected original generated instructions: cached editor44..52 minus monitor point, single-rounded component differences, Y multiplication, fused Z add, fused X add, each rounded exactly at the original single-precision operation. It uses double intermediates as in the ReX-generated original, not a generic dot helper or Euclidean distance. This arithmetic is a source-mapped integration adapter, not an unchanged extracted function.

On success it commits only transform84..135, constrained distance28 and held-point snapshot68..79 into the persistent336-byte state. It preserves physics-compensated offset56, scale36, decay40 and all preferences. Validation failures leave the caller's state unchanged. This stage is shared for grabs and re-grabs and has no spawn-only caller filter. Native ownership/variant/dequeue order, native world queries and subsequent notifications still need complete live orchestration; held/monitor updates and release remain incomplete.

No build or test was run; no deployment. This source implementation is not proof the reported re-grab defect is fixed.


### Native variant bounds and grab-world collection — 2026-11-12

H3 `822837C8` (file104) resolves the live variant at engine+120. Decoder821E01E0 (file25) reads192 bits into variant+260 and passes that same address to823C41C0 for bounded position decoding. That decoder (file7) copies six words and calls821AE060 (file83), which processes three axes with min at0/max at4 and advances the bounds pointer by8. Thus native variant260..283 maps to H4 variant696..719 without reinterpretation or invented limits.

Added `NativeVariantBounds`, validating and reading those six native bounds. Factored the already-mapped144-byte physics-instance resolution into `NativePhysicsInstance`; `NativeSceneryGrabPose` now shares it. Added `NativeGrabPlacement` to collect post-transition body availability, selected-body/object pose, real variant bounds, held/monitor points and native monitor orientation for the persistent bridge initializer. It is still unwired, as are the complete native grab/held/release transitions. The caller must supply an explicitly mapped radius and processed push/pull input.

Re-reading native822835E0 (file51) confirms the old spawn workaround's radius is the maximum of object-definition4 and the first model placement-block16, with its own minimum fallback. Do not silently use that as H4 runtime object76 in82452738: those are different source queries. Radius/input mapping remains a specific next prerequisite. No builds, tests, launches or deployment.


### Runtime radius and original manipulation-input producer integrated — 2026-11-12

Mapped runtime bounds rather than reusing the old authored placement-radius query. H3 object32/44 is its runtime center/radius:821ED730 (file110) passes these to820AEE78;8228A840 (file67) passes them to820AC0D0, whose projection/radius-squared operations confirm the sphere semantics. H4 object64/76 is the corresponding runtime center/radius:821EC400 (file58) passes these to824808B8 (file127), which compares plane distances against the supplied radius, and82452738 reads76 for grab clearance. NativeGrabPlacement now reads and validates object44 directly; callers cannot silently substitute822835E0's authored model radius.

Added `Bridge::ConsumeManipulationInput`, executing unchanged82368CE0 with an explicit native eligibility/held-object boundary82232AC8. Private persistent input state corresponds to H4 player1888..1907. Supplied semantic movement/look axes, rotation-available flag and trigger are written to the original packet fields28/32,44/48,40,56. The original routine chooses dominant axes (including tie behavior), retains prior fields on paths that do not write them, toggles active state, and consumes movement packet values. The API returns both updated persistent state and remaining movement so integration can preserve ordinary-unit packet consumption.

Extraction now includes82 unchanged functions and22 boundaries. This does not claim native physical-axis direction mapping or live input integration: the adapter still must run before H3 consumes its packet, map axes from source, and suppress duplicate H3 edit-distance processing. Full native grab/held/release integration remains open. No builds, tests, launches or deployment.


### Native semantic movement input mapped — 2026-11-12

Re-read both original unit producers. H3 `821EC0E0` (file95) copies frame20/24 into the movement vector passed to820B8608, whose existing mapped writer places it at unit496/500. H3 `82383B08` (file42) combines496 times the forward basis plus500 times the lateral basis from82383988 (file99). The horizontal branch of that basis helper explicitly builds lateral=(-forward.y,forward.x,0), establishing positive-forward/positive-left semantics.

H4 `823619F8` (file276) copies frame28/32 into the corresponding movement vector;82361880 (file56) adjusts its vertical component or gates horizontal movement but does not invert/swap the first two components. Existing original writer mapping reaches unit1348/1352. Original8244A8D8 constructs horizontal movement as (forwardInput*heading.x-leftInput*heading.y, forwardInput*heading.y+leftInput*heading.x). Consequently native H3 frame20/24 maps directly to H4 frame28/32 by semantic direction. This does not claim a test of physical controller bindings. H4's distance subtraction versus H3's addition is an actual consumer difference, not justification for an adapter sign flip.

Added unwired `ReadNativeSceneryInput`: validates the native packet/player, uses original820B06A0 with held-output and null secondary-output just like821F04C0, and admits only valid scenery/crate objects. It reads the pre-consumption native forward/left values, trigger44 and rotation-available byte28. Raw look32/36 are retained explicitly; their rotation-axis sign correspondence remains a separate prerequisite, not a completed mapping. No packet writes occur in this reader, and non-scenery controls retain the native path.

Full pre-consumption hook, persistent input ownership, suppression of duplicate native edit-distance handling, rotation sign mapping and complete grab/held/release integration remain unfinished. No builds, tests, launches or deployment.


### Original held rotation and native predicate mapping integrated — 2026-11-12

Added `Bridge::RotateHeld`, executing unchanged8244A7D0,8244B518 and8244A6A8 plus their original math helpers. It copies persistent336-byte editor state into private storage, supplies explicit processed input, monitor view, tick interval and translated physics metadata, and copies the full updated state back. The original caller handles active input, negated roll, sticky rotation byte81 and offset-decay initialization40; the original transform handles signed-square response, normalization, threshold, trigonometry and composition while preserving translation. Native held datum is restored after private query remapping. The original zero-initialized force-decay global gets its own committed private page; no host toggle is introduced. Extraction now contains87 unchanged functions and22 world boundaries.

Native `8227F578` (file70) and H4 `8244A6A8` (file262) establish the physics mapping: native object172 connected bit7 -> H4 object256 bit8; native instance4 bit7 -> H4 instance16 bit7; body entry stride72/pointer64/motion168 -> H4 stride60/pointer52/motion232. Native fixed7 maps to H4 fixed5. Crucially H3 also rejects keyframed6, whereas H4 does not reject keyframed4. Reusing the native blocking result would incorrectly preserve that H3 restriction.

Added `NativeRotationPhysics` to populate the exact predicate inputs. Non-fixed motion is projected to0 solely because the original H4 predicate compares only against5; this is explicitly NOT a general Havok motion conversion. Native scenery6 remains H4 scenery6; native crate10 maps to H4 crate11 because H4 inserts dispenser9. Local TagTool Gen4 Pathfinding.ObjectTypeEnum and GameObjectTypeHalo3Retail corroborate these type identities. All other native types are rejected at this scenery-only adapter.

The production rotation stage is still unwired. Native monitor view-field sourcing, physical look-axis correspondence, packet-consumption timing, persistent lifecycle ownership, held movement/controller and release integration remain open. Source inspection is not functional proof. No builds, tests, launches or deployment.


### Native rotation view and input-consumption stage connected — 2026-11-12

Original H3 `820F6658` (file39) and H4 `82227810` (file59) are counterpart view-reset routines. They acquire the current unit vector at native424 versus H4 1260, then propagate it into desired/view history vectors and notify the object. This establishes the correct input for original8244B518. Native object orientation96/108, used by other queries, is not substituted for this unit view. Added `NativeMonitorRotationView` and `RotateNativeScenery`, which combine that view, mapped native rotation physics and unchanged native TLS188 tick interval with the original bridge rotation stage.

Source caller argument mapping also resolves the semantic rotation fields: native82281A98 passes player776/780/-772 as f1/f2/f3 to8227F768; H4 8244A7D0 passes1900/1904/-1896 to8244B518. Producers map native frame32/36 and H4 frame44/48 to the first two fields, and the second movement component to the third. Preserve the look signs; original H4's caller applies the roll negation. This is a semantic input mapping, not proof of physical-device binding equivalence or runtime behavior.

Added `ConsumeNativeSceneryInput` as the replacement producer stage: it invokes the original H4 input routine through the bridge, retains its private input state, writes back exactly the two movement components consumed by H4 and clears native player764 to disarm duplicate H3 edit-distance/rotation handling. It returns false for non-scenery/invalid editing context so the native producer remains responsible there. Its caller must skip native821F04C0 only when true is returned. The stage is not hooked yet; enabling it alone would be incomplete without the new held lifecycle.

Persistent per-player lifecycle orchestration, full held/monitor target calculation and submission, collision mapping and release remain unfinished. No builds, tests, launches or deployment.


### Persistent held target and original magnet caller - 2026-11-12

Read complete original8244A8D8 (file194),8244EED8 (file70) and8244A118 (file49). After movement/contact/displacement/bounds handling,8244AD8C..8244ADA0 copies52 bytes from editor84 into a separate stack submission. Quantization can update the persistent basis before8244AF10..8244AF34 passes that separate submission through magnets and82452930. Magnet alignment must not overwrite editor84, the movement accumulator.

Added production root8244EED8:90 unchanged original functions,22 boundaries. Bridge::ApplyHeldMagnets loads existing336-byte editor state without resetting preferences/offsets/pose/candidate, maps native IDs, invokes the unchanged enclosing caller and returns a separate13-float submission. Original code owns enabled gating, selection, movement suppression, quaternion conversion, candidate writeback and visibility transition. A previous candidate outside the nearby set receives a visibility-only private ID so removal can still resolve its native identity. Native IDs are restored before state copyback. No marker helpers enter native save data.

Scene.cursor/heldBasis/sensitivity are deliberately unused here: persistent editor state owns these inputs. Local ownership is explicit. Preceding held/monitor movement/contact/quantization and following native physics submission remain unfinished. Existing live Evaluate retains its legacy reset/direct-pose path until the whole lifecycle replacement is ready. Source extraction only; no builds/tests/launches/deployment. All three reported defects remain open.


### Held rotation-quantization ordering implemented - 2026-11-12

Added unchanged82451A38 to production extraction (91 original bodies,22 boundaries). PrepareHeldSubmission source-maps the enclosing8244ADA0..8244AF10 stage: mode224 and sticky rotation byte81 gate quantization; table833F195C selects0/90/45/30/15/5 degrees, converted using original82128A20. Quantizer consumes a separate52-byte submission. Its nine resulting basis floats are compared with editor136..168 using original epsilon82128A54. A changed remembered basis copies the quantized transform to editor84 and remembers the new basis. An unchanged remembered basis preserves the accumulated unquantized target while the outgoing submission stays quantized. Comparing to the current unsnapped basis instead would discard small accumulated rotations.

ApplyHeldMagnets now stages this state change and uses the returned submission rather than copying editor84 again. Original magnet selection still sees the persistent target. Successful completion commits staged editor state; invalid scene/candidate exceptions do not change caller-owned state. The earlier standalone quantizer source generator avoids a duplicate function definition now that production includes it. No test generator or test was executed; production extraction only.

The original held update's contact/world and physics submission boundaries remain unfinished, as does native lifecycle wiring. This change is source implementation, not native behavior proof. No builds, launches or deployment.


### Original enclosing held-update bridge implemented - 2026-11-12

Production extraction now includes unchanged8244A8D8 and8244B338:98 original bodies,29 explicit boundaries. Bridge::UpdateHeld loads existing per-player editor bytes and supplies scene/monitor/physics-instance/time/variant records, then calls8244A8D8 once. The original function owns velocity-dependent correction, its first-body transform-cache refresh every fifth tick, movement scaling, both bounds clamps, directional attenuation, contact projection, displacement limit, quantization/remembered-basis handling, magnets and final target request in source order. No-instance/no-body returns preserve state and report submitted=false rather than fabricating a target.

HeldUpdateWorld explicitly requires six native services: object motion, reference point, camera position, geometry containment, body transform, and contact vector. Monitor fields1212,1200 bit0,2168 and definition1428 remain individually named by source offset; no guessed native offsets/defaults are supplied. Physics and scene IDs are mapped privately; prior candidates absent from the current nearby set still resolve marker removal. Variant bounds are supplied at original696, unchanged tick interval at TLS88+8 and tick counter at+12. Tag0 retains Forge settings while private tag1 supplies the monitor definition field. Original8244B338 performs the distance correction using the native-service positions rather than replacing it with a clearance constant.

The82452930 boundary currently collects the exact final pose and controller parameter as HeldUpdateResult; it does not perform native physics submission. The native caller must map that original controller request, including body routing and notifications, before the path is live. Direct pose writes are not an implementation of this boundary. Missing native world callbacks are rejected; no no-contact/zero-motion/default-camera stand-ins are provided. Persistent state and visibility are committed after the original update returns.

Remaining required work: native world-service correspondence (including geometry containment/contact and monitor scaling fields), original monitor-follow update, controller submission, persistent lifecycle ownership and grab/release ordering. The original routine's presence does not establish these services or resolve the deployed defects. Source reads/edits/extraction only; no builds, tests, launches or deployment.


### Native motion and explicit body-transform adapters - 2026-11-12

Read H3 820AC960 (generated file97) against H4 82260CF0 (file237). Both resolve root ancestry, handle the frozen/global-vector branch, gate physics access, validate the selected body index, read body velocity when available, and otherwise copy object velocity. Native parent16/H4 parent36; native flags172 bit9/H4 flags256 bit10; native instance160/H4 instance240; selected index12/count36 versus24/count52; native fallback linear120/angular132 versus H4 linear136/angular148. Native linear reader820ACC10 (file82) returns body384..392 unless fixed7; angular820FAE68 (file24) reads400..408. These correspond to H4 body432/448 and fixed5.

Added NativeObjectMotion using the original native820AC960, explicitly setting r5=0 for the held update's linear-only query. It does not read raw object velocity as a substitute for physics, calculate velocity from frame differences, or map a zero fixture result. NativeObjectVector allocates process-local guest output and preserves the caller context.

Added NativeSceneryBodyPose(datum,index) using original820FFAB0 after validating native instance/body references. Refactored NativeSceneryGrabPose to reuse it for the instance-selected body, retaining original820D8FA0 fallback. The full H4 held update instead requests body0 every fifth tick when its geometry predicate is false; the adapter now supports that explicit distinction. Queries do not change native physics or save data.

These adapters are source implementations only. Full held-world callback construction, remaining native services, controller submission and lifecycle hooks remain open. No build/test/launch/deployment.


### Contact boundary correction: response and cached-point mutation - 2026-11-12

Read original H4 82235650 (file256) and located related native H3 820FFBE0 (file34) by their motion/physics-point/collector/velocity-setter chains. This corrects the earlier description of82235650 as a read-only contact-vector query. It resolves root ancestry, chooses object-type response settings, reads velocity and physics point, refreshes the caller's cached point, gathers contacts, compares competing contact responses, computes/applies velocity, updates root contact-state flags and performs type-specific notifications/state changes. The supplied r4 cached point is written at82235874..82235890 independently of the eventual true/false result. Its r5 output provides the accepted response normal consumed by8244A8D8.

Changed HeldUpdateWorld.contactVector to resolveContact with a mutable cachedPoint argument. The bridge now copies that point back to the original private editor even when no normal is returned. Documented that the adapter must preserve native velocity/flag/notification effects, not merely return a normal. This fixes a concrete omission in the unfinished bridge contract; no runtime fix is claimed.

Native820FFBE0 is related but NOT directly interchangeable: it takes datum and cached-point arguments, stores its normal in its own stack, and does not expose the H4 normal-output argument. H3 collects via822385C8 then calls82237E58 twice and applies velocity through820F29C8. H4 collects via82486B78 then calls824863F8 twice and applies through822D1158. H3 also supplies an additional origin vector to collection. H4 response coefficients come through a global definition block whereas H3 loads constants. Those geometry-input and response differences require explicit mapping, not a wrapper that calls native820FFBE0 and invents an output normal.

Mapped response-state storage for further integration: H4 object364 bit2 versus native276 bit2 early suppression; parent36 versus16; root contact flag H4 bit20 versus native bit19; H4 unit timestamp2188 versus native1008 and unit-mode byte3910 versus native1218. Scenery must retain only applicable branches; stock character behavior is not being replaced. Full contact-service implementation and native behavior remain open. Source inspection/edit/extraction only; no builds/tests/launches/deployment.


### Original multi-plane contact selector exposed - 2026-11-12

Read H4 824863F8/82486220 and native82237E58/82237C80 plus both collector caller conventions. Added original824863F8 root and unchanged dependencies:106 production bodies,29 boundaries. SelectContactResponse projects collected geometry into private records and invokes the unchanged H4 multi-plane selector. It does not call the H3 response selector or synthesize a normal. It retains original triangle-neighborhood checks, up-to-three contributing planes, reversal, degeneracy handling, signed approach threshold and residual calculation.

Original collector82486B78 has a256-record capacity and updates header0 primary index/header4 closest distance/header20 count. Records start at24 with stride32; pointer at+8, plane-distance value+12, closest-distance value+16, closest point+20. The selector reads the pointed triangle's normal at0 and three vertices at32/44/56. ContactSet/ContactSample expose these values without transferring native pointers. The selected-index list, normal, distance and squared residual are returned only when the original routine accepts the response. The collector's hit ranking and replacement policy remain upstream responsibilities, not recreated by this adapter.

The pure helper can be called from the unfinished enclosing contact adapter while the original held update is suspended. Its private stack170000 and scratch regionsF0000/100000/110000 are separate from the held update stack180000 and editor/scene records; it does not alter held-state scopes. This is source integration only, not proof from execution.

Native collector geometry mapping, H4 enclosing velocity/flag response, monitor-follow and controller/lifecycle wiring remain unfinished. No build/test/launch/deployment; source extraction only.


### Native scenery contact collection adapter - 2026-11-12

Compared H3 822385C8 and H4 82486B78 record creation and filtering. Both collect up to256 triangle contacts, keep a primary closest index/distance, replace the furthest retained contact at capacity, and store68-byte triangle data (normal0, vertices32/44/56). Both store32-byte records after a24-byte header: pointer8, plane distance12, closest distance16, closest point20. Triangle identifiers differ in representation/order, so the adapter does not copy their opaque metadata or pointers into H4 memory.

Added CollectNativeSceneryContacts using original native822385C8. The native call receives the actual scenery/crate type, point, origin, and explicitly supplied object/search radii. The object radius parameter corresponds to the definition radius passed by native820FFBE0 (tag4), not the runtime sphere radius used by grab distance. No response radius is invented. Scenery6 and crate10 make the vehicle-specific and biped-mode switches false; original surface filtering still executes. Native BSP enumeration stays native. The adapter copies finite normals/vertices/distances/closest points into ContactSet and preserves collection flags separately for the enclosing response.

The native call uses a bounded process-local guest scratch frame for its maximum8216-byte collection, then copies records synchronously before its lifetime ends. No copied native pointer is dereferenced by the H4 selector. This adapter is not live-wired; original H4 response radii/settings, the enclosing velocity/flag update and complete held-world construction remain required. It does not establish broader object-type collector equivalence or runtime visual/collision correctness. No builds/tests/launches/deployment.


### Original scenery contact response integrated into bridge - 2026-11-12

Added the unchanged original82235650 body in a scoped contact_response namespace while retaining its held-update boundary. Production extraction now contains108 top-level and1 scoped bodies, with32 boundaries. ResolveSceneryContact runs that original response with native-supplied geometry, velocity, physics point, definition radius, time interval and original response settings. It returns cached-point and object-flag changes and calls the supplied velocity setter at the original submission point. The contact selector remains original; no replacement normal or response coefficients are fabricated.

This API requires an unparented scenery/crate root. Parent handling is not claimed complete. Native settings extraction, root-precondition establishment, returned flag application, full world callback construction and lifecycle/controller wiring remain open. Special non-scenery collection flags are rejected instead of approximated. Private response scratch and stack are separate from the suspended held update. Contact-selector reentry during response callbacks is rejected.

Source work only. No build, test, launch or deployment. The user gate remains: complete required scenery RE AND implementation before testing. Deployed overlap, detachment and camera-clearance defects remain open.


### Original soft-ceiling coefficients and native response adapter - 2026-11-12

Identified global8405D340 +328 as the matg SoftCeilings block pointer: Gen4 Globals places its tag block at0x144 (pointer0x148). Source82235650 selects offsets16/20/24 for non-bipeds, including scenery6 and crate11. Schema names these VehicleSpringConstant, VehicleNormalDamping and VehicleTangentDamping; the names do not restrict the original consumer to vehicles. This is the soft-ceiling response path, not a replacement for the entire Havok collision system.

Added extract_contact_settings.py, a bounded source-cache reader with no game execution. Retail Ravine matg index5 atBD922814 points to one28-byte record atBD7A7A54. Original values:20,4,1; complete record SHA25623864e6ed506e94f604825b25faf59b2cb3b67336a12efe86c9e88411b3a5864. Compact original bytes and field provenance are retained in isolated/contact-settings.bin and .json. No guessed coefficients or gameplay timing changes.

ResolveNativeSceneryContact now constructs the world for the original response: native definition radius at tag4, original interval at time8, scenery6/crate10 ->H4 types6/11, suppression at object276 bit2, and native object172 bit19 <->H4 object256 bit20. It calls original native820F29C8 for velocity submission with angular output null, preserving its native body/wake/notification path. It commits only the mapped contact bit, retaining other native flags, and preserves cached-point updates even when the original returns false. Native contact collection now returns the shared bridge ContactCollection type.

The adapter requires an unparented scenery root and rejects unsupported parent state. Caller lifecycle still must establish that precondition. It is not yet hooked into the live held update; monitor-follow, controller submission and lifecycle integration remain unfinished. Source inspection and data extraction only: no build, test, launch or deployment.


### Original held-body controller implemented in production bridge - 2026-11-12

Re-read original82452930 and8249B418. Scenery bypasses the biped orientation-special-case, resolves the signed selected-body index, and only calls8249B418 for an in-range selection.8249B418 builds the target and gains using its passed controller parameter, calls original82C023E8 and82C01FB8, then marks owner object flag30. The parameter is not replaced with a host timing value.

Added Bridge::ControlBody and ControlledBody world snapshots/callbacks. Production extraction now includes115 unchanged original bodies and34 boundaries. Original8249B418, quaternion/target helpers, gain constructor and82C01FB8 execute unchanged. Only82C01FB8 is permitted to perform indirect calls, resolved through a strict body-receiver/linear-or-angular setter dispatch. Source body text is not rewritten. The macro override follows the original header so the platform macro cannot replace the boundary.

Original relocation and activation calls invoke supplied native callbacks at their original points. Original motion setter dispatch also updates the private snapshot so later reads see the same effects; relocation updates private position/orientation. Input preserves all four vector lanes, the original body411 deactivation class, incoming velocities, quaternion and position. The returned original owner flag is available for explicit native mapping. No H3 controller substitution, artificial wake policy or unconditional teleport was introduced.

This implements the original calculation/submission algorithm but does not yet provide the complete native adapter: native deactivation-class representation, virtual setter/relocation/activation mappings, owner-flag mapping and selected-body lifecycle integration remain required. Existing historical fixture results are not validation of this new bridge. Source extraction and edits only; no builds/tests/launches/deployment.


### Native body-controller callbacks mapped - 2026-11-12

Added NativeControlledBody for scenery6/crate10 with explicit selected native body index. It snapshots four-lane body position224, quaternion288, linear motion384 and angular motion400, retaining body identity for every callback. Original H382651968 handles activation eligibility and wake setup; original8265FD48 handles relocation through motion virtual52 followed by8265FB88. These wrappers are called rather than replacing their effects with direct body writes.

Re-read all virtual calls in native82629000: native linear setter slot60, angular slot64, receiver body160. H4 uses64/68, receiver body224. The adapter resolves the actual native motion vtable through the existing function dispatcher; it does not assume every body uses82662340/82662350. Scratch vector arguments remain process-local guest-stack data. Source review corrected the initial slot mapping before any execution.

Renamed the bridge snapshot byte from deactivationClass to responseThresholdCode: the former semantic name was not established. Original H482CD3888 exports body410 and411 via the encoded-float table to construction-description float172 and176 respectively. The controller consumes body411. A native equivalent or source-backed source-class policy is still required; NativeControlledBody requires an explicit code and supplies no guessed default. Selected-body routing, owner-flag/notification mapping and full lifecycle remain unfinished.

No builds/tests/launches/deployment. New adapters are not yet called by the live hooks; the deployed manipulation defects remain open.


### Controller limit constructor correspondence and selected-body routing - 2026-11-12

Located original H4 motion constructor82CD3140 (file211): incoming f2/f3 are retained at caller-stack196/204 and encoded with82C969B0 into motion186/187. Original H3 counterpart8265F4F0 (file60) retains f2/f3 in f31/f30, then stores them to motion180/184. With native motion at body160, the f3 value is body344. With H4 motion at body224, its encoded form is body411. Fixed-motion branches replace f2/f3 using their original engine constants before these writes; using the live native field preserves that native selection.

Removed the unresolved externally supplied response-threshold byte. NativeControlledBody now reads body344; ControlBody executes unchanged original82C969B0 to encode it into private body411 before original8249B418 runs. Original encoded-table rounding is retained instead of a host conversion or guessed default. Production extraction now contains116 unchanged bodies and34 boundaries. No native body field is changed by this projection.

Added SubmitNativeSceneryTarget connecting the native snapshot/callback adapter to the original controller. It follows82452930 scenery routing: no physics instance or out-of-range signed selected index ->no submission; otherwise use exactly the selected body. It does not substitute body0, iterate all bodies, or directly set the object pose. Returned original owner flag30 remains exposed for explicit native notification mapping; live hooks remain unwired until that and the complete lifecycle are ready.

Source inspection/extraction/implementation only. No builds, tests, launches or deployment.


### Controller owner flag consumer traced - 2026-11-12

Original8249B418 sets object256 bit30. Located another writer822036D8 and a concrete reader82939248 (file225). The reader resolves the root parent, requires a physics instance with instance16 bit3, then tests object256 bit30. On that branch it reads original linear/angular velocity82260CF0, negates the original time interval, constructs a reverse angular transform and translated position, and composes these with the object transform before82939080. This is evidence of a transform back-projection path, not grounds to label the bit as a generic network/update notification. Native equivalent and reset lifetime still require tracing; do not blindly map it to native bit29 based on neighboring field shifts.

H3 motion-query callers examined so far do not establish an equivalent reader. Therefore SubmitNativeSceneryTarget continues returning the original flags explicitly, with live wiring incomplete. This avoids silently treating an unknown flag as safely ignorable.

Added controlled-body reentry rejection to the other bridge query/edit APIs: native controller callbacks must not overwrite the private world while the original controller is suspended. Existing entry guards already reject an active body controller in ControlBody itself. Source-only changes and inspection; no build/test/launch/deployment.


### Held reference-point and geometry service boundaries clarified - 2026-11-12

Read complete original822410D0 (file44). It is not unconditionally the ordinary object origin: object304 must be valid, object308 bit0 enabled, and8281F450 must succeed before its alternate point is accepted. With a parent36, it transforms that point through the parent node selected by child57 and parent pose offset446. Otherwise it falls back to8225EA20. Therefore NativeObjectOrigin alone is not a complete implementation of HeldUpdateWorld.objectReferencePoint. Native equivalence remains required; no fallback was silently installed.

Read complete82451BA8 (file182), used by8244A8D8 to decide whether to refresh its body0 pose cache. It queries8293A3B0 object position, calls82415970 with the original global mask and two exclusions=-1, requires821EF090, iterates geometry through824F92C8/824F93C0, transforms every enumerated vertex using its52-byte matrix, and applies82415970 again. It does not simply ask whether the object has a collider or is touching something. The current bool callback remains unwired until this geometry/location behavior is mapped. Original held update preserves the every-five-ticks body0 refresh condition.

Continued native search for82939248 counterpart: the examined H3 motion-query callers do not establish the flag30 back-projection equivalent. No guessed native flag assignment was added. These concrete service semantics constrain the remaining native world adapter; calling ordinary origin or returning a constant geometry result would violate the original sequence. Source inspection only; no builds/tests/launches/deployment.


### Alternate reference-point provider and state gate - 2026-11-12

Traced8281F450 (file270): it calls828211D8, requires returned-record96 bit4, and adds record68/72/76 to original object100/104/108. This is an offset from the ordinary local origin, not an unrelated camera position. The enclosing822410D0 applies the parent-node transform when needed. Native820A9E58 (file44) directly supplies ordinary object84/88/92 and transforms through parent16, child node20 and parent transform offset316. That establishes the ordinary fallback correspondence with H48225EA20.

Traced828211D8 (file120): the alternate record is only available when8230DE48 returns4 or5, object304 is valid, and the signed block count at object488 is positive; the record is object plus offset490.8230DE48 (file90) reads TLS48, requires its byte0 or byte1 to be enabled, and returns its field28; otherwise0. This narrows the integration question to the session-state mapping and alternate record, rather than inventing an offset for every scenery object. H3 LocalForge currently checks game+14==1, but that check alone has not been proved equivalent to H4 TLS48 field28 and is not used to waive the alternate path.

Source investigation only. Existing native ordinary-origin adapter is correct for the ordinary fallback, but full reference-point integration remains open pending the state mapping. No builds/tests/launches/deployment.


### Local simulation reference-point adapter resolved - 2026-11-12

Located original H4 setter82372328 (file101): it writes TLS48 field28 and logs its value through the original game_simulation string table. Read the executable table referenced by the setter:0 none,1 local,2 sync-client,3 sync-server,4 dist-client,5 dist-server. H3 image contains the matching table at8276B5B0 with the same six names/order. H3 local Forge gate explicitly requires game20 byte==1. Thus the supported local path cannot take828211D8's simulation4/5 alternate-position branch.

Added NativeHeldReferencePoint with an explicit LocalForge simulation gate. It delegates to original native820A9E58, the mapped counterpart of H48225EA20, preserving parent-node transformation. It rejects a nonlocal session rather than silently treating distributed simulation as local. This resolves the reference-point query for the existing authorized local Forge integration without importing H4 networking behavior. General distributed alternate-state parity is not claimed.

Source image/code reads and implementation only; no build/test/launch/deployment. Native world construction and the rest of the held lifecycle remain unwired.


### Native collision-vertex stage mapped and implemented (2026-11-12; source only)

- H4 821EF090 corresponds to H3 820AF448 (generated file108): object definition64 -> model collision28; returns datum/model/collision/selected-permutation/node-pose pointers at descriptor0/4/8/12/16. The original native reader handles object318/320 permutation storage and object316 node transforms. No raw all-permutations walk is substituted.
- H4 824F92C8 corresponds to H3 820AF6D0 (file0): native model regions160/164, 20-byte regions, 8-byte permutations and collision-choice byte5. H3 supports16 choices and iterator state20; H4 supports32 and state36. Native defaults and authored-region mapping remain inside the original function.
- H3 iterator820AF7B0 (file57) maps to H4 824F93C0. Native regions32/36, 16-byte region, 40-byte permutation, 100-byte BSP. It returns packed region/permutation/BSP/node at20 and geometry pointer24. Node is the low byte. The local stock schema CollisionGeometry.cs confirms eight12-byte blocks, vertex count84/pointer88 and16-byte vertices.
- Added NativeCollisionVerticesPass in advanced_forge.cpp using the three original H3 readers. A reserved guest frame keeps callback frames below the iterator. Missing collision model returns false; empty geometry remains accepted, matching the original vertex stage. Failure skips remaining vertices of that BSP but continues later BSPs, as in82451BA8.
- H4 transforms accumulate scaled z then y then x with fused adds. Native820BDC38 (file19) uses y then z then x; the adapter spells out H4 ordering rather than assuming bit-identical helper behavior.
- This is only the vertex stage. H4's initial8293A3B0 point source and82415970 world-point query/mask still need native correspondence before constructing the full geometryContainsObject callback. No constant-success callback or overlap substitute was added. Live wiring remains incomplete. No builds, tests, launches or deployments were run; implementation is unverified.


### Initial geometry point and native point-query candidate (2026-11-12; source only)

Read complete H4 8293A3B0 (file288): its starting point is82260B58 (physics-center service), not8225EA20 (ordinary origin). When object304 is valid and308 bit0 set,822CFA08(file77) transforms that point by inverse ordinary transform and then corrected transform.822A3000(file30) obtains the ordinary pose through829403C0, with parent-node context, and the corrected pose through829405E0(file95).829405E0 consumes82937AD0(file21), building a quaternion correction and adding the translation correction while retaining original translation.82937AD0 calls8281F608 and828211D8. It dereferences the latter's result without a local null guard in the enabled branch; do not assume the earlier reference-point local fallback is sufficient to waive this entire correction. Its enable-state writers still need correspondence.

Located native point-query candidate820AE5C0 (H3 file86). Signature is64-bit mask r3, point r4, excluded datums r5/r6, optional result-type pointer r7. It traverses16 active BSPs, uses82132BE8 then820AB9F0 for point leaf classification, and returns type1 for the no-leaf case. With high-word bit3 it traverses cluster collision instances through8229BC40(file40), and with low-word bit0 it visits object shapes with exclusion checks through8229BDA0. This is stronger correspondence than a ray cast, but not established equivalence to H4 82415970.

Material difference: H4 82569F08(file33), called for the high-word bit3 branch, walks its cluster tree and populates a collision cache via82269660/822A5598; the complete generated body ends with r3=0. H3 8229BC40 actually classifies the point against instance geometry and returns true on a solid leaf. Therefore copying the64-bit H4 mask into820AE5C0 would add behavior not justified by this trace. H4 object-query interaction with the primed cache and the effective mask must be resolved before choosing the production point-query mapping. No direct call or constant-result workaround added. No builds/tests/launches/deployment.


### Effective held-geometry point mask resolved (2026-11-12; implementation, not runtime proof)

Re-read original83292E30(file1) and83292E50(file271): high word4105/0x1009, low word0. In82415970(file94), the low-word0 branch excludes object query8256A198 and its cache consumer entirely. High bit1 is unset, excluding82374870. High bit3 invokes82569F08, whose complete body always returns0 and clears its cache-active byte on exit. With these inputs, the returned boolean is therefore true exactly when at least one active BSP returned no leaf and no active BSP returned a leaf; no active BSP returnsfalse. H4's instance-cache preparation does not contribute a true result on this path.

Native820AE5C0 with zero mask has the same boolean truth conditions: it continues over no-leaf BSPs recordingtrue; the first containing leaf skips the disabled instance/object branches and returnsfalse; no active BSP leavesfalse. This explicitly maps the requested boolean service, not the general query's flags or richer outputs. H3 world records/cache remain native; copying H4's high-bit3 would enable additional H3 instance hits and is wrong here.

Added NativeHeldWorldPointBlocked calling unchanged820AE5C0 with this mapped zero mask, excluded datums-1/-1 and null reason output, using a reserved guest frame and finite point input. It is scoped to82451BA8's initialized mask, not the camera ray or generalcollision API. Do not reuse it for object-enabled masks. It remains unwired while the initial physics-center correction and remaining held-world assembly are resolved. No test/build/launch/deployment occurred.


### Local initial-point correction gate resolved; geometry callback assembled (2026-11-12)

Source scan of308-byte stores identifies the object correction-bit setters82821790(file129) and828218D8(file25). Both call828211D8 first and return without changing object308 bit0 when no record is returned.828211D8(file120), re-read in full, requires simulation4/5, valid object304, positive signed488 and the490 record offset. Creation82933B30(file203) stores zero fromr16 into308; its later r16 reassignment occurs after this store.8293B928 clears308 and8281F770 clears bit0 and record flags. Other identified object308 writers set bits1/2/3/4, not bit0. This closes the previously open enable-state question for the existing local-simulation1 gate; no H4 distributed correction is imported into stock H3 networking.

Added NativeHeldGeometryBlocked as the full local82451BA8 callback: validate local Forge and scenery/crate datum, obtain original native820AFA98 physics center, run the mapped world-point predicate first, returnfalse on failure, then run original H3 selected-permutation collision readers and per-vertex predicates. Missing collision model returnsfalse; the original per-BSP failure ordering is retained. This replaces no current hook yet: HeldUpdateWorld construction/lifecycle integration remains pending. Current live defects remain open; no builds, tests, launch or deployment.


### Desired-view input separated from rotation view (2026-11-12; source implementation)

Re-read complete native820F6658(file39) and H482227810(file59). Native reset copies current unit424 into400/412/448/460; H4 copies current1260 into1212/1248/1284/1296, additionally shifting desired1212 into history1224 and1224 into1236. Original8244A8D8(file194) uses1212..1220 to orient movement, while8244B518 uses1260 for rotation. H4 packet consumer822562A8(file180) updates1212/1216/1220 from packet56/60/64 and1248/1252/1256 separately from68/72/76, reinforcing the distinct roles. Native82338FF8(file14) also reads the400 vector in its unit-orientation calculation.

Added NativeMonitorDesiredView reading native400 with salted-object/unit validation and finite-value rejection, separate from NativeMonitorRotationView at424. No held-world defaults inserted. Native monitor movement flag, movement multiplier/fraction and camera-position services still require mapping before complete HeldUpdateWorld construction. This is unbuilt/untested source only, with live hooks unchanged.


### Held movement boost multiplier mapped to native H3 (2026-11-12; source only)

H4 unit2168 is a boost fraction, not an independent Forge speed setting. Original8294C5A8(file61) updates2168/2172/2176 under definition516 bit28, using definition1432/1436 and1440/1448/1452 timing/recharge controls.8244A8D8 multiplies movement by1+(definition1428-1)*unit2168.

Native820EA138(file60) provides the native fraction in f1 from unit992/996 and definition724/732. Its output is used with definition720 in native82388AA0(file103),82383E50(file112),8238B290(file58) and other movement consumers to form the same1+(peakPower-1)*fraction. Local schema names720/0x2D0 Boost Peak Power. Native timers must not be copied directly into H4 fraction2168.

Added ReadNativeMonitorBoost returning original native820EA138's result and native tag720, with salted-unit/tag validation and finite checks. This preserves native H3 boost lifecycle and game timing while feeding the original H4 scenery movement formula; no H4 boost subsystem or guessed speed constant is introduced. Desired view and boost inputs are now mapped; movement flag, camera-position service and complete live lifecycle remain open. No build, test, launch or deployment.


### Held movement flag mapped through both original packet chains (2026-11-12)

H3821EC0E0(file95) copies action word8 into stack144 (unit packet128+16), later ORs bit16, and sends the packet to820B8608(file51). That consumer stores packet16 into unit392. H4823619F8(file276) copies64-bit action8 into stack112 (packet96+16); its other writes to112 clear bit27 or select bit24, preserving bit0. H4822562A8(file180) stores64-bit packet16 into unit1200, whose bit0 is the field read by8244A8D8. Thus native unit392 bit0 is the processed-action counterpart required by the held update. Added NativeMonitorMovementFlag with salted-unit validation; no new input handling or gameplay flag write.

The native820B8608 read also confirms the desired-view mapping independently of reset: packet40/44/48 -> unit400/404/408; packet52/56/60 ->412/416/420; packet64/68/72 ->448/452/456. This parallels H4's separate desired and secondary vectors. Movement flag, desired view and boost now have explicit source-backed native readers. Camera position, world assembly and lifecycle wiring still remain. No builds/tests/launches/deployment.


### Camera boundary corrected; original pitch curve recovered (2026-11-12)

Re-read824BEAD0(file101),824BE840(file259),8244B758(file146),821D6D90(file93). The HeldUpdateWorld.monitorCameraPosition boundary must not be implemented as a native rendered-camera/eye-position query. It is original H4 held-editor camera construction: physical held point plus editor36-scaled editor56 offset, desired view1212, editor276 history and pitch-dependent vertical offset.824BEAD0 fixes mode0, so its call does not enter824BEB50 prediction.821D6D90 then applies the basis-relative offset. The production bridge should execute these original bodies and consume native physics points/radius rather than keep this high-level native-camera boundary.

A source-only dependency inventory finds seven additional original functions for this mode0 path:824BEAD0,824BE840,8244B758,821D6D90,8229FAD8,822C8040,822E15E0.824BEB50 remains a separate prediction integration dependency for the mode1 monitor-follow path; no zero-output stub is justified.

8244B758's globals256 camera16 field is Camera.PitchToVerticalOffset (Gen4 Globals.cs). Its scale is held object-definition32 BoundingRadius (Gen4 Object.cs), corresponding to native definition4; this is not the runtime bounding sphere radius. Added and ran source-only extract_camera_curve.py against original Ravine matg index5, globalsBD922814, cameraBD7A7290, curveBD7A723C. Retains84 original bytes in isolated/camera-pitch-function.bin and a compact provenance JSON; SHA256879c90d4b91430d71a28f61373ef7304f2d39b990896b9dd665d1c107158555d. Existing original8226CD10 evaluator reads data-reference pointer12. No curve values fabricated or evaluated, and no test/build/game execution. Original-body extraction/bridge data wiring is the next implementation step.


### Original held-camera construction integrated in bridge (2026-11-12)

Replaced the high-level824BEAD0 camera-position boundary with the seven unchanged original bodies listed above; regenerated extraction now contains123 bodies and34 explicit boundaries. HeldUpdateWorld now supplies native objectPhysicsPoint and heldDefinitionRadius, not an externally computed camera position. Original8293A3B0 delegates to that physical-point service during held update; other existing scene-only callers retain their earlier scene projection. Private tag2 provides definition32, and NativeHeldDefinitionRadius reads stock H3 definition4. Full native world construction remains unwired.

Bridge loads the84-byte original pitch function adjacent to Forge configuration and relocates globals256 -> camera16 -> reference12 into private190000/190100. Missing or wrong-size data fails explicitly. Future private-runtime packaging includes this source asset; no packaging/build/deployment was run. Original image pointer833F7EAC resolves82125188, whose data is (0,0,1), so original8244B758 retains the actual up-vector input.

Correction to prior shorthand:822E15E0 is an auxiliary scalar camera-field query, not direction normalization. Its output is descriptor40;824BEAD0 consumes point4, offset16, direction44 and up56 only. The mode0 point calculation therefore does not consume that auxiliary field or copied descriptor184..204. Mode1 prediction824BEB50 explicitly throws until its separate services are implemented; it is not a successful no-op or claimed completed camera-follow path.

Previous goal turn was no progress (gate restatement only). This turn changes production source and extracted original bodies. No builds, tests, launches or deployment; the incomplete native lifecycle and monitor-follow work keeps the user gate closed.


### Next dependency: mode1 camera prediction824BEB50 (static source inspection)

Original file56 requests both linear and angular vectors from82260CF0 (r4 and r5 are non-null). The current held-motion adapter intentionally accepts only linear output and cannot be reused unchanged. With a valid held datum, the function computes speed times the motion query's returned f1; above the original threshold it compares held editor8..16 against8225EA20's object point and limits the linear prediction multiplier to at most1. It applies linear displacement using the caller's original time f29. With an instance and positive body count it additionally obtains object orientation82243068, builds/inverts a basis through8232F960/82264A58, queries the instance point8249B1F8, and rotates its relative point using the original angular vector and time through8232F708/8232F830. This extra displacement is added to the linear prediction. Both motion-query output and f1-return semantics, orientation service and instance point need native mapping before removing the explicit unfinished boundary. No fabricated angular zero, body-center substitution or velocity unit assumption is justified.


### Prediction motion boundary: both outputs and preserved time (2026-11-12)

Read complete82260CF0(file237), root82260C98(file93), linear82260AF8(file239), angular822302F8(file93), eligibility82260E80(file290), and its helpers82260F08(file10)/82260F70(file142). None writes f1; integer save/restore thunks likewise do not. Correction to the prior prediction note: speed is multiplied by the incoming time still in f1, NOT a scalar returned by the velocity query. The bridge must preserve that register.

Added NativeObjectVelocities: one native820AC960 query with separate linear/angular outputs in reserved guest stack storage. Both outputs are checked for finite components; native physics eligibility, root selection, fixed handling and fallback remain original. HeldUpdateWorld now exposes that paired snapshot, and the82260CF0 boundary writes whichever outputs the original caller requests, leaving f1 untouched. Existing linear-only held update still uses its original callback. Mode1 itself remains gated by the unfinished824BEB50 boundary until the remaining services are mapped.

Native820AFBC0(file82), reached by820AFA98(file69), is NOT an interchangeable first-body point for H48249B1F8. Native service accepts a selected index, only uses its authored-body alternative for fixed7, and transforms phmo record96 through body176; its ordinary branch reads body256/260/264. H4 service uses first body, accepts fixed5 OR keyframed4, and reads phmo record56 directly in its alternate branch, otherwise body368/372/376. Those are distinct point semantics; do not plug NativePhysicsPoint into that boundary merely because both return three floats. Corresponding native local-center/model-field mapping remains to be resolved. No test/build/launch/deployment.


### Prediction local-center native projection (2026-11-12)

Native826292C8(file110) rotates body304 by the requested quaternion, adds requested position, subtracts body256, then submits linear velocity through motion160 virtual60. This identifies304 as local center and256 as world center; native clone822623E8(file29) also passes body304 to construction822698A0. H4 clone8249AB98(file114) passes body368 to construction824A39A0 alongside body240 transform. This supports the local-center368 ->304 projection independently of assuming a uniform body offset shift.

The authored alternative in H48249B1F8 is phmo rigid-body record56, which is CenterOffMassOffset in Gen4 PhysicsModel.cs: node/region/permutation/shape8, bounding sphere16, flags2/no-phantom2/motion1/proxy1/size2, inertia scales16, damping8. Native PhysicsModel.cs has no three extra inertia scales; its corresponding CenterOfMassOffset is44. Native CenterOfMass96 is a DIFFERENT field;820AFBC0 uses that transformed world-space alternative and must not be used here.

Added NativePredictionLocalPoint preserving H4's first-body selection and authored-alternative predicate: instance flag bit8, fixed OR keyframed motion, positive binding count, signed binding index not -1. Native instance flags4/owner8, body array32/entry64, binding count16/pointer12, fixed7/keyframed6; phmo block88/92 stride176 and field44. Ordinary branch reads body304. Includes pointer/index/finite checks. No world transform is applied to the authored local point. The helper is source-only and not yet wired to live camera follow. No builds/tests/launches/deployment.


Original mode1 prediction824BEB50 has now replaced the temporary throw boundary. Production extraction is125 unchanged bodies/35 boundaries. Original math, linear cap and angular displacement remain in original source; new boundaries82243068 and8249B1F8 request mapped native orientation and local center.8225EA20 now accepts the held-world context while preserving its existing selection context. Native world callbacks must still be constructed and the real monitor-follow entry wired; no claim that adding an extracted path makes it live. Required orientation/center callbacks fail explicitly if missing. Previous turn made source progress; this turn completes another data mapping and incorporates the original prediction body. User's no-test gate remains closed.


### Native held-update world assembled (2026-11-12)

Added NativeHeldUpdateWorld in advanced_forge.cpp. It requires local Forge and an unparented scenery/crate root, reads the native instance/count, monitor desired view, processed movement flag, boost multiplier/fraction, actual simulation tick/interval, authored definition radius and live variant bounds. It connects native motion, paired velocities, reference/physical/local-center points, orientation, collision containment, explicit indexed body pose and original contact response to HeldUpdateWorld. Native local-holder ownership remains a required caller input from the holder transaction, not an assumption based on monitor index.

Callbacks capture their PPC context by value; each native query uses its own reserved guest frame. The original bridge reference and native memory remain synchronous-call lifetime requirements. No synthetic world values or host timing added. This connects previously separate source adapters but does NOT yet replace the live legacy held path: per-player editor lifecycle, holder transactions, monitor update and owner-notification mapping still require integration. No tests/builds/launches/deployment. Previous turn and this turn both changed implementation source; goal remains active.


### Grab transaction and selection-world integration (2026-11-12)

Read native8227E810(file75) and822800B0(file106), H482450E10(file43),82449ED8(file101),82505DE8(file120). Native8227E810 resolves the variant slot to a live datum, calls822800B0 for holder ownership, computes its legacy distance, then calls8227E770 to transition physics.822800B0 validates no other player holds the slot, preserves native variant/attachment transactions, stores the slot at engine57752 + playerIndex*4, and removes it from the pending-object path82283B90. It cannot be replaced by writing only an H4 held datum. The native datum can also differ from the original slot input; initialization must use the post-transaction resolved object.

H482450E10 orders selection82449ED8, object dequeue8244F5D8, physics selection/transition8244A180/8244A2A0, then placement initialization. Thus the current grab hook needs orchestration around native ownership and physics, not a repeated per-frame reset. Existing spawn-only distance workaround remains until complete replacement is ready.

Important focus clarification:82505DE8(player,false) reads player36, the controlled unit. It does not perform an object focus/raycast query. Added NativeHeldSelectionWorld mapping this to native player40 through TLS96, table68 and stride880, plus mapped physics/origin callbacks and caller-supplied ownership/event sink. The callback reads the current controlled unit and validates its object handle; no fabricated -1 focus. This adapter is not yet connected to live per-player state or grab/release hooks. No tests/builds/launches/deployment.


### Persistent native editor storage and original selection/reset (2026-11-12)

Read original constructor82449DD8(file129) and callers8244C210(file217)/8244C440(file99): both maintain16 independent336-byte editors. Constructor writes held/target sentinels, default distance, offsets/vectors, rotation mode, scaling, visibility settings and event. It is not equivalent to zeroing storage.

Added16 NativeEditorSlot records keyed by full player datum, each retaining original HeldEditorState plus mapped manipulation input. NativeEditor allocates zero backing then executes original InitializeHeldEditorState; it never treats the backing bytes as initialized editor state. Per-frame callers reuse the same state. World identity changes/backward tick reset discard this host-only storage alongside existing map-scoped state. A new salted player identity initializes fresh state. No H4 records are overlaid on H3 memory or persisted into native saved variants.

SelectNativeHeldEditor builds the mapped selection world and executes original82449ED8. Passing -1 performs original release/reset and clears the separate input state, while preserving original preferences via the original routine. The wrapper is a transaction stage, not a frame reset. Live hooks still need to call it at the proven ownership/physics boundaries; old behavior has not been removed prematurely. No tests/builds/launches/deployment.


### Grab initialization prerequisite: selection ray44 (2026-11-12)

Source investigation changes the next integration step. Original8244C740(file133) produces editor44/48/52: after82417550 it copies the hit point from stack168/172/176; on miss it stores the computed ray endpoint.82449DD8 does not initialize these fields, and82449ED8 does not supply them. InitializeGrabPlacement consumes44 when projecting the grab distance. Therefore wiring a newly constructed zero-backed editor directly into grab would silently use an invalid reference point. Required ordering is selection-ray update before the original grab-distance stage, including first grab and subsequent re-grab. No assumption that physical center or camera point is equivalent is allowed.

Native ray counterpart82281268(file43) writes engine57880 +12*playerIndex (hit point or endpoint), normal58072 and view58264. Native ray uses current unit424 and its current held distance, origin820AA480, mask0x001000090000099D, excludes held datum plus variant-associated datum, then820AD3E0. H4 uses current unit1260, origin822B79A0, mask0x000000090000179F, a minimum range optionally sourced from a globals-linked tag, and82417550 with an exclusion list built by82268800 (up to64 entries with definition1364 predicate). Its hit-category4 controls returned object identity. These differences mean native cached ray cannot simply be declared equivalent.

Next required RE/integration is selection-ray world mapping and original ray state write, before completing grab hooks. Monitor-follow is separate from this producer. Existing held/camera code remains unwired; no testing/build/launch/deployment. Previous turn was implementation progress; this turn finds a concrete uninitialized-state hazard and identifies the exact producer and native correspondence rather than running the incomplete path.


### Selection-ray range and biped exclusions resolved (2026-11-12)

Original8244C740 reads ForgeGlobals.ObjectGrabRange at forg68, with positive threshold from original image82128A54 (approximately0.0001) and fallback82128A10 (5.0). Existing extracted88-byte retail forge-globals.bin contains7.5 at68. The ray length is max(editor28,ObjectGrabRange) after the original threshold fallback. No new tuning value is needed; this field already ships in the private configuration.

Its exclusion iterator82268800(file63) uses type mask1, required header flags0 and native object-header order, collecting at most64 entries. The field1364 predicate is the Unit.Seats block count (pointer1368 is independently consumed by822B79A0 for seat lookup); only bipeds with fewer than one seat are appended. This is not an arbitrary scenery filter or all-unit exclusion. H3's Unit.Seats count/pointer counterpart is672/676, independently used by native820AA480(file27). Type0 remains biped. This resolves exclusion meaning; native header iteration and ray mask/category correspondence still need integration.

Origin services822B79A0/820AA480 share the ordinary eye/marker, attachment and seat paths, but H4 adds822B7848 animation-controller offset, an external-view player56 path and final8222C5C8 correction. Full code was inspected; it is premature to assert blanket equality for all monitor states. Native scenery editing keeps stock H3 player/monitor systems by user requirement, so the native unit-origin service is the integration candidate, with the H4-specific branches accounted for explicitly before wiring. Selection ray remains unfinished; no tests/builds/launches/deployment.


### Native selection exclusions implemented (2026-11-12)

Native82332608(file91) confirms data-array56 index limit,36 element stride,68 headers, nonzero signed salt0, native type byte3 and object pointer12. H482268800 uses ascending header order, nonzero salt and type-mask1 with required flags0 for this caller. Added NativeSelectionRayExclusions: walks native headers in that order, selects type0, reads mapped Seats672 and appends signed-count<1 datums until64. Validates table ranges, stride, tag pointers and handles; no synthetic exclusion count or scenery-only filtering. This helper is still awaiting the original selection-ray bridge and mapped collision-query service.

Re-read native820AD3E0/file104 and82417550/file265 plus filter construction82416438/file124. The H3 query has distinct BSP preprocessing, object traversal and post-hit correction; H4 uses physics-world batch traversal plus collector merge. H4 request flags cannot be copied wholesale as native flags. Existing source evidence is insufficient to declare complete mask correspondence; this remains the next collision mapping obligation. No tests/builds/launches/deployment.


### Original selection-ray upstream layer gate resolved (2026-11-12)

Source inspection, no execution:8236D730(file64) dispatches hcfd (0x68636664), repairs tag+16 via824AD928, then installs ray-interface vtable82000F00 at group-filter+20. Cached pointers are zero; reading the cache alone does not identify the runtime implementation. Image slot82000F04 is82286F38(file213), a forwarding wrapper to82D817C0(file122), which reads ray-input36 and shape28 and calls82D813F8(file161).

8244C740 writes request0=26.82417550(file265) copies request0 to stack116, i.e. ray-input80+36, before824A9D68.82D813F8 uses lookup[ray_info&31] & (1<<(shape_info&31)) unless both inputs have matching nonzero upper16 system groups. Ray26 has zero upper16, so that exceptional branch cannot apply here. The table lives at group-filter52, tag68. Ravine hcfd index17059/pointerBDFAD5FC row26 isCBFEFFFB: rejects layers2,16,26,28,29 (schema labels EnvironmentOnly, Decal, ZeroExtent, EnvironmentInvisibleWall, EnvironmentPlayCollision). These are collision layers, NOT object types or the lowword request mask.

Added tools/h4-forge/extract_selection_filter.py to reproduce bounded cache/image extraction into work/h4-forge-research/isolated/selection-filter.json (one compact overwritten report). The original virtual wrapper is resolved; the later82416640 metadata/exclusion gates, collector merging and H3 query category mapping still require integration. This finding rules out treating the H4 request bitmask alone as the entire selection filter. No build, test, launch or deployment performed.


### Original collision predicate available in production bridge (2026-11-12)

Added Bridge::CollisionGroupAllows(queryInfo,shapeInfo,lookup), executing unchanged82D813F8. Caller supplies the original32-word lookup table and physics filter-info words; this API deliberately does not reinterpret object types as collision layers. Preserves original same-system-group branching as well as the ordinary layer lookup. Uses private scratch191000/191100 and a separate PPC context; the leaf has no calls, TLS accesses or stack reads, so native callbacks can use it without replacing the enclosing held-update context. Extraction now includes126 unchanged bodies and35 world boundaries. Source generation only; unbuilt/untested and not yet connected to the native selection query.

Further query trace: H3820AEC70(file7) initially gates type from candidate+4 against native mask lowword shifted1, then820AED80 surface flags and820AEE78 bounds before820AEF50 detailed query. H482416DF8(file206) sorts collected candidates through82223660, terminates candidates at fraction>=best (initial1), invokes82416120 for the ordinary detailed path and82415178 before physical-body traversal. H482416AD0(file286) merges static geometry only if its fraction is strictly smaller than the already selected result; equal-distance geometry does not overwrite the earlier hit. Native correspondence must preserve that ordering. Next trace target is82415178 versus native820AF170, plus82416120 detailed-query mapping. Original full selection-ray wrapper still needs integration before grab initialization.


### Selection object-mask and detailed-query correspondence (2026-11-12)

Read82415178(file185),82416120(file51),82415E80(file58),82282860(file215),82202870(file169),824150C8(file263) and native820AF170(file103)/820AEF50(file44). Both per-object predicates use lowword bit(type+1). H4 selection179F enables types0,1,2,3,6,7,8,9,11: biped, vehicle, weapon, equipment, scenery, machine, control, dispenser, crate (Gen4 Pathfinding.ObjectTypeEnum). Native old Forge99D enables1,2,3,6,7,10. Translating shared H4 categories to H3 yields lowword0B9F, preserving generic bit0 and mapping crate11->10; H4 dispenser9 has no native category. Thus the old native selection mask is NOT a faithful replacement: it omits bipeds with seats and controls. This is query-category mapping only, not authorization to import H4 gameplay. No native query is wired yet.

Detailed paths correspond82415E80 ->820AEF50: predicate82415178 ->820AF170; bounds821F7E48 ->820AEE78 (center H4 object80 vs H3 object48, radius92 vs60); collision iterator821EF090 ->820AF448; ray iterator824F9628 ->820AF5D8. Both detailed results accept only strictly smaller fractions, return category4 and record object identity (H4 detailed64; native60). H4 batch final object identity is40, a distinct result layout.82416120 derives surface-mask bits from request highword12..17, defaulting bits0/1 on when neither is set; this differs from native820ADFE0's highword11..16 conversion. Do not copy either entire64-bit flags or result records.

H4 detailed guard82282860 walks all ancestors for header flags0x20/0x400 and object flags bit0.82202870 walks all ancestors for object flags bit41.82415178 separately checks direct exclusions, ancestors with seat/attachment exceptions, direct bit41, and category flags. Native820AF170 supports only three excluded datums; H4 accepts64.824150C8's seat exception uses parent36, seat44, definitionSeats1368 with stride364 and short74; native counterpart uses parent16, seat582, definitionSeats676 with stride228 and short66. A general native query call with three exclusions cannot silently replace the full H4 list. Remaining integration obligations: map native visibility/header flags and the H4-specific bit41 gate explicitly, provide full exclusion filtering, then query/merge and original ray-state writes before grab. No tests, builds, launches or deployment.


### Native full-length selection exclusions implemented (2026-11-12)

Added thread-local SelectionRayExclusionScope (maximum64, rejects nesting, RAII cleanup) and a narrow820AF170 hook. Outside a scoped query, it calls the original predicate once. Within scope it preserves the ordinary result, then evaluates additional exclusions in groups of three through the same unchanged native predicate. Reuses each original call's entry arguments, retains the first call's returned context, and changes only the boolean result when another group rejects. The native predicate has no world writes: it checks direct IDs, ancestors, seat exception, type and flags. Therefore conjunction extends native exclusion capacity without inventing ancestry behavior. No scope is created by the live caller yet; integration remains incomplete and untested.

Scope decision from the user's hard stock-H3 requirement: collision eligibility of native objects stays with H3's existing world services, including its native ancestry/seat handling. Do not copy H4 runtime flag41 into an arbitrary H3 bit or import H4 gameplay state. H4 source82939DC8(file131) sets bit41, clears collision-model-active bit7 and calls82937610; clearing bit41 restores bit7 from the object's model collision reference before the same update. Thus this is collision suppression, not a new Forge magnet preference. Its concrete native eligibility remains delegated to the stock H3 collision service, not claimed bit-for-bit equivalent. Source callers82A11880,82A2E2B8/82A2E328 and82A11988 plus creation paths8229F458/82280808 are recorded for H4 inventory. This does not finish H4 query layer/world merging or ray-before-grab state integration. No tests/builds/launches/deployment.


### Native selection query adapter implemented (2026-11-12)

Added NativeSelectionRay around original820AD3E0 with explicit native64-bit mask and mode (no unproven H4-to-H3 flag cast/default). Copies origin and displacement into a private caller frame, passes an independent96-byte H3 result buffer, supplies the64-entry exclusion scope, and returns only category/fraction/point/native object identity. Native category4 datum comes from result60, not H4 result40. Finite inputs/results, exclusion handles and returned object handle are checked. Native routine allocates17504 bytes; adapter inputs begin at caller+128 above the callee frame and beyond outgoing parameters. No writes to native object flags or saves. Existing H3 world query owns broad-phase geometry, visibility and native post-hit behavior; adapter does not claim H4 batch-world equivalence.

Added NativeSelectionOrigin using original820AA480 (the H3 Forge82281268 eye/marker/seat service), separate from physics-center/origin helpers. This keeps stock H3 player/monitor behavior at the822B79A0 world boundary, as required by the user's scope. Original H4 ray construction, radius/range selection, editor44 hit/endpoint writes and lifecycle ordering are still pending bridge wiring. Native layer/filter treatment must be explicit at that caller. Neither new helper is called by live Forge yet. No builds, tests, launches or deployment.


### Original selection-ray bridge and native world assembly (2026-11-12)

Added UpdateSelectionRay executing unchanged8244C740. It projects private monitor/held handles, the original held-distance state and ordered seatless-biped exclusions, preserves original forg68 range fallback, endpoint arithmetic, hit-vs-miss branching and editor44/48/52 writes, then restores the native held datum. State commits only after the original call returns. Added explicit origin/iterator/query boundaries, private/native handle translation and ray reentrancy guards. Source extraction now130 unchanged bodies/39 boundaries. No execution of extracted code occurred.

The temporary variant read823C5C28 is deliberately discarded ONLY within this ray scope:8244C740 initializes its76-byte output, never reads any field or the return value, and subsequently uses the same temporary as the collision result. Inspected823C5C28,823C1D00 and8230DE48: they copy/clear that output and read mode/variant state; no live mutation is omitted. This boundary must not be reused where variant data is consumed. Native held slot24 maps to the source-read short62.

Added NativeSelectionRayWorld assembling native eye origin, native rotation view424, original-rule exclusion list and held variant slot. It validates the exact H4 request layer26/flags000000090000179F, converts endpoint to displacement, and invokes the native query with stock H3 Forge world/surface highword00100009 plus mapped shared-category lowword0B9F, mode0. This is an explicit native-world compatibility boundary, NOT a claim that H4 hcfd groups equal H3 geometry filters: native H3 world eligibility and post-hit behavior remain stock. H4 private layer predicate remains available for original-source parity work; no H4 group numbers are assigned to native bodies. The original ray construction/state stage is retained, while world geometry services stay H3 as scoped by the user.

TODO now records the new ray stage as source-only and still awaiting live lifecycle wiring. Original monitor-follow, lifecycle sequencing, controller notification and remaining implementation work continue to block testing. No builds, tests, launches or deployment.


### Monitor-follow obstruction configuration recovered (2026-11-12)

Inspected full8244AF48(file201): mode1 camera prediction; candidate-point containment82415970; collision/obstruction smoothing824F5CF0; relative-reference/contact-plane correction; original monitor controller submission82452930; local view update823FC348; editor32 distance and editor276 pitch-history updates. Caller8244D0E0(file196) orders82452738,8244A8D8,8244AF48. Monitor-follow is not merely copying the held target into a camera position.

824F5CF0(file13) updates the three-float editor228 state using824F5F78(file239) obstruction bounds, timestep and source constants.824F5F78 casts a center ray plus six surrounding rays through824F5E28 and handles retained obstruction geometry; no single-ray substitute is justified.8244AF48 copies six words from runtime8407F34C (global camera base8407F2B0+156). Those executable-image bytes are zero-filled, not usable authored defaults.

Found original824BFE90(file266) initialization: reads globals256 camera block, source camera36; maintains a180-byte baseline and conditionally imports fields into8407F2B0 when not overridden. Extended extract_camera_curve.py to retain the full216-byte camera block from Ravine, SHA2566d3e00c453092e35076caf8584c166110165100c14b9134d0aba837f27e4d62d. Its final24 bytes at192 are obstruction settings (0,0.1745329201221466,4,1,10,0). Bridge now loads this record, relocates its existing pitch-function reference, and invokes unchanged824BFE90 after globals setup. Added private runtime file discovery/CMake copy for camera-settings.bin. Source extraction131 unchanged bodies/39 boundaries.

Only source/data extraction ran. Original monitor-follow root and native obstruction/view/submission boundaries still require implementation and live sequencing. The new initialization has not been built or executed. No tests/builds/launches/deployment.


### Original obstruction algorithm and query initialization implemented (2026-11-12)

Added UpdateMonitorObstruction executing original824F5CF0, with its full824F5F78/824F5E28 closure: original center/six-ray sampling, cached obstruction point, fraction constraints and three-float smoothing/timer state. The method is conditional on the enclosing follow containment result, updates only editor228..263 after success, and supplies held/monitor exclusions as8244AF48 does. A separate obstruction query context reuses the explicit collision boundary; it preserves native identities and now returns the hit fraction as well as point/category/datum. Selection query translation remains scoped separately. No hand-authored smoothing or single-ray replacement.

Discovered another necessary startup dependency: image845548B8 obstruction flags and its source845548B0 are both initially zero. Original83292E30 writes highword4105(1009),lowword0 to845548B0;83292E50 copies it to845548B8. Both unchanged constructors are now extracted and called after camera-settings initialization. Original surrounding-ray angle constants83400920/24 are present in the image:0.5 and0.8660253882408142. No synthesized values substituted.

NativeMonitorObstructionQuery accepts only original layer27/flags0000100900000000, converts endpoint to displacement and maps the surface selector H4 high bit12 to native bit11 (82416120 versus820ADFE0), retaining native H3 world geometry services. The lowword stays0: this request is not the selection object's category mask. The native callback returns native fraction for original824F5E28 to consume. Native H3 physics groups remain native rather than copying the H4 layer27 bit number.

Extraction143 unchanged bodies/39 boundaries. Original enclosing monitor-follow containment, contact-plane handling, controller/view submission and live lifecycle wiring remain open. Source only; no builds, tests, launches or deployment.


### Monitor-follow containment boundary resolved (2026-11-12)

Re-read full82415970 (H4 file94) and820AE5C0 (H3 file86). Follow8244AF48 uses the same initialized0000100900000000 mask and boolean-only result as the previously mapped placement query. Reuse NativeHeldWorldPointBlocked for this boundary: no new ray mask or instance-overlap approximation. H4 tracks whether any active BSP contains the point; with no containing leaf and at least one queried BSP it returns true. Native zero-mask query provides the same boolean while avoiding the native instance branch that copying H4 highword bit3 would enable. H4 result details are not consumed by follow; this mapping is only for its boolean. Full follow orchestration remains pending.

User reiterated: do not test while RE or implementation remains unfinished. No build, test, launch or deployment performed.


### Original monitor-view conversion implemented (2026-11-12)

Inspected full823FC348 (file104). It constructs a basis from the supplied forward/up and their cross product, calls8229E900 then82331BC8 using the original image constant, stores three angles at local-view record+288+20/24/28, wraps negative first angle with the original image constant, and calls82400D48 only after those writes. Local records are480 bytes at TLS100.

Added ConvertMonitorView with unchanged823FC348 and its existing math closure. A private local slot captures the three angles at the exact82400D48 notification boundary. TLS100 is restored on success or exception, nonfinite inputs/results and unexpected/repeated notification are rejected, and other bridge entries reject reentry during this stage. This is the original conversion stage only: native H3 local-view storage/notification mapping and the enclosing follow orchestration are not implemented by this API. No native view writes or runtime fix claims. Extraction144 unchanged bodies/40 boundaries.

Only source extraction ran; no build, test, launch or deployment. User gate remains RE plus implementation complete before testing.


### Native local monitor-view boundary implemented (2026-11-12)

H4 notification82400D48 (file241) copies248 bytes from matching current control records to four retained records; this is not a renderer callback. Native counterpart82227800 (file104) copies104 bytes from the matching current record to four retained108-byte records at TLS120+960. Current native records have stride236, controlled datum at+16. Its native facing caller820B04B0 (file100) uses820D18B8 (file3) to produce yaw/pitch from forward, wraps negative yaw and then calls82227800. H4's source uses three quaternion-derived angles; H3's native action/view format has a two-angle facing field at current record+28. Do not transplant H4 record size or third angle.

Added SubmitNativeMonitorView calling original820B04B0 with a process-local guest direction vector. It validates local Forge, local index, current controlled datum, live object and finite nonzero direction before any native write. This deliberately retains stock H3 player controls as required by the user; scenery rotation is not restricted by the monitor view representation. The enclosing original follow root must supply its corrected facing vector and the mapped local index. Adapter remains unwired pending that orchestration, monitor-controller routing and contact-plane mapping. No builds/tests/launches/deployment.


### Monitor contact provenance and active-biped submission branch (2026-11-12)

H4 follow8244AF48 reads player152 normal under object256 bit20. Its writer8297F658(file263) calls82235650 with player140 cached point and player152 normal, resolving player from unit1180. Native820F57A8(file100) resolves player from unit380 and calls820FFBE0 with player64 cached point only: no matching normal-output argument. A native player offset for the H4 normal cannot be inferred. The full H4 monitor response needs an explicit retained-normal boundary; do not substitute another native player vector or silently disable the correction.

Full82452930(file2) contains a special type0 branch when any physics body byte56 bit0 is active. It copies target, invokes8257FB98(file108) on its basis, writes the flattened forward into the object while retaining its current up, notifies822AAB18, replaces the controller target basis with nine original identity floats, then routes through signed selected body24 and8249B418. Scenery-only routing is not valid for the monitor.

Added PrepareActiveBipedTarget: unchanged8257FB98 and dependency closure produce the facing output; controller target retains scale/translation and receives the source identity basis at82125148. Caller must establish original active-body eligibility, retain current up, perform mapped orientation notification, then submit the selected body. These native obligations remain open, and this API is not wired live. Extraction146 bodies/40 boundaries. No builds/tests/launches/deployment.


### Native monitor orientation notification mapped (2026-11-12)

Compared fullH4822AAB18(file208) with native820F6550(file58): both compare old/new forward components, construct their relative rotation, and rotate two cached node arrays. H4 counts/offsets428..434 map to native306..312. Native820F64B8(file50) confirms forward96 and calls this notification; native820F6A70(file8) also demonstrates write-before-notify ordering used by H4's active-biped controller branch.

Added SubmitNativeMonitorOrientation for local unparented type0 monitors: finite old/new forward and retained up, guest-stack validation before writes, old forward saved, new forward96 written, current up108 retained, original820F6550 invoked with old/new vectors. It does not use820F64B8 because that wrapper renormalizes and notifies before writing, whereas the requested original82452930 path has already prepared the vector and writes first. Native active-body eligibility and monitor controller routing remain unresolved; helper is not live. No build/test/launch/deployment.


### Native monitor body routing implemented (2026-11-12)

Found original native entry constructor8226AE28(file82), compared with H4824A4D20(file133). H3 includes an extra12-byte array ahead of the shared fields: body pointer64/flags68 versus H4 pointer52/flags56; both assign flag bit0 from seventh argument. H3 additionally assigns bits1/2 from arguments8/9; these must not enter the H4 bit0 predicate. This resolves the upright-target branch without guessing flag offsets from entry size alone.

Added SubmitNativeMonitorTarget for local unparented type0 monitors. It resolves the native instance, scans all body entries for bit0, calls original H4 active-biped target preparation and native orientation notification when required, then validates the signed selected index and sends that body's native callbacks through the original H4 controller. Orientation occurs before selected-index validation, matching82452930 even when no body target is submitted. NativeControlledBody now allows type0 only through an explicit monitorTarget argument; existing scenery callers retain their type6/type10 gate. No direct pose teleport or all-body controller loop.

Returned owner flags still require mapped notification handling. Monitor contact-normal retention, complete original follow orchestration and live lifecycle remain unfinished. Source only, no builds/tests/launches/deployment.


### Controller flag lifetime and native attachment counterpart (2026-11-12)

Located native823317C0(file94), the structural counterpart of H482939248(file225): parent16 vs36, attachment node20 vs57, node-array offset316 vs446, parent visibility query8210C630 vs822CE090, child transform823316D8 vs82939080, rebuild82330B20 vs82388A08 and velocity820AC960/820F29C8 vs82260CF0/822D1158. Native follows the current parent node directly and copies parent velocities; it has no H4 root-instance/bit30 reverse-time transform branch. Therefore matching bit positions or labeling this a generic notification is not an established integration.

Found explicit H4 flag30 clears in both8293E878(file156) and8293E1B0(file177), before physics synchronization8293DD10. Mask is sign-extended BFFFFFFF, preserving all other64-bit owner flags. Controller8249B418 sets this transient flag after controller execution; attached-child82939248 consumes it only on its root-instance bit3 branch. This is frame-phase state, not a saved-property change or a standalone event that can simply be sent to an arbitrary native callback. Other readers and exact parent/child update ordering must be accounted for before finalizing the boundary.

No implementation shortcut was added. Existing scenery/monitor controller APIs continue exposing original owner flags until the boundary is resolved. Native H3 saved formats and attachment updates remain untouched. No build, test, launch or deployment.


### Complete follow root extracted; containment boundary connected to native world (2026-11-12)

Added unchanged8244AF48 and its dependency closure to production extraction (150 bodies/41 boundaries). Added a strictly follow-scoped82415970 bridge boundary accepting only the original0000100900000000 mask and two invalid exclusions. It maps only the consumed boolean to HeldUpdateWorld.pointOutsideWorld; the native world builder now supplies NativeHeldWorldPointBlocked. The unused16-byte source query record is intentionally not synthesized:8244AF48 overwrites that stack space without reading it. The boundary rejects all other callers. The full follow entry still needs transient player/contact/local-view projection and monitor-target result routing before it can execute.

Additional flag-reader scan found82230FD8 and829B9EC8 as syntactic bit30 candidates, but inspection shows their tests use unrelated fields1136 and3840, respectively. They are not evidence of more controller flag consumers. Known controller reader remains82939248; the scan is not asserted exhaustive for indirect/aliased accesses.

Source extraction only. No builds/tests/launches/deployment.


### Complete monitor-follow bridge entry implemented (2026-11-12)

Added UpdateMonitorFollow using unchanged8244AF48. Shared RunHeldStage projects the same held scene/native world as UpdateHeld, then invokes either original root without hand-reordering its math. Follow supplies an explicit contact-active bit20/normal snapshot, private monitor identity64, local-player lookup and view record. Original82415970 containment,824F5CF0 obstruction, relative-reference/contact-plane projection, monitor controller request, local view conversion, editor32 distance and editor276 pitch history now belong to one original root call.

Controller boundary distinguishes held0 from monitor64 and returns submittedDatum independently of the magnet candidate targetDatum. Local view angles are returned only after original82400D48 notification and checked against local ownership. Obstruction exclusions are translated from private handles to native handles at the query boundary and restored to native identities in persistent editor256/260. Temporary view/local-map TLS pointers are restored through scoped cleanup, including exceptions; caller editor storage is committed only on successful completion.

This is source implementation, not an executed result. The API requires a genuine native monitor contact snapshot; no false/zero substitute is installed. Native contact producer, transient controller flag boundary, complete live grab/held/follow/release orchestration and save/lifecycle integration remain open. No builds, tests, launches or deployment.


### Original monitor contact-response bridge (2026-11-12)

Extended the existing unchanged82235650 scoped response with ResolveMonitorContact. The biped branch reads globals0/4/8/12 rather than scenery16/20/24; the existing original Ravine extraction contains45/10/2/4 respectively (same recorded28-byte settings hash). Original source selects tangent damping using its velocity threshold. The bridge supplies all four coefficients without substituting scenery behavior.

Private monitor projection now includes unit3910 movement mode,4015 surface flags,2188 timestamp and original time4/12. Collector mode follows the original movement-mode==1 argument. Character surface flags are admitted only through the monitor entry; ordinary scenery retains its rejection guard. Surface category bit1 executes the original timestamp/window logic and82943B08 notification at the source call position; bit2 retains the original mode-gated4015 bit1 write. Notification arguments are checked exactly (65,0,1,1,0) before invoking the required native callback. All returned timestamp/flag state is explicit. Scope restoration covers both contact callback pointers.

Native820FFBE0(file34) establishes matching state fields: H4 mode3910 -> H3 1218; surfaceFlags4015 ->1323; surfaceTimestamp2188 ->1008; time tick rate4/tick12 remain4/12. Native category bit1 sets object276 bit6 and calls820F2A78; H4 uses82943B08. The notification equivalence still needs inspection before wiring that boundary. Native collector must also admit monitor mode explicitly; its current scenery-only adapter remains unchanged.

This adds source implementation, not runtime evidence. Full native monitor-contact producer, transient controller flag handling and live lifecycle wiring remain unfinished. No build, test, launch or deployment.


### Native monitor contact adapter and persistent normal (2026-11-12)

Added ResolveNativeMonitorContact, restricted to an unparented biped in local Forge, for use only by the scenery-held lifecycle. It supplies original Ravine45/10/2/4 response settings, native physics point/velocity, definition radius, tick interval/rate/count, contact flag and mapped unit surface state. Native geometry collector now has an explicit monitor branch, supplying native1218==1 to its biped-mode argument; scenery retains its existing path. Original response velocity is submitted through820F29C8. Returned contact bit, surface timestamp and source-owned surface flag bit are mapped back while preserving unrelated native bits.

Inspected H482943B08(file220): for its exact(0,1,1,0) arguments it sets source collision flags32 and0x01000000, stores bytes368/369 and tails into8225CBA8(file6). That latter body matches native820F2A78(file19)'s object/parent header-bit1 queue walk (H4 header16-bit flags versus native8-bit). The adapter invokes the stock H3 equivalent action at the matching820FFBE0 category-bit1 branch: native collision flag64 then820F2A78. It does not copy H4 collision-flag offsets or widths into H3.

Source suppression exits before writing the normal, so the monitor bridge now accepts and preserves previousNormal rather than zeroing it every call. Native H3 has no corresponding normal field: the lifecycle must retain this vector in transient editor state and provide it explicitly. The helper returns original cached point and normal together; they are not yet wired into the live tick. Full lifecycle must enforce controlled-monitor/scenery ownership and replace (not double-run) the native contact stage.

No builds, tests, launches or deployment. Live phase/order integration, transient controller flag handling and the three reported bugs remain open.


### Contact phase replacement and follow snapshot (2026-11-12)

Compared complete caller prologues: native820F57A8 calls820FFBE0 with controlled-unit datum and player64 cached point, after root eligibility820EA1C0. Return address is820F584C. H48297F658 calls82235650 at the matching unit-update stage after822E32C0, with player140 and player152. Therefore contact response belongs at this existing native call, not as another operation inside held/follow.

Added a guarded820FFBE0 hook and ReplaceNativeMonitorContact. It only replaces the matching return-address caller when the host editor slot explicitly owns monitor contact, has an initialized retained normal, matches the full salted player/monitor identities, matches the native controlled-unit and cached-point destination, and agrees with the native held scenery record. Stock calls otherwise remain native. Replacement writes original cached-point output, retains returned normal in host state and returns the original contact boolean.

NativeMonitorFollowWorld consumes that retained normal and the actual native contact-active bit, plus the existing obstruction query. It does not invoke the response a second time. Release/reset disarms contact ownership; world/player reset discards host state. No H4 normal is inserted into native H3 player/save memory.

The new hook is dormant: ownsMonitorContact defaults false and has no enabling assignment. Full lifecycle must establish original normal initialization and monitor ownership before arming it. That initialization, lifecycle orchestration and transient controller attachment flag remain incomplete. No build/test/launch/deployment.


### Contact-normal allocation lifetime established (2026-11-12)

H4 player allocator82355698(file225) calls82A3B180 then82355740 and823562E8.82A3B180(file226) invokes82A3B2B0(file152); that routine reads datum-array stride32 and clears the full record through8224A558 for sizes over32, then restores its salt. Player pool setup82354F20 specifies4144 bytes. Constructor82355740 and initializer823562E8 do not overwrite player152..160. Thus the original contact normal starts at zero at player allocation. Controlled-unit reassignment82357E90 resets cached point140..148 but retains normal152..160; it must not be reinitialized on every grab or monitor switch.

Rejected82355428 as a normal initializer: its apparent152 writes target TLS132 state, not the player record. No implementation uses that misleading offset match.

Native821E7A90(file76) matches the H4 player creation wrapper, returning a full salted datum after allocation821FCB48 and initialization821E8110. Added its post-call hook to initialize host contact normal only on successful player allocation. NativeEditor now preserves an existing same-player contact snapshot when constructing the original editor; it does not manufacture zero for late attachment. Player/world reset ordering and activation remain to be integrated, including preserving allocation-time state across the first PhysicsWorld synchronization. The contact hook remains dormant.

Source inspection/implementation only; no builds, tests, launches or deployment.


### Player contact state separated from editor/world reset (2026-11-12)

Moved retained contact normals into16 NativePlayerContact records, distinct from per-map NativeEditorSlot storage. Successful native player allocation records full salted player identity, datum-pool pointer and exact880-byte record address. Every lookup validates current pool, record and salt. Initial PhysicsWorld synchronization can now discard editor/held state without erasing the player's allocation-time normal. NativeEditor never fabricates a normal for late attachment.

Inspected native821E74C8: its ordinary reset path passes TLS96's player pool into821FCA48; its preservation branch does not.821FCA48(file102) resets pool counts/salts, clears active record salts and occupancy bits. Added a hook scoped by exact TLS96 pool identity: actual player-pool clearing discards both host contacts and editors, while other datum pools are ignored. A subsequent successful player allocation establishes fresh zero state from the original H4 allocation contract.

Normal reads/writes in contact replacement and follow now use the independently validated player lifetime. PhysicsWorld changes still disarm ownership and discard per-map manipulation state. Full lifecycle activation, transition/update ordering and transient controller flag remain open. The normal behavior during intervals outside the replacement's held-scenery ownership still needs integration review before activation. No builds/tests/launches/deployment.


### Contact-state handoff while stock H3 owns movement (2026-11-12)

Native820FFBE0's primary82237E58 call returns at820FFED0 with direction0 and normal destination in r6 (stack112). Its second reverse selector returns at820FFEFC and must not replace the primary normal. The primary normal is subsequently consumed for the native response, then overwritten in the same stack space by output velocity. Reading the stack after the entire routine would therefore capture the wrong quantity.

Added scoped read-only observation around the stock native contact routine and its primary selector. It captures a finite normal immediately after a successful original primary selection, then commits it to the validated host player-contact record only after the native response returns. No native arguments, outputs, velocities, collision flags or notifications are modified by observation. Nested calls restore their previous observation scope. Matching controlled-player identity, exact cached-point destination and local Forge are required. Reverse selection and unrelated users of the selector are ignored.

This is the stock-H3 boundary outside held-scenery ownership, not a claim that H3 and H4 selectors are identical. It prevents later scenery grabs from using an allocation zero or stale last-held plane after native movement has established a new contact. H4 response continues to own contact calculations only when the completed scenery lifecycle activates its replacement; otherwise stock H3 behavior runs unchanged. Failed native selection does not publish an unproven output vector.

No execution/testing. Full grab/held/release orchestration, activation and controller attachment-state handling remain open.


### Controlled-root attachment compensation math (2026-11-12)

Added CompensateAttachmentPose for82939248's root-instance-bit3/controller-flag30 branch. The source normalizes angular velocity with8228ACE8, uses negative original tick interval and original82265C30/82265E28 trigonometry, constructs rotation with82300D40, rotates the root basis with821E0550, advances root translation by negative tick using fused multiply-add, then composes previousRoot * inverse(root) * attachedNode using822864E0 and8226BFC0. Root scale is retained. The bridge follows this helper order and keeps inputs/output in private scratch; no native physics or saved data is changed by the calculation.

Production extraction now includes153 unchanged bodies and41 boundaries. Newly included original functions are82300D40,821E0550,822864E0; existing helpers are reused. This is source extraction, not execution. Eligibility, owner-flag lifetime and native attached-node submission remain required before integration. The existing native823317C0 still has no equivalent compensation branch.

Source inspection also found RotateHeld's monitorView parameter shadowed the thread-local monitorView scope pointer used by its reentrancy guard. Renamed that parameter to viewDirection so the guard refers to the intended pointer. No build or test was performed. Full lifecycle and reported defects remain incomplete.


### Attachment eligibility resolved from its producers (2026-11-12)

H48298E798(file244) is not a general physical-object validity predicate: with its true second argument it reads object definition28 bit11. Local Gen4 Object schema identifies this as EarlyMoverLocalizedPhysics; stock H3 GameObject flags are a ushort at definition2 with the corresponding bit7. The native adapter now requires that authored flag without changing it.

H4824A2B38(file23) chooses instance24/25 selected-body indices and sets/clears instance16 bit3 based on the selected body's runtime motion232==4 (after preliminary authored selection). H4824A3220 also sets it for motion4. Native counterpart82269088(file85) chooses instance12/13 using72-byte body entries and then updates its separate single-body flag6; it does not maintain the H4 selected-keyframed flag.

Added NativeAttachmentCompensationEligible: valid unparented root, authored localized-physics flag, valid native instance/selected index, and selected body168==6 (the established native keyframed counterpart). It does not read native instance bit3 as though it were H4's flag. Root/child ancestry, controller-flag phase and actual compensated-node submission still need wiring. No build/test/launch/deployment.


### Controller flag phase and native child-node submission (2026-11-12)

Mapped H48293DD10 physics synchronization to native82332FF0(file78): connected flag, instance lookup, selected body/motion predicates, transform and velocity synchronization. The native's only direct caller is82333388(file36), which checks object160 then calls synchronization at return823333C4 before ordinary object update and recursive descendants. This is the native phase corresponding to H48293E878/8293E1B0 clearing owner flag30 before8293DD10.

Successful mapped scenery/monitor controller submissions now retain flag30 in a host-only controllerAttachments record when source-derived eligibility holds. Record includes full datum plus live object and instance pointers. Native82333388 entry erases the object's record before synchronization; world reset also clears the map. No H4 flag bit is written into native H3 objects or saved variants.

Added guarded native823316D8 hook at exact82331858 caller from823317C0. It walks child ancestry to the root, requires retained controller state and matching object/instance plus localized-keyframed eligibility, validates the passed parent-node address against native signed node20/offset316 and byte count314, reads actual root node0 and parent node, then submits the original compensation result through the original native setter. Native root velocity/time are read as-is. Other setter calls/roots stay on their original path. Scratch guest stack is restored with RAII.

The source path is now connected from successful controller submission through child-node adjustment to the object-update reset phase, but those controller submissions still await full live scenery lifecycle wiring. This is not executed proof, nor an exhaustive claim about all indirect H4 flag readers. No builds, tests, launches or deployment.


## Native release completion boundary (2026-11-12)

Source inspection: H4 `82451250` (generated file11) calls original selection/reset `82449ED8(editor,player,-1)` before its release eligibility branches. Its retained local-object path performs variant/update handling, optionally enqueues `8244F300`, then calls `8244A180` and `8244A2A0` after ownership has been cleared. H3 `8227FDF8` (generated file62) has different transaction semantics: invalid player returns; session type4 serializes a request through `823C2B10`; the local path syncs/optionally throws/enqueues through `82283950`, then clears engine57752[player] at `8227FFC8`. Returning from this routine alone does not prove release.

Corrected the native wrapper's completion boundary in advanced_forge.cpp: capture the previous held datum independently of throw strength, retain the existing non-throw condition for fixed-snap finalization, and permit host cleanup only after the original local transaction has actually cleared the held slot. Previously the wrapper discarded coordinates, anchors and spawn-distance state unconditionally, including no-op/network-request returns. The change preserves the stock native transaction and request path. It does not activate the incomplete H4 held lifecycle or claim the three reported defects resolved.

Integration requirement: full H4 selection-reset and physics ordering must be connected at the native ownership transaction boundary, not blindly placed after every public drop call. The original H4 reset-before-eligibility order cannot be inferred from H3 function return. Original H4 physics transition also sets object flag10 after rebuilding a frozen body; the complete native transition adapter must explicitly account for that post-rebuild effect before activation.

No builds, tests, launches, captures or deployment. Prior turn was a status-only/no-progress acknowledgement; this turn inspected both original release functions and changed the authoritative release wrapper. Full grab/held/follow/release integration remains unfinished.


## Complete native physics-transition boundary (2026-11-12)

Progress classification: preceding turn changed the native release completion guard. This turn re-read H4 82260CF0 (generated237) and H3 820AC960 (generated97): H4 object256 bit10 and native object172 bit9 gate both linear and angular velocity reads before the body/fallback paths. This confirms the previously documented cross-version mapping also applies to the post-rebuild bit10 write in original8244A2A0 (generated58).

Implemented TransitionNativeSceneryPhysics in advanced_forge.cpp. It accepts the original selector's four-state result and explicit holder state, queries native model/physics-instance availability, maps frozen6/velocity-gate9/force-dynamic20 into private original-layout bits6/10/21, and executes the existing unchanged-original transition bridge with RebuildSceneryPhysics at its create/rebuild boundary. A held editor must name the exact same salted object. Held offset/scale/decay changes remain in the persistent original editor. The callback now reflects native post-rebuild bit9 as H4 bit10, and the enclosing adapter applies the original post-rebuild bit10 result back to native bit9 while preserving unrelated native flags. H4 bit22 remains a scoped constructor request; every valid original state writes it before rebuild. No H4 object/save layout is copied into H3.

The adapter requires PhysicsWorld synchronization before obtaining its PhysicsObject reference; it does not reset the owning map while holding that reference. It remains unwired pending the native ownership transaction and selector orchestration. Old ApplyPhysics still exists and is not claimed as equivalent. No builds, tests, launches, captures or deployment occurred. All three reported manipulation defects remain open.


## Native selector and post-ownership grab assembly (2026-11-12)

Previous turn was progress (native complete physics transition adapter). Re-read original8244A180 (H4 generated195) and native8227EB28 (H3 generated103). Implemented SelectAndTransitionNativeSceneryPhysics: obtains native held ownership, validates the object's native variant slot/datum, executes the authored-keyframed predicate only for unheld Fixed/Phased, and calls native8227EB28 only for unheld Normal. It then runs the unchanged original state selector followed by the full transition adapter. Native deferred-queue capacity is checked; no raw queue bit substitutes for the native session/state-gated predicate. Explicit mode remains a host editor property, not an interpretation of incompatible native variant bits.

Implemented InitializeNativeSceneryHold as the post-ownership/post-dequeue stage: requires the correct native holder, no remaining queue entry, exact previously-selected original editor datum, and pre-grab physics metadata. It runs selector/transition before collecting post-transition placement data, then original grab initialization. Player input is retained across re-grab. It deliberately does not synthesize/reset selection after dequeue and does not arm monitor contact. The complete outer lifecycle still needs wiring.

Exact insertion boundary established by re-reading native822800B0 (generated106): after native validation, local variant update/sync, holder-slot store and823BFBD0 notification, it calls82283B90(datum,-1) with return address822802A8. The selection/reset stage must run before that dequeue call; native ownership has already committed there. Using only a post-return822800B0 hook would put original selection after dequeue, contrary to H4 82450E10. The public grab post-stage must also replace, rather than retain, the later H3 forced-dynamic/distance initialization for owned scenery. No incomplete lifecycle is activated by these helpers.

Source implementation only. No compilation, tests, game launches, captures, or deployment. Unresolved: inner transaction hook, replacing old grab/held path, release/exit cleanup, and complete sequence verification after RE/implementation finish. All three user defects remain open.


## Native grab transaction hooks (2026-11-12)

Previous turn was progress (selector and post-dequeue assembly). Wired public8227E810 through a scoped scenery-grab transaction: validate local Forge, capture pre-grab physics metadata, retain native ownership/variant processing, and initialize original post-transition placement on successful acquisition. New inner82283B90 hook runs original selection/reset only for the confirmed822802A8 grab caller and matching datum after checking the native holder; native dequeue/notification always executes. Scope restoration protects nested native calls. Failed/rejected native acquisition does not manufacture a held editor.

For that successfully selected transaction only, the8227E770 hook skips H3's forced-dynamic stage at exact return address8227E9F0 (confirmed in generated75). The complete original selector/transition runs in the post-grab stage instead. The original distance is copied back to H3's native distance cache for native consumers. Removed the radius*2+1 palette-only clearance heuristic from the public grab hook; both create and re-grab now use the same original-placement stage for eligible scenery. Other object classes retain the native public grab. A post-grab bridge failure restores tracked native physics, clears original editor state and disables the bridge.

This is INCOMPLETE integration source, not a candidate ready to run: held tick still uses the old path, legacy distance preservation remains to remove, and release/exit handling is not yet the complete original lifecycle. Monitor contact ownership remains unarmed. No build, tests, launches, screenshots or deployment. No reported defect is marked fixed.


## Held pre-submission sequence and rejected interception point (2026-11-12)

Prior turn made source progress by wiring grab stages. Added Bridge::AdvanceHeldPlacement for original8244D5E4..8244D60C: single-rounded scale-minus-decay, fsel against original image821289E0 (read directly:00000000), then unchanged82452738 distance update. It changes only editor36 and28, preserving selection, transform and remembered snapping state. This stage belongs after RotateHeld and before UpdateHeld/UpdateMonitorFollow. The dispatcher source explicitly orders those three stages and then follow; no second native distance update should run.

Removed the now-unproduced SpawnClearance structure and the remaining82281A98 post-call cap-extension workaround. Native held movement capture remains for the existing path while full replacement is unfinished.

Inspected native8227F578 (generated70) and its exact82281A98 caller (generated109, return82281F28). This is NOT a full held-update gate: nonzero jumps only to82282114, after some translation work but before subsequent8227FA50, rotation, distance and sync work. Therefore overriding this predicate would not skip the entire old placement path and would mix H4/H3 movement. Do not implement the proposed predicate interception. A narrow replacement of the held block in the enclosing original routine, retaining its selection-ray/prefix and non-placement suffix, or individually accounted suppression of all old consumers is required. The original native routine must not simply be replaced by magnets alone.

No build/test/launch/deployment. Complete held block orchestration and native eligibility correspondence remain open, followed by release/exit and later sequence verification.


## Preserve native tick around complete held-block replacement (2026-11-12)

Prior turn was source progress (decay/distance stage and removal of dead clearance overrides). Added extract_native_tick.py, producing one private native_forge_tick.inl under the existing isolated directory. It copies original H3 82281A98 from generated109, renames its declaration, and inserts exactly one optional callback at loc_82281F20. A handled scenery callback jumps to loc_822821E8, bypassing the complete native translation/rotation/distance/sync block; false retains that block. Original prefix and suffix remain byte-for-byte equivalent source after removing the declaration change and inserted handoff. The extractor enforces that textual invariant and records the normalized original function hash. This is source extraction, not executed parity or a gameplay test.

The handoff supplies original r18 player and r31 held datum. It calls through a context copy, retaining native nonvolatile state for the suffix. Source inspection shows the skipped block's changed nonvolatile register is r30, which the suffix does not consume; r18/r20/r22/r23/r24/r26/r27 used by the suffix are not assigned in the skipped block. The callback must still account for native memory effects: placement/variant synchronization and held-state cleanup. The extractor does not invent those effects or activate an incomplete callback. Local eligibility/parent handling in the prefix remains native; H4 instance eligibility still requires explicit native correspondence in the replacement.

The extracted routine is not yet included/called by advanced_forge.cpp. Pending: complete held-stage callback and its eligibility, input interception, scene supply, body/monitor submission, native bookkeeping, then release/exit integration. Original tests/builds/launches remain prohibited until RE and implementation finish. No game or test was run, and nothing was deployed.


## Coupled eligibility and exact monitor-facing output (2026-11-12)

Prior turn was source progress (preserved native tick extraction). Traced H4 instance16 bit2 writer8249C390 (generated78) and clearer8249B7B0 (generated99): world-connection lifecycle. Native object disconnect82330AA0 calls82263098 (generated90), which clears instance4 bit3; native connect82330B20 calls822633B8 (generated7), whose final write sets instance4 bit3. Added NativeCoupledSceneryEligible using this exact counterpart, valid scenery/crate identity and no parent. This is not the authored-motion predicate nor native single-body bit6. Local holder/editor eligibility remains a separate enclosing condition.

Resolved monitor-follow output mismatch without reconstructing a direction from angles. H4 follow8244AF48 calls822C8040 to derive up from its corrected facing, then823FC348 with facing/up. Original823FC348 (generated104) copies facing to its stack112..120, builds quaternion/angles, stores local view angles and calls82400D48 at return823FC440. Bridge notification now validates that exact caller and captures the saved facing alongside the original angle result. HeldUpdateResult exposes viewDirection for the native820B04B0 adapter, retaining stock H3's two-angle control format. The original H4 conversion and notification still run unchanged; no guessed pose basis or inverse trigonometry is used.

Both changes are source-only and feed the pending complete tick callback. No builds, tests, launches or deployment. Scene supply, input producer hookup, ordered body/monitor submission and native bookkeeping still need connection; release/exit integration remains open.


## Ordered coupled-stage assembly and input interception (2026-11-12)

Prior turn was progress (instance eligibility and exact facing output). Added RunNativeCoupledSceneryStage: validates exact native/original holder, local monitor control record and contact lifetime, then runs original rotation, scale-decay/distance, held update, native scenery controller, original monitor follow, native monitor controller and native view-facing submission in that order. Follow's world queries occur after scenery submission; its native view update occurs after monitor body submission. Submitted datums are checked and the native menu distance cache is updated from retained original editor28. The helper requires an actual supplied nearby scene and does not fabricate one or run a second Evaluate/magnet pass.

Re-read H3 input producer821F04C0 (generated40): r3 player, r4 packet, eligibility820B06A0 before packet consumption. Added its native hook to use ConsumeNativeSceneryInput only when the complete held lifecycle owns that player's contact/input state. Otherwise original handling remains. PhysicsWorld is synchronized before acquiring the editor slot. Existing original H4 input adapter performs dominant-axis processing and disarms native distance/rotation consumption. Failure restores tracked native physics, clears original editor state and disables bridge handling.

The lifecycle ownership flag is still unarmed. Full held callback still needs nearby-scene supply/native bookkeeping and connection to the extracted native tick; release/exit cleanup remains pending. Source-only work: no builds, tests, launches, captures or deployment. The reported manipulation defects remain open.


## Native magnet candidate-query boundary (2026-11-12)

Prior turn was source progress (coupled stage and input hook). Re-read H4 marker candidate82582250 (generated156): query821F2050 receives category1, type mask15071, held object location+24, center from8293A3B0, capacity64, and radius equal to held runtime sphere76 plus the single-precision distance between that center and editor reference returned by824499A8. This differs from the old Evaluate host filter based only on held-binding radius plus candidate-binding radius. Do not carry that filter into the complete held lifecycle.

Mapped the native service by source: H3 820E0350 (generated1) calls820B0B60 with the same category/type/location/center/output/capacity convention and a location copied from object28. Native820B0B60 (generated40) calls820B0F30 for clusters, iterates native object spatial lists, suppresses duplicate object IDs, checks object type and sphere intersection, filters through820B13A0, and stops at the supplied capacity. It does not depend on being listed in a Forge variant. H4 821F2050 (generated140) packs flags and dispatches to8256B440; native bit positions must be translated explicitly rather than copying15071 blindly.

Implemented NativeNearbyObjects around unchanged820B0B60 using the object's native location, explicit caller-provided type mask and original center/radius. It preserves returned order and full salted datums, uses a process-local guest stack buffer, and rejects invalid counts/identities. It does not sort, prefilter by marker binding or synthesize candidate geometry. Outstanding for scene integration: finish exact type-mask mapping, original radius/reference calculation, maintain held-first private indexing without changing the native query order, and resolve root marker transforms. The existing old Evaluate path remains pending replacement; no claim of a magnet fix yet.

No builds, tests, game launches, captures or deployment.


## Candidate types and marker ancestry (2026-11-12)

Prior turn was progress (native sphere-query adapter). Read original Ravine cache object tags directly using tag-group hierarchy and runtime type halfword0; retained compact evidence in isolated/object-type-source.json. Observed: bipd0, vehi1, weap2, eqip3, proj5, scen6, mach7, ctrl8, dspn9, ssce10, bloc11, efsc14. Original dispenser9 has no stock-H3 object class; native sound scenery is9 and crate10. Literal15071 is consequently invalid as a native mask. Terminal4, creature12 and giant13 were not present in this cache extraction; do not present them as cache-proven. Complete mask translation remains pending explicit source correspondence for those classes.

Re-read82582610: traverse object parent36 to root, then retrieve the configured marker group from that root, capacity32. Added NativeMarkerRoot using native parent16 with salted identity validation and cycle rejection. Candidate identity remains unchanged for eligibility/scoring; root traversal must not rewrite or deduplicate the native sphere-query result.

Clarified82937F50: it resolves the candidate's object model/render-model reference and calls8226BF48 with the incoming marker group. That helper searches render-model marker-group records (count60, pointer64, stride16) for the requested group. Thus the predicate checks candidate model group availability separately from82582610's root marker collection; it is not merely a generic has-render-model check. The existing cached-marker approximation must be replaced by separate eligibility/root-marker fields in the complete native scene mapping.

No builds, tests, game launches or deployment. Native scene mapping and final held callback remain incomplete.

## Separate candidate eligibility and query order (2026-11-12)

Previous turn only acknowledged the no-testing instruction (no progress). This turn re-read original82937F50 (generated52),82582610 (generated240), and the marker predicate caller82582390. Implemented independent optional candidate-model group existence in bridge Object. The original predicate now checks the requested configured group, preserves the invalid-datum false result, and uses that field independently of collected root markers. Legacy diagnostic scenes alone retain their old inferred behavior.

Scene now carries optional native-query order as private indices, separate from held-first storage. Query boundary preserves supplied order and validates capacity, indices and duplicates before writes. An explicitly empty query differs from an unspecified legacy query. The coupled native stage requires both explicit eligibility and query order before it can mutate placement state; no synthetic fallback is allowed on that route.

Private diagnostic AFS3 preserves these fields; AFS1/AFS2 remain readable, and old scenes still write AFS2. This changes no H3 save or map format. Source edits only: no build, test, launch, capture or deployment. Native scene population, type mapping, root transforms and full held lifecycle remain incomplete. The 64-result query plus held-not-in-results case still needs a private arena capacity/index audit (monitor currently occupies private index64); do not truncate a native result to make it fit.
## Full query capacity without private-handle aliasing (2026-11-12)

Previous turn made source progress (separate eligibility and query order). Inspected all bridge uses of private indices64/65/66 and all scene-record allocation sites. A native query can return64 entries without including the held object, requiring65 storage records. Original query capacity remains64; no native budget or map limit changes.

Moved the private monitor handle from64 to67 across selection-ray setup/callback, rotation setup, coupled held/follow setup, magnet evaluation and native-datum translation. Scene indices0..64 now fit without aliasing; standalone adapter65 and previous-target sentinel66 remain distinct. Storage at0xa0000+i*0x100 ends at0xa4100, below coordinate storage0xb0000; object headers through67 are inside the already committed arena. Monitor body remains0xb4000. This is a host-private remap, not a change to any original H4 routine or native datum.

Bridge entry points now preflight scene storage and explicit query order before copying editor state. A65-record scene requires an explicit at-most64-result query; it cannot fall back to returning65 objects. AFS3 supports65 records while old versions retain64. Root-marker transforms, translated type mask, exact query sphere and scene population are still pending. No builds/tests/launches/deployment; no gameplay claim.
## Original marker construction and query reference (2026-11-12)

Previous turn was progress (private-handle capacity correction). Read original82582250/generated156,824499A8/generated48,8226BCA0/generated187,8259E9A8/generated265 and8226BB50/generated266. Source evidence changes the next integration step: do not construct root markers from a generic object pose alone.

82582250 obtains the reference from824499A8: current held physics point plus editor56/60/64 multiplied by editor36, using single-precision fused multiply-add. It subtracts that reference from the physics point, accumulates squared distance in Y,Z,X order (multiply then two FMAs), square-roots and adds runtime sphere76. Native query must receive this exact result or be called directly at the original query boundary, rather than an approximate binding-radius filter.

8226BCA0 obtains live node matrices (H4 object444 byte count /52, offset446), validates model region/node counts, and calls8259E9A8. That routine filters markers by region/permutation, reads the marker's node byte2, composes local position/quaternion with that node's52-byte matrix, copies authored marker32 to output108, and negates world-basis72/76/80 for mirrored objects. Its fallback uses authored render-model nodes only when no node matrix array is supplied. AFM2 currently stores only node-zero position/quaternion; the exporter proves identity authored root but does not establish the current live root matrix or preserve all marker metadata. Existing MakeMarker is therefore insufficient as the complete native adapter.

Added8259E9A8 as an original extraction root and regenerated source only:157 unchanged bodies,41 boundaries. This includes original transform construction/composition dependencies (822826C0,8226BFC0). Next step is to expose this original constructor with explicit native node/marker data rather than extend the host quaternion approximation. No execution of the extracted logic occurred. No build, test, game launch or deployment. Complete scene mapping and lifecycle remain unfinished.
## Original marker builder adapter (2026-11-12)

Previous turn was source progress (original marker construction extraction). Added Bridge::BuildMarkers using unchanged8259E9A8. Inputs are original48-byte BE marker records, live13-float node matrices, optional current region permutations and explicit mirrored state. The original code performs filtering, node composition, authored trailing-float copy, mirroring and32-result truncation. The adapter validates node/region references and finite node values, supplies a temporary private render-model/group view and restores its temporary tag entry. Source marker groups are not truncated before permutation filtering. Temporary guest pages are decommitted on return/error; no persistent native or save-format allocation is introduced.

The native caller is not connected yet. AFM2 source metadata and live native node/region/mirror acquisition must be completed before replacing MakeMarker. This method is source implementation only, not evidence of parity or working interaction. No build, test, launch, capture or deployment.
## Native live marker-node source (2026-11-12)

Previous turn was progress (original marker builder adapter). Located native8210CDF8/generated67 by marker-collection call sites and compared its data flow with H4 8226BCA0. Native signed object314 is node-array byte length; signed316 is relative node-array offset; the reciprocal multiply/shift divides by52. Native object4 bit10 is forwarded as mirror state and drives the same world-basis72/76/80 negation in the fallback. This is distinct from parented object-pose reader820D8FA0.

Added ReadNativeMarkerNodes: salted object validation, explicit node-array bounds, complete live13-float matrices and native mirror bit. This helper does not reconstruct basis/scale or use authored bind matrices. It is not wired to the final scene yet. Native region/permutation acquisition remains pending:8210CDF8 reads signed318/320, subtracts16 when object4 bit11 is set, divides remaining size by10 and offsets8 bytes per region before calling82591580. Read that callee before mapping this into H4's permutation byte array.

No builds, tests, launches or deployment. Full scene mapping and held/release lifecycle still unfinished.
## Native marker permutations and constructor connection (2026-11-12)

Previous turn was progress (live node reader). Read native82591580/generated60. It receives the permutation-byte array from8210CDF8, compares the byte indexed by marker region0 to marker permutation1, and builds112-byte output using node2 and the supplied live matrix array. Native source records have36-byte stride; H4 records48-byte stride. Their position4/quaternion16/trailing float32 fields agree. Do not reinterpret a native36-byte group as H4 records without explicit repacking.

Extended native node-state reading with the exact signed318/320 region-block calculation from8210CDF8: subtract16 from byte-size when object4 bit11 is set, divide adjusted size by10, start permutation bytes at block+8*count. Implemented BuildNativeRootMarkers to resolve the original parent root and call the original H4 constructor with its live matrices, permutations and mirror state. Caller must supply that root's marker definitions; candidate eligibility remains independent. Removed an unnecessary128-entry input-array restriction in the bridge; original marker region indices constrain accesses, while the supplied region table can be larger.

Connection is still incomplete: source marker definitions and root binding lookup must be supplied by the scene provider. Existing AFM2 cannot preserve the full source metadata. No gameplay validation claim. No builds/tests/launches/deployment.
## Full marker binding metadata (2026-11-12)

Previous turn was progress (native permutation mapping). Added a read-only mmap source-cache reader for complete original48-byte sandbox_magnet records, selected by the existing original render-model index and configured group0x193. Exporter now prepares AFM3: retains legacy pose fields plus complete BE definitions, rewriting only the previously adapted position/quaternion fields. It compares the indexed source points with raw source records before association and rejects node remapping/count mismatches. Region, permutation, authored float32 and remaining bytes are preserved rather than invented. Loader accepts AFM3 and stores definitions; AFM2 stays readable with definitions absent and cannot supply complete new lifecycle metadata.

Exporter has not been executed: source implementation only. Native root binding lookup and the final query provider remain outstanding. No build/test/launch/deployment. The original files and installed marker pack have not been changed.
## Candidate/root metadata binding (2026-11-12)

Previous turn was progress (AFM3 exporter/loader). Implemented NativeMarkerBinding using the current map and exact native object-definition datum. ReadNativeMarkerData checks the candidate's binding independently, resolves the parent root, obtains that root's binding, and constructs markers from its live node/permutation/mirror state through original H4 code. Old AFM2 bindings explicitly fail this complete path rather than synthesizing missing metadata. Missing root bindings return no markers without borrowing the child's data.

Read original cache records only (no game logic/test execution): all631 markers across indexed fw_unsc_c_ source models have region255/permutation255/node0. Thus these source groups are unconditional and node-zero; preserving their raw metadata does not accidentally index a different native region. This census does not prove correctness for other source families or final gameplay.

TODO now records the current helper/metadata status, unregenerated pack, pending query/lifecycle integration and no-testing gate. No builds, tests, launches, captures or deployment. The three reported interaction defects remain open.
## Original magnet query radius adapter (2026-11-12)

Previous turn was progress (candidate/root binding connection). Implemented Bridge::MagnetQueryRadius. It copies the selected editor into private memory, maps only its physics-point query, and executes original824499A8 to obtain the reference point. It then follows82582250's displayed instruction order and single-precision rounding: Y/Z/X subtraction, Y multiply, Z/X fused multiply-add, square root, radius addition. This retains offset/scale state rather than using authored binding bounds or a guessed distance. Input editor remains unchanged.

Native scene provider must call this after the original per-tick offset decay/distance stage, using the current held physics point and native runtime radius44. Complete native type-mask correspondence remains unresolved for source classes absent from the available cache; the TagTool Gen4 definition stores only a numeric short and does not establish those missing enum values. No speculative mask was installed.

Source implementation only; no parity/runtime execution or test claim. No builds, tests, launches or deployment. Native query provider and final lifecycle connection remain pending.
## Complete executable object-type mapping (2026-11-12)

Previous turn was progress (original query-reference/radius adapter). Located object-type descriptors in the original image by name/fourcc, then their dispatch pointer table8336AD78. Original822B4458/generated10 loads signed object178, multiplies by4 and indexes that table, establishing the runtime type correspondence directly. Retained all15 descriptor names/groups/addresses in isolated/object-type-executable.json. This closes the previous missing terminal4/creature12/giant13 evidence; cache-only absence no longer blocks the mapping.

Implemented explicit0x3ADF ->0x1CDF native query-mask translation: preserve0..8, omit H4 dispenser9 (no stock H3 counterpart), shift10..14 down one. Added NativeMagnetCandidates combining exact selected-editor identity, current native physics point, original-reference-derived radius and unchanged native nearby query. Caller must use it after original offset decay; it does not sort, truncate or substitute binding bounds.

Next: assemble query results into held-first private scene records while preserving query order, then finish native held/release lifecycle. No builds/tests/launches/deployment. Source data inspection only, not runtime verification.
## Native magnet scene assembly (2026-11-12)

Previous turn was progress (complete executable type mapping). Source820FC7F8/generated106 and82344B58/generated98 explicitly pass native object32/44 as the runtime sphere; mapped to H4 candidate-scoring64/76. Implemented BuildNativeMagnetScene with runtime spheres, current monitor movement496, independent eligibility, root markers, held-first storage and explicit native-query order. Held marker absence follows the original early-out without querying. Returned objects remain in the query even when marker-ineligible; no variant-only enumeration, radius shortcut, candidate sorting or parent deduplication is used.

RunNativeCoupledSceneryStage now constructs this scene after original rotation and offset-decay/distance work rather than accepting an externally prepared scene. Removed an invalid bridge rejection of a monitor appearing among query results: the original type mask includes bipeds, so its scene identity must coexist with the separate monitor handle. Original candidate eligibility filters markerless objects.

Full tick activation, phase audit against writes during8244A8D8, native bookkeeping and release/exit remain pending. AFM3 exporter not run. No builds, tests, launches or deployment; no assertion that the three reported defects are fixed.
## Held phase and native synchronization audit (2026-11-12)

Previous turn was progress (native scene assembly). Read complete original8244A8D8/generated194: before8244EED8 it changes target124..132, cached pose172..220 and quantized orientation84..168, but has no direct writes to reference offset56..64 or scale36. Native contact/controller world effects still require final integration review. Query reference must not be replaced by the changed snap submission.

Read the full native82281F20..822821E8 block and callees8227FA50/generated25 and82284078/generated20. Important correction to earlier pending notes:8227FA50 is not mere variant synchronization; it computes a spring/rotation response and submits velocities through820F29C8 (or native placement fallback). Calling it after the H4 controller would retain a second competing controller. It belongs to the skipped movement block.

Actual settling synchronization calls82284078(1,held), then clears engine58520+playerIndex. Added SyncNativeSceneryPose around that original pose/variant path, with a narrowly scoped matching-datum bypass of legacy Evaluate in placement/live-pose hooks. This preserves native serialization and avoids a second magnet evaluation. It is not yet called by the final native tick: ownership/contact activation, the native dirty-byte lifecycle, release and cleanup remain pending. No builds/tests/launches/deployment.
## Native scenery owner resolution (2026-11-12)

Previous turn was progress (controller/synchronization phase audit). Added ResolveNativeSceneryOwner and connected it to the coupled stage before mutation. It joins the exact salted player allocation/contact lifetime, native held variant entry, unparented scenery/crate object, controlled biped with reciprocal player ownership, and unique matching local control record. This supplies the monitor/local-slot mapping needed by the final tick callback without relying on coincidental player-index/local-index equality. Existing offsets come from the already inspected native contact, control and held-owner paths.

Original release-selection handling now clears contactMonitor as well as ownsMonitorContact, so an inactive slot cannot retain the previous monitor identity. Full ownership activation still awaits tick/release integration; this does not claim the lifecycle is complete. No builds/tests/launches/deployment.
## Original release ordering and final physics stage (2026-11-12)

Previous goal turn was no progress (instruction acknowledgement/source reread only). Continued source inspection rather than testing. Read original82451250/generated11,82450CD8/generated120,82451DA8/generated247 and82936B78/generated40.82451250 resets selection through82449ED8 BEFORE eligibility checks. Successful unparented release updates variant flags, calls8244F838 pose synchronization and8220BD58 velocity gate, conditionally enqueues8244F300, then selects8244A180 and transitions8244A2A0. This ordering matters for Normal mode's deferred-queue predicate.

The failed82451DA8 branch is not ordinary settling:82450CD8 clears matching selections across players, notifies the monitor, conditionally removes a variant entry through823C53F0 and invokes82936B78. The latter has removal/deferred-cleanup branches. Do not run successful-release finalization indiscriminately on this path.82451DA8 includes position/world and object-specific checks; exact native counterpart remains to be traced rather than approximating it with bounds alone.

Implemented FinalizeNativeSceneryRelease for the final selector/transition stage. It requires the original editor selection already reset, contact ownership cleared, native holder cleared, a surviving valid unparented scenery/crate and retained authored physics metadata. It queries native queue membership through the existing selector adapter after enqueue; it does not force authored physics with the legacy ApplyPhysics shortcut. It is intentionally not connected until the preceding local release transaction and removal branch are mapped. Full tick/release activation and export remain outstanding. No builds, tests, launches, captures or deployment.
## Local release hook integration (2026-11-12)

Previous turn was progress: final release selector/transition helper and removal-branch evidence. Read native8227FDF8/generated62 in full. Its local arm skips pose/velocity/queue work when r5 is set or parent16 is valid, but still clears the holder and sends notification823BFBD0. Ordinary local release calls82284078(0,datum),820F2DD0(datum,0), optional throw velocity,82283950 enqueue, then clears holder. Session type4 instead queues823C2B10 and must not be treated as committed local release.

Connected original selection reset and FinalizeNativeSceneryRelease to the existing native release hook, gated on full coupled-lifecycle ownership. Captures full salted player identity and held datum, resets original selection before native work, suppresses legacy magnet reevaluation only for that datum during serialization, then runs original physics selection/transition after native ownership clears. r5/parent skips bypass finalization. Throws retain stock H3 impulse handling. The coupled branch returns before legacy fixedSnap cleanup/ApplyPhysics, avoiding a second competing transition.

This branch remains inactive until the complete held tick arms ownsMonitorContact. Native removal eligibility, monitor/attachment release cleanup, full tick activation and entry/exit/save audit remain unfinished. H4 forced variant-bit release behavior is not yet mapped; do not claim complete release parity. Source edits and source inspection only; no builds/tests/launches/captures/deployment.
## Release monitor and physics boundary closure (2026-11-12)

Previous turn was progress (guarded local release hook). Inspected complete82939170/generated268: both its type-descriptor callback traversal and fallback82939248 are conditional on object parent36 != -1. It is parent detachment, not generic monitor cleanup. For the unparented monitor already required by ResolveNativeSceneryOwner, this call has no side effects. Added a pre-reset release check of the retained monitor identity, parent16 and reciprocal player380; no invented reset or detach is applied. Parent/transition workflows outside this owned path remain stock and require their separate lifecycle audit.

Read H4 release velocity/activation gate8220BD58/generated116 and native820F2DD0/generated61, plus instance helpers8222D9C0/generated192 and820F2D18/generated91. Native type mask7391 corresponds to H4 mask15071 with the established category shift. Connected runtime flag H4 bit8 maps to native bit7; release flag H4 bit10 maps to native bit9. For false, both call the instance service when connected/valid, clear the release flag, and call the corresponding object service. Instance helpers traverse real body records (H4 count52/pointer48/stride60/body52; H3 count36/pointer32/stride72/body64), gated on connected bits2 versus3. Their optional true branch uses the already established fixed-motion5 versus7 mapping. Native8227FDF8 already calls820F2DD0(false), so ordinary release retains this native service rather than replacing it with flag-only writes. No runtime parity assertion is made from this source correspondence.

Unparented monitor detachment and ordinary release activation-service mapping are now accounted for. Forced-release variant flags, local attachment iteration, deletion/exit and complete tick activation remain open. No builds, tests, launches, capture or deployment.
## Whole held-block dispatcher integration (2026-11-12)

Previous turn was progress (ordinary release service and unparented monitor boundary). Re-read the complete native82281F20..822821E8 block and suffix. The suffix does not consume skipped f29/f30/f31 arithmetic or r30 temporary state; it rebuilds its working registers before use and restores saved FP registers at return. The skipped block owns dirty byte engine58520+playerIndex: active manipulation sets it, inactive manipulation calls82284078(1,held) once and clears it.

Included the already extracted native_forge_tick.inl and connected DispatchOriginalSceneryHeldStage to RunNativeForgeTick. The dispatcher only handles exact owned original-editor slots, resolves the native monitor/control owner, runs the coupled rotation/decay/scenery/follow stage, and preserves native dirty-byte synchronization using original input.active (native764 is intentionally disabled by the input hook). Scoped SyncNativeSceneryPose prevents legacy magnet re-evaluation. After ownership is established for a frame, failure restores editor physics/state and returns handled; it never runs H3's second spring controller after a partially submitted H4 target. Unowned slots retain the extracted original native block.

OwnsMonitorContact remains unarmed: complete grab ownership/contact-input timing, forced release flags/attachments and deletion/exit/save paths still require integration. The new source include depends on the existing generated extraction; build setup must regenerate it when absent. No compile or execution performed. No builds/tests/launches/captures/deployment; interaction defects remain unverified.
Build configuration now explicitly rejects a missing native_forge_tick.inl and names its source-only extraction command, matching the existing private original-code prerequisite. Configuration was not run.

## Input lifetime across release and re-grab (2026-11-12)

Previous turn was progress (whole held-block dispatch and extraction prerequisite). Read complete82449ED8/generated101 and82368CE0/generated181. Selection reset writes only the original editor state and emits visibility/events; it does not clear player1888..1907. The producer writes active=false on ineligible/no-held/low-trigger paths but deliberately retains the four float fields. With active trigger and no rotation-available byte, it likewise retains the previous look-axis values.

Corrected SelectNativeHeldEditor(-1): removed the invented ManipulationInputState{} reset. Contact ownership/identity still clear. Added read-only input observation for an existing editor between owned holds: evaluate the original producer in private storage, retain its state, discard its movement-consumption result and then run native821F04C0 normally. Missing eligible scenery clears only active, matching82368DD8. This prevents a retained active byte from becoming stale across a release/re-grab gap. Active owned input now checks the exact player/editor/persistent-state identity and verifies the native held datum matches original selection before consuming the packet.

No host input or runtime execution was used. Full grab activation/contact timing, release exceptions and exit/save audit remain pending. No builds/tests/launches/captures/deployment. Earlier notes claiming clearing all input on release was original behavior are superseded by this source finding.
## Restoration ownership and deferred-update conflict (2026-11-12)

Previous turn was progress (input lifetime correction). Read native822843A8/generated30 and82283A30/generated86.822843A8 operates on a specific player/monitor transition; the existing host wrapper performs global RestorePhysics before entering it.82283A30 walks the deferred queue, removes out-of-world/flagged/parented entries through82283CF8, optionally resolves contact and serializes variant poses. The host post-hook currently reapplies legacy ApplyPhysics across every tracked object. That is a concrete competing override, not original H4 state-transition behavior; it must be reconciled with original mode selection/menu/deferred state before lifecycle activation. A per-player exit audit also remains necessary; do not label the existing global restore wrapper complete H4 exit parity.

Corrected the existing global RestorePhysics error/exit path to revoke all editor/contact ownership and transient controller attachments before native rebuild callbacks. Previously it could erase physicsObjects while retaining owned editor slots. The invalid/non-Forge world branch now also clears coordinate/anchor UI state. This preserves the existing global restoration scope, not a newly claimed per-player exit implementation.

Refreshed TODO's stale giant source paragraph with current connected-but-unarmed dispatcher/release status and explicit remaining activation, selection-ray, deferred/menu, exit/save and metadata work. No builds, tests, launches, captures or deployment. Full RE/implementation remains incomplete.
## Owned held-physics override separation (2026-11-12)

Previous turn was progress (restoration lifetime and deferred conflict identified). Inspected original transition callers8244F740/generated12 (deferred removal),823C6B28/generated116 (variant application),82940D68/generated18 (object flag change),824515C8/generated212 (property update),82450E10/generated43 (grab). These are event/state boundaries; they do not justify host legacy ApplyPhysics across all tracked held objects every frame.824515C8 compares selected states before transition; exact property no-change gating remains to be reconciled.8244F740 dequeues before selection/transition and has skip/deletion gates, so a blanket post-queue transition is not an equivalent substitute.

Added OwnedOriginalSceneryEditor lookup with unique ownership validation. ApplyPhysics now routes explicit changes on an owned original-held object through SelectAndTransitionNativeSceneryPhysics/TransitionHeldPhysics, preserving the original held offset compensation instead of the legacy freeze/disconnect shortcut. The deferred host post-hook skips these owned objects entirely, so it cannot reapply old physics after the original held controller. All other paths remain unchanged while the released-object queue boundary is being mapped. Ownership remains unarmed; this is not a runtime fix claim.

Remaining: exact property no-change guard, original-controlled released-object lifetime and native cleanup boundary, grab activation and other documented lifecycle gaps. No builds/tests/launches/captures/deployment.
## Property transition comparison and settling boundary (2026-11-12)

Previous turn was progress (held override separation). Read complete824515C8/generated212. It selects runtime state before committing the property, selects again afterward, and only calls8244A2A0 when those state values differ; comparing mode labels is insufficient. Factored SelectNativeSceneryPhysics out of the transition wrapper and added ChangeNativeSceneryPhysicsMode. Both native menu and queued/diagnostic property requests use it. Owned original-held properties retain the before/after selected-state comparison and invoke the original held transition only when needed. Native saved-variant bytes remain unchanged by this host-only mode property.

Read full native82283CF8/generated45 alongside H48244F740/generated12. Both dequeue, test an exclusion predicate, conditionally change physics when r5=false, synchronize, then check deletion/world bounds. The native physics point is its call8227E770(datum,false); this is the counterpart of H4 selector8244A180 plus transition8244A2A0, BEFORE synchronization and possible deletion. Therefore an outer post-return transition would be incorrectly ordered and could address a deleted object. Next integration must intercept that exact inner call for tracked original-controlled released objects and preserve every other native branch. Existing generic8227E770 hook currently runs the native call and legacy ApplyPhysics; it must be narrowed there.

No builds/tests/launches/captures/deployment. Released-object ownership persistence/settling integration and previously listed lifecycle gaps remain open.
## Released-object settling integration (2026-11-12)

Previous turn was progress (property selected-state comparison and exact settling boundary). Confirmed native generated82283CF8 sets LR82283D50 for its8227E770(datum,false) call. Added host-only originalReleasedPhysics lifetime metadata, set after successful original final release transition. It survives selection clearing and is removed with the existing salted-object/world/restoration metadata; no native cache/save flags are added.

The8227E770 hook now replaces only that exact deferred-cleanup call for surviving original-released scenery. It executes original selector/transition before native82283DF8 synchronization and deletion checks, preserves the caller's dequeue/exclusion/r5 gating, and does not perform a post-deletion transition. Explicit mode edits on those released objects use the same before/after selected-state comparison as owned holds. The host deferred post-loop skips original-released objects as well as owned holds, preventing legacy per-frame freeze/force-dynamic reapplication. Native queue pose synchronization remains responsible for released poses.

Ownership is still unarmed, so this is source integration only. Re-grab activation must establish owned editor identity before any property request on a previously original-released object; the selector explicitly rejects a held/native-editor mismatch. Forced-release flags, attachment cleanup, selection-ray wiring, per-player exit/save and metadata export remain open. No builds/tests/launches/captures/deployment.
## Phased release branch mapping (2026-11-12)

Previous turn was progress (released settling integration). Traced direct82451250 callers and82451500 callers: ordinary local/editor paths pass false; the event dispatcher can forward a payload byte. Read original8244A180/generated195 alongside82451250: variant record+62 bit7 is the phased physics bit, not an unknown unrelated release flag. Supported modes are0/0x40/0xC0. On phased release,82451250 forces its boolean true, ORs bit6 (already present for0xC0), calls8244F838(true) and8220BD58(true), and skips8244F300 enqueue before final selector/transition.

Added a scoped, exact-datum phased-release context around owned local unparented releases. Native82284078 at LR8227FEC4 receives true; native820F2DD0 at LR8227FED0 receives true; native82283950 at LR8227FFC8 is skipped. Other callers/objects remain native. Native r5 is NOT repurposed because it skips the whole placement branch, unlike the H4 boolean. Host Phased mode already includes bit6, so no H4 flag writes enter H3 variant memory. Scoped state restores on nested return/exception. Native throw handling remains unchanged per stock-H3 scope.

The event-forwarded explicit true path for non-phased objects remains to be classified; no guessed mapping is installed. Complete ownership activation, attachment cleanup, selection ray and per-player exit/save still remain. No builds/tests/launches/captures/deployment.
## Release event producer and saved-pose prerequisite (2026-11-12)

Previous turn was progress (phased release mapping). Read824500A8 event dispatch and8244CAC8/generated193 drop producer. Event4 payload is datum at0 and boolean at4. At8244CF84 onward the producer sets r28=0, then writes that byte to packet1252 with base1248 before825812D0; both manual drop and its object364 flag path retain zero. All inspected direct82451500 non-dispatch callers also pass zero. A source scan for nearby constant event4 initialization before825812D0 found this producer only; this is bounded static evidence, not proof that arbitrary indirect/network payloads cannot set true. Stock H3 networking remains outside replacement scope. No synthetic local true-action mapping is required by this producer.

Read full82451500/generated144 and8281EF50/generated19. BEFORE82451250 resets selection, byte280 can request saved-pose application: position at editor324, forward at288, up at312.8281EF50 selects a special unparented/tag-qualified path828206F0 via82821B38; otherwise it calls82932E28 with the supplied pose and zero flags. The current native release hook starts at the equivalent inner release transaction and does not yet reproduce this wrapper step. This is an explicit activation prerequisite: trace the producer/meaning of byte280 and the special tag path, then map to native pose services. Do not guess that the flag is always false or treat the saved pose as a magnet target. Direct stores to editor280 found in82449ED8 clear it on selection; the setting path may use an interior pointer and remains open.

No builds, tests, launches, captures or deployment. Source inspection yielded new release-wrapper coverage; overall lifecycle remains unfinished.
## Saved release pose producer located (2026-11-12)

Previous turn was progress (release input provenance and missing wrapper step). Located the positive saved-pose writer in82888DA0/generated13, using the editor base shifted by376: store1 at6796 equals editor280; matrix output6800 equals editor284. It requires821DEF70 to return the same player as the incoming record owner and that player's held datum to equal the updated object. It builds the saved transform through82251AE0 using incoming record vectors76/88/100. This is not a local magnet or grab setter.

Direct caller822D2868/generated267 iterates players, tests per-player mask14208, and supplies a140-byte record at14212+index*140. Further provenance of that record is needed to distinguish network/simulation/replay application; do not label it solely a network-only branch without that evidence. Preserve stock H3 state handling while tracing the counterpart.

Read82821B38/generated128 and828206F0/generated229. The special release-pose path is a tag/global fallback-definition lookup, including tag reference412 and category-dependent global references260..340. It is not inherently limited to units; the fallback branch can cover scenery.828206F0 compares requested position/orientation with current pose, calls82821790/828218D8 before native transform update when values differ, and sets runtime bit26 for selected categories. Therefore replacing8281EF50 with a generic pose setter without mapping those services would omit behavior.

The next source step is incoming per-player record provenance and native counterpart; no guessed implementation or activation was added. No tests/builds/launches/captures/deployment.
## Saved-pose transport and history provenance (2026-11-12)

Previous turn was progress (positive saved-pose writer and release transform services). Traced record production:8280E7D0/generated158 clears output mask14208, iterates16 source records of304 bytes beginning184, requires record type4 at+8, obtains140 bytes through828DC408 and remaps four references through828406E0 before setting the output player bit.828DC408/generated198 resolves source+20/source+28 through828124C0, obtains a history block at resolved+12+25760, checks its bitsets, copies140 bytes from18960+index*140, conditionally clears bit0 of the copied first byte and records consumption. It then validates/transforms via828EEC88. This is history-backed state delivery, not a pose generated by local magnets.

Transport consumers/producers are also explicit:82211FF8/generated225 reads mask14208 from a bit stream and decodes records through828EE578;822EC108/generated250 writes the presence/mask bits and encodes through828EE108;82816658/generated279 compares active records through828EE9D8.822D2868 later applies records through82888DA0. Thus copying this complete subsystem would replace native state transport/history, contrary to the stock-H3 constraint. The remaining task is determining the local scenery-relevant application boundary and retaining/mapping H3's equivalent, not importing H4 packet layouts or declaring the field irrelevant.

No source behavior changed this turn. These source findings narrow the next integration step. No tests, builds, launches, captures or deployment.
## Saved-pose integration boundary under stock-H3 scope (2026-11-12)

Previous turn was progress (history/transport record provenance). Revalidated the user scope at FULL-RE-PLAN lines5..11: scenery manipulation with all other systems stock H3; native gameplay/save/network compatibility is mandatory. H4's history-derived per-player records are not a replacement transport mandate. Retain native H3 object-state application and its release behavior instead of importing H4 stream/history records or constructing a guessed equivalent H4 record from current pose.

The bridge's private editor is initialized then updated by extracted local-manipulation functions;82888DA0 is not part of that extracted/runtime path. Source scan of the157-body extraction finds the known selection reset store at editor280 and unrelated stack/math accesses, with no direct positive store from the identified producer. This is bounded source evidence, not runtime proof. Added a release precondition rejecting unexpected nonzero editor280 before selection clears it, making this integration boundary explicit rather than silently ignoring a saved pose.

The earlier plan to port8281EF50/history application is superseded by the stock-H3 transport boundary for this local manipulation implementation. Native transport behavior remains in place; this is not a claim of H4 multiplayer parity. If a future supported local path can produce byte280, its provenance must be mapped before allowing that path. Searching for a full H4-history replacement must not block the remaining scenery lifecycle work. Continue with ownership activation, native release attachment behavior, selection-ray integration and per-player exit/save. No builds/tests/launches/captures/deployment.
## Grab ownership activation connected in source (2026-11-12)

Previous turn was progress (stock-H3 transport boundary). Connected ActivateNativeSceneryHold after successful original selection, physics transition and placement initialization in native grab. It validates salted player/contact lifetime, native held record, controlled monitor/local slot, original selected datum and surviving physics metadata before committing contactMonitor/ownsMonitorContact. No synthetic contact response or input reset is run: the current frame's unit phase has already executed; subsequent input/contact hooks own their original phases.

The complete held dispatcher now preserves original8244D514..D5A8's connected-instance eligibility as a handled skip, rather than throwing or falling back to a competing H3 controller when no connected instance exists. Legacy placement Evaluate keeps its numeric/menu path but bypasses its reconstructed magnet scene for an owned original hold. Release and settling paths already consume this ownership. This replaces earlier unarmed status in the worktree; nothing was built or installed.

Still incomplete before any test: numeric coordinate preview/accept/cancel must update persistent original-held state and coexist with its controller; marker visibility publication must use the coupled result; live selection-ray wiring, release attachment behavior, per-player exit/save and AFM3 export remain. No claim that the now-connected source is ready to run. No builds/tests/launches/captures/deployment.
### Coordinate event13 transform boundary (2026-11-12)

Source: work/h4-forge-research/generated/halo4_recomp.115.cpp, original824500A8 at824503C4..82450428. The handler validates ownership through82451908, requires selected datum equality, copies52 bytes from packet+4 to editor+84, then clamps editor+124 using variant bounds+696 through82282580. It does not reset distance, grab offset, manipulation input or magnet state.

Implemented Bridge::ApplyHeldCoordinatePose as the selected-datum-guarded transform boundary, reusing unchanged original82282580. Only editor bytes84..135 are written. Invalid requests leave the editor unchanged. Native ownership validation remains the caller's responsibility.

Integration remains incomplete: numeric preview currently writes only the native object pose. Wire the new boundary into the persistent editor, preserve cancellation semantics without rolling back unrelated tick/contact state, and reconcile the existing Precise lock with the original held movement stage. Do not invent camera-offset resets. This API has not been compiled or tested; no build, launch, capture or deployment was performed.
### Persistent coordinate preview integration (2026-11-12)

Native numeric ShowNumericPose now applies the event13 transform boundary for an owned original scenery hold before the native display transform. The original bounds-clamped result is reconciled back into CoordinateSession so the menu and later exact-pose requests retain the actual point. Explicit confirmation also applies the selected value, even without an earlier preview-change callback.

NumericPreview retains only editor bytes84..135 at preview entry. Cancel restores those52 bytes after existing selection/session checks, and restores the prior native pose and coordinate lock state. It deliberately does not restore the entire336-byte editor: input, contact, selection and magnet state can advance while a menu is open. This cancellation behavior is the existing Spartan menu contract, not a claim that H4 has an identical preview transaction.

Incomplete: Precise/Free locking in the coupled movement/controller path, live selection ray, marker visibility publication, release attachments/removal, per-player exit/save and AFM3 production. These edits were inspected as source only; no compile, tests, launches, captures or deployment. TODO stale unarmed/settling statements updated to match current source.
### Coordinate movement semantics corrected (2026-11-12)

Re-read original824500A8 event13 (generated115,824503C4..82450428) and8244A8D8 (generated194). Event13 copies the target transform and bounds-clamps its point; it installs no permanent coordinate lock.8244A8D8 continues to consume that persistent target, processed monitor movement, physics displacement and contact/bounds constraints. Rotation precision/quantization remains its distinct existing original path, not a permanent position freeze.

Removed the custom Movement: Free/Precise property row from the native menu. Physics plus six numeric position/rotation rows remain. Confirmation applies the value, commits native pose synchronization, and releases the temporary CoordinateSession preview lock. Cancellation still restores its saved pose/transform and prior session state. Owned original scenery now returns before the legacy exact-pose override as well as before legacy magnet evaluation; the original controller remains the movement authority during and after numeric previews. This supersedes prior notes proposing a permanent Precise/Free lock integration. No camera offset or placement distance reset was invented.

Source inspection completed for these edits only. No build, test, game launch, capture or deployment. The full RE/implementation goal remains incomplete; remaining integration is listed in TODO.
### Coupled marker publication and camera source correction (2026-11-12)

Connected PublishNativeHeldAnchors after coupled held/follow execution. It consumes HeldUpdateResult.visibleObjects from original visibility calls, selects the already-constructed live world markers, and publishes a value snapshot to the existing renderer. It does not run a second magnet/visibility evaluation or predict marker locations by moving them to a future snapped target.

Found an independent old camera mapping error: TLS604/0x25c is allocated with size1 in native82211500..82211534 (generated18) and accessed as a byte by82211AE0 (generated102); it cannot provide the claimed camera at+460. Native821412FC onward (generated1) resolves TLS716, local-index stride968 and position272/276/280. Native821421E4 onward (generated105) also resolves that observer result at+272. The new publisher uses this source-backed local-index camera position, with finite/address guards. The legacy single-view marker path now also reads TLS716+272. No other video diagnostics were modified.

Remaining visual integration coverage: the existing renderer has one shared snapshot, so simultaneous local views and retained visible targets outside the current scene still need explicit handling/accounting. This turn connects the ordinary owned-hold publication path; it does not establish rendered correctness or close all marker coverage. Source edits only, no builds/tests/launches/captures/deployment.
### Per-editor marker state and retained targets (2026-11-12)

Inspected original825827B0 (generated45): r3 is retained as player,82582610 independently collects the object's markers, and creation records include the player identity (stack96) and822028D8 result. Original82582950 (generated100) filters attached marker objects by player at object+280, with -1 as wildcard, before deletion. A bridge-global set therefore cannot represent independent editor lifetimes.

Moved held-path visible-object bookkeeping into HeldEditorState as host-only metadata. Selection/reset, full held/follow and standalone held-magnet paths now stage and publish that editor's own set. Original336-byte memory copies remain unchanged; no metadata enters native saves. Legacy standalone UpdateVisibility retains its separate private set. Also mapped the retained previous-target sentinel66 in ApplyHeldMagnets, matching the already-mapped full held path.

Publisher now iterates the original visible-object set and obtains each valid object's live root markers after controller submission. It no longer requires membership in this frame's nearby query; a retained target can render without being inserted into or reordering snap candidates. Invalid native datums are omitted from rendering without changing original candidate/editor state.

Remaining: the renderer still stores one camera/snapshot and captures at most one scene per frame; per-editor logical state is now separate, but simultaneous local-view rendering is not implemented. No compiled/runtime evidence: no build, test, launch, capture or deployment performed.
### Native mode-exit transaction ordering (2026-11-12)

Inspected native822843A8/generated30, its only direct caller82280610/generated19, and enclosing82280720/generated91.82280720 receives player in r4 and requested play mode1 in r5. It invokes the per-player transitions, checks the successful-player mask, commits engine halfword57748, then (play branch) releases through8227FDF8 at LR82280818 before821E4788 applies native world mode.822843A8 destroys the monitor and reassigns the player's controlled unit before returning. This matches the previously traced H4 exit -> commit -> release ordering; release cannot require the old monitor still to exist at that later call.

Removed global RestorePhysics from the start of822843A8. Owned scenery validates its owner before native teardown. Successful teardown records the exact player in transaction-scoped host state. Only the matching release at LR82280818 accepts this completed-teardown boundary instead of requiring a live old monitor; all other release checks and the normal selection-reset/physics sequence remain.

Added enclosing82280720 scope and post-transaction stock-physics restoration only for requested play with empty committed edit-player mask. Another player's remaining edit bit prevents global restoration. Native mode/world/save representations are unchanged. Full global error cleanup remains separate.

Incomplete exit coverage still includes failure paths, player deletion/lifetime changes and save cleanup. The new source has not been built or run. No tests, launches, captures or deployment.
### Departed-player lifetime invalidation (2026-11-12)

Located native821EF708 in generated78. It receives the full player datum in r3, addresses TLS96's880-byte record, performs controlled-unit/ownership removal, sets record+4 bit1 and clears bit0, stores the departure tick at+16, decrements player count, and invokes82288410 before returning. The record salt can remain unchanged after logical departure; salt equality alone is insufficient to prove a live contact/editor owner.82288410 is a game-mode dispatch boundary and its sandbox removal branch still needs tracing for held-object/deferred-physics parity.

PlayerContact now rejects departed records (flag2). Added821EF708 post-hook: capture the known contact record before the native call, then clear only the matching player contact/editor and any matching completed-exit token after native flag2 commits. Failed/no-op calls do not clear host state. Other players and native removal actions are untouched. Existing full-pool reset and successful-allocation hooks remain responsible for their distinct lifetimes.

This implements host lifetime invalidation, not complete player-removal gameplay/physics parity. The mode dispatch, object-deletion/attachment cleanup and save boundary remain pending. No builds, tests, launches, captures or deployment.
### Departure pre-cleanup dispatch (2026-11-12, source inspection only)

Native player departure 821EF708 first calls 821EF5D0 (return 821EF744), before clearing player+40. That pre-cleanup calls 8227E9F8 through the object's variant slot; for a held variant, 8227E9F8 resolves its holder via 8227E668 and invokes 8227FDF8 at return 8227EACC. This is an earlier release path than the later engine-vtable48 callback (82281230 -> 82280720). Do not insert an extra release based only on that later callback's early return after unit clearing. Remaining work: audit the pre-cleanup gates and native deletion/attachment interactions against original held ownership before declaring departure coverage complete. No build, test, launch, capture or deployment performed.

## Native holder-removal integration (2026-11-12; source only)

Previous turn was progress: departure pre-cleanup dispatch evidence changed the next action. Continued inspection confirms820B06A0 requires Forge/edit state and returns the held object from engine57752[player], using84-byte variant records.821EF5D0 invokes8227E9F8 while the monitor is still controlled;8227E9F8 calls8227FDF8 at8227EACC, then8227E710 for remaining matching holders. No extra departure release is needed for this path.

Read H482450CD8/generated120: after82451908 eligibility it iterates players, compares the selected datum, calls82449ED8(-1) for matches, then performs monitor detachment and variant/object removal. Native822802D0/generated77 instead calls8227E710 BEFORE variant flags/deletion gates, then can invoke8210C428. Native8227E710/generated69 clears all matching variant slots and emits native notifications; it does not invoke8227FDF8. This previously left the private original editor owning a deleted selection.

Added a scoped8227E710 hook: resolve the native variant datum, match owned editors by native holder slot/full player lifetime/selected datum, execute original selection reset before native holder clearing, and retain native notifications and deletion behavior. It does not invoke ordinary release physics or enqueue settling, destroy another player's editor, clear retained input, or replace native save/variant operations. Nested selection work uses a context copy. The existing departure release already resets ownership, so the later8227E710 call does not reset it twice.

Also resolved native object deletion's engine callback: guest-image vtable82040D68+164 contains82280860, called by8210C428 before marking header+2 bit0x10.82280860 has a session4-only direct holder-clear arm; that remote-session behavior is outside the local original-owned path. Generic deletion, parent attachment paths, release eligibility/variant flags and failure/save coverage remain open. Do not generalize this holder-removal implementation to complete deletion parity.

Source edit inspected only. No build, test, launch, capture or deployment.


## Live original ray-state producer (2026-11-12; source only)

Previous turn was progress: native holder-removal source integration. Re-read the full H48244C740/generated133 and H382281268/generated43, plus their enclosing callers. H4 calls its ray at8244D154 before held movement; H3 calls its ray at82281B0C. H3 stores point/normal/direction in engine arrays, not in the private original editor. H482449ED8/generated101 preserves editor44/48/52 on both select and reset. Consequently, connecting selection/grab without8244C740 leaves its grab reference zero-backed or stale.

Added an exact-caller82281268 post-hook that runs unchanged original UpdateSelectionRay for local unheld/scenery-owned editors at the corresponding prefix phase. Uses a copied guest context, validates native owner and held identity, and skips non-owned/non-scenery holds. Original query arithmetic and hit/miss writes populate editor44/48/52 before movement. Native H3 targeting return and hit/normal/direction caches remain untouched. Added the same original ray producer before selection in the committed grab hook so creation/re-grab does not depend on an earlier tick having populated the private state. No synthetic center, radius-based clearance or fixed distance is substituted.

This closes the missing persistent ray-point producer in source, not complete targeting parity: the returned H4 target is still not substituted into native target eligibility/highlight/placement-normal consumers. That remaining mapping must distinguish scenery manipulation from stock weapon/vehicle selection and account for native caches before claiming completion. Also audit the extra grab-boundary query timing against event ordering. No runtime claim about the reported camera issue is made.

Inspected edits and original instruction listings only. No build, test, launch, capture or deployment.


## Target-result routing and grab cadence (2026-11-12; source only)

Previous turn was progress: live original ray-state producer. Re-read direct grab callers824511B0/generated119 and8244E2C0/generated219. Neither refreshes8244C740 before82450E10; they consume persistent state. Removed the extra grab-boundary ray query added last turn. The corresponding native selection-prefix hook remains the sole live original ray-state producer. First-entry/event ordering still requires eventual full-sequence verification; no fabricated point or additional grab query is used.

Read full native82281268 instruction listing. Hit point is native result+8, normal+36, object identity+60. Per-player destinations are engine57880+12*i (point),58072+12*i (normal),58264+12*i (direction). Miss normal comes from8203B0E0. Added native query normal capture separate from the private H4 result layout. Original scenery targets now feed native output/boolean and matching point/normal caches at the exact82281B0C call. An original world hit or miss clears a native-only scenery target with consistent cache data. Non-scenery results keep native targeting. Native prefix still performs normal ancestry/eligibility/highlighting after return; direction remains its original monitor-view value.

This is the explicit scenery-only integration boundary: original H4 ray arithmetic/range/exclusions, native H3 geometry queries and downstream eligibility; weapon/vehicle targeting remains stock. It is not a claim of full H4 targeting across all object categories. Captured native normal/point values are checked for finite values; context/output mapping inspected in source only.

Remaining before testing: marker multiview; release eligibility/variant flags and attachment/generic deletion coverage; exit failure/save cleanup; metadata regeneration and final source coverage review. No build, test, launch, capture or deployment.


## Per-local-view marker storage (2026-11-12; source only)

Previous turn was progress: selection result/cadence integration. Current renderer inspection confirmed one pending/captured scene, one matrix/depth/viewport and one frame latch. Host publication likewise overwrote a single AnchorView. This contradicted the already traced player-filtered marker visibility creation/removal.

Replaced host snapshot with four local-view entries carrying the full player datum. Original-owned publication writes only its resolved local index. Original selection reset, release and committed player departure clear that player's anchors; global world reset still clears all. UI publishes all four entries, including empty requests to disable expired/cleared views. Added local_view to the transient SceneMarkers API and four independent D3D12SceneMarkers instances in the command processor. Each retains separate pending/captured requests, matrix/depth resources and frame latch; the CP routes updates by index and visits each at capture/draw. No guest/save layout changed. Legacy single-view publication remains index0.

NOT complete: capture still associates a request by camera-position tolerance, so coincident player cameras need an authoritative viewport-owner discriminator. Draw still projects against the full output dimensions; split-screen output rectangles/depth coordinate mapping and clipping must be implemented before testing. Material preparation currently remains per view, so shared immutable GPU material ownership should be consolidated. This is intermediate source work, not functional multiview proof.

No build, test, launch, capture or deployment. Remaining release/attachment/deletion, exit failure/save, metadata and final source review gates remain open.


## Shared marker GPU material (2026-11-12; source only)

Previous turn was progress: per-local-view snapshots and renderer state. Inspected marker shader constants, capture/draw routing and native observer accessors. Observer968-byte records establish camera position but do not yet establish the output viewport rectangle or a render-thread owner discriminator; do not infer split-screen layout from player number or camera coincidence.

Consolidated renderer material resources into a shared MaterialState: root signature, single-sample/MSAA pipelines, immutable texture upload, preparation status and one asynchronous preparation future. The first local-view renderer creates this state and the other three share it. Pending/captured markers, matrix, depth texture, retirement and frame latch remain per-view. The preparation worker owns device/material data and does not capture a renderer or CP; its future remains last inside the shared state, preserving join-before-resource-release lifetime. Only render-thread Initialize/Draw access shared material state; Set retains its separate snapshot mutex.

Source inspection only. Viewport ownership, split-screen projection/depth mapping and clipping remain incomplete; no build, test, launch, capture or deployment. Release/attachment/deletion, exit failure/save and metadata gates remain open.


## Native viewport rectangles and marker projection (2026-11-12; source only)

Previous turn was progress: shared GPU material. Traced native8221E000/generated9 ->821507E8/82150900 ->821582B0. Iterator82150900/generated2 walks active local indices through TLS216+184 and stores the actual local index at iterator12 and observer result at16. Main render setup passes render ordinal r4, view count r5, actual local index r7, observer r8 to821582B0; render ordinal must not be assumed to equal player/local index.

821582B0/generated99 invokes82158678 at return821582F4.82158678/generated88 uses signed width/height from8275A248/24C and the native layout table to write top/left/bottom/right shorts.821582B0 rebases camera48/50 to zero, retains height/width in52/54 and original left/top in64/66; camera is renderView+4. Added a post-setup hook using actual r7 to publish normalized output rectangles, guarded by valid positive dimensions and in-display bounds. No hardcoded player-count layout. UI supplies these only with fresh native rectangle evidence; invalid/stale evidence sends empty marker requests.

Renderer SceneMarkers now carries normalized output_rect. Draw projects clip coordinates into that final-output rectangle, scales marker radius to its width, clips compute origins/lower edges and existing output_size upper edges, and maps final pixels back into the captured depth viewport with scale and offset. Existing80-byte shader constants/ABI retained: shader already treats output_size as exclusive pixel bounds. Single-view rectangle remains0,0,1,1. No shader compilation occurred.

Remaining multiview gap: Capture still chooses by camera-position tolerance; it needs authoritative projection/view association to distinguish coincident or nearby cameras with different directions. Do not claim depth ownership or full split-screen correctness yet. Source edits inspected only; no build, test, launch, capture or deployment.


## Projection ownership trace (2026-11-12; source only)

Previous goal turn was no progress (instruction acknowledgement). Resumed source tracing without testing. Read the remainder of native82158CF8/generated9: its output120..183 is a distinct64-byte projection matrix, following the52-byte transform at0 and inverse-side record at52. The native render setup stores this projection at renderView+260 and copies its192-byte record to renderView+468. Do not compare that projection-only block directly with GPU world-to-clip c0..c3.

Read complete8217BDE8/generated36: it obtains the active view through global828E6738 (lis -32114 / offset26424), copies64 bytes from view+260, then processes the copy through8217BF60 and8217C058. Its plane transform uses view+140. This establishes a concrete consumer of both blocks; it is not itself proof of GPU constant upload or view ownership. Read complete82162590/generated62: it composes the52-byte transform supplied in r3 with the64-byte matrix in r4 into64 bytes in r5, including the translation contribution. Its callers82175D18/generated26 and82474990/generated62 are next trace points for composition and upload; active-view global writers also need association with local-view identity.

No renderer matching changes were made on incomplete evidence. Camera-position-only capture remains an open defect for nearby/coincident player views. No builds, tests, launches, captures, exports or deployment.


## Native world-to-clip constant producer (2026-11-12; source only)

Previous turn was progress (projection consumer/composition trace). Read complete82162398/generated82 and8215DA40/generated30:82162398 takes camera in r3 and projection record in r4, calls82162590(record,record+120,stack144), then8215DA40(global828E66F0, index0, stack144, count4, dirty-bit63).8215DA40 copies vectors to state+(index+120)*16, so the composed matrix occupies state1920..1983.82162398 additionally writes camera forward/basis vectors at1984..2031 and camera position at2032..2047 (constant7), and a second position copy at6272..6287. This identifies a concrete post-composition snapshot location without guessing multiplication conventions or comparing projection-only bytes.

Enumerated every direct82162398 caller:82473988/generated15,821745B0/generated30,8247D458/generated31,82162940/generated43,821807A8/generated47,82460220 and82463BD8/generated64. Read complete8247D458:camera=view+4,projection=view+140, then local index from view10688 goes to82162680.821807A8 is a separate adjusted-camera path using view+332 and projection+468; it must not overwrite the main-scene marker association merely because camera position matches.82175D18/generated26 independently composes a temporary projection for auxiliary calculations, not the main constant submission; this is no longer the next upload trace target.

Remaining before capture implementation: trace shader-state flush from state1920 to c0..c3 and associate main-view submission with GPU command ordering. A latest-only UI snapshot can be newer than the GPU draw; an exact matrix check without preserving submission correspondence would hide moving markers. Identical-camera local views still require ownership beyond a matrix equality test. No such incomplete gate was added. No builds/tests/launches/captures/deployment.


## Camera constants reach the command stream (2026-11-12; source only)

Previous turn was progress (camera constant producer). Traced native8215EB28/generated77: before emitting its draw packet it reads state0 dirty mask, passes state1920 in r6 and register base16384/0x4000 in r5 to8215EF10, then clears state0. Read complete8215EF10/generated109: dirty-mask runs select64-byte groups, it emits type0 register headers and copies the corresponding vectors directly into the command buffer, advancing state48. Its space-exhaustion arm delegates to8218A738. Thus82162398 ->8215DA40 ->state1920 ->8215EB28 ->8215EF10 ->GPU0x4000 proves the main matrix path without a guessed transpose.

Read SDK CommandProcessor::WorkerThreadMain and CallInThread: queued host callbacks drain before an arbitrary primary-buffer execution batch, not at a particular guest draw. CallInThread cannot by itself bind a marker snapshot to a native view submission. Native marker visibility and GPU execution need stream-ordered association; latest-only UI publication is insufficient for moving cameras and coincident local views. Existing PM4_NOP simply skips its payload. A host-only ordered metadata packet is a possible adapter, but has not been implemented or declared correct. Preserve native gameplay/save records.

Read complete82157688/generated52: command-space handling may submit/rebuild command state via82157788/82157948/82157CD0 and82158040, then returns state48. Do not append into stale command pointers across this call. Remaining work is an explicit ordered marker association with bounded snapshot lifetime, including view changes/restoration and disabled/empty markers; continue actual implementation before any tests. No builds, tests, launches, captures or deployment.


## Ordered native marker submission implemented (2026-11-12; unbuilt/untested)

Previous turn was progress (constant flush trace). Added a host-only metadata record carried by a four-word PM4_NOP payload: signature SCMK, version1,64-bit snapshot token. CommandProcessor owns immutable per-submission SceneMarkers snapshots under a mutex; token consumption occurs in ExecutePacketType3_NOP, not CallInThread/UI dispatch. Outstanding storage is bounded at256 snapshots/64 points each and never evicts a snapshot still referenced by a queued packet; exhaustion emits disabled token0. Shutdown clears abandoned snapshots without resetting token identity. Ordinary NOP payloads remain ignored. This is a rendering adapter, not imported H4 gameplay or save data.

Native82162398 post-hook now snapshots the completed camera constants at state1920/camera2032 and matches camera/projection pointers to a render view registered by821582B0 with its actual local index. It appends metadata to the same native command buffer, honoring state48 last-written semantics and state52 limit; on insufficient space it calls original82157688 using a copied context and rereads pointers. Auxiliary camera/projection pairs emit token0, disabling capture until a registered main-view submission. Main-view snapshots include native rectangle, current original anchor visibility, material and exact composed matrix. Removed UI-thread snapshot publication.

D3D12 activation sets exactly one capture view. All four completed view captures still draw in their own output rectangles. Capture also requires exact c0..c3 equality with the ordered snapshot, preventing auxiliary projection depth from matching only by position. Two coincident local cameras no longer share eligibility solely because their position/matrix matches: the consumed token carries the actual local view. Source reads inspected after edits, with no execution checks.

Still open before declaring this integration finished: audit native submission failure/abandonment and buffer-replay lifetime, scene-depth capture timing/completeness and view restoration call paths. The transport and producer are connected in source, but no visual/functional correctness is claimed. Remaining release attachment/removal, exit failure/deletion/save and AFM3 regeneration gates also remain. No builds, tests, launches, captures or deployment.


## Scene-depth sequence capture correction (2026-11-12; unbuilt/untested)

Previous turn was progress (ordered marker transport). Source inspection found capture was placed inside EndOcclusionDraw after its invalid-query early return, and Capture latched the first eligible draw per frame. This made markers depend on an unrelated active occlusion query and could retain depth before later geometry was drawn. Removed that coupling. Both indexed/nonindexed emitted draws now reach one Observe call after emission, independently of query status. Observe retains the matching native camera/depth metadata and source-resource identity without copying a depth texture per draw.

Finish copies accumulated depth at ordered view activation, before resolve/swap, or before the next draw changes camera matrix/depth target/surface description. The next-draw check precedes render-target-cache Update. Capture permits later completed segments to replace an earlier capture in the same frame. It requires the observed resource still be the cache current depth resource and the same frame; mismatches are discarded instead of copying another pass. Native scene identity now replaces the old320x200 heuristic; small valid player viewports are accepted. Removed wall-clock expiry during GPU consumption: an ordered in-flight snapshot must not expire solely because a slow frame exceeds250ms. Native producer freshness guards remain.

FinishSceneMarkers opens a submission only when an observed resource exists, including when an ordered camera packet arrives after a previous submission closed. Source edits reviewed, not compiled or run. First edit script stopped on an unmatched IssueSwap anchor before writing any files; corrected edit then completed. Remaining audit includes target changes not represented by camera/depth/surface registers, tiled depth completeness, buffer abandonment/replay and scene restoration. No build/test/launch/capture/deployment.


## Depth-binding transitions and reset lifetime (2026-11-12; unbuilt/untested)

Previous turn was progress (sequence capture). Read RenderTargetCache::Update in src/graphics/pipeline/render_target/cache.cpp: normalized depth/stencil enable and color binding/base conflicts affect the accumulated depth binding independently of RB_DEPTH_INFO. The base update computes ownership/transfers and replaces bindings; D3D12 Update executes transfers/resolve-clears afterwards. Added a D3D12 transition boundary that retains the previous depth target through a scoped capture-source override and finishes observed markers before GPU transfers/clears whenever the depth binding changes, depth transfers are pending, or base update fails. The override restores automatically and CopySceneDepth uses that target tracked resource state. This closes the identified gap in the register-only precheck without copying depth on every draw.

Added ResetAfterGpuIdle to discard marker observations, captured requests, depth allocations and retired resources, disable views and reset frame identities. Called after the existing shutdown wait and within the successful GPU-idle cache-clear branch, before target-cache destruction. Shared immutable material resources remain reusable. InitializeRingBuffer now clears outstanding host submission snapshots without reusing token IDs, preventing a replaced ring from retaining abandoned snapshots indefinitely. Removed the unused consumer wall-clock timestamp.

Inspected edited source; no execution checks. Remaining source audit: per-buffer abandonment/replay beyond ring reset, tiled-depth completeness and camera restoration. Scenery release/deletion/save/AFM3 gates remain separately open. No builds, tests, launches, captures or deployment.


## Monitor-exit validation failure containment (2026-11-12; unbuilt/untested)

Previous turn was progress (renderer transition/reset work). Reviewed822843A8 wrapper and ResolveNativeSceneryOwner: ownership validation can throw before the native monitor teardown, and PhysicsWorld may invalidate private editors after a world change. The wrapper previously let that exception escape across the native mode transaction. Added a copied validation context and exception containment: record failure, do not grant the completed-monitor exception to an invalid owner, and always execute original822843A8. Only when native teardown reports success does the rejected-player path discard that matching private editor and clear its markers. Native failed teardown preserves state; native release/serialization is not replaced. This is host failure containment, not a claim of original-code parity for a failed adapter.

Re-read complete native82280860/generated85 (engine object-removal callback): it calls8227E668 to find the holder, directly clears the held slot only when game+20==4, clears matching target references at engine58456+4*i for16 players, then calls82283CF8(datum,-1,1) when game+20!=4. Thus ordinary local generic deletion is not equivalent to the already hooked8227E710 variant-removal path. No guessed extra holder clear was added. H4 counterpart/caller coverage and native attachment/deletion lifetime remain to trace. No builds, tests, launches, captures or deployment.


## Original generic object-deletion callback resolved (2026-11-12; source only)

Previous turn was progress (exit containment). Traced H4 Forge delete82450CD8 ->82936B78.82936B78/generated40 can defer destruction using header bit1024; immediate path uses827FC530 and82936808. Read82936808/generated155,82936780/generated134,82943860/generated11,827FC530/generated104,82937610/generated5 and82279BF0/generated66 to distinguish object deactivation/network/auxiliary bookkeeping from actual editor notification.

The decisive path is82936498/generated117: after deactivation and recursive child handling it invokes16 callbacks from original image table83368C30. Read that table directly from h4-image.bin (base82000000); callback index5 is8242C128.8242C128/generated198 selects an engine instance through835718E0 and invokes vtable+208. Engine index1 points to instance833FE5C8, vtable821314D8, method8244C000. This resolves the Forge generic-deletion counterpart from original data, not an address-name guess.

Read complete8244C000/generated59: for each live salted player, clear editor24 when it matches the deleted datum; if editor0 matches, call original82449ED8(-1) and822FF770 notification; if editor4 matches, call8244A118(-1). Then call8244F740(datum,-1,1) outside its session4 branch. This supplies concrete cleanup semantics missing from native82280860: private selection and visible-target state must both be reset on generic deletion, not only on variant removal. Next implementation needs the private-editor8244A118 boundary alongside existing SelectNativeHeldEditor, preserving the native callback and its stock held-slot/session behavior. No builds/tests/launches/captures/deployment.


## Generic object-deletion cleanup connected (2026-11-12; unbuilt/untested)

Implemented the private per-editor branch sequence recovered from8244C000: clear matching editor24, reset matching selection through unchanged82449ED8, then reset any remaining matching visible target through unchanged8244A118. Native82280860 now supplies this cleanup for existing private editors before its unchanged H3 body. Salted player lifetime is checked; selection removal revokes private monitor ownership and coordinate/physics sessions. Marker records carry their object datum so visibility removal preserves surviving selected/target markers.

The adapter deliberately retains native H3 engine notification, holder/session and deferred-removal behavior; it does not emit H4822FF770 or substitute H4 transport. Exception handling records failure and clears that player's markers while still calling native82280860. This is source implementation only, not proof of working deletion or multiplayer parity. Attachment/save paths and the other outstanding integration gates remain open. No builds, tests, launches, captures, exports or deployment.

## Attached-object release coverage gap (2026-11-12; source only)

Previous goal turn was progress: generic deletion implementation changed authoritative source. This turn read complete original82451250/generated11 and82939170/generated268, native8227FDF8/generated62, original selector8244A180/generated195, transition8244A2A0/generated58 and eligibility82451DA8/generated247. In82451250, object+36 parent != -1 branches to824513A4: it bypasses the variant-flag/placement/queue block but STILL calls8244A180 then8244A2A0. The monitor detachment follows that transition. Neither the original selector nor transition has a parent early return. By contrast, the current adapter gates FinalizeNativeSceneryRelease on originalPlacementRelease, and both finalization and RebuildSceneryPhysics require an unparented object. This is an identified coverage gap, not parity established by leaving native release intact.

Native8227FDF8 treats r5!=0 or object+16 parent != -1 as a jump to8227FFC8 (holder clear); it bypasses the enqueue call whose return address is8227FFC8. Therefore that return-address hook must not be confused with a branch executing the enqueue. Keep ownership-only r5 removal separate from a parented release; removing all guards together would be unjustified.

Read complete original create82388C68/generated17 and rebuild82388A08/generated152 plus native821CBB88/generated108 and821CB8D8/generated12. Their top-level entry points do not reject parented objects. Original rebuild additionally conditionally traverses child/sibling links after rebuilding; the native wrapper does not share that traversal. Before widening the adapter, trace original82388890/82388808/82388700 and native82122338/821CB7D8/821CB6D8 for parent/body ownership and construction behavior, and identify the actual parent-attachment producer that releases an original-owned scenery object. No guessed parent rebuild or additional detach has been installed.

Also classified82451DA8 as more than the already mapped geometry predicate: after82451BA8 it checks a point/world predicate,8228F4D0, and object extension types13/15/16 with further conditions. The latter type-dependent branches must be distinguished from supported scenery before claiming complete release eligibility. This remains an explicit source gate. No builds, tests, launches, captures, exports or deployment.

## Attached release final transition connected (2026-11-12; unbuilt/untested)

Previous turn was progress: identified the parented-release branch mismatch. Read complete H482388890/generated56,82388808/generated252,82388700/generated26,823885D0/generated66 and H382122338/generated35,821CB7D8/generated63,821CB6D8/generated75,821CB850/generated31,821CB5B8/generated99. Creation in both engines traverses parent links before root preparation (H4823885D0 ->8238A7F8; H3821CB5B8 ->821CDFB0), then allocates the object's physics instance. H482388808 and H3821CB850 recursively visit children lacking instances with the corresponding child/sibling fields (32/28 versus12/8). The scoped keyframed-motion override already matches the exact requested datum, so descendant creation does not accidentally inherit its override.

Changed native finalization to run after a committed original-owned release whenever r5 does not request ownership-only cleanup, including attached objects. Placement/queue overrides remain limited to unparented releases. Removed parent rejection from the released transition/body-rebuild boundary; held-editor transitions still require unparented scenery. Native create/rebuild and parent-aware physics-point services remain responsible for body behavior. This connects the observed824513A4 selector/transition branch without detaching the scenery or changing H3 parent/save representation.

Read all four generated direct8227E9F8 callers:821E1908 (variant removal),821DFCC8 (variant object callback),823C65E0 (decoded event dispatch),821EF5D0 (player cleanup). The first three pass r5=0; player cleanup computes its skip flag from native state.8227E9F8 forwards r5 and later clears remaining holder state. This does not yet establish the indirect parent-attachment producer: that callback path, original conditional descendant-rebuild differences and release eligibility remain open for source coverage. No claim of complete attachment parity or verified runtime behavior. No builds, tests, launches, captures, exports or deployment.

## Attachment transaction identified; no automatic release inferred (2026-11-12)

Previous turn was progress (attached-release final transition implementation). Re-read native8210C428/generated90 and822802D0/generated77:8210C428 invokes engine vtable164 then821DFCC8 before setting the deletion header bit.822802D0 clears holder state, removes the variant and deletes its object. These are deletion paths, not evidence of an attachment notification.

Located and read complete H4 attachment82938A48/generated218 plus wrapper82938980/generated80, orientation helper82938770/generated61, detach unlink82938E60/generated191 and detach transaction82939248/generated225. Attachment writes parent36/node57 and links sibling28/child32; transforms the pose into parent-node coordinates; performs existing physics/connectivity and node updates. The wrapper dispatches type-specific attach callbacks at service+104 before the fallback. Detachment unlinks that chain, restores world pose (with its root-motion compensation branch), clears attachment-related flags, conditionally rebuilds, and transfers velocity. No direct Forge release call appears in the inspected attachment transaction.

Matched native82331260/generated44 by its actual writes: parent16/node20, sibling8/child12, parent-node pose conversion, native physics/connectivity updates. Read complete body. Native wrapper82331198/generated37 dispatches type-specific attach callbacks; direct fallback callers also include82330D88/generated66. H4 fallback callers are82938980,82938380 and825B86D0. Caller enumeration is static evidence, not an exhaustive indirect-call proof. Do not synthesize a release-on-attach hook: neither inspected fallback transaction requests that behavior.

This changes the next source task: inspect the parented-held tick branch and type-specific callbacks, rather than assume attachment must immediately clear ownership. The current original-owned resolver rejects parented scenery, while original8244D0E0 has a parent-dependent movement gate; that difference needs accounting for. The connected final release transition remains useful when release actually occurs but does not settle parented-held lifecycle behavior. No builds/tests/launches/captures/exports/deployment.

## Parented-held skip and origin cache connected (2026-11-12; unbuilt/untested)

Previous turn was progress (actual attachment transaction mapping). Read complete8244D0E0/generated196. The local held branch at8244D514..D5A8 permits movement/follow only for an unparented object with a connected physics instance. Regardless of whether that block runs,8244D628 queries8225EA20 into editor+8 when selection remains valid. It does not reset selection or report an ownership failure merely because the held object is attached. The existing adapter instead rejected attachment in ResolveNativeSceneryOwner before reaching its movement skip, and omitted the editor+8 refresh on both skipped and normal coupled updates.

Added an explicit allowAttached owner-validation argument, enabled only for held-tick dispatch and mode-exit lifetime validation. Initial activation/coupled movement retain their unparented requirement. Dispatch checks the private selection identity even on skipped frames, executes movement/follow only when eligible, then refreshes exactly three editor+8 floats through the existing native parent-aware820A9E58 service. It returns handled on the skipped path, retains ownership/input/contact state, and does not fall back to H3's spring controller or emit a synthetic detach. Native dirty-pose bookkeeping remains limited to the coupled path.

Inspected the generated native dispatch location:82281EDC performs local-player predicate821F0688 before the injected82281F20 block. At82281F08, session!=4 goes directly to82281F20; only session4 additionally rejects parented objects. Thus this local supported path reaches the adapter for an attached object; no extraction-boundary relocation is needed. No regenerated extraction, build, test, launch, capture, export or deployment. Type-specific attachment callbacks, descendant rebuild differences and remaining source gates are not declared complete.

## Scenery attachment callback tables resolved (2026-11-12; source only)

Previous turn was progress (parented-held skip/origin-cache implementation). Read complete native82331198/generated37. Its service chain starts at descriptor172 and selects the first nonzero attach pointer at service108. H482938980 uses descriptor184 and service104. Read those chains directly as big-endian words from the original mapped images, base82000000:

| Image/type | Type table | Descriptor | Service chain | Attach pointers |
| --- | --- | --- | --- | --- |
| H4 scenery6 |8336AD78|8336A078|83369778,8336A078,0|0,0|
| H4 crate11 |8336AD78|8336A278|83369778,8336A278,0|0,0|
| H3 scenery6 |8275E2F4|8275D938|8275D048,8275D938,0|0,0|
| H3 crate10 |8275E2F4|8275DB28|8275D048,8275DB28,0|0,0|

Sources:work/h4-forge-research/h4-image.bin and work/advanced-forge/guest-image.bin. Thus the supported scenery/crate types have no specialized attachment callback in these original images; they reach the shared fallback already mapped. No additional attach-specific Forge ownership hook is indicated. H4 service108 detach pointers are also zero in both chains; native adjacent entries were read but native detach dispatch offset has not been independently established here, so no native detach-callback conclusion is claimed.

This closes the named scenery-specific attachment-callback lookup, not all attachment/physics coverage. Conditional descendant rebuild and native save/property persistence remain explicit gaps. Existing runtime mode selections live in PhysicsObject.mode, and RestorePhysics clears them; current code does not establish saved physics-mode equivalence. Retain the native format and trace its writer/property meanings before claiming save/load completion. No build, test, launch, capture, export or deployment.

## Native save writer and live property application traced (2026-11-12; source only)

Previous turn was progress (scenery callback-table evidence). Read complete H3 writer821DFDB0/generated72 and decoder821E01E0/generated25. Writer iterates declared84-byte object records, writes occupied/flags/quota, optional64-bit parent identifier, bounded position and orientation, then stock24-byte properties. Runtime datum is not a physics-mode persistence mechanism. Object record+0 flags are written16 bits; record+62 placement flags are written8 bits. Preserving bits in the stream does not prove stock H3 gives them a useful meaning.

Read native property transaction8227F0B8/generated7: copies24 property bytes into a native record, commits via821E25B0, applies live fields via821E4338, then issues native update notification.821E25B0/generated93 copies84 bytes, marks edited, handles a deleted runtime datum and calls821E1B90. Read complete821E4338/generated97: placement byte+2 bits0/1 map into multiplayer extension flags6/7, bits2/3 select symmetry; it writes team/shared storage/spawn/boundary fields and a weapon-specific ammo branch. It does not interpret property-byte bits6/7 as H4 Fixed/Phased or rebuild scenery physics. The local TagTool MapVariant.cs schema independently labels only UniqueSpawn, NotInitiallyPlaced, Symmetric and Asymmetric for that byte. Therefore copying H4 mode0x40/0xC0 into native placement flags would serialize bytes without implementing the required stock behavior, and is not a valid mapping.

Current ChangeNativeSceneryPhysicsMode stores its result in PhysicsObject.mode; RestorePhysics clears those runtime entries. Save/load physics-mode support is consequently incomplete. No additional field/sidecar/altered save format was introduced. Next source boundary: native record flags and object-creation/load consumer (821E1B90 and its creation path), to distinguish authored static physics and runtime suspension from a persistent mode. No build, tests, game execution, export or deployment.

## Native re-creation and suspension flags mapped (2026-11-12; source only)

Previous turn was progress (writer/live property tracing). Read821E1B90/generated87: this is existing-object pose synchronization, not object creation. It resolves variant pose via821E1D78, accounts for existing object orientation and submits8232E8B8. Read821E0DE0/generated63: quota recount/clamp, also not creation. Corrected the next-action assumption rather than treating those names as evidence.

Located creation through direct821E4338 callers. Read821E2898/generated55 in full: chooses a free/available record and quota, builds a placement descriptor through8232ED68 or scenario-placement82346F50, sets pose/basis, calls8232F3D8 to create, associates the variant using821DE2A8, then applies/reads multiplayer properties using821E4338/821E44F8 or821E42D8. Read complete821E44F8/generated42: clears/reconstructs the24-byte stock properties from the runtime multiplayer extension, including only placement bits0..3; it does not capture runtime frozen/force-dynamic/keyframed mode. Read82284A10/generated24 and823C05A0/generated56 post-creation routines; no physics-mode decode was identified in these bodies. Their downstream networking/monitoring services remain native.

Read complete821E4028/generated22, the record-driven re-creation path. Record+0 bit6 is set when an engine-filtered object is removed/suspended. On re-creation it explicitly clears bits0 and6 with mask0xFFBE before calling821E2898. That bit is not a persistent Fixed-mode choice and must not be repurposed. Parent-relative/attached handling uses bits8/9 and native parent identity; no extra H4 field is inserted. Also read821E4D28/generated32 update application and821E42D8/generated39 property forwarding.

Evidence now rejects both proposed shortcuts: H4 physics bits in the property byte, and native runtime-suspension bit6 as Fixed. Existing runtime-only mode storage remains an unresolved stock-save compatibility gap. Complete the remaining record creation/physics flag consumers before a final compatibility decision; no claim that all native flags have been exhaustively excluded. No build, tests, execution, captures, exports or deployment.


## Native variant association and attachment consumers (2026-11-12; source only)

Read complete821DE2A8/generated94,821E14A8/generated82,821E1050/generated45 and821DF580/generated5. Association selects scenario or non-scenario records, stores the runtime datum and slot, and applies/readbacks native properties. Non-scenario association clears runtime suspension bit6. Scenario association uses (flags & 0xFF96) | 9 before its conditional edited bit. Neither inspected association body transfers an H4 physics mode.

821DF580 resolves the saved parent identifier through82335E78, transforms relative position/basis by the parent's node transform, and applies the native pose. Record bit9 then invokes82331198 to attach the child and marks native attachment state. This is existing native parent-relative/attached persistence, not an interchangeable Fixed/Phased encoding.

Read complete821DE458/generated95, called after association. It is gated by game-engine type5 and explicitly exits for runtime object type6 (scenery). Its remaining branch manages a secondary runtime object in the record, using native deletion/creation and association services. It supplies no scenery-mode restoration path. This closes that particular downstream association candidate, not every possible native consumer.

Stock-compatible physics-mode persistence remains unresolved; no spare flag, sidecar or format change was introduced. The user's gate remains binding: RE and implementation must finish before testing. No builds, tests, launches, captures, exports or deployment in this pass.


## Descendant rebuild is constraint-dependent (2026-11-12; source only)

Read complete H482388A08/generated152 and H3821CB8D8/generated12. H4 snapshots instance+16 bits10/12 before rebuilding; only that pre-existing dependency permits traversal of object child32/sibling28. It rebuilds an instantiated child when object+256 low-word bit29 is set or child instance+16 bit9/11 is set. Child calls pass rebuild flags0. This is not an unconditional recursive rebuild of every attached object. H3's native rebuild has no matching traversal.

Located concrete producers and read complete824A4600/generated240 and8249BE20/generated178.824A4600 sets parent instance bit10 and child bit9 only when a constraint endpoint is successfully bound to an attached parent's physics body.8249BE20 sets parent bit12/child bit11 after creating a parent/child constraint stored at child instance+144. Therefore copying these bits into native H3 instances or rebuilding all children would not reproduce their meaning.

Mapped the constraint-frame counterpart by callers: H4824A2B38 ->824A3E90 ->824A4600 versus H382269088 ->82269D48 ->8226A648. Read complete8226A648/generated102. Its missing-second-body branch binds to the native world body; it lacks H4's added parent-body endpoint branch and dependency-bit writes. Read complete motion selectors824A1610/generated287 and82267A88/generated79 as well; H4 also has parent-motion inheritance that must not be inferred from H3's instance bit positions. Constraint service replacement is not authorized by the stock H3/360 gameplay requirement.

This resolves the origin of the dependency flags and rejects broad child rebuilding as a fix. Remaining decision boundary: identify which parent-dependent behavior is reachable through the supported scenery manipulation workflow, versus authored H4-only constraint behavior. Preserve native H3 constraint construction while establishing that boundary. No runtime change, build, test, launch, capture, export or deployment in this pass.


## Marker failure/replay invalidation connected (2026-11-12; unbuilt/untested)

Previous pass progressed by identifying parent/child constraint dependency producers. This pass inspected the current renderer source. ExecutePrimaryBuffer, ExecuteIndirectBuffer and direct ExecutePacket each abandon the remaining reader after ExecutePacket returns false; none previously invalidated queued or captured marker metadata. A consumed/cancelled/missing token produced an invalid local view, but ActivateSceneMarkers only stopped observation, leaving prior same-frame captured views eligible for Draw.

Added AbandonSceneMarkerSubmissions at all three parse-failure boundaries: clear queued snapshots under their mutex, then invoke GPU-thread logical invalidation outside that lock. Tokens remain monotonic. D3D12 invalidation disables every view and clears pending/captured metadata and frame identities while retaining depth, retired and material resources for existing GPU work. It does not call ResetAfterGpuIdle. Missing/replayed/disabled tokens now take this path; invalid data for a known local view invalidates that view. A successfully replaced same-view snapshot also invalidates its previous capture, so no-world-draw frames cannot display stale markers. Other valid local-view captures survive ordinary view switching.

Read the edited dispatch/source boundaries after writing; no compiled or runtime claim. Remaining source gates include producer-side buffers abandoned before execution, tiled-depth completeness and view restoration. Parse-failure handling does not establish those cases. No build, tests, launch, capture, export or deployment.


## Restored/ring-replaced command stream marker lifetime (2026-11-12; unbuilt/untested)

Inspected CommandProcessor Save/Restore, InitializeRingBuffer and the native82162398 metadata producer. Restore previously reloaded guest stream positions without discarding host marker snapshots; ring initialization cleared only queued snapshots. Neither invalidated backend captures. Added a pending atomic logical reset, set while clearing the queue at both boundaries and consumed on the GPU thread before the next ExecutePacket. This preserves thread ownership of backend metadata, avoids GPU-resource release without idle, and leaves token numbering monotonic. No marker data is added to native save state.

The native producer allocates capacity before queueing a snapshot, then writes the five-word packet and commits state48. Thus ordinary allocator rejection does not itself queue a snapshot. Read complete82157688/generated52: it obtains/submits buffer data through82157788/82157948/82157CD0 and calls82158040; its early exits can leave capacity unchanged, which the producer rechecks. Later abandonment of an already written buffer remains distinct and requires tracing that submission/reuse boundary. Queue capacity remains bounded, not proof of eventual reclamation.

Previous pass made implementation progress on failed-buffer/replay cleanup. This pass adds state-restore and ring-replacement cleanup; the broader source gates remain open. No build, tests, launch, captures, exports or deployment.


## Marker render-state source audit and physics decision (2026-11-12)

Read D3D12SceneMarkers Observe/Finish/Capture/Draw, the IssueSwap marker insertion and both FXAA/no-FXAA continuations, SetExternalPipeline, and the render-target capture override. Draw uses compute roots/descriptors/pipeline and UAV barriers; it does not change graphics root, viewport, scissor or render-target bindings. SetExternalPipeline invalidates the cached guest pipeline; the guest draw path selects its pipeline again. FXAA explicitly rebinds its compute root, constants, descriptor tables and pipeline. Both output continuations restore the output resource state; CopySceneDepth restores the source's previous tracked state. PreviousDepthScope restores the temporary source pointer. This closes the named render-state-restoration source inspection, not runtime verification.

Tiled-depth coverage remains unresolved: Capture rejects a viewport extending beyond the source allocation. This avoids sampling missing rows but is not implementation of complete tiled visibility. Also retain the producer-side abandoned-buffer reclamation question from the previous entry.

Asked the user to choose editing-only Fixed/Phased (restore stock physics on leaving Forge; save position/rotation normally) or omit those controls, because the traced native save/load path does not preserve H4 mode selection. No approval inferred and no dependent mode/persistence changes made. Stock H3/360 compatibility remains mandatory. No builds/tests/launches/captures/exports/deployment.


## Native allocation-failure producer boundary connected (2026-11-12; unbuilt/untested)

Read complete82157788/generated46,82157948/generated30,82157CD0/generated104 and82158040/generated22.82157948 returns zero when state10941 bit5 is already set and sets it after a failed allocation.82158040 skips its submission branches when this bit is set. Normal submission may instead append indirect-buffer descriptors to native lists; that is not abandonment and must not be cancelled simply because it was not immediately submitted to the primary ring.

The82162398 marker producer now rejects the native failed-stream state both before collecting/queueing a snapshot and after the allocator may have changed state. It clears queued host metadata through a new producer-safe DiscardQueuedSceneMarkers boundary, which requests GPU-thread logical invalidation through the existing atomic reset. Expanded the native state pointer range guard to cover the referenced stream fields. It does not drive the GPU/backend from the producer thread and does not modify native submission flags or commands.

This closes the explicit native allocation-failure case. Successful recorded command lists later discarded/reused remain a separate lifetime case; do not call all producer-side reclamation complete. No builds, tests, launches, captures, exports or deployment. Physics-mode user decision remains pending.


## Release validation versus native deferred cleanup (2026-11-12; source only)

Read complete8227FDF8/generated62,82284078/generated20,822837C8/generated104 and82283CF8/generated45. Native release serializes the pose via82284078 ->822837C8 ->821E25B0, unfreezes/applies throw motion, enqueues82283950, and clears holder state. The pose synchronization routine does not perform H4's82451DA8 validation. Native deferred cleanup82283CF8 later checks82100108 and821AA050 and removes the variant/deletes the object on its invalid-placement branch. Therefore retaining native release alone does not establish original immediate validation ordering.

Read82286248/generated33: its exclusion is object types2/3 with runtime353 nonzero; supported scenery6/crate10 do not enter it. Read82100108/generated41: gated by native object172 bit7 and no parent, it performs sphere/geometry queries against loaded structures. This is distinct from the already mapped82451BA8 vertex predicate; do not substitute it merely because both concern geometry.

Read H482328310/generated211 and native821AA050/generated42: both OR configured scenario trigger-volume containment and return true for an empty volume list. H4 fields1312/1316 use4-byte entries and8224E6F8; native1176/1180 use2-byte entries and820BC010. H4's caller supplies r4=0, so its additional scenario-flag override does not apply here. This establishes the native counterpart for the release point/volume predicate.

Read H48228F4D0/generated51: valid object returns low-word object256 bit10 (true for missing object). It is the previously mapped object flag, not another world query. In82451DA8 it gates the extra multiplayer-extension checks; those types13/15/16 still require scope classification. Remaining release source task is now explicit: connect or intentionally retain the supported-scenery validation ordering at the native boundary, preserving native deletion/variant semantics. No new eligibility rule or deletion hook was guessed. No builds, tests, launches, captures, exports or deployment.


## Release special-type classification (2026-11-12; source only)

Inspected local Gen4 Object.MultiplayerObjectType in work/stock-h3-audit/TagTool/TagTool/Tags/Definitions/Gen4/Object.cs. Its explicit sequence identifies13 as Teleporter2way,15 as TeleporterReceiver and16 as PlayerSpawnLocation. These are multiplayer object types, not scenery object-header type6; do not conflate the two enums or silently renumber around Powerup. This schema attribution is corroborating evidence, not by itself an executable enum proof.

Located the actual runtime field producer and read complete823C6B28/generated116: object extension offset is object486; the function copies saved variant properties byte9 to extension22, the exact byte consumed by82451DA8. This also invokes the original physics selector/transition before applying the multiplayer fields, confirming that property application participates in mode restoration in H4. H3's earlier mapped property consumer lacks that transition.

For the controlling scope, retain native H3 teleporter/spawn gameplay and its validity rules; do not import H4's82484EC8/8243BF98 gameplay validation as a prerequisite to ordinary scenery manipulation. Ordinary scenery still requires the geometry/volume release-order decision already identified. No guessed subtype filtering or production release mutation was added in this pass. No builds, tests, launches, captures, exports or deployment.


## Ordinary scenery early release rejection connected (2026-11-12; unbuilt/untested)

Read complete original82451250/generated11 and native822802D0/generated77 before wiring. H4 resets selection, evaluates82451DA8 in the local path, and calls82450CD8 on rejection before pose/queue work. Native822802D0 accepts player in r3 and VARIANT SLOT in r4, clears holders through8227E710, reads/checks the record, removes it through821E1908 and deletes its runtime datum through8210C428, preserving native notification823C00C0. Passing the object datum as r4 would be wrong.

Added NativeSceneryReleasePositionValid: mapped geometry predicate first, then original parent-aware origin and native scenario-volume union821AA050. The source-backed counterparts were established in the previous entries. Connected after original selection reset, before native release serialization, only for original-owned local scenery and non-ownership-only releases. Rejection validates the held slot/datum and occupied/not-removed record, invokes native deletion, clears UI/marker/fixed-snap state and returns without settling/rebuilding the removed object. Valid release continues unchanged. Teleporter/spawn-specific gameplay validation remains native H3 under the controlling scope.

No standalone collision algorithm, direct holder writes, private save fields or guessed delete notifications were added. Source remains unbuilt/untested; invalid/valid placement interaction sequences remain part of the later required verification. No tests, launch, capture, export or deployment.


## AFM3 export source-record blocker identified (2026-11-12; source inspection)

Inspected export_bindings.py, source_marker_data.py and anchor_completion.json without executing export or tests. Four legacy completion profiles have source=null: Radio Antennae, Weapon Holder, Glass Sail, Sniper Nest. Their points were generated from native supporting planes, not copied from original H4 marker records. Existing AFM3 exporter unconditionally indexes source_models[completed['source']], so these rows cannot be exported as written. This is a concrete implementation gap, not just a deferred regeneration command.

Added exporter preflight reporting all missing original source names before opening the source cache or writing outputs. Also reject an empty staged-map search rather than overwrite the retained pack with an empty file. No invented48-byte records or silent palette omissions. Original source correspondence or an explicit supported authoring decision remains necessary for these four profiles. Existing AFM2 diagnostic readers are historical and must not be mistaken for full AFM3 lifecycle verification. No export, build, tests, launch or deployment was performed.


## Four authored profiles: original metadata proposal (2026-11-12; source inspection)

Read the existing MATH-AUDIT.md and complete_anchor_transforms.py: the four source-null profiles were deliberately authored from native supporting planes because no matching H4 object was identified; they are not four accidentally missing donor names. The Ravine inventory has Antenna and Dish Antenna but those are already distinct bindings, not evidence of a Radio Antennae match. Preserve that distinction.

Read raw48-byte sandbox_magnet records through SourceMarkerCache from the original ca_forge_ravine.map, without executing any renderer or test harness. Across the inventoried original groups,728 records have bytes0..3 ffff0001 and bytes32..47 3dcccccd3f8000000000000000000000. Five Arch Brace records share the same sentinels/flags/direction but use scale bits3f4492eb. Gen4 RenderModelMarkerBlock names these fields region/permutation=-1, node0, flag HasNodeRelativeDirection, scale0.1, direction(1,0,0) for the common record. Example original donor: objects\levels\forge\fw_gadgets\fw_cannon_man\fw_cannon_man.

Asked the user whether to retain the four existing authored point/rotation sets and complete their AFM3 records using this actual common H4 metadata, or leave the four without magnets. This is a concrete authoring choice, not permission to create a replacement snapping algorithm. No response yet; no donor assignment, changed profile, regenerated pack or silent omission was made. Export preflight remains explicit until resolved. No builds, tests, launches or deployment.


## AFM3 live-loader transaction completed (2026-11-12; unbuilt/untested)

Inspected Load, NativeMarkerBinding, ReadNativeMarkerData and BuildNativeMagnetScene. Load accepted AFM2 and announced Ready, but the connected live path explicitly throws when original definitions are absent. Removed that misleading partial compatibility: production Load now requires AFM3 before publishing any bindings. Historical standalone AFM2 diagnostics remain separate.

The loader now reads full records unconditionally, rejects nonfinite pose/scale/direction values, and checks the seven stored position/quaternion floats against the corresponding big-endian source-record fields. This ensures legacy pose consumers and the original marker constructor do not use different transforms for the same entry. Region/permutation/node interpretation remains with the existing live-node/original-constructor path; no guessed remapping was added.

Bindings accumulate in a local map and are swapped into the global state only after marker/material loading and private Bridge construction succeed. Partial input failures no longer leave a partially populated global binding map. The retained AFM2 pack remains unchanged and is intentionally not ready for this new candidate until the pending authoring decision and export are resolved. No builds, tests, launches, export or deployment.


## Host world-lifetime cleanup completed at existing boundaries (2026-11-12; unbuilt/untested)

Inspected PhysicsWorld, RestorePhysics and Evaluate's existing local-Forge-exit branch. PhysicsWorld detects engine/header/map changes or tick rollback and discarded physics/editor objects, but left the coordinate session, fixedSnap and anchor viewport/queued GPU snapshots intact. Evaluate's exit branch omitted original editor/controller attachment state as well. Those stale identities could refer to reused datums/addresses in a later world.

Added ClearAnchorWorld to reset all anchor owners/viewports under anchorMutex and request producer-safe marker queue/backend logical invalidation after releasing that lock. Connected it with coordinate/fixedSnap reset at PhysicsWorld's existing world-change branch; added editor/controller invalidation to Evaluate's existing exit branch; RestorePhysics now revokes queued world visuals and fixedSnap at entry, including its error path. Original player contact lifetime remains separately owned and unchanged. No stale guest object pointer is restored into a new world.

This is host-lifetime cleanup at already detected boundaries, not proof that every possible engine exit reaches Evaluate, and not an implementation of the pending physics-mode gameplay/persistence decision. Further source coverage and later complete session-transition verification remain required. No builds, tests, launches, captures, exports or deployment.


## Marker depth clear ordering and viewport boundary audit (2026-11-12; source only)

Inspected D3D12CommandProcessor::IssueCopy and its only readback helper caller, plus both D3D12RenderTargetCache::PerformTransfersAndResolveClears call sites. IssueCopy finishes observed marker depth before either Resolve path, including the path with readback disabled. Resolve prepares its clear rectangle and invokes PerformTransfersAndResolveClears only afterward. The actual depth/stencil clear is guarded by non-null clear values and rectangle. Update calls that helper without these clear arguments; its existing previous-depth capture precedes depth ownership transfers. Thus these source paths do not introduce an unhandled resolve-clear-before-capture boundary. This is command-order source evidence, not GPU execution verification.

A separate uncovered boundary remains: FinishIfChanged compares camera matrix, depth info and surface info only. GetHostViewportInfo also depends on clip/VTE controls, vertex/window-offset controls, six viewport registers and depth interpretation. The command processor already constructs a ViewportCacheKey for those inputs, but does so after the marker FinishIfChanged call. Observe then replaces the prior viewport after the next draw. Consequently unchanged camera/depth registers do not establish an unchanged depth-to-screen mapping. Before claiming tiled-depth coverage, preserve the prior observation before a changed effective viewport is drawn, and account for partial-tile capture/assembly rather than merely accepting absent rows as clear depth. Also preserve scissor coverage separately: an unchanged viewport is not proof every pixel received scene depth.

No implementation shortcut, test, build, game launch, capture, export or deployment was performed. Next source work is the effective viewport/tile boundary and its coverage representation; producer-side recorded-buffer abandonment remains independently open.


## Effective viewport boundary connected (2026-11-12; unbuilt/untested)

Added D3D12SceneMarkers::FinishIfViewportChanged and called it after effective viewport calculation but before UpdateFixedFunctionState, binding upload and the next guest draw. It compares all ViewportInfo fields explicitly: integer offset/extent, depth range and all three NDC scale/offset components. It does not compare structure padding or infer mapping identity from camera constants alone. Existing render-target ownership/transfer handling still captures earlier when required.

Read CopySceneDepth: this boundary enqueues copy/transition barriers and restores the source resource state; it does not replace the graphics pipeline or descriptor bindings. Thus placing the boundary after pipeline selection does not itself require another pipeline bind. This is source ordering evidence only, not execution verification.

Further inspection of Draw identified the next concrete gap: depth UV scale/offset currently uses only viewport dimensions and output rectangle; Capture retains NDC Z only. GetHostViewportInfo explicitly puts fractional/window offsets, clipping/cropping and axis signs in NDC XY. Those components therefore need to participate in depth lookup before claiming correct partial/tiled viewport mapping. Complete tile/scissor coverage remains separate, and the last-capture replacement behavior is not tile assembly. No build, tests, game launch, capture, export or deployment performed.


## Marker depth lookup includes effective NDC XY (2026-11-12; unbuilt/untested)

Read GetHostViewportInfo's axis crop/offset calculation and final origin_bottom_left conversion, plus dxbc_translator.cpp's original guest-to-host vertex epilogue: position.xyz is multiplied by ndc_scale, then ndc_offset * position.w is added. The existing marker kernel samples depth at (outputPixel + 0.5) * depth_scale + depth_offset. Its constants can represent this mapping without changing its ABI or recompiling a material pack.

Capture now retains all three NDC scale/offset components and rejects nonfinite transforms. Draw composes final-view pixels with the scene mapping: for horizontal position, depthX = viewportX + viewportWidth/2 * (1 + sx * nx + ox); vertically, depthY = viewportY + viewportHeight/2 * (1 - sy * ny - oy). Substituting nx = 2*(pixelX-left)/viewWidth-1 and ny = 1-2*(pixelY-top)/viewHeight yields the scale/offset now passed to the unchanged kernel. Depth Z uses the same retained array and previous formula. Output marker placement still uses the native camera/output rectangle; the change is its corresponding scene-depth lookup.

Source inspection confirms the old Z-only member references were removed. This is not a numerical, shader or visual test. It does not assemble tiles, establish scissor coverage, or prove which partial source captures contain the required pixels. Those remain explicit implementation gaps. No builds, tests, launch, capture, export or deployment.


## Native camera bounds versus depth-tile coverage (2026-11-12; source only)

Read all original instructions in native821582B0/generated99,82158808/generated75 and821589C0/generated24. The render-view setup rebases the camera's48..54 rectangle to zero, preserves its prior origin at64/66, and separately rebases56..62. It then derives projection data via821589C0 and82158CF8. The existing output-rectangle hook reads the saved origin and rebased dimensions; these fields describe the output view, not an EDRAM coverage manifest.

82158808 copies observer position/basis and field-of-view values, initializes near/far values and clears camera116.821589C0 scales both rectangles using camera72/74 and88/90 through82158C38 before calculating four projection extents. Its camera116 branch additionally modifies that window using120..132. Therefore neither the initial output rectangle nor camera identity alone establishes which scene-depth pixels have been rendered. Projection-window changes and host viewport changes are distinct boundaries; the existing exact matrix comparison accounts for changed uploaded projection constants, while the newly connected effective-viewport check handles host mapping changes.

Also confirmed GetSceneDepthResource returns the currently bound host depth allocation (or the explicit transition capture source), with no validity rectangle or clear history. Resource allocation size is not a scene-coverage guarantee. Do not remove the partial-viewport rejection and claim tile support from the new NDC mapping. Remaining implementation needs retain multiple completed depth regions with explicit coverage, prevent duplicate additive marker output for overlapping regions, and retire their resources safely. Next source trace should follow actual depth clears/resolves and their rectangles rather than reinterpret the split-screen view setup as tile boundaries. No builds, tests, launch, capture, export or deployment.


## Resolve rectangle provenance and coverage constraint (2026-11-12; source only)

Read GetResolveInfo's rectangle construction in graphics/util/draw.cpp and PrepareHostRenderTargetsResolveClear in pipeline/render_target/cache.cpp. Resolve bounds originate from three CPU-written vf0 XY vertices, account for pixel-center and enabled window offset, intersect the current scissor, then expand outward to eight-pixel alignment. They are subsequently clamped to aligned surface pitch and maximum resolve height. Therefore the resulting ResolveInfo rectangle is not the exact pre-alignment draw region.

PrepareHostRenderTargetsResolveClear translates the adjusted EDRAM base relative to the original base into rows/columns using pitch and MSAA sample layout, adds the eight-pixel coordinate offsets, and clamps to the host surface's width/height. It then bounds ownership to the EDRAM tile count and prevents simultaneous depth/color clear ranges from overlapping. The returned depth target can differ from the last bound target. The D3D12 helper scales this actual clear rectangle to host resolution before ClearDepthStencilView. Thus recording clear coverage against only the current bound depth pointer, or copying raw ResolveInfo XY directly as resource XY, would be incorrect.

Implementation consequence: collect clear provenance at the actual depth clear call with its concrete resource and scaled rectangle; preserve the separate pre-alignment scene draw/scissor region for visibility coverage. Use the native target cache's conversion rather than duplicate base/pitch/MSAA math in the marker renderer. Coverage must follow ownership/transfers as well as resource identity. Merely using the enlarged resolve rectangle could expose hidden anchors in padded pixels. This narrows the next implementation boundary without asserting that tile assembly is complete. No builds, tests, launch, capture, export or deployment.


## Grab failure ownership cleanup unified (2026-11-12; unbuilt/untested)

Re-read the native grab transaction and original824511B0/generated119 and8244E2C0/generated219. Both original entry paths funnel accepted ownership into82450E10; the native integration selects at the inner committed ownership/dequeue boundary and initializes placement after the public native call. The source defect found here is host exception cleanup, not a newly inferred H4 gameplay rule: the captured inner selection error set failed and returned without RestorePhysics, whereas post-grab initialization errors attempted restoration. Evaluate immediately returns when failed, so later Evaluate cleanup cannot be relied on to revoke that stale private state.

Both post-native grab failure branches now use one local abort path: disable the bridge, call existing RestorePhysics through a copied PPC context, and log restoration exceptions separately. RestorePhysics already revokes private editor/controller/marker ownership before attempting any native rebuild; it now also clears coordinate/physics UI state at entry so a restoration exception cannot leave those sessions live. Remaining object metadata is retained if restoration fails rather than falsely declaring all bodies restored. Native grab/dequeue still executes unchanged; no fabricated release, delete, save update or distance adjustment was added. The copied context preserves the completed native call's registers.

This closes the identified discrepancy between the two grab error branches in source. It is not proof of recovery during live interaction or a fix claim for the three reported movement defects. Those still require completed integration and later full interaction verification. No builds, tests, game launch, capture, export or deployment.


## Grab eligibility now observes native detachment (2026-11-12; unbuilt/untested)

Read all82450E10/generated43 instructions and native822800B0/generated106. H4's common accepted grab selects, dequeues, transitions physics, then initializes pose/distance for objects with bodies. Its initializer uses the persistent editor44..52 ray point minus monitor physics point, projects Y then Z then X, constrains distance through82452738, and writes the held physics point to68..76. The current bridge implements that stage; it does not substitute a new ray or camera-origin distance. Bodyless handling skips it. This is source correspondence, not runtime parity proof.

The native function traverses parents, checks the root/physics conditions, and may call82120960 on the selected child before variant synchronization, holder assignment and82283B90 dequeue. The outer integration rejected every parented object before that native function ran. Consequently even a child successfully detached by stock H3 could never activate the original H4 path on that grab.

Removed the pre-grab parent exclusion while retaining scenery/crate and authored-override eligibility. At the existing committed ownership boundary, now re-resolve the live object and select the original editor only if native detachment has actually left it unparented. Retained attachments continue the native path and are explicitly still a coverage gap; no guessed detach or parent transform write was added. Original authored physics metadata is still captured before native grab changes the body, and the extra native forced-dynamic stage is skipped only after original selection succeeds. No builds, tests, launch, capture, export or deployment. Attached-to-detached grab and retained-parent behavior require later sequence verification and remaining source mapping respectively.


## Original root eligibility mapped at native scenery detach boundary (2026-11-12; unbuilt/untested)

Read complete H4822BE858/generated118 and8298E798/generated244, native82345288/generated21 and82120960/generated1, and the precise822800B0 branch around822801EC..82280274. H4's association helper reads object256 bits1/2 and associated datum248, corresponding to the native inline object172 bits1/2 and datum164 gate. When no association bypass applies, H4 calls8298E798(root,0): with false second argument it returns root != -1, without consulting tags. H3's82345288(root,0) instead searches TLS264's list9728/count9856 and returns false for an absent root. These predicates are not equivalent.

Added an exact-caller82345288 hook at return address822801F8, scoped to the already prepared scenery grab transaction, matching native r27 selected datum and r23 player. For a still-attached selected child and a valid distinct root, it maps the H4 valid-root result. All other calls retain native results, including general gameplay and grabs outside the adapter. No guessed parent-field write is used. Native822800B0 proceeds through82120960, whose type detach callback/fallback823317C0 owns unlinking, then clears native attachment bookkeeping, serializes the stock variant and sends native notifications before holder/dequeue. The prior post-native parent check still prevents activating an unparented-only adapter if a callback leaves an attachment intact.

This is a source-backed editor-only eligibility adaptation, not proof that every authored parent/child constraint can be represented by H3. Parent-dependent physics and unexpected retained attachments remain open. No builds, tests, game launch, capture, export or deployment.


## Detach pose and velocity correspondence (2026-11-12; source only)

Read complete H482939248/generated225 and native823317C0/generated94, plus native82331608/generated21,823316D8/generated93 and H4822980D8/generated193. Native unlink walks the parent's child/sibling chain, removes the selected datum, sets its parent16/node20 and sibling8 to invalid, and clears its attachment flag. Native pose restoration composes the saved parent-node transform with the child's local orientation/position before calling8232E8B8. These are the existing stock operations retained by the new grab eligibility hook; direct parent clearing would omit required work.

The generic detach transactions are not fully equivalent. H4 has an optional root-motion compensation branch before restoring pose, and conditionally clears frozen/forced-dynamic/keyframe flags and rebuilds. H3's generic fallback does not contain those branches. H4 then attempts822980D8 at the child's physics point before falling back to parent velocities; H3 directly copies the parent's linear/angular velocity.822980D8 requires object256 bit3, a valid8298E2D8 association, a qualifying root definition when r7=true, and an active TLS248 record. It selects one of two velocity/center histories and computes linear velocity as omega cross (point-center) plus root linear velocity, returning angular velocity separately. This is a concrete motion-history difference, not a missing constant or evidence to invent a new spring controller.

The ordinary original grab physics selector/transition still follows native detachment in the adapter. That accounts for the explicit held-state transition but does not prove the root-motion compensation or velocity-history branches irrelevant. Remaining work: map their native equivalents/reachability for supported scenery and parent constraints before closing parent-dependent physics. Kept native detach behavior intact in this pass. No builds, tests, launch, capture, export or deployment.


## Native early-mover point-velocity service located (2026-11-12; source only)

Read complete H48298E2D8/generated53 and native82345330/generated105. The H4 resolver first checks823009B8, then follows the parent root and requires root definition28 bit11 before8298E740 lookup. Local Gen4 ObjectDefinitionFlags names bit11 EarlyMoverLocalizedPhysics; this corroborates the executable gate and identifies the system, rather than treating every scenery object as having a velocity history. Native detach association propagation clears object172 bits1/2/3 and datum164, then conditionally copies those fields from the root via the native managed-object association.

Located and read native820AFCF8/generated9 by scanning TLS264/304-byte history consumers. It is the concrete counterpart to H4822980D8: requires object172 bit3, resolves8211DE00, validates the optional root definition and active record265, computes angular cross point-offset plus linear velocity, and returns angular velocity. Native offsets differ: history0 uses linear0/angular12/center24; the alternate uses72/96/48. Native r8 selects the history explicitly. H4 uses record460 internally: zero selects linear0/angular24/center48; nonzero selects264/288/240. Its active byte is457 and stride500. Do not substitute record byte offsets or assume a constant native r8 value.

Also read823450F0/generated59: it computes a difference between history velocities with additional active/change flags, so it is not the direct point-velocity replacement. The appropriate service is820AFCF8 once history-phase correspondence is established. Identified non-stack H4 record460 writers in generated114,253,35 for the next producer trace. No custom physics formula or hard-coded history choice was installed. No builds, tests, game launch, capture, export or deployment.


## Early-mover history phase producers mapped (2026-11-12; source only)

Read H48298DDD8/generated35 and8298E098/generated114 in full, with their enclosing callers8228E570/generated169 and822E8CE8/generated275.8298DDD8 samples the selected body into linear0/angular24/center48, updates history and sets record460=0 after successful body sampling.8298E098 samples into264/288/240 and sets460=1, also setting it on its failure/invalid-record return while clearing active457/456. Thus460 is updated by the producing phase, not simply a permanent object preference or interchangeable zero/one selector.

Read native82344D50/generated36 and82344E90/generated10 in full. Their sampling services correspond: first producer writes0/12/24 and flag266; second writes72/96/48 and active265 plus history264. Native820AFCF8 r8=true selects the first bank; r8=false selects the second. This is the inverse of H4 record460's bank choice. A successful first producer and the second producer's inactive failure must be handled distinctly; checking only a stale native flag266 cannot establish which bank was last produced.

Excluded the generated253 offset460 hit:82837040 initializes an unrelated604-byte record, not TLS248's500-byte early-mover record. A matching numeric offset was not accepted as producer evidence. Native producer callers are generated111 and75, available for the next lifecycle/order trace. Required integration is now an explicit per-object phase correspondence at these producer boundaries, with world/object lifetime handling; no hard-coded r8 choice was introduced. No builds, tests, launch, capture, export or deployment.


## Native history phase observation implemented (2026-11-12; unbuilt/untested)

Read complete native producer callers820E5E78/generated111 and82117550/generated75. Both enumerate TLS264 table9728/count9856 and pass the table index to the corresponding producer; the32-slot limit follows from the304-byte records preceding9728. H4 counterparts8228E570 and822E8CE8 likewise pass their early-mover list indices. Confirmed first native producer's body eligibility call returns to82344DCC.

Added bounded private history-phase storage and non-mutating hooks for82344D50,82344E90 and the exact first-producer82345A80 eligibility boundary. A successful first producer records first-bank=true; failed first sampling retains the preceding phase. The second records first-bank=false, matching H4's second-phase invalidation behavior. No duplicate body query or write to native history records is introduced. NativeHistoryFirstBank returns an optional, not a guessed default, and validates list slot/datum, history/header/object pointers, engine/map/time identity and tick rollback. Publication/query use a mutex; the nested producer eligibility observation is thread-local and restored by scope.

The observer intentionally has a lifetime separate from held-editor reset so entering or resetting an editor does not erase already-produced motion history. Consumer wiring into the exact scenery detach boundary is still pending; collection alone does not change detach velocity. Same-world history unregister/re-register and save restoration lifetime must also be accounted for before declaring this coverage complete. No builds, tests, launch, capture, export or deployment.


## Early-mover removal and association resolver (2026-11-12; source only)

Read complete native821224C0/generated83 and8211DE00/generated86.821224C0 checks the object's definition early-mover bit, searches TLS264 table9728/count9856 for the datum, clears object172 bit0, replaces the removed table entry with the last table entry, zeroes the removed 304-byte history record through825A4760 (return address8212259C), then decrements count. It does not copy the last history record into the removed record. Subsequent traversal clears dependent objects' association bits1/2/3 and datum164, including their native update/notification work. Private phase tracking therefore must not migrate the last slot's phase into the removed slot. Both the zeroed slot and retired last slot need invalidation; same-datum re-registration must not revive the retired phase. The exact zeroing boundary is identified, but cleanup is not yet implemented.

Located registration in8232F3D8/generated55: under its definition-bit and count<32 gates, it sets object172 bit0, appends the new datum at9728+4*count, and increments9856. Only the registration region was inspected without truncation; do not count the entire large object-creation function as reviewed. Registration does not establish a newly sampled phase. Whole-table initialization/save restoration still needs tracing.

Native8211DE00 follows parent16 to the root, then requires root object172 bit1 or bit2 and searches the list for root datum164. It is an association resolver, not a direct search for the input datum. This distinction matters for the pending detach consumer: after unlink, the detached child's propagated association determines the lookup. Do not replace it with direct list lookup of the detached child or assume every early-mover root resolves itself. The H4 resolver's initial823009B8 branch remains an additional correspondence boundary to account for.

No builds, tests, launches, captures, exports or deployment. Detach velocity consumption, root-motion compensation, history reset/save lifetime and removal invalidation remain incomplete.


## Native history removal/reset cleanup connected (2026-11-12; unbuilt/untested)

Read complete82344A88/generated41,82344AF8/generated93 and82344B40/generated66.82344A88 allocates9864 bytes via82345C38, publishes the allocation atTLS264 and zeros it.82344AF8 zeros the same allocation then sets byte9860 to1.82344B40 only clears byte9860; it does not clear history, so it was not treated as a reset. Direct-call search found no generated bl callers for these three routines; their lifecycle dispatch registration remains to be traced rather than inferred from function names.

Added post-original hooks for both complete zeroing routines to clear private phase observations. Added an821224C0 removal observer: bounded pre-call list lookup records the removed index/count/last datum; after the original routine returns, it requires the decremented count and expected last-datum replacement, then invalidates the zeroed index and retired tail slot for that history allocation. It does not migrate phase metadata with the list entry or modify native history, object fields, registers, or simulation order. Unsuccessful removal leaves phase observations intact. Source readback inspected all newly added hooks; no executable was built or exercised.

This closes the mapped ordinary removal and whole-table zeroing source hooks, not save/load coverage. Save restoration may bypass those zeroing routines, and lifecycle callback dispatch still requires evidence. The detach consumer remains disconnected until remaining lifetime and root-motion boundaries are accounted for. No builds, tests, launch, capture, export or deployment.


## Native history lifecycle dispatch resolved (2026-11-12; source only)

Read the original guest-image callback pointers. The lifecycle table starts at82039DF0 and has92 entries of48 bytes. Early-mover entry34 at8203A450 contains82344A88,82344AE0,82344AF8,82344B40 at offsets0/4/8/12; offsets16 through44 are null. The second pointer appearances around8206ACC8 belong to a different address/descriptor table and are not evidence of lifecycle calls.

Read complete821C6FE8/generated45,821C70B0/generated80 and821C71A8/generated31.821C6FE8 initializes TLS128 and dispatches all92 offset0 callbacks forward, reaching the history allocator/zeroer82344A88.821C70B0 clears the three512-byte masks, performs821C7268, brackets forward offset8 dispatch with TLS128 state-byte changes and reaches82344AF8.821C71A8 traverses offset12 callbacks backward, reaching82344B40, which only clears the history active byte9860. This establishes the indirect call paths for the existing whole-table reset hooks without relying on absent direct calls.

Also read complete820E5160/generated24,821A96A0/generated58,821A9860/generated5 and821C94A8/generated24. They dispatch offsets24,36/44,40,and28/32 respectively; all those slots are null for the early-mover entry. Their mask/region transitions must not be mistaken for calls to the history zeroer or evidence of save restoration. The remaining offset4 callback82344AE0 and the allocation service82345C38 are the next concrete lifetime boundaries. Direct game-state restoration coverage remains open; no save/load parity claim follows from this table alone.

No code execution, builds, tests, launch, capture, export or deployment. Current implementation remains incomplete and unverified.


## History allocation rebind and disposal boundaries (2026-11-12; unbuilt/untested)

Read complete82344AE0/generated59,82345C38/generated84,821E5A38/generated81 and82344A78/generated93. Disposal82344AE0 writes zero to TLS264.82345C38 registers the requested9864-byte allocation through821E5A38, supplying82344A78 in r8; it derives the returned pointer from TLS60 plus the registered24-byte descriptor's offset and publishes TLS264.821E5A38 records offset at124+24*index, requested size128+24*index and supplied callback132+24*index, with additional descriptor fields.82344A78 itself simply assigns r3 to TLS264. This is a separate rebind boundary from allocation zeroing, and may publish already-populated state.

Added post-original hooks for disposal and the registered rebind callback to invalidate private phase observations. Rebinding never invents an H4 record460 value: the private phase remains unknown until an observed producer establishes it. These hooks do not change native allocation, saved bytes, callback arguments, return registers or the restored history. The allocation-descriptor dispatcher and its restore callers still need tracing to prove coverage of the save path; the registered callback alone is not a complete save/load audit.

Source-only implementation; no builds, tests, launches, captures, exports or deployment. Detach consumer and root-motion correspondence remain unfinished.


## Rebind is not restoration: narrowed history invalidation (2026-11-12; unbuilt/untested)

Read complete821E5B48/generated21 and821E5BA8/generated62. The former loops allocation descriptors at132+24*index and calls each callback with supplied buffer base plus descriptor offset124. The latter calls the same callbacks with zero. Their callers include ordinary buffer acquisition/release:821E6AC8,821E6BA0,821E6C00,821E6C98,821E5860,821E5988 and821E6B38 (read complete generated0/20/23/62/79/78/96). These manage buffer references, locks and TLS group pointers, not exclusively state restoration. Therefore the previous unconditional82344A78 invalidation was overbroad: another thread binding or releasing a snapshot could erase a valid simulation phase. Removed that hook before any build or run.

Read complete821ABAB0/generated8: it visits five3208-byte allocation groups, rebinding eligible active buffers through821E5B48. Read complete821E6448/generated12 and821AB6D0/generated92, which invoke that sweep after loading/copying state into the authoritative allocation, before821E68B0. Also inspected restore call regions in82290D78/generated19,the enclosing restore routine in generated80, and821AC540/generated95; the combined output was truncated, so these additional enclosing functions are not claimed fully reviewed.

Moved private phase invalidation to post-original821ABAB0. Native initialization/zeroing, disposal and ordinary removal cleanup remain in place. Ordinary per-thread buffer rebinds no longer reset global observations. State replacement leaves phases unknown until the original sampling producers run; no saved H3 bytes or native callbacks are replaced. This establishes a concrete restoration boundary for private history but does not prove the entire Forge save/load integration complete.

No builds, tests, launches, captures, exports or deployment. Remaining detach work: consume the observed phase at the original point-velocity boundary, account for unknown phase after restore, and finish root-motion compensation correspondence.


## Scenery detach point-velocity consumer connected (2026-11-12; unbuilt/untested)

Re-read complete H482939248/generated225 and native823317C0/generated94. H4 propagates the former root association via8298E800, queries the detached child's physics point82260B58, attempts822980D8 with root qualification enabled, falls back to the former parent's velocities on rejection, then sets child velocity822D1158. Native823317C0 copies parent velocity earlier and propagates association through82345330 at its end. Confirmed its fallback caller82120960 returns from823317C0 at82120A18.

Added a post-original823317C0 hook restricted to that return address and the active prepared scenery grab transaction/datum. It calls the new ApplyNativeDetachPointVelocity helper after native association propagation. The helper retains native rejection for absent localized-history flags or missing association; resolves the list index with original8211DE00; reads the observed bank phase; queries the original physics point; and calls native820AFCF8 with root qualification enabled. Successful finite vectors are applied through native820F29C8. Rejected queries retain the already-applied native parent fallback. No custom velocity formula, saved-format extension, or generic gameplay detach override was added.

If the service would accept an active history but its private phase is unknown (for example immediately after restoration), its provisional result is discarded and the grab transaction records an explicit integration error. This is an unfinished case, not a silent bank default or completion claim. The selection/dequeue hook now skips original selection after a transaction error while still executing native dequeue; outer cleanup handles the failure. Native caller registers are preserved by copied query/setter contexts. Source readback inspected the added helper and hook; corrected a mixed-type auto declaration before any compilation.

H4 root-motion compensation remains separate and unfinished: its eligible-root branch normalizes angular velocity, forms negative-timestep rotation, constructs a prior root transform, transforms the saved parent-node basis into root-local space, composes with that prior transform, then restores the child's pose. Native823317C0 directly restores the saved parent-node pose. H4's conditional frozen/forced-dynamic/keyframe clearing and rebuild also still need final correspondence. The extra native fallback setter before the final corrected setter is retained for now; full detach ordering equivalence is not claimed.

No builds, tests, launches, captures, exports or deployment. Reported manipulation defects remain unverified.


## Corrected compensation identity lifetime across unlink (2026-11-12; unbuilt/untested)

Current-source audit found that root-motion math and eligibility were already implemented earlier in Bridge::CompensateAttachmentPose and NativeCompensatedAttachment (see controller flag phase entry above). The recent wording that root compensation still required implementation was imprecise: the concrete missing integration was its attachment-identity lifetime. Native823317C0 calls82331608 before823316D8; unlink clears child parent16 and node20. NativeCompensatedAttachment was reading those cleared fields at the later82331858 callback, returning before reaching the existing original H4 math. H482939248 instead retains parent22 and parent-node28 across unlink.

Added a scoped thread-local NativeDetachAttachment captured at823317C0 entry for supported local scenery/crates. It retains the full child datum/object pointer, parent datum and signed node index. The compensation callback uses this saved identity, checks the live child pointer, walks the still-live parent ancestry and validates the passed node address using the saved index. Root/node poses and velocities are still read at the compensation stage, preserving the original timing rather than caching a pre-unlink computed transform. Nested calls restore their prior scope. Existing authored-localized/keyframed eligibility and original controller flag lifetime remain in force.

The compensation wrapper now catches mapping errors, records a grab transaction error (or disables/logs outside a grab), and completes the original pose/notification path instead of unwinding through an unfinished native detach. Source readback inspected the new scope, consumption and wrapper. This is a source correction, not visual or behavioral proof.

Read complete native820F29C8/generated107: it updates object/body velocity, wakes/notifies for nonzero input and calls820F2EC8. Its early invocation in native detach therefore cannot be dismissed as an inert write. Exact native early-setter return address is823318CC. Deferring this scoped setter to the final H4-equivalent stage, together with restored-phase handling and conditional physics-flag/rebuild correspondence, remains required. No builds, tests, launch, capture, export or deployment.


## Deferred scenery detach setter and late parent fallback (2026-11-12; unbuilt/untested)

Connected the exact native820F29C8 return-address823318CC boundary to the prepared scenery-grab detach scope. The hook captures finite native linear/angular arguments and defers the setter; unrelated velocity calls and detach operations continue through the original function. Native823317C0 then completes unlink, pose/maintenance and association propagation. Its post-hook applies the accepted original point-velocity query once, or on a normal rejection queries the former parent's current velocities at this final stage and applies them once. The earlier native parent query remains a redundant read; it no longer causes an early velocity/body wake update in the scoped path.

The retained native vectors are an error fallback only. If phase mapping or the late parent query fails, the transaction records the error and completes its deferred native velocity update rather than abandoning it. If argument capture fails, the early native setter runs and the deferred record is cleared, preventing a second setter in that failure path. Root compensation uses the same attachment identity scope; nested scopes restore correctly. The guarded original-selection hook skips after a recorded error. No skipped native return value is consumed at823318CC: the original caller immediately sets r3 for the following maintenance call.

Source readback inspected the consumer, fallback helper, scoped setter and enclosing detach hook. Subsequent source edits added late parent querying and cleared the deferred record before the early-setter error fallback. Runtime behavior, build compatibility and wake/notification parity remain unverified. Restored active history without an observed phase is still explicitly incomplete, and the remaining H4 detach physics-flag/rebuild correspondence remains open. No builds, tests, launches, captures, exports or deployment.


## Retain forced-keyframed request independently of native body type (2026-11-12; unbuilt/untested)

Compared the current RebuildSceneryPhysics/TransitionNativeSceneryPhysics adapters with H482939248's detach flag branch. The adapter previously consumed H4 bit22 only during scoped construction and forgot the request afterward. Detach explicitly examines and clears that flag, independently of frozen6 and force-dynamic21. Inferring it from runtime keyframed motion would also classify authored keyframed bodies as overrides and is not equivalent.

Added PhysicsObject::keyframedOverride as private lifetime metadata. The original transition's rebuild callback updates it from requested H4 bit22 at the native flag-write/construction boundary; subsequent transition snapshots reflect it in their original-layout flags. Native body construction still uses the same scoped mapping. No native H3 object bit or saved-layout field is repurposed. Restore/ownership teardown continues to discard PhysicsObject metadata. This supplies the missing state to the upcoming detach-clear operation; it does not itself implement that operation or resolve persistence after state restoration.

H4 detach also rebuilds for prior connected bit8 and its additional attachment flag29, resets byte265 for flag29, and performs its conditional dependent-child rebuild. The remaining native correspondence must preserve those gates; applying the already-mapped frozen/dynamic/keyframed subset alone would not establish complete parity. Inspected flag-reference regions in82938A48/generated218: no flag29 write was present in those regions; producer coverage is still open. No builds, tests, launch, capture, export or deployment.


## Detach flag29 producer identified as marker attachment (2026-11-12; source only)

Scanned original generated instructions for the concrete bit29 set followed by object256 storage. Located82938708/generated266 and read it completely: it sets object256 bit29, calls8226BCA0 with the supplied marker identifier and a one-result output, then stores the returned marker node index in object265. Read complete8226BCA0/generated187: it resolves the render-model marker against current model/node data and supplies a fallback transform when absent. Thus byte265 is a child-marker node index; it is not the parent attachment node57 or a Forge physics-mode byte.

Located direct82938708 callers in82933B30/generated203,82936150/generated204,829C6550/generated204 and82941450/generated241. Inspected their call regions, not the complete large creation routines. They prepare a child marker before829382A8 under authored placement/attachment gates. Read complete829382A8/generated146 and native82330CB8/generated60: both dispatch object-type attachment callbacks and then a fallback when still unparented. H4 uses service offset100 for this marker wrapper; native uses104. This differs from the previously traced separate node-attachment wrapper and must not be conflated with it.

This explains why detach clears flag29 and resets265 before rebuilding: it is unwinding special marker attachment setup. No corresponding H3 field was assumed or written. Further work must establish whether the supported stock-H3 scenery manipulation paths produce an equivalent condition, using native82330D88 and original82938380 as the next fallback comparison. The current private forced-keyframed request is correctly separate from this state. No builds, tests, launch, capture, export or deployment.


## Marker attachment fallback comparison (2026-11-12; source only)

Read complete native82330D88/generated66 and H482938380/generated97. Both query parent and child markers (native8210CDF8 / H48226BCA0), distinguish an explicit child marker from marker identifiers0/-1, compute the placement transform, update orientation/pose, and attach the child to the parent's resolved node (native82331260 / H482938A48). This confirms native H3 already provides marker-based attachment positioning; implementing another approximate placement calculation is unnecessary.

H4 additionally stores the parent marker identifier at child40, performs a parent-category/marker-property offset adjustment in the default-marker branch, and contains a post-attach correction gated by child categories2/3 and definition516 bit4. The latter is outside supported scenery/crate categories, so it must not be imported as a scenery rule. Native82330D88 ends after the node attachment call and has no corresponding explicit parent-marker identity store or tail correction. Neither fallback itself sets the separate H4 flag29; that setup belongs to the previously traced82938708 calls before the wrapper.

Do not infer a native flag29 equivalent from the shared marker-positioning work. The pending scenery detach adapter must distinguish native existing attachment behavior from H4's additional marker-physics metadata and prove reachability in the actual imported scenery manipulation path. Existing stock H3 attachment/save code remains unchanged. No builds, tests, launch, capture, export or deployment.


## Discard private scenery ownership on native state replacement (2026-11-12; unbuilt/untested)

Reviewed the current outer grab, PhysicsObject state, PhysicsWorld identity checks and821ABAB0 hook. The restore hook previously invalidated only motion-history phases. A state replacement can retain allocation addresses, datum salts and a nondecreasing/equal tick, so those checks do not prove that private held-editor state, controller flags, original physics snapshots or keyframedOverride still belong to the restored objects.

Extended the existing post-original821ABAB0 cleanup to clear nativeEditors, controllerAttachments, physicsObjects, coordinate/physics menu sessions, fixed-snap state and queued/displayed anchors. It deliberately does not call RestorePhysics: applying old per-object original flags after loading authoritative state would overwrite the newly restored native state. Native save bytes, restored object flags and native holder slots remain under stock H3 control. Existing history invalidation remains protected by its mutex; renderer invalidation is performed after releasing that lock.

This fixes stale private ownership, not full resumed-editor parity. Reconstructing supported H4 manipulation ownership from a restored native held slot, and the separate player-contact normal's restoration provenance, remain explicitly open. No assumption that native player allocation callbacks rerun on a same-address restore was made. Marker attachment bridge search found no direct wrappers for82938708/829382A8/82938380/82933B30; this is limited direct-reference evidence, not proof that no indirect original call can reach them.

No builds, tests, launches, captures, exports or deployment.


## Restored player contact provenance made explicit (2026-11-12; unbuilt/untested)

Reviewed NativePlayerContact, PlayerContact, ObserveNativeContact, player allocation/removal hooks and native820FFBE0/82237E58 observation publication. The previous contact identity check accepted an old normal after same-address restoration when player/pool/record still matched. Clearing the whole record alone would also stop recapture, because ObserveNativeContact required an already-bound PlayerContact.

Added normalKnown, false by default. Actual native player allocation initializes the original H4 zero normal and marks it known; state replacement marks retained contact normals unknown without manufacturing an allocation event. PlayerContact's normal-consuming callers reject unknown values. Observation and player removal may resolve identity without requiring a known normal; the observation path can bind a valid restored player identity with unknown normal. Only the existing finite primary-plane result from native82237E58 publishes a fresh known normal after native820FFBE0 returns. Native contact motion, queries and notifications are unchanged.

This prevents stale-normal reuse and permits genuine native recapture. It is not a substitute for H4 saved contact state: a restored player that has not produced a fresh primary plane remains unknown, and current manipulation ownership reconstruction must account for that case before the restore flow is complete. No normal was guessed from velocity, input, object orientation or an arbitrary up vector. Source readback inspected the identity/known-state handling and publication. No builds, tests, launches, captures, exports or deployment.

## Four magnet omissions authorized (2026-11-12; source only)

User explicitly selected no magnets for Radio Antennae, Weapon Holder, Glass Sail and Sniper Nest. Exporter now excludes these labels before alias/donor resolution and records zero-point omissions in its report. Their scenery remains intact. All other missing source records still fail preflight. Source inspection of NativeMarkerBinding/ReadNativeMarkerData confirms absent bindings return no marker group; no custom snapping substitute is introduced. Historical authored profiles remain inactive for these labels. Pack regeneration and deployment remain pending. No export, build, test, launch or capture performed.

## Inactive follow contact and identity separated (2026-11-12; source only)

Previous turn made progress by implementing the four user-directed magnet omissions. Inspected the complete instruction stream of original8244AF48 in generated halo4_recomp.201.cpp. Object256 bit20 gates the projection branch; player152/156/160 normal loads occur only after that gate and the displacement threshold. The native owner resolver needs only the validated player record, not a known collision normal. Changed its PlayerContact lookup to identity-only. NativeMonitorFollowWorld now requires a known normal only with native object172 bit19 set; otherwise it supplies an unread zero scratch value without marking stored normal known. Active contact with an unknown restored normal still fails explicitly. This does not solve contact-response reconstruction or restored held-editor ownership. No build, test, launch, capture or deployment.

## Original response can recover an unknown restored normal (2026-11-12; source only)

Previous turn progressed by separating inactive-follow contact from player identity. Read complete instruction streams for82235650 (generated256) and824863F8 (generated35). In82235650 r18 is the supplied normal pointer; it is passed as the primary selector output, and read only after primary success. Reverse selection uses a separate stack output. In824863F8 r21 is that output; every path reaching its first load has first stored all three components (single-plane copy or two-plane cross projection). Early exits do not consume the supplied old normal. A successful response therefore does not require prior normal validity.

ReplaceNativeMonitorContact now binds player identity even when its normal is unknown and supplies an unread zero scratch seed for that case. A successful original response promotes its actual output to known state; a failed response does not promote the seed. Previously known state retains original output behavior, including selector writes on non-response paths. This uses the existing single unit-update response, not an extra query. Follow still rejects active contact with an unknown normal, including an early collision-disabled return preserving an active flag. Restored held-editor ownership and that early-return case remain open; no claim of full restoration parity. No builds, tests, launches, captures or deployment.

## Remaining identity-only contact callers and restore dispatch (2026-11-12; source only)

Previous turn progressed by allowing original contact response to recover an unknown normal. Inspected all remaining PlayerContact call sites. Native selection-ray ownership reads only record40; variant-removal and object-deletion cleanup only validate the live player record. Changed these three to explicit identity-only lookups and removed the default requireNormal argument so future callers must choose. No collision normal is consumed by these paths.

Read complete821E68B0 (generated103): post-restore processing invokes27 callbacks through table0x8276B188, passing the restore flags. Inspected call neighborhoods of821E6448,82290D78,821AB6D0 and821AC540: they invoke this stage after821ABAB0. A combined output truncated821AB488, so its path is not counted as reviewed. Reconstructing original-held ownership at the earlier rebind hook would precede these native callbacks; callback effects must be traced before choosing a reconstruction point. Existing invalidation remains in place. No builds/tests/launches/captures/deployment.

## Post-restore callback inventory resolved from native image (2026-11-12; source inspection)

Previous turn progressed by correcting identity-only contact callers. Read all27 BE pointers at8276B188 from guest-image.bin. In order:821B81F0,82348E08,82233DE8,821C7728,82211818,821CB520,82233DE8,821087D0,8220C9B8,82213580,821E7620,823B5628,824659B0,82233DE8,82233DE8,82233DE8,821AC180,82211820,825119F8,8223F770,822135D0,82233DE8,82233DE8,82233DE8,82461B00,82229D78,821BA2C8. Direct-call inventory is located against generated source; that inventory is not full semantic coverage.

Fully read821B8168 (target of first callback): rebuilds TLS312 time samples, not held-object ownership. Fully read821C7728: repairs session variant-related data through82254530/821DEC38/821DE790. Callback4 is a branch entry at82211818 into82211580; read that entire body: it rebuilds four352-byte TLS268 local-control objects using retained type selectors, vtable writes and sentinel/default fields. Callback17 (82211820, read fully) then runs local-player/control association repair, including salted player validation and8213AA00 after the local-control virtual query. These callbacks establish that local-control identities are repaired after the current invalidation hook. They do not establish a held-object reset.

Callback16 (821AC180) has no separate generated definition; raw bytes begin816D0000394000BC (TLS read and offset188), so it is not a missing-pointer/no-op and must be recovered before declaring callback coverage complete. Other callbacks have only direct-call inventory so far. Next step: trace object and game-engine restore effects, and reconstruct ownership only after native repairs, if their source contract requires it. No runtime edits guessed from this inventory; no builds/tests/launches/captures/deployment.

## Post-restore physics rebuilding precedes editor reconstruction (2026-11-12; source only)

Previous turn progressed by resolving the callback table and local-control repair. Read full callback bodies821087D0,8220C9B8,821CB520,82213580,824659B0, plus821CE4C8 and821CAA68. The first two operate their own global/TLS pools and flags; neither directly addresses the Forge holder array, but their callees are not exhaustively reviewed and no claim of held-state preservation follows.82213580 resets four968-byte TLS716 observer records before822133C8.824659B0 resets TLS712 lookup entries and offset8 of TLS272 records.

The relevant physics callback821CB520 skips on restore flag0x80; otherwise it visits TLS260 records, clears selected offset12 fields, clears TLS492, then passes flag bit0 to821CE4C8. That wrapper invokes821CAA68 with temporary global flag82 behavior.821CAA68 clears physics lookup arrays, initializes world/configuration services, runs per-world creation and reconnects existing world entries before821CAFE8/821CBFA8. This confirms substantial native physics repair occurs after821ABAB0 and before later local-control callbacks. Private physics pointers/controller ownership must not be reconstructed during the earlier rebind hook. Full subordinate physics semantics and Forge holder survival remain open.

Direct57752-offset references resolve to82304AD0,82308210,8227E710,82282538,82309348; this is a search lead, not exhaustive holder-write coverage (other instructions can form the address differently). The next ownership audit must follow native Forge initialization/restore dispatch rather than infer a release from generic pool reconstruction. No builds, tests, launches, captures or deployment.

## Forge holder initialization separated from maintenance (2026-11-12; source only)

Previous turn progressed by mapping post-restore physics rebuilding. Resolved first60 entries of native Forge vtable82040D68 directly from guest-image.bin. Relevant entries: +20=82280D80, +28=82280F98, +100=82282538, +104=82282378. Read complete82280D80,82280F98,82282538 and +16=82283058.82280D80 clears1864 bytes beginning engine57740 and explicitly initializes16 holder entries engine57752..57812 to-1, alongside other Forge state.82280F98 instead performs variant setup and clears the64-entry queue engine58536; it does not directly clear that holder array. Its subordinate variant operations still require tracing before declaring holder preservation.82283058 exposes held/target eligibility to the menu; it is not a restoration callback.

82282538 (+100) iterates all16 existing holders in session mode4, resolves each84-byte variant record, conditionally enables the held object via8227E770, then checks movement/orientation against the stored variant and may zero linear/angular velocity. It is maintenance, not the initializer; no direct holder-clear write occurs there. Need resolve restore callers of initialization/variant setup, rather than treating the shared57752 literal as evidence of reset. No runtime reconstruction has been guessed. No builds/tests/launches/captures/deployment.

## Forge initialization dispatch located (2026-11-12; source only)

Previous turn progressed by distinguishing holder initialization from maintenance. No generated direct calls target82280D80 or82280F98; these are virtual methods. A narrowed engine-table/virtual-load search resolves engine+20 in82216710 and engine+28 in82216CB0/8221A518.82216710 first zeroes TLS100 engine storage (88048 bytes), selects the engine through session data, and calls820B07F0 then vtable20; this is a full initialization path, not evidence that post-restore rebind clears holders. A broad earlier search output was truncated; only its fully visible82216710 body and subsequent focused excerpts are counted.

Read complete8221A518: event1 stamps current simulation tick atengine57612, invokes82216C30 and selected engine vtable28; event3 performs player configuration work. Its callers are82217028 and822F8600.82216CB0 callers are82217028 and82219E60. These identify concrete lifecycle paths for the next restore reachability audit; merely identifying event1 does not establish save/load semantics. No implementation based on an assumed restore event. No builds/tests/launches/captures/deployment.
Original lifecycle table82039DF0 entry28 contains822165D8/82233DE8/82216710/82216FB8 at offsets0/4/8/12; all remaining slots are zero. Thus the holder-reset caller is specifically the previously mapped offset8 map-initialization dispatch, rather than a member of the27 post-restore callback table.

## Native Forge initialization now clears private holder state (2026-11-12; unbuilt/untested)

Previous turn progressed by locating the map-initialization dispatch. Read complete82217028,822F8600,82219E60 and82216CB0.82217028 explicitly initializes current state1;822F8600 applies changed state from incoming field36 under maskbit2;82219E60 compares desiredengine81212/current57608 and handles transitions. These callers establish state-transition dispatch, not a generic post-restore callback.82216CB0 clears124 bytes atengine57616 (ending57740), outside holder entries57752..57812, before selected engine+28. Subordinate variant behavior remains open.

Added an after-original82280D80 hook: clear private editors, controller attachment observations, physics snapshots, coordinate/physics UI state and queued anchors when the original initializer clears native holders. Do not restore stale physics snapshots or reset player allocation-lifetime contact data. This closes a concrete lifecycle gap when native map/engine/tick identities are reused; the existing PhysicsWorld heuristics alone cannot prove initializer detection. Native initializer return/register state is preserved. Restore reconstruction is still separate and incomplete. No builds/tests/launches/captures/deployment.

## Variant lifecycle mutations and missing restore callback recovered (2026-11-12; source only)

Previous turn progressed by connecting native initialization cleanup. Read full821E4028,821E0D20,821E4788 and82331940. In Forge+28 (82280F98), non-session4 runs821E4028: variant flags can trigger detachment82120960, transform update8232E8B8, slot modification/removal821E25B0/821E1908 and generic deletion8210C428, or recreation821E2898. Therefore the earlier absence of direct holder-array writes is insufficient evidence of ownership preservation; the existing generic deletion hook is relevant.821E0D20 recalculates variant budget usage.821E4788 derives variant296 from a player predicate/count and requested flag, then calls82331940 on each valid entry atvariant312+84*i when that byte changes.82331940 toggles object4 bit0, with823359C8/8210C700 notifications; it is not a direct holder reset. Subordinate notification reachability remains unproven.

Recovered callback821AC180 directly from48 original bytes with the existing Capstone dependency, without executing guest code: reads TLS188 tick12, stores it atglobal828E6AB0+0x1F35C, then tail-calls821E6E40(0,2). It is a12-instruction callback missing from generated standalone definitions, not a no-op. Its forwarded helper remains to inspect. No builds, tests, launches, captures or deployment; source disassembly only. Restored-holder reconstruction remains incomplete, and a new grab must not be fabricated merely to fill missing host state.

## Recovered restore callback is time-state repair (2026-11-12; source only)

Previous turn progressed by recovering821AC180 and tracing variant mutations. Read complete821E6E40,821E6FA0,82090668 and822503C8.821AC180 forwards(0,2), so821E6E40 clears bit2 of TLS188 halfword2, recomputes time-state gating through821E6FA0, and propagates the resulting pause/activity predicate through822503C8 and821B2A20.821E6FA0 uses bit0 as a recursion guard and adjusts reason bits using session/local-state predicates. These bodies do not touch Forge holder storage or dispatch its initialization. Peripheral session/audio helpers were not fully expanded; they are not evidence for a held-state reset. Do not expand unrelated pause/audio RE merely because this callback reaches it.

Restore integration boundary now established:821ABAB0 invalidates stale private ownership;821E68B0 subsequently repairs physics, local controls/observers and time state. Native Forge initialization is separately tied to map lifecycle entry28+8, and private cleanup now hooks it directly. Outstanding work is specifically source-backed recovery of original held-editor state after actual state replacement, including compatibility of transient H4 state with native H3 storage. No synthetic re-grab or silent holder drop was added. No builds/tests/launches/captures/deployment.

## Scene-depth observation excludes non-rasterizing memexport (2026-11-12; source only)

Previous turn progressed by bounding restore dependencies. Reviewed scene-marker Observe/Capture/Draw, command-processor rasterization selection and render-target transfer/clear boundaries. Command processing explicitly permits vertex-memexport draws when IsRasterizationPotentiallyDone is false; they can reach the final Observe call despite producing no scene pixels. Added the existing is_rasterization_done guard to Observe so a retained depth resource is not attributed to camera state from such a draw. Existing scene-boundary Finish behavior remains unchanged. This is necessary input provenance, not proof of initialized depth coverage.

Remaining rendering gap: Capture still copies a complete source resource and retains only the latest mapping; viewport bounds alone do not prove clear/transfer/scissor coverage or correctly accumulate tiled rendering. Actual depth-clear resource and rectangle are available at the D3DClearDepthStencilView path; source mapping still needs explicit coverage handling. No build, shader compilation, test, game launch, capture or deployment.

## Continuous depth-coordinate edge guard corrected (2026-11-12; uncompiled source)

Previous turn progressed by excluding non-rasterizing depth observations. Inspected the complete shared marker compute kernel and Draw coordinate mapping. Kernel converted continuous coordinates to int before bounds rejection; a negative fractional coordinate (-0.5) truncates to0 and incorrectly samples the resource edge instead of rejecting an outside pixel. Moved finite/continuous bounds checks before conversion. Nonnegative in-range conversion keeps the existing texel selection; constants remain80 bytes and material arithmetic is unchanged. Also reject nonfinite viewport origin/depth range before capture, complementing existing extent and NDC checks.

This is a resource-edge correction, not a substitute for tiled clear/transfer coverage. The material compiler includes this kernel, but existing packed shader bytecode is unchanged: regeneration is required after remaining implementation work. No shader compilation, builds, tests, launches, captures or deployment.

## Retained depth binding distinguished from actual depth use (2026-11-12; source only)

Previous turn progressed by correcting shader edge bounds. Reviewed RenderTargetCache::Update actual-use selection and accumulated-binding retention: normalized z_enable/stencil_enable select current depth/stencil use, while old accumulated targets may survive draws that use neither. GetSceneDepthResource uses accumulated bindings, so rasterization alone is not sufficient provenance. Scene-marker Observe now additionally requires normalized_depth_control.z_enable. This retains depth-tested draws (not merely depth writers), while excluding color-only/stencil-only work from establishing new depth observation. Finish still preserves preceding scene depth at mapping/resource boundaries.

Resolve paths both pass IssueCopy, which calls FinishSceneMarkers before resolving/clearing. Update separately captures the previous source before ownership transfers. Actual resolve-clear rectangles are scaled from Transfer::Rectangle; host depth-store rectangles require8-pixel alignment. These boundaries preserve ordering but not per-pixel initialized coverage. No full tiled-coverage claim: explicit coverage and multiple mapping accumulation remain outstanding. No builds/tests/launches/captures/deployment.

## Detach reset boundary and reconnect lifetime (2026-11-12; source review)

Previous goal turn was no progress: it restated an already-applied marker exclusion. This turn re-read complete original H4 82939248 (generated225), native H3 823317C0 (generated94), H3 82330778 (generated35), H3 82330B20 (generated112), and H4 82936D60 (generated38). No execution or tests.

Confirmed reset ordering in H4: snapshot original bit8 into rebuild accumulator r21; bit29 additionally clears marker byte265 to255 and forces rebuild; unlink; restore compensated/uncompensated pose; optional visibility reconnect82936D60(child,false,null); inspect current frozen6/keyframed22/forceDynamic21. If any of those three are set, clear all three and force rebuild. Call82388A08(child,false) iff accumulator is set. Only then perform activation/maintenance, root association, point-velocity query and final velocity setter. Clearing flags at outer detach entry or after the final velocity call would not reproduce this order.

H3 823317C0 performs pose823316D8, optional visibility reconnect82330778(child,true,null), conditional body connection82330B20, parent-velocity query/setter, maintenance, then root association. It contains no corresponding three-override reset/rebuild. Native body connection82330B20 is not a rebuild substitute: it calls822633B8 for an existing instance, sets native bit7, and writes halfword180. The detach condition tests native bit8, distinct from connected bit7; do not conflate them.

Reconnect lifetime matters: H3 82330778 ends with world-bound checks8232DEF0/8232E038 and can call object deletion8210C428. H4 82936D60 has analogous bounds checks82932288/829323F8 and removal82936B78. A newly inserted post-reconnect reset must re-resolve the salted datum and private physics entry; it must not trust a pre-call pointer/reference. The true/false reconnect argument difference also selects different subordinate paths, so copying just that argument is not established parity.

Next implementation boundary is the post-pose/post-optional-reconnect, pre-body-connection stage, with original pre-unlink rebuild eligibility retained. Existing deferred velocity work does not close this gap. Marker-bit29 representation and dependent-body rebuild mapping remain unresolved; no guessed flag mapping or recursive rebuild was added. Testing remains prohibited pending RE and implementation completion.

## Detach override reset integrated at native boundaries (2026-11-12; unbuilt)

Previous goal turn progressed by establishing reset ordering and reconnect lifetime. Added ResetNativeDetachPhysics to advanced_forge.cpp for prepared scenery-grab transactions only. Native detach captures pre-unlink connected bit7. After pose823316D8 at LR82331858, reset runs only if the native parent-reconnect predicate r28 is false; otherwise it runs after82330778 at LR82331870. Both paths precede the native body-connection branch. Generated94 confirms all three exact return addresses, including connection82330B20 at LR823318AC.

The adapter re-resolves salted object identity and private physics ownership after reconnect. Prior connection or current frozen6/forceDynamic20/private-keyframed override causes the existing native rebuild adapter to clear the three mapped overrides and rebuild with create=false. Other native flag bits are preserved. The scoped connection hook skips native82330B20 only after successful reset when connected bit7 is already set, corresponding to H4's additional connected-bit gate; native bit8/type exclusions remain in the original caller. Unrelated objects/call sites retain native behavior. Original velocity deferral and final association-based velocity selection remain in place.

This implements the established override-reset component, not complete detach parity. Still open: H4 attachment-marker flag29 and its rebuild trigger, dependent-child rebuild traversal, reconnect subordinate-path differences, restored transient history and held-editor recovery. No build, test, launch, capture, export or deployment; reported user defects remain unverified.

## Current bridge excludes H4 constraint producers, including indirect calls (2026-11-12; source audit)

Previous goal turn progressed by integrating ordered detach override reset. Re-read complete82388A08/H3821CB8D8 and producer bodies824A4600/8249BE20; their dependency-bit findings were already established and are not new coverage. New evidence closes the earlier indirect-reachability question for the CURRENT imported bridge: CMake compiles forge_bridge.cpp plus isolated/forge_original.cpp. The latter currently contains157 original function bodies. Its only four indirect-call sites belong to82C01FB8; its macro routes every such call to controller_dispatch. Read that dispatcher completely: it accepts only controlled-body address+224 and synthetic targets0x100/0x104, calls native linear/angular velocity callbacks, and otherwise throws. The other computed branch is a local switch/goto in scalar tag-function evaluation, not an arbitrary executable call.

Current isolated code has no references to82938708,824A4600,8249BE20. Rebuild boundary82388A08 is supplied by UpdatePhysicsBody, which invokes the native adapter; no original H4 constructor runs through it. Thus imported H4 code cannot currently create its special attachment29 or constraint dependency9/10/11/12 state, directly or via the original controller's indirect calls. This is stronger than a direct symbol search, but is explicitly bounded to current bridge reachability, not every possible H4 scenery asset.

Implementation consequence: do not add blanket native-child recursion or reinterpret H3 instance flags as H4 dependency flags. Native H3 constraint construction remains authoritative under the compatibility requirement. Authored H4-only marker/constraint equivalence is still a separate asset/behavior question; absence from the imported bridge is not proof of full original-game parity. Reconnect differences and restored editor/history recovery remain active integration gaps. No builds, test execution, extraction/export, launches, captures or deployment.

## Reconnect boolean is not portable between H4 and H3 (2026-11-12; source audit)

Previous goal turn progressed by closing current-bridge indirect constraint reachability. Read complete H4824F5880/generated259,824F5A30/generated228,82482858/generated129,822C3718/generated114,824F59A8/generated108; native820F3A98/generated7 and82348E28/generated86.

Native82330778's true branch calls82348E28: when its TLS192 subsystem is enabled, it gathers data through82349078, updates the object's28-byte entry, invokes the subsystem virtual method at+8, and releases temporary query storage. Its false branch820F3A98 only copies five words of bounds into that entry when enabled; it does not perform the virtual update. H482936D60's false branch824F5880 instead constructs typed object records (824F5A30 sets type1 plus datum), optionally submits type0 for object16 bit7, and calls82482858. The latter gathers spatial bounds/cells, iterates cell keys and invokes82482D50, then updates six-word results. H4's true branch822C3718 either invokes this same broader service after removing prior records or submits through822C36A8; the alternate824F59A8 submits paired records through822C3628. Therefore literal false/true copying would select different work.

Native reconnect argument is intentionally retained. Added a source comment at the narrow82330778 hook to document why. The hook only inserts the already-mapped post-reconnect physics reset; it does not replace spatial services or mutate caller arguments. This resolves the apparent boolean mismatch as a reason to patch, not proof of complete equivalence of the games' spatial subsystems. Stock H3 placement/visibility bookkeeping remains native under the compatibility mandate. No builds, tests, exports, launches, captures or deployment.

## Original all-editor reset callbacks identified (2026-11-12; source audit)

Previous goal turn progressed by resolving nonportable reconnect booleans. Reviewed current grab initialization, coupled held/follow submission, and original8244AF48: persistent unsnapped editor state remains distinct from submitted pose; no new distance or snap workaround was added. Runtime correctness remains untested.

New lifecycle evidence: all direct original constructor/reset82449DD8 callers are8244C210/generated217 and8244C440/generated99; both complete bodies were read. Each loops16 records at TLS28+6892+i*336 and calls the original editor reset.8244C210 additionally initializes32 entries at12268 and related state.8244C440 runs824FF550, variant operations when session category differs from4, resets all16 editors, then clears32 queue entries at12268 and counter12780. This is more than the previously reviewed H3 queue-only82280F98 callback.

Original image references locate8244C210 at821314F8 and8244C440 at82131500 in a contiguous callback table (intervening8244C1F0), plus unwind/function records at82177518/82177520. This establishes the original reset callbacks, not yet their table base or native post-restore invocation equivalence. Do not invent a re-grab reconstruction before resolving whether the matching H4 lifecycle resets ownership instead. Also read8244C000/generated59: it handles removed object identity across player editors, clearing selected/target state through82449ED8/8244A118, distinct from full editor initialization.

Next source task: resolve callback-table owner/slot and actual dispatch for8244C440 against the native lifecycle. Native holder clearing or synthetic re-grab remains unauthorized by this evidence alone. No builds, tests, launches, captures, exports or deployment.

## H4 full-editor reset dispatch mapped to game-state event1 (2026-11-12; source audit)

Previous goal turn progressed by identifying original reset bodies. Original image now establishes vtable base821314D8: object833FE5C8 contains that pointer; registry835718E4 points to the object. The complete accessor822E9AE8/generated14 reads current engine category from TLS28+50364, accepts1..5 and indexes835718E0. Category1 selects833FE5C8. Therefore8244C210 is vtable+32,8244C1F0 +36, and8244C440 +40 (not native H3's offsets).

Read complete823EA4B0/generated152. Event1 stamps TLS28+212 with current time tick, calls823E5420, validates the current registry entry, obtains the engine through822E9AE8 and invokes vtable+40. Event3 instead calls823E7600. This matches the already-reviewed native8221A518 event1 sequence (tick stamp,82216C30, engine+28), whose Forge callback is82280F98. The original H4 counterpart resets all16 editors as well as its queue; native callback only resets the queue. Current private-editor map-initializer cleanup does not by itself cover that event reset.

Implementation still needs to synchronize private original editor reset with native scenery-holder/physics ownership at this event; merely clearing private state and leaving an active native held controller would be incomplete. No arbitrary reconstruction, release transaction or native saved-state mutation was introduced. This establishes a game-state-event boundary only; it does not prove native post-restore calls it. Restore recovery remains separately open. The earlier824500A8 output was truncated and was used only for its inspected singleton-object reference region, not full dispatcher coverage. No tests/builds/launches/captures/deployment.

## Authored-body restoration must remove private keyframing (2026-11-12; unbuilt source)

Previous goal turn progressed by mapping the original reset dispatch. Re-read82449DD8/generated129 completely: it clears selected/target identities and resets editor preferences/distance fields; it does not itself call physics release. Native82280F98 likewise was re-read in full; its queue reset is not a held-object release. Event-level holder/physics synchronization remains unfinished.

Current-source review found a separate concrete restoration defect. RestorePhysics invokes SetRuntimePhysics using saved native frozen/forceDynamic bits. That helper rebuilt only when those bits differed. An H4 transition can force native motion6 through private keyframedOverride without a difference in those native bits, so exit/error restoration could erase metadata while leaving the forced keyframed body alive. Added an explicit restoreAuthoredMotion argument, used by RestorePhysics only. It disables the scoped constructor override for that datum and forces rebuild when private keyframing remains, even when native bits match. The existing force-dynamic setter still owns its own rebuild, avoiding a duplicate. Clear keyframedOverride only after successful native rebuild/setter return; on exception it remains available for retry. This changes the existing stock-physics restoration mechanism, not the unresolved Fixed/Phased persistence policy.

Also exposed a remaining legacy path: ApplyPhysics still uses SetRuntimePhysics's frozen/forceDynamic/disconnect approximation for entries without original held/released ownership, and deferred82283A30 can reapply it. This must be replaced with the original selector/transition at its proper ownership boundary, not carried into completion. No test/build/launch/capture/export/deployment.

## Legacy Phased disconnect and maintenance override removed (2026-11-12; unbuilt)

Previous goal turn progressed by fixing authored-keyframing restoration. Removed ApplyPhysics's non-owned fallback that approximated modes with frozen/forced-dynamic flags and disconnected held Phased objects. ApplyPhysics now invokes the original selector/transition only for established original held/released ownership. Metadata-only entries stay with their native transaction until the explicit original ownership stage; this is an unresolved creation/grab integration gap, not a claimed H4 implementation for those paths.

ChangeNativeSceneryPhysicsMode now always obtains original state before editing, compares original selected state afterwards, and transitions only when the state differs, including valid unheld scenery not previously grabbed. The selector rejects held objects lacking original editor ownership before changing the property. Successful unheld edits retain original released-physics ownership for native settling. Deferred82283A30 no longer reapplies a host mode every frame; it only retires invalid metadata after native maintenance. Exact original settling hook remains.

Renamed the remaining flag setter to RestoreRuntimePhysics and restricted it to stock authored-state restoration. Removed its disconnect option, dead disconnected metadata and unused native-disconnect declaration. It retains the newly required native rebuild for private keyframing. Updated the capture comment/log so metadata capture is not described as mode application. These changes remove unsupported behavior; lifecycle integration is still incomplete and must finish before testing. No build/test/launch/capture/export/deployment.

## Creation shares grab ownership; pre-creation point correction is separate (2026-11-12; source audit)

Previous goal turn progressed by removing legacy physics approximation. Read complete native8227F2A0/generated68 and its direct grab-call peers823C65E0/generated28 and82280948/generated69. Successful local creation runs822836D8, creates through821E2898, reads the new object's variant slot24, then calls8227E810. Existing outer preparation, inner selection/dequeue and post-grab original initialization therefore also cover successful supported scenery creation. No second ownership initializer is needed. Dispatch/decode peers also route through the same public grab; current local-only gates remain.

Read complete H4824506D8/generated169 and824511B0/generated119. H4 requires no held selection for create, checks/adjusts placement through8244EF80, creates the variant/runtime object, then824511B0 releases a differing held selection if necessary, checks eligibility and calls82450E10. This establishes the common grab-stage correspondence. It does not establish initial placement parity.

Read complete8244EF80/generated153 and native822836D8/generated42. H4's nonnull-point branch, gated by its first multiplayer-property bit1, gets the definition radius (fallback1 below original epsilon), queries the monitor physics point, normalizes monitor-minus-requested-point, and moves the requested point toward the monitor by radius or half the separation before its collision placement call824685C8. Native822836D8 obtains native placement radius822835E0 then immediately calls8226E590; it lacks that preceding correction. Both retain their separate budget checks. Remaining source mapping is the pre-creation property gate/radius and collision query argument correspondence, preserving native H3 budgets and creation rules. No guessed distance multiplier was added.

Updated the grab hook comment and TODO to distinguish confirmed common ownership wiring from the actual missing pre-creation step. Ordinary/rejected/retained-attachment ownership paths and event/restore integration still need completion. No builds/tests/launches/captures/exports/deployment.

## Creation collision-placement ABI and pending prefix wiring (2026-11-12; source only)

Previous goal turn only confirmed an already-applied decision, so it was no progress. This turn inspected the current PrepareSpawnPlacement implementation and read the complete original instruction listings of H4 824685C8/generated238, H3 8226E590/generated5, and both creation callers (8244EF80/generated153 and 822836D8/generated42).

The existing, unwired PrepareSpawnPlacement implements the non-phased prefix: original definition-radius epsilon/fallback, monitor-minus-request direction, original 8228ACE8 normalization, and separately single-rounded multiply/add using radius or half-separation. It does not own collision placement, budget checks or the authored Phased gate. H4 multiplayer block0x184 record flags0x1C bit1 means Phased Physics in Forge; H3 block0xEC record flags4 bit1 means Valid Initial Player Spawn. Never map these bits by position. Native definition radius is +4 versus H4 +32; native822835E0 may enlarge its result from model metadata, unlike this H4 caller.

Collision wrapper argument mapping:

| Meaning | H4 824685C8 | H3 8226E590 |
| --- | --- | --- |
| Search radius | f2 (f1 is not consumed by wrapper) | f2 (f1 is not consumed by wrapper) |
| Query selector | r5=1 | r5=1 |
| Maximum attempts | r6=4 | r6=4 |
| Requested point | r7 | r8 |
| Next query argument | r8=0 | r9=0 |
| Next query argument | r9=-1 | r10=-1 |
| Output point | r10 | caller stack+84 |
| Trailing byte | caller stack+87 | caller stack+95 |

H3 caller also supplies controlled-unit datum in r7, but this wrapper does not read it. Do not infer an ignored-object filter from that register alone. Both wrappers copy requested position into a 52-byte query transform and only write the output point on success. Both clamp radius to0.001 and multiply by2 after a failed attempt. These constants were read from the original images using addresses computed from the actual lis/addi instructions: H4 82128C0C/821289F4 and H3 8203B074/82024334. Both pass zero as the nested query f1 (H4 821289E0, H3 82022578). Earlier exploratory address guesses were discarded; they are not evidence.

Nested services differ: H4 calls824686F0 with a global-loaded query descriptor and extra zero fields; native calls8226E6C8 with its native descriptor. Argument correspondence and shared retry arithmetic do not prove full nested collision equivalence. Integration must retain the native query service and native creation budget checks, and explicitly resolve the authored Phased gate rather than silently bypass collision. The prefix is still unwired. No export, build, test, launch, capture or deployment was performed.

## Native scenery creation prefix connected (2026-11-12; unbuilt)

Previous turn progressed by mapping the collision-wrapper ABI. Read native8227F2A0 completely again and checked the actual image instructions at8227F31C..8227F340 and822836D8..82283720. Native creation supplies tag inr3, player inr4 and optional point inr5; the local branch copies the point to its stack, obtains player40 controlled-unit datum, then calls822836D8 at8227F340. The placement helper calls radius822835E0 at822836F8. Native scen schema confirms definition type0 values6/10 for scenery/crates.

Added a scoped native-create record retaining original tag/player/non-null-point status. At the exact local creation caller8227F344, supported local scenery now invokes PrepareSpawnPlacement with native physics-point counterpart820AFA98 and definition+4 radius. It writes the adjusted point only after the full bridge computation succeeds. The exact radius return822836FC uses the prepared original definition radius rather than native model-enlarged radius. Other callers/object types retain the native path. Original822836D8 still owns collision query/result propagation and budget rejection; original8227F2A0 still owns allocation, notifications and the existing shared grab initializer. Scope restoration is RAII and does not serialize editor metadata.

Stock H3 has no authored Phased-in-Forge tag bit. This connects the non-phased branch for these native definitions, without misreading H3's Valid Initial Player Spawn flag or adding an invented flag. It does not implement an imported H4 authored-phased default; that remains a separate metadata/compatibility gap. Runtime physics-menu persistence is also still unresolved. Source inspection confirmed NativePhysicsPoint copies PPC context and uses scoped scratch memory, and no duplicate hooks for these three entries exist in halo3mp/src. No build, test, export, launch, capture or deployment. Reported snap/pull-away/re-grab defects remain unverified.

## Retained attachment grab now keeps original ownership (2026-11-12; unbuilt)

Previous turn progressed by connecting the creation prefix. Inspected the current coupled held stage, native scene collector, RunHeldStage and complete isolated8244AF48. Persistent unsnapped pose remains separate from controller submission; the follow function writes its held/monitor ray exclusions before calling824F5CF0, so stale native identities are not consumed by that branch. No change to snap scoring/detachment thresholds was justified by this audit.

Read complete original82450E10/generated43,8244A180/generated195 and8244A2A0/generated58. Grab's attachment predicate optionally calls82939170, but both outcomes converge on selection82449ED8, queue removal8244F5D8, physics selector/transition8244A180/8244A2A0 and body-dependent grab placement. Neither selector nor transition rejects a parented selected object. The current adapter incorrectly skipped original selection for a retained parent, rejected held-parent transitions, and required an unparented object when activating contact ownership. That disagreed with original control flow independently of the still-open parent-constraint differences.

Removed those three exclusions. Native committed holder/dequeue validation still applies. Retained-parent grabs now run the same original selection, physics and placement stages. Existing RebuildSceneryPhysics routes through native parent-aware create/rebuild services; no H4 dependency flags or new recursive constraint rebuild is introduced. Activation allows an attached held object while continuing to require a valid unparented monitor and local owner. The existing held tick already allows attached ownership, skips movement/follow via NativeCoupledSceneryEligible, and refreshes the parent-aware origin. Unparented-only contact/controller readers remain restricted to the coupled movement branch.

This closes the explicit retained-parent ownership exclusion in source, not full H4 constraint equivalence or restored-state recovery. No build/test/export/launch/capture/deployment; the reported manipulation defects remain unverified.

## Event1 reset connected without an invented release (2026-11-12; unbuilt)

Previous turn progressed by connecting retained-parent grab ownership. Read complete native82280F98/generated33,821E4028/generated22,821E0D20/generated12,821E4788/generated61 and82280D80/generated37, plus original82449DD8/generated129. The event callback's variant reconciliation can move/create/delete objects; budget recomputation and the multiplayer player-count flag do not clear the sixteen holder slots. Native map initialization separately writes sentinel-1 to engine57752/e198 and initializes its distance cache at57816/e1D8. Original H4 event callback8244C440 invokes82449DD8 for all sixteen editors after variant bookkeeping. That reset clears selected/target identities and preferences but does not perform a release or physics rebuild.

Added an after-original82280F98 hook for active local H4 scenery editing. It runs actual82449DD8 against each existing private editor's prior336 bytes, preserving fields the original reset does not touch. It clears a native holder only when its current variant datum matches that editor's selected scenery/crate, and mirrors original reset distance into the native cache. Stock weapon/vehicle holders are untouched. The private contact ownership and anchor view are revoked; player input/contact-normal history is retained. Existing physics restoration metadata is retained without applying a new release transition. Native object deletion/variant bookkeeping runs first, so the hook revalidates the current selected object rather than relying on pre-callback pointers. No whole editor allocation is zeroed.

This is the source-mapped event1 reset boundary, not a workaround for unknown restored holders. State replacement821ABAB0 still invalidates private ownership and has a separately unresolved recovery path. Direct caller inspection found all seven calls within five functions; the displayed combined listing was truncated, so no claim of complete caller coverage is made. The inspected paths load/replace state and call post-restore821E68B0; that alone does not establish event1 delivery. No tests, builds, launches, captures, exports or deployment.

## Marker footprint edge clipping corrected (2026-11-12; unbuilt)

Previous turn progressed by connecting event1 reset. Inspected current D3D12SceneMarkers Observe/Finish/Capture/Draw, the command processor's normalized depth-use observation/scissor calculation, and the material kernel's output/depth bounds. The existing kernel samples a finite square around center/radius and clips individual output pixels. Draw nevertheless rejected every marker whose center had abs(NDC X/Y)>1. That discards a partially visible marker quad at a view edge before pixel clipping can run.

Replaced that center rejection with rectangle-footprint intersection against the current normalized output view, retaining existing dispatch lower/upper clipping and shader ABI. Added finite checks for all four clip coordinates, divided XY, and projected centers before integer dispatch-coordinate conversion; finite inputs can still overflow during matrix multiplication. No new shader source or compiled material was generated. This fixes a host adapter clipping inconsistency in source, not a claim of completed original rendering parity.

The separate tiled-depth gap remains: Capture still rejects viewports beyond resource bounds and stores one latest depth mapping. Bounds are not clear/transfer/scissor provenance. This turn did not remove that protection or claim tile assembly. No build, test, shader compilation, launch, capture, export or deployment.

## Actual host depth-clear coverage recorded (2026-11-12; unbuilt)

Previous turn progressed by correcting marker footprint clipping. Inspected the actual D3D12 clear/transfer submission sites and the render-target allocation wrapper. Added per-allocation bounded CPU rectangle metadata to D3D12RenderTarget. RecordDepthClear receives the exact host-scaled clear_rect immediately after the depth+stencil clear is queued, against that clear's destination target. Stencil-only transfer clears do not count. Rectangles are clamped to the concrete allocation, contained duplicates are discarded, and disjoint rectangles are not promoted to a bounding box. At64 retained entries the tracker discards prior evidence and retains the new clear rather than accumulating metadata indefinitely or asserting an unproven union.

Ownership transfers currently invalidate this evidence for the destination before their submission. This deliberately does not claim that color/depth/MSAA reinterpretation preserves the source rectangle mapping. GetSceneDepthClearCoverage uses the same explicit previous-depth capture override and bound-target selection as GetSceneDepthResource, avoiding an identity mismatch at target transitions. Metadata is owned by the existing allocation; no additional texture, file, log or cache copy was introduced.

The getter is not yet consumed by marker Capture/Draw. This is implementation of the previously missing actual-clear provenance boundary, not completed tiled coverage. Next required work remains mapping transfer-derived valid regions, collecting exact scene scissor regions, retaining all required depth tiles, and consuming the resulting nonoverlapping coverage without duplicate additive marker output. Initial source review caught and corrected declaration ordering in the transfer invalidation block. No build, test, shader compilation, export, launch, capture or deployment.

## Scene scissor coverage consumed by marker shader (2026-11-12; unbuilt)

Previous turn progressed by adding actual-clear provenance. The command processor now passes its existing host-scaled Scissor (the one used by UpdateFixedFunctionState) into successful scene depth observations. Observations retain an exact half-open rectangle union, resetting it on frame/resource change and after Finish. Capture intersects that union with the same selected depth allocation's known-clear rectangles. A bounded subtraction algorithm keeps the resulting regions nonoverlapping rather than promoting disconnected regions to a bounding box. Missing coverage rejects the replacement capture and invalidates the older snapshot instead of reusing stale depth.

The marker kernel now receives one96-byte/24-DWORD constant record including a host-depth coverage rectangle. It checks continuous mapped depth coordinates against the half-open rectangle before sampling. Draw submits each disjoint region with a UAV barrier, so the same output pixel cannot receive additive marker light from two overlapping observation rectangles. Existing output-view and resource bounds checks remain. CPU coverage retention is capped at256 regions; overflow retains only proven subsets and is not claimed as complete coverage.

Updated material pack version H4MP2 ->3, native loader, offline compiler argument contract and pack script together. An old compiler rejects the extra ABI argument rather than silently producing an old shader inside a version3 package. No generated material or executable was rebuilt. AFM3 marker-record format is unchanged.

Remaining: transfer-derived coverage, partial-resource viewport mapping and multiple completed tiles. Transfer invalidation currently loses coverage conservatively and can suppress markers; this is an unfinished implementation, not a deployable rendering result. The existing single-depth snapshot remains. No build/test/shader compilation/export/launch/capture/deployment.

## Matching depth transfer coverage propagated (2026-11-12; unbuilt)

Previous turn progressed by connecting exact scissor coverage and material ABI3. Inspected TransferAddressConstant, transfer shader coordinate construction, Transfer rectangle generation, merged-source identity rules and the actual transfer draw submission. For same-format/same-MSAA depth-to-depth mode, pixel/sample coordinates within each tile are unchanged; source tile index is (destination row*pitch + column + destinationBase-sourceBase) masked by EDRAM tile count, followed by source-pitch quotient/remainder. The existing shader scales tile sample dimensions by draw resolution and shifts X for4x MSAA, Y for2x/4x. No color/depth half-column swap applies to this selected branch.

Added RecordMatchingDepthTransfer with those exact tile rules and actual emitted transfer rectangles. Coverage is copied from the source before invalidating destination regions, including a possible self-source. It is recorded only after the transfer draw is queued; descriptor/pipeline/vertex-buffer failures do not gain positive coverage. Merged draws require identical sources and shader keys. Other depth-writing modes invalidate only their affected rectangle instead of throwing away all initialization evidence for the allocation. Stencil-only passes leave depth evidence unchanged.

Rectangle tracking now coalesces touching/overlapping rectangles only when they have identical orthogonal spans (or containment), which preserves exact unions without bridging holes. This keeps complete tiled rows from exhausting the64-record retention bound. Overflow still loses evidence conservatively rather than claiming uninitialized pixels are valid. Source review corrected a local-key scope reference before completion of the edit.

Remaining transfer mappings: differing MSAA/format, color-to-depth, and combined host-depth-source modes. Multiple depth captures and partial-resource viewport support remain open. This source change has not been built or tested, and no FPS/visual parity is claimed. No shader compilation, generated pack, launch, capture or deployment.


## Depth MSAA transfer and marker sample selection (2026-11-12; unbuilt)

Previous goal turn was no progress: it reconfirmed an existing exporter exclusion. Continued implementation after inspecting the current source. Read the complete same-BPP MSAA coordinate branches in D3D12RenderTargetCache transfer shader generation: 4x transfers move horizontal pixel/sample bits, 2x transfers move vertical bits, and both depth formats use 32-bit samples. RecordDepthTransfer now maps source and destination tile pixel dimensions independently, retaining physical base/pitch/wrap addressing. Bounds round inward when multiple source pixels supply one destination pixel, so only pixels with all required source samples covered gain positive evidence. Adjacent partial regions may still lose coverage conservatively; no completeness claim. Color/depth half-column swaps and combined host-depth transfers remain unsupported by this tracker.

The transfer shader and pipeline_cache.cpp SampleMask=0b1001 independently establish that emulated 2x uses host samples0/3. Marker visibility previously averaged all four samples. Capture now validates the guest/host sample-count pairing, retains the active sample mask with the depth snapshot, and Draw passes it to the material kernel. The kernel samples only enabled indices within the actual texture sample count and normalizes by the number used. Single-sample behavior is unchanged. This updates the already-unbuilt material ABI3 source together with its CPU constants, without generating another package or changing AFM3 records.

Reviewed enum values, declarations, call sites and affected source after editing. This is source inspection only, not compilation, executable parity or visual verification. Multiple captures, partial-resource viewports and the other listed lifecycle/physics gaps remain unfinished. No build, test, shader compilation, export, launch, capture or deployment.


## Failure after final camera publication (2026-11-12; unbuilt)

Previous goal turn progressed by implementing depth-transfer/sample selection. This turn read complete native82158040/generated22,82157788/generated46,82157688/generated52,825C13B8/generated53 and82182D90/generated103.82158040 can append descriptors instead of submitting immediately; a successful deferred list is not an abandoned list.825C13B8 finalizes the recording, with the inline-storage branch independently setting state10941 bit5 when command count exceeds0x100000. It records failed status7 / HRESULT8007000E rather than successful status1/zero, then clears state13500.82182D90 resets cursor/limit to the scratch area on prior or new allocation failure and preserves/sets the same bit. Both can happen after the last camera hook, so checking failure only at camera publication did not cover final failure.

Added post-original hooks at82182D90 and825C13B8. They clear queued host marker snapshots only when the native state is the exact global stream used by the marker producer and its original failure bit is set. They preserve original return registers, native commands and flags; renderer logical invalidation remains deferred to its own thread. Successful allocation/list finalization does not trigger cleanup. Read the inserted source after editing; no executable verification.

This covers the newly traced terminal-failure observation boundary, not all successful list lifetimes. Recorded-list release/reuse/replay ownership remains open. Existing global failure invalidation intentionally discards marker visibility across views rather than retaining a stale capture. No test, build, export, launch, capture or deployment. The required manipulation, physics and tiled-depth gaps remain open.


## Implementation/build pivot (2026-11-12)

User parked further RE and rejected excessive verification. Built the existing integrated implementation in the retained SDK build (0.87GiB before build), with TEMP/TMP confined to work/build-temp. First link failed because marker QueueSceneMarkers/DiscardQueuedSceneMarkers were direct non-exported GPU-plugin calls. Changed queue/cancel/discard to virtual interface dispatch, matching the plugin ownership boundary, then rebuilt successfully. Native source, H4 bridge and renderer compiled; this is not interaction verification. Exported 129 AFM3 bindings (61,032 bytes), rebuilt both H4MP3 shader variants and staged matching private data beside the candidate. No new runtime installation, launch or deployment. Exact candidate hashes in work/build-temp/forge-candidate.json. Next work is practical interaction checking and fixes; prior research gaps remain documented rather than gates to more research.
