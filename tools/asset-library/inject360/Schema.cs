// Field schema built from an Assembly plugin through Blamite's own plugin loader (IPluginVisitor).
// Each node records what the translator needs: kind, name, offset, size and the byte-swap unit.
using System.Collections.Generic;
using System.IO;
using System.Xml;
using Blamite.Plugins;
using Blamite.Blam.Shaders;

namespace Inject360
{
    public enum Kind { Scalar, Raw, StringId, TagRef, DataRef, Block, Shader, UnicList }

    public class Node
    {
        public Kind Kind; public string Type; public string Name; public uint Offset;
        public int Size;      // bytes occupied in the parent struct
        public int Unit;      // byte-swap unit for Scalar/Raw (1 = no swap)
        public bool WithGroup;
        public uint ElementSize; public int Align; public bool Sort;   // Block
        public List<Node> Kids = new List<Node>();                      // Block element fields
        public Dictionary<int, string> Bits, Options;                     // flags bit names / enum option names
        public string Key => Type + "|" + (Name ?? "").Trim().ToLowerInvariant();
        public override string ToString() => Type + " '" + Name + "' @0x" + Offset.ToString("X");
    }

    public class Schema
    {
        public uint BaseSize; public List<Node> Fields = new List<Node>(); public string File;

        public static Schema Load(string pluginPath, int tagRefSize, int dataRefSize, int blockSize)
        {
            var v = new Builder(tagRefSize, dataRefSize, blockSize);
            using (var r = XmlReader.Create(pluginPath)) AssemblyPluginLoader.LoadPlugin(r, v);
            return new Schema { BaseSize = v.BaseSize, Fields = v.Root, File = pluginPath };
        }

        class Builder : IPluginVisitor
        {
            readonly int _tagRef, _dataRef, _block;
            public uint BaseSize; public List<Node> Root = new List<Node>();
            readonly Stack<List<Node>> _stack = new Stack<List<Node>>();
            List<Node> Cur => _stack.Count > 0 ? _stack.Peek() : Root;
            public Builder(int tagRef, int dataRef, int block) { _tagRef = tagRef; _dataRef = dataRef; _block = block; }

            void Add(string type, string name, uint offset, int size, int unit, Kind kind = Kind.Scalar)
                => Cur.Add(new Node { Kind = kind, Type = type, Name = name, Offset = offset, Size = size, Unit = unit });

