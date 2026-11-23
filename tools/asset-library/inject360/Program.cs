// Inject360: bespoke MCC -> original Xbox 360 Halo 3 tag injector built on XboxChaos Assembly's Blamite (GPL-3.0).
//   probe <map> [name-substring...]           what Blamite detects in a cache file
//   plan  <mcc map> <360 map> <root tag>...   dependency walk from the roots in the MCC map; tags that already exist
//                                             (same group + name) in the 360 map are reused, not converted
//   port  <mcc map> <360 map> <output map> <root tag>...   translate the converted tags to the 360 layout and inject
//                                             them into a copy of the 360 map (the input 360 map is never written)
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Xml;
using Blamite.Blam;
using Blamite.Blam.Resources;
using Blamite.Injection;
using Blamite.IO;
using Blamite.Plugins;
using Blamite.Serialization;
using Blamite.Serialization.Settings;
using Blamite.Util;
using Inject360;

partial class Program
{
    static string Root = AppDomain.CurrentDomain.BaseDirectory;
    // 34-byte resource hash salt from the game's default.xex, extracted once into the repository's .local folder.
    static string SaltPath => Path.GetFullPath(Path.Combine(Root, "..", "..", "..", "..", "inject360", "resource_salt.bin"));

    static int Main(string[] args)
    {
        for (int i = 1; i < args.Length; i++) if (args[i].Length > 2 && (args[i][1] == ':' || args[i].StartsWith("/") || args[i].Contains("\\") && System.IO.File.Exists(args[i]))) args[i] = Path.GetFullPath(args[i]);
        Environment.CurrentDirectory = Root;   // Blamite resolves its format files relative to the working directory
        var db = XMLEngineDatabaseLoader.LoadDatabase(Path.Combine(Root, "Formats", "Engines.xml"));
        switch (args.Length > 0 ? args[0] : "")
        {
            case "probe": return Probe(db, args[1], args.Skip(2).ToArray());
            case "plan": return Plan(db, args[1], args[2], args.Skip(3).ToArray());
            case "res": return ResTag(db, args[1], args[2], args[3], args.Length > 4 ? args[4] : null);
            case "tiletest":
                {
                    var lin = System.IO.File.ReadAllBytes(args[1]); var gold = System.IO.File.ReadAllBytes(args[2]);
                    int w = int.Parse(args[3]), h = int.Parse(args[4]), n = int.Parse(args[5]), bpb = int.Parse(args[6]), ext = int.Parse(args[7]), sw = int.Parse(args[8]);
                    var t = Xenos.Tile(lin, 0, w, h, n, ext, bpb, sw);
                    System.IO.File.WriteAllBytes(args[2] + ".mine", t);
                    int same = 0, cmp = Math.Min(t.Length, gold.Length); if (args.Length > 9) cmp = Math.Min(cmp, int.Parse(args[9]));
                    for (int i = 0; i < cmp; i++) if (t[i] == gold[i]) same++;
                    Console.WriteLine($"tiled {t.Length} bytes (linear used {Xenos.LinearSize(w, h, n, ext, bpb)} of {lin.Length}); 360 {gold.Length}; identical {same}/{cmp}");
                    return 0;
                }
            case "zonerow":
                using (var c = new Cache(db, args[1]))
                {
                    var z = c.File.Tags.First(t => t != null && t.Group != null && CharConstant.ToString(t.Group.Magic) == "zone");
                    var tree = TagTree.Read(c.File, c.Reader, z, Schema.Load(c.Plugin(z.Group.Magic), 0x10, 0x14, 0xC));
                    foreach (var kv in tree.F) Console.WriteLine("  zone field " + kv.Key + (kv.Value is List<Elem> l ? " [" + l.Count + "]" : ""));
                    var rows = tree.Block(args[2]);
                    foreach (var i in args.Skip(3).Select(int.Parse))
                    { Console.WriteLine("row " + i); foreach (var kv in rows[i].F) Console.WriteLine("   " + kv.Key + " = " + (kv.Value is List<Elem> l ? "[" + l.Count + "]" : kv.Value is uint u ? "0x" + u.ToString("X8") : kv.Value)); }
                }
                return 0;
            case "resave":   // control experiment: Blamite load + save + integrity, nothing injected
                {
                    System.IO.File.Copy(args[1], args[2], true);
                    using (var c = new Cache(db, args[2], true))
                    {
                        var stream = new EndianStream(c.Stream, c.Engine.Endian);
                        var inj = new TagContainerInjector(c.File, new TagContainer(), c.Engine, true, true, false, false);
                        inj.SaveChanges(stream);
                    }
                    Integrity.Finalize(args[2], System.IO.File.ReadAllBytes(SaltPath));
                    Console.WriteLine(Integrity.Verify(args[2], System.IO.File.ReadAllBytes(SaltPath)));
                    return 0;
                }
            case "check":   // every tag reference / block pointer / string id in tags whose name contains a filter
                using (var c = new Cache(db, args[1]))
                {
                    int bad = 0, refs = 0, tags = 0;
                    foreach (var kv in c.ByName.Where(kv => args.Skip(2).Any(f => kv.Key.IndexOf(f, StringComparison.OrdinalIgnoreCase) >= 0)))
                    {
                        tags++;
                        var t = kv.Value; var schema = Schema.Load(c.Plugin(t.Group.Magic), 0x10, 0x14, 0xC);
                        void walk(long at, List<Node> fields, string path)
                        {
                            foreach (var f in fields)
                            {
                                c.Reader.SeekTo(at + f.Offset);
                                if (f.Kind == Kind.TagRef)
                                {
                                    if (f.WithGroup) c.Reader.Skip(12); uint d = c.Reader.ReadUInt32(); refs++;
                                    if (d != 0xFFFFFFFF && !c.File.Tags.IsValidIndex(new DatumIndex(d))) { bad++; Console.WriteLine($"  BAD REF {kv.Key}{path}/{f.Name} = 0x{d:X8}"); }
                                }
                                else if (f.Kind == Kind.StringId)
                                {
                                    uint v = c.Reader.ReadUInt32();
                                    if (v != 0 && c.File.StringIDs.GetString(new StringID(v)) == null) { bad++; Console.WriteLine($"  BAD STRING {kv.Key}{path}/{f.Name} = 0x{v:X8}"); }
                                }
                                else if (f.Kind == Kind.Block || f.Kind == Kind.DataRef)
                                {
                                    int count = c.Reader.ReadInt32(); if (f.Kind == Kind.DataRef) c.Reader.Skip(8); uint ptr = c.Reader.ReadUInt32();
                                    if (count == 0) continue;
                                    long exp = c.File.PointerExpander.Expand(ptr);
                                    uint size = f.Kind == Kind.Block ? (uint)count * f.ElementSize : (uint)count;
                                    if (count < 0 || ptr == 0 || !c.File.MetaArea.ContainsBlockPointer(exp, size)) { bad++; Console.WriteLine($"  BAD BLOCK {kv.Key}{path}/{f.Name} count {count} ptr 0x{ptr:X8}"); continue; }
                                    if (f.Kind == Kind.Block)
                                    {
                                        long off = c.File.MetaArea.PointerToOffset(exp);
                                        for (int i = 0; i < count; i++) walk(off + i * f.ElementSize, f.Kids, path + "/" + f.Name + "[" + i + "]");
                                    }
                                }
                            }
                        }
                        walk(t.MetaLocation.AsOffset(), schema.Fields, "");
                    }
                    Console.WriteLine($"checked {tags} tags, {refs} references: {bad} problems");
                }
                return 0;
            case "strings":   // strings <map> <key substring>   which string lists hold matching keys, with the English text
                using (var c = new Cache(db, args[1]))
                {
                    var pack = c.File.Languages.LoadLanguage(Blamite.Blam.Localization.GameLanguage.English, c.Reader);
                    foreach (var list in pack.StringLists)
                        foreach (var str in list.Strings)
                        {
                            var key = c.File.StringIDs.GetString(str.Key) ?? "";
                            if (key.IndexOf(args[2], StringComparison.OrdinalIgnoreCase) >= 0)
                                Console.WriteLine($"{c.Name(list.SourceTag)} | {key} = {str.Value} | " + string.Join(" ", str.Value.Where(ch => ch > 126 || ch < 32).Select(ch => ((int)ch).ToString("X4"))));
                        }
                }
                return 0;
            case "animverify":   // animverify <mcc map> <360 map>: convert every shared animation and compare with the 360 bytes
                using (var a = new Cache(db, args[1]))
                using (var b = new Cache(db, args[2]))
                {
                    var others = new Dictionary<string, Cache>(StringComparer.OrdinalIgnoreCase);
                    var ta = a.File.Resources.LoadResourceTable(a.Reader); var tb = b.File.Resources.LoadResourceTable(b.Reader);
                    var stats = new Dictionary<string, int[]>(); var shown = new Dictionary<string, int>();
                    Func<Cache, string, Blamite.Blam.Resources.ResourcePage, byte[]> pageOf = (c, path, pg) => Res.PageBytes(c.File, path, c.Stream, pg, pth =>
                    {
                        if (!System.IO.File.Exists(pth)) return null;
                        if (!others.TryGetValue(pth, out var o)) others[pth] = o = new Cache(db, pth);
                        return o.File;
                    });
                    List<(byte[] hdr, byte[] data)> members(Cache c, string path, Blamite.Blam.Resources.Resource r, bool le)
                    {
                        var res = new List<(byte[], byte[])>(); var info = r.Info; if (info == null) return res;
                        Func<int, uint> u32 = at => le ? BitConverter.ToUInt32(info, at) : (uint)(info[at] << 24 | info[at + 1] << 16 | info[at + 2] << 8 | info[at + 3]);
                        var fix = r.ResourceFixups.ToDictionary(f => f.Offset, f => f.Address);
                        int root = r.BaseDefinitionAddress & 0x1FFFFFFF; int n = (int)u32(root); if (n == 0) return res;
                        int tab = (int)(fix[root + 4] & 0x1FFFFFFF);
                        for (int i = 0; i < n; i++)
                        {
                            int at = tab + i * 48; int size = (int)u32(at + 28); uint addr = fix[at + 40];
                            bool prim = (addr & 0xE0000000) == 0x40000000;
                            var pg = prim ? r.Location.PrimaryPage : r.Location.SecondaryPage;
                            int off = (int)(addr & 0x1FFFFFFF) + Math.Max(0, prim ? r.Location.PrimaryOffset : r.Location.SecondaryOffset);
                            var bytes = pageOf(c, path, pg); if (bytes == null) { res.Add((null, null)); continue; }
                            res.Add((info.Skip(at).Take(48).ToArray(), bytes.Skip(off).Take(size).ToArray()));
                        }
                        return res;
                    }
                    int jm = CharConstant.FromString("jmad");
                    foreach (var kv in a.ByName.Where(k => k.Value.Group.Magic == jm && b.ByName.ContainsKey(k.Key)))
                    {
                        var ba = new DataBlockBuilder(a.Reader, kv.Value, a.File, a.Engine); using (var xr = XmlReader.Create(a.Plugin(jm))) AssemblyPluginLoader.LoadPlugin(xr, ba);
                        var bb = new DataBlockBuilder(b.Reader, b.ByName[kv.Key], b.File, b.Engine); using (var xr = XmlReader.Create(b.Plugin(jm))) AssemblyPluginLoader.LoadPlugin(xr, bb);
                        var ra = ba.ReferencedResources.ToList(); var rb = bb.ReferencedResources.ToList(); if (ra.Count != rb.Count) continue;
                        for (int g = 0; g < ra.Count; g++)
                        {
                            List<(byte[] hdr, byte[] data)> ma, mb;
                            try { ma = members(a, args[1], ta.Resources[ra[g].Index], true); mb = members(b, args[2], tb.Resources[rb[g].Index], false); } catch { continue; }
                            if (ma.Count != mb.Count) continue;
                            for (int i = 0; i < ma.Count; i++)
                            {
                                var (h, d) = ma[i]; var (h2, d2) = mb[i]; if (d == null || d2 == null || d.Length != d2.Length || d.Length == 0) continue;
                                int frames = BitConverter.ToUInt16(h, 8), sf = h[12], af = h[13], md = BitConverter.ToUInt16(h, 14), pill = BitConverter.ToUInt16(h, 16), stat = BitConverter.ToUInt16(h, 18);
                                int unpacked = (int)BitConverter.ToUInt32(h, 20), comp = (int)BitConverter.ToUInt32(h, 24);
                                var parts = new List<(string name, int start, int len)>();
                                if (stat > 0) parts.Add(("codec" + d[0], 0, stat));
                                if (comp > 0) parts.Add(("codec" + d[stat], stat, comp));
                                int rest = stat + comp; if (d.Length > rest) parts.Add(($"tail(mov{h[11]} pill{(pill > 0 ? 1 : 0)} unp{(unpacked > 0 ? 1 : 0)})", rest, d.Length - rest));
                                foreach (var (name0, start, len) in parts)
                                {
                                    var name = name0; byte[] conv;
                                    try
                                    {
                                        var piece = d.Skip(start).Take(len).ToArray();
                                        if (name.StartsWith("codec")) conv = AnimationConverter.Codec(piece, frames);
                                        else { conv = (byte[])piece.Clone(); for (int k = 0; k + 4 <= len; k += 4) { conv[k] = piece[k + 3]; conv[k + 1] = piece[k + 2]; conv[k + 2] = piece[k + 1]; conv[k + 3] = piece[k]; } }
                                    }
                                    catch (Exception ex) { conv = null; name += " EXC " + ex.Message; }
                                    if (!stats.TryGetValue(name, out var st)) stats[name] = st = new int[2];
                                    bool ok = conv != null && conv.SequenceEqual(d2.Skip(start).Take(len));
                                    st[ok ? 0 : 1]++;
                                    if (!ok && conv != null && (!shown.TryGetValue(name, out var sh) || sh < 2))
                                    {
                                        shown[name] = sh + 1; int first = Enumerable.Range(0, len).First(k => conv[k] != d2[start + k]);
                                        Console.WriteLine($"MISMATCH {name} {kv.Key} group {g} member {i} frames {frames} len {len} first diff at {first}");
                                        Console.WriteLine("   mcc  " + BitConverter.ToString(d, start, Math.Min(64, len)));
                                        Console.WriteLine("   360  " + BitConverter.ToString(d2, start, Math.Min(64, len)));
                                        Console.WriteLine("   mine " + BitConverter.ToString(conv, 0, Math.Min(64, len)));
                                    }
                                }
                            }
                        }
                    }
                    foreach (var kv in stats.OrderBy(k => k.Key)) Console.WriteLine($"{kv.Key}: identical {kv.Value[0]}, different {kv.Value[1]}");
                }
                return 0;
            case "texverify": return TexVerify(db, args);
            case "texscan": return TexScan(db, args);
            case "sndinfo": return SoundInfo(db, args);
            case "templates": return TemplatePlan(db, args[1], args[2], args[3], args.Skip(4).ToArray());
            case "graft": return Graft(db, args[1], args[2], args[3], args.Skip(4).ToArray());
            case "verify": Console.WriteLine(Integrity.Verify(args[1], System.IO.File.ReadAllBytes(SaltPath))); return 0;
            case "pagehash":
                {
                    var (h1, h2, h3) = Integrity.PageHashes(System.IO.File.ReadAllBytes(SaltPath), System.IO.File.ReadAllBytes(args[1]));
                    Console.WriteLine(BitConverter.ToString(h1) + " | " + BitConverter.ToString(h2) + " | " + BitConverter.ToString(h3)); return 0;
                }
            case "dump": return DumpTag(db, args[1], args[2], args[3]);
            case "port": return Port(db, args[1], args[2], args[3], args.Skip(4).Where(a => !a.StartsWith("--")).Where((a, i) => true).ToArray(), args);
        }
        Console.WriteLine("usage: Inject360 probe <map> [filter...] | plan <mcc map> <360 map> <root tag>...");
        return 1;
    }

