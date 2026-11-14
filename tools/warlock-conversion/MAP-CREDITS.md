# Map origins and source conversion credits

Verified 2026-10-25 against the linked Workshop pages' creator listings and
descriptions, matched to the installed source cache IDs. These are credits for
the upstream Halo 3 MCC ports/remakes, not claims that this project authored
their original art or layouts. Our subsequent conversion targets native Halo 3
cache formats for OpenH3M/RGH; those adaptation changes are documented separately.

| Installed map | Original map/game or lineage | Halo 3 MCC source | Credited source creator |
|---|---|---|---|
| Warlock | Warlock, Halo 2 (Wizard lineage from Halo CE) | [Warlock](https://steamcommunity.com/sharedfiles/filedetails/?id=2977651586) | Neckzilla |
| Resuscitation | Coagulation, Halo 2 | [Resuscitation](https://steamcommunity.com/sharedfiles/filedetails/?id=2898876653) | Aerial Dave |
| Prisoner | Prisoner, Halo: Combat Evolved | [Halo Generational Combat](https://steamcommunity.com/sharedfiles/filedetails/?id=2962955878) | Drksteel (source package creator) |
| Forge Gulch | Forge World, Halo: Reach; Gulch/shoreline partition made here | [Forge World – Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3597611181) | Ryno |
| Force Cove | Forge World, Halo: Reach; complementary partition made here | [Forge World – Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3597611181) | Ryno |
| Chiron TL-34 | Chiron TL-34, Halo: Combat Evolved | [Halo Generational Combat](https://steamcommunity.com/sharedfiles/filedetails/?id=2962955878) | Drksteel (source package creator) |
| Battle Canyon (historical installation, replaced 2026-11-03) | Battle Canyon, Halo: Reach Anniversary map pack (Battle Creek/Beaver Creek lineage) | [Remember Reach – Halo 3 Multiplayer Pack](https://steamcommunity.com/sharedfiles/filedetails/?id=3575686579) | Ryno |
| Rodentia | Halo 2 custom Rat Race remake; Rat Race originates in Halo CE | [Halo 2 Map Pack for Halo 3 – WIP](https://steamcommunity.com/sharedfiles/filedetails/?id=3500400217) | Blackandfan (H3 port); original Rodentia remake author not yet verified |
| Lockout | Lockout, Halo 2 | [Lockout](https://steamcommunity.com/sharedfiles/filedetails/?id=2898979693) | Neckzilla |
| 3longation | Elongation, Halo 2 (Longest lineage from Halo CE) | [3longation](https://steamcommunity.com/sharedfiles/filedetails/?id=3618057049) | TBeezie |
| Sanctuary | Sanctuary, Halo 2 | [Sanctuary](https://steamcommunity.com/sharedfiles/filedetails/?id=2898920291) | Neckzilla |

The source packages may credit additional asset contributors. Preserve their
linked credit lists; a Workshop creator listing is not proof of sole authorship.
Halo Generational Combat specifically thanks The Ghost of Five, Kashiiera,
AnoleCannoli and Glitch5970. It does not assign individual map authorship to them
in its description. Stock Halo game assets retain their original creators' credit.

Unfinished maps remain in TODO.MD. Add their verified origin and source author
when reporting or completing each conversion; do not label deferred maps installed.


## Pending conversions

Verified 2026-10-28; these entries do not imply installation or acceptance.

| Map | Original map/game or lineage | Exact source package | Credited source creators |
|---|---|---|---|
| Powerhouse | Halo Reach lineage, Halo Online version | [Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190), `maps/s3d_powerhouse.map` | General Heed and Priception (Workshop creator listing) |
| Foundation (2026-11-14 native-only rebuild candidate) | Foundation, Halo 2 | [Foundation](https://steamcommunity.com/sharedfiles/filedetails/?id=2898955198), uploaded `foundation.map`, scenario `halo_2\levels\foundation\foundation` | R93 Sniper (page credits: "Ported by R93 Sniper"); original game assets retain their original authorship |
| Relic / Dune (2026-11-14 native-only rebuild candidate) | Relic, Halo 2; Dune is its internal scenario name | Uploaded `dune.map`, scenario `levels\multi\dune\dune`; inferred association with [Relic - Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=2899644124), not independently byte-proven | Ryno is the verified creator of the linked port; the upload contains no manifest linking its exact bytes to that package |
| Battle Canyon fresh rebuild | Battle Canyon, Halo: Reach Anniversary map pack | [Crisp/community HaloReachScenarios](https://github.com/ILoveAGoodCrisp/HaloReachScenarios), commit `aa35d15ff50db13da39685ad537430ad78492778`, `data/levels/dlc/cex_beaver_creek/cex_beaver_creek.blend`; original Reach tags, official H3EK compilation | Crisp/community prepared authoring scene; this project's H3/360 adaptation. Ryno's installed port remains separately credited above and is not this rebuild's input. |

The fresh Battle Canyon rebuild uses General-101 / Steven Garcia's
[Halo Asset Blender Development Toolset](https://github.com/General-101/Halo-Asset-Blender-Development-Toolset)
for H3 ASS export. Tool authorship is distinct from map authorship. Exact source
and tool revisions are recorded in `tools/battle-canyon-rebuild/README.md` and
its provenance records. This pending entry does not claim final acceptance or
deployment.

## Supplied-Mythic-only rebuilds, 2026-11-14

Resuscitation and 3longation have new individually packaged, statically verified
unsigned LIVE candidates. Their upstream authors and package links are unchanged
from the table above. Resuscitation's source cache SHA256 is
`e32d9553e66ac143d42260da5bbe4296e4625ba827ee27247ba74204ec66d670`;
3longation's is
`ec4276d22bfad72055caa4a810785dbc344172e1c96a0ad62d8a1c63e35e960c`.
These builds use the supplied original Halo 3 Mythic resources, not campaign
caches or MCC sound banks. Purpose-matched native sound substitutions can change
the audible samples; each package's conversion report identifies them. Their
preview images are actual upstream author screenshots, not native-output captures.
The packages retain explicit derived-mapinfo provenance. Static checks do not
establish fresh Xbox 360 gameplay, performance or system-link acceptance.
This project's work is the native Xbox 360/OpenH3M adaptation, not authorship of
the upstream geometry, artwork or game assets.

Foundation uses the uploaded source cache SHA256
`d81e6ee504dd17a7d33f6379adf8e1fad210d6bdb7f2a5b185f546aaea595e68`.
Its internal scenario identifies the map; the Workshop attribution and artwork
were checked against the author page. The upload contains no Workshop manifest,
so package-to-upload identity is not independently byte-proven. The explicit
native-camera fallback omits MCC-only SSAO while preserving supported exposure,
bloom and lighting; it is not an equivalent SSAO implementation.

The later texture-preservation audit supersedes the initial package quality
status above. Repaired candidates for 3longation, Foundation, Relic, Forge Gulch
and Force Cove retain their authored texture base resolutions and mip chains,
with independent serialized pixel and complete bitmap-resource coverage checks.
Gulch and Cove remain partitions of Ryno's Forge World port, not Halo 4 Forge
Island; their upstream source credit is unchanged. Their selected Forge palette
retains 40 Reach architecture entries plus 101 native Sandbox entries and the
native 1,500 budget. Only proven unreferenced native shader-donor textures were
retired to fit the original cache limit; authored images were not reduced.

Resuscitation's initial package remains a rollback, not a completed full-quality
repair. Its restored authored texture candidate exceeds the original native
file limit. A rejected serialized diagnostic verifies all 180 Forge entries and
their labels, including 84 authored labels and the owner-approved derived labels
"Spectre", "Sniper Rifle Ammo" and "Map Credits" where source English text was
absent. The source Forge currency remains 6,400. No over-budget cache was retained
or packaged. None of these static checks constitutes native-console rendering,
gameplay, performance or system-link validation.

## Sky Bridge (candidate36 installed; pending final review)

Status set by the user on 2026-11-04. Active conversion work has moved to
Desolation; the existing installed map and corrected LIVE archive are retained.

Original lineage: Halo Online, as identified by the source pack description.
Source: `3003239190/maps/s3d_sky_bridgenew.map`, from
[Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190).
The Workshop page credits General Heed and Priception as package creators
(verified 2026-11-03); individual original map authorship is not specified.
This project supplies the subsequent Xbox 360/OpenH3M adaptation.

The shared content tree contains candidate36, combining the traced fabric
correction and restored billboard mip addressing with the accepted rain/card
fix. Its LIVE package passed native installation and saved-view loading.
Six authorized native frames were individually inspected: transparent rain,
shaded fabric and changing billboard content are visible. The existing map alone
was replaced, with a verified rollback copy and unrelated files preserved.
The corrected LIVE archive is ready. The subsequently marked cylinder's
non-black brightness modulation has now been causally traced to the source
map's electric_02 light flashes. Removing duplicate render references left
the modulation unchanged; suppressing only electric_02 light creation made
the measured cylinder lighting constant for300 frames. Source timing and light
curves are preserved. The light-muting control is private, not a shipped fix.
Full-map traversal and close-up ad legibility remain final-review items.
Further numeric GPU tracing confirms that the arc particles are alive but hidden
by back-face culling and geometry from the saved view below them. With native
render settings unchanged, a private observer view from above measures actual
arc color contribution in73 frames. The source also specifies single-sided
horizontal particles. This explains how the light can pulse without visible
arcs in the lower view. Six subsequently authorized overhead native captures
were inspected individually in order: branching electrical arcs are clearly
visible in frames 2, 4, 5 and 6, with frame 4 showing the strongest burst around both
cylinders. The exact requested camera and unchanged production map/runtime were
verified. This confirms the local arc shapes; it is not a continuous animation
test or full-map visual acceptance. All six captures in this allowance are used.
See `snapshot/reference/sky-bridge-performance/README.md`.

## Haven (Halo 4 editing-kit workflow, 2026-11-04)

Original map/game: Haven, Halo 4. Selected source is the user's installed
official MCC Halo 4 content, with editable input from the user-installed
[official Halo 4 Mod Tools](https://store.steampowered.com/app/1695792/Halo_4_Mod_Tools__MCC/).
No community port/remake is selected. The installed `wraparound.map` and paired
mapinfo are hashed; the mapinfo identifies Haven. Individual original geometry
authorship is not established by this preflight. This project will perform the
H4-to-H3 adaptation, using the official kits and unmodified community tools;
it does not claim authorship of the map or tools. H4EK build 11571341 is installed;
the official API has read Haven's main scenario, five child scenarios, BSP,
lighting and environment tags without changing the source. Source archive and
selected tag hashes are recorded. Dependency/import validation remains in
progress; no converted candidate is claimed.
See [HAVEN.md](HAVEN.md) and [the reusable WIP process](HALO4-CONVERSION-PROCESS.md).

## Desolation (pending final review, 2026-11-04)

Requested lineage: Desolation from Halo 2. The user supplied MythicJaqui's
[Halo 3 Desolation Map Port (H3MO)](https://www.nexusmods.com/halothemasterchiefcollection/mods/1897),
version 1.0, updated 2022-05-18, as a Downloads archive. The map is an MCC U13
Waterfall replacement with scenario `levels\multi\derelict\derelict`; it is not
an original Halo 2 cache. Exact original-geometry provenance remains to be traced.
The package page credits MythicJaqui for the port, Krevil for its Halo Infinite
HUD and Mackaye99 for its MA5K model. Those custom gameplay assets do not override
this project's stock-Halo 3 asset policy. Source page checked 2026-11-04.
This project's role is Xbox 360/OpenH3M adaptation. Candidate3 passes native
metadata/resource checks and reports 79 native quotas within the 256-row limit;
broader runtime validation remains in progress. Candidate2's all-map scenery
union was rejected. The user clarified Construct's gameplay Forge palette with
zero Forge scenery, stock H3 weapons throughout, and removal of the Brute/Grunt
corpses. Distinct LIVE ID 1748 installs and loads in an isolated native profile;
the original/shared installation remains untouched. The review preview is an
actual native capture of this adaptation, not upstream artwork. The stationary
warm view measures 29.98 FPS for 40 seconds. Traversal is deferred to the user;
audio listening, broader visual/playtest review and console hardware testing
remain unverified. No final release is claimed.
See `DESOLATION.md` for source hashes, scope and remaining validation.


## Fresh Battle Canyon installation - 2026-11-03

The fresh rebuild entry above is now installed for user testing, not final
acceptance. Its Crisp/community scene, exact revision and tool attribution are
unchanged. Ryno remains credited for the replaced historical port, which was
not this rebuild input. See `../battle-canyon-rebuild/README.md` for final hashes
and bounded native evidence; renamed-DLC loading remains for user testing.


## Current Battle Canyon source — 2026-11-04

The current `battle_canyon_fresh` build replaces the rejected attempts described
above. It uses original Halo Reach MCC Battle Canyon source tags, developed by
Certain Affinity, from the official [Halo Reach Mod Tools](https://support.halowaypoint.com/hc/en-us/articles/8955559396372-Halo-The-Master-Chief-Collection-MCC-Update-August-2022).
Neither Ryno's port nor the earlier Crisp/community scenario rebuild is an input.
Foundry 5dc085e4432b6b57b2bf97e02a442ecc6edc985f imports the original tags;
General-101 exporter 81e86bf98aee4607a2159ff9a22a223a1a91c9d7 exports H3 ASS.
This project's contribution is H3 authoring and original-H3 adaptation. The user
waived MCC playtest on November 4; native acceptance is still pending. Current
evidence and limitations: [Native draft](../stock-h3-audit/NATIVE-DRAFT.md).
