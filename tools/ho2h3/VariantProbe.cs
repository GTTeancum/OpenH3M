// variant <pak> [map id]: the package's map files (ElDewrito keeps each map's default object layout in its map file's
// map variant): objects with their object tag (quota -> tag index), position and multiplayer settings
using System;
using System.IO;
using System.Linq;
using TagTool.BlamFile;
using TagTool.Cache;
using TagTool.IO;

namespace Ho2H3
{
    static class VariantProbe
    {
        public static MapFile Read(GameCacheModPackage pak, int i)
        {
            var s = pak.BaseModPackage.MapFileStreams[i]; s.Position = 0;
            var mf = new MapFile(); mf.Read(new EndianReader(s, EndianFormat.LittleEndian)); return mf;
        }
        public static int Run(string[] a)
        {
            var pak = (GameCacheModPackage)Program.OpenPak(a[1]);
            var mp = pak.BaseModPackage;
            for (int i = 0; i < mp.MapFileStreams.Count; i++)
            {
                MapFile mf; try { mf = Read(pak, i); } catch (Exception ex) { Console.WriteLine($"map {i} id {mp.MapIds[i]}: {ex.Message}"); continue; }
                var v = mf.MapFileBlf?.MapVariant?.MapVariant; string name = mf.Header?.GetName() ?? "?";
                Console.WriteLine($"map {i} id {mp.MapIds[i]} {name} scenario {mf.Header?.GetScenarioPath()} variant objects {v?.VariantObjectCount} scenario objects {v?.ScenarioObjectCount} quotas {v?.PlaceableQuotaCount}");
                if (v == null || (a.Length > 2 && mp.MapIds[i].ToString() != a[2])) continue;
                var counts = new System.Collections.Generic.Dictionary<string, int>();
                for (int k = 0; k < v.Objects.Length; k++)
                {
                    var o = v.Objects[k]; if (o.QuotaIndex < 0 || o.QuotaIndex >= v.Quotas.Length) continue;
                    int ti = v.Quotas[o.QuotaIndex].ObjectDefinitionIndex; var t = ti >= 0 && ti < pak.TagCache.Count ? pak.TagCache.GetTag(ti) : null;
                    var key = t == null ? $"tag {ti}" : $"{t.Group.Tag}:{t.Name}"; counts[key] = counts.TryGetValue(key, out var n) ? n + 1 : 1;
                    if (a.Length > 3) Console.WriteLine($"  [{k}] {key} at {o.Position} type {o.Properties?.Type} team {o.Properties?.Team} spawn {o.Properties?.SpawnTime} flags {o.Flags}");
                }
                foreach (var kv in counts.OrderByDescending(x => x.Value)) Console.WriteLine($"  {kv.Value,4} {kv.Key}");
            }
            return 0;
        }
    }
}
