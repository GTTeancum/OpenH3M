// texscan <360 map>: one line per stock texture (size, levels, type, format, GPU fetch word, flags, data sizes),
// used to learn the rules the original tools followed (which textures are tiled, how sizes are computed).
using System;
using System.Linq;
using Blamite.Blam;
using Blamite.Serialization;
using Blamite.Util;
using Inject360;

partial class Program
{
    static int TexScan(EngineDatabase db, string[] args)
    {
        using (var b = new Cache(db, args[1]))
        {
            var tb = b.File.Resources.LoadResourceTable(b.Reader);
            int bm = CharConstant.FromString("bitm"); var sb0 = Schema.Load(b.Plugin(bm), 0x10, 0x14, 0xC);
            foreach (var kv in b.ByName.Where(k => k.Value.Group.Magic == bm))
            {
                var tr = TagTree.Read(b.File, b.Reader, kv.Value, sb0);
                var hw = tr.Block("Hardware Textures"); var bs = tr.Block("Bitmaps");
                for (int i = 0; i < hw.Count && i < bs.Count; i++)
                {
                    var d = new DatumIndex(hw[i].Datum("[zone] Asset Datum")); if (!d.IsValid) continue;
                    var ib = tb.Resources[d.Index].Info; if (ib == null || ib.Length < 0x40) continue;
                    uint gpu = (uint)(ib[0x30] << 24 | ib[0x31] << 16 | ib[0x32] << 8 | ib[0x33]);
                    int p = ib[0] << 24 | ib[1] << 16 | ib[2] << 8 | ib[3], s = ib[0x14] << 24 | ib[0x15] << 16 | ib[0x16] << 8 | ib[0x17];
                    Console.WriteLine(string.Join("\t", (ib[0x28] << 8 | ib[0x29]), (ib[0x2A] << 8 | ib[0x2B]), ib[0x2C], ib[0x2D], ib[0x2E], ib[0x2F],
                        (int)bs[i].Num("Format"), (int)bs[i].Num("Curve"), "0x" + gpu.ToString("X8"), (int)bs[i].Num("More Flags"), p, s, kv.Key));
                }
            }
        }
        return 0;
    }
}