    class Cache : IDisposable
    {
        public Stream Stream; public EndianReader Reader; public ICacheFile File; public EngineDescription Engine;
        public Dictionary<string, ITag> ByName = new Dictionary<string, ITag>(StringComparer.OrdinalIgnoreCase);
        public Cache(EngineDatabase db, string path, bool write = false)
        {
            Stream = write ? System.IO.File.Open(path, FileMode.Open, FileAccess.ReadWrite, FileShare.None) : System.IO.File.OpenRead(path);
            Reader = new EndianReader(Stream, Endian.BigEndian);
            File = CacheFileLoader.LoadCacheFile(Reader, path, db, out Engine);
            foreach (var t in File.Tags)
            {
                if (t == null || t.Group == null || t.MetaLocation == null) continue;
                var n = File.FileNames.GetTagName(t); if (n == null) continue;
                ByName[Key(t.Group.Magic, n)] = t;
            }
        }
        public string Name(ITag t) => File.FileNames.GetTagName(t) ?? t.Index.ToString();
        public string Plugin(int magic)
        {
            var group = SterilizeGroup(CharConstant.ToString(magic));
            foreach (var setting in new[] { "plugins", "fallbackPlugins" })
            {
                if (!Engine.Settings.PathExists(setting)) continue;
                var p = Path.Combine(Root, "Plugins", Engine.Settings.GetSetting<string>(setting), group + ".xml");
                if (System.IO.File.Exists(p)) return p;
            }
            return null;
        }
        public void Dispose() { Stream.Dispose(); }
    }

