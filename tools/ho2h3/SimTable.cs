// Scenario simulation definition table: the object, effect and damage definitions the game may create through its
// simulation (network) layer, which Forge uses even offline. A Forge creation message carries a 12-bit index into this
// table and the game resolves it to the definition (sub_824256E0); an empty table resolves every item to "no object"
// and Forge crashes in forge_object_radius (0x822835E0) with -1. Stock Sandbox: 1580 entries, every Forge palette object
// included. Halo Online's scenarios convert with an empty table (Void, Icebox, Sword Base, Reflection, Breakneck: 0
// entries; user play test 2026-11-23: Void crashed as soon as an object was placed). The table is rebuilt from the slot's
// own stock table (entries whose tags are in the converted map) plus every converted definition of the simulated
// groups, within the 12-bit limit, sorted by tag handle (binary search). Map-agnostic.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using TagTool.Cache;
using TagTool.Tags.Definitions;

namespace Ho2H3
{
    public static class SimTable
    {
        static readonly string[] Groups = { "bipd", "vehi", "weap", "eqip", "bloc", "scen", "mach", "ctrl", "proj", "crea", "gint", "term", "ssce", "efsc", "effe", "jpt!" };

        public static void Build(GameCache ho, Scenario scn, IEnumerable<CachedTag> converted, Func<string, (GameCache c, Stream s)> h3, string basis, string basisScenario,
                                 Func<string, CachedTag> stockTag, Func<CachedTag, bool> stockRef, Func<CachedTag, uint> datumOf, List<string> log)
        {
            var list = new List<CachedTag>(); var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            void Add(CachedTag t) { if (t == null || list.Count >= 4095) return; if (seen.Add(t.Group.Tag + ":" + t.Name)) list.Add(t); }
            // Forge palette objects first (the menu's own items)
            foreach (var f in typeof(Scenario).GetFields().Where(f => f.Name.StartsWith("Sandbox")))
                foreach (var e in (f.GetValue(scn) as List<Scenario.SandboxObject>) ?? new()) Add(e.Object);
            int palette = list.Count;
            // the slot's stock table, for the stock objects, effects and damage the converted map still contains
            int stock = 0;
            try
            {
                var (bc, bs) = h3(basis);
                var bscn = bc.Deserialize<Scenario>(bs, bc.TagCache.GetTag(basisScenario, "scnr"));
                foreach (var e in bscn.SimulationDefinitionTable ?? new())
                {
                    if (e.Tag == null) continue;
                    var st = stockTag(e.Tag.Group.Tag + ":" + e.Tag.Name);
                    if (st != null && stockRef(st)) { int n0 = list.Count; Add(st); if (list.Count > n0) stock++; }
                }
            }
            catch (Exception ex) { log.Add($"simulation table: slot scenario not read ({ex.Message})"); }
            // every converted definition of the simulated groups
            int conv = 0;
            foreach (var t in converted) if (Groups.Any(g => t.IsInGroup(g))) { int n0 = list.Count; Add(t); if (list.Count > n0) conv++; }
            // the game finds a definition's table index by binary search with the comparator a - b over the 32-bit tag
            // handles (sub_82425660 -> sub_82105770, comparator sub_8234D568): the table must be sorted by handle as a signed
            // number (unsorted, the search missed most converted objects and Forge still crashed)
            int unresolved = list.Count(t => datumOf(t) == 0xFFFFFFFF);
            list = list.Where(t => datumOf(t) != 0xFFFFFFFF).OrderBy(t => unchecked((int)datumOf(t))).ToList();
            int before = scn.SimulationDefinitionTable?.Count ?? 0;
            scn.SimulationDefinitionTable = list.Select(t => new Scenario.SimulationDefinitionTableBlock { Tag = t }).ToList();
            log.Add($"simulation table: {before} entries in the source -> {list.Count} ({palette} Forge palette objects, {stock} more from the slot's stock table, {conv} more converted definitions; {unresolved} without a handle left out; sorted by handle){(list.Count >= 4095 ? "; 12-bit limit reached" : "")}");
        }
    }
}
