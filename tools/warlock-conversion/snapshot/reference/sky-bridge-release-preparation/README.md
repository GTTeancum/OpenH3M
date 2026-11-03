Sky Bridge release preparation

Map ID 1747 is reserved in the payload builder and does not collide with installed mapinfo IDs. Five native preview variants were generated from source-pack skybridge.png; these are artwork preparation, not a finished package. The temporary stock mapinfo must not be packaged.

Build-particle-15 completed geometry and both missing particle shaders, then stopped at the projector flare. Source audit identifies seven custom flares, with nonzero axis offsets, constant anisotropic scales and selected occlusion indices not directly represented by original H3 metadata. Existing Forge sun converter reduces curves/scales and rejects nonzero offsets; it is not a faithful drop-in. Native scan found 1,020 lens records. User preference requested for original-H3 flare behavior versus exact newer behavior; no answer yet and no bypass applied.

Source: Halo Online, via General Heed and Priception, Halo Online Map Pack For Halo 3: https://steamcommunity.com/sharedfiles/filedetails/?id=3003239190 (verified 2026-11-03). This project provides the Xbox 360/OpenH3M adaptation. No launch test or final package exists yet.

Standalone release command prepared in snapshot/tools/package_sky_bridge.py. It requires the selected DLC map SHA256 and actual launch report, checks map/mapinfo identity 1747, packages exactly seven files, sets Sky Bridge container labels, verifies STFS hashes and payload bytes, then verifies the single-container ZIP. Syntax/import/CLI help passed; end-to-end packaging remains unexecuted because no completed Sky Bridge cache or launch result exists. This helper does not infer launch success from the presence of a report. The caller must inspect that report before releasing.

Pending sequence: resolve the requested flare behavior choice, finish full conversion, stage distinct DLC payload, run one native launch with actual content inspection, then invoke the release command against that tested payload. No new build was started while the same flare choice remained unanswered.
