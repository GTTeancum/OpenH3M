// convert <pak> <scenario> <basis 360 map> <output map> [options]
//   --substitute grp:name=name   stock Halo 3 tag for a Halo Online tag (weapons, equipment, props: map cfg)
//   --skip grp                   group never converted (references cleared)
//   --remove grp:name            tag left out (references cleared)
//   --salt file                  360 resource page salt
// Walks the scenario's dependencies in the package and decides per tag:
//   convert     package-owned, group exists in Halo 3, not a shader program: TagTool definition -> Halo 3 360 blocks
//   reuse       a stock Halo 3 tag of the same group and name is in the basis map (referenced by name)
//   graft       ... in another stock map: copied in first (ReachPort graftinto), then referenced by name
//   substitute  cfg: another stock Halo 3 tag
//   drop        anything else: references cleared, listed in <output>.unresolved.txt
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Blamite.Blam;
using Blamite.Injection;
using Blamite.IO;
using Blamite.Serialization;
using Blamite.Serialization.Settings;
using Blamite.Util;
using TagTool.Cache;
using TagTool.Cache.HaloOnline;
using TagTool.Serialization;
using TagTool.Tags;
using BDatum = Blamite.Blam.DatumIndex;

namespace Ho2H3
{
    public class Map : IDisposable
    {
        public static EngineDatabase Db = XMLEngineDatabaseLoader.LoadDatabase(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Formats", "Engines.xml"));
        public Stream Stream; public EndianReader Reader; public ICacheFile File; public EngineDescription Engine;
        public Dictionary<string, ITag> ByName = new Dictionary<string, ITag>(StringComparer.OrdinalIgnoreCase);
        public Map(string path, bool write = false)
        {
            Stream = write ? System.IO.File.Open(path, FileMode.Open, FileAccess.ReadWrite, FileShare.None) : System.IO.File.OpenRead(path);
            Reader = new EndianReader(Stream, Endian.BigEndian);
            File = CacheFileLoader.LoadCacheFile(Reader, path, Db, out Engine);
            foreach (var t in File.Tags) { if (t?.Group == null || t.MetaLocation == null) continue; var n = File.FileNames.GetTagName(t); if (n != null) ByName[CharConstant.ToString(t.Group.Magic) + ":" + n] = t; }
        }
        public HashSet<string> Groups => new HashSet<string>(File.TagGroups.Select(g => CharConstant.ToString(g.Magic)));
        public void Dispose() { Stream?.Dispose(); }
    }

    public static class Converter
    {
        // shader programs and render method definitions are never converted: Halo Online's are compiled for the PC
        static readonly HashSet<string> ShaderStage = new HashSet<string> { "rmt2", "rmdf", "rmop", "vtsh", "pixl", "glvs", "glps" };
        static readonly HashSet<string> NeverConvert = new HashSet<string> { "rmt2", "rmdf", "rmop", "vtsh", "pixl", "glvs", "glps", "rasg" };
        public static string ReachPort = @"C:\Programming\GitHub\OpenH3M\.local\asset-tools\src\Assembly\src\ReachPort\bin\dev\ReachPort.exe";

        public static int Run(string[] a)
        {
            string pak = a[1], scenario = a[2], basis = a[3], output = a[4], salt = null, basisScenario = null;
            var subst = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase); var groupSubst = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase); var skip = new HashSet<string>(); var remove = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            for (int i = 5; i < a.Length; i++)
            {
                if (a[i] == "--substitute") { var v = a[++i]; int e = v.IndexOf('='); subst[v.Substring(0, e)] = v.Substring(e + 1); }
                else if (a[i] == "--skip") skip.Add(a[++i]);
                else if (a[i] == "--remove") remove.Add(a[++i]);
                else if (a[i] == "--salt") salt = a[++i];
                else if (a[i] == "--place") { var w = a[++i].Split(' ', StringSplitOptions.RemoveEmptyEntries); var ic = System.Globalization.CultureInfo.InvariantCulture; Placements.Extra.Add((w[0], double.Parse(w[1], ic), double.Parse(w[2], ic), double.Parse(w[3], ic), w.Length > 4 ? double.Parse(w[4], ic) : 0)); }
                else if (a[i] == "--ramp-zone") { var z = a[++i].Split(',').Select(x => double.Parse(x, System.Globalization.CultureInfo.InvariantCulture)).ToArray(); Ramps.Zones.Add((z[0], z[1], z[2], z[3], z.Length > 4 ? z[4] : double.MinValue, z.Length > 5 ? z[5] : double.MaxValue)); }
                else if (a[i] == "--forge-palette") { var w = a[++i].Split(';'); ForgePalette.Specs.Add((w[0].Trim(), w[1].Trim(), w[2].Trim())); if (w.Length > 3 && w[3].Trim() == "keep_stock") ForgePalette.KeepStock = true; }
                else if (a[i] == "--basis-scenario") basisScenario = a[++i];
                else if (a[i] == "--forge-prices") ForgePalette.LoadPrices(a[++i]);
                else if (a[i] == "--forge-budget") ForgePalette.Budget = float.Parse(a[++i], System.Globalization.CultureInfo.InvariantCulture);
                else if (a[i] == "--group-substitute") { var v = a[++i]; int e = v.IndexOf('='); groupSubst[v.Substring(0, e)] = v.Substring(e + 1); }
            }
            var log = new List<string>(); var unresolved = new List<string>();
            var cache = Program.OpenPak(pak); Program.SourcePath = pak; bool baseMode = !(cache is GameCacheModPackage);
            var stockDir = Path.GetDirectoryName(Path.GetFullPath(basis));

