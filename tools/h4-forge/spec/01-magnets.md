# Forge magnets specification, section 1: markers, selection, alignment and snap state

Clean-room behavioural specification derived by static reading of the Halo 4
functions recompiled into
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\forge_original.cpp`.
Three small helpers that live outside that file (`82582A68`, `82582610`,
`82937F50`) were read in
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\generated\halo4_recomp.202.cpp`,
`...\halo4_recomp.240.cpp` and `...\halo4_recomp.52.cpp`. Numeric constants were
read directly from the original decoded executable image
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\h4-image.bin`
and from the retail Ravine Forge globals block
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\forge-globals.bin`.
Nothing was built, run or tested.

Function addresses (for example `sub_82582250`) are given as provenance for
every rule. Descriptive names are this document's own.

---

## 0. Conventions used in this section

- **World units** are the engine's native distance units. All distances in this
  section are in world units; all angles in radians unless stated as degrees.
- **Axes.** A basis is three unit vectors: *forward* (local +X), *left*
  (local +Y) and *up* (local +Z). The engine is Z-up.
- **Transform (52 bytes).** scale (1 float), forward (3), left (3), up (3),
  position (3). Applying a transform T to a local point p gives
  `T.position + T.scale * (p.x*forward + p.y*left + p.z*up)`. Composing
  `A ∘ B` gives scale `A.scale*B.scale`, basis `A.basis * B.basis`, position
  `A.position + A.scale * A.basis * B.position` (`sub_8226BFC0`).
- **Quaternion.** stored x, y, z, w (w last). Product `a ⊗ b` is the standard
  Hamilton product (`sub_822A1F98`). Normalise: if `|q|² > 0` divide by `|q|`,
  else return identity (0,0,0,1) (`sub_82226460`). Conjugate is produced by
  multiplying w by −1 (constant at `821289E0+100` = −1.0).
- **Quaternion to basis** (`sub_82282728`). With `s = 2/|q|²` when
  `|q|² > 0.0001`, else `s = 0`:
  - forward = (1 − s(y²+z²), s(xy + wz), s(xz − wy))
  - left    = (s(xy − wz), 1 − s(x²+z²), s(yz + wx))
  - up      = (s(xz + wy), s(yz − wx), 1 − s(x²+y²))
  i.e. forward/left/up are the images of local X/Y/Z under the standard
  rotation of q.
- **Basis to quaternion** (`sub_8229E900`): standard trace method with
  largest-diagonal fallback, the inverse of the mapping above.
- **Rotate vector by quaternion** (`sub_8232F830`): standard `q v q*`.
- **Angle between two orientations** (`sub_8232F8D8`):
  `angle = 2 * acos(|clamp(dot(q1,q2), −1, 1)|)` (4-component dot).
- **Quaternion to Euler** (`sub_82331BC8`, gimbal tolerance ε passed in,
  0.0001 here). Output order (yaw, pitch, roll):
  - `t = z*x − y*w`
  - pitch = asin( clamp(2t, −1, 1) / |q|² , then clamped again to [−1,1] )
  - if `| |t| − 0.5 | < ε` (gimbal): roll = 0,
    yaw = 2 * sign(t) * atan2(x, w), pitch = sign(t) * π/2
    (sign(t) is −1, 0 or +1; π/2 from `821289E0+232`).
  - otherwise: roll = atan2(2(xw + yz), w² − x² − y² + z²),
    yaw = atan2(2(zw + xy), w² + x² − y² − z²).
- **Euler to quaternion** (`sub_82264A58`). With half angles
  A = yaw/2, B = pitch/2, C = roll/2 (the 0.5 is `821289E0+40`):
  - x = cosB cosA sinC + sinB sinA cosC
  - y = sinC cosB sinA − cosC sinB cosA
  - z = cosC cosB sinA + sinC sinB cosA
  - w = cosB cosA cosC − sinB sinA sinC
  This is the exact inverse of the Euler extraction above (pure yaw is a
  rotation about +Z; positive pitch raises the nose, i.e. forward gains +Z;
  pure roll is about +X).

---

## 1. Markers (magnets)

### 1.1 Source definition record (48 bytes, big-endian)

Read by `sub_8259E9A8`. Field use by the magnet code:

