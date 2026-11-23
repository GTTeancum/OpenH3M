// Resource output (new 360 resources and pages in the tag container) and the bitmap resource converter.
using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using Blamite.Blam;
using Blamite.Blam.Resources;
using Blamite.Injection;

namespace Inject360
{
    public static class Crc32
    {
        static readonly uint[] T = Enumerable.Range(0, 256).Select(i => { uint c = (uint)i; for (int k = 0; k < 8; k++) c = (c & 1) != 0 ? 0xEDB88320 ^ (c >> 1) : c >> 1; return c; }).ToArray();
        public static uint Of(byte[] d) { uint c = 0xFFFFFFFF; foreach (var b in d) c = T[(c ^ b) & 0xFF] ^ (c >> 8); return c ^ 0xFFFFFFFF; }
    }

    public class ResourceSink
    {
        readonly TagContainer _c; readonly byte[] _salt; int _nextPage = 0x10000;
        public ResourceSink(TagContainer c, byte[] salt) { _c = c; _salt = salt; }

        // One deflate-compressed page holding `raw`. The 360 page checksum is the complemented CRC-32 of the
        // uncompressed bytes; the three salted SHA-1s cover the whole page, its first and its last KiB (both verified on stock pages).
        public int Page(byte[] raw, bool compress = true, bool required = false)   // required: always-loaded page (0x11), as stock Halo 3 keeps geometry and collision
        {
            var (h1, h2, h3) = Integrity.PageHashes(_salt, raw);
            byte[] comp = raw;
            if (compress) using (var ms = new MemoryStream())
            {
                using (var ds = new DeflateStream(ms, CompressionLevel.Optimal, true)) ds.Write(raw, 0, raw.Length);
                comp = ms.ToArray();
            }
            var page = new ResourcePage
            {
                Index = _nextPage++, Salt = 0, Flags = (byte)(required ? 0x11 : 0x1), FilePath = null, Offset = -1,
                UncompressedSize = raw.Length, CompressedSize = comp.Length, CompressionMethod = compress ? ResourcePageCompression.Deflate : ResourcePageCompression.None,
                Checksum = ~Crc32.Of(raw), Hash1 = h1, Hash2 = h2, Hash3 = h3,
                AssetCount = 1, Unknown1 = required ? 0 : -1, Unknown2 = -1,
            };
            _c.AddResourcePage(page);
            _c.AddExtractedResourcePage(new ExtractedPage(comp, page.Index));
            return page.Index;
        }

        public void Add(ExtractedResourceInfo r) => _c.AddResource(r);
    }

    public static class BitmapConverter
    {
        static uint Le32(byte[] b, int at) => BitConverter.ToUInt32(b, at);
        static int Le16(byte[] b, int at) => BitConverter.ToUInt16(b, at);
        static void Be32(byte[] b, int at, uint v) { b[at] = (byte)(v >> 24); b[at + 1] = (byte)(v >> 16); b[at + 2] = (byte)(v >> 8); b[at + 3] = (byte)v; }
        static void Be16(byte[] b, int at, int v) { b[at] = (byte)(v >> 8); b[at + 1] = (byte)v; }

        // H3 bitmap format -> block extent, bytes per block, GPU byte-swap unit, 360 fetch format (linear) and gamma variant.
        // Fetch words verified on stock 360 bitmaps for DXT5 (gamma) and DXN; others per the project's format notes.
        static readonly Dictionary<int, (int ext, int bpb, int swap, uint gpu, int gammaLow)> Formats = new Dictionary<int, (int, int, int, uint, int)>
        {
            [0] = (1, 1, 1, 0x04900102, 2),     // A8      (fetch words for 0-3 read from stock 360 textures)
            [1] = (1, 1, 1, 0x28000102, 2),     // Y8
            [2] = (1, 1, 1, 0x1a200102, 2),     // AY8
            [3] = (1, 2, 2, 0x0800014a, 10),    // A8Y8
            [9] = (1, 2, 2, 0x1828014f, 15),    // A4R4G4B4 (stock word seen only in its gamma form)
            [11] = (1, 4, 4, 0x18280186, 50),   // A8R8G8B8
            [25] = (1, 8, 2, 0x1a22ab5d, -1),   // ABGRFP16
            [14] = (4, 8, 2, 0x1a200152, 51),   // DXT1
            [15] = (4, 16, 2, 0x1a200153, 52),  // DXT3
            [16] = (4, 16, 2, 0x1a200154, 53),  // DXT5
            [22] = (1, 2, 2, 0x2d20ab4a, -1),   // V8U8
            [26] = (1, 4, 4, 0x1a20ab86, -1),   // Q8W8V8U8
            [33] = (4, 16, 2, 0x1a215571, -1),  // DXN
        };

