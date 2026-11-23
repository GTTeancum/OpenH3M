// graft <donor 360 map> <target 360 map> <out map> <tag name>...
// Copies tags between two maps of the same engine unchanged (no translation): used to bring a stock 360 tag that
// the target map lacks (for example a shader template with its compiled shaders) from another stock 360 map.
// Tags the target already has (same group and name) are referenced, not copied.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Xml;
using Blamite.Blam;
using Blamite.Injection;
using Blamite.IO;
using Blamite.Plugins;
using Blamite.Serialization;
using Blamite.Util;
using Inject360;

partial class Program
{
    static int Graft(EngineDatabase db, string donorPath, string targetPath, string outPath, string[] roots)
    {
        var container = new TagContainer(); var copied = new List<ITag>(); int reused = 0;
        using (var src = new Cache(db, donorPath))
        using (var dst = new Cache(db, targetPath))
        {
            if (src.Engine.Name != dst.Engine.Name) throw new Exception("graft needs two maps of the same engine: " + src.Engine.Name + " / " + dst.Engine.Name);
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
                if (t == null || t.MetaLocation == null || !seen.Add(t.Index.Value)) continue;
                string name = src.Name(t);
                if (dst.ByName.ContainsKey(Key(t.Group.Magic, name))) { container.AddTag(new ExtractedTag(t.Index, 0, t.Group.Magic, name)); reused++; continue; }
                var plugin = src.Plugin(t.Group.Magic);
                if (plugin == null) throw new Exception("no plugin for " + CharConstant.ToString(t.Group.Magic) + " " + name);
                var builder = new DataBlockBuilder(src.Reader, t, src.File, src.Engine);
                using (var xr = XmlReader.Create(plugin)) AssemblyPluginLoader.LoadPlugin(xr, builder);
                if (builder.ReferencedResources.Count > 0 || builder.ContainsSoundReferences)
                    throw new Exception("graft does not copy resources or sounds yet: " + CharConstant.ToString(t.Group.Magic) + " " + name);
                foreach (var b in builder.DataBlocks) container.AddDataBlock(b);
                container.AddTag(new ExtractedTag(t.Index, src.File.PointerExpander.Contract(t.MetaLocation.AsPointer()), t.Group.Magic, name));
                copied.Add(t);
                foreach (var tr in builder.ReferencedTags) queue.Enqueue(src.File.Tags[tr]);
            }
        }
        File.Copy(targetPath, outPath, true);
        using (var fs = File.Open(outPath, FileMode.Open, FileAccess.ReadWrite))
        {
            var reader = new EndianReader(fs, Endian.BigEndian);
            var file = CacheFileLoader.LoadCacheFile(reader, outPath, db, out var engine);
            var stream = new EndianStream(fs, engine.Endian);
            var injector = new TagContainerInjector(file, container, engine, true, true, false, false);
            foreach (var t in copied)
            {
                var et = container.FindTag(t.Index);
                var ni = injector.InjectTag(et, stream);
                Console.WriteLine("COPIED " + CharConstant.ToString(et.Group) + " " + et.Name + " -> " + ni);
            }
            injector.SaveChanges(stream);
        }
        Integrity.Finalize(outPath, File.ReadAllBytes(SaltPath));
        Console.WriteLine($"copied {copied.Count} tags, referenced {reused} already on the target");
        return 0;
    }
}