    static string Key(int magic, string name) => CharConstant.ToString(magic) + ":" + name;
    static string SterilizeGroup(string g)
    {
        foreach (var c in Path.GetInvalidFileNameChars()) g = g.Replace(c, '_');
        return g.Trim();
    }

    static int Probe(EngineDatabase db, string path, string[] filters)
    {
        using (var c = new Cache(db, path))
        {
            Console.WriteLine("ENGINE " + c.Engine.Name + " | endian " + c.Engine.Endian + " | tags " + c.File.Tags.Count);
            foreach (var kv in c.ByName.Where(kv => filters.Any(f => kv.Key.IndexOf(f, StringComparison.OrdinalIgnoreCase) >= 0)))
                Console.WriteLine("  " + kv.Key);
        }
        return 0;
    }

    static int Plan(EngineDatabase db, string mccPath, string x360Path, string[] roots)
    {
        using (var src = new Cache(db, mccPath))
        using (var dst = new Cache(db, x360Path))
        {
            Console.WriteLine("SOURCE " + src.Engine.Name + " | TARGET " + dst.Engine.Name);
            var queue = new Queue<ITag>(); var seen = new HashSet<uint>();
            var convert = new List<ITag>(); var reuse = new List<ITag>(); var noPlugin = new List<ITag>();
            int resources = 0;
            foreach (var r in roots)
            {
                var hit = src.ByName.Where(kv => kv.Key.EndsWith(":" + r, StringComparison.OrdinalIgnoreCase)).Select(kv => kv.Value).ToList();
                if (hit.Count == 0) { Console.WriteLine("ROOT NOT FOUND " + r); return 2; }
                foreach (var h in hit) queue.Enqueue(h);
            }
            while (queue.Count > 0)
            {
                var t = queue.Dequeue();
                if (t == null || !seen.Add(t.Index.Value)) continue;
                var name = src.Name(t);
                if (dst.ByName.ContainsKey(Key(t.Group.Magic, name))) { reuse.Add(t); continue; }  // stock tag present in the 360 map
                var plugin = src.Plugin(t.Group.Magic);
                if (plugin == null) { noPlugin.Add(t); continue; }
                convert.Add(t);
                var builder = new DataBlockBuilder(src.Reader, t, src.File, src.Engine);
                using (var xr = XmlReader.Create(plugin)) AssemblyPluginLoader.LoadPlugin(xr, builder);
                foreach (var tr in builder.ReferencedTags) queue.Enqueue(src.File.Tags[tr]);
                resources += builder.ReferencedResources.Count;
            }
            Console.WriteLine("CONVERT " + convert.Count + " | REUSE (already in 360 map) " + reuse.Count + " | NO PLUGIN " + noPlugin.Count + " | resource refs " + resources);
            foreach (var g in convert.GroupBy(t => CharConstant.ToString(t.Group.Magic)).OrderByDescending(g => g.Count()))
                Console.WriteLine("  convert " + g.Key + " x" + g.Count());
            foreach (var t in convert) Console.WriteLine("    C " + CharConstant.ToString(t.Group.Magic) + " " + src.Name(t));
            foreach (var t in reuse) Console.WriteLine("    R " + CharConstant.ToString(t.Group.Magic) + " " + src.Name(t));
            foreach (var t in noPlugin) Console.WriteLine("    ? " + CharConstant.ToString(t.Group.Magic) + " " + src.Name(t));
        }
        return 0;
    }

    // Dependency walk shared by plan and port.
    static void Walk(Cache src, Cache dst, string[] roots, List<ITag> convert, List<ITag> reuse, List<ITag> noPlugin, Dictionary<uint, DataBlockBuilder> built, Func<ITag, bool> intercept = null)
    {
        var queue = new Queue<ITag>(); var seen = new HashSet<uint>();
        foreach (var r in roots)
        {
            var hit = src.ByName.Where(kv => kv.Key.EndsWith(":" + r, StringComparison.OrdinalIgnoreCase)).Select(kv => kv.Value).ToList();
            if (hit.Count == 0) throw new Exception("ROOT NOT FOUND " + r);
            foreach (var h in hit) queue.Enqueue(h);
        }
        while (queue.Count > 0)
        {
            var t = queue.Dequeue();
            if (t == null || !seen.Add(t.Index.Value)) continue;
            if (dst.ByName.ContainsKey(Key(t.Group.Magic, src.Name(t)))) { reuse.Add(t); continue; }
            if (intercept != null && intercept(t)) continue;
            var plugin = src.Plugin(t.Group.Magic);
            if (plugin == null) { noPlugin.Add(t); continue; }
            convert.Add(t);
            var builder = new DataBlockBuilder(src.Reader, t, src.File, src.Engine);
            using (var xr = XmlReader.Create(plugin)) AssemblyPluginLoader.LoadPlugin(xr, builder);
            built[t.Index.Value] = builder;
            foreach (var tr in builder.ReferencedTags) queue.Enqueue(src.File.Tags[tr]);
        }
    }

