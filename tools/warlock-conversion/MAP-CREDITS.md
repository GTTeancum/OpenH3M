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
| Battle Canyon fresh rebuild | Battle Canyon, Halo: Reach Anniversary map pack | [Crisp/community HaloReachScenarios](https://github.com/ILoveAGoodCrisp/HaloReachScenarios), commit `aa35d15ff50db13da39685ad537430ad78492778`, `data/levels/dlc/cex_beaver_creek/cex_beaver_creek.blend`; original Reach tags, official H3EK compilation | Crisp/community prepared authoring scene; this project's H3/360 adaptation. Ryno's installed port remains separately credited above and is not this rebuild's input. |

The fresh Battle Canyon rebuild uses General-101 / Steven Garcia's
[Halo Asset Blender Development Toolset](https://github.com/General-101/Halo-Asset-Blender-Development-Toolset)
for H3 ASS export. Tool authorship is distinct from map authorship. Exact source
and tool revisions are recorded in `tools/battle-canyon-rebuild/README.md` and
its provenance records. This pending entry does not claim final acceptance or
deployment.

## Sky Bridge (candidate32 installed for testing; candidate36 prepared)

Original lineage: Halo Online, as identified by the source pack description.
Source: `3003239190/maps/s3d_sky_bridgenew.map`, from
[Halo Online Map Pack For Halo 3](https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190).
The Workshop page credits General Heed and Priception as package creators
(verified 2026-11-03); individual original map authorship is not specified.
This project supplies the subsequent Xbox 360/OpenH3M adaptation.

The shared content tree contains candidate32. Candidate36 combines the traced
fabric correction and restored billboard mip addressing; its separate LIVE
package has passed native installation and saved-view loading in a private run.
The candidate archive is prepared for review, with full visual acceptance and
shared promotion still pending. See `snapshot/reference/sky-bridge-performance/README.md`.


## Fresh Battle Canyon installation - 2026-11-03

The fresh rebuild entry above is now installed for user testing, not final
acceptance. Its Crisp/community scene, exact revision and tool attribution are
unchanged. Ryno remains credited for the replaced historical port, which was
not this rebuild input. See `../battle-canyon-rebuild/README.md` for final hashes
and bounded native evidence; renamed-DLC loading remains for user testing.
