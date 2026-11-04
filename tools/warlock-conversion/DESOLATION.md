# Desolation conversion

Active goal from 2026-11-04. The user moved Sky Bridge to pending final review
and designated the Desolation download as the next source. Downloads is read-only;
all extraction, analysis, conversion, builds and tests stay in this repository.

## Source and attribution

Requested map lineage: Desolation, Halo 2. The supplied artifact is an existing
Halo 3 MCC port, not an original Halo 2 cache. Its exact original-geometry
provenance still needs tracing; the filename alone does not establish fidelity.

Source package: MythicJaqui's
[Halo 3 Desolation Map Port (H3MO)](https://www.nexusmods.com/halothemasterchiefcollection/mods/1897),
Nexus mod 1897, version 1.0, updated 2022-05-18. The author page identifies it as a
Waterfall replacement in a larger multiplayer overhaul, and credits Krevil for
the Halo Infinite HUD and Mackaye99 for the MA5K model. Page checked 2026-11-04.
This project's work is the subsequent Xbox 360/OpenH3M adaptation; upstream port
authorship remains MythicJaqui's. Original individual map authorship is not
established by the package page.

The user's latest instruction selects this downloaded package as the current
starting point, superseding the old deferral/source-acquisition state. Original
Xbox 360 Halo 3 stock-asset reuse and gameplay rules remain binding. In particular,
the overhaul's custom HUD/weapons are not approval to replace stock Halo 3 assets.
No publication or asset upload is part of this preflight.

## Verified input

- Archive: `C:/Users/smmel/Downloads/Halo 3 Desolation Map Port (H3MO)-1897-1-0-1652899630.rar`
- Archive size: 1251575010 bytes.
- Archive SHA256: `414189e01acc187fd51d2c3e22ef05b92176ca9382bc4f4d8b6b1af944800208`.
- Members: `halo3/maps/s3d_waterfall.map`, `halo3/fmod/pc/sfx.fsb` and
  `halo3/fmod/pc/sfx.fsb.info`, under the `Halo 3 Desolation` directory.
- Extracted map: `work/desolation/source/Halo 3 Desolation/halo3/maps/s3d_waterfall.map`.
- Map size: 664530944 bytes.
- Map SHA256: `aaf0129aab5aee63a52cacac27657cd85ac7c810b0768b0e386c16e76543333f`.
- Little-endian `daeh` header, version 13; header build date 2022-04-20.
- Existing MCC reader parses 12,000 tags. Scenario 8 and BSP 10246 both have the
  path `levels\multi\derelict\derelict`.

The map and audio index were extracted using the installed Windows tar tool.
The large `sfx.fsb` bank remains in the original archive until its dependencies
are needed. No source files, installed maps or runtime binaries were changed.

## Initial checks and next work

`work/desolation/source-preflight.json` contains header identity, hashes, tag
counts and relevant names. `work/desolation/collision-preflight.json` passes the
existing collision-format check: one small collision BSP, no large collision
BSPs, no collision instances and no Havok blocks. This is format evidence only,
not a playable candidate or proof of memory/rendering/performance acceptance.

Next: trace scenario geometry, resource pages, materials, effects, lighting,
audio and gameplay dependencies; audit stock Halo 3 donors and shared resources;
adapt through the established MCC-to-H3 pipeline; then validate a private native
candidate before preparing LIVE DLC and final review. Preserve existing maps.
Unattended native runs use process-local input and a maximum 180-second watchdog;
visual proof uses the game's own captures. No desktop input or capture app.
