# 04 — Manipulation input, rotation, rotation snap, coordinate panel, physics modes and marker visibility

Clean-room behavioural specification derived by static reading of the Halo 4
statically recompiled functions in
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\forge_original.cpp`
and, for the one caller not present there (event 13), the generated source
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\generated\halo4_recomp.115.cpp`
(824503C4..82450428). Nothing was built, run or executed. Literal constants were
read from the original decoded image
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\h4-image.bin`
(file offset = address − 0x82000000). None of the functions in this section read
the Forge-globals configuration tag; every tuning value here is an image literal
(section 7).

Function addresses are provenance. Names are this document's; the original has
no symbols. Field offsets are given only for traceability; an implementation may
use any layout. Round 3: every rule here is Halo 4 behaviour. Earlier notes about this
project's own wiring or Halo 3 substitutes have been removed; where Halo 4's
behaviour could not be determined, the gap is stated in §10 instead of being
filled with a substitute.

Conventions:

- Editor fields use the names of section 03 §1.1 (held, magnetTarget,
  offsetScale +36, offsetDecay +40, grabOffset +56..+64, rotated +81,
  magnetEnabled +82, pose +84..+135, rotationSnapMode +224).
- Additional editor fields used here: snappedBasis +136..+171 (nine floats, the
  last snapped basis remembered by the snap stage).
- A **pose** is 13 floats: scale, forward vector F, left vector L, up vector U,
  position P (in that order; orig. pose +0, +4, +16, +28, +40). The basis is
  right-handed with L = U × F.
- World axes: +Z is up. "Monitor view" is the controlled unit's current view
  direction vector (unit +1260..+1268), not its desired-view vector.
- All arithmetic is single precision in the original.
- **Normalise rule N** (8228ACE8): as section 03 §1.3 — vectors shorter than
  0.0001 are left unchanged and report length 0.

---

## 1. Manipulation input shaping (82368CE0)

This stage is specified in section 03 §4.3; it is restated here only for the
rotation fields. It runs once per tick on the player's frame packet before
ordinary movement consumes it.

1. **Gate.** All of: the Forge edit-input eligibility service (82232AC8)
   succeeds; it returns a held object that is not none; the trigger value
   (packet +56) is strictly greater than **0.1**. Otherwise `inputActive := false`,
   the four stored input values are left as they were (stale but unused), and the
   packet is not modified.
2. **Look pair (rotation).** Only if the packet's "rotation available" byte
   (+40) is non-zero. Dominant-axis selection on look axes A = +44, B = +48:
   if |A| > |B| strictly then `yawInput := A`, `pitchInput := 0`; otherwise
   `yawInput := 0`, `pitchInput := B` (ties go to pitch). If the byte is zero,
   yawInput and pitchInput keep their previous values (they are not zeroed).
   The look axes in the packet are **not** consumed.
3. `inputActive := true`.
4. **Movement pair.** Dominant-axis selection on movement axes C = +28, D = +32:
   if |C| > |D| strictly then `distanceInput := C`, `rollInput := 0`; otherwise
   `distanceInput := 0`, `rollInput := D` (ties go to roll).
5. Both movement axes in the packet are set to zero (consumed).

Shaping facts:

- No dead zone is applied to any stick axis here. The only threshold is the
  trigger's 0.1. Any stick dead zone is upstream and not traced.
- Only one axis of each pair is ever non-zero, so the user cannot yaw and pitch
  simultaneously, nor push/pull and roll simultaneously. Yaw/pitch can combine
  with roll or push/pull.
- The response curve is not applied here; it is applied by the rotation stage
  (signed square, §2.2). Push/pull (0.3 per tick, linear) is section 03 rule D.
- The stored fields are per-player (player record +1888 active, +1892 distance,
  +1896 roll, +1900 yaw, +1904 pitch; player stride 4144).

Semantic meaning of the packet fields (Q1, round 2): +28 is the forward
movement axis and +32 the sideways (left) movement axis (8244A8D8 builds
horizontal movement as forward·heading + left·perpendicular from exactly these
two, and 823619F8 copies them unswapped into the unit's movement vector);
+44/+48 are the two look axes (yaw, pitch); +56 is the Forge edit trigger.
Hence: push/pull = forward/back on the movement stick, roll = sideways on the
movement stick, yaw/pitch = the look stick. Physical button/stick identity
and device sign are not fully established (see §1.1 and Q1).

### 1.1 Halo 4 input chain upstream of 82368CE0 (round 3, disassembled)

1. **Device poll (82335740).** For each of 4 controllers, XamInputGetState
   (thunk 832F27FC via 821D0000). Results go to a per-controller raw table
   (base 835B38EE, 0x3C bytes each): two trigger bytes (index 0 = left trigger,
   index 1 = right trigger, 0..255), a per-trigger digital threshold with
   hysteresis (+0x40 above / −0x20 below the current value, capped at 255), hold
   counters and hold durations for triggers and 14 buttons, and the four raw
   thumbstick shorts LX, LY, RX, RY (+0x34..+0x3A). Button index order (mask
   table 8211E9C4): 0 d-pad up, 1 down, 2 left, 3 right, 4 Start, 5 Back,
   6 left-stick click, 7 right-stick click, 8 A, 9 B, 10 X, 11 Y, 12 LB, 13 RB.
   No dead zone is applied at this stage.
2. **Player control record.** Per local player, record = TLS+0x64 base +
   index × 0x1E0; the control block starts at record +0x128. The per-tick
   player-control update (823FAEA0) fills it. Inside it, when the Forge
   edit-input gate 82232AC8 succeeds (object held in Forge edit mode), the
   ordinary processing call 82363A08 is skipped (823FBDCC..823FBDE4).
3. **Control → action (824008F0, called from 821F8630).** Copies control
   fields into the frame action: angles +0x0C/+0x10/+0x14 → action +0x10/+0x14/
   +0x18; movement +0x30/+0x34 → +0x1C/+0x20; trigger analogs +0x38/+0x3C →
   +0x38/+0x3C; the "rotation available" byte +0xE8 → action +0x28; its two
   floats +0xEC/+0xF0 → action +0x2C/+0x30.
4. **Network form (decoder 82315C00..82316300).** The +0x28 byte travels as one
   bit; +0x2C/+0x30 are sent only when it is set, each quantised to 5 bits over
   [−1, 1]; the two trigger analogs +0x38/+0x3C are each quantised to 5 bits
   over [0, 1] (zero when absent). So on remote machines these inputs carry
   only 32 levels.

The action field offsets here are the frame-packet offsets used in §1 (the
256-byte per-player record that 8225CE30 copies is this action). Hence +56 is
the first trigger analog (control +0x38) and +60 the second.

Not yet established: which physical trigger fills control +0x38 (versus
+0x3C), which physical stick fills control +0xEC/+0xF0 and the movement pair,
the signs, and any dead zone or curve between the raw table and the control
block. The writer of control +0xE8/+0xEC/+0xF0 was not found by direct store
search (stores to these offsets in the image are initialisers, mergers and
network decoders only), so the conversion is probably done through a block
copy or computed address; it needs a full trace of 823FAEA0 and the input
abstraction that reads the raw table (Q1–Q3).

### 1.2 Physical mapping, signs, dead zones and the rotation flag (round 4, disassembled)

This replaces the "not yet established" paragraph of §1.1.

**Stage A — device poll (82335740).** As §1.1. Raw input index used by the
button-layout table (from the record order in 821F1060..821F1440):
0 = left trigger, 1 = right trigger, 2 = d-pad up, 3 = d-pad down,
4 = d-pad left, 5 = d-pad right, 6 = Start, 7 = Back, 8 = left-stick click,
9 = right-stick click, 10 = A, 11 = B, 12 = X, 13 = Y, 14 = LB, 15 = RB;
45 means "unbound".

**Stage B — input abstraction (821F0F50), per local player.** Record at
84550EE0 + 0x340 + local × 0x1F0; preferences at 84550EE0 + local × 0xD0.

1. The 44 abstract-action → raw-input bindings are copied from the preferences
   (+0x08..+0xB4) into the record (+0x100..+0x1AC). Each raw input has a 16-byte
   state record (hold frames, duration, and for the triggers an analog value
   = trigger byte / 255, constant 1/255 at 821289FC). Triggers get no analog
   dead zone.
2. Raw sticks are copied as shorts: +0x1B0 LX, +0x1B2 LY (left stick),
   +0x1B4 RX, +0x1B6 RY (right stick); XInput sign: +X right, +Y up.
3. **Axial dead zone (823EF4F0), per stick.** D = 7849 for the left stick,
   8689 for the right stick (halfword table 8211DCAC; these are the standard
   XInput values). Optionally replaced by game data: if record byte +0xB09 is
   set and the globals tag (8405D340) block at +0x108/+0x10C has an entry, D =
   clamp(entry[0], 0, 1) × 32767. Each axis v separately:
   v > D → (v − D)·32767/(32767 − D); v < −D → (v + D)·(−32768)/(−D − 32768);
   otherwise 0. The stick angle atan2(y, x) of the result is stored
   (+0x1E4 left, +0x1E8 right). If the same globals entry has a positive second
   value R (×32767), a radial dead zone follows: magnitude |v| clamped to
   [0, 32767]; |v| ≤ R → stick zero; else magnitude (|v| − R)·32767/(32767 − R)
   along the stored angle.

**Stage C — player-control input (823F65E8), per local player, every tick.**

1. Each stick axis := short / 32767 (constant 82128A40), clamped to [−1, 1].
2. Stick layout preference (+0xB8; default 0): values 1 and 3 swap the two
   sticks; values 2 and 3 apply a further remap (823FA598) and recompute the
   angles.
3. **Response curve, per stick.** Descriptor from the controlled unit's
   definition (82953518; block entry stick + 8), else from the globals tag block
   at +0x118 (entry per stick). If it has a function (+0x1C count > 0, +0x20
   pointer), the stick magnitude is replaced by that function's value
   (8226CD10) along the stored angle. Then (823FAB00), if there is no descriptor
   or its type byte is 2: when both |x| and |y| exceed 0.0001, both components
   are multiplied by √(1 + (smaller/larger)²) and clamped to [−1, 1]
   (square-to-circle correction); otherwise unchanged. Descriptor contents are
   tag data for the Forge monitor / globals and were not extracted (Q3).
4. Outputs written to the abstraction record (left stick L, right stick R):
   +0x1B8 = Ly, +0x1BC = −Lx, +0x1C0 = −Rx, +0x1C4 = Ry (negated when the
   look-inversion preference +0xBA is set), +0x1C8 = Ry (negated for
   preference +0xBB), +0x1CC = Ry, +0x1D0 = −Rx.
5. Movement (control +0x30/+0x34, i.e. packet +28/+32) := (+0x1B8, +0x1BC) =
   (Ly, −Lx): forward and left.
6. Trigger analogs: control +0x38 (packet +56) := analog of the raw input bound
   to abstract action 6; control +0x3C (packet +60) := action 11. A value is
   taken only when that raw input is not marked consumed and is not claimed by
   a different action; otherwise 0.
7. **Rotation-available flag (control +0xE8 → packet +40).** Set to 1, with
   control +0xEC := +0x1C0 (−Rx) and +0xF0 := +0x1C4 (Ry, inversion applied),
   exactly when this local player's player record (TLS+0x18 table, salted
   datum from TLS+0xA0) has byte +0x760 set. Byte +0x760 = player +1888 is the
   Forge `inputActive` byte written by 82368CE0 on the previous tick. Otherwise
   the flag is 0 and the two floats are not written.
8. Later in 823FAEA0, when the Forge gate 82232AC8 holds, the ordinary
   look/aim processing (82363A08) is skipped, so the camera does not turn while
   manipulating. 82368CE0 zeroes the movement pair, so the monitor does not move.

**Default button layout** (823EF7F8; abstract action k → raw input):
0 A, 1 Y, 2 X, 3 RB, 4 LB, 5 LT, 6 RT, 7 B, 8 right-stick click, 9 d-left,
10 d-right, 11 LT, 12 B, 13 RB, 14 LB, 15 B, 16 d-up, 17 Start, 18 Back,
19 d-left, 20 d-right, 21 d-left, 22 A, 23 B, 24 d-down, 25 d-up, 26 d-left,
27 d-right, 28 RB, 29 LB, 30 d-up, 31 Y, 32 d-up, 33 d-down, 34 Back,
35 d-up or d-left (chosen by global byte 8407FCD7), 36 Y, 37 left-stick click,
38 d-right, 39 X, 40 RT, 41 LT, 42 RB, 43 B. Default stick layout 0; both
inversion flags off; the two preference floats at +0x00/+0x04 default to 120.0 and 60.0
(constants 82128CA8/82128CAC; ordinary look rates, not used by the Forge
rotation pair). Abstract-action names are not present in the image; only
actions 6 and 11 are tied to this section.

**Resulting physical mapping with the default layout**

| Manipulation | Control | Sign (code) |
| --- | --- | --- |
| Enable (gate) | Right trigger, analog > 0.1 (≈ 26/255) | — |
| Push/pull | Left stick up/down (Ly) | distance −= 0.3·Ly per tick: **up brings the object closer**, down moves it away |
| Roll | Left stick left/right; packet +32 = −Lx, negated again by 8244A7D0 | stick right → right-hand turn about the view direction: **clockwise as seen by the player** |
| Yaw | Right stick left/right; packet +44 = −Rx | stick right → turn about world up: **counter-clockwise seen from above**; the face toward the player moves right |
| Pitch | Right stick up/down; packet +48 = Ry (−Ry with look inversion) | stick up → turn about the view's left axis: **top tips away from the player** |

Yaw and pitch never combine (dominant axis, §1), nor do push/pull and roll.
Response: per-axis dead zone, then the per-stick curve, then square-to-circle
correction, then rotation's own signed-square × 5 (§2.2). Push/pull is linear.

**One-tick latency of the rotation inputs.** The flag reflects the previous
tick's `inputActive`. On the first tick the trigger passes 0.1 the flag is
still 0, so 82368CE0 keeps the yaw/pitch values left over from the last
manipulation for one tick (§1 step 2) while roll and push/pull are already
live. From the second tick the right stick drives yaw/pitch.

---

## 2. Rotating the held object

### 2.1 Caller stage (8244A7D0)

Runs every tick in the held-placement sequence (section 03 §4.4, step 1), before
offset decay, distance update and the held/monitor submission.

1. If `inputActive` is false: no rotation (result "not rotated").
2. Otherwise call the rotation routine (§2.2) with
   (yaw = yawInput, pitch = pitchInput, roll = **−rollInput**) and the monitor
   view. The roll input is negated here before shaping.
3. `rotated := rotated OR result` (editor +81; sticky — once set it stays set
   until the next selection call clears it, section 03 §1.3 step 4).
4. **Offset-decay seeding.** If (result is "rotated" OR the global switch byte
   8407EFFB is non-zero) AND offsetDecay is exactly 0:
   `offsetDecay := tickDuration × 5.0`.
   A non-zero offsetDecay is never changed here.

The dispatcher then applies `offsetScale := max(offsetScale − offsetDecay, 0)`
every tick (section 03 §4.4 step 2). Effect: on the first rotation after a grab
(or after a physics transition, §4.4), the grab offset fades linearly from its
current scale to zero over 1 / 5.0 = 0.2 s of constant-rate ticks, so the object
pivots toward rotating about its own physics point rather than the original grab
point. Image value of 8407EFFB is 0 (Q6).

### 2.2 Rotation routine (8244B518)

Inputs: editor, monitor, yaw y, pitch p, roll r (already negated by the caller),
tick duration dt (global time record +8).

1. **Reject** (returns "not rotated", pose unchanged) if held is none, or the
   rotation-block predicate (§2.3) says blocked.
2. **Axes** (all world space):
   - V = monitor view direction, normalised (rule N).
   - Yaw axis Ay = world down (0, 0, −1) (image vector at 821251BC via pointer
     833F7EB8).
   - Pitch axis Ap = normalise(worldUp × V) where worldUp = (0, 0, 1) (image
     vector at 82125188 via pointer 833F7EAC). For a horizontal view this is the
     horizontal axis to the left of the view. If the view is vertical the cross
     product is zero, rule N leaves it zero, and pitch contributes nothing (no
     fallback axis).
   - Roll axis Ar = V.
3. **Response curve.** Signed square times gain K = **5.0**:
   s(x) = x·|x|·K for each of y, p, r.
4. **Angular vector** ω = s(y)·Ay + s(p)·Ap + s(r)·Ar.
5. Normalise ω (rule N) to get the rotation axis a and length |ω|.
   Angle θ = |ω| × dt (radians). So the maximum rate on a single full-deflection
   axis is 5 rad/s (≈286°/s); deflection 0.5 gives 1.25 rad/s.
6. If θ ≤ **0.0001** (strictly greater is required to proceed): return
   "not rotated", pose unchanged.
7. Build the rotation R(a, θ) by the Rodrigues formula (822C1398) with
   c = cos θ, s = sin θ (82265E28 / 82265C30), right-handed (positive θ turns
   +X toward +Y about +Z). Each column/vector: R·e_x =
   (c + ax²(1−c), ax·ay(1−c) + az·s, ax·az(1−c) − ay·s), and analogously; scale 1,
   translation 0.
8. **Apply about the object's own position.** Temporarily replace the pose
   position with (0, 0, 0) (image zero vector 82125110 via 833F7E98), compose
   pose := R ∘ pose (8226BFC0: R applied to every basis vector; scale multiplied
   by R's scale 1), then restore the three original position words exactly.
   The rotation is therefore about world-space axes through the held pose's
   position, and the pose's scale and position are bit-identical afterwards.
9. Return "rotated".

Sign summary (given monitor looking along +X, worldUp +Z): positive yawInput
rotates about world down (clockwise seen from above); positive pitchInput
rotates about +Y (the view's left); positive rollInput, after the caller's
negation, rotates about −view. Physical stick directions are Q1.

No acceleration or angular inertia exists in this path: rotation is purely
rate × dt each tick from the current input. No rotation decay. The only
time-dependent state is the grab-offset fade of §2.1.

Rotation acts on the **persistent unsnapped pose** (editor +84). Snapping is a
separate later stage (§3).

### 2.3 Rotation-block predicate (8244A6A8)

Returns "allowed" only when all of the following hold for the held object,
otherwise "blocked":

1. Object type (object +178, small integer) is one of
   {0, 1, 2, 3, 4, 6, 7, 8, 9, 11, 12, 13}. Blocked: 5, 10, 14 and above
   (computed from masks 0x390 and 0x3ADF; see §7). With the Halo 4 object-type
   enumeration (TagTool Gen4 schema, `ObjectTypeEnum` bit order, consistent with
   this code's own use of 0 = biped, 6 = scenery, 11 = crate): allowed are biped,
   vehicle, weapon, equipment, terminal, scenery, machine, control, dispenser,
   crate, creature, giant; blocked are projectile (5), sound scenery (10),
   effect scenery (14), spawner (15) and anything higher.
2. Object flag word (+256, 64-bit) has bit 0x100 set (object connected to
   physics; cross-version mapping in FULL-RE-FINDINGS).
3. The object has a physics instance (+240 ≠ −1).
4. If the instance has one or more bodies: every body's motion type
   (body +232) is not 5 (Fixed), **and** the instance flag word (+16) has bit
   0x80 clear. (The instance-flag test is evaluated per body but does not depend
   on the body.) With zero bodies, condition 4 passes.

Keyframed bodies (motion 4) do not block rotation.

---

## 3. Rotation snap

### 3.1 Snap modes

rotationSnapMode (editor +224) is an index 0..5 into the image integer table at
833F195C: **[0, 90, 45, 30, 15, 5] degrees**. 0 = snapping off. The editor
constructor sets it to 0; release/selection never resets it (section 03). The
menu control that sets it (constructor 8268A290, setter 82685E88, event 14;
menu field +0xBC written as 5 at 8268A370) — see FULL-RE-FINDINGS "Rotation
snap: resolved menu-to-event binding". Round 2: the only writer of editor +224
other than event 14 is the editor constructor (value 0), so **a player starts
with snapping off** and keeps that until the menu sends event 14. Whether the
menu's +0xBC value 5 is the initially highlighted choice or the last valid index
was not established; it does not reach the editor without event 14.

### 3.2 Where and when snapping is applied (8244A8D8, 8244ADA0..8244AF34)

Every held-update tick, after movement/contact work and before magnets:

1. Make a **copy** S of the persistent pose (editor +84).
2. If rotationSnapMode ≠ 0 **and** rotated (editor +81) is set:
   1. step = table[mode] × (π/180) (constant at 82128A20 = 0.017453292).
   2. Quantise S's orientation (§3.3).
   3. Compare S's nine basis floats with snappedBasis (editor +136..+171).
      They are "the same" only if every |remembered − quantised| < **0.0001**.
   4. If not the same: overwrite the persistent pose (all 52 bytes, including
      position and scale) with S, and set snappedBasis := S's basis.
      If the same: leave the persistent pose untouched (it keeps accumulating
      unsnapped rotation).
3. Magnet alignment (8244EED8, other section) runs on S.
4. S is submitted as the physics target with controller parameter 0.2
   (82452930; other section).

Consequences:

- No snapping happens until the user has actually rotated the object at least
  once since the last selection call (rotated flag). A freshly grabbed object
  keeps its authored orientation even with snapping on.
- Small rotations accumulate in the unsnapped pose; the submitted orientation
  jumps to the next increment once the accumulated Euler angle crosses a
  half-step. When it jumps, the accumulator is reset to the snapped orientation,
  so accumulation restarts from the new increment.
- Because the comparison is against the remembered snapped basis (not the
  current unsnapped one), a stale snappedBasis left from an earlier object can
  cause an immediate overwrite on the first snapped tick; this is the intended
  path for adopting the snapped pose.
- A pose written by the coordinate panel (§5.5) does not touch rotated or
  snappedBasis. If rotated is already set and snapping is on, the next tick will
  quantise the typed angles to the snap increment and write that back.

### 3.3 Orientation quantiser (82451A38)

Input: pose S (scale and position untouched), step (radians, > 0).

1. Build the basis from F and U only, recomputing L = U × F (8223B050).
2. Convert to Euler angles (yaw, pitch, roll) by rule E→ (§5.3, 823C0208).
3. For each angle a: q = a × (1/step) (reciprocal computed first, then
   multiplied); n = truncate-toward-zero(q + sign(q)·0.5) where sign(q) = +1
   for q ≥ 0 (including +0) and −1 otherwise (round half away from zero);
   a′ = n × step.
4. Rebuild F and U from (yaw′, pitch′, roll′) by rule →E (§5.3, 8232F9B8 /
   82265D10), then L = U × F.

All three angles are snapped independently, including pitch (whose principal
range is ±90°). The snapped orientation is therefore a grid in this Euler
parameterisation, not an arbitrary rotation snapped about the view axes.

---

## 4. Physics modes

### 4.1 The three menu values and the property word

The per-object Forge physics property is two bits (mask **0xC0**) of a 16-bit
property halfword (variant object record +62, i.e. properties +10; record
array at variant +5356, 651 records of 76 bytes). Menu values (constructor
82687088, per FULL-RE-FINDINGS): Normal = 0x00, Fixed = 0x40, Phased = 0xC0.

**Property edit (8268C340).** Generic masked setter used by the menu:
new = ((old AND NOT mask) AND 0x3FF) OR value, with mask 0xC0 for physics.
Note the AND 0x3FF: bits 10..15 of the halfword are cleared by every edit
through this setter. Value bits are not range-checked.

### 4.2 Runtime state selection (8244A180)

Produces one of four runtime states (0..3), distinct from the three menu values.

1. If the object has no variant slot (object +62 = 0xFFFF): state 0.
2. held := the object is currently held by some player's editor (82449B18).
3. Read the property halfword of the object's variant record (slot must be in
   0..650; for an out-of-range non-0xFFFF slot the original reads an unrelated
   address, Q9).
4. Select:

| Property bits | Held | Not held |
| --- | --- | --- |
| 0x80 set (Phased) | 2 | 0 if the model has a keyframed body, else 3 |
| 0x40 set, 0x80 clear (Fixed) | 1 | 0 if the model has a keyframed body, else 3 |
| neither (Normal) | 1 | 1 if special predicate 8244A5F0 is true, else 0 |

"Has a keyframed body" (82469630) scans the object's physics-model bodies for
motion type 4. The 0x80 bit alone (value 0x80, not offered by the menu) behaves
as Phased.

So Fixed and Phased differ only while held; released, both become state 3
(unless keyframed). Normal released is state 0, or state 1 while it is in the
post-release settle queue (§4.5). Every held object (any mode except Phased) is state 1.

### 4.3 State transition (8244A2A0)

Inputs: object, state.

0. **Precondition:** the object's definition has a model reference (definition
   +148 ≠ −1) and that model has a physics-model reference (model +60 ≠ −1).
   Otherwise the routine does nothing at all.
1. holder := the player holding the object, or none. If held, record
   Pbefore := the object's physics point (82260B58) and localHolder := the
   holder passes the local-player identity predicate (822ED938). If not held,
   localHolder := false.
2. **Flag table** on the object's 64-bit flag word (+256):

| State | 0x40 | 0x200000 | 0x400000 |
| --- | --- | --- | --- |
| 0 | clear | clear | clear |
| 1 | clear | set | clear |
| 2, local holder | clear | set | set |
| 2, otherwise | clear | clear | clear |
| 3 | set | clear | clear |
| > 3 | unchanged | unchanged | unchanged |

3. **Body update.** If the object has no physics instance (+240 = −1) and
   state ≠ 0: create physics (82388C68, arguments 1, 1). Otherwise: update
   physics (82388A08, argument 0). Both are native boundaries.
4. If 0x40 is now set: also set 0x400. (0x400 is never cleared by this routine,
   including on a later state 0; Q11.)
5. **Held-offset compensation.** If held: Pafter := physics point again;
   for the holder's editor,
   grabOffset := grabOffset × offsetScale − (Pafter − Pbefore) (component-wise),
   offsetDecay := 0, offsetScale := 1.
   This keeps the held reference point (physics point + grabOffset ×
   offsetScale) where it was when the body changes shape/centre, and restarts
   the offset fade (§2.1 reseeds decay on the next rotation).

Flag meanings (round 2, from their consumers):

- **0x40 "frozen"**: the body builder (824A1610, via 82388A08 → 8249A070 →
  824A1578) gives every body of a frozen object the Fixed motion type (5). So
  state 3 = immovable static collision.
- **0x400000 "keyframed request"**: in the same builder, a non-frozen object with
  this bit gets the Keyframed motion type (4). So a Phased object held by the
  local player is driven as a keyframed body: it moves to the controller target
  and pushes dynamic things but is not pushed back by them or stopped by them.
- **0x200000 "force dynamic"**: in the final body constructor (824A39A0, per
  FULL-RE-FINDINGS, not re-read) an authored-Fixed body becomes Dynamic (or
  Keyframed if 0x400000 is also set). So state 1 = every body simulated, even
  ones authored as fixed; this is what lets the held-object controller move it.
- **0x400 "at rest / velocity gate"**: velocity queries (82260CF0, per notes)
  return a fixed global vector instead of body velocities when it is set; the
  settle processor (§4.5) treats it as "has come to rest".

No flag here disables collision. Phased does **not** lose collision in this
code: while held (local holder) it is keyframed rather than dynamic, and on
release it is frozen exactly like Fixed but skips the settle/validation step
(§4.5). What "phased" means to the user (place intersecting other objects,
does not fall or get pushed out) comes from those two differences.

### 4.4 When selection/transition run (callers; from FULL-RE-FINDINGS, not re-read here)

- Grab (82450E10): after the selection reset and queue removal, select and
  transition (object is now held).
- Release (82451250): after ownership is cleared, select and transition (now
  unheld).
- Property change (event 5, 824515C8): select before and after committing the
  property; transition **only if the two states differ** (comparing mode
  labels instead would be wrong, e.g. Fixed→Phased released is 3→3, no
  transition).
- Variant record apply (823C6B28) on other runtime objects sharing the slot.

### 4.5 Release settling and the "special" predicate (round 2; 82451250, 8244F300, 8244F400, 8244A5F0)

Disassembled from the image:

1. **Release (82451250, 82451320..824513B4).** After the selection reset, read
   the object's variant record. If its property has bit 0x80 (Phased) — or the
   release was called with its "force" argument — the property gets 0x40 OR-ed
   in and is committed (no change for 0xC0), the object is notified with
   "phased = true" (8244F838 with 1, 8220BD58 with 1) and it is **not** queued
   for settling. Otherwise it is notified with false and **queued for
   settling** (8244F300). Then physics is selected and transitioned (§4.2–4.3).
2. **Queue for settling (8244F300).** Skipped in session type 4, if the object
   is already settling (the special predicate below), or if the queue already
   holds 32 objects. Otherwise append (datum, last-point sentinel
   (65536, 65536, 65536) from 82128FDC) to the per-game queue (count at game
   +0x31EC) and set bit 0x4000 in the object's multiplayer runtime block
   (object halfword +0x1E6 is that block's offset; flag halfword at block +0x14),
   then notify (827FC618).
3. **Special predicate (8244A5F0)** = "this object is currently settling": true
   only when the game mode index is 1..5 with a non-null mode entry (table
   835718E0), the Forge session predicate 82265430 holds, 821DF530 returns 1,
   and the object's multiplayer block has bit 0x4000. So a released Normal
   object that is settling selects state 1 (all bodies simulated, force-dynamic)
   instead of state 0.
4. **Settle processor (8244F400), every tick, per queued object:**
   - If the object has gone, has flag 0x400 (at rest), or has become parented:
     dequeue it (8244F740: clears the settling bit and re-runs physics
     selection/transition, so it drops to state 0), then run the placement
     validity check (82451DA8). **If invalid, the object is deleted**
     (82936B78); if valid, the variant is notified (827FBBA0, argument 2).
   - Otherwise, for runtime block type byte (+0x16) 13..16 only, run the contact
     response (82235650) against its cached point; then notify (8244F838 false).

Consequences: Normal objects are released into full simulation, fall/settle,
are then made ordinary state 0 and are deleted if they settle somewhere invalid.
Fixed objects are frozen at release but still go through the settle queue and
its validity check once at rest. Phased objects are frozen at release and never
validated.

### 4.6 The at-rest marker and the settled-object delete rule (round 3)

Writers of object flag 0x400 found in the image (all read-modify-write of the
64-bit flag word +0x100):

- 8220BD58 (release notification, argument "phased"): for an object type in
  mask 0x3ADF with physics flag 0x100 and a physics instance — when the
  argument is false it first wakes the physics instance (8222D9C0 with 0) and
  then **clears** 0x400; when true it **sets** 0x400. So every non-Phased
  release starts settling with 0x400 clear; a Phased release has it set.
- 8244A2A0 (§4.3) and 828203A0 (another rebuild path): after creating or
  rebuilding physics, 0x400 := (0x40 frozen is set). 8244A2A0 only sets;
  828203A0 sets or clears.
- 829341FC (object creation): from a definition flag bit.
- 8293DD10 (attachment change): set or cleared from its argument / the parent
  object's 0x400.
- 82A12388: set when global byte 84080044 is non-zero (purpose unknown).
- 82A33750: cleared on a definition flag (purpose unknown).

So 0x400 means "not moving under physics" (frozen or sleeping); velocity
queries return a fixed vector while it is set. For a Normal object, no writer
found here sets it when the object comes to rest by itself; the settle loop
ends for such objects when it becomes parented, deleted, or some other path
(physics deactivation not found) sets 0x400 (Q11).

**Delete rule (settle processor 8244F400, validity 82451DA8).** When a queued
object is dequeued (gone, 0x400 set, or parented), it is checked; it is valid
only if all hold:

1. 82451BA8 (object-against-world test also used by the held update) is false;
2. its origin (8225EA20) passes the world point test 82328310(point, 0);
3. 8228F4D0(object) is true;
4. if the object has a multiplayer runtime block whose type byte (+0x16) is 13,
   15 or 16: 82484EC8(object, 0, 1) reports no flag in any of its three result
   bytes, and the globals-tag check 8243BF98 (globals 8405D340 → +0x184 → +0x54,
   with the object's centre from 8293A3B0) passes. Other block types, or no
   block, skip this step.

An invalid object is deleted with 82936B78; a valid one has its variant slot
notified (827FBBA0, 2). The semantics of 82451BA8, 82328310, 8228F4D0,
82484EC8 and 8243BF98 were not decoded (Q18).

---

## 5. Numeric coordinate panel

### 5.1 Fields, units, ranges, steps (constructor 8268AE80)

Six numeric controls, in menu order (control records at editor-panel +216,
+236, +256, +276, +296, +316; label string IDs 0x80619..0x8061E =
`forge_object_edit_coords_x`, `_y`, `_z`, `_pitch`, `_yaw`, `_roll`; help IDs
0x8061F..0x80624 = the same names with `_description`; decoded from the Ravine
map's string table in round 2):

| Order | Edits (panel offset) | Quantity | Range | Step |
| --- | --- | --- | --- | --- |
| 1 | +152 | position X | −1000 .. 1000 | 0.1 |
| 2 | +156 | position Y | −1000 .. 1000 | 0.1 |
| 3 | +160 | position Z | −1000 .. 1000 | 0.1 |
| 4 | +168 | angle 2 (pitch, rotation about local/world Y) | −180 .. 179 | 1.0 |
| 5 | +164 | angle 1 (yaw, rotation about Z) | −180 .. 179 | 1.0 |
| 6 | +172 | angle 3 (roll, rotation about X) | −180 .. 179 | 1.0 |

Ranges/steps are shared descriptors at panel +176 (position: min +180, max +184,
step +192) and +196 (angles: min +200, max +204, step +212). Position units are
world units; angles are degrees (converted with π/180 at commit). Menu order is
X, Y, Z, Pitch, Yaw, Roll (labels decoded in round 2). The constructor also sets panel +40 and
+44 (player, object) to none and clears the byte flags at +36, +188, +208.

Angle range is asymmetric: +180 itself is not enterable; yaw/roll derived from
a pose can be exactly ±180° (§5.3), pitch ±90°.

### 5.2 Panel state

- +40 player index, +44 object datum.
- **Applied** block: pose +48..+99 (52 bytes), angles +100..+111 (3 floats).
- **Working** block: pose +112..+163, angles +164..+175 (yaw +164, pitch +168,
  roll +172). The numeric controls write directly into working position
  (+152..+160) and working angles.
- **Populate (round 2; 8268B130, panel vtable slot after the constructor).**
  Run by the Forge object-menu refresh (826BE6C0), which runs when menu pages
  are pushed or popped (82686040/82686F60/82687020). If the player's editor
  holds an object:
  1. Working pose := the editor's persistent pose (editor +84), scale included.
  2. Working angles := rule E→ of that pose, converted to degrees (×57.29578,
     constant 82128B50) and rounded half-away-from-zero to whole degrees.
  3. Working position := the pose position rounded half-away-from-zero to
     0.1 (×10.0 at 82128A04, round, ×0.1), **then** minus the scenario's
     sandbox origin (§5.4). Rounding happens before the subtraction.
  4. Applied pose := working pose; applied angles := working angles.
  Then, if the player is valid, the angle controls' step is set to the current
  rotation-snap increment in degrees (table 833F195C by editor +224, minimum
  1°); if that changes the step, the descriptor's "changed" byte (+208) is set.
  So with snap 15° the angle fields step in 15°; with snap off, 1°.

### 5.3 Pose ↔ angles conventions

**Rule E→ (pose to angles; 8232F960 → 8223B050 + 823C0208).** From F and U
(L recomputed as U × F):

- pitch = −asin(clamp(U.x, −1, 1)).
- c = cos(pitch). If c > 0.0001 (double-precision constant):
  roll = atan2(−U.y / c, U.z / c); yaw = atan2(−L.x / c, F.x / c).
- Else (gimbal): roll = 0; yaw = atan2(F.y, L.y).
- Result order (yaw, pitch, roll), radians; yaw and roll in (−π, π], pitch in
  [−π/2, π/2].

**Rule →E (angles to pose; 8232F9B8 → 82265D10).** With cy, sy = cos/sin yaw;
cp, sp = pitch; cr, sr = roll:

- F = (cy·cp, sy·cr − cy·sp·sr, cy·sp·cr + sy·sr)
- L = (−sy·cp, cy·cr + sy·sp·sr, cy·sr − sy·sp·cr)
- U = (−sp, −cp·sr, cp·cr)

Equivalently, the object-to-world rotation is Rx(roll) · Ry(−pitch) · Rz(yaw):
read extrinsically, yaw about world Z first, then pitch about world Y
(positive pitch raises the nose), then roll about world X (positive roll turns
L toward +Z). Read intrinsically: roll about X, then pitch about the new local Y,
then yaw about the newest local Z. U never depends on yaw. Rules E→ and →E are
mutual inverses away from the gimbal case. Only F and U are produced by →E; L is
always rebuilt by the caller as U × F.

### 5.4 Commit (8268B410)

1. **Change test.** Compare the working pose bytes (+112..+163) with the applied
   pose (+48..+99); if identical, compare working angles (+164..+175) with
   applied angles (+100..+111). If both are byte-identical: clear panel byte
   +208 and stop (no event). The comparison is bytewise, so +0 vs −0 counts as a
   change.
2. **Validate.** The object (+44) must resolve (82271460, any type) and the
   player (+40) must resolve (822714E0). If either fails, skip to step 5 (no
   event, but the working values are still accepted as applied).
3. **Build pose.**
   - Working position += the scenario's **sandbox origin point**, written back
     in place. Global 8405D33C is the loaded scenario (`scnr`) tag definition
     (set at map load by 82340B40, which looks up group 'scnr' and stores it
     next to 'matg' at 8405D340); +124..+132 is its SandboxOriginPoint field
     ("forge coordinates are relative to this point" in the Gen4 schema).
     Translation only; no rotation.
   - Angles: (yaw, pitch, roll) = working (+164, +168, +172) × π/180.
   - F, U from rule →E written to working pose F (+116) and U (+140); L := U × F
     (+128). The working basis is entirely replaced; only angles matter.
     Working scale (+112) is carried unchanged.
4. **Emit event 13** (825812D0) for the player (index & 0xFFFF): payload =
   object datum + the full 52-byte working pose (scale, F, L, U, world position).
5. Applied pose := working pose; applied angles := working angles; clear +208.

There is no range check in the commit itself; ranges are enforced only by the
numeric controls.

### 5.5 Event 13 handler (824500A8 at 824503C4..82450428) — ApplyHeldCoordinatePose

1. Validate the sender and object (82451908). Fail → ignore.
2. The player's editor held datum must equal the event's datum. Otherwise
   ignore.
3. Copy the 52-byte pose into the persistent pose (editor +84): scale, basis and
   position all replaced.
4. Clamp the position into the map-variant bounds (variant +696: minX, maxX,
   minY, maxY, minZ, maxZ) with rule B (82282580): per axis, if min > p use min;
   else if max < p use max; else keep p. (Min is tested first, so inverted
   bounds yield min.)

Not touched: holdDistance, grabOffset, offsetScale/Decay, manipulation input,
magnet target, rotated flag, snappedBasis. It is a one-shot target change, not a
lock: the very next held update continues from this pose with the normal
movement, contact, snap (§3.2 consequence) and magnet stages.

### 5.6 Live preview, accept, cancel, restore (round 3)

Halo 4's behaviour, from the object-properties screen update 826BE090 (method
at 821817B0) and the panel interface:

- **Panel interface** (vtable 82143800): slot 0 title, slot 1 item count
  (panel +32), slot 2 item i, slot 3 **apply** (8268B410, §5.4).
- **Every update of the screen:** if the player or the player's held object
  differs from the cached pair (screen +0x10, +0x14) the screen re-initialises
  every panel, including populate (§5.2). Otherwise it calls **apply on the
  current page** (screen page stack: depth +0x48, pages at +0x30 + 8·depth,
  826BE52C..826BE568). Apply only acts when the working values differ from the
  applied ones (§5.4 step 1).
- So in Halo 4 an edited number takes effect on the object at the next screen
  update: **edits are live**, one event 13 per change. There is no separate
  preview store, no confirm step, and nothing in the Forge-side code restores
  the old pose on Back or cancel: leaving the page keeps the edited pose.
  Page push/pop refreshes all panels (826BE6C0 from 82686040/82686F60/82687020),
  which re-reads the held pose.
- **Value lists** (range descriptor vtable 82143820): number of choices =
  trunc(trunc(max − min + 1) / step); choice i = min + i·step; the choice index
  for a value is trunc((value + 0.49·step − min) / step) modulo the count
  (constant 0.49 at 82128B64), so out-of-range values wrap. Position: 20010
  choices of 0.1; angles: 360 choices of 1° (or 360/snap choices when snap is
  on, §5.2).
- **Panel byte +208** is the angle range descriptor's "choices changed" flag
  (descriptor +12, returned by 8268CBD8): set by populate when the angle step
  changes, cleared by apply. **+188** is the same flag for the position
  descriptor (never set by these functions). **+36** is initialised to 0 by the
  constructor and not read by any panel function examined.
- Whether the generic list widget itself restores a value when its list is
  dismissed with Back (and so whether a scrolled-but-cancelled value is applied
  and then reverted) is inside the generic menu framework, which was not traced
  (Q16).

---

## 6. Magnet-marker visibility while editing (825826B0)

What is shown/hidden is the per-player **magnet marker display** (marker
effects created by 825827B0 and removed by 82582950, native boundaries) on the
held object and on the current magnet target. The objects themselves are never
hidden by this code.

Inputs: player, priorHeld, priorTarget (the pair captured before the change).
Current values: held (editor +0), magnetTarget (+4), magnetEnabled (+82).

- **Magnets enabled:**
  1. If magnetTarget ≠ priorTarget: remove markers from priorTarget (if valid),
     then show markers on magnetTarget (if valid).
  2. If held ≠ priorHeld: remove markers from priorHeld (if valid), then show
     markers on held (if valid).
  If a pair is unchanged nothing is done for it (no re-show).
- **Magnets disabled:** remove markers from priorHeld, held, priorTarget,
  magnetTarget, in that order (each only if valid). Nothing is shown.

Callers (all gated on the player being local, 822ED938): selection/release
82449ED8 (prior pair captured before held changes), magnet-target setter
8244A118 (prior pair loaded before storing the new target), and the magnet
enable toggle (event 16, producer 82685EE0, per FULL-RE-FINDINGS; not re-read).

Effective rule: while magnets are on, markers are shown on the held object and
on the current target only, updated on change; turning magnets off clears all
of them. Because an enabled call with unchanged pairs shows nothing, re-enabling
magnets with the same held/target would not restore markers unless the caller
passes "none" as the prior pair.

---

## 7. Tuning constants

### 7.1 Image literals (all read from h4-image.bin)

| Value | Address | Used for | Function |
| --- | --- | --- | --- |
| 0.0 | 821289E0 | zero comparisons, decay floor fallback, offsetDecay reset | 8244A7D0, 8244A2A0, 823C0208 |
| 1.0 | 821289E4 | offsetScale reset; rounding sign; reciprocal; angle step 1.0 | 8244A2A0, 82451A38, 8268AE80 |
| 0.1 | 821289EC | trigger threshold; position step | 82368CE0, 8268AE80 |
| 0.5 | 82128A08 | round-half-away offset | 82451A38 |
| 5.0 | 82128A10 | rotation gain K; decay seed multiplier | 8244B518, 8244A7D0 |
| 0.3 | 82128A1C | push/pull per tick (section 03) | 82452738 |
| 10.0 | 82128A04 | position rounding to 0.1 at populate | 8268B130 |
| 65536.0 | 82128FDC | settle-queue last-point sentinel | 8244F300 |
| 0.017453292 (π/180) | 82128A20 | degree→radian for snap step and commit | 8244A8D8, 8268B410 |
| −1.0 | 82128A44 | rounding sign; clamp | 82451A38, 823C0208 |
| 0.0001 | 82128A54 | rule N threshold; min rotation angle; snap basis equality | 8228ACE8, 8244B518, 8244A8D8 |
| 0.2 | 82128AE0 | controller parameter of held submission (other section) | 8244A8D8 |
| 57.29578 (180/π) | 82128B50 | radian→degree for populate angles | — |
| 1000.0 | 82128D6C | position max | 8268AE80 |
| −1000.0 | 82128F98 | position min | 8268AE80 |
| −180.0 | 82129244 | angle min | 8268AE80 |
| 179.0 | 82129684 | angle max | 8268AE80 |
| 0.0001 (double) | 82129170 | gimbal threshold on cos(pitch) | 823C0208 |
| [0,90,45,30,15,5] (int32) | 833F195C | snap increments (degrees) by mode | 8244A8D8 |
| (0,0,1) | 82125188 via 833F7EAC | world up | 8244B518 |
| (0,0,−1) | 821251BC via 833F7EB8 | yaw axis | 8244B518 |
| (0,0,0) | 82125110 via 833F7E98 | temporary pose position during rotation | 8244B518 |
| byte 0 | 8407EFFA | alternate held-placement path switch (section 03) | 8244D0E0 |
| byte 0 | 8407EFFB | force offset-decay seeding | 8244A7D0 |

### 7.2 Code literals (immediates)

| Value | Meaning | Function |
| --- | --- | --- |
| 0xC0 | physics property mask | menu, 8244A180 |
| 0x40 / 0x80 | Fixed bit / Phased bit tests | 8244A180 |
| 0x3FF | property halfword keep-mask on edit | 8268C340 |
| 651, 76, +5356, +62 | variant record count, stride, base, property halfword | 8244A180 |
| 0x40, 0x200000, 0x400000, 0x400 | runtime object flags | 8244A2A0 |
| 0x100 | object physics-connected flag required for rotation | 8244A6A8 |
| 0x390 (0x3F0 & ~0x60), 0x3ADF | allowed object-type masks | 8244A6A8 |
| 5 | body motion type that blocks rotation (Fixed) | 8244A6A8 |
| 0x80 | instance flag that blocks rotation | 8244A6A8 |
| 4 | body motion type tested as keyframed (per notes) | 82469630 |
| 13 | coordinate event id | 8268B410 |
| 4144 / 336 | player record / editor stride | 82368CE0, 825826B0 |

### 7.3 Configuration globals

None. No function in this section reads the Forge-globals tag. The only runtime
global data read are the time record (tick duration, TLS +88 → +8), the
coordinate-origin pointer 8405D33C, the variant (for record and bounds) and the
two switch bytes above.

---

## 8. Per-tick order (summary)

1. Input shaping (§1) on the frame packet.
2. If the held-placement path applies (section 03 §4.4): rotation stage (§2.1),
   offset decay, distance rule D, held update containing snap (§3.2) and
   magnets, monitor follow.
3. Coordinate commits (§5.4) and physics-mode edits (§4) arrive as events
   between ticks and modify the persistent pose / property word; the next tick
   proceeds from there.

---

## 9. Corrections and confirmations relative to earlier notes

- FULL-RE-FINDINGS rotation axis description is confirmed and made precise: yaw
  axis is world **down** (0,0,−1), not up; pitch axis is worldUp × view; roll
  axis is the view; gain 5.0; threshold strictly > 0.0001.
- The composition order (rotation applied in world frame, R ∘ pose) is inferred
  from the routine zeroing and restoring the pose position around the compose
  call. Round 2: also confirmed by the project's earlier execution of the
  unchanged routine (test_grab.cpp, 384 cases incl. a 90-degree-yaw starting
  pose, expectation = Rodrigues rotation of each world-space basis vector),
  which a local-frame composition would fail. Lane-by-lane decoding of 8226BFC0
  was not done.
- 8244A180 table in FULL-RE-FINDINGS confirmed. Additional detail: the 0x80 test
  precedes 0x40; invalid non-0xFFFF slots are not guarded (Q9).
- 8244A2A0 flag table confirmed. Additional details not in the notes: the whole
  routine is skipped without a model/physics-model reference; create vs update
  choice depends on (no instance AND state ≠ 0); 0x400 is set but never cleared.
- 8268C340 additionally clears property bits 10..15 (AND 0x3FF); notes did not
  mention this.
- Coordinate panel: the menu's fourth control edits pitch (+168), the fifth yaw
  (+164); storage order is yaw, pitch, roll but display order is X, Y, Z,
  Pitch, Yaw, Roll.
- The commit adds the scenario sandbox origin to the position in place.

---

## 10. Open questions (round 3 status — Halo 4 behaviour only)

- **Q1 Physical controller layout.** RESOLVED for the default layout (§1.2):
  right trigger enables; left stick up/down = push/pull (up = closer), left
  stick left/right = roll (right = clockwise to the player), right stick
  left/right = yaw (right = counter-clockwise from above), right stick up/down
  = pitch (up = top away; reversed by look inversion). Other layouts follow
  the stick-layout and binding preferences.
- **Q2 Rotation-available flag.** RESOLVED: set by 823F65E8 when the player's
  Forge `inputActive` byte (player +1888) was set on the previous tick; carries
  (−Rx, Ry).
- **Q3 Dead zones / curves.** RESOLVED for Ravine in "Round 5: Ravine values" (the text below is the round 4 status): axial dead zones 7849/8689 with
  rescaling, optional globals overrides, square-to-circle correction, network
  5-bit quantisation (§1.2). UNRESOLVED: the per-stick response-curve function
  and the optional dead-zone override values are tag data (Forge monitor unit
  definition / globals), not code, and were not extracted from the map; also
  the purpose of 823F5B00 (called on the stick vector before the layout step).
- **Q4 Maths helpers.** RESOLVED (round 2).
- **Q5 Compose order.** RESOLVED (round 2).
- **Q6 Switch bytes 8407EFFA/B.** UNRESOLVED: no writer found; image value 0
  is Halo 4's shipped behaviour.
- **Q7 Rotation-gate types.** RESOLVED.
- **Q8 Starting snap setting.** RESOLVED: off (0) until changed in the menu.
  The menu's initially highlighted entry: UNRESOLVED.
- **Q9 Out-of-range variant slot.** RESOLVED: unguarded read in the original
  (undefined behaviour; never valid data).
- **Q10 Special predicate.** RESOLVED (settling, §4.5).
- **Q11 At-rest marker.** PARTLY RESOLVED: all direct writers listed (§4.6).
  UNRESOLVED: how a Normal object that simply stops moving gets 0x400 (no
  physics-sleep writer found), hence when its settling ends.
- **Q12 Physics flags / Phased collision.** RESOLVED (round 2), with 0x400
  refined in §4.6.
- **Q13 Labels.** RESOLVED.
- **Q14 Populate.** RESOLVED.
- **Q15 Coordinate origin.** RESOLVED: scenario SandboxOriginPoint. Double-add:
  RESOLVED as real Halo 4 behaviour — apply adds the origin to the working
  position in place, and only a refresh (object/player change or page push/pop)
  re-reads it; a further edit on the same page without a refresh adds the
  origin again to the untouched axes. Visible only on maps with a non-zero
  sandbox origin.
- **Q16 Preview/cancel.** RESOLVED for the Forge side (§5.6: live apply, no
  restore). UNRESOLVED: whether the generic list widget restores its own value
  on Back. Panel bytes: +208/+188 RESOLVED; +36 has no reader in the functions
  examined.
- **Q17 Pose scale.** RESOLVED.
- **Q18 Validity sub-tests.** UNRESOLVED: meanings of 82451BA8, 82328310,
  8228F4D0, 82484EC8 and 8243BF98 inside the delete rule (§4.6).

## 11. Round 2 changes

- Input fields given semantic meanings (forward → push/pull, sideways → roll,
  look → yaw/pitch) and Halo 3 packet counterparts (§1).
- Rotation-gate object types named (§2.3).
- Starting snap mode established as off; the menu value 5 does not reach the
  editor without event 14 (§3.1).
- Physics flag meanings added; Phased shown not to remove collision (§4.3).
- New §4.5: release settle queue, the special predicate, the per-tick settle
  processor and deletion of invalidly settled objects.
- Coordinate labels decoded; menu order X, Y, Z, Pitch, Yaw, Roll (§5.1).
- New populate rules: rounding to 0.1 and whole degrees, sandbox-origin
  subtraction, angle step = snap increment (§5.2).
- Coordinate origin identified as the scenario SandboxOriginPoint (§5.4).
- Compose order backed by prior executed evidence (§9); maths helper edge
  behaviour recorded (Q4).
- Open questions re-tagged (§10).

## 12. Round 3 changes

- All project-wiring and Halo 3 substitute notes removed; the document now
  states Halo 4 behaviour only, with gaps listed in §10.
- New §1.1: Halo 4 input chain from the controller poll to the frame action
  (raw controller table, button order, trigger indices, control block,
  control→action copy, network quantisation of the rotation and trigger
  inputs). Physical assignment of trigger/stick to each field still open.
- New §4.6: all writers of the at-rest marker 0x400 and the exact validity rule
  that deletes a settled object.
- §5.6 rewritten from Halo 4: numeric edits are applied live on every screen
  update; no restore on Back in Forge-side code; value-list arithmetic and
  wrap-around; panel flags +208/+188 identified.
- §10 re-tagged without Halo 3 substitutions.

## 13. Round 4 changes

- New §1.2: full Halo 4 chain from controller to the manipulation inputs —
  raw input indices, input abstraction, axial dead zones 7849/8689 and their
  rescaling, optional globals dead zones, stick layouts, response curve source,
  square-to-circle correction, sign flips, look inversion.
- Physical mapping with signs established for the default layout (right
  trigger gate; left stick push/pull and roll; right stick yaw and pitch).
- Rotation-available flag setter found (previous tick's Forge input-active
  byte); one-tick latency described.
- Default button layout table recorded (44 abstract actions; names absent).
- Q1/Q2 resolved; Q3 narrowed to tag-data curve contents and 823F5B00.

## Round 5: Ravine values

Read offline from `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\disc2-assets\ca_forge_ravine.map`
(globals tag `matg`, tag index 5, definition at cache address BD922814; same
tag-table walk as `C:\Programming\GitHub\OpenH3M\tools\h4-forge\extract_camera_curve.py`).
Nothing was run except a read-only byte reader.

### Which data the control step uses on Ravine

- **Unit/weapon descriptors:** all four biped tags in the map (indices 10554,
  16155, 16315, 16397) have empty per-stick blocks in both candidate unit
  structures (definition +0x23C and +0x2B4, entries +0x60/+0x6C). So the
  per-stick descriptors always come from the globals tag, as long as the
  controlled unit is not seated and holds no weapon that has its own block
  (weapon definition +0x318/+0x31C). That weapon case was not checked; the
  Forge monitor normally holds none.
- **Dead-zone override switch** (input record byte +0xB09): set to 1 by the
  input system's new-map initialiser (823EF468, game-system table entry
  82123680) and cleared only by its map-dispose entry (823EF4D8). So during
  play the globals override replaces the built-in 7849/8689.

### Dead zones (globals +0x108/+0x10C block, 1 element at BD7A7368)

| Field | Value | Effect |
| --- | --- | --- |
| element +0x00 (inner, per axis) | 0.125 | D = trunc(0.125 × 32767) = **4095** for both sticks; per axis, v > 4095 → (v − 4095)·32767/28672, v < −4095 → (v + 4095)·32768/28673, otherwise 0 |
| element +0x04 (radial) | 0.125 | R = **4095**; after the axial step, a stick whose magnitude ≤ 4095 is zeroed, otherwise magnitude → (m − 4095)·32767/28672 along the stick angle (m first clamped to 32767) |

Both steps apply in that order. Each axis is then divided by 32767 and
clamped to [−1, 1].

### Per-stick descriptors (globals +0x114/+0x118 block element BD7A74E8; stick blocks at element +0x0C and +0x18)

| | Left stick (move) BD7A7430 | Right stick (look) BD7A74C0 |
| --- | --- | --- |
| type byte (+0x00) | 1 → no square-to-circle correction | 2 → square-to-circle correction applied |
| response function (+0x1C/+0x20 → data reference) | 60-byte function at BD7A73E0 | 84-byte function at BD7A7458 |
| other fields, not used by this step | 0.95, 0, 0, 0, 0, 2π | 0.95, 1.15, 1.15, 3.0, 2.0, 2π |

Both functions are piecewise cubic curves (function type 8, flags 0x34
including "clamp to [0, 1]", output range 0..1). Each segment applies while
x ≤ its end value, with y = a·x³ + b·x² + c·x + d in the global x, then y is
clamped to [0, 1]:

- **Left stick:** a single segment (end = largest float):
  a = −0.5830377, b = 0.9754766, c = 0.6075611, d = 0.
- **Right stick:**
  - x ≤ 0.505: a = 1.5447578, b = −0.6235934, c = 0.2508628, d = 0.
  - x > 0.505: a = −1.9517484, b = 5.7023044, c = −3.4632044, d = 0.7126485.
  - The two segments meet at 0.1666 when x = 0.505.

The input x is the stick's magnitude after the dead zones (0 to √2). The
output replaces the magnitude, and the stick keeps its direction.

| Magnitude in | Left stick out | Right stick out |
| --- | --- | --- |
| 0.00 | 0.0000 | 0.0000 |
| 0.05 | 0.0327 | 0.0112 |
| 0.10 | 0.0699 | 0.0204 |
| 0.15 | 0.1111 | 0.0288 |
| 0.20 | 0.1559 | 0.0376 |
| 0.25 | 0.2037 | 0.0479 |
| 0.30 | 0.2543 | 0.0608 |
| 0.35 | 0.3071 | 0.0776 |
| 0.40 | 0.3618 | 0.0994 |
| 0.45 | 0.4178 | 0.1274 |
| 0.50 | 0.4748 | 0.1626 |
| 0.55 | 0.5322 | 0.2081 |
| 0.60 | 0.5898 | 0.2660 |
| 0.65 | 0.6469 | 0.3348 |
| 0.70 | 0.7033 | 0.4131 |
| 0.75 | 0.7584 | 0.4994 |
| 0.80 | 0.8118 | 0.5923 |
| 0.85 | 0.8632 | 0.6902 |
| 0.90 | 0.9119 | 0.7918 |
| 0.95 | 0.9577 | 0.8956 |
| 1.00 and above | 1.0000 | 1.0000 |

After the curve, the right stick only (type 2) gets the square-to-circle
correction: if both components exceed 0.0001 in magnitude, both are multiplied
by √(1 + (smaller/larger)²) and clamped to [−1, 1]. The Forge rotation inputs
then take these right-stick values through §1.2 (yaw = −x, pitch = y) and the
signed-square × 5 of §2.2. Push/pull and roll take the left-stick values
(curve only, no correction).

Q3 is resolved for Ravine with these values. The one remaining gap is the
weapon-descriptor case, which only applies if the controlled unit holds a
weapon with its own block. 823F5B00 (called on the stick vector before the
layout step) remains undecoded.

## 14. Round 5 changes

- Ravine globals dead-zone override (0.125 / 0.125 → 4095 inner per axis,
  4095 radial) and its always-on switch documented.
- Left/right stick response curves extracted, with coefficients and an
  evaluated sample table; descriptor types (left: no correction; right:
  square-to-circle).
- Confirmed every biped tag in the map lacks its own stick descriptors, so the
  globals values apply.
