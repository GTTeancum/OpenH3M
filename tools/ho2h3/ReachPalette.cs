// reachpal <Reach MCC .map> <out.json>: the scenario's Forge palette ("map variant palettes": entry name, display name,
// object, maximum allowed, price per instance), read with Blamite and Assembly's ReachMCC scnr layout (offsets below).
// Read only. Written for Void's prices (user 2026-11-23: carry Forge World's prices over).
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Blamite.Blam;
using Blamite.IO;
using Blamite.Serialization.Settings;
using Blamite.Util;

namespace Ho2H3
{
    static class ReachPalette
    {
        public static int Run(string[] a)
        {
            var db = XMLEngineDatabaseLoader.LoadDatabase(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Formats", "Engines.xml"));
            using (var fs = File.OpenRead(a[1]))
            {
                var probe = new EndianReader(fs, Endian.LittleEndian);
                var file = CacheFileLoader.LoadCacheFile(probe, a[1], db, out var engine);
                var r = new EndianReader(fs, engine.Endian);
                var scnr = file.Tags.First(t => t?.Group != null && CharConstant.ToString(t.Group.Magic) == "scnr");
                long At(uint ptr) => file.MetaArea.PointerToOffset(file.PointerExpander.Expand(ptr));
                string S(int id) => file.StringIDs.GetString(new StringID((uint)id)) ?? "";
                string TagName(uint datum) { var t = file.Tags.FirstOrDefault(x => x != null && x.Index.Value == datum); return t?.Group == null ? "" : CharConstant.ToString(t.Group.Magic) + ":" + file.FileNames.GetTagName(t); }
                long b = scnr.MetaLocation.AsOffset();
                r.SeekTo(b + 0x228); int pc = r.ReadInt32(); uint pp = r.ReadUInt32();
                var rows = new List<Dictionary<string, object>>();
                for (int i = 0; i < pc; i++)
                {
                    long pa = At(pp) + i * 0x14; r.SeekTo(pa); string pal = S(r.ReadInt32());
                    r.SeekTo(pa + 8); int ec = r.ReadInt32(); uint ep = r.ReadUInt32();
                    for (int j = 0; j < ec; j++)
                    {
                        long ea = At(ep) + j * 0x1C; r.SeekTo(ea); string name = S(r.ReadInt32());
                        int vc = r.ReadInt32(); uint vp = r.ReadUInt32();
                        r.SeekTo(ea + 0x10); int max = r.ReadInt32(); int price = r.ReadInt32();
                        for (int k = 0; k < Math.Max(1, vc); k++)
                        {
                            string disp = "", obj = "";
                            if (vc > 0) { long va = At(vp) + k * 0x18; r.SeekTo(va); disp = S(r.ReadInt32()); r.SeekTo(va + 4 + 12); obj = TagName(r.ReadUInt32()); }
                            rows.Add(new Dictionary<string, object> { ["palette"] = pal, ["entry"] = name, ["display"] = disp, ["object"] = obj, ["max"] = max, ["price"] = price });
                        }
                    }
                }
                File.WriteAllText(a[2], System.Text.Json.JsonSerializer.Serialize(rows, new System.Text.Json.JsonSerializerOptions { WriteIndented = true }));
                Console.WriteLine($"{pc} palettes, {rows.Count} entries; engine {engine.Name}");
            }
            return 0;
        }
    }
}
