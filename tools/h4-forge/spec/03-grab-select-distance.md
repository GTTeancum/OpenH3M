# 03 — Aim selection, grab/re-grab, spawn placement and hold distance

Clean-room behavioural specification derived by static reading of the Halo 4
statically recompiled functions in
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\forge_original.cpp`
and, for callers not present there, the generated sources in
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\generated\`.
Nothing was built, run or executed. Literal constants were read from the original
decoded image `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\h4-image.bin`
(file offset = address − 0x82000000). Configuration values come from the
verified Ravine Forge-globals extraction
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\full-re-globals.json`.

Function addresses are cited per rule as provenance. Descriptive names are this
document's; the original has no symbols.

Conventions used below:

- "Editor" is the per-player Forge editor record (336 bytes, one per player slot,
  16 slots). Field offsets are given only to make provenance traceable; an
  implementation is free to use any layout.
- "Monitor" is the player's controlled unit (the Forge monitor biped).
- "Physics point" of an object is its selected physics body's centre (falling back
  to the object's stored centre), as returned by 82260B58. It is distinct from the
  object's origin (8225EA20) and from the eye/aim origin (822B79A0).
- "Runtime radius" is the live object bounding-sphere radius (object record +76).
  "Definition radius" is the tag's authored bounding radius (tag +32). They are
  different values and are used in different rules.
- All arithmetic in the original is single precision. Where order of rounding
  matters for exact parity it is noted; otherwise only the behaviour is given.
- Clamp operations in the original are built from "select if difference ≥ 0"
  steps. A NaN difference selects the second operand. Where that matters it is
  stated.

---

## 1. Editor state

### 1.1 Fields relevant to this section

| Name (this spec) | Orig. offset | Meaning |
| --- | --- | --- |
| held | +0 | Datum of the held object, or none (−1). |
| magnetTarget | +4 | Datum of the current magnet/snap target, or none. |
| heldOrigin | +8..+16 | Held object's origin (three floats), refreshed from the object. |
| flag20 | +20 | Integer, set to 1 by the constructor only. Meaning not established. |
| aimed | +24 | Object currently under the aim ray that passes the target filter, or none. |
| holdDistance | +28 | Current hold ("focal") distance. |
| field32 | +32 | Float, zeroed at construct/release. Consumer not in this section. |
| offsetScale | +36 | Scale applied to the grab offset; decays toward 0 each held tick. |
| offsetDecay | +40 | Amount subtracted from offsetScale per held tick. |
| aimPoint | +44..+52 | Last aim-ray hit point, or ray endpoint on a miss. |
| grabOffset | +56..+64 | Grab-offset vector (written by physics/rotation stages, section 04/05). |
| heldPoint | +68..+76 | Snapshot of the held object's physics point taken at grab. |
| bytes80/81 | +80, +81 | Flags cleared at construct and release; +81 also cleared on every selection. |
| magnetEnabled | +82 | Magnet preference; cleared only by the constructor. |
| byte83 | +83 | Mode-switch flag; cleared only by the constructor. |
| pose | +84..+135 | Persistent (unsnapped) held transform: scale, 3×3 basis, position at +124. |
| rotationSnapMode | +224 | Cleared only by the constructor. |
| field228 | +228 | Set to 1.0 at construct and release. |
| field232 | +232 | Set to 0 at construct and release. |
| ids256/260/264 | +256, +260, +264 | Three object identities set to none at construct and release. +264 is also written by the per-tick target filter (1.3). |
| sensitivity | +268 | Integer, constructor default 2. |
| byte272 | +272 | Byte, constructor default 7. |
| verticalAim | +276 | Vertical (Z) component of the unit direction monitor→held point (2.4). |
| restoreFlag | +280 | Cleared on every selection call. |

Per-player input fields (player record, not editor): `distanceInputActive`
(+1888), `distanceInput` (+1892), `rollInput` (+1896), `yawInput` (+1900),
`pitchInput` (+1904).

### 1.2 Construction (82449DD8)

Run for every editor slot when the Forge session state is initialised
(caller 8244C210) and again for every slot from the variant-reset event callback
(8244C440). It does not clear the whole record. It sets:

- held, magnetTarget, aimed, ids256/260/264 := none.
- flag20 := 1.
- holdDistance := default focal distance (rule D0, section 4.1).
- field32, offsetScale, offsetDecay, verticalAim, field232 := 0.
- grabOffset := (0,0,0); heldPoint := (0,0,0). (Both copied from the original's
  global zero vector at 82125110.)
- bytes +80, +81, magnetEnabled (+82), byte83 := 0; rotationSnapMode (+224) := 0.
- field228 := 1.0; sensitivity := 2; byte272 := 7.
- Emits lifecycle event `forge_mode_init` (string at 82131288).

Not written by construction: heldOrigin, aimPoint, pose, restoreFlag and any
field not listed. These must hold whatever the backing storage held before; the
next aim-ray update fills aimPoint (section 2 ordering requirement).

### 1.3 Release reset and selection (82449ED8) — "select held object"

Inputs: editor, player, newHeld (a datum or none).

1. Capture the previous held and previous magnetTarget (for visibility, step 5).
2. **Release reset** — only when previous held ≠ newHeld **and** newHeld is none:
   - held, magnetTarget, aimed := none; verticalAim := 0.
   - holdDistance := default focal distance (D0).
   - field32, offsetScale, offsetDecay := 0; grabOffset, heldPoint := zero vector.
   - bytes80, bytes81 := 0; field228 := 1.0; field232 := 0; ids256/260/264 := none.
   - Not touched: magnetEnabled, byte83, rotationSnapMode, sensitivity, byte272,
     flag20, aimPoint, pose, heldOrigin.
3. Always: held := newHeld. If newHeld is valid, heldOrigin := the object's origin
   (8225EA20; for a parented object, the origin transformed through its parent
   node).
