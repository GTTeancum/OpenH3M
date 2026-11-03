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

Original map: Sky Bridge from Halo Online. Source conversion: GeneralHeed /
Priception, Halo Online Map Pack For Halo 3, Workshop 3003239190:
https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190
Source cache: `s3d_sky_bridgenew.map`. This project supplies the Xbox 360 /
OpenH3M adaptation; the original individual map creator is unspecified.
