# OpenH3M custom maps TODO

## Performance and hardware coverage

- [ ] Resolve uneven motion/frame pacing despite the reported 30 FPS average.
  Measure new in-game frames separately from host presentation, and compare
  converted maps against original disc maps. The host pacing fix is deployed;
  verified Prisoner variation fell from 14.718ms to 0.806ms. Remaining: reproduce
  the larger intermittent Cold Storage traversal hitch before calling this done.
- [ ] Optimize further after the current frame-pacing investigation. The only
  test system so far is the user's **Beelink SER8**; results do not establish
  performance on other PCs or Xbox 360 hardware.
- [ ] Establish a small representative hardware test matrix, including slower
  systems. Record CPU/GPU, memory, display refresh rate, settings, map, frame-time
  distribution, loading time and memory use. Reuse bounded reproducible routes
  and in-game capture tools; avoid exhaustive testing and duplicate builds.
- [ ] Profile CPU, GPU, memory and resource streaming before selecting further
  optimizations. Preserve original Halo 3 behavior and stock assets, and keep
  converted caches appropriate for the Xbox 360 compatibility objective.
- [ ] Investigate loading-time shader/pipeline preparation for first-visit
  stutters. Cached pipelines already load at startup; Cold Storage exploration
  increased that cache from 507 to 560 pipelines. Confirm causality with timing
  before attributing all stalls to compilation. Keep one shared cache and do
  not skip rendering or change guest simulation to hide compilation work.
  A fresh-cache recorded walk showed an 82ms gap overlapping pipeline builds.
  The startup worker-limit/completion-wait correction is deployed and passed
  stock Cold Storage and direct Prisoner native checks;
  it prepares known combinations only, not unencountered content.

## Video options

- [ ] Add a video-options menu for quality settings, with understandable presets,
  relevant individual controls, persistent settings, and restore-defaults support.
  Identify which settings the existing runtime actually supports before choosing
  controls; verify their visual and performance effects on the test matrix.
  The user authorized host-engine smoothness patches on 2026-10-20, provided
  the core stays compatible with Xbox 360. Preserve that boundary for quality
  settings; recording this TODO does not authorize altered game simulation.

## Packaging and maintenance

- [ ] After the three converted maps are ready, package them as one DLC bundle
  rather than stock-map replacements.
- [ ] Keep the conversion process repeatable and documented. Maintain one shared
  test installation, regularly remove superseded outputs, and retain only the
  rollback and diagnostic evidence needed for current work. Never commit assets.