| Offset | Content | Used by magnets? |
| --- | --- | --- |
| 0 | region index (signed byte; −1 = any region) | yes, filtering |
| 1 | permutation index (byte) | yes, filtering |
| 2 | node index (byte) | yes, chooses the node frame |
| 3 | flags byte (value 1 in every retail record; schema name "has node relative direction") | **not read** |
| 4..15 | local position (3 floats), node-relative | yes |
| 16..31 | local rotation quaternion (x,y,z,w), node-relative | yes |
| 32 | scale float (0.1 on 728 retail records; 0.768 on five Arch Brace records) | copied, **never read** by selection or alignment |
| 36..47 | direction vector (1,0,0 in retail records) | **not read** |

Markers belong to a named marker group on the render model. The group name is
the string id stored in Forge globals offset +0x1C (value `0x193`, the
"sandbox_magnet" group), returned by `sub_82582A68`; if the globals block is
absent it returns −1 (no group).

### 1.2 Built runtime marker (112 bytes)

`sub_8259E9A8` builds up to a caller-given capacity (32 for magnets) runtime
markers from the definitions of one group:

| Offset | Content |
| --- | --- |
| 0 | node index (16-bit) |
| 4..55 | **local transform**: scale 1, basis from the definition quaternion, position from the definition (local position at +44/+48/+52) |
| 56..107 | **world transform** = node transform ∘ local transform (world forward +60, world left +72, world up +84, world position +96/+100/+104) |
| 108 | definition scale float (copied unchanged) |

Build rules, in definition order (`sub_8259E9A8`):

1. A definition is included when no permutation array is supplied, or its
   region index is −1, or the object's current permutation for that region
   equals the definition's permutation byte. Otherwise it is skipped.
2. If an included definition arrives when the output already holds `capacity`
   markers, processing stops (later definitions are ignored).
3. Local transform = (scale 1, rotation from the stored quaternion, stored
   position).
4. Node transform = the object's live node matrix for the definition's node
   index (world space). If no live node matrices are supplied, the node's
   rest pose from the render model is used instead (render-model node table,
   112-byte entries, position at +12, rotation at +24).
5. World transform = node ∘ local.
6. If the object is mirrored, the world *left* vector is negated (only that
   vector; forward, up and position are untouched).

There is **no per-marker radius, no per-marker fixed/locked flag and no
direction test** in the magnet code. The only per-marker data used are the
local transform, the world transform and the node they derive from.

### 1.3 Which object's markers

`sub_82582610` first walks the object's parent chain (object +36 holds the
parent datum, −1 at the root) to the **root** object and builds the root's
magnet-group markers (capacity 32) via the marker gatherer `sub_8226BCA0`
(outside the source file), which supplies live node matrices to
`sub_8259E9A8`. A child object therefore presents its root's markers.

`sub_82937F50` (candidate eligibility) checks the candidate object **itself**
(not its root): its definition's model must contain a marker group with the
configured name. It does not check the marker count.

---

## 2. Candidate search (`sub_82582250`)

Inputs: player index, held object datum, output record. The output record is
cleared; its candidate datum is set to −1; state starts at 0.

1. **Held markers.** Build the held object's markers (root rule, ≤32). If there
   are none, return state 0 with no candidate.
2. **Thresholds.** Obtain the snap radius R and snap angle Θ (section 3.1,
   `sub_825824E0`).
3. **Reference point** (`sub_824499A8`):
   `ref = heldPhysicsPoint + offset * offsetScale`, where offset is
   editor +56/+60/+64 and offsetScale is editor +36 (single-precision fused
   multiply-add per component). heldPhysicsPoint is world-space (physics body
   point, else object centre; see Q1). With no held object it is the zero
   vector (image pointer `833F7E98` → (0,0,0)). Offset and scale are zero at
   grab; a physics-state change sets a continuity offset with scale 1, which
   then decays (`max(scale − rate, 0)`, rate at editor +40). See Q1/Q10.
4. **Query radius.**
   `queryRadius = heldBoundingRadius + |heldPhysicsPoint − ref|`
   where heldBoundingRadius is the held object's runtime bounding-sphere
   radius (object +76). The distance is accumulated in the order y², then z,
   then x (multiply, then two fused multiply-adds), square-rooted, then added.
5. **Spatial query** (`sub_821F2050`, outside the file): objects of query
   category 1 matching object-type mask `0x3ADF` (type bits 0–4, 6, 7, 9,
   11, 12, 13), within `queryRadius` of `heldPhysicsPoint`, located from the
   held object's location (object +24), at most **64** results, in the
   query's own order. No sorting is applied afterwards. If zero, return
   state 0.
