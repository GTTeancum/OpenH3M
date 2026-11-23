// render_geometry_api_resource_definition: MCC (PC vertex streams, little-endian) -> original 360 (Xenos streams, big-endian).
// Control layout (both platforms): root of four 12-byte blocks {pc vertex, pc index, xenon vertex, xenon index};
// vertex descriptor 0x1C = count, format u16, stride u16, data reference (size +8, pointer +20);
// index descriptor 0x18 = primitive type, data reference (size +4, pointer +16); table entries are 12-byte
// interop pointers (definition fixup type 0 = vertex buffer, 1 = index buffer). Checked against stock 360 models.
// Vertex stream formats follow the project's format notes (render_buffers.py); new implementation.
using System;
using System.Collections.Generic;
using System.Linq;
using Blamite.Blam;
using Blamite.Blam.Resources;
using Blamite.Injection;

namespace Inject360
{
    public static class GeometryConverter
    {
        static uint Le32(byte[] b, int at) => BitConverter.ToUInt32(b, at);
        static int Le16(byte[] b, int at) => BitConverter.ToUInt16(b, at);
        static short Les16(byte[] b, int at) => BitConverter.ToInt16(b, at);
        static void Be32(byte[] b, int at, uint v) { b[at] = (byte)(v >> 24); b[at + 1] = (byte)(v >> 16); b[at + 2] = (byte)(v >> 8); b[at + 3] = (byte)v; }
        static void Be16(byte[] b, int at, int v) { b[at] = (byte)(v >> 8); b[at + 1] = (byte)v; }

        // Signed 16-bit XYZ (normalized) -> 360 signed 10:11:11, big-endian.
        static uint PackBasis(short x, short y, short z)
        {
            uint p = 0; var c = new[] { x, y, z }; var shift = new[] { 0, 10, 21 }; var bits = new[] { 10, 11, 11 };
            for (int a = 0; a < 3; a++)
            {
                double u = Math.Max(c[a] / 32767.0, -1.0); int lim = (1 << (bits[a] - 1)) - 1;
                int q = (int)Math.Round(Math.Max(-1, Math.Min(1, u)) * lim, MidpointRounding.ToEven);
                p |= ((uint)q & ((1u << bits[a]) - 1)) << shift[a];
            }
            return p;
        }

        static void Swap(byte[] s, int so, byte[] d, int dof, int n, int unit)
        { for (int i = 0; i + unit <= n; i += unit) for (int k = 0; k < unit; k++) d[dof + i + k] = s[so + i + unit - 1 - k]; }