4. Always: restoreFlag := 0; byte81 := 0.
5. If the player is a local player (822ED938):
   - Refresh marker visibility from the previous held/target pair (825826B0).
   - If newHeld is valid: let P = held object's physics point, P′ = P +
     grabOffset × offsetScale (component-wise, current stored values). If the
     monitor exists, let Q = monitor's physics point; normalise (P′ − Q) (see
     normalisation rule N below) and store its Z component in verticalAim.
   - Emit `forge_mode_pickup_item` (82131298) if newHeld is valid, otherwise
     `forge_mode_drop_item` (821312B0).

Consequences:

- Switching directly from object A to object B (newHeld valid) does **not** run
  the reset block. Distance, offsets, etc. are kept until the grab stage
  overwrites the ones it owns (section 2.3).
- Calling with the same datum as currently held only refreshes heldOrigin,
  restoreFlag/byte81, visibility and the event.

**Normalisation rule N (8228ACE8):** length L = √(x²+y²+z²). If |L| < 0.0001 the
vector is left unchanged and the result length is reported as 0. Otherwise the
vector is divided by L and L is reported.

### 1.4 Set magnet target (8244A118)

Sets magnetTarget := given datum and, for a local player, refreshes marker
visibility from the previous held/target pair. No other state changes. (Despite
its use in deletion, this is a plain setter.)

### 1.5 Object deleted (8244C000)

For each of the 16 player slots that is in use, in slot order:

1. If aimed = deleted object → aimed := none.
2. If held = deleted object → run selection with none (1.3, i.e. the release
   reset, **not** the full release transaction with physics restoration), then
   raise game notification 0x08000000 (822FF770).
3. If magnetTarget = deleted object → set magnet target to none (1.4).

After the loop, unless the session is in the state where game-type value 4
applies (session byte flags + type 4 check in the original), the deleted object is
passed to a removal-queue routine (8244F740, arguments −1, 1). Its semantics are
outside this section.

---

## 2. Aim selection

### 2.1 Per-tick ordering (caller 8244D0E0)

Each tick, per player:

1. If the player is not in Forge edit eligibility (82449A60 false): aimed := none,
   and for a local player clear the aim-based marker visibility (82452588 with
   none). Skip the rest.
2. Run the aim ray (2.2). This writes aimPoint every tick and yields a raw hit.
3. Filter the hit into a candidate target (2.3) and store it in aimed.
4. For a local player, update marker visibility for (held if any, else aimed)
   (82452588).
5. Held-object work (section 4.4) runs after this.
6. Finally, if an object is held, refresh heldOrigin from the object (8225EA20).

The aim ray must run before any grab is initialised: grab initialisation reads
aimPoint (2.4/2.3). The grab entry points do not re-run the ray themselves; they
use the stored aimPoint from the latest tick.

### 2.2 Aim ray (8244C740)

1. **Origin** O: the monitor's eye/aim origin (822B79A0 — eye/marker point with
   attachment, seat and view corrections). Not the physics point.
2. **Direction** V: the monitor's current view/aim vector (unit +1260). The ray
   routine does not normalise it. Every writer of that vector in the unit aim
   update (82948A80) gives a direction: an object forward basis vector, a copy
   of the look vector, or the output of rotation/interpolation helpers (8223E130,
   8294D6F8) that normalise through 8228ACE8. So it is unit length in practice.
   An implementation should normalise its own aim vector.
3. **Range** R = max(holdDistance, grabRange), where grabRange is Forge-globals
   field +0x44 if it is > 0.0001, else the literal 5.0 (also 5.0 if the globals
   tag is unavailable). With Ravine's 7.5 and the default hold distance 7.5, an
   un-held ray is 7.5 long; while holding, the ray reaches at least the current
   hold distance.
4. **Endpoint** E = O + V × R (each product rounded, then added).
5. **Exclusions**: all bipeds whose definition has fewer than one seat (unit
   definition seat-block count < 1), in object-header order, at most 64 entries
   (iterator 82268800 with type mask "biped", no required header flags). In
   practice this makes every monitor and Spartan transparent to the ray. The held
   object is **not** in the exclusion list.
6. **Query** (82417550): collision layer 26, request flags 0x00000009_0000179F,
   segment O→E, the exclusion list. Whether a world/shape element is considered
   at all is decided first by the layer predicate (2.5).
7. **Result**:
   - Hit: aimPoint := hit point. If the hit category is 4 (object), the raw hit
     object is the hit datum; any other category (structure etc.) gives "no
     object". Returns true.
   - Miss: aimPoint := E. Returns false; no object.

The routine also reads the held object's variant record into a temporary that is
then overwritten without use; it has no behavioural effect.

### 2.3 Target filter (8244D0E0, 8244D154–8244D3E8)

Given the raw hit object H (only if the ray returned true and H is valid;
otherwise the target is none):

1. **Parent redirection.** If H has a parent: walk the parent chain to the root.
   The target becomes the root unless both (a) the root passes predicate 8298E798
   (argument 0) and (b) H's tag has flag bit 0 of its byte at tag +28 clear; in
   that case H itself stays the target.
2. **Forge eligibility** (starts true):
   - Target must have a Forge variant slot (object +62 ≠ 0xFFFF), else ineligible.
   - If the target has a parent, its root must pass 8298E798(root, 0).
   - Its variant record's palette/quota index must be valid, and the palette entry
     (resolved via 823C37A0, entry flags byte +4) must have bit 0 clear.
3. If eligible and the variant record's byte +60 is non-zero and object +486 ≠
   0xFFFF, the editor's ids264 := target (purpose not established).
4. **Type/flag gate.** The target survives only if its object type is in the set
   {0, 1, 2, 3, 6, 7, 8, 9, 11} (mask 0xBCF), the object's flag word +364 has
   mask 0x4 clear, and it was eligible in step 2. Otherwise target := none.
   With the Halo 4 (Gen4) object-type numbering these are biped, vehicle, weapon,
   equipment, scenery, machine, control, dispenser and crate; excluded are
   terminal, projectile, sound scenery, creature, giant, effect scenery and
   spawner. (Numbering reference only: Halo 3's enum numbers the same kinds 0,
   1, 2, 3, 6, 7, 8 and crate 10, and has no dispenser.)
