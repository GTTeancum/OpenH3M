# Frame pacing investigation

Status: active; no smoothness fix has been accepted or applied to the normal
launcher. The user reports uneven motion despite the 30 FPS counter. The only
hardware tested is their Beelink SER8. See `../../TODO.MD` for broader optimization
and the requested quality-options menu.

## Capture tools

`snapshot/tools/check_frame_pacing.py` runs the unchanged installed executable
with the existing process-local route to Cold Storage/Prisoner. It has a
165-second watchdog, uses the shared cache, and keeps logs, saves and temporary
files under the project's `.local/pacing` directory. `--stock` reads original
disc maps directly without replacing the installed conversion. `--capture`
requests one native guest-output PNG; it does not capture or drive the desktop.

`--native-timing` uses `native_frame_timing.py` to locate the existing completed
guest-frame counter. One debugger breakpoint at the exported presenter entry
discovers its instance before measurement; the instruction and instruction
pointer are restored and the debugger detaches. Measurement subsequently only
reads the counter roughly every 1ms. No engine files, guest code or game data
are modified. The known counter instruction is checked before use; unsupported
layouts fail. This is not a per-frame debugger breakpoint or screenshot loop.

Timestamps use Windows QueryPerformanceCounter through `time.perf_counter`.
This Python installation's `time.monotonic` uses 15.625ms GetTickCount64; the first
native timing trial (`20261020-172005-baseline`) is therefore invalid for detailed
timing analysis and must not be used to establish a fix.

The optional presentation measurements use the official standalone
[PresentMon 2.6.0](https://github.com/GameTechDev/PresentMon/releases/tag/v2.6.0)
console executable at `.local/tools/PresentMon-2.6.0-x64.exe`, PID-filtered to the
owned game with input tracking disabled. There is no overlay, hotkey, screen
takeover or persistent system setting. Window occlusion changes display delivery;
the native counter is needed to measure game-frame production independently.
PresentMon is a private diagnostic dependency, not part of the engine or Git.

From the conversion repository:

```powershell
python -B tools/warlock-conversion/snapshot/tools/check_frame_pacing.py --project ../.. --exe D:/Programming/GitHub/H3M/OpenH3M.exe --mode baseline --native-timing
python -B tools/warlock-conversion/snapshot/tools/summarize_frame_pacing.py ../pacing/RUN-DIRECTORY
```

The summary uses settled gameplay from 125 seconds onward. It reports skipped
counter increments and polling gaps rather than concealing sampling uncertainty.
Native timing by itself does not prove visual correctness, simulation speed or
smooth display delivery. Inspect native output and compare equivalent routes.

## Evidence so far

- Prisoner is candidate 10, SHA256
  `c14c7d8fe5f810bdec1873e620caadd11803702d6c120bee4de053456609e460`.
- `20261020-171311-baseline`: inspected native PNG confirms Prisoner gameplay.
  Host presentations occur about 90 times/sec while new game output is about
  30/sec. Host presents alone are not a measure of unique game frames.
- `20261020-171635-no-tearing`: native gameplay image inspected; disabling
  `d3d12_allow_variable_refresh_rate_and_tearing` did not establish a pacing fix.
  Display results were affected by composed presentation/occlusion.
- `20261020-172315-baseline`: first valid high-resolution native capture.
  898 settled-gameplay intervals, zero skipped frames, mean 33.390ms,
  standard deviation 14.924ms, p05 14.305ms, p50 33.176ms, p95 51.969ms.
  Maximum observed polling gap was 25.363ms; inspect raw polling gaps when
  interpreting individual outliers. Hundreds of short/long intervals motivate
  the investigation, rather than a single slow sample.
- `20261020-172642-ui-thread`: `host_present_from_non_ui_thread=false` did
  not resolve the irregularity: 898 intervals, mean 33.314ms, standard deviation
  14.385ms, p05 14.301ms, p95 51.952ms, zero skipped frames, maximum observation
  gap 4.364ms. No production default has changed. The setting is documented in the
  [runtime presenter source](https://github.com/rexglue/rexglue-sdk/blob/main/src/ui/presenter.cpp).
- The harness also supports an `honor-timers` experiment: disable the owned
  child's `PROCESS_POWER_THROTTLING_IGNORE_TIMER_RESOLUTION` policy through
  [SetProcessInformation](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setprocessinformation).
  This honors existing timer requests even when Windows occludes the game. It
  does not request a global timer change, change game speed, or persist beyond
  the process. This experiment has not yet established a fix.

Remaining acceptance: compare native timings with stock Cold Storage, identify
a repeatable improvement without changing the engine or game simulation, inspect
the resulting native output, and document/deploy only the validated settings.
