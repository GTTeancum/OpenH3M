# Sky Bridge — exclusive text-only takeover

## User-directed takeover

The user explicitly requested a new chat to take over the currently stalled
Sky Bridge goal, using only this Markdown file as handoff context, with no
chat history and no image imports. You are the new owner. Start by creating
an active goal with the full objective below; do not merely propose taking it.
The source chat has stopped project work. Its goal currently reports blocked.
Do not inspect, read, fork, or import the source chat or other chats for context.
Do not import images: no image attachments, image viewers, screenshot imports,
image OCR, image decoding for model input, or indirect image-to-context routes.
Use textual source, binaries, metadata, logs, and test reports for investigation.
If final visual verification requires human observation, preserve that explicit
requirement and report it honestly; do not replace it with a claim based only
on frames rendering. There is substantial independent work available now.

## Goal (create verbatim)

Address Sky Bridge playtest feedback: identify and fix the black, vertically
streaked panels reported by the user; diagnose and correct the roughly 20 FPS
performance while preserving original Halo 3 behavior and Xbox 360
compatibility; verify the affected visuals and measured performance, then
update the LIVE DLC package. Keep all work inside
C:/X360/ISOs/H3M/.local/OpenH3M-source, preserve unrelated changes, use no desktop
control, and import no images. Keep the goal open until the user explicitly
authorizes closing it.

The user explicitly said: "Don't close this goal. You only get to stall it
unless I say otherwise." Do not mark completion on your own. Do not shrink
the objective to a passing launch, isolated material fix, or packaging alone.
The latest work instruction before takeover was: "Load failed. Close it and
do some deeper work for a while." The failed process was closed. Keep the
game closed during the current deeper source/conversion work; do not immediately
repeat launches. This is not a request to stop investigating or pause the goal.

## Repository and operating constraints

- Repository: `C:/X360/ISOs/H3M/.local/OpenH3M-source`, branch `main`.
- Set the working directory explicitly. All project-created outputs, temporary
  files, caches, profiles, logs, builds, and captures stay in this repository.
  Use ignored `work/sky-bridge` or `.local` directories. A new chat's default
  Documents workspace does not authorize writing project files there.
- Read the repository AGENTS.md. Preserve existing unrelated dirty changes.
  Do not stage the whole importer or other preexisting dirty files. Prior
  task changes are tracked as narrow integration patch snapshots where needed.
- Commit narrow changes locally; no push or external install is authorized.
- No computer-use tools, capture app, desktop automation, OS keyboard/mouse/
  controller input, or window activation. Ordinary process management is allowed.
  Process-local game harness input is allowed when testing later, but no image
  imports are permitted in this new chat.
- No subagents unless separately authorized. The user requested a new owning
  chat, not parallel agents.
- Python: `C:/Users/smmel/AppData/Local/Programs/Python/Python312/python.exe -B`.
  PowerShell shell. Keep TEMP/TMP and any generated caches in repository.
- Existing original H3 assets are preferred whenever applicable. Preserve
  native gameplay, simulation, map formats, physics, and network semantics.
- Target LIVE/STFS DLC for OpenH3M and RGH/JTAG. No retail signing or physical
  Xbox acceptance has been established. Do not claim network compatibility tested.

## What the user observed (text description only)

Two playtest screenshots showed framed panels as opaque black surfaces with
bright noisy vertical strips, indoors and in an outdoor courtyard. Window
titles reported 20.8 and 19.7 FPS. The same strip pattern was subsequently
observed in the left corridor from the authored Slayer spawn. The prior
launch check established loading, not acceptable visuals or performance.

## Current authoritative state

Recent commits:
- `3332346`: first material correction and deeper audit notes.
- `83ab7e9`: reproduced defect and performance baseline.
- `e7a9a7f`: feedback and keep-goal-open instruction.
- `304c388`: earlier pending-feedback TODO state.

No game process should remain; recheck before any process action. PID 32392
was stopped and confirmed gone after the user reported load failure.

