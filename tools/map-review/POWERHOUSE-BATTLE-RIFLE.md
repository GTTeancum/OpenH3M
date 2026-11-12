# Powerhouse Battle Rifle correction — 2026-11-11

Installed and packaged after coordinated native tests. Shared runtime, Forge
source and TODO were not changed. All owned test instances exited; temporary
test installations were removed after compact evidence was retained.

## Finding and correction

The installed bootstrap selects `work/dlc/installed-corrections`.
`work/dlc/installed-current` contains no Powerhouse map. The accepted installed
Powerhouse SHA256 is
`9b4a7ee5604d2c11e73cc2330bc5b90d92e65e5e67fd47f11801916ab2082cf1`.

Its scenario weapon palette entry 3 points to unnamed imported weapon
`0x9000277a`. `work/powerhouse/build-98.json` identifies that exact weapon datum
as `priception\objects\weapons\rifle\dmr\dmr`. Placed weapon rows 4, 5, 9,
15 and 18 use this entry. All 18 Forge weapon entries already use native H3
weapons, including Battle Rifle `0xee850d0f`; none references the DMR.

The candidate redirects that one palette reference to the existing stock Battle
Rifle. The only changed bytes are its four-byte datum, the four-byte map checksum
and the twenty-byte header digest. Every other byte is identical, preserving
weapon placements, the accepted 18.4559% polygon reduction, collision, lighting,
materials, effects, audio data, Forge palette, metadata and all other corrections.
Unselected custom DMR tags remain as inert data to avoid rebuilding or relocating
the accepted cache. A complete datum scan finds one remaining registration:
simulation definition 13, not a placement or Forge selection. BR is already
registered at definition 572. The simulation table and its wire indices are
preserved. No engine weapon behavior was changed.

The conversion alias in `generational_assets.py` now selects the full native H3
Battle Rifle graph for this exact custom DMR identity. `item_labels.py` skips
custom DMR labels when that alias resolves to the Battle Rifle. A headless check
executed the real native alias resolver and label staging guard: existing BR
selected, no DMR dependency import and no custom labels staged.

## Verification and artifacts

Repository-relative evidence directory: `work/powerhouse-battle-rifle`. The active
LIVE container is under `.local/releases/current-live/Content/0000000000000000/4D5307E6/00000002/`.

- Map: `powerhouse.map`, SHA256
  `33391df9f821db6befead183a3bc54fcf033e2793329e91759dd8f5a29a30cf1`.
- Main LIVE container: `2D5EF2B496BB0D835F9D6839517605BA736166EC`, SHA256
  `e9a4aa7b4c7c2c3b83f017e07c76412f26c47582d0efe867643303c3ab93293d`.
- `proof.json`: bounded byte-change audit and donor checks.
- `package-proof.json`: all 77 packaged files verified byte-for-byte, STFS data,
  header and hash-tree integrity passed. Only Powerhouse differs from the
  previous main bundle. Final installed files match the new package; manifest
  and current-proof-audit were updated. One previous map/container pair is retained
  as rollback; the old container is outside active Content in `current-live/rollback/`.
- Reproducers: `prepare_powerhouse_battle_rifle.py` and
  `package_powerhouse_battle_rifle.py` in `tools/map-review`. Both refuse to overwrite
  an existing candidate. Packaging used temporary read-only hardlink staging,
  then removed those links. Existing private runtime files were reused for native
  runs; generated test installations were removed after retaining compact evidence.

The original Xbox 360 Last Resort (`maps/zanzibar.map`) donor comparison traversed
761 dependency tags and checked 190 resource pairs. Native metadata is identical
after resource ID normalization, except five resource references already stripped
from four default texture tags: reference_grids (two), color_red,
monochrome_alpha_grid and gray_50_percent_linear. These inherited exceptions are
enumerated in the proof, not silently treated as exact complete graph identity.
All 190 retained resource controls, fixups and bounded payload segments matched
the donor, including shared-cache reads. These file checks do not establish
audible sound or working weapon behavior.

## Native results and deployment

Coordinated with the Forge chat before isolated tests and again before promotion.
No shared runtime, Forge source or TODO edits. Four runs each used a 180-second
watchdog. Two early route failures were retained as compact failure evidence,
not accepted tests. All produced frames were inspected individually.

Successful pickup run `20261111-201424-18272`: exact candidate loaded as
`OpenH3MCustomMaps:\powerhouse`. Pickup prompt uses stock BR silhouette; the
player picks up an actual native BR. First-person appearance passes. Live weapon
field 0x23e records 36 -> 33 after one trigger press, then 36 after reload;
separate captures show 33 and 36, reserve 72 -> 69. Evidence: native-pickup/.

Forge run `20261111-202036-31848`: five original replacement BR objects plus a
newly spawned sixth BR (`0xe3a40087`); no live DMR. Native weapon audio was captured
after the actual fire-input event while BR was held: 800 six-channel PCM blocks,
4.267 seconds, peak 0.8911. Evidence: native-forge/. Audio was not listened to
because this assistant cannot receive audio input. The initial Forge frame was
inspected; two timed menu/drop captures were missing at the watchdog. Forge menu
and dropped-world-model appearance remain unverified. These limits are retained
in native-acceptance.json; no console hardware or system-link claim.

The installed map and LIVE bundle were promoted after rechecking the starting
inventory. All 77 payloads match the final installed files. Only Powerhouse map
bytes changed; other maps, metadata/previews, Sky Bridge and shared runtime were
preserved. The final container header removes the earlier staging-status text;
STFS integrity and all payload bytes were verified again after this header edit.
See deployment.json and package-proof.json for final identities and rollback.

Proposed TODO note for its owner: Powerhouse DMR correction installed and packaged;
all five placements use stock BR, accepted 18.46% polygon reduction preserved.
Native pickup, burst, reload and Forge spawning verified. Weapon PCM captured but
not listened to; Forge menu/drop images and Xbox360/system-link unverified.

Source credit: Powerhouse (Halo Reach / Halo Online lineage), General Heed /
Priception, [Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190).
This project supplies the Xbox 360/OpenH3M adaptation.
