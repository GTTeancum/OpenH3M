# Advanced Forge status

### 2026-11-12 13:44 — cancellation passes; deletion visual failure

Prior turn progressed by verifying native menu physics and pitch acceptance.
PID13476 completed its watchdog on the unchanged current candidate. Native
pitch previews1/2 were cancelled, restoring the original identity basis and
pre-preview position (-41.2291374,-197.077316,2.99957681). The subsequent Y
input removed Bank1x1 E2A80004 from occupied native variant records (including
tag identity), but the final capture is completely black. Deletion is NOT
accepted: continuing GPU calls and record removal do not establish a working
view. No reported bridge exception or nonfinite trace value explains it yet.

All three captures inspected individually: cancel-restored.png and
cancel-restored-held.png show restored geometry with menu closed;
delete-black-frame.png is the failing final view. No preview screenshot was
captured in this run; filenames based on requested timings were not treated
as proof of actual stage. Compact cancellation/deletion logs and restored-pose
CSV retained. Added verify_cancel_delete.py for native evidence only, explicitly
labelled NATIVE_RECORDS_PASS rather than overall success; validation JSON
records visual failure. No deployment. Other chat now owns the game slot.

Next action: isolate deletion's camera/monitor teardown from the immediately
following ordinary A input and verify a valid post-deletion view. Do not alter
magnet selection or infer success from the removed saved record.

### 2026-11-12 13:40 — native physics menu and live pitch acceptance passed

Prior turn progressed through editing-only restoration and native property
comparison. Current run PID7756 completed its 180-second watchdog with the
same candidate and reused staging. Bank1x1 E2A80004 was created through the
native palette; the native property menu selected Normal, Fixed and Phased,
then previewed pitch1 and2 and accepted2. All three screenshots individually
inspected: first two show1, last shows2 with the menu still open; the piece's
edge changes visibly. Do not describe these captures as 0/1/2.
Native final saved forward/up vectors yield pitch1.9999999065 degrees.
Return to player restores stock physics flags. No reported preview/bridge
failures. Retained rotation-menu-evidence.log, rotation-accepted-pose.csv,
rotation-validation.json, rotation-preview-one.png,
rotation-preview-one-held.png and rotation-preview-two.png.

Ground creation remains unresolved: existing extracted wrapper evidence has
the same four-attempt/doubling search in both games; it does not justify a
custom offset or prove nested collision equivalence. No guessed change made.
Cancellation, other axes, other pieces and remaining lifecycle cases remain
open. No deployment; single game slot released.

### 2026-11-12 13:35 — editing-only physics restoration passed

Previous goal turn progressed by verifying the airborne creation sequence.
PID19752 reused the same candidate/staging directory and completed its
180-second watchdog. Process-local property requests selected Normal, Fixed,
then Phased for E2A80004. Normal/Fixed held states both use native motion4;
Phased constructs motion6. Release uses motion7, re-grab reconstructs motion6,
and final return to player mode restores original physics flags (reported
0x280 versus original0x80; frozen/force-dynamic/connected bits match).
The 2026-10-28 recorded user decision already makes modes editing-only;
the stale persistence TODO was corrected rather than adding save extensions.

Updated verify_physics_run.py with an explicit original-controller check;
the legacy checker expected the obsolete Phased-disconnect workaround.
Current verification passes exact mode sequence, same datum, native body
classes, restoration, automatic activation, absence of reported errors and
byte-identical object properties against the preceding ordinary creation
variant. Both native version12 records match. This is not a fresh reload or
console test. Native menu activation was not exercised by diagnostic requests.

All three captures inspected individually: physics-first-release.png,
physics-phased-regrab.png and physics-player-restored.png. The last shows the
rifle/player HUD underneath the airborne structure after exiting monitor mode.
Retained physics-lifecycle-evidence.log, physics-validation.json and compact
creation-reference.variant in the reused run. No deployment. Remaining work
includes ground creation, Normal penetration, other pieces and menu/lifecycle
coverage; no claim of full Forge completion.

### 2026-11-12 13:28 — airborne large-item creation sequence passed

Previous turn made progress by fixing native keyframed pose synchronization.
Current candidate 8c04fa7d579a2cd1fa1f958ffa87eb416a65606450720e3c47274284f99ac121
ran the existing creation/manipulation replay with six seconds of monitor
ascent, no forced object pose, no physics-mode override, and a 180-second
watchdog (PID26188, reused staging directory). Created Base, Round E2A80004,
moved it, dropped it, re-grabbed the same datum, moved it back and dropped it.
Both grabs initialize distance7.869545. Submitted Y moves -196.06006 to
-197.74576 and returns to -196.06001; re-grab preserves the dropped pose.
All three native captures individually inspected: creation-held.png,
creation-regrab.png and creation-return.png. Exterior remains outside camera;
large object fills much of the view. Native placement search moves the spawn
point one radius along X but does not raise its Z in this airborne case.
Compact logs retained in creation-evidence.log. Ground-level creation remains
open because prior runs showed a two-radius upward placement search. This
pass does not establish other pieces, Normal penetration recovery or remaining
mode/lifecycle/save behavior. No deployment; game exited and slot released.

### 2026-11-12 13:23 — native keyframed pose-sync correction built and tested

Native82332FF0 explicitly rejects selected-body motion6 and7 at823330F0..3310C
before82118140 reconstructs the object pose and8232E698 publishes it. This
accounts for the observed moving motion6 body with stale object84 origin.
Added advanced_forge_pose_sync.cpp, generated from that exact native function
by generate_native_pose_sync.py. Its sole body change admits motion6; the
native fixed-motion7 rejection and all update/velocity/notification code remain.
The hook selects this path only for a locally owned, valid, unparented scenery
or crate with retained H4 keyframed override and an actual selected motion6 body.
Other objects invoke the unchanged original function. No body-type spoofing,
raw pose writes, magnet changes, or changed movement limits.

Build passed. Native run PID12172 completed its 180-second watchdog in the
reused 20261112-112536-6476 staging directory. With Phased motion6, object
reference and physics-body position now agree: Y progresses from -191.76173
to -212.94727, rather than stalling against a stale origin. Total displacement
from the starting overlap is approximately 23 units. Return movement also
progresses, and Normal restores motion4. All three captures were inspected
individually and retained as pose-sync-held.png, pose-sync-pull.png and
pose-sync-regrab.png. They show the held structure with stable camera clearance
and changing terrain position. Native grab records additionally confirm the
same datum E2A30034 was re-grabbed with distance7.869545; screenshots alone
do not establish identity. Compact records are in pose-sync-evidence.log.
Candidate hashes are recorded in
work/build-temp/forge-candidate.json. Original H4 magnet behavior is unchanged
per the user's decision. Normal-mode penetration recovery, creation clearance,
and other large-piece sequences remain open. No deployment.