            // stock Halo 3 names: basis first, then every stock map
            var owner = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase); HashSet<string> h3Groups;
            using (var b = new Map(basis)) { foreach (var k in b.ByName.Keys) owner[k] = basis; h3Groups = b.Groups; }
            foreach (var m in Directory.GetFiles(stockDir, "*.map").OrderBy(x => x, StringComparer.OrdinalIgnoreCase))
            {
                var fn = Path.GetFileName(m).ToLowerInvariant();
                // HO2H3_EXCLUDE_STOCK: comma-separated stock map files not to take tags from (e.g. one overwritten by a test build)
                if ((Environment.GetEnvironmentVariable("HO2H3_EXCLUDE_STOCK") ?? "").Split(',').Contains(fn)) continue;
                if (fn == "shared.map" || fn == "campaign.map" || fn == "mainmenu.map" || Path.GetFullPath(m).Equals(Path.GetFullPath(basis), StringComparison.OrdinalIgnoreCase)) continue;
                try { using (var c = new Map(m)) { if (c.Engine.Name.Contains("Reach")) continue; foreach (var k in c.ByName.Keys) if (!owner.ContainsKey(k)) owner[k] = m; } } catch (Exception ex) { log.Add("stock map skipped " + m + ": " + ex.Message); }
            }

