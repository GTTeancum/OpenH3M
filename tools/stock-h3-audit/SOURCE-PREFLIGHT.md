# Fresh Battle Canyon source preflight

Original map/game: Battle Canyon, Halo Reach MCC, originally developed by
Certain Affinity. No community-converted map or rejected rebuild is an input.
Installed original cache: `D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/haloreach/maps/cex_beaver_creek.map`.
Official source-tag input: `work/editing-kits/hrek/tags/levels/dlc/cex_beaver_creek`.

## Tool selection and observed limits

- Unmodified pinned TagTool cannot open this installed Reach cache: `string_id
  set 56` failure. Saved log: `work/stock-h3-audit/reach-source-all-tags.txt`.
  No TagTool fix was authored; the successful H3 inventories remain separate.
- Current [Foundry](https://github.com/ILoveAGoodCrisp/Foundry) requires Blender
  5.2; installed Blender is 4.5. Historical upstream Foundry 1.1.61 declares
  Blender 4.5 support. Unmodified source is pinned at
  `5dc085e4432b6b57b2bf97e02a442ecc6edc985f`, downloaded into
  `work/stock-h3-audit/upstream/Foundry-5dc085e4432b6b57b2bf97e02a442ecc6edc985f`.
  This is source availability, not yet a successful geometry-import test.
- [Halo Asset Blender Development Toolset](https://github.com/General-101/Halo-Asset-Blender-Development-Toolset)
  documents H3 ASS export with limitations, including missing UVW W-coordinate
  support. Do not silently compensate with a bespoke exporter.

## Read-only source inspection

`inspect_reach_source.py` invokes the official ManagedBlam tag API using the
initialization and field-selection pattern from Foundry's `managed_blam`
modules. It only loads, reads references, disposes and stops; no Save call,
binary parser, conversion or geometry generation. Run with installed Blender's
bundled Python (`C:/Program Files/Blender Foundation/Blender 4.5/4.5/python/bin/python.exe`).
Dependencies are isolated in `work/stock-h3-audit/python-packages`.
Pythonnet 3.0.5 and clr_loader 0.2.7.post0 were installed there. The bundled
Foundry wheel set's cffi 1.16 did not satisfy clr_loader's >=1.17 requirement;
pip resolved the dependency from PyPI without editing Foundry.

Successful output: `work/stock-h3-audit/reach-source-references.json`.
One source BSP and one sky scenery reference were read. The BSP has 193 material
slots with 102 unique references: 90 shader, 9 terrain, and one each water,
foliage and glass. This includes the source invalid-shader reference; no
conclusion about whether its faces are visible has been drawn.

Next: inspect source effects and sky dependencies and select stock H3 surface
donors. Standoff remains the first donor; consult other original maps for
missing surface types. A name match is a candidate, not visual validation.
No surface substitutions, fresh scene import, map compilation, or conversion
have been performed. Required features without stock alternatives go to the
user for a decision.

## Additional source and donor evidence

The same official API read now records seven effect-scenery palette entries:
three laser emitters, dripping point, rainbow, mist and sun flare. Each resolves
through an FX anchor model to its corresponding Reach effect. The sky resolves
to `levels/dlc/cex_beaver_creek/beavercreek_sky/beavercreek_sky.model`.
No stock counterpart has yet been established for the rainbow or decorative
lasers. Do not treat a Spartan Laser weapon effect as an established substitute.

Original stock Guardian, Valhalla (`riverworld`) and Sandtrap (`shrine`) tag
inventories are saved beside the Standoff inventory. These were consulted for
water and architectural/terrain alternatives absent from the initial donor.
`surface-donor-candidates.csv` records seven concrete original-stock candidates;
they are not applied mappings or visual approvals. Standoff supplies terrain
and foliage candidates; Valhalla supplies river water, cliff terrain and red/blue
Forerunner surfaces; Guardian supplies an architectural floor candidate.

All seven candidate level-material files were absent from the partial local
editing kit, despite the gameplay palette dependency check passing. Filling in
the official archive's `tags/*` with 7-Zip `-aos` preserves existing files while
adding the missing stock source tags. Extraction log:
`work/stock-h3-audit/h3ek-complete-stock-tags-extract.log`. Verify its terminal
result and candidate presence before relying on the completed kit.

Extraction subsequently exited 0 with `Everything is Ok`; all seven candidate
material files now exist. The log reports 57,442 processed files, 27,973,636,020
bytes; this is not a count of newly created files because existing files were
skipped. Source assets were not uploaded or installed into the live game.

## Background tool readiness

Unmodified Foundry 1.1.61 successfully enabled in Blender 4.5.8 LTS, with its
scene properties registered. Evidence: `foundry-background-check.log` records
`FOUNDRY_BACKGROUND_LOAD_OK 4.5.8 LTS`, process exit 0. This only verifies add-on
loading, not source import, geometry fidelity or export compatibility.

Run `check_foundry.py` through Blender with `--background --factory-startup
--python-exit-code 1 --python`. For that subprocess set APPDATA and LOCALAPPDATA
to `work/stock-h3-audit/profile/roaming` and `profile/local`, BLENDER_USER_CONFIG
to `profile/blender`, and TEMP/TMP to `work/stock-h3-audit/temp` (absolute paths).
The initial load attempt occurred before dependency installation had finished
and failed on missing networkx; after the installer exited successfully the
load check passed without upstream modifications.

On top of the official tag API dependencies, the isolated Python directory
contains networkx 3.4.2, scipy 1.16.0, pillow 11.3.0, pymem 1.13.1 and
py360convert 1.0.4 with their pip-resolved dependencies. Installation output is
`foundry-dependencies.log`. No pymem process-control functionality was invoked.

The user has been asked whether unmatched decorative effects should be omitted
or receive a specific Reach-import proposal if no stock match is found. No
answer is assumed. Geometry authoring and effects remain unchanged.
