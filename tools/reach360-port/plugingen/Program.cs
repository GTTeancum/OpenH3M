// Generates Assembly plugin XML layouts from TagTool's tag definitions for a given game build and platform.
// TagTool is used read-only as the layout reference (field names, offsets, sizes, enums, flags, block element sizes).
// Usage: plugingen <out dir> <game: Reach|Halo3> <group tag or TagTool type name>...
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Xml;
using TagTool.Cache;
using TagTool.Tags;

class P
{
    static CacheVersion V; static CachePlatform Pf; static Assembly Tt;
    static readonly HashSet<string> Unknown = new HashSet<string>();

    static int Main(string[] a)
    {
        Tt = typeof(CacheVersion).Assembly;
        if (a[0] == "enum")
        {   // plugingen enum <type name substring>: print matching enums (name = value)
            Type[] ts; try { ts = Tt.GetTypes(); } catch (ReflectionTypeLoadException e) { ts = e.Types.Where(x => x != null).ToArray(); }
            foreach (var et in ts.Where(x => x.IsEnum && x.Name.IndexOf(a[1], StringComparison.OrdinalIgnoreCase) >= 0))
            {
                Console.WriteLine("== " + et.FullName);
                foreach (var v in Enum.GetValues(et)) Console.WriteLine("  " + Convert.ToInt64(Convert.ChangeType(v, Enum.GetUnderlyingType(et))) + " " + v);
            }
            return 0;
        }
        var outDir = a[0]; var game = a[1];
        (V, Pf) = game == "Reach" ? (CacheVersion.HaloReach, CachePlatform.Original) : (CacheVersion.Halo3Retail, CachePlatform.Original);
        Directory.CreateDirectory(outDir);
        Type[] all; try { all = Tt.GetTypes(); } catch (ReflectionTypeLoadException e) { all = e.Types.Where(x => x != null).ToArray(); }
        var defs = all.Where(t => typeof(TagStructure).IsAssignableFrom(t) && t.GetCustomAttributes(typeof(TagStructureAttribute), false).Any()).ToList();
        var wants = a.Skip(2).ToList();
        if (wants.Count == 1 && wants[0] == "all")
        {   // every tag group TagTool defines for this build
            wants = defs.Select(t => { try { var i = TagStructure.GetTagStructureInfo(t, V, Pf); return i.GroupTag.Value == -1 ? null : i.GroupTag.ToString(); } catch { return null; } })
                        .Where(g => g != null && g.Trim().Length > 0).Distinct().ToList();
        }
        foreach (var want in wants)
        {
            Type type = defs.FirstOrDefault(t => t.Name == want);
            if (type == null)
                type = defs.FirstOrDefault(t => { try { var info = TagStructure.GetTagStructureInfo(t, V, Pf); return info.GroupTag.ToString().Trim() == want.Trim(); } catch { return false; } });
            if (type == null) { Console.WriteLine("not found: " + want); continue; }
            try {
            var sinfo = TagStructure.GetTagStructureInfo(type, V, Pf);
            var group = sinfo.GroupTag.ToString().Trim();
            var size = TagStructure.GetStructureSize(type, V, Pf);
            var fileStem = (sinfo.GroupTag.Value == -1 || group.Contains("?")) ? type.Name : group;
            var path = Path.Combine(outDir, string.Concat(fileStem.Select(ch => Path.GetInvalidFileNameChars().Contains(ch) ? '_' : ch)) + ".xml");
            var xs = new XmlWriterSettings { Indent = true, IndentChars = "\t", Encoding = new UTF8Encoding(false) };
            using (var w = XmlWriter.Create(path, xs))
            {
                w.WriteStartDocument();
                w.WriteStartElement("plugin"); w.WriteAttributeString("game", game); w.WriteAttributeString("baseSize", "0x" + size.ToString("X"));
                w.WriteComment(" Generated from TagTool " + type.FullName + " (" + V + ", " + Pf + ") by tools/reach360-port/plugingen ");
                Emit(w, type, 0, "");
                w.WriteEndElement(); w.WriteEndDocument();
            }
            Console.WriteLine($"{group}  {type.Name}  0x{size:X}  -> {path}");
            } catch (Exception ex) { Console.WriteLine("FAILED " + want + ": " + ex.GetType().Name + " " + ex.Message); }
        }
        if (Unknown.Count > 0) Console.WriteLine("types written as undefined bytes: " + string.Join(", ", Unknown.OrderBy(x => x)));
        return 0;
    }

    static string Hex(uint v) => "0x" + v.ToString("X");

    static void Leaf(XmlWriter w, string kind, string name, uint off)
    {
        w.WriteStartElement(kind); w.WriteAttributeString("name", name); w.WriteAttributeString("offset", Hex(off)); w.WriteAttributeString("visible", "true"); w.WriteEndElement();
    }