5. **The +364 mask-0x4 flag means "this object has been killed".** It is set
   exactly once by the object-death routine 82999408 (and its unit counterpart
   829DAEC0), which returns at once if the flag is already set and goes on to
   destroy the object (ending in object deletion 82936B78). Two unit/respawn
   routines (82A11088, 829B1C78) clear it. Behaviour: a killed object is never a
   target. If the held object is killed (for example a destructible piece taking
   lethal damage), the input producer 8244CAC8 emits the release event (event 4)
   for it on the next pass, with no button press, so it drops before it is
   deleted.
6. aimed := target.

### 2.3a Held object and the aim ray

The held object is not on the exclusion list, and the request's object bit
(bit 0 of the low flag word, set in 0x179F) admits object shapes. The object
filter callback (82416640) rejects an object only when it, or an ancestor, is on
the exclusion list; with the aim ray's high flag word (9) neither of its optional
extra gates applies. Object candidates are then tested precisely against their
collision model (82416DF8 → 82416120), nearest first. Therefore the held object
is hit by the aim ray whenever its physics shapes pass the layer table (2.4) for
row 26.

**Layer of a held piece (round 3).** Each body's collision filter word is
built in the body constructor 824A39A0 as (system group << 16) | layer.
System group = the root object's index + 1, or 2050 when the layer is 12.
Grabbing selects physics state 1 (state 2 for a Phased piece held locally),
and both set the object's "force dynamic" flag 0x200000 (spec 04 §4.3). For
every body whose authored motion is Fixed (5), the constructor then overrides
the layer with this flag set: **layer 17 for scenery (type 6), layer 4 for any
other type**. Motion becomes Dynamic (3), or Keyframed (4) when 0x400000 is
also set. For placed, unheld fixed scenery the per-type chooser 824A2A48 gives
layer 1 (17 when 0x200000 is set). The rigid-body builder 824A1C30 then passes
the chooser's result through 824ADCC8 together with a layer set derived from
the shape data (824A1F28), so the final placed layer also depends on map data.
The held override above is applied after that, in 824A39A0, and is not
data-dependent. An object flag 0x80 forces layer 18 with Fixed motion. The general layer choosers (824A2A48 and 82465E48) only produce layers
1, 3, 4, 5, 6, 8, 9, 11, 13, 14, 15, 17 and 18. Ravine's row 26 (0xCBFEFFFB)
accepts all of them; it rejects only 2, 16, 26, 28 and 29. Its group bits are
zero, so the same-group rule never applies.

**Result: in Halo 4 the aim ray hits the held piece**, with exactly one
exception among Ravine's Forge objects (Round 4). Ravine's Forge blocks are tag
group `bloc` with object type 11 (crate), not scenery, so a held fixed-body block
is on layer 4 and a held fixed-body scenery object is on layer 17. While holding, each tick, before the held-object update moves the
piece:

- The ray runs from the monitor eye along the view direction, out to
  max(holdDistance, grabRange).
- aimPoint = the nearest point on that segment that lies on any accepted
  structure geometry or on the collision model of any non-excluded object,
  **including the held piece at its pose from the end of the previous tick**.
  If nothing is hit, aimPoint is the segment end.
- When the view line passes through the held piece, aimPoint is the near
  surface of the held piece facing the eye, unless something else lies in
  front of it.
- aimed becomes the held piece (it passes the 2.3 filter) or whatever was
  hit. While holding, aimed only drives marker visibility, and visibility
  prefers the held object, so this has no visible effect.

While holding, aimPoint is consumed only by the duplicate action (event 10). That
action releases the held object and requests the copy at this aimPoint, which is
typically on the held piece's near surface. 5.2 then pulls the copy toward the
player and searches for free space. Grab and create are issued only when nothing
is held.

Data dependency (resolved for Ravine in Round 4): the final layer of an
unheld body, and of a held body whose authored motion is not Fixed, also folds
in the rigid body's RuntimeHavokGroupMask through 824ADCC8, so it can be a
layer the choosers never produce (Ravine: 0, 2, 24, 28). Round 4 lists the
result per object. The one held exception is fw_one_way_door_small (layer 28,
not hit by the ray).

### 2.4 Layer predicate (82D813F8)

Inputs: query filter word q (for the aim ray, layer 26 in its low bits) and the
shape's filter word s. Let group(x) = upper 16 bits, layer(x) = low 5 bits,
sub(x) = bits 5–9, noCollideWith(x) = bits 10–14.

- If group(q) = group(s) and group(q) ≠ 0 (same non-zero system group): reject if
  noCollideWith(s) = sub(q) or noCollideWith(q) = sub(s); otherwise accept.
- Otherwise: accept iff bit layer(s) is set in table row layer(q). The 32-row
  table is source data from the collision-filter tag (`hcfd`, filter +52). For
  Ravine, row 26 is 0xCBFEFFFB, rejecting shape layers 2, 16, 26, 28, 29.

The aim ray's group bits are zero, so only the table path applies to it.

---

## 3. Grab and re-grab

### 3.1 Grab entry (824511B0)

Called by the grab event handler (event 3, dispatcher 824500A8, after 8244EE00,
outside session type 4) with the packet's object, and by creation (5.1).

The grab event's only producer (input routine 8244CAC8) emits it when the grab
button is pressed, nothing is held, and aimed is valid; the packet object is
aimed. The same button with an object held emits the release event (event 4).
Creation refuses while holding. So in practice step 1 below never sees a
different held object.

1. If something is held and it is not the requested object, the original calls
   the release event (82451500) **with the requested object**, not the held one.
   That release event acts only when its argument equals the held datum, so in
   this case it performs no release and only raises notification 827FB1A8. (The
   earlier findings describe this step as "relinquishing" the old object; the
   code does not do that. See open question Q1.)
2. Validate ownership (82451908): player is Forge-eligible; object resolves; object
   has a variant slot; and the object is not held by a different player (its
   current holder, 82451F10, is none or this player).
3. Validate physics (824519C0): if the object resolves, it must have a physics
   instance with at least one body. An unresolvable object passes this check
   (the resolver leaves the "true" register intact), but step 2 has already
   rejected it.