### 2026-11-12 13:12 — stale native object origin identified

Previous goal turn made progress by ruling out bounds with native evidence.
Added passive observations at original8244AB68 (before its first clamp): prior
target, accumulated movement delta and actual reference-point callback result.
Built and ran the same reused-staging 180-second sequence; watchdog completed,
game exited, shared slot released. No new captures or deployment.

At ticks1197..1287, forward input remains0.8666667 and movement delta is about
(-0.01143,+0.11490,0), but reference origin remains
(-51.475197,-190.04713,3.6144574). Target converges to Y=-187.06187,
approximately three units from that stale origin. Phased body motion6 persists.
This explains the original H4 displacement cap preventing further progress;
the native object-origin path820A9E58 reads object84 while its physics body moves.
Do not replace this with a different movement cap or raw body-center substitution.
Next implementation: native body-to-object pose synchronization for the privately
keyframed scenery, preserving the body/local-origin transform and notifications.
The root cause of the missing synchronization itself remains to be established.

Re-grab in this run selected E2A10032 (the other overlapping piece); do not count
it as same-piece re-grab verification. Earlier opposed-pair evidence is separate.

### User decision — preserve original coincident-snap behavior

User answered the proposed identical-piece coincidence safeguard: **Keep original
magnet behavior.** Do not add that rejection rule. Original selection/alignment
remains authoritative; resolve native held movement, detachment and collision
integration instead. Earlier entries calling this decision pending are historical.

### 2026-11-12 13:04 — live bounds hypothesis ruled out

Implementation remains the priority; broad RE remains parked. The preceding
question-answer turn made no implementation progress. This turn completed the
existing obstruction trace and one reused-staging bounds trace, both ending at
their 180-second watchdogs. No game remains, shared test slot released, no deployment.

Added `test_bridge.exe --asymmetric-bounds`: original H4 82282580 preserves an
interior Y=-250 and independently clamps all six faces without changing the
basis or other coordinates. Passed. Added bounded live-bounds diagnostics to
the existing held trace; candidate builds successfully.

The live variant bounds are X[-6409.255,5559.469], Y[-6949.2915,6390.13],
Z[-34.80757,1201.0226], not the saved fixture's bounds. The stalled position
is well inside these limits. Therefore the apparent match between the previous
monitor Y and fixture X minimum was coincidental, not evidence of an axis bug.
Current trace ticks931..961 retain Phased motion6 but converge near Y=-193.0324;
991..1051 return near -190.54468. Sustained movement remains failed.
No obstruction diagnostic lines were emitted; this alone does not prove that
all collision paths are clear. Next work: held/monitor target accumulation and
native controller integration, not changing bounds or inventing snap rules.

Latest run has no new visual captures. Retained images belong to the earlier
85979c32 candidate; do not attribute them to the current diagnostic-only build.

### Phased retention and Normal restoration confirmed; recovery still incomplete

Candidate85979c32dd4efe734670b959d2a54e8e509d0e1ef10b9e589eb6b1ba4c0a411b
completed the180-second native run. Body motion6 persists across later native
constructors while Phased, including ticks878..1284. Backward movement reaches
Y=-193.09619 from near-190; forward reaches-187.12529, but does not sustain
full traversal. Switching back to Normal at1314 produces motion4. Same piece
E2A30034 re-grabs1464 with distance7.869545, but overlap remains visibly present.
This proves the retained-request fix and Normal restoration, not complete
penetration recovery, native menu interaction, or mode persistence in saves.
All three new captures inspected individually and retained in reused
20261112-112536-6476: retained-phased-held.png, retained-phased-pull.png,
retained-phased-regrab.png. Superseded six physics-mode/constructor-check
captures removed after inspection of replacement evidence. Original opposed
pass, solo pass and same-facing failure images retained. No game remains;
shared slot released; no deployment. Coincident-snap safeguard decision remains
pending; partial movement/monitor-follow behavior remains open independently.

### Phased is constructed correctly, then reverts; retained request candidate

Native trace12:47:51.566 records selected body0 at82A8C480 with motion6
immediately after Phased rebuild. Subsequent held ticks report motion4.
Therefore initial construction succeeds; later native processing changes it.
Normal restoration at12:48:06.660 produces motion4 as expected. Run completed
180-second watchdog; no new images in this trace-only run; shared slot released.
Added SceneryConstructionRequest: matching explicit scope takes precedence
(including false during restoration), otherwise a valid live physicsObjects
entry with keyframedOverride retains the request for subsequent native rebuilds.
It uses the existing early motion-array hook; no invented H3 flag or changed
saved data. Built, not yet native-tested. If reversion occurs through motion
mutation instead of rebuilding, this alone will not resolve it. No deployment.

### Final-constructor hypothesis rejected in native test

Candidate510a703f6ffc94c5363d3c96ac581e8d05191399d1c03769458bef491db2512a
completed180-second watchdog. At12:43:33.930 final constructor logs motion6->6:
it already received the correct keyframed argument. Subsequent selected body
still reports motion4 and remains trapped. Thus the proposed final override
did not address this failure and has been removed. All three native captures
inspected individually; retained constructor-check-held/pull/release.png in
the reused run. They prove failure, not a fix. Shared test slot released.
Added trace-only immediate post-rebuild body index/address/motion observations
to distinguish construction output from later body changes. This revised
candidate builds, but has not run yet. Physics command connection remains.

### Historical final-constructor experiment — rejected and removed

Original isolated `test_bridge.exe --held-physics` confirms held/local Normal
and Fixed select state1/flags0x200000; Phased selects state2/flags0x600000.
Native trace at12:39 confirms state1->2, keyframed=true reaches rebuild and
both82267DD8 calls with matching datumE2A30034. Earlier request wiring is intact.
Native82267DD8 reads82268148's fixed-compound output and can replace motion
with7. Native822698A0 then converts7 to dynamic4 when native force-dynamic20
is present. Added datum-scoped final822698A0 argument override to6 alongside
the existing earlier motion-array override; ordinary objects bypass it.
Argument at caller stack+92 is restored after the call. Current candidate
build succeeds; no native verification of this new correction yet, no deployment.
Previous trace completed180-second watchdog and shared slot released. Its
output is retained in the reusable run; earlier visual captures remain from
the preceding build and must not be presented as proof of this correction.

