# Authored texture mip restoration

2026-10-22: the user described the converted maps as overly sharp/grainy.
The converter retained a single level for most BC1/2/3 textures even when the
source had authored smaller levels. This prevents distance filtering from using
those levels. The correction preserves the full-size compressed image and restores
the authored chain; it does not blur the image, change exposure, or change shaders.

`snapshot/tools/material_importer.py` now retains supported authored BC1/2/3/5
chains by default. The Xenos packed-tail encoder currently supports power-of-two
dimensions of at least 32 pixels on both axes. Other layouts remain explicit
limitations; do not invent smaller levels or silently resample their base image.

## Updating accepted maps without repeating terrain conversion

Run inside `C:/X360/ISOs/H3M/.local/OpenH3M-source`, with Python 3.12 and `-B`:

```powershell
python -B tools/warlock-conversion/snapshot/tools/restore_authored_mips.py --source SOURCE_MCC_MAP --basis ACCEPTED_CONVERTED_MAP --xex C:/X360/ISOs/H3M/default.xex --output work/forge-world/MAP-mips.map --report work/forge-world/restored-mips-MAP.json
```

Use new output/report filenames. The source Workshop cache and original disc
files are read-only. `audit_missing_mips.py` can produce the match inventory alone.

The tool matches nameless imported, single-image 2D textures by dimensions,
compression format and exact SHA256 of the untiled base blocks. BC5 endpoint
bias is translated before matching. Ambiguous source matches are skipped.
Unreadable source pages are reported, never accepted by bypassing integrity checks.
The accepted map's color curve and other bitmap fields remain unchanged.

Every restored level is decoded by the separately built TagTool validator and
compared byte-for-byte (SHA256) against the authored source. The pinned TagTool
dependency is checked. Validation files and runtime output stay inside the repo.

Resource IDs/salts stay stable. New resources replace their old slots, every
affected manifest's resource-size category is adjusted, and unreferenced local
pages are omitted from the repacked raw section. Shared cache references remain
references; no shared.map is copied into the bundle. Simulation definitions are
sorted and checked against the original engine's binary-search comparison and
12-bit wire-index limit.

## Current incremental restoration inventory

| Map | Restored textures | Added resource bytes |
| --- | ---: | ---: |
| Forge Gulch | 50 | 4,005,888 |
| Warlock | 79 | 7,794,688 |
| Resuscitation | 31 | 2,514,944 |
| Prisoner | 55 | 3,297,280 |

The independent decoder verified 2,053 authored levels across these 215 textures.
The Reach scenery import also retains its supported authored chains directly;
these newly imported textures are not counted as incremental restorations.
This is not a claim that every source texture had usable
mips. Non-power-of-two textures and ambiguous matches remain in the audit reports.
Full console RAM usage cannot be inferred from file sizes or these deltas.

## Ambient lighting packing correction

The Reach scenery visibility check exposed a separate, confirmed conversion bug.
`render_buffers.py` had written each ambient-PRT coefficient into a four-byte
slot with three zero bytes. Original Sandbox uses four consecutive coefficient
bytes per advertised element: `Count = ceil(primary_vertex_count / 4)`, stride 4.
The cached TagTool `VertexStreamXbox.ReadAmbientPrtData` reads one `Float8_1` per
vertex; `RenderGeometryConverter.cs` explicitly documents this count convention.

The converter now packs the bytes and adjusts the descriptor count. The focused
regression is `python -B snapshot/tools/test_ambient_prt.py` (from this directory).
For already accepted maps, run from the repository:

```powershell
python -B tools/warlock-conversion/snapshot/tools/repair_ambient_prt.py --basis MIP_RESTORED_MAP --xex C:/X360/ISOs/H3M/default.xex --output work/forge-world/MAP-lighting.map --report work/forge-world/ambient-repair-MAP.json
```

This only accepts nameless imported model streams whose primary vertex count,
ambient descriptor and zero-padding pattern prove the specific old layout.
It preserves each coefficient, resource ID, owner and salt. Existing raw
allocations remain the same size; the unused bytes become trailing padding.
It rejects unfamiliar layouts and refuses to create a new map when no repair
is needed. Fresh conversions already use the corrected packing.

Serialized readback verifies 9 older Gulch buffers, 121 Warlock buffers,
143 Resuscitation buffers and 7 Prisoner buffers. The newly imported Reach
models were rebuilt directly with the correct packing. Reports are
`work/forge-world/ambient-repair-*.json` and `work/dlc/ambient-readback.json`.

The private reports are `work/forge-world/restored-mips-*.json`; each records the
source/target mapping, output hash, per-level hashes and memory/file-size deltas.
Runtime visual evidence and deployment status are recorded in DLC-BUNDLE.md.

All typed resource references pass for Gulch, Resuscitation and Prisoner.
The generic reference checker reports datum `0xe1660003` in both the accepted
Warlock basis and the updated Warlock cache; this is a pre-existing finding,
not a clean pass. The restoration preserves every existing resource owner,
salt and type in all three previously converted maps, verified independently
in `work/dlc/mip-resource-stability.json`.
