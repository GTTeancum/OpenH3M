# Halo conversion closeout and Codex handoff — 2026-11-18

## Read this first

The owner closed this assistant's conversion work and requested documentation for a later Codex takeover. **No new conversions, reconstruction of lost code, or runtime tests were performed for this closeout.** This is a handoff, not a release. Preserve existing accepted maps. The next owner should resume **Sky Bridge, Reactor and Battle Canyon** from their actual retained candidates, and begin/re-establish **retail Reach Sword Base and Reflection extraction/import**, not mistake older MCC-specific tools for the lost retail pipeline.

This document supplements, not rewrites, the repository's earlier task-specific notes. In particular, the root README describes the separate Spartan PC application; its gameplay status is not evidence that these Xbox 360 conversions work. Earlier local task permissions and priorities are historical, not a new grant to the next executor.

### Evidence classes

- **Surviving**: inspected files or durable repository/checkpoint contents available at closeout.
- **Historical**: engineering reports made before workspace loss. These preserve findings and hypotheses but their caches, detailed proofs and implementations are not currently available to reproduce them.
- **Unverified**: not demonstrated in-game or on physical Xbox hardware. Serialization/readback, menu presence, countdown and scoreboard are not gameplay acceptance.

## Asset/source inventory and reset

The cloud workspace reset during the Reach investigation. The new retail-Reach converter, HaloBridge Linux adaptation, generated Sword Base/Reflection caches, most intermediate proofs and E25/E26 runtime evidence were not recovered. Do not claim a hash or this prose can recreate those bytes.

Surviving recovery workspace (executor-local, not a guarantee on a Codex computer):

- `reach-recovery-20261118/h3-stock/extracted/`: 26 stock H3 cache files, including `warehouse.map`, `sandbox.map`, `mainmenu.map`, `shared.map`; archive/member integrity was checked during recovery.
- `reach-recovery-20261118/support/extracted/`: older Turf v7/v8 converter checkpoints and the retained Xenia support archive.
- `reach-recovery-20261118/rebuilt/`: independently reconstructed stock attachment audit and guarded placement contract; the small, asset-free sources are now included under [tools/reach-retail-recovery](../../tools/reach-retail-recovery/).
- A small private recovery ledger was saved outside the VM and re-downloaded/hash-verified. It contains notes and audits, **not** the lost converter, maps or game binaries.

The original Reach input archive is currently inaccessible. The required inputs were `20_sword_slayer.map` (Sword Base), `52_ivory_tower.map` (Reflection), and **Reach's own** `mainmenu.map` and `shared.map`, retail build `11860.10.07.24.0147.omaha_relea`, cache version 12. H3 shared resources are not substitutes. No alternate retail Reach source was found in available backups. The owner says missing work is missing; this closeout does not request uploads or attempt to reconstruct it.

No game caches, XEXs, compiled shaders, emulator binaries, screenshots, private transfer URLs, credentials or proprietary game data are included in this commit.

## Resume cards: existing H3 MCC → H3 360 conversions

These last cloud-work checkpoints are **historical identifiers**, not confirmations that their files survived. Find the exact package/input in the owner's retained files and hash it before applying any changes. Do not regenerate an older source and label it the current candidate.

| Map | Last cloud checkpoint and known issue | Actual next step for Codex |
| --- | --- | --- |
| Sky Bridge | Package identifier `9A23C8B4FAC24082064FF40A08427BA25789DAD4`; user confirmed it loads, but busy/wide views still drop FPS. Recovered embedded original ASS was 152,439,102 bytes; matched candidate's 246 portals, 53 clusters, 1,146 placements. Supplied loose scenario visibility was stale: 54 rows/checksum mismatch versus 53 clusters. | Locate current candidate and H3EK/tag inputs; preserve existing reductions and changes. Use documented Windows structure import/visibility workflow, then validate cluster/instance/resource/seam associations. Never transplant the stale scenario PVS. Existing earlier repo context: [Sky Bridge text handoff](../../tools/warlock-conversion/SKY-BRIDGE-TEXT-HANDOFF.md), which describes a different earlier local checkpoint and restrictions. |
| Reactor | Package identifier `63E200F7E1B1B9E6122DB19225359F3595B3FB9B`; user confirmed it loads after menu fix, then reported slow reactor interior/wide views. Recovered embedded ASS was 98,800,975 bytes; 250 portals, 54 clusters, 1,406 placements. Loose scenario visibility had 59 rows/wrong checksum versus 54 clusters. | Locate exact current candidate and recovered/source H3EK material. Resume official visibility work without rolling back current edits. Validate whole-BSP integration, not only a PVS blob. Existing `tools/warlock-conversion/build-reactor.ps1` is surviving older tooling, not proof of the cloud candidate. |
| Battle Canyon | V3 package identifier `A504E946420656B65AB129F72D83887816FE27B8`; user still saw single-digit cold-start FPS and choppiness from bases/wide views. Reuploaded `cex_beavercreek.map` SHA-256 `d92e723e4aee4be25ec12d2a98a7fda11de1847d4d607e1a848f84d477035834` matched the earlier MCC source. No editable Battle Canyon source was found in H3EK. Reconstructed ASS controls retained 61 portals and 1,173 placements (618 active, 555 hidden); null-material semantics and association gates remained unresolved. | Locate retained V3 and exact source; establish an editable/importable structure with verified semantics before official rebuild. Do not treat the old reconstructed controls as finished authoring data. A later direct Reach 360 route is a separate rebuild idea, not proof of improved performance. Preserve current installed map until replacement accepted. |

