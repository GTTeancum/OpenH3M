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
