# Warlock conversion: working checkpoint

This preserves the map-side conversion process that produced recognizable Warlock
in the unchanged OpenH3M runtime. The owner tested solo and reported good collision
and visuals on 2026-10-18. This is a checkpoint, not a complete general converter.
No game assets, maps, screenshots, runtime binaries, or generated logs are included.

## Restore the working layout

The snapshot deliberately preserves the exact scripts used for the successful map.
Copy snapshot/tools to <disc-root>/.local/tools and snapshot/reference to
<disc-root>/.local/reference; copy snapshot/Run-Warlock.cmd to <disc-root>.
Use an explicitly authorized project directory as disc-root. The current directory
is C:\X360\ISOs\H3M. Python paths derive this root from .local/tools.
Install requirements using a project-local environment and pip cache. Use python -B
and run from disc-root so no bytecode/output escapes the project.

Private prerequisites (not distributed):
- Original Mythic disc data, including default.xex and maps/lockout.map.
- Earlier conversion seed at D:/Programming/GitHub/H3M/game/maps/lockout.map.
  SHA256: a2cf1f69bef10728b380848a2217bb69c2779797929a03beff17c8e64012d558
- MCC Warlock workshop map at
  D:/SteamLibrary/steamapps/workshop/content/976730/2977651586/maps/warlock.map.
- Unchanged runtime at D:/Programming/GitHub/H3M/OpenH3M.exe for manual testing.

These historical paths are hardcoded in the snapshot. Update them for another
installation. The initial seed creation process was lost in the earlier chat;
this checkpoint reconstructs its relocation and material stages, not that seed.
Create .local/reports and .local/candidate before running the pipeline:

    python -B .local/tools/audit_mcc_visual.py
    python -B .local/tools/import_materials.py
    python -B .local/tools/diagnose_loading.py

import_materials invokes relocation first and replaces the candidate in place.
Close OpenH3M before rebuilding. Never use a stock map hardlink as the candidate.
The existing test-game layout uses original disc assets and a hardlink only to the
separate generated candidate. A fresh installation still needs this layout built.
The launcher expects .local/test-game/maps/lockout.map and uses Blackout's slot:
Custom Games > Blackout > Slayer.

Optional focused checks: check_texture_encoding.py, compare_geometry.py and
compare_render_buffers.py. trace_loading.py is an optional Windows child-process
debugger for a matching runtime build. It restores temporary breakpoints, logs
loading failures, and uses a bounded watchdog. --capture uses native game capture;
no desktop capture or OS input is used. Do not assume its fixed addresses or input
script support work on another runtime build.

## Confirmed checkpoint and limits

Final candidate SHA256:
499f0516e016524f7f8a98ca580e4acb66c2b5d58403a5c755e4ed8f23de4279
Size: 210231296 bytes. Primary positions/UVs and index buffers matched source;
packed basis vectors matched within 0.005. Native bounded load observed five hash
passes, zero failures, and no fatal exception. Solo visual/collision acceptance
comes from the owner. Multiplayer, audio, game modes and system link are not verified.

Implemented: fixed retail tag-memory boundary, schema pointer relocation, page and
header hashes, required soft surfaces, Xbox texture tiling/endian conversion,
source diffuse/alpha materials, camera exposure and authored Slayer spawn positions.

Remaining code completion:
- Reconstruct a reproducible source-to-retail geometry/resource pipeline without
  the unavailable earlier seed generator; configurable inputs and one entry point.
- Inventory and handle omitted material slots, normal/detail maps, terrain blending,
  remaining hologram approximations and mip/format support as required by this map.
- Audit and convert remaining scenario objects, game-mode placements, sky/atmosphere,
  decals, lighting and audio dependencies with explicit unsupported-item reporting.
- Make generation transactional, document deployment, and bound/clean generated
  data. Use focused structural checks and at most a minimal native smoke test.
- Do not change OpenH3M or introduce runtime workarounds. Leave exhaustive gameplay
  testing to the owner; do not claim system-link compatibility without evidence.

## Reference provenance

reference/plugins and reference/mcc contain Halo3/Halo3MCC XML schemas from
https://github.com/XboxChaos/Assembly (dev branch); see Assembly-LICENSE.
The tiling algebra is based on xenia-project/xenia texture_address.h; see
xenia-LICENSE. xexlib.py originated in this repository's halo3mp/tools/xexlib.py.
The private source map is Neckzilla's Warlock workshop item 2977651586.
