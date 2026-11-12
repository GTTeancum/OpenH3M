# Gulch/Cove scenery anchor mathematics

## Current scope complete

Latest user direction: finish the mathematical adjustments within twenty
minutes; in-game testing and follow-up fixes belong to the user. The previous
per-piece proof expansion is stopped. No gameplay test campaign is required.

All 179 Gulch/Cove scenery entries are accounted for: 135 have exported anchor
data and 44 retain source-backed H4 anchorless behavior. The 135-binding pack
is 24,688 bytes and is staged beside the repository runtime executable.
There are no remaining unapplied transforms in this scope.

The final 17 map entries use `p_target = A * p_source + t + correction`.
Rotations use a proper orthonormal basis, with inverse-transpose normals when
dimensions change. Known construction levels are retained on beveled pieces;
local surface corrections address the other remaining offsets. The unchanged
original H4 routines still select and align the markers at runtime.

Radio Antennae, Weapon Holder, Glass Sail and Sniper Nest have no matching H4
object. Their anchors are authored on native geometric supporting planes in
the same H4 marker format. No substitute gameplay or snapping code is added.
The exporter now accepts both signs of an identity quaternion, fixing omitted
stock props. Source-backed models retain their original marker frames through
the mathematical transform.

Numerical checks cover all exported positions, orientations and search bounds.
The historical 118 detailed proofs remain recorded; the remaining 17 entries
have equation checks, not claims of in-game validation. All seventy original
H4 bodies remain unchanged. Native maps, saved-variant formats, physics,
network behavior, accepted anchor visuals and native editing controls are
unchanged by this pass. F7 framerate unlock remains a separate pending task.

Staged pack SHA-256: `341fb93c4d3db26bf08eebd6ee2b97aa0deda4c737e9c102b847d3aee2be6661`.

## Historical detailed proofs

| Piece | Result on both maps | Correction |
| --- | --- | --- |
| Room Triple | All 6 anchors verified | Match the six entrance thresholds, including recessed side floor lips and three distinct floor levels. |
| Tower | All 5 anchors verified | Map the four ground entrances and upper balcony opening to exact local floor surfaces. |
| Dish / Dish Door | All 4 / 2 anchors verified | Use the identical front geometry for common base/upper mating references; correct Dish rear support depth. |
| Door 2 | All 10 anchors verified | Map feet and middle roles to the narrower target opening while preserving original offsets and full frames. |
| Room Double | Both anchors verified | Derive both entrance centers from actual wall sections and place them on the floor edges. |
| Wall Curve Short | All 8 anchors verified | Match actual end-cap angles, widths and height tiers. |
| Antenna | All 3 anchors verified | Rotate -90 degrees; preserve cap-opening references and the base point. |
| Base Strut | All 7 anchors verified | Match upper face/base references and actual tapered-foot intersections. |
| Bunker Full | All 4 anchors verified | Rotate 45 degrees and match both diagonal supports and floor/roof references. |
| Teleport Frame | All 4 anchors verified | Match actual base supports and bottom level, retaining complete authored frames. |
| Cylinders Small / Big | All 4 anchors on each piece verified | Correct radius/height; rotate the large cylinder 90 degrees to align the raised pair. |
| Brace | All 6 anchors verified | Map the two top and four foot roles onto measured construction faces and foot centers. |
| Crenel Full | All 4 anchors verified | Correct the outer X/Z references and principal front plane; retain every authored frame. |
| Column | All 8 anchors verified | Correct center/tier offsets and two source yaw errors to the measured cardinal faces. |
| Crenel Notch | All 4 anchors verified | Match actual end width and upper surfaces while preserving authored frames. |
| Arch Brace | All 5 anchors verified | Correct the construction Z origin and map side roles onto Y=+-1.2 bevel edges. |
| Arena Wall | All 9 anchors verified | Y scale 5/6; Z scale 60/59. |
| Arena Window | All 16 anchors verified | Map the rectangular source roles onto the six-edge target profile; rotate five side frames onto the sloped ends. |
| Bank, 1x1 | All 3 anchors verified | Origin correction and bounded authored-noise removal onto exact base-edge midpoints. |
| Bank, 1x2 | All 3 anchors verified | Translate X +0.009595917, Y +0.001142657, Z +0.015420973. |
| Bank, 2x1 | All 3 anchors verified | Existing Y reflection and origin correction confirmed. |
| Bank, 2x2 | All 3 anchors verified | Translate X -0.002733920, Y +0.002239241, Z +0.007239699. |
| Bridge 2x1, 2x2, 2x3, 2x5 | All 4 anchors on each size verified | Match the actual end planes and preserve the two deck-relative tiers. |
| Dish Antenna | All 12 anchors verified | Resolve the child-node physics frame; correct four radial levels and add both previously absent bindings. |
| Base Round | All 10 anchors verified | Prove the front floor, outer ledges and roof; remove sub-0.00011 marker noise. |
| Bridge Diag | Both anchors verified | Match both entrance centers and the zero-height deck. |
| Cover 2 | All 5 anchors verified | Correct Z origin and upper Y ends while preserving foot centers and original vertical clearance. |
| Bunker Covered / Low | Both anchors on each piece verified | Correct the front entrance depth and each model�s floor origin. |
| Wall 2x2 | All 8 anchors verified | Match actual X/Z support planes while retaining the two principal wall faces. |

Arena Wall's unadjusted anchors describe thickness 0.6 and height 11.8, while
the actual construction envelope is 0.5 thick and 12 tall. Consequently raw
anchor spacing leaves a 0.1 face gap or produces 0.2 vertical overlap. The new
scales map every corresponding plane correctly, preserving all cardinal
anchor-frame directions.

The bank proofs establish all four convex planes, all four core vertices, the
identity root/body transforms, the render envelope, and the anchor locations
at the triangular base-edge midpoints. The target converter shrank bank
vertices along their bounding-box axes. That changes the diagonal plane's
normal; treating it as a uniform plane offset would be incorrect. The proof
reconstructs that measured per-axis shrink before deriving contact geometry.
Bank 2x1's marker frames are reflected as proper orthonormal frames; the other
three banks retain their authored H4 marker rotations.

### Cove blocks and ramps

Fifteen previously missing block bindings now have complete proofs and are
included in the runtime pack. `box_anchor_geometry.json` lists their reviewed
construction planes; `anchor_aliases.json` supplies explicit label mappings.
Each proof establishes the full eight-vertex/six-plane collision box, its node
and body transforms, six corresponding planes in the actual rendered mesh
(face triangles or beveled support edges), every anchor position and the
independently rotated original marker frames. The collision cores of these
blocks use one radius of inset; the earlier banks use two. The verifier checks
the convention per piece instead of assuming one universal skin correction.