6. **Per result, in query order:**
   1. Skip if the object lacks the magnet marker group (`sub_82937F50`).
   2. Skip if it is the held object (datum comparison).
   3. Build its markers (root rule, ≤32).
   4. Score the best marker pair (section 3.2, `sub_82582C80`), giving score S
      and the chosen (held marker, candidate marker).
   5. Let d² = squared distance between the two chosen markers' **world**
      positions.
   6. **Snap test:** if `S > bestScore` (strict) **and** `d² < R²` (strict):
      bestScore = S, record both markers and the candidate datum, state = 2.
   7. **Otherwise, only while state ≠ 2:** let c² = squared distance between
      the candidate's and the held object's bounding-sphere centres
      (object +64/+68/+72). If `c² < bestCentre²` (strict): bestCentre² = c²,
      candidate datum = this object, state = 1.
7. Return the state (0, 1 or 2). The output record holds the candidate datum
   and, for state 2, copies of the chosen held marker and candidate marker.

Initial values: bestScore = −FLT_MAX (image `834BD2A4` = 0xFF7FFFFF);
bestCentre² = +FLT_MAX (image `82128A34` = 0x7F7FFFFF), so state 1 has **no
distance limit**: any eligible queried object can become the state-1
candidate.

Consequences that follow from this order:

- Once any state-2 candidate exists, later objects can replace it only by a
  strictly higher score that also passes the distance test; the state-1
  branch no longer runs.
- A state-1 candidate recorded earlier is overwritten by a later state-2
  candidate.
- An object whose pairs all fail validation (score stays −FLT_MAX) can still
  be the state-1 candidate.
- Equal scores keep the earlier object (query order).

State meaning: **2 = snap available**, **1 = a nearby magnet-bearing object
whose markers should be shown, but no snap**, 0 = nothing.

---

## 3. Scoring and pair validation

### 3.1 Thresholds (`sub_825824E0`)

- Radius base: the held object's bounding radius (object +76) when editor +0
  (held datum) is valid; else the object at editor +24 when that is valid;
  else 0.0 (image `821289E0`).
- Sensitivity index k = editor +268 (default 2, set by `sub_82449DD8`).
- With Forge globals present:
  - if k ≤ 4: `R = factor[k] * radiusBase`, factor[k] = globals +0x28 + 4k;
  - if k > 4: `R = radiusBase` (no factor);
  - `Θ = globals +0x3C (degrees) * 0.017453292` (image `82128A20`).
- Without Forge globals: `R = radiusBase`, `Θ = 0.785398` rad (π/4, image
  `821293B0`).

### 3.2 Best pair for one candidate (`sub_82582C80`)

Weight w = globals +0x40 (0.75 on Ravine); without globals w = 0.0 (image
`821289E0`). ε = 0.0001 (image `82128A54`).

For each held marker h (outer loop, marker order), and each candidate marker
c (inner loop, marker order):

1. Before the inner loop: `a = |h.localPosition − ref|²` where
   h.localPosition is the held marker's **local (node-relative) position**
   (+44/+48/+52) and ref is the world reference point of section 2 step 3.
   (See open question Q1: the code compares a node-space point with a
   world-space point.)
2. Validate the pair (section 3.3). If invalid, skip.
3. If valid:
   - `a = a + ε` (cumulative: a grows by ε for every valid pair already seen
     for this h);
   - `b = pairDistance² + ε`;
   - `score = w / a + (1 − w) / b`.
4. If `score > best` (strict, best starts at −FLT_MAX), keep this pair.

Return the best score (−FLT_MAX if no valid pair) and the chosen pair (zeroed
records if none).

### 3.3 Pair validity (`sub_82582E38`)

1. **Actual orientation of the held object's marker node:**
   `qActual = normalise(quat(h.worldBasis)) ⊗ normalise(conj(quat(h.localBasis)))`.
2. **Target orientation:** run the alignment of section 4 for (h, c); take its
   output rotation `qTarget` (which equals the editor's target orientation —
   see 4.2).
3. `angle = 2 acos(|dot(qActual, qTarget)|)`.
4. `pairDistance² = |c.worldPosition − h.worldPosition|²` (order y, z, x).
5. **Valid iff `angle < Θ` (strict) and `pairDistance² < R²` (strict).**

Because qTarget does not depend on c and qActual depends only on h's node, the
angle test does **not** compare the two markers' orientations. It accepts only
while the held object's real node orientation is within Θ of the
editor's requested orientation (for example, while the physical piece has not
yet caught up with a large rotation step). Opposing or matching marker
directions are never tested.

---

## 4. Alignment (`sub_82582AD0`)

Inputs: player, held marker h, candidate marker c. Outputs: rotation
quaternion and position for the held object.

### 4.1 Computed but discarded "face-to-face" rotation

