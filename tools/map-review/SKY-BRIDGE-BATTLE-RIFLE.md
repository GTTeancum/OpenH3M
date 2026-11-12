# Sky Bridge Battle Rifle correction — 2026-11-11

The four authored DMR placements (scenario rows 14, 15, 27 and 29) now reference
the existing stock Halo 3 Battle Rifle, `0xee850d0f`. The final Forge weapon row
was the DMR, `0x90002735`; it is removed from the active palette, reducing its
count from 29 to 28. The existing Battle Rifle entry remains. All other palette
rows, labels, budgets and placement coordinates are unchanged.

The byte-change audit permits only the placed-weapon palette datum, Forge count
and map checksums. Geometry, collision, rain-card and electrical-light corrections,
materials, lighting and other map content are byte-identical. Unselected DMR
data and its simulation registration remain inert; existing simulation indices
are preserved. No shared runtime or Forge implementation was changed.

The reusable conversion alias selects the native BR graph for the exact imported
DMR identity. The Forge converter now removes the redundant DMR source row when
the source already has the stock BR entry. A check against the actual MCC Sky
Bridge source confirmed 29 -> 28 rows, with only the DMR removed, and exercised
the native BR alias resolver.

Evidence is retained in `work/sky-bridge-battle-rifle/`. `proof.json` contains the
bounded byte audit and stock Zanzibar donor comparison: 761 dependency tags,
1,227,689 metadata bytes and 190 resources, including shared resources. Five
already-stripped default bitmap resource references are recorded explicitly;
these are inherited from the accepted cache, not introduced by this correction.

`package-proof.json` records all seven payload comparisons and successful STFS
header, data and hash-tree integrity checks. The unsigned LIVE package targets
OpenH3M and RGH/JTAG, with no retail-signature claim.

- Map SHA256: `3c43fe2149a0466e3ad34c472831f5cb5b267a76b71b8559e12fb07cfe6b9589`
- LIVE content ID: `64B3D0B404505477CE6AB57F11AD4BF1680F5F2A`
- LIVE SHA256: `c23ae9cda4a5f9eea9a019deaa5a3469017ae5fcb1013c87d6bae3ae9e8ff260`

Native pickup evidence records zero live DMR objects, ten initial BR objects,
pickup of a BR, two three-round bursts (36 -> 33 -> 30) and reload to 36.
The initial screenshot shows the stock BR pickup silhouette. Weapon PCM was
captured after the actual fire event (800 blocks, 4.267 seconds), but was not
listened to. Timed pickup screenshots did not arrive before the 180-second
watchdog. No FPS, Xbox 360 hardware or system-link validation is claimed.

Source credit: Sky Bridge (Halo Online), General Heed / Priception,
[Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190).
This project supplies the Xbox 360/OpenH3M adaptation.


The final visual-only native pass recovered the missing timed evidence. All four
images were inspected individually: pickup prompt, pre-pickup view, stock BR
firing with muzzle flash/impacts, and the reload animation. Live magazine values
again recorded 36 -> 33 -> 30 -> 36. The Forge pass also supplied four inspected
images, including the Battle Rifle menu label and spawned, held weapon model;
the live BR count rose from ten to eleven, with no live DMR. A dropped-world-model
view was not captured. See native-visual/ and native-forge/ summaries.

Installed and packaged after the coordinated tests. All seven Sky Bridge payloads
match the final installed inventory; all 77 main-bundle files were reread and
matched their manifest hashes. The current main container, including Powerhouse's
BR correction and accepted polygon reduction, is unchanged. The previous Sky
Bridge map and container are retained as one rollback pair; the old container is
outside active Content. Manifest, current-proof-audit and release README now
identify this release. All three owned test processes exited and their temporary
test installations were removed after compact logs and captures were archived.
Shared runtime, Forge implementation and TODO were untouched.
