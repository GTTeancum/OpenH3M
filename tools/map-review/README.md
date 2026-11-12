# Final map review corrections — 2026-11-05

Goal active: 3longation conveyor correction remains open. Chiron, Powerhouse, Resuscitation, Rodentia and Sky Bridge corrections are installed with targeted native evidence below. Rodentia08 brightness tuning is superseded by exact source exposure restoration. Deployment is not an exhaustive compatibility certification. Sanctuary, metadata and previews are preserved.
All generated candidates and audits: `work/map-review-20261105/`.

| Map | Current evidence | Required next work |
|---|---|---|
| 3longation | Idle-player uneven carrying reproduced on both belts in native runs; camera segments include near-zero motion between moving intervals. Physics scalar audit matches source except required serialization changes. | Diagnose contact/animated-support versus scripted recycling; apply a correction and compare the same idle-player tests. Repeated teleporting between moving belts also crashed the harness run. |
| Chiron TL-34 | `chiron-06.map`: native alpha-blended diffuse shader replaces opaque fallback; source base/detail textures retained. No exact stock permutation includes its weak dynamic reflection, so the candidate explicitly omits that reflection. Native targeted capture shows rungs with the wall visible between them. | Corrected map installed and hash-verified. Requested ladder transparency is visually verified; climbing/teleporter traversal was not rerun. The attempted opposite-side position was outside walkable space and is not a passing check. |
| Powerhouse | Topology-preserving index-order optimization deployed; three-view native GPU means improved 2.5%, 7.0%, 6.3%. Five captures inspected. | Approval pending uncapped FPS before/after at the same three native views (2026-11-11 user requirement). Existing capped GPU times are insufficient. No timing changes; use --fpsunlock. No geometry reduction used; no all-map or console performance claim. |
| Resuscitation | `resuscitation-07.map`: exact stock diffuse shader for `coag_panel_i`, removing unrelated fallback normal/specular behavior. Both bases inspected from native exterior positions. | Close-up views of both bases completed; all four captures individually inspected. No complete traversal or network claim. |
| Rodentia | Glass transparency verified. User requires canonical source lighting; exposure experiments retired. Exact source camera values restored and installed, preserving glass correction. | Original-exposure native review completed at three valid points; all five captures inspected. Glass remains transparent. Do not tune exposure. |
| Sky Bridge | `sky-bridge-no-rain-flash.map`: eight rain-card parts (4350 indices) suppressed; two electric light-creation events disabled. Byte-diff restricted to those fields and checksums. | Doorway/outdoor native views inspected. Specific light events and eight rain-card draws structurally removed; arc particles retained. No exhaustive traversal claim. |

Sky Bridge is based on the exact installed candidate36 hash. Source and target
BSP material-slot counts both equal 345; rain source tags 12310/12318 map to
native slots 19/20/21 and materials 9415/9418. The prior causal electric-light
control is now authorized by the user's explicit request to remove the flashes.
`remove_sky_weather_cards.py` reproduces the candidate and refuses a changed basis.

`candidate-build-check.json` confirms each targeted material appears in its
actual serialized build report. This is not visual or gameplay acceptance.
`sanctuary-preservation.json` records the installed Sanctuary hash matching the
user-accepted candidate09. Preserve it during packaging and installation.
Forge rotation preview and large-item spawn distance remain separate in TODO.MD.

