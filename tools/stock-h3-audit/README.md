# Stock Halo 3 Xbox 360 asset inventory

User-selected starting template: Standoff, with its Forge vehicle category excluded.
This is a fresh stock-map inventory, not reuse of the rejected Battle Canyon work.

## Tool and source

- Unmodified community [TagTool](https://github.com/TheGuardians/TagTool), commit
  `ce2dc6ac13072b160752af618ea1dc143e2727ac`.
- ShaderGenerator submodule: `9c7536ee729c6e24ac0dda6675bc0a209ea2fa98`.
- Checkout: `work/stock-h3-audit/TagTool`; executable: `work/stock-h3-audit/bin/TagTool.exe`.
- Stock input: `C:/X360/ISOs/H3M/maps/bunkerworld.map` (Standoff).
- Input SHA256 before and after queries:
  `9c2899044211dfa01e9a7d425d5f04fef7bdb0623d4d51562be4ab5718e2ee34`.
- Build succeeded, 30 upstream warnings, zero errors. .NET 8 is targeted;
  execution uses installed newer .NET with `DOTNET_ROLL_FORWARD=Major`.

The tool was built with `dotnet build work/stock-h3-audit/TagTool/TagTool/TagTool.csproj
-c Release -p:Platform=x64 -o work/stock-h3-audit/bin`. During the build,
DOTNET_CLI_HOME, NUGET_PACKAGES, NUGET_HTTP_CACHE_PATH, TEMP and TMP were directed
to dotnet-home, nuget, nuget-http and temp directories under work/stock-h3-audit.
No TagTool implementation was edited.

## Repeat the read-only inventory

From the repository run `tools/stock-h3-audit/inventory.ps1` in PowerShell.
This invokes TagTool's existing ListTags, RunCommands, ListFields and ForEach
commands. EditTag only opens the scenario for inspection; no save/mutation
command is issued. The Python helper only formats TagTool's text output.

Outputs under `work/stock-h3-audit`:

- `standoff-all-tags.txt` and `.csv`: all 9,807 cache tag entries.
- `standoff-forge-palette.txt`: original Forge entries, costs, maximum counts.
- `standoff-forge-no-vehicles.csv`: 99 entries: 23 weapons, 15 equipment,
  30 scenery, 3 teleporters, 9 goals, 19 spawning entries.
- `standoff-excluded-vehicles.csv`: 7 excluded Forge entries: Ghost, Mongoose,
  Warthog, Chopper, Banshee, Wraith and Gauss Warthog.
- `standoff-summary.json`: counts and scope; original Forge budget is 800.
- `stock-map-integrity.json`: stock map unchanged.

The full tag inventory intentionally retains all original dependencies. Removing
the Vehicles category from a proposed authoring palette does not delete every
vehicle-associated resource from a cache. Stationary turrets and the soccer ball
are vehicle-class tags too, so excluding the entire tag class would be incorrect.
Their original non-vehicle Forge categories are retained.

This proves original Xbox 360 provenance of these tags and Forge choices. It is
not approval of MCC versions of the same assets, a new map's memory use, or a
complete shared-resource payload audit. Matching stock materials/effects and
checking MCC-specific changes remain subsequent authoring decisions. No map
has been changed, built or converted by this inventory.

## Initial MCC matching

`compare_mcc.py` formats existing TagTool text reports and prepares read-only
`TagDependency List` command lists. It does not parse or modify asset binaries.
MCC input: `D:/SteamLibrary/steamapps/common/Halo The Master Chief Collection/halo3/maps/bunkerworld.map`.
Editing-kit tags: `work/editing-kits/h3ek/tags`.

All 99 retained stock choices exist in MCC and as editing-kit files. Original
names, costs and maximum counts match. MCC has 115 palette entries versus the
original 106: eight additional category/tag choices and one duplicate choice.
These additions are outside the chosen Standoff baseline; that alone does not
mean each is exclusive to MCC or absent from all other original H3 maps.

Immediate dependency queries completed for all 99 roots in each cache, without
reported errors. Seventeen roots have different reference sets. This is not yet
a recursive dependency audit, behavioral comparison or clearance to convert.
Reports: `work/stock-h3-audit/standoff-mcc-comparison.json` and
`work/stock-h3-audit/standoff-dependency-comparison.json`.
The immediate differences are sixteen roots losing references (pickup sounds,
equipment HUDs, and an energy-sword weapon reference) and the soccer ball gaining
a material-effects and impact-sound reference. No replacement behavior was authored.

## Recursive reference preflight

Run `python tools/stock-h3-audit/trace_dependencies.py 360`, then the same command
with `mcc`, then `python tools/stock-h3-audit/compare_closures.py`. The wrapper
only batches upstream `TagDependency List` commands and interprets their text.
Each process has a 180-second timeout. No asset parser or conversion logic is
implemented. All temporary files and subprocess working directories stay here.

Both traversals completed in nine waves without reported errors: 4,580 stock
tags and 4,760 MCC tags, with 4,304 shared names. The 456 MCC-only names relative
to this stock closure include shader templates/options, colored weapon effects,
materials and sounds. They are not 456 new gameplay objects. The 276 stock-only
names include platform shader templates, sounds and equipment HUD definitions.
Do not delete platform shader infrastructure just because names differ.

The local kit was missing 22 files present in both graphs (21 bitmaps and one
shader). All 22 were found in the official installed archive
`D:/SteamLibrary/steamapps/common/H3EK/H3EK.7z` and restored using 7-Zip with
`-aos` (skip existing files), the explicit include list
`work/stock-h3-audit/h3ek-missing-files.txt`, and destination
`work/editing-kits/h3ek`. Archive listing and extraction logs are beside the list.
After extraction, zero MCC closure names lack an editing-kit file. Remaining
257 original-stock names absent from the kit are 85 sets of compiled shader
templates/pixel/vertex shaders, one weapon and one damage-response definition.
Those are available in the original stock cache; do not fabricate equivalents.

Authoring policy: keep the 99 original nonvehicle choices, original limits and
budget 800; omit the additional MCC palette choices/duplicate. Retain the
official MCC dependency infrastructure needed for MCC compilation. At the later
approved conversion stage, use original stock objects and their dependencies,
not MCC cosmetic variants. This preselection reduces object-conversion scope;
it does not promise that no platform-specific conversion work remains.

This is a tag-reference preflight, not a shared-resource payload audit or visual
acceptance. Original map geometry, sky, surface-material selection and effects
still need their own authoring review. No fresh map has been authored or compiled.