4. If both pass, run grab initialisation (3.2).

### 3.2 Grab initialisation (82450E10)

In order:

1. Read and discard the object's variant record (no effect).
2. **Detach from parent.** Walk to the root. If the object reports an attachment
   (822BE858 ≠ none), or the root passes 8298E798(root, 0), and the root differs
   from the object, detach it (82939170) and clear object flag 0x01000000 in its
   64-bit flags at +16.
3. **Type-specific clean-up** (non-scenery): types 0/1 run an occupant routine
   (8295D1A8 / 8297E5F8 with 12); type 9 under a definition flag removes up to N
   attached objects listed at +1448. Not needed for scenery/crates.
4. 8244F838(0, object) (purpose not established).
5. **Select**: run 1.3 with the object (no reset block, since the new datum is
   valid).
6. Raise notification 0x08000000; dequeue the object from the pending-release
   queue (8244F5D8, −1); choose and apply the physics state (8244A180 →
   8244A2A0; section 05).
7. If the object's physics instance now has zero bodies, stop here: pose,
   holdDistance and heldPoint are left unchanged.
8. **Pose**: pose := the object's current transform (selected physics-body
   transform, else object transform; 82452820). Then constrain pose.position
   with the variant bounds (3.3). Scale and basis are untouched.
9. **Initial hold distance** (size-aware policy):
   - M = monitor's physics point; F = monitor's forward vector (82243068: the
     optional attachment-orientation service if enabled on the monitor, else the
     object's forward basis vector).
   - projected = F · (aimPoint − M). (Original order: Y product, then fused Z add,
     then fused X add; each component difference rounded first.)
   - holdDistance := clampHoldDistance(projected) (rule D, 4.2), which also
     applies any active push/pull input this tick.
   - This is a projection onto the forward axis, not a Euclidean distance, and it
     uses the stored aimPoint — not the object's position or the clamped pose.
10. heldPoint := the object's physics point (taken after the physics state
    change).
11. For a local holder, send a replication message to each recipient (822E8E20 /
    829449D0). Out of scope.

### 3.3 Pose constraint (82282580)

Bounds are the variant's world box (variant +696: xmin, xmax, ymin, ymax, zmin,
zmax). For each axis independently: if min > p → p := min; else if max < p →
p := max; else unchanged. Because the min test comes first, an inverted box
yields min. A NaN coordinate fails both tests and passes through unchanged. Only
the position is constrained. The same routine is used by the coordinate-edit
event (824500A8 event 13) and the held update.

### 3.4 Re-grab

There is no separate re-grab path. Releasing (release transaction 82451250, which
first runs the reset in 1.3) restores holdDistance to the default; the next grab
runs 3.1–3.2 again from the current aimPoint. The initial distance is therefore
recomputed from the current aim for every grab; nothing from the previous hold
distance carries over. Preferences (magnetEnabled, rotationSnapMode,
sensitivity) persist across release and re-grab.

### 3.5 Release (summary only)

Release event 82451500 acts only if its object equals held. It raises
notification 0x08000000, optionally restores a saved pose if restoreFlag is set
(8281EF50 with saved fields at editor +288/+312/+324), then runs the release
transaction 82451250, which resets via 1.3 and then applies placement/physics
(section 05).

---

## 4. Hold distance (push/pull)

### 4.1 Configuration readers

- **D0 default distance** (82452AD8): Forge-globals +0x48 if > 0.0001, else 5.0.
- **Multiplier** (82452C28): Forge-globals +0x54 if > 0.0001, else 5.0.
- **Maximum** (82452BB8): Forge-globals +0x50 if > 0.0001, else 22.0.

The Forge-globals tag is reached through a global tag reference (pointer at
8405D340; tag group +492, tag index +504; resolver 82340E60). If it is missing, all
three fall back to the literals.

### 4.2 Rule D — clamp and push/pull (82452738)

Inputs: player, held object (or none), current distance d.

- **No held object**: result = D0. (Input is ignored.)
- **Held object**:
  1. If the player's distanceInputActive is set: d := d − distanceInput × 0.3
     (single fused multiply-subtract). Positive input pulls in, negative pushes
     out (see Q5 for physical stick direction).
  2. r = the held object's runtime radius.
  3. Lower bound L = max(r × 1.25, r + 0.4). (Ties pick r + 0.4; numerically the
     same.) So for r < 1.6 the margin is 0.4, above it 25 %.
  4. Upper bound U = min(multiplier × L, maximum). With Ravine values, U =
     min(5L, 22).
  5. result = min(max(d, L), U). Order matters: when L > U (large pieces, e.g.
     r > 17.6 with Ravine values), the result is U, i.e. the maximum wins over the
     clearance minimum.
  6. NaN d yields L at step 5's inner max, then min(L, U).

Forge-globals field +0x4C ("minimum focal distance", Ravine 2.0) is **not** read
here. The offset +76 read by this rule belongs to the held object record (runtime
radius), not to the configuration. Its only consumer is the alternate held path
(4.4, switch byte 8407EFFA), which the image default does not take.

### 4.3 Input mapping (82368CE0, upstream of rule D)

Run once per tick on the player's input packet before ordinary movement uses it:

1. Gate: Forge edit-input eligibility (82232AC8) succeeds, a held object exists,
   and the trigger value (packet +56) is strictly greater than 0.1. If the gate
   fails: distanceInputActive := false; the stored input values are kept but not
   used; the packet is left intact.
2. If the "rotation available" byte (packet +40) is set: of the two look axes
   (packet +44, +48), only the one with strictly larger magnitude is kept
   (yawInput := +44 and pitchInput := 0, else yawInput := 0 and pitchInput := +48;
   ties go to +48). If not set, yaw/pitch inputs keep their previous values.