### Physics command queue wired into owned held tick; Phased recovery fails

Candidate bdd53350ceba7bdc7e864279cbcc238204c8ccd3d718a03b33605685db4a8879
built successfully. UpdatePhysics previously ran only from legacy pose callbacks,
which the replacement held controller bypasses during ordinary movement. It now
runs before the owned held tick's instance eligibility check. Owned pose callbacks
skip queue consumption to avoid recursive requests during body rebuilding.
Native180-second same-facing run confirms Normal/Phased/Normal commands are
consumed while held, but Phased modeC0 still shows dynamic body motion4 and
does not recover penetration. For example tick1190 rawY=-189.75215 remains near
the target instead of separating; repeated motion4 persists through1250.
This verifies command delivery, NOT correct Phased physics or full menu input.
All three captures inspected individually; intersecting walls remain visible,
third capture is released rather than a successful re-grab. Retained in reused
20261112-112536-6476 as physics-mode-held.png, physics-mode-pull.png,
physics-mode-release.png. Watchdog exited, no game remains, shared slot released.
Next inspect original state2 transition and native keyframed constructor routing.
No deployment. Duplicate-position safeguard decision remains pending separately.

### Untouched H4 markers also submit coincident same-facing pose

Updated `check_coincident_snap.py` to remove its obsolete AFM2 synthetic-marker
path. It now uses the AFM3 original marker builder and held caller, comparing
current adapted records with complete untouched48-byte records read directly
from H4 ca_forge_ravine's fw_unsc_c_base_round model. Same-facing original H4
records select target456 and submit(0,0.100000024,0) against target(0,0.1,0),
matching the adapted-pack coincident result within floating-point precision.
Output and input hashes: work/h4-forge-research/isolated/coincident-snap-result.json.
The source diagnostic radius is an explicit enclosing query envelope, not a
claimed H4 runtime radius. This establishes original magnet acceptance, not
full H4 engine penetration behavior. Requested a user decision on a narrow
same-piece/same-position/same-orientation snap safeguard because such a guard
would be a deliberate behavior change. Do not invent it under the RE mandate.

### Same-facing native penetration sequence fails, 2026-11-12

Current candidate9afee87e2e7717d243800cae6fc14c6bfe9c3f73c530617314e75d1327190688;
reused20261112-112536-6476 staging, completed180-second watchdog at12:25.
Added `build_snap_fixture.py --bank base-round --existing-pair --same-facing`.
This intentionally starts overlapped: it tests recovery from penetration, not
whether ordinary placement first creates overlap. Original selection, grab,
held update and native controller run; moving input is recognized at850.
At910 the unsnapped submissionY=-191.06773 commands velocityY=-5.225754, while
bodyY=-190.02258 remains near targetY=-190.0297. It remains trapped during
backward/forward movement; stopping1346 again submits the target origin.
Re-grab1466 selects the OTHER pieceE2A10032, not the original heldE2A30034.
Therefore this is a failed recovery sequence, not another re-grab pass.
All three captures inspected individually: intersecting duplicated doorway/wall
edges remain visible. Retained same-facing-held.png, same-facing-pull.png,
same-facing-regrab.png in the reusable run. No process remains; shared slot
released; no deployment. Next implementation boundary: collision/penetration
recovery for the held scenery body. The successful opposed-pair test does not
cover this failure. Movement gating itself is demonstrably receiving input.

### Same-facing overlap narrowed to held submission, 2026-11-12

The current AFM3 Base Round records reproduce coincident origins through both
the original selector/alignment and the original held-magnet caller8244EED8.
Run `work/h4-forge-research/isolated/test_bridge.exe --coincident-pack work/rexglue-sdk/out/win-amd64/advanced-forge/isolated/markers.bin`.
With held origin(0,0,0), target(0,0.1,0), stationary movement and sensitivity2,
both same-facing and opposed cases select target456 and submit(0,0.1,0).
The staged editor uses the original constructor and current full48-byte marker
records. This excludes missing AFM2 metadata and a selector-only bypass as
explanations; it does not exercise native world collision or the full held
lifecycle. No custom overlap filter or production change was introduced.
Next resolve how the integrated held update/physics path handles this submission
before attributing overlapping objects to original H4 gameplay.

### Base Round paired snap / detach / re-grab sequence passes

Current candidate9afee87e2e7717d243800cae6fc14c6bfe9c3f73c530617314e75d1327190688, reusable run launch-clock1794503521.3848536, completed180-second watchdog. Corrected pair originZ3.489226, no initial lift or forced runtime pose. HeldE2A30034 snaps to opposedE2A10032 at tick776, closingY-190.1297 to-190.0297. Ordinary backward input moves it away; target clears at918, with continued displacement beyondY-211. Return reacquires target at1283; stopping at1345 submits exact original joint(-51.569447,-190.0297,3.489226). Drop occurs1375; same datum re-grabs1466 at distance7.869545 without camera intersection, then sideways movement and second drop complete. Three native captures131000/139000/154000 inspected individually and retained as pair-snap.png, pair-detached.png, pair-regrab.png in the reused directory. Solo captures renamed solo-movement_136000ms/140000ms/150000ms.png. No deployment. Identical-orientation overlap, creation clearance, other large pieces/modes and lifecycle gaps remain open. This pass supersedes the buried-fixture detachment failure as evidence about the ordinary controller, not as proof that all contact/penetration cases work.

### Base Round moves and re-grabs clear of terrain

Current reusable run launch-clock1794503220.563443 used the elevated solo fixture and3900ms approach. Completed180-second watchdog. Same datumE2A10032 grabbed, lifted, moved backward/forward, dropped, re-grabbed, moved sideways and dropped. Raw Z13.489226 at tick851 ->16.825354 at881 ->20.822554 at911 ->24.822542 at941. Backward rawY-192.97244 at971 ->-203.30258 at1061; return rawY-179.7692 at1376. Re-grab at1467 retains raw position(-52.648014,-179.76884,25.315208) and distance7.869545; subsequent sideways motion changesX to-54.328476 at1571. No magnet target in this solo control; no snap/detach acceptance implied. All three captures136000/140000/150000 inspected individually: piece visible outside camera, held in first two, released in third. Re-grab itself is supported by native trace, not a capture at that instant.

