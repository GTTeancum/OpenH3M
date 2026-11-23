// Resource inspector: what a tag's resources look like in a cache file (definition bytes, fixups, page data).
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Blamite.Blam;
using Blamite.Blam.Resources;
using Blamite.IO;

namespace Inject360
{
    public static class Res
    {
        public static string Hex(byte[] b, int max = 4096)
        {
            var sb = new StringBuilder();
            for (int i = 0; i < Math.Min(b.Length, max); i++) { if (i % 32 == 0) sb.Append("\n      " + i.ToString("X4") + ": "); else if (i % 4 == 0) sb.Append(' '); sb.Append(b[i].ToString("X2")); }
            return sb.ToString();
        }

        // Decompressed bytes of one page (the page may live in another cache file next to this one, e.g. shared.map).
        public static string MccHalo3Maps = @"D:\SteamLibrary\steamapps\common\Halo The Master Chief Collection\halo3\maps";
        public static byte[] PageBytes(ICacheFile file, string mapPath, Stream mapStream, ResourcePage page, Func<string, ICacheFile> other)
        {
            var srcFile = file; var stream = mapStream; Stream owned = null;
            if (!string.IsNullOrEmpty(page.FilePath))
            {
                // The shared file sits beside the map, or (MCC mods) in the mod's halo3\maps folder, or in the MCC install.
                string name = Path.GetFileName(page.FilePath.Replace('\\', '/')), dir = Path.GetDirectoryName(mapPath);
                var p = new[] { Path.Combine(dir, name), Path.Combine(Path.GetDirectoryName(dir) ?? dir, "halo3", "maps", name), Path.Combine(MccHalo3Maps, name) }.FirstOrDefault(File.Exists);
                if (p == null) return null;
                srcFile = other(p); if (srcFile == null) return null;
                owned = stream = File.OpenRead(p);
            }
            try
            {
                var ms = new MemoryStream();
                new ResourcePageExtractor(srcFile).ExtractDecompressPage(page, stream, ms);
                return ms.ToArray();
            }
            finally { owned?.Dispose(); }
        }

        public static void Print(TextWriter w, Resource r, Func<ResourcePage, byte[]> page, string dumpDir)
        {
            w.WriteLine($"  RESOURCE {r.Index} type={r.Type} flags=0x{r.Flags:X} bits={r.ResourceBits} baseDef=0x{r.BaseDefinitionAddress:X} info={r.Info?.Length ?? 0} bytes");
            foreach (var f in r.ResourceFixups) w.WriteLine($"    fixup @0x{f.Offset:X} -> 0x{f.Address:X8}");
            foreach (var f in r.DefinitionFixups) w.WriteLine($"    definition fixup @0x{f.Offset:X} type {f.Type}");
            if (r.Info != null) w.WriteLine("    info:" + Hex(r.Info, 512));
            if (dumpDir != null && r.Info != null)
            {
                File.WriteAllBytes(Path.Combine(dumpDir, $"res_{r.Index.Value:X8}_info.bin"), r.Info);
                File.WriteAllLines(Path.Combine(dumpDir, $"res_{r.Index.Value:X8}_fixups.txt"),
                    new[] { "base " + r.BaseDefinitionAddress + " poff " + (r.Location?.PrimaryOffset ?? 0) + " soff " + (r.Location?.SecondaryOffset ?? 0) }
                    .Concat(r.ResourceFixups.Select(f => f.Offset + " " + f.Address)));
            }
            var loc = r.Location; if (loc == null) return;
            var parts = new[] { ("primary", loc.PrimaryPage, loc.PrimaryOffset, loc.PrimarySize), ("secondary", loc.SecondaryPage, loc.SecondaryOffset, loc.SecondarySize), ("tertiary", loc.TertiaryPage, loc.TertiaryOffset, loc.TertiarySize) };
            foreach (var (name, pg, off, size) in parts)
            {
                if (pg == null) continue;
                w.WriteLine($"    {name}: page {pg.Index} salt=0x{pg.Salt:X} flags=0x{pg.Flags:X} crc=0x{pg.Checksum:X8} assets={pg.AssetCount} u1={pg.Unknown1} u2={pg.Unknown2} h1={(pg.Hash1 == null ? "-" : BitConverter.ToString(pg.Hash1, 0, 4))} file='{pg.FilePath}' comp={pg.CompressionMethod} csize={pg.CompressedSize} usize={pg.UncompressedSize} offset={off} size={size?.Size}"
                    + (size?.Parts != null ? " parts=" + string.Join(",", size.Parts.Select(p => p.Offset + "+" + p.Size)) : ""));
                if (dumpDir == null) continue;
                var bytes = page(pg); if (bytes == null) { w.WriteLine("      (page unavailable)"); continue; }
                int len = size?.Size ?? bytes.Length - off; len = Math.Max(0, Math.Min(len, bytes.Length - off));
                var outp = Path.Combine(dumpDir, $"res_{r.Index.Value:X8}_{name}.bin");
                File.WriteAllBytes(outp, bytes.Skip(off).Take(len).ToArray());
                w.WriteLine($"      -> {outp} ({len} bytes)");
            }
        }
    }
}
