// Halo Online (ODST-style) lightmaps -> Halo 3 retail.
// Halo Online keeps each structure's lightmap in its own scenario_lightmap_bsp_data tag (Lbsp), referenced from the
// scenario lightmap's Per Pixel Lightmap Data References in scenario BSP order; Halo 3 retail has no Lbsp group and
// keeps the same data inline in the scenario lightmap's Lightmaps block (TagTool ScenarioLightmap: Lightmaps,
// MaxVersion Halo3Retail, Original). The structure's render geometry lives in the Lbsp (TagTool's Reach port put it
// there; the sbsp's own geometry is empty), while Halo 3 draws the structure from the sbsp geometry with the same mesh
// list in the lightmap (stock Guardian: 238 meshes in both): the sbsp takes the Lbsp's geometry object, so both share
// one converted resource.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using TagTool.Cache;
using TagTool.Geometry;
using TagTool.Tags.Definitions;

namespace Ho2H3
{
    public static class Lightmaps
    {
        public static void Merge(GameCache cache, Stream stream, CachedTag scenarioTag, List<CachedTag> convert, Dictionary<int, object> preDefs, List<string> log)
        {
            var scn = cache.Deserialize<Scenario>(stream, scenarioTag);
            var sldtTag = scn.Lightmap; if (sldtTag == null || !convert.Any(t => t.Index == sldtTag.Index)) { log.Add("lightmap: none converted"); return; }
            var sldt = cache.Deserialize<ScenarioLightmap>(stream, sldtTag);
            int nb = scn.StructureBsps?.Count ?? 0;
            var lbsp = new ScenarioLightmapBspData[nb];
            var refs = sldt.PerPixelLightmapDataReferences ?? new List<ScenarioLightmap.DataReferenceBlock>();
            for (int i = 0; i < Math.Min(nb, refs.Count); i++)
                if (refs[i]?.LightmapBspData != null) lbsp[i] = cache.Deserialize<ScenarioLightmapBspData>(stream, refs[i].LightmapBspData);
            sldt.Lightmaps = new List<ScenarioLightmapBspData>();
            for (int i = 0; i < nb; i++)
            {
                var l = lbsp[i] ?? new ScenarioLightmapBspData { BspIndex = (short)i, Geometry = new RenderGeometry() };
                sldt.Lightmaps.Add(l);
                var sbspTag = scn.StructureBsps[i].StructureBsp;
                if (lbsp[i]?.Geometry?.Meshes?.Count > 0 && sbspTag != null && convert.Any(t => t.Index == sbspTag.Index))
                {
                    var sbsp = cache.Deserialize<ScenarioStructureBsp>(stream, sbspTag);
                    sbsp.Geometry = lbsp[i].Geometry; preDefs[sbspTag.Index] = sbsp;
                    log.Add($"lightmap: {sbspTag.Name} takes its lightmap BSP's geometry ({lbsp[i].Geometry.Meshes.Count} meshes)");
                }
                else log.Add($"lightmap: bsp {i} {(lbsp[i] == null ? "has no lightmap BSP (empty entry)" : "keeps its own geometry")}");
            }
            sldt.PerPixelLightmapDataReferences = new List<ScenarioLightmap.DataReferenceBlock>();
            sldt.PerVertexLightmapDataReferences = new List<CachedTag>();
            preDefs[sldtTag.Index] = sldt;
        }
    }
}
