# Lockout conversion

Source port/remake author: Neckzilla, [Lockout for Halo 3 MCC](https://steamcommunity.com/sharedfiles/filedetails/?id=2898979693).
Original map: Lockout, Halo 2. See MAP-CREDITS.md for attribution scope.

## Correction candidate 02 (2026-10-25)

Restores supported native emissive shaders and adds +1 EV to this map's camera
target/bounds. Four audited surfaces use native unit detail-normal strength
instead of their MCC-only 1.5x/2x/5x amplification; build report lists these
explicit appearance corrections. Textures and emission remain present.

Run `20261025-180331-24336` completed at 150 seconds. Both 115/135-second native
captures inspected: indoor room, lit wall details and geometry are visible;
movement ends at a wall, so this does not verify outdoor traversal. Timing:
median 33.36 ms, p95 33.73 ms, maximum 50.65 ms, no >100 ms stalls, excluding
capture intervals. Candidate not deployed. Remaining source emission gaps are
listed in build-02.json and require review before declaring all materials complete.

Source: Halo 3 MCC Workshop 2898979693, `maps/lockoutfix.map`.
Its metadata identifies the classic snowy Halo 2 layout with updated Halo 3
visuals. The alternative Halo Online pack source is the lava-themed remake;
it was investigated but is not the selected source. Assembly basis is original
Last Resort; independent DLC identity is `lockout_classic`, map ID 1738.

Build command: `build-lockout.ps1`. Installed after bounded native gameplay,
Forge exterior and menu/preview checks. The full Forge palette is retained.

Original-disc Isolation's `flood_sack_destroyed_spec` bitmap has stripped
resource data. The only reference in its shader is the editor Parameters
array, not the compiled texture table. Native import now clears only such
stripped editor bitmap references and records each occurrence; compiled
runtime references still require intact data. Audit:
`work/lockout/flood-spec-references.json`.

The dripping-water particle has no exact native template. Original-disc Armory
has the same parameter order, blending, fog and alpha handling with black-point
support enabled. All source emitters referencing this particle were checked:
their black-point function is a constant zero with no output modifier. The
adapter rejects any other function, value or missing emitter evidence. Audits:
`work/lockout/rain-black-point.json` and `particle-template-donors.json`.

Spawn Data now preserves authored heights and nested spawn zones/influences,
relocating the three blocks past the retail format's additional reserved bytes.
No original gameplay or engine format limits are changed.

Installed 2026-10-25: `work/lockout/promotion-01.json` records byte-verified
promotion of the 10-map, 70-file LIVE bundle. Map ID 1738, 183,676,928 bytes
(175.17 MiB). Existing maps and saved-layout profiles are preserved.

Native evidence:
- `.local/loading-traces/20261025-061838-20772`: menu preview and indoor gameplay.
- `.local/loading-traces/20261025-063842-10068`: Forge exterior courtyard,
  bridges, surrounding structures and pickups. A cliff overhang partly
  occludes the overview; this is a bounded visual check, not full traversal.
- Both completed to their watchdog. Function integrity checks passed.
  The first run's late third capture was beyond its watchdog and was not used.

The process-local `--forge-overview-check` route now accounts for Lockout's
indoor spawn: left strafe through the audited doorway, ascend, then turn toward
the courtyard. Generic forward/ascent hits the ceiling. Ray audit:
`work/lockout/exterior-ray-routes.json` (main BSP only).
Audio, all Forge objects and real-console memory/networking remain unverified.

Repeat native exterior check (PowerShell, repository cwd; TEMP/TMP inside
`.local/build-temp`):
```powershell
& 'C:/Users/smmel/AppData/Local/Programs/Python/Python312/python.exe' -B tools/warlock-conversion/snapshot/tools/trace_loading.py --project C:/X360/ISOs/H3M --exe C:/X360/ISOs/H3M/OpenH3M.exe --expected-exe-sha256 ef03724a0fca2aec96a2e7f87ab56a2c2341557659cefbb7799eb2306e0beb58 --cache-root work/dlc/cache --game C:/X360/ISOs/H3M --dlc-map lockout_classic --dlc-installed-root work/dlc/installed-current --forge-overview-check --capture --capture-times-ms 140000 --sample-observer --seconds 180
```

### Pending correction candidate 03

The flickering circular light now uses original-disc Descent's detail-emission
shader with its native neutral default_detail input. Surface shading, parallax,
reflections and the source color-flicker animation are retained. Written-cache
readback verifies parameters and animation routing; targeted visual verification
is still pending. Candidate size: 191,115,264 bytes. Not deployed yet.

Origin: Halo 2 Lockout. Source H3 MCC conversion: Neckzilla's
[Lockout](https://steamcommunity.com/sharedfiles/filedetails/?id=2898979693).

### Candidate 05: world illumination and native check

All reported missing world emission is restored. The center-platform shader
uses a composed normal texture (a filtering approximation); three other panels
use their original Halo 3 Chill/Guardian two-lobe lighting parameters while
retaining authored textures, colors, parallax and glow. This deliberately
replaces the source port's single-lobe specular model on those three surfaces.

Written-cache checks preserve the animation curves. Native run
20261025-192919-36256 shows the lit room and exterior glowing doorway after
walking out; individual animation speeds were not visually measured. Current
candidate is 191,774,720 bytes. Shared autoturret emission remains pending.
Source: Halo 2 Lockout, H3 MCC conversion by Neckzilla (linked above).