        // Returns converted bytes and the 360 stride, or throws for a format without a converter.
        public static (byte[] data, int stride, int count) Vertices(byte[] src, int count, int fmt, int stride)
        {
            if (src.Length < count * stride) throw new Exception("vertex payload shorter than count x stride");
            if (fmt == 1 || fmt == 2 || fmt == 3)
            {
                int expect = fmt == 2 ? 36 : 44, outStride = fmt == 2 ? 24 : 32, prefix = fmt == 1 ? 20 : 12, unit = fmt == 1 ? 4 : 2;
                if (stride != expect) throw new Exception($"format {fmt} stride {stride}, expected {expect}");
                var o = new byte[count * outStride];
                for (int v = 0; v < count; v++)
                {
                    int s = v * stride, d = v * outStride;
                    Swap(src, s, o, d, prefix, unit);
                    for (int ch = 0; ch < 3; ch++)
                    {
                        int at = s + prefix + ch * 8;
                        Be32(o, d + prefix + ch * 4, PackBasis(Les16(src, at), Les16(src, at + 2), Les16(src, at + 4)));
                    }
                    if (fmt == 3) Buffer.BlockCopy(src, s + 36, o, d + 24, 8);   // bone indices + weights: bytes, not swapped
                }
                return (o, outStride, count);
            }
            if (fmt == 25)   // particle model: position xyz, texcoord uv, normal xyz as floats -> unsigned 16-bit x4 (w = 0), x2, signed 10:11:11
            {                // positions and texcoords match stock 360 data to the last bit; normals within one step (MCC stores them re-normalized)
                if (stride != 32) throw new Exception($"format {fmt} stride {stride}, expected 32");
                var o = new byte[count * 16];
                Func<int, int> u16 = at => Math.Max(0, Math.Min(65535, (int)Math.Floor(BitConverter.ToSingle(src, at) * 65535.0 + 0.001)));
                Func<int, short> s16 = at => (short)Math.Round(Math.Max(-1f, Math.Min(1f, BitConverter.ToSingle(src, at))) * 32767.0);
                for (int v = 0; v < count; v++)
                {
                    int s = v * 32, d = v * 16;
                    for (int k = 0; k < 3; k++) Be16(o, d + k * 2, u16(s + k * 4));
                    Be16(o, d + 8, u16(s + 12)); Be16(o, d + 10, u16(s + 16));
                    Be32(o, d + 12, PackBasis(s16(s + 20), s16(s + 24), s16(s + 28)));
                }
                return (o, 16, count);
            }
            if (fmt == 11)   // quadratic PRT: three short4 (xyz + pad) -> three signed 10:10:10
            {
                if (stride != 24) throw new Exception("PRT stride");
                var o = new byte[count * 12];
                for (int v = 0; v < count; v++)
                    for (int k = 0; k < 3; k++)
                    {
                        uint p = 0;
                        for (int a = 0; a < 3; a++)
                        {
                            int q = (int)Math.Round(Math.Max(-1, Math.Min(1, Les16(src, v * 24 + k * 8 + a * 2) / 32767.0)) * 511, MidpointRounding.ToEven);
                            p |= ((uint)q & 1023) << (a * 10);
                        }
                        Be32(o, v * 12 + k * 4, p);
                    }
                return (o, 12, count);
            }
            if (fmt == 4 || fmt == 14)  // 2-byte / 4-byte units straight endian swap (per project notes)
            {
                int expect = fmt == 4 ? 4 : 12, unit = fmt == 4 ? 2 : 4;
                if (stride != expect) throw new Exception($"format {fmt} stride {stride}");
                var o = new byte[count * stride]; Swap(src, 0, o, 0, count * stride, unit); return (o, stride, count);
            }
            if (fmt == 9)   // ambient PRT: one float per vertex -> one byte per vertex, buffer count = ceil(n / 4)
            {
                var o = new byte[(count + 3) / 4 * 4];
                for (int v = 0; v < count; v++) o[v] = (byte)Math.Round(Math.Max(0, Math.Min(1, BitConverter.ToSingle(src, v * 4))) * 255, MidpointRounding.ToEven);
                return (o, 4, (count + 3) / 4);
            }
            throw new Exception($"vertex format {fmt} has no converter yet");
        }

        public class Result { public ExtractedResourceInfo Resource; public string Note; }

