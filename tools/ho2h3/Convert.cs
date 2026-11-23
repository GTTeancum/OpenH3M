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
            string pak = a[1], scenario = a[2], basis = a[3], output = a[4], salt = null;
            var subst = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase); var groupSubst = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase); var skip = new HashSet<string>(); var remove = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            for (int i = 5; i < a.Length; i++)
            {
                if (a[i] == "--substitute") { var v = a[++i]; int e = v.IndexOf('='); subst[v.Substring(0, e)] = v.Substring(e + 1); }
                else if (a[i] == "--skip") skip.Add(a[++i]);
                else if (a[i] == "--remove") remove.Add(a[++i]);
                else if (a[i] == "--salt") salt = a[++i];
                else if (a[i] == "--group-substitute") { var v = a[++i]; int e = v.IndexOf('='); groupSubst[v.Substring(0, e)] = v.Substring(e + 1); }
            }
            var log = new List<string>(); var unresolved = new List<string>();
            var cache = Program.OpenPak(pak);
            var stockDir = Path.GetDirectoryName(Path.GetFullPath(basis));

            // stock Halo 3 names: basis first, then every stock map
            var owner = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase); HashSet<string> h3Groups;
            using (var b = new Map(basis)) { foreach (var k in b.ByName.Keys) owner[k] = basis; h3Groups = b.Groups; }
            foreach (var m in Directory.GetFiles(stockDir, "*.map").OrderBy(x => x, StringComparer.OrdinalIgnoreCase))
            {
                var fn = Path.GetFileName(m).ToLowerInvariant();
                if (fn == "shared.map" || fn == "campaign.map" || fn == "mainmenu.map" || Path.GetFullPath(m).Equals(Path.GetFullPath(basis), StringComparison.OrdinalIgnoreCase)) continue;
                try { using (var c = new Map(m)) { if (c.Engine.Name.Contains("Reach")) continue; foreach (var k in c.ByName.Keys) if (!owner.ContainsKey(k)) owner[k] = m; } } catch (Exception ex) { log.Add("stock map skipped " + m + ": " + ex.Message); }
            }

            // 1. walk
            var root = cache.TagCache.NonNull().First(t => t.Name.Equals(scenario, StringComparison.OrdinalIgnoreCase) && t.Group.Tag.ToString() == "scnr");
            var convert = new List<CachedTag>(); var byName = new Dictionary<int, string>();   // HO index -> stock "grp:name" referenced by name
            var grafts = new List<(string donor, string key)>(); var datum = new Dictionary<int, BDatum>();
            var seen = new HashSet<int>(); var q = new Queue<CachedTag>(); q.Enqueue(root); var lbspTags = new List<CachedTag>();
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
            foreach (var kv in byName) { var d = new BDatum(0xD000, (ushort)kv.Key); datum[kv.Key] = d; int c = kv.Value.IndexOf(':'); container.AddTag(new ExtractedTag(d, 0, CharConstant.FromString(kv.Value.Substring(0, c)), kv.Value.Substring(c + 1))); }
            var preDefs = new Dictionary<int, object>();
            using (var stream0 = ((GameCacheModPackage)cache).OpenCacheRead(new MemoryStream())) Lightmaps.Merge(cache, stream0, root, convert, preDefs, log);
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
            using (var stream = ((GameCacheModPackage)cache).OpenCacheRead(new MemoryStream()))
            {
                var shaders = new Shaders(cache, stream, owner, basis, StockRef, log);
                foreach (var t in convert)
                {
                    string g = t.Group.Tag.ToString();
                    try
                    {
                        var def = preDefs.TryGetValue(t.Index, out var pd) ? pd : cache.Deserialize(stream, t);
                        shaders.ConvertAll(def, t);
                        if (def is TagTool.Tags.Definitions.Scenario scn0 && t == root) Placements.Add(cache, scn0, root.Name, subst, owner, shaders.StockTag, StockRef, log, unresolved);
                        resources.Prepare(t, def, tagDatum);
                        TagFixups.Apply(t, def, log);
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