This contradicts a general inability of the H4/native controller to move Base Round. The earlier ground fixture is contact-confounded: verified target bounds have minZ=-1, while its origin was onlyZ1.489226 near the player ground plane. Corrected existing-pair fixture generation to raise origin2 units (one for the lower model extent plus one clearance); installed assets/runtime behavior are unchanged. Next exercise paired snapping/detachment with corrected clearance, then address real grounded contact and creation behavior. Do not tune magnet thresholds or replace physics based on the old penetrated fixture. Current elevated evidence remains retained; regenerate the corrected pair for the next run.

The3800ms elevated approach (launch-clock1794502984.5132523) ended at ray originZ12.366113, below the confirmed hit atZ12.543887. No grab occurred. All three native captures inspected individually; they show the unladen monitor and piece below the view. This is a selection-route failure, not a physics result. A100ms ascent increase corresponds to0.25 units at the measured2.5 speed. Old test-content cleanup attempted after explicit path/reparse validation: automatic approval review again rejected directory removal as blocked by policy; all52 targeted superseded content directories remain. Three superseded failed captures were successfully removed before this run; current captures retained.

### Elevated selection measured, 2026-11-12

Position-trace run reused current staging with launch-clock1794502734.9963698 and completed180 seconds. Actual Base Round remains at Z13.489226 before grab (not merely its saved variant). Monitor selection originZ12.543887 at tick598 hits datumE2A10032; originZ15.366067 at tick658 misses. The5000ms ascent overshot the piece. Free ascent reaches2.5 units/second; a3800ms approach targets the measured hit-height region. No controller/collision conclusion from this run, which never grabbed. Current diagnostics log origin/direction/target and up to four live/saved scenery poses every60ticks. Diagnostic exceptions are isolated from the gameplay path in the pending guard build. Log truncation on reuse verified: first record belongs to current launch.

### Terrain-clearance control inconclusive; stale-log reuse corrected

Run `.local/loading-traces/20261112-112536-6476`, launch-clock1794502354.3059905, used saved solo scenery elevated12 units and ordinary RB flight for5000ms before grab. Completed180-second watchdog; no held update occurred in this run. All three captures136000/140000/150000 inspected individually: monitor view above the valley, no selected piece. Therefore this run does NOT distinguish terrain collision from controller failure. Saved variant still records the piece at Z13.489226; that saved pose does not prove the live rigid body remained there. No deployment; process exited and shared slot released.

Added bounded diagnostic `--elevate` (scenery only; grounded player spawns) and `--forge-pair-approach-up-ms` (ordinary process-local flight). Do not repeat this failed approach unchanged. Current run revealed that the runtime logger appends when staging is reused; old records remained before the current launch timestamp. Corrected reuse startup to truncate trace-runtime.log before launch, preventing stale records from contaminating later checks. Current run must be filtered by its launch timestamp; previous summaries' claims that raw logs were fully overwritten were inaccurate. TODO now distinguishes built implementation from unverified behavior and retains open attachment/restoration/rendering/persistence requirements.

Original H4 Ravine Base Round phmo comparison: shape15/MOPP and mass79999.984375, versus native converted shape15 and mass80000. Those facts alone do not support changing the native shape or mass. Native820ACC10 directly copies body384/388/392 without timestep scaling, so incoming velocity reduction is not a per-tick conversion in that getter.

### Native writer boundary narrowed, 2026-11-12

Built bounded diagnostics for incoming velocity and calls to native pose setter8232E8B8 / velocity setter820F29C8 while an original editor owns the object. Reused the solo Base Round run at `.local/loading-traces/20261112-112536-6476` (launch-clock wall_time1794502042.6288269); completed180-second watchdog, process exited, shared slot released. No native-writer records occurred during the hold. Tick1001 incoming velocity(-0.007907,0.017727,-0.002253), controller output(0.248375,-2.487640,0.002103); tick1196 incoming(-0.011211,-0.100409,0.010013), output(-0.249405,2.487564,0.0000596). Motion is substantially reduced between updates. This excludes these two competing native setter paths, not every possible body writer or collision cause. The existing detach-only820F29C8 interception does not run continuously. Next distinguish native body collision/solver behavior from other synchronization paths; do not alter magnet thresholds. No gameplay fix or visual acceptance claimed, no deployment. Manifest updated to current diagnostic build. Prior detailed logs in reused directory are superseded; summaries remain here.

### Single-piece control rules out magnet trapping

Reused current run `.local/loading-traces/20261112-112536-6476` with `snap-fixture-base-round-solo.bin`, generated by --existing-pair --single-near. Only the far piece is removed; near pose/spawn/replay/candidate unchanged. Completed180-second watchdog. Held E2A10032 has targetFFFFFFFF and candidates0 throughout observed movement, yet still stalls: tick1254 raw position(-51.4816,-190.5861,2.0375295), commanded velocity(-0.249462,2.4874878,-0.00406); tick1314 raw position(-51.48095,-190.58247,2.0259514) with similar velocity. This is a general Base Round held-physics failure, not specifically magnet pair retention. Do not adjust magnet release thresholds to compensate. No visual acceptance from log-only control; no deployment. Current reused log supersedes prior run details at that path; compact prior findings retained here.

Source boundary follow-up: stock H3 Forge held block invokes822836D8/822837C8, whereas H4 integration submits its original raw-body controller. Native8232E8B8/8232E698 are pose/visibility/reconnection paths, not a drop-in velocity controller; do not call them speculatively as a notification.

### Runtime speed limits ruled out; reusable staging

Reused `.local/loading-traces/20261112-112536-6476` for the motion-limit run (current launch-clock identifies the rerun; earlier detailed logs at that path were superseded, findings retained above/below). Run completed180-second watchdog. Native linear/angular limits both200 throughout held movement, far above the requested approximately2.5 velocity. Body remains motion4 and raw translation stalls; speed limits do not explain it. No gameplay behavior changed or accepted. No deployment.