The icon build changed the host binaries during this investigation. Current
`work/rexglue-sdk/out/win-amd64/halo3mp.exe` SHA256 was independently verified:
`54c8e03981b06d319f3c81a0b52f1741bb88f4876b894cbec94ca9efa9a55326`.
It also rebuilt debug_overlay.cpp and relinked rexruntime.dll. Existing timing
runs used the previous executable SHA256
`25be7e7212e021d3b51ffeafc522782d442b4233b9e3051f025690e5e5f86a9d`.
Do not blindly replace the old hash in launch scripts or treat comparisons
across binaries as controlled. Preserve icon/CMake/Advanced Forge changes.
Icon build evidence: `.local/icon-work/build.log`, `verification.json`;
prior exe backup `.local/icon-work/halo3mp-before-icon.exe`.

## Existing package and source

Released candidate 27 is NOT a verified fix for this feedback:
`.local/releases/sky-bridge-final-20261103/Sky-Bridge-LIVE-DLC.zip`.
Staged payload: `work/sky-bridge/payload-27`.
Checkpoint: `work/sky-bridge/zanzibar-27.map`.
Build report: `work/sky-bridge/build-27.json`.
Source cache (read only):
`D:/SteamLibrary/steamapps/workshop/content/976730/3003239190/maps/s3d_sky_bridgenew.map`.
Source shared cache: same package's `halo3/maps/shared.map`.
Original H3 stock maps: `C:/X360/ISOs/H3M/maps`; XEX: parent `default.xex`.

Map credit for every conversion report: Sky Bridge from Halo Online, converted
upstream by GeneralHeed / Priception in Halo Online Map Pack For Halo 3,
https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190 . This project
supplies the Xbox 360/OpenH3M adaptation. Original individual creator unspecified.

User accepted native H3 flare and camera behavior: retain native exposure/bloom,
omit unsupported SSAO/screen-space sun shafts. "Forge effects? If so just drop
them" was conditional and does not authorize indiscriminate effect removal.
Powerhouse is outside this task; its TODO section must remain only
"Pending user feedback". Sky Bridge TODO was previously the same; do not treat
that stale label as proof this feedback has been resolved.

## Findings to preserve and deepen

1. `panel-feedback/bsp-material-map.json` maps all 345 source BSP material
   table entries to the converted map by preserved order. Source sbsp 10471,
   material block offset 0xD0; target sbsp 9225, block offset 0xC0; stride 36.
   Script: `work/sky-bridge/map-bsp-materials.py`.
2. Ten source materials with no bump map inherited Voi's factory-panel bump
   (target bitmap 6114) through the generic metal fallback. Details:
   `panel-feedback/unintended-normals.json`, `audit-unintended-normals.py`.
   This is a real conversion mismatch, but which surface causes each streak
   has not yet been fully established.
3. Converted door-light bitmap payloads decode correctly. Door-light source
   materials map to target tags 9577, 9636, 9639, 9721 by identical float
   constants. Textual metadata: `panel-feedback/door-target-match.json`.
4. `screen_lines` is source rmsh 12515, target rmsh 9730. It lost its authored
   self-illumination texture and controls and was mapped to fallback metal.
   Source variant `_0_0_0_0_0_0_7_1_0_0_0_0_0` is additive and uses
   `calc_self_illumination_times_diffuse_ps`, confirmed from source rmdf.
   This is not equivalent to simple emission. Source primary_change_color_blend
   is static value zero, but the material DOES have animations (see latest issue).
   Base map is `objects/bitmaps/screen_maps/screen_line_01` (backslashes in tags).
   Base transform (1,30,0,0); self-illum transform (1,1,0,4); intensity 38.72549.
5. Native template audit: nine exact option names cover 66 source materials,
   but parameter interfaces differ for most, including MCC bool versus native
   float use_material_texture. Do not equate matching names with fidelity.
   Reports `native-standard-template-audit.json`, `native-standard-parameters.json`
   under `work/sky-bridge/panel-feedback`.
6. First correction already made in material_importer.py: scope to source
   `s3d_sky_bridgenew.map`, route eight pure diffuse-only materials with source
   `_0_0_0_0_0_0_0_0_0_0_0_0_0` to exact native ten-option equivalent.
   Parameter lists match. Syntax parsed; not yet rebuilt or runtime verified.
   Narrow tracked snapshot:
   `tools/warlock-conversion/snapshot/reference/sky-bridge-feedback-materials.patch`.
