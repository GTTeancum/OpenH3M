# OpenH3M custom maps TODO

## Performance and hardware coverage

- [ ] Resolve uneven motion/frame pacing despite the reported 30 FPS average.
  Measure new in-game frames separately from host presentation, and compare
  converted maps against original disc maps. Work is in progress.
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

## Video options

- [ ] Add a video-options menu for quality settings, with understandable presets,
  relevant individual controls, persistent settings, and restore-defaults support.
  Identify which settings the existing runtime actually supports before choosing
  controls; verify their visual and performance effects on the test matrix.
  Engine-side implementation remains subject to the existing instruction to
  keep OpenH3M unchanged unless the user explicitly overrides it. Recording this
  TODO does not authorize engine modifications or altered game simulation.

## Packaging and maintenance

- [ ] After the three converted maps are ready, package them as one DLC bundle
  rather than stock-map replacements.
- [ ] Keep the conversion process repeatable and documented. Maintain one shared
  test installation, regularly remove superseded outputs, and retain only the
  rollback and diagnostic evidence needed for current work. Never commit assets.