Added --reuse-run to trace_loading.py: confines reuse to an existing direct loading-traces child with launch manifest, rejects an active halo3mp process and incompatible seeding, requires existing immutable content to be the same linked source, and reuses saved-layout directories. Syntax checked and full diagnostic run succeeded without another content installation. Continue reusing this run for current diagnostics; old cleanup restrictions remain unresolved.

### Authored-body comparison, 2026-11-12

Read-only inspection of installed Forge Gulch cache: Base Round bloc2952 resolves to one176-byte rigid body, authored motion5, flags0, linear damping0, angular damping0.05, MOPP shape15/index0, mass80000, center(-0.00001051,-2.66849065,0.40517378). Passing Bank1x1 bloc2937 has the same authored motion/flags/damping but polyhedron shape4/index0 and mass339.9282. Damping therefore does not explain the difference; complex-shape/mass behavior remains a candidate, not a proven cause. Native controller activation/setter routing matches82629000. Legacy Evaluate explicitly exits for OwnedOriginalSceneryEditor before its older pose-snap application; no evidence of that path reapplying the snap. No asset edits, run, or deployment in this inspection. Runtime speed-limit trace remains the next discriminating check.

### Raw physics transform confirms stall, 2026-11-12

Log-only run `.local/loading-traces/20261112-112536-6476` completed180-second watchdog. During upward input, raw body translationZ2.0428247 at881 reaches only2.0862863 at911 while raw velocityZ remains approximately2.5. Native transform itself stalls; stale editor reporting is not the sole cause. Original activation and native virtual setters match source. Next inspect imported dynamic-body motion limits/rebuild settings; native8265F4F0 writes maximum velocity inputs to motion180/184 (body340/344). Added those two source-backed fields to bounded tracing, not built yet. No visual acceptance from this log-only run; no deployment or magnet threshold changes.

### Lift comparison, 2026-11-12

Run `.local/loading-traces/20261112-112046-5580` used ordinary RB ascent for3 seconds before backward pull. All3 captures136000/140000/150000 inspected individually: piece remains near joined base, release visible, no camera intersection, no successful sustained lift/detach. At tick881 upward input(0,0,1) gives velocityZ2.4999845 and centerZ2.4451373; at911 velocityZ2.4999607 but centerZ2.4697351. Runtime body0 motion4, native frozen bit6 clear (flags00900080), force-dynamic bit20 set. Original H4 geometry/contact constraints remain false. Native activation and velocity dispatch agree with82629000/82651968 source. Added raw body translation224 and velocity384 to the same bounded trace to distinguish physics progress from stale object reporting; source change not built yet. Do not alter original magnet thresholds. No deployment.

### Held physics integration isolated, 2026-11-12

Log-only run `.local/loading-traces/20261112-111438-7640` completed its180-second watchdog. At tick939 the held center is (-51.509693,-193.14818,2.45073), velocity (0.24963379,-2.4874878,-0.00469327); at tick999 center remains (-51.509773,-193.14925,2.4512815) despite velocity (0.24944305,-2.4874878,-0.00022888). Geometry-block and H4 contact-response results are both false throughout those samples. Original held controller is requesting motion; native physical progress stalls. Do not infer that all native Havok collisions are absent from the H4 contact-response result. No visual acceptance claimed from this log-only run. Next inspect native body motion class/frozen flags and collision integration; bounded trace added for those fields, not built yet. No threshold changes or deployment.

### Held feedback instrumentation built

Source inspection confirms original8244A8D8 limits requested movement relative to the actual held reference point and applies geometry/contact constraints before magnet submission. Added bounded actual held-center/velocity and captured geometry/contact results to the existing diagnostic event. The wrappers observe the original callback invocation, never invoke contact response twice. Existing monitor-follow traces alone cannot distinguish a stalled held body from constraint suppression. Build succeeded; candidate manifest refreshed. Not runtime-tested or deployed. Next run must distinguish these cases before any movement or snapping change. Previous run cleanup remains blocked by automatic approval review.

### Monitor-follow boundary narrowed, 2026-11-12

Run `.local/loading-traces/20261112-110828-19444` completed its 180-second watchdog. All three native screenshots inspected individually: joined Base Round exterior remains outside the camera, release/regrab visible, no successful pull-away. At tick1004 monitor actual (-50.730057,-201.01009,2.7213068) is close to requested (-50.73199,-200.9985,2.72092); contact correction is inactive. Similar agreement persists during sustained input. The follow request itself stalls; this run does not show a large unfulfilled monitor controller displacement. Next inspect held-body actual motion versus its requested target and correction feedback. Added actual held-center/velocity to the same bounded diagnostic event; not built or run yet. No snapping threshold changes, no deployment.

### Base, Round sustained pull: unresolved

Run `.local/loading-traces/20261112-110017-26928` used seven seconds of backward input. The persistent unsnapped position survives stopping input (tick1061 approximately -51.435,-191.246,2.024), while the submitted object returns to its snap. Intended movement and actual monitor movement saturate during continued input. Overwriting the persistent target with the snap is therefore not the cause. Flat-face snap and same-object regrab observed; pull-away FAILED. Three native captures individually inspected in the preceding work session. No deployment.

Next candidate adds bounded monitor-follow target/contact logging alongside actual monitor position to distinguish a blocked follow request from controller motion failure. Build succeeded; candidate not run. Original magnet thresholds and selection logic unchanged.

### Base, Round two-second pull, 2026-11-12

Run .local/loading-traces/20261112-105537-11164 closes the flat-face gap, but the two-second backward pull never clears target E2A10032 and stopping restores the snapped pose. Movement at tick876 reaches approximately Y=-190.6843/Z2.0566, then returns to Y=-190.0297/Z1.4892 at906. Same near-half datum E2A30034 is successfully re-grabbed at1072 after the sideways unladen approach; no camera intersection in individually inspected captures133000/136000/141000. Detachment is NOT accepted. Added diagnostic logging of persistent unsnapped target and actual monitor point alongside submitted target, and lengthened the input hold to measure accumulation/saturation. No custom detachment rule or threshold change. No deployment.


### Base, Round flat-face snap observed, 2026-11-12

Run .local/loading-traces/20261112-105129-9644 successfully grabs near half E2A30034 and selects opposed E2A10032. At tick775 the submitted origin changes from Y=-190.1297 to Y=-190.0297, closing the authored 0.1 flat-face gap. All three captures inspected individually; the exterior remains outside camera and the halves form the joined base. Half-second backward input at849 produces only small displacement, then snaps back at864; this is NOT a detachment pass. After drop, native follow has centered the doorway and the attempted regrab misses scenery (no second pickup event). Extended the approach route to two-second pull/return and an unladen sideways move before regrab. These are ordinary process-local controls, no forced held pose or algorithm changes. Next run pending; no deployment.