    static void Emit(XmlWriter w, Type type, uint baseOff, string prefix)
    {
        foreach (var f in TagStructure.GetTagFieldEnumerable(type, V, Pf))
        {
            if (f.Attribute != null && (f.Attribute.Flags & TagFieldFlags.Runtime) != 0 && f.Size == 0) continue;
            var name = prefix + Pretty(f.Name);
            Field(w, f.FieldType, f.Attribute, name, baseOff + f.Offset, f.Size);
        }
    }

    static string Pretty(string n)
    {
        var sb = new StringBuilder();
        for (int i = 0; i < n.Length; i++)
        {
            char c = n[i];
            if (i > 0 && char.IsUpper(c) && (char.IsLower(n[i - 1]) || (i + 1 < n.Length && char.IsLower(n[i + 1])))) sb.Append(' ');
            sb.Append(c);
        }
        return sb.ToString();
    }

    static void Field(XmlWriter w, Type t, TagFieldAttribute attr, string name, uint off, uint size)
    {
        if (Nullable.GetUnderlyingType(t) is Type u) t = u;
        if (t.IsEnum) { EnumField(w, t, name, off, size); return; }
        if (t == typeof(sbyte)) { Leaf(w, "int8", name, off); return; }
        if (t == typeof(byte)) { Leaf(w, "uint8", name, off); return; }
        if (t == typeof(short)) { Leaf(w, "int16", name, off); return; }
        if (t == typeof(ushort)) { Leaf(w, "uint16", name, off); return; }
        if (t == typeof(int)) { Leaf(w, "int32", name, off); return; }
        if (t == typeof(uint)) { Leaf(w, "uint32", name, off); return; }
        if (t == typeof(float)) { Leaf(w, "float32", name, off); return; }
        if (t == typeof(byte[]) && attr != null && attr.Length > 0)
        {   // fixed-length inline bytes (padding/raw), not a data reference
            for (uint i = 0; i < size; i++) { w.WriteStartElement("uint8"); w.WriteAttributeString("name", name + " " + i); w.WriteAttributeString("offset", Hex(off + i)); w.WriteAttributeString("visible", "false"); w.WriteEndElement(); }
            return;
        }
        if (t == typeof(byte[])) { DataRef(w, name, off, attr); return; }
        if (t.IsArray && attr != null && attr.Length > 0)
        {
            var et = t.GetElementType(); uint es = attr.Length > 0 ? size / (uint)attr.Length : 0;
            for (int i = 0; i < attr.Length; i++) Field(w, et, null, name + " " + i, off + (uint)i * es, es);
            return;
        }
        if (t == typeof(long) || t == typeof(ulong)) { Leaf(w, "uint32", name + " (high)", off); Leaf(w, "uint32", name + " (low)", off + 4); return; }
        if (t == typeof(string)) { w.WriteStartElement("ascii"); w.WriteAttributeString("name", name); w.WriteAttributeString("offset", Hex(off)); w.WriteAttributeString("visible", "true"); w.WriteAttributeString("size", Hex(size)); w.WriteEndElement(); return; }
        if (t.Name == "RealMatrix4x3") { for (int i = 0; i < 4; i++) Leaf(w, "vector3", name + " row " + i, off + (uint)i * 12); return; }
        if (t.Name == "RealRectangle3d") { Leaf(w, "rangef", name + " x", off); Leaf(w, "rangef", name + " y", off + 8); Leaf(w, "rangef", name + " z", off + 16); return; }
        if (t.Name == "IndexBufferIndex" || t.Name == "StructureSurfaceToTriangleMapping") { Leaf(w, size == 2 ? "uint16" : "uint32", name, off); return; }
        if (t.IsGenericType && (t.GetGenericTypeDefinition() == typeof(List<>) || t.GetGenericTypeDefinition().Name == "TagBlock`1"))
        {
            var et = t.GetGenericArguments()[0];
            uint es = typeof(TagStructure).IsAssignableFrom(et) ? TagStructure.GetStructureSize(et, V, Pf) : TagFieldInfo.GetFieldSize(et, new TagFieldAttribute(), V, Pf);
            w.WriteStartElement("tagblock"); w.WriteAttributeString("name", name); w.WriteAttributeString("offset", Hex(off)); w.WriteAttributeString("visible", "true"); w.WriteAttributeString("elementSize", Hex(es));
            if (typeof(TagStructure).IsAssignableFrom(et) && et.Name != "TagResourceReference") Emit(w, et, 0, ""); else Field(w, et, null, "Value", 0, es);
            w.WriteEndElement(); return;
        }
        switch (t.Name)
        {
            case "StringId": Leaf(w, "stringid", name, off); return;
            case "CachedTag": w.WriteStartElement("tagref"); w.WriteAttributeString("name", name); w.WriteAttributeString("offset", Hex(off)); w.WriteAttributeString("visible", "true"); w.WriteEndElement(); return;
            case "DatumHandle": Leaf(w, "datum", name, off); return;
            case "Angle": Leaf(w, "degree", name, off); return;
            case "RealPoint2d": Leaf(w, "point2", name, off); return;
            case "RealPoint3d": Leaf(w, "point3", name, off); return;
            case "RealVector2d": Leaf(w, "vector2", name, off); return;
            case "RealVector3d": Leaf(w, "vector3", name, off); return;
            case "RealVector4d": case "RealQuaternion": Leaf(w, "vector4", name, off); return;
            case "RealPlane2d": Leaf(w, "plane2", name, off); return;
            case "RealPlane3d": Leaf(w, "plane3", name, off); return;
            case "RealEulerAngles2d": Leaf(w, "degree2", name, off); return;
            case "RealEulerAngles3d": Leaf(w, "degree3", name, off); return;
            case "RealRgbColor": ColorF(w, name, off, "rgb"); return;
            case "RealArgbColor": ColorF(w, name, off, "argb"); return;
            case "ArgbColor": w.WriteStartElement("color32"); w.WriteAttributeString("name", name); w.WriteAttributeString("offset", Hex(off)); w.WriteAttributeString("alpha", "true"); w.WriteAttributeString("visible", "true"); w.WriteEndElement(); return;
            case "Tag": Leaf(w, "uint32", name + " (group tag)", off); return;
            case "PlatformUnsignedValue": Leaf(w, Pf == CachePlatform.MCC ? "undefined" : "uint32", name, off); return;
            case "PlatformSignedValue": Leaf(w, "int32", name, off); return;
            case "TagResourceReference": Leaf(w, "uint32", name + " (resource datum)", off); if (size > 4) Leaf(w, "uint32", name + " (resource pad)", off + 4); return;
            case "TagData": DataRef(w, name, off, attr); return;
            case "Point2d": Leaf(w, "point16", name, off); return;
            case "Rectangle2d": Leaf(w, "rect16", name, off); return;
        }
        if (t.IsGenericType && t.Name.StartsWith("Bounds"))
        {
            var bt = t.GetGenericArguments()[0];
            if (bt == typeof(float)) { Leaf(w, "rangef", name, off); return; }
            if (bt == typeof(short)) { Leaf(w, "range16", name, off); return; }
            if (bt.Name == "Angle") { Leaf(w, "ranged", name, off); return; }
            Field(w, bt, null, name + " min", off, size / 2); Field(w, bt, null, name + " max", off + size / 2, size / 2); return;
        }
        if (typeof(TagStructure).IsAssignableFrom(t)) { Emit(w, t, off, name + " / "); return; }
        Unknown.Add(t.Name);
        for (uint i = 0; i < size; i += 4)
        {
            w.WriteStartElement("undefined"); w.WriteAttributeString("name", name + (size > 4 ? " +" + i : "") + " (" + t.Name + ")"); w.WriteAttributeString("offset", Hex(off + i)); w.WriteAttributeString("visible", "false"); w.WriteEndElement();
        }
    }