Block 1x2 needs a 90-degree rotation and a vertical origin adjustment. Block
3x3 Short needs a +0.1 vertical adjustment. Several others have smaller origin
errors. A bounded offline projection removes measured authoring noise of at
most 0.005 units from these block anchors; it is not a replacement for H4's
runtime selection/alignment logic. Decorative render protrusions are retained,
so proving a construction plane does not claim every decorative ridge is flush.

Ramp 1x2 and Ramp 1x2 Shallow also pass. The normal ramp needed X +0.1; the
shallow ramp already matched. Their complete six-vertex/five-plane wedge
geometry, three construction endpoints and outward frames are verified.
Beveled tips are checked as intersections of measured support planes, with
their actual point-to-render distances recorded separately.

### Bridges and the remaining flat slabs

All four straight bridge sizes pass on both maps. Their four original markers
retain two end-face tiers: the deck level and 0.15 below it. The lower tier is
an end-face reference, not the bridge bottom. Every point is within 0.0001
units of its actual end triangles, with the original outward frame unchanged.
Matching the same tier cancels its deck offset algebraically, so the decks
align across lengths without enumerating object pairs. Bridge 2x3 uses its
measured 2.9989-unit end spacing; the other lengths are 1, 2 and 5.

Four more Cove block mappings are proved and exported, bringing the added
block mappings to nineteen. Block 1x1 Short needs only bounded authoring-noise
removal onto X/Y=+-0.5 and Z=0/0.5. All eight points lie on actual mesh triangles
within 0.00002 units. The proof resolves both collision boxes and the tapered
upper collision cap, retaining that authored cap unchanged.

The other three flat slabs have different thicknesses from the H4 markers:
2x1 and 2x2 are 0.255 units thick; 3x3 is 0.299468. The 2x1 slab also extends
from Y=-0.5 to +0.529417. Positive diagonal transforms map all eight original
side-midpoint/top/bottom roles onto their measured support planes, preserving
the cardinal frames. All six render supports, substantial top/bottom faces,
complete convex collision topology and identity body transforms are checked.
The native collision skins are recorded separately: they do not exactly follow
the visible slabs. The 2x1 collision bottom is slightly tilted, so treating it
as an axis-aligned box would be wrong. No collision or map data is rewritten.

### Bridge ramps, walls and railings

Ramp 2x2 and all three bridge ramps now pass. The bridge ramps were missing
bindings; their H4 sources are `ramp_3`, `ramp_4` and `ramp_5`. The two original
entrance markers map to the intersections of measured end planes and the
main walking-deck plane. Extensive deck triangles and three centerline ray
intersections independently distinguish that plane from the underside and
raised railings. All compound leaves and node/body transforms are resolved.
Beveled ends are recorded as construction-plane intersections, not claimed as
flat triangles at the exact corner. The proof checks the original outward
frames and the source entrance span/rise as well as the target positions.

Wall 2x2 passes on both maps, with new mappings for Cove's Double Window and
Double Wall. All eight original front/back perimeter roles are preserved.
The principal Y faces are at +-0.1; decorative trim remains outside those
planes. X and Z follow the actual support planes. Double Window's source
faces are asymmetric (-0.15/+0.1), requiring a centered 0.2-unit target span.
H4's marker-direction difference is retained: Double Wall's side markers face
outward along X, whereas the 2x2 wall/window markers face along Y. Each native
collision box is fully reconstructed, including the differing inset rules;
no common skin convention is assumed and no native hull is rewritten.

All three Cove railings have new, proved bindings. The source cap is higher
on +X; the target cap is higher on -X. A 180-degree turn and height adjustment
map the two cap planes correctly. The target height is about 0.39884 rather
than 0.5. The proof reconstructs all ten target convex vertices and seven
planes, checks extensive triangles of both cap planes, and verifies all six
original anchor roles and rotated frames. End markers share the base-relative
height 0.180648, so matching ends algebraically preserves equal base heights
across lengths. The long source's 0.007326 lateral endpoint error is corrected
to the centerline through an explicitly bounded 0.008 adjustment; the global
projection guard allows at most 0.01, and other frames keep their own tighter
limits. These are offline marker-data corrections, not new snap logic.

### Different profiles and multiple nodes

Arena Window is not a translated rectangular reskin. Its Reach geometry has
a six-edge X/Z profile, extruded through Y=-0.5 to +0.5. The proof reconstructs
all twelve collision vertices and eight planes, then independently checks all
eight support planes against every referenced rendered vertex. All sixteen
original anchor roles remain: left/right, front/back, center, and three heights.
Five side-facing anchors require a 45-degree Y rotation onto the sloped ends.
Other authored frame directions are preserved. The native motion type is 2,
so its exported default remains Normal, unlike the authored Fixed pieces.

Staircase's four anchors pass after a 180-degree Z rotation, a Y scale of 1.25,
and an origin correction. The scale follows from the target's 2.5-unit lanes
versus the source's 2-unit lanes. All four resulting points lie within 0.0002
units of the corresponding actual faces, with independently checked outward
directions and floor levels. Its sixteen collision leaves are resolved through
the MOPP/list hierarchy; an unresolved compound transform cannot pass.