    static int ResTag(EngineDatabase db, string path, string group, string name, string dumpDir)
    {
        var others = new Dictionary<string, Cache>(StringComparer.OrdinalIgnoreCase);
        using (var c = new Cache(db, path))
        {
            if (!c.ByName.TryGetValue(group + ":" + name, out var t)) { Console.WriteLine("not found"); return 2; }
            var builder = new DataBlockBuilder(c.Reader, t, c.File, c.Engine);
            using (var xr = XmlReader.Create(c.Plugin(t.Group.Magic))) AssemblyPluginLoader.LoadPlugin(xr, builder);
            var table = c.File.Resources.LoadResourceTable(c.Reader);
            if (dumpDir != null) Directory.CreateDirectory(dumpDir);
            Console.WriteLine($"{group}:{name} -> {builder.ReferencedResources.Count} resource(s)");
            foreach (var di in builder.ReferencedResources)
            {
                var r = table.Resources[di.Index];
                Res.Print(Console.Out, r, pg => Res.PageBytes(c.File, path, c.Stream, pg, p =>
                {
                    if (!System.IO.File.Exists(p)) return null;
                    if (!others.TryGetValue(p, out var o)) others[p] = o = new Cache(db, p);
                    return o.File;
                }), dumpDir);
            }
        }
        foreach (var o in others.Values) o.Dispose();
        return 0;
    }

    static int DumpTag(EngineDatabase db, string path, string group, string name)
    {
        using (var c = new Cache(db, path))
        {
            if (!c.ByName.TryGetValue(group + ":" + name, out var t)) { Console.WriteLine("not found"); return 2; }
            var schema = Schema.Load(c.Plugin(t.Group.Magic), 0x10, 0x14, 0xC);
            Dumper.Dump(c.File, c.Reader, t, schema, Console.Out, idx =>
            {
                if (idx == 0xFFFFFFFF) return "null";
                var di = new DatumIndex(idx);
                if (!c.File.Tags.IsValidIndex(di)) return "invalid 0x" + idx.ToString("X8");
                var tt = c.File.Tags[di]; return CharConstant.ToString(tt.Group.Magic) + " " + c.Name(tt);
            });
        }
        return 0;
    }

    // 360 bitmap entries: big-endian signature, 360 layout flags, pixel sizes as stock 360 tags record them.
    static void BitmapTagFix(Translator tr, DataBlock root, Schema ds, Func<int, BitmapConverter.Result> result)
    {
        var bf = ds.Fields.First(f => f.Name == "Bitmaps");
        var fx = root.AddressFixups.FirstOrDefault(f => f.WriteOffset == bf.Offset + 4); if (fx == null) return;
        var blk = tr.Get(fx.OriginalAddress); if (blk == null) return;
        Func<string, int> off = n => (int)bf.Kids.First(k => k.Name == n).Offset;
        for (int i = 0; i < blk.EntryCount; i++)
        {
            int b = i * (int)bf.ElementSize; var d = blk.Data;
            var r = result(i);
            d[b + off("Signature")] = (byte)'b'; d[b + off("Signature") + 1] = (byte)'i'; d[b + off("Signature") + 2] = (byte)'t'; d[b + off("Signature") + 3] = (byte)'m';
            d[b + off("More Flags")] = (byte)(0x1E | (r != null && r.Secondary ? 0x20 : 0));
            Action<string, uint> put = (n, v) => { int a = b + off(n); d[a] = (byte)(v >> 24); d[a + 1] = (byte)(v >> 16); d[a + 2] = (byte)(v >> 8); d[a + 3] = (byte)v; };
            put("Pixels Offset", 0); put("Pixels Size", 0); put("High Res Pixels Offset", 0);
            put("High Res Pixels Size", r != null && r.Secondary ? (uint)BitConverter.ToInt32(new byte[] { r.Resource.Info[0x17], r.Resource.Info[0x16], r.Resource.Info[0x15], r.Resource.Info[0x14] }, 0) : 0);
            put("Hardware Format", 0xFFFFFFFF);
            if (r != null && r.Format >= 0) { int a = b + off("Format"); d[a] = (byte)(r.Format >> 8); d[a + 1] = (byte)r.Format; }
        }
    }