Sources: Chiron TL-34 from Halo Generational Combat, workshop2962955878
(https://steamcommunity.com/sharedfiles/filedetails/?id=2962955878);
Rodentia from workshop3500400217
(https://steamcommunity.com/sharedfiles/filedetails/?id=3500400217);
Resuscitation from workshop2898876653
(https://steamcommunity.com/sharedfiles/filedetails/?id=2898876653).
MAP-CREDITS.md credits Drksteel for the HGC package, Blackandfan for Rodentia's
H3 port (original custom remake author unverified), and Aerial Dave for
Resuscitation. Original maps/games: Chiron TL-34, Halo CE; Rodentia, a Halo 2
custom Rat Race remake with Halo CE lineage; Resuscitation, Halo 2 Coagulation.
Sky Bridge originates in Halo Online, via GeneralHeed / Priception's Halo Online
Map Pack for Halo3 (https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190).
This project's work is the Xbox360/OpenH3M adaptation and corrections.

## Native validation evidence

- `chiron-native-01`: failed setup; both captures were blank. Missing waves,
  fonts and movies were subsequently included in private staging. Not a pass.
- `chiron-native-02`: `.local/loading-traces/20261105-151405-56168`.
  Both captures individually inspected: proper Chiron gameplay, but no useful
  ladder view. Six hash checks passed; this alone does not establish visuals.
- `chiron-ladder-native-03`: `.local/loading-traces/20261105-152057-36288`.
  All four generated captures inspected individually. Targeted evidence:
  `.local/map-benchmarks/chiron-ladder-review/spawn-2.png`, camera
  (-13.2, -18.24, 0.98), native position valid. Rungs and the wall behind gaps
  are visible, without the user's opaque black rectangles.
  Point 1 fell outside collision and respawned; native result correctly reports
  `valid=false`. Its screenshot and the timed captures are not ladder proof.
  No climbing or teleporter traversal was exercised by this run.
- `locate_source_surfaces.py` reads source mesh/material associations and world
  vertex bounds. It explicitly leaves compressed instance transforms unresolved.
  Chiron's ladder is mesh 5 part 9; bounds recorded in `chiron-ladder-bounds.json`.
  Resuscitation's selected panel is an instanced mesh, so its screenshot match
  still needs the instance transform and native view.
- `rodentia-floor-texture-audit.json` records unique tag previews and decoded
  hashes. The inspected Colossus `dcr_bridge_spec` tag 10120 matches the user's
  honeycomb artwork, with alpha range 0–147. This identifies the surface artwork;
  it does not establish native transparency or brightness acceptance.
- `conveyor-machine-audit.json`: source/native conveyor flags both retain
  EarlyMover/LocalizedPhysics (192). No evidence yet supports changing them.
- `conveyor-physics-audit.json`: compared source physics tag 4021 with the
  converted machine's actual model/physics dependency. Rigid-body values, motion
  types, mass and damping match. Root flag 4 is the source schema's `Is 64 Bit`
  serialization flag, intentionally cleared by `tag_metadata.py`; it is not a
  missing player-motion flag. List padding differs and is not interpreted as
  gameplay behavior. Live player transport still needs reproduction.
- Rodentia native run `.local/loading-traces/20261105-152454-30916` completed
  with three valid targeted positions. All three spawn captures and both timed
  captures inspected individually. The 155/165-second downward views show the
  honeycomb floor as transparent with the lower structure visible; opaque fill
  is removed. The interior remains readable. The outdoor second view remains
  very bright, so final brightness acceptance is open. Native captures live in
  that run and `.local/map-benchmarks/rodentia-glass-review/`.
- Source instance-bucket lookup now locates Resuscitation's corrected panel on
  mesh 10, instances 49/50, centered around (43.70,-78.62,-0.07) and
  (92.40,-159.98,-0.07). These identify both bases for targeted native review;
  they are bounding-sphere centers, not asserted walkable player positions.
- Conveyor baseline `.local/loading-traces/20261105-152821-55956`:
  first belt carried the idle player unevenly; one-second camera segments include
  zero and approximately 0.14 world-units/second forward motion. Both generated
  captures inspected: player is on the belt, with crates ahead. Relocating to
  the second belt caused a guest read violation at 0x00040002 in 0x82620360,
  recorded in `halo3mp_fault.txt`. This run failed and is not two-belt acceptance.
  `conveyor-player-baseline.json` preserves trajectory and machine snapshots.
- Separate second-belt baseline `.local/loading-traces/20261105-153132-54640`
  completed its watchdog without that crash. All three captures inspected
  individually; player remains in the conveyor lane and crates advance.
  `conveyor-red-baseline.json` preserves per-second movement. The fixed-position
  benchmark reports `valid=false` after legitimate conveyor displacement beyond
  its 1.5-unit radius; this test uses observed movement, not that FPS validity
  flag, as its evidence. No walking input was supplied after placement.
  Both baselines retain the unmodified accepted candidate06 map.
  Both source and converted conveyor animation headers contain 16-frame overlay
  animation, with equal loop/playback flags; animation/contact behavior remains
  under investigation. No speculative physics or script tuning was applied.
- Resuscitation `.local/loading-traces/20261105-153618-10180`: two native
  benchmark positions valid; all four generated captures individually inspected.
  Both bases render, with the selected diffuse material; distant views alone
  do not settle the user's close-up side/ramp appearance complaint.
- Sky Bridge `.local/loading-traces/20261105-153944-55132`: loaded the actual
  private DLC candidate and produced four individually inspected outdoor frames.
  Benchmark camera alignment timed out after a long stall; intended cylinder
  view was not reached. Not a complete validation pass.
- Sky Bridge retry `.local/loading-traces/20261105-154349-19920` reused the
  first private shader cache. Both intended positions were reached and aligned,
  with `valid=true`. Individually inspected captures:
  `.local/map-benchmarks/sky-weather-review-02/spawn-1.png` (outdoor approach),
  `spawn-2.png` (doorway view from inside). Doorway card fill is absent; native
  architecture, lighting and billboard remain. The timed capture series did
  not arrive before the watchdog: the wrapper correctly failed completeness.
  These two native captures are useful partial evidence, not a temporal flash
  verification. Existing byte-diff proof still establishes removal of the
  specific light-creation events and rain-card index ranges.
- `chiron-review-payload.json` stages the corrected Chiron with map ID 1732 and
  its installed thumbnail BLFs/mapinfo byte-for-byte. Not installed.
- `rodentia-07.json` records the new bright-area candidate and verifies only the
  camera minimum and map checksums changed from candidate06. Production build
  logic in `map_exposure.py` now reproduces this candidate minimum; do not call
  it visually accepted before the matched comparison.

Next tests: candidate07 Rodentia with the previous glass/interior/outdoor points;
close Resuscitation side/ramp view; targeted Chiron climbing; Sky Bridge temporal
check with sufficient startup margin. Powerhouse's private runner now supports
the existing `--fpsunlock`, 480p/720p and timing diagnostics for a matched
resolution sensitivity comparison. Those performance runs have not yet occurred.

The previous deploy-only turn made no map-goal progress. This turn produced
targeted native ladder evidence and identified Rodentia's pictured artwork.


Rodentia user correction: original source lighting is canonical. Removed the exposure override and deployed exact source camera bounds/target (2, 4.5, -2.514573097229004). Glass correction retained. Byte comparison permits only those three floats and checksums. Evidence: work/map-review-20261105/rodentia-original-lighting-deployment.json. Visual review remains pending; prior brightness experiments are superseded.

Conveyor Platform control rejected: all three native captures inspected; player and crate remain stationary in the red lane. Observer X is unchanged from 125.093 to 189.234 seconds. See `work/map-review-20261105/conveyor-platform-result.json`. Not installed. The machine includes both thin pushers and long support shapes; class change is not a carrying fix.

## Performance and conveyor investigation after deployment

Powerhouse native GPU baseline completed at three authored positions: 29.38,
25.29 and 27.41 ms mean execution per frame. All three spawn captures and both
timed captures individually inspected (rock/rooftop, rock edge, generator room).
The displayed frame rates were capped and are not uncapped capacity estimates.
Evidence: `work/map-review-20261105/powerhouse-gpu-720.json` and native run
`.local/loading-traces/20261105-160840-5792`.
The 480p display comparison retained the same 1152x640 guest render buffer,
so it does not isolate pixel cost. Its five captures were also inspected;
results are in `powerhouse-gpu-480.json`. No polygon-reduction conclusion follows.
Two unlocked-route attempts landed in the Theater lobby and are rejected.

Powerhouse triangle audit finds 599,560 triangles, no index-degenerate triangles
or same-winding duplicate triples within parts. Meshoptimizer v1.3 cache-order
analysis operates within opaque subparts, retains exact triangle tuples/winding,
and leaves transparent parts untouched. Its simulated transformed-vertex count
falls from 1,005,579 to 797,519 across eligible subparts. This is an estimate,
not a runtime performance claim. Source/tool: https://github.com/zeux/meshoptimizer
at 9e1f07b159d3cb777f1c67ed31fc11fd117986f4, MIT license retained in
`.local/map-review-deps/meshoptimizer`. No decimation has occurred.

Conveyor clearance control raised only the six invisible machines by 0.05 units.
Player camera rises accordingly, but movement still has repeated zero-speed
intervals. All three native captures inspected; crates and player advance along
the lane, with intermittent stops. Rejected as a fix and not installed.
Evidence: `work/map-review-20261105/conveyor-clearance-result.json` and
`.local/loading-traces/20261105-161630-46104`. Read-only player object samples are
now present; raw handle references require verified field semantics before being
called contact/support identities.

Powerhouse cache-order private candidate built: `work/map-review-20261105/powerhouse-cache-order.map`. Resource controls/fixups and every non-index byte of the decoded geometry resource were verified unchanged. Opaque subpart boundaries and exact triangle tuples/winding are retained; collision is untouched. Runtime performance/visual comparison is in progress; not installed.

Powerhouse cache-order candidate native run completed:
`.local/loading-traces/20261105-162405-55828`, all four resource hash checks passed,
three valid benchmark views, all five captures individually inspected. GPU means
28.65 / 23.52 / 25.69 ms versus 29.38 / 25.29 / 27.41 ms baseline (about 2.5%,
7.0%, 6.3% lower). Locked displayed rates 28.906 / 29.880 / 30.011 are not uncapped
capacity figures. No visual regression was seen in these views; no all-map or
console performance claim. Deployed with original metadata/thumbnails and
Sanctuary preserved: `work/map-review-20261105/powerhouse-deployment.json`.
All original triangles are retained; no polygon reduction was needed for this
measured improvement. Larger geometry simplification remains a separate possible
tradeoff, not an implicit permission to remove authored detail.

Conveyor Gear control also rejected: native run `.local/loading-traces/20261105-162855-37328` completed, all three images inspected, repeated near-zero/zero transport intervals remain. `conveyor-gear-result.json` records the trajectory. No conveyor experiment has been installed. Classification and floor clearance have now been tested; do not repeat these as proposed fixes. Next diagnosis must examine animated support/recycling and player motion rather than repeat type changes.

## Close-up review completion

Resuscitation native run `.local/loading-traces/20261105-163337-55592` completed with both close base positions valid. All four images inspected individually. Corrected panels show their authored artwork; unrelated fallback normal/specular behavior is removed. Archived captures and bounded conclusions: `work/map-review-20261105/resuscitation-close-evidence/review.json`.

Rodentia native DLC run `.local/loading-traces/20261105-164001-26552` completed with three valid positions. All five captures inspected individually; downward views show glass and the structure beneath. Exact source exposure restoration remains installed; bright outdoor appearance is not retuned. Archived evidence: `work/map-review-20261105/rodentia-original-lighting-evidence/review.json`. Initial attempt failed argument parsing before launch, and is not a test.

Conveyor reference research: read-only ManagedDonkey commit `38295bdc94a3839921a33d2fa6efee64e44ff13b` suggests local-physics semantics; Halo Online layouts are not asserted to be Xbox360 offsets. Source/native machine OBB blocks both empty; sampled player reference 0xa4 alternates lane machine handles. A one-bit localized-physics control is being tested privately; no conveyor change installed.

Localized-physics control rejected: `.local/loading-traces/20261105-164428-54372`, all three native captures individually inspected; 14 near-zero one-second movement intervals remain. Source/native physics material names match `hard_metal_solid_hum` with empty global override. No conveyor change installed. Evidence: `work/map-review-20261105/conveyor-local-physics-result.json` and `conveyor-material-name-audit.json`. Next: animated-node transport and script recycling, not another flag/class/clearance variation.

## Conveyor animation diagnosis

Expanded read-only baseline run `.local/loading-traces/20261105-165045-9520` completed; all three native captures inspected individually. Device position progresses at -0.05/second while player carrying stalls. Device phase/frame relation verifies within 1.8e-7. The three overlapping support nodes repeatedly restart in the flat opening keyframes as scripts recreate them. Stationary-player intervals coincide with newly created/near-static supports while other supports move. This is correlation until the linear control is tested. Evidence: `conveyor-state-analysis.json`.

`audit_conveyor_animation.py` proves the entire converted animation control/payload/fixups equal the source after endian conversion. Codec 6 has two opposite translation channels, 16 frames, keys 0/1/2/5/12/15; first two key values are identical. A private linear-animation control retains endpoints, paths, duration, scripts, collision and all machine flags, changing eight intermediate X values only. The rebuilt resource was reopened and verified. Not deployed pending native result.


## Powerhouse acceptance gate — 2026-11-11

User requires at least 35 uncapped FPS at each of three distinct spawn points (two outdoors and generator room), no timing changes. Original baseline 27.455 / 31.183 / 31.781; installed index-order candidate 28.340 / 32.053 / 26.692. All six captures individually inspected. A private 14.217% geometry reduction retained collision and original vertex data but measured 28.590 / 30.273 / 26.778; rejected as insufficient and not deployed. Testing opaque overdraw ordering next, with all original triangles retained. No acceptance or hardware-console claim.

Native route discovery: long uncapped-menu waits enter the attract video; short inputs could miss polls. Confirmed route is `45000:B+200,46000:DOWN+200,47000:A+200,50000:A+200,54000:A+200`, using an isolated Last Resort slot containing Powerhouse. No OS input, game clock or simulation changes. Earlier menu-only attempts are failures, not FPS evidence.

Overdraw-order candidate retained all 599,560 triangles and measured 27.180 / 28.448 / 23.773 FPS; all three native spawn captures individually inspected. Concurrent GPU workloads invalidate attributing that regression to map ordering: RacerRevengePC started 15:39:21 and Xemu 15:42:30; the overdraw run was 15:41:23–15:43:xx. OBS started 14:41:17. These start times do not explain the earlier low FPS. The installed map was rehashed unchanged and reusable private map restored to installed-equivalent cache-order basis. No game instance remains. Awaiting user choice on closing/pausing other applications versus measuring under current load.

User steering: benchmark under current concurrent load; leave Xemu, Racer Revenge and OBS alone. Acceptance remains >=35 FPS in each of three views. Current installed-equivalent map is being remeasured with 30-second samples per view, unchanged original video quality and --fpsunlock.


## 2026-11-11 loaded benchmark and conveyor deployment

Current-load Powerhouse benchmark completed at 31.228 / 30.011 / 27.540 FPS over 30 seconds each. All positions valid; three native captures individually inspected. User requested concurrent load. Basic-water diagnostic measured 29.396 / 31.462 / 27.057, no consistent benefit; original private settings restored and no performance experiment deployed. The 35 FPS gate remains unmet.

3longation linear animation passed both red and blue transport checks (79 observer samples each, no near-zero intervals). Installed after verifying DLC identity-only rewrap and retaining original metadata/thumbnails, rollback and accepted Sanctuary hash. See work/map-review-20261105/elongation-review-payload.json and elongation-deployment.json. Shared runtime map is corrected; current-live package still contains previous 3longation and must be refreshed before claiming packaging parity.


Main LIVE bundle refreshed 2026-11-11 to 325626ABDF6E6266E29C15269D930E79D2616F3E. All 77 payload files match installation byte-for-byte, STFS integrity verified. Only elongation.map changed against previous payload inventory. Sky Bridge container hash unchanged. Superseded main container removed after verification; exactly two current containers remain. No hardware-console test claimed.


Powerhouse 2026-11-11 rendering diagnosis: read-only visibility audit proves both 18-row PVS tables and all 138 portal connections match source; 17/18 rows restrict visibility. No culling rewrite justified by this evidence. Native uncapped profiling run 20261111-163608-20780 completed three 30-second samples: 29.389 / 33.684 / 34.783 FPS; mean GPU execution 30.254 / 25.690 / 25.327 ms. All three captures individually inspected, valid positions. GPU time is roughly 87–89% of frame duration under concurrent load; no map change or performance improvement claim. Process stopped after COMPLETE. Next: rendering-pass/material cost isolation, retaining original quality for acceptance. Reports: powerhouse-visibility-audit.json and powerhouse-execution-profile.json.


Powerhouse material inventory: 599,560 native triangles partitioned by BSP material. Verified all 460 source Lbsp/native BSP mesh part-material assignments; 213 material palette entries in each. Bolts 59,318 triangles, pipe couplings 45,651, sandstone 89,294. Program byte lengths retained only as inventory, not GPU cost estimates. Source geometry is in Lbsp (source BSP mesh array is empty); direct BSP-to-BSP mesh comparison is invalid. Evidence: work/map-review-20261105/powerhouse-material-cost-inventory.json. No material or geometry modified. Next diagnostic should isolate small-detail draw cost before any additional decimation or shader substitution.


Powerhouse small-detail exclusion diagnostic 20261111-164335-14344: zeroed BSP/lightmap draw counts for materials27 and60 only (100 parts;104,969 triangles), verified all other bytes except checksums unchanged. Three valid30-second samples:32.111 /37.526 /34.628 FPS; GPU means28.583 /24.003 /25.868ms. All three native captures inspected; indoor pipe fittings visibly absent. This upper-bound diagnostic still fails two views and is not a production fix. Variable background load prevents exact attribution. Private map restored byte-identical to cache-order baseline; installed/LIVE untouched. Evidence: powerhouse-detail-cost.json and powerhouse-detail-cost-profile.json.


Powerhouse shadow diagnostic20261111-164809-19788 finished normally; seven10-second phases in one process. Same recorded position/forward in phases4–6. GPU means27.166ms original /27.388ms zero-budget /28.082ms original. Shadow-map calls drop from4 per water draw to1 (not zero), so this is not proof all shadow rendering stopped. All three timed captures individually inspected, map intact; no useful performance gain demonstrated. Native captures may affect wall-clock FPS. Private sweep setting removed, original three-point benchmark restored, installed maps/settings untouched. Evidence: powerhouse-shadow-cost.json.


Bounded per-draw GPU timestamp probe implemented and SDK GPU DLL built. Probe is off unless a repository-confined OPENH3M_DRAW_GPU_DIR and arm file are present; at most3frames/16384draws, no synchronous waits or render-state changes. First runtime attempt20261111-165426-29152 never reached valid Powerhouse viewpoint; guard did not arm, no CSV produced. Wrapper exited0 at watchdog but this is a failed runtime validation, not evidence. Restored private GPU DLL from unchanged installation and original3point config. Probe code/integration retained for subsequent validation; no production deployment. Existing GPU submission trace averages2.38submissions/frame, only0.009tiny submissions/frame, so excessive tiny batches are not supported as the primary cause.


Per-draw profiler launch diagnosis: native90-second screenshots of retries165801-22868 and170053-31224 both show Matchmaking Lobby, not Custom Games. Extra later confirmation and longer separatedDOWN pulse both failed; neither produced valid map view or GPU CSV. Stopped only private processes; restored private renderer/config. Next investigate startup before menu inputs, not another downstream button-duration trial. Profiler build remains successful but runtime unvalidated.


Native startup capture170410-30992 establishes main menu already ready at30/40/44seconds. RemovingBack reaches Custom Games (170531-10492); finalStartGame needs lobby readiness. Verified route31000:DOWN+200,33000:A+200,36000:A+200,40000:A+200,70000:A+250 loaded Powerhouse in170813-20712. Per-draw probe armed on valid view, produced3frameIDs; first discarded. Particle-update shader2217137582779835915 matched exact native programbytes (exclude constant prefix) and ranks highest at5.181ms/frame in two instrumented frames. Three native gameplay images individually inspected. No production-cost or FPS claim; missing probe shutdownfooter limits completion verification. Add explicit capture-complete marker and warmup delay before repeat. Private renderer/config restored; installed unchanged.


2026-11-11 settled GPU trace: first retry171459-16768 loaded the map but no benchmark because runner wrote doubled CR line endings to TOML; both screenshots inspected, no usable measurement, config restored. Runner now normalizes and parses TOML before launch. Successful retry171829-17640 has explicit complete marker:12,360draws across3frameIDs, first discarded. Both timed native captures individually inspected. Probe now records actual active pixel shader (not stale bound state), vertex hash and memexport status. Earlier particle pixel label is invalid attribution. Vertex shader11431419820553024093 correlates to particle_update tag7727:8,976codebytes, only33words in11initial vertex-fetch instructions change at runtime linkage; remaining instructions identical. Particle vertex group4.440ms in two instrumented frames; total captured draw costs are not isolated vertex timings. Single-view60second diagnostic21.263FPS is not a three-view acceptance run. No map/runtime deployment. Testing existing dxbc_switch=false privately across original three views, with uninstrumented installed renderer and unchanged quality/timing.


Alternative shader-control-flow trial172305-10604 completed all3valid30secondviews:25.541 /26.185 /14.224FPS. GPUmeans34.868 /32.566 /62.836ms under concurrent load. All6native images individually inspected. All views fail35FPS, rejected; private configuration restored and renderer DLL matches installed hashB09F847BEE09F831E27EC118A68641D15B0ADF11D738336402FE77BD77D2F4BA. No production change. Capture copies archived in powerhouse-controlflow; this run reused and overwrote powerhouse-current-load/spawn images, so those images now depict this trial, not the earlier baseline. Future trial runner now uses its own compact points/output folder. Raw rotated logs are now included by FPS summarizer. Cleanup of failed trace171459-16768 was blocked by automatic approval review; retained, no alternate deletion attempted.


2026-11-11 batching audit: 460 meshes, 1,400 parts, 28,678 subparts; zero duplicate compatible opaque batches inside a mesh. Every populated mesh has MOPP visibility data, so simple merging is not supported. New private geometry candidate removes18.4559%:599,560 to488,906triangles; SHA798ee32bd89d18927ce340d9c1e4df197cf246a6467fcccca638d329579cc685. Run173019-12796:15.946 /25.338 /14.519FPS, three valid30second samples. All3native captures individually inspected; no obvious gross new surface/material defect in those views, not full traversal approval. RacerRevengePC26112 restarted17:27:01; one live sample47.857%GPU3Dengine versus OpenH3M46.898%. Other apps left running. Candidate fails35FPSgate; not deployed; private map/config restored. Immediate original-map baseline next. Replaced only the prior generated candidate after its recorded hash matched; reused existing staging.


User2026-11-11 explicitly redirected effort away from clean FPS baselines. Stopped only private baseline process20708 after verifying executable and trace173409-28588; runner restored private map/config. Independent reduction verifier passed: all metadata identical except opaque index counts/ranges and geometry resource descriptors; resource payloads identical except reduced index ranges; collision data/fixups/raw buffers identical. Installed DLC SHA9b4a7ee5604d2c11e73cc2330bc5b90d92e65e5e67fd47f11801916ab2082cf1,58identity bytes differ from tested candidate. Metadata/thumbnail/Sanctuary preserved. Retained only latest verified rollback. Three proof images updated; no FPS gain claimed. LIVE refresh started.


LIVE refresh complete: main1C912C9AC8F772E69D150E9C9CC644F191E9305F contains installed reduction. All77payload files compared byte-for-byte and STFS hash tree verified. Sky container unchanged; superseded main removed after checking both hashes. Exactly two current containers remain. Refreshed current-proof-audit.json verifies all installed map hashes against current manifests and Sanctuary acceptance hash. No game process remains.

Sky Bridge unlocked benchmark, 2026-11-11: user loaded the map manually after automated menu routes failed. First pass measured two valid indoor views for 30 seconds each: Terminal 02 28.659 FPS, Terminal 01 31.786 FPS. Both native captures inspected individually. Concurrent sampled total 3D-engine utilization averaged 94.80% and 94.13%; unrelated GPU processes remained running. Exterior sample 44.246 FPS rejected because the authored start settled below the permitted height range. Second manual-launch process is waiting for the user to load Sky Bridge, configured for corrected exterior height plus doorway and outdoor positions. Evidence: .local/map-benchmarks/sky-bridge-manual-20261111/results.json. Five-view result remains incomplete. No simulation timing or map assets changed.

Sky Bridge benchmark completed: five accepted native views, 30 seconds each, captures individually inspected. Terminal 02 interior 28.659 FPS; Terminal 01 interior 31.786; corrected exterior wall 42.913; outdoor courtyard 31.997; interior doorway looking outdoors 35.365. Shared-load GPU samples retained; initial invalid exterior sample excluded. Report and screenshots: tools/map-review/SKY-BRIDGE-FPS-20261111.md. Five-view request complete; game left open and native benchmark input released. Powerhouse review remains outstanding; no broader goal-completion claim.

User accepted the Powerhouse correction pass on 2026-11-11. All six map corrections are complete for this pass. Rechecked all installed map hashes against the current proof audit and both LIVE container hashes against the manifest at closure. The 35 FPS Powerhouse target remains unverified, not waived into a measured result. Forge follow-ups remain deferred in TODO.MD.
