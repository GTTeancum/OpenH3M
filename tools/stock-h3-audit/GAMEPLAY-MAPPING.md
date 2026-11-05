# Battle Canyon gameplay mapping

Source: original Battle Canyon, Halo Reach MCC / official Reach Editing Kit,
`levels/dlc/cex_beaver_creek/cex_beaver_creek.scenario`. Original map by
Certain Affinity; no community port or rejected rebuild supplies this layout.
Target: stock Halo 3 gameplay objects, authored with official H3 editor fields.

## Stock mappings

- DMR -> H3 Battle Rifle; Reach grenade launcher -> H3 Brute Shot. Two each;
  explicitly selected by the user on 2026-11-04.
- Plasma Rifle -> stock H3 Plasma Rifle. Two placements; Guardian supplies
  the original-360 witness missing from Standoff's Forge palette.
- Sixteen invisible respawn markers -> unchanged stock H3 invisible respawn
  markers, present in original Standoff and Guardian.
- Shared initial starts -> H3's dedicated initial-start objects for the
  supported H3 modes, retaining the source positions and teams. The source
  has 52 team starts, 16 neutral starts and 24 Infection starts. Reach's
  generic scripted start must be represented by the stock mode-specific H3
  markers, without changing those stock tags. Native mode/team behavior must
  be checked in MCC; the original label is retained in the authoring report.
- CTF, Assault, Oddball, King and Territories goals/zones -> their stock H3
  object types, preserving authored transforms, boundaries and ordering.
- Seven Infection havens -> stock `infection_haven_static`, present in
  original Guardian. These have a stock H3 counterpart and are not removed.
- Two-way teleporters -> stock H3 two-way teleporters; retain source channels.
- Gravity lifts -> stock H3 permanent grav lifts; retain source placement.
  Traversal and force/exit direction require the user's MCC test.

Stock/MCC Guardian inspection for the extra Plasma Rifle, invisible respawn
marker and Infection haven found identical immediate dependency names. Their
object flags and gameplay fields were read with unchanged TagTool. The Plasma
Rifle has platform differences (MCC first-person offsets/font fields and an
ejection-port recovery rate); preserve native MCC infrastructure for this
stage and reuse the original stock object during the later approved 360
conversion. This is not a claim of runtime equivalence.

## Decision requested: Reach-only mode markers

The original layout contains 23 markers for modes absent from stock H3:

| Source role | Count |
| --- | ---: |
| Stockpile respawn zones | 4 |
| Stockpile collection goals | 4 |
| Stockpile flag positions | 8 |
| Headhunter drop points | 7 |

Proposed: omit these 23 mode-only markers. Retain all supported H3 mode
placements and the seven stock-compatible Infection havens. Do not implement
new game rules or leave inert substitute objects in the map. These omissions
remain pending the user's decision.

The previously rejected Spartan doll is excluded under the existing explicit
instruction. The four health-station appearances and other custom scenery
remain separate asset work; this proposal does not authorize discarding them.
