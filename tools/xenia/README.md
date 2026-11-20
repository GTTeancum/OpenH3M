# Xenia Canary test setup

Local, untracked install for loading this project's custom maps in an emulator. Set up
2026-11-19. Nothing here is a console or performance result.

## Layout (all under `.local/xenia-canary`, ignored by Git)

- `app/` — official Xenia Canary Windows build `54386cb` (2026-11-19) from
  https://github.com/xenia-canary/xenia-canary/releases, archive SHA-256
  `d1292c3cc3970099b444b00b40ee6c2857c504cefa839a9a291de80046db8c5f`. `portable.txt` keeps
  config, cache, profiles and content inside `app/`.
- `app/patches/4D5307E6 - Halo 3 Mythic (custom maps).patch.toml` — the five edits of
  `tools/warlock-conversion/snapshot/tools/patch_dlc_xex.py`, applied in memory. Keyed to
  module hash `3FE73A3A9C3BD684` (original Mythic `default.xex`, SHA-256 `18816c1d…`). A disc
  image with a different executable will not get the patch and will reject the custom maps.
- `app/content/0000000000000000/4D5307E6/00000002/<Map_Name>/` — custom maps as extracted
  package folders (map, mapinfo and preview files), one folder per map. Xenia reads folders
  here, not raw LIVE container files; use `tools/map-review/speed-review/extract_stfs.py`.
- `iso/` — put the Halo 3 Mythic (ODST disc 2) image here.
- `game-local/` — hard links to the extracted disc files already on this machine.
- `Run-Xenia.cmd` — launches the first `.iso` in `iso/`, otherwise `game-local/default.xex`.

## Checked

Launching `game-local/default.xex`: title bar shows Halo 3, title ID 4D5307E6, "Patches
Applied"; the game reaches the Mythic "Not signed in" menu prompt (window capture
`.local/xenia-canary/boot-check.png`).

## Not checked

Whether the custom maps appear in Custom Games or load; any gameplay; an ISO launch.

## Driving Xenia without the desktop

`.local/xenia-canary/xe.ps1` starts Xenia minimized, posts key messages to its window handle
and captures the window with `PrintWindow`. Captures work. Posted keys do not: Xenia ignores
keyboard input unless its window has focus (tested 2026-11-19: a posted Down did not move the
menu selection). The owner does not allow taking focus, moving the cursor or sending global
input, so Xenia cannot currently be driven unattended. The test maps were not reached.

## PC port instead of Xenia (2026-11-19)

`tools/map-review/speed-review/run_pc_port.py` loads one package in the PC port on a separate,
never-displayed Windows desktop, muted, driven only by the game's own timed input script, with
the game's own guest-output captures. Nothing reaches the interactive desktop.

- Reactor test build (`Reactor_20261119`) and Sky Bridge test build (`Sky_Bridge_20261119`)
  both install, appear in the Custom Games map list and reach Slayer gameplay; captures in
  `.local/pc-port/reactor-02` and `.local/pc-port/sky-bridge-01` show textured in-game frames.
  One fixed spawn view each, about a minute of play; no traversal, no frame-rate measurement.
- The installer used to reject any package not named by its 40-digit content ID.
  `halo3mp/src/halo3mp_app.h` now accepts any extensionless name of letters, digits, `_` or
  `-` up to 42 characters. Rebuilt incrementally in the earlier workspace's build tree
  (`C:/X360/ISOs/H3M/.local/OpenH3M-source/work/rexglue-sdk/out/pacing-release`, target
  `halo3mp`), whose copy of that source file received the identical edit; the pre-edit copy is
  `.local/pc-port/halo3mp_app.h.before-name-fix`.