            public bool EnterPlugin(int baseSize) { BaseSize = (uint)baseSize; return true; }
            public void LeavePlugin() { }
            public bool EnterRevisions() => false;
            public void VisitRevision(PluginRevision revision) { }
            public void LeaveRevisions() { }
            public void VisitComment(string title, string text, uint pluginLine) { }
            public void VisitUInt8(string n, uint o, bool v, uint l, string t) => Add("u8", n, o, 1, 1);
            public void VisitInt8(string n, uint o, bool v, uint l, string t) => Add("i8", n, o, 1, 1);
            public void VisitUInt16(string n, uint o, bool v, uint l, string t) => Add("u16", n, o, 2, 2);
            public void VisitInt16(string n, uint o, bool v, uint l, string t) => Add("i16", n, o, 2, 2);
            public void VisitUInt32(string n, uint o, bool v, uint l, string t) => Add("u32", n, o, 4, 4);
            public void VisitInt32(string n, uint o, bool v, uint l, string t) => Add("i32", n, o, 4, 4);
            public void VisitUInt64(string n, uint o, bool v, uint l, string t) => Add("u64", n, o, 8, 8);
            public void VisitInt64(string n, uint o, bool v, uint l, string t) => Add("i64", n, o, 8, 8);
            public void VisitFloat32(string n, uint o, bool v, uint l, string t) => Add("f32", n, o, 4, 4);
            public void VisitUndefined(string n, uint o, bool v, uint l, string t) => Add("undef", n, o, 4, 4);
            public void VisitDatum(string n, uint o, bool v, uint l, string t) => Add("datum", n, o, 4, 4);
            public void VisitPoint2(string n, uint o, bool v, uint l, string t) => Add("point2", n, o, 8, 4);
            public void VisitPoint3(string n, uint o, bool v, uint l, string t) => Add("point3", n, o, 12, 4);
            public void VisitVector2(string n, uint o, bool v, uint l, string t) => Add("vector2", n, o, 8, 4);
            public void VisitVector3(string n, uint o, bool v, uint l, string t) => Add("vector3", n, o, 12, 4);
            public void VisitVector4(string n, uint o, bool v, uint l, string t) => Add("vector4", n, o, 16, 4);
            public void VisitDegree(string n, uint o, bool v, uint l, string t) => Add("degree", n, o, 4, 4);
            public void VisitDegree2(string n, uint o, bool v, uint l, string t) => Add("degree2", n, o, 8, 4);
            public void VisitDegree3(string n, uint o, bool v, uint l, string t) => Add("degree3", n, o, 12, 4);
            public void VisitPlane2(string n, uint o, bool v, uint l, string t) => Add("plane2", n, o, 12, 4);
            public void VisitPlane3(string n, uint o, bool v, uint l, string t) => Add("plane3", n, o, 16, 4);
            public void VisitRect16(string n, uint o, bool v, uint l, string t) => Add("rect16", n, o, 8, 2);
            public void VisitQuat16(string n, uint o, bool v, uint l, string t) => Add("quat16", n, o, 8, 2);
            public void VisitPoint16(string n, uint o, bool v, uint l, string t) => Add("point16", n, o, 4, 2);
            public void VisitStringID(string n, uint o, bool v, uint l, string t) => Add("stringid", n, o, 4, 4, Kind.StringId);
            public void VisitOldStringID(string n, uint o, bool v, uint l, string t) => Add("oldstringid", n, o, 32, 1, Kind.Raw);
            public void VisitTagReference(string n, uint o, bool v, bool withGroup, uint l, string t)
                => Cur.Add(new Node { Kind = Kind.TagRef, Type = "tagref", Name = n, Offset = o, Size = withGroup ? _tagRef : 4, Unit = 4, WithGroup = withGroup });
            public void VisitDataReference(string n, uint o, string format, bool v, int align, uint l, string t)
                => Cur.Add(new Node { Kind = Kind.DataRef, Type = "dataref", Name = n, Offset = o, Size = _dataRef, Unit = 4, Align = align });
            public void VisitRangeInt16(string n, uint o, bool v, uint l, string t) => Add("range16", n, o, 4, 2);
            public void VisitRangeFloat32(string n, uint o, bool v, uint l, string t) => Add("rangef", n, o, 8, 4);
            public void VisitRangeDegree(string n, uint o, bool v, uint l, string t) => Add("ranged", n, o, 8, 4);
            public void VisitRawData(string n, uint o, bool v, int size, uint l, string t) => Add("raw", n, o, size, 1, Kind.Raw);
            public void VisitAscii(string n, uint o, bool v, int size, uint l, string t) => Add("ascii", n, o, size, 1, Kind.Raw);
            public void VisitUtf16(string n, uint o, bool v, int size, uint l, string t) => Add("utf16", n, o, size, 2, Kind.Raw);
            public void VisitHexString(string n, uint o, bool v, int size, uint l, string t) => Add("hex", n, o, size, 1, Kind.Raw);
            public void VisitColorInt(string n, uint o, bool v, bool alpha, uint l, string t) => Add("color32", n, o, 4, 4);
            public void VisitColorF(string n, uint o, bool v, bool alpha, bool basic, uint l, string t) => Add("colorf", n, o, alpha ? 16 : 12, 4);
            public bool EnterFlags8(string n, uint o, bool v, uint l, string t) { Add("flags8", n, o, 1, 1); Cur[Cur.Count - 1].Bits = new Dictionary<int, string>(); return true; }
            public bool EnterFlags16(string n, uint o, bool v, uint l, string t) { Add("flags16", n, o, 2, 2); Cur[Cur.Count - 1].Bits = new Dictionary<int, string>(); return true; }
            public bool EnterFlags32(string n, uint o, bool v, uint l, string t) { Add("flags32", n, o, 4, 4); Cur[Cur.Count - 1].Bits = new Dictionary<int, string>(); return true; }
            public bool EnterFlags64(string n, uint o, bool v, uint l, string t) { Add("flags64", n, o, 8, 8); Cur[Cur.Count - 1].Bits = new Dictionary<int, string>(); return true; }
            public void VisitBit(string name, int index, string tooltip) { var b = Cur[Cur.Count - 1].Bits; if (b != null) b[index] = (name ?? "").Trim(); }
            public void LeaveFlags() { }
            public bool EnterEnum8(string n, uint o, bool v, uint l, string t) { Add("enum8", n, o, 1, 1); Cur[Cur.Count - 1].Options = new Dictionary<int, string>(); return true; }
            public bool EnterEnum16(string n, uint o, bool v, uint l, string t) { Add("enum16", n, o, 2, 2); Cur[Cur.Count - 1].Options = new Dictionary<int, string>(); return true; }
            public bool EnterEnum32(string n, uint o, bool v, uint l, string t) { Add("enum32", n, o, 4, 4); Cur[Cur.Count - 1].Options = new Dictionary<int, string>(); return true; }
            public void VisitOption(string name, int value, string tooltip) { var o = Cur[Cur.Count - 1].Options; if (o != null && !o.ContainsKey(value)) o[value] = (name ?? "").Trim(); }
            public void LeaveEnum() { }
            public bool EnterTagBlock(string n, uint o, bool v, uint entrySize, int align, bool sort, uint l, string t)
            {
                var node = new Node { Kind = Kind.Block, Type = "block", Name = n, Offset = o, Size = _block, Unit = 4, ElementSize = entrySize, Align = align, Sort = sort };
                Cur.Add(node); _stack.Push(node.Kids); return true;
            }
            public void LeaveTagBlock() { _stack.Pop(); }
            public void VisitShader(string n, uint o, bool v, ShaderType type, uint l, string t)
                => Cur.Add(new Node { Kind = Kind.Shader, Type = "shader", Name = n, Offset = o, Size = 4, Unit = 4 });
            public void VisitUnicList(string n, uint o, bool v, int languages, uint l, string t)
                => Cur.Add(new Node { Kind = Kind.UnicList, Type = "uniclist", Name = n, Offset = o, Size = 4, Unit = 4 });
        }
    }
}
