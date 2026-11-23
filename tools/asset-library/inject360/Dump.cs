// Schema-driven text dump of one tag (all fields, recursing into blocks), for comparing MCC and 360 copies.
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using Blamite.Blam;
using Blamite.IO;

namespace Inject360
{
    public static class Dumper
    {
        public static void Dump(ICacheFile file, IReader r, ITag tag, Schema schema, TextWriter w, Func<uint, string> tagName, int maxEntries = 64)
        {
            Walk(file, r, tag.MetaLocation.AsOffset(), schema.Fields, w, "", tagName, maxEntries);
        }

        static void Walk(ICacheFile file, IReader r, long at, List<Node> fields, TextWriter w, string path, Func<uint, string> tagName, int maxEntries)
        {
            foreach (var n in fields)
            {
                r.SeekTo(at + n.Offset);
                string p = path + "/" + n.Name, v;
                switch (n.Type)
                {
                    case "u8": v = r.ReadByte().ToString(); break;
                    case "i8": v = r.ReadSByte().ToString(); break;
                    case "u16": case "flags16": case "enum16": v = r.ReadUInt16().ToString(); break;
                    case "i16": v = r.ReadInt16().ToString(); break;
                    case "flags8": case "enum8": v = r.ReadByte().ToString(); break;
                    case "u32": case "flags32": case "enum32": case "undef": case "datum": case "color32": v = "0x" + r.ReadUInt32().ToString("X8"); break;
                    case "i32": v = r.ReadInt32().ToString(); break;
                    case "f32": case "degree": v = r.ReadFloat().ToString("R"); break;
                    case "stringid": var sid = new StringID(r.ReadUInt32()); v = file.StringIDs.GetString(sid) ?? "0x" + sid.Value.ToString("X"); break;
                    case "tagref":
                        uint idx;
                        if (n.WithGroup) { r.Skip(12); idx = r.ReadUInt32(); } else idx = r.ReadUInt32();
                        v = tagName(idx); break;
                    case "block":
                        {
                            int count = r.ReadInt32(); uint ptr = r.ReadUInt32();
                            w.WriteLine(p + " [" + count + "]");
                            if (count <= 0 || ptr == 0) continue;
                            long off = file.MetaArea.PointerToOffset(file.PointerExpander.Expand(ptr));
                            for (int i = 0; i < Math.Min(count, maxEntries); i++)
                                Walk(file, r, off + i * n.ElementSize, n.Kids, w, p + "[" + i + "]", tagName, maxEntries);
                            continue;
                        }
                    case "dataref":
                        {
                            int size = r.ReadInt32(); r.Skip(8); uint ptr = r.ReadUInt32();
                            var sb = new StringBuilder();
                            if (size > 0 && ptr != 0)
                            {
                                r.SeekTo(file.MetaArea.PointerToOffset(file.PointerExpander.Expand(ptr)));
                                foreach (var b in r.ReadBlock(Math.Min(size, 64))) sb.Append(b.ToString("X2"));
                            }
                            v = "(" + size + ") " + sb; break;
                        }
                    default:
                        if (n.Size > 0 && n.Size <= 64) { var sb = new StringBuilder(); var bytes = r.ReadBlock(n.Size); int k = 0; foreach (var b in bytes) { if (n.Unit > 1 && k++ % n.Unit == 0 && k > 1) sb.Append(' '); sb.Append(b.ToString("X2")); } v = sb.ToString(); }
                        else v = "?"; break;
                }
                // multi-float types: print as floats
                if (n.Type.StartsWith("point") || n.Type.StartsWith("vector") || n.Type.StartsWith("plane") || n.Type.StartsWith("degree") && n.Type != "degree" || n.Type == "rangef" || n.Type == "ranged" || n.Type == "colorf")
                {
                    r.SeekTo(at + n.Offset); var parts = new List<string>();
                    for (int i = 0; i < n.Size / 4; i++) parts.Add(r.ReadFloat().ToString("R"));
                    v = string.Join(" ", parts);
                }
                w.WriteLine(p + " = " + v);
            }
        }
    }
}
