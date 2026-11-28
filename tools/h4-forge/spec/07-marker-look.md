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
