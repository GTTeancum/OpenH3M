Sky Bridge camera compatibility

Build24 passes playbill_sb_02 and stops at outdoor camera SSAO. Outdoor source flags18 enable SSAO (intensity0.5/radius2/threshold0.5) and lightshafts (intensity0.6). Original H3 cfxs ends at0xE4, before these extensions. User choice requested for native camera effects versus preserving the newer effects; no SSAO/lightshaft omission added without the answer.

Color grading flags17 have Use Default set and Enable clear, so authored row flags do not activate grading. The guard now checks overall grading selection before interpreting individual rows. This retains rejection of enabled custom grading and fixes a false rejection of ignored editor rows.

Source: Sky Bridge, Halo Online; General Heed / Priception, Halo Online Map Pack For Halo3: https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190. This project supplies Xbox360/OpenH3M adaptation.

User decision 2026-11-03: "Original Halo 3, always, when there's a chance to use it." Applied the requested original-H3 camera adaptation to the named Sky Bridge outdoor cfxs: omit MCC-only SSAO and screen-space shafts, retain supported exposure/bloom. Later "Forge effects? If so just drop them" was conditional, not permission to drop arbitrary Forge effects; no Forge-effect removal was made. Build25 was running at pause and the same process was confirmed live on resume, already past objects/spawns and processing environment.