1. `qFace = normalise( normalise(quat(c.worldBasis)) ⊗ E2Q(π, 0, 0) )` — the
   candidate marker frame turned 180° about its up axis (π from image
   `834BD23C`, zeros from `821289E0`).
2. `qFace = normalise( qFace ⊗ normalise(conj(quat(h.localBasis))) )`.

This value is converted to Euler angles and then **entirely overwritten**
(step 4.2.3). It has no effect on any output. Record it only so an
implementation does not mistake it for live behaviour.

### 4.2 Live rotation: keep the editor's orientation

1. Take the editor's persistent target transform (editor +84, 52 bytes).
2. If rotation-snap mode (editor +224) ≠ 0 **and** the rotation-changed byte
   (editor +81) ≠ 0, replace its basis with the remembered quantized basis
   (editor +136..+168).
3. `qHeld = quat(basis)`; `out = normalise( E2Q( Q2E(qHeld, ε=0.0001) ) )`.

So the output rotation is the editor's (possibly quantized) orientation,
round-tripped through Euler angles. Magnets never rotate the held piece.
The only behavioural effect of the round trip is at the pitch singularity
(|pitch| ≈ 90°), where roll is folded into yaw.

### 4.3 Translation

`outPosition = c.worldPosition − rotate(out, h.localPosition)`.

The held marker's node-relative position is rotated by the output rotation and
subtracted from the candidate marker's world position. The held marker's
node frame, the object scale and any node offset from the object origin are
**not** applied (see open question Q2). The result is placed as the held
object's position.

---

## 5. Per-tick application, snap, stay-snapped and detach

### 5.1 Submission preparation (caller `8244A8D8` at `8244AD8C..8244AF10`, quantizer `sub_82451A38`)

Each tick, after movement and bounds work owned by other sections:

1. Copy the persistent target transform (editor +84) to a separate
   **submission** transform. Magnets and quantization act on the submission.
2. If rotation-snap mode m = editor +224 ≠ 0 and editor +81 ≠ 0:
   1. step = table[m] degrees × 0.017453292, table at image `833F195C` =
      [0, 90, 45, 30, 15, 5] (menu: off, 90, 45, 30, 15, 5).
   2. Quantize the submission's rotation (`sub_82451A38`):
      - Build a basis from forward and up (left = up × forward).
      - Extract (yaw, pitch, roll) from that basis (`sub_823C0208`):
        pitch = −asin(clamp(up.x, −1, 1)); with c = cos(pitch):
        if c > 0.0001 (double at `821289E0+1936`):
        roll = atan2(−up.y/c, up.z/c), yaw = atan2(−left.x/c, forward.x/c);
        else roll = 0, yaw = atan2(forward.y, left.y).
      - For each angle: q = angle × (1/step); add +0.5 if q ≥ 0 else −0.5;
        truncate toward zero; angle = integer × step (ties round away from
        zero).
      - Rebuild forward and up from the three angles (`sub_82265D10` via
        `sub_8232F9B8`), with sa/ca = sin/cos yaw, sb/cb pitch, sc/cc roll:
        forward = (ca·cb, sa·cc − ca·sb·sc, sa·sc + ca·sb·cc),
        up = (−sb, −cb·sc, cb·cc);
        then left = up × forward. Scale and position are untouched.
   3. Compare each of the nine quantized basis components with the remembered
      quantized basis (editor +136..+168). If any absolute difference is
      ≥ 0.0001 (image `82128A54`), copy the whole quantized submission back
      into the persistent target (editor +84) and store its basis as the new
      remembered basis. If all nine match, the persistent target keeps its
      unquantized basis while the submission is quantized.
3. Apply magnets to the submission (5.2).
4. Submit the submission to the physics controller with scalar 0.2 (outside
   this section).

### 5.2 Magnet step (`sub_8244EED8`)

1. If the magnet-enable byte (editor +82; default 0 = off, `sub_82449DD8`) is
   0: candidate = −1; go to step 5.
2. Run the candidate search (section 2). Candidate = its candidate datum
   (kept for state 1 **and** state 2).
3. If state ≠ 2: no alignment; go to step 5.
4. **Movement suppression** (`sub_82582178`): read the controlling unit's
   processed movement vector v (unit +1348/+1352/+1356) and compute |v|
   (y² first, then x and z by fused multiply-add). Threshold
   T = Forge globals +0x24 (0.5 on Ravine), or 0.5 (image `82128A08`) without
   globals. If `|v| > T` (strict), no alignment this tick.
   Otherwise align (section 4) and overwrite the **submission's** basis
   (quaternion → basis) and position. Scale is untouched.
