# Installed conversion corrections — 2026-10-25

Deployed to `C:/X360/ISOs/H3M/OpenH3M.exe`, using the shared installation.
The executable is unchanged; the tested GPU runtime, corrected maps and merged
shader cache are installed. No extra game build or launcher was introduced.

## Maps and source credits

| Map | Original | H3 MCC conversion source/author | Deployed candidate |
|---|---|---|---|
| Battle Canyon | Halo Reach Anniversary | [Remember Reach, Ryno](https://steamcommunity.com/sharedfiles/filedetails/?id=3575686579) | Battle06 |
| Rodentia | H2 custom Rat Race remake; Halo CE lineage | [H2 Map Pack, Blackandfan](https://steamcommunity.com/sharedfiles/filedetails/?id=3500400217); original remake author unverified | Rodentia05 |
| Lockout | Halo 2 | [Lockout, Neckzilla](https://steamcommunity.com/sharedfiles/filedetails/?id=2898979693) | Lockout06 |
| 3longation | Halo 2 Elongation | [3longation, TBeezie](https://steamcommunity.com/sharedfiles/filedetails/?id=3618057049) | Elongation06 |
| Sanctuary | Halo 2 | [Sanctuary, Neckzilla](https://steamcommunity.com/sharedfiles/filedetails/?id=2898920291) | Sanctuary04 |

This project's work is the Xbox 360/OpenH3M adaptation and corrections, not
authorship of the original maps or source ports.

## Changes and verification

- Per-map brightness adjustments and restored missing material illumination.
  Written-cache checks cover texture/constants/animation bindings; bounded
  native captures cover representative interiors/exteriors. Native shader
  approximations, including Lockout normals/specular and shared autoturret
  highlights, remain documented in conversion reports; not every palette-only
  object or animation was individually viewed.
- 3longation's visible conveyor animation and moving crates were checked in
  paired native captures, not inferred solely from conveyor forces.
- Battle Canyon flare occlusion was checked against a solid wall with the
  corrected GPU runtime. The gravlift's translucent animated vapor was checked
  in paired captures.
- Battle Canyon's jagged cliff overlays were traced through GPU pixel history
  to simplified collision geometry. Battle06 preserves original polygons under
  authored decals, leaving visible geometry unchanged. The same native seam
  view now shows continuous dirt/grass overlays. Its 32,351 collision surfaces,
  visibility tree and physics keys pass original-format checks. All 12,257
  protected polygons retain exact coordinates and winding. Collision elsewhere
  is more simplified; the bounded test is not an exhaustive collision survey.
- The merged cache contains 943 shaders and 1,207 pipeline records, with no
  conflicting records or incomplete tails. Existing presentation pacing remains.
  The packaged native run has a 33.82 ms p95 and 50.40 ms maximum after gameplay
  was established (elapsed 125–180 seconds, capture window excluded). A separate
  3.02-second load-to-gameplay gap remains in the complete trace and is explicitly
  retained in the report. These are host observations on the current PC, not
  guaranteed performance on other hardware or Xbox 360 measurements.

## Release evidence

- `work/installed-map-corrections/live-release.json`: LIVE container
  `E3C216511E5A0ED8A2E37F70BC65E407C481C510`, 1,740,374,016 bytes,
  SHA256 `cf26c25e8d16d1082c9770fe51beeb6d23fb0f863875520ad90af746151c5714`.
  Header/data/hash-tree integrity passed. OpenH3M/RGH/JTAG target; unsigned.
- Native package run `.local/loading-traces/20261025-225628-18532`:
  all 11 map hash checks passed; movement/observer evidence and actual gameplay
  capture inspected. All 77 installed payload files match the staged package.
  Eleven map identities, eleven menu records and all 55 preview BLFs retained.
- `work/dlc/installed-corrections` preserves existing user profile data and all
  five saved Forge layouts independently of rollback copies.
- `work/installed-map-corrections/direct-release.png`: installed executable's
  normal bootstrap inspected at startup; correct Halo 3 Mythic menu/background,
  readable text. The bounded startup process was then closed.
- `work/dlc/deployment.json`, `release-timing.json`, `prewarm-release.json` and
  `installed-release.json` record deployed files, measurements and preservation.

No console/devkit or system-link test was performed. Format checks do not
certify complete 512 MiB residency. Deferred new maps, further hardware
optimization and the unfocused-input bug remain in `TODO.MD`.

Superseded Battle02/03 candidate files were removed. Recursive cleanup of old
bundle staging was rejected by automatic approval review ("blocked by policy");
the old staging/container remain retained, and the new release uses separate
staging. Do not delete `work/dlc/installed-corrections` or `work/dlc/cache`: the
live bootstrap uses them.