            // 1. walk
            var root = cache.TagCache.NonNull().First(t => t.Name.Equals(scenario, StringComparison.OrdinalIgnoreCase) && t.Group.Tag.ToString() == "scnr");
            var convert = new List<CachedTag>(); var byName = new Dictionary<int, string>();   // HO index -> stock "grp:name" referenced by name
            var grafts = new List<(string donor, string key)>(); var datum = new Dictionary<int, BDatum>();
            var seen = new HashSet<int>(); var q = new Queue<CachedTag>(); q.Enqueue(root); var lbspTags = new List<CachedTag>();
            foreach (var r in Placements.Roots(cache, scenario, subst, owner, log)) q.Enqueue(r);
            if (ForgePalette.Specs.Count > 0) using (var fs0 = Program.OpenStream(cache)) foreach (var r in ForgePalette.Roots(cache, fs0, log)) q.Enqueue(r);
            while (q.Count > 0)
            {
                var t = q.Dequeue(); if (t == null || !seen.Add(t.Index)) continue;
                string g = t.Group.Tag.ToString(), key = g + ":" + t.Name; var h = t as CachedTagHaloOnline; bool owned = h != null && !h.IsEmpty();
                void ByStockName(string k, string why)
                {
                    if (owner.TryGetValue(k, out var om)) { byName[t.Index] = k; if (om != basis && !grafts.Contains((om, k))) grafts.Add((om, k)); log.Add($"{why} {key} -> {k}{(om != basis ? " (from " + Path.GetFileName(om) + ")" : "")}"); }
                    else unresolved.Add($"{why}, no stock Halo 3 tag: {key}");
                }
                if (remove.Contains(key)) { unresolved.Add("removed (map cfg): " + key); continue; }
                // diagnostic: every material of these groups replaced by one stock Halo 3 shader (HO2H3_ONE_SHADER=rmsh:<name>)
                if (Environment.GetEnvironmentVariable("HO2H3_ONE_SHADER") is string one && (g == "rmsh" || g == "rmtr" || g == "rmfl" || g == "rmhg" || g == "rmw " || g == "rmcs")) { ByStockName(one, "one-shader diagnostic"); continue; }
                if (subst.TryGetValue(key, out var stock)) { ByStockName(stock.Contains(":") ? stock : g + ":" + stock, "substitute"); continue; }
                if (skip.Contains(g)) { unresolved.Add("skipped group: " + key); continue; }
                if (ShaderStage.Contains(g)) continue;   // the shader stage picks stock Halo 3 templates and definitions
                // Halo Online base game: its tags are Halo 3-derived and mostly share Halo 3's names; any tag that exists in stock
                // Halo 3 is used from there (stock asset policy), only the rest is converted
                if (baseMode && g != "scnr" && g != "sbsp" && g != "sLdT" && g != "Lbsp" && owner.ContainsKey(key)) { ByStockName(key, "stock Halo 3"); continue; }
                if (!owned || NeverConvert.Contains(g)) { ByStockName(key, owned ? "shader program by name" : "base cache"); continue; }
                if (g == "Lbsp") { lbspTags.Add(t); foreach (var d in h.Dependencies) q.Enqueue(cache.TagCache.GetTag(d)); continue; }   // merged into the scenario lightmap
                // a whole group Halo 3 lacks mapped to one stock tag (map cfg "shadergroup", e.g. Reach glass -> stock glass shader)
                if (!h3Groups.Contains(g) && groupSubst.TryGetValue(g, out var gs)) { ByStockName(gs, "group substitute"); continue; }
                if (!h3Groups.Contains(g)) { unresolved.Add("group not in Halo 3: " + key); continue; }
                if (owner.TryGetValue(key, out var own0) && own0 == basis) { byName[t.Index] = key; log.Add("reuse " + key); continue; }
                convert.Add(t);
                foreach (var d in h.Dependencies) q.Enqueue(cache.TagCache.GetTag(d));
            }
            Console.WriteLine($"walk: convert {convert.Count} | by stock name {byName.Count} ({grafts.Count} to copy) | unresolved {unresolved.Count}");