3. distanceInputActive := true. Of the two movement axes (packet +28, +32), only
   the one with strictly larger magnitude is kept: if |+28| > |+32|,
   distanceInput := +28 and rollInput := 0; otherwise distanceInput := 0 and
   rollInput := +32 (ties go to roll).
   Packet +28 is the movement stick's forward axis (positive = forward) and +32
   its left axis (positive = left); the unit movement code uses them that way
   (823619F8 → 8244A8D8). Rule D subtracts the input, so **pushing the stick
   forward pulls the piece toward the player and pulling back pushes it away**,
   as the code reads. This Halo 4 sense is the required behaviour. A host
   engine's own edit-distance handling must not also run (Halo 3's native
   consumer 82281A98 adds the input, the opposite sense). The trigger value is
   packet +56. Which physical trigger or button fills it was not traced (the
   device-to-packet producer lies outside the read code).
4. Both movement axes in the packet are zeroed (consumed), so the monitor does not
   also move with them.

So push/pull and roll share one stick: whichever axis dominates wins exclusively.
There is no dead zone on the stick axes in these functions; the only threshold is
the trigger's 0.1. Any stick dead zone is upstream (not traced).

### 4.4 Per-tick advance (8244D0E0, 8244D5A8–8244D628)

Runs every tick after the aim update (2.1) when all hold: an object is held; the
player is local; the held object has no parent; it has a physics instance whose
flag word (+16) has mask 0x4 set; and global switch byte 8407EFFA is zero (it
always is in shipped Halo 4, round 3). Then, in order:

Mask 0x4 of the physics-instance flags means "the instance's bodies are
currently in the physics world". It is set by 8249C390, which adds the
instance's bodies to the world (82389220 / 82CD9258). It is cleared by 8249B7B0,
which removes them (82CDDBE8). These are its only writers. Behaviour: while the
held piece's physics is out of the world, the piece gets no rotation, no offset
decay, no push/pull and no held/monitor update, and simply stays put.

1. Rotation stage (8244A7D0; section 04). If offsetDecay is 0 after a rotation
   was applied, it is set to (seconds per tick × 5.0). So a full offsetScale of
   1 decays to 0 in 0.2 s.
2. offsetScale := max(offsetScale − offsetDecay, 0).
3. holdDistance := rule D(holdDistance). This is where push/pull accumulates:
   0.3 × input per tick, not scaled by tick duration.
4. Held-object update (8244A8D8) and monitor follow (8244AF48).

If the switch byte were non-zero, an alternate routine (82451FC0) would replace
all four steps. That routine (per the earlier notes) is the only consumer of
Forge-globals +0x4C. **It is never enabled in shipped Halo 4.** A search of all
73,876 generated functions found no instruction that writes 8407EFFA or its
neighbour 8407EFFB. The only accesses are the two reads, in 8244D0E0 and
8244A7D0. Nearby code touches only the separate word at 8407EFFC. The image
also holds no data pointer to either byte, so no debug-variable table can reach
them. Both bytes are zero in the image. The normal path alone is the shipped
behaviour, and the alternate path and +0x4C need not be implemented. Held objects that are parented, bodyless or lack the instance flag get no
distance update, no decay and no rotation from this path.

There is no decay of holdDistance toward the default while holding; it changes
only through input or re-clamping (e.g. if the radius changes). It returns to D0
only on release/reset/construction.

---

## 5. Spawn / creation placement

### 5.1 Creation flow (context)

Event 0 (create) clears grabOffset, offsetScale and offsetDecay, then (outside
session type 4) calls the creation routine 824506D8 with palette indices and a
requested position. Creation does nothing if the player already holds an object.
It checks placement eligibility (5.2) with the position, allocates the variant
record, creates the runtime object, and for a valid variant slot calls the grab
entry (3.1). The create event's producer, the palette menu action 82685838,
first runs eligibility without a position (quota/budget only). It then puts
the player's aimPoint into the event as the requested position. The duplicate
path (event 10, producers 8244CAC8 and menu 82685CA8) also uses aimPoint. A new
piece is therefore requested at the aim point (ray hit, or ray end on a miss)
and then pulled back toward the player by 5.2.

### 5.2 Placement eligibility and spawn point (8244EF80)

Inputs: player, object tag, optional requested point p (modified in place).

1. Invalid tag, or tag with no multiplayer-object block (count at tag +388 ≤ 0):
   not eligible.
2. If p is absent, or the multiplayer block's flags (+28) have bit 1 set ("phased
   physics in Forge"), skip steps 3–5 (eligible so far, point untouched, no
   clearance query).
3. **Radius** ρ = definition radius (tag +32); if ρ < 0.0001, ρ := 1.0.
4. **Pull toward the monitor**: if the monitor exists, let Q = its physics point,
   v = Q − p, and normalise v by rule N (length s). Then p := p + v × k with
   k = ρ if ρ < s, else k = 0.5 × s. So the requested point moves toward the
   player by the piece's radius, or halfway to the player if the player is closer
   than one radius. (If s < 0.0001, v is not normalised and k = 0, so no move.)
5. **Clearance search** (824685C8 → 824686F0, specified in 5.3): on success
   p := the returned point and the step passes; if every attempt fails the
   object is not eligible.
6. **Quota**: the palette quota for the tag (823C3498) must exist; if its
   definition limit (+16) is positive, the placed count must be below it.
7. **Budget**: current budget + item cost (+20) must not exceed the maximum
   (823C5160), else not eligible.

The spawned object is then grabbed through 3.1–3.2; its initial hold distance
comes from the current aimPoint by rule D, not from the spawn point.

### 5.3 Free-space search (824685C8 wrapper, 824686F0 search) — round 3

Inputs from 5.2: requested point p (after the pull toward the monitor) and
definition radius ρ (after its 1.0 fallback).

**Probe.** A sphere of radius ρ (82D80CA8; the sphere's radius is ρ itself,
not floored). It is placed with the identity orientation (52-byte identity
transform from 8212516C) and wrapped in a shape phantom (82CE5658). The
phantom's collision filter word is layer 1, system group 0 (selector 1, no
owner object). The phantom is added to the physics world (world at 8405DDAC)
for the duration of the search and removed and freed at the end
(82CD8CC8, 82C8FE98).

