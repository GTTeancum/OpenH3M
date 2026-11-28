# How Bungie built Halo 3 multiplayer levels to run on Xbox 360

Study written 2026-11-27, before any Sky Bridge rebuild. Questions were written first
(`C:\Programming\GitHub\OpenH3M\.local\h3-study\questions.md`), then answered from official sources only:

- **Kit**: the MCC Halo 3 Editing Kit in `C:\Programming\GitHub\OpenH3M\.local\h3ek-source` — its stock
  tags for 11 shipped MP levels, `tool.exe` commands (`export-tag-to-xml`, `script-doc`) and the kit's
  test game `halo3_tag_test.exe` with its built-in draw-call profiler (`dip_stats_enable` /
  `dip_stats_dump`).
- **Docs**: 343's official MCC modding documentation on Microsoft Learn (H3 section, last updated
  2022-11-22). Community pages (c20.reclaimers.net) are used only where marked *community*.

Nothing here comes from our own conversion tools except where marked *earlier project measurement*.

Stock levels measured (tag name → shipped name): guardian (Guardian), riverworld (Valhalla), zanzibar
(Last Resort), construct (Construct), shrine (Sandtrap), snowbound (Snowbound), chill (Narrows),
cyberdyne (The Pit), deadlock (High Ground), isolation (Isolation), salvation (Epitaph). The kit has no
tags for Sandbox, Standoff, Rat's Nest, Foundry or the DLC levels.

## Method

1. `tool export-tag-to-xml <tag> <xml>` on each stock `.scenario_structure_bsp`, `.scenario` and
   `.performance_throttles`. The XML (450 MB–1.2 GB per level) was summarised and deleted:
   `C:\Programming\GitHub\OpenH3M\tools\map-review\h3-level-study\summarize_bsp.py` (reads only the
   official export; the exporter writes `value="<unavailable>"` for paged resources, which the
   summariser makes parseable), `analyze.py`, `export_all.sh`. Summaries:
   `C:\Programming\GitHub\OpenH3M\.local\h3-study\*.json`, table in `stock_table.json`.
2. `tool script-doc <command>` for command meanings.
3. `halo3_tag_test.exe` run on a separate, never-displayed desktop
   (`C:\Programming\GitHub\OpenH3M\tools\map-review\h3-level-study\run_tag_test.py`): `init.txt` loads the
   level (`game_multiplayer slayer`, `game_start levels\multi\<map>\<map>`, `dip_stats_enable 1`);
   console commands are posted as window messages to the game's own window (no focus change, no OS
   input): `debug_camera_load_text "<x y z  fwd xyz  up xyz  fov>"` places the camera,
   `dip_stats_dump` writes `debug_dip_stats.txt`, `screenshot "<name>"` writes a 1920×1080 TIFF. Every
   reading was checked against its screenshot. (Putting `sleep` in `init.txt` crashes the game: game
   time is not running yet.)