            File.Copy(basis, output, true);
            // 3. serialize
            var container = new TagContainer();
            foreach (var t in convert) datum[t.Index] = new BDatum(0xE000, (ushort)t.Index);
            var convertedIdx = new HashSet<int>(convert.Select(t => t.Index)); Placements.IsConverted = i => convertedIdx.Contains(i);
            foreach (var kv in byName) { var d = new BDatum(0xD000, (ushort)kv.Key); datum[kv.Key] = d; int c = kv.Value.IndexOf(':'); container.AddTag(new ExtractedTag(d, 0, CharConstant.FromString(kv.Value.Substring(0, c)), kv.Value.Substring(c + 1))); }
            var preDefs = new Dictionary<int, object>();
            using (var stream0 = Program.OpenStream(cache)) Lightmaps.Merge(cache, stream0, root, convert, preDefs, log);
            // stock Halo 3 tags met as TagTool Gen3 tags (shader stage): referenced by name, copied in when not in the basis
            var stockRefs = new Dictionary<CachedTag, BDatum>(ReferenceEqualityComparer.Instance); var stockKeys = new Dictionary<string, BDatum>(StringComparer.OrdinalIgnoreCase); ushort nextStock = 0;
            bool StockRef(CachedTag st)
            {
                if (st == null || stockRefs.ContainsKey(st)) return st != null;
                var k = st.Group.Tag.ToString() + ":" + st.Name;
                if (!owner.TryGetValue(k, out var om)) { unresolved.Add("stock tag not found by name: " + k); return false; }
                if (!stockKeys.TryGetValue(k, out var d))
                {
                    stockKeys[k] = d = new BDatum(0xD800, nextStock++);
                    container.AddTag(new ExtractedTag(d, 0, CharConstant.FromString(st.Group.Tag.ToString()), st.Name));
                    if (om != basis && !grafts.Contains((om, k))) grafts.Add((om, k));
                }
                stockRefs[st] = d; return true;
            }
            Func<CachedTag, BDatum> tagDatum = t => t == null ? BDatum.Null : stockRefs.TryGetValue(t, out var sd) ? sd : datum.TryGetValue(t.Index, out var d) ? d : BDatum.Null;
            var ser = new TagSerializer(CacheVersion.Halo3Retail, CachePlatform.Original, TagTool.IO.EndianFormat.BigEndian);
            uint addrBase = 0x10000000; int failed = 0;
            TagFixups.SourceVersion = cache.Version; TagFixups.SourcePlatform = cache.Platform; TagFixups.SourceStrings = cache.StringTable;
            var resources = new Resources(cache, salt == null ? null : File.ReadAllBytes(salt), container, log);
            using (var stream = Program.OpenStream(cache))
            {
                var shaders = new Shaders(cache, stream, owner, basis, StockRef, log);
                Dictionary<int, float> modelRadius = null; int modelObjectData = 0;
                foreach (var t in convert)
                {
                    string g = t.Group.Tag.ToString();
                    try
                    {
                        var def = preDefs.TryGetValue(t.Index, out var pd) ? pd : cache.Deserialize(stream, t);
                        shaders.ConvertAll(def, t);
                        if (def is TagTool.Tags.Definitions.Scenario scn0 && t == root) { Placements.Add(cache, scn0, root.Name, subst, owner, shaders.StockTag, StockRef, log, unresolved); ForgePalette.Apply(cache, scn0, shaders.H3, basis, basisScenario, shaders.StockTag, StockRef, log); SimTable.Build(cache, scn0, convert, shaders.H3, basis, basisScenario, shaders.StockTag, StockRef, t => tagDatum(t).Value, log); }
                        resources.Prepare(t, def, tagDatum);
                        TagFixups.Apply(t, def, log);
                        // model object data (Forge's size and centre of an object): every stock Halo 3 Forge object's model has
                        // one auto-generated entry (radius = the object's bounding radius, offset = centre of the render model's
                        // bounds; Sandbox sand_wall 1.274 / (0.010, -0.007, 0.897)); Halo Online's models have none and Forge
                        // could not create the object (Void: placing any Forge World item crashed, user play test 2026-11-23)
                        if (def is TagTool.Tags.Definitions.Model mdl && (mdl.ModelObjectData == null || mdl.ModelObjectData.Count == 0))
                        {
                            if (modelRadius == null)
                            {
                                modelRadius = new Dictionary<int, float>();
                                foreach (var ot in convert.Where(x => x.IsInGroup("obje")))
                                    try { var go = (TagTool.Tags.Definitions.GameObject)(preDefs.TryGetValue(ot.Index, out var od) ? od : cache.Deserialize(stream, ot)); if (go.Model != null) modelRadius[go.Model.Index] = Math.Max(modelRadius.TryGetValue(go.Model.Index, out var r0) ? r0 : 0, go.BoundingRadius); } catch { }
                            }
                            if (modelRadius.TryGetValue(t.Index, out var rad) && rad > 0)
                            {
                                var off = new TagTool.Common.RealPoint3d(0, 0, 0);
                                try { var rm = cache.Deserialize<TagTool.Tags.Definitions.RenderModel>(stream, mdl.RenderModel); var c0 = rm.Geometry.Compression[0]; off = new TagTool.Common.RealPoint3d((c0.X.Lower + c0.X.Upper) / 2, (c0.Y.Lower + c0.Y.Upper) / 2, (c0.Z.Lower + c0.Z.Upper) / 2); } catch { }
                                mdl.ModelObjectData = new List<TagTool.Tags.Definitions.Model.ModelObjectDatum> { new TagTool.Tags.Definitions.Model.ModelObjectDatum { Type = TagTool.Tags.Definitions.Model.ModelObjectDatum.TypeValue.AutoGenerated, Padding0 = new byte[2], Offset = off, Radius = rad } };
                                modelObjectData++; if (modelObjectData <= 3 || modelObjectData % 50 == 0) log.Add($"model object data: {t.Name}: radius {rad:0.000}, offset {off} (running count {modelObjectData})");
                            }
                        }
                        var ctx = new H3Context(cache, tagDatum, resources.Pre);
                        ser.Serialize(ctx, def);
                        // container addresses: each tag's blocks keep their TagTool stream offsets inside a window of their
                        // own, sized to the tag (fixed 16 MB windows overflowed 32 bits past 240 tags and collided)
                        uint mainAddr = addrBase + (uint)ctx.MainBlock.StreamOffset;
                        var blocks = ctx.ToDataBlocks(addrBase, resources.Fixup);
                        long span = ctx.Blocks.Max(b => b.StreamOffset + b.Stream.Length);
                        if (addrBase + span + 0x10000 > 0xF0000000u) throw new InvalidOperationException("container address space exhausted");
                        addrBase += (uint)((span + 0x10000) & ~0xFFFFL);
                        foreach (var b in blocks) container.AddDataBlock(b);
                        container.AddTag(new ExtractedTag(datum[t.Index], mainAddr, CharConstant.FromString(g), t.Name));
                    }
                    catch (Exception ex) { failed++; unresolved.Add($"conversion failed: {g}:{t.Name}: {ex.Message}"); datum.Remove(t.Index); }
                }
                foreach (var kv in TagFixups.Counts) log.Add($"per-game value {kv.Key}: {kv.Value}");
                log.Add($"function curves byte-swapped: {TagFixups.FunctionsSwapped}");
                if (ForgePalette.DisplayNames.Count > 0) File.WriteAllText(output + ".forge_names.json", System.Text.Json.JsonSerializer.Serialize(ForgePalette.DisplayNames));
                log.Add($"physics model MOPP data converted to Halo 3 byte order: {TagFixups.PhysicsMoppData}");
                log.Add($"MOPP codes re-keyed for Halo 3: {TagFixups.MoppsConverted} ({TagFixups.MoppsFailed} not convertible, left as is)");
                Console.WriteLine($"shaders: {shaders.Converted} onto stock Halo 3 templates ({shaders.Exact} exact) | {shaders.Failed} failed");
            }
            Console.WriteLine($"serialized {convert.Count - failed} tags ({failed} failed) | resources {resources.Converted} converted, {resources.Dropped} dropped");