**Wrapper (824685C8).** Search radius R := ρ, but R := 0.001 if ρ is not
greater than 0.001. Up to 4 attempts with R, 2R, 4R, 8R (×2.0 after each
failed attempt). Each attempt runs the search below. The first success writes
the chosen point to the output and returns true. Four failures return false,
and the output is left untouched.

**Search (824686F0), one attempt with radius R.** In this caller the inner
radius is 0, the optional bounding-box phantom is absent and the optional extra
test object is absent. The "allow downward" byte is 0, so 18 candidate
directions are used, in this fixed order (a = 0.70710677, s = 0.57735026):

| # | direction | # | direction | # | direction |
| --- | --- | --- | --- | --- | --- |
| 0 | (0, 0, 0) | 6 | (a, 0, a) | 12 | (0, −a, a) |
| 1 | (1, 0, 0) | 7 | (s, s, s) | 13 | (−a, −a, 0) |
| 2 | (0, 1, 0) | 8 | (s, −s, s) | 14 | (−a, a, 0) |
| 3 | (−1, 0, 0) | 9 | (a, a, 0) | 15 | (−a, 0, a) |
| 4 | (0, −1, 0) | 10 | (a, −a, 0) | 16 | (−s, −s, s) |
| 5 | (0, 0, 1) | 11 | (0, a, a) | 17 | (−s, s, s) |

(Entries 0–5 are static image data at 83574AD0; 6–26 are filled once on first
use. Entries 18–26 are the downward set — (0,0,−1), (a,0,−a), (−a,0,−a),
(0,a,−a), (0,−a,−a), (s,s,−s), (s,−s,−s), (−s,−s,−s), (−s,s,−s) — and are
used only when the byte is non-zero, which this caller never sets.)

For each direction d in order:

1. candidate c := p + d × R (per component, fused multiply-add). Entry 0 is
   the requested point itself.
2. Move the probe to c (82CE6DD0) and collect its penetrations (phantom virtual
   +72, collector at 8212C8FC). If it overlaps anything its layer-1 filter
   accepts, reject c and go to the next direction. For Ravine, row 1 =
   0xBF83FC7D accepts layers 0, 2–6, 10–17, 23–29 and 31, and rejects 1, 7–9,
   18–22 and 30. Which placed pieces block it is listed per layer in Round 4.
3. **World test.** Let c′ = c raised by h (Z only). h is element 0 of a float
   block in the scenario tag (scenario +2060 count, +2064 pointer, via 824AAA88;
   selector 1 maps to element 0 through 824AA9F0). h = 0 if the block is empty.
   For Ravine h = 0.0 (Round 4), so c′ = c. Run the engine point query 82415970
   on c, and if that reports a hit, on c′. The query mask is the 64-bit global
   at 84554980, which start-up routine 832932B8 sets to 0x00029009_00000081.
   No exclusions are passed. Reject c only if **both** queries report a hit.
4. Accept: output := c. Compute c's structure location (822AA7B8 into the
   caller's buffer). If the location's leading byte is −1 (not inside any
   structure cluster), the attempt keeps going with the next direction.
   Otherwise the search succeeds with c.

If no direction succeeds the attempt fails. The returned point is therefore
the **first** candidate, in the table order above, whose probe sphere is clear,
which passes the world test and which lies inside a structure cluster. The
requested point itself is always tried first. Candidates are never ranked by
distance or clearance depth.

Not determined: the value of h (map globals data), and the full internal
classification performed by the engine point query 82415970 (its general
world/geometry traversal was not decoded; only its inputs, mask and how the
result is used are specified here).

---

## 6. Tuning constants

### 6.1 Image literals

| Value | Address | Used for |
| --- | --- | --- |
| 0.0 | 821289E0 | zero for resets, decay floor, normalisation fallback length |
| 1.0 | 821289E4 | field228 default; definition-radius fallback |
| 0.1 | 821289EC | trigger threshold for edit input (strictly greater) |
| 2.0 | 821289F4 | clearance search radius growth per failed attempt |
| 0.5 | 82128A08 | spawn pull factor when monitor is inside one radius |
| 5.0 | 82128A10 | fallback for grab range, default distance, multiplier |
| 0.3 | 82128A1C | push/pull rate per tick per unit input |
| 0.0001 | 82128A54 | "configured" threshold for globals; tiny-radius and normalisation epsilon |
| 0.4 | 82128B04 | additive clearance margin |
| 0.001 | 82128C0C | minimum clearance search radius |
| 1.25 | 82128F30 | multiplicative clearance margin |
| 22.0 | 8212915C | fallback maximum distance |

Integer literals: ray layer 26; ray flags 0x000000090000179F; 64 max exclusions;
target type mask 0xBCF; 4 clearance attempts; constructor sensitivity 2 and
byte272 = 7; notification 0x08000000.

### 6.2 Forge-globals fields (tag `forg`, Ravine values)

| Offset | Name (TagTool schema) | Ravine | Fallback | Consumer here |
| --- | --- | --- | --- | --- |
| +0x44 | object grab range | 7.5 | 5.0 | aim ray range (8244C740) |
| +0x48 | default focal distance | 7.5 | 5.0 | D0 (82452AD8) |
| +0x4C | minimum focal distance | 2.0 | 2.0 | only the alternate held path 82451FC0 (per earlier notes) |
| +0x50 | maximum focal distance | 22.0 | 22.0 | upper cap (82452BB8) |
| +0x54 | focal distance multiplier | 5.0 | 5.0 | upper bound factor (82452C28) |

A field is used only if strictly greater than 0.0001. Other maps' values are not
verified.

### 6.3 Other source data

- Collision-filter table row 26 (Ravine `hcfd`): 0xCBFEFFFB.
- Variant world bounds (variant +696, six floats): per map/variant.

---

## 7. Persistent state and resets — summary

