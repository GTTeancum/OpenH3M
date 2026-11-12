# Native PC video menu — 2026-11-05

Settings > Video now extends Halo 3's native Display screen. The rejected ImGui
panel has been removed from this flow. The screen uses the original Halo fonts,
blue pane, orange selection bar, row animations, horizontal value spinners and
controller prompts. Ten rows are visible; the list scrolls to the remaining
settings and Apply/Cancel/Restore actions.

The extension changes the loaded screen definition in guest memory, scoped to
the native Display screen. It creates a separate native datasource and spinner
for each PC option. Original disc tags and map caches are not rewritten.
Brightness retains its original game behavior. Its illustration is removed to
make room for the longer settings list, and contextual help sits below it.

## Controls and behavior

- Select an option, change its value with left/right, and confirm or cancel using
  the existing Halo menu controls. Native keyboard/controller mapping applies.
- Resolution: game default, 1280 x 720, 1920 x 1080, 2560 x 1440, 3840 x 2160.
- Windowed/fullscreen; texture quality; anisotropic filtering through 16x.
- Shadows, object detail, decoration/effect distance, water quality.
- Extra FXAA (off/normal/strong); internal render scale 1x/2x/3x.
- Performance/Balanced/Original presets preserve resolution, display mode,
  render scale and extra anti-aliasing.
- PC edits remain staged until Apply Changes. Cancel Changes restores saved
  values; Restore Defaults stages defaults. Leaving and reopening discards
  unsaved drafts. Brightness remains the original game's separate live control.
- Apply saves through atomic replacement, preserving unrelated configuration.
  Resolution, internal scale and extra FXAA require restarting the game.
- FPS unlock, simulation timing and title-bar behavior are unchanged.

## Verification and evidence

Build: `work/video-options/native-menu-build.log`.
Backend checks: `work/video-options/native-backend-check/` plus the
`pc_video_settings_check` executable. Checks cover drafts/cancel, presets,
persistence, invalid values, failed saves, defaults, resolution axes and timing
isolation.

Game-native captures from isolated, process-local replay tests:

- `work/video-options/native-menu-05/menu_068000ms.png`: native resolution
  spinner displaying 1280 x 720, Confirm/Cancel prompts.
- `work/video-options/native-menu-06/menu_076000ms.png`: scrolling reaches Apply.
- `work/video-options/native-menu-06/menu_080000ms.png`: successful save message.
- `work/video-options/native-menu-06/menu_089000ms.png`: closing/reopening keeps
  the saved resolution. `saved-settings.toml` records that actual UI save.
- `work/video-options/native-menu-07/`: final preset/cancel/defaults action run.

These are actual guest-rendered frames, inspected directly, not mockups or
software renders of a separate panel. Tests use application-native capture and
process-contained input; no host desktop input or desktop capture is used.

Expanded verification is recorded in [VALIDATION-2026-11-05.md](VALIDATION-2026-11-05.md). Every individual option value was exercised, including restarted resolution/scale/AA, native fullscreen transitions and gameplay pause-menu return. This is not a Cartesian test of every combination or every map. The map-corrections goal remains paused.

## Deployment

The tested executable was deployed to `C:/X360/ISOs/H3M/OpenH3M.exe` on
2026-11-05. Its SHA-256 matches the final isolated test binary:
`afa0ee550b85c10c538714332c1b5ab087ae2372c76abb6c860b0a010f35dc42`.
The six installed runtime libraries already matched the build. Only the EXE
was replaced; bootstrap, user configuration and map caches were unchanged.
Backup and before/after hashes:
`.local/deployments/native-video-menu-20261105/manifest.json`.

The final action run visually confirms cancelling a preset choice preserves
Custom; confirming Balanced updates its dependent rows; Restore Defaults and
Cancel Changes display their correct messages; closing/reopening preserves the
saved state. Runtime artifacts and config for that run reside under
`work/video-options/native-menu-07/`, including its own copied executable/DLLs.

## Resolution behavior correction

Explicit legacy window dimensions no longer override the resolution selection.
Oversized windowed output fits within the current desktop; fullscreen is borderless
at desktop size. Internal render scale changes scene detail separately. The native
resolution help explains this behavior. Validation launchers serialize game instances.

## Verified corrective deployment

The expanded verification and corrections supersede the limited initial deployment
above. EXE plus six matching libraries deployed 2026-11-05 after the final native
menu check. EXE SHA-256:
`547243ad9445afe3b3c8d4c7777a9d020a0df5e2d72cfcbbd1c9f1b8f8b03318`.
Backup/hash manifest: `.local/deployments/video-verified-20261105/manifest.json`.
Installed configuration hashes are unchanged; no maps/test fixtures deployed.
