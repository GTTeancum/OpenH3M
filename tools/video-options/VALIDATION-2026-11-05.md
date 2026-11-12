# Native video settings validation

Status: every individual menu value exercised; the completed native captures were inspected. The two resolution defects found were corrected and retested. Tested binaries deployed with verified hashes. Coverage limits are stated below.

## Corrections found during validation

- Resolution initially stayed at 1280x720 because explicit application defaults
  overrode the chosen preset. Application defaults now defer to resolution, and
  Apply clears legacy saved dimension overrides. Backend regression passed;
  corrected 4K run produced a 3840x2160 application surface.
- That 4K window exceeded the user's 1080p desktop and visibly cropped the game.
  A complete off-screen backbuffer is insufficient evidence for the visible
  window. Window creation now fits oversized windows within the display's usable
  bounds while preserving aspect ratio. Serial runtime retest passed: 4K selection
  fits a 1765x993 application surface on the 1920x1080 desktop. Both native captures
  were inspected, and the user's desktop screenshot independently shows the full
  window, HUD and scene visible. This does not mean 4K internal rendering.
- User requires ONE game instance. Overlapping runners and games were stopped.
  Both validation launchers now share an exclusive process mutex and refuse to
  launch while any Halo game process exists. All subsequent testing is serial.
  An intentional second launch was refused; only one game process remained.
- The interrupted `res-2160` and `effects-curve` runs must not be counted as
  completed passes. Fresh serial runs provide the replacement evidence.

Evidence root: `work/video-options/validation-20261105/` in this repository.
All runs use private binaries, configurations, profiles and caches. Input replay
is contained in the target game process. Captures come from its own renderer.
Timed watchdog termination is intentional and is recorded separately from crashes.
The isolated runs did not modify installed maps or settings. After verification, the tested executable and six matching libraries were deployed; configuration hashes remained unchanged.

## Inspected results

| Control | Values exercised | Observed result |
|---|---|---|
| Brightness | Lower, Low, Normal, High, Higher | All five menu captures inspected in order; image brightness changes progressively. Cancel returns to Normal. |
| Quality preset | Performance, Balanced, Original | All three native choices display correctly. Gameplay textures and shadows change with presets; Original and Defaults restore detailed textures and the central vehicle shadow. |
| Resolution | Game default, 720p, 1080p, 1440p, 2160p | All five restarted runs inspected (guest and output captures). Default/720p use 1280x720; larger presets fit 1765x993 on this desktop. All retain the complete scene/HUD; 1x guest rendering remains 1152x640. |
| Display mode | Windowed, Fullscreen | Actual native-menu Apply changes application dimensions from 1280x720 to 1920x1080 and back. Both resulting menu captures inspected. Independent gameplay transition retains scene/HUD and firing/reloading. |
| Texture quality | Original, Medium, Low | Eligible weapon/world textures visibly lose detail progressively; HUD and geometry remain intact. |
| Filtering | Game default, Off, 2x, 4x, 8x, 16x | All native choices inspected. Oblique sand changes between Off and anisotropic filtering; high settings have subtler differences in this view. |
| Shadows | Original, Medium, Low | Central test vehicle shadow weakens/disappears; unrelated geometry remains. Original preset/defaults restore it. Native adaptive shadow allocation also varies over time. |
| Object detail | Original, Medium, Low | Distant stock rifle meshes switch LOD; nearby weapon and world geometry remain. |
| Decoration distance | Original, Medium, Near | All native choices and eight distance-run images inspected. Far vegetation reduces at Near and restores at Original. Native distance scales are 1, 0.75, 0.5. |
| Cosmetic effect distance | Original, Medium, Near | All three levels and restoration rendered with working firing effects. Actual native fade-function probes of live effect metadata confirm nearer fading: effect 4007529832/system 4 at distance 5 returns 1, 0.444444, 0 for Original/Medium/Near. This is native calculation evidence plus close-effect images, not a visual distant-effect comparison. |
| Water | Original, Reduced, Basic | Focused nearshore captures inspected for all levels/restoration. Native feature flags are (1,1), (0,1), (0,0); Basic switches from the full water draw to the basic draw, then Original restores it. Surface, shore and HUD remain intact. Bullet ripples are not independently isolated by these shots. |
| Extra anti-aliasing | Off, FXAA, Strong FXAA | Off, FXAA and Strong FXAA restarted; guest and output captures inspected individually. FXAA smooths silhouettes and HUD edges; Strong is softer. Scene/HUD remain intact. |
| Internal render scale | 1x, 2x, 3x | Restarted 1x/2x/3x produce 1152x640, 2304x1280 and 3456x1920 guest buffers. Both native captures for each inspected: sharper world/weapon edges at higher scales, intact scene/HUD and 1280x720 output. |

All 47 `menu-values` captures were inspected individually in chronological order.
All 14 `surface`, eight `shadows`, and six `water` captures were also inspected.
Floating objects in the surface/shadow scenes are deliberate isolated stock-asset
test placements used to expose LOD and shadow transitions.

Backend tests exercise Apply, live flag value, persisted reload and restoration
for all 37 PC choices, plus invalid values, failed saves, presets, defaults,
cancel, render-scale axes and timing isolation. These tests passed; they are
supporting evidence, not substitutes for rendered/functional verification.

## Final checks and coverage limits

- All resolution, internal-scale and AA restart cases are complete.
- Active effect fade-curve comparison complete: 553 evaluations, 13 differing distance comparisons shared across all three levels. Full results: `effects-curve-serial/effect-curve-comparison.json`. Four captures inspected individually; Original restores native distance scale/inverse to 1.
- Gameplay pause-menu access and return to movement/firing passed: all six pause
  captures inspected. Video screen opens from in-game Settings, exits to gameplay,
  movement changes the camera position, and firing consumes three rounds (32 to 29).
  Halo's in-game screen retains Subtitles as its original first row, whereas the
  main-menu screen retains Brightness.
- Completed logs contain no matches for device removed/hung, fatal/unhandled exception, failed creation or out-of-memory errors. Intentional watchdog exits are recorded, not counted as crashes.
- Coverage is every individual value, not every combination, map, graphics card or long-duration session. High anisotropic levels have subtle visual differences in this view; their backend values and sampler mapping were checked. No claim of exhaustive system-link or audio regression testing is made.

Final `menu-resolution-final` check passed. All three captures were inspected: native resolution help fits in two readable lines; actual menu Apply switches 1765x993 window -> 1920x1080 fullscreen -> 1765x993 window without clipping or a hang.

Deployment: `.local/deployments/video-verified-20261105/manifest.json` records backups and before/after hashes for the executable and six libraries. Installed EXE SHA-256: `547243ad9445afe3b3c8d4c7777a9d020a0df5e2d72cfcbbd1c9f1b8f8b03318`. Maps, bootstrap and saved configuration were not modified. Test instances have exited.