| State | Construct | Release reset | Select (valid) | Grab init | Per tick |
| --- | --- | --- | --- | --- | --- |
| held | none | none | := object | := object | — |
| magnetTarget | none | none | — | — | (magnets, sec. 06) |
| aimed | none | none | — | — | := filtered ray hit |
| aimPoint | not written | kept | kept | read | := hit or endpoint |
| holdDistance | D0 | D0 | kept | := rule D(projection) | := rule D(·) while held |
| offsetScale/Decay | 0 | 0 | kept | (physics stage) | scale decays to 0 |
| grabOffset | 0 | 0 | kept | (physics stage) | — |
| heldPoint | 0 | 0 | kept | := physics point | — |
| pose | not written | kept | kept | := object pose, bounded | (held update) |
| preferences (+82, +224, +268) | 0 / 0 / 2 | kept | kept | kept | — |
| distance/roll/yaw/pitch input | — | kept | kept | kept | 4.3 rules |

Input fields live in the player record and are never reset by the editor reset;
an inactive gate leaves stale values that are ignored because the active flag is
false.

---

## 8. Corrections to earlier notes

- FULL-RE-FINDINGS "Original grab and distance policy" says 824511B0
  "checks/relinquishes a different currently held object". The call passes the
  requested object to a release routine that only acts on the held object, so no
  release happens (3.1 step 1).
- The same section's formulas (L, U, clamp order, 0.3 input subtraction, fallbacks
  5/22/5) are confirmed.
- "Without a held object, 82452AD8 supplies ... otherwise 5": confirmed.
- The bridge comment on 8244A118 implies a deletion function; it is a plain magnet
  target setter used by the deletion routine 8244C000.
- The bridge's `PrepareSpawnPlacement` covers steps 3–4 of 5.2 only; the phased
  gate, clearance search, quota and budget remain outside it.

---

## 9. Open questions (status after round 3)

Target: behave exactly like Halo 4. No host-engine behaviour is substituted
anywhere in this section.

| # | Question | Status | Finding |
| --- | --- | --- | --- |
| Q1 | Grab while a different object is held | RESOLVED | Grab is emitted only when nothing is held (3.1). |
| Q2 | 824519C0 result | RESOLVED | Effectively always passes after 82451908 (3.1). |
| Q3 | Does the aim ray hit the held piece; what is aimPoint while holding | RESOLVED (Round 4: every held Ravine piece except fw_one_way_door_small) | Held fixed-body scenery gets layer 17, other types layer 4, and row 26 accepts both, so the ray hits the held piece. aimPoint is the nearest hit on structure or any non-excluded object including the held piece (previous-tick pose), else the segment end (2.3a). The map-data layer set is resolved per object in Round 4. |
| Q4 | View vector unit length | RESOLVED | Produced normalised (2.2). |
| Q5 | Pull direction / physical controls | Direction RESOLVED; physical button UNRESOLVED | Forward stick = pull in, back = push out (4.3). The device-to-packet producer for the trigger (packet +56) was not traced. |
| Q6 | Switch byte 8407EFFA | RESOLVED | No writer, no pointer, zero in the image: never enabled in shipped Halo 4. The normal path only (4.4). |
| Q7 | Create position | RESOLVED | aimPoint (5.1). |
| Q8a | Object +364 mask 0x4 | RESOLVED | "Killed": set once by the object-death routine; the object is untargetable and force-dropped (2.3 step 5). |
| Q8b | Physics-instance +16 mask 0x4 | RESOLVED | "Bodies are in the physics world"; set and cleared only by world add/remove (4.4). |
| Q8c | Other unnamed fields (flag20, field32, field228/232, ids256–264, byte272, tag +28 bit 0, 8298E798, 8244F838, 822BE858) | UNRESOLVED | Their observable effect within this section is fully specified by the rules that test them; their names are not established. |
| Q9 | Free-space search | RESOLVED except two inputs | Fully specified in 5.3. Not determined: the height h (map globals data), and the internal classification of the generic engine point query 82415970. |
| Q10 | Tick rate | UNRESOLVED | Push/pull is 0.3 × input per Halo 4 simulation tick. The rate is runtime state (game options +36, copied by 8238FBD8/8238FDD0) and no literal was found. To match Halo 4 the per-second rate (0.3 × input × Halo 4 tick rate) must be preserved, so the rate is needed and is not determinable from the read code. offsetDecay is time-based (seconds per tick × 5), so it is unaffected. |
| Q11 | Type mask names | RESOLVED | Halo 4 types: biped, vehicle, weapon, equipment, scenery, machine, control, dispenser, crate (2.3). |

---

## Round 2 changes

- Corrected two flag masks read wrongly in round 1. Object +364 is mask 0x4
  (not bit 1), and the held-tick physics-instance gate is mask 0x4 (not bit 1).
- Added: the same +364 flag forces a release of a held object (2.3 step 5).
- Added 2.3a: the held object is not excluded from the aim ray; the layer
  question is narrowed.
- Grab producer identified (event 3 from 8244CAC8, uses aimed, only when nothing
  is held); Q1 closed.
- 824519C0 behaviour settled (Q2).
- Aim vector normalisation evidence added to 2.2 (Q4).
- Push/pull direction stated: forward stick pulls in; Halo 3's native sign is
  opposite (4.3).
- Create position = aimPoint, from menu producer 82685838 (5.1).
- offsetDecay initialisation (seconds per tick × 5) added to 4.4.
- Minimum focal distance consumer noted (alternate path 82451FC0, from earlier
  notes); 4.2, 4.4 and 6.2 updated.
- Object type names added with Gen4 and Halo 3 numbering (2.3).
- Tick-rate source located (game options +36, runtime); still no literal.

## Round 3 changes

- Removed all Halo 3 behaviour substitutions: the push/pull sign note, the
  ray-exclusion suggestion, the Halo 3 aim-vector and placement-search
  suggestions and the per-Halo-3-tick suggestion. Halo 3 type numbers remain
  as a numbering reference only.
- 2.3a: traced the held piece's collision layer through the body constructor
  824A39A0 and the layer choosers 824A2A48/82465E48. Held fixed-body scenery is
  on layer 17 (others layer 4), which ray row 26 accepts, so the ray hits the
  held piece. aimPoint while holding is specified exactly.
- 2.3 step 5: +364 mask 0x4 identified as the "killed" flag (writers 82999408 /
  829DAEC0; clearers 82A11088 / 829B1C78).