Dish Antenna has an identity root and a child rotated +90 degrees about Z.
Its render vertices already use object bind space; only its node-local physics
requires that child transform. Applying it to both would double-rotate the
mesh. `node_frames.py` checks the hierarchy against every stored inverse bind.
Rotated collision bounds independently corroborate the unrotated mesh bounds.
This distinction is also supported by Reclaimer's pinned
[H3 model reader](https://github.com/Gravemind2401/Reclaimer/blob/36224d7a4581f2a1f255099bf706aa56be9f6e21/Reclaimer.Blam/Blam/Halo3/RenderModelTag.cs)
and [mesh import path](https://github.com/Gravemind2401/Reclaimer/blob/36224d7a4581f2a1f255099bf706aa56be9f6e21/Reclaimer.RMFImporter/Reclaimer/blender/BlenderInterface.py).

All twelve Dish Antenna markers preserve their original heights, threefold
angular roles and orientations. Four corrected radii match ordered ray/triangle
intersections for the cap ring, upper stem, outer feet and inner collars, each
within 0.0002 units. This identifies the relevant radial feature rather than
passing from an arbitrary nearest surface. The exporter permits this reviewed
multi-node binding and validates its inverse binds before emitting it.

### Bounds used by the editor

H3 tag spheres can have nonzero centers, while the H4 adapter supplies object
origins. Copying the radius alone could reject a valid pair before checking
its anchors. Export now conservatively encloses the native sphere about the
object origin and also includes all exported anchors. The triangle-inequality
enclosure and anchor containment checks pass for all 124 bindings. This is an
editor-data correction; native map bounds and collision are unchanged.

### Source-backed anchorless entries

`anchorless_policy.json` records the reviewed mappings for rocks, grid, lights,
screen effects, barriers, pallet, fusion coil, shield door, kill ball and golf
props. The verifier reads their actual H4 marker groups and requires no
`sandbox_magnet` points, then checks that no runtime binding was emitted.
Rock policy is based on all four H4 Ravine Forge rock models, not a claim that
the Reach and H4 rock meshes are identical. These 44 entries are accounted for
separately from the 116 geometry proofs.

## Evidence and reproducibility

Run from the repository, using the installed Python with `-B`:

1. `tools/h4-forge/inventory_scenery.py`
2. `tools/h4-forge/inspect_scenery_render_planes.py --prefix ""`
3. `tools/h4-forge/inspect_scenery_render_planes.py --prefix Block`
4. `tools/h4-forge/export_bindings.py` after reviewing any data changes.
5. `tools/h4-forge/inventory_scenery.py` to refresh binding coverage.
6. `tools/h4-forge/measure_anchor_residuals.py` for unresolved-piece diagnostics.
7. `tools/h4-forge/verify_scenery_math.py --check-pack` for the final proof report.

The inventory reads the installed palettes independently of the existing
bindings. It records map hashes, all rows, node and physics references, raw
collision geometry signatures and source-name candidates. Candidate aliases
are research leads; they do not alter runtime bindings or constitute proof.

The verifier reads the actual H4 cache and checks current map hashes. A proof
must establish the node/body relationship, geometry, corresponding anchor
planes/edges, applicable orientation transform and construction spacing. It
also compares every proved anchor to the exported runtime binary. Bounds
alone, nearest-neighbor fit scores and matching names cannot pass a piece.

Private outputs are under `work/h4-forge-research/isolated/`:

- `scenery-inventory.json` — full palette accounting, hashes and candidates.
- `scenery-geometry.json` — target geometry and node/body metadata.
- `scenery-math-verification.json` — per-entry proofs and unresolved status.
- `render-planes-all.json`, `render-planes-block.json` and `render-triangles/` — actual referenced triangle data and hashes.
- `unresolved-anchor-residuals.json` — every available unresolved source marker measured against its own target mesh, without a pass verdict.

Corrected data is staged beside the repository executable. The exported and
staged marker packs have matching SHA256 values. No native game runs were
performed for this mathematical audit; no map assets, authored physics or
saved-variant formats were modified.

The pack contains 115 bindings / 21,880 bytes. Existing frame regressions pass,
and all 70 extracted H4 function bodies still match ReXGlue output exactly.
The goal remains active. Large residuals on Pyramid, Corner 4x4, the small
circular ramp and other pieces require construction-frame review; a small nearest-surface
distance is equally insufficient to pass an anchor on the wrong face.

### Full Base Round and compound entrance proofs

Base Round now has complete mathematical coverage of all ten markers on both
maps. The proof resolves all 49 collision leaves and checks the actual target
mesh: three front-floor intersections at Y=0/Z=0, three outer ledge roles at
Z=-0.2, and four points on the actual Z=1.6 roof. The rear ledge slopes slightly
inward; three interior ray intersections establish its plane and extrapolate
through the small bevel to the construction edge. The side ledges are flat.
All original marker axes retain the 180-degree turn, and the 11/12 horizontal
scale is checked against the source/target construction diameters.

Corrections below 0.00011 remove source coordinate noise. All three flat-face
markers now have exactly Y=0 and Z=0. The whole mesh lies in Y<=0, so a half
turned about that seam occupies the opposite closed half-space with matching
floor heights. This proves the reported disc seam algebraically. The earlier
native joint evidence remains historical; no new game run was required.

Bridge Diag's two anchors now lie at the measured end-cap centers
(2.5,-1.5,0) and (-1.5,2.5,0). End spans independently establish both two-unit
widths, and interior rays establish a shared zero-height deck. The source's
marker directions, including -Y on its positive-Y entrance, are preserved.
Cover 2's five markers receive a -0.1 Z origin correction and measured upper
Y ends of +-2.009992. Its foot centers remain at Y=+-1.85. The proof preserves
the source's common vertical clearance and independently checks both foot
faces, upper construction planes and all thirteen compound leaves.

Covered and Low bunkers retain their original half-unit entrance rise, with
Y=-1.2/+1.2 replacing the source's -1.2/+1.25. Their floor pairs are -0.5/0 and
-0.35/+0.15 respectively. End/floor planes and actual centerline intersections
establish both roles and unchanged outward directions. Compound resolution
now handles planar polygons with positive collision radius: it proves two
opposing face planes and the complete polygon boundary instead of assuming
every leaf is a solid polyhedron. Covered has nine such leaves; Low has five.

Bunker Low's native leaves 10, 11 and 14 have three stored support planes that
conflict with their own vertices. The report records these exact discrepancies;
those planes are excluded as geometric evidence and left untouched in the map.
They belong to bottom/roof features away from the entrance levels. The anchor
proof uses actual rendered entrance surfaces and resolved body/node frames,
so it neither depends on those planes nor claims a native collision repair.
This adds no broader map-validation or repair task.

### XL-ramp correspondence

The earlier unbound XL candidate is now resolved as `fw_unsc_c_ramp_4x2`.
A yaw/translation alone was insufficient: source and target exchange their
upper/lower profile faces. The reviewed mapping rotates horizontal directions
-90 degrees and explicitly reverses the four height roles onto actual target
face intersections. This is a geometry-role remapping, not a claimed rigid
shape transform. Complete marker bases stay proper, outward and upright.
The full source/target prism and mesh-section proof is described below.

## Remaining work

- [ ] Prove the remaining existing bindings, including all anchors on previously adapted pieces.
- [ ] Resolve missing architectural aliases and multi-node coordinate frames against geometry before adding bindings.
- [ ] Resolve remaining source mappings, including architectural aliases and stock utilities not covered by the anchorless policy.
- [ ] Correct all discovered mismatches and finish per-entry mathematical coverage.

## Arch Brace construction correction

Both maps now pass all five original anchor roles. The previous Z shift
(-0.975056853) aligned render minima, but those minima did not identify the
construction ledges. The corrected shift is exactly -1 after the existing
180-degree yaw and X/Y origin correction. The X-facing anchors meet the
actual end/ledge planes at (2.9,0,3.1), (1.9,0,0.9), and (-1.9,0,0.9).

The two side anchors retain their authored lateral X=0.312716347. Explicit
source-level mapping takes the rotated source Y values +1.170733166 and
-1.174299049 to the measured target faces at +1.2 and -1.2. Their height is
-0.75, where the vertical faces meet the bevels; -0.7 would be the wrong
surface. This is a reviewed dimensional correction, separate from the
existing bounded marker-noise projection. Unknown or ambiguous source
levels are rejected by the exporter.

The proof resolves all 19 native collision leaves, checks every original
rotated basis, witnesses the required actual mesh planes, and checks every
marker against the relevant face triangles. Maximum face residual is below
0.00012. Both side markers also meet measured bevel triangles within
0.00008. No map, native physics, variant format, or runtime snapping code
changed. The exported and repository-staged 108-binding pack matches the
final mathematical report; all 70 original H4 function bodies still match.

## Column, Crenel Notch and two more blocks

Column's eight source roles now map to the actual 0.3 by 0.3 by 1 construction
box. Three explicit coordinate-level mappings remove the inconsistent source
centers and negative bottom height. Two source normals differ by approximately
4.5619 degrees from their target faces; reviewed upright yaw mappings correct
those normals. The other six orientations remain cardinal. Unknown source
positions or orientations fail export. The proof checks complete native box
topology, its two-radius collision skin, six actual mesh planes, all eight
side/tier roles, and the retained 0.01 edge bevel.

Crenel Notch's native base is a tapered prism, not a rectangular box. Its
complete eight-vertex profile and all three compound leaves are resolved.
The two bottom end anchors now use target Y=+-1.25 rather than the source
+-1.2, with Z=-0.5. At X=0.05, rays through both original upper lateral
positions independently intersect the mesh at Z=0.507503053. Those points
replace the previous Z=0.5 references. All four original frames are retained,
including the two authored -Y upper normals. Bottom corner bevel clearance
is below 0.0057; upper surface residual is below 0.0000001.

Cove's 1x4 and 3x4 blocks now have bindings and complete eight-role proofs.
`detailed_box_anchor_geometry.json` records independently reviewed source,
native-collision and target-construction dimensions. All six target planes
have substantial actual mesh faces. The 1x4 ends are X=+-2.00774; its side
center is Y=0.00005, and construction height remains one. The 3x4 ends are
X=-1.99849/+2.00003, Y=+-1.5, Z=-0.49989/+0.5. Each uses its true construction
center for side-midpoint roles. Cardinal frames are preserved.

Native collision retains its authored nominal box and one-radius skin.
Measured decorative relief extends less than 0.0092 beyond the 1x4 planes
and less than 0.0002 beyond the 3x4 planes. Anchor-to-surface residuals also
record the existing relief/bevels; these proofs do not claim that decorative
triangles become flush everywhere or that native collision was changed.
That pass produced a 110-binding pack (20,884 bytes) passing all 73 geometry proofs and
all search-sphere checks, matches the repository-staged bytes, and retains
all 70 original ReXGlue H4 function bodies.

## Brace and Crenel Full

Brace's six anchors now use the actual upper faces X=+-0.05 and lower faces
X=+-0.25, correcting the source's X origin by -0.15. The two flat bottom
patches have Y centers approximately -0.9000124 and +0.8999657; their reviewed
construction centers are +-0.9. This replaces inconsistent source offsets
+0.95, -0.95 and -0.8936257. The bottom plane is Z=-1.500693321; a vertical
ray through the top center establishes Z=1.499263286. The proof checks all
six substantial face planes, both bottom-patch extents, every authored frame
and all ten native collision leaves. The existing foot bevels leave
0.0105-0.0107 surface clearance at the construction-plane intersections.

Crenel Full's four outward roles now use bottom (0,0,-0.8), top (0,0,0.5),
and side references (+-1,0.1,0). Actual mesh planes and the two native hulls
independently establish these references. Its broad upper hull supplies the
outer X/top planes; the lower foot supplies the bottom. Both hulls share
the principal front reference Y=0.1. The full H4 marker frames are preserved,
including the right-side marker's different roll. The complete rendered
X/Z envelope stays within 0.00007 of those support planes; local bevel
residuals are below 0.0051. No native shape or physics data changed.

That pass produced a 110-binding pack passing all 77 geometry proofs and matches the
repository-staged bytes. Existing frame regressions pass, and all 70 original
H4 function bodies remain identical to ReXGlue output.

### Door 2 remains unresolved

The source has fifteen collision leaves and target five; a global width
scale does not establish equivalent anchor roles. Source middle references
X approximately +-1.069, Y=+-0.1, Z approximately 0 lie toward the opening,
inside the principal post at that level (source core inner X approximately
+-1.1164 with radius 0.0164). The target opening/post profile differs. Initial
candidate foot centers +-0.75 at Z=-1 lie on the actual bottom, but the four
middle roles require explicit opening/profile correspondence before export.
No Door 2 correction or complete-proof claim was made in this pass.

## Cylinders and Cove corner pieces

Both cylinder sizes pass all four original cardinal roles on both maps.
The small cylinder uses construction radius 1.79613 and common deck reference
Z=1. Its X-side rim extends to Z=1.3, but the original four anchors all share
the deck tier. Measured face residuals are below 0.00006 on X and below 0.017
at the Y-side deck bevel. Four substantial outer faces and interior vertical
mesh intersections establish the radius and heights independently.

The large cylinder requires 90-degree yaw: its original higher Y-side pair
corresponds to the target's raised X-side rim. Its construction radius is
3.1; low roles use Z=2 and high roles Z=2.3. Interior rays independently
confirm both target heights, and the existing outer bevels account for
0.0280-0.0284 surface clearance at the plane intersections. Every original
basis is checked after rotation. The target's fourteen/sixteen native leaves
are fully resolved; native geometry and physics stay unchanged.

Cove Corner 2x2 gains its missing binding. The ten original roles are the
five edge midpoints of polygon (-1,0), (0,-1), (1,-1), (1,1), (-1,1), at
Z=0 and Z=0.2. The entire native ten-vertex/seven-plane prism is reconstructed;
all five actual side faces, both horizontal planes and all ten outward frames
are checked. Sub-0.0000002 coordinate noise is removed. Native collision top
0.1783925 and the decorative upper relief are retained; the visible 0.02 edge
bevel explains the 0.0130-0.0142 construction-corner surface clearances.

Cove Corner 4x4 gains its missing binding with 180-degree yaw and translation
(0.3,0.4,-0.3). Without that rotation, several anchors land in the target's
cut-away corner. All ten source midpoint/end/corner roles now use the actual
positive X/Y mating faces, deck Z=-0.1 and base Z=-0.3. The lower corner tier
retains its original 0.03 height above the base. Complete mesh half-spaces,
four native leaves, actual face sections inside end chamfers, every rotated
basis and measured bevel residuals are checked independently.

The final pack contains 112 bindings / 21,484 bytes. All 83 proofs match the
exported runtime positions, frames and native Fixed defaults. Exported and
repository-staged bytes match; all 112 search bounds pass and all seventy
original H4 function bodies remain identical to ReXGlue output.

## 45-degree corner and Teleport Frame

Cove Corner 45 Degrees now has a verified binding. Its two entrances have
construction width two. One is X=-0.4, from Y=-1 to Y=1. The other runs from
A=(-0.4,1) to B=A+(sqrt(2),-sqrt(2)); its midpoint is approximately
(0.307106781,0.292893219). Both lie on actual outward entrance planes.
A 180-degree yaw maps the original H4 frame directions onto these faces.
The four source roles use deck Z=0.2 and lower tier Z=0.05, preserving the
original 0.15 separation.

The proof reconstructs all eight base vertices and six planes from that
construction quad and its authored collision inset, resolves all six native
leaves, and checks both complete render support half-spaces. Face sections
at Z=0.1 and interior rays independently verify the actual entrance planes
and deck/base heights. The top bevel gives less than 0.0069 surface residual;
lower references are within 0.00002 of the actual faces. Every original
marker basis is checked after rotation.

Teleport Frame now has verified bindings on both maps. All four original
cardinal roles lie on a common target base reference Z=-0.083473511. Actual
base supports are X=+-0.710867524 and Y=-0.688184083/+0.690000474; the X-side
midpoints therefore use Y=0.000908196. The proof separately establishes that
these extrema belong to the base, checks the entire rendered support envelope,
resolves all four native leaves including the 24-vertex base, and preserves
every authored frame. Actual base-surface residuals are below 0.00003 on X
and 0.00047 on Y, including the small existing edge bevel.

Current runtime data has 115 bindings / 21,880 bytes. All 86 mathematical
proofs and all 115 search-bound checks pass against the exported pack. Its
bytes match the repository staging directory; all seventy original H4 bodies
still match ReXGlue. Native maps, physics and saved-variant formats are unchanged.

## Bunker Full

All four original roles now pass on both maps. Source X is mapped onto the
target diagonal axis u=(X+Y)/sqrt(2), using 45-degree yaw. Actual render
support coordinates are u=-1.138054188 and u=1.573972338; the transverse
center v=(-X+Y)/sqrt(2) is 0.000156786. The rear support is an edge extremum,
not a claim that the whole rear has a flat wall. Original front/rear points
are near the source axial extrema; their unequal source values map explicitly
to the corresponding target supports.

The lower and upper references use Z=-0.9 and Z=1.1. Independent vertical
rays just inside both ends confirm those floor/roof surfaces; the recessed
central roof at approximately 1.0838 does not define the end reference.
Existing bevels leave about 0.0281 surface clearance at the front and
0.0162-0.0174 at the rear support intersections. Complete rendered support
half-spaces and substantial horizontal face triangles are also checked.

The original H4 markers deliberately share the same forward direction at
both ends. All four complete bases retain that relationship after rotation;
the proof records the geometric support normal separately from the authored
marker forward. All 26 native collision leaves are resolved, with no native
map or physics edits. The 115-binding runtime pack matches all 88 proofs and
the repository-staged bytes; all seventy original H4 bodies remain unchanged.

## Antenna and Base Strut

Antenna's three original markers now rotate -90 degrees. All six rotated
source render bounds agree with the target within 0.000001, independently
confirming this orientation. The two side anchors are references inside
openings between cap strips. Actual coplanar triangles on either side of
each opening bracket the marker's height at its exact lateral coordinate;
nearest-triangle fitting would incorrectly move those authored references.
Their cap-plane X coordinates are -0.692404151 and +0.504169822, with opening
height ranges approximately 0.569965-0.629950 and 0.559058-0.640856. The base
marker lies on the actual Z=0 surface. All complete bases, including their
roll, and all four native collision leaves are checked.

Base Strut's seven roles now match its upper face, flat base and tapered
foot. Source/target top geometry establishes the -0.1 vertical-origin shift.
The two upper roles preserve their original separation at target Y=0.8;
the bottom uses the actual plane Z=-1.991763830 and Y=-0.25 construction
reference. Native collision retains its slightly deeper bottom.

The four foot markers share their mean source height minus 0.1,
Z=-1.859719670, removing less than 0.00081 of unequal source-tier offsets.
Independent mesh-ray intersections give Y=-0.780221081/+0.283398421 and
X=-0.478595595/+0.478580128; X-side roles use the measured foot center
Y=-0.248411330. Every perimeter point lies on the actual tapered surface.
Upper face residuals are below 0.000025; base and foot residuals are below
0.00000001. Full original cardinal frames and the complete native twelve-
vertex/eight-plane hull are checked without changing physics.

At that stage, both maps passed all ten newly reviewed roles. The 115-binding pack
matches all 92 proofs, all editor search bounds and repository-staged bytes.
All seventy original H4 function bodies remain unchanged. Forty-three
scenery entries remained unresolved at that stage.


## Wall Curve Short and remaining small construction pieces

Wall Curve Short now passes all eight anchors on both maps. The dominant actual
positive end-cap face supplies the normal (0.170981906,0.985274169,0); the
opposite end uses its reflected counterpart. Twelve real cap triangles per end
establish the outer support and full tangential width 0.171712356. Every rendered
vertex lies behind its corresponding support. The two corner roles on each end
and both Z tiers form the complete eight-role set. Original source yaw differs
by about 5.6 degrees; the reviewed correction has an explicit six-degree bound.
The full frames, top/bottom heights and all three native hulls are checked.
Virtual cap corners have 0.0307-0.031 surface clearances from existing recesses
and bevels; they are not claimed to lie on individual mesh triangles.

Cove's 1x1 Tall block now has its missing nine-anchor binding. Its actual height
is 2.5, from Z=-1 to +1.5, versus the source's three-unit span. Outer substantial
rib faces establish X/Y=-0.50728,+0.50718; independent centerline mesh sections
corroborate all four vertical planes. Eight side/tier roles and the top-center
role retain complete cardinal bases. Two source lateral offsets below 0.000448
are removed. The complete box topology, native radius, decoration extending
less than 0.0019 beyond the principal faces and side-cap clearances near 0.0059
are recorded. The center of the top is recessed to Z=1.495613031; its anchor
retains the shared top construction plane at 1.5 for aligned stacking.

Both Cove Y platforms also have their missing bindings. Y Large's two original
high/low entrance roles rotate 180 degrees: the high deck is at X=+2.5,Z=0,
and the low deck at X=-2.5,Z=-0.5, both centered on Y=0. Actual end planes,
main-deck ray intersections and the native deck hulls corroborate those levels.
All nine native leaves are resolved. The existing low entrance rim rises to
Z=-0.462387677 and is retained; endpoint surface residuals are below 0.00007.

Y Small's six roles rotate 180 degrees onto a pentagonal construction profile:
the back face, four side-edge midpoints and a forward tip. The profile is
independently reconstructed from all ten native vertices and seven planes and
corroborated by all seven actual outer support faces. The two native diagonal
plane coefficient residuals are 0.0000331 and are recorded locally. Render
support discrepancies are below 0.00003. Two original diagonal anchor directions
need 18.6/18.9-degree corrections to the target's 45-degree faces; the reviewed
mapping has an explicit twenty-degree bound. The tip direction lies in the
outward normal cone of the two diagonals. Existing top-edge and tip bevel
clearances are recorded, not removed from native geometry.

The resulting pack has 118 bindings / 22,416 bytes. All 97 map-specific proofs
(68 unique pieces), every editor search sphere and the repository-staged pack
match. Frame regressions pass; all seventy original H4 bodies remain unchanged.
No game runs or object-combination campaign were used. Forty-four entries are
source-backed as anchorless and 38 still need complete proofs or corrections.
The goal remains active. No map, console physics or variant serialization
changes are part of this increment.

Staged pack SHA-256: `52013178b298e478f7366ef78635f8c8304ba1ec6f8b25e2b8a829ea439a2173`.


## Stunt Ramp, XL Ramp and Landing Pad

All three newly bound Cove pieces now have complete mathematical anchor proofs.
They add 17 original H4 marker roles; no runtime selection/alignment replacement
or map edit is involved.

Stunt Ramp's five roles rotate -90 degrees. The actual dominant front slope
intersects the principal base at X=-2.003766133,Z=0.003025179. This virtual
construction tip is distinct from the beveled outer vertex. The actual rear
face is X=1.996003261, and the upper landing is Z=1.503029453. The side pair
uses the midpoint X=-0.003881436 and actual Y=+-1.2 faces at the base tier.
All original roles and complete rotated cardinal bases are checked. A local
vertical section corroborates the base and landing; all four native leaves
retain their authored bounds [-2,2] x [-1.2,1.2] x [0,1.5]. Measured surface
clearances are about 0.00368 at the side edges, 0.01928 at the front bevel,
and 0.01417 at the rear edges.

XL Ramp's four end references come from the actual end planes and the two
dominant sloping faces. The thin end at X=-1.998993039 has lower/upper levels
1.986686308 and 2.199971457; the thick end at X=2.000623465 has levels
-0.004466307 and 3.195559563. Both full eight-vertex/six-plane source and target
prisms prove the exchanged slope arrangement. Five independent vertical mesh
sections corroborate both target faces. Original outward horizontal directions
rotate -90 degrees while up remains +Z; the explicit position-level mapping
reverses the vertical roles without inventing a rigid or upside-down frame.
All four anchors have measured edge clearances below 0.009. The complete native
collision hull is retained.

Landing Pad's eight upper/lower perimeter roles map to X=+-2,Y=-4/+2 and
Z=-0.3/0. Its side pairs remain 1.75 units behind the front, at Y=0.25, as
authored in H4; neither the whole-bounds center nor a guessed square-deck center
is used. Source side-reference noise is below 0.00016. The actual six principal
faces, both entrance deck/base sections, twenty-vertex/fourteen-plane base
support bounds, full seven-leaf compound and every original cardinal basis are
checked. Upper side references lie within 0.000004 of the mesh; existing cap
bevel clearances are about 0.00706.

The resulting pack has 121 bindings / 22,952 bytes. All 100 map-specific proofs
(71 unique pieces), all editor search spheres and the repository-staged bytes
match. Frame regressions pass; all seventy original H4 function bodies match
ReXGlue output. Forty-four entries are source-backed as anchorless and 35
remain unresolved. The goal stays active. No game runs or object-combination
campaign were used, and console physics/variant serialization are unchanged.

Staged pack SHA-256: `9b8bcf913e0f6b1c3e6a6164199ff94ff7da740f1a8730e5ea33e19bb65509dd`.


## Ramped Platform, Room Double and Large Walkway

Ramped Platform now has all four original entrance anchors. Source collision
extents establish a 5.4-wide layout versus the target's 4.5, giving a reviewed
5/6 lateral scale. A 180-degree turn places the low ramp at negative X. Actual
target inner rail faces Y=0.5 and 2.1 independently locate its center at 1.3.
The low anchor uses the actual front/base reference (-3.000203133,1.3,-0.999919116).
The three upper roles retain their evenly spaced source arrangement after the
same lateral transformation, at X=2,Y=1.091666667/0.05/-0.991666667 on the measured
deck Z=0.699824188. Each has its own independent vertical deck section. All
complete cardinal bases remain upright and outward; all nine native target
leaves are resolved. Existing edge clearances range from 0.0129 to 0.0189.
The source reader now supports compound shape arrays with complete buffer
accounting, allowing source construction dimensions to be measured directly.

Room Double passes both anchors on both maps. Actual wall-cap triangles cut at
Z=1 expose the left opening [-0.338749062,1.722496955] in Y and the right/front
opening [1.072305653,2.527110446] in X. Their centers determine the new references:
(-2.793519735,0.691873946,0.296669026) and
(1.799708049,1.991210575,0.296669026). Both are exactly incident on the actual
outer floor edges. Independent horizontal rays confirm clear entrances and
vertical sections confirm the floor and more than 1.4 units of headroom.
The source wall gaps establish the corresponding original roles. Both H4
markers deliberately face -X, including the front entrance; every component
of those authored frames is retained, and geometric opening normals are
recorded separately. All 31 target collision leaves are resolved.

Large Walkway now binds the three original H4 `walkway_small` roles at
(-1,0,6), (1,0,6) and (0,7,6). The source references sit six units above the
base; target deck, side and end planes plus independent sections establish
the corrected locations. All three original frames face +X and are retained.
The .1-unit side bevel produces measured corner clearances near 0.07035;
the end reference is within 0.0001 of its actual face. Native collision bounds
extend 0.004637858 beyond the nominal X reference and 0.003885409 beyond Y;
these small authored overhangs remain unchanged.

All 91 Large Walkway collision leaves are resolved. Existing plane residuals
0.000108147 and 0.000104079 are recorded specifically for leaf 24/plane 5 and
leaf 74/plane 5. Leaf 33 has four noncoplanar vertices but only two stored
planes. Its vertices prove a complete tetrahedron of volume 0.000463340;
both stored planes match independently reconstructed faces within 0.0000022.
The verifier now checks this partial-plane representation mathematically
instead of treating the stored plane list as a complete half-space hull.
No collision data was repaired or replaced.

The pack contains 123 bindings / 23,188 bytes. All 104 map-specific proofs
(74 unique pieces), all editor search bounds and the repository-staged bytes
match. Frame regressions pass and all seventy original H4 bodies remain
identical to ReXGlue output. Forty-four entries are source-backed as anchorless;
31 still require complete proofs or corrections. The goal remains active.
No native game runs, object-combination campaign, map changes or variant-format
changes were part of this increment.

Staged pack SHA-256: `a873389e42f9c9303e4ab0d09c90a7952c85862d8d2dd0329d8f6b7e7958a226`.


## Door 2 and Large Brace

Door 2 now passes all ten anchors on both maps. Its original H4 opening is
2.2 units wide; the actual target opening at the middle tier is 1.399984616.
Uniform width scaling would incorrectly change foot offsets, header placement
and the original opening clearances. Native source foot/jamb features and
independent target triangle sections instead establish a separate translation
for each role. The target base section has intervals
[-0.899870002,-0.600030256] and [0.600000154,0.899839901]; their centers locate
the two feet. Source foot offsets, including the unequal front/back left-foot
positions, are retained. The header retains its original lateral offset.
All heights relative to the measured base and all front/back Y distances are
preserved, as are the ten complete original marker frames.

The four middle markers intentionally sit inside the source opening. Their
original clearances from the inner jambs are 0.030675748 and 0.032657603.
Those same clearances are proven against the target geometry; the verifier
checks unobstructed rays through these opening positions instead of falsely
requiring them to touch the visible jamb. The other six surface residuals are
below 0.00003. All five native target collision leaves are resolved.

Large Brace was missing its alias. Its five original roles are now bound on
Cove. Source/target native features and actual target triangle patches establish
X translation -1, bottom Z=-2, front Y=1.5 and beam end Y=-9. The beam end is
4.5 above the base; the two front references retain heights 1 and 3.1. Both
footprints are .9 long, moving the source foot center .75 to target .45 while
retaining the authored opposite-foot offset .125889421. All lateral offsets
and every complete orientation are preserved. Both foot references touch the
actual geometry within 0.000002; measured beam/front bevel clearances are below
0.0101, with independent interior sections confirming the corresponding faces.

All eight native Large Brace leaves are resolved. Leaf 1/plane 4 has the existing
0.000157235 support residual, recorded against that exact shape/plane; it is
not silently treated as exact containment and no collision data is changed.

Coverage is 107 map-specific entries / 76 unique pieces, plus 44 source-backed
anchorless entries; 28 remain unresolved. The exported and repository-staged
pack contains 124 bindings / 23,348 bytes. Every proved anchor and all 124
search spheres match the export. Frame regressions pass; all seventy original
H4 function bodies still exactly match ReXGlue. Native map data and saved-layout
formats were not modified. No game runs or object-combination tests were used.

Next evidence: Covered Walkway's native body has motion type 2, so the fixed-only
compound proof cannot be reused unchanged. Its source has 107 collision leaves
and nine authored roles; target has 56 leaves. Actual feature correspondence
still needs proof. Preserve that native motion type; do not change it to make
the verifier accept the piece. Research is in `covered-walkway-details.py`.

Staged pack SHA-256: `bd1982e2750750a1a445a24f8c428eab17b52f209594f0d4975f0ff63e672c26`.


## Dish and Dish Door

Both variants now have complete proofs on both maps: all four Dish anchors and
both Dish Door anchors. The actual target central front surfaces have matching
120-vertex sets within 0.000001403. Both meshes are entirely behind Y=0 within
0.000001, so that shared plane, the common actual base Z=-1.4, and a common
upper reference give consistent front-to-front placement. Their full native
compounds contain 26 and 30 leaves respectively; all resolve unchanged.

The upper H4 reference is intentionally in open space. Its height above the
source base is 1.496693611 for both variants within 0.000001 and matches the
source central cap's upper construction level. That original common height is
retained, giving target Z=0.096693635. Its measured target surface clearance is
about 0.507664; independent rays prove the open space. It is not falsely
classified as a point on the bowl floor. The front base reference has the
existing lower bevel clearance about 0.026606, independently checked by a
nearby vertical section.

Dish Door's source lower marker sits 0.040163418 above its base, unlike Dish's
lower marker. Keeping that discrepancy produced inconsistent references on
identical target front geometry. Both lower markers now use the measured
common base. The upper marker heights already agree after accounting for each
source model's own base. Transverse source noise below 0.000238 is removed;
all complete original frames rotate 270 degrees, preserving every axis.

Dish's rear construction plane was approximately 0.060738 too far back.
Both rear roles now use the actual supporting plane Y=-5.852496624 while
retaining their original heights above the source base. The lower role meets
the actual rear surface within 0.000006. The upper role deliberately stays on
the same construction plane through the native bevel, with measured nearest
surface clearance 0.0237 and a separate horizontal section confirming the
0.026-0.029 setback at its height. All rendered points satisfy the rear support
half-space; no map geometry or collision data was modified.

Covered Walkway's native motion-type-2 body and all 56 leaves now pass the
compound geometry checks directly. The helper accepts an explicit expected
native motion type and records it; the default remains type 5 for prior fixed
pieces. This changes the verifier only. Covered Walkway still remains
unverified because its nine actual anchor feature correspondences are not yet
established. In particular, upper side roles and the two different foot pairs
must not be guessed from a single global scale/translation.

Coverage is 111 map-specific entries / 78 unique pieces, plus 44 source-backed
anchorless entries; 24 remain unresolved. All exported proved anchors and all
124 search bounds pass. The 23,348-byte private pack matches the repository
runtime staging. Frame regressions pass, and all seventy original H4 bodies
still match ReXGlue exactly. No game runs, object-pair campaign, native map
edits or saved-variant format changes were used.

Staged pack SHA-256: `71a923413578147e51896c8f1c687455226bc37de377e340a71cfea4ab4bb7bb`.


## Pyramid

All five Pyramid anchors on Cove now pass. The H4 structure faces the opposite
direction, requiring a 180-degree rotation of every full marker basis. Its
dimensions and origins differ by feature, so a single scale/translation does
not establish the ramp entrance, rear floor and rear roof references.

Source leaves 4/10/7 identify the two side and front ramp entrances; leaves
8/12 identify the rear roof and lower floor. The original markers lie at the
corresponding cap supports and upper regions, checked against those vertices
and skin radii. Actual target side and front cap triangles have exactly matching
vertical bounds [-0.453671613,-0.010108890]. All three entrance anchors therefore
use the common actual upper edge Z=-0.010108890. The side centers follow from
the independently measured inner/outer construction planes Y=1.511823654 and
3.011823654, giving Y=2.261823654 at X=+-7.5. The front anchor uses X=0 and the
actual front face Y=-4.488176346.

Intersecting the actual rear-face triangles at X=0 produces two disconnected
vertical sections: [-1.953672098,-1.810109473] for the lower floor and
[0.425321818,1.511923597] for the upper structure. Their upper edges directly
locate both rear anchors at Y=3.011823654. The intervening opening exceeds
2.2 units; an independent ray confirms a clear entrance. Every anchor is
incident on its actual target cap within 1e-10, and all rendered vertices lie
behind its outward supporting plane. No object-pair campaign is needed.

All ten native target leaves resolve. Existing native support residuals are
recorded specifically for leaf0/plane5 (0.000161551), leaf1/plane4 (0.000101261)
and leaf2/plane5 (0.000162459); no collision repair or motion change is made.

Coverage is 112 map-specific entries / 79 unique pieces, plus 44 source-backed
anchorless entries; 23 remain unresolved. The 124-binding / 23,348-byte export
passes every proved anchor and search-bound check and matches the repository
runtime staging. Frame regressions pass and all seventy original H4 bodies
still exactly match ReXGlue. Maps and saved variants were not modified.

Next evidence: `tower-openings.py` identifies the actual Tower ground wall
sections at Y=2.20103/-1.69897 and X=-1.99643, plus upper structures at X=-2.4.
Its source upper-left reference may be a balcony edge, not the upper doorway;
do not assume that every marker identifies the nearest opening. All five
Tower roles remain unresolved until this distinction is established.

Staged pack SHA-256: `22d82a0e278719559d4c0bae52a7e592531036b7f740ac42931b85b676b0201e`.


## Tower

All five Tower anchors now pass on both maps. Source convex-leaf line sections
identify four ground entrances and one opening in the upper balcony railing.
The upper-left marker does not identify the nearby upper doorway. Its source
opening lies between Y=-0.222266018 and 0.771450076, with its floor edge in
source leaf 41. Ground floor references come from source leaves 26 and 57.
All source markers lie inside their corresponding clear opening, close to its
center, and at the matching native floor edge/tier.

Actual target triangle sections 0.05 inside each wall identify the apertures.
Independent outside-to-inside rays reject the decorative upper trim gap, which
is blocked by the railing, and retain the free balcony opening. Each final
height is derived from a vertical ray through that exact floor-edge position,
not from the largest floor plane elsewhere in the object. All five anchors
are incident on actual geometry within 1e-10:

| Role | X | Y | Z |
| --- | ---: | ---: | ---: |
| Front right entrance | 1.586139884 | 2.201034106 | 0.399971412 |
| Front left entrance | -0.700023959 | 2.201034106 | 0.396170392 |
| Left ground entrance | -1.996432443 | 0.701110967 | 0.399971412 |
| Upper balcony opening | -2.400003672 | 0.707617330 | 2.399193662 |
| Rear ground entrance | -0.700023959 | -1.698974996 | 0.396170392 |

The ground panels differ in height by 0.003801020, and the balcony edge slopes
slightly below the larger upper floor plane. Those native features remain
unchanged. All five complete original frames are preserved. The target's
identity node/body and all 59 native leaves pass the compound checks.

The offline adapter now supports an explicit full-position role mapping.
Tower needs it because four markers share source Z=0.4 but map to two distinct
actual target floor heights. Matching requires a unique reviewed source point
within a bounded tolerance; stale source positions, duplicate/ambiguous roles,
nonfinite target coordinates and mixed position-mapping schemes fail closed.
Those rejection cases pass alongside the existing frame regressions. This
only prepares marker data; original H4 selection/alignment code is unchanged.

Coverage is 114 map-specific entries / 80 unique pieces, plus 44 source-backed
anchorless entries; 21 remain unresolved. All proved exported anchors and all
124 search bounds pass. The 23,348-byte pack matches repository runtime staging.
All seventy original H4 bodies still exactly match ReXGlue. No native map,
physics or saved-variant changes, game runs or object-combination tests were
part of this correction.

Staged pack SHA-256: `bc609ca908e907e7d5c209df98efb8a3209a1d4e0904be988c5ec401faab5b65`.


## Room Triple

All six Room Triple entrance anchors now pass on both maps. Source convex
sections identify the rear, three front and two side openings. Each original
marker belongs to the matching native threshold cap (source leaves
79/65/31/104/12/15), within 0.025 units of its expanded edge and upper surface.
Every marker lies in the corresponding clear aperture, within 0.025 of its
center. This establishes the roles from geometry rather than names or bounds.

Exact target wall sections locate the openings. Vertical floor intersections
reject two decorative front gaps. The side thresholds are recessed: the main
wall lies at X=-5.100132605/+5.099946445, but the narrow horizontal floor lips
end at X=-4.878602198/+4.878416038 before their bevels. Intersecting all actual
horizontal floor triangles with each doorway center plane locates those edges;
using the wall or the broad main floor boundary would place them incorrectly.

All six complete H4 frames are preserved. The corrected positions are:

| Role | X | Y | Z |
| --- | ---: | ---: | ---: |
| Rear central threshold | -0.000093080 | -1.950057120 | -0.496286405 |
| Left side lip | -4.878602198 | 1.247587820 | -0.597284827 |
| Front left threshold | -3.496028289 | 2.449984047 | -0.596324551 |
| Front central threshold | -0.000093080 | 2.449984047 | -0.496286405 |
| Front right threshold | 3.495842129 | 2.449984047 | -0.596324551 |
| Right side lip | 4.878416038 | 1.247587820 | -0.597284827 |

Every point is incident on its actual target surface within 1e-10. The center
thresholds sit 0.100038146 above the wing floors; the side lips sit
0.000960276 below the wings. These native differences remain intact. Source
and target share outward cardinal frames, so no rotation correction is needed.

All 92 native leaves resolve with unchanged Fixed motion. Two leaves are
valid radius-bearing planar quadrilaterals. Leaf 52 has an existing maximum
stored face-plane residual of 0.000011831422684; the verifier checks that exact
recorded residual while still proving the polygon's rank, complete boundary,
opposed normals and edge planes. The exception cannot silently accept a
different leaf/error or bypass the remaining geometry checks. No collision
data is repaired or retuned.

Coverage is 116 map-specific entries / 81 unique pieces, plus 44 source-backed
anchorless entries; 19 remain unresolved. The 124-binding / 23,348-byte pack
passes every proved anchor and search-bound check and matches repository
runtime staging. Frame regressions pass and all seventy original H4 bodies
still exactly match ReXGlue. No game runs, exhaustive pair tests, map changes
or saved-format changes were needed.

Staged pack SHA-256: `e38569913712712cd0a547f35abb2aebff30eac54d87f31bd490cd6bc377fff6`.


## Final transform pass

Bunker Stair's eleven source anchors were corrected on both maps before the
final batch, preserving its virtual under-stair foot reference. The remaining
Tower 3 Story, Tower Tall, Covered Walkway, two circular ramps, Man Cannon and
Long Tunnel use their H4 anchor sets with rotation, translation, dimensional
scaling and explicit construction/surface offsets. Four H3-only object types
use native supporting-plane markers. `anchor_completion.json` records the
source data, matrices, translations, corrections and resulting markers;
`check_transform_equations.py` checks the equations and exported frames.

The completion claim covers mathematical adjustment and staged runtime data.
It does not claim that every combination has been exercised in-game. That
testing is explicitly the user's work under the latest instruction.
