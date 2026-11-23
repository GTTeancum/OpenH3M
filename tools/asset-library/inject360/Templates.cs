// templates <mcc map> <target 360 map> <folder of stock 360 maps> <root tag>...
// For every shader template the roots need: the same template if any stock 360 map has it, otherwise the nearest one
// across all of those maps (same cost rule as the port). Prints one line per template the target map lacks:
//   GRAFT <tab> <donor map path> <tab> <template name> <tab> exact|nearest for <wanted>
// so the caller can `graft` them into the target before running `port`, which then finds them by name.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Blamite.Blam;
using Blamite.Injection;
using Blamite.Serialization;
using Blamite.Util;
using Inject360;

partial class Program
{
    static int TemplatePlan(EngineDatabase db, string mccPath, string x360Path, string donorDir, string[] roots)
    {
        using (var src = new Cache(db, mccPath))
        using (var dst = new Cache(db, x360Path))
        {
            var convert = new List<ITag>(); var reuse = new List<ITag>(); var noPlugin = new List<ITag>(); var built = new Dictionary<uint, DataBlockBuilder>();
            Walk(src, dst, roots, convert, reuse, noPlugin, built);
            int rmt2 = CharConstant.FromString("rmt2");
            var needed = convert.Where(t => t.Group.Magic == rmt2).Select(t => src.Name(t)).Distinct(StringComparer.OrdinalIgnoreCase).ToList();

            // every template any stock map has -> the first map that has it (the target itself first)
            var owner = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (var k in dst.ByName.Keys.Where(k => k.StartsWith("rmt2:"))) owner[k.Substring(5)] = x360Path;
            foreach (var map in Directory.GetFiles(donorDir, "*.map").OrderBy(p => p, StringComparer.OrdinalIgnoreCase))
            {
                string file = Path.GetFileName(map).ToLowerInvariant();
                if (file == "shared.map" || file == "campaign.map" || file == "mainmenu.map" || Path.GetFullPath(map).Equals(Path.GetFullPath(x360Path), StringComparison.OrdinalIgnoreCase)) continue;
                try
                {
                    using (var c = new Cache(db, map))
                    {
                        if (c.Engine.Name != dst.Engine.Name) continue;
                        foreach (var k in c.ByName.Keys.Where(k => k.StartsWith("rmt2:"))) if (!owner.ContainsKey(k.Substring(5))) owner[k.Substring(5)] = map;
                    }
                }
                catch (Exception ex) { Console.Error.WriteLine("skipped " + map + ": " + ex.Message); }
            }

            var schemas = new Dictionary<string, Schema>(); var trees = new Dictionary<string, Elem>(StringComparer.OrdinalIgnoreCase);
            var rule = new ShaderRule(owner.Keys,
                key =>
                {
                    if (trees.TryGetValue(key, out var e)) return e;
                    if (!dst.ByName.TryGetValue(key, out var t)) return null;
                    var p = dst.Plugin(t.Group.Magic); if (!schemas.TryGetValue(p, out var s)) schemas[p] = s = Schema.Load(p, 0x10, 0x14, 0xC);
                    return trees[key] = TagTree.Read(dst.File, dst.Reader, t, s);
                },
                key => dst.ByName.ContainsKey(key), null, null, null, null);
            int exact = 0, nearest = 0, present = 0;
            foreach (var name in needed)
            {
                int before = rule.Log.Count;
                var chosen = rule.Choose(name); if (chosen == null) continue;
                bool wasNearest = rule.Log.Skip(before).Any(l => l.Contains("using nearest"));
                if (owner[chosen].Equals(x360Path, StringComparison.OrdinalIgnoreCase)) { present++; if (wasNearest) Console.WriteLine("KEEP\t" + chosen + "\tnearest for " + name + " (already on the target; no stock map has a closer one)"); continue; }
                if (wasNearest) nearest++; else exact++;
                Console.WriteLine("GRAFT\t" + owner[chosen] + "\t" + chosen + "\t" + (wasNearest ? "nearest for " + name : "exact"));
            }
            Console.WriteLine($"templates needed {needed.Count} | on the target {present} | to borrow: {exact} exact, {nearest} nearest | stock templates known {owner.Count}");
        }
        return 0;
    }
}