        public static bool Supported(int format) => Formats.ContainsKey(format);
        // 360 texture fetch word for a format and gamma curve (as Convert writes it; used by ho2h3)
        public static uint FetchWord(int format, int curve)
        {
            var f = Formats[format]; uint gpu = f.gpu;
            if ((curve == 0 || curve == 1 || curve == 5) && f.gammaLow >= 0) gpu = (gpu & ~0x3Fu) | (uint)f.gammaLow | 0x7E00;
            return gpu;
        }
        public static (int ext, int bpb, int swap) Shape(int format) { var f = Formats[format]; return (f.ext, f.bpb, f.swap); }

        public static bool CubeFaceMajor = false, CubeSwapFaces = true;   // switches exist so texverify can test the alternatives

        // Formats the 2007 engine never shipped are re-expressed in one it has: 16-bit-per-channel colour as
        // 8-bit ARGB, 16-bit two-channel normals as DXN (the compressed normal format stock 360 bump maps use).
        // 2D only. Returns the format the data is in afterwards.
        public static int Recode(ref byte[] prim, ref byte[] sec, bool split, int w, int h, int levels, int format, int type)
        {
            if (format != 28 && format != 29) return format;
            if (type != 0) throw new Exception("format " + format + " is only re-encoded for 2D textures");
            Func<byte[], int, int, int, byte[]> chain = (d, w0, h0, n) =>
            {
                if (d == null) return null;
                var o = new List<byte>(); int at = 0;
                for (int l = 0; l < n; l++)
                {
                    int lw = Math.Max(1, w0 >> l), lh = Math.Max(1, h0 >> l), px = format == 28 ? 8 : 4;
                    if (at + lw * lh * px > d.Length) throw new Exception("16-bit level data truncated");
                    int at0 = at;
                    if (format == 28)
                        for (int k = 0; k < lw * lh; k++) { int a = at0 + k * 8; o.Add(d[a + 5]); o.Add(d[a + 3]); o.Add(d[a + 1]); o.Add(d[a + 7]); }   // R,G,B,A words -> B,G,R,A bytes
                    else
                    {
                        Func<int, int, int, int> val = (x, y, c) =>
                        {
                            x = Math.Min(x, lw - 1); y = Math.Min(y, lh - 1);
                            int v = (short)(d[at0 + (y * lw + x) * 4 + c * 2] | d[at0 + (y * lw + x) * 4 + c * 2 + 1] << 8);
                            return Math.Max(0, Math.Min(255, (int)Math.Round(v / 32767.0 * 127.0) + 128));
                        };
                        for (int by = 0; by < (lh + 3) / 4; by++) for (int bx = 0; bx < (lw + 3) / 4; bx++)
                            for (int c = 0; c < 2; c++)
                            {
                                var v = new int[16]; for (int q = 0; q < 16; q++) v[q] = val(bx * 4 + (q & 3), by * 4 + (q >> 2), c);
                                o.AddRange(DxnChannel(v));
                            }
                    }
                    at += lw * lh * px;
                }
                if (at != d.Length) throw new Exception("16-bit level data is " + d.Length + " bytes, expected " + at);
                var r = o.ToArray(); if (format == 29) Dxn(r);   // Tile360 flips the endpoints back to the 360's unsigned form
                return r;
            };
            if (split) { sec = chain(sec, w, h, 1); prim = levels > 1 ? chain(prim, Math.Max(1, w >> 1), Math.Max(1, h >> 1), levels - 1) : null; }
            else prim = chain(prim, w, h, levels);
            return format == 28 ? 11 : 33;
        }

        // One DXN channel block (unsigned): two endpoints, sixteen 3-bit selectors into the 8-step ramp between them.
        static byte[] DxnChannel(int[] v)
        {
            int e0 = v.Max(), e1 = v.Min(); var b = new byte[8]; b[0] = (byte)e0; b[1] = (byte)e1;
            if (e0 == e1) return b;
            var pal = new int[8]; pal[0] = e0; pal[1] = e1; for (int q = 1; q < 7; q++) pal[q + 1] = ((7 - q) * e0 + q * e1) / 7;
            ulong bits = 0;
            for (int q = 0; q < 16; q++)
            {
                int best = 0; for (int k = 1; k < 8; k++) if (Math.Abs(pal[k] - v[q]) < Math.Abs(pal[best] - v[q])) best = k;
                bits |= (ulong)best << (3 * q);
            }
            for (int q = 0; q < 6; q++) b[2 + q] = (byte)(bits >> (8 * q));
            return b;
        }