    static int Port(EngineDatabase db, string mccPath, string x360Path, string outPath, string[] roots, string[] all)
    {
        // Roots are the plain arguments; an option's value (the argument after any --name except the bare switches) is not a root.
        {
            var bare = new HashSet<string> { "--skip-animations", "--skip-sounds" }; var rl = new List<string>();
            for (int i = 4; i < all.Length; i++)
            {
                if (all[i].StartsWith("--")) { if (!bare.Contains(all[i])) i++; continue; }
                rl.Add(all[i]);
            }
            roots = rl.ToArray();
        }
        // options: --retarget grp:old name=new name   (applied to scenario and multiplayer globals tags after injection)
        var retargets = new List<(string group, string from, string to)>();
        for (int i = 0; i < all.Length - 1; i++)
            if (all[i] == "--retarget")
            {
                var v = all[i + 1]; int c = v.IndexOf(':'), e = v.IndexOf('=');
                retargets.Add((v.Substring(0, c), v.Substring(c + 1, e - c - 1), v.Substring(e + 1)));
            }
        // --substitute grp:mcc name=360 name   use an existing 360 tag instead of converting the MCC one
        var substitutes = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        for (int i = 0; i < all.Length - 1; i++)
            if (all[i] == "--substitute") { var v = all[i + 1]; int e = v.IndexOf('='); substitutes[v.Substring(0, e)] = v.Substring(e + 1); }
        roots = roots.Where(r => !r.Contains("=")).ToArray();   // option values carry '=', tag names never do
        if (Path.GetFullPath(outPath).Equals(Path.GetFullPath(x360Path), StringComparison.OrdinalIgnoreCase)) { Console.WriteLine("output must be a new file"); return 1; }
        System.IO.File.Copy(x360Path, outPath, true);
        var container = new TagContainer();
        var convert = new List<ITag>(); var reuse = new List<ITag>(); var noPlugin = new List<ITag>();
        var built = new Dictionary<uint, DataBlockBuilder>();
        var log = new List<string>();
        var animNames = new List<AnimationConverter.Result>();
        using (var src = new Cache(db, mccPath))
        {
            using (var dstRead = new Cache(db, x360Path))
            {
                var schemas = new Dictionary<string, Schema>();
                Func<Cache, int, Schema> schema = (c, magic) =>
                {
                    var p = c.Plugin(magic); if (p == null) return null;
                    if (!schemas.TryGetValue(p, out var s)) schemas[p] = s = Schema.Load(p, 0x10, 0x14, 0xC);
                    return s;
                };
                var srcTrees = new Dictionary<uint, Elem>(); var dstTrees = new Dictionary<string, Elem>(StringComparer.OrdinalIgnoreCase);
                var synth = new Dictionary<string, DatumIndex>(StringComparer.OrdinalIgnoreCase); ushort synthNext = 0;
                var rule = new ShaderRule(
                    dstRead.ByName.Keys.Where(k => k.StartsWith("rmt2:")).Select(k => k.Substring(5)),
                    key =>
                    {
                        if (dstTrees.TryGetValue(key, out var e)) return e;
                        if (!dstRead.ByName.TryGetValue(key, out var t)) return null;
                        return dstTrees[key] = TagTree.Read(dstRead.File, dstRead.Reader, t, schema(dstRead, t.Group.Magic));
                    },
                    key => dstRead.ByName.ContainsKey(key),
                    idx =>
                    {
                        if (srcTrees.TryGetValue(idx, out var e)) return e;
                        var t = src.File.Tags[new DatumIndex(idx)];
                        return srcTrees[idx] = TagTree.Read(src.File, src.Reader, t, schema(src, t.Group.Magic));
                    },
                    idx => src.Name(src.File.Tags[new DatumIndex(idx)]),
                    idx => { var di = new DatumIndex(idx); return idx == 0xFFFFFFFF || !dstRead.File.Tags.IsValidIndex(di) ? null : dstRead.Name(dstRead.File.Tags[di]); },
                    (group, name) =>
                    {
                        var key = group + ":" + name;
                        if (!dstRead.ByName.ContainsKey(key)) return DatumIndex.Null;
                        if (synth.TryGetValue(key, out var di)) return di;
                        di = new DatumIndex(0xFEED, synthNext++);
                        container.AddTag(new ExtractedTag(di, 0, CharConstant.FromString(group), name));
                        return synth[key] = di;
                    });
                int rmt2 = CharConstant.FromString("rmt2");
                var substituted = new Dictionary<uint, string>();
                Walk(src, dstRead, roots, convert, reuse, noPlugin, built, t =>
                {
                    var key = CharConstant.ToString(t.Group.Magic) + ":" + src.Name(t);
                    if (substitutes.TryGetValue(key, out var stock))
                    {
                        if (!dstRead.ByName.ContainsKey(CharConstant.ToString(t.Group.Magic) + ":" + stock)) throw new Exception("substitute not in the 360 map: " + stock);
                        substituted[t.Index.Value] = stock; log.Add("substituted " + key + " -> " + stock); return true;
                    }
                    if (t.Group.Magic != rmt2) return false;
                    rule.Template[t.Index.Value] = rule.Choose(src.Name(t));
                    return true;
                });
                var known = new HashSet<uint>(convert.Concat(reuse).Select(t => t.Index.Value).Concat(rule.Template.Where(kv => kv.Value != null).Select(kv => kv.Key)).Concat(substituted.Keys));
                foreach (var kv in substituted)
                    container.AddTag(new ExtractedTag(new DatumIndex(kv.Key), 0, src.File.Tags[new DatumIndex(kv.Key)].Group.Magic, kv.Value));
                // Resources: convert what has a 360 converter; everything else is cleared (and logged) by the translator.
                var sink = new ResourceSink(container, System.IO.File.ReadAllBytes(SaltPath));
                var table = src.File.Resources.LoadResourceTable(src.Reader);
                Console.WriteLine("source resources " + table.Resources.Count + " typed " + table.Resources.Count(x => !string.IsNullOrEmpty(x.Type)) + " untyped at " + string.Join(",", table.Resources.Select((x, i) => (x, i)).Where(p => string.IsNullOrEmpty(p.x.Type)).Select(p => p.i).Take(40)));
                var converted = new HashSet<uint>(); var bitmapResults = new Dictionary<uint, BitmapConverter.Result>();
                var pageCache = new Dictionary<ResourcePage, byte[]>(); var sharedFiles = new Dictionary<string, Cache>(StringComparer.OrdinalIgnoreCase);
                Func<ResourcePage, byte[]> pageBytes = pg =>
                {
                    if (!pageCache.TryGetValue(pg, out var b))
                    {
                        if (pageCache.Values.Sum(v => v == null ? 0L : v.Length) > 900L * 1024 * 1024) pageCache.Clear();
                        pageCache[pg] = b = Res.PageBytes(src.File, mccPath, src.Stream, pg, pth =>
                        {
                            if (!sharedFiles.TryGetValue(pth, out var o)) sharedFiles[pth] = o = new Cache(db, pth);
                            return o.File;
                        });
                    }
                    return b;
                };
                int bitm = CharConstant.FromString("bitm");
                // Sounds: decoded from the MCC sound banks (beside the map, then the MCC install) with vgmstream.
                string opt(string name, string def) { int i = Array.IndexOf(all, name); return i >= 0 && i + 1 < all.Length ? all[i + 1] : def; }
                var soundFixups = new Dictionary<DataBlockSoundFixup, DataBlockSoundFixup>(); SoundConverter sounds = null;
                Func<SoundConverter> soundConverter = () => sounds ?? (sounds = new SoundConverter(
                    src.File.SoundGestalt.LoadSoundResourceTable(src.Reader), id => src.File.StringIDs.GetString(id),
                    opt("--sound-banks", Path.Combine(Path.GetDirectoryName(Path.GetDirectoryName(mccPath)), "halo3", "fmod", "pc") + ";" + @"D:\SteamLibrary\steamapps\common\Halo The Master Chief Collection\halo3\fmod\pc").Split(';'),
                    opt("--sound-decoder", @"C:\X360\ISOs\H3M\.local\tools\vgmstream-r2117\vgmstream-cli.exe"),
                    Path.Combine(Path.GetDirectoryName(outPath), "_sound_tmp"), container, sink));
                // --sound-donor <360 map> (repeatable): take a sound's samples from that map when it has a sound of the same name.
                // --sound-donor-prefix <text>: a prefix the MCC mod put in front of the original name (e.g. dw3\r3ach\), tried with and without.
                var donorKeep = new List<IDisposable>(); var donors = new List<Func<string, NativeSound>>();
                for (int ai = 0; ai + 1 < all.Length; ai++) if (all[ai] == "--sound-donor") donors.Add(OpenSoundDonor(db, all[ai + 1], donorKeep));
                string donorPrefix = opt("--sound-donor-prefix", null);
                Func<string, NativeSound> nativeSound = name =>
                {
                    foreach (var d in donors)
                    {
                        var n = d(name); if (n != null) return n;
                        if (donorPrefix != null && name.StartsWith(donorPrefix, StringComparison.OrdinalIgnoreCase)) { n = d(name.Substring(donorPrefix.Length)); if (n != null) return n; }
                    }
                    return null;
                };
                foreach (var t in convert)
                {
                    var b = built[t.Index.Value];
                    if (t.Group.Magic != bitm)
                    {
                        foreach (var di in b.ReferencedResources)
                        {
                            var res = table.Resources[di.Index]; var where = CharConstant.ToString(t.Group.Magic) + " " + src.Name(t);
                            if (res.Type == "render_geometry_api_resource_definition")
                            {
                                try { var g = GeometryConverter.Convert(res, pageBytes, sink, t.Index); log.Add("geometry " + where + ": " + g.Note); if (g.Resource != null) converted.Add(di.Value); }
                                catch (Exception ex) { log.Add("geometry " + where + " FAILED: " + ex.Message); }
                            }
                            else if (res.Type == "model_animation_tag_resource" && all.Contains("--skip-animations")) log.Add("animations skipped (diagnostic) in " + where);
                            else if (res.Type == "model_animation_tag_resource")
                            {
                                try
                                {
                                    var an = AnimationConverter.Convert(res, pageBytes, sink, t.Index, sid => src.File.StringIDs.GetString(new StringID(sid)));
                                    log.Add("animations " + where + ": " + an.Note); converted.Add(di.Value); animNames.Add(an);
                                }
                                catch (Exception ex) { log.Add("animations " + where + " FAILED: " + ex.Message); }
                            }
                            else if (res.Type == "sound_resource_definition" && !all.Contains("--skip-sounds"))
                            {
                                try
                                {
                                    var rootBlock = b.DataBlocks[0]; var sf = rootBlock.SoundFixups.FirstOrDefault();
                                    if (sf == null) throw new Exception("sound tag carries no sound table references");
                                    string suffix = rootBlock.StringIDFixups.FirstOrDefault(x => x.WriteOffset == 0x20)?.OriginalString;
                                    var (sres, sfix, note) = soundConverter().Convert(sf, suffix, res, t.Index, nativeSound(src.Name(t)));
                                    soundFixups[sf] = sfix; converted.Add(di.Value); log.Add("sound " + where + ": " + note);
                                }
                                catch (Exception ex) { log.Add("sound " + where + " FAILED: " + ex.Message); }
                            }
                            else if (res.Type == "constant_buffer_resource_definition") { }   // MCC-only shader constants; 360 shaders keep them in the tag
                            else log.Add("resource not converted yet: " + (string.IsNullOrEmpty(res.Type) ? "(empty in source map)" : res.Type) + " in " + where);
                        }
                        continue;
                    }
                    var tree = TagTree.Read(src.File, src.Reader, t, schema(src, t.Group.Magic));
                    var bitmaps = tree.Block("Bitmaps"); var hw = tree.Block("Hardware Textures");
                    for (int i = 0; i < hw.Count; i++)
                    {
                        var di = new DatumIndex(hw[i].Datum("[zone] Asset Datum")); if (!di.IsValid) continue;
                        var res = table.Resources[di.Index];
                        int fmt = i < bitmaps.Count ? (int)bitmaps[i].Num("Format") : -1, curve = i < bitmaps.Count ? (int)bitmaps[i].Num("Curve") : 0;
                        try
                        {
                            var r = BitmapConverter.Convert(res, pageBytes, fmt, curve, sink, t.Index);
                            log.Add($"bitmap {src.Name(t)}[{i}]: {r.Note} (datum {di}, table {res.Index}, type {res.Type})");
                            if (r.Resource != null) { converted.Add(di.Value); bitmapResults[t.Index.Value * 64u + (uint)i] = r; }
                        }
                        catch (Exception ex) { log.Add($"bitmap {src.Name(t)}[{i}] FAILED: {ex.Message}"); }
                    }
                }
                var tr = new Translator(built.Values.SelectMany(b => b.DataBlocks)) { KeepTagRef = i => known.Contains(i.Value), KeepResource = i => converted.Contains(i.Value), SoundFixup = f => soundFixups.TryGetValue(f, out var nf) ? nf : null };
                if (sounds != null) log.Add("sounds: " + sounds.Native + " copied from 360 donor maps, " + sounds.Decoded + " decoded to PCM, " + sounds.Bytes + " bytes");
                foreach (var dk in donorKeep) dk.Dispose();
                foreach (var kv in rule.Template.Where(kv => kv.Value != null))
                    container.AddTag(new ExtractedTag(new DatumIndex(kv.Key), 0, rmt2, kv.Value));
                foreach (var t in convert)
                {
                    var name = src.Name(t); var group = CharConstant.ToString(t.Group.Magic);
                    var ss = schema(src, t.Group.Magic); var ds = schema(dstRead, t.Group.Magic);
                    if (ds == null) { log.Add("NO 360 PLUGIN " + group + " " + name); continue; }
                    uint addr = src.File.PointerExpander.Contract(t.MetaLocation.AsPointer());
                    var root = tr.TranslateRoot(addr, ss, ds, group + " " + name);
                    if (root != null && group == "effe")
                    {
                        // Effect flags: MCC added two bits at positions 8 and 9, so every higher bit sits two places up
                        // (same stock effects in both games: battle rifle firing 0x1402 vs 0x502, wraith mortar firing 0x802 vs 0x202).
                        // The 360 engine reads those bits to decide, among other things, whether the effect plays its sound parts.
                        var d = root.Data; uint v = (uint)(d[0] << 24 | d[1] << 16 | d[2] << 8 | d[3]);
                        uint w = (v & 0xFF) | ((v >> 2) & 0xFFFFFF00);
                        d[0] = (byte)(w >> 24); d[1] = (byte)(w >> 16); d[2] = (byte)(w >> 8); d[3] = (byte)w;
                        if (w != v) log.Add($"effe {name}: flags 0x{v:X} -> 0x{w:X}");
                        // Event durations: MCC runs effects at 60 ticks a second, the 360 at 30. A one-tick event is 1/60 s in MCC
                        // and 1/30 s on the 360 (same stock effect in both games); a 1/60 s event is shorter than a 360 tick.
                        var evF = ds.Fields.FirstOrDefault(f => f.Name == "Events" && f.Kind == Kind.Block);
                        var evFix = evF == null ? null : root.AddressFixups.FirstOrDefault(f => f.WriteOffset == evF.Offset + 4);
                        var evBlk = evFix == null ? null : tr.Get(evFix.OriginalAddress);
                        var durF = evF?.Kids.FirstOrDefault(k => k.Name == "Duration Bounds");
                        if (evBlk != null && durF != null)
                            for (int e = 0; e < evBlk.EntryCount; e++)
                                for (int k = 0; k < 2; k++)
                                {
                                    int a = e * (int)evF.ElementSize + (int)durF.Offset + k * 4; var ed = evBlk.Data;
                                    float fv = BitConverter.ToSingle(new[] { ed[a + 3], ed[a + 2], ed[a + 1], ed[a] }, 0);
                                    if (Math.Abs(fv - 1f / 60f) < 1e-5f) { var nb = BitConverter.GetBytes(1f / 30f); ed[a] = nb[3]; ed[a + 1] = nb[2]; ed[a + 2] = nb[1]; ed[a + 3] = nb[0]; }
                                }
                    }
                    if (root != null && rule.Applies(ds)) rule.Apply(tr, root, ds, group + " " + name);
                    else if (root != null) { int nested = rule.ApplyNested(tr, root, ds.Fields, 0, group + " " + name); if (nested > 0) log.Add(group + " " + name + ": " + nested + " embedded render method(s) mapped"); }
                    if (root != null && t.Group.Magic == bitm) BitmapTagFix(tr, root, ds, i => bitmapResults.TryGetValue(t.Index.Value * 64u + (uint)i, out var r) ? r : null);
                    container.AddTag(new ExtractedTag(t.Index, addr, t.Group.Magic, name));
                }
                foreach (var t in reuse) container.AddTag(new ExtractedTag(t.Index, 0, t.Group.Magic, src.Name(t)));
                foreach (var b in tr.Output) container.AddDataBlock(b);
                log.AddRange(rule.Log); log.AddRange(tr.Log);
                Console.WriteLine($"translated {convert.Count} tags into {tr.Output.Count} blocks | reused {reuse.Count} | templates {rule.Template.Count} | no plugin {noPlugin.Count} | dropped refs {tr.Dropped} | functions {tr.Functions}, identity re-expressed {tr.Identity} (+{tr.FunctionFallbacks} fallback)");
            }
        }
        using (var dst = new Cache(db, outPath)) { }   // validate the copy opens
        var outEngineDb = db;
        using (var fs = System.IO.File.Open(outPath, FileMode.Open, FileAccess.ReadWrite))
        {
            var reader = new EndianReader(fs, Endian.BigEndian);
            var file = CacheFileLoader.LoadCacheFile(reader, outPath, outEngineDb, out var engine);
            var stream = new EndianStream(fs, engine.Endian);
            var injector = new TagContainerInjector(file, container, engine, true, true, false, false);
            int injected = 0;
            foreach (var t in convert)
            {
                var et = container.FindTag(t.Index); if (et == null) continue;
                var ni = injector.InjectTag(et, stream);
                log.Add("INJECTED " + CharConstant.ToString(et.Group) + " " + et.Name + " -> " + ni);
                injected++;
            }
            // Animation resources name their members by string id: write the 360 ids (added to the map when absent).
            foreach (var an in animNames)
                foreach (var (offset, name) in an.Names)
                {
                    var sid = string.IsNullOrEmpty(name) ? StringID.Null : file.StringIDs.FindStringID(name);
                    if (!string.IsNullOrEmpty(name) && sid == StringID.Null) sid = file.StringIDs.AddString(name);
                    var info = an.Resource.Info; uint v = sid.Value;
                    info[offset] = (byte)(v >> 24); info[offset + 1] = (byte)(v >> 16); info[offset + 2] = (byte)(v >> 8); info[offset + 3] = (byte)v;
                }
            injector.SaveChanges(stream);
            Console.WriteLine($"injected tags {injector.InjectedTags.Count} | blocks {injector.InjectedBlocks.Count} | strings {injector.InjectedStringIDs.Count} | resources {injector.InjectedResources.Count} | pages {injector.InjectedPages.Count}");
        }
        // --move <scenario block>:<index>=x,y,z[,yaw]   reposition one placement (e.g. Vehicles:12) in the target scenario
        var moves = new List<(string block, int index, float[] v)>();
        for (int i = 0; i < all.Length - 1; i++)
            if (all[i] == "--move")
            {
                var v = all[i + 1]; int c1 = v.IndexOf(':'), e = v.IndexOf('=');
                moves.Add((v.Substring(0, c1), int.Parse(v.Substring(c1 + 1, e - c1 - 1)), v.Substring(e + 1).Split(',').Select(x => float.Parse(x, System.Globalization.CultureInfo.InvariantCulture)).ToArray()));
            }
        if (moves.Count > 0 || all.Contains("--move-all"))
            using (var c = new Cache(db, outPath, true))
            {
                var stream = new EndianStream(c.Stream, c.Engine.Endian);
                var scnr = c.File.Tags.First(t => t != null && t.Group != null && CharConstant.ToString(t.Group.Magic) == "scnr" && t.MetaLocation != null);
                var schema = Schema.Load(c.Plugin(scnr.Group.Magic), 0x10, 0x14, 0xC);
                foreach (var (block, index, v) in moves)
                {
                    var bf = schema.Fields.First(f => f.Kind == Kind.Block && f.Name == block);
                    stream.SeekTo(scnr.MetaLocation.AsOffset() + bf.Offset); int count = stream.ReadInt32(); uint ptr = stream.ReadUInt32();
                    if (index >= count) { Console.WriteLine($"MOVE: {block} has {count} entries"); return 3; }
                    long el = c.File.MetaArea.PointerToOffset(c.File.PointerExpander.Expand(ptr)) + index * bf.ElementSize;
                    var pos = bf.Kids.First(k => k.Name == "Position"); var rot = bf.Kids.First(k => k.Name == "Rotation");
                    stream.SeekTo(el + pos.Offset); for (int k = 0; k < 3; k++) stream.WriteFloat(v[k]);
                    if (v.Length > 3) { stream.SeekTo(el + rot.Offset); stream.WriteFloat(v[3]); stream.WriteFloat(0); stream.WriteFloat(0); }
                    log.Add($"moved {block}[{index}] to {string.Join(",", v)}");
                }
                // --move-all <block>:<palette tag name>=x,y,z[,yaw]   every placement of that palette entry (e.g. all respawn points)
                for (int i = 0; i < all.Length - 1; i++)
                {
                    if (all[i] != "--move-all") continue;
                    var v = all[i + 1]; int c1 = v.IndexOf(':'), e = v.IndexOf('=');
                    string block = v.Substring(0, c1), tagName = v.Substring(c1 + 1, e - c1 - 1);
                    var xyz = v.Substring(e + 1).Split(',').Select(x => float.Parse(x, System.Globalization.CultureInfo.InvariantCulture)).ToArray();
                    var bf = schema.Fields.First(f => f.Kind == Kind.Block && f.Name == block);
                    var pf = schema.Fields.First(f => f.Kind == Kind.Block && f.Name == block + " Palette");
                    var tree = TagTree.Read(c.File, c.Reader, scnr, schema);
                    var pal = tree.Block(pf.Name).Select(p => { var d = p.F.Values.OfType<uint>().First(); var di = new DatumIndex(d); return d != 0xFFFFFFFF && c.File.Tags.IsValidIndex(di) ? c.Name(c.File.Tags[di]) : ""; }).ToList();
                    var places = tree.Block(block);
                    stream.SeekTo(scnr.MetaLocation.AsOffset() + bf.Offset); stream.ReadInt32(); uint ptr = stream.ReadUInt32();
                    long baseOff = c.File.MetaArea.PointerToOffset(c.File.PointerExpander.Expand(ptr));
                    var pos = bf.Kids.First(k => k.Name == "Position"); var rot = bf.Kids.First(k => k.Name == "Rotation");
                    int n = 0;
                    for (int k = 0; k < places.Count; k++)
                    {
                        int pi = (int)places[k].Num("Palette Index");
                        if (pi < 0 || pi >= pal.Count || !pal[pi].Equals(tagName, StringComparison.OrdinalIgnoreCase)) continue;
                        long el = baseOff + k * bf.ElementSize;
                        stream.SeekTo(el + pos.Offset); for (int q = 0; q < 3; q++) stream.WriteFloat(xyz[q]);
                        if (xyz.Length > 3) { stream.SeekTo(el + rot.Offset); stream.WriteFloat(xyz[3]); stream.WriteFloat(0); stream.WriteFloat(0); }
                        n++;
                    }
                    log.Add($"moved all {n} {block} placements of {tagName}"); Console.WriteLine($"moved all {n} placements of {tagName}");
                }
                Console.WriteLine("moved placements " + moves.Count);
            }
        if (retargets.Count > 0)
            using (var c = new Cache(db, outPath, true))
            {
                var stream = new EndianStream(c.Stream, c.Engine.Endian);
                var map = new Dictionary<uint, uint>();
                foreach (var (g, from, to) in retargets)
                {
                    if (!c.ByName.TryGetValue(g + ":" + from, out var a) || !c.ByName.TryGetValue(g + ":" + to, out var b)) { Console.WriteLine("RETARGET MISSING " + g + ":" + from + " or " + to); return 3; }
                    map[a.Index.Value] = b.Index.Value;
                }
                int total = 0;
                foreach (var t in c.File.Tags)
                {
                    if (t == null || t.Group == null || t.MetaLocation == null) continue;
                    var gname = CharConstant.ToString(t.Group.Magic);
                    if (gname != "scnr" && gname != "mulg") continue;
                    total += Retarget.Apply(c.File, stream, t, Schema.Load(c.Plugin(t.Group.Magic), 0x10, 0x14, 0xC), map, log, gname + " " + c.Name(t));
                }
                Console.WriteLine("retargeted references " + total);
            }
        // --add-string <new key>=<existing key>|<text>   add <text> under <new key> to the string list that holds
        // <existing key>, in every language (the English text is used where no translation exists)
        var adds = new List<(string key, string like, string text)>();
        for (int i = 0; i < all.Length - 1; i++)
            if (all[i] == "--add-string")
            {
                var v = all[i + 1]; int e = v.IndexOf('='), b = v.IndexOf('|', e);
                adds.Add((v.Substring(0, e), v.Substring(e + 1, b - e - 1), v.Substring(b + 1)));
            }
        // --set grp:tag name/Block[i or *]/.../Field=value[ value...]   set number fields (several numbers for vectors)
        var sets = all.Select((a, i) => (a, i)).Where(x => x.a == "--set" && x.i + 1 < all.Length).Select(x => all[x.i + 1]).ToList();
        if (sets.Count > 0)
            using (var c = new Cache(db, outPath, true))
            {
                var stream = new EndianStream(c.Stream, c.Engine.Endian);
                var inv = System.Globalization.CultureInfo.InvariantCulture;
                foreach (var v in sets)
                {
                    int e = v.LastIndexOf('='); var spec = v.Substring(0, e); var vals = v.Substring(e + 1).Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
                    var parts = spec.Split('/'); var key = parts[0]; int used = 1;
                    while (!c.ByName.ContainsKey(key) && used < parts.Length) key += "/" + parts[used++];
                    if (!c.ByName.TryGetValue(key, out var t)) { Console.WriteLine("SET: no tag in " + spec); return 3; }
                    var path = parts.Skip(used).ToArray(); int n = 0;
                    void Go(long at, List<Node> fields, int depth)
                    {
                        var seg = path[depth]; int br = seg.IndexOf('['); var name = br < 0 ? seg : seg.Substring(0, br);
                        int ao = name.IndexOf("@0x"); uint wantOff = ao < 0 ? 0 : Convert.ToUInt32(name.Substring(ao + 3), 16); if (ao >= 0) name = name.Substring(0, ao);   // Field@0xOFFSET picks one of several same-named fields
                        var f = fields.FirstOrDefault(x => x.Name == name && (ao < 0 || x.Offset == wantOff)); if (f == null) return;
                        if (depth == path.Length - 1)
                        {
                            stream.SeekTo(at + f.Offset);
                            foreach (var val in vals)
                                switch (f.Type)
                                {
                                    case "i16": case "u16": case "enum16": case "flags16": case "range16": stream.WriteInt16(short.Parse(val)); break;
                                    case "i8": case "u8": case "enum8": case "flags8": stream.WriteByte((byte)sbyte.Parse(val)); break;
                                    case "i32": case "u32": case "enum32": case "flags32": stream.WriteInt32(int.Parse(val)); break;
                                    default: stream.WriteFloat(float.Parse(val, inv)); break;   // reals, vectors, angles, ranges
                                }
                            n++; return;
                        }
                        stream.SeekTo(at + f.Offset); int count = stream.ReadInt32(); uint ptr = stream.ReadUInt32(); if (count <= 0) return;
                        long b0 = c.File.MetaArea.PointerToOffset(c.File.PointerExpander.Expand(ptr));
                        var idx = seg.Substring(br + 1).TrimEnd(']');
                        foreach (var i in idx == "*" ? Enumerable.Range(0, count) : new[] { int.Parse(idx) })
                            if (i < count) Go(b0 + i * f.ElementSize, f.Kids, depth + 1);
                    }
                    Go(t.MetaLocation.AsOffset(), Schema.Load(c.Plugin(t.Group.Magic), 0x10, 0x14, 0xC).Fields, 0);
                    if (n == 0) { Console.WriteLine("SET: no field for " + spec); return 3; }
                    log.Add($"set {spec} = {string.Join(" ", vals)}");
                }
                Console.WriteLine("set fields " + sets.Count);
            }
        // --set-string grp:tag name/Block[i or *]/.../Field=new string   point string-id fields at another string
        foreach (var v in all.Select((a, i) => (a, i)).Where(x => x.a == "--set-string" && x.i + 1 < all.Length).Select(x => all[x.i + 1]).ToList())
            using (var c = new Cache(db, outPath, true))
            {
                var stream = new EndianStream(c.Stream, c.Engine.Endian);
                int e = v.LastIndexOf('='); var newStr = v.Substring(e + 1); var spec = v.Substring(0, e);
                var parts = spec.Split('/'); var key = parts[0]; int used = 1;
                while (!c.ByName.ContainsKey(key) && used < parts.Length) key += "/" + parts[used++];
                if (!c.ByName.TryGetValue(key, out var t)) { Console.WriteLine("SET-STRING: no tag in " + spec); return 3; }
                var sid = c.File.StringIDs.FindStringID(newStr); if (sid == StringID.Null) sid = c.File.StringIDs.AddString(newStr);
                var path = parts.Skip(used).ToArray(); int n = 0;
                void Go(long at, List<Node> fields, int depth)
                {
                    var seg = path[depth]; int br = seg.IndexOf('['); var name = br < 0 ? seg : seg.Substring(0, br);
                    var f = fields.FirstOrDefault(x => x.Name == name); if (f == null) return;
                    if (depth == path.Length - 1) { stream.SeekTo(at + f.Offset); stream.WriteUInt32(sid.Value); n++; return; }
                    stream.SeekTo(at + f.Offset); int count = stream.ReadInt32(); uint ptr = stream.ReadUInt32(); if (count <= 0) return;
                    long b0 = c.File.MetaArea.PointerToOffset(c.File.PointerExpander.Expand(ptr));
                    var idx = seg.Substring(br + 1).TrimEnd(']');
                    foreach (var i in idx == "*" ? Enumerable.Range(0, count) : new[] { int.Parse(idx) })
                        if (i < count) Go(b0 + i * f.ElementSize, f.Kids, depth + 1);
                }
                Go(t.MetaLocation.AsOffset(), Schema.Load(c.Plugin(t.Group.Magic), 0x10, 0x14, 0xC).Fields, 0);
                c.File.SaveChanges(stream);
                log.Add($"set-string {spec} = {newStr} ({n} fields)"); Console.WriteLine($"set-string {newStr}: {n} fields");
            }
        if (adds.Count > 0)
            using (var c = new Cache(db, outPath, true))
            {
                var stream = new EndianStream(c.Stream, c.Engine.Endian);
                foreach (var lang in c.File.Languages.AvailableLanguages.ToList())
                {
                    var pack = c.File.Languages.LoadLanguage(lang, c.Reader);
                    int added = 0;
                    foreach (var (key, like, text) in adds)
                    {
                        var likeId = c.File.StringIDs.FindStringID(like);
                        var list = pack.StringLists.FirstOrDefault(l => l.Strings.Any(x => x.Key == likeId));
                        if (list == null) { log.Add($"add-string: no list holds {like} ({lang})"); continue; }
                        var id = c.File.StringIDs.FindStringID(key);
                        if (id == StringID.Null) id = c.File.StringIDs.AddString(key);
                        if (list.Strings.Any(x => x.Key == id)) continue;
                        // empty text: copy the existing string; "{icon}" in text is replaced by the existing string's icon glyphs
                        var like0 = list.Strings.First(x => x.Key == likeId).Value;
                        var glyphs = new string(like0.Where(ch => ch >= 0xE000 && ch <= 0xF8FF).ToArray());
                        // "\uXXXX" in the text writes the game's private button / weapon glyphs (U+E445 = RB)
                        var value = text.Length > 0 ? System.Text.RegularExpressions.Regex.Replace(text.Replace("{icon}", glyphs),
                            @"\\u([0-9A-Fa-f]{4})", m => ((char)Convert.ToInt32(m.Groups[1].Value, 16)).ToString()) : like0;
                        list.Strings.Add(new Blamite.Blam.Localization.LocalizedString(id, value)); added++;
                    }
                    c.File.Languages.SaveLanguage(pack, stream);
                    log.Add($"add-string: {added} strings added ({lang})");
                }
                c.File.SaveChanges(stream);
                Console.WriteLine("added strings " + adds.Count);
            }
        Console.WriteLine("before finalize: " + Integrity.Verify(outPath, System.IO.File.ReadAllBytes(SaltPath)));
        Integrity.Finalize(outPath, System.IO.File.ReadAllBytes(SaltPath));
        Console.WriteLine("after finalize: " + Integrity.Verify(outPath, System.IO.File.ReadAllBytes(SaltPath)));
        var logPath = Path.ChangeExtension(outPath, ".port.log");
        System.IO.File.WriteAllLines(logPath, log);
        Console.WriteLine("log " + logPath);
        return 0;
    }
}
