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
