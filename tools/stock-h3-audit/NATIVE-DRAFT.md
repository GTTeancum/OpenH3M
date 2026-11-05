# Fresh Battle Canyon original-H3 draft

The user explicitly waived MCC playtest/approval on 2026-11-04 and requested
original Halo 3 within one hour, ending 2026-11-05 02:51:08 UTC.

Source: Battle Canyon, Halo Reach MCC, originally developed by Certain Affinity.
The input is the original `cex_beaver_creek` tags from the official
[Halo Reach Mod Tools](https://support.halowaypoint.com/hc/en-us/articles/8955559396372-Halo-The-Master-Chief-Collection-MCC-Update-August-2022),
under `work/editing-kits/hrek/tags/levels/dlc/cex_beaver_creek`.
No community-converted map or rejected rebuild is an input. Foundry
`5dc085e4432b6b57b2bf97e02a442ecc6edc985f` imports the source; General-101's
unchanged exporter `81e86bf98aee4607a2159ff9a22a223a1a91c9d7` produces H3 ASS.
This project's contribution is the H3 authoring and original-Xbox-360 adaptation.

Current native candidate: `.local/battle-canyon-fresh/candidate3` (source geometry/cache from candidate2).
Run `build_360_draft.py --candidate 3 --convert-only` against the completed source cache;
run `package_360_draft.py --candidate 3` with the installed Python after
successful native conversion. `launch_360_draft.ps1` uses the shared H3 install
and `work/dlc/installed-corrections`; it does not create a separate game install.
It generates native game captures and sends no keyboard/mouse/controller input.

Native budget changes: standard Blender planar dissolution reduces only world
collision from 46,032 source polygons to 10,482 polygons / 23,723 exported
triangles, with portal/sky seam delimiters. Visible world positions, faces,
material indices and UVs compare exactly; remaining collision vertices keep
source coordinates. A strict face-identity check reports 18 changed protected
faces, so complete portal-boundary equivalence is not claimed. Initial spawns
retain all FFA/infection starts and four per team per mode; total placed objects
drop from 765 to 625. All normal respawn points remain. Larger-team initial
spawning and simplified collision require gameplay review. Original source
scene and pre-budget scenario are retained as fresh-authoring inputs.

This is an unfinished review build: existing geometry/portal and draft-lighting
errors, unfinished rainbow/lasers/atmosphere/audio and multiplayer traversal
remain. Compilation and structural checks are not visual or gameplay acceptance.
The menu preview uses actual fresh-source Blender artwork, not a game screenshot.

Candidate1's collapse decimation failed official compilation by overflowing
cluster geometry limits; it is not deployable. Candidate2's planar export
compiled in 7m36s, retaining 32 visibility clusters. Native Tool reports 58
portals versus the original 59, and 13 leakage warnings versus the original 12.
No engine limits were raised. Remaining collision/traversal defects require
native review.


Installed 2026-11-05 02:31:48 UTC in the existing shared user-data root, content
ID `4CE566178F63BBD5C0188E510D6FCE563692C1BC`, map ID 1733. Installed map SHA256
`919f5627847831e856f1ef2592c99fc3bde6212cfdf5da1de4bed1fbe90774d9` matches
the staged payload. Native cache/header, STFS data/hash tree and quota checks
pass (625/640 placements; 99 Forge entries; conservative quota bound 108/256).
The two pre-existing custom bundles remain. Native menu captures render normally;
map loading, appearance, traversal, audio and gameplay are not yet verified.

The shared converter lacked serialization of `InstancedGeometryBlock.RenderBsp`.
The generic addition preserves all eight standard CollisionGeometry arrays and
relocates their pointers; TagTool documents the same 96-byte header in MCC and
original H3. It does not replace collision geometry or alter the engine.
`test_bsp_render_collision.py` passes its nested-array byte-order/relocation test.
The new `--stock-h3-draft` entry uses the working shared converter's exact stock
shader path; all legacy Battle Canyon repair flags remain false. Shared converter
files also contain other chats' uncommitted changes; those were preserved.
