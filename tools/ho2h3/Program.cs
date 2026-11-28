// ho2h3 <command> ...
//   probe <pak> <tag name.group>   serialize one Halo Online tag in Halo 3 retail 360 layout; report sizes and references
using System;
using System.IO;
using System.Linq;
using TagTool.Cache;
using TagTool.Cache.HaloOnline;
using TagTool.Serialization;

namespace Ho2H3
{
    static class Program
    {
        // a TagTool mod package (.pak), or Halo Online's base game (tags.dat in its maps folder)
        public static GameCache OpenPak(string path) => (path.EndsWith(".dat", StringComparison.OrdinalIgnoreCase) || path.EndsWith(".map", StringComparison.OrdinalIgnoreCase)) ? GameCache.Open(new FileInfo(path)) : new GameCacheModPackage(null, new FileInfo(path), true);
        public static Stream OpenStream(GameCache c) => c is GameCacheModPackage mp ? mp.OpenCacheRead(new MemoryStream()) : c.OpenCacheRead();
        public static string SourcePath;

        static int Main(string[] args)
        {
            if (args.Length == 0) { Console.WriteLine("ho2h3 probe <pak> <tag name.group>"); return 1; }
            for (int i = 1; i < args.Length; i++) if (File.Exists(args[i]) || Directory.Exists(Path.GetDirectoryName(args[i]) ?? "")) args[i] = args[i].Contains(":") ? args[i] : args[i];
            Environment.CurrentDirectory = AppContext.BaseDirectory;
            switch (args[0])
            {
                case "probe": return Probe(args);
                case "inventory": return Inventory(args);
                case "convert": return Converter.Run(args);
                case "shaderprobe": return ShaderProbe.Run(args);
                case "collprobe": return CollProbe.Run(args);
                case "geomprobe": return GeomProbe.Run(args);
                case "objexport": return ObjExport.Run(args);
                case "variant": return VariantProbe.Run(args);
                case "physprobe": return PhysProbe.Run(args);
                case "collcheck": return CollCheck.Run(args);
                case "refcheck": return CollCheck.RefCheck(args);
                case "sphere360": return CollCheck.Sphere360(args);
                case "vector360": return CollCheck.Vector360(args);
                case "solidstats": return CollCheck.SolidStats(args);
                case "linecheck": return CollCheck.LineCheck(args);
                case "renderbsp": return CollCheck.RenderBsp(args);
                case "moppkeys": return CollCheck.MoppKeys(args);
                case "mcvcheck": return VisRules.McvCheck(args);
                case "pvscheck": return VisRules.PvsCheck(args);
                case "fadecheck": return VisRules.FadeCheck(args);
                case "spherecheck": return VisRules.SphereCheck(args);
                case "bucketcheck": return VisRules.BucketCheck(args);
                case "seamcheck": return VisRules.SeamCheck(args);
                case "locate": return VisRules.Locate(args);
                case "blankclustermopp": return PatchProbe.Run(args);
                case "rawtag": return PatchProbe.RawTag(args);
                case "rawinst": return PatchProbe.RawInst(args);
                case "gapscan": return CollCheck.GapScan(args);
                case "raycol": return CollCheck.Ray(args);
                case "points": return CollCheck.Points(args);
                case "viscompare": return VisCheck.Run(args);
                case "decalcheck": return CollCheck.Decals(args);
                case "decaloverlap": return CollCheck.DecalOverlap(args);
                case "surftest": return SurfTest.Run(args);
                case "addr": return AddrProbe.Run(args);
                case "locale": return LocaleProbe.Run(args);
                case "buckets": return BucketProbe.Run(args);
                case "reachpal": return ReachPalette.Run(args);
                case "addlocale": return AddLocale.Run(args);
                case "tags": return ListTags.Run(args);
            }
            return 1;
        }

        // inventory <pak> <scenario name>: every tag the scenario depends on, by group: package-owned or base-cache only
        static int Inventory(string[] a)
        {
            var cache = OpenPak(a[1]); SourcePath = a[1];
            var root = cache.TagCache.NonNull().First(t => t.Name.Equals(a[2], StringComparison.OrdinalIgnoreCase) && t.Group.ToString() == "scenario");
            var seen = new System.Collections.Generic.HashSet<int>(); var q = new System.Collections.Generic.Queue<CachedTag>(); q.Enqueue(root);
            var own = new System.Collections.Generic.Dictionary<string, int>(); var bas = new System.Collections.Generic.Dictionary<string, int>();
            var baseNames = new System.Collections.Generic.List<string>();
            while (q.Count > 0)
            {
                var t = q.Dequeue(); if (t == null || !seen.Add(t.Index)) continue;
                var h = t as CachedTagHaloOnline; string g = t.Group.ToString();
                if (h != null && !h.IsEmpty()) { own[g] = own.TryGetValue(g, out var n) ? n + 1 : 1; foreach (var d in h.Dependencies) q.Enqueue(cache.TagCache.GetTag(d)); }
                else { bas[g] = bas.TryGetValue(g, out var n) ? n + 1 : 1; baseNames.Add($"{t.Name}.{g}"); }
            }
            Console.WriteLine($"package-owned {own.Values.Sum()}, base-cache only {bas.Values.Sum()}");
            foreach (var g in own.Keys.Union(bas.Keys).OrderByDescending(g => (own.TryGetValue(g, out var x) ? x : 0) + (bas.TryGetValue(g, out var y) ? y : 0)))
                Console.WriteLine($"  {g,-36} own {(own.TryGetValue(g, out var o) ? o : 0),5}   base {(bas.TryGetValue(g, out var b) ? b : 0),5}");
            if (a.Length > 3) File.WriteAllLines(a[3], baseNames);
            return 0;
        }

        static int Probe(string[] a)
        {
            var cache = OpenPak(a[1]); SourcePath = a[1];
            var tag = cache.TagCache.NonNull().First(t => $"{t.Name}.{t.Group}".Equals(a[2], StringComparison.OrdinalIgnoreCase));
            object def; using (var s = ((GameCacheModPackage)cache).OpenCacheRead(new MemoryStream())) def = cache.Deserialize(s, tag);
            var ser = new TagSerializer(CacheVersion.Halo3Retail, CachePlatform.Original, TagTool.IO.EndianFormat.BigEndian);
            var ctx = new H3Context(cache, t => new Blamite.Blam.DatumIndex((uint)(0xE0000000 | (uint)t.Index)));
            ser.Serialize(ctx, def);
            Console.WriteLine($"{tag.Name}.{tag.Group}: {ctx.Blocks.Count} blocks; main struct {ctx.MainBlock?.Stream.Length} bytes");
            var m = ctx.MainBlock;
            if (m != null)
            {
                Console.WriteLine($"main: {m.Pointers.Count} pointers, {m.Tags.Count} tag refs, {m.Strings.Count} strings");
                var d = m.Stream.ToArray();
                foreach (var (at, datum) in m.Tags.Take(4)) Console.WriteLine($"  tag ref @0x{at:X}: {BitConverter.ToString(d, Math.Max(0, at - 12), Math.Min(16, d.Length - Math.Max(0, at - 12)))} -> {datum}");
            }
            return 0;
        }
    }
}