### Existing-pair route preparation, 2026-11-12

Added a stock saved-layout fixture containing opposed Base Round halves with a 0.1-unit flat-face gap, and a process-local grab/pull/release/regrab/return input route. Run20261112-104348-19044 entered Custom Games because the new option was absent from both Forge lobby selectors; corrected both predicates. Run20261112-104737-25776 entered Forge but aimed through the central doorway and selected a spawn marker rather than scenery. All six screenshots inspected individually; neither run supports a magnet pass. Moved the saved initial/respawn viewpoint 2.5 units sideways to aim at solid wall. Held-object state and geometry remain unforced; corrected viewpoint has not run yet. No deployment.


### Elevated Base, Round comparison, 2026-11-12

Run .local/loading-traces/20261112-103752-26900 used ordinary monitor ascent before creation, then movement/drop/re-grab/movement/drop. Candidate c01aa81a4afe930d82e69098e6c3b9d8e6909ec52948912b30f03e3b54a52723. Requested/adjusted Z17.03 remains unchanged by collision placement; instead it shifts X by one radius6.295636. All three captures (137000,140000,146000) individually inspected: exterior geometry stays outside the camera, but the large piece occupies much of the view. Same held datum E2A80038 is re-grabbed; distance remains7.869545 and pose is retained. No selected magnet target, so this does not verify Base Round mating. Ground-run upward displacement is an environment-dependent native placement-search result, not a new displacement on re-grab. The source wrapper inspection confirms both H4 and H3 use a -1 collision-filter identity at the nested call; changing that to ignore the monitor without further evidence would be guessed. Retain the native query for now. Next practical coverage remains an approach to an opposed Base Round flat face from clear space. No deployment. Exact-path removal of an older completed run's temporary installation was again rejected by automatic approval review with no specific reason; cleanup remains pending.


### Creation-query result, 2026-11-12

Log-only run .local/loading-traces/20261112-103220-15116: requested Z2.0212421, H4 prefix Z2.020146, native collision-placement result Z14.611418. The rise is exactly 2 * radius6.295636. It happens inside native822836D8/8226E590, before object creation/grab; neither snapping nor grab projection introduces it. Original H4 Base Round source chain verified read-only in ca_forge_ravine.map: mode12753 -> hlmt12752 -> bloc12751. Source radius6.8537383, multiplayer block count1, flags at record+28 are0x20000 (Phased bit1 clear). Therefore bypassing collision on an assumed authored Phased flag would be incorrect. Next discriminating check is creation in clear airborne space using the existing ascent route, rather than another guessed magnet fixture offset. Current ground-level setup remains a failed visual case. Nothing deployed.


### Base, Round placement boundary, 2026-11-12

Run .local/loading-traces/20261112-102738-27040 confirms the selected body is already at (-49.5292,-195.87717,15.016592) BEFORE grab initialization, while monitor is (-49.56363,-195.68459,2.01905) looking horizontally along +Y. Radius6.295636, initialized distance7.869545. Thus the excessive height predates magnet selection and re-grab. Follow then turns the monitor upward; regrab does not cause the original height change. All three native captures individually inspected, reproducing the same obstructed view. Added creation-query input/adjusted/output logging to isolate the existing native collision placement boundary. No guessed position offset applied. No deployment.


### Base, Round regression, 2026-11-12

Run .local/loading-traces/20261112-102249-26112, same candidate as the triangular-bank pass. All three captures inspected individually: the large piece fills the camera from creation onward. No target was selected (zero candidates). Held E2A80038 is at approximately (-49.53,-193.21,14.61), far above the saved target. Release/regrab retained its pose but this is NOT a visual or magnet acceptance. Creation/initial grab placement needs diagnosis before changing snapping. Added bounded grab-event logging of held point, monitor point/forward, runtime radius and initialized distance to distinguish collision placement from grab projection. No deployment.


### Native two-piece result, 2026-11-12

Run .local/loading-traces/20261112-101817-25776 used candidate SHA256 10b6fe0679fff6e9800b2ef2ea0a354ca051e759722359d6ebc8b34f9b20f8ac. Target E2A10032 selected at tick773, movement submitted unsnapped pose at848, target cleared at868. Same held E2A80038 re-grabbed at999 without distance jump. Return reacquired target at1063 and aligned at1103. All three native captures inspected individually: first two separated pieces, final opposed banks meeting at lower tips without coincident stacking. This supports this sequence only; Base, Round and arbitrary orientations remain open. No lifecycle failure. No deployment. Automatic approval review rejected the combined evidence-update/temporary-installation-cleanup command; cleanup remains pending.


## Current status — 2026-11-12

Further RE is parked by user instruction. The current scenery implementation now compiles and links in the existing SDK build. Fixed the GPU-plugin interface linkage by dispatching marker queue/cancellation operations through the plugin virtual interface. Generated and staged AFM3 metadata (129 bindings, 61,032 bytes) and H4MP3 material into the candidate's adjacent private-data directory. Radio Antennae, Weapon Holder, Glass Sail and Sniper Nest remain without magnets.

Candidate: `work/rexglue-sdk/out/win-amd64/halo3mp.exe`. Build log: `work/build-temp/forge-implementation-build.log`; exact file identities: `work/build-temp/forge-candidate.json`. Nothing deployed. First native run exposed a stale monitor index (64 versus current67) in target submission. Corrected it, rebuilt, and repeated: pickup/move/drop/re-grab/move/drop completed without lifecycle failure; all three captures inspected and no camera jump observed in this large-piece case. The subsequent triangular-bank test demonstrates snap/pull-away/re-grab/re-snap; Base, Round and broader manipulation acceptance remain open.

### Snapping integration correction

The three two-piece runs ending in `20261112-101001-7648` never selected a target; they do not establish snap or detachment success. Source inspection found the missing preference mapping: H4 initializer `82449DD8` clears editor byte82; `8244EED8` bypasses selection when it is zero. Spartan now maps its enabled control and sensitivity into private H4 editor fields before the coupled held update. The triangular-bank native sequence above verifies this correction for that case. Raw scene diagnostics overwrite one file, allowing actual marker positions to be inspected without guessing fixture offsets.

