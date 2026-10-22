# OpenH3M custom maps TODO

## Performance and hardware coverage

- [x] Resolve periodic uneven motion/frame pacing despite reported30FPS.
  Phase-aligned host presentation is deployed and direct-launch verified on the
  SER8:1,347/1,347 measured image transitions evenly spaced, no missing images.
  Stock recorded walk99.1% evenly spaced; one isolated65.58ms output gap remains
  for broader performance profiling. Guest clocks and map assets are unchanged.
  Rendering follows29.97FPS on this59.94Hz display. Compared with one-frame
  capacity, the chosen queue adds roughly one refresh of measured report delay.
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

## Converted-map rendering regressions

- [ ] Fix missing Forge menu glyphs on Forge Gulch. The 2026-10-21 process-local
  palette check reproduces missing letters/symbols on Gulch while the identical
  stock Sandbox route renders them correctly with the same runtime/font package.
  See FORGE-WORLD.md for both native captures and the repeatable route. Investigate
  conversion data/resource usage; do not treat the earlier readable main-menu
  capture as coverage of this failure.

- 2026-10-22 update to the Forge Gulch glyph issue: three requested automated
  comparisons (palette-only, CPU-font probe, combined diagnostics) all showed
  complete text in individually inspected native captures. No causal fix was
  made. Retain as a monitored regression; do not repeat this checkpoint without
  new failure evidence. Results and limitations are in FORGE-WORLD.md.

- 2026-10-22 follow-up: corrected-address font run 20261022-103051-32368
  reproduced missing J/#/$ and budget text. CPU glyph pixels were populated
  and stable at the correct address. Text glitch is active again; focus on
  GPU upload/drawing rather than repeating the three-run readability check.
