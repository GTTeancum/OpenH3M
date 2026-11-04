# Desolation conversion

Active goal from 2026-11-04. The user moved Sky Bridge to pending final review
and designated the Desolation download as the next source. Downloads is read-only;
all extraction, analysis, conversion, builds and tests stay in this repository.

## Source and attribution

Requested map lineage: Desolation, Halo 2. The supplied artifact is an existing
Halo 3 MCC port, not an original Halo 2 cache. Its exact original-geometry
provenance still needs tracing; the filename alone does not establish fidelity.

Source package: MythicJaqui's
[Halo 3 Desolation Map Port (H3MO)](https://www.nexusmods.com/halothemasterchiefcollection/mods/1897),
Nexus mod 1897, version 1.0, updated 2022-05-18. The author page identifies it as a
Waterfall replacement in a larger multiplayer overhaul, and credits Krevil for
the Halo Infinite HUD and Mackaye99 for the MA5K model. Page checked 2026-11-04.
This project's work is the subsequent Xbox 360/OpenH3M adaptation; upstream port
authorship remains MythicJaqui's. Original individual map authorship is not
established by the package page.

The user's latest instruction selects this downloaded package as the current
starting point, superseding the old deferral/source-acquisition state. Original
Xbox 360 Halo 3 stock-asset reuse and gameplay rules remain binding. In particular,
the overhaul's custom HUD/weapons are not approval to replace stock Halo 3 assets.
No publication or asset upload is part of this preflight.

## Verified input

- Archive: `C:/Users/smmel/Downloads/Halo 3 Desolation Map Port (H3MO)-1897-1-0-1652899630.rar`
- Archive size: 1251575010 bytes.
- Archive SHA256: `414189e01acc187fd51d2c3e22ef05b92176ca9382bc4f4d8b6b1af944800208`.
- Members: `halo3/maps/s3d_waterfall.map`, `halo3/fmod/pc/sfx.fsb` and
  `halo3/fmod/pc/sfx.fsb.info`, under the `Halo 3 Desolation` directory.
- Extracted map: `work/desolation/source/Halo 3 Desolation/halo3/maps/s3d_waterfall.map`.
- Map size: 664530944 bytes.
- Map SHA256: `aaf0129aab5aee63a52cacac27657cd85ac7c810b0768b0e386c16e76543333f`.
- Little-endian `daeh` header, version 13; header build date 2022-04-20.
- Existing MCC reader parses 12,000 tags. Scenario 8 and BSP 10246 both have the
  path `levels\multi\derelict\derelict`.

The map, audio index and `sfx.fsb` bank were extracted using the installed Windows
tar tool into `work/desolation/source`. No Downloads source files, installed maps
or runtime binaries were changed.

## Initial checks and next work

`work/desolation/source-preflight.json` contains header identity, hashes, tag
counts and relevant names. `work/desolation/collision-preflight.json` passes the
existing collision-format check: one small collision BSP, no large collision
BSPs, no collision instances and no Havok blocks. This is format evidence only,
not a playable candidate or proof of memory/rendering/performance acceptance.

## Older MCC layout: traced and readable

The existing scenario/dependency audits originally failed with an invalid zero
pointer. The source is the `Apr 20 2022 11:55:21` MCC build. Its scenario root is
0x7B8 bytes, with the BSP block at 0x14, 0x30-byte object/Forge palettes and a
0x24-byte zone-set record. The current schema is 0x780 bytes, with the BSP block
at 0x18, 0x10-byte object palettes, 0x1C-byte Forge entries and 0x28-byte zone sets.
This cannot be repaired by applying one offset adjustment.

Assembly's December 2022 update explains the scenario changes; July 2023 adds
further object/model changes. The existing shared tools now have build-specific
schema selection using the pre-December definitions, not a new converter or a
rewritten source cache. See the shared [MCC schema guidance](README.md#mcc-source-schema-versions).

Read-only evidence in `work/desolation`:

- `scenario-inventory.json`: all 614 scenario block headers, 1,388 rows, 312
  tag references and two data references validate with no errors.
- `object-dependencies.json`: 32 unresolved direct placement-object identities
  and their dependencies are inventoried and structurally validated. This is
  a comparison with Last Resort only, not the required all-disc reuse audit.
- `script-capacity-audit.json`: no scripts, globals or script references;
  all 512 expression slots are inactive capacity. No opcode translation needed.
- `schema-regression.json`: the current Sky Bridge MCC scenario and original
  Last Resort scenario also pass structural validation with their existing layouts.

The source has 122 scenery placements, 43 weapons, 30 equipment and 66 crates;
120/17/30/31 respectively can already be resolved by the existing placement
planner against Last Resort. Two custom tower objects, map lights/lifts, custom
overhaul weapons and ambient sentinels need further tracing. Same-name matches
here establish only a placement plan; native dependency/resource reuse still
needs its own evidence. Two biped placements also require inspection.

The Forge palettes contain 23 vehicles, 62 weapons, 25 equipment, four scenery,
one teleporter, nine goals and 20 spawners. Preserve the requested palette with
stock H3 equivalents where available. Do not import the overhaul's gameplay
changes just because their source tags parse.

## Remaining integration

No native Desolation candidate has been built. Version selection is integrated
into `inventory_conversion.py` and `object_dependencies.py` so far. The assembly
stages still directly select newer schemas and must be migrated before a build:
scenario/runtime/geometry/environment/Forge, object/model metadata and resource
schema users. In particular, the old Forge and spawn record sizes differ from
the existing stage assumptions. Preserve the existing unsupported-content checks.

Next: finish stock disc/shared-resource dependency tracing, carry the pinned
older layouts through the established MCC-to-H3 assembly stages, then validate
a private native candidate before preparing LIVE DLC and final review. Preserve
existing maps. The extracted source cache stays immutable.
Unattended native runs use process-local input and a maximum 180-second watchdog;
visual proof uses the game's own captures. No desktop input or capture app.