        public static Result Convert(Resource src, Func<ResourcePage, byte[]> pageBytes, ResourceSink sink, DatumIndex parentTag)
        {
            var c = src.Info; if (c == null) return new Result { Note = "no control data" };
            var fix = src.ResourceFixups.ToDictionary(f => f.Offset, f => f.Address);
            int root = src.BaseDefinitionAddress & 0x1FFFFFFF;
            byte[] seg(uint addr)
            {
                var pg = (addr & 0xE0000000) == 0x40000000 ? src.Location?.PrimaryPage : (addr & 0xE0000000) == 0x60000000 ? src.Location?.SecondaryPage : null;
                if (pg == null) throw new Exception("payload page missing");
                return pageBytes(pg);
            }
            int segOff(uint addr) => (int)(addr & 0x1FFFFFFF) + ((addr & 0xE0000000) == 0x40000000 ? Math.Max(0, src.Location.PrimaryOffset) : Math.Max(0, src.Location.SecondaryOffset));
            int ptr(int at) => fix.TryGetValue(at, out var a) ? (int)(a & 0x1FFFFFFF) : throw new Exception($"no control fixup at 0x{at:X}");

            var ctl = new List<byte>(); var raw = new List<byte>();
            var fixups = new List<ResourceFixup>(); var defs = new List<ResourceDefinitionFixup>();
            int Alloc(int n) { int at = ctl.Count; ctl.AddRange(new byte[n]); return at; }
            int Gpu(byte[] d) { while (raw.Count % 16 != 0) raw.Add(0); int at = raw.Count; raw.AddRange(d); return at; }
            int rootOut = Alloc(48);
            var notes = new List<string>();
            foreach (var (blockAt, kind) in new[] { (24, 0), (36, 1) })
            {
                int n = (int)Le32(c, root + blockAt); if (n == 0) continue;
                int tableSrc = ptr(root + blockAt + 4);
                int tableOut = Alloc(12 * n);
                fixups.Add(new ResourceFixup { Offset = rootOut + blockAt + 4, Address = 0x20000000u | (uint)tableOut });
                var descs = new List<(int at, byte[] desc, int ptrOff, byte[] data)>();
                for (int i = 0; i < n; i++)
                {
                    int d = ptr(tableSrc + i * 12);
                    if (kind == 0)
                    {
                        int count = (int)Le32(c, d), fmt = Le16(c, d + 4), stride = Le16(c, d + 6), size = (int)Le32(c, d + 8);
                        uint a = fix[d + 20]; var page = seg(a); int off = segOff(a);
                        var payload = page.Skip(off).Take(size).ToArray();
                        var (data, outStride, outCount) = Vertices(payload, count, fmt, stride);
                        var desc = new byte[0x1C]; Be32(desc, 0, (uint)outCount); Be16(desc, 4, fmt); Be16(desc, 6, outStride); Be32(desc, 8, (uint)data.Length);
                        descs.Add((i, desc, 20, data)); notes.Add($"v{i}:fmt{fmt} {count}x{stride}->{outStride}");
                    }
                    else
                    {
                        int prim = (int)Le32(c, d), size = (int)Le32(c, d + 4);
                        uint a = fix[d + 16]; var page = seg(a); int off = segOff(a);
                        var data = new byte[size]; Swap(page, off, data, 0, size - size % 2, 2);
                        var desc = new byte[0x18]; Be32(desc, 0, (uint)prim); Be32(desc, 4, (uint)size);
                        descs.Add((i, desc, 16, data)); notes.Add($"i{i}:type{prim} {size / 2}");
                    }
                }
                foreach (var (i, desc, ptrOff, data) in descs)
                {
                    int dAt = Alloc(desc.Length); for (int k = 0; k < desc.Length; k++) ctl[dAt + k] = desc[k];
                    int entry = tableOut + i * 12;
                    fixups.Add(new ResourceFixup { Offset = entry, Address = 0x20000000u | (uint)dAt });
                    fixups.Add(new ResourceFixup { Offset = dAt + ptrOff, Address = 0x40000000u | (uint)Gpu(data) });
                    defs.Add(new ResourceDefinitionFixup { Offset = (int)(0x20000000u | (uint)entry), Type = kind });
                }
                var b = ctl.ToArray(); Be32(b, rootOut + blockAt, (uint)n); ctl = b.ToList();
            }
            var info = ctl.ToArray();
            var r = new ExtractedResourceInfo(src.Index)
            {
                Flags = src.Flags, Type = src.Type, Info = info, ResourceBits = src.ResourceBits,
                BaseDefinitionAddress = (int)(0x20000000u | (uint)rootOut), OriginalParentTagIndex = parentTag,
                Location = new ExtractedResourcePointer(),
            };
            r.ResourceFixups.AddRange(fixups); r.DefinitionFixups.AddRange(defs);
            if (raw.Count > 0) { r.Location.OriginalPrimaryPageIndex = sink.Page(raw.ToArray()); r.Location.PrimaryOffset = 0; }
            sink.Add(r);
            return new Result { Resource = r, Note = string.Join(" ", notes) + $" ({raw.Count} bytes)" };
        }
    }
}