**No official VIS rebuild completed for any of these three.** The original instruction was to use current candidates for a baseline, not roll back geometry or textures. The H3EK Windows tool failed to start in the old cloud because Wine IPC/socket creation was blocked. Original ASS recovery and checks did not overcome that runtime restriction. The owner later had the writable H3EK kit removed; one read-only browser download remained at the time, but it is not a surviving source guarantee after the reset.

Microsoft's [structure import](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/quickstart/process/step4) and [portal guide](https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/guides/usingportals) distinguish import-time PVS (especially activation) from runtime portal-overlap rendering. Rebuilding visibility does not by itself prove a frame-rate fix. Measure gameplay and physical-console performance separately. Static investigation found `fix-structure-new-visibility` enters the importer; it was not established as a safe standalone PVS-only command.

## Turf: experimental release, not unfinished packaging

Surviving Turf v8 checkpoint status records an already-delivered **Turf1755 Experimental Test** LIVE package:

- Container SHA-256 `74e5821314c8341e8df2c0b534d55088c5272103ffac8fb08db9df15b46c836b`, 157,052,928 bytes.
- ZIP SHA-256 `4189ac8e56fff6869dd588006e6665a3e2f9e99f8e296344f8a49c3ec2c22b1e`, 127,411,711 bytes; seven parts and a join BAT were delivered. A later resend was the same bytes, **not** new progress.
- Historical exact-container local Xenia test: menu entry, authentic Turf geometry, movement/turn/firing, Forge AR creation/release. No physical-console, system-link, full collision-domain, audio or performance certification.
- Approved changes: decorative Hornet/train removed; 15 missing sound tags/74 recordings silenced; 11 unsupported steam placements omitted; 232 world images downscaled by retaining authored mips. Valhalla Forge set retained.
- Collision/render-association omission remains an explicit experimental limitation. Default packaging quarantine was not lifted; only the exact, pinned experimental opt-in was permitted. Do not promote or remove quarantine based on these notes.

Codex should start from the exact delivered package and v8 status rather than reissue it as a new release. Surviving older tooling is useful for H3 packing, but contains no full new retail-Reach conversion layer.

## Reach → Blender → H3: what was actually attempted

