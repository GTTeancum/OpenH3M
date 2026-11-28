# Halo 3 visibility (what gets drawn), as the game code does it

Read from the Halo 3 Editing Kit's Sapien (x64, same engine; assertion texts and source file names kept) with the 360
counterparts where noted. Checkers in `VisRules.cs` (`mcvcheck`, `pvscheck`, `fadecheck`, `spherecheck`, `bucketcheck`,
`seamcheck`, `locate`); each was run on stock maps as the control first. Companion to COLLISION-360.md.

Source files: visibility/visibility_portal_traversal.cpp, visibility_collection_structure.cpp, visibility_collection.cpp,
visibility_portal_activation.cpp, visibility_projections_and_volumes.cpp, scenario/scenario_pvs.cpp,
structures/structure_seams.cpp, scenario/scenario.cpp, render/render_visibility.cpp.

## 1. Where the camera is (scenario.cpp, sapien 0x3DDFE0)

The active structure BSPs are tried in index order; the first whose structure collision BSP has the camera point in a
non-solid leaf (3D BSP walk, child -1 = solid) wins. Cluster = that BSP's leaf table (`sbsp` Leaves, one byte per leaf;
0x3DC110). Only this one (BSP, cluster) starts the visibility walk.

## 2. Portal walk (visibility_portal_traversal.cpp, sapien 0x780040 driver, 0x77DE40 per cluster)

Per projection (view), from the camera's cluster:
- attached clusters: the zone set PVS "cluster mappings" list for the cluster (one byte per entry = cluster of the same
  BSP; 0x612220, PVS entry +0x48) are added directly;
- structure seams (structure_seams.cpp, 0x618670): the only way into **another BSP** (assert
  `seam_cluster_reference.bsp_index != new_cluster_reference.bsp_index`);
- each portal in the cluster's portal list (`Clusters[].Portals`, ClusterPortals 0x28 bytes: back cluster, front cluster,
  plane, centroid, radius, flags, vertices): skipped if flag NoWay (0x8); the cluster on the other side must be set in the
  current cluster's PVS row (zone set PVS, per-BSP bit vectors; there is also a doors-closed set); one-way flags
  (OneWay 0x2 / OneWayReversed 0x10) by side; the portal's projected outline must overlap the current view window;
  door activation (visibility_portal_activation.cpp, 0x61CDA0); then the portal hull is clipped to the window and the walk
  continues into the next cluster.

## 3. Per visible cluster: structure parts (visibility_collection_structure.cpp, sapien 0x7765D0 / 0x776380)

The cluster's mesh (`Clusters[].MeshIndex`) and its MeshClusterVisibility entry (render geometry +0x40, 0x20 bytes: MOPP
code + reorder table). The whole cluster mesh is skipped unless the entry exists and the reorder table holds more than
2 * subparts values (0x6B6050). The MOPP is queried with the view volume; hits are subpart ranges; the reorder table maps
them to parts (stock layout, every map checked: MOPP keys = subparts 0..S-1, table length 2S + 2P).

## 4. Per visible cluster: placed pieces (sapien 0x775B6A)

Pieces come only from the cluster mesh's instance buckets (draw lists). Each: drawn once per frame (marker), world sphere
(instance +0x40 centre, +0x4C radius) against the view volumes (0x6805E0), then fade by projected size: the piece's
FadePixelsStart/End (+0x6C/+0x6E) if start > 0 and start >= end, else the scenario structure BSP entry's
InstanceFadeStart/EndPixels.

## Checks on the converted maps (2026-11-24)

| check | stock (Guardian, Isolation, Valhalla) | ho2h3 maps |
|---|---|---|
| leaf -> cluster table vs shipped tree | - | 0 mismatches (LeafClusters.cs) |
| per-mesh visibility (`mcvcheck`) | all pass | all pass (Sword Base, Breakneck, Icebox) |
| portal neighbours in PVS (`pvscheck`) | 0 missing | 0 missing (all maps, normal and doors closed) |
| piece fade (`fadecheck`) | off | off; Icebox 683 pieces fade below 5-7 pixels (source values) |
| piece spheres hold the render box (`spherecheck`) | all | all but one Reflection ceiling piece (0.9 over) |
| pieces in no draw list | 0 | Icebox 769 = Halo Online "not for render" copies removed on purpose (z-fighting fix) |
| structure seams (`seamcheck`) | single-BSP maps | present in the BSPs (from Reach), ids and centres match on both sides |

## Structure seams (structure_seams.cpp, sapien 0x619080 -> 0x617E90 connect, 0x618670 query)

Earlier version of this note called the multi-BSP maps seamless because their scenarios have no structure-seams tag.
That was wrong: the connect step does not read that tag (only a reimport warning, 0x6190F8.., uses it when present).
At zone activation, for every active BSP and every seam position s in its SeamIdentifiers (0x28 bytes: four ids, edge
mapping, cluster mapping = cluster index + centre):
- skipped unless the BSP lists at least one cluster for seam s;
- the BSP takes one of two slots of runtime seam s; a third BSP on the same seam is an error ("can only connect 2 bsps");
- when the other slot is taken, the two BSPs' ids for seam s must match ("seam %d not matched");
- each listed cluster pairs with a cluster of the other side whose stored centre is within 0.2 units (squared distance
  under 0.04); unpaired clusters are reported ("unmatched cluster") and cannot be crossed.
The portal walk then crosses seams from any visible cluster with a seam pairing (0x618670), without a PVS test.

Converted maps (`seamcheck`, centres printed): every seam listed on two active BSPs has identical ids and identical
centres on both sides. Reflection pairs BSP 1 <-> 2 on seams 0, 1, 2, 3, 5, 10, 11 and BSP 2 <-> 0 (vista) on 4, 6, 7;
Sword Base pairs BSP 0 cluster 14 <-> BSP 2 on seam 1 (seams 0 and 4 list only BSP 2; seam 3 pairs BSP 0 with the
inactive hidden BSP 1). By the connect rules these seams connect; nothing to build. Not yet confirmed in the 360 code
(the 360 counterpart of the connect step has not been located) or in game.

## Not yet read

Portal activation details (doors), one-way flag cases in full, occlusion queries (rasterizer_instance_occlusion.cpp),
sky drawing (attached / visible sky indices in the PVS), structure_seams.cpp data layout.
