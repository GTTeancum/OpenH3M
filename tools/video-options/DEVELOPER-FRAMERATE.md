# Developer FPS unlock and map benchmarks

User direction, 2026-11-05: only FPS measurements are required. Sped-up gameplay
is accepted during developer benchmarks. Do not add simulation timing compensation.

Configure with `-DOPENH3M_DEVELOPER_BUILD=ON`. This option defaults OFF. Release
builds must configure it explicitly OFF when reusing a developer build directory.
The FPS unlock and benchmark hooks are compiled only in developer builds.

Launch `OpenH3M.exe --fpsunlock` to keep FPS unlocked for that process. Without
the switch, normal 30 FPS pacing remains. F7 no longer changes FPS. The switch
enables host FPS=0, host sync interval=0, SDK vsync=false, and guest immediate
presentation. Simulation code is not compensated; the game may run faster.
No performance qualification is applied. FPS and unlock status are no longer
displayed in the title bar. Optional file logging and benchmark counters remain.
The benchmark runner passes `--fpsunlock` explicitly.

## Benchmark commands

Run from `C:/X360/ISOs/H3M/.local/OpenH3M-source`:

```powershell
python tools/video-options/benchmark_maps.py --list
python tools/video-options/benchmark_maps.py --map chillout
python tools/video-options/benchmark_maps.py --map sky_bridge --spawn 2
python tools/video-options/benchmark_maps.py --all
```

The default executable is the shared installation's `OpenH3M.exe`. `--exe` may
select a developer build while retaining the same shared game data and content.
An installed executable must contain the benchmark hooks before using the default.
Use `--seconds` for the measurement duration (default 10 seconds per point).
`--watchdog` bounds each child process (default 210 seconds).
Use `--start-index N` to choose a different first authored spawn, followed by
two spatially separated candidates. `--multiplayer-starts-only` excludes scenario
player-start records and selects placed multiplayer spawn markers instead.
These options allow retrying unsafe starts without modifying installed maps.

Map selection runs through process-local replay of the native menu route. No
host input is generated. The runner owns and terminates only its child process.
Live player input is excluded during replay. Installed caches are read-only.

Three spatially separated authored starts are selected deterministically from
the installed scenario or saved Forge layout. The two empty Forge canvases have
only one authored start; two nearby provisional benchmark positions require
native collision/position and visual confirmation. Native code verifies the map and
layout, teleports the player, settles for three seconds, captures the native
frame, warms for two seconds, then measures new guest outputs over wall time.
Repeated display presentations are excluded. Per-frame diagnostic logging is
disabled during measurement. Camera position and player identity are checked;
drift or respawn invalidates the sample. Screenshots require human/agent visual
review before a run is accepted, not just checking that image files exist.

Outputs live in `.local/map-benchmarks/<timestamp>/`: command/executable hash,
selected spawn coordinates, logs, native captures, JSON and CSV. The machine
manifest is `.local/map-benchmarks/machine.json`. FPS describes this machine and
viewpoint; it is not a prediction of older-machine performance or GPU-only time.

## Evidence and limitations

The original host-only implementation remained at 30 FPS and was insufficient.
The initial Cold Storage positional pilot measured 46.89, 46.67 and 46.70 FPS,
but it did not verify authored camera facing. Those measurements are superseded
for the final report. A process-local input feedback correction now aligns the
native camera before measurement. Corrected Avalanche results are 46.65, 38.03
and 43.93 FPS, with all three positions, directions and captures checked.
The shared installation was updated on 2026-11-05; deployment hashes and rollback
binaries are in `.local/map-benchmarks/deploy-20261105-064843`.
A non-developer build compiled successfully and excluded benchmark/unlock markers;
evidence is `.local/map-benchmarks/release-exclusion.json`.

Earlier OFF/ON/OFF gameplay testing measured 46.77 new outputs/sec ON and 29.91
OFF. Simulation advanced faster ON, as now explicitly accepted by the user.
Evidence: `.local/developer-framerate/test-20261105-055914` and
`.local/map-benchmarks/20261105-062448/chillout`. No system-link validation.

The SDK instrumentation patch is `developer-framerate-sdk.patch`, applied to
the existing pacing-enabled SDK baseline. Only successful new guest output
refreshes increment the measured counter.
