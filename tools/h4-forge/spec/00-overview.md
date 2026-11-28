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
