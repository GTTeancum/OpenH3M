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