7. A diagnostic copy changed target window material 9234's inherited bump to
   neutral bitmap 32. It failed loading because the experiment updated body
   XOR checksum but omitted header SHA1 refresh. Original payload passes both.
   `check-diagnostic-integrity.py` proved this and repaired only the diagnostic
   file. It has not been relaunched or accepted. Never deploy this experiment.
   `panel-feedback/diagnostic-load-integrity.json` records evidence.

## Performance evidence

All times below are instrumented stationary-spawn host observations, not a
traversal or console benchmark. No performance fix accepted.
- Human play log: ~339,697 visibility-query messages over ~338 seconds;
  no frame timing enabled. Logging overhead is only a hypothesis.
- `performance-baseline-01`: median observed frame interval 66.385 ms,
  p95 83.041 ms; summed GPU execution median 30.826 ms/frame; queue wait
  median 21.848 ms. Native capture interval excluded from frame statistics.
- `performance-async-02`: existing d3d12_async_occlusion_readback enabled;
  median interval 50.238 ms, p95 83.868 ms; GPU median 32.128 ms/frame.
  Defect remained. Insufficient performance, not an accepted runtime change.
- Each directory has `timing-summary.json`, launch.json and rotating text logs.
  Summary script `work/sky-bridge/summarize-feedback-timing.py`.
- Do not import the PNGs in those directories. Written observations above are
  sufficient starting context. Future proof of visual fixes remains required.

## Latest unfinished work — next useful action

No shader integration yet for screen_lines. Experimental compiler script:
`work/sky-bridge/build-screen-native.py` produces 13 Xbox 360 pixel programs in
`work/sky-bridge/screen-native-01` using installed XDK and existing adapted H3
shader source. It uses default albedo, no bump, diffuse-only, no environment,
times-diffuse illumination, additive blending, and maybe_calc_albedo=1.
That last define preserves the native transparent-material albedo branch;
without it the shader incorrectly reads only the opaque albedo buffer.

Native donor chosen for interface analysis:
`shaders/shader_templates/_0_0_0_0_0_0_1_1_0_0` in stock zanzibar.map.
It has 12 pixel entries: 1,3,4,5,6,7,8,9,12,13,14,17. Script
`reflect-screen-donor.py` saved `screen-native-01/native-reflection.json`.
Native shader has actually_calc_albedo at b0 and fixed texture slots 10–13.

The compiler currently specializes primary_change_color_blend=0 to eliminate
an otherwise unnecessary primary_change_color register. **This specialization
is not yet proven safe against animations.** The next script
`work/sky-bridge/plan-screen-native.py` failed on `assert not s.u(p+92)` because
the source material HAS an animation block. It did NOT create a valid route
plan/interface audit. Next action: inspect all actual source animation routes
and functions; determine whether primary_change_color_blend is animated.
If not, guard its specific absence, preserve the other animations through
existing material_animation.py, and complete the 12-entry route/interface
audit. If it is animated, remove specialization and map the required native
color binding correctly. Never freeze the material's animations for convenience.

Useful existing code:
- `tools/warlock-conversion/snapshot/tools/sky_bridge_hologram.py`: scoped
  shader cloning and named route mapping, currently specific to 10 hologram
  entries. Do not weaken its guards to squeeze in a 12-entry rmsh profile.
- `powerhouse_compiled_concrete.py`: standard rmsh shader cloning, 12-entry
  native interface guard, fixed texture slots and route handling.
- `reference/sky-bridge-soft-shaders/plan-routes.py`, `audit-interface.py`:
  native register/extern mapping and declaration audit patterns.
- `lightmap_register_reservations.py`: enforce fixed shared register blocks.
- Existing adapted source under `work/powerhouse/native-concrete-shaders/xenos-source`;
  pinned source cache `work/powerhouse/shader-toolchain/reference/halo_online_shaders`.
- `tools/warlock-conversion/build-sky-bridge.ps1` currently targets candidate 27
  and must not overwrite it. Choose fresh paths for future corrected builds.
- Packaging helper `snapshot/tools/package_sky_bridge.py` produces LIVE/STFS.

Keep investigating and implementing. Do not mark the goal closed, claim visual
verification from text logs, or repackage an unverified diagnostic as final.
