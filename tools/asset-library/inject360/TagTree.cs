// Read a tag from a cache file into a simple field tree (schema-driven), for rules that need values by name.
using System;
using System.Collections.Generic;
using System.Linq;
using Blamite.Blam;
using Blamite.IO;

namespace Inject360
{
    public class Elem
    {
        public Dictionary<string, object> F = new Dictionary<string, object>(StringComparer.OrdinalIgnoreCase);
        public object this[string name] => F.TryGetValue(name, out var v) ? v : null;
        public List<Elem> Block(string name) => this[name] as List<Elem> ?? new List<Elem>();
        public string Str(string name) => this[name] as string;
        public uint Datum(string name) => this[name] is uint u ? u : 0xFFFFFFFF;
        public double Num(string name) => this[name] is IConvertible c ? Convert.ToDouble(c) : 0;
        public float[] Floats(string name) => this[name] as float[];
    }

    public static class TagTree
    {
        public static Elem Read(ICacheFile file, IReader r, ITag tag, Schema s)
            => Walk(file, r, tag.MetaLocation.AsOffset(), s.Fields);

        static Elem Walk(ICacheFile file, IReader r, long at, List<Node> fields)
        {
            var e = new Elem();
            foreach (var n in fields)
            {
                r.SeekTo(at + n.Offset);
                string key = (n.Name ?? "").Trim();
                if (e.F.ContainsKey(key)) key += "#" + n.Offset.ToString("X");
                object v = null;
                switch (n.Type)
                {
                    case "u8": case "flags8": case "enum8": v = (int)r.ReadByte(); break;
                    case "i8": v = (int)r.ReadSByte(); break;
                    case "u16": case "flags16": case "enum16": v = (int)r.ReadUInt16(); break;
                    case "i16": v = (int)r.ReadInt16(); break;
                    case "u32": case "flags32": case "enum32": case "undef": case "datum": case "color32": v = r.ReadUInt32(); break;
                    case "i32": v = r.ReadInt32(); break;
                    case "f32": case "degree": v = r.ReadFloat(); break;
                    case "stringid": v = file.StringIDs.GetString(new StringID(r.ReadUInt32())) ?? ""; break;
                    case "tagref": if (n.WithGroup) r.Skip(12); v = r.ReadUInt32(); break;
                    case "block":
                        {
                            int count = r.ReadInt32(); uint ptr = r.ReadUInt32();
                            var list = new List<Elem>();
                            if (count > 0 && ptr != 0)
                            {
                                long off = file.MetaArea.PointerToOffset(file.PointerExpander.Expand(ptr));
                                for (int i = 0; i < count; i++) list.Add(Walk(file, r, off + i * n.ElementSize, n.Kids));
                            }
                            v = list; break;
                        }
                    default:
                        if (n.Unit == 4 && n.Size % 4 == 0 && n.Kind == Kind.Scalar)
                        { var f = new float[n.Size / 4]; for (int i = 0; i < f.Length; i++) f[i] = r.ReadFloat(); v = f; }
                        break;
                }
                e.F[key] = v;
            }
            return e;
        }
    }
}