            // 4. stock Halo 3 tags from other maps (named and chosen by the shader stage) copied in
            foreach (var grp in grafts.GroupBy(x => x.donor))
            {
                var keys = grp.Select(x => x.key).ToList();
                for (int i = 0; i < keys.Count; i += 40)
                {
                    var psi = new System.Diagnostics.ProcessStartInfo(ReachPort) { UseShellExecute = false, RedirectStandardOutput = true, CreateNoWindow = true };
                    psi.ArgumentList.Add("graftinto"); psi.ArgumentList.Add(output); psi.ArgumentList.Add(grp.Key); foreach (var k in keys.Skip(i).Take(40)) psi.ArgumentList.Add(k);
                    using (var p = System.Diagnostics.Process.Start(psi)) { log.Add(p.StandardOutput.ReadToEnd()); p.WaitForExit(); }
                }
            }

            // 5. inject
            using (var fs = File.Open(output, FileMode.Open, FileAccess.ReadWrite))
            {
                var reader = new EndianReader(fs, Endian.BigEndian);
                var file = CacheFileLoader.LoadCacheFile(reader, output, Map.Db, out var engine);
                var stream = new EndianStream(fs, engine.Endian);
                var injector = new TagContainerInjector(file, container, engine, true, true, false, false);
                foreach (var t in convert) if (datum.TryGetValue(t.Index, out var d)) { var et = container.FindTag(d); if (et != null) injector.InjectTag(et, stream); }
                injector.SaveChanges(stream);
                Console.WriteLine($"injected tags {injector.InjectedTags.Count} | blocks {injector.InjectedBlocks.Count} | strings {injector.InjectedStringIDs.Count} | resources {injector.InjectedResources.Count} | pages {injector.InjectedPages.Count}");
            }
            // tags whose resources the zone sets must load: converted tags and stock tags copied from other maps
            var zoneKeys = convert.Where(t => datum.ContainsKey(t.Index)).Select(t => t.Group.Tag.ToString() + ":" + t.Name).ToList();
            foreach (var l in log) foreach (var line in l.Split('\n')) if (line.StartsWith("grafted ")) { var w = line.TrimEnd('\r').Split(' '); int f = Array.LastIndexOf(w, "from"); if (f > 2) zoneKeys.Add(w[1] + ":" + string.Join(" ", w.Skip(2).Take(f - 2))); }
            File.WriteAllLines(output + ".keys.txt", zoneKeys.Distinct());
            File.WriteAllLines(output + ".log.txt", log);
            File.WriteAllLines(output + ".unresolved.txt", unresolved.GroupBy(x => x).Select(gr => $"{gr.Count(),5} {gr.Key}").OrderByDescending(x => x));
            return 0;
        }
    }
}
