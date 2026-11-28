// Experiment patches on a COPY of a map in the private test folder (never on stock or installed files).
// blankclustermopp <map copy> <sbsp name>: sets every cluster's instanced-geometry MOPP code block count to 0 (cluster
// +0x90 in the 360 layout), as Halo 3's own tools leave it in tags, to see whether the 360 game builds the cluster
// instance index itself or needs the stored one.
using System;
using System.IO;
using System.Linq;
using Blamite.Blam;
using Blamite.IO;

namespace Ho2H3
{
    static class PatchProbe
    {
        public static int Run(string[] a)
        {
            var full = Path.GetFullPath(a[1]);
            if (full.IndexOf(Path.DirectorySeparatorChar + ".local" + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) < 0 || full.StartsWith("C:" + Path.DirectorySeparatorChar + "X360", StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("only map copies inside the repository .local folder");
            using var m = new Map(full, true);
            var t = m.ByName["sbsp:" + a[2]];
            var w = new EndianStream(m.Stream, Endian.BigEndian);
            long tagOff = t.MetaLocation.AsOffset();
            m.Stream.Position = tagOff + 0xB4; int count = w.ReadInt32(); uint addr = w.ReadUInt32();
            long clusters = m.File.MetaArea.PointerToOffset(addr);
            int blanked = 0;
            for (int i = 0; i < count; i++)
            {
                m.Stream.Position = clusters + i * 220L + 0x90; int n = w.ReadInt32();
                if (n != 0) { m.Stream.Position = clusters + i * 220L + 0x90; w.WriteInt32(0); blanked++; }
            }
            Console.WriteLine($"{count} clusters, {blanked} cluster MOPP code blocks set to count 0");
            return 0;
        }

        // rawinst <map> <sbsp> <instance index>: the instance record (0x78) and its first bsp physics element (0x70) as raw bytes
        public static int RawInst(string[] a)
        {
            using var m = new Map(Path.GetFullPath(a[1]));
            var t = m.ByName["sbsp:" + a[2]]; var r = m.Reader;
            long tagOff = t.MetaLocation.AsOffset();
            m.Stream.Position = tagOff + 0x1B0; int count = r.ReadInt32(); uint addr = r.ReadUInt32();
            int i = int.Parse(a[3]); long at = m.File.MetaArea.PointerToOffset(addr) + i * 0x78L;
            m.Stream.Position = at; var inst = r.ReadBlock(0x78);
            void Hex(string what, byte[] b) { for (int o = 0; o < b.Length; o += 16) Console.WriteLine($"{what} +{o:X2}: {string.Join(" ", b.Skip(o).Take(16).Select(x => x.ToString("x2")))}"); }
            Hex("instance", inst);
            int pc = (inst[0x60] << 24) | (inst[0x61] << 16) | (inst[0x62] << 8) | inst[0x63]; uint pa = (uint)((inst[0x64] << 24) | (inst[0x65] << 16) | (inst[0x66] << 8) | inst[0x67]);
            if (pc > 0) { m.Stream.Position = m.File.MetaArea.PointerToOffset(pa); Hex("physics", r.ReadBlock(0x70)); }
            return 0;
        }

        // rawtag <map> <group:name> <offset hex> <length hex>: raw bytes of a tag's main struct
        public static int RawTag(string[] a)
        {
            using var m = new Map(Path.GetFullPath(a[1]));
            var t = m.ByName[a[2]]; var r = m.Reader;
            m.Stream.Position = t.MetaLocation.AsOffset() + Convert.ToInt64(a[3], 16);
            var b = r.ReadBlock(Convert.ToInt32(a[4], 16));
            for (int o = 0; o < b.Length; o += 16) Console.WriteLine($"+{Convert.ToInt64(a[3], 16) + o:X3}: {string.Join(" ", b.Skip(o).Take(16).Select(x => x.ToString("x2")))}");
            return 0;
        }
    }
}
