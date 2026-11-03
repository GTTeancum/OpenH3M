# Sky Bridge playtest feedback — 2026-11-03

User instruction: keep the Sky Bridge goal open until the user explicitly
authorizes closing it. Report stalled work and blockers without declaring
completion. Continue work while progress is possible.

Reported issues: framed panels render black with bright vertical streaks;
the two supplied playtest screenshots show 20.8 and 19.7 FPS. Candidate 27's
earlier bounded launch proves loading only, not correctness of these panels
or acceptable performance. The released package is not a verified correction.

Investigation artifacts remain inside `work/sky-bridge`:

- `panel-feedback/materials.json`: source hologram material/texture bindings.
- `panel-feedback/texture-index.png`: decoded source texture reference;
  unsupported preview formats still require inspection.
- `play-log-audit.json`: 339,697 visibility-query messages among 359,723
  retained log lines over approximately 338 seconds. No present-timing samples
  were enabled in the human play session. Logging overhead is a hypothesis,
  not an established explanation for low FPS.
- `performance-baseline-01`: bounded run with native frame timing enabled,
  using the same executable and candidate 27 payload as the play session.

The baseline finished under its 180-second watchdog. Native `loaded.png` was
visually inspected: Sky Bridge is in gameplay, and a streaked panel is visible
in the left corridor from the authored spawn. This reproduces the defect in a
reachable test view without host input. The 110–179 second timing window has
1,090 observed frame-change intervals after excluding the capture interval:
median 66.385 ms, p95 83.041 ms. Summed GPU submission execution per observed
frame has median 30.826 ms; logged queue waits have median 21.848 ms. These
instrumented stationary observations identify substantial GPU/wait cost but
do not isolate its cause or establish traversal performance. Native capture
and timing evidence are in the baseline directory; no fix is claimed yet.

## Deeper material investigation

Mapped all 345 BSP material entries between source and candidate 27 by their
preserved table order. `panel-feedback/bsp-material-map.json` records the map.
Ten source materials with no normal texture inherited Voi's
`metal_factory_outerpanel_i_bump`; see `unintended-normals.json`. The converted
door-light texture payloads themselves decode correctly. This does not yet
identify which surface produces every reported streak.

The source `screen_lines` material was mapped to opaque fallback metal,
dropping its self-illumination texture and controls. The source rmdf explicitly
identifies option 7 as `calc_self_illumination_times_diffuse_ps`. A simple
emission replacement is not equivalent. Native candidates found so far use
other albedo/distortion options and require further analysis.

The stock-template audit found nine exact option names covering 66 source
materials, but most have parameter differences, including MCC boolean versus
H3 float `use_material_texture`. Only the eight pure diffuse-only materials
have been routed to their exact stock diffuse-only shader so far. Their
parameter lists match. The isolated converter change is retained in
`sky-bridge-feedback-materials.patch`; the preexisting dirty importer is not
staged wholesale. Syntax parsing passed; rebuilt-map verification is pending.

The async visibility comparison (`performance-async-02`) still showed the
streaked panels. Median observed frame interval was 50.238 ms, p95 83.868 ms;
median summed GPU work was 32.128 ms. This is insufficient for acceptable
performance and is not an accepted runtime correction.

User requested closing the failed test and doing deeper work before further
launches. PID 32392 was stopped and confirmed gone. That diagnostic copy had a
valid body checksum but an invalid header SHA1 because the diagnostic edit
failed to refresh it. The original payload passes both checks. The diagnostic
header has been repaired on disk without relaunching; it is not a release.

The icon chat reports a newly rebuilt executable and runtime DLL. Future
tests must verify those current binaries and account for the runtime change;
the old executable hash must not be silently substituted in launch scripts.
No further game launch has occurred after the user's close instruction.

Original map: Sky Bridge from Halo Online. Source conversion: GeneralHeed /
Priception, Halo Online Map Pack For Halo 3, Workshop 3003239190:
https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190
Source cache: `s3d_sky_bridgenew.map`. This project supplies the Xbox 360 /
OpenH3M adaptation; the original individual map creator is unspecified.