        // Linear little-endian MCC levels -> 360 data (primary = lower levels, secondary = top level when split).
        public static (byte[] p360, byte[] s360) Tile360(byte[] prim, byte[] sec, bool split, int w, int h, int levels, int format, bool tiled = true, int type = 0)
        {
            var f = Formats[format];
            if (format == 33) { prim = (byte[])prim?.Clone(); sec = (byte[])sec?.Clone(); Dxn(prim); Dxn(sec); }
            byte[] p360 = null, s360 = null;
            if (type == 2)
            {
                if (w != h) throw new Exception("cube map faces must be square");
                // Cut the MCC data into (face, level) pieces, then lay them out the way stock 360 cube maps are:
                // top level of all six faces in the secondary page, the lower levels in the primary page.
                // MCC stores faces 1 and 2 the other way round (seen byte-exact on a stock single-level cube map).
                Func<int, int> size = l => { int nb = (Math.Max(1, w >> l) + f.ext - 1) / f.ext; return nb * nb * f.bpb; };
                var piece = new byte[6][][]; for (int fc = 0; fc < 6; fc++) piece[fc] = new byte[levels][];
                int at = 0; byte[] src = split ? sec : prim;
                Action<int, int> take = (fc, l) => { int n = size(l); if (at + n > src.Length) throw new Exception("cube map data truncated"); piece[fc][l] = new byte[n]; Buffer.BlockCopy(src, at, piece[fc][l], 0, n); at += n; };
                if (split) { for (int fc = 0; fc < 6; fc++) take(fc, 0); src = prim; at = 0; }
                int first = split ? 1 : 0;
                if (first < levels)
                {
                    if (CubeFaceMajor) for (int fc = 0; fc < 6; fc++) for (int l = first; l < levels; l++) take(fc, l);
                    else for (int l = first; l < levels; l++) for (int fc = 0; fc < 6; fc++) take(fc, l);
                }
                if (src != null && at != src.Length) throw new Exception("cube map data is " + src.Length + " bytes, expected " + at);
                int[] order = CubeSwapFaces ? new[] { 0, 2, 1, 3, 4, 5 } : new[] { 0, 1, 2, 3, 4, 5 };
                Func<int, int, int, byte[]> lay = (from, n, w0) =>
                {
                    var lin = new List<byte>(); foreach (int fc in order) for (int l = from; l < from + n; l++) lin.AddRange(piece[fc][l]);
                    var offs = Xenos.CubeOffsets(w0, n, f.ext, f.bpb, true, out uint total); return Xenos.Place(lin.ToArray(), offs, total, f.bpb, f.swap);
                };
                if (levels > 1) { s360 = lay(0, 1, w); p360 = lay(1, levels - 1, Math.Max(1, w >> 1)); }
                else p360 = lay(0, 1, w);
                return (p360, s360);
            }
            if (type != 0) throw new Exception("texture type " + type + " has no converter yet");
            if (split)
            {
                s360 = Xenos.Tile(sec, 0, w, h, 1, f.ext, f.bpb, f.swap);
                if (levels > 1) p360 = Xenos.Tile(prim, 0, Math.Max(1, w >> 1), Math.Max(1, h >> 1), levels - 1, f.ext, f.bpb, f.swap);
            }
            else p360 = Xenos.Tile(prim, 0, w, h, levels, f.ext, f.bpb, f.swap, tiled);
            return (p360, s360);
        }

        public class Result { public ExtractedResourceInfo Resource; public bool Secondary; public string Note; public int Format = -1; }