## Historical scope completion (superseded)

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

## Earlier completed fixes

Base, Round's reported flat-face joint is fixed. Its original H4 anchors used
a different origin, orientation and radius; the data adapter now maps them onto
the existing Reach geometry. Native run `20261028-152444-6080` forms the intended
disc and retains it through release and return to player mode. Both captures
were inspected. The two saved origins differ by 0.000244260 units, with equal
heights and exactly opposed forward axes in ordinary H3 version-12 records.

This also exposed a default-physics bug: the native menu displayed authored
Fixed mode, but the runtime only applied it after an explicit selection. Grab
now immediately applies the displayed authored mode through the same existing
runtime setter. The run records default Fixed flags `001000C0`, followed by
restoration of the original motion/connection bits on returning to player mode.
No release-pose override is present in the final implementation. The `.map`
geometry, collision, authored physics and save format were not changed.

The Base, Round and default-physics fixes are in the repository build. The
outside-repository installation has not been updated. Cross-map automatic
anchor discovery is not implemented: bindings remain an explicit external
table keyed by map ID and object tag datum, requiring regeneration for new or
rebuilt maps. This is a documented design limitation, not a new coverage task.
The user accepted the current anchors and asked to check off the completed
physics/restoration and ordinary save/reload work. On 2026-10-28 the user also
clarified: "You are not responsible for broader validation." The subsequent
reopening specifically authorizes mathematical verification of all Gulch/Cove
scenery transforms. Hardware, system-link and unrelated validation remain out
of scope. Existing evidence and its limits remain documented below.

The authorized goal is Halo 4 parity for magnets and visible anchors,
standard/fixed/phased physics controls, and precise movement, using actual H4
program logic through ReXGlue. Scenery is required; other objects may be covered
where appropriate. Every saved result must be an ordinary H3 variant accepted
by consoles without this editor update. Do not add format extensions or make
saved gameplay depend on host-only physics. The latest user direction makes
Advanced Forge automatic in Forge, with native object-properties controls
(X while holding an object). No F7 console or enable step. Achievements remain
disabled. F7 is now reserved for the separate, pending developer-only framerate
unlock toggle recorded in TODO.MD; it must default off.

The user explicitly confirmed on 2026-10-28 that physics modes are editing-only.
Normal/Fixed/Phased must not persist in the saved variant; reload uses ordinary
H3 physics. Runtime transitions and restoration now pass a limited native
Bank fixture; Normal release also passes saved-pose tracking. The native menu
row is implemented and visually inspected; all three choices, release and
return-to-player restoration pass. Native Position X also reaches the saved
pose. A native Yaw selection also retains the requested one-degree rotation in
the saved basis. Position/rotation and Free/Precise rows use the original H4
range/step definitions. Free movement resumes native dragging after a precise
position edit. Reopening properties and canceling a second position edit retain
the committed pose in the Bank fixture. Broader rotation and other scenery
coverage are unverified and outside the agreed task scope.
The Arch Brace native-menu run `20261028-143021-39388` also passes all three
physics choices, authored-state restoration and a Position X edit retained at
(-44.700012, -197.840622, 2.582953). Its six allocated object property records
and quota tag identities match the earlier Arch Brace reference. Both captures
were inspected: native Physics/position rows and subsequent player gameplay.
This adds scenery coverage, not a broad overlap/collision pass.

Controlled Bank 2x1 overlap tests now cover all three modes. Phased and Fixed
retain the exact intersecting pose through release and authored-state restoration.
Normal responds to collision while held, then separates and falls after release.
Live object snapshots and the map's direct convex collision shape establish
these results; all six serialized property records remain unchanged. This does
not establish unrestricted drag collision or other collision-shape layouts.
The Phased overlap result reloads in ordinary Slayer in
`20261028-145209-12460`: all six saved records match, and six live snapshots
retain both intersecting pieces at their saved poses with connected, ordinary
physics. The native Slayer capture was inspected. This directly supports shape
retention for this authored-fixed scenery case, without certifying consoles.
The edited Arch Brace layout also reloads in ordinary Slayer in run
`20261028-143419-34884`, with all six allocated poses/properties and quota tag
identities unchanged. Its capture was inspected and shows Slayer with the
placed geometry. No Advanced Forge launch options were supplied.

The edited fixture reloads in ordinary Slayer with no Advanced Forge options
or H4 inputs, retaining all six native poses/properties byte-for-byte. This
does not certify console hardware testing.

Automatic activation and adjacent-input discovery pass the Bank fixture without
enable or data-path overrides, despite the build's legacy bootstrap setting
being false. The optional local build stages its private H4 inputs beside the
executable and prefers them over the old persisted path. The native run loaded
all 79 bindings there. Explicit diagnostic paths remain supported, and older
local installs can still use their configured path if adjacent inputs are absent.
These changes are built and tested inside the repository; no outside-repository
installation was updated.

Current work and compatibility findings: [PARITY-2026-10-28.md](PARITY-2026-10-28.md).

The repository test build now passes scenery-anchor depth occlusion on the
native Bank fixture. Rear anchors are hidden and exposed ring portions remain.
The Hornet issue is therefore resolved under the user's explicit acceptance
criterion. Anchor appearance is also accepted by the latest user decision.
This renderer patch has not been copied to the outside-repository installed binaries.

All five original H4 marker base textures and six material shader programs are
extracted and verified. Both original pixel programs now have generated HLSL
translations checked against ReXGlue's execution of the retail microcode:
2,816 cases pass, including faded-particle endpoints. The maximum output error
is 1.49e-8. This verifies shader instructions with supplied inputs, not live
particle animation, sizing or scene compositing. Those differences remain
documented limitations of the accepted visuals, not further acceptance work. The repository game build now draws the original pixel
materials and textures, with provisional particle inputs and sizing. The shared game build
also now uses **Spartan** for initial and FPS-updated window titles, following
the user's request relayed from "Check Spartan name availability." Existing
profile/config identity and the repository URL/directory are preserved.

Native run `20261028-134358-30048` loads the adjacent material pack and draws
six anchor candidates with scene depth. Both native held-object captures were
inspected: the exposed left-edge light and small lower-edge fragments remain,
with hidden rear anchors occluded. The host capture is from later player mode,
not a held-object material acceptance image. Known differences from full H4
appearance remain: the radius is fixed in screen pixels, lifecycle inputs are provisional,
and compositing occurs after guest gamma without the original HDR/bloom path.