    static void ColorF(XmlWriter w, string name, uint off, string fmt)
    {
        w.WriteStartElement("colorf"); w.WriteAttributeString("name", name); w.WriteAttributeString("offset", Hex(off)); w.WriteAttributeString("alpha", fmt == "argb" ? "true" : "false"); w.WriteAttributeString("visible", "true"); w.WriteEndElement();
    }

    static void DataRef(XmlWriter w, string name, uint off, TagFieldAttribute attr)
    {
        w.WriteStartElement("dataref"); w.WriteAttributeString("name", name); w.WriteAttributeString("offset", Hex(off)); w.WriteAttributeString("visible", "true"); w.WriteEndElement();
    }

    static void EnumField(XmlWriter w, Type t, string name, uint off, uint size)
    {
        bool flags = t.GetCustomAttributes(typeof(FlagsAttribute), false).Any();
        var bits = size == 1 ? "8" : size == 2 ? "16" : "32";
        w.WriteStartElement((flags ? "flags" : "enum") + bits); w.WriteAttributeString("name", name); w.WriteAttributeString("offset", Hex(off)); w.WriteAttributeString("visible", "true");
        foreach (var v in Enum.GetValues(t))
        {
            ulong n = unchecked((ulong)Convert.ToInt64(Convert.ChangeType(v, Enum.GetUnderlyingType(t))));
            if (flags)
            {
                if (n == 0 || (n & (n - 1)) != 0) continue;
                int idx = 0; while ((1UL << idx) != n) idx++;
                w.WriteStartElement("bit"); w.WriteAttributeString("name", v.ToString()); w.WriteAttributeString("index", idx.ToString()); w.WriteEndElement();
            }
            else
            {
                long sv = Convert.ToInt64(Convert.ChangeType(v, Enum.GetUnderlyingType(t)));
                w.WriteStartElement("option"); w.WriteAttributeString("name", v.ToString()); w.WriteAttributeString("value", sv.ToString()); w.WriteEndElement();
            }
        }
        w.WriteEndElement();
    }
}