Source project: [HaloBridge Blender Asset/Map Importer](https://github.com/BarnacleBoii/HaloBridge-Blender-Asset-Map-Importer-Addon-BETA), inspected commit `6975817b83544bb03dddb33598eec29c5592b1a8`. Upstream/its dependencies retain their authorship and licenses; this project did not author the importer. Original Sword Base and Reflection are Bungie's Halo Reach maps. User-supplied retail cache package had no separate third-party map-conversion author identified. No private asset link is published here.

The historical adaptation made a **native Linux extraction path**, not a Linux H3EK:

1. Blender 4.3.2 was present. Upstream synthetic import tests passed transforms, shared meshes and cancellation/rollback.
2. Three C# projects were retargeted from `net10.0-windows` to `net10.0`. Windows/WPF PNG conversion in `DdsConvert.cs`/`DdsOutputArgs.cs` was replaced with a portable .NET encoder; Python launched a `dotnet` DLL rather than `.exe`.
3. Native extractor built and read an existing H3 MCC Beaver Creek map. PNG channels/alpha/BC1/cubemap layouts were independently checked. **That MCC proof did not establish Reach 360 support.**
4. The user then explicitly directed console support. Retail readers processed both Reach 360 maps; resources used verified DEFLATE on the pages actually needed (initial LZX concern was not a demonstrated requirement for these maps).
5. Sword's authored zone mask is `0x5`, active BSP slots 0/2; its slot-1 hidden BSP has metadata but no resource pages and is not authored active. Reflection mask `0x7` needs all three; its additional BSP geometry is in `sbsp`, not the empty lightmap slot. Preserve slot identity; do not discard active geometry or fabricate inactive payloads.
6. Page inventories referenced the supplied local/mainmenu/shared resources, not campaign files. This was a finding for these particular maps, not a universal Reach rule.

**The adaptation code and full extracted scenes were lost.** Codex must start from upstream plus these constraints if continuing, not assume an installable fork exists in this commit. Native extraction does not supply Sapien, an H3 compiler, complete shaders, physics, gameplay or a finished Xbox cache. Reclaimer and blam-tags/Baboon are possible source references, not proven retail-map replacements.

## Reach native H3 pipeline and last verification

See [historical engineering details](REACH-HISTORICAL-ENGINEERING.md) for exact structural findings, hashes, native offsets and lost module names. That file is explicitly historical, not restored implementation.

Before reset the pipeline reported structural readback of all five active BSPs, 4,321 source instances, native geometry/indices, collision/portals, converted lighting, required/optional bitmap resources and scene residency. Reflection needed a real spatial split to fit H3's 16-bit **terminal index-buffer corner** field; simple index truncation was invalid. Fixed collision aggregation reduced the artificial actor counts while retaining original hulls/materials. Native shaders were translated/reused explicitly; many materials still lacked support. Partial-visual diagnostic variants deliberately omitted unresolved draw parts and were not finished maps.

Several actual loader bugs were found, but neither port became playable:

- Full-width native manifest masks were missing/trimmed. Repair advanced both maps from metadata-only loading to reading world-resource pages; still no world/HUD.
- Native resource-use selectors and cluster ordinals needed correction; neither alone fixed startup.
- Generated spawn writer used manual BSP override at `+0x32` while leaving compiled attachment at `+0x50` zero. The independent **surviving** reconstructed stock audit confirmed 2,068 Slayer-eligible native markers use automatic policy, manual 0, compiled 1 in single-BSP stock controls. The tiny audit/contract is not the lost serializer or whole-map converter.
- Reflection fallback was above its safe box; a grounded authentic start was prepared. Stock Orbital also has an out-of-bounds fallback, so that alone is not a root-cause proof. Proper Slayer initial markers and Reach FFA/team semantics remained incomplete.
- Per-room collision spatial indexes and 980 per-mesh visibility compiler jobs remained unfinished. The latter executable batch was held and **never run**; do not claim a VIS result.

### Runtime record to preserve

- Both appeared in H3 local Custom Games and read their actual files; early starts faulted before gameplay.
- A matched experimental package activating untouched Warehouse rendered a 3D stock interior. This narrowed packaging concerns, not conversion correctness; a later host kill limited the control.
- Reflection E25 reached countdown zero, then black screen/player roster for over five minutes. No level, player HUD or movement. It exited normally after closure; **not a gameplay pass**.
- E26 changed only fallback coordinates and derived checksums. Display connection was lost. The reset removed its final evidence; final outcome unknown. No emulator was running after recovery.
- Some other runs were killed by the cloud host before conclusive observation. Keep those separate from genuine guest faults.
- Neither map has physical Xbox gameplay or performance proof. No installable Reach release is being handed off.

## Concrete takeover sequence (not executed during closeout)

1. Inspect this branch's existing conversion tools and actual local retained artifacts; identify exact source edition and hashes. Do not overwrite accepted installations.
2. For the three older optimization maps, locate their current candidate + authoring sources and resume Windows H3EK visibility work as separate map tasks. Validate whole-BSP references after importer changes, then test actual performance.
3. For Sword Base/Reflection, establish actual retail Reach inputs and re-establish Linux extraction/import or an available supported Windows route. The missing code is missing; historical claims must be reproduced before relying on them.
4. Preserve immutable source inputs and durable, asset-free source checkpoints. Use one current candidate, one necessary rollback and compact evidence; do not accumulate full test copies or rely on VM-only state.
5. Keep native limits, original H3 asset policy, exact scene/resource ownership, per-map provenance and fail-closed validation. Separate format readback, emulator launch/render/play, physical console acceptance and performance milestones.
6. Evaluate remaining native attachment/initial-spawn, collision-index and visibility gaps using controlled tests. Do not bundle unverified hypotheses into a claimed cure or ask the owner to test a merely renamed file.

Closeout validation was documentation/path/diff review only. No new compilation, emulator, game or conversion test was run.