The extraction now contains 70 unchanged H4 function bodies, including the
original scalar curve evaluator and color conversion. The isolated marker check
executes all 58 authored functions at 37,410 input/range combinations; 34,185
constant/identity samples also pass independent numerical checks. Complex
curve outputs are finite and come from original execution, but have no separate
numerical oracle. These curves are not yet wired into live particle lifecycle.
Existing bridge selection, visibility, physics and coordinate checks still pass.

The near/far fade blocks are now integrated using the original vertex ALUs,
verified against ReXGlue with zero difference across 2,074 cases. The packaged
compute shader also passes fade/occlusion/alpha checks in single-sample and
MSAA modes. This caught and fixed the ray layer's missing alpha composition.
Default-scale camera-axis depth is wired live. A native camera sweep across
fade boundaries and zoom/override behavior remain unverified; the user accepted
the current visuals without requiring this additional anchor work.

Run `20261028-141136-24732` passes the native held-anchor visual regression;
all three captures were inspected. All six saved poses/properties match the
preceding run. The private pack now contains precompiled programs, removing
source compilation from the render thread. Its 73.591 ms synchronous setup
was subsequently moved to a worker. Run `20261028-141944-5944` measured
0.041 ms render-thread dispatch, 84.654 ms worker setup and 0.005 ms adoption.
All three native captures were inspected; the six allocated native object
records match the preceding run byte-for-byte. Initial anchors wait for worker
readiness while rendering continues. This resolves the synchronous pipeline
setup cost, not every possible Forge hitch. The runtime build and assets remain
inside the repository.

## Earlier installed implementation (2026-10-24)

The earlier programmatic Advanced Forge implementation was installed.
This status covers the user-requested program logic first, using actual Halo 4
ReXGlue output. It does not certify every H4-to-Reach object correspondence.

Current implementation is installed in `C:/X360/ISOs/H3M/OpenH3M.exe`.
Start normally, enter offline Forge, press F7, and enable **Magnets (Halo 4)**.
Magnets default off. Automated-input and capture settings are not installed.

## Verified program behavior

| Requirement | Evidence |
| --- | --- |
| Actual Halo 4 logic, not replacement snapping | ReXGlue output and `verify_original.py`: 34 integrated bodies match exactly. Five adapters supply scene data only. |
| Original selection and alignment execute | `isolated/alignment-test.log`, `bridge-test.log`; bridge executable also passes near, far, alternate target and missing-marker checks. |
| Integration into live H3 Forge | Native Bank 1x1, Bank 2x1, Dish and Arch Brace runs reach gameplay, snap and release. Saved positions match the final H4 result. See README for exact run directories and visual limits. |
| Controls | Shared process-local ImGui test passes F7, enable/disable and distance endpoints. Native `isolated/panel-check/panel.bmp` was inspected for actual panel appearance. |
| Standard H3 saved layouts | Native Bank placement exported and reloaded in ordinary Slayer without Advanced Forge options or private H4 inputs. |
| Normal installed startup | Native `isolated/direct-launch/startup.png` shows the expected main menu; deployment inventory records exact binaries. |
| Separate PC metadata | H4 image, settings and 13,712-byte bindings remain under `work/h4-forge-research`; no metadata is added to maps or saved variants. |
| Preserve network simulation | Source guard requires local simulation before editing; disabled/nonlocal calls proceed through original H3 routines. This is source evidence, not a physical-console or system-link test. |

Paths beginning `isolated/` above are relative to `work/h4-forge-research/`.

## Asset correspondence follow-up

The catalog currently contains 79 map-specific bindings across Gulch/Cove.
That count is not a claim that every reskinned object has a verified joint.
Bank 1x1, adapted Bank 2x1, Dish and Arch Brace have native placement evidence.
Dish Door, Crenel Notch and Bunker Covered have reviewed coordinate adaptations;
their in-game fit remains unverified. Other candidate registrations
remain unverified and are not applied automatically. Collision fit scores alone
cannot establish intended construction frames or distinguish symmetrical shapes.

The user explicitly prioritized programmatic behavior over object matching
(AGENTS.md, Advanced Forge instruction of 2026-10-23). Earlier chronological
notes treated exhaustive binding review as a completion gate; that expanded
the implementation goal beyond that priority. These open asset items remain
visible here and are not represented as passing tests or silently removed.

## Completion audit

On 2026-10-24, installed executable/library hashes were checked against the
tested deployment inventory. Bootstrap configuration leaves magnets off and
contains no input replay, forced drag or capture settings. The private-data
path resolves inside this repository. Original-code integrity passes for all
34 extracted bodies. The native saved layout contains only standard `_blf`,
`chdr`, version-12 `mapv`, and `_eof` chunks; ordinary native reload was already
visually verified. Source review confirms local-simulation gating before H4
evaluation and before fixed-object release cleanup. No console or system-link
hardware validation is claimed. The table above identifies behavioral and
visual evidence, rather than treating compilation or FPS as proof.

## Repeatability

Use the existing shared build and `run_native_check.ps1`; do not duplicate the
game installation. `README.md` records extraction, integration, native fixtures,
saved-layout export/reload, deployment and capture procedures. All captures,
temporary files and private game inputs remain inside the repository. No desktop
input is used. The native tests have a 180-second watchdog.

## Forge review fixes — 2026-11-11

User review failed: magnets permit overlapping snaps, pull-away fails, and large-item re-grab returns the piece onto the camera. Implementation is incomplete; earlier targeted tests were insufficient. The candidate and matching libraries were deployed on 2026-11-11 at the user's request; interactive user review is pending. See [current proof record](FORGE-REVIEW-PROOFS.md) for candidate hash, exact runs, inspected screenshots and limitations.

Live numeric rotation, accept/cancel, large-item clearance on both maps, native push/pull above ten units, and unchanged small-item spawn were checked. Final Bank 1x1 native basis confirms pitch 0 -> 1 -> 2 -> 0, matching the inspected screenshots.

The goal is not complete: retention cleanup was rejected twice by automatic approval review (`blocked by policy`), including a narrower file-identity-verified hardlink-only removal. Temporary staging and diagnostic evidence remain. No cleanup bypass was performed. Deployment was subsequently authorized and completed.
