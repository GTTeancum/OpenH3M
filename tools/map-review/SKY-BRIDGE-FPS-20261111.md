# Sky Bridge unlocked FPS — 2026-11-11

Five distinct views, 30 seconds each, using `--fpsunlock`. Simulation timing unchanged. User loaded the map; the native benchmark positioned the player and captured each view. All five accepted captures were individually inspected. The initial exterior-height failure is excluded and retained in results.json.

| View | FPS | Sampled total GPU 3D usage |
|---|---:|---:|
| Terminal 02 interior | 28.66 | 94.8% |
| Terminal 01 interior | 31.79 | 94.1% |
| Exterior wall retry | 42.91 | 98.7% |
| Outdoor courtyard | 32.00 | 97.7% |
| Interior doorway looking outdoors | 35.37 | 94.9% |

GPU figures are means of 2–3 Windows 3D-engine samples within each actual measurement window, including other applications. Xemu and XboxPcApp remained running. These are shared-load observations, not isolated performance estimates. Video-codec usage is not included. No Xbox 360 hardware result is implied.

Native benchmark position checks passed for all five accepted samples. Installed maps and runtime binaries were not modified. The game remains open with benchmark control released.

![Terminal 02 interior](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/map-benchmarks/sky-bridge-manual-20261111/spawn-2.png)

![Terminal 01 interior](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/map-benchmarks/sky-bridge-manual-20261111/spawn-3.png)

![Exterior wall retry](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/map-benchmarks/sky-bridge-manual-20261111-second/spawn-1.png)

![Outdoor courtyard](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/map-benchmarks/sky-bridge-manual-20261111-second/spawn-2.png)

![Interior doorway looking outdoors](C:/X360/ISOs/H3M/.local/OpenH3M-source/.local/map-benchmarks/sky-bridge-manual-20261111-second/spawn-3.png)
