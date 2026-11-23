// Sounds taken from an Xbox 360 map (Halo 3 or Reach) by tag name: the tag's sound-table references, the map's
// sound tables, and the sound's data (its primary block followed by its secondary block, as chunk offsets expect).
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Xml;
using Blamite.Blam;
using Blamite.Blam.Resources;
using Blamite.Injection;
using Blamite.Plugins;
using Blamite.Serialization;
using Blamite.Util;
using Inject360;

partial class Program
{
    // Returns a lookup: sound tag name -> the donor's copy, or null when the donor has no usable sound of that name.
    static Func<string, NativeSound> OpenSoundDonor(EngineDatabase db, string mapPath, List<IDisposable> keep)
    {
        var c = new Cache(db, mapPath); keep.Add(c);
        if (c.Engine.Endian != Blamite.IO.Endian.BigEndian) throw new Exception("sound donor must be an Xbox 360 map: " + mapPath);
        var st = c.File.SoundGestalt.LoadSoundResourceTable(c.Reader);
        var rt = c.File.Resources.LoadResourceTable(c.Reader);
        var others = new Dictionary<string, Cache>(StringComparer.OrdinalIgnoreCase);
        var pages = new Dictionary<string, byte[]>();
        Func<ResourcePage, byte[]> page = pg =>
        {
            string key = pg.FilePath + "|" + pg.Index;
            if (pages.TryGetValue(key, out var have)) return have;
            if (pages.Count > 6) pages.Clear();
            return pages[key] = Res.PageBytes(c.File, mapPath, c.Stream, pg, pth =>
            {
                if (!File.Exists(pth)) return null;
                if (!others.TryGetValue(pth, out var o)) { others[pth] = o = new Cache(db, pth); keep.Add(o); }
                return o.File;
            });
        };
        int snd = CharConstant.FromString("snd!");
        return name =>
        {
            if (!c.ByName.TryGetValue("snd!:" + name, out var t)) return null;
            var b = new DataBlockBuilder(c.Reader, t, c.File, c.Engine);
            using (var xr = XmlReader.Create(c.Plugin(snd))) AssemblyPluginLoader.LoadPlugin(xr, b);
            var fix = b.DataBlocks[0].SoundFixups.FirstOrDefault(); if (fix == null || b.ReferencedResources.Count == 0) return null;
            var r = rt.Resources[b.ReferencedResources.First().Index]; var loc = r.Location; if (loc == null) return null;
            var data = new List<byte>();
            foreach (var (pg, off, size) in new[] { (loc.PrimaryPage, loc.PrimaryOffset, loc.PrimarySize), (loc.SecondaryPage, loc.SecondaryOffset, loc.SecondarySize) })
            {
                if (pg == null || size == null || size.Size <= 0) continue;
                var all = page(pg); if (all == null) return null;                 // resource stripped from this map, or its shared file is missing
                int at = Math.Max(0, off); if (at + size.Size > all.Length) return null;
                data.AddRange(all.Skip(at).Take(size.Size));
            }
            if (data.Count == 0) return null;
            return new NativeSound { Fixup = fix, Table = st, Str = id => c.File.StringIDs.GetString(id), Data = data.ToArray(), Source = Path.GetFileName(Path.GetDirectoryName(Path.GetDirectoryName(mapPath))) + " " + Path.GetFileName(mapPath) };
        };
    }
}