4. Sky Bridge source census of the untouched original
   `C:\Programming\GitHub\OpenH3M\.local\h3ek-source\data\levels\multi\s3d_sky_bridgenew\structure\s3d_sky_bridgenew.original.ass`
   (`ass_census.py`; reads the kit's own input format).

## Stock level figures (from the kit's own tags)

"Instance parts" = for every placed copy, one per material it uses; it is what would be drawn if
everything were in view (see Q4). Triangles are index count ÷ 3 (all stock meshes are triangle lists).

| Level | Clusters | Portals | Materials | Structure tris | Structure parts | Instance pieces | Placed copies | Pieces used once | Instance tris (all copies) | Instance parts | Tris per piece (median / max) | Materials per piece |
| --- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| Guardian | 26 | 51 | 88 | 15k | 225 | 212 | 479 | 145 | 100k | 1,097 | 134 / 3.6k | 1.75 |
| Valhalla | 26 | 60 | 64 | 37k | 191 | 76 | 262 | 38 | 87k | 408 | 133 / 3.6k | 1.62 |
| Last Resort | 40 | 93 | 112 | 39k | 242 | 336 | 1,130 | 209 | 316k | 1,899 | 148 / 5.1k | 1.35 |
| Construct | 15 | 41 | 94 | 12k | 132 | 135 | 545 | 86 | 143k | 1,318 | 118 / 2.0k | 2.53 |
| Sandtrap | 44 | 100 | 44 | 12k | 188 | 110 | 330 | 53 | 53k | 581 | 134 / 2.6k | 1.70 |
| Snowbound | 40 | 68 | 83 | 46k | 486 | 207 | 550 | 143 | 215k | 1,138 | 202 / 11.1k | 2.10 |
| Narrows | 35 | 53 | 88 | 27k | 258 | 104 | 201 | 73 | 82k | 974 | 396 / 1.1k | 3.37 |
| The Pit | 48 | 113 | 85 | 12k | 299 | 311 | 834 | 177 | 229k | 1,649 | 82 / 3.0k | 1.67 |
| High Ground | 43 | 76 | 79 | 39k | 260 | 275 | 857 | 194 | 313k | 1,405 | 56 / 10.9k | 1.29 |
| Isolation | 49 | 80 | 43 | 19k | 242 | 100 | 391 | 57 | 191k | 600 | 320 / 9.9k | 1.60 |
| Epitaph | 31 | 132 | 53 | 24k | 254 | 123 | 383 | 68 | 120k | 984 | 128 / 2.4k | 2.42 |
| **Range** | 15–49 | 41–132 | 43–112 | 12–46k | 132–486 | 76–336 | 201–1,130 | | 53–316k | 408–1,899 | 56–396 / ≤11k | 1.3–3.4 |

Official draw counts from the kit's profiler (`dip_stats_dump`, one frame, MCC PC renderer in
`halo3_tag_test.exe`, player at the first spawn or camera placed by text; screenshots in
`C:\Programming\GitHub\OpenH3M\.local\h3-study\`):

| Level and view | Draw calls | Triangles drawn |
| --- | --: | --: |
| Guardian, spawn (interior corridor, two runs) | 1,154 / 1,246 | 257k / 262k |
| Valhalla, spawn | 1,552 | 356k |
| Valhalla, open view across the valley from the south cliff top | 1,142 | 381k |
| Last Resort, spawn | 1,815 | 451k |
| Last Resort, long view down the warehouse | 1,448 | 373k |
| Construct, high view down a shaft (camera may sit in a wall gap, see unknowns) | 5,016 | 268k |
| Guardian, placed camera | discarded: screenshot shows the camera outside the level | |

The profiler's per-section breakdown (`LEVEL/SECTION`, inclusive/exclusive draws) printed only a
`[global]` total in this build.

## Questions and answers

### Q1. Structure vs instanced geometry — what goes where?

**Answer.** Stock MP levels put most of their triangles in instanced geometry ("instances", %-named
pieces) and keep the structure BSP small: structure 12k–46k triangles, instances 53k–316k triangles.
Instance pieces are small: median 56–396 triangles per piece, 2–4 copies per piece on average. One-off
pieces are normal: 48–71% of pieces are placed once, but they hold only 11–38% of the instance
triangles. The largest single piece on any stock level is ~11k triangles (Snowbound, High Ground).
Large pieces (over 2,000 triangles) carry 0–60% of instance triangles depending on the level
(Valhalla 60%, High Ground 47%), so big pieces alone are not un-Bungie-like; the totals stay small.
*Source:* kit tags (table). Official doc: instancing is described as cheap copies that reuse the
original's data; a unique (one-off) instance "doesn't save anything"
(https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/art/instanceobjects/instanceobjectshome).

### Q2. Clusters and portals — how many and how are they laid out?

**Answer.** 15–49 clusters and 41–132 portals per level, roughly 2–4 portals per cluster. All are
plain two-way portals except 8 one-way portals on Snowbound and 1 door portal on High Ground. The
docs give no counts or placement rules beyond the stated goal of shutting down as much as possible.
Four portal types exist (two-way, one-way, door, no-way), set by the portal's material.
*Source:* kit tags (cluster/portal blocks, portal flags); official
https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/guides/usingportals.

### Q3. How does the engine decide what to draw?

**Answer.**
- **Clusters:** a runtime portal test every frame. From the camera's cluster, a neighbouring
  cluster is drawn if its portals overlap the current portals on screen. Portals are not hidden by
  walls; only portal-to-portal overlap counts (official). The kit's test game confirms the
  machinery: `visibility_portal_traversal`, `visibility_debug_portals`,
  `visibility_debug_visible_clusters`.
- **PVS** (potentially visible set, built at import per cluster): per the official doc it is used for
  object activation (mainly shutting AI off), not for choosing what to render.
- **Instances:** belong to clusters. Each cluster's mesh carries "instance buckets" listing which
  pieces, and which copies of them, sit in that cluster. A copy spanning several clusters is listed in
  each (Guardian: 479 copies, 569 bucket entries). Each copy has a world bounding sphere for culling.
- **Screen-size fade:** each copy fades by the on-screen size of its bounding sphere. The default
  (when neither the piece name nor the scenario sets it) is the hard-coded pair 36/30 pixels: fading
  begins near 36 px and the copy is not drawn below 30 px. Eight of the eleven stock levels use the
  default on every copy. Sandtrap and High Ground lower it to keep landmark pieces visible longer
  (10/5 on 84 copies; 20/10 on 156 copies).
- **Occluders:** there are no general occluder objects. The only occluder-like structure in the
  game data is door portals (`game_portal_to_door_occluder_block`).

*Source:* official usingportals and instanceobjectshome pages; kit tags (buckets, fade fields,
scenario `default instance fade start/end pixels` = 0 on Guardian); command and block names in
`halo3_tag_test.exe`.

### Q4. How is geometry turned into draw calls?

**Answer (tag layout, official kit data):**
- **Structure:** each cluster has exactly one mesh, with one part per material used in that cluster
  (13 parts per cluster on average; Guardian's largest has 43). All structure in a cluster that
  shares a material is therefore already combined into one part.
- **Instance pieces:** each piece has its own mesh, one part per material.
- **Subparts:** every part is split into subparts (Guardian's structure: 225 parts, 1,034 subparts),
  and every mesh has a per-mesh MOPP culling tree over its subparts and parts (238 meshes, 238 trees
  on Guardian).
- **Budget vertex count:** each part and subpart records one, computed by the tool.

**Not documented anywhere official:** whether the engine issues one draw per part or one per
visible subpart, and whether copies in a bucket are drawn in one batched (hardware-instanced) call.
Measured stock frames run 1,150–1,800 draws for 257k–451k triangles (Valhalla's open view:
381k triangles in 1,142 draws), about 250–330 triangles per draw.

### Q5. Instance counts and limits

**Answer.** Stock: 76–336 pieces and 201–1,130 placed copies per level. No official page gives
limits.
*Community* (c20 scenario_structure_bsp page): 1,024 piece definitions and 4,096 copies per BSP;
32,767 vertices and 64,000 indices per piece. The 65,535-index mesh limit was also hit in this
project's kit-15 import.

### Q6. What sets the number of draws per frame?

**Answer.** From the tag layout: the visible clusters' structure parts, plus, for every visible copy
that has not faded, its parts (one per material). Fewer materials per piece and per cluster means
fewer parts. Stock pieces average 1.3–3.4 materials (most under 2.5), and stock levels use only
43–112 materials in total.
Whether visible subparts multiply the count is open (see Q4 and the unknowns).

### Q7. Lightmaps

**Answer.**
- **Instance lighting choice:** set by the piece name. `%?` gives per-vertex, `%!` per-pixel, `%>`
  single-probe. Plain `%` gives single-probe under 8 world units, otherwise per-pixel. `(N)` scales a
  per-pixel instance lightmap (64×N square).
- **Same quality, different storage** (official):
  - per-pixel takes resolution from the structure's lightmap;
  - per-vertex costs about 20 bytes per vertex;
  - single-probe costs almost nothing but shows seams and gradients badly.
- **What stock levels use:** mostly per-vertex. Guardian 426 of 479 copies, Last Resort 1,043 of
  1,130, High Ground 708 of 857. Per-pixel is common only on Valhalla (185 of 262) and Sandtrap
  (220 of 330).
- **Draw cost:** no official source says lighting type changes the number of draws. Per-vertex
  meshes are flagged "mesh has per-instance lighting".

*Source:* official instanceobjectshome and lightmapresolution pages; kit tags.

### Q8. LOD and fade

**Answer.** Instances have no LOD models, only the screen-size fade (Q3).
`performance_throttles` scales fades for split-screen. Every stock MP level has a throttle tag with
four rows, one per local player count:
- **1 player:** every scale is 1.0; up to 2 CPU and 6 GPU dynamic lights, 5 shadow-casting objects.
- **2 players:** instance fade 0.9, object fade 0.8, decorator fade 0.8, effect LOD 0.25, no dynamic
  shadows.
- **3–4 players:** further cuts (instance fade 0.8, decorators 0.3→0, first-person shadows and object
  PRT off).

Objects have LODs (per model, not studied here). Decorators fade by distance and are "relatively
inexpensive to render" (official decorators page).
*Source:* kit tags (`guardian.performance_throttles` exported); official instanceobjectshome; Sky
Bridge has no throttle tag (irrelevant to single-player views, where all scales are 1.0).

### Q9. Shaders / render methods

**Answer.** Stock levels use 43–112 materials, almost all the standard `shader` type (Guardian: 78
shader, 9 terrain, 1 halogram; Last Resort 101/9 plus water and foliage). No official statement on
the cost of shader variety. The only official performance note is texture memory: compressed
textures are most efficient at multiples of 128
(https://learn.microsoft.com/en-us/halo-master-chief-collection/h3/misc/optimaltexture).

### Q10. Budgets the tools enforce or report

**Answer.**
- **Tool output:** the structure tag's own import report (`errors` block) on stock levels lists
  only tangent-space and UV warnings, no budget warnings.
- **What the tool stores:**
  - per-part and per-subpart budget vertex counts;
  - the scenario's BSP size class (Guardian: 1024×1024);
  - the zone-set PVS.
- **No published budget:** no official triangle, draw or memory budget for MP levels was found.
- **Engine counters:** the test game's statistics overlay has counters with maxima — instances
  visible/max, clusters visible/max, GPU lights, shadows, decorators. Its maxima were not read in
  this study.

### Q11. Which official tools report draw cost and visibility?

**Answer.**
- **Draw calls and triangles:** `dip_stats_enable 1`, then `dip_stats_dump`, writes
  `debug_dip_stats.txt` (`dip_stats_sort_toggle` switches inclusive/exclusive sorting). Used above.
- **Visibility and portals:**
  - `visibility_debug_portals 1`, `debug_pvs 1` (with `debug_view 1`), `visibility_debug_visible_clusters`;
  - `debug_instanced_geometry` with its `_bounding_spheres`, `_names` and `_vertex_counts` variants;
  - `debug_structure_complexity`, `debug_structure_cluster`.
- **Memory:** `display_zone_size_estimates`, `render_debug_query_bsp_resources`.
- **Camera and screenshots:** `debug_camera_load_text`, `screenshot <name>`.

*Source:* official usingportals page; `tool script-doc`; strings in `halo3_tag_test.exe`.

### Q12. Sky, weather, decorators

**Answer.** Skies are a scenery object per scenario (Guardian: one sky, active on its BSP; clusters
carry a sky index). Decorators are placed per cluster and are cheap (official). Not a factor in the
draw comparison above; not studied further.

## What is still unknown

1. **What one draw call corresponds to:** whether the engine issues one per part or one per visible
   subpart, and whether bucketed copies are batched. Measurable with the official profiler: same
   view, then `debug_instanced_geometry`-style toggles (`render_instanced_geometry`,
   `render_structure`), compared.
2. **The Construct reading** (5,016 draws, 268k triangles) needs a second camera position. If the
   camera sat in a wall gap outside any cluster, portal culling would not apply.
3. **Per-section breakdown:** the profiler printed only a global total. Section breakdown may need a
   profiling build or another toggle.
4. **Overlay maxima:** the statistics overlay's maximum values (e.g. instances visible per frame)
   were not read.
5. **Renderer difference:** tag_test uses the MCC PC renderer, while our Sky Bridge numbers come
   from the recompiled Xbox 360 renderer in the PC port. Absolute draw counts may differ between the
   two; comparisons should be made within one renderer.

---

## Sky Bridge against the official pattern

Sky Bridge source = the untouched Halo Online level source (`s3d_sky_bridgenew.original.ass`).
Cluster and portal counts come from the installed map via this project's own cache reader
(*earlier project measurement*). Kit tags for Sky Bridge were not used: they come from the
2026-11-26 fold-all import that was killed, built from the modified `.ass`.

| Measure | Stock range | Sky Bridge | Verdict |
| --- | --- | --- | --- |
| Placed instance copies | 201–1,130 | 961 | normal (Last Resort has more) |
| Instance pieces | 76–336 | 247 | normal |
| Instance triangles, all copies | 53k–316k | **796k** | 2.5× the heaviest stock level |
| Triangles per piece, median | 56–396 | **683** | 2–10× stock |
| Largest piece | ≤ 11k | **21k** (6 pieces over 13k) | above anything stock |
| Share of instance triangles in pieces over 2,000 triangles | 0–60% | 61% | at the top of the stock range |
| Pieces placed once / their share of instance triangles | 48–71% / 11–38% | 47% / 44% | slightly more triangles in one-offs |
| Materials per piece, average | 1.3–3.4 (mostly < 2.5) | **4.3** | 2× stock |
| Instance parts (copies × materials) | 408–1,899 | **2,925** | 1.5× the heaviest stock level |
| Distinct shaders referenced | 43–112 materials | **281** distinct shaders (390 material entries) | 3–6× stock |
| Structure triangles | 12k–46k | 97k | 2× stock |
| Clusters / portals | 15–49 / 41–132 | 53 / 246 | plenty of portals, but almost everything can see everything |
| Pieces with a custom fade | 0 on 8 levels; Sandtrap/High Ground lower it on landmarks | 260 copies set to 6/5 px | small pieces stay drawn until 5 px instead of 30 px |
| Per-vertex lighting share | dominant (e.g. 89–92%) | 53% (508 of 961) | mixed |
| Draws per frame at the pain views | 860–1,815 (kit profiler, MCC PC renderer) | 696–1,335 (kit profiler, kit build of the source; step 0) / 2,000–2,900 (PC port, installed converted build, *earlier project measurement*) | normal on the kit's own build |

**Where Sky Bridge departs from how Bungie builds a level:**
1. **Too many materials per piece and too many shaders.** Every part is a separate draw, so each
   copy costs about 3 draws versus Bungie's 1.3–2.5. With 281 shaders, nearly every piece has its
   own material set, so nothing shares parts.
2. **Heavier pieces and far more triangles overall.** The median piece is 683 triangles against
   Bungie's 56–396, the largest is 21k against 11k, and the total is 796k against at most 316k.
   Big pieces as such are within the stock pattern (Valhalla); the weight is not.
3. **The default screen-size fade is turned down** on 260 copies.
4. **Portals don't separate the open area.** That is the level's design (one big open space) and
   portals cannot fix it: the runtime test sees through any portal that is on screen.

**Kit-15 merge in this light.** It combined everything into 171 neighbourhood pieces, the
opposite of the official pattern of small reused pieces plus per-cluster structure. Draws rose
from ~2,880 to ~4,050. Why is still unknown (Q4, unknown 1).

### Step 0 result — the untouched source, built by the kit, measured with the official profiler (2026-11-27)

What was done: `s3d_sky_bridgenew.original.ass` and `s3d_reactor.original.ass` imported unchanged under scratch
names (`levels\multi\sb_study`, `levels\multi\rx_study`) with `tool structure`, draft-lit with the kit's own farm
(`speed-review/bake.py ... draft`), and measured in `halo3_tag_test` with `dip_stats_dump` and a screenshot per view.
Same views, same counter, same renderer as the stock readings. Scripts: `h3-level-study/level_views.py`,
`run_levels.sh`, `run_tag_test.py`; dumps and screenshots in `.local/h3-study` (`dip_sbe_*`, `dip_rxe_*`, `dip_ste_*`).

**Test-game trap found first.** The kit's test game draws every import warning stored in the structure tag as
on-screen error geometry. Sky Bridge's import stored ~15,000 tangent-space warnings (plus portal leaks and
broken-instancing notes), and drawing them cost **16,000–20,000 draws** per frame — 21,400–23,100 in total at the pain
views. `error_geometry_hide_all` removes them; the screenshots are otherwise unchanged. Built cache files do not carry
this overlay. Earlier readings without that command are not level cost. The draft lighting did not change draw counts
(unlit and lit runs agreed to within 10 draws).

**Level cost with the error overlay hidden** (draws per frame; "pieces" = all minus instanced geometry switched off):

| View | Total | Placed pieces | Rest (structure, sky, transparents) | Triangles |
| --- | --- | --- | --- | --- |
| Sky Bridge pain view 1 | 696 | 440 | 256 | 364k |
| Sky Bridge pain view 2 | 887 | 577 | 310 | 424k |
| Sky Bridge pain view 3 | 1,335 | 903 | 432 | 466k |
| Zanzibar open view (stock) | 1,289 | 908 | 381 | 216k |
| Riverworld open view (stock) | 857 | 413 | 444 | 219k |
| Valhalla / Last Resort spawn (stock, earlier reading) | 1,552 / 1,815 | — | — | 381k / 451k |

**What this means.** Built natively by the kit from its untouched source, Sky Bridge costs **as many draws as a stock
level**, on the official counter. Triangles are at the top of the stock range (Last Resort level), not far above
it. The material and piece outliers listed above are real, but on this renderer they do not translate into an
abnormal draw count.

**Unknown 1 settled (draw = visible part, not subpart).** Sky Bridge's lit tag has 528 structure parts / 4,359
subparts and 1,617 instance-piece parts / 29,486 subparts; Zanzibar and Riverworld are subdivided just as finely
(9–33 triangles per subpart). Measured draws (256–432 structure, 440–903 pieces) fit one draw per visible part and are
an order of magnitude below the subpart counts. Fragmentation into subparts is normal and not a cost driver.

**The gap that remains.** The build the user plays (`SkyBridge_20261119_v1`) did not come from this source through the
kit: it is the compiled H3 MCC Workshop map converted by this project's pipeline. On the PC port it ran 2,000–2,900
draws at the same views (*earlier project measurement*, different renderer and counter). There is no PC-port reading of
a stock level yet, so it is not known whether the PC port simply counts higher, or whether the converted build draws
more than the kit's own build of the same level.

**PC-port calibration (2026-11-27).** Same spot measured with both counters (PC port: `run_pc_port.py` benchmark,
uncapped, `--d3d12_log_frame_workload`; kit: `level_views.py` with the camera at the PC port's logged eye position;
screenshots match). Scripts `h3-level-study/pc_views.sh`; outputs in `.local/h3-study/pc`.

| Spot | Kit profiler draws / triangles | PC port draws / triangles / FPS | PC ÷ kit draws |
| --- | --- | --- | --- |
| Last Resort, near spawn | 809 / 283k | 1,115 / 308k / 46.4 | 1.4 |
| Valhalla, near spawn | 1,142 / 410k | 1,414 / 287k / 45.1 | 1.2 |
| Sky Bridge views 1–3 | 696 / 887 / 1,335 (kit build of the source, scratch scenario, no objects) | 1,987 / 2,430 / 2,872; 630k / 859k / 982k; 38.5 / 33.6 / 32.1 (installed converted build) | 2.2–2.9 |

The PC port counts stock levels about 1.2–1.4× the kit profiler. The installed Sky Bridge reads 2.2–2.9× the kit's
own build of the same source and pushes about twice the triangles. Not yet separated: the installed scenario's
objects (the scratch scenario has none) versus the conversion itself.

**Full kit rebuild from the source (2026-11-27).** `s3d_sky_bridgenew.original.ass` re-imported into the real
`s3d_sky_bridgenew` scenario (all objects, sky, spawns), draft-lit, built by the kit, converted (`kit_to_360.sh
sky-bridge orig-01`) and packaged (`package_and_measure.sh ... SkyBridge_20261127_v1`; preview artwork reused from
the installed build because the Workshop pack is gone). PC port: 35.9 / 34.2 / 29.7 FPS, 2,218 / 2,832 / 4,085 draws,
825k / 1,133k / 1,486k triangles. Installed build on the same day: 38.5 / 33.6 / 32.1 FPS. **A plain kit rebuild
does not help**; the test package was deleted. The screenshots render correctly.
- Kit profiler on the full scenario: 2,314 / 2,950 draws at views 2–3 with objects, about what the installed build
  reads on the PC port. So the conversion is not what adds cost.
- With objects, first person and error markers hidden, the full scenario still reads 1,294–1,901 at view 2 against
  887 for the scratch scenario built from the same `.ass`. Placed pieces account for most of the gap (850 vs 577
  draws in one paired reading). The distant tower skyline is placed-piece geometry, not sky (`render_sky 0`
  changes 7 draws). Why the same geometry draws more under the real scenario is not established.
- **Noise:** the same view of the same build read 1,901 and 1,294 in two kit runs. Single kit readings vary by up
  to a third; only large gaps are conclusions.

**Reactor: views not verified.** The three Reactor points from `.local/pc-port/reactor-points.txt` land on open
terrain in the scratch import (206 / 210 / 691 draws), not inside the reactor where the slowdown was reported. The
points may be in a different coordinate frame from the source. No Reactor conclusion is drawn.

### What an official-style rebuild would change (proposal; nothing built)

**Step 0 — measure the original with the official profiler first.** Import the untouched
`s3d_sky_bridgenew.original.ass` under a separate scratch scenario name, so it does not touch the
in-progress Sky Bridge or Elongation kit tags. Run `halo3_tag_test` with `dip_stats_dump` and
screenshots at the three pain views and at the Valhalla/Last Resort comparison views. This gives
one renderer, one counter, stock versus Sky Bridge. In the same runs, settle unknown 1 (part vs
subpart vs batched copies) with the render toggles, so the plan below rests on measured cause.

**Step 1 — material consolidation (largest expected effect, no shape change).** Map the 281 shaders
onto a stock-sized set, about 60–110, by merging near-identical surfaces: same texture with different
lightmap settings, colour variants, duplicated panel shaders. Target at most 2 materials per piece,
like Bungie's.
- Prefer stock Halo 3 shaders where an equivalent exists (binding asset policy).
- Expected effect: instance parts fall from 2,925 towards ~1,500–1,900, inside the stock range.

**Step 2 — move large one-off pieces into the structure (lower confidence; decide after step 0).**
- Pieces over ~2,000 triangles used once or twice become structure geometry. The per-cluster mesh
  then combines them by material (structure layout, Q4). Whether this lowers draws depends on
  unknown 1.
- Repeated small pieces (columns, rails, lights) stay instances, the way Bungie uses them.
- Check the structure against the 65,535-index limit per cluster mesh part.

**Step 3 — restore default fades** (drop the `@6-5` suffixes) except on true landmarks, as Sandtrap
and High Ground do.

**Step 4 — re-measure** each step with the same official profiler views and the PC-port pain views.
The step is accepted only if draws fall and the screenshots match.

Each step is a separate kit import, so steps 1–3 can be judged one at a time, one map at a time,
with nothing installed until the user approves.

## Reduction to 360 budgets (2026-11-27)

User: "Scale the map back to 360 numbers", then "Every spot needs to be at least 42" (PC port, uncapped, the three
pain spots). Tools: `speed-review/reduce_to_360.py` (look-alike material merge, Blender Decimate to 34%),
`speed-review/merge_into_structure.py` (visible geometry out of the pieces; collision kept on the pieces).

| Build (package) | What changed | Spot 1 / 2 / 3 FPS | PC draws per frame |
|---|---|---|---|
| Installed `SkyBridge_20261119_v1` | — | 38.5 / 33.6 / 32.1 | 1,987 / 2,430 / 2,872 |
| `SkyBridge_20261127_v2` | pieces decimated to 34%, at most 2 materials each (broke two signs) | 40.1 / 39.3 / 33.9 | 1,653 / 2,161 / 3,006 |
| `SkyBridge_20261127_v3` | visible geometry grouped into 64 render-only instances on a 24 wu grid, 40-material palette plus every non-plain shader; collision on invisible pieces | 40.2 / 36.9 / 37.7 | 2,126 / 2,625 / 3,021 |

Findings:
- Material symbols: tool.exe holds the table `%#?!@*$^-&=.;)><|~({}[` (Halo 2 order). The built structure confirms
  `!` = render only (instance flag "render only") and an `@` child or `@` material = collision only ("collidable not
  for render"). All-`!` pieces with no `@` model have no collision in the shipped map either (empty collision BSP).
- An instance's parent field is read as a position in the instance list; after inserting or removing instances
  renumber them (`ass_io.renumber`). Both "bad scale (inf)" and "bad rotation (0,0,0/0)" crashes at
  intermediate_scene.cpp #1106 were this.
- An instance definition section may hold at most 32,767 vertices after the tool's own splitting (50,095 failed).
- Putting 300k decimated triangles into the structure as render-only geometry crashed the plane builder
  ("unable to converge", connected_geometry_plane_builder.cpp #4092). Structure collision cannot take the pieces'
  collision anyway (32,767 surfaces per small collision BSP).
- Sky Bridge cluster 2 covers nearly the whole play space, so per-cluster grouping is useless; grid cells were used.
- The kit's draw count and the PC port's draws/triangles did not predict PC FPS between these builds. With
  `--d3d12_log_present_timing` the PC port spends 25–27 ms of a 28–30 ms frame in GPU work at all three spots
  (native resolution; `resolution_scale` is already 1), and every other frame the guest waits 20–28 ms on a
  4 KB resolve readback (`resolve-cache-miss`), so CPU and GPU time add instead of overlapping. 42 FPS needs
  about 21 ms of GPU work per frame.