5. **Visibility / candidate memory** (`sub_8244A118`): store the candidate
   datum at editor +4. For the local player only (`822ED938`), update marker
   display (`sub_825826B0`):
   - magnets enabled: if the candidate changed, hide the old candidate's
     markers and show the new candidate's (−1 means none);
   - magnets disabled: hide markers of the held object and of both old and
     new candidates.

### 5.3 State kept between ticks

The magnet code writes **only**:
- editor +4: the last candidate datum (used only for marker-display
  transitions; it does not influence the next tick's selection);
- the per-tick submission transform.

It does **not** write the persistent target (editor +84), the reference
offset, the scale/decay fields or any timer. There is **no explicit
hysteresis, latch, timer or engage/release distance pair**: every tick
re-runs selection from scratch with the same thresholds.

### 5.4 Resulting snap, stay-snapped and pull-away behaviour

These follow from the rules above, not from extra code:

- **Snap engages** on a tick when magnets are on, some held/candidate marker
  pair has world separation < R (= sensitivity factor × held bounding
  radius), the held piece's real orientation is within Θ (45°) of the
  requested orientation, and the player's processed movement magnitude is
  ≤ 0.5. The piece is then translated so the held marker lands on the
  candidate marker, orientation unchanged.
- **The unsnapped target is untouched.** The player keeps steering the
  persistent target (editor +84); the snap only modifies that tick's
  submission copy.
- **Stay-snapped.** Held marker world positions come from the held object's
  live nodes, i.e. where the physical piece actually is. After a snap the
  physics body is driven to the snapped pose, so on the following ticks the
  chosen pair's separation is near zero and the snap revalidates, even if
  the persistent target has drifted (small input with |v| ≤ 0.5 still moves
  the target while the piece stays snapped).
- **Pull-away (detach).** When |v| > 0.5, alignment is skipped and the
  submission is the unsnapped target, so the physics body heads back to the
  target. The candidate is still reported (markers stay visible). When
  movement drops back to ≤ 0.5, the snap re-engages only if a valid pair
  exists from the piece's new real position. A snap is also lost when the
  pair separation reaches R, when the orientation gap reaches Θ, when the
  candidate leaves the query radius, or when magnets are disabled.

---

## 6. Tuning constants

| Value | Meaning | Source |
| --- | --- | --- |
| 0.5 | movement magnitude above which alignment is suppressed | Forge globals +0x24 (Ravine 0.5); fallback image `82128A08` = 0.5 |
| 0.10, 0.25, 0.50, 0.75, 1.00 | snap radius factor for sensitivity 0..4 | Forge globals +0x28, +0x2C, +0x30, +0x34, +0x38 (Ravine) |
| none (factor 1) | sensitivity > 4, or no globals | `sub_825824E0` |
| 2 | default sensitivity index (→ factor 0.5) | literal in `sub_82449DD8` (editor +268) |
| 0 (off) | default magnet enable | literal in `sub_82449DD8` (editor +82) |
| 45° | maximum orientation gap Θ | Forge globals +0x3C (Ravine 45.0); fallback image `821293B0` = 0.785398 rad |
| 0.017453292 | degrees to radians | image `82128A20` |
| 0.75 | score weight w on the reference-point term | Forge globals +0x40 (Ravine); fallback image `821289E0` = 0.0 |
| 0.0001 | score epsilon; basis-compare epsilon; quaternion-normalise threshold; Euler gimbal tolerance | image `82128A54` (float) and `821289E0+1936` (double, Euler-from-basis) |
| −FLT_MAX | initial best score | image `834BD2A4` |
| +FLT_MAX | initial best centre distance² (state 1, unbounded) | image `82128A34` |
| π | flip angle in the discarded rotation | image `834BD23C` |
| π/2 | pitch at gimbal in quaternion→Euler | image `82128AC8` |
| 32 | markers per object | literal capacity in `sub_82582610` |
| 64 | objects per spatial query | literal in `sub_82582250` |
| 0x3ADF | object-type mask for the query | literal in `sub_82582250` |
| 1 | query category | literal in `sub_82582250` |
| 0x193 | magnet marker group name id | Forge globals +0x1C (via `sub_82582A68`) |
| [0, 90, 45, 30, 15, 5] | rotation-snap steps (degrees) by mode 0..5 | image table `833F195C` |
| (0,0,0) | reference point with no held object; reset grab offset | image pointers `833F7E98`, `833F7EA0` → `82125110` |
| 0.2 | physics-controller scalar for the submission | `8244A8D8`, outside this section's routines |

Forge globals are resolved at run time through the pointer at `8405D340`
(fields +492/+504, resolver `sub_82340E60`); the table values above are the
retail Ravine block (88 bytes, SHA-256
`0aa93e946f5ba028c26b21e4d892dd6996512c302e5eea87221e39756c9777a7`). Other maps
were not checked.

---

## 7. Corrections to earlier notes

- `FULL-RE-FINDINGS.md` (magnet pair diagnostics section) says state 1 uses an
  "original squared-distance bound 4". The bound is read from `82128A34`,
  which is +FLT_MAX: state 1 has no distance limit.
- `FULL-RE-FINDINGS.md` (placement and magnet call paths) says the bridge's
  `Evaluate` omits `sub_82582178`. That is out of date: the current
  `C:\Programming\GitHub\OpenH3M\tools\h4-forge\forge_bridge.cpp` `Evaluate`
  calls it before alignment.
- The notes describe the score as "weighted reciprocal squared distances to
  the editor point and between markers". The editor-point term actually uses
  the held marker's node-relative position, not its world position.
- The notes describe the angle test as comparing the held orientation with the
  alignment quaternion. That is correct, but it leaves out that the result
  does not depend on the candidate marker at all (section 3.3).
- The notes call config +0x24 "throttle sensitivity"; its only consumer here
  is the movement-suppression threshold.
- The notes describe `sub_82582AD0`'s first rotation as using "a fixed
  rotation". That rotation is a 180° yaw (Euler (π, 0, 0)), and the result is
  discarded.

---


## 8. Open questions — round 2 status

Tags: **RESOLVED / UNRESOLVED**, and **NEEDED / NOT-NEEDED** for a fresh
implementation running inside Halo 3 (NOT-NEEDED = Halo 4-internal detail with
no observable effect on magnet behaviour, or replaced by Halo 3 data or our own
design). Functions outside `forge_original.cpp` were read in the recompiled
sources under
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\generated\`
(file named per item); constants from
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\h4-image.bin`.
(`C:\Programming\GitHub\OpenH3M\tools\h4-forge\inspect_ppc.py` expects the
image under `C:\Programming\GitHub\OpenH3M\work\h4-forge-research\`, which does
not exist, so it was not used; the generated sources contain the same
instructions as comments.)

### Q1. Node-space marker position against a world reference point in scoring — RESOLVED, NEEDED

- The reference point is world-space. `sub_824499A8` adds the editor offset to
  the held object's point from `sub_8293A3B0`. That routine calls
  `sub_82260B58` (`halo4_recomp.54.cpp`), which returns the object's physics
  body point (via the physics model, `8228FD18`) when the object has one, and
  otherwise the object's world-space centre at object +64/+68/+72. It then
  optionally passes the point through `822CFA08` (an extra transform when
  object +304 is valid and bit 0 of object +308 is set). Every path yields a
  world-space point.
- The editor offset is a continuity term, not a grab offset. On grab/release
  `sub_82449ED8` and `sub_82449DD8` set offset = (0,0,0), scale = 0, rate = 0.
  When a physics-state change moves the physics point (`sub_8244A2A0`), the
  code sets offset = oldOffset × oldScale − (newPoint − oldPoint), scale = 1,
  rate = 0. The reference point therefore stays where it was and then decays
  onto the new physics point once a rate is seeded (5 × tick interval, image
  `821289E0+48` = 5.0, when rotation input is applied; `8244A7D0`, per notes)
  and scale = max(scale − rate, 0) each tick. In steady state the reference
  point is the held object's physics point.
- Scoring (`sub_82582C80`) compares this world point with the held marker's
  node-relative position (runtime marker +44..+52). This is confirmed as the
  literal behaviour. Whether it was intended cannot be determined from code.
- Observable effect: with w = 0.75 the reference term is w / (|p_local −
  ref|² + ε). Far from the world origin it is tiny and nearly equal for every
  held marker. The pair-distance term then decides the ranking (smallest
  marker separation wins). Within a few units of the world origin the
  reference term can change which held marker is chosen. A parity
  implementation must reproduce the literal comparison. Any simplification
  differs from H4 only near the world origin.

### Q2. Node offset and scale ignored in the translation — UNRESOLVED (H4 data), NOT-NEEDED

- Confirmed from `sub_82582AD0`: the translation uses only the held marker's
  node-relative position, rotated by the output orientation. The node's own
  transform and the object scale are not applied.
- Supporting evidence that H4 treats node 0 as the object's frame:
  - all 728 retail magnet records use node 0;
  - the gatherer's built-in origin marker for marker names 0 and 555 is
    "identity local transform, world = node 0" (`sub_8226BCA0`,
    `halo4_recomp.187.cpp`);
  - the pair-validity orientation test (3.3) compares the node 0 orientation
    with the editor's object orientation, which only makes sense when they
    coincide.
- Not determinable from code: whether each Forge model's node 0 rest pose is
  the identity, and whether held objects ever have scale ≠ 1. Settling this
  needs the render-model node data of every Forge piece in the map cache, not
  code.
- NOT-NEEDED for Halo 3: the H3 implementation supplies markers expressed in
  the object's own frame (node offset folded in, scale 1). With that data the
  H4 formula is exact and no node or scale handling is needed.

### Q3. Meaning of the 0.5 movement threshold — RESOLVED, NEEDED

Traced producer chain:

1. `82368CE0` (Forge manipulation input, in `forge_original.cpp`) reads the
   player's per-tick input record. Movement stick is at +28/+32, look stick
   at +44/+48, the manipulation trigger at +56.
   - When the player holds or aims at an object and the trigger is above 0.1
     (image `821289E0+12`), the sticks drive rotation/distance instead, and
     the movement pair is zeroed.
   - Otherwise the movement pair is left as is.
2. `823619F8` copies the movement pair into the unit-control packet as X/Y,
   with Z = 0 (notes).
3. `82361880` (`halo4_recomp.56.cpp`), on the ordinary unattached path
   (`82221B08` returns 16), handles vertical input:
   - input halfword +52 bit 0 adds +1 to Z;
   - bit 1 subtracts 1 (both pressed cancel).
   It zeroes X and Y when player-state float +2096 (read at player +1915
   rounded down, +184) is 0. An equipment-tag branch can skip this
   processing.
4. `822562A8` copies the packet vector unchanged into unit +1348/+1352/+1356
   for a player-owned unit (unit +1180 ≠ −1; notes).
5. `sub_82582178` compares the vector's length with 0.5. The Forge globals
   field holding 0.5 is named "throttle sensitivity" in the Gen4 tag schema;
   "throttle" is the engine's name for the movement stick.

Meaning: the vector is (movement stick X, movement stick Y, vertical button
value), in stick units with a full deflection of 1. Magnets are suppressed
when the movement stick is pushed past half deflection (combined with any
vertical value), or whenever an up/down button is held (|Z| = 1 > 0.5). It is
not a speed. Movement made while the manipulation trigger is held (rotating
the piece) is zeroed first, so rotating with the trigger never suppresses
magnets. Dead-zone and response-curve processing of the raw stick before
input +28/+32 was not traced (upstream input code).

### Q4. Type mask 0x3ADF, query category 1 and the spatial-query inclusion rule — UNRESOLVED, NOT-NEEDED

- `sub_821F2050` (`halo4_recomp.140.cpp`) packs category and mask into a
  filter, then calls `8256B440`.
- `8256B440` widens an axis-aligned box of ±radius around the query centre
  and walks spatial clusters through `8256B1B0`.
- The per-object inclusion test in `8256B1B0` (sphere overlap or centre
  inside) and the object-type names were not traced. The type names are only
  partly known from notes (bit 9 = dispenser).
- NOT-NEEDED: Halo 3 supplies its own nearby-object query. Our candidate set
  is the Forge-placed objects that carry magnet markers.

### Q5. Meaning of object +24, +64..+72 and +76 — RESOLVED (meaning from consumers), NEEDED

- +64..+72 is a world-space object centre. `sub_82260B58` returns it as the
  object's point when there is no physics body.
- +76 is that object's bounding radius. It is used as:
  - the snap-radius base (`sub_825824E0`);
  - the query-radius base (`sub_82582250`);
  - the grab-distance radius (`82452738`, per notes).
- +24 is the object's location record, which the spatial query uses to start
  its cluster walk.
- The writer of +64/+76 was not identified. A search for routines writing all
  four fields found only unrelated matrix copies. The consumers fully fix the
  meaning, though.
- NEEDED: map these to the Halo 3 object's bounding-sphere centre and radius,
  and to the H3 location for the H3 query.

### Q6. Marker gatherer `sub_8226BCA0` — RESOLVED, NOT-NEEDED

Read in `halo4_recomp.187.cpp`:

- Resolves the object's render model.
- Obtains the object's current region permutations (`8293AD18`).
- Takes live node matrices from the object (object +446 offset, +444 byte
  count / 52).
- Requires both the permutation-region count and the node count to match the
  render model, else returns no markers.
- Finds the marker group by name (`8226BF48`).
- Calls `sub_8259E9A8` with mirrored = object +16 bit 0x100.
- If no markers result, only marker names 0 and 555 get a synthetic origin
  marker. The magnet name 0x193 yields zero markers.

NOT-NEEDED: Halo 3 marker data comes from our own pack.

### Q7. A child of the held piece could present the held root's markers — UNRESOLVED, NOT-NEEDED

- The magnet search excludes only the held datum itself. Markers come from
  the candidate's root (`sub_82582610`).
- Whether the spatial query returns parented children depends on
  `8256B1B0`, which was not traced (see Q4).
- The selection ray resolves aimed objects to their root (`8244D0E0`), which
  suggests H4 Forge holds root objects.
- NOT-NEEDED: in Halo 3 our candidate list contains only Forge-placed variant
  objects, which are unparented. The case cannot arise.

### Q8. Mirrored objects — RESOLVED (flag identified), NOT-NEEDED

- The mirrored flag is object +16 bit 0x100 (`sub_8226BCA0`).
- Whether any Forge piece can carry it is not determinable from code.
- NOT-NEEDED: Halo 3 Forge placement has no mirroring.

### Q9. What editor +24 holds — RESOLVED, NOT-NEEDED

- Editor +24 is the object currently under the selection ray (the aimed
  object): `8244D0E0` (`halo4_recomp.196.cpp`, at `8244D3E4`) stores the
  root-resolved ray hit there after `sub_8244C740`. It is reset to −1 on
  release (`sub_82449ED8`) and at initialisation (`sub_82449DD8`).
- `sub_825824E0` uses it as the radius base only when nothing is held.
  Magnet selection always runs with a held object, so this fallback never
  affects magnets.

### Q10. Offset decay and grab offset — RESOLVED (see Q1), NEEDED

- Grab/release: offset = (0,0,0), scale = 0, rate = 0 (`sub_82449ED8`,
  `sub_82449DD8`).
- A physics-state change sets the continuity offset, scale = 1, rate = 0
  (`sub_8244A2A0`).
- The rate is seeded to 5 × tick interval (when rotation input is applied;
  `8244A7D0`, per notes; constant `821289E0+48` = 5.0), and scale decays by
  rate per tick down to 0.
- NEEDED in the sense that the reference point feeds the query radius and the
  score. An H3 implementation without physics-state transitions can use
  reference = held physics point (scale stays 0). This matches H4 whenever no
  physics-state change has occurred since the grab.

### Summary table

| Q | Topic | Status | For H3 |
| --- | --- | --- | --- |
| Q1 | node-space marker vs world reference in score | RESOLVED | NEEDED |
| Q2 | node offset / scale in translation | UNRESOLVED (needs H4 model data) | NOT-NEEDED (object-frame markers) |
| Q3 | meaning of 0.5 movement threshold | RESOLVED | NEEDED |
| Q4 | query mask / category / inclusion rule | UNRESOLVED | NOT-NEEDED |
| Q5 | object +24 / +64..72 / +76 meaning | RESOLVED (producer not found) | NEEDED |
| Q6 | marker gatherer details | RESOLVED | NOT-NEEDED |
| Q7 | child objects presenting root markers | UNRESOLVED | NOT-NEEDED |
| Q8 | mirrored objects | RESOLVED (flag) | NOT-NEEDED |
| Q9 | editor +24 | RESOLVED | NOT-NEEDED |
| Q10 | offset decay / grab offset | RESOLVED | NEEDED |

---

## Round 2 changes

- Q1: traced `sub_8293A3B0` → `sub_82260B58`. The reference point is the
  world-space physics point (or the object centre) plus a continuity offset.
  The node-space versus world mismatch in scoring is confirmed literal
  behaviour, and its observable effect is quantified.
- Q2: confirmed the formula. Added evidence that node 0 is treated as the
  object frame. Marked NOT-NEEDED given object-frame marker data.
- Q3: traced the vector to the movement stick (input +28/+32) plus up/down
  buttons (±1). 0.5 means half stick deflection or any vertical button, and
  trigger-held manipulation zeroes movement first.
- Q5, Q6, Q8, Q9, Q10: resolved from `sub_82260B58`, `sub_8226BCA0`,
  `8244D0E0` (editor +24 writer), `sub_8244A2A0` (offset continuity) and
  `sub_82449ED8`.
- Correction to section 2 step 3: editor +56..+64 is a physics-transition
  continuity offset, not a grab-time offset. It is zero at grab.
- Q4 and Q7 remain unresolved (per-object test in `8256B1B0` not traced) and
  are tagged NOT-NEEDED.
