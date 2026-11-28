// Forge palette from ElDewrito's forge globals (map cfg "forge_palette <forg tag> ; <object name regex> ; <scenario block> [; keep_stock]").
// ElDewrito keeps its Forge menu in multiplayer\forge_globals, not in the scenario; Halo 3 keeps it in the scenario's
// sandbox blocks. The matching palette objects are walked and converted like any other tag (extra roots) and listed in
// the named block, replacing that block's stock entries (or after them with ";keep_stock").
// Map-agnostic. Display names: the object's file name as a string id (Halo 3 shows names it has no text for as-is or blank).
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using TagTool.Cache;
using TagTool.Common;
using TagTool.Tags.Definitions;

namespace Ho2H3
{
    public static class ForgePalette
    {
        public static List<(string forg, string regex, string block)> Specs = new List<(string, string, string)>();
        public static bool KeepStock;
        public static float Budget;
        // map cfg "forge_prices <json>" (ho2h3 reachpal output): price and maximum per object from a Reach Forge palette
        // (Void: Forge World's own). The first entry for an object wins, ordinary palettes before the "thorage" ones.
        public static Dictionary<string, (int price, int max)> Prices;
        public static void LoadPrices(string path)
        {
            Prices = new Dictionary<string, (int, int)>(StringComparer.OrdinalIgnoreCase);
            var rows = System.Text.Json.JsonSerializer.Deserialize<List<Dictionary<string, System.Text.Json.JsonElement>>>(File.ReadAllText(path));
            foreach (var r in rows.OrderBy(r => r["palette"].GetString().Contains("thorage") ? 1 : 0))
            {
                var obj = r["object"].GetString(); if (string.IsNullOrEmpty(obj)) continue;
                var key = obj.Substring(obj.IndexOf(':') + 1);
                if (!Prices.ContainsKey(key)) Prices[key] = (r["price"].GetInt32(), r["max"].GetInt32());
            }
        }   // map cfg "forge_budget <n>" (Void: Forge World's 10000); otherwise the slot's stock budget   // ";keep_stock" in the spec: the basis's stock entries stay ahead of the converted ones
        static readonly List<(string block, CachedTag obj, int max, string display)> Items = new List<(string, CachedTag, int, string)>();
        // display names for the Forge menu (string id -> text), written into the map's sandbox string list after the build
        public static readonly Dictionary<string, string> DisplayNames = new Dictionary<string, string>();

        // before the walk: the palette objects to convert
        public static IEnumerable<CachedTag> Roots(GameCache ho, Stream s, List<string> log)
        {
            foreach (var (forg, regex, block) in Specs)
            {
                var fg = ho.Deserialize<ForgeGlobalsDefinition>(s, ho.TagCache.GetTag(forg, "forg"));
                var re = new Regex(regex, RegexOptions.IgnoreCase);
                var seen = new HashSet<int>();
                foreach (var it in fg.Palette.Where(p => p.Object != null && re.IsMatch(p.Object.Name)))
                    if (seen.Add(it.Object.Index)) Items.Add((block, it.Object, it.MaxAllowed, it.Name));
                log.Add($"forge palette: {Items.Count(i => i.block == block)} objects from {forg} matching {regex} -> {block}");
            }
            return Items.Select(i => i.obj);
        }

        // on the converted scenario: basis entries + palette objects
        public static void Apply(GameCache ho, Scenario scn, Func<string, (GameCache c, Stream s)> h3, string basis, string basisScenario,
                                 Func<string, CachedTag> stockTag, Func<CachedTag, bool> stockRef, List<string> log)
        {
            if (Budget > 0) { scn.SandboxBudget = Budget; log.Add($"forge palette: budget {Budget} (map cfg)"); }
            if (Items.Count == 0 && scn.SandboxBudget > 0) return;
            var (bc, bs) = h3(basis);
            var bscn = bc.Deserialize<Scenario>(bs, bc.TagCache.GetTag(basisScenario, "scnr"));
            // Forge budget: the converted scenario has none (Void: $0); the slot's stock budget is used
            if (scn.SandboxBudget <= 0 && bscn.SandboxBudget > 0) { scn.SandboxBudget = bscn.SandboxBudget; log.Add($"forge palette: budget {bscn.SandboxBudget} from the slot's scenario"); }
            if (Items.Count == 0) return;
            foreach (var block in Items.Select(i => i.block).Distinct())
            {
                var f = typeof(Scenario).GetField(block) ?? throw new ArgumentException("no scenario block " + block);
                var list = new List<Scenario.SandboxObject>();
                foreach (var e in KeepStock ? (List<Scenario.SandboxObject>)f.GetValue(bscn) ?? new List<Scenario.SandboxObject>() : new List<Scenario.SandboxObject>())
                {
                    if (e.Object == null) continue;
                    var st = stockTag(e.Object.Group.Tag + ":" + e.Object.Name);
                    if (st == null || !stockRef(st)) continue;
                    list.Add(new Scenario.SandboxObject { Object = st, Name = ho.StringTable.GetOrAddString(bc.StringTable.GetString(e.Name)), MaxAllowed = e.MaxAllowed, Cost = e.Cost });
                }
                int stock = list.Count; var unpriced = new List<string>();
                foreach (var it in Items.Where(i => i.block == block))
                {
                    var key = Path.GetFileName(it.obj.Name);
                    int max = it.max > 0 ? it.max : 20; float cost = 1; bool priced = false;
                    if (Prices != null && Prices.TryGetValue(it.obj.Name, out var pr)) { cost = pr.price; if (pr.max > 0) max = pr.max; priced = true; }
                    if (Prices != null && !priced) unpriced.Add(key);
                    list.Add(new Scenario.SandboxObject { Object = it.obj, Name = ho.StringTable.GetOrAddString(key), MaxAllowed = max, Cost = cost });
                    if (!string.IsNullOrWhiteSpace(it.display))
                    {
                        // ElDewrito's names are all capitals ("ROCK, SMALL"); Halo 3's Forge menu uses "Rock, Small"
                        var d = it.display.Trim();
                        if (d == d.ToUpperInvariant())
                        {
                            d = System.Globalization.CultureInfo.InvariantCulture.TextInfo.ToTitleCase(d.ToLowerInvariant());
                            d = System.Text.RegularExpressions.Regex.Replace(d, @"(\d)X(\d)", "$1x$2").Replace("Xlarge", "XLarge").Replace("Xsmall", "XSmall");   // "4x4", "XLarge"
                        }
                        DisplayNames[key] = d;
                    }
                }
                f.SetValue(scn, list);
                log.Add($"forge palette: {block}: {stock} stock Halo 3 entries + {list.Count - stock} converted" + (Prices != null ? $"; prices from the map cfg's palette, {unpriced.Count} without a price ($1): {string.Join(", ", unpriced)}" : ""));
            }
        }
    }
}