        // src: the MCC resource; pageBytes: decompressed page data; format/curve from the MCC bitmap entry.
        public static Result Convert(Resource src, Func<ResourcePage, byte[]> pageBytes, int format, int curve, ResourceSink sink, DatumIndex parentTag)
        {
            var info = src.Info;
            if (src.Type != "bitmap_texture_interop_resource" || info == null || info.Length < 0x30) return new Result { Note = "not a texture resource" };
            int w = Le16(info, 0x28), h = Le16(info, 0x2A), depth = info[0x2C], levels = info[0x2D], type = info[0x2E], hasSecondary = info[0x2F];
            if ((type != 0 && type != 2) || depth != 1) return new Result { Note = $"type {type} depth {depth}: only 2D textures and cube maps are converted so far" };
            int outFormat = format == 28 ? 11 : format == 29 ? 33 : format;
            if (!Formats.TryGetValue(outFormat, out var f)) return new Result { Note = $"format {format} not supported yet" };
            Func<ResourcePage, int, int, byte[]> slice = (pg, off, size) =>
            {
                var all = pageBytes(pg); if (all == null) throw new Exception("page unavailable");
                off = Math.Max(0, off);
                if (off + size > all.Length) throw new Exception("resource outside its page");
                return all.Skip(off).Take(size).ToArray();
            };
            int pSize = (int)Le32(info, 0x00), sSize = (int)Le32(info, 0x14);
            byte[] prim = pSize > 0 && src.Location?.PrimaryPage != null ? slice(src.Location.PrimaryPage, src.Location.PrimaryOffset, pSize) : null;
            byte[] sec = sSize > 0 && src.Location?.SecondaryPage != null ? slice(src.Location.SecondaryPage, src.Location.SecondaryOffset, sSize) : null;
            bool split = hasSecondary != 0 && sec != null;
            Recode(ref prim, ref sec, split, w, h, levels, format, type);
            var (p360, s360) = Tile360(prim, sec, split, w, h, levels, outFormat, true, type);
            split = s360 != null;   // cube maps with several levels are split on the 360 even when the MCC copy is not

            uint gpu = f.gpu;
            if ((curve == 0 || curve == 1 || curve == 5) && f.gammaLow >= 0)   // stock: curves 0 and 1 carry the gamma fetch word, 2 and 3 the linear one
                gpu = (gpu & ~0x3Fu) | (uint)f.gammaLow | 0x7E00;

            var ctl = new byte[64];
            var r = new ExtractedResourceInfo(src.Index)
            {
                Flags = src.Flags, Type = src.Type, Info = ctl, ResourceBits = src.ResourceBits, BaseDefinitionAddress = 0x20000034,
                OriginalParentTagIndex = parentTag, Location = new ExtractedResourcePointer(),
            };
            if (p360 != null)
            {
                Be32(ctl, 0x00, (uint)p360.Length);
                r.Location.OriginalPrimaryPageIndex = sink.Page(p360); r.Location.PrimaryOffset = 0;
                r.ResourceFixups.Add(new ResourceFixup { Offset = 0x0C, Address = 0x40000000 });
            }
            if (s360 != null)
            {
                Be32(ctl, 0x14, (uint)s360.Length);
                r.Location.OriginalSecondaryPageIndex = sink.Page(s360); r.Location.SecondaryOffset = 0;
                r.ResourceFixups.Add(new ResourceFixup { Offset = 0x20, Address = 0x60000000 });
            }
            Be16(ctl, 0x28, w); Be16(ctl, 0x2A, h); ctl[0x2C] = (byte)depth; ctl[0x2D] = (byte)levels; ctl[0x2E] = (byte)type; ctl[0x2F] = (byte)(split ? 1 : 0);
            Be32(ctl, 0x30, gpu);
            Be32(ctl, 0x3C, 0xB0063001);     // constant word present in every stock 360 texture control seen
            r.ResourceBits = (p360 != null ? 1 : 0) | (s360 != null ? 2 : 0);   // which data blocks exist (stock: 1 = primary only, 3 = both)
            r.ResourceFixups.Add(new ResourceFixup { Offset = 0x34, Address = 0x20000000 });
            r.DefinitionFixups.Add(new ResourceDefinitionFixup { Offset = 0x20000034, Type = 2 });
            sink.Add(r);
            return new Result { Resource = r, Secondary = split, Format = outFormat, Note = $"{w}x{h} type {type} fmt {format}{(outFormat != format ? "->" + outFormat : "")} levels {levels}{(split ? " (top level separate)" : "")} -> {p360?.Length ?? 0}+{s360?.Length ?? 0} bytes" };
        }

        // MCC BC5 endpoints are signed; the 360 DXN fetch is biased unsigned (selector bits unchanged).
        static void Dxn(byte[] d)
        {
            if (d == null) return;
            for (int b = 0; b + 16 <= d.Length; b += 16) { d[b] ^= 0x80; d[b + 1] ^= 0x80; d[b + 8] ^= 0x80; d[b + 9] ^= 0x80; }
        }
    }
}
