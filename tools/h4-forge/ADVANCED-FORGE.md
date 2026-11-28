# Advanced Forge — clean-room specification

User direction, 2026-11-26: Advanced Forge must be a fresh implementation learned from the code, not Halo 4's
code run inside Spartan. The current version executes 157 recompiled Halo 4 functions fed by a copy of Halo 4's
program image (`h4-image.bin`), uses magnet anchors taken from Halo 4 object data, and draws markers with
translated Halo 4 shaders. This document replaces all of that with a written description of the behaviour.

## Method and boundary
- Written from static reading of the recompiled Halo 4 functions (and, where needed, disassembly of the image);
  nothing was run to discover behaviour. Two reading rounds: first pass, then each section's open questions.
- Sections describe rules, maths, state and tuning values in our own words. Function addresses are citations
  for review only.
- The implementation is written from this document alone: no Halo 4 program image, no recompiled Halo 4 code,
  no Halo 4 object data, no Halo 4 shaders or textures. Tuning numbers are stated here as our chosen values.
- Testing happens once, at the end, against this document.

## Sections
1. `01-magnets.md` — markers, candidate search, scoring, alignment, snap / stay / pull-away.
2. `02-held-update.md` — per-tick held movement, soft-ceiling push-back, body drive, attachment fix.
3. `03-grab-select-distance.md` — aim selection, grab and re-grab, spawn placement, hold distance (push/pull).
4. `04-rotation-coordinates-physics.md` — input shaping, rotation and rotation snap, coordinate panel, physics
   modes, marker visibility.
5. `05-camera-and-data.md` — monitor camera while holding; inventory of the Halo 4 data being replaced and the
   pieces that need freshly authored magnets.
6. `06-magnet-placement-rules.md` — where magnets go on each kind of piece (Halo 4's design conventions applied to
   our pieces' own geometry); open fine-detail choices are settled the way Halo 4's designers did.
7. `07-marker-look.md` — how the magnet markers look and animate, with a from-scratch drawing recipe.

## Behaviour in brief
- **Magnets** only translate the held piece so its magnet lands on the target magnet; they never rotate it.
  Search radius = piece size + grab-point offset; pair accepted when magnets are within the snap radius
  (0.1/0.25/0.5/0.75/1 x piece radius by sensitivity; default 0.5) and the piece's actual orientation is within
  45 degrees of the requested one. Score = 0.75/(grab-point term) + 0.25/(pair distance term). Re-evaluated every
  tick; no timers. Movement input above 0.5 (or up/down held) switches snapping off, which is how pull-away works.
  Magnets start off.
- **Held movement:** target moved by input (10% in precision mode); kept inside map bounds; a piece fully outside
  the level may only move back toward it; the body is driven to reach the target in 0.2 s (monitor 0.05 s),
  re-planned every tick; target may lead the piece by 0.5 units per tick. The only "contact" is the map's soft
  ceilings / kill-volume push-back (Halo 3 has its own).
- **Grab:** aim ray from the monitor eye, length max(hold distance, 7.5); hold distance clamped to
  [max(1.25 r, r + 0.4), min(5 x that, 22)] (large pieces: the maximum wins); push/pull 0.3 x stick per tick,
  only with the trigger past 0.1; release resets distance to 7.5. New pieces appear at the aim point, pulled
  toward the player by their radius; 4-try free-space search (Halo 3's own).
- **Rotation:** about world down (yaw), the horizontal view-side axis (pitch) and the view axis (roll), not the
  piece's axes; speed rises with stick deflection squared to about 286 degrees/s; each stick keeps only its
  dominant axis. Snap steps off/90/45/30/15/5; snapping applies only after the first turn since grab, jumping at the
  half-step. Snap starts off.
- **Coordinate panel:** X/Y/Z -1000..1000 step 0.1; Pitch/Yaw/Roll -180..179 in whole degrees (step follows the
  snap setting); only changed fields are applied; result kept inside map bounds. Preview/cancel are our design.
- **Physics modes:** Phased moves on a keyframed path while held, then freezes when dropped without the
  settle-and-validate step; Fixed freezes when dropped; Normal returns to free physics. Normal/Fixed are checked
  once settled (Halo 4 deletes a Normal piece that settles somewhere invalid).
- **Camera:** camera point = held centre + grab offset, lifted along view-up by a pitch curve (+1 radius looking
  up, about 0 level, -1 looking down), pulled back by the hold distance; monitor moves toward it at most 2 units per
  tick. Obstruction rays only run when the focus point is outside the world.

## Governing rule: exactly like Halo 4, in every respect
User, 2026-11-26: "It should work exactly like Halo 4 in all respects" — magnetism, placement camera,
translation and rotation, physics settings, grabbing and placement, controls and menus, marker look. No
generalised rules, no "Halo 3's own" substitutes for Halo 4 behaviour, and no "our own design" fill-ins. Where
Halo 3 must supply something (its map data, collision queries, object storage), the behaviour built on it must be
Halo 4's exactly. The only permitted difference is the saved format (next section). Anything not yet determined
from Halo 4's code is listed as unresolved, never filled with a choice.

## Hard rule: editing capability only, saved output stays Halo 3
User, 2026-11-26: "The point is Halo 4 capabilities, but once the variants are saved they're standard Halo 3
variants." Advanced Forge changes how pieces are moved, rotated, snapped and placed while editing. What gets
saved is an ordinary Halo 3 map variant: positions, orientations, physics settings and other fields stored
exactly as stock Halo 3 stores them, with no extra data, companion files or Halo 4-only fields. A layout made
with Advanced Forge must load, play and edit in stock Halo 3 Forge (PC or Xbox 360). Anything Halo 4 keeps per
piece that Halo 3 cannot store (e.g. magnet state, grab offsets) is transient and discarded on save.

## Scope: maps now and later; magnets live in code
User, 2026-11-26: today this covers Forge Gulch and Force Cove; it is meant to extend later to other maps,
including Void and Sandbox. Stock Halo 3 Sandbox items have never had magnets, so they will need anchors authored
from scratch — a later item. "We keep magnets in code": magnet positions are defined in the program's source code
(per piece), not loaded from a data file. The placement rules (`06`) are how those code tables are authored.
"We're not exponentially expanding this. I control what maps will have the feature": Advanced Forge is enabled
only for maps the user names (now Forge Gulch and Force Cove). Nothing turns it on for other maps or pieces
automatically; adding a map is a separate user decision, with its magnet tables authored then.
Void uses the same Gulch/Cove pieces, so enabling it needs no new magnet tables; Sandbox's stock items would.

Magnets apply to scenery only (user, 2026-11-26): only scenery pieces carry magnets, and magnet search, snapping
and markers run only when the held object is scenery. Weapons, vehicles, equipment and other objects are moved
and placed without magnets.

## User decisions, 2026-11-26
1. Push/pull: **Halo 4 way** (stick forward pulls the piece toward the player).
2. Magnet placement: **Halo 4 way** — derive the placement rules Halo 4's designers used (where magnets sit
   relative to faces, edges and corners per kind of piece) and apply them to our pieces' own geometry; no Halo 4
   anchor data is copied (`06-magnet-placement-rules.md`).
3. Settled-invalid deletion: **Halo 4's rule** (a dropped Normal piece that settles somewhere invalid is deleted).
4. Marker look: **Halo 4 way** — describe the look (colour, shape, screen size, fade, animation) and draw it with
   our own rendering code; no Halo 4 shaders or textures (`07-marker-look.md`).

## Decisions that were put to the user
1. **Push/pull direction:** Halo 4 pulls the piece toward you with stick forward; Halo 3 pushes it away.
2. **Magnet placement rule** for the 89 pieces (129 entries) that need fresh anchors: a rule to apply to each
   piece's own geometry (for example: centre of every flat outer face, plus face corners/edge midpoints for
   pieces meant to tile), with per-piece exceptions. Radio Antennae, Weapon Holder, Glass Sail and Sniper Nest
   stay magnet-free (user 2026-11-12).
3. **Marker look:** our own simple marker (Halo 4's glow shaders and textures are being dropped).
4. **Settled-invalid deletion:** keep Halo 4's rule that a Normal piece settling somewhere invalid is deleted, or
   leave Halo 3's behaviour.

## Remaining unresolved items that matter
- Whether the aim ray can hit the held piece (data-dependent in Halo 4): follow Halo 3, which ignores it.
- Physical controller buttons for each input: taken from Halo 3's own Forge controls.
- Tick rate: per-tick values are applied per Halo 3 tick (30 Hz).
All other open questions are resolved or marked not needed for a Halo 3 implementation in their sections.


---

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


---

# Forge magnets specification, section 2: held-object movement, contacts and body drive

Clean-room behavioural specification derived by static reading of the Halo 4
functions recompiled into
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\forge_original.cpp`.
Two routing helpers that live outside that file were read in
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\controller_original.cpp`
(`sub_82452930`) and
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\generated\halo4_recomp.182.cpp`
(`sub_82451BA8`, control flow only). The caller order was checked in the
generated body of `sub_8244D0E0`. Numeric constants were read from the decoded
executable image
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\h4-image.bin`;
contact coefficients come from the retail Ravine globals extract
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\contact-settings.bin`.
Nothing was built, run or tested.

Function addresses are given as provenance for every rule. Descriptive names
are this document's own. Conventions (units, Z-up axes, 52-byte transform
layout, composition `A ∘ B`, quaternion layout) are those of section 1,
`C:\Programming\GitHub\OpenH3M\tools\h4-forge\spec\01-magnets.md` §0.

Shorthand used below:

- **C** = the constant pool at `821289E0`. `C+n` is the float at byte offset n
  (for example `C+88` = `82128A38` = 4.0).
- **dt** = the game tick interval (time globals +8). **tick** = the game tick
  counter (time globals +12). **rate** = ticks per second (time globals +4,
  signed 16-bit).
- **editor+n** = the per-player Forge editor record (336 bytes).
- **unit** = the player's controlled unit (the Forge monitor), reached through
  the player record +36. Unit fields used: desired facing +1212..1220,
  processed movement input +1348..1356, action flags +1200 (64-bit), boost
  fraction +2168, flags +256 (64-bit). Unit definition field +1428.
- **object flags** = 64-bit word at object +256. Bit 20 (`0x100000`) is
  "contact active"; bit 30 (`0x40000000`) is "keyframe-driven this tick".
- `normalize(v)`: if `|v| < 1e-4` (`C+116`) the vector is left unchanged and the
  reported length is 0; otherwise v is divided by its length (`sub_8228ACE8`).
  A second variant replaces a short vector with a supplied fallback
  (`sub_8229D390`).
- `limit(v, m)`: if `|v|² > m²`, scale v to length m; report whether it changed
  (`sub_8221CA38`).
- `clampBox(p, b)` with b = (minX, maxX, minY, maxY, minZ, maxZ): per axis, if
  `min > p` use min, else if `max < p` use max, else keep p (`sub_82282580`).
  The box is the game variant's map-bounds record at variant +696
  (`sub_823C2020` returns the variant).

---

## 1. Per-tick order of operations

### 1.1 Where the held stage runs

The Forge player tick `sub_8244D0E0` does, for a player who is holding an
object (non-alternate path, selected by global byte `8407EFFA` = 0 in the
image):

1. rotation / input processing (`sub_8244A7D0`, then editor+36 reduced by
   editor+40 with a floor of 0, then `sub_82452738`) — other sections;
2. **held-object update** `sub_8244A8D8` (§1.2);
3. **monitor follow** `sub_8244AF48` (§1.3).

When the byte at `8407EFFA` is nonzero `sub_82451FC0` runs instead (not
covered here). The H3 port inserts this whole stage at the native tick's held
block (`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\native_forge_tick.inl`,
before native `sub_8227F578`; a false result falls through to the native
block). Under the round 3 requirement, the native Halo 3 held behaviour is
not a substitute: for a held piece this stage's behaviour is the whole held
behaviour.

Because follow runs after the held update, every value follow writes
(editor+32 leash distance, editor+80 outside-world flag, editor+228.. smoothing
state, editor+276 pitch ratchet) is consumed by the held update one tick
later.

### 1.2 Held-object update (`sub_8244A8D8`)

Inputs: player index and editor record. H = held object (editor+0).

1. **Velocity sample.** Read H's linear velocity **v** (`sub_82260CF0`).
2. **Leash correction.** If `|v| > 0` (strictly; `C+0`), compute the leash
   correction **c** of §2.2 (`sub_8244B338`); otherwise c = 0.
3. **Physics gate.** If H has no physics instance (object +240 = −1), or the
   instance record is missing, or it has no bodies (instance +52 ≤ 0): return
   immediately. Nothing is written; no target is submitted.
4. **Body-pose cache.** Let `outside = objectFullyOutsideWorld(H)`
   (`sub_82451BA8`, §3.5). If not outside and `tick mod 5 == 0`, store body 0's
   current world transform into editor+172..223 (`sub_822AD348`).
5. **Movement delta.** Compute the input displacement **Δ** and the requested
   velocity **u** (§2.1).
6. Read H's reference point **R** = its world origin (`sub_822410D0`).
7. **Integrate.** target position T (editor+124..132) += c + Δ.
8. **First bounds clamp.** T = clampBox(T, variant bounds).
9. **Offset.** d = T − R.
10. **Out-of-world restriction** (§2.3). Applies if `outside`, or if global
    byte `8407F008` is nonzero **and** editor+80 is nonzero.
11. **Step limit choice.** If `v · u > 1e-4` then `L = 3 × boost` (`C+16` = 3,
    boost from §2.1) else `L = 0.5` (`C+40`).
12. **Contact response.** Run the contact response for H (§3) with H's cached
    contact point editor+68..76. If it reports a contact with normal **n**, and
    `|d| > 1e-4`, and `n·d < 0`: remove the into-surface part,
    `d = d − n (n·d)`, and set `L = 0.5`.
13. **Displacement cap.** d = limit(d, L).
14. T = R + d; **second bounds clamp** T = clampBox(T, variant bounds). T is
    stored back into editor+124..132.
15. **Submission copy.** Copy the full persistent target transform
    (editor+84..135) into a temporary *submission* transform S.
16. **Rotation quantization** (only if rotation-step mode editor+224 ≠ 0 and
    editor byte +81 ≠ 0): quantize S's basis to the step angle (table
    `833F195C` = [0, 90, 45, 30, 15, 5] degrees × `C+64` = 0.0174532924 rad/deg,
    applied by `sub_82451A38`). Compare S's nine basis floats with the
    remembered quantized basis editor+136..171. If any differs by ≥ 1e-4
    (`C+116`), copy S over the whole persistent target (editor+84..135) and copy
    S's basis into editor+136..171. If all are within 1e-4 leave the
    persistent target untouched (it keeps accumulating unquantized rotation).
17. **Magnet hand-off.** Pass S to the magnet stage (`sub_8244EED8`, section 1).
    It may rewrite S (snap) and editor+4 (magnet target). Nothing in this
    function copies the magnet-adjusted S back into the persistent target.
18. **Physics submission.** Submit S for H with drive time `T_drive = 0.2`
    (`C+256` = `82128AE0`) through the body router (§4.1).

### 1.3 Monitor follow (`sub_8244AF48`)

M = the player's controlled unit (the monitor).

1. **Camera solve.** Ask the held-camera builder (mode 1, with prediction;
   `sub_824BEA10`, camera section) for a camera point **Pc**, a unit view
   direction **f**, and a distance **D**. The focal point is `F = Pc + f·D`.
2. **Focal containment.** `editor+80 = pointOutsideWorld(F)` (`sub_82415970`
   with mask `0000100900000000`, no exclusions).
3. **Obstruction pull-in** (only if editor+80 is true): write exclusions
   editor+256 = H and editor+260 = M, copy six configuration words from
   `8407F34C` (runtime camera globals; zero in the image) and run the obstruction
   smoother over its state editor+228..263 with F, Pc and dt (`sub_824F5CF0`,
   camera section). With `k = editor+228` after the update:
   `F = F − f·(k·D)` and `D = D − k·D`.
4. Read M's reference point **U** (`sub_822410D0`).
5. **Step cap.** `w = Pc − U`; if `|w|² > 4` (`C+88`) set `|w| = 2` (`C+20`).
6. **Contact projection.** If M's object flag bit 20 is set and `|w| > 1e-4`,
   with the player's stored contact normal **m** (player record +152..160,
   written by M's own contact response elsewhere): if `m·w < 0`,
   `w = w − m (m·w)`.
7. New monitor position `P = U + w`.
8. **Facing.** `g = normalize(F − P)`; if `|F − P| < 1e-4` use `normalize(f)`
   instead.
9. Build a transform with scale 1, position P, forward g and world up
   (0,0,1) (global `833F7EAC` → `82125188`; `sub_8221B258` sets scale 1 and
   position, then the frame builder `sub_8221B030` makes the basis):
   1. forward = normalize(g); if shorter than 1e-4, forward = (1,0,0)
      (`82125170`);
   2. left = normalize(up × forward);
   3. if that was shorter than 1e-4 (forward parallel to up): if forward
      equals (0,0,1) or (0,0,−1) within 1e-4 per component (globals
      `833F7EAC` → `82125188`, `833F7EB8` → `821251BC`), use the helper axis
      (1,0,0); otherwise use (0,0,1); left = normalize(helper × forward). For a
      monitor looking straight up this gives left = (0,−1,0), straight down
      left = (0,1,0);
   4. up = normalize(forward × left).
10. Submit it for M with drive time `T_drive = 0.05` (`C+276` = `82128AF4`)
    through the body router (§4.1).
11. **Local view.** If the player maps to a local view slot 0..3, derive an up
    vector from g (`sub_822C8040`) and update that view's angles from (g, up)
    (`sub_823FC348`).
12. **Leash distance.** `editor+32 = min(|P − F|, D)`.
13. **Pitch ratchet** on `r = editor+276` with `z = g.z`: if `r > 0` and
    `0 < z < r`, set `r = z`; else if `r < 0` and `r < z < 0`, set `r = z`.
    Otherwise unchanged. The value therefore only moves toward zero and never
    changes sign; 0 stays 0.

---

## 2. Target pose maths

### 2.1 Input displacement (`sub_8244A8D8`)

Let (hx, hy, hz) = unit desired facing (+1212..1220; not the current view
+1260) and (mf, ml, mu) = processed movement input (+1348..1356: forward,
left, up).

- Direction: `a = (mf·hx − ml·hy, mf·hy + ml·hx, mu)`. The facing's x/y are
  used as given, not renormalized; hz is not used.
- Precision factor: `p = 0.1` (`C+12`) if unit action flag bit 0 (+1200) is set,
  else `1` (`C+4`).
- Boost: `boost = 1 + (def1428 − 1) × fraction2168` (`C+4` = 1).
- Speed: `s = p × boost × 4` (`C+88` = 4 world units/second).
- Requested velocity `u = s·a`; displacement `Δ = dt·u`.

The vertical input moves the target vertically in world Z; nothing in this
function changes the target distance from the camera directly (distance
input is handled in another stage).

### 2.2 Leash correction (`sub_8244B338`)

Only when H is moving (§1.2 step 2).

1. A = the mode-0 held-camera anchor (`sub_824BEAD0` → `sub_824BE840`): held
   physics point plus editor+36 × editor+56..64 plus the view-relative offset
   (camera section). No prediction.
2. U = monitor reference point (`sub_822410D0`).
3. `e = U − A`, `r = |e|`, `excess = r − editor+32`.
4. If `excess > 1` (strict; `C+4`): `c = e × (excess / r)`; else `c = 0`.

Effect: when the monitor is more than (leash + 1) from where the camera wants
it relative to the moving object, the target is shifted toward the monitor by
the full excess (bringing the separation back to the leash distance).

### 2.3 Out-of-world restriction (`sub_8244A8D8` steps 10)

Let K = cached body-0 position (editor+212..220, the translation of the cache
filled in §1.2 step 4).

1. `â = d` normalized (left as-is if shorter than 1e-4).
2. `b̂ = (K − R)` normalized (same rule).
3. `k = max(â·b̂, 0)`.
4. `d = d × k`.

So, while the object is entirely outside the level (or the focal-point flag
and the global switch are both on), offsets are scaled down by how well they
point back toward the last in-world body position; offsets pointing away are
cancelled entirely.

### 2.4 Orientation

`sub_8244A8D8` never changes the target basis except through quantization
(§1.2 step 16). Rotation input is applied earlier by other stages. The scale
field of the target is carried along but is ignored by the body drive
(§4.2: `sub_82301320` does not read it).

### 2.5 Summary of limits

| Quantity | Rule | Value |
|---|---|---|
| target offset from object, default | `|T − R| ≤ L` | 0.5 |
| same, object already moving with the input | `L = 3 × boost` | 3 × boost |
| same, after a contact projection | `L` | 0.5 |
| target position | inside variant bounds box, clamped before and after | box at variant +696 |
| leash correction trigger | separation − editor+32 | > 1 |
| monitor step per tick | `|P − U|` | ≤ 2 |

All caps are per tick, in world units, independent of dt.

---

## 3. Contact handling

### 3.1 Contact response (`sub_82235650`)

**What it responds to (round 2).** This is the engine's *soft-ceiling*
response, not general collision. The collector reads only the soft-ceiling
data of the active structure designs (§3.1 step 8); ordinary level collision,
instanced geometry and other objects are not involved. The coefficients come
from the globals "soft ceilings" block. A held scenery piece is therefore
pushed back only by soft ceilings (invisible map-boundary surfaces of type
Acceleration); everything else it touches is left to the physics engine.

Called each tick for the held object (from §1.2 step 12) and, elsewhere, for
the monitor (unit update `sub_8297F658`, with player +140 as cached point and
player +152 as the normal slot). Inputs: object, in/out cached point Q, normal
output slot.

1. **Opt-out.** If the object's collision flags (object +364) have bit `0x4`
   set: return "no contact" without touching anything.
2. **Root.** Walk the parent chain (object +36) to the root object. All reads
   and writes below are on the root. Let biped = (root type == 0).
3. **Coefficients** from the globals soft-response block (globals +328):

   | | spring k | normal damping cn | tangent damping ct | tangent threshold |
   |---|---|---|---|---|
   | biped (offsets 0/4/8/12) | 45 | 10 | 2 | 4 |
   | non-biped incl. scenery 6 and crate 11 (16/20/24) | 20 | 4 | 1 | — |

   (values: Ravine map data, not code.)
4. **Prior state.** `active` = root flag bit 20 from the previous call.
5. Read root velocity **v** (`sub_82260CF0`) and physics point **P**
   (`sub_82260B58`).
6. **Sweep.** `sweep = 2 × max(|P − Q|, |v|·dt)` (`C+20` = 2). Then always
   `Q = P` (the cached point is refreshed whatever the result).
7. **Query range.** `cap = biped ? 6 : 10` (`C+92`, `C+36`);
   `base = active ? cap : (biped ? 1 : 3)` (`C+4`, `C+16`);
   `range = min(max(base, sweep), cap)`.
8. **Gather** (collector `sub_82486B78`; a native boundary in the extraction,
   read in round 2 from
   `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\generated\halo4_recomp.155.cpp`).
   Inputs: centre P, object radius ρ (definition +32), `range`, object type,
   a "huge vehicle" flag (type-1 objects only: definition +1552 bit `0x400`),
   and for an unparented biped "movement mode == 1" (unit +3910).
   1. Clear the set: count 0, primary −1, closest distance = float max
      (`C+84`); flags word 0. Working radius `r = range`.
   2. For every structure design active in the current zone set (bit mask
      from the scenario's zone-set record, scenario +256, 416-byte entries,
      +280; current zone set index at `833F7F7C`; structure design reached
      through the scenario structure-BSP block, scenario +176, 32-byte
      entries, +12): skip it if it has no soft-ceiling search tree
      (design +52 = 0). Designs are visited in ascending zone-set bit order.
      Query that tree with a sphere of radius `range` at P (§3.6). The result
      is an ordered list of keys (initial in-place capacity 8192, grown on the
      heap if exceeded, so there is no hit limit); key high 16 bits = soft
      ceiling index, low 16 bits = triangle index. Hits are processed in list
      order.
   3. Per soft ceiling (design +64/+68, 20-byte entries: name, type at +4,
      triangles at +8/+12, 68-byte triangle records: plane, bounding sphere
      centre and radius, three vertices) look up its scenario entry by name
      (§3.7; skip if absent or disabled). The lookup and type filter are
      redone only when a hit's ceiling index differs from the previous hit's.
      Filter by the scenario entry's flags word (bit0 ignore bipeds, bit1
      ignore vehicles, bit3 ignore huge vehicles, Gen4 scenario soft-ceiling
      schema):
      - type 0 *Acceleration*: rejected if the huge-vehicle flag is set and
        bit3 is set; otherwise rejected for bipeds by bit0 and for every other
        type (scenery and crates included) by bit1;
      - type 1 *Soft kill*: only for object types 0, 1 and 13 (bit mask
        `0x2003`), test radius ρ;
      - type 2 *Slip surface*: only when the movement-mode input is set, test
        radius 0.2 (`C+256`);
      - other types ignored.
   4. Acceleration triangles become samples:
      - if the design's importer version (+48) is below 1, skip triangles with
        a zero normal;
      - signed plane distance `s = n·P − planeD`; skip if `|s| ≥ r`;
      - skip unless `|P − sphereCentre| < sphereRadius + r`;
      - closest distance `q` from P to the triangle and its closest point
        (§3.8); skip if `q ≥ r`;
      - store (triangle, s, q, closest point, design index, triangle index,
        ceiling index). If 256 samples are already held, replace the one with
        the largest q, but only if the new q is smaller;
      - if q is below the set's closest distance it becomes the primary sample
        and the closest point is copied to the header; then the working radius
        shrinks to `min(r, q + 0.1)` (`C+12`).
   5. Soft-kill and slip triangles produce no samples; when one is within its
      test radius (same bounding-sphere and closest-distance tests) the flags
      word gets bit (1 << type): `0x2` soft kill, `0x4` slip surface.
9. If there is at least one sample:
   1. Forward selection (§3.2) with reverse = false → normal n into the
      caller's slot, distance dF, residual eF, plane count cF.
   2. If forward fails → no contact.
   3. Reverse selection with reverse = true → (dR, eR, cR) into scratch.
   4. **Reject** if reverse succeeds and `cF ≤ cR` and `eF ≥ eR`.
   5. Otherwise **respond** (§3.3) and mark contact.
10. Root flag bit 20 = contact (set or cleared).
11. **Biped-only extras** driven by the collector flags:
    - flag `0x2` (soft-kill timing): `lo = round(3·rate)`, `hi = round(6·rate)`
      ticks (round half away from zero; `C+16`, `C+92`, `C+40`, `C+100`). With
      the unit's stamp (+2188): if the stamp is unset, or `tick − stamp` is −1
      or `> hi`, set stamp = tick; else if `lo ≤ tick − stamp ≤ hi` send the
      surface notification (`sub_82943B08`); if below lo do nothing.
    - flag `0x4` (slip surface): if movement mode == 1, set unit +4015 bit
      `0x2`.
    The bridge rejects nonzero collector flags for scenery
    (`C:\Programming\GitHub\OpenH3M\tools\h4-forge\forge_bridge.cpp`).
12. Return whether a contact was applied.

### 3.2 Multi-plane selection (`sub_824863F8`, helper `sub_82486220`)

Inputs: sample set (primary index p, closest distance dmin, samples), point P,
reverse flag. Outputs: up to three chosen sample indices, normal, distance,
residual.

"**Near**" sample i: `closestDistance_i < dmin + 0.1` (`C+12`).
"**Adjacent**" to p (`sub_82486220`): i == p, or sample p's closest point
lies within 0.05 (√0.0025, `C+2836` = 0.0025 squared) of a vertex of i's
triangle, of i's own closest point, or of one of i's triangle edges (the
projection onto the edge must fall inside the edge).

1. Fail if p is invalid.
2. **Eligibility:** fail unless some sample is near, adjacent and has a
   negative plane distance (`< 0`).
3. `dir = P − closestPoint_p`; if reverse, negate. Normalize; fail if the
   reported length is 0.
4. Working vector `w = dir`. Up to three rounds: among near, adjacent samples
   choose the one whose normal has the smallest `n_i · w`, provided it is
   below −0.001 (`C+2596`). If none, stop. Append it.
   - after the first pick (normal n1, dot δ): `w = dir − n1·δ` (dir projected
     onto n1's plane);
   - after the second pick (n2): `e = normalize(n1 × n2)`;
     `w = e (e·dir)` (dir projected onto the crease);
   - after the third pick: no update.
   There is no explicit "already picked" exclusion; earlier picks drop out
   because w becomes perpendicular to their normals (dot 0, not below −0.001),
   apart from rounding.
5. Fail if nothing was picked.
6. **Distance output** = closest distance of the first pick.
7. **Normal:** let m = the picked normal with the smallest `n·dir`.
   - 1 pick: normal = n1.
   - ≥ 2 picks: `c = normalize(n1 × n2)`; normal = m with its component along
     c removed (`m − c(c·m)`). With two picks m is one of n1, n2, so this is m.
   - 3 picks: additionally `k = normalize(normal × n3)` and the normal has its
     component along k removed (k is perpendicular to it, so this only
     renormalizes). The code branches on `normal·dir < n3·dir` and on which
     pick was minimal, but every branch evaluates the same projection.
   - Normalize; if shorter than 1e-4, use the unit vector from P toward the
     primary closest point instead.
8. **Residual output** = `|w|²` (last working vector).
9. **Success** iff `normal · dir < −0.001`.

Note: the normal slot is written at step 7 even when step 9 then fails. Early
failures (steps 1–3, 5) do not write it.

Geometric reading (round 2, now backed by the collector's sign convention
`s = n·P − planeD`, positive in front of the triangle): eligibility needs a
sample with P behind its plane, the forward pass succeeds when P has crossed
behind the soft ceiling, the reverse pass tests the opposite interpretation,
and the returned normal is the ceiling's front-facing normal, so the spring
pushes back toward the front side.

### 3.3 Velocity response (`sub_82235650`)

With normal n, distance δ (= forward distance output), velocity v, tick dt:

1. Spring: `v1 = v + n (k · δ · dt)`.
2. Split: `vn = n (n·v1)`, `vt = v1 − vn`.
3. Tangent damping factor: non-biped `ct`; biped `ct` only if `|vt| ≥ 4`
   (threshold field), else 0.
4. `v2 = vt (1 − ct·dt) + vn (1 − cn·dt)`.
5. Set the root's linear velocity to v2 (`sub_822D1158`).

No position push-out is performed; the response is purely a velocity change
plus flag bit 20.

### 3.4 How the held update uses the response

For the held object the velocity written in §3.3 does not survive the tick
(round 2). The setter `sub_822D1158` writes the object's velocity cache
(`sub_82932FE8`, object +136..156) and applies it to the rigid bodies at
once: `sub_8223D7F0` → `sub_8248FC30` / `sub_8248FBE0` wake the body and call
the same linear/angular velocity setters (slots +64/+68) the drive uses.
Later in the same `sub_8244A8D8` call the drive (§4.2) reads that body
velocity and replaces it with `(pt − pc)/τ` whenever any component differs
by more than 1e-5. No physics step runs in between, and the velocity query
(`sub_82260CF0`) reads physics bodies, not the object cache, for objects with
an instance. What the held update actually consumes is the normal
(displacement projection and the 0.5 cap, §1.2 step 12), contact flag bit 20
and the refreshed cached point. A fresh implementation can omit the velocity
write for the held piece.

### 3.5 Whole-object out-of-world test (`sub_82451BA8`)

1. Take the object's physics point (`sub_8293A3B0`). If it is inside the
   world (`sub_82415970` false), return false at once.
2. Fetch the object's render geometry and node transforms
   (`sub_821EF090`); return false if unavailable.
3. Walk every mesh part (`sub_824F92C8` / `sub_824F93C0`, all 32 region
   permutation slots enabled) and every vertex of it (count from
   `sub_8236B808`; vertex stride 16 or 20 bytes by vertex format). Transform
   the vertex by its part's node transform (52-byte record: scale × basis ×
   vertex + position) and test it with `sub_82415970`.
4. If any vertex is inside the world the result becomes false (the walk
   continues over remaining parts but cannot set it true again).
5. Return true only if the physics point and every vertex are outside.

(Read in round 2 from the generated body; iterator internals and vertex
decompression were not followed.)

### 3.6 Soft-ceiling tree sphere query (`sub_82B9E1C8` → `sub_82BCA198` → `sub_82BC9860`)

Read in round 3 from
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\generated\halo4_recomp.105.cpp`
and `halo4_recomp.195.cpp`. The tree is the design's soft-ceiling
search-code record (design +56): quantization offset O = (+16, +20, +24),
scale k (+28), byte-code pointer (+32). The query is conservative: it returns
every triangle whose quantized cell the sphere may touch, never an exact
hit test; the collector's exact tests (§3.1 step 8.4) decide.

**Setup.** Integer conversion is truncation toward zero, saturating at the
32-bit limits (NaN gives the most negative value).

- Full-resolution centre `Q_i = trunc((P_i − O_i)·k) − 1` for each axis.
- Full-resolution radius `R = trunc(range·k) + 2`.
- Root frame: `pos_i = Q_i >> 16` (arithmetic), `rad = (R >> 16) + 1`, cell
  offsets `o_i = 0`, id base 0, shift 16.

**Interpreter.** Starting at the code pointer, read the opcode byte b0 and
operand bytes b1… (multi-byte operands are big-endian). A frame is passed by
value: changes made inside a child never affect the parent's continuation.
"Visit both" means: run the left child to completion as a nested query with
the current frame, then continue with the right child. Left children always
come first, so emitted ids are in depth-first, left-before-right order.

| Opcode | Length | Action |
|---|---|---|
| 0 | — | end of branch |
| 1–4 | 4 | rescale by `n = b0`: shift −= n; `o_i = (o_i + b_{i+1}) << n` for x, y, z; `pos_i = (Q_i >> shift) − o_i`; `rad = (R >> shift) + 1` |
| 5 / 6 / 7 / 8 | 2 / 3 / 4 / 5 | jump forward by the 8 / 16 / 24 / 32-bit operand (relative to the next instruction) |
| 9 / 10 | 2 / 3 | id base += 8 / 16-bit operand |
| 11 | 5 | id base = 32-bit operand |
| 16–18 | 4 | split on axis b0−16 with `v = pos`, `rr = rad`, lower-child bound `lo = b1`, upper-child bound `hi = b2`, right child at next + b3 (left child is the next instruction) |
| 19–24 | 4 | as 16–18 with `rr = rad + (rad >> 1) + 1`, `lo = 2·b1`, `hi = 2·b2` and v = y+z, y−z+255, x+z, x−z+255, x+y, x−y+255 respectively |
| 25–28 | 4 | as 16–18 with `rr = 4·rad`, `lo = 3·b1`, `hi = 3·b2` and v = x+y+z, x+y−z+255, x−y+z+255, x−y−z+510 |
| 32–34 | 3 | single-plane split on axis b0−32 at `s = b1`, right child at next + b2: if `v + rad < s` left only; else if `v > rad + s + 1` right only; else both |
| 35–37 | 7 | split on axis b0−35 with `lo = b1`, `hi = b2`, left child at next + 16-bit (b3,b4), right child at next + 16-bit (b5,b6) |
| 38–40 | 3 | prune on axis b0−38: end branch if `pos + rad < b1` or `pos > b2 + rad`; else continue |
| 41–43 | 7 | full-resolution prune on axis b0−41 with 24-bit bounds L = (b1,b2,b3), H = (b4,b5,b6): end branch if `Q + R < L` or `Q > H + R`; else continue |
| 48–79 | 1 | emit id `(b0 − 48) + base`; end branch |
| 80 / 81 / 82 / 83 | 2 / 3 / 4 / 5 | emit id = 8 / 16 / 24 / 32-bit operand + base; end branch |
| 96–99 / 100–103 / 104–107 | 2 / 3 / 5 | set a property slot (8 / 16 / 32-bit); no effect on emitted ids |
| others | — | invalid code (trap) |

Split rule for opcodes 16–28 and 35–37, with v and rr as given: if
`v + rr < hi`, go to the left child only (the left bound is not checked); else
if `v > rr + lo`, go to the right child only; else visit both.

Ids are appended to the caller's list in emission order. Duplicates are not
removed. A one-time library initialization guard runs first; if it fails the
query returns no ids.

### 3.7 Soft-ceiling enable lookup (`sub_82487108`)

Read in round 3 from
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\generated\halo4_recomp.28.cpp`.

1. Scan the scenario's soft-ceiling block (scenario +780 count, +784 entries,
   12 bytes each: flags u16 +0, runtime flags u16 +2, name +4, type +8) in
   index order for the first entry j whose name equals the design ceiling's
   name. None → no entry.
2. Enable bit: game-state bit array (thread-state +772), bit `j mod 32` of
   32-bit word `j / 32`. Clear → no entry.
3. Otherwise return entry j; the collector tests its flags at +0 (not the
   runtime flags at +2).

The bit array has four words (128 entries). `sub_82485668` resets it to all
ones (every ceiling enabled); `sub_821E3B60` sets or clears one bit.

### 3.8 Point–triangle closest point (`sub_8232FBA8`)

Read in round 3 from
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\generated\halo4_recomp.270.cpp`.
This is the standard region-classification method. Inputs: P and vertices V0,
V1, V2.

- `e0 = V1 − V0`, `e1 = V2 − V0`, `D = V0 − P`.
- `a = e0·e0`, `b = e0·e1`, `c = e1·e1`, `d = e0·D`, `e = e1·D`.
- `det = ac − b²`, `s = be − cd`, `t = bd − ae`.
- ε = 1e-6 (`C+916`).

Edge helpers:

- edge01(d): if `−d ≥ a` → V1; else `u = −d/a` (u = 0 if `a ≤ ε`) → V0 + u·e0.
- edge02(e): if `e ≥ 0` → V0; else if `−e ≥ c` → V2; else `u = −e/c`
  (u = 0 if `c ≤ ε`) → V0 + u·e1.
- edge12(numer): `den = a − 2b + c`; if `numer ≥ den` or `den < ε` → V1;
  else `u = numer/den` → V0 + u·e0 + (1−u)·e1.

Cases:

1. `s + t ≤ det`:
   - `s < 0`, `t < 0`, `d < 0` → edge01(d);
   - `s < 0` otherwise → edge02(e);
   - `s ≥ 0`, `t < 0`: `d < 0` → edge01(d), else V0;
   - `s ≥ 0`, `t ≥ 0` (inside): `g = 1/det` (g = 0 if `|det| ≤ ε`) →
     V0 + s·g·e0 + t·g·e1.
2. `s + t > det`:
   - `s < 0`: `p0 = b + d`, `p1 = c + e`. If `p1 > p0` → edge12(p1 − p0).
     Else: `p1 ≤ 0` → V2; else `e ≥ 0` → V0; else `u = −e/c` (0 if `c ≤ ε`)
     → V0 + u·e1.
   - `s ≥ 0`, `t < 0`: `p0 = b + e`, `p1 = a + d`. If `p1 > p0`:
     `den = a − 2b + c`; if `p1 − p0 ≥ den` or `den < ε` → V2; else
     `u = (p1 − p0)/den` → V0 + (1−u)·e0 + u·e1. Else: `p1 ≤ 0` → V1; else
     `d ≥ 0` → V0; else `u = −d/a` (0 if `a ≤ ε`) → V0 + u·e0.
   - `s ≥ 0`, `t ≥ 0`: `n = c + e − b − d`; `n > 0` → edge12(n); else V2.

Returns the distance `|X − P|` (not squared) and optionally the point X.

### 3.9 Ordering sensitivity of the contact set

The sample set depends on hit order (§3.6) only in two places: the shrinking
working radius (step 8.4), and replacement when 256 samples are held. Every
selector rule (§3.2) uses only samples with
`closestDistance < dmin + 0.1`. Such a sample always passes the radius
tests when it is processed (the working radius never drops below the final
`dmin + 0.1`), so for 256 or fewer such samples the selector's inputs are
the same whatever the order. The primary sample on an exact distance tie is
the first in hit order, which only matters when tied samples have different
closest points. Exact Halo 4 behaviour in those edge cases needs the same
tree byte code and the same traversal.

---

## 4. Driving the physics body

### 4.1 Body router (`sub_82452930`)

Inputs: object, 52-byte target transform, drive time `T_drive`.

1. Copy the target. If the object has no physics instance: do nothing.
2. **Active biped special case** (object type 0 only): if any body record
   (60-byte stride, instance +48, count instance +52) has byte +56 bit 0 set:
   1. Remember the object's current forward (object +112..120).
   2. Flatten the target basis (`sub_8257FB98`, §4.4).
   3. Write the flattened forward into object +112..120 and the flattened up,
      which is world (0,0,1), into object +124..132.
   4. Send the orientation-change notification with old and new forward
      (`sub_822AAB18`).
   5. Replace the target basis with identity (`82125148`); scale and position
      are kept.
3. Body index = signed byte at instance +24. If negative or ≥ body count, do
   nothing. Otherwise drive that body (§4.2).

Scenery (type 6) and crates (type 11) never take step 2.

### 4.2 Keyframe drive (`sub_8249B418`, `sub_82C023E8`, `sub_82C01FB8`)

Let `τ = T_drive` (0.2 held, 0.05 monitor) and `g = 1/τ` (`C+4` / τ).

1. Convert the target to position **pt** and orientation quaternion **qt**
   (`sub_82301320` then `sub_82C95448`); the target scale is ignored.
2. Read the body's current position **pc** (body +288) and orientation **qc**
   (body +352).
3. **Keyframe velocities** (`sub_82C023E8`):
   - `vk = (pt − pc) · g`;
   - relative rotation `qr = qt ⊗ conj(qc)` (Hamilton product, section 1
     convention; quaternions stored x, y, z, w): vector part
     `qc.w·qt.xyz − qt.w·qc.xyz + qc.xyz × qt.xyz`, scalar part `qt·qc`
     (4D dot). Lane decoding verified in round 2. This is the world-frame
     rotation with `qt = qr ⊗ qc`, so ωk is a world-frame angular velocity;
   - if `|qr.xyz|² > 1.42e-14` (`8201ECB0`): axis = normalize(qr.xyz);
     angle = `2·acos(|qr.w|)` when `|qr.w| < 1`, else 0 (`8203E7FC` = 2,
     acos `sub_8229D0F0`); flip the axis if `qr.w < 0` (shortest arc);
     `ωk = axis · angle · g`. Otherwise `ωk = 0`.
   - The keyframe's reference pose is the body's own current pose (pc, qc).
4. **Gains** (`sub_82C01E90` defaults then overwritten by `sub_8249B418`):
   linear position, angular position, linear velocity and angular velocity
   factors all = g; maximum linear acceleration, maximum angular acceleration
   and maximum allowed distance all = 3.40282347e38 (`C+84`).
5. **Controller** (`sub_82C01FB8`, step length passed = τ, inverse = g):
   1. If the keyframe reference position is farther than the maximum allowed
      distance from the body, teleport the body to the keyframe pose and set
      its velocities to the keyframe velocities. With the distance at float
      maximum this branch is unreachable for finite inputs.
   2. Position error `ep = keyframe reference position − pc` (= 0 here).
      Orientation error `eq = 2 × (keyframe reference orientation ⊗ conj(qc))`,
      negated if its scalar is negative (= 0 here).
   3. `Δv = (vk − v_body)·(τ·g) + g·ep`, `Δω = (ωk − ω_body)·(τ·g) + g·eq`.
   4. Cap `|Δv| ≤ maxLinAcc·τ` and `|Δω| ≤ maxAngAcc·τ` (never active here).
   5. New velocities `v' = v_body + Δv`, `ω' = ω_body + Δω`.
   6. For each of ω', v' (angular first): if any x/y/z component differs from
      the body's current value by more than 1e-5 (`82000E04`), wake the body
      and set that velocity. Otherwise leave it untouched.
6. Set owner object flag bit 30 ("keyframe-driven this tick"). Per the notes
   it is cleared by `sub_8293E878` / `sub_8293E1B0` before physics
   synchronization (not read here).

**Net behaviour** with these gains: `v' = (pt − pc)/τ` and
`ω' = rotationVector(qc → qt)/τ`. The body is commanded to reach the target
in τ seconds; the engine re-plans each tick. At 30 ticks/s the held object
closes about 1/6 of the remaining gap per tick (time constant 0.2 s), the
monitor about 2/3 (0.05 s). There is no explicit braking, tolerance or
velocity cap other than the 1e-5 change threshold.

### 4.3 Response-limit byte (`sub_82C969B0`)

Before the drive the bridge encodes the native body's angular response value
into body byte +411 (`sub_82C969B0`): values below 0.0099372864 encode to 0;
otherwise a 7-step binary search over the 256-entry table at `82003690`
(decoded value `float_bits((h + 0x3B800) << 12)`, entry 0 = 0, entry 1 ≈ 0.01,
last ≈ 999936) chooses the smallest entry not below the value (rounding up).
Inside `sub_82C01FB8` the byte is decoded, squared and compared with the new
angular speed, but the only result of that comparison is a stack value that is
never read. With the code as compiled it has **no effect** on the drive
(open question 5).

### 4.4 Flattened biped basis (`sub_8257FB98`)

up = world (0,0,1); forward.z = 0, then forward normalized with fallback
(1,0,0) (`82125170`) when shorter than 1e-4; left = up × forward.

### 4.5 Normal / fixed / phased

None of the functions in this section branch on the Forge physics mode. The
mode only matters through what it leaves behind: no instance or no bodies
(§1.2 step 3, §4.1 step 1) means no submission; otherwise the selected body is
driven the same way. Construction of fixed/keyframed motion (`sub_82CD3140`)
belongs to the physics-transition section.

---

## 5. Attachment compensation (`sub_82939248` branch; helpers in this file)

**Problem.** When the keyframe drive has run for a root object this tick
(flag bit 30) and the root's physics instance has instance +16 bit 3, a child
attached to it (during the detach transaction, `sub_82939248`, read in the
notes rather than here) would otherwise be placed against the root pose the
physics step has already advanced. The branch reconstructs the root pose one
tick earlier and re-expresses the child against it, so the child keeps its
pose relative to where the root visibly was.

**Maths** (helper order as in the bridge's `CompensateAttachmentPose`):

1. Root transform Rt, attached node transform Nt, root linear velocity v and
   angular velocity ω, tick dt.
2. `ω̂ = normalize(ω)` (unchanged and length 0 when shorter than 1e-4;
   `sub_8228ACE8`). Angle `θ = |ω| × (−dt)`.
3. `s = sin θ` (`sub_82265C30`), `c = cos θ` (`sub_82265E28`).
4. Rotation about ω̂ by θ (`sub_82300D40`, Rodrigues form:
   `c + (1−c)x²`, `(1−c)xy + s·z`, `(1−c)xz − s·y`, … stored so that a basis
   row times the matrix is that vector rotated about ω̂ by θ). With |ω| < 1e-4,
   θ = 0 and the rotation is identity.
5. Previous root: scale = Rt.scale; basis = Rt.basis with every basis vector
   rotated by step 4 (`sub_821E0550`); position = Rt.position + v·(−dt).
6. Result = previousRoot ∘ inverse(Rt) ∘ Nt (`sub_822864E0` inverse,
   `sub_8226BFC0` composition, section 1 convention: first argument is the
   outer transform A in A ∘ B).

**Where it is used (round 2, `sub_82939248` read in
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\generated\halo4_recomp.225.cpp`).**
Detach of child C from parent A (full sequence, round 3):

1. `N` = A's node transform for C's attachment node (A's node array at
   A +446, node C +57, 52-byte stride). `vis` = A's visibility/activity
   query (`sub_822CE090`). If vis: notify (`sub_82942938(C, 1, 0, 0, 0)`).
2. `rebuild` = C flag bit 8. If C flag bit 29 is set: set rebuild, write 255
   to C +265 and clear bit 29.
3. Unlink C from A's child chain (`sub_82938E60(C, 1)`).
4. Root Rr = topmost ancestor of A. If Rr passes the association test
   `sub_8298E798(Rr, 1)`, Rr has a physics instance with instance +16 bit 3,
   and Rr flag bit 30 is set: read Rr's linear and angular velocity, build the
   compensated pose above with Rr's velocities (`Nt` = N) and place C there
   (`sub_82939080`). Otherwise place C at N.
5. If vis: notify (`sub_82936D60(C, 0, 0)`).
6. If C has any of flag bits 6, 21, 22: clear all three and set rebuild.
7. If rebuild: rebuild C's physics (`sub_82388A08(C, 0)`).
8. If C has neither flag bit 8 nor bit 9 and C is not object type 7:
   `sub_82937298(C)`.
9. `sub_8220F670(C)`, `sub_8225CBA8(C)`, `sub_8220BD58(C, 0)`; clear bit 24
   of C +16 (64-bit); write 255 to C +309.
10. Copy the former root's motion association to C (`sub_8298E800(C, Rr)`).
11. **Velocity inheritance.** p = C's physics point (`sub_82260B58`).
    Association velocity (`sub_822980D8(C, p, …, qualify = 1)`): requires C
    flag bit 3 and an association record k (`sub_8298E2D8(C)`); the record's
    associated object's definition +28 must have bit 11; record byte +457
    must be nonzero. With record byte +460 zero the motion is (ω at +288,
    v at +264, centre at +240), otherwise (ω +24, v +0, centre +48). Then
    linear = `v + ω × (p − centre)`, angular = ω. If the test fails, use the
    linear and angular velocity of the former **immediate parent** A.
12. Set C's velocities to the result (`sub_822D1158`).

(Read from
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\generated\halo4_recomp.225.cpp`
and `halo4_recomp.193.cpp`; the notification and bookkeeping callees in
steps 1, 5, 8, 9 and 10 were not followed.)

---

## 6. Persistent state and resets

| Location | Contents | Written by | Reset |
|---|---|---|---|
| editor+0 | held object | grab (other section) | grab/release |
| editor+4 | magnet target | magnet stage | other section |
| editor+32 | leash distance | follow §1.3 step 12 | other section |
| editor+36/+40/+56..64 | camera offset scale/decay/vector | other sections | other section |
| editor+68..76 | held contact cached point | contact response §3.1 step 6, every call | grab (other section) |
| editor+80 | focal point outside world | follow §1.3 step 2, every tick | — |
| editor+81 | rotation-snap enable | preferences | — |
| editor+84..135 | persistent target (scale, basis, position at +124) | held update, quantization copy-back | grab |
| editor+136..171 | remembered quantized basis | §1.2 step 16 | grab |
| editor+172..223 | body-0 pose cache (position +212) | §1.2 step 4, every 5th tick while not fully outside | grab |
| editor+224 | rotation-step mode 0..5 | preferences | — |
| editor+228..263 | obstruction smoothing (+228 pull-in fraction, +256/+260 exclusions) | follow §1.3 step 3 | other section |
| editor+276 | pitch ratchet | follow §1.3 step 13 | other section |
| object flags bit 20 | contact active | contact response, every call | each call |
| object flags bit 30 | keyframe-driven this tick | drive §4.2 step 6 | cleared before physics sync |
| player +140 / +152 | monitor cached point / contact normal | monitor contact response | — |
| unit +2188, +4015 | surface timing stamp / flag | biped contact extras | — |

Nothing in these functions resets state on its own except the per-call flags.
Initialization values on grab are in the grab/select section
(`C:\Programming\GitHub\OpenH3M\tools\h4-forge\spec\03-grab-select-distance.md`).

---

## 7. Tuning constants

All literals are in the executable image unless marked "map data".

| Value | Address | Use |
|---|---|---|
| 0 | `821289E0` (C+0) | moving test, dot floor, zero vectors |
| 1 | `821289E4` (C+4) | precision off factor, boost base, leash excess threshold, reciprocal numerator, damping base |
| 0.1 | `821289EC` (C+12) | precision movement factor; near-sample band |
| 3 | `821289F0` (C+16) | moving step limit × boost; non-biped base query range; surface-timing lo seconds |
| 2 | `821289F4` (C+20) | sweep factor; monitor step cap |
| 10 | `82128A04` (C+36) | non-biped query range cap |
| 0.5 | `82128A08` (C+40) | default/contact step limit; rounding |
| 0.0174532924 | `82128A20` (C+64) | degrees to radians |
| 3.40282347e38 | `82128A34` (C+84) | drive acceleration/distance caps; selector "best" seed |
| 4 | `82128A38` (C+88) | movement speed; monitor step cap squared |
| 6 | `82128A3C` (C+92) | biped query range cap; surface-timing hi seconds |
| −1 | `82128A44` (C+100) | reverse factor; rounding |
| 1e-4 | `82128A54` (C+116) | epsilons (normalize, quantization, offsets, facing) |
| 0.2 | `82128AE0` (C+256) | held drive time; slip-surface test radius |
| 8192, 256 | literals in `sub_82486B78` | initial (growable) hit-list capacity; sample capacity |
| 1e-6 | `82128D74` (C+916) | point–triangle division guard |
| 16 | literal in `sub_82BCA198` | initial tree-query shift |
| 128 bits | `sub_82485668` | soft-ceiling enable bits, reset to all enabled |
| `0x2003` | literal in `sub_82486B78` | object types eligible for soft kill (0, 1, 13) |
| 0.05 | `82128AF4` (C+276) | monitor drive time |
| −0.001 | `82129404` (C+2596) | selector plane / success threshold |
| 0.0025 | `821294F4` (C+2836) | adjacency distance squared (0.05) |
| [0,90,45,30,15,5] | `833F195C` | rotation steps, degrees (integers) |
| (0,0,1) | `82125188` via `833F7EAC` | world up |
| identity basis | `82125148` | biped controller basis |
| (1,0,0) | `82125170` | flatten fallback |
| 1.0 / 3.4028200e38 | `82043E74` / `82043744` | gain defaults before overwrite (`sub_82C01E90`) |
| 1.42108547e-14 | `8201ECB0` | minimum rotation-axis length squared |
| 0.5 | `8201EBB0` | rsqrt refinement |
| 2, 0, π | `8203E7FC`, `8203AF30`, `8200F464` | angle doubling, zero angle, acos range |
| 1e-5 | `82000E04` | velocity change threshold |
| 0.0099372864 | `0x3C22D000` literal | response byte zero cutoff |
| table | `82003690` | response byte decode |
| byte, 0 in image | `8407F008` | global switch for focal-flag restriction |
| byte, 0 in image | `8407EFFA` | alternate held path |
| 6 words, 0 in image | `8407F34C` | obstruction configuration (runtime) |
| 45, 10, 2, 4 | globals +328, offsets 0/4/8/12 (map data) | biped contact |
| 20, 4, 1 | offsets 16/20/24 (map data) | non-biped contact |
| def +1428, unit +2168 | tag / runtime | boost |
| definition +32 | tag | contact radius |
| tick mod 5 | literal | cache refresh |

---

## 8. Corrections to earlier notes

- `C:\Programming\GitHub\OpenH3M\tools\h4-forge\FULL-RE-FINDINGS.md` (entry on
  `82452930`'s type-0 branch) and the comment on `PrepareActiveBipedTarget` in
  `C:\Programming\GitHub\OpenH3M\tools\h4-forge\forge_bridge.h` say the object's
  current up is retained. The code writes the flattened up, world (0,0,1),
  into object +124..132 (§4.1 step 2).
- The notes treat the response-limit byte (body +411) as a meaningful
  controller input. In `sub_82C01FB8` its decoded value only feeds an unused
  stack value (§4.3).
- `sub_82451BA8` is described in the notes as a body-cache refresh decision
  "not simply touching". Its result is true only when the origin and all
  geometry vertices are outside the world, and it also enables the
  out-of-world restriction (§2.3), not just the cache refresh.

---

- (round 2) Earlier wording here, in the bridge (`ContactSample` "geometry
  records", `SceneryContactWorld.collect`) and in the notes describes
  `sub_82235650` as a general contact response. Its collector reads only
  structure-design **soft ceilings**; it is the soft-ceiling push-back
  (§3.1), consistent with its coefficients living in the globals soft-ceiling
  block.

---

## 9. Open questions (round 3 status)

Requirement (user, via coordinator, round 3): the implementation must behave
exactly like Halo 4 in all respects. Halo 3 may supply data (soft-ceiling
geometry and tree, scenario soft-ceiling entries, world containment, render
vertices, attachment records), but Halo 4's rules above are applied to that
data. NOT-NEEDED below means no observable effect, nothing else.

| # | Question | Status | Need | Outcome |
|---|---|---|---|---|
| 1 | Contact collector, including the tree query, point–triangle distance and name lookup | RESOLVED | NEEDED | §3.1 step 8, §3.6–3.9. Halo 3 data must provide soft-ceiling triangles, a search tree in the byte-code form of §3.6 (or an exactly equivalent traversal order), and scenario soft-ceiling entries with names, flags and enable bits |
| 2 | Writer of global `8407F008` | RESOLVED: no writer and no data pointer to it in the image; constant 0 | NOT-NEEDED (no observable effect; the focal-flag branch of §2.3 never fires) | |
| 3 | Obstruction configuration at `8407F34C` | UNRESOLVED: runtime-filled camera globals (`8407F2B0` +156); writer not traced | NEEDED (camera section) | |
| 4 | Whole-object outside-world test | RESOLVED; mesh iterator internals and vertex unpacking not followed | NEEDED | §3.5, applied to Halo 3 world containment and the object's render vertices |
| 5 | Response byte comparison | RESOLVED | NOT-NEEDED (dead) | §4.3 |
| 6 | Contact velocity vs body drive | RESOLVED: overwritten in the same call | NOT-NEEDED for the held piece (no observable effect); the normal, flag bit 20 and cached point are NEEDED | §3.4 |
| 7 | Quaternion convention | RESOLVED | NEEDED | §4.2 |
| 8 | Orientation builder and degenerate facing | RESOLVED | NEEDED | §1.3 step 9 |
| 9 | Composition order | RESOLVED | NEEDED (used by 10) | §5 |
| 10 | Detach, including velocity inheritance | RESOLVED; bookkeeping callees named but not followed (`sub_82942938`, `sub_82936D60`, `sub_82937298`, `sub_8220F670`, `sub_8225CBA8`, `sub_8220BD58`, `sub_8298E800`, association record layout behind `sub_8298E2D8`) | NEEDED | §5 |
| 11 | Monitor contact response vs held stage ordering | UNRESOLVED (partly traced) | NEEDED | see below |

**Q11, what was traced.** Game tick `sub_82370150` calls the players update
`sub_822BEB90`. That loops over players with `sub_823E9360`, which calls the
current game engine's function table slot 30 (offset 120). The engine table
is at `835718E0` indexed by engine type 1..5. The Forge engine object
`833FE5C8` has table `821314D8`, whose slot 30 is `sub_8244D970`, which calls
`sub_8244D0E0` (this stage). The monitor's contact response `sub_8297F658` is
called from `sub_82289960`. That is slot 97 of an object function table at
`82002678`; slot 73 of the same table (`sub_82243878`) reaches it through
`sub_82976D40` → `sub_82976A98`. No static call path from `sub_82370150` to
those object-table slots was found: they are only reached through function
tables loaded at runtime, and the candidate table dispatchers checked
(`sub_82206F50`, `sub_823EC1B8`) are not the object update. So whether the
monitor's contact response runs before or after `sub_822BEB90` within the
tick is still not determined. Determining it needs the object-update
dispatcher identified, for example by finding the code that loads slot 73
from per-type tables.

---

## Round 2 changes

- §3.1: identified the response as the soft-ceiling push-back. Replaced the
  collector boundary with its full rules (structure-design soft ceilings,
  type and flag filters, 256-sample replacement, shrinking search radius,
  soft-kill/slip flags).
- §3.1 step 11: named the collector flags (soft kill `0x2`, slip surface
  `0x4`).
- §3.2: geometric reading now backed by the collector's plane-distance sign.
- §3.4: established that the held piece's contact velocity is overwritten in
  the same call (Q6).
- §3.5: full control flow of the whole-object outside-world test (physics
  point first, then every render-geometry vertex).
- §4.2: verified quaternion convention `target ⊗ conj(current)` (Q7).
- §1.3 step 9: frame builder rules including the vertical-facing fallback
  (Q8).
- §5: added how the detach transaction uses the compensated pose.
- §8: added the soft-ceiling correction.
- §9: every open question tagged with its status and whether Halo 3 needs it.

## Round 3 changes

- Removed every substitution of a Halo 3 system for Halo 4 behaviour; §9
  re-tagged (Q1, Q4, Q9, Q10, Q11 now NEEDED; NOT-NEEDED only where there is
  no observable effect).
- §3.1 step 8: designs visited in ascending zone-set order; the hit list
  grows without limit (8192 is only the initial capacity); ceiling lookup
  redone only when the ceiling index changes.
- §3.6: specified the soft-ceiling tree sphere query (setup, every opcode,
  split and prune rules, emission order).
- §3.7: specified the soft-ceiling name lookup and enable bits.
- §3.8: specified the point–triangle closest point, including degenerate
  guards.
- §3.9: added the analysis of when hit order can change the selector's inputs.
- §5: full detach sequence, including velocity inheritance (association
  velocity at the child's point, else the former immediate parent's
  velocities).
- §7: added the new constants.
- §9 Q11: recorded the traced dispatch path of the Forge stage and why the
  unit-update side is still open.


---

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


---

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


---

# 05 — Monitor camera while holding, and the Halo 4 data inventory

Clean-room behavioural specification derived by static reading only. Nothing was
built, run, tested or launched. Sources read:

- Halo 4 functions statically recompiled into C:
  `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\forge_original.cpp`
  (157 `DEFINE_REX_FUNC` bodies; the disassembly comments in that file were the
  primary evidence).
- Wrapper: `C:\Programming\GitHub\OpenH3M\tools\h4-forge\forge_bridge.cpp`,
  `C:\Programming\GitHub\OpenH3M\tools\h4-forge\forge_bridge.h`.
- Loader: `C:\X360\ISOs\H3M\.local\OpenH3M-source\halo3mp\src\advanced_forge.cpp`
  (`Load()`), build wiring in
  `C:\X360\ISOs\H3M\.local\OpenH3M-source\halo3mp\CMakeLists.txt`.
- Data: `C:\X360\OpenH3M\advanced-forge\` (byte-identical to the copies in
  `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\`).
- Field names for tag data: TagTool Gen4 schemas
  `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\stock-h3-audit\TagTool\TagTool\Tags\Definitions\Gen4\Globals.cs`,
  `...\Gen4\ForgeGlobals.cs`, `...\Gen4\RenderModel.cs`. Names are corroboration
  only; the consuming code is the authority for behaviour.

Constants were read from `C:\X360\OpenH3M\advanced-forge\h4-image.bin`, which is
loaded at guest address 0x82000000, so **file offset = address − 0x82000000**.
Both are cited as `addr (off 0x…)`.

Conventions (same as sections 01 and 03):

- "Editor" = the per-player Forge editor record (336 bytes per player). Offsets
  are provenance only.
- "Monitor" = the player's controlled unit. "Held object" = editor +0.
- "View direction" D = the monitor's desired view vector (unit record +1212).
- "Focal distance" d = editor +28 (the hold distance; its clamping is specified in
  section 03, function 82452738).
- "Definition radius" = the held object's tag bounding radius (tag +32), not the
  live bounding sphere.
- All original arithmetic is single precision. World is Z-up; frames are
  forward / left / up.

---

## Part A — monitor camera while holding an object

### A.0 Where this runs

Each tick, for a player holding an object, the editor tick 8244D0E0 runs, in
this order: hold-distance policy 82452738 (section 03), the held-object update
8244A8D8, then the **monitor-follow stage 8244AF48**. Inside the held update,
the camera-to-monitor correction 8244B338 (A.6) also uses the camera point.

The monitor-follow stage moves the *monitor body* (not just a render camera)
behind the held object, decides which way it faces, updates the local player's
view angles, and maintains two pieces of persistent state used next tick: the
"retained distance" (editor +32) and the "pitch history" (editor +276).

### A.1 Basis helpers used throughout

1. **View-up from a forward vector** (822C8040). Given forward f:
   horizontal side s = normalise(f.y, −f.x, 0); if that has zero length (f is
   vertical), s = (1, 0, 0) (constant at 82125170 (off 0x125170)). Up u = s × f.
   u is perpendicular to f and tilts upward.
2. **Apply a basis-relative offset** (821D6D90). Given point p, offset
   (ox, oy, oz), forward f and up u: left l = u × f;
   p ← p + f·ox + l·oy + u·oz.
3. **Rotate a vector about a unit axis** (8229C9F0) by an angle given as
   (sine, cosine) — standard Rodrigues rotation.

### A.2 Camera point and backoff distance (824BE840, 824BEA10, 824BEAD0, 8244B758)

There are two variants of the same construction:

- **Focus point** F (824BEAD0, "mode 0"): no prediction, no backoff.
- **Backed-off camera point** P (824BEA10, caller-chosen mode; the monitor-follow
  stage uses mode 1 = with prediction). Also returns the view direction D and
  the distance d.

Steps (824BE840 builds the shared description, the wrappers finish it):

1. If the editor has no held object, or the monitor is invalid, nothing is
   produced.
2. H = the held object's physics point (8293A3B0).
3. H ← H + editor_offset × editor_scale, where editor_offset is the 3-vector at
   editor +56/+60/+64 and editor_scale is editor +36 (world-space offset; set by
   the grab code, see section 03).
4. Mode 1 only: H ← predicted(H, tick interval) (A.3).
5. **Pitch-dependent vertical lift** (8244B758):
   - z = D.z − pitch_history (editor +276); clamp z to [−1, 1] (constants
     −1.0 at 82128A44 (off 0x128A44), 1.0 at 821289E4 (off 0x1289E4)).
   - a = arcsine(z) (82226398; exact definition in A.9.3; returns exactly 0 for
     input 0), rounded to single precision.
   - x = (π/2 − a) × (1/π) (π/2 at 82128AC8 (off 0x128AC8), 1/π at 82128B70
     (off 0x128B70)), clamped to [0, 1]. So x = 0 looking straight up, 0.5 level,
     1 straight down.
   - c = PitchCurve(x) × definition_radius. PitchCurve is the camera
     "pitch to vertical offset" function (camera-pitch-function.bin, B.3),
     evaluated by the original function evaluator 8226CD10. Its output runs from
     +1 (looking straight up) through 0 (level) to −1 (straight down); the decoded
     table is in B.3.
   - The lift is the basis-relative offset (0, 0, c): it is applied along the
     **view-up vector u** of D (A.1 step 1), not along world Z. (The "(0,0,1)" read
     through pointer 833F7EAC → 82125188 (off 0x125188) is the local-z unit used to
     form the offset, not a world direction.)
6. F = H + u·c (A.1 step 2 with offset (0, 0, c)). This is the result of the
   mode-0 variant.
7. P = F − D·d, with d = editor +28. The wrapper 824BEA10 returns P, D and d.

824BE840 also computes the camera field of view in radians (822E15E0: camera
FieldOfView × π/180 when finite and within [π/180, 150°], i.e. limits at
833F9C00 (off 0x13F9C00) = 0.01745 and 833F9C04 (off 0x13F9C04) = 2.618; otherwise
fallback 1.3614 rad = 78° at 82128E60 (off 0x128E60)) and copies the six
obstruction settings (B.2) into its description, but **neither is consumed** by
the camera point or by the monitor-follow stage. They can be omitted.

### A.3 Prediction (824BEB50, mode 1 only)

Inputs: the point H from A.2 step 3, tick interval t, the held object's linear
velocity v and angular velocity ω (82260CF0), its origin R (8225EA20), and the
editor's cached position C_e (editor +8/+12/+16; written elsewhere by the held
update).

1. **Linear part.**
   - Predicted travel p = |v| × t.
   - If there is no held object, k = 1.
   - Else if p ≤ 0.001 (82128C0C (off 0x128C0C)), k = 0 (no linear prediction).
   - Else k = min(1, |C_e − R| / p). C_e is the held object's origin captured at
     grab time (82449ED8 writes it via 8225EA20; no other writer was found in the
     Forge functions). So the prediction never projects further than the object
     has actually moved since it was grabbed; a freshly grabbed, stationary object
     gets no linear prediction.
   - H' = H + v × k × t.
2. **Angular part**, only if the held object has a physics instance with at least
   one rigid body:
   - q = the object's orientation as a quaternion (forward/up from 82243068 →
     matrix → quaternion).
   - c_local = the first body's local centre of mass (8249B1F8; for a fixed or
     keyframed body the authored centre-of-mass offset is used instead).
   - c_world = q applied to c_local.
   - Rotation r = axis normalise(ω), angle |ω| × t.
   - H' ← H' + (r applied to c_world − c_world).
   - The angular part is not scaled by k.

### A.4 Monitor-follow stage (8244AF48)

Per tick, for the holding player:

1. Get P, D, d from A.2 (mode 1, with prediction).
2. F = P + D·d (the predicted focus point).
3. **Outside-the-world test** of F (82415970) with the query mask
   0x0000100900000000 (B.7). The boolean result is stored at editor +80. Its
   16-byte detail result is never read. Exact definition in A.9.1: true only when
   F lies in the "outside" region of the 3D BSP tree of every loaded structure BSP
   (and at least one is loaded).
4. If the focus point is outside the world (test true):
   - Exclusions for the obstruction rays: the held object and the monitor
     (written to editor +256/+260).
   - Run the obstruction filter (A.5) from F (start) toward P (end) with the six
     runtime obstruction settings and the tick interval. It yields a smoothed
     clear fraction s ∈ [0, 1] (1 = unobstructed).
   - Camera point C = F − D·(s·d), i.e. the point at fraction s of the way from F
     to P.
   - Remaining distance r = d − s·d.
   Otherwise (the normal case: focus inside the world) C = F and r = d, and no
   obstruction rays are cast at all.
5. M = the monitor's reference point (822410D0).
6. Displacement Δ = P − M. If |Δ|² > 4 (82128A38 (off 0x128A38)), rescale Δ to
   length 2 (2.0 at 821289F4 (off 0x1289F4)). The monitor never moves more than 2
   world units in one tick, and it always heads for the **unobstructed** point P,
   not C (the body's own collision keeps it out of walls).
7. **Contact handling.** If the monitor's contact flag is set (unit +256, bit
   0x00100000) and |Δ| > 0.0001 (82128A54 (off 0x128A54)): with the stored contact
   normal n (player record +152/+156/+160), if n·Δ < 0, Δ ← Δ − n·(n·Δ) — the
   inward component is removed; outward motion is untouched.
8. Target position T = M + Δ.
9. **Facing.** fwd = normalise(C − T). If |C − T| < 0.0001, fwd = D. In the
   normal case C = F, so the monitor looks from its new position at the focus
   point. In the outside-world case C lies between P and F, so it still looks
   toward F, except when s = 1 and the monitor has reached P (C = P = T): then it
   falls back to the view direction.
10. Build the monitor's target transform from position T, forward fwd and world
    up (0, 0, 1) (8221B258) and submit it to the monitor's body controller
    (82452930) with response parameter 0.05 (82128AF4 (off 0x128AF4)).
11. **View update** (local players only, i.e. local index 0–3): up = view-up of
    fwd (A.1 step 1); convert (fwd, up) to view angles (A.7) and store them in the
    local player's view.
12. **Retained distance**: editor +32 = min(|T − C|, r). Normal case: about d
    (the monitor sits about d from the focus). Outside-world case: about
    (1 − s)·d, the monitor's distance from the obstruction point. Reset to 0 on
    editor initialisation (82449DD8) and on release (82449ED8); read only by A.6.
13. **Pitch history** h (editor +276) with z = fwd.z: if h > 0 and 0 < z < h, set
    h = z; else if h < 0 and h < z < 0, set h = z; otherwise unchanged. The history
    only relaxes toward zero from the same side.

    **Where h is set** (82449ED8, Round 2 R2): when a local player grabs an object,
    h = the vertical component of the unit vector from the monitor's physics point
    to (held object's physics point + grab offset × offset scale), i.e. the sine of
    the elevation angle at which the object was grabbed. It is reset to 0 on editor
    initialisation (82449DD8) and on release. Effect: at grab, the lift curve sees
    "level" (D.z − h about 0) when the player is looking at the object, whatever
    the actual pitch; as the facing later levels out, h relaxes toward 0 so the
    curve gradually returns to measuring true pitch.

### A.5 Obstruction filter (824F5CF0 → 824F5F78 → 824F5E28)

Persistent state per editor (editor +228, 36 bytes):

| Offset | Meaning |
| --- | --- |
| +0 | smoothed clear fraction s |
| +4 | fraction velocity |
| +8 | return-delay timer (seconds) |
| +12/+16/+20 | cached obstruction point |
| +24 | cached-point valid flag (byte) |
| +28, +32 | ray exclusions: held object, monitor |

Settings (B.2): cylinder fraction cf, test angle θ, return delay τ. The tag's
"max inward/outward acceleration" and "max velocity" fields are **not read** by
this code; it uses its own fixed stiffnesses.

#### A.5.1 Target and upper bound (824F5F78)

Inputs: start A (focus F), end B (camera P).

1. seg = B − A, L = |seg|, dir = seg / L. Both outputs are pre-set to 0 by the
   caller (821289E0 (off 0x1289E0) = 0.0). If L ≤ 0.0001 (82128A54), return
   immediately: target = 0 and upper = 0 (the camera collapses onto the focus).
2. **Centre ray** A → B. Fraction defaults to 1.0 on a miss. Record the centre
   fraction f_c and its hit point (B on a miss). best = f_c, best_point = that
   point.
3. **Cone radius** R = sin(θ) × L (sine via 82265C30, A.9.3). For Ravine's
   θ = 0.17453292 (0x3E32B8C2), sin(θ) = 0.17364818 (0x3E31D0D4).
4. **Three lateral vectors**: v0 = (view-up of dir) × R; v1 = v0 rotated +60°
   about dir; v2 = v0 rotated −60° about dir (cos 0.5 at 83400920
   (off 0x1400920), sin 0.8660254 at 83400924 (off 0x1400924)).
5. **Six surrounding rays**, in order +v0, −v0, +v1, −v1, +v2, −v2 (sign +1 from
   821289E4, −1 from 82128A44). For lateral vector w: start = A + w·cf,
   end = B + w. With cf = 0 every ray starts at the focus (a cone); cf = 1 gives a
   cylinder. The six end points form a regular hexagon around B.
6. Any surrounding hit with fraction < best replaces best and best_point.
7. **Cached point** (if valid), cached point Q:
   - t = dir·(Q − A) / L. If t < 0 or t > 1, invalidate.
   - Allowed radius at t: ρ = lerp(cf·R, R, t). If squared distance from Q to the
     segment > ρ² + 0.0001, invalidate (8228CCE0).
   - If |Q − A|² > |best_point − A|² + 0.0001 (the fresh hit is nearer), invalidate.
   - Otherwise keep the cache: best = t, best_point = Q. The cached point stays at
     its fixed world position while it remains valid.
8. If no valid cache remains and best < 1.0, cache best_point and mark it valid.
9. Outputs: target = best, upper = f_c.

#### A.5.2 Single ray request (824F5E28)

- Request type 27, the 64-bit mask from B.2, start, end, up to two exclusions
  (an exclusion of −1 is skipped).
- If |end − start|² ≤ 1.0e-6 (821296D0 (off 0x1296D0)), no query; reported as a
  miss.
- On a hit, the caller's fraction and point are overwritten; on a miss both are
  left unchanged (the point is pre-set to the ray end).
- What counts as a hit is specified in A.9.2.

#### A.5.3 Smoothing (824F5CF0), with tick interval Δt

1. Compute target g and upper U (A.5.1).
2. If Δt = 0 exactly: s = g (velocity and timer untouched), then go to step 5.
3. Choose stiffness k:
   - If s < g (opening up, camera moving outward):
     - k = 25 (82128A88 (off 0x128A88)) if velocity ≥ 0, else k = 75
       (82129018 (off 0x129018)).
     - If g − s ≥ 0.05 (82128AF4 (off 0x128AF4)) and timer > 0: timer −= Δt,
       velocity = 0, k = 0 (hold still this tick).
     - If g − s ≥ 0.05 and timer ≤ 0: timer = 0.
     - If g − s < 0.05, the timer is not consulted.
   - If s ≥ g (closing in): k = 75 and timer = τ (return delay).
4. Critically damped spring, damping factor 2 (821289F4) and half factor 0.5
   (82128A08 (off 0x128A08)):
   - a = k·(g − s) − 2·√k·velocity
   - s ← s + velocity·Δt + 0.5·a·Δt²
   - velocity ← velocity + a·Δt
5. **Upper clamp**: if U < s then s = U, timer = τ, velocity = 0. The camera can
   never stay beyond the centre ray's own hit.

Effect: the camera moves in quickly (k = 75) when something blocks it, moves back
out more gently (k = 25), and with τ > 0 would wait τ seconds before moving out by
0.05 or more. With Ravine's τ = 0 there is no waiting.

### A.6 Camera-to-monitor correction during the held update (8244B338)

Used inside the held-object update when the requested motion is non-trivial
(section 03 covers when). Compute F (mode 0, A.2 steps 1–6, no prediction) and the
monitor reference point M. δ = M − F, e = |δ| − retained_distance (editor +32).
If e > 1.0 (821289E4), the correction is δ × (e / |δ|) (pull the held object
toward the monitor by the excess); otherwise zero.

### A.7 View conversion (823FC348)

Inputs: local index, forward f, up u.

1. Rotation matrix with rows f, l = u × f, u.
2. Matrix → quaternion (8229E900) → three angles (82331BC8, tolerance 0.0001
   (82128A54)), Round 2 R5:
   - angle 0, heading = atan2(f.y, f.x);
   - angle 1, pitch = arcsine(f.z) (positive looking up);
   - angle 2, roll = atan2(l.z, u.z).
   Near vertical (|f.z| within the tolerance of 1) pitch = ±π/2, roll = 0 and the
   heading comes from the quaternion's x/w part instead. Because the caller always
   passes the view-up of f (whose left vector is horizontal), roll is always 0 in
   this use.
3. If the heading < 0, add 2π (833FD91C (off 0x13FD91C) =
   6.2831855). Store the three angles in the local view record (TLS +100 record,
   480 bytes per local player, at +288+20/+24/+28).
4. Notify the view system (82400D48; our wrapper captures the angles and the
   forward vector at this point).

To reproduce Halo 4, the local player's view must end the tick with exactly these
values: heading = the wrapped angle above, pitch = arcsine(f.z), roll = 0. Where
Halo 3's view stores only heading and pitch, those two must be set to these
values with no further processing; the roll is 0 in every case this stage can
produce, so nothing is lost.

### A.8 Constant table (Part A)

All from `h4-image.bin` unless marked "config".

| Value | Address (file offset) | Use |
| --- | --- | --- |
| 0.0 | 821289E0 (0x1289E0) | default outputs, zero |
| 1.0 | 821289E4 (0x1289E4) | miss fraction, clamp, correction threshold, cap on k |
| −1.0 | 82128A44 (0x128A44) | clamp, ray side sign |
| 0.0001 | 82128A54 (0x128A54) | degenerate-length/epsilon tests |
| 1.0e-6 | 821296D0 (0x1296D0) | minimum squared ray length |
| 0.001 | 82128C0C (0x128C0C) | prediction travel threshold |
| 2.0 | 821289F4 (0x1289F4) | max monitor step; spring damping factor |
| 4.0 | 82128A38 (0x128A38) | squared max monitor step |
| 0.5 | 82128A08 (0x128A08) | half factor in integration |
| 0.05 | 82128AF4 (0x128AF4) | controller response parameter; outward gap threshold |
| 25.0 | 82128A88 (0x128A88) | outward stiffness |
| 75.0 | 82129018 (0x129018) | inward / reversing stiffness |
| 0.5, 0.8660254 | 83400920, 83400924 (0x1400920, 0x1400924) | ±60° ray rotation |
| π/2 | 82128AC8 (0x128AC8) | pitch mapping |
| 1/π | 82128B70 (0x128B70) | pitch mapping |
| 2π | 833FD91C (0x13FD91C) | heading wrap |
| (1,0,0) | 82125170 (0x125170) | side fallback when looking vertical |
| (0,0,1) | 82125188 (0x125188), via pointer 833F7EAC (0x13F7EAC) | up unit |
| 0, 10° (0.1745 rad), 0 | config (camera-settings.bin +192/+196/+212) | cylinder fraction, test angle, return delay |
| pitch curve | config (camera-pitch-function.bin) | vertical lift |
| 0x0000100900000000 | built at start-up by 83292E30/83292E50 into 845548B0/845548B8 | ray and containment query mask |

### A.9 World queries and maths helpers, exactly (Round 3)

#### A.9.1 Outside-the-world test (82415970 with mask 0x0000100900000000)

Mask words: high 0x00001009, low 0x00000000. Behaviour with this mask:

1. The extra "location" query gated by high-word value 0x2 is skipped (bit clear).
2. For each loaded structure BSP (bit set in the active-BSP mask read from
   8405D350, up to 32):
   - Walk that BSP's 3D tree (8223D368 → 8223D238 or 8236EB58): at each node,
     compare (point · plane normal) − plane distance with 0; **≥ 0 goes to the
     front child**, < 0 to the back child. The walk ends at a terminal value: the
     special value −1 means "outside"; anything else is a leaf index (low 23 bits).
   - If the result is −1: remember this BSP and continue with the next one.
   - Otherwise the point is "inside some BSP". Because high-word value 0x8 is set,
     the instanced-geometry pieces registered in that leaf are visited with
     82569F08, which returns false in all cases (its only exit returns 0), so they
     never change the answer.
3. Objects are never tested (gated by low-word bit 0, clear).
4. Result: **true** only if no loaded BSP returned a leaf and at least one BSP was
   queried; **false** if any BSP contains the point in a leaf, or if no BSP is
   loaded.

What a Halo 3 query must return to reproduce this: the same rule evaluated on
the loaded map's structure BSP 3D trees — "outside" exactly when every loaded
structure BSP's 3D tree classifies the point into its outside region, using
"on the plane counts as front"; instanced geometry, objects, Forge pieces, kill
volumes and soft barriers must have no effect.

#### A.9.2 Obstruction ray (824F5E28 → 82417550, request type 27, same mask)

Established from the code:

1. The request is cast as a Havok world ray (82417550 builds a ray collector with
   82416438 and 824169F8 and casts it through 824A9D68). The collector is bound
   to the collision-filter configuration found through the globals tag
   (globals root +1984 → that tag's +16), i.e. **map data**, combined with the
   request's type 27 as its query layer.
2. Havok returns candidate hits sorted by distance. The nearest non-object hit
   (structure surface) is accepted by 82416AD0 when its shape's user-data class is
   1 (structure); it becomes a hit of category 3 with its fraction and point.
3. Each candidate **object** hit (82416DF8), nearest first and only while nearer
   than the current best:
   - The high-word values 0x04000000 and 0x02000000 (physics-instance object
     options) are clear, so objects take the plain path.
   - The high-word value 0x20000000 (a length test) is clear.
   - The object must pass an object check (82271460, not followed) and is tested
     with the request's exclusion list (request +36: the held object and the
     monitor, A.4), which is passed into the object test.
   - The object's own collision model is ray-tested exactly (82416120 →
     82415E80) with surface-test flags built from high-word bits:
     0x1000 → flag 1, 0x2000 → flag 2, 0x4000 → flag 4, 0x8000 → flag 8,
     0x10000 → flag 16, 0x20000 → flag 32; if neither flag 1 nor flag 2 results,
     both are set. With this mask the flags are exactly **1**.
   - Flag 1 alone means "test one facing only" (the code treats 1 and 2 as a pair
     that defaults to both), i.e. only surfaces whose front faces the ray start
     (the focus point) can block. Flags 4, 8, 16, 32 are clear, so two-sided,
     invisible and breakable surfaces are **not** ignored, and the test does not
     stop early.
4. Hit = the nearest accepted structure or object hit; the fraction is along the
   focus → camera segment.

Not determinable from the code alone (see R9 in the status table): which body
classes Havok lets layer 27 see. That is decided by the collision-filter tables
in Ravine's map data (the tag reached in step 1), which have not been extracted.
Also, the polarity of flag 1 (front-facing versus back-facing) is inferred from
the paired-default structure in 82416120 and the Halo naming convention, not from
the per-triangle test itself (82415E80 was not followed into the model-geometry
traversal).

What a Halo 3 query must return to reproduce this, as far as established: the
nearest intersection along the segment with (a) structure BSP surfaces and (b)
object collision models that layer 27 sees, excluding the held object and the
monitor, counting only surfaces facing the ray start, and counting two-sided,
invisible and breakable surfaces; on a hit it returns the fraction and point.

#### A.9.3 Maths helpers

- **Arcsine** (82226398), double precision, coefficients at 8332E648
  (off 0x132E648): for |t| ≤ 0.5, g = t², y = |t|, base 0; otherwise
  g = (1 − |t|) × 0.5, y = −2·√g, base π/2. Result = base + y + y·g·P(g)/Q(g)
  with P(g) = (((p4·g + p3)·g + p2)·g + p1)·g + p0 and
  Q(g) = ((((g + q4)·g + q3)·g + q2)·g + q1)·g + q0, sign of t restored; t = 0
  returns 0. p0…p4 = −27.368494524164255, 57.20822787789173, −39.68886299750488,
  10.152522233806463, −0.6967457344735065; q0…q4 = −164.2109671449856,
  417.14430248260413, −381.8630336175015, 150.95270841030606,
  −23.823859153670238. The caller rounds the result to single precision.
- **Sine** (82265C30), double precision: argument reduction by multiples of π,
  odd polynomial of degree 17 (coefficients at 8332E6C8 (off 0x132E6C8)), result
  rounded to single by the caller. For θ = 0x3E32B8C2 the result is 0x3E31D0D4.
- **Square root, division, products**: hardware single precision (fsqrts,
  fdivs, fmuls, fused multiply-add with one rounding) as noted per step.
- Arctangent (8229D260, used for the heading in A.7) and the matrix → quaternion
  step (8229E900) were not re-expressed; they are standard functions evaluated in
  single precision (see the status table, R11).


---

## Part B — inventory of Halo 4 data loaded at runtime

### B.0 What the runtime loads, and from where

`Load()` in advanced_forge.cpp looks for the folder `advanced-forge` beside the
executable (`C:\X360\OpenH3M\advanced-forge\` in the installed build), unless the
`halo3mp_advanced_forge_data` setting names another. It reads, in order:

1. `isolated\markers.bin` (B.4) — required, must be AFM3.
2. `isolated\marker-material.bin` (B.5) — required.
3. Constructs the bridge (forge_bridge.cpp, `Bridge::Bridge`), which reads
   `h4-image.bin` (B.1), `isolated\forge-globals.bin` (B.6),
   `isolated\camera-settings.bin` (B.2) and `isolated\camera-pitch-function.bin`
   (B.3).

The build (`OPENH3M_ADVANCED_FORGE`) copies these files from
`...\work\h4-forge-research\` next to the executable; it also compiles
`forge_original.cpp` and `forge_bridge.cpp` into the program.

Classification used below:

- **(1) Tuning numbers** — plain values a fresh implementation can state as its
  own choices.
- **(2) Per-piece magnet anchor data.**
- **(3) Halo 4 program code, layout or graphics** — must be replaced entirely.

### B.1 `h4-image.bin` — class (3)

- Format: raw decoded Halo 4 executable image (code + data), 49,512,448 bytes
  (0x2F38000), loaded byte-for-byte at guest 0x82000000 in a private 4 GB
  reservation. SHA-256
  `1f7d0f7723001c819e0f0d4a7e534a9ca908c3a0dc1d9c7dfd80454830d1a860`.
- Origin: Halo 4 Disc 1 `default.xex` (title 4D530919; input hash recorded in
  `C:\Programming\GitHub\OpenH3M\tools\h4-forge\README.md`).
- Every one of the 157 recompiled Halo 4 functions reads constants, tables,
  pointers and global state from it. Specific items the bridge itself reads or
  rewires:
  - rotation-step table 833F195C (off 0x13F195C): 0, 90, 45, 30, 15, 5 degrees by
    rotation-snap mode 0–5 (class 1 values, but stored in H4 layout);
  - degrees-to-radians 82128A20 (off 0x128A20), radians-to-degrees 82128B50
    (off 0x128B50) = 57.29578, identity basis 82125148 (off 0x125148);
  - lifecycle event name strings at 82131288 / 82131298 / 821312B0
    ("forge_mode_init", "forge_mode_pickup_item", "forge_mode_drop_item");
  - Halo 4 global pointer slots the bridge redirects to private records:
    8405D340 (globals root), 8405D33C, 8420FF20, 835B6A50 (tag table),
    83625160, 8407F34C (runtime camera obstruction block), plus TLS-style records
    in the low private arena;
  - zero-filled Halo 4 runtime globals that the code reads as-is (e.g. bytes at
    8407EFFB and 8407F008 read by 8244A8D8; the camera runtime block at 8407F2B0
    before start-up import).
- Not a source of usable tuning: several runtime blocks in it are zero-filled and
  only become meaningful after the start-up routines in B.7 run.

### B.2 `isolated\camera-settings.bin` — classes (1) and (3)

- Format: 216 bytes, big-endian, the Halo 4 globals "camera" block
  (`CameraBlock`, size 0xD8). SHA-256
  `6d3e00c453092e35076caf8584c166110165100c14b9134d0aba837f27e4d62d`.
- Origin: `ca_forge_ravine.map` (Disc 2), globals tag `matg` at
  BD922814, camera block pointer BD7A7290 (globals +252 count / +256 pointer),
  extracted by `C:\Programming\GitHub\OpenH3M\tools\h4-forge\extract_camera_curve.py`.
- Loaded to private 0x190000; the bridge rewrites its function data pointer to
  0x190100 and runs the original importer 824BFE90 (B.7), which copies bytes
  +36…+215 (180 bytes) into the runtime camera block 8407F2B0 wherever that block
  still equals its baseline.

| Off | Field (Gen4 schema) | Value | Used by Forge path? |
| --- | --- | --- | --- |
| 0 | default unit camera track (tag ref `trak`, datum A8D83609) | — | no (class 3 reference) |
| 16 | pitch-to-vertical-offset function (data ref: size 84, cache pointer BD7A723C) | see B.3 | **yes** (A.2 step 5) |
| 36 | field of view (deg) | 78 | computed by 822E15E0 but not consumed |
| 40 | yaw scale | 1 | no |
| 44 | pitch scale | 1 | no |
| 48 | forward scale | 2.25 | no |
| 52 | side scale | 2.25 | no |
| 56 | up scale | 2 | no |
| 60 | transition time (s) | 1.5 | no |
| 64 | falling-death transition time | 0.7 | no |
| 68 | initial distance | 3.2 | no |
| 72 | final distance | 1.6 | no |
| 76 | dead-cam Z offset | 0.45 | no |
| 80 | dead-cam max elevation (rad) | 0.26 | no |
| 84 | dead-cam movement delay | 0.3 | no |
| 88 | time to auto-switch to orbiting | 2 | no |
| 92 | ignore stick time | 2 | no |
| 96 | ignore button time | 2 | no |
| 100 | dead-camera min falling velocity | 0.05 | no |
| 104 | maximum boost speed | 5 | no |
| 108 | time to maximum boost | 0.5 | no |
| 112 | boost function (short) | 0 (linear) | no |
| 116 | zoomed field of view | 20 | no |
| 120 | zoomed look speed | 0.5 | no |
| 124 | bounding sphere radius | 0.2 | no |
| 128 | flying-cam movement delay | 0.3 | no |
| 132 | zoom transition time | 0.5 | no |
| 136 | vertical movement time to max speed | 1.5 | no |
| 140 | vertical movement function (short) | 3 (late) | no (also never imported, see B.7) |
| 144 | survival switch time | 0 | no |
| 148 | minimum distance | 1 | no |
| 152 | maximum distance | 2.5 | no |
| 156 | orbit-cam movement delay | 0.3 | no |
| 160 | orbit-cam Z offset | 0.45 | no |
| 164 | orbit-cam min elevation (rad) | −0.1 | no |
| 168 | orbit-cam max elevation (rad) | 0.78 | no |
| 172 | max playback speed | 5 | no |
| 176 | fade-out time | 0.3 | no |
| 180 | fade-in time | 0.3 | no |
| 184 | enter-vehicle transition | 0.55 | no |
| 188 | exit-vehicle transition | 0.5 | no |
| 192 | obstruction: cylinder fraction | 0 | **yes** (A.5.1) |
| 196 | obstruction: test angle (rad) | 0.17453292 (10°) | **yes** (A.5.1) |
| 200 | obstruction: max inward accel | 4 | no |
| 204 | obstruction: max outward accel | 1 | no |
| 208 | obstruction: max velocity | 10 | no |
| 212 | obstruction: return delay (s) | 0 | **yes** (A.5.3) |

"No" means: not read by any Forge path specified in sections 01–05. Other
recompiled functions might read the runtime block; see Open questions.

**Runtime obstruction block 8407F34C** (runtime camera block 8407F2B0 + 156,
six floats). The only writer found in the whole generated program is the
importer 824BFE90 (called from 82396170, the per-map globals set-up; its address
also appears in the function table at 821796E0). It runs when a map loads and
copies camera block +36…+215 into 8407F2B0…+179, field by field, whenever the
runtime value still equals the 180-byte baseline at 84E0AF18 (the baseline is
zero before the first import and is refreshed to the runtime values after each
import). Both start zero in the image, so after loading Ravine the six values
are exactly the tag's: cylinder fraction 0.0 (0x00000000), test angle
0.17453292 rad (0x3E32B8C2), max inward accel 4.0, max outward accel 1.0, max
velocity 10.0, return delay 0.0. 8244AF48 copies all six each tick; only
+156 (cylinder fraction), +160 (test angle) and +176 (return delay) are read.
No other writer exists, so these are the values in every Ravine session.

Classification: the four used values (pitch curve aside) are class (1): a fresh
implementation can choose its own cylinder fraction, cone angle and return delay.
The unused 170+ bytes need not be carried. The tag reference and cache pointer are
class (3).

### B.3 `isolated\camera-pitch-function.bin` — class (1) values in a class (3) encoding

- Format: 84 bytes, big-endian, a Halo 4 "mapping function" blob, evaluated only
  by the original evaluator 8226CD10. SHA-256
  `879c90d4b91430d71a28f61373ef7304f2d39b990896b9dd665d1c107158555d`.
- Origin: Ravine globals camera block +16 data reference, payload at cache
  address BD7A723C (extract_camera_curve.py).
- Loaded at private 0x190100.
- Decoded (Round 2 R4, from evaluators 8226CD10 → 82313E90 → 82285AD0):
  - header: function type 8 (piecewise), flags 0x34 (bit 4 = clamp the inner value
    to [0, 1]; the blend and extra-clamp flags are off), output range −1 to +1;
    the 0.001/0.002 words belong to a flag that is off.
  - two cubic segments y = a·x³ + b·x² + c·x + e; the first segment whose upper
    bound is ≥ x is used:
    - x ≤ 0.50135: a 3.96276, b −1.98673, c −1.0, e 1.0;
    - x > 0.50135: a 8.02747, b −18.07410, c 12.06579, e −2.01916.
  - output = −1 + 2 × clamp(y, 0, 1).
- Meaning: maps the normalised relative pitch x (A.2 step 5) to a multiplier of
  the held object's definition radius; the camera is moved along view-up by that
  many radii.
- **Exact data to re-express** (Round 3). Single-precision values, big-endian hex:

| Item | Value | Hex |
| --- | --- | --- |
| output minimum | −1.0 | BF800000 |
| output maximum | 1.0 | 3F800000 |
| segment 1 upper bound | 0.50134998 | 3F005879 |
| segment 1 a, b, c, e | 3.9627557, −1.9867272, −1.0, 1.0 | 407D9DCA, BFFE4D14, BF800000, 3F800000 |
| segment 2 upper bound | FLT_MAX | 7F7FFFFF |
| segment 2 a, b, c, e | 8.0274725, −18.074102, 12.065789, −2.0191586 | 41007087, C19097C3, 41410D79, C00139E5 |

- **Exact evaluation** (each step rounded to single precision; "fused" means one
  rounding of the exact a·b + c):
  1. Pick segment 1 if x ≤ 0.50134998, else segment 2.
  2. x2 = x·x; cx = c·x; x3 = x2·x; t = fused(b·x2 + cx); t = fused(x3·a + t);
     y = t + e.
  3. If y ≤ 0 then y = 0; else if not (y < 1) then y = 1.
  4. out = fused((max − min)·y + min) = fused(2·y − 1).
  5. lift = definition_radius × out (single multiply); the offset is
     (0, 0, lift) in the view basis, i.e. view-up × lift.
- **Input x exactly** (8244B758): t = clamp(D.z − h, −1, 1) in single precision;
  a = asin(t) rounded to single (A.9.3); x = (−a + 1.5707964 (0x3FC90FDB))
  rounded, times 0.31830987 (0x3EA2F983) rounded; clamp x to [0, 1].
- Samples by x (exact outputs of the steps above):

| x | out | out (hex) |
| --- | --- | --- |
| 0.00 | +1.0000000 | 3F800000 |
| 0.05 | +0.8910570 | 3F641C50 |
| 0.10 | +0.7681910 | 3F44A82A |
| 0.15 | +0.6373458 | 3F232918 |
| 0.20 | +0.5044658 | 3F0124AC |
| 0.25 | +0.3754952 | 3EC040E8 |
| 0.30 | +0.2563779 | 3E8343F8 |
| 0.35 | +0.1530582 | 3E1CBB48 |
| 0.40 | +0.0714800 | 3D926420 |
| 0.45 | +0.0175877 | 3C901400 |
| 0.50 | −0.0026747 | BB2F4A00 |
| 0.55 | −0.0296392 | BCF2CE00 |
| 0.60 | −0.1048555 | BDD6BE80 |
| 0.65 | −0.2163181 | BE5D8280 |
| 0.70 | −0.3519855 | BEB43770 |
| 0.75 | −0.4998183 | BEFFE830 |
| 0.80 | −0.6477742 | BF25D488 |
| 0.85 | −0.7838101 | BF48A7C8 |
| 0.90 | −0.8958874 | BF6558E0 |
| 0.95 | −0.9719634 | BF78D298 |
| 1.00 | −0.9999986 | BF7FFFE8 |

- Samples by t = D.z − h (end to end, including the arcsine step):

| t | x | out | out (hex) |
| --- | --- | --- | --- |
| −1.0 | 1.0000000 | −0.9999986 | BF7FFFE8 |
| −0.9 | 0.8564337 | −0.7998285 | BF4CC190 |
| −0.8 | 0.7951673 | −0.6338010 | BF2240C8 |
| −0.7 | 0.7468166 | −0.4902759 | BEFB0570 |
| −0.6 | 0.7048328 | −0.3659363 | BEBB5C00 |
| −0.5 | 0.6666667 | −0.2594471 | BE84D640 |
| −0.4 | 0.6309898 | −0.1704350 | BE2E8680 |
| −0.3 | 0.5969867 | −0.0991759 | BDCB1CC0 |
| −0.2 | 0.5640942 | −0.0464749 | BD3E5C80 |
| −0.1 | 0.5318843 | −0.0136728 | BC600400 |
| 0.0 | 0.5000000 | −0.0026747 | BB2F4A00 |
| +0.1 | 0.4681157 | +0.0060494 | 3BC63A00 |
| +0.2 | 0.4359058 | +0.0296323 | 3CF2BF80 |
| +0.3 | 0.4030133 | +0.0673885 | 3D8A0300 |
| +0.4 | 0.3690102 | +0.1191580 | 3DF40920 |
| +0.5 | 0.3333333 | +0.1853758 | 3E3DD328 |
| +0.6 | 0.2951672 | +0.2672966 | 3E88DB18 |
| +0.7 | 0.2531833 | +0.3675549 | 3EBC3028 |
| +0.8 | 0.2048327 | +0.4917347 | 3EFBC4A8 |
| +0.9 | 0.1435663 | +0.6544216 | 3F27882C |
| +1.0 | 0.0000000 | +1.0000000 | 3F800000 |

  The tables were computed offline from the decoded data with exact
  single-precision rounding. The arcsine step used a correctly rounded asin; the
  original's double-precision approximation (A.9.3) agrees to within its double
  accuracy before the final rounding.
  Note: at level (t = 0) the lift is slightly negative (−0.0027 radius), and at
  straight down it is −0.9999986, not exactly −1.
- A fresh implementation may store this in its own representation (for example
  the two cubic segments above, or a dense table), but must produce these values.

### B.4 `isolated\markers.bin` — class (2), with class (3) metadata

- Format (little-endian host order for the wrapper fields):
  - header: magic "AFM3", record count (u32) = **129**; file 61,032 bytes.
  - per record: map ID (u32), palette object datum (u32), editor query radius
    (f32), anchor count n (u32, 1–32), fixed-release flag (u32, 0/1);
    then n anchors × 28 bytes (position x, y, z; quaternion x, y, z, w; f32);
    then n Halo 4 marker definition records × 48 bytes (big-endian, Gen4
    `RenderModelMarkerBlock`): region index (s8), permutation index (s8), node
    index (u8), flags (u8), translation (3 f32), rotation quaternion (4 f32),
    scale (f32), direction (3 f32).
  - The loader rejects files where a definition's first seven floats differ
    bit-for-bit from the anchor pose, non-unit quaternions, non-positive radius,
    duplicates or trailing bytes.
- Contents summary:
  - Map IDs: 1730 (40 records) and 1731 (89 records); 769 anchors total.
  - Anchors per piece: 2 (17 pieces), 3 (13), 4 (26), 5 (11), 6 (8), 7 (2), 8 (29),
    9 (5), 10 (12), 11 (2), 12 (2), 16 (2).
  - Fixed-release flag set on 125 of 129 (from the H3 physics model: every body
    is motion type 5 and the palette entry does not override it).
  - Query radius 0.727–10.891: computed from our H3 tag bounding sphere enclosed
    about the object origin, or the farthest anchor — class (1)-like, our own.
  - Definition metadata is uniform: region −1, permutation −1, node 0, flags 1
    (has node-relative direction), direction (1, 0, 0), scale 0.1 on 759 anchors
    and 0.76787 on 10 (Arch Brace, both maps).
  - Effect of those fields (Round 2 R10): the marker builder 8259E9A8 reads the
    region and permutation (to skip markers of permutations not present) and the
    node index (to place the marker on its node); it copies the scale into the
    output record (+108) and never reads the flags byte or the direction. No
    function in the extraction reads output +108. This agrees with
    `C:\Programming\GitHub\OpenH3M\tools\h4-forge\spec\01-magnets.md`.
    A fresh implementation needs only position, orientation and (for pieces with
    several nodes or permutations) node/permutation membership.
- Origin: produced by
  `C:\Programming\GitHub\OpenH3M\tools\h4-forge\export_bindings.py` from the
  staged H3 Forge maps (palette, bounds, physics) plus the Halo 4 Ravine cache
  render models' `sandbox_magnet` marker group (string ID 0x193), read by
  `source_marker_data.py`. The 48-byte definitions are the Halo 4 records with
  their position/rotation replaced by our adapted pose; the other bytes
  (region/permutation/node/flags/scale/direction) are Halo 4's.
- Runtime use: positions/rotations become live marker matrices on the host
  (`MakeMarker` in advanced_forge.cpp); the 48-byte definitions are passed to the
  original marker builder 8259E9A8 through `Bridge::BuildMarkers`, which returns
  112-byte Halo 4 marker records for the magnet code.

**Anchor provenance per piece** (from
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\marker-bindings.json`,
`anchor_frames.json`, `anchor_completion.json`, `anchorless_policy.json`):

1. **Halo 4 anchors, unchanged coordinates (1 piece):** Ramp, 1x2, Shallow
   (← fw_unsc_c_ramp_1x2_shallow).
2. **Halo 4 anchors adapted to our frame (81 pieces, 117 records):** the Halo 4
   marker positions and orientations are kept as the source and mapped by a
   reviewed per-piece transform in `anchor_frames.json` (yaw, translation,
   optional axis or horizontal scale, Y mirror, and snapping to measured
   construction planes/levels or extrusion/radial profiles of our Reach/H3 piece,
   by `anchor_frames.py`). The anchor *set* and roles are Halo 4's; the final
   numbers are fitted to our geometry. Pieces: Antenna, Arch Brace, Arena Wall,
   Arena Window, Bank 1x1/1x2/2x1/2x2, Base Round, Base Strut, all Block variants
   (2x2 Short, 1x1 Tall, 1x1 Flat, 1x1 Short, 1x1 Tall and Thin, 1x2, 1x4,
   2x1 Flat, 2x2, 2x2 Flat, 2x2 Tall, 2x3, 2x4, 3x1 Flat, 3x3, 3x3 Flat, 3x3 Short,
   3x4, 4x4, 4x4 Flat, 4x4 Tall, 5x1 Short), Brace, Brace Large, Bridge Diag,
   Bridge 2x1/2x2/2x3/2x5, Bunker Covered/Full/Low/Stair, Column, Corner 2x2,
   Corner 45 Degrees, Corner 4x4, Cover 2, Crenel Full, Crenel Notch, Cylinder
   Big/Small, Dish, Dish Antenna, Dish Door, Door 2, Landing Pad, Platform Ramped,
   Platform Y, Platform Y Large, Pyramid, Railing Long/Medium/Small, Ramp 1x2,
   Ramp 2x2, Ramp Bridge Large/Medium/Small, Ramp Stunt, Ramp XL, Room Double,
   Room Triple, Staircase, Teleport Frame, Tower, Walkway Large, Wall Curve Short,
   Wall 2x2, Wall Double, Window Double.
3. **Halo 4 anchors re-fitted to our geometry (7 pieces, 11 records):**
   `complete_anchor_transforms.py` maps Halo 4 points through an affine fit of
   Halo 4 bounds to our piece's bounds, then either projects each onto our
   triangles or replaces it with a construction point we authored:
   - only projected (no authored replacements): Tower 3 Story (10), Tower Tall
     (10), Tunnel Long (10);
   - partly authored: Walkway Small Cover (7 of 9 authored);
   - fully authored positions: Ramp Circular Small (5 of 5), Ramp Circular Large
     (5 of 5), Man Cannon (2 of 2; the affine-mapped Halo 4 positions are kept as
     the "reference").
   Orientations come from the Halo 4 markers through the same fit.
4. **Computed purely from our geometry, but excluded (4 pieces):** Radio
   Antennae, Weapon Holder, Glass Sail, Sniper Nest. Profiles exist in
   `anchor_completion.json` (supporting-plane anchors with no Halo 4 source), but
   the user decision of 2026-11-12 disables their magnets; they are not in
   markers.bin (6 report rows).
5. **No anchors by policy (24 labels):** pieces whose Halo 4 counterpart has no
   magnet markers — Grid Object, Fusion Coil, Pallet, Barricade, Shield Door
   Large, Kill Ball, Golf Ball, Tin Cup, Blue/Red Light, the six screen FX, and
   the eight Rock pieces.

Replacement guidance: every record's metadata bytes and the anchor roles of
groups 1–3 derive from Halo 4 object data. A fresh implementation must author
its own anchors from our piece geometry for all 89 pieces; group 3's authored
construction points (in anchor_completion.json evidence) are our own and are the
only anchor values not derived from Halo 4 coordinates.

### B.5 `isolated\marker-material.bin` — class (3)

- Format: little-endian header 20 bytes: magic "H4MP", version 3, program 0
  size 12,132, program 1 size 12,496, pixel payload 1,442,816; then the two
  programs, then the pixels. Total 1,467,464 bytes. SHA-256
  `95324a1d60765e04d57767424bb16addcbed92aa18c0f37266ef708ac5416f64`.
- The two programs are D3D compute shaders (cs_5_0), non-multisampled and
  multisampled builds of the same source, compiled offline by
  `compile_marker_material.cpp`. Their source (`pack_marker_material.py`)
  contains **pixel shader microcode of two Halo 4 particle materials
  (indices 331 and 16) translated to HLSL**, their original near/far fade
  blocks, and constants from the effects `objects\levels\forge\fx\ca_fw_mag_01a`
  (ring layer) and `ca_fw_mag_01b` (rays layer).
- Pixel payload: five decoded Halo 4 bitmaps, RGBA8, concatenated:
  ring_glow 256×256 (`fx\bitmaps\2d\shapes\ring_glow`), grad_bishop_glow_red
  256×1, plasma_clouds_128_a 128×128, plasma_clouds_128_b 128×128 (both
  `fx\reach\bitmaps\plasma\...`), radial_rays_01 512×512
  (`fx\bitmaps\2d\glows\radial_rays_01`).
- Embedded tuning: fade near range 0.2016, near cutoff 0.4032, far range 2.0,
  far cutoff 23.0 (identical for both layers); these four can be restated as our
  own values. Everything else in the file is Halo 4 graphics and must be replaced
  with original artwork and shaders.
- Runtime use: handed to the scene-marker renderer, which draws a ring + rays
  billboard at each visible magnet anchor (advanced_forge.cpp around
  `QueueSceneMarkers`).

### B.6 `isolated\forge-globals.bin` — classes (1) and (3)

- Format: 88 bytes, big-endian, the Halo 4 `forge_globals` tag (`forg`, 0x58).
  SHA-256 `0aa93e946f5ba028c26b21e4d892dd6996512c302e5eea87221e39756c9777a7`.
- Origin: `ca_forge_ravine.map`, found by group `forg`
  (`C:\Programming\GitHub\OpenH3M\tools\h4-forge\extract_config.py`).
- Loaded at private 0x52000 as tag slot 0; the bridge requires +0x1C = 0x193.

| Off | Field | Value | Class | Consumer (see sections 01/03) |
| --- | --- | --- | --- | --- |
| 0x00 | Forge colours block (count 8, H4 cache pointer BF95ECE0) | — | 3 | not used |
| 0x0C | magnet effect scenery (tag ref `efsc`, datum B4484110) | — | 3 | not used |
| 0x1C | parent magnet marker name (string ID) | 0x193 (`sandbox_magnet`) | 3 | marker group selection |
| 0x20 | child magnet marker name (string ID) | 0x2A6BC | 3 | no reader found (Round 2 R8) |
| 0x24 | throttle sensitivity | 0.5 | 1 | magnet suppression while moving (82582178) |
| 0x28–0x38 | five magnetism factors | 0.1, 0.25, 0.5, 0.75, 1.0 | 1 | magnet range × held radius, by sensitivity |
| 0x3C | magnetism angle (deg) | 45 | 1 | magnet alignment |
| 0x40 | magnet offset influence | 0.75 | 1 | magnet scoring |
| 0x44 | object grab range | 7.5 | 1 | grab |
| 0x48 | default focal distance | 7.5 | 1 | hold distance (82452AD8) |
| 0x4C | minimum focal distance | 2 | 1 | getter 82452B48, used only by the alternate held path 82451FC0 (Round 2 R8) |
| 0x50 | maximum focal distance | 22 | 1 | hold distance (82452BB8) |
| 0x54 | focal distance multiplier | 5 | 1 | hold distance (82452C28) |

The code's fallbacks when a field is ≤ 0.0001 (5 for default distance and
multiplier, 22 for maximum, 0.5 for throttle) live in h4-image.bin and are class (1).

### B.7 Everything in the runtime that executes Halo 4 code

The runtime never interprets PowerPC bytes from h4-image.bin. All Halo 4
behaviour runs as **statically recompiled C** (157 functions, compiled into the
program as library `h4_forge_original` from `forge_original.cpp`), operating on
a private guest memory that holds h4-image.bin as its data. Indirect calls are
redirected to a host dispatcher (`controller_dispatch`), and 41 world-facing
functions are replaced by host boundaries listed in
`C:\Programming\GitHub\OpenH3M\tools\h4-forge\extract_forge.py` (`BOUNDARIES`).
That generated code is itself Halo 4 program logic and is class (3).

Bridge methods (forge_bridge.cpp) and the top-level recompiled Halo 4 functions
each one calls directly. advanced_forge.cpp reaches these through several bridge
references; which host path calls each method is not listed here.

| Bridge method | Halo 4 function(s) called directly |
| --- | --- |
| constructor | 824BFE90 (camera import), 83292E30 + 83292E50 (query mask) |
| MagnetQueryRadius | 824499A8 |
| BuildMarkers | 8259E9A8 |
| CollisionGroupAllows | 82D813F8 |
| UpdateSelectionRay | 8244C740 |
| PrepareActiveBipedTarget | 8257FB98 |
| ConvertMonitorView | 823FC348 |
| UpdateMonitorObstruction | 824F5CF0 |
| ControlBody | 82C969B0, 8249B418 |
| CompensateAttachmentPose | 8228ACE8, 82265C30, 82265E28, 82300D40, 821E0550, 822864E0, 8226BFC0 |
| InitializeHeldEditorState | 82449DD8 |
| SelectHeldObject | 82449ED8 |
| NotifyObjectDeleted | 82449ED8, 8244A118 |
| PrepareSpawnPlacement | 8228ACE8 |
| ConstrainGrabPose | 82282580 |
| ConsumeManipulationInput | 82368CE0 |
| RotateHeld | 8244A7D0 |
| ConstrainHeldDistance | 82452738 |
| SelectPhysicsState | 8244A180 |
| TransitionPhysics | 8244A2A0 |
| EditPhysics | 8268C340 |
| CoordinateAngles | 8232F960 |
| CoordinateRanges | 8268AE80 |
| EditCoordinates | 8268AE80, 8268B410 |
| UpdateVisibility | 825826B0 |
| SelectContactResponse | 824863F8 |
| UpdateHeld | 8244A8D8 |
| UpdateMonitorFollow | 8244AF48 (which itself reaches 824BEA10, 824BE840, 824BEB50, 8244B758, 824F5CF0, 824F5F78, 824F5E28, 8221B258, 82452930 boundary and 823FC348) |
| PrepareHeldSubmission | 82451A38 |
| ApplyHeldMagnets | 8244EED8 |
| Evaluate | 82582250, 82582178, 82582AD0 |

ConvertMonitorView and UpdateMonitorObstruction are standalone wrappers; in the
live path the same two functions run inside UpdateMonitorFollow. Methods not
listed (InitializeGrabPlacement, AdvanceHeldPlacement, TransitionHeldPhysics,
ResolveSceneryContact, ResolveMonitorContact) make no direct call matched by the
search used here; whether they reach recompiled code indirectly was not checked.

Start-up routines worth noting:

- 824BFE90 keeps a 180-byte baseline (84E0AF18) of the runtime camera block
  (8407F2B0) and, per field, imports the tag value when the runtime still equals
  the baseline. It compares the boost-function short (+76) twice and never imports
  the vertical-movement-function short (+104); irrelevant to Forge.
- 83292E30 writes 0x0000100900000000 into 845548B0; 83292E50 copies it to
  845548B8. Both words are zero in the image until these run.

---

## Open questions — Round 3 status

Requirement (user, Round 3): the camera must behave exactly as in Halo 4. Every
item below is therefore stated as Halo 4's behaviour; where Halo 3 supplies a
query, A.9 states what it must return.

| # | Question | Status |
| --- | --- | --- |
| R1 | Focus-point test that gates obstruction | RESOLVED, exact rule in A.9.1 |
| R2 | Who sets the stored pitch (editor +276) | RESOLVED (A.4 step 13) |
| R3 | Writer of the cached position that caps prediction | RESOLVED within the Forge functions (A.3) |
| R4 | Lift curve | RESOLVED, exact data and samples in B.3 |
| R5 | View angle convention | RESOLVED (A.7), including the exact values the view must receive |
| R6 | Other readers of the runtime camera block | RESOLVED: other Halo 4 camera modes; none on the Forge path |
| R7 | Meaning of the retained distance | RESOLVED (A.4 step 12, A.6) |
| R8 | Minimum focal distance, child marker name | Minimum distance RESOLVED (only the alternate path 82451FC0); child name UNRESOLVED (no reader found) |
| R9 | Which surfaces block the obstruction rays | PARTLY RESOLVED: request flags, surface-test flags, exclusions, hit selection (A.9.2) and, in Round 4, Ravine's layer-27 filter row (which layers block). UNRESOLVED: which layer each surface/object kind is assigned, and the facing polarity inside 82415E80 |
| R10 | Marker scale/direction/flags | RESOLVED: no effect (B.4) |
| R11 | Exact arctangent, matrix → quaternion and sine coefficients | Sine and arcsine RESOLVED (A.9.3); arctangent 8229D260 and 8229E900 not re-expressed (standard maths; last-bit agreement not verified) |
| R12 | Runtime obstruction settings at 8407F34C | RESOLVED: writer 824BFE90 at map load, values in B.2 |

**R1.** See A.9.1. The obstruction rays run only when the focus point is outside
the world by that rule; in ordinary use they never run and the monitor looks at
the focus (A.4 steps 4 and 9). The same test with the same mask serves 82451BA8
(piece-out-of-world check).

**R2.** Written only by 82449DD8 (0 at start-up), 82449ED8 (0 on release; on grab
by a local player, the sine of the elevation from the monitor's physics point to
the held object's offset point) and 8244AF48 (relaxation toward 0).

**R3.** Editor +8/+12/+16 = the held object's origin at grab (82449ED8 via
8225EA20). No other writer in the Forge functions; whole-program offset matches
could not be attributed to the editor record and were not counted.

**R6.** About 50 Halo 4 functions address 8407F2B0, mostly other camera modes
(824B81C0–824BCF30 range). On the Forge path only 822E15E0 (field of view,
result unused), 824BE840, 8244AF48 and the importer 824BFE90 read it.

**R8.** Minimum focal distance (+0x4C): getter 82452B48 (fallback 2.0), called
only from 82451FC0, the alternate held path selected by a byte that is zero in
the image with no writer found (section 03, its Q6). There: lower limit =
max(minimum, definition radius + 0.4), upper = min(multiplier × lower, maximum),
after push/pull of 0.3 × input. Child marker name (+0x20): no reader of the Forge
tag's +0x20 among all calls to the globals resolver 82340E60.

**R9.** To settle the rest: extract the collision-filter configuration from
`ca_forge_ravine.map` (globals root +1984 tag, its +16 block, as used by
82416438) and follow 824A9D68's filter callback for layer 27; follow 82415E80
into the per-triangle facing test. Both are static tasks not done in this round.

**R11.** The heading is atan2(f.y, f.x) and the roll term is 0 here; only the
last-bit behaviour of the original arctangent is unverified.

## Round 4: Ravine values

### Source

- Map: `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\disc2-assets\ca_forge_ravine.map`
  (read-only).
- Globals tag `matg` (tag index 5, cache address BD922814) +1972 is a tag
  reference: group `hcfd` (havok_collision_filter), datum B5EC42A3 → tag index
  17059, cache address BDFAD5FC, file offset 0x6D0A5FC. This is the tag the ray
  query binds to (globals +1984 datum, then the tag's +16 block, A.9.2 step 1).
- Layout (TagTool Gen4 `HavokCollisionFilter.cs`, size 0x110): +0 "Groups" block
  (31 entries × 4 bytes), +16 the Havok group-filter structure (0x100 bytes). In
  the group filter: +32 type = 2, +48 next free system group = 0, **+52 the
  32-row collision lookup table** (one 32-bit word per layer). SHA-256 of the
  0x110 bytes: `e9510f8addf66d54b99e2fcf9158caff1c4b028bc3ffb4e8df555285342791c8`.
- The Groups block holds the same rows 0–30 without bit 31; its 31 entries
  identify the layers by position. Layer names below are the bit names of the
  schema's `CollisionFilterEnum` (layer n = bit n); they are TagTool's names, used
  for corroboration only.

### How the table is used (rule, no code)

Every Havok body and every ray carries a 32-bit filter word: layer in the low 5
bits, "system group" in the high 16 bits. Two words A and B may collide when:

1. If both share the same non-zero system group: allowed only if their
   sub-system numbers (bits 5–9 of one matched against bits 10–14 of the other,
   either way round) differ in the way Havok's group filter defines; otherwise
   blocked.
2. Otherwise: allowed exactly when bit (layer of B) is set in row (layer of A).

The obstruction ray's word is 27 (layer 27, system group 0), so rule 2 always
applies: **a body can block the ray exactly when bit (body layer) is set in row
27**. The table is symmetric (row a bit b = row b bit a, checked for all pairs).

### The full table (Ravine)

| Layer | Name | Row (hex) |
| --- | --- | --- |
| 0 | Everything | FFFFFFFF |
| 1 | EnvironmentDefault | BF83FC7D |
| 2 | EnvironmentOnly | B0000003 |
| 3 | SmallCrate | BE6203B3 |
| 4 | Crate | BFE2FFFB |
| 5 | HugeCrate | BFE2FFFB |
| 6 | Item | BF6283B3 |
| 7 | Projectile | 8F608379 |
| 8 | Machine | 8FE2FCF9 |
| 9 | EarlyMoverMachine | 8FE2FCF9 |
| 10 | Creature | BE628333 |
| 11 | Biped | BEEA8B33 |
| 12 | DeadBiped | BE608333 |
| 13 | SuperCollidableRagdoll | BE600333 |
| 14 | Ragdoll | BE688333 |
| 15 | Vehicle | BEE2DFF3 |
| 16 | Decal | C0000003 |
| 17 | ForgeDynamicScenery | BFE28F7B |
| 18 | SmallExpensivePlant | 86000001 |
| 19 | TechArtCustom | 86104801 |
| 20 | Proxy | 86080001 |
| 21 | HugeVehicle | 8FC2FFF9 |
| 22 | IgnoreEnvironment | 8EA2FFF9 |
| 23 | CharacterPosture | BE628B33 |
| 24 | ItemBlocker | BE2203F3 |
| 25 | User00 | BFFEFFFB |
| 26 | ZeroExtent | CBFEFFFB |
| 27 | PhysicalProjectile | A7E2FFFB |
| 28 | EnvironmentInvisibleWall | B382FC7F |
| 29 | EnvironmentPlayCollision | BB82FC7F |
| 30 | EnvironmentBulletCollision | C4010001 |
| 31 | (unnamed) | FFFFFFFF |

### Row 27 — camera-obstruction rays (A.9.2)

Row 27 = A7E2FFFB.

- **Can block** (bit set): 0 Everything, 1 EnvironmentDefault, 3 SmallCrate,
  4 Crate, 5 HugeCrate, 6 Item, 7 Projectile, 8 Machine, 9 EarlyMoverMachine,
  10 Creature, 11 Biped, 12 DeadBiped, 13 SuperCollidableRagdoll, 14 Ragdoll,
  15 Vehicle, 17 ForgeDynamicScenery, 21 HugeVehicle, 22 IgnoreEnvironment,
  23 CharacterPosture, 24 ItemBlocker, 25 User00, 26 ZeroExtent,
  29 EnvironmentPlayCollision, 31 (unnamed).
- **Never block** (bit clear): 2 EnvironmentOnly, 16 Decal, 18 SmallExpensivePlant,
  19 TechArtCustom, 20 Proxy, 27 PhysicalProjectile (other rays/bodies of the same
  layer), 28 EnvironmentInvisibleWall, 30 EnvironmentBulletCollision.

Plain meaning for the camera: ordinary level geometry (EnvironmentDefault) and
the level's player-collision surfaces (EnvironmentPlayCollision) block; the
level's **invisible walls and bullet-only collision do not**. Crates of all
sizes, dynamic Forge scenery, machines (doors, lifts), vehicles, bipeds and
creatures (living and dead), ragdolls and items block. Decals, small expensive
plants, tech-art custom bodies and proxies do not. After the Havok filter, the
object and facing rules of A.9.2 step 3 still apply (front faces only; the held
object and the monitor are excluded).

### The world test (A.9.1)

The outside-the-world test uses no Havok filter and no row of this table: it is
a pure walk of the structure BSP 3D trees (A.9.1). Nothing in this tag changes
its result.

### Row 1 and row 26 (for section 03)

Row 1 (EnvironmentDefault) = BF83FC7D. A query or body on layer 1:
- sees: 0 Everything, 2 EnvironmentOnly, 3 SmallCrate, 4 Crate, 5 HugeCrate,
  6 Item, 10 Creature, 11 Biped, 12 DeadBiped, 13 SuperCollidableRagdoll,
  14 Ragdoll, 15 Vehicle, 16 Decal, 17 ForgeDynamicScenery, 23 CharacterPosture,
  24 ItemBlocker, 25 User00, 26 ZeroExtent, 27 PhysicalProjectile,
  28 EnvironmentInvisibleWall, 29 EnvironmentPlayCollision, 31;
- ignores: 1 EnvironmentDefault (level geometry itself), 7 Projectile,
  8 Machine, 9 EarlyMoverMachine, 18 SmallExpensivePlant, 19 TechArtCustom,
  20 Proxy, 21 HugeVehicle, 22 IgnoreEnvironment, 30 EnvironmentBulletCollision.
- Plain meaning: a probe on layer 1 behaves like a piece of level geometry: it
  does **not** see ordinary level geometry, machines, huge vehicles or
  bullet-only collision, but sees crates, Forge scenery, characters, vehicles,
  items, invisible walls and player-collision surfaces.

Row 26 (ZeroExtent) = CBFEFFFB. A query on layer 26:
- sees: 0, 1 EnvironmentDefault, 3–15 (all crates, items, projectiles, machines,
  creatures, bipeds, ragdolls, vehicles), 17 ForgeDynamicScenery,
  18 SmallExpensivePlant, 19 TechArtCustom, 20 Proxy, 21 HugeVehicle,
  22 IgnoreEnvironment, 23 CharacterPosture, 24 ItemBlocker, 25 User00,
  27 PhysicalProjectile, 30 EnvironmentBulletCollision, 31;
- ignores: 2 EnvironmentOnly, 16 Decal, 26 ZeroExtent, 28 EnvironmentInvisibleWall,
  29 EnvironmentPlayCollision.
- Plain meaning: an aim ray on layer 26 hits what a bullet would hit: level
  geometry and bullet collision, every kind of object including plants, proxies
  and tech-art bodies, but **not** invisible walls, player-only collision or
  decals.

Whether section 03's spawn probe and aim ray really use layers 1 and 26 is that
section's finding; this table only gives the rows.

### Still not determined

- **Which layer each kind of thing is placed on.** The table says which layers
  block; it does not say which layer a given BSP surface, Forge piece or object is
  assigned. That assignment is made when bodies are created (from each object's
  physics model and the BSP's collision materials) and was not traced. In
  particular, whether static (fixed) Forge pieces sit on ForgeDynamicScenery (17),
  EnvironmentDefault (1) or another layer is open, and which BSP surfaces are
  marked invisible-wall (28), play-collision (29) or bullet-only (30) depends on
  each surface's material, per level.
- The layer names are TagTool's labels; the behaviour above follows from the row
  bits, not from the names.

## Halo 3 pieces needing freshly authored magnet anchors

All 129 entries in markers.bin need new anchors. They cover 89 pieces; map 1730
is `forge_gulch.map`, map 1731 is `forge_island.map`; numbers are anchors per map.

- On both maps (40 pieces, 80 entries): Antenna (3), Arch Brace (5), Arena Wall
  (9), Arena Window (16), Bank 1x1 (3), Bank 1x2 (3), Bank 2x1 (3), Bank 2x2 (3),
  Base Round (10), Base Strut (7), Brace (6), Bridge Diag (2), Bridge 2x1 (4),
  Bridge 2x2 (4), Bridge 2x3 (4), Bridge 2x5 (4), Bunker Covered (2), Bunker Full
  (4), Bunker Low (2), Bunker Stair (11), Man Cannon (2), Column (8), Cover 2 (5),
  Crenel Full (4), Crenel Notch (4), Cylinder Big (4), Cylinder Small (4), Dish
  (4), Dish Antenna (12), Dish Door (2), Door 2 (10), Room Double (2), Room Triple
  (6), Teleport Frame (4), Tower (5), Tower 3 Story (10), Tower Tall (10), Walkway
  Small Cover (9), Wall Curve Short (8), Wall 2x2 (8).
- On map 1731 only (49 pieces): Block 2x2 Short (8), Block 1x1 Tall (9), Block 1x1
  Flat (8), Block 1x1 Short (8), Block 1x1 Tall and Thin (10), Block 1x2 (8),
  Block 1x4 (8), Block 2x1 Flat (8), Block 2x2 (8), Block 2x2 Flat (8), Block 2x2
  Tall (8), Block 2x3 (8), Block 2x4 (8), Block 3x1 Flat (8), Block 3x3 (8),
  Block 3x3 Flat (8), Block 3x3 Short (8), Block 3x4 (8), Block 4x4 (8), Block 4x4
  Flat (8), Block 4x4 Tall (8), Block 5x1 Short (8), Brace Large (5), Corner 2x2
  (10), Corner 45 Degrees (4), Corner 4x4 (10), Landing Pad (8), Platform Ramped
  (4), Platform Y (6), Platform Y Large (2), Pyramid (5), Railing Long (6),
  Railing Medium (6), Railing Small (6), Ramp 1x2 (3), Ramp 1x2 Shallow (3), Ramp
  2x2 (2), Ramp Bridge Large (2), Ramp Bridge Medium (2), Ramp Bridge Small (2),
  Ramp Circular Large (5), Ramp Circular Small (5), Ramp Stunt (5), Ramp XL (4),
  Staircase (4), Tunnel Long (10), Walkway Large (3), Wall Double (8), Window
  Double (8).

The counts are today's Halo 4-derived anchor counts, given only as a size guide;
a fresh set may use different counts. Not in the list: the four pieces with
magnets disabled by the user (Radio Antennae, Weapon Holder, Glass Sail, Sniper
Nest) and the 24 anchorless pieces in B.4 group 5.

## Round 2 changes

- A.2, B.3: lift curve decoded (two cubic segments) with a sample table and a
  description of its feel.
- A.3: cached position identified as the grab-time object origin.
- A.4: the obstruction test now stated as "focus point outside the world";
  normal-case behaviour (no rays, monitor looks at the focus) spelled out; facing
  and retained-distance notes corrected; where the pitch history is set added.
- A.7: angle convention (heading, pitch, roll; roll always 0 here).
- B.4: marker scale/direction/flags shown to have no effect.
- B.6: minimum focal distance and child marker name consumers.
- Open questions replaced by the Round 2 status table and notes; added the list
  of pieces needing new anchors.

## Round 3 changes

- Requirement changed to "exactly Halo 4": removed every statement that Halo 3's
  own point-in-world test, collision filters or facing path may substitute.
- New A.9: exact outside-the-world rule (BSP tree walk, "on the plane counts as
  front", instanced geometry and objects never count) and what a Halo 3 query
  must return; the obstruction ray's request flags, surface-test flags (exactly
  1), exclusions and hit selection; exact arcsine and sine definitions.
- A.7: the view must receive heading = atan2(f.y, f.x) wrapped to [0, 2π),
  pitch = asin(f.z), roll = 0.
- B.2: runtime obstruction settings at 8407F34C — sole writer 824BFE90 at map
  load; exact values for Ravine.
- B.3: lift curve given as exact single-precision data, exact evaluation order,
  and exact sample tables by x and by D.z − h (with hex values); the "similar
  feel" wording removed.
- Status table replaced by the Round 3 table; remaining unknowns: the Havok
  layer-27 filter (map data) and the facing polarity inside 82415E80, the child
  marker name reader, and the last-bit behaviour of arctangent / matrix-to-
  quaternion.

## Round 4 changes

- Added "Round 4: Ravine values": the havok_collision_filter tag referenced from
  Ravine's globals (+1972), its full 32-row layer table, the filter rule, and the
  plain meaning of row 27 (camera-obstruction rays), plus rows 1 and 26 for
  section 03. The world test is confirmed not to use the table.
- R9 updated: the layer-27 row is settled; the assignment of surfaces and objects
  to layers remains open.


---

# 06 — Magnet placement rules (authoring conventions)

Purpose: the rules Halo 4's designers followed when they placed Forge magnets on construction pieces, written
so that fresh magnet positions can be authored from **our own piece geometry** for the 89 Forge Gulch / Force
Cove pieces (129 entries) listed in `05-camera-and-data.md`. Rules are stated by piece shape. The output of
applying them is a **per-piece magnet table written into the program's source code** (position and frame per
magnet), not a data file. Section 7 gives each magnet as a feature of our piece in our own coordinates; no raw
Halo 4 coordinate tables are reproduced.

**Status (user direction, 2026-11-26): magnetism must work exactly like Halo 4.** Section 7, *Exact per-piece
magnet sets*, is the definition: for each of the 89 pieces it lists every Halo 4 magnet, same count and order,
duplicates and frames included, at the audited location on our piece (MATH-AUDIT.md). Sections 1 to 6 are **background** that explains the
patterns; where they suggest a choice, section 7's exact correspondence overrides it.

Method: analysis only, nothing built or run. Inputs read:
- `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\markers.bin` (129 records, 89 pieces,
  543 distinct anchors after merging the two maps; format in `05-camera-and-data.md` B.4), joined to piece labels
  through `...\isolated\marker-bindings.json`, measured against our own piece bounds and planes in
  `...\isolated\render-planes-all.json`.
- `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\ravine-magnets.json` (Halo 4's original
  `sandbox_magnet` sets, 119 models, 733 anchors) — used only for counts and frame-direction statistics.
- `C:\Programming\GitHub\OpenH3M\tools\h4-forge\anchor_frames.py`, `anchor_frames.json`,
  `complete_anchor_transforms.py`, `export_bindings.py`, the `*_geometry.json` files, `MATH-AUDIT.md`.

The markers.bin anchors are Halo 4's anchor *roles* re-fitted onto our meshes (`anchor_frames.py` only accepts a
mapping when each marker matches one reviewed construction role), so measuring them against our bounds shows the
designers' conventions directly in our pieces' terms. Analysis scripts lived in the session scratchpad and are not
part of the product.

Piece kinds used below (each piece in the data was put in exactly one):

| Kind | Shape test | Pieces in data |
| --- | --- | --- |
| Box | rectangular solid, flat top and bottom (includes thin slabs and square posts) | 22 blocks + Column |
| Wall | vertical slab, two large opposed vertical faces; may have window/door openings or crenels | 9 |
| Polygon floor | flat slab with a non-rectangular footprint (L, Y, chamfered corner, pad) | 6 |
| Ramp / wedge | one sloped walking surface between a low end and a high end; banks (triangular wedges) | 14 |
| Bridge / walkway | thin deck meant to span between two supports, ends are the joints | 8 |
| Railing | low, narrow barrier strip | 3 |
| Round | cylinder, disc, ring or radial part | 8 |
| Structure | enterable building: rooms, towers, bunkers, tunnels, pyramid, covers | 13 |
| Strut / prop-like construction | braces, struts, antenna, frames, gadgets with a base | 7 |

---

## 1. Why the rules look the way they do

These follow from `01-magnets.md` and govern every rule below.

1. **Only position matters.** A snap translates the held piece so that one of its magnets lands exactly on one
   magnet of the target. Rotation is never changed. Any held magnet may pair with any target magnet; the pair
   with the best score (in practice the closest pair) wins.
2. **A magnet is a contact reference point.** Two pieces end up touching flush when the two coinciding magnets
   both lie on the faces that should touch. A magnet set back from the surface by an inset would leave a gap
   (or overlap) of twice the inset. Hence: magnets lie **on** the surface, with zero inset.
3. **Magnet orientation has no effect** on snapping. It is also not visible: our marker renderer draws a
   camera-facing ring and rays at each magnet. The frame convention in section 2 is therefore a tidiness rule for
   authoring, not a behaviour; Halo 4's own data breaks it in places without any consequence.
4. **Coincident duplicates are useless.** Two magnets at the same point with different frames behave as one.
5. **Hard cap 32 magnets per piece**; later ones are ignored.
6. Because the snap radius scales with the held piece's size, small pieces need magnets reasonably close to where
   the player will bring them; sparse sets on big pieces are acceptable.

## 2. Universal rules (all kinds)

**U1 — On the construction surface, zero inset.** Each magnet sits on the plane of the face it belongs to: the
large flat face that defines the piece's size, not on decorative trim. Box pieces: 168 of 179 anchors lie
exactly on two bounding planes at once; all of the rest lie on construction planes just inside a bevelled or
trimmed outline (for example a block whose rim trim sticks out 0.009 beyond its 0.5 face). Measured authoring
noise in Halo 4's own data was at most 0.005 units and was removed; author on the exact plane.

**U2 — Edge midpoints, not corners.** The standard magnet is at the **midpoint of an edge** where a side face
meets a horizontal face (top, bottom or deck). On box pieces 178 of 178 side magnets are exactly at the centre of
the face's width. Midpoints make faces of different lengths centre on each other (a 2-wide block snapped to a
4-wide block lines up centred). Vertical corner edges get nothing (0 of 179 on boxes). Corner points are used
only on one floor piece (section 3.3) and there as coincident duplicates.

**U3 — One magnet per edge, whatever its length.** No piece in the data spaces magnets along a long face. A
5-unit block edge, a 4-unit edge and a 10-unit wall edge each get exactly one, at the midpoint. More than one
magnet at the same height on the same face appears only where the face carries **repeated features**: separate
feet (braces, door posts, cover), separate entrances or lanes (tower, room, ramped platform with three lanes about
1 unit apart, tunnel mouths), or a face split by a step. Rule: one per edge, plus one per distinct contact
feature on that edge.

**U4 — Height tiers.** Where a face is to be joined at more than one height, magnets are repeated straight above
each other on that face. Boxes: every side has two (top edge and bottom edge), 89 vertical pairs on 22 boxes.
Thin decks use the deck level plus a second reference 0.15 below it (bridges, the 45-degree corner, a deck-pad),
rather than the true underside. Walls use bottom edge, mid-height side edges and top edge.

**U5 — Frame convention.** forward (local +X) = outward normal of the face the magnet belongs to, horizontal;
up (local +Z) = the piece's up. In Halo 4's original sets: up = piece up on 710 of 733 anchors (97%), forward
horizontal on 722 of 733 (98.5%), forward straight up or down on the other 11, and never tilted. When the face
itself is horizontal (a top or bottom magnet), forward = ±Z and up = any horizontal piece axis. For a sloped or
curved face use the horizontal component of its outward normal. (Observed convention; section 7 keeps every frame exactly, including the exceptions.)

**U6 — Top and bottom faces rarely get their own magnets.** Only 11 of 733 Halo 4 anchors face up or down.
Stacking works through the edge magnets of U2/U4: a piece's bottom-edge magnet lands on the other piece's
top-edge magnet. A centre-of-top magnet appears only on narrow tall posts (one 1x1 post) and on a few pieces
whose top is the only usable joint (crenel tops and bottoms, antenna and strut feet).

**U7 — Follow the piece's symmetry.** 69 of 89 pieces have a magnet set mirror-symmetric about the piece's own
centre plane in X or Y (36 in both); all 22 boxes are symmetric in both. Asymmetric sets belong to asymmetric
pieces (ramps, banks, round bases cut in half, buildings).

**U8 — Count.** Our 89 pieces: 2 to 16 magnets, median 6. Halo 4 range 1 to 17. Typical totals: boxes 8, walls
8, bridges 4, straight ramps 2–3, railings 6, cylinders 4, buildings 2–11.

**U9 — Walking levels for enterable pieces.** On anything a player walks on or through, magnets sit at the
**floor or deck height** at the outer boundary, not at the piece's overall bottom: cylinder rims at deck height,
tower and room entrances at their floor levels, bridge ends at deck level.

**U10 — No magnets on non-construction pieces.** Halo 4 put none on: natural rock, lights, screen effects,
physics toys (golf ball and cup, kill ball), crates/pallets, fusion coils, barricades, large shield doors, the
grid. User decision: Radio Antennae, Weapon Holder, Glass Sail and Sniper Nest stay magnet-free.

## 3. Rules by piece kind

### 3.1 Box (blocks, slabs, square posts)

- Magnets: the midpoint of each of the **8 horizontal edges** — on each of the 4 side faces, one at the top edge
  and one at the bottom edge, centred across the face width. Total 8.
- Applies at every proportion: flat slabs (0.2 thick), cubes, tall posts (3 high), long bars (5x1). 20 of 22
  boxes in the data have exactly these 8; the square column also has exactly these 8.
- Frames: forward = side face outward normal, up = +Z (177 of 179 outward; the other two are centre points).
- Top/bottom centres: none, except narrow tall posts (side length about 1 or less, height 2.5 or more), which
  add one at the top-face centre (forward +Z), and a post that is thinner than it is wide adds a centre point on
  the top and bottom faces on its thin axis.
- Example: a 2x2x1 block centred on its origin gets (±1, 0, ±0.5) and (0, ±1, ±0.5).

### 3.2 Wall (incl. window walls, door walls, crenels, long arena walls)

- Magnets belong to the **two large faces** (front and back). On each: midpoint of the top edge, midpoint of the
  bottom edge, and midpoint of each vertical side edge (at mid-height). 4 per face, 8 total. 3 of 3 plain/window
  walls follow this exactly; the long arena wall follows it with one duplicate.
- The narrow end faces have no magnets of their own; the side-edge magnets of the large faces do that job (wall
  continues in line when side magnets coincide; walls stand back to back when face magnets coincide).
- Openings do not add magnets on plain window walls (the window wall has the same 8 as the plain wall). A door
  wall adds magnets at the door posts' feet and mid-height posts (10 total).
- Very long walls with a non-rectangular end profile (sloped ends): add the same top/centre/bottom rows at the
  middle of the face and at each end (16 on the one example).
- Crenels (short parapet pieces) use top-centre and bottom-centre (vertical-facing) plus the two ends; a notched
  crenel uses its two end feet and the two raised tops.
- Frames: forward = large-face normal for all 8 (wall and window); one long wall turns its side magnets to face
  along the wall instead.
- Curved walls: same 8 roles, at the arc's two ends on both faces at top and bottom; forward along the end
  tangent.

### 3.3 Polygon floor (L-shapes, Y-shapes, chamfered corners, pads)

- Generalised box rule: **each vertical side of the footprint polygon** gets a magnet at the midpoint of its top
  edge and of its bottom edge (or of its deck edge and a 0.15-below reference). A 5-sided corner floor gets 10.
- Short sides formed by a cut (chamfer or 45-degree face) get magnets like any other side, forward along that
  side's diagonal normal.
- Thin Y-shaped floor: top edges only (6 sides, 6 magnets).
- A large corner floor adds magnets at its outer square corner (as coincident duplicates, one per facing) and at
  deck and underside tiers.
- Large or tiered floors may have only end joints (the large Y-piece has 2, at its two straight ends).

### 3.4 Ramp / wedge (straight ramps, bridge ramps, banks, stunt ramps)

- The joints are the **ends**: at the centre of each end face's width (32 of 39 side magnets on ramps are
  centred).
- Low end: magnet at the bottom edge midpoint, where the slope meets the ground. High end: magnet at the top edge
  midpoint, where the deck meets the end face; a solid wedge also gets the high end's bottom edge midpoint
  (3 magnets: low-bottom, high-bottom, high-top). A thin sloped plate gets only low-bottom and high-top (2).
- Bridge ramps (thin sloped decks with rails): one magnet at each end at **deck height**, nothing else (2).
- Long sides of a ramp get no magnets, except the stunt ramp (all four base edge midpoints plus the high-end top).
- Banks (triangular-footprint wedges): one magnet at the base-edge midpoint of each of the three footprint sides,
  forward along each side's horizontal outward normal (4 of 4 banks, 3 each).
- Platform with an attached ramp: the base of the low end, plus one magnet per lane on the high end (three lanes,
  about 1 unit apart).
- Staircases: one magnet per landing/entrance at its floor level on the outer face.

### 3.5 Bridge / walkway

- Only the **two ends** get magnets: centred on each end face, at deck level and at 0.15 below deck (4 total).
  4 of 4 straight bridges, all lengths. The lower tier is an end-face reference, not the underside. Matching
  tiers cancel the deck offset so bridges of every length line up deck to deck.
- Diagonal bridges: the same, on the two angled end faces (2 or 4).
- Long walkways: deck-height magnets at the ends and sides; covered walkways add magnets at their support feet
  and roof ends (no simple rule; section 4).
- Tunnels: per mouth, floor-level magnets at the mouth's two sides plus a roof-level centre (10 on the example).

### 3.6 Railing

- 6 magnets: each long face gets one at its bottom-edge centre and one at its top-edge centre (the top follows
  the cap, which is lower on one side); each end face gets one centred at a **fixed height above the base**
  shared by all railing lengths (so railings of different lengths join at the same height).
- 3 of 3 railings follow this; the end height is the same on all three lengths (section 7 gives it per piece).

### 3.7 Round (cylinders, discs, round bases, dishes)

- **Four magnets at 90-degree intervals on the outer rim**, on the cardinal axes, at the **deck height** (the
  walkable top surface or rim lip), forward radially outward (2 of 2 cylinders). A raised lip on two sides gets
  its own pair at the lip height.
- Half-round bases and dishes (cut flat on one side): magnets on the **flat cut face** (centre and two points
  either side, at floor and roof levels) and on the outer rim opposite it; the flat face is the main joint.
- Pieces with threefold symmetry (legs or arms at 120 degrees): one magnet per arm per feature level (cap, stem,
  feet, collars), forward along the arm direction (12 on the example).
- Curved ramps: magnets on the two flat end planes at the low and high deck levels and on the outer curve's
  midpoint.

### 3.8 Structure (rooms, towers, bunkers, pyramids, covers)

- **One magnet per entrance or opening**, at the threshold: centred on the opening, on the opening's outer
  plane, at that opening's floor level. Room with six entrances: 6; tower with four ground entrances and a
  balcony: 5; small bunker with front and back openings: 2.
- Multi-storey pieces: the same at each storey's floor level, plus magnets on the outer footprint at the base
  (towers: 10).
- Pieces with sloped outer walls (pyramid) or diagonal walls (full bunker): magnets on the footprint sides at base
  level and on the main flat face, forward along the face normal.
- Covers: on the top front edge and the two top side ends, plus at each foot.
- These need case-by-case review; section 4 lists them.

### 3.9 Strut / prop-like construction (braces, struts, antenna, frames, man cannon)

- Magnets at each **foot centre** (on the foot's outer face, at its base) and at the **top joint** (top face or
  the two sides of the top beam), forward outward.
- Frames (teleporter frame): one at the base on each of the four outer sides.
- Man cannon / lift pads: one at the front edge and one at the back edge of the base, at base level.
- Antenna-like pieces: one at the base centre facing down, one on each side of the cap opening.

## 4. Pieces that do not follow a simple rule

Each needs a human-reviewed set authored from our own measured features:

| Piece (shape) | What it needs |
| --- | --- |
| Long arena window (sloped six-edge end profile) | wall rows at the middle and both ends, end magnets on the sloped faces; decide which height rows matter |
| Half-round base | flat cut face: centre and two side points at floor level, roof points, rim points at ledge height (10) |
| Base strut, brace, large brace, arch brace | foot centres located on each tapered foot; top joints on the beam's own faces, not the bounding box (the brace's top joint is 0.05 off centre on its thin beam) |
| Cover with feet | top edge points and per-foot base points |
| Covered walkway | deck ends, roof ends, four support feet facing down |
| Towers (all three), tunnel, rooms, bunkers, staircase, ramped platform | list every entrance/landing, its floor height and centre |
| Three-armed dish antenna | per-arm features at four radial levels; the piece has a rotated child node, so magnets must be in the object frame |
| Dish and dish door (half-disc) | flat-face points at base and upper levels; the door shares the dish's front points |
| Curved ramps | end planes at low/high deck levels, outer-curve midpoint |
| Large corner floor | outer corner, deck and underside tiers; drop the duplicates |
| Large Y-platform, landing pad | only end/side joints at deck and underside levels; pad sides are off-centre because of its ramp section |
| Door piece | foot points at each post, mid-height post points, top centre on both faces |
| Pyramid | three footprint sides at base, main flat face at top and bottom |
| Man cannon | front and back base points |

Irregularities in Halo 4's data, kept exactly in section 7: coincident duplicate magnets (one long wall, one
corner floor); forward axes pointing inward or sideways on 15 anchors across 9 pieces (for example one diagonal
bridge, one room, the walkway's three magnets all facing one way). They have no gameplay effect (section 1).

## 5. Applying the rules to the 89 pieces

**Step 1 — which pieces.** The 89 pieces (129 entries) in `05-camera-and-data.md`. The 24 anchorless labels
there (rocks, lights, screen effects, physics toys, pallet, fusion coil, barricade, large shield door, grid) and
the four user-excluded pieces (Radio Antennae, Weapon Holder, Glass Sail, Sniper Nest) get none (U10).

**Step 2 — classify** each piece by the shape tests in the opening table.

**Step 3 — measure the piece** from our own mesh, in the object frame with any child-node offsets folded in:
1. bounding box;
2. list of construction faces: plane, outward normal, area, and the face's outline (edge list), separated from
   trim/decoration (a face below a minimum area, or within a small distance of a larger parallel face, is trim);
3. horizontal levels: bottom, top, every walkable deck or floor level;
4. footprint polygon at each level (polygon floors, banks);
5. for ramps: deck plane (slope, height) and the two end faces;
6. for round pieces: centre axis, rim radius, deck/lip heights, rotational symmetry order;
7. for structures: each opening's centre, width, floor height and outer plane;
8. repeated features: feet, posts, lanes, arms;
9. symmetry planes.

**Step 4 — place** each magnet at the feature named for it in section 7, keeping Halo 4's count, order, duplicates
and frames. Write the result as that piece's magnet table in source code, one table per piece shared by both maps
where the piece is the same model on both.

**Step 5 — check** with the piece's own copies: two copies side by side, stacked, and (for kinds that join to
other kinds, e.g. ramps to blocks, railings to floors) against a standard box at equal heights. A piece passes
when it joins flush at the intended relations.

### What our existing measurement files already provide

| File | Covers | Gives | Missing |
| --- | --- | --- | --- |
| `...\isolated\render-planes-all.json` + `render-triangles\*.npz` | all 89 pieces (165 measured rows, 20 unsupported) | bounding box, every axis-aligned plane level with its area, node frames, the full triangle mesh | sloped and curved faces, face outlines/edges, openings, decks on irregular pieces, symmetry; derivable from the triangles by new tooling |
| `C:\Programming\GitHub\OpenH3M\tools\h4-forge\box_anchor_geometry.json`, `detailed_box_anchor_geometry.json`, `flat_anchor_geometry.json` | 20 boxes/slabs | construction planes / bounds | mixed provenance: `source`, `source_bounds` and the `extra_centers` flag are Halo 4 data |
| `wall_anchor_geometry.json` | 3 walls | target bounds | `source_bounds`, `nominal_half_width` are Halo 4 derived |
| `railing_anchor_geometry.json` | 3 railings | length, height | `end_reference_height` is a Halo 4 magnet height; `source_half_length` is Halo 4 |
| `straight_ramp_geometry.json` | 4 ramps | end positions, deck slope and height | `source_length` is Halo 4 |
| `anchor_completion.json` | 11 pieces | target bounds, supporting-plane points for the four excluded pieces | the other entries are Halo 4 points mapped through fits |

So the bounding box and axis-aligned faces exist for every current piece; the face outlines, sloped/curved faces,
openings and repeated features (items 2, 4–8 above) do not. A
fresh measurement step should produce all nine items from the mesh alone, without the Halo 4 fields.

## 6. Open questions

Settled by the audit and the user (2026-11-26): the seven off-piece magnets follow the audited features; pieces
of different size use the matching-spot correspondence; the 17 project-authored positions stay as audited.
Left open, because the audit does not settle them:

1. **Arena Window #1 and #15.** The audit preserves the centre front/back role on Y=+-0.5 at Z=0, which on our
   piece lies in the window opening 0.32 from material. The audit does not say whether that clearance is
   intended, as it explicitly does for Dish and Door 2.
2. **Walkway Small Cover.** The audit's own note says its nine feature correspondences (upper side roles, the
   two different foot pairs) were never established and must not be guessed from one global fit; the final pass
   then authored seven positions without a feature proof. Kept as audited, but unproven by the audit's own
   standard.
3. **Final-pass pieces.** Tower 3 Story, Tower Tall and Tunnel Long take Halo 4 points through a bounds fit and
   then the nearest point of our mesh. The audit warns elsewhere that a small nearest-surface distance does not
   prove the right face. These three, plus Bunker Stair, Man Cannon and the circular ramps, have equation checks
   only.
4. **Order.** Halo 4 keeps the first of equal-score pairs, so magnet order can matter in a tie. Section 7 keeps
   Halo 4's order; the source-code tables must too.
5. **Multi-node piece.** Dish Antenna has a rotated child node; its magnets in section 7 are in the object frame.

## 7. Exact per-piece magnet sets

Every Halo 4 magnet on each of the 89 pieces (129 map entries; the 40 pieces present on both maps use identical
sets), in Halo 4's order, with Halo 4's duplicates and frames: **543 magnets**, none added or removed. The 24
pieces Halo 4 left without magnets and the four user-excluded pieces (Radio Antennae, Weapon Holder, Glass Sail,
Sniper Nest) have none and are not listed.

**Source of every position: the audited correspondence.** Each magnet sits where the reviewed mapping recorded in
`C:\Programming\GitHub\OpenH3M\tools\h4-forge\MATH-AUDIT.md` (committed in 109f868) placed it:
`anchor_frames.json` through `anchor_frames.py` for 81 pieces, `anchor_completion.json` (from
`complete_anchor_transforms.py`) for 7, Halo 4's unchanged coordinates for Ramp 1x2 Shallow. All 769 exported
anchor positions were recomputed from those committed files and match the current marker pack to within
0.0000004, and neither file has changed since 109f868. On pieces that differ in size or shape from Halo 4's the
audit's matching-spot correspondence applies: each magnet is on the corresponding feature of our piece. The 17
positions this project authored (Walkway Small Cover #2 to #8, both circular ramps #1 to #5) are kept as audited.

How to read the tables:
- **Audit entry** names the MATH-AUDIT.md section whose mapping and proof the piece follows.
- **Location** is the feature of our piece, in the piece's own frame (Z up). "+X face" is the face at the piece's
  largest X; "middle of the top edge of the +X face" is the point centred across that face on its top edge. A
  named measured plane is used where the magnet is not on the overall bounding box. Heights are above the base.
  Rows the audit treats specially carry the audit's own description in bold.
- **Frame** is the magnet's forward (local X) and up (local Z), as Halo 4 had them after the same turn or mirror
  as the piece (and, where the audit says so, rotated onto a sloped face). No gameplay effect; kept for exactness.
- **Our measured feature** names the measured flat faces of our mesh (from
  `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\render-planes-all.json`) the magnet
  lies on, with their areas. "bbox extreme, no flat face" is a bevelled edge: the magnet is where the
  construction planes meet.
- **Off our mesh** is the distance to the nearest triangle of our mesh. Up to about 0.03 this is bevelling or
  trim at an edge; larger values are explained in the row.
- **H4 to feature** is the distance from the Halo 4 magnet, placed on our piece, to the audited feature. *Rigid*:
  piece alignment only (turn, mirror, origin shift). *Fitted*: also stretched to our measured size. A large value
  means our piece is a different size or shape there.

Summary:
- 543 magnets on 89 pieces / 129 entries; counts equal Halo 4's on every piece.
- Rigid distance at most 0.01 on 273 magnets; fitted at most 0.01 on 366. The rest are on 37 pieces whose
  dimensions differ from Halo 4's (largest: Arena Window 4.8, Ramp XL 4.4, Landing Pad 1.4, Pyramid 1.0,
  Tunnel Long 1.0).
- Magnets the audit deliberately places away from material: Dish #2 and Dish Door #2 (upper front reference,
  0.51 clearance), Bunker Stair #9 (virtual under-stair foot), Man Cannon #1 and #2 (below the visible base),
  Door 2 #7 to #10 (inside the opening, Halo 4's jamb clearance), Wall Curve Short #1 to #8 (virtual end-cap
  corners, 0.031). Arena Window #1 and #15 fall in the window opening (0.32 from material) as a consequence of
  the audited role mapping; the audit does not discuss that clearance.
- Proof depth: 81 pieces have detailed feature proofs in the audit. Bunker Stair, Tower 3 Story, Tower Tall,
  Tunnel Long, Man Cannon, both circular ramps and Walkway Small Cover (8 pieces) rely on the final transform
  pass, which checks the equations only.
- Duplicates kept: Arena Wall (1 pair), Corner 4x4 (2 pairs).

#### Block 2x2, Short (Box, 8 magnets)

Audit entry: Cove blocks and ramps (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002A9C. Our bounds X -1.000..1.000, Y -1.000..1.000, Z -0.200..0.300. Halo 4 set placed on our piece: origin shifted by (0, 0, 0); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.000 plane, area 0.39 (bbox); Z=-0.200 bbox extreme, no flat face | 0.0083 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 0.39 (bbox); Z=-0.200 bbox extreme, no flat face | 0.0083 | 0.000 / 0.000 |
| 3 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.000 plane, area 0.39 (bbox); Z=0.300 bbox extreme, no flat face | 0.0083 | 0.000 / 0.000 |
| 4 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.000 plane, area 0.39 (bbox); Z=0.300 bbox extreme, no flat face | 0.0083 | 0.000 / 0.000 |
| 5 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.000 plane, area 0.39 (bbox); Z=0.300 bbox extreme, no flat face | 0.0083 | 0.000 / 0.000 |
| 6 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 0.39 (bbox); Z=0.300 bbox extreme, no flat face | 0.0083 | 0.000 / 0.000 |
| 7 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.000 plane, area 0.39 (bbox); Z=-0.200 bbox extreme, no flat face | 0.0083 | 0.000 / 0.000 |
| 8 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.000 plane, area 0.39 (bbox); Z=-0.200 bbox extreme, no flat face | 0.0083 | 0.000 / 0.000 |

#### Block, 1x1 Tall (Box, 9 magnets)

Audit entry: Wall Curve Short and remaining small construction pieces (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002A6E. Our bounds X -0.509..0.509, Y -0.509..0.509, Z -1.000..1.500. Halo 4 set placed on our piece: origin shifted by (0, 0, 0.250); stretched per axis by (1.014, 1.014, 0.8333); then moved onto measured features (coordinate_planes).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.250 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.507 plane, area 0.10 (bbox); Z=-1.000 plane, area 0.58 (bbox) | 0.0059 | 0.250 / 0.000 |
| 2 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=0.507 plane, area 0.10 (bbox); Z=-1.000 plane, area 0.58 (bbox) | 0.0059 | 0.250 / 0.000 |
| 3 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.507 plane, area 0.10 (bbox); Z=-1.000 plane, area 0.58 (bbox) | 0.0059 | 0.250 / 0.000 |
| 4 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-0.507 plane, area 0.10 (bbox); Z=-1.000 plane, area 0.58 (bbox) | 0.0059 | 0.250 / 0.000 |
| 5 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-0.507 plane, area 0.10 (bbox); Z=1.500 plane, area 0.58 (bbox) | 0.0059 | 0.250 / 0.000 |
| 6 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.507 plane, area 0.10 (bbox); Z=1.500 plane, area 0.58 (bbox) | 0.0059 | 0.250 / 0.000 |
| 7 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=0.507 plane, area 0.10 (bbox); Z=1.500 plane, area 0.58 (bbox) | 0.0059 | 0.250 / 0.000 |
| 8 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.507 plane, area 0.10 (bbox); Z=1.500 plane, area 0.58 (bbox) | 0.0059 | 0.250 / 0.000 |
| 9 | top face (frame facing +Z), centred in X, centred in Y | faces +Z, up +X | Z=1.500 plane, area 0.58 (bbox) | 0.0044 | 0.250 / 0.000 |

#### Block, 1x1, Flat (Box, 8 magnets)

Audit entry: Cove blocks and ramps (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002A64. Our bounds X -0.509..0.509, Y -0.509..0.509, Z -0.100..0.100. Halo 4 set placed on our piece: origin shifted by (0, 0, 0); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the top edge of the +X-facing plane at X=0.500 | faces +X, up +Z | X=0.500 plane, area 0.06; Z=0.100 plane, area 0.58 (bbox) | 0.0001 | 0.003 / 0.003 |
| 2 | middle of the top edge of the -Y-facing plane at Y=-0.500 | faces -Y, up +Z | Y=-0.500 plane, area 0.06; Z=0.100 plane, area 0.58 (bbox) | 0.0001 | 0.000 / 0.000 |
| 3 | middle of the top edge of the -X-facing plane at X=-0.500 | faces -X, up +Z | X=-0.500 plane, area 0.06; Z=0.100 plane, area 0.58 (bbox) | 0.0000 | 0.003 / 0.003 |
| 4 | middle of the top edge of the +Y-facing plane at Y=0.500 | faces +Y, up +Z | Y=0.500 plane, area 0.06; Z=0.100 plane, area 0.58 (bbox) | 0.0000 | 0.000 / 0.000 |
| 5 | middle of the bottom edge of the -Y-facing plane at Y=-0.500 | faces -Y, up +Z | Y=-0.500 plane, area 0.06; Z=-0.100 plane, area 0.58 (bbox) | 0.0001 | 0.000 / 0.000 |
| 6 | middle of the bottom edge of the +X-facing plane at X=0.500 | faces +X, up +Z | X=0.500 plane, area 0.06; Z=-0.100 plane, area 0.58 (bbox) | 0.0001 | 0.003 / 0.003 |
| 7 | middle of the bottom edge of the +Y-facing plane at Y=0.500 | faces +Y, up +Z | Y=0.500 plane, area 0.06; Z=-0.100 plane, area 0.58 (bbox) | 0.0000 | 0.000 / 0.000 |
| 8 | middle of the bottom edge of the -X-facing plane at X=-0.500 | faces -X, up +Z | X=-0.500 plane, area 0.06; Z=-0.100 plane, area 0.58 (bbox) | 0.0000 | 0.003 / 0.003 |

#### Block, 1x1, Short (Box, 8 magnets)

Audit entry: Bridges and the remaining flat slabs (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002A69. Our bounds X -0.509..0.509, Y -0.509..0.509, Z 0..0.500. Halo 4 set placed on our piece: then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the top edge of the +X-facing plane at X=0.500 | faces +X, up +Z | X=0.500 plane, area 0.15; Z=0.500 plane, area 0.58 (bbox) | 0.0000 | 0.001 / 0.001 |
| 2 | middle of the top edge of the -X-facing plane at X=-0.500 | faces -X, up +Z | X=-0.500 plane, area 0.15; Z=0.500 plane, area 0.58 (bbox) | 0.0000 | 0.001 / 0.001 |
| 3 | middle of the top edge of the -Y-facing plane at Y=-0.500 | faces -Y, up +Z | Y=-0.500 plane, area 0.15; Z=0.500 plane, area 0.58 (bbox) | 0.0000 | 0.001 / 0.001 |
| 4 | middle of the top edge of the +Y-facing plane at Y=0.500 | faces +Y, up +Z | Y=0.500 plane, area 0.15; Z=0.500 plane, area 0.58 (bbox) | 0.0000 | 0.001 / 0.001 |
| 5 | middle of the bottom edge of the +X-facing plane at X=0.500 | faces +X, up +Z | X=0.500 plane, area 0.15; Z=0 plane, area 1.00 (bbox) | 0.0000 | 0.000 / 0.000 |
| 6 | middle of the bottom edge of the -X-facing plane at X=-0.500 | faces -X, up +Z | X=-0.500 plane, area 0.15; Z=0 plane, area 1.00 (bbox) | 0.0000 | 0.000 / 0.000 |
| 7 | middle of the bottom edge of the -Y-facing plane at Y=-0.500 | faces -Y, up +Z | Y=-0.500 plane, area 0.15; Z=0 plane, area 1.00 (bbox) | 0.0000 | 0.000 / 0.000 |
| 8 | middle of the bottom edge of the +Y-facing plane at Y=0.500 | faces +Y, up +Z | Y=0.500 plane, area 0.15; Z=0 plane, area 1.00 (bbox) | 0.0000 | 0.000 / 0.000 |

#### Block, 1x1, Tall and Thin (Box, 10 magnets)

Audit entry: Cove blocks and ramps (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002A73. Our bounds X -0.500..0.500, Y -0.300..0.200, Z -1.500..1.500. Halo 4 set placed on our piece: then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the X centre plane (frame facing -X) | faces -X, up +Z | Z=-1.500 plane, area 0.47 (bbox) | 0.0002 | 0.002 / 0.002 |
| 2 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-0.500 plane, area 1.41 (bbox); Z=-1.500 plane, area 0.47 (bbox) | 0.0069 | 0.004 / 0.004 |
| 3 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.300 plane, area 2.88 (bbox); Z=-1.500 plane, area 0.47 (bbox) | 0.0069 | 0.000 / 0.000 |
| 4 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.200 plane, area 2.88 (bbox); Z=-1.500 plane, area 0.47 (bbox) | 0.0069 | 0.000 / 0.000 |
| 5 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=0.500 plane, area 1.41 (bbox); Z=-1.500 plane, area 0.47 (bbox) | 0.0069 | 0.004 / 0.004 |
| 6 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-0.500 plane, area 1.41 (bbox); Z=1.500 plane, area 0.47 (bbox) | 0.0069 | 0.004 / 0.004 |
| 7 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.300 plane, area 2.88 (bbox); Z=1.500 plane, area 0.47 (bbox) | 0.0069 | 0.000 / 0.000 |
| 8 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.200 plane, area 2.88 (bbox); Z=1.500 plane, area 0.47 (bbox) | 0.0069 | 0.000 / 0.000 |
| 9 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=0.500 plane, area 1.41 (bbox); Z=1.500 plane, area 0.47 (bbox) | 0.0069 | 0.004 / 0.004 |
| 10 | middle of the top edge of the X centre plane (frame facing -X) | faces -X, up +Z | Z=1.500 plane, area 0.47 (bbox) | 0.0002 | 0.002 / 0.002 |

#### Block, 1x2 (Box, 8 magnets)

Audit entry: Cove blocks and ramps (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002A78. Our bounds X -1.009..1.009, Y -0.509..0.509, Z -0.500..0.500. Halo 4 set placed on our piece: turned 90 deg; origin shifted by (0, 0, -0.100); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the -X-facing plane at X=-1.000 | faces -X, up +Z | X=-1.000 plane, area 0.50; Z=-0.500 plane, area 1.00 (bbox) | 0.0000 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the +Y-facing plane at Y=0.500 | faces +Y, up +Z | Y=0.500 plane, area 1.37; Z=-0.500 plane, area 1.00 (bbox) | 0.0000 | 0.000 / 0.000 |
| 3 | middle of the bottom edge of the -Y-facing plane at Y=-0.500 | faces -Y, up +Z | Y=-0.500 plane, area 1.37; Z=-0.500 plane, area 1.00 (bbox) | 0.0000 | 0.000 / 0.000 |
| 4 | middle of the bottom edge of the +X-facing plane at X=1.000 | faces +X, up +Z | X=1.000 plane, area 0.50; Z=-0.500 plane, area 1.00 (bbox) | 0.0000 | 0.000 / 0.000 |
| 5 | middle of the top edge of the -X-facing plane at X=-1.000 | faces -X, up +Z | X=-1.000 plane, area 0.50; Z=0.500 plane, area 1.35 (bbox) | 0.0000 | 0.000 / 0.000 |
| 6 | middle of the top edge of the +Y-facing plane at Y=0.500 | faces +Y, up +Z | Y=0.500 plane, area 1.37; Z=0.500 plane, area 1.35 (bbox) | 0.0000 | 0.000 / 0.000 |
| 7 | middle of the top edge of the -Y-facing plane at Y=-0.500 | faces -Y, up +Z | Y=-0.500 plane, area 1.37; Z=0.500 plane, area 1.35 (bbox) | 0.0000 | 0.000 / 0.000 |
| 8 | middle of the top edge of the +X-facing plane at X=1.000 | faces +X, up +Z | X=1.000 plane, area 0.50; Z=0.500 plane, area 1.35 (bbox) | 0.0000 | 0.000 / 0.000 |

#### Block, 1x4 (Box, 8 magnets)

Audit entry: Column, Crenel Notch and two more blocks (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002A7D. Our bounds X -2.008..2.008, Y -0.509..0.509, Z -0.509..0.509. Halo 4 set placed on our piece: origin shifted by (0, 0, 0); stretched per axis by (1.004, 1, 1); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +Y-facing plane at Y=0.500, centred across it, at the level of the horizontal surface 1.009 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.500 plane, area 1.02; Z=0.500 plane, area 1.02 | 0.0091 | 0.000 / 0.000 |
| 2 | the -Y-facing plane at Y=-0.500, centred across it, at the level of the horizontal surface 1.009 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.500 plane, area 1.02; Z=0.500 plane, area 1.02 | 0.0091 | 0.000 / 0.000 |
| 3 | the +Y-facing plane at Y=0.500, centred across it, at the level of the horizontal surface 0.009 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.500 plane, area 1.02; Z=-0.500 plane, area 1.02 | 0.0091 | 0.000 / 0.000 |
| 4 | the +X face, centred across it, at the level of the horizontal surface 1.009 above the base | faces +X, up +Z | X=2.008 plane, area 1.00 (bbox); Z=0.500 plane, area 1.02 | 0.0000 | 0.008 / 0.000 |
| 5 | the -Y-facing plane at Y=-0.500, centred across it, at the level of the horizontal surface 0.009 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.500 plane, area 1.02; Z=-0.500 plane, area 1.02 | 0.0091 | 0.000 / 0.000 |
| 6 | the -X face, centred across it, at the level of the horizontal surface 1.009 above the base | faces -X, up +Z | X=-2.008 plane, area 1.00 (bbox); Z=0.500 plane, area 1.02 | 0.0000 | 0.008 / 0.000 |
| 7 | the +X face, centred across it, at the level of the horizontal surface 0.009 above the base | faces +X, up +Z | X=2.008 plane, area 1.00 (bbox); Z=-0.500 plane, area 1.02 | 0.0000 | 0.008 / 0.000 |
| 8 | the -X face, centred across it, at the level of the horizontal surface 0.009 above the base | faces -X, up +Z | X=-2.008 plane, area 1.00 (bbox); Z=-0.500 plane, area 1.02 | 0.0000 | 0.008 / 0.000 |

#### Block, 2x1, Flat (Box, 8 magnets)

Audit entry: Bridges and the remaining flat slabs (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002A82. Our bounds X -1.000..1.000, Y -0.500..0.529, Z -0.145..0.110. Halo 4 set placed on our piece: origin shifted by (0, 0.015, -0.017); stretched per axis by (1, 1.029, 1.275); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.529 plane, area 0.36 (bbox); Z=-0.145 plane, area 1.97 (bbox) | 0.0136 | 0.031 / 0.000 |
| 2 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 0.18 (bbox); Z=-0.145 plane, area 1.97 (bbox) | 0.0136 | 0.027 / 0.000 |
| 3 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.500 plane, area 0.36 (bbox); Z=-0.145 plane, area 1.97 (bbox) | 0.0136 | 0.031 / 0.000 |
| 4 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.000 plane, area 0.18 (bbox); Z=-0.145 plane, area 1.97 (bbox) | 0.0136 | 0.027 / 0.000 |
| 5 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.000 plane, area 0.18 (bbox); Z=0.110 plane, area 1.97 (bbox) | 0.0136 | 0.027 / 0.000 |
| 6 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.500 plane, area 0.36 (bbox); Z=0.110 plane, area 1.97 (bbox) | 0.0136 | 0.031 / 0.000 |
| 7 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 0.18 (bbox); Z=0.110 plane, area 1.97 (bbox) | 0.0136 | 0.027 / 0.000 |
| 8 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.529 plane, area 0.36 (bbox); Z=0.110 plane, area 1.97 (bbox) | 0.0136 | 0.031 / 0.000 |

#### Block, 2x2 (Box, 8 magnets)

Audit entry: Cove blocks and ramps (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002A87. Our bounds X -1.000..1.000, Y -1.000..1.000, Z -0.500..0.500. Halo 4 set placed on our piece: origin shifted by (0, 0, -0.003); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 1.13 (bbox); Z=-0.499 plane, area 1.73 (bbox) | 0.0083 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.000 plane, area 1.13 (bbox); Z=-0.499 plane, area 1.73 (bbox) | 0.0083 | 0.000 / 0.000 |
| 3 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.000 plane, area 1.13 (bbox); Z=-0.499 plane, area 1.73 (bbox) | 0.0083 | 0.000 / 0.000 |
| 4 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.000 plane, area 1.13 (bbox); Z=-0.499 plane, area 1.73 (bbox) | 0.0083 | 0.000 / 0.000 |
| 5 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 1.13 (bbox); Z=0.498 plane, area 1.73 (bbox) | 0.0084 | 0.000 / 0.000 |
| 6 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.000 plane, area 1.13 (bbox); Z=0.498 plane, area 1.73 (bbox) | 0.0084 | 0.000 / 0.000 |
| 7 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.000 plane, area 1.13 (bbox); Z=0.498 plane, area 1.73 (bbox) | 0.0084 | 0.000 / 0.000 |
| 8 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.000 plane, area 1.13 (bbox); Z=0.498 plane, area 1.73 (bbox) | 0.0084 | 0.000 / 0.000 |

#### Block, 2x2, Flat (Box, 8 magnets)

Audit entry: Bridges and the remaining flat slabs (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002A97. Our bounds X -1.000..1.000, Y -1.000..1.000, Z -0.145..0.110. Halo 4 set placed on our piece: origin shifted by (0, 0, -0.017); stretched per axis by (1, 1, 1.275); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.000 plane, area 0.36 (bbox); Z=-0.145 plane, area 3.88 (bbox) | 0.0136 | 0.027 / 0.000 |
| 2 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 0.36 (bbox); Z=-0.145 plane, area 3.88 (bbox) | 0.0136 | 0.027 / 0.000 |
| 3 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.000 plane, area 0.36 (bbox); Z=-0.145 plane, area 3.88 (bbox) | 0.0136 | 0.027 / 0.000 |
| 4 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.000 plane, area 0.36 (bbox); Z=-0.145 plane, area 3.88 (bbox) | 0.0136 | 0.027 / 0.000 |
| 5 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.000 plane, area 0.36 (bbox); Z=0.110 plane, area 3.88 (bbox) | 0.0136 | 0.027 / 0.000 |
| 6 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.000 plane, area 0.36 (bbox); Z=0.110 plane, area 3.88 (bbox) | 0.0136 | 0.027 / 0.000 |
| 7 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 0.36 (bbox); Z=0.110 plane, area 3.88 (bbox) | 0.0136 | 0.027 / 0.000 |
| 8 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.000 plane, area 0.36 (bbox); Z=0.110 plane, area 3.88 (bbox) | 0.0136 | 0.027 / 0.000 |

#### Block, 2x2, Tall (Box, 8 magnets)

Audit entry: Cove blocks and ramps (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002AA1. Our bounds X -1.000..1.000, Y -1.000..1.000, Z -1.500..1.500. Halo 4 set placed on our piece: then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 1.49 (bbox); Z=-1.500 plane, area 1.63 (bbox) | 0.0071 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.999 plane, area 1.26 (bbox); Z=-1.500 plane, area 1.63 (bbox) | 0.0083 | 0.000 / 0.000 |
| 3 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.000 plane, area 1.49 (bbox); Z=-1.500 plane, area 1.63 (bbox) | 0.0071 | 0.000 / 0.000 |
| 4 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.999 plane, area 1.26 (bbox); Z=-1.500 plane, area 1.63 (bbox) | 0.0083 | 0.000 / 0.000 |
| 5 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.999 plane, area 1.26 (bbox); Z=1.500 plane, area 1.63 (bbox) | 0.0083 | 0.000 / 0.000 |
| 6 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.000 plane, area 1.49 (bbox); Z=1.500 plane, area 1.63 (bbox) | 0.0071 | 0.000 / 0.000 |
| 7 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.999 plane, area 1.26 (bbox); Z=1.500 plane, area 1.63 (bbox) | 0.0083 | 0.000 / 0.000 |
| 8 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 1.49 (bbox); Z=1.500 plane, area 1.63 (bbox) | 0.0071 | 0.000 / 0.000 |

#### Block, 2x3 (Box, 8 magnets)

Audit entry: Cove blocks and ramps (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002AA6. Our bounds X -1.000..1.000, Y -1.500..1.500, Z -0.500..0.500. Halo 4 set placed on our piece: origin shifted by (0, 0, -0.005); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 1.55 (bbox); Z=-0.498 plane, area 1.04 (bbox) | 0.0083 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.500 plane, area 1.13 (bbox); Z=-0.498 plane, area 1.04 (bbox) | 0.0083 | 0.004 / 0.004 |
| 3 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.000 plane, area 1.55 (bbox); Z=-0.498 plane, area 1.04 (bbox) | 0.0083 | 0.000 / 0.000 |
| 4 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.500 plane, area 1.13 (bbox); Z=-0.498 plane, area 1.04 (bbox) | 0.0083 | 0.000 / 0.000 |
| 5 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.500 plane, area 1.13 (bbox); Z=0.498 plane, area 1.41 (bbox) | 0.0083 | 0.000 / 0.000 |
| 6 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.000 plane, area 1.55 (bbox); Z=0.498 plane, area 1.41 (bbox) | 0.0083 | 0.000 / 0.000 |
| 7 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.500 plane, area 1.13 (bbox); Z=0.498 plane, area 1.41 (bbox) | 0.0083 | 0.004 / 0.004 |
| 8 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 1.55 (bbox); Z=0.498 plane, area 1.41 (bbox) | 0.0083 | 0.000 / 0.000 |

#### Block, 2x4 (Box, 8 magnets)

Audit entry: Cove blocks and ramps (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002AAB. Our bounds X -1.000..1.000, Y -2.000..2.000, Z -0.500..0.500. Halo 4 set placed on our piece: then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 1.97 (bbox); Z=-0.498 plane, area 1.33 (bbox) | 0.0083 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-2.000 plane, area 1.13 (bbox); Z=-0.498 plane, area 1.33 (bbox) | 0.0083 | 0.000 / 0.000 |
| 3 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.000 plane, area 1.97 (bbox); Z=-0.498 plane, area 1.33 (bbox) | 0.0083 | 0.000 / 0.000 |
| 4 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=2.000 plane, area 1.13 (bbox); Z=-0.498 plane, area 1.33 (bbox) | 0.0083 | 0.000 / 0.000 |
| 5 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 1.97 (bbox); Z=0.498 plane, area 2.23 (bbox) | 0.0083 | 0.000 / 0.000 |
| 6 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-2.000 plane, area 1.13 (bbox); Z=0.498 plane, area 2.23 (bbox) | 0.0083 | 0.000 / 0.000 |
| 7 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.000 plane, area 1.97 (bbox); Z=0.498 plane, area 2.23 (bbox) | 0.0083 | 0.000 / 0.000 |
| 8 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=2.000 plane, area 1.13 (bbox); Z=0.498 plane, area 2.23 (bbox) | 0.0083 | 0.000 / 0.000 |

#### Block, 3x1, Flat (Box, 8 magnets)

Audit entry: Cove blocks and ramps (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002AB0. Our bounds X -1.500..1.500, Y -0.500..0.500, Z -0.100..0.100. Halo 4 set placed on our piece: then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.500 plane, area 0.05 (bbox); Z=-0.100 plane, area 2.84 (bbox) | 0.0106 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.500 plane, area 0.05 (bbox); Z=-0.100 plane, area 2.84 (bbox) | 0.0106 | 0.002 / 0.002 |
| 3 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.500 bbox extreme, no flat face; Z=-0.100 plane, area 2.84 (bbox) | 0.0100 | 0.000 / 0.000 |
| 4 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.500 bbox extreme, no flat face; Z=-0.100 plane, area 2.84 (bbox) | 0.0100 | 0.000 / 0.000 |
| 5 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.500 bbox extreme, no flat face; Z=0.100 plane, area 2.84 (bbox) | 0.0100 | 0.000 / 0.000 |
| 6 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.500 bbox extreme, no flat face; Z=0.100 plane, area 2.84 (bbox) | 0.0100 | 0.000 / 0.000 |
| 7 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.500 plane, area 0.05 (bbox); Z=0.100 plane, area 2.84 (bbox) | 0.0106 | 0.002 / 0.002 |
| 8 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.500 plane, area 0.05 (bbox); Z=0.100 plane, area 2.84 (bbox) | 0.0106 | 0.000 / 0.000 |

#### Block, 3x3 (Box, 8 magnets)

Audit entry: Cove blocks and ramps (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002AB5. Our bounds X -1.500..1.500, Y -1.500..1.500, Z -0.500..0.500. Halo 4 set placed on our piece: origin shifted by (0, 0, 0); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.500 plane, area 2.05 (bbox); Z=-0.500 plane, area 1.52 (bbox) | 0.0071 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.500 plane, area 2.05 (bbox); Z=-0.500 plane, area 1.52 (bbox) | 0.0071 | 0.000 / 0.000 |
| 3 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.500 plane, area 2.05 (bbox); Z=-0.500 plane, area 1.52 (bbox) | 0.0071 | 0.000 / 0.000 |
| 4 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.500 plane, area 2.05 (bbox); Z=-0.500 plane, area 1.52 (bbox) | 0.0071 | 0.000 / 0.000 |
| 5 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.500 plane, area 2.05 (bbox); Z=0.500 plane, area 1.52 (bbox) | 0.0071 | 0.000 / 0.000 |
| 6 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.500 plane, area 2.05 (bbox); Z=0.500 plane, area 1.52 (bbox) | 0.0071 | 0.000 / 0.000 |
| 7 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.500 plane, area 2.05 (bbox); Z=0.500 plane, area 1.52 (bbox) | 0.0071 | 0.000 / 0.000 |
| 8 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.500 plane, area 2.05 (bbox); Z=0.500 plane, area 1.52 (bbox) | 0.0071 | 0.000 / 0.000 |

#### Block, 3x3, Flat (Box, 8 magnets)

Audit entry: Bridges and the remaining flat slabs (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002ABE. Our bounds X -1.500..1.500, Y -1.500..1.500, Z -0.199..0.100. Halo 4 set placed on our piece: origin shifted by (0, 0, -0.050); stretched per axis by (1, 1, 1.497); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.497 plane, area 0.10 (bbox); Z=-0.199 plane, area 1.52 (bbox) | 0.0073 | 0.050 / 0.000 |
| 2 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.497 plane, area 0.10 (bbox); Z=-0.199 plane, area 1.52 (bbox) | 0.0073 | 0.050 / 0.000 |
| 3 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.497 plane, area 0.10 (bbox); Z=-0.199 plane, area 1.52 (bbox) | 0.0073 | 0.050 / 0.000 |
| 4 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.497 plane, area 0.10 (bbox); Z=-0.199 plane, area 1.52 (bbox) | 0.0073 | 0.050 / 0.000 |
| 5 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.497 plane, area 0.10 (bbox); Z=0.100 plane, area 1.52 (bbox) | 0.0073 | 0.050 / 0.000 |
| 6 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.497 plane, area 0.10 (bbox); Z=0.100 plane, area 1.52 (bbox) | 0.0073 | 0.050 / 0.000 |
| 7 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.497 plane, area 0.10 (bbox); Z=0.100 plane, area 1.52 (bbox) | 0.0073 | 0.050 / 0.000 |
| 8 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.497 plane, area 0.10 (bbox); Z=0.100 plane, area 1.52 (bbox) | 0.0073 | 0.050 / 0.000 |

#### Block, 3x3, Short (Box, 8 magnets)

Audit entry: Cove blocks and ramps (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002AC3. Our bounds X -1.500..1.500, Y -1.500..1.500, Z -0.200..0.300. Halo 4 set placed on our piece: origin shifted by (0, 0, 0.100); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.500 plane, area 0.46 (bbox); Z=-0.200 bbox extreme, no flat face | 0.0083 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.500 plane, area 0.46 (bbox); Z=-0.200 bbox extreme, no flat face | 0.0083 | 0.000 / 0.000 |
| 3 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.500 plane, area 0.46 (bbox); Z=-0.200 bbox extreme, no flat face | 0.0083 | 0.000 / 0.000 |
| 4 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.500 plane, area 0.46 (bbox); Z=-0.200 bbox extreme, no flat face | 0.0083 | 0.000 / 0.000 |
| 5 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.500 plane, area 0.46 (bbox); Z=0.300 bbox extreme, no flat face | 0.0083 | 0.000 / 0.000 |
| 6 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.500 plane, area 0.46 (bbox); Z=0.300 bbox extreme, no flat face | 0.0083 | 0.000 / 0.000 |
| 7 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.500 plane, area 0.46 (bbox); Z=0.300 bbox extreme, no flat face | 0.0083 | 0.000 / 0.000 |
| 8 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.500 plane, area 0.46 (bbox); Z=0.300 bbox extreme, no flat face | 0.0083 | 0.000 / 0.000 |

#### Block, 3x4 (Box, 8 magnets)

Audit entry: Column, Crenel Notch and two more blocks (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002AC8. Our bounds X -1.999..2.000, Y -1.500..1.500, Z -0.500..0.500. Halo 4 set placed on our piece: origin shifted by (0.001, 0, 0); stretched per axis by (0.9996, 1, 0.9999); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.000 plane, area 0.98 (bbox); Z=-0.500 plane, area 7.81 (bbox) | 0.0062 | 0.001 / 0.000 |
| 2 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.500 plane, area 1.86 (bbox); Z=-0.500 plane, area 7.81 (bbox) | 0.0062 | 0.000 / 0.000 |
| 3 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.998 plane, area 0.98 (bbox); Z=-0.500 plane, area 7.81 (bbox) | 0.0062 | 0.001 / 0.000 |
| 4 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.500 plane, area 1.86 (bbox); Z=-0.500 plane, area 7.81 (bbox) | 0.0062 | 0.000 / 0.000 |
| 5 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.500 plane, area 1.86 (bbox); Z=0.500 plane, area 7.81 (bbox) | 0.0062 | 0.000 / 0.000 |
| 6 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.998 plane, area 0.98 (bbox); Z=0.500 plane, area 7.81 (bbox) | 0.0062 | 0.001 / 0.000 |
| 7 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.500 plane, area 1.86 (bbox); Z=0.500 plane, area 7.81 (bbox) | 0.0062 | 0.000 / 0.000 |
| 8 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.000 plane, area 0.98 (bbox); Z=0.500 plane, area 7.81 (bbox) | 0.0062 | 0.001 / 0.000 |

#### Block, 4x4 (Box, 8 magnets)

Audit entry: Cove blocks and ramps (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002ACD. Our bounds X -2.000..2.000, Y -2.000..2.000, Z -0.500..0.500. Halo 4 set placed on our piece: origin shifted by (0, 0, 0); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.999 plane, area 0.21 (bbox); Z=-0.500 plane, area 11.25 (bbox) | 0.0076 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-2.000 plane, area 2.03 (bbox); Z=-0.500 plane, area 11.25 (bbox) | 0.0071 | 0.000 / 0.000 |
| 3 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.999 plane, area 0.21 (bbox); Z=-0.500 plane, area 11.25 (bbox) | 0.0076 | 0.000 / 0.000 |
| 4 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=2.000 plane, area 2.03 (bbox); Z=-0.500 plane, area 11.25 (bbox) | 0.0071 | 0.000 / 0.000 |
| 5 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=2.000 plane, area 2.03 (bbox); Z=0.500 plane, area 11.25 (bbox) | 0.0071 | 0.000 / 0.000 |
| 6 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.999 plane, area 0.21 (bbox); Z=0.500 plane, area 11.25 (bbox) | 0.0076 | 0.000 / 0.000 |
| 7 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-2.000 plane, area 2.03 (bbox); Z=0.500 plane, area 11.25 (bbox) | 0.0071 | 0.000 / 0.000 |
| 8 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.999 plane, area 0.21 (bbox); Z=0.500 plane, area 11.25 (bbox) | 0.0076 | 0.000 / 0.000 |

#### Block, 4x4, Flat (Box, 8 magnets)

Audit entry: Cove blocks and ramps (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002AD7. Our bounds X -2.000..2.000, Y -2.000..2.000, Z -0.100..0.100. Halo 4 set placed on our piece: origin shifted by (0, 0, 0); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.000 plane, area 0.74 (bbox); Z=-0.100 plane, area 2.91 (bbox) | 0.0056 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-2.000 plane, area 0.74 (bbox); Z=-0.100 plane, area 2.91 (bbox) | 0.0056 | 0.000 / 0.000 |
| 3 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-2.000 plane, area 0.74 (bbox); Z=-0.100 plane, area 2.91 (bbox) | 0.0056 | 0.000 / 0.000 |
| 4 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=2.000 plane, area 0.74 (bbox); Z=-0.100 plane, area 2.91 (bbox) | 0.0056 | 0.000 / 0.000 |
| 5 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.000 plane, area 0.74 (bbox); Z=0.100 plane, area 2.91 (bbox) | 0.0056 | 0.000 / 0.000 |
| 6 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-2.000 plane, area 0.74 (bbox); Z=0.100 plane, area 2.91 (bbox) | 0.0056 | 0.000 / 0.000 |
| 7 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-2.000 plane, area 0.74 (bbox); Z=0.100 plane, area 2.91 (bbox) | 0.0056 | 0.000 / 0.000 |
| 8 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=2.000 plane, area 0.74 (bbox); Z=0.100 plane, area 2.91 (bbox) | 0.0056 | 0.000 / 0.000 |

#### Block, 4x4, Tall (Box, 8 magnets)

Audit entry: Cove blocks and ramps (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002ADC. Our bounds X -2.000..2.000, Y -2.000..2.000, Z -1.500..1.500. Halo 4 set placed on our piece: origin shifted by (0, 0, -0.003); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.999 plane, area 7.06 (bbox); Z=-1.500 plane, area 11.27 (bbox) | 0.0066 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-2.000 plane, area 7.40 (bbox); Z=-1.500 plane, area 11.27 (bbox) | 0.0067 | 0.000 / 0.000 |
| 3 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.999 plane, area 7.06 (bbox); Z=-1.500 plane, area 11.27 (bbox) | 0.0066 | 0.000 / 0.000 |
| 4 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=2.000 plane, area 7.40 (bbox); Z=-1.500 plane, area 11.27 (bbox) | 0.0067 | 0.000 / 0.000 |
| 5 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=2.000 plane, area 7.40 (bbox); Z=1.500 plane, area 11.27 (bbox) | 0.0067 | 0.000 / 0.000 |
| 6 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.999 plane, area 7.06 (bbox); Z=1.500 plane, area 11.27 (bbox) | 0.0066 | 0.000 / 0.000 |
| 7 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-2.000 plane, area 7.40 (bbox); Z=1.500 plane, area 11.27 (bbox) | 0.0067 | 0.000 / 0.000 |
| 8 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.999 plane, area 7.06 (bbox); Z=1.500 plane, area 11.27 (bbox) | 0.0066 | 0.000 / 0.000 |

#### Block, 5x1, Short (Box, 8 magnets)

Audit entry: Cove blocks and ramps (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002AE7. Our bounds X -2.500..2.500, Y -0.500..0.500, Z -0.111..0.111. Halo 4 set placed on our piece: origin shifted by (0, 0, -0.100); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +X face, centred across it, at the level of the horizontal surface 0.011 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.500 bbox extreme, no flat face; Z=-0.100 plane, area 4.60 | 0.0100 | 0.000 / 0.000 |
| 2 | the +Y face, centred across it, at the level of the horizontal surface 0.011 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.500 plane, area 0.08 (bbox); Z=-0.100 plane, area 4.60 | 0.0106 | 0.000 / 0.000 |
| 3 | the -X face, centred across it, at the level of the horizontal surface 0.211 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-2.500 bbox extreme, no flat face; Z=0.100 plane, area 4.60 | 0.0100 | 0.000 / 0.000 |
| 4 | the -Y face, centred across it, at the level of the horizontal surface 0.211 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.500 plane, area 0.08 (bbox); Z=0.100 plane, area 4.60 | 0.0106 | 0.000 / 0.000 |
| 5 | the +X face, centred across it, at the level of the horizontal surface 0.211 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.500 bbox extreme, no flat face; Z=0.100 plane, area 4.60 | 0.0100 | 0.000 / 0.000 |
| 6 | the +Y face, centred across it, at the level of the horizontal surface 0.211 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.500 plane, area 0.08 (bbox); Z=0.100 plane, area 4.60 | 0.0106 | 0.000 / 0.000 |
| 7 | the -X face, centred across it, at the level of the horizontal surface 0.011 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-2.500 bbox extreme, no flat face; Z=-0.100 plane, area 4.60 | 0.0100 | 0.000 / 0.000 |
| 8 | the -Y face, centred across it, at the level of the horizontal surface 0.011 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.500 plane, area 0.08 (bbox); Z=-0.100 plane, area 4.60 | 0.0106 | 0.000 / 0.000 |

#### Bridge Diag (Bridge / walkway, 2 magnets)

Audit entry: Full Base Round and compound entrance proofs (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x90002991, Cove 0x90002985. Our bounds X -2.500..2.500, Y -2.500..2.500, Z -0.200..0.402. Halo 4 set placed on our piece: origin shifted by (-0.100, -0.100, -0.005); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +X face, Y=-1.500 (20% across from -Y), at the level of the horizontal surface 0.200 above the base | faces +X, up +Z | X=2.500 plane, area 0.30 (bbox); Z=0 plane, area 8.12 | 0.0000 | 0.002 / 0.002 |
| 2 | the +Y face (frame turned inward, -Y), X=-1.500 (20% across from -X), at the level of the horizontal surface 0.200 above the base | faces -Y, up +Z | Y=2.500 plane, area 0.30 (bbox); Z=0 plane, area 8.12 | 0.0000 | 0.007 / 0.007 |

#### Bridge, 2x1 (Bridge / walkway, 4 magnets)

Audit entry: Bridges and the remaining flat slabs (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x90002974, Cove 0x90002968. Our bounds X -0.500..0.500, Y -1.000..1.000, Z -0.202..0.400. Halo 4 set placed on our piece: origin shifted by (0, 0, -0.001); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +X face, centred across it, at the level of the horizontal surface 0.200 above the base | faces +X, up +Z | X=0.500 plane, area 0.31 (bbox); Z=-0.002 plane, area 1.25 | 0.0000 | 0.001 / 0.001 |
| 2 | the -X face, centred across it, at the level of the horizontal surface 0.200 above the base | faces -X, up +Z | X=-0.500 plane, area 0.56 (bbox); Z=-0.002 plane, area 1.25 | 0.0000 | 0.003 / 0.003 |
| 3 | the -X face, centred across it, at 0.050 above the base (8% of the height) | faces -X, up +Z | X=-0.500 plane, area 0.56 (bbox) | 0.0000 | 0.001 / 0.001 |
| 4 | the +X face, centred across it, at 0.050 above the base (8% of the height) | faces +X, up +Z | X=0.500 plane, area 0.31 (bbox) | 0.0000 | 0.001 / 0.001 |

#### Bridge, 2x2 (Bridge / walkway, 4 magnets)

Audit entry: Bridges and the remaining flat slabs (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x9000297A, Cove 0x9000296E. Our bounds X -1.000..1.000, Y -1.000..1.000, Z -0.202..0.400. Halo 4 set placed on our piece: origin shifted by (0, 0, -0.002); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -X face, centred across it, at the level of the horizontal surface 0.200 above the base | faces -X, up +Z | X=-1.000 plane, area 0.56 (bbox); Z=-0.002 plane, area 2.51 | 0.0000 | 0.001 / 0.001 |
| 2 | the +X face, centred across it, at the level of the horizontal surface 0.200 above the base | faces +X, up +Z | X=1.000 plane, area 0.21 (bbox); Z=-0.002 plane, area 2.51 | 0.0000 | 0.001 / 0.001 |
| 3 | the -X face, centred across it, at 0.050 above the base (8% of the height) | faces -X, up +Z | X=-1.000 plane, area 0.56 (bbox) | 0.0000 | 0.001 / 0.001 |
| 4 | the +X face, centred across it, at 0.050 above the base (8% of the height) | faces +X, up +Z | X=1.000 plane, area 0.21 (bbox) | 0.0000 | 0.001 / 0.001 |

#### Bridge, 2x3 (Bridge / walkway, 4 magnets)

Audit entry: Bridges and the remaining flat slabs (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x9000297F, Cove 0x90002973. Our bounds X -1.499..1.499, Y -1.000..1.000, Z -0.200..0.402. Halo 4 set placed on our piece: origin shifted by (0, 0, 0); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -X face, centred across it, at the level of the horizontal surface 0.200 above the base | faces -X, up +Z | X=-1.499 plane, area 0.56 (bbox); Z=0 plane, area 3.76 | 0.0000 | 0.001 / 0.001 |
| 2 | the +X face, centred across it, at the level of the horizontal surface 0.200 above the base | faces +X, up +Z | X=1.499 plane, area 0.21 (bbox); Z=0 plane, area 3.76 | 0.0000 | 0.000 / 0.000 |
| 3 | the -X face, centred across it, at 0.050 above the base (8% of the height) | faces -X, up +Z | X=-1.499 plane, area 0.56 (bbox) | 0.0000 | 0.001 / 0.001 |
| 4 | the +X face, centred across it, at 0.050 above the base (8% of the height) | faces +X, up +Z | X=1.499 plane, area 0.21 (bbox) | 0.0000 | 0.000 / 0.000 |

#### Bridge, 2x5 (Bridge / walkway, 4 magnets)

Audit entry: Bridges and the remaining flat slabs (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x9000298C, Cove 0x90002980. Our bounds X -2.500..2.500, Y -1.000..1.000, Z -0.200..0.402. Halo 4 set placed on our piece: origin shifted by (0, 0, 0); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -X face, centred across it, at 0.050 above the base (8% of the height) | faces -X, up +Z | X=-2.500 plane, area 0.56 (bbox) | 0.0000 | 0.000 / 0.000 |
| 2 | the +X face, centred across it, at 0.050 above the base (8% of the height) | faces +X, up +Z | X=2.500 plane, area 0.39 (bbox) | 0.0001 | 0.000 / 0.000 |
| 3 | the +X face, centred across it, at the level of the horizontal surface 0.200 above the base | faces +X, up +Z | X=2.500 plane, area 0.39 (bbox); Z=0 plane, area 6.26 | 0.0000 | 0.000 / 0.000 |
| 4 | the -X face, centred across it, at the level of the horizontal surface 0.200 above the base | faces -X, up +Z | X=-2.500 plane, area 0.56 (bbox); Z=0 plane, area 6.26 | 0.0000 | 0.000 / 0.000 |

#### Tunnel, Long (Bridge / walkway, 10 magnets)

Audit entry: Final transform pass (equation checks of the anchor_completion.json transform, not a detailed feature proof) (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002BB9. Our bounds X -1.498..1.498, Y -1.499..1.499, Z 0..2.000. Halo 4 set placed on our piece: centred on our bounding box, then stretched to our bounds per axis, then projected onto our mesh.

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 1.021 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -Y face, centred across it, at 1.956 above the base (98% of the height) | faces -Y, up +Z | Y=-1.499 plane, area 1.26 (bbox) | 0.0000 | 0.001 / 0.000 |
| 2 | the -Y-facing plane at Y=-1.487, X=1.198 (90% across from -X), at 0.013 above the base (1% of the height) | faces -Y, up +Z | Y=-1.490 plane, area 0.46 | 0.0000 | 0.802 / 0.018 |
| 3 | the +Y-facing plane at Y=1.487, X=-1.198 (10% across from -X), at 0.013 above the base (1% of the height) | faces +Y, up +Z | Y=1.490 plane, area 0.46 | 0.0000 | 0.802 / 0.018 |
| 4 | the +Y face, centred across it, at 1.961 above the base (98% of the height) | faces +Y, up +Z | Y=1.499 plane, area 1.26 (bbox) | 0.0000 | 0.036 / 0.037 |
| 5 | the -X-facing plane at X=-1.479, Y=-0.026 (49% across from -Y), at the level of the horizontal surface 1.892 above the base | faces -X, up +Z | X=-1.478 plane, area 0.14; Z=1.890 plane, area 0.58 | 0.0000 | 1.021 / 0.020 |
| 6 | the +X-facing plane at X=1.479, Y=-0.026 (49% across from -Y), at the level of the horizontal surface 1.892 above the base | faces +X, up +Z | X=1.478 plane, area 0.14; Z=1.890 plane, area 0.58 | 0.0000 | 1.021 / 0.020 |
| 7 | the -Y-facing plane at Y=-1.487, X=-1.198 (10% across from -X), at 0.013 above the base (1% of the height) | faces -Y, up +Z | Y=-1.490 plane, area 0.46 | 0.0000 | 0.802 / 0.018 |
| 8 | the -X-facing plane at X=-1.479, centred across it, at the level of the horizontal surface 0.010 above the base | faces -X, up +Z | X=-1.478 plane, area 0.14; Z=0.007 plane, area 1.07 | 0.0000 | 1.021 / 0.021 |
| 9 | the +X-facing plane at X=1.479, centred across it, at the level of the horizontal surface 0.010 above the base | faces +X, up +Z | X=1.478 plane, area 0.14; Z=0.007 plane, area 1.07 | 0.0000 | 1.021 / 0.021 |
| 10 | the +Y-facing plane at Y=1.487, X=1.198 (90% across from -X), at 0.013 above the base (1% of the height) | faces +Y, up +Z | Y=1.490 plane, area 0.46 | 0.0000 | 0.802 / 0.018 |

#### Walkway Small Cover (Bridge / walkway, 9 magnets)

Audit entry: Final transform pass (equation checks of the anchor_completion.json transform, not a detailed feature proof); the earlier "Dish and Dish Door" and "Door 2 and Large Brace" notes record that its detailed feature proof was never completed (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029C5, Cove 0x900029B7. Our bounds X -1.000..1.000, Y -6.000..6.000, Z -1.700..1.000. Halo 4 set placed on our piece: centred on our bounding box, then stretched to our bounds per axis, then projected onto our mesh.

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.502 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | Y=3.558, facing +Y, off any measured Y plane, centred across it, at 2.420 above the base (90% of the height) | faces +Y, up +Z | no measured axis-aligned plane | 0.0000 | 0.053 / 0.033 |
| 2 | the +X face, Y=-0.198 (48% across from -Y), at the level of the horizontal surface 2.500 above the base **Position authored by this project from our construction planes (Final transform pass, anchor_completion.json), kept as audited; the Halo 4 point mapped by the bounds fit is the "fitted" distance.** | faces +X, up -Y | X=1.000 plane, area 4.79 (bbox); Z=0.800 plane, area 7.03 | 0.0000 | 0.101 / 0.150 |
| 3 | the -X face, Y=-0.198 (48% across from -Y), at the level of the horizontal surface 2.500 above the base **Position authored by this project from our construction planes (Final transform pass, anchor_completion.json), kept as audited; the Halo 4 point mapped by the bounds fit is the "fitted" distance.** | faces -X, up +Y | X=-1.000 plane, area 4.95 (bbox); Z=0.800 plane, area 7.03 | 0.0000 | 0.082 / 0.164 |
| 4 | bottom face (frame facing -Z), on the measured X=-0.850 plane, Y=1.750 (65% across from -Y) **Position authored by this project from our construction planes (Final transform pass, anchor_completion.json), kept as audited; the Halo 4 point mapped by the bounds fit is the "fitted" distance.** | faces -Z, up -Y | X=-0.852 plane, area 0.99; Z=-1.700 plane, area 0.20 (bbox) | 0.0000 | 0.249 / 0.014 |
| 5 | bottom face (frame facing -Z), on the measured X=0.850 plane, Y=1.750 (65% across from -Y) **Position authored by this project from our construction planes (Final transform pass, anchor_completion.json), kept as audited; the Halo 4 point mapped by the bounds fit is the "fitted" distance.** | faces -Z, up -Y | X=0.852 plane, area 0.99; Z=-1.700 plane, area 0.20 (bbox) | 0.0000 | 0.251 / 0.014 |
| 6 | bottom face (frame facing -Z), at the +X extreme, Y=4.250 (85% across from -Y) **Position authored by this project from our construction planes (Final transform pass, anchor_completion.json), kept as audited; the Halo 4 point mapped by the bounds fit is the "fitted" distance.** | faces -Z, up -Y | X=1.000 plane, area 4.79 (bbox); Z=-1.700 plane, area 0.20 (bbox) | 0.0000 | 0.201 / 0.080 |
| 7 | bottom face (frame facing -Z), at the -X extreme, Y=4.250 (85% across from -Y) **Position authored by this project from our construction planes (Final transform pass, anchor_completion.json), kept as audited; the Halo 4 point mapped by the bounds fit is the "fitted" distance.** | faces -Z, up -Y | X=-1.000 plane, area 4.95 (bbox); Z=-1.700 plane, area 0.20 (bbox) | 0.0000 | 0.199 / 0.081 |
| 8 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) **Position authored by this project from our construction planes (Final transform pass, anchor_completion.json), kept as audited; the Halo 4 point mapped by the bounds fit is the "fitted" distance.** | faces -Y, up +Z | Y=-6.000 plane, area 0.27 (bbox); Z=1.000 plane, area 6.59 (bbox) | 0.0632 | 0.050 / 0.001 |
| 9 | Y=5.995, facing +Y, off any measured Y plane, on the measured X=0.500 plane, at 1.013 above the base (38% of the height) | faces +Y, up +Z | X=0.500 plane, area 0.08 | 0.0000 | 0.502 / 0.499 |

#### Walkway, Large (Bridge / walkway, 3 magnets)

Audit entry: Ramped Platform, Room Double and Large Walkway (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002BBE. Our bounds X -1.000..1.000, Y -7.000..7.000, Z 0..6.300. Halo 4 set placed on our piece: origin shifted by (0, 0.100, 0.200); stretched per axis by (0.8333, 1, 1); then moved onto measured features (coordinate_planes).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.200 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -X face (frame turned inward, +X), centred across it, at the level of the horizontal surface 6.000 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=-1.000 plane, area 3.35 (bbox); Y=0 plane, area 0.17; Z=6.000 plane, area 17.00 | 0.0703 | 0.200 / 0.000 |
| 2 | the +X face, centred across it, at the level of the horizontal surface 6.000 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 3.35 (bbox); Y=0 plane, area 0.17; Z=6.000 plane, area 17.00 | 0.0703 | 0.200 / 0.000 |
| 3 | the X centre plane (frame facing +X), at the +Y extreme, at the level of the horizontal surface 6.000 above the base | faces +X, up +Z | Y=7.000 plane, area 0.56 (bbox); Z=6.000 plane, area 17.00 | 0.0001 | 0.000 / 0.000 |

#### Corner, 2x2 (Polygon floor, 10 magnets)

Audit entry: Cylinders and Cove corner pieces (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002A92. Our bounds X -1.000..1.000, Y -1.000..1.000, Z 0..0.224. Halo 4 set placed on our piece: then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -X face, Y=0.500 (75% across from -Y), at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.000 plane, area 0.15 (bbox); Z=0 plane, area 1.73 (bbox) | 0.0141 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.000 plane, area 0.31 (bbox); Z=0 plane, area 1.73 (bbox) | 0.0130 | 0.000 / 0.000 |
| 3 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 0.31 (bbox); Z=0 plane, area 1.73 (bbox) | 0.0130 | 0.000 / 0.000 |
| 4 | the -Y face, X=0.500 (75% across from -X), at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.000 plane, area 0.15 (bbox); Z=0 plane, area 1.73 (bbox) | 0.0141 | 0.000 / 0.000 |
| 5 | surface facing -135 deg from +X toward +Y; X=-0.500 (25% across from -X), Y=-0.500 (25% across from -Y), at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces horizontal at -135 deg from +X toward +Y, up +Z | Z=0 plane, area 1.73 (bbox) | 0.0141 | 0.000 / 0.000 |
| 6 | surface facing -135 deg from +X toward +Y; X=-0.500 (25% across from -X), Y=-0.500 (25% across from -Y), at the level of the horizontal surface 0.200 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces horizontal at -135 deg from +X toward +Y, up +Z | Z=0.200 plane, area 1.66 | 0.0141 | 0.000 / 0.000 |
| 7 | the -Y face, X=0.500 (75% across from -X), at the level of the horizontal surface 0.200 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.000 plane, area 0.15 (bbox); Z=0.200 plane, area 1.66 | 0.0141 | 0.000 / 0.000 |
| 8 | the +X face, centred across it, at the level of the horizontal surface 0.200 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 0.31 (bbox); Z=0.200 plane, area 1.66 | 0.0130 | 0.000 / 0.000 |
| 9 | the +Y face, centred across it, at the level of the horizontal surface 0.200 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.000 plane, area 0.31 (bbox); Z=0.200 plane, area 1.66 | 0.0130 | 0.000 / 0.000 |
| 10 | the -X face, Y=0.500 (75% across from -Y), at the level of the horizontal surface 0.200 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.000 plane, area 0.15 (bbox); Z=0.200 plane, area 1.66 | 0.0141 | 0.000 / 0.000 |

#### Corner, 45 Degrees (Polygon floor, 4 magnets)

Audit entry: 45-degree corner and Teleport Frame (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002A8C. Our bounds X -0.400..1.007, Y -1.000..0.994, Z 0..0.600. Halo 4 set placed on our piece: turned 180 deg; then moved onto measured features (axis_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.536 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -X face, centred across it, at the level of the horizontal surface 0.200 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-0.400 plane, area 0.49 (bbox); Z=0.200 plane, area 0.51 | 0.0068 | 0.536 / 0.536 |
| 2 | surface facing 45 deg from +X toward +Y; X=0.307 (50% across from -X), Y=0.293 (65% across from -Y), at the level of the horizontal surface 0.200 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces horizontal at 45 deg from +X toward +Y, up +Z | Z=0.200 plane, area 0.51 | 0.0068 | 0.408 / 0.408 |
| 3 | the -X face, centred across it, at 0.050 above the base (8% of the height) | faces -X, up +Z | X=-0.400 plane, area 0.49 (bbox) | 0.0000 | 0.536 / 0.536 |
| 4 | surface facing 45 deg from +X toward +Y; X=0.307 (50% across from -X), Y=0.293 (65% across from -Y), at 0.050 above the base (8% of the height) | faces horizontal at 45 deg from +X toward +Y, up +Z | no measured axis-aligned plane | 0.0000 | 0.408 / 0.408 |

#### Corner, 4x4 (Polygon floor, 10 magnets)

Audit entry: Cylinders and Cove corner pieces (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002AD2. Our bounds X -2.000..2.000, Y -2.000..2.000, Z -0.300..0.300. Halo 4 set placed on our piece: turned 180 deg; origin shifted by (0.300, 0.400, -0.300); then moved onto measured features (coordinate_planes).

Halo 4 duplicates kept: #8 and #9 share one point, #2 and #10 share one point.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +Y face, centred across it, at the level of the horizontal surface 0.200 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=2.000 plane, area 0.70 (bbox); Z=-0.100 plane, area 9.46 | 0.0122 | 0.000 / 0.000 |
| 2 | the +X face, at the +Y extreme, at 0.030 above the base (5% of the height) | faces +X, up +Z | X=2.000 plane, area 0.70 (bbox); Y=2.000 plane, area 0.70 (bbox) | 0.0000 | 0.000 / 0.000 |
| 3 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=2.000 plane, area 0.70 (bbox); Z=-0.300 plane, area 10.28 (bbox) | 0.0115 | 0.000 / 0.000 |
| 4 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.000 plane, area 0.70 (bbox); Z=-0.300 plane, area 10.28 (bbox) | 0.0115 | 0.000 / 0.000 |
| 5 | the +X face, centred across it, at the level of the horizontal surface 0.200 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.000 plane, area 0.70 (bbox); Z=-0.100 plane, area 9.46 | 0.0122 | 0.000 / 0.000 |
| 6 | the +Y face, at the -X extreme, at the level of the horizontal surface 0.200 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | X=-2.000 plane, area 0.55 (bbox); Y=2.000 plane, area 0.70 (bbox); Z=-0.100 plane, area 9.46 | 0.0142 | 0.000 / 0.000 |
| 7 | the +X face, at the -Y extreme, at the level of the horizontal surface 0.200 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.000 plane, area 0.70 (bbox); Y=-2.000 plane, area 0.55 (bbox); Z=-0.100 plane, area 9.46 | 0.0142 | 0.000 / 0.000 |
| 8 | the +Y face, at the +X extreme, at the level of the horizontal surface 0.200 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | X=2.000 plane, area 0.70 (bbox); Y=2.000 plane, area 0.70 (bbox); Z=-0.100 plane, area 9.46 | 0.0141 | 0.000 / 0.000 |
| 9 | the +X face, at the +Y extreme, at the level of the horizontal surface 0.200 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.000 plane, area 0.70 (bbox); Y=2.000 plane, area 0.70 (bbox); Z=-0.100 plane, area 9.46 | 0.0141 | 0.000 / 0.000 |
| 10 | the +Y face, at the +X extreme, at 0.030 above the base (5% of the height) | faces +Y, up +Z | X=2.000 plane, area 0.70 (bbox); Y=2.000 plane, area 0.70 (bbox) | 0.0000 | 0.000 / 0.000 |

#### Landing Pad (Polygon floor, 8 magnets)

Audit entry: Stunt Ramp, XL Ramp and Landing Pad (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002AE1. Our bounds X -2.000..2.000, Y -4.000..2.000, Z -0.300..1.000. Halo 4 set placed on our piece: then moved onto measured features (axis_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 1.393 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -X face, Y=0.250 (71% across from -Y), at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-2.000 plane, area 2.28 (bbox); Z=-0.300 plane, area 13.23 (bbox) | 0.0071 | 1.261 / 1.261 |
| 2 | the +Y face, centred across it, at the level of the horizontal surface 0.300 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=2.000 plane, area 1.84 (bbox); Z=0 plane, area 8.80 | 0.0071 | 1.145 / 1.145 |
| 3 | the -X face, Y=0.250 (71% across from -Y), at the level of the horizontal surface 0.300 above the base | faces -X, up +Z | X=-2.000 plane, area 2.28 (bbox); Z=0 plane, area 8.80 | 0.0000 | 1.288 / 1.288 |
| 4 | the +X face, Y=0.250 (71% across from -Y), at the level of the horizontal surface 0.300 above the base | faces +X, up +Z | X=2.000 plane, area 2.28 (bbox); Z=0 plane, area 8.80 | 0.0000 | 1.393 / 1.393 |
| 5 | the -Y face, centred across it, at the level of the horizontal surface 0.300 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-4.000 plane, area 0.44 (bbox); Z=0 plane, area 8.80 | 0.0071 | 1.145 / 1.145 |
| 6 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-4.000 plane, area 0.44 (bbox); Z=-0.300 plane, area 13.23 (bbox) | 0.0071 | 1.209 / 1.209 |
| 7 | the +X face, Y=0.250 (71% across from -Y), at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.000 plane, area 2.28 (bbox); Z=-0.300 plane, area 13.23 (bbox) | 0.0071 | 1.359 / 1.359 |
| 8 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=2.000 plane, area 1.84 (bbox); Z=-0.300 plane, area 13.23 (bbox) | 0.0071 | 1.081 / 1.081 |

#### Platform, Y (Polygon floor, 6 magnets)

Audit entry: Wall Curve Short and remaining small construction pieces (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002AEC. Our bounds X -1.507..1.979, Y -1.500..1.500, Z -0.100..0.100. Halo 4 set placed on our piece: turned 180 deg; then moved onto measured features (axis_levels, upright_yaw_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.316 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.507 plane, area 0.47 (bbox); Z=0.100 plane, area 8.03 (bbox) | 0.0141 | 0.224 / 0.224 |
| 2 | the +Y face, X=-0.507 (29% across from -X), at top (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.500 plane, area 0.31 (bbox); Z=0.100 plane, area 8.03 (bbox) | 0.0141 | 0.224 / 0.224 |
| 3 | the -Y face, X=-0.507 (29% across from -X), at top (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.500 plane, area 0.31 (bbox); Z=0.100 plane, area 8.03 (bbox) | 0.0141 | 0.224 / 0.224 |
| 4 | middle of the top edge of X=1.993, facing +X, off any measured X plane (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | Z=0.100 plane, area 8.03 (bbox) | 0.0231 | 0.316 / 0.316 |
| 5 | surface facing -45 deg from +X toward +Y; X=1.243 (79% across from -X), Y=-0.750 (25% across from -Y), at top (on the construction planes; our mesh is bevelled or trimmed here) | faces horizontal at -45 deg from +X toward +Y, up +Z | Z=0.100 plane, area 8.03 (bbox) | 0.0142 | 0.274 / 0.274 |
| 6 | surface facing 45 deg from +X toward +Y; X=1.243 (79% across from -X), Y=0.750 (75% across from -Y), at top (on the construction planes; our mesh is bevelled or trimmed here) | faces horizontal at 45 deg from +X toward +Y, up +Z | Z=0.100 plane, area 8.03 (bbox) | 0.0141 | 0.274 / 0.274 |

#### Platform, Y, Large (Polygon floor, 2 magnets)

Audit entry: Wall Curve Short and remaining small construction pieces (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002AF1. Our bounds X -2.500..2.500, Y -2.000..2.000, Z -0.701..0.398. Halo 4 set placed on our piece: turned 180 deg; then moved onto measured features (axis_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.747 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +X face, centred across it, at the level of the horizontal surface 0.701 above the base | faces +X, up +Z | X=2.500 plane, area 1.16 (bbox); Z=0 plane, area 4.18 | 0.0000 | 0.747 / 0.747 |
| 2 | the -X face, centred across it, at the level of the horizontal surface 0.201 above the base | faces -X, up +Z | X=-2.500 plane, area 0.33 (bbox); Z=-0.500 plane, area 4.51 | 0.0001 | 0.728 / 0.728 |

#### Railing, Long (Railing, 6 magnets)

Audit entry: Bridge ramps, walls and railings (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002B36. Our bounds X -0.100..0.100, Y -1.500..1.500, Z 0..0.399. Halo 4 set placed on our piece: turned 180 deg; stretched per axis by (1, 0.9999, 0.7977); then moved onto measured features (coordinate_planes).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.101 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +X face, centred across it, at 0.319 above the base (80% of the height) | faces +X, up +Z | X=0.100 plane, area 0.88 (bbox) | 0.0037 | 0.081 / 0.000 |
| 2 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=0.100 plane, area 0.88 (bbox); Z=0 plane, area 0.54 (bbox) | 0.0062 | 0.000 / 0.000 |
| 3 | the -Y face, centred across it, at 0.181 above the base (45% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.500 bbox extreme, no flat face | 0.0071 | 0.046 / 0.007 |
| 4 | the +Y face, centred across it, at 0.181 above the base (45% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.500 bbox extreme, no flat face | 0.0070 | 0.045 / 0.001 |
| 5 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-0.100 plane, area 1.14 (bbox); Z=0.399 plane, area 0.24 (bbox) | 0.0062 | 0.101 / 0.000 |
| 6 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-0.100 plane, area 1.14 (bbox); Z=0 plane, area 0.54 (bbox) | 0.0062 | 0.000 / 0.000 |

#### Railing, Medium (Railing, 6 magnets)

Audit entry: Bridge ramps, walls and railings (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002B31. Our bounds X -0.100..0.100, Y -0.999..0.999, Z 0..0.399. Halo 4 set placed on our piece: turned 180 deg; origin shifted by (0, 0, 0); stretched per axis by (1, 0.9995, 0.7977); then moved onto measured features (coordinate_planes).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.101 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -Y face, centred across it, at 0.181 above the base (45% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.999 bbox extreme, no flat face | 0.0070 | 0.045 / 0.001 |
| 2 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=0.100 plane, area 0.57 (bbox); Z=0 plane, area 0.36 (bbox) | 0.0062 | 0.000 / 0.000 |
| 3 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-0.100 plane, area 0.76 (bbox); Z=0.399 plane, area 0.16 (bbox) | 0.0062 | 0.101 / 0.000 |
| 4 | the +Y face, centred across it, at 0.181 above the base (45% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.999 bbox extreme, no flat face | 0.0070 | 0.045 / 0.001 |
| 5 | the +X face, centred across it, at 0.319 above the base (80% of the height) | faces +X, up +Z | X=0.100 plane, area 0.57 (bbox) | 0.0037 | 0.081 / 0.000 |
| 6 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-0.100 plane, area 0.76 (bbox); Z=0 plane, area 0.36 (bbox) | 0.0062 | 0.000 / 0.000 |

#### Railing, Small (Railing, 6 magnets)

Audit entry: Bridge ramps, walls and railings (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002B2B. Our bounds X -0.100..0.100, Y -0.499..0.499, Z 0..0.399. Halo 4 set placed on our piece: turned 180 deg; origin shifted by (0, 0, 0); stretched per axis by (1, 0.9979, 0.7976); then moved onto measured features (coordinate_planes).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.101 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +X face, centred across it, at 0.319 above the base (80% of the height) | faces +X, up +Z | X=0.100 plane, area 0.27 (bbox) | 0.0037 | 0.081 / 0.000 |
| 2 | the +Y face, centred across it, at 0.181 above the base (45% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.499 bbox extreme, no flat face | 0.0070 | 0.045 / 0.001 |
| 3 | the -Y face, centred across it, at 0.181 above the base (45% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.499 bbox extreme, no flat face | 0.0070 | 0.045 / 0.001 |
| 4 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-0.100 plane, area 0.37 (bbox); Z=0.399 plane, area 0.08 (bbox) | 0.0062 | 0.101 / 0.000 |
| 5 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-0.100 plane, area 0.37 (bbox); Z=0 plane, area 0.18 (bbox) | 0.0062 | 0.000 / 0.000 |
| 6 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=0.100 plane, area 0.27 (bbox); Z=0 plane, area 0.18 (bbox) | 0.0062 | 0.000 / 0.000 |

#### Bank, 1x1 (Ramp / wedge, 3 magnets)

Audit entry: Historical detailed proofs (table row and bank-proof paragraph) (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x90002937, Cove 0x9000293B. Our bounds X -1.000..0, Y 0..1.000, Z -0.500..0.500. Halo 4 set placed on our piece: origin shifted by (0.001, -0.001, 0.002); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | surface facing 135 deg from +X toward +Y; centred in X, centred in Y, at bottom | faces horizontal at 135 deg from +X toward +Y, up +Z | Z=-0.500 plane, area 0.50 (bbox) | 0.0000 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the -Y face | faces -Y, up +Z | Y=0 plane, area 0.50 (bbox); Z=-0.500 plane, area 0.50 (bbox) | 0.0000 | 0.000 / 0.000 |
| 3 | middle of the bottom edge of the +X face | faces +X, up +Z | X=0 plane, area 0.50 (bbox); Z=-0.500 plane, area 0.50 (bbox) | 0.0000 | 0.000 / 0.000 |

#### Bank, 1x2 (Ramp / wedge, 3 magnets)

Audit entry: Historical detailed proofs (table row and bank-proof paragraph) (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x90002943, Cove 0x90002942. Our bounds X -1.000..0, Y 0..2.000, Z -0.500..0.500. Halo 4 set placed on our piece: origin shifted by (0.010, 0.001, 0.015).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +X face | faces +X, up +Z | X=0 plane, area 1.00 (bbox); Z=-0.500 plane, area 1.00 (bbox) | 0.0000 | 0.000 / 0.000 |
| 2 | surface facing 154 deg from +X toward +Y; centred in X, centred in Y, at bottom | faces horizontal at 154 deg from +X toward +Y, up +Z | Z=-0.500 plane, area 1.00 (bbox) | 0.0000 | 0.000 / 0.000 |
| 3 | middle of the bottom edge of the -Y face | faces -Y, up +Z | Y=0 plane, area 0.50 (bbox); Z=-0.500 plane, area 1.00 (bbox) | 0.0000 | 0.000 / 0.000 |

#### Bank, 2x1 (Ramp / wedge, 3 magnets)

Audit entry: Historical detailed proofs (table row and bank-proof paragraph) (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x90002948, Cove 0x90002947. Our bounds X -2.000..0, Y 0..1.000, Z -0.500..0.500. Halo 4 set placed on our piece: mirrored in Y; origin shifted by (-0.003, 0, -0.012).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the -Y face | faces -Y, up +Z | Y=0 plane, area 1.00 (bbox); Z=-0.500 plane, area 1.00 (bbox) | 0.0000 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the +X face | faces +X, up +Z | X=0 plane, area 0.50 (bbox); Z=-0.500 plane, area 1.00 (bbox) | 0.0000 | 0.000 / 0.000 |
| 3 | surface facing 116 deg from +X toward +Y; centred in X, centred in Y, at bottom | faces horizontal at 116 deg from +X toward +Y, up +Z | Z=-0.500 plane, area 1.00 (bbox) | 0.0000 | 0.000 / 0.000 |

#### Bank, 2x2 (Ramp / wedge, 3 magnets)

Audit entry: Historical detailed proofs (table row and bank-proof paragraph) (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x9000294D, Cove 0x9000294C. Our bounds X -2.000..0, Y 0..2.000, Z -0.500..0.500. Halo 4 set placed on our piece: origin shifted by (-0.003, 0.002, 0.007).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the -Y face | faces -Y, up +Z | Y=0 plane, area 1.00 (bbox); Z=-0.500 plane, area 2.00 (bbox) | 0.0000 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the +X face | faces +X, up +Z | X=0 plane, area 1.00 (bbox); Z=-0.500 plane, area 2.00 (bbox) | 0.0000 | 0.000 / 0.000 |
| 3 | surface facing -45 deg from +X toward +Y; centred in X, centred in Y, at bottom | faces horizontal at -45 deg from +X toward +Y, up +Z | Z=-0.500 plane, area 2.00 (bbox) | 0.0000 | 0.000 / 0.000 |

#### Platform, Ramped (Ramp / wedge, 4 magnets)

Audit entry: Ramped Platform, Room Double and Large Walkway (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002B6E. Our bounds X -3.000..2.000, Y -2.201..2.301, Z -1.000..1.100. Halo 4 set placed on our piece: turned 180 deg; origin shifted by (-0.283, -0.533, -1.000); stretched per axis by (1, 0.8333, 1); then moved onto measured features (coordinate_planes, axis_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.367 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -X face, Y=1.300 (78% across from -Y), at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-3.000 plane, area 0.17 (bbox); Z=-1.000 plane, area 0.64 (bbox) | 0.0188 | 0.367 / 0.000 |
| 2 | the +X face, Y=1.092 (73% across from -Y), at the level of the horizontal surface 1.700 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.000 plane, area 0.58 (bbox); Z=0.700 plane, area 5.03 | 0.0137 | 0.325 / 0.000 |
| 3 | the +X face, centred across it, at the level of the horizontal surface 1.700 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.000 plane, area 0.58 (bbox); Z=0.700 plane, area 5.03 | 0.0134 | 0.117 / 0.000 |
| 4 | the +X face, Y=-0.992 (27% across from -Y), at the level of the horizontal surface 1.700 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.000 plane, area 0.58 (bbox); Z=0.700 plane, area 5.03 | 0.0129 | 0.092 / 0.000 |

#### Ramp, 1x2 (Ramp / wedge, 3 magnets)

Audit entry: Cove blocks and ramps (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002B3B. Our bounds X -1.000..1.000, Y -0.501..0.501, Z 0..1.000. Halo 4 set placed on our piece: origin shifted by (0.100, 0, 0).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the top edge of the +X face | faces +X, up +Z | X=1.000 plane, area 0.94 (bbox); Z=1.000 bbox extreme, no flat face | 0.0046 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 0.94 (bbox); Z=0 plane, area 1.88 (bbox) | 0.0073 | 0.000 / 0.000 |
| 3 | middle of the bottom edge of the -X face | faces -X, up +Z | X=-1.000 bbox extreme, no flat face; Z=0 plane, area 1.88 (bbox) | 0.0035 | 0.000 / 0.000 |

#### Ramp, 1x2, Shallow (Ramp / wedge, 3 magnets)

Audit entry: Cove blocks and ramps (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002B40. Our bounds X -1.000..1.000, Y -0.501..0.501, Z 0..0.500. Halo 4 set placed on our piece: Halo 4 coordinates used unchanged.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the -X face | faces -X, up +Z | X=-1.000 bbox extreme, no flat face; Z=0 plane, area 1.88 (bbox) | 0.0033 | 0.000 / 0.000 |
| 2 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.000 plane, area 0.46 (bbox); Z=0 plane, area 1.88 (bbox) | 0.0071 | 0.000 / 0.000 |
| 3 | middle of the top edge of the +X face | faces +X, up +Z | X=1.000 plane, area 0.46 (bbox); Z=0.500 bbox extreme, no flat face | 0.0042 | 0.000 / 0.000 |

#### Ramp, 2x2 (Ramp / wedge, 2 magnets)

Audit entry: Bridge ramps, walls and railings (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002B45. Our bounds X -1.000..1.000, Y -1.000..1.000, Z -0.505..0.495. Halo 4 set placed on our piece: origin shifted by (0.105, 0, -0.005); stretched per axis by (1, 1, 1); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the -X face | faces -X, up +Z | X=-1.000 bbox extreme, no flat face; Z=-0.505 plane, area 1.48 (bbox) | 0.0000 | 0.000 / 0.000 |
| 2 | middle of the top edge of the +X face | faces +X, up +Z | X=1.000 plane, area 0.74 (bbox); Z=0.495 bbox extreme, no flat face | 0.0000 | 0.000 / 0.000 |

#### Ramp, Bridge, Large (Ramp / wedge, 2 magnets)

Audit entry: Bridge ramps, walls and railings (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002B59. Our bounds X -2.500..2.500, Y -1.000..1.000, Z 0..3.091. Halo 4 set placed on our piece: origin shifted by (0, 0, -0.005); stretched per axis by (0.9999, 1, 0.9999); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -X face, centred across it, at 2.695 above the base (87% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-2.500 plane, area 0.60 (bbox) | 0.0100 | 0.000 / 0.000 |
| 2 | the +X face, centred across it, at 0.195 above the base (6% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.500 plane, area 0.11 (bbox) | 0.0052 | 0.000 / 0.000 |

#### Ramp, Bridge, Medium (Ramp / wedge, 2 magnets)

Audit entry: Bridge ramps, walls and railings (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002B4F. Our bounds X -2.005..2.005, Y -1.000..1.000, Z 0..2.596. Halo 4 set placed on our piece: origin shifted by (0, 0.025, -0.005); stretched per axis by (1.002, 1, 1.002); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -X face, centred across it, at 2.200 above the base (85% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-2.005 plane, area 0.60 (bbox) | 0.0099 | 0.007 / 0.000 |
| 2 | the +X face, centred across it, at 0.196 above the base (8% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.005 plane, area 0.11 (bbox) | 0.0053 | 0.005 / 0.000 |

#### Ramp, Bridge, Small (Ramp / wedge, 2 magnets)

Audit entry: Bridge ramps, walls and railings (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002B4A. Our bounds X -1.500..1.500, Y -1.000..1.000, Z 0..2.091. Halo 4 set placed on our piece: origin shifted by (0.007, 0.003, -0.004); stretched per axis by (1, 1, 1); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -X face, centred across it, at 1.696 above the base (81% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-1.500 plane, area 0.60 (bbox) | 0.0100 | 0.000 / 0.000 |
| 2 | the +X face, centred across it, at 0.196 above the base (9% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.500 plane, area 0.11 (bbox) | 0.0052 | 0.000 / 0.000 |

#### Ramp, Stunt (Ramp / wedge, 5 magnets)

Audit entry: Stunt Ramp, XL Ramp and Landing Pad (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002B05. Our bounds X -1.988..1.999, Y -1.200..1.200, Z 0..1.519. Halo 4 set placed on our piece: turned 270 deg; then moved onto measured features (axis_levels).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +Y face, X=-0.004 (50% across from -X), at bottom | faces +Y, up +Z | Y=1.200 plane, area 1.62 (bbox); Z=0.003 plane, area 9.07 (bbox) | 0.0037 | 0.006 / 0.006 |
| 2 | middle of the bottom edge of X=-2.004, facing -X, off any measured X plane (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | Z=0.003 plane, area 9.07 (bbox) | 0.0193 | 0.013 / 0.013 |
| 3 | the -Y face, X=-0.004 (50% across from -X), at bottom | faces -Y, up +Z | Y=-1.200 plane, area 1.62 (bbox); Z=0.003 plane, area 9.07 (bbox) | 0.0037 | 0.006 / 0.006 |
| 4 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.996 plane, area 3.32 (bbox); Z=0.003 plane, area 9.07 (bbox) | 0.0142 | 0.006 / 0.006 |
| 5 | the +X face, centred across it, at the level of the horizontal surface 1.503 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.996 plane, area 3.32 (bbox); Z=1.503 plane, area 0.44 | 0.0142 | 0.041 / 0.041 |

#### Ramp, XL (Ramp / wedge, 4 magnets)

Audit entry: XL-ramp correspondence; Stunt Ramp, XL Ramp and Landing Pad (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002B54. Our bounds X -1.999..2.001, Y -1.200..1.200, Z 0..3.193. Halo 4 set placed on our piece: turned 270 deg; origin shifted by (0.300, 0, 0); then moved onto measured features (axis_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 4.396 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.001 plane, area 4.59 (bbox); Z=3.196 bbox extreme, no flat face | 0.0080 | 4.396 / 4.396 |
| 2 | the +X face, centred across it, at -0.004 above the base (-0% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.001 plane, area 4.59 (bbox) | 0.0085 | 2.005 / 2.005 |
| 3 | the -X face, centred across it, at 2.200 above the base (69% of the height) | faces -X, up +Z | X=-1.999 plane, area 0.48 (bbox) | 0.0018 | 2.400 / 2.400 |
| 4 | the -X face, centred across it, at 1.987 above the base (62% of the height) | faces -X, up +Z | X=-1.999 plane, area 0.48 (bbox) | 0.0014 | 1.987 / 1.987 |

#### Staircase (Ramp / wedge, 4 magnets)

Audit entry: Different profiles and multiple nodes (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002BB4. Our bounds X -3.000..4.000, Y -2.000..3.000, Z -1.600..1.900. Halo 4 set placed on our piece: turned 180 deg; origin shifted by (0.500, 0.875, -1.200); stretched per axis by (1, 1.25, 1).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.425 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +X face, Y=-0.750 (25% across from -Y), at the level of the horizontal surface 0.600 above the base | faces +X, up +Z | X=4.000 plane, area 6.50 (bbox); Z=-1.000 plane, area 1.77 | 0.0000 | 0.325 / 0.000 |
| 2 | the +X face, Y=1.750 (75% across from -Y), at the level of the horizontal surface 3.100 above the base | faces +X, up +Z | X=4.000 plane, area 6.50 (bbox); Z=1.500 plane, area 2.89 | 0.0000 | 0.175 / 0.000 |
| 3 | the +Y face, X=2.400 (77% across from -X), at the level of the horizontal surface 3.100 above the base | faces +Y, up +Z | Y=3.000 plane, area 18.39 (bbox); Z=1.500 plane, area 2.89 | 0.0001 | 0.425 / 0.000 |
| 4 | the Y centre plane (frame facing -Y), X=2.300 (76% across from -X), at the level of the horizontal surface 3.100 above the base | faces -Y, up +Z | Y=0.500 plane, area 15.47; Z=1.500 plane, area 2.89 | 0.0000 | 0.075 / 0.000 |

#### Base Round (Round, 10 magnets)

Audit entry: Full Base Round and compound entrance proofs (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x90002952, Cove 0x90002951. Our bounds X -5.500..5.500, Y -5.500..0, Z -1.000..1.700. Halo 4 set placed on our piece: turned 180 deg; origin shifted by (0, -2.979, -0.100); stretched horizontally by 0.9167; then moved onto measured features (coordinate_planes).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.549 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +Y face, centred across it, at the level of the horizontal surface 1.000 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0 plane, area 5.56 (bbox); Z=0 plane, area 17.98 | 0.0113 | 0.271 / 0.000 |
| 2 | Y=-1.276, facing +Y, off any measured Y plane, centred across it, at the level of the horizontal surface 2.600 above the base | faces +Y, up +Z | Z=1.600 plane, area 28.85 | 0.0000 | 0.155 / 0.000 |
| 3 | the -Y face, centred across it, at the level of the horizontal surface 0.800 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-5.500 plane, area 1.31 (bbox); Z=-0.200 plane, area 9.54 | 0.0108 | 0.229 / 0.000 |
| 4 | the +Y face, X=1.375 (62% across from -X), at the level of the horizontal surface 1.000 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0 plane, area 5.56 (bbox); Z=0 plane, area 17.98 | 0.0114 | 0.298 / 0.000 |
| 5 | the +Y face, X=-1.375 (38% across from -X), at the level of the horizontal surface 1.000 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0 plane, area 5.56 (bbox); Z=0 plane, area 17.98 | 0.0114 | 0.298 / 0.000 |
| 6 | X=-1.833, facing +X, off any measured X plane, Y=-0.492 (91% across from -Y), at the level of the horizontal surface 2.600 above the base | faces +X, up +Z | Z=1.600 plane, area 28.85 | 0.0000 | 0.281 / 0.000 |
| 7 | X=1.833, facing -X, off any measured X plane, Y=-0.492 (91% across from -Y), at the level of the horizontal surface 2.600 above the base | faces -X, up +Z | Z=1.600 plane, area 28.85 | 0.0000 | 0.281 / 0.000 |
| 8 | Y=-5.003, facing -Y, off any measured Y plane, centred across it, at the level of the horizontal surface 2.600 above the base | faces -Y, up +Z | Z=1.600 plane, area 28.85 | 0.0000 | 0.184 / 0.000 |
| 9 | the -X face, Y=-0.492 (91% across from -Y), at the level of the horizontal surface 0.800 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-5.500 plane, area 0.59 (bbox); Z=-0.200 plane, area 9.54 | 0.0113 | 0.549 / 0.000 |
| 10 | the +X face, Y=-0.492 (91% across from -Y), at the level of the horizontal surface 0.800 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=5.500 plane, area 0.32 (bbox); Z=-0.200 plane, area 9.54 | 0.0114 | 0.549 / 0.000 |

#### Cylinder Big (Round, 4 magnets)

Audit entry: Cylinders and Cove corner pieces (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029F2, Cove 0x900029E4. Our bounds X -3.326..3.326, Y -3.326..3.326, Z -2.000..2.900. Halo 4 set placed on our piece: turned 90 deg; then moved onto measured features (axis_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.214 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -Y-facing plane at Y=-3.100, centred across it, at the level of the horizontal surface 4.000 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-3.100 plane, area 10.52; Z=2.000 plane, area 15.98 | 0.0283 | 0.214 / 0.214 |
| 2 | the -X-facing plane at X=-3.100, centred across it, at the level of the horizontal surface 4.300 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-3.100 plane, area 11.51; Z=2.300 plane, area 1.57 | 0.0282 | 0.214 / 0.214 |
| 3 | the +Y-facing plane at Y=3.100, centred across it, at the level of the horizontal surface 4.000 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=3.100 plane, area 10.52; Z=2.000 plane, area 15.98 | 0.0284 | 0.214 / 0.214 |
| 4 | the +X-facing plane at X=3.100, centred across it, at the level of the horizontal surface 4.300 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=3.100 plane, area 11.51; Z=2.300 plane, area 1.57 | 0.0283 | 0.214 / 0.214 |

#### Cylinder Small (Round, 4 magnets)

Audit entry: Cylinders and Cove corner pieces (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029F7, Cove 0x900029E9. Our bounds X -1.796..1.796, Y -1.796..1.796, Z -3.000..1.300. Halo 4 set placed on our piece: then moved onto measured features (axis_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.103 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -Y face, centred across it, at the level of the horizontal surface 4.000 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-1.796 plane, area 4.25 (bbox); Z=1.000 plane, area 5.11 | 0.0168 | 0.103 / 0.103 |
| 2 | the +Y face, centred across it, at the level of the horizontal surface 4.000 above the base (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.796 plane, area 2.40 (bbox); Z=1.000 plane, area 5.11 | 0.0169 | 0.103 / 0.103 |
| 3 | the -X face, centred across it, at the level of the horizontal surface 4.000 above the base | faces -X, up +Z | X=-1.796 plane, area 4.64 (bbox); Z=1.000 plane, area 5.11 | 0.0000 | 0.103 / 0.103 |
| 4 | the +X face, centred across it, at the level of the horizontal surface 4.000 above the base | faces +X, up +Z | X=1.796 plane, area 2.29 (bbox); Z=1.000 plane, area 5.11 | 0.0001 | 0.103 / 0.103 |

#### Dish (Round, 4 magnets)

Audit entry: Dish and Dish Door (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029FC, Cove 0x900029EE. Our bounds X -5.861..5.861, Y -5.852..0, Z -1.400..0.628. Halo 4 set placed on our piece: turned 270 deg; origin shifted by (0, -0.043, -0.117); then moved onto measured features (axis_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.061 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0 plane, area 2.32 (bbox); Z=-1.400 bbox extreme, no flat face | 0.0266 | 0.000 / 0.000 |
| 2 | the +Y face, centred across it, at 1.497 above the base (74% of the height) **Audited upper reference (Dish and Dish Door): on the shared front plane Y=0, centred, at the height of the source central cap's upper construction level (1.497 above the base). Intentionally in open space; the audit proves the 0.508 clearance with rays.** | faces +Y, up +Z | Y=0 plane, area 2.32 (bbox) | 0.5077 | 0.000 / 0.000 |
| 3 | the -Y face, centred across it, at 0.820 above the base (40% of the height) | faces -Y, up +Z | Y=-5.852 bbox extreme, no flat face | 0.0000 | 0.061 / 0.061 |
| 4 | the -Y face, centred across it, at 1.293 above the base (64% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-5.852 bbox extreme, no flat face | 0.0237 | 0.061 / 0.061 |

#### Dish Antenna (Round, 12 magnets)

Audit entry: Different profiles and multiple nodes (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029A0, Cove 0x90002994. Our bounds X -2.645..4.800, Y -4.295..4.295, Z -0.700..4.300. Halo 4 set placed on our piece: then moved onto measured features (radial_profile).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | surface facing 120 deg from +X toward +Y; X=-0.374 (30% across from -X), Y=0.649 (58% across from -Y), at 4.980 above the base (100% of the height) | faces horizontal at 120 deg from +X toward +Y, up +Z | no measured axis-aligned plane | 0.0000 | 0.012 / 0.012 |
| 2 | the +X-facing plane at X=0.749, centred across it, at 4.980 above the base (100% of the height) | faces +X, up +Z | X=0.749 plane, area 0.10 | 0.0001 | 0.012 / 0.012 |
| 3 | surface facing -120 deg from +X toward +Y; X=-0.374 (30% across from -X), Y=-0.649 (42% across from -Y), at 4.980 above the base (100% of the height) | faces horizontal at -120 deg from +X toward +Y, up +Z | no measured axis-aligned plane | 0.0001 | 0.012 / 0.012 |
| 4 | surface facing 120 deg from +X toward +Y; X=-0.961 (23% across from -X), Y=1.664 (69% across from -Y), at 3.741 above the base (75% of the height) | faces horizontal at 120 deg from +X toward +Y, up +Z | no measured axis-aligned plane | 0.0000 | 0.002 / 0.002 |
| 5 | surface facing 120 deg from +X toward +Y; X=-2.400 (3% across from -X), Y=4.157 (98% across from -Y), at 0.775 above the base (15% of the height) | faces horizontal at 120 deg from +X toward +Y, up +Z | no measured axis-aligned plane | 0.0000 | 0.048 / 0.048 |
| 6 | surface facing -60 deg from +X toward +Y; X=-1.353 (17% across from -X), Y=2.343 (77% across from -Y), at 0.398 above the base (8% of the height) | faces horizontal at -60 deg from +X toward +Y, up +Z | no measured axis-aligned plane | 0.0000 | 0.005 / 0.005 |
| 7 | X=1.922, facing +X, off any measured X plane, centred across it, at 3.741 above the base (75% of the height) | faces +X, up +Z | no measured axis-aligned plane | 0.0000 | 0.002 / 0.002 |
| 8 | the +X face, centred across it, at 0.775 above the base (15% of the height) | faces +X, up +Z | X=4.800 bbox extreme, no flat face | 0.0001 | 0.048 / 0.048 |
| 9 | X=2.705, facing -X, off any measured X plane, centred across it, at 0.398 above the base (8% of the height) | faces -X, up +Z | no measured axis-aligned plane | 0.0001 | 0.005 / 0.005 |
| 10 | surface facing -120 deg from +X toward +Y; X=-0.961 (23% across from -X), Y=-1.664 (31% across from -Y), at 3.741 above the base (75% of the height) | faces horizontal at -120 deg from +X toward +Y, up +Z | no measured axis-aligned plane | 0.0000 | 0.002 / 0.002 |
| 11 | surface facing -120 deg from +X toward +Y; X=-2.400 (3% across from -X), Y=-4.157 (2% across from -Y), at 0.775 above the base (15% of the height) | faces horizontal at -120 deg from +X toward +Y, up +Z | no measured axis-aligned plane | 0.0001 | 0.048 / 0.048 |
| 12 | surface facing 60 deg from +X toward +Y; X=-1.353 (17% across from -X), Y=-2.343 (23% across from -Y), at 0.398 above the base (8% of the height) | faces horizontal at 60 deg from +X toward +Y, up +Z | no measured axis-aligned plane | 0.0001 | 0.005 / 0.005 |

#### Dish Door (Round, 2 magnets)

Audit entry: Dish and Dish Door (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x90002A01, Cove 0x900029F3. Our bounds X -5.861..5.861, Y -5.761..0, Z -1.400..0.628. Halo 4 set placed on our piece: turned 270 deg; origin shifted by (0, -0.043, -1.330); then moved onto measured features (axis_levels).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0 plane, area 2.32 (bbox); Z=-1.400 bbox extreme, no flat face | 0.0266 | 0.040 / 0.040 |
| 2 | the +Y face, centred across it, at 1.497 above the base (74% of the height) **Audited upper reference (Dish and Dish Door): on the shared front plane Y=0, centred, at the height of the source central cap's upper construction level (1.497 above the base). Intentionally in open space; the audit proves the 0.508 clearance with rays.** | faces +Y, up +Z | Y=0 plane, area 2.32 (bbox) | 0.5077 | 0.001 / 0.001 |

#### Ramp, Circular, Large (Round, 5 magnets)

Audit entry: Final transform pass (equation checks of the anchor_completion.json transform, not a detailed feature proof) (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002B5E. Our bounds X 0.001..4.002, Y -3.997..4.002, Z 0..2.550. Halo 4 set placed on our piece: centred on our bounding box, then stretched to our bounds per axis, then projected onto our mesh.

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.203 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -X face, Y=2.656 (83% across from -Y), at the level of the horizontal surface 0.250 above the base (on the construction planes; our mesh is bevelled or trimmed here) **Position authored by this project from our construction planes (Final transform pass, anchor_completion.json), kept as audited; the Halo 4 point mapped by the bounds fit is the "fitted" distance.** | faces -X, up +Z | X=0.002 plane, area 0.30 (bbox); Z=0.250 plane, area 0.40 | 0.0112 | 0.150 / 0.013 |
| 2 | the -X face, Y=-2.557 (18% across from -Y), at top (on the construction planes; our mesh is bevelled or trimmed here) **Position authored by this project from our construction planes (Final transform pass, anchor_completion.json), kept as audited; the Halo 4 point mapped by the bounds fit is the "fitted" distance.** | faces -X, up +Z | X=0.002 plane, area 0.30 (bbox); Z=2.550 plane, area 0.41 (bbox) | 0.0123 | 0.200 / 0.001 |
| 3 | the +X face, centred across it, at 1.037 above the base (41% of the height) **Position authored by this project from our construction planes (Final transform pass, anchor_completion.json), kept as audited; the Halo 4 point mapped by the bounds fit is the "fitted" distance.** | faces +X, up +Z | X=4.000 bbox extreme, no flat face | 0.0015 | 0.203 / 0.195 |
| 4 | the -X face, at the +Y extreme, at the level of the horizontal surface 2.150 above the base (on the construction planes; our mesh is bevelled or trimmed here) **Position authored by this project from our construction planes (Final transform pass, anchor_completion.json), kept as audited; the Halo 4 point mapped by the bounds fit is the "fitted" distance.** | faces -X, up +Z | X=0.002 plane, area 0.30 (bbox); Y=4.000 bbox extreme, no flat face; Z=2.150 plane, area 11.28 | 0.0163 | 0.155 / 0.346 |
| 5 | the -X face, Y=-4.000 (-0% across from -Y), at the level of the horizontal surface 2.150 above the base (on the construction planes; our mesh is bevelled or trimmed here) **Position authored by this project from our construction planes (Final transform pass, anchor_completion.json), kept as audited; the Halo 4 point mapped by the bounds fit is the "fitted" distance.** | faces -X, up +Z | X=0.002 plane, area 0.30 (bbox); Z=2.150 plane, area 11.28 | 0.0205 | 0.155 / 0.346 |

#### Ramp, Circular, Small (Round, 5 magnets)

Audit entry: Final transform pass (equation checks of the anchor_completion.json transform, not a detailed feature proof) (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002B63. Our bounds X -2.300..0, Y -2.298..2.298, Z 0.001..2.192. Halo 4 set placed on our piece: centred on our bounding box after a -90 deg turn, then stretched to our bounds per axis, then projected onto our mesh.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +X face, Y=1.571 (84% across from -Y), at 0.699 above the base (32% of the height) (on the construction planes; our mesh is bevelled or trimmed here) **Position authored by this project from our construction planes (Final transform pass, anchor_completion.json), kept as audited; the Halo 4 point mapped by the bounds fit is the "fitted" distance.** | faces +X, up +Z | X=0 plane, area 1.10 (bbox) | 0.0135 | 0.004 / 0.004 |
| 2 | the +X face, Y=-1.571 (16% across from -Y), at 1.699 above the base (78% of the height) (on the construction planes; our mesh is bevelled or trimmed here) **Position authored by this project from our construction planes (Final transform pass, anchor_completion.json), kept as audited; the Halo 4 point mapped by the bounds fit is the "fitted" distance.** | faces +X, up +Z | X=0 plane, area 1.10 (bbox) | 0.0213 | 0.006 / 0.007 |
| 3 | the +X face, Y=1.571 (84% across from -Y), at 0.499 above the base (23% of the height) (on the construction planes; our mesh is bevelled or trimmed here) **Position authored by this project from our construction planes (Final transform pass, anchor_completion.json), kept as audited; the Halo 4 point mapped by the bounds fit is the "fitted" distance.** | faces +X, up +Z | X=0 plane, area 1.10 (bbox) | 0.0168 | 0.001 / 0.002 |
| 4 | the +X face, Y=-1.571 (16% across from -Y), at 1.499 above the base (68% of the height) (on the construction planes; our mesh is bevelled or trimmed here) **Position authored by this project from our construction planes (Final transform pass, anchor_completion.json), kept as audited; the Halo 4 point mapped by the bounds fit is the "fitted" distance.** | faces +X, up +Z | X=0 plane, area 1.10 (bbox) | 0.0102 | 0.003 / 0.004 |
| 5 | the +X face, centred across it, at 1.155 above the base (53% of the height) (on the construction planes; our mesh is bevelled or trimmed here) **Position authored by this project from our construction planes (Final transform pass, anchor_completion.json), kept as audited; the Halo 4 point mapped by the bounds fit is the "fitted" distance.** | faces +X, up +Z | X=0 plane, area 1.10 (bbox) | 0.0174 | 0.002 / 0.002 |

#### Bunker Covered (Structure, 2 magnets)

Audit entry: Full Base Round and compound entrance proofs (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029D4, Cove 0x900029C6. Our bounds X -1.559..1.559, Y -1.250..1.200, Z -1.000..1.000. Halo 4 set placed on our piece: origin shifted by (0, -0.024, -0.500); stretched per axis by (1, 0.9796, 1); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -Y-facing plane at Y=-1.200, centred across it, at 0.500 above the base (25% of the height) | faces -Y, up -X | Y=-1.200 plane, area 0.30 | 0.0000 | 0.024 / 0.000 |
| 2 | the +Y face, centred across it, at mid-height (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.200 plane, area 0.04 (bbox); Z=0 plane, area 2.74 | 0.0071 | 0.026 / 0.000 |

#### Bunker Full (Structure, 4 magnets)

Audit entry: Bunker Full (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029D9, Cove 0x900029CB. Our bounds X -1.526..2.513, Y -1.526..2.514, Z -0.900..1.100. Halo 4 set placed on our piece: turned 45 deg; then moved onto measured features (axis_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.339 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | surface facing 45 deg from +X toward +Y; X=1.113 (65% across from -X), Y=1.113 (65% across from -Y), at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces horizontal at 45 deg from +X toward +Y, up +Z | Z=-0.900 plane, area 10.88 (bbox) | 0.0281 | 0.337 / 0.337 |
| 2 | surface facing 45 deg from +X toward +Y; X=-0.805 (18% across from -X), Y=-0.805 (18% across from -Y), at top (on the construction planes; our mesh is bevelled or trimmed here) | faces horizontal at 45 deg from +X toward +Y, up +Z | Z=1.100 plane, area 3.12 (bbox) | 0.0162 | 0.318 / 0.318 |
| 3 | surface facing 45 deg from +X toward +Y; X=-0.805 (18% across from -X), Y=-0.805 (18% across from -Y), at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces horizontal at 45 deg from +X toward +Y, up +Z | Z=-0.900 plane, area 10.88 (bbox) | 0.0174 | 0.320 / 0.320 |
| 4 | surface facing 45 deg from +X toward +Y; X=1.113 (65% across from -X), Y=1.113 (65% across from -Y), at top (on the construction planes; our mesh is bevelled or trimmed here) | faces horizontal at 45 deg from +X toward +Y, up +Z | Z=1.100 plane, area 3.12 (bbox) | 0.0281 | 0.339 / 0.339 |

#### Bunker Low (Structure, 2 magnets)

Audit entry: Full Base Round and compound entrance proofs (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029DE, Cove 0x900029D0. Our bounds X -1.569..1.569, Y -1.250..1.200, Z -0.860..0.960. Halo 4 set placed on our piece: origin shifted by (0, -0.024, -0.350); stretched per axis by (1, 0.9796, 1); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -Y-facing plane at Y=-1.200, centred across it, at 0.510 above the base (28% of the height) | faces -Y, up +Z | Y=-1.200 plane, area 0.30 | 0.0000 | 0.024 / 0.000 |
| 2 | the +Y face, centred across it, at the level of the horizontal surface 1.010 above the base | faces +Y, up +Z | Y=1.200 plane, area 0.04 (bbox); Z=0.150 plane, area 2.74 | 0.0000 | 0.026 / 0.000 |

#### Bunker Stair (Structure, 11 magnets)

Audit entry: Final transform pass (equation checks of the anchor_completion.json transform, not a detailed feature proof) (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029E3, Cove 0x900029D5. Our bounds X -2.901..1.830, Y -2.400..2.664, Z -1.000..2.300. Halo 4 set placed on our piece: then moved onto measured features (position_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.903 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -X face, Y=1.400 (75% across from -Y), at 0.500 above the base (15% of the height) | faces -X, up +Z | X=-2.900 plane, area 7.83 (bbox) | 0.0000 | 0.822 / 0.822 |
| 2 | the -X face, Y=1.400 (75% across from -Y), at bottom | faces -X, up +Z | X=-2.900 plane, area 7.83 (bbox); Z=-1.000 plane, area 5.35 (bbox) | 0.0000 | 0.841 / 0.841 |
| 3 | the -Y face, on the measured X=-0.300 plane, at bottom | faces -Y, up +Z | X=-0.300 plane, area 4.67; Y=-2.400 plane, area 10.10 (bbox); Z=-1.000 plane, area 5.35 (bbox) | 0.0000 | 0.848 / 0.848 |
| 4 | the -X face, Y=1.400 (75% across from -Y), at the level of the horizontal surface 3.000 above the base | faces -X, up +Z | X=-2.900 plane, area 7.83 (bbox); Z=2.000 plane, area 15.04 | 0.0000 | 0.828 / 0.828 |
| 5 | the +Y-facing plane at Y=2.600, on the measured X=-0.300 plane, at bottom | faces +Y, up +Z | X=-0.300 plane, area 4.67; Y=2.600 plane, area 5.69; Z=-1.000 plane, area 5.35 (bbox) | 0.0000 | 0.875 / 0.875 |
| 6 | the +Y-facing plane at Y=2.600, on the measured X=-0.300 plane, at the level of the horizontal surface 3.000 above the base | faces +Y, up +Z | X=-0.300 plane, area 4.67; Y=2.600 plane, area 5.69; Z=2.000 plane, area 15.04 | 0.0001 | 0.863 / 0.863 |
| 7 | the +X-facing plane at X=1.800, Y=1.038 (68% across from -Y), at the level of the horizontal surface 3.000 above the base | faces +X, up +Z | X=1.800 plane, area 9.16; Z=2.000 plane, area 15.04 | 0.0000 | 0.822 / 0.822 |
| 8 | X=1.825, facing +X, off any measured X plane, Y=1.038 (68% across from -Y), at 0.030 above the base (1% of the height) | faces +X, up +Z | no measured axis-aligned plane | 0.0000 | 0.872 / 0.872 |
| 9 | X=1.825, facing +X, off any measured X plane, Y=-1.567 (16% across from -Y), at 0.030 above the base (1% of the height) **Audited virtual under-stair foot reference (Final transform pass): on the +X foot plane, at the foot level, in the open space under the stair, 0.57 from material. Kept deliberately.** | faces +X, up +Z | no measured axis-aligned plane | 0.5675 | 0.903 / 0.903 |
| 10 | the +X-facing plane at X=1.800, Y=-1.567 (16% across from -Y), at the level of the horizontal surface 3.000 above the base | faces +X, up +Z | X=1.800 plane, area 9.16; Z=2.000 plane, area 15.04 | 0.0000 | 0.856 / 0.856 |
| 11 | the -Y face, on the measured X=-0.300 plane, at top | faces -Y, up +Z | X=-0.300 plane, area 4.67; Y=-2.400 plane, area 10.10 (bbox); Z=2.300 plane, area 1.82 (bbox) | 0.0001 | 0.836 / 0.836 |

#### Cannon, Man (Structure, 2 magnets)

Audit entry: Final transform pass (equation checks of the anchor_completion.json transform, not a detailed feature proof) (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0xFA981922, Cove 0xFA981922. Our bounds X -0.483..0.483, Y -0.725..0.113, Z -0.010..0.160. Halo 4 set placed on our piece: centred on our bounding box after a -90 deg turn, then stretched to our bounds per axis; both Halo 4 points kept at that fitted position, not projected.

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.705 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | Y=-0.728, facing -Y, off any measured Y plane, X=-0.012 (49% across from -X), at bottom **Audited reference below the visible base (Final transform pass; anchor_completion.json keeps the bounds-fitted Halo 4 point because projecting it into our V-shaped housing would change it). 0.25 from material.** | faces -Y, up +Z | Z=-0.013 bbox extreme, no flat face | 0.2498 | 0.705 / 0.000 |
| 2 | Y=0.050, facing +Y, off any measured Y plane, X=-0.012 (49% across from -X), at bottom **Audited reference below the visible base (Final transform pass; anchor_completion.json keeps the bounds-fitted Halo 4 point because projecting it into our V-shaped housing would change it). 0.19 from material.** | faces +Y, up +Z | Z=-0.013 bbox extreme, no flat face | 0.1945 | 0.634 / 0.000 |

#### Cover, 2 (Structure, 5 magnets)

Audit entry: Full Base Round and compound entrance proofs (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x90002996, Cove 0x9000298A. Our bounds X -1.100..1.400, Y -2.010..2.010, Z -1.200..0.900. Halo 4 set placed on our piece: origin shifted by (0, 0, -0.100); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +X face, centred across it, at 2.093 above the base (100% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=1.400 plane, area 0.34 (bbox) | 0.0071 | 0.000 / 0.000 |
| 2 | the +Y face, X=1.235 (93% across from -X), at 1.993 above the base (95% of the height) | faces +Y, up +Z | Y=2.010 plane, area 0.45 (bbox) | 0.0018 | 0.010 / 0.010 |
| 3 | the -Y face, X=1.235 (93% across from -X), at 1.993 above the base (95% of the height) | faces -Y, up +Z | Y=-2.010 plane, area 0.95 (bbox) | 0.0018 | 0.010 / 0.010 |
| 4 | the +X-facing plane at X=-0.400, Y=1.850 (96% across from -Y), at 0.193 above the base (9% of the height) | faces +X, up +Z | X=-0.400 plane, area 0.06 | 0.0000 | 0.000 / 0.000 |
| 5 | the +X-facing plane at X=-0.400, Y=-1.850 (4% across from -Y), at 0.193 above the base (9% of the height) | faces +X, up +Z | X=-0.400 plane, area 0.06 | 0.0000 | 0.000 / 0.000 |

#### Pyramid (Structure, 5 magnets)

Audit entry: Pyramid (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002AF6. Our bounds X -7.500..7.500, Y -4.488..3.012, Z -2.000..1.530. Halo 4 set placed on our piece: turned 180 deg; then moved onto measured features (axis_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 1.032 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -X face, Y=2.262 (90% across from -Y), at 1.990 above the base (56% of the height) | faces -X, up +Z | X=-7.500 plane, area 0.56 (bbox) | 0.0000 | 0.750 / 0.750 |
| 2 | the -Y face, centred across it, at 1.990 above the base (56% of the height) | faces -Y, up +Z | Y=-4.488 plane, area 1.31 (bbox) | 0.0000 | 0.553 / 0.553 |
| 3 | the +X face, Y=2.262 (90% across from -Y), at 1.990 above the base (56% of the height) | faces +X, up +Z | X=7.500 plane, area 0.56 (bbox) | 0.0000 | 0.750 / 0.750 |
| 4 | the +Y face, centred across it, at 3.512 above the base (99% of the height) | faces +Y, up +Z | Y=3.012 plane, area 7.22 (bbox) | 0.0000 | 1.016 / 1.016 |
| 5 | the +Y face, centred across it, at 0.190 above the base (5% of the height) | faces +Y, up +Z | Y=3.012 plane, area 7.22 (bbox) | 0.0000 | 1.032 / 1.032 |

#### Room Double (Structure, 2 magnets)

Audit entry: Ramped Platform, Room Double and Large Walkway (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029A5, Cove 0x90002999. Our bounds X -2.794..2.704, Y -1.900..1.991, Z 0..2.596. Halo 4 set placed on our piece: then moved onto measured features (axis_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.156 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -X face, Y=0.692 (67% across from -Y), at the level of the horizontal surface 0.297 above the base | faces -X, up +Z | X=-2.794 plane, area 3.18 (bbox); Z=0.297 plane, area 11.22 | 0.0000 | 0.147 / 0.147 |
| 2 | X=1.800, facing -X, off any measured X plane, at the +Y extreme, at the level of the horizontal surface 0.297 above the base | faces -X, up +Z | Y=1.991 plane, area 4.79 (bbox); Z=0.297 plane, area 11.22 | 0.0000 | 0.156 / 0.156 |

#### Room Triple (Structure, 6 magnets)

Audit entry: Room Triple (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029AC, Cove 0x9000299E. Our bounds X -6.100..6.100, Y -2.950..2.950, Z -1.498..2.204. Halo 4 set placed on our piece: then moved onto measured features (position_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.271 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -Y-facing plane at Y=-1.950, centred across it, at the level of the horizontal surface 1.002 above the base | faces -Y, up +Z | Y=-1.950 plane, area 6.58; Z=-0.496 plane, area 0.62 | 0.0000 | 0.257 / 0.257 |
| 2 | X=-4.879, facing -X, off any measured X plane, Y=1.248 (71% across from -Y), at the level of the horizontal surface 0.901 above the base | faces -X, up +Z | Z=-0.596 plane, area 16.45 | 0.0000 | 0.271 / 0.271 |
| 3 | the +Y-facing plane at Y=2.450, X=-3.496 (21% across from -X), at the level of the horizontal surface 0.902 above the base | faces +Y, up +Z | Y=2.450 plane, area 11.91; Z=-0.596 plane, area 16.45 | 0.0000 | 0.245 / 0.245 |
| 4 | the +Y-facing plane at Y=2.450, centred across it, at the level of the horizontal surface 1.002 above the base | faces +Y, up +Z | Y=2.450 plane, area 11.91; Z=-0.496 plane, area 0.62 | 0.0000 | 0.237 / 0.237 |
| 5 | the +Y-facing plane at Y=2.450, X=3.496 (79% across from -X), at the level of the horizontal surface 0.902 above the base | faces +Y, up +Z | Y=2.450 plane, area 11.91; Z=-0.596 plane, area 16.45 | 0.0000 | 0.245 / 0.245 |
| 6 | X=4.878, facing +X, off any measured X plane, Y=1.248 (71% across from -Y), at the level of the horizontal surface 0.901 above the base | faces +X, up +Z | Z=-0.596 plane, area 16.45 | 0.0000 | 0.256 / 0.256 |

#### Teleport Frame (Structure, 4 magnets)

Audit entry: 45-degree corner and Teleport Frame (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029B1, Cove 0x900029A3. Our bounds X -0.711..0.711, Y -0.688..0.690, Z -0.083..1.217. Halo 4 set placed on our piece: then moved onto measured features (axis_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.207 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +Y face | faces +Y, up +Z | Y=0.690 bbox extreme, no flat face; Z=-0.083 plane, area 1.74 (bbox) | 0.0005 | 0.084 / 0.084 |
| 2 | middle of the bottom edge of the -X face | faces -X, up +Z | X=-0.711 plane, area 0.04 (bbox); Z=-0.083 plane, area 1.74 (bbox) | 0.0000 | 0.207 / 0.207 |
| 3 | middle of the bottom edge of the -Y face | faces -Y, up +Z | Y=-0.688 bbox extreme, no flat face; Z=-0.083 plane, area 1.74 (bbox) | 0.0004 | 0.084 / 0.084 |
| 4 | middle of the bottom edge of the +X face | faces +X, up +Z | X=0.711 plane, area 0.03 (bbox); Z=-0.083 plane, area 1.74 (bbox) | 0.0000 | 0.207 / 0.207 |

#### Tower (Structure, 5 magnets)

Audit entry: Tower (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029B6, Cove 0x900029A8. Our bounds X -2.400..2.400, Y -2.401..2.401, Z 0..4.700. Halo 4 set placed on our piece: then moved onto measured features (position_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.609 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +Y-facing plane at Y=2.201, X=1.586 (83% across from -X), at the level of the horizontal surface 0.400 above the base | faces +Y, up +Z | Y=2.201 plane, area 3.56; Z=0.400 plane, area 5.19 | 0.0000 | 0.609 / 0.609 |
| 2 | the +Y-facing plane at Y=2.201, on the measured X=-0.700 plane, at the level of the horizontal surface 0.396 above the base | faces +Y, up +Z | X=-0.700 plane, area 0.09; Y=2.201 plane, area 3.56; Z=0.396 plane, area 3.66 | 0.0000 | 0.517 / 0.517 |
| 3 | the -X-facing plane at X=-1.996, Y=0.701 (65% across from -Y), at the level of the horizontal surface 0.400 above the base | faces -X, up +Z | X=-1.996 plane, area 4.47; Z=0.400 plane, area 5.19 | 0.0000 | 0.488 / 0.488 |
| 4 | the -X face, Y=0.708 (65% across from -Y), at the level of the horizontal surface 2.399 above the base | faces -X, up +Z | X=-2.400 plane, area 2.66 (bbox); Z=2.400 plane, area 8.23 | 0.0000 | 0.567 / 0.567 |
| 5 | the -Y-facing plane at Y=-1.699, on the measured X=-0.700 plane, at the level of the horizontal surface 0.396 above the base | faces -Y, up +Z | X=-0.700 plane, area 0.09; Y=-1.699 plane, area 2.59; Z=0.396 plane, area 3.66 | 0.0000 | 0.517 / 0.517 |

#### Tower 3 Story (Structure, 10 magnets)

Audit entry: Final transform pass (equation checks of the anchor_completion.json transform, not a detailed feature proof) (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029BB, Cove 0x900029AD. Our bounds X -3.350..3.350, Y -2.500..2.500, Z -1.351..4.849. Halo 4 set placed on our piece: centred on our bounding box, then stretched to our bounds per axis, then projected onto our mesh.

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.054 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -Y-facing plane at Y=-2.000, X=-0.813 (38% across from -X), at the level of the horizontal surface 0.669 above the base | faces -Y, up +Z | Y=-2.000 plane, area 18.99; Z=-0.681 plane, area 6.36 | 0.0000 | 0.054 / 0.054 |
| 2 | the -Y-facing plane at Y=-2.000, X=-0.813 (38% across from -X), at 2.675 above the base (43% of the height) | faces -Y, up +Z | Y=-2.000 plane, area 18.99 | 0.0000 | 0.054 / 0.054 |
| 3 | the +Y-facing plane at Y=2.000, X=-0.813 (38% across from -X), at the level of the horizontal surface 0.669 above the base | faces +Y, up +Z | Y=2.000 plane, area 18.99; Z=-0.681 plane, area 6.36 | 0.0000 | 0.054 / 0.054 |
| 4 | the +Y-facing plane at Y=2.000, X=-0.813 (38% across from -X), at 2.673 above the base (43% of the height) | faces +Y, up +Z | Y=2.000 plane, area 18.99 | 0.0000 | 0.054 / 0.054 |
| 5 | the -X face, centred across it, at 0.664 above the base (11% of the height) | faces -X, up +Z | X=-3.350 plane, area 9.87 (bbox) | 0.0000 | 0.018 / 0.018 |
| 6 | X=-3.343, facing -X, off any measured X plane, centred across it, at 2.687 above the base (43% of the height) | faces -X, up +Z | no measured axis-aligned plane | 0.0000 | 0.016 / 0.016 |
| 7 | X=-2.332, facing -X, off any measured X plane, centred across it, at the level of the horizontal surface 5.197 above the base | faces -X, up +Z | Z=3.849 plane, area 3.61 | 0.0000 | 0.005 / 0.005 |
| 8 | the +X-facing plane at X=3.302, centred across it, at 4.659 above the base (75% of the height) | faces +X, up +Z | X=3.300 plane, area 0.27 | 0.0000 | 0.039 / 0.039 |
| 9 | X=3.256, facing +X, off any measured X plane, centred across it, at 3.011 above the base (49% of the height) | faces +X, up +Z | no measured axis-aligned plane | 0.0000 | 0.037 / 0.037 |
| 10 | the +X-facing plane at X=2.650, centred across it, at 0.683 above the base (11% of the height) | faces +X, up +Z | X=2.650 plane, area 6.52 | 0.0000 | 0.038 / 0.038 |

#### Tower Tall (Structure, 10 magnets)

Audit entry: Final transform pass (equation checks of the anchor_completion.json transform, not a detailed feature proof) (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029C0, Cove 0x900029B2. Our bounds X -2.000..2.000, Y -2.704..2.796, Z 0..6.324. Halo 4 set placed on our piece: centred on our bounding box, then stretched to our bounds per axis, then projected onto our mesh.

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.578 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -Y-facing plane at Y=-0.923, X=-1.172 (21% across from -X), at bottom | faces -Y, up +Z | Y=-0.920 plane, area 0.04; Z=0.002 plane, area 1.13 (bbox) | 0.0000 | 0.339 / 0.002 |
| 2 | Y=-1.047, facing -Y, off any measured Y plane, X=-1.172 (21% across from -X), at 1.542 above the base (24% of the height) | faces -Y, up +Z | no measured axis-aligned plane | 0.0000 | 0.340 / 0.011 |
| 3 | Y=2.776, facing +Y, off any measured Y plane, X=-0.020 (50% across from -X), at the level of the horizontal surface 3.301 above the base | faces +Y, up +Z | Z=3.301 plane, area 0.64 | 0.0000 | 0.109 / 0.086 |
| 4 | the +Y-facing plane at Y=1.597, X=-0.749 (31% across from -X), at bottom | faces +Y, up +Z | Y=1.596 plane, area 1.65; Z=0.002 plane, area 1.13 (bbox) | 0.0000 | 0.331 / 0.217 |
| 5 | the -X face, Y=0.365 (56% across from -Y), at bottom | faces -X, up +Z | X=-2.000 plane, area 4.20 (bbox); Z=0.002 plane, area 1.13 (bbox) | 0.0000 | 0.578 / 0.002 |
| 6 | X=0.483, facing +X, off any measured X plane, on the measured Y=0.134 plane, at bottom | faces +X, up +Z | Y=0.135 plane, area 0.07; Z=0.002 plane, area 1.13 (bbox) | 0.0000 | 0.140 / 0.002 |
| 7 | X=0.467, facing +X, off any measured X plane, Y=1.945 (85% across from -Y), at 4.533 above the base (72% of the height) | faces +X, up +Z | no measured axis-aligned plane | 0.0000 | 0.140 / 0.016 |
| 8 | the -Y-facing plane at Y=-2.504, X=-0.553 (36% across from -X), at the level of the horizontal surface 4.503 above the base | faces -Y, up +Z | Y=-2.504 plane, area 0.59; Z=4.503 plane, area 0.62 | 0.0000 | 0.168 / 0.015 |
| 9 | X=-1.534, facing -X, off any measured X plane, Y=0.372 (56% across from -Y), at the level of the horizontal surface 4.474 above the base | faces -X, up +Z | Z=4.473 plane, area 0.43 | 0.0000 | 0.445 / 0.044 |
| 10 | the -Y-facing plane at Y=-1.104, X=0.031 (51% across from -X), at 6.193 above the base (98% of the height) | faces -Y, up +Z | Y=-1.104 plane, area 1.58 | 0.0000 | 0.042 / 0.059 |

#### Antenna (Strut / column, 3 magnets)

Audit entry: Antenna and Base Strut (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x90002900, Cove 0x90002920. Our bounds X -0.692..0.510, Y -0.470..0.470, Z 0..3.504. Halo 4 set placed on our piece: turned 270 deg.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the -X face, centred across it, at 0.595 above the base (17% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up -Y | X=-0.692 bbox extreme, no flat face; Y=0 plane, area 0.13 | 0.0151 | 0.000 / 0.000 |
| 2 | X=0.504, facing +X, off any measured X plane, centred across it, at 0.595 above the base (17% of the height) (near our mesh) | faces +X, up -Y | Y=0 plane, area 0.13 | 0.0118 | 0.000 / 0.000 |
| 3 | bottom face (frame facing -Z), X=0 (58% across from -X), centred in Y | faces -Z, up -Y | Y=0 plane, area 0.13; Z=0 plane, area 0.03 (bbox) | 0.0000 | 0.000 / 0.000 |

#### Arch Brace (Strut / column, 5 magnets)

Audit entry: Arch Brace construction correction (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x9000291B, Cove 0x90002926. Our bounds X -1.900..3.100, Y -1.200..1.200, Z -1.000..4.900. Halo 4 set placed on our piece: turned 180 deg; origin shifted by (0.200, -0.050, -1.000); then moved onto measured features (coordinate_planes, axis_levels).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +X-facing plane at X=2.900, centred across it, at the level of the horizontal surface 4.100 above the base | faces +X, up +Z | X=2.900 plane, area 0.24; Z=3.100 plane, area 1.05 | 0.0000 | 0.000 / 0.000 |
| 2 | the +X-facing plane at X=1.900, centred across it, at the level of the horizontal surface 1.900 above the base | faces +X, up +Z | X=1.900 plane, area 0.24; Z=0.900 plane, area 3.36 | 0.0001 | 0.000 / 0.000 |
| 3 | the +Y face, X=0.313 (44% across from -X), at 0.250 above the base (4% of the height) | faces +Y, up +Z | Y=1.200 plane, area 1.34 (bbox) | 0.0001 | 0.029 / 0.029 |
| 4 | the -Y face, X=0.313 (44% across from -X), at 0.250 above the base (4% of the height) | faces -Y, up +Z | Y=-1.200 plane, area 3.37 (bbox) | 0.0000 | 0.026 / 0.026 |
| 5 | the -X face, centred across it, at the level of the horizontal surface 1.900 above the base | faces -X, up +Z | X=-1.900 plane, area 0.12 (bbox); Z=0.900 plane, area 3.36 | 0.0000 | 0.000 / 0.000 |

#### Base Strut (Strut / column, 7 magnets)

Audit entry: Antenna and Base Strut (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x90002969, Cove 0x9000295D. Our bounds X -0.500..0.500, Y -0.800..0.800, Z -1.992..2.200. Halo 4 set placed on our piece: origin shifted by (0, -0.250, -0.100); then moved onto measured features (axis_levels).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | bottom face (frame facing -Z), centred in X, Y=-0.250 (34% across from -Y) | faces -Z, up -Y | Z=-1.992 plane, area 0.94 (bbox) | 0.0000 | 0.032 / 0.032 |
| 2 | the +Y face, centred across it, at 1.497 above the base (36% of the height) | faces +Y, up +Z | Y=0.800 plane, area 2.40 (bbox) | 0.0000 | 0.001 / 0.001 |
| 3 | the +Y face, centred across it, at 3.260 above the base (78% of the height) | faces +Y, up +Z | Y=0.800 plane, area 2.40 (bbox) | 0.0000 | 0.001 / 0.001 |
| 4 | the +Y-facing plane at Y=0.283, centred across it, at 0.132 above the base (3% of the height) | faces +Y, up +Z | Y=0.284 plane, area 0.23 | 0.0000 | 0.001 / 0.001 |
| 5 | the -Y-facing plane at Y=-0.780, centred across it, at 0.132 above the base (3% of the height) | faces -Y, up +Z | Y=-0.780 plane, area 0.23 | 0.0000 | 0.001 / 0.001 |
| 6 | the +X-facing plane at X=0.479, Y=-0.248 (34% across from -Y), at 0.132 above the base (3% of the height) | faces +X, up +Z | X=0.478 plane, area 0.26 | 0.0000 | 0.001 / 0.001 |
| 7 | the -X-facing plane at X=-0.479, Y=-0.248 (34% across from -Y), at 0.132 above the base (3% of the height) | faces -X, up +Z | X=-0.478 plane, area 0.26 | 0.0000 | 0.001 / 0.001 |

#### Brace (Strut / column, 6 magnets)

Audit entry: Brace and Crenel Full (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x9000296E, Cove 0x90002962. Our bounds X -0.274..0.274, Y -1.529..1.529, Z -1.501..1.499. Halo 4 set placed on our piece: origin shifted by (-0.150, 0, 0); then moved onto measured features (coordinate_planes, axis_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.299 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the top edge of the -X-facing plane at X=-0.050 | faces -X, up +Z | X=-0.050 plane, area 0.04; Z=1.499 plane, area 0.12 (bbox) | 0.0000 | 0.295 / 0.295 |
| 2 | the -X-facing plane at X=-0.250, on the measured Y=0.900 plane, at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-0.250 plane, area 3.11; Y=0.900 plane, area 0.60; Z=-1.501 plane, area 0.54 (bbox) | 0.0106 | 0.299 / 0.299 |
| 3 | the -X-facing plane at X=-0.250, on the measured Y=-0.900 plane, at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-0.250 plane, area 3.11; Y=-0.900 plane, area 0.60; Z=-1.501 plane, area 0.54 (bbox) | 0.0106 | 0.295 / 0.295 |
| 4 | the +X-facing plane at X=0.250, on the measured Y=-0.900 plane, at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=0.250 plane, area 2.77; Y=-0.900 plane, area 0.60; Z=-1.501 plane, area 0.54 (bbox) | 0.0106 | 0.299 / 0.299 |
| 5 | the +X-facing plane at X=0.250, on the measured Y=0.900 plane, at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=0.250 plane, area 2.77; Y=0.900 plane, area 0.60; Z=-1.501 plane, area 0.54 (bbox) | 0.0106 | 0.299 / 0.299 |
| 6 | middle of the top edge of the +X-facing plane at X=0.050 | faces +X, up +Z | X=0.050 plane, area 0.04; Z=1.499 plane, area 0.12 (bbox) | 0.0000 | 0.295 / 0.295 |

#### Brace, Large (Strut / column, 5 magnets)

Audit entry: Door 2 and Large Brace (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002A5F. Our bounds X -2.010..0.010, Y -9.000..1.500, Z -2.000..2.500. Halo 4 set placed on our piece: origin shifted by (-1.000, 0, -0.113); then moved onto measured features (axis_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.300 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | X=-2.000, facing -X, off any measured X plane, Y=0.450 (90% across from -Y), at bottom | faces -X, up +Z | Z=-2.000 plane, area 0.23 (bbox) | 0.0000 | 0.300 / 0.300 |
| 2 | X=0, facing +X, off any measured X plane, Y=0.576 (91% across from -Y), at bottom | faces +X, up +Z | Z=-2.000 plane, area 0.23 (bbox) | 0.0000 | 0.300 / 0.300 |
| 3 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-9.000 plane, area 0.05 (bbox); Z=2.500 plane, area 2.09 (bbox) | 0.0100 | 0.200 / 0.200 |
| 4 | the +Y face, X=-1.047 (48% across from -X), at 1.000 above the base (22% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.500 plane, area 0.54 (bbox) | 0.0100 | 0.300 / 0.300 |
| 5 | the +Y face, centred across it, at 3.100 above the base (69% of the height) (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=1.500 plane, area 0.54 (bbox) | 0.0100 | 0.300 / 0.300 |

#### Column (Strut / column, 8 magnets)

Audit entry: Column, Crenel Notch and two more blocks (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029E8, Cove 0x900029DA. Our bounds X -0.150..0.150, Y -0.150..0.150, Z 0..1.000. Halo 4 set placed on our piece: then moved onto measured features (axis_levels, upright_yaw_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.069 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the top edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=0.150 plane, area 0.08 (bbox); Z=1.000 plane, area 0.04 (bbox) | 0.0071 | 0.069 / 0.069 |
| 2 | middle of the top edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-0.150 plane, area 0.08 (bbox); Z=1.000 plane, area 0.04 (bbox) | 0.0071 | 0.069 / 0.069 |
| 3 | middle of the top edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.150 plane, area 0.08 (bbox); Z=1.000 plane, area 0.04 (bbox) | 0.0071 | 0.059 / 0.059 |
| 4 | middle of the bottom edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.150 plane, area 0.08 (bbox); Z=0 plane, area 0.04 (bbox) | 0.0071 | 0.059 / 0.059 |
| 5 | middle of the bottom edge of the -X face (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-0.150 plane, area 0.08 (bbox); Z=0 plane, area 0.04 (bbox) | 0.0071 | 0.069 / 0.069 |
| 6 | middle of the bottom edge of the +X face (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=0.150 plane, area 0.08 (bbox); Z=0 plane, area 0.04 (bbox) | 0.0071 | 0.069 / 0.069 |
| 7 | middle of the top edge of the +Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.150 plane, area 0.08 (bbox); Z=1.000 plane, area 0.04 (bbox) | 0.0071 | 0.059 / 0.059 |
| 8 | middle of the bottom edge of the -Y face (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.150 plane, area 0.08 (bbox); Z=0 plane, area 0.04 (bbox) | 0.0071 | 0.059 / 0.059 |

#### Arena Wall (Wall, 9 magnets)

Audit entry: Historical detailed proofs (table row) and the Arena Wall paragraph (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900028EC, Cove 0x9000291B. Our bounds X -5.000..5.000, Y -0.250..0.250, Z -6.000..6.000. Halo 4 set placed on our piece: stretched per axis by (1, 0.8333, 1.017).

Halo 4 duplicates kept: #7 and #8 share one point.

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.112 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the -Y face | faces -Y, up +Z | Y=-0.250 plane, area 120.00 (bbox); Z=-6.000 plane, area 5.00 (bbox) | 0.0000 | 0.112 / 0.000 |
| 2 | middle of the bottom edge of the +Y face | faces +Y, up +Z | Y=0.250 plane, area 120.00 (bbox); Z=-6.000 plane, area 5.00 (bbox) | 0.0000 | 0.112 / 0.000 |
| 3 | the +Y face, at the -X extreme, at 6.012 above the base (50% of the height) | faces +Y, up +Z | X=-5.000 plane, area 6.00 (bbox); Y=0.250 plane, area 120.00 (bbox) | 0.0000 | 0.050 / 0.000 |
| 4 | middle of the top edge of the +Y face | faces +Y, up +Z | Y=0.250 plane, area 120.00 (bbox); Z=6.000 plane, area 5.00 (bbox) | 0.0000 | 0.112 / 0.000 |
| 5 | middle of the top edge of the -Y face | faces -Y, up +Z | Y=-0.250 plane, area 120.00 (bbox); Z=6.000 plane, area 5.00 (bbox) | 0.0000 | 0.112 / 0.000 |
| 6 | the +Y face, at the +X extreme, at 6.012 above the base (50% of the height) | faces +Y, up +Z | X=5.000 plane, area 6.00 (bbox); Y=0.250 plane, area 120.00 (bbox) | 0.0000 | 0.050 / 0.000 |
| 7 | the -Y face, at the +X extreme, at 6.012 above the base (50% of the height) | faces -Y, up +Z | X=5.000 plane, area 6.00 (bbox); Y=-0.250 plane, area 120.00 (bbox) | 0.0000 | 0.050 / 0.000 |
| 8 | the -Y face, at the +X extreme, at 6.012 above the base (50% of the height) | faces -Y, up +X | X=5.000 plane, area 6.00 (bbox); Y=-0.250 plane, area 120.00 (bbox) | 0.0000 | 0.050 / 0.000 |
| 9 | the -Y face, at the -X extreme, at 6.012 above the base (50% of the height) | faces -Y, up +Z | X=-5.000 plane, area 6.00 (bbox); Y=-0.250 plane, area 120.00 (bbox) | 0.0000 | 0.050 / 0.000 |

#### Arena Window (Wall, 16 magnets)

Audit entry: Different profiles and multiple nodes (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x9000292F, Cove 0x90002935. Our bounds X -9.600..9.000, Y -0.500..0.500, Z -3.000..3.000. Halo 4 set placed on our piece: then moved onto measured features (extrusion_profile).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 4.804 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +Y face, X=0 (52% across from -X), at mid-height **Audited role (Different profiles and multiple nodes): the centre role X=0 on the +Y face plane Y=0.5 at the middle level Z=0. On our piece that point is in the window opening, 0.32 from material; the audit preserves the role and does not comment on the clearance.** | faces +Y, up +Z | Y=0.500 plane, area 13.24 (bbox) | 0.3240 | 0.186 / 0.186 |
| 2 | the -Y face, X=5.500 (81% across from -X), at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.500 plane, area 15.68 (bbox); Z=-3.000 plane, area 14.49 (bbox) | 0.0147 | 3.805 / 3.805 |
| 3 | surface facing 180 deg from +X toward +Y; X=-7.400 (12% across from -X), centred in Y, at mid-height | faces (-0.71, 0.00, 0.71), up (0.71, -0.00, 0.71) | no measured axis-aligned plane | 0.0000 | 1.800 / 1.800 |
| 4 | the +Y face, X=0 (52% across from -X), at top (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.500 plane, area 13.24 (bbox); Z=3.000 plane, area 12.86 (bbox) | 0.0142 | 0.186 / 0.186 |
| 5 | surface facing 180 deg from +X toward +Y; X=-4.400 (28% across from -X), at the +Y extreme, at top (on the construction planes; our mesh is bevelled or trimmed here) | faces (-0.71, 0.00, 0.71), up (0.71, -0.00, 0.71) | Y=0.500 plane, area 13.24 (bbox); Z=3.000 plane, area 12.86 (bbox) | 0.0147 | 4.804 / 4.804 |
| 6 | the -X face, bottom corner at the +Y end (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-9.600 bbox extreme, no flat face; Y=0.500 plane, area 13.24 (bbox); Z=-3.000 plane, area 14.49 (bbox) | 0.0188 | 0.441 / 0.441 |
| 7 | the +Y face, X=0 (52% across from -X), at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.500 plane, area 13.24 (bbox); Z=-3.000 plane, area 14.49 (bbox) | 0.0141 | 0.186 / 0.186 |
| 8 | surface facing 0 deg from +X toward +Y; X=8.500 (97% across from -X), centred in Y, at mid-height | faces (0.71, 0.00, -0.71), up (0.71, 0.00, 0.71) | no measured axis-aligned plane | 0.0000 | 0.800 / 0.800 |
| 9 | the +X face, top corner at the -Y end (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=9.000 plane, area 2.40 (bbox); Y=-0.500 plane, area 15.68 (bbox); Z=3.000 plane, area 12.86 (bbox) | 0.0164 | 0.353 / 0.353 |
| 10 | surface facing 0 deg from +X toward +Y; X=5.500 (81% across from -X), at the +Y extreme, at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces (0.71, 0.00, -0.71), up (0.71, 0.00, 0.71) | Y=0.500 plane, area 13.24 (bbox); Z=-3.000 plane, area 14.49 (bbox) | 0.0147 | 3.806 / 3.806 |
| 11 | surface facing 180 deg from +X toward +Y; X=-4.400 (28% across from -X), at the -Y extreme, at top (on the construction planes; our mesh is bevelled or trimmed here) | faces (-0.71, 0.00, 0.71), up (0.71, -0.00, 0.71) | Y=-0.500 plane, area 15.68 (bbox); Z=3.000 plane, area 12.86 (bbox) | 0.0146 | 4.804 / 4.804 |
| 12 | the -X face, bottom corner at the -Y end (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-9.600 bbox extreme, no flat face; Y=-0.500 plane, area 15.68 (bbox); Z=-3.000 plane, area 14.49 (bbox) | 0.0187 | 0.441 / 0.441 |
| 13 | the -Y face (frame turned inward, +Y), X=0 (52% across from -X), at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=-0.500 plane, area 15.68 (bbox); Z=-3.000 plane, area 14.49 (bbox) | 0.0141 | 0.186 / 0.186 |
| 14 | the +X face, top corner at the +Y end (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=9.000 plane, area 2.40 (bbox); Y=0.500 plane, area 13.24 (bbox); Z=3.000 plane, area 12.86 (bbox) | 0.0164 | 0.367 / 0.367 |
| 15 | at mid-height (frame facing +Z), X=0 (52% across from -X), at the -Y extreme **Audited role (Different profiles and multiple nodes): the centre role X=0 on the -Y face plane Y=-0.5 at the middle level Z=0. On our piece that point is in the window opening, 0.32 from material; the audit preserves the role and does not comment on the clearance.** | faces +Z, up -Y | Y=-0.500 plane, area 15.68 (bbox) | 0.3172 | 0.186 / 0.186 |
| 16 | top face (frame facing +Z), X=0 (52% across from -X), at the -Y extreme (on the construction planes; our mesh is bevelled or trimmed here) | faces +Z, up -Y | Y=-0.500 plane, area 15.68 (bbox); Z=3.000 plane, area 12.86 (bbox) | 0.0142 | 0.186 / 0.186 |

#### Crenel Full (Wall, 4 magnets)

Audit entry: Brace and Crenel Full (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029ED, Cove 0x900029DF. Our bounds X -1.000..1.000, Y -0.198..0.140, Z -0.800..0.500. Halo 4 set placed on our piece: then moved onto measured features (axis_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.250 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | bottom face (frame facing -Z), centred in X, Y=0 (59% across from -Y) | faces -Z, up -Y | Z=-0.800 plane, area 0.29 (bbox) | 0.0000 | 0.083 / 0.083 |
| 2 | the -X face, on the measured Y=0.100 plane, at 0.800 above the base (62% of the height) | faces -X, up +Z | X=-1.000 plane, area 0.15 (bbox); Y=0.100 plane, area 1.87 | 0.0040 | 0.250 / 0.250 |
| 3 | the +X face, on the measured Y=0.100 plane, at 0.800 above the base (62% of the height) | faces +X, up -Y | X=1.000 plane, area 0.15 (bbox); Y=0.100 plane, area 1.87 | 0.0040 | 0.246 / 0.246 |
| 4 | top face (frame facing +Z), centred in X, Y=0 (59% across from -Y) (on the construction planes; our mesh is bevelled or trimmed here) | faces +Z, up +Y | Z=0.500 plane, area 0.08 (bbox) | 0.0050 | 0.249 / 0.249 |

#### Crenel Notch (Wall, 4 magnets)

Audit entry: Column, Crenel Notch and two more blocks (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x9000299B, Cove 0x9000298F. Our bounds X -0.110..0.141, Y -1.251..1.251, Z -0.500..0.508. Halo 4 set placed on our piece: origin shifted by (0, 0, -0.500); then moved onto measured features (coordinate_planes, axis_levels).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +Y face, X=0.050 (64% across from -X), at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up -X | Y=1.250 plane, area 0.05 (bbox); Z=-0.500 plane, area 0.21 (bbox) | 0.0057 | 0.050 / 0.050 |
| 2 | the -Y face, X=0.050 (64% across from -X), at bottom (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up -X | Y=-1.250 plane, area 0.05 (bbox); Z=-0.500 plane, area 0.21 (bbox) | 0.0056 | 0.050 / 0.050 |
| 3 | Y=-0.775, facing -Y, off any measured Y plane, X=0.050 (64% across from -X), at top | faces -Y, up -X | Z=0.508 bbox extreme, no flat face | 0.0000 | 0.008 / 0.008 |
| 4 | Y=0.786, facing -Y, off any measured Y plane, X=0.050 (64% across from -X), at top | faces -Y, up -X | Z=0.508 bbox extreme, no flat face | 0.0000 | 0.008 / 0.008 |

#### Door, 2 (Wall, 10 magnets)

Audit entry: Door 2 and Large Brace (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x90002A06, Cove 0x900029F8. Our bounds X -1.000..1.000, Y -0.200..0.200, Z -1.000..1.000. Halo 4 set placed on our piece: origin shifted by (0, 0, 0.003); then moved onto measured features (axis_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.400 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | the +Y face, X=0.006 (50% across from -X), at 1.959 above the base (98% of the height) | faces +Y, up +Z | Y=0.200 plane, area 0.53 (bbox) | 0.0000 | 0.000 / 0.000 |
| 2 | Y=0.175, facing +Y, off any measured Y plane, X=0.750 (87% across from -X), at bottom | faces +Y, up +Z | Z=-1.000 plane, area 0.21 (bbox) | 0.0000 | 0.400 / 0.400 |
| 3 | the -Y face, X=0.006 (50% across from -X), at 1.959 above the base (98% of the height) | faces -Y, up +Z | Y=-0.200 plane, area 0.60 (bbox) | 0.0000 | 0.000 / 0.000 |
| 4 | Y=0.175, facing +Y, off any measured Y plane, X=-0.734 (13% across from -X), at bottom | faces +Y, up +Z | Z=-1.000 plane, area 0.21 (bbox) | 0.0000 | 0.400 / 0.400 |
| 5 | Y=-0.175, facing -Y, off any measured Y plane, X=-0.750 (13% across from -X), at bottom | faces -Y, up +Z | Z=-1.000 plane, area 0.21 (bbox) | 0.0000 | 0.400 / 0.400 |
| 6 | Y=-0.175, facing -Y, off any measured Y plane, X=0.750 (87% across from -X), at bottom | faces -Y, up +Z | Z=-1.000 plane, area 0.21 (bbox) | 0.0000 | 0.400 / 0.400 |
| 7 | Y=0.100, facing +Y, off any measured Y plane, X=0.669 (83% across from -X), at mid-height **Audited middle role (Door 2 and Large Brace): intentionally inside the door opening, keeping Halo 4's own 0.031-0.033 clearance from the inner jamb.** | faces +Y, up +Z | no measured axis-aligned plane | 0.0307 | 0.400 / 0.400 |
| 8 | Y=-0.100, facing -Y, off any measured Y plane, X=0.669 (83% across from -X), at mid-height **Audited middle role (Door 2 and Large Brace): intentionally inside the door opening, keeping Halo 4's own 0.031-0.033 clearance from the inner jamb.** | faces -Y, up +Z | no measured axis-aligned plane | 0.0307 | 0.400 / 0.400 |
| 9 | Y=0.100, facing +Y, off any measured Y plane, X=-0.667 (17% across from -X), at mid-height **Audited middle role (Door 2 and Large Brace): intentionally inside the door opening, keeping Halo 4's own 0.031-0.033 clearance from the inner jamb.** | faces +Y, up +Z | no measured axis-aligned plane | 0.0327 | 0.400 / 0.400 |
| 10 | Y=-0.100, facing -Y, off any measured Y plane, X=-0.667 (17% across from -X), at mid-height **Audited middle role (Door 2 and Large Brace): intentionally inside the door opening, keeping Halo 4's own 0.031-0.033 clearance from the inner jamb.** | faces -Y, up +Z | no measured axis-aligned plane | 0.0327 | 0.400 / 0.400 |

#### Wall Curve Short (Wall, 8 magnets)

Audit entry: Wall Curve Short and remaining small construction pieces (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029CF, Cove 0x900029C1. Our bounds X -0.142..0.222, Y -1.107..1.089, Z -0.997..1.000. Halo 4 set placed on our piece: then moved onto measured features (axis_levels, upright_yaw_levels).

Our piece differs in size or shape from Halo 4's: each magnet is at the corresponding feature; the Halo 4 point placed by the alignment alone would be up to 0.124 away.

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | surface facing -80 deg from +X toward +Y; X=0.045 (51% across from -X), Y=-1.112 (-0% across from -Y), at bottom **Audited virtual end-cap corner (Wall Curve Short and remaining small construction pieces): where the measured end-cap plane meets the top or bottom plane; 0.031 from material because of recesses and bevels.** | faces horizontal at -80 deg from +X toward +Y, up +Z | Z=-0.996 plane, area 0.19 (bbox) | 0.0308 | 0.122 / 0.122 |
| 2 | surface facing 80 deg from +X toward +Y; X=0.214 (98% across from -X), Y=1.065 (99% across from -Y), at bottom **Audited virtual end-cap corner (Wall Curve Short and remaining small construction pieces): where the measured end-cap plane meets the top or bottom plane; 0.031 from material because of recesses and bevels.** | faces horizontal at 80 deg from +X toward +Y, up +Z | Z=-0.996 plane, area 0.19 (bbox) | 0.0307 | 0.118 / 0.118 |
| 3 | surface facing -80 deg from +X toward +Y; X=0.045 (51% across from -X), Y=-1.112 (-0% across from -Y), at top **Audited virtual end-cap corner (Wall Curve Short and remaining small construction pieces): where the measured end-cap plane meets the top or bottom plane; 0.031 from material because of recesses and bevels.** | faces horizontal at -80 deg from +X toward +Y, up +Z | Z=1.000 plane, area 0.09 (bbox) | 0.0309 | 0.122 / 0.122 |
| 4 | surface facing 80 deg from +X toward +Y; X=0.214 (98% across from -X), Y=1.065 (99% across from -Y), at top **Audited virtual end-cap corner (Wall Curve Short and remaining small construction pieces): where the measured end-cap plane meets the top or bottom plane; 0.031 from material because of recesses and bevels.** | faces horizontal at 80 deg from +X toward +Y, up +Z | Z=1.000 plane, area 0.09 (bbox) | 0.0308 | 0.118 / 0.118 |
| 5 | surface facing 80 deg from +X toward +Y; X=0.045 (51% across from -X), Y=1.094 (100% across from -Y), at bottom **Audited virtual end-cap corner (Wall Curve Short and remaining small construction pieces): where the measured end-cap plane meets the top or bottom plane; 0.031 from material because of recesses and bevels.** | faces horizontal at 80 deg from +X toward +Y, up +Z | Z=-0.996 plane, area 0.19 (bbox) | 0.0308 | 0.124 / 0.124 |
| 6 | surface facing 80 deg from +X toward +Y; X=0.045 (51% across from -X), Y=1.094 (100% across from -Y), at top **Audited virtual end-cap corner (Wall Curve Short and remaining small construction pieces): where the measured end-cap plane meets the top or bottom plane; 0.031 from material because of recesses and bevels.** | faces horizontal at 80 deg from +X toward +Y, up +Z | Z=1.000 plane, area 0.09 (bbox) | 0.0309 | 0.124 / 0.124 |
| 7 | surface facing -80 deg from +X toward +Y; X=0.214 (98% across from -X), Y=-1.083 (1% across from -Y), at top **Audited virtual end-cap corner (Wall Curve Short and remaining small construction pieces): where the measured end-cap plane meets the top or bottom plane; 0.031 from material because of recesses and bevels.** | faces horizontal at -80 deg from +X toward +Y, up +Z | Z=1.000 plane, area 0.09 (bbox) | 0.0308 | 0.120 / 0.120 |
| 8 | surface facing -80 deg from +X toward +Y; X=0.214 (98% across from -X), Y=-1.083 (1% across from -Y), at bottom **Audited virtual end-cap corner (Wall Curve Short and remaining small construction pieces): where the measured end-cap plane meets the top or bottom plane; 0.031 from material because of recesses and bevels.** | faces horizontal at -80 deg from +X toward +Y, up +Z | Z=-0.996 plane, area 0.19 (bbox) | 0.0307 | 0.120 / 0.120 |

#### Wall, 2x2 (Wall, 8 magnets)

Audit entry: Bridge ramps, walls and railings (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Gulch 0x900029CA, Cove 0x900029BC. Our bounds X -1.000..1.000, Y -0.116..0.116, Z -0.997..1.000. Halo 4 set placed on our piece: origin shifted by (0, 0, 0.002); stretched per axis by (1, 1, 0.9987); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the top edge of the +Y-facing plane at Y=0.100 (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.100 plane, area 0.84; Z=1.000 plane, area 0.15 (bbox) | 0.0101 | 0.001 / 0.000 |
| 2 | the +Y-facing plane at Y=0.100, at the +X extreme, at mid-height (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | X=1.000 plane, area 0.11 (bbox); Y=0.100 plane, area 0.84 | 0.0268 | 0.000 / 0.000 |
| 3 | middle of the bottom edge of the +Y-facing plane at Y=0.100 (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.100 plane, area 0.84; Z=-0.997 plane, area 0.17 (bbox) | 0.0108 | 0.001 / 0.000 |
| 4 | the +Y-facing plane at Y=0.100, at the -X extreme, at mid-height (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | X=-1.000 plane, area 0.21 (bbox); Y=0.100 plane, area 0.84 | 0.0267 | 0.000 / 0.000 |
| 5 | the -Y-facing plane at Y=-0.100, at the -X extreme, at mid-height (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | X=-1.000 plane, area 0.21 (bbox); Y=-0.100 plane, area 0.84 | 0.0267 | 0.000 / 0.000 |
| 6 | the -Y-facing plane at Y=-0.100, at the +X extreme, at mid-height (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | X=1.000 plane, area 0.11 (bbox); Y=-0.100 plane, area 0.84 | 0.0268 | 0.000 / 0.000 |
| 7 | middle of the bottom edge of the -Y-facing plane at Y=-0.100 (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.100 plane, area 0.84; Z=-0.997 plane, area 0.17 (bbox) | 0.0108 | 0.001 / 0.000 |
| 8 | middle of the top edge of the -Y-facing plane at Y=-0.100 (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.100 plane, area 0.84; Z=1.000 plane, area 0.15 (bbox) | 0.0100 | 0.001 / 0.000 |

#### Wall, Double (Wall, 8 magnets)

Audit entry: Bridge ramps, walls and railings (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002BC8. Our bounds X -2.000..2.000, Y -0.116..0.116, Z -0.997..1.000. Halo 4 set placed on our piece: origin shifted by (0, 0, 0.001); stretched per axis by (1, 1, 0.9987); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the top edge of the +Y-facing plane at Y=0.100 (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.100 plane, area 1.21; Z=1.000 plane, area 0.25 (bbox) | 0.0100 | 0.001 / 0.000 |
| 2 | middle of the bottom edge of the +Y-facing plane at Y=0.100 (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.100 plane, area 1.21; Z=-0.996 plane, area 0.50 (bbox) | 0.0109 | 0.001 / 0.000 |
| 3 | the +X face, on the measured Y=0.100 plane, at mid-height (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.000 plane, area 0.21 (bbox); Y=0.100 plane, area 1.21 | 0.0267 | 0.000 / 0.000 |
| 4 | the -X face, on the measured Y=0.100 plane, at mid-height (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-2.000 plane, area 0.21 (bbox); Y=0.100 plane, area 1.21 | 0.0267 | 0.000 / 0.000 |
| 5 | middle of the top edge of the -Y-facing plane at Y=-0.100 (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.100 plane, area 1.21; Z=1.000 plane, area 0.25 (bbox) | 0.0100 | 0.001 / 0.000 |
| 6 | middle of the bottom edge of the -Y-facing plane at Y=-0.100 (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.100 plane, area 1.21; Z=-0.996 plane, area 0.50 (bbox) | 0.0109 | 0.001 / 0.000 |
| 7 | the -X face, on the measured Y=-0.100 plane, at mid-height (on the construction planes; our mesh is bevelled or trimmed here) | faces -X, up +Z | X=-2.000 plane, area 0.21 (bbox); Y=-0.100 plane, area 1.21 | 0.0267 | 0.000 / 0.000 |
| 8 | the +X face, on the measured Y=-0.100 plane, at mid-height (on the construction planes; our mesh is bevelled or trimmed here) | faces +X, up +Z | X=2.000 plane, area 0.21 (bbox); Y=-0.100 plane, area 1.21 | 0.0267 | 0.000 / 0.000 |

#### Window, Double (Wall, 8 magnets)

Audit entry: Bridge ramps, walls and railings (C:/Programming/GitHub/OpenH3M/tools/h4-forge/MATH-AUDIT.md).

Entries: Cove 0x90002BC3. Our bounds X -1.000..1.000, Y -0.116..0.116, Z -0.997..1.000. Halo 4 set placed on our piece: origin shifted by (0, 0.020, 0.001); stretched per axis by (1, 0.8, 0.9987); then moved onto measured features (coordinate_planes).

| # | Location on the piece | Frame | Our measured feature | Off our mesh | H4 to feature, rigid / fitted |
|---|---|---|---|---|---|
| 1 | middle of the bottom edge of the +Y-facing plane at Y=0.100 (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.100 plane, area 0.84; Z=-0.997 plane, area 0.17 (bbox) | 0.0109 | 0.020 / 0.000 |
| 2 | middle of the top edge of the +Y-facing plane at Y=0.100 (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | Y=0.100 plane, area 0.84; Z=1.000 plane, area 0.15 (bbox) | 0.0100 | 0.020 / 0.000 |
| 3 | the +Y-facing plane at Y=0.100, at the +X extreme, at mid-height (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | X=1.000 plane, area 0.21 (bbox); Y=0.100 plane, area 0.84 | 0.0267 | 0.020 / 0.000 |
| 4 | the +Y-facing plane at Y=0.100, at the -X extreme, at mid-height (on the construction planes; our mesh is bevelled or trimmed here) | faces +Y, up +Z | X=-1.000 plane, area 0.21 (bbox); Y=0.100 plane, area 0.84 | 0.0267 | 0.020 / 0.000 |
| 5 | middle of the top edge of the -Y-facing plane at Y=-0.100 (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.100 plane, area 0.84; Z=1.000 plane, area 0.15 (bbox) | 0.0100 | 0.030 / 0.000 |
| 6 | the -Y-facing plane at Y=-0.100, at the -X extreme, at mid-height (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | X=-1.000 plane, area 0.21 (bbox); Y=-0.100 plane, area 0.84 | 0.0267 | 0.030 / 0.000 |
| 7 | middle of the bottom edge of the -Y-facing plane at Y=-0.100 (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | Y=-0.100 plane, area 0.84; Z=-0.997 plane, area 0.17 (bbox) | 0.0109 | 0.030 / 0.000 |
| 8 | the -Y-facing plane at Y=-0.100, at the +X extreme, at mid-height (on the construction planes; our mesh is bevelled or trimmed here) | faces -Y, up +Z | X=1.000 plane, area 0.21 (bbox); Y=-0.100 plane, area 0.84 | 0.0267 | 0.030 / 0.000 |

## User decision, 2026-11-26: pieces without a usable template
"Derive magnets as best you can when you have no template." Where no Halo 4 magnet set can be matched to our
piece with confidence, magnets are derived from our piece's own geometry using the background placement rules
above (edge middles, surface-flush, deck height on walkable pieces, symmetry), chosen to behave as Halo 4's would.
This covers Arena Window's two face-centre magnets (moved onto the frame where the rules place them), the seven
unchecked Covered Walkway magnets, and the eight pieces whose placement was only checked numerically (Bunker
Stair, Tower 3 Story, Tower Tall, Long Tunnel, Man Cannon, both circular ramps, Covered Walkway): each is checked
against the actual piece and re-derived from its geometry where it does not sit on the intended feature.


---

# Forge magnets specification, section 7: how the magnet markers look

Clean-room description of the appearance of Halo 4's Forge magnet markers, written so that the look can be
redrawn with our own rendering code. No Halo 4 shader, texture or curve data is to be shipped; every number
below is a description of the appearance, restated as our chosen value.

Sources (static reading and offline decoding only; the game was not run for this section):

- Retail effect, particle and material fields as decoded by
  `C:\Programming\GitHub\OpenH3M\tools\h4-forge\inspect_marker_effect.py` and
  `C:\Programming\GitHub\OpenH3M\tools\h4-forge\inspect_marker_particles.py`, saved in
  `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\marker-effect-fields.json` and
  `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\marker-particle-inputs.json`.
- Curve samples from the original curve evaluator
  (`C:\Programming\GitHub\OpenH3M\tools\h4-forge\check_marker_curves.cpp`,
  `C:\Programming\GitHub\OpenH3M\tools\h4-forge\verify_marker_curves.py`), saved in
  `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\marker-curves.csv`.
- Decoded textures (`C:\Programming\GitHub\OpenH3M\tools\h4-forge\decode_marker_bitmaps.py`) in
  `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\marker-bitmaps\`; profiles measured
  from those pixels for this section.
- Pixel-program disassembly and translation
  (`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\isolated\marker-shaders\331-ps-0.ucode.txt`,
  `...\16-ps-0.ucode.txt`, the fade blocks from
  `C:\Programming\GitHub\OpenH3M\tools\h4-forge\translate_marker_fade.py`) and the packing wrapper
  `C:\Programming\GitHub\OpenH3M\tools\h4-forge\pack_marker_material.py`.
- Marker-visual creation `sub_825827B0` (read in
  `C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\generated\halo4_recomp.45.cpp`) and the
  visibility rules in `C:\Programming\GitHub\OpenH3M\tools\h4-forge\spec\04-rotation-coordinates-physics.md`
  section 6.
- Spartan's current drawing: `C:\X360\ISOs\H3M\.local\OpenH3M-source\halo3mp\src\advanced_forge.cpp`
  (`PublishNativeHeldAnchors`, the `sub_82162398` hook) and the renderer patches
  `C:\X360\ISOs\H3M\.local\OpenH3M-source\halo3mp\patches\rexglue-sdk-scene-marker-depth.patch` and
  `...\rexglue-sdk-scene-marker-material.patch`.

Units: distances are Halo world units (wu; 1 wu = 10 ft = 3.048 m by the usual Halo convention). Colours are
8-bit sRGB-style triples as stored in the textures/curves; "intensity" values above 1 are high-dynamic-range
multipliers. Curve inputs are the particle's normalised age (0 = born, 1 = dies).

Confidence tags: **[data]** read directly from decoded values; **[derived]** worked out from several decoded
values; **[traced]** read from Halo 4's own code (Round 3: the recompiled functions in
`C:\X360\ISOs\H3M\.local\OpenH3M-source\work\h4-forge-research\generated\halo4_recomp.*.cpp`, whose comments
carry the original PowerPC, with constants read from `C:\X360\OpenH3M\advanced-forge\h4-image.bin`). Nothing was
run. Where the reading does not settle something it is marked **not determined**; no gap is filled with a
choice.

---

## 1. What a magnet marker looks like, in one paragraph

Each magnet is a small, camera-facing glow at the magnet point: a thin, soft-edged **ring** about 11 cm across
whose colour boils between deep red and hot orange with a scrolling plasma pattern, sitting on top of a larger
(roughly 0.3 to 0.85 m) soft **orange starburst** of a dozen uneven rays around a dark centre. The ring is
drawn very bright (HDR, up to about 30 times its base colour); how that is exposed and bloomed on screen was not
determined. Each individual particle lives half a second, swelling in and out (the ring flares to full
brightness halfway through); the rays slowly spin and flicker slightly. Each marker keeps one ring emitter and
one ray emitter for its whole life; at 30 frames per second they start a new ring particle every 5th frame and a
new ray particle every 3rd frame, so about 3 ring and 5 ray particles overlap at staggered ages. On screen this
reads as a continuous glow with a slight six-times-a-second shimmer in the ring (section 2.4).
Markers fade out between 21 and 23 wu from the camera and vanish when the camera is within about 0.4 wu (closer
fade distances shrink when the view is zoomed). Held-piece and target-piece markers look identical; there is no
special look for the pair that is snapping. Each marker object also carries a looping sound attachment.

---

## 2. Structure: one effect, two particle layers per magnet

- **[data]** `sub_825827B0` collects the object's magnet markers (up to 32, see section 1 of this spec) and, for
  each one, creates one effect-scenery object from the single reference in the Forge globals (+0x0C) and attaches
  it at that marker's position and orientation. The same object type is used for every marker on every piece.
  Creation records the editing player; removal (`sub_82582950`) deletes only that player's marker objects. The
  callers run only for local players, so markers are a per-player, local-only visual.
- **[data]** The effect-scenery plays one effect (`ca_fw_mag_01a`). It has one location (the attachment marker),
  one event (no start delay, duration 1/30 s) and two particle systems, both in the object's **local** coordinate
  system, so particles ride along with the piece when it moves or snaps.
  - Layer A, the **plasma ring** (`ca_fw_mag_01a`, system size scale 0.25).
  - Layer B, the **ray burst** (`ca_fw_mag_01b`, system size scale 1.4).
- **[data]** Both particle types are **camera-facing billboards** (billboard style "camera facing"), square
  (aspect curve constant 1), no sprite-sheet animation (frame and animation-rate curves constant 0).
- **[data]** Emitter shape: point sprayer, emission radius 0, initial velocity 0.001 wu/s, no forces, no
  collision. The particles therefore sit on the magnet point and do not drift.
- **[data]** Effect death delay 0.1 s (particles may linger up to 0.1 s after the marker is removed).
- **[data]** Authored emission values: starting count 0.2 (ring) and 0.3 (rays), emission rate 0 per second
  (ring) and 1 per second (rays), emission per distance 0, lifespan 0.5 s for both, max count 0 (= no limit).

### 2.1 Who creates the marker visuals, and when (traced, Round 3)

- **[traced]** `sub_825826B0` calls the create routine `sub_825827B0` only when the held piece or the target
  **changes** (spec 04 section 6). Nothing in the Forge code re-creates markers every tick. Each marker object
  then lives until `sub_82582950` removes it.
- **[traced]** `sub_825827B0` builds one placement per marker and calls the object-creation routine
  (`sub_8297C8E0` prepares the placement, `sub_82933B30` creates the object, with placement flags `|= 0x300`), then
  attaches the new object to the piece at the marker's node (`sub_82938980`).
- **[data]** The effect-scenery object definition (`objects\levels\forge\fx\ca_fw_mag_01a`, object type 14) has
  an invisible model (`fx\anchor\fx_anchor`, shader `fx\anchor\shaders\invisible`) and two attachments:
  1. the effect `ca_fw_mag_01a`, at marker string ID 0x193, flags 0, no colour change, no scale functions;
  2. a looping sound `sound\visual_fx\gasoline_fire\gasoline_fire`, no marker, flags 0.
- **[traced]** Object attachments are set up by `sub_82941E38`. Lights and sounds are started at creation; for
  effects it records an empty slot. `sub_82942238` (attachment update, also run at creation) then creates the
  effect when the slot is empty and the attachment counts as active (with no scale-function name it is active),
  and deletes it if it becomes inactive. It does not restart an effect that already exists.
- **[traced]** The effect is created through `sub_82454C50`, which always starts its request flags as 0x87
  (bits 0, 1, 2 and 7; initial 0x80 from `sub_821D3270`, then `| 7`). In `sub_82200638` (effect creation) request
  bit 1 sets the new effect's **looping** flag (instance flag bit 0); the effect tag's own "force looping" bit
  would set the same flag. Effects created as object attachments therefore always loop.

### 2.2 How the effect repeats (traced, Round 3)

- **[traced]** Per-location event timing is in `sub_82459EA8` (advance), `sub_82459B78` (enter delay/duration
  phase) and `sub_824599D8` (next event). The single event has delay 0 and duration 1/30 s.
- **[traced, corrected Round 5]** At the end of the duration phase `sub_82459EA8` checks effect-tag bit 1
  ("run events in parallel"), which is set: the location is marked finished (location flag 2) and no next event
  is chosen there. (`sub_8245B230` with 0 runs too, but it walks only the event's parts block, which is empty
  here.) When every location is finished, the effect driver `sub_8245A0D8` sees the instance is looping
  (`sub_82452ED8`) and restarts all locations at once (`sub_82459DF0` → `sub_82459B78`). The effect is never
  deleted while the marker exists. With delay 0 and duration 1/30 s this restart happens once per effect update.
- **[traced, corrected Round 5]** On each event start `sub_82459B78` either creates particle systems
  (`sub_82458598`, first start only) or sends a "restart" message (type 12) for the existing ones. After the first
  start it sets location flag 4 unless effect-tag **bit 2** ("do not re-use parts when looping") is set. That bit
  is clear here, so **only the first start creates systems**; every later loop sends message 12. (Rounds 3–4 read
  this test as bit 1 and wrongly concluded that every loop creates new systems; the instruction is
  `rlwinm r10,r11,30,31,31`, which extracts bit 2.)
- **[derived]** Each marker therefore has exactly **one ring system and one ray system for its whole life**,
  created on the first event start (messages 0, 1, 2 to the particle thread, `sub_8245D7F0`: 0 →
  `sub_82458950`/`sub_825835C0` allocate the system, 1 → `sub_82583B40` adds its location, 2 → `sub_822711D8`).

### 2.3 How particles are spawned from the counts (traced, Round 3)

- **[traced]** Emission is `sub_8226C918`, called per emitter by `sub_82278320` while the system location's
  emission gate (location +76, initialised to 1.0 by `sub_82585AF0`) is above zero, and only when the system's
  "emitting" flag (0x10, section 2.4) is set:
  1. accumulator = fractional part of the accumulator (`fmod(acc, 1)`, `sub_82256DC8`);
  2. if the location has not yet had an emission update: accumulator += starting count; `sub_82278320` marks the
     location (flag 0x10) after every update, so on its own the starting count would be added once per location —
     but for this effect the restart re-arms it every frame (section 2.4);
  3. accumulator += emission rate × time step; accumulator += emission-per-distance × distance moved;
  4. if max count > 0, the accumulator is clamped so the live count cannot exceed it;
  5. if the accumulator is at least 1, spawn `floor(accumulator)` particles (`sub_82290570`, `sub_82266230`),
     spreading their birth times evenly through the step; otherwise spawn nothing. The fraction carries over.
- **[traced]** Each emitter instance's accumulator starts at 0 (`sub_825ED3A0`). Each new system gets one new
  location and new emitter instances. The particle-property reader `sub_8226CC60` returns the stored constant
  when the property is flagged constant (runtime flag 0x40), which the starting counts, rates and lifespans are.
### 2.4 Emission over time and the resulting particle count (traced, Round 5; replaces Round 4)

- **[traced] The restart re-arms the starting count every frame.** Message 12 sets flag 8 on the effect's
  location record (`sub_8245D7F0` case 12); nothing clears that flag afterwards. Every particle-system update
  (`sub_82277F28`, once per system per rendered frame) begins with `sub_82271030` → `sub_822711D8`, which, when
  the location record has flag 8 (or the effect has flag 0x1000) and the system's recorded event-start count
  equals the location's (true: the count only advances on the create path), clears the once-only flag 0x10 on
  all of the system's locations. The emitter routine `sub_8226C918` then adds the starting count again. So from
  the second frame on, **the starting count is added on every particle update** — it behaves as "particles per
  frame", not a one-off count.
- **[traced] Emission is enabled every frame.** `sub_82265A40` reports the system current and active (location in
  its duration phase, not finished; same event index and start count; effect active), so `sub_82271030` sets
  system flag 0x10 and `sub_8226C918` runs. Because the effect driver restarts the location inside the same update
  in which it finishes, the location is in its duration phase whenever the particle update runs. The location
  gate value at +76 is the "location LOD" input (state slot 11), initialised to 1.0.
- **[traced] Cadence.** The particle update (`sub_822640F0` → `sub_82277F28`) is called from the per-view render
  setup `sub_822460A8` via `sub_821F7C68`, with the frame time step (0 while paused, in which case no emission
  runs). So the count is per rendered frame. `sub_8226C918` is the only spawner (no other code reads emitter
  +0x110); GPU-updated systems spawn through it too.
- **[derived] Spawn pattern.** Per frame: accumulator = fraction(accumulator) + starting count + rate × dt; spawn
  floor(accumulator).
  - Ring: +0.2 per frame → **one ring particle every 5th frame** (float sums 0.2, 0.4, 0.6, 0.8, 1.0000001; the
    residue left after each spawn is about 1e-7, negligible).
  - Rays: +0.3 + 1 × dt per frame; at 30 frames per second that is 0.3333 → **one ray particle every 3rd frame**
    (also every 3rd frame for any dt between about 0.034 and 0.1 s).
  - At Halo 4's 30 frames per second: 6 ring particles and 10 ray particles per second per marker. If the frame
    rate drops, the per-second rate drops with it (counts are per frame).
- **[derived] Live particles.** Lifespan 0.5 s (15 frames at 30 fps): **3 ring particles** alive at once, at
  1/3-life spacing (ages about 0, 0.17 and 0.33 s), and **5 ray particles**, at 1/5-life spacing (0.1 s apart).
  Summing intensity × tint across the live particles: ring multiplier 27–36 (mean 30), rippling about ±14% six
  times a second as each new particle starts and the oldest ends; rays 4.1–4.3 (effectively steady). Each
  particle has its own random spin (rays), mirroring and plasma orientation, so the pattern shifts constantly.
  **On screen this is a continuous glow with a slight 6 Hz shimmer in the ring, not a pulse.**
- **[traced] First appearance.** On the first frame the systems hold only the one-off starting count (ring 0.2,
  rays 0.333); the per-frame re-arming starts once the second event start has sent message 12. The first ring
  particle therefore appears after about 5 frames (about 0.17 s) and the first ray particle after about 3; the
  glow reaches its steady 3 + 5 particles after about 0.5 s.
- **[traced] Removal.** When the marker object is deleted the effect and its systems go with it; particles may
  linger up to the 0.1 s death delay.

---

## 3. Layer A — the plasma ring

### 3.1 Shape (texture described in words)

- **[data]** Ring mask: a 256 x 256 greyscale image of a single soft annulus, centred, perfectly round, black
  outside and inside. Measured on the channel the material reads (alpha), as a fraction of the sprite's
  half-width: brightest at radius **0.71**, half-brightness at **0.60** and **0.83**, fades to nothing by 0.47
  inside and 0.96 outside. The falloff is smooth (gaussian-like) on both sides; the band is about 0.23 of the
  half-width wide at half-brightness. The interior (radius < 0.45) is empty.
- **[data]** Two tiling "plasma cloud" noise images, 128 x 128 greyscale, soft fractal clouds (like Perlin
  clouds) with values spread over the full 0..1 range; average about 0.47 (A) and 0.41 (B). They wrap
  (repeat) at the edges. The ring mask and palette clamp.
- **[data]** Palette: a 256 x 1 colour strip used as a lookup from a 0..1 value to a colour:

  | Lookup value | Colour (R,G,B) |
  | --- | --- |
  | 0.00 | 123, 12, 0 (dark blood red) |
  | 0.25 | 156, 16, 0 |
  | 0.50 | 206, 20, 0 |
  | 0.75 | 255, 28, 0 (pure red) |
  | 0.875 | 255, 73, 0 (red-orange) |
  | 1.00 | 255, 130, 8 (orange) |

  Red climbs roughly linearly to full at 0.75; green stays near 12..28 until 0.75 and then rises steeply; blue is
  essentially zero.

### 3.2 How the ring is coloured each pixel

**[derived]** from the pixel program (instructions 27–47 and 58–74):

1. Sample both noise images over the sprite (one repeat across the billboard), each sliding with time: noise A
   moves by (+0.5, +0.5) texture widths per second, noise B by (−0.5, −0.5) per second (material constants
   0.5, 0.5, −0.5, −0.5). They move in opposite diagonal directions, so the pattern churns rather than drifts.
2. `plasma = |A − B|` (absolute difference, 0..1; bright filaments where the two clouds disagree).
3. `m = ring_mask × particle_alpha`.
4. Palette lookup value `u = saturate((1 − m) × 1 + plasma)` (the 1 is a material constant).
5. Colour = `palette(u) × particle_colour` (particle colour already includes intensity and tint, section 3.4).
6. Output alpha = `ring_mask × particle_alpha` (× soft-depth fade if enabled, Q4).
7. Blend: **"add source times source alpha"** — the colour is multiplied by its own alpha and added to the scene.
   Nothing is darkened; the ring only adds light.

Effect on the look: where the ring is strongest and the particle most opaque, `u` is low and the colour sits
at the deep-red end, broken by orange filaments wherever the plasma term is large; toward the soft edges of the
ring and when the particle is faint, `u` rises toward orange but the output alpha drops, so edges are dim. The
result is a red ring with a moving, boiling orange texture.

The program also contains an optional fog/atmosphere branch and an optional "push toward white" step scaled by
a constant that is 0 for this material; neither changes the look here.

### 3.3 Size

- **[data]** Per-particle size curve 0.30 → 0.35 over the particle's life, scale curve 0.50 → 0.40 over life,
  system size scale 0.25, effect global size scale 1.
- **[derived]** Billboard full width = size × scale × system scale: **0.0375 wu at birth, 0.0366 wu at mid-life,
  0.035 wu at death** (about 11 cm; effectively constant). The visible ring diameter (peak at 0.71 of the
  half-width) is therefore about 0.026 wu (8 cm). That "size" means full width, not radius, follows from the
  emitter's stored bounding-radius estimate (0.124 = 0.35 × 0.5 / √2, the half-diagonal of a 0.175 square).
- **[data]** Rotation property: input selector 25, range selector 15; the curve's output depends only on the
  range input, 0.5 turns at range 0 falling to 0 at range 1. **[traced, Round 5]** In Halo 4's particle state
  array (`sub_82278838`) slot 15 is filled with 0, so on the CPU side this evaluates to 0.5 turns (180 degrees)
  for every particle. The rotation property is not evaluated by the CPU spawn code (`sub_8231C560` reads only
  emission radius/angle, lifespan, initial velocity and spin rate); it goes to the GPU through the emitter's
  runtime GPU property tables, which were not decoded. The particle type also has the "random starting rotation"
  and random U/V mirroring flags; how the GPU combines them with the 0.5 turns was not determined. No spin.
  With a round ring these only change the orientation of the plasma pattern.

### 3.4 Animation over the 0.5 s life

All curves are functions of normalised age t (0..1 over 0.5 s):

- **Intensity [data]:** a triangle. Starts at 1, rises linearly to a peak of **29.9 at t ≈ 0.48** (0.24 s), falls
  linearly back to 1 at t = 1. Samples: t 0.125 → 8.6, 0.25 → 16.1, 0.375 → 23.7, 0.5 → 28.7, 0.625 → 21.8,
  0.75 → 14.8, 0.875 → 7.9.
- **Emitter tint [data]:** grey triangle, 0 at birth, **0.99 at t = 0.5**, 0 at death (0.25 → 0.50, 0.75 → 0.50).
  Multiplies the particle colour.
- **Particle colour [data]:** constant white.
- **Particle alpha [data]:** straight ramp 0 → 1 over life. Emitter alpha: constant **0.25**. The particle type
  has the "intensity affects alpha" flag set (Q3).
- **Net brightness multiplier** (intensity × tint) [derived]: 0 → 8.1 (t 0.25) → **28.4 (t 0.5)** → 7.4
  (t 0.75) → 0. In words: a sharp half-second flash, dark at both ends, very bright in the middle.
- **Plasma scroll [data]:** continuous with time (not with particle age), at the rates in 3.2.

---

## 4. Layer B — the ray burst

### 4.1 Shape (texture described in words)

- **[data]** 512 x 512 greyscale starburst: about **13–14 soft, tapered rays** radiating from the centre at
  irregular angles, of uneven length and brightness (the brightest rays roughly twice as bright as the dimmest;
  a couple of wider gaps of 40–60 degrees with no ray). Each ray is a blurred wedge about 15–25 degrees wide.
  The centre is a **dark hole** (nothing inside 0.23 of the half-width). Averaged around the circle the
  brightness peaks at radius **0.44**, is above half that between **0.33 and 0.60**, and fades to nothing by
  0.92. The brightest pixel is only 0.56 of full white (144/255); the average ray brightness at the peak radius
  is about 0.18. The image tiles (wraps) but is laid out to fit inside the square.

### 4.2 Colour, blend and material

- **[data]** Material is a plain textured particle: colour = texture × particle colour, alpha = texture ×
  particle alpha. Blend **additive** (adds light, never darkens).
- **[data]** Particle colour curve: a straight blend over life from **(255, 89, 35)** at birth to
  **(255, 92, 0)** at death (warm orange, losing its slight pink).
- **[data]** Intensity curve: a gentle irregular flicker between **10.1 and 12.3** (average about 11). Over one
  life it shows about five bumps (peaks near t 0.11, 0.36, 0.63, 0.80, 0.92), i.e. roughly a 10 Hz shimmer of
  ±10%.
- **[data]** Emitter tint: grey, near-triangle, 0 at birth, **0.133 at t = 0.5**, 0 at death (0.25 → 0.082,
  0.75 → 0.075). Particle alpha 1; emitter alpha **0.25**.
- **[derived]** Net brightness multiplier (intensity × tint): 0 → 0.85 (t 0.25) → **1.44 (t 0.5)** → 0.80 → 0.
  So the rays are a moderate glow, about 1/20 of the ring's peak brightness per unit of colour.

### 4.3 Size and motion

- **[data]** Size curve 0.40 → 0.20 over life, scale 0.50 → 0.40, system size scale 1.4.
- **[derived]** Billboard full width: **0.28 wu at birth, 0.19 wu at mid-life, 0.11 wu at death** (about
  0.85 m → 0.34 m). The burst visibly shrinks to 40% while it fades in and out. Because of the dark core and the
  ray peak at 0.44 of the half-width, the bright part of the rays starts just outside the ring and reaches
  about 3–5 ring-widths out.
- **[data]** Starting rotation: 0.25 turns (90 degrees) plus the "random starting rotation" flag; random U/V
  mirroring. **Spin [traced, Round 5]:** evaluated at spawn by `sub_8231C560` from the particle state array.
  Range selector 24 is the particle's 7th random number: each new particle draws eight 16-bit randoms from its
  system's generator (`sub_82266230`; multiplier 1664525, increment 1013904223, top 16 bits, scaled to 0..65535)
  and `sub_82278838` stores them, divided by 65535, in state slots 4, 5, 6, 7, 22, 23, 24, 25. Spin =
  0.15 − 0.30 × random₂₄ turns per second: uniform between **−0.15 and +0.15 turns per second** (up to 54 degrees
  per second either way), independently per particle.

---

## 5. Timeline summary (one particle of each layer)

| Age (s) | Ring width (wu) | Ring brightness × | Ring alpha (particle × emitter) | Rays width (wu) | Rays brightness × | Rays colour |
| --- | --- | --- | --- | --- | --- | --- |
| 0.000 | 0.0375 | 0 | 0 × 0.25 | 0.28 | 0 | 255, 89, 35 |
| 0.125 | 0.0371 | 8.1 | 0.25 × 0.25 | 0.23 | 0.85 | 255, 90, 26 |
| 0.250 | 0.0366 | 28.4 | 0.50 × 0.25 | 0.19 | 1.44 | 255, 91, 18 |
| 0.375 | 0.0359 | 7.4 | 0.75 × 0.25 | 0.15 | 0.80 | 255, 91, 9 |
| 0.500 | 0.0350 | 0 | 1.00 × 0.25 | 0.11 | 0 | 255, 92, 0 |

"Brightness ×" is intensity × emitter tint, multiplying the layer's base colour (palette colour for the ring,
the listed colour for the rays) before blending.

---

## 6. Distance fades

**[data]** Both systems carry the same fade settings; the vertex program applies them as two linear ramps
multiplied together, using the distance along the camera's view direction (not straight-line distance):

- **Near fade:** `saturate((d − 0.4032) / 0.2016)` — invisible at 0.403 wu or closer, full at 0.605 wu.
- **Far fade:** `saturate((23 − d) / 2)` — full out to 21 wu, linearly to invisible at 23 wu.
- Visibility = near × far, applied to the particle alpha. Linear ramps, no easing.
- **Zoom [traced, Round 3]:** the near range and near cutoff (not the far values) are multiplied by a per-frame
  scale written by the view setup `sub_822460A8`: scale = 1 / max(v, 0.0001), where v is a float at +460 in the
  current local view's record (array at thread-local slot 848, 1056 bytes per view). `sub_8262EFE8` applies it
  when it writes the near/far constants. The earlier native reading found the scale to be 1 in the normal view.
  So if v grows when zoomed (as a zoom magnification would), the near fade moves proportionally closer to the
  camera. That v is the zoom magnification is the natural reading but was not confirmed (Q6).
- **[data]** The systems also have a level-of-detail cut-out at 25 wu with a 5 wu feather; it lies beyond the
  far fade and has no visible effect.

---

## 7. Occlusion

- **[data]** The markers are ordinary transparent particles in the normal sort layer: depth-tested against the
  scene, not drawn through walls. A marker on the far side of a piece is hidden by the piece itself; a marker
  partly behind an edge shows only its exposed part.
- **[data]** The ring material has a soft-particle depth fade with a range of 0.5 wu (fades the sprite where it
  comes within 0.5 wu of the surface behind it), behind a renderer switch whose state for these particles was
  not determined (Q4).
- The ray layer has no depth fade.

---

## 8. States

- **When markers are shown [data]:** see `C:\Programming\GitHub\OpenH3M\tools\h4-forge\spec\04-rotation-coordinates-physics.md`
  section 6. With magnets on, every magnet of the **held piece** and of the **current target piece** shows a
  marker; with magnets off none do. Markers appear and disappear as whole effects when the held piece or target
  changes; there is no transition animation beyond the particles' own life and the 0.1 s death delay.
- **Held vs target [data]:** identical. The creation routine takes no state argument and always uses the one
  effect-scenery type.
- **Active snap pair [data, negative]:** no distinct visual was found. There is a single marker effect in the
  Forge globals and the show/hide routine (`sub_825826B0`) only adds or removes whole sets. The two magnets
  that are snapping simply overlap at the same point (the held marker moves with the piece), which doubles the
  added light there.
- **Other players:** markers are created per editing player and only for local players (section 2).

---

## 9. HDR and bloom

**[data]** Halo 4 renders these particles into its high-dynamic-range buffer: the ring's colour reaches about
28 times its palette colour at mid-life, and the rays about 1.4 times. The final on-screen colour and any glow
beyond the painted sprite depend on Halo 4's exposure, tone mapping and bloom, which were **not determined**
(Q7). No on-screen appearance is asserted here.

---

## 10. Reproduction checklist (Halo 4 behaviour only)

Only traced or decoded behaviour is listed. Items that are not determined are named as gaps, not filled.

1. One marker object per magnet of the held piece and of the current target, while magnets are on; created
   and removed only when the held piece or target changes (section 2.1, spec 04 section 6). Local player only.
2. Each marker object carries a looping effect and a looping sound attachment
   (`gasoline_fire`; its level/audibility not determined, Q9).
3. The effect loops forever while the marker exists: one event, delay 0, duration 1/30 s; the first event start
   creates one ring system and one ray system at the marker, in the marker's local space; later loops only
   restart them (section 2.2).
4. Per rendered frame, each system adds its starting count (re-armed every frame by the restart) plus rate × dt
   to a carried fractional accumulator and spawns floor(accumulator) particles (sections 2.3–2.4): one ring
   particle every 5th frame, one ray particle every 3rd frame; about 3 ring and 5 ray particles alive at once.
5. Each particle: camera-facing square in world units, transparent pass, depth-tested, no depth write; ring and
   ray appearance, sizes, curves and timing exactly as sections 3–5; random U/V mirroring; rays spin at
   0.15 − 0.30 × (particle random slot 24) turns/s. **Gap:** how the GPU applies the ring's start rotation
   (0.5 turns on the CPU side) together with the random-start-rotation flag (Q2).
6. Ring blend "add colour × alpha", ray blend additive; ring colour from the palette lookup of section 3.2.
   **Gaps:** intensity-affects-alpha (Q3), soft depth fade (Q4), exposure/tone mapping/bloom (Q7).
7. Near/far fades as section 6, near distances scaled by the view value of section 6.
8. Identical look for held and target markers; no snap-pair highlight.

---

## 11. Spartan's current drawing and how it differs from Halo 4

What Spartan draws today (accepted by the user on 2026-10-28; the translated Halo 4 materials and textures it
uses are being dropped under the clean-room rule):

- One screen-space square per visible magnet, **radius fixed at 5 pixels at 1152 pixels of output width**
  (scaled with output width), regardless of distance. Both layers share this one square. Halo 4 uses world-size
  billboards, with the rays 3–8 times wider than the ring and the ring about 0.036 wu wide (about 6 px at 5 wu
  with a 70-degree view, about 46 px for the rays).
- Both layers' original pixel programs are evaluated with fixed inputs: ring colour white with alpha = distance
  fade; rays colour fixed at the birth orange (255, 89, 35), alpha = distance fade. **No particle life:** no
  intensity curves (ring 1–30, rays 10–12 flicker), no tint triangles, no emitter alpha 0.25, no age ramp, no
  size change, no rotation, spin or random mirroring. The only motion is the plasma noise scrolling with the
  game's tick time (tick / 30 s).
- Composited as `ring × ring_alpha + rays × rays_alpha`, **added after the game's gamma**, with no HDR and no
  bloom.
- Occlusion: every pixel of the square is compared against the scene depth at the magnet point's own depth (the
  whole square shares one depth), so rear markers are hidden and exposed parts of partly hidden markers remain.
  No soft-particle fade.
- Near/far fade: same values as Halo 4 (section 6), using camera-axis depth; zoom adjustments are not modelled.
- At most 64 markers per view; one view's snapshot is rendered per frame (split-screen not covered).
- Held and target markers are drawn the same (all pushed with white colour, which the material ignores) —
  this matches Halo 4.
- When snapped, the legacy path draws the held markers at the snapped position; the coupled path re-reads the
  live marker positions after the piece moves.

---

## 12. Open questions

Status after Round 5. "Not determined" means static reading so far does not settle it; nothing is substituted.

- **Q1. Live particle count per marker — RESOLVED (Round 5).** Rounds 3–4 misread one bit test (bit 1 instead of
  bit 2 in `sub_82459B78`) and concluded that each loop creates new, short-lived systems that never spawn. The
  corrected reading (sections 2.2, 2.4): one ring and one ray system per marker for its life; the looping restart
  (message 12) re-arms the starting count on every particle update, so the fractional counts act per frame: one
  ring particle every 5th frame, one ray particle every 3rd frame, about 3 + 5 live particles, a continuous glow.
  Of the candidate explanations put forward, (d) was the gap — the attachment keeps one effect instance and only
  restarts events — combined with the per-frame re-arming of the starting count. No multiplier, random roll,
  unit change or minimum-count rule exists in the spawn routine (a: no scale is applied between the property
  read and the floor; b: no random number is drawn in `sub_8226C918`; c: the counts are flagged constant and read
  as stored; e: spawning requires accumulator ≥ 1 with no minimum).
- **Q2. Ring start angle — PARTLY RESOLVED; ray spin — RESOLVED (Round 5).** Particle randoms: eight per
  particle from the system generator, in state slots 4–7 and 22–25 (`sub_82266230`, `sub_82278838`). Ray spin =
  0.15 − 0.30 × slot 24, evaluated at spawn by `sub_8231C560`. Ring rotation property: range slot 15 = 0 on the
  CPU side → 0.5 turns; the property is applied on the GPU via the emitter's runtime GPU property tables
  together with the "random starting rotation" flag, which were not decoded — not determined. Ray start rotation
  is the constant 0.25 turns plus the same GPU-side flag handling.
- **Q3. "Intensity affects alpha" — NOT DETERMINED.** Traced as far as `sub_8262EFE8`, which converts the particle
  type's flag words (including the appearance flags at +0x10, where this flag lives) to floats in the particle
  render constants; the bit is tested inside Halo 4's GPU particle shaders, which were not extracted.
- **Q4. Soft depth fade near surfaces — NOT DETERMINED.** The ring material's 0.5 wu depth-fade code is behind
  pixel-program bool b228, a renderer-set constant whose value for this pass was not traced.
- **Q5. Spin direction per particle — RESOLVED** (Q2): each ray particle picks its own direction and speed.
- **Q6. Zoom — RESOLVED except one identification.** Near range and cutoff × 1/max(v, 0.0001); far unchanged
  (section 6). That v (view record +460) is the zoom magnification is not confirmed.
- **Q7. Exposure, tone mapping and bloom — NOT DETERMINED.** Not traced in Round 5. No Halo 4 screenshot or
  footage was compared for this section.
- **Q8. Vertex-side extras — NOT DETERMINED.** Material vertex constants (1, 1, 0.4, 0) and the emitter runtime
  GPU property tables were not interpreted.
- **Q9. Marker sound — NOT DETERMINABLE FROM MAP DATA.** Each marker object has a looping-sound attachment
  (`sound\visual_fx\gasoline_fire\gasoline_fire`, started when the object is created, `sub_82941E38` →
  `sub_82379E80`). Round 4: the looping-sound tag in the map holds no track or gain data, only a few small fields
  (a 7.0 and a 15.0 float, and the 32-bit value 0x2D83DBA7, which looks like an identifier into the separate
  sound bank). Volume, falloff and audibility live outside the map tag and were not read.
---

## Round 3 changes

1. Removed every gap-filling choice: the "continuous pulse with random offsets" and "fake bloom sprite" recipe
   items and the "expected appearance" paragraph under HDR. Section 10 is now a checklist of traced behaviour
   with named gaps.
2. Added section 2.1: marker objects are created only when the held piece or target changes (`sub_825826B0`,
   `sub_825827B0`), and the effect is created by the object-attachment system (`sub_82941E38`, `sub_82942238`,
   `sub_82454C50`).
3. Added section 2.2: attachment-created effects are always looping (request flags 0x87 → instance looping flag
   in `sub_82200638`); loop index −1 wraps to event 0 (`sub_824599D8`); with "run events in parallel" each
   1/30 s event start creates new particle systems (`sub_82459B78`, `sub_8245D7F0`).
4. Added section 2.3: the emission accumulator (`sub_8226C918`): carried fraction, starting count once per
   location, rate × time step, floor spawn, max-count clamp; accumulator starts at 0 (`sub_825ED3A0`). Recorded
   that these steps do not yet reproduce visible particles, and what must be read next.
5. Zoom effect on the near fade resolved (`sub_822460A8`, `sub_8262EFE8`); far fade is unaffected.
6. Found the looping sound attachment on the marker object (Q9).
7. Open questions restated with status; Q2, Q3, Q4, Q7, Q8 remain not determined.

## Round 4 changes

1. Section 2.2 corrected: `sub_8245B230` at the end of an event handles only the event's parts block; this
   event has none, so the event end sends nothing to the particle systems.
2. New section 2.4: emission is gated per system per frame by `sub_82271030`/`sub_82265A40` — a system emits
   only while it is its location's current event instance in its duration phase; a newer loop iteration
   supersedes it (stops emission, deletable when empty, `sub_82277F28`). `sub_8226C918` is confirmed as the only
   spawner (GPU systems included). The restart paths that re-add a starting count (`sub_822711D8`, messages 11 and
   12) are not taken by this effect.
3. Result recorded: with starting counts 0.2/0.3 and a 1/30 s emission window, each system's accumulator stays
   below 1 (ring 0.2, rays ≈0.333), so static reading predicts **no particles at all**. Labelled as conflicting
   with the unverified assumption of a visible glow; settling it requires observing the real game.
4. Summary (section 1), checklist item 4 and Q1 updated accordingly; sections 3–5 are now explicitly the authored
   per-particle look, not a confirmed on-screen result.
5. Marker sound: the map's looping-sound tag carries no gain/track data (only an apparent sound-bank identifier),
   so volume and audibility are not determinable from map data.
6. Random-value routing (Q2/Q5), intensity-affects-alpha (Q3), the depth-fade switch (Q4), exposure/tone
   mapping/bloom (Q7) and vertex extras (Q8) remain not determined; not pursued because, per item 3, they shape
   particles that are never spawned.

## Round 5 changes

1. Gap found: `sub_82459B78` tests effect-tag **bit 2** ("do not re-use parts when looping"), not bit 1, when
   deciding between creating new systems and restarting existing ones. With bit 2 clear, only the first event
   start creates systems; every later loop sends restart message 12. Sections 2.2 and 2.4 rewritten; the Round 4
   "no particles ever spawn" result is withdrawn.
2. Also corrected: the parallel-events bit (bit 1) is what makes each location finish after its event, after
   which the effect driver `sub_8245A0D8` restarts all locations because the instance is looping.
3. New traced mechanism: message 12 sets a location-record flag that stays set; every particle update
   `sub_822711D8` then clears the emitter's once-only flag, so the starting count is added per rendered frame.
   Result: one ring particle every 5th frame, one ray particle every 3rd frame (6 and 10 per second at 30 fps),
   about 3 ring and 5 ray particles alive, a continuous glow with a ±14% six-times-a-second ripple in the ring's
   summed brightness. First particles after about 3–5 frames; steady state after about 0.5 s.
4. Particle update cadence traced to the per-view render setup (`sub_822460A8` → `sub_821F7C68` →
   `sub_822640F0` → `sub_82277F28`), so counts are per rendered frame, with no emission while paused.
5. Random routing: eight per-particle randoms in state slots 4–7, 22–25; ray spin = 0.15 − 0.30 × slot 24
   (resolved). Ring start rotation is 0.5 turns on the CPU side; its GPU-side application with the
   random-start-rotation flag is not determined.
6. Intensity-affects-alpha traced to the GPU particle shaders (flag passed as a float constant by `sub_8262EFE8`);
   not determined because those shaders were not extracted. Soft depth fade (b228) and exposure/tone mapping/bloom
   remain not determined.
7. Summary (section 1), checklist items 3–6 and open questions updated.


---

