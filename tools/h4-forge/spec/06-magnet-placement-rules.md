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