- 4.4: the held-tick gate flag identified as "physics bodies in the world"
  (writers 8249C390 / 8249B7B0).
- 4.4: confirmed 8407EFFA/8407EFFB have no writers and no image pointers; the
  alternate path is never enabled; minimum focal distance is unused in shipped
  behaviour.
- 5.3 (new): full specification of the free-space search: probe sphere and
  filter layer, retry radii, 18-direction candidate table and order, overlap,
  world and cluster tests, and first-acceptable selection. Ravine layer rows 1
  and 26 decoded.
- Section 9 rewritten for round 3.

## Round 4: Ravine values

Source: `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\disc2-assets\ca_forge_ravine.map`,
read offline. Tag table and address translation are the same as in
`tools\h4-forge\audit_forge_globals.py`; tag names come from the encrypted name
table, as in `tools\h4-forge\audit_marker_visual.py`. Field names are from the
local TagTool Gen4 schema (`PhysicsModel.cs`).

### Spawn-search height offset h

- The runtime pointer 8405D33C is the **scenario** tag (`scnr`, tag index 11).
  8405D340 is the globals tag (`matg`, tag index 5), whose +492 reference is
  the `forg` tag. Both are set by the map-load routine 82340A80.
- Scenario +2060 block: count 1, one float, value **0.0**. The selector 1 used
  by the spawn search maps to element 0.
- **h = 0.0**, so the raised point equals the candidate. The world test is a
  single point query on the candidate: reject it if that query reports a hit.

### Layer-set table (used to resolve a body's final layer)

- matg +1972 is a tag reference to `hcfd` (tag index 17059, the same
  collision-filter tag as the ray table). Its first block (+0 count, +4
  pointer) holds 31 collision masks, one per layer.
- Final-layer rule (824ADCC8): the body's wanted set W = rigid body
  **RuntimeHavokGroupMask** (+160, OR over all the object's bodies), plus
  bit (chooser layer) when rigid body **RuntimeFlags** (+178) bit 1 is set on
  any body. If W has exactly one bit, that bit is the layer. Otherwise the
  layer is the lowest-numbered layer whose mask contains all of W, with the
  fewest set bits; 0 if none.
- The held override (layer 17 for scenery / 4 for others, Fixed-authored
  bodies only) replaces this result while held.

### Per-object results (all `bloc`, `scen`, `mach`, `ctrl`, `eqip` and `weap` tags with physics)

Rigid body MotionType (+28): `bloc` bodies are Fixed (5) or Box (2), rarely
Sphere (0). "Placed" = released Normal (authored motion); "frozen" = released
Fixed/Phased (every body Fixed, the chooser sees motion 5).

| Group (type) | Placed layers (count of tags) | Frozen | Held |
| --- | --- | --- | --- |
| bloc (11, crate) | 1 ×152, 4 ×209, 28 ×14, 6 ×3, 3 ×1, 24 ×1 | (= placed for Fixed bodies) | 4 ×378, 28 ×1 |
| scen (6) | 1 ×12, 6 ×19, 4 ×9, 2 ×3, 3 ×1 | 1 ×21, 6 ×19, 2 ×3, 3 ×1 | 17 ×21, 6 ×14, 4 ×9 |
| mach (7) | 4 ×16, 1 ×3, 28 ×1 | 1 ×19, 28 ×1 | 4 ×20 |
| ctrl (8) | 4 ×5 | 1 ×5 | 4 ×5 |
| eqip (3) | 6 ×16 | 1 ×16 | 6 ×16 |
| weap (2) | 6 ×45, 0 ×1, 24 ×1 | 1 ×45, 0 ×1, 24 ×1 | 6 ×45, 0 ×1, 24 ×1 |

Where layers 2 and 28 come from: a wanted set of only layer 2 (0x4), sometimes
plus the chooser's layer 1, resolves to layer 2 or 28.

- **Layer 2** occurs only for three placed fixed scenery tags:
  `objects\multi\dominion\ca_dom_terminal_wires\ca_dom_terminal_wires`,
  `...\dom_terminal_wires002` and `...\dom_terminal_wires003`. When held they
  move to layer 17.
- **Layer 28** occurs for placed gravity volumes (`fw_global_grav_5x5`,
  `_5x5_inv`, `_10x10`, `_10x10_inv`), one-way and two-way doors (all sizes),
  `ff_light_blue`, the three Dominion damage shields and `ca_blam_crate_med`.
- **Layer 16 never occurs.**
- **Non-fixed-body pieces never get layer 2 or 16.** They get 4, 3, 6, 0 or 24.
  The single exception is `fw_one_way_door_small` (Box motion, wanted set 0x4
  plus the chooser), which resolves to **layer 28 even while held**.

### Consequences for the rules above

- **Aim ray (row 26 rejects 2, 16, 26, 28, 29):**
  - Every held Ravine piece is hit by the ray except `fw_one_way_door_small`
    (layer 28). While holding that piece, aimPoint ignores it.
  - Placed pieces on layer 2 (the terminal wires) or 28 (gravity volumes,
    doors, `ff_light_blue`, damage shields, `ca_blam_crate_med`) are
    invisible to the aim ray. Their physics layer alone makes them
    unselectable by aiming.
- **Spawn probe (row 1 accepts 0, 2–6, 10–17, 23–29):**
  - Placed pieces on layer 1 never block the spawn sphere. That is every
    Fixed-body `bloc` placed Normal (152 tags), and nearly every object
    placed Fixed or Phased (frozen).
  - Placed pieces on layers 2, 3, 4, 6, 24 or 28 do block it. That includes
    all Box-motion blocks placed Normal (layer 4), the layer-28 gadgets and
    weapons/equipment (layer 6).
  - A held piece blocks it (layer 4, 6 or 17; 28 for the small one-way door).

Assumption to note: the "frozen" column assumes the body builder hands the
layer chooser motion 5 for a frozen object, as the frozen-motion rule in spec 04
§4.3 implies. The input that carries this (824A2578 → 824A1C30) was not traced
to the bit. For Fixed-authored bodies the frozen and placed results are the same
either way.
