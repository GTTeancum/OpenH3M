// Halo Online render geometry -> Halo 3 360 render geometry resource.
// Vertex buffers: TagTool's Halo Online vertex stream reads each vertex, TagTool's Xbox vertex stream writes it (the
// same pair TagTool's VertexBufferConverter uses for 360 -> Halo Online, run the other way); the per-format value
// transforms TagTool applies on the way to Halo Online are inverted here (VertexConverter.cs: ConvertVectorSpace,
// ConvertColorSpace, ConvertNormal). Index buffers: 16-bit indices, byte order swapped.
// Resource layout (as ReachPort's GeometryPort, verified in game): a 48-byte root with the vertex buffer table at +24
// and the index buffer table at +36; descriptors and tables in the definition, buffer data in the page.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Blamite.Injection;
using TagTool.Cache;
using TagTool.Common;
using TagTool.Geometry;
using TagTool.Tags.Resources;
using ResourceFixup = Blamite.Blam.Resources.ResourceFixup;
using ResourceDefinitionFixup = Blamite.Blam.Resources.ResourceDefinitionFixup;
using BDatum = Blamite.Blam.DatumIndex;

namespace Ho2H3
{
    public static class GeometryConvert
    {
        static float Inv(float u) => u >= 0 ? u / 2f : u / 2f + 1f;   // inverse of TagTool ConvertVectorSpace
        static RealVector3d Inv(RealVector3d v) => new RealVector3d(Inv(v.I), Inv(v.J), Inv(v.K));
        static RealQuaternion Inv(RealQuaternion v) => new RealQuaternion(Inv(v.I), Inv(v.J), Inv(v.K), v.W);
        static uint InvColor(uint c) { uint r = 0; for (int k = 0; k < 4; k++) r |= (uint)((((c >> (8 * k)) & 0xFF) - 0x7F) & 0xFF) << (8 * k); return r; }
        static RealQuaternion InvNormal(RealQuaternion n)   // inverse of ConvertNormal: reverse order, [0,1] -> [-1,1]
        {
            var a = Enumerable.Reverse(n.ToArray()).Select(e => 2f * (Math.Clamp(e, 0f, 1f) - 0.5f)).ToArray();
            return new RealQuaternion(a);
        }

        // 360 vertex writer: the exact inverse of TagTool's VertexStreamXbox readers (whose writers are not implemented)
        class XWriter
        {
            readonly VertexElementStream S; readonly MemoryStream M; readonly TagTool.IO.EndianWriter W;
            public XWriter(MemoryStream m) { M = m; S = new VertexElementStream(m, TagTool.IO.EndianFormat.BigEndian); W = new TagTool.IO.EndianWriter(m, TagTool.IO.EndianFormat.BigEndian); }
            static uint Q(float v, int max) => (uint)Math.Clamp((int)Math.Round(Math.Clamp(v, 0f, 1f) * max), 0, max);
            public void DHen3N(RealVector3d v) => W.Write(Q(v.I, 1023) | Q(v.J, 2047) << 10 | Q(v.K, 2047) << 21);
            public void Float3(RealVector3d v) => S.WriteFloat3(v);
            public void Float2(RealVector2d v) => S.WriteFloat2(v);
            public void UShort4N(RealQuaternion v) => S.WriteUShort4N(v);
            public void UShort2N(RealVector2d v) => S.WriteUShort2N(v);
            public void UByte4(byte[] v) => S.WriteUByte4(v);
            public void UByte4N(RealQuaternion v) => S.WriteUByte4N(v);
            public void SByte4N(RealQuaternion v) => S.WriteSByte4N(v);
            public void Dec3N(RealVector3d v) => S.WriteDec3N(v);
            public void Color(uint v) => S.WriteColor(v);
            public void Byte(float v) => W.Write((byte)Q(v, 255));
            public void Pad(long start, int stride) { while (M.Position - start < stride) M.WriteByte(0); }
        }

        public static (byte[] data, int stride, int count, int format)? Vertices(VertexBufferDefinition vb, CacheVersion inVer, CachePlatform inPlat)
        {
            using var input = new MemoryStream(vb.Data.Data); using var output = new MemoryStream();
            var i = VertexStreamFactory.Create(inVer, inPlat, input); var o = new XWriter(output);
            var xs = new VertexStreamXbox(new MemoryStream());
            int n = vb.Count; var fmt = vb.Format == VertexBufferFormat.World2 ? VertexBufferFormat.World : vb.Format;
            int stride = xs.GetVertexSize(fmt);
            for (int k = 0; k < n; k++)
            {
                long st = output.Position;
                switch (fmt)
                {
                    case VertexBufferFormat.World: { var v = i.ReadWorldVertex(); o.Float3(new RealVector3d(v.Position.I, v.Position.J, v.Position.K)); o.Float2(v.Texcoord); o.DHen3N(Inv(v.Normal)); o.DHen3N(Inv(v.Tangent.IJK)); o.DHen3N(Inv(v.Binormal)); break; }
                    case VertexBufferFormat.Rigid: { var v = i.ReadRigidVertex(); o.UShort4N(v.Position); o.UShort2N(v.Texcoord); o.DHen3N(Inv(v.Normal)); o.DHen3N(Inv(v.Tangent.IJK)); o.DHen3N(Inv(v.Binormal)); break; }
                    case VertexBufferFormat.Skinned: { var v = i.ReadSkinnedVertex(); o.UShort4N(v.Position); o.UShort2N(v.Texcoord); o.DHen3N(Inv(v.Normal)); o.DHen3N(Inv(v.Tangent.IJK)); o.DHen3N(Inv(v.Binormal)); o.UByte4(v.BlendIndices); o.UByte4N(new RealQuaternion(v.BlendWeights)); break; }
                    case VertexBufferFormat.StaticPerPixel: o.UShort2N(i.ReadStaticPerPixelData().Texcoord); break;
                    case VertexBufferFormat.StaticPerVertex: { var v = i.ReadStaticPerVertexData(); o.Color(InvColor(v.Color1)); o.Color(InvColor(v.Color2)); o.Color(InvColor(v.Color3)); o.Color(InvColor(v.Color4)); o.Color(InvColor(v.Color5)); break; }
                    case VertexBufferFormat.AmbientPrt: o.Byte(i.ReadAmbientPrtData().SHCoefficient); break;
                    case VertexBufferFormat.LinearPrt: o.SByte4N(InvNormal(i.ReadLinearPrtData().SHCoefficients)); break;
                    case VertexBufferFormat.QuadraticPrt: { var v = i.ReadQuadraticPrtData(); o.Dec3N(v.SHCoefficients1); o.Dec3N(v.SHCoefficients2); o.Dec3N(v.SHCoefficients3); break; }
                    case VertexBufferFormat.StaticPerVertexColor: o.Float3(i.ReadStaticPerVertexColorData().Color); break;
                    case VertexBufferFormat.ParticleModel: { var v = i.ReadParticleModelVertex(); o.UShort4N(new RealQuaternion(v.Position.I, v.Position.J, v.Position.K, 0)); o.UShort2N(v.Texcoord); o.DHen3N(Inv(v.Normal)); break; }
                    default: return null;
                }
                o.Pad(st, stride);
            }
            return (output.ToArray(), stride, n, (int)fmt);
        }

        static void Be32(List<byte> b, int at, uint v) { b[at] = (byte)(v >> 24); b[at + 1] = (byte)(v >> 16); b[at + 2] = (byte)(v >> 8); b[at + 3] = (byte)v; }
        static void Be16(List<byte> b, int at, int v) { b[at] = (byte)(v >> 8); b[at + 1] = (byte)v; }

        // the whole resource; returns null when nothing usable
        // Halo 3 stores a mesh part's (and subpart's) first index and index count as 16-bit values; Halo Online as 32-bit.
        // A Halo Online mesh with more than 65535 indices (Reflection's atrium: 83469) would have every later part wrap
        // around (TagTool only warns). Fix: rebuild that mesh's index buffer with its parts in ascending size, so the
        // largest part comes last and every part starts below 65536. Same triangles, same materials; part order within a
        // mesh carries no meaning for drawing. Triangle lists only; a shared or unfixable buffer is reported, not changed.
        public static void FixPartOffsets(TagTool.Geometry.RenderGeometry geo, RenderGeometryApiResourceDefinition def, List<string> log, string where)
        {
            if (geo?.Meshes == null || def?.IndexBuffers == null) return;
            for (int mi = 0; mi < geo.Meshes.Count; mi++)
            {
                var m = geo.Meshes[mi];
                bool over = m.Parts.Any(p => (int)p.FirstIndex > 65535 || (int)p.IndexCount > 65535) || m.SubParts.Any(p => (int)p.FirstIndex > 65535 || (int)p.IndexCount > 65535);
                if (!over) continue;
                int ibi = m.IndexBufferIndices[0];
                if (ibi < 0 || ibi >= def.IndexBuffers.Count) continue;
                if (geo.Meshes.Where((x, k) => k != mi).Any(x => x.IndexBufferIndices[0] == ibi)) { log.Add($"geometry {where}: mesh {mi} index buffer shared; parts past 65535 not fixed"); continue; }
                var ib = def.IndexBuffers[ibi].Definition;
                if (ib.Format != IndexBufferFormat.TriangleList) { log.Add($"geometry {where}: mesh {mi} {ib.Format} with parts past 65535 not fixed"); continue; }
                var src = ib.Data.Data; int total = src.Length / 2;
                var order = Enumerable.Range(0, m.Parts.Count).OrderBy(k => (int)m.Parts[k].IndexCount).ThenBy(k => k).ToList();
                var outIdx = new List<byte>(src.Length); var newSubs = new List<TagTool.Geometry.SubPart>(); var newParts = new List<TagTool.Geometry.Part>(); int covered = 0;
                foreach (int k in order)
                {
                    var p = m.Parts[k]; int oldFirst = p.FirstIndex, cnt = p.IndexCount, newFirst = outIdx.Count / 2;
                    if (oldFirst + cnt > total) { log.Add($"geometry {where}: mesh {mi} part {k} outside its index buffer; not fixed"); newParts = null; break; }
                    for (int q = 0; q < cnt * 2; q++) outIdx.Add(src[oldFirst * 2 + q]);
                    covered += cnt;
                    int firstSub = newSubs.Count;
                    for (int si = p.FirstSubPartIndex; si < p.FirstSubPartIndex + p.SubPartCount && si < m.SubParts.Count; si++)
                    {
                        var sp = m.SubParts[si]; sp.FirstIndex = newFirst + ((int)sp.FirstIndex - oldFirst); newSubs.Add(sp);
                    }
                    p.FirstIndex = newFirst; if (p.SubPartCount > 0) p.FirstSubPartIndex = (short)firstSub;
                    newParts.Add(p);
                }
                if (newParts == null) continue;
                if (newParts.Any(p => (int)p.FirstIndex > 65535 || (int)p.IndexCount > 65535) || newSubs.Any(p => (int)p.FirstIndex > 65535 || (int)p.IndexCount > 65535))
                { log.Add($"geometry {where}: mesh {mi}: {total} indices cannot be ordered under 65536 (largest part {m.Parts.Max(p => (int)p.IndexCount)}); needs splitting"); continue; }
                if (covered < total) for (int q = covered * 2; q < src.Length; q++) outIdx.Add(src[q]);   // anything outside the parts kept at the end
                ib.Data.Data = outIdx.ToArray(); m.Parts = newParts; if (newSubs.Count == m.SubParts.Count) m.SubParts = newSubs;
                log.Add($"geometry {where}: mesh {mi}: {total} indices, parts reordered so all start below 65536 (last part starts at {newParts.Last().FirstIndex.Value})");
            }
        }

        public static ExtractedResourceInfo Convert(RenderGeometryApiResourceDefinition def, CacheVersion inVer, CachePlatform inPlat, BDatum id, BDatum parent, Inject360.ResourceSink sink, List<string> log, string where)
        {
            var ctl = new List<byte>(); var raw = new List<byte>(); var fixups = new List<ResourceFixup>(); var defs = new List<ResourceDefinitionFixup>();
            int Alloc(int n) { int at = ctl.Count; ctl.AddRange(new byte[n]); return at; }
            int Gpu(byte[] d) { while (raw.Count % 16 != 0) raw.Add(0); int at = raw.Count; raw.AddRange(d); return at; }
            int root = Alloc(48); int dropped = 0;
            var vbs = def.VertexBuffers?.Select(x => x?.Definition).ToList() ?? new List<VertexBufferDefinition>();
            var ibs = def.IndexBuffers?.Select(x => x?.Definition).ToList() ?? new List<IndexBufferDefinition>();
            void Table(int blockAt, int n, int kind, Func<int, (byte[] desc, int ptrOff, byte[] data)> make)
            {
                if (n == 0) return;
                int table = Alloc(12 * n);
                fixups.Add(new ResourceFixup { Offset = root + blockAt + 4, Address = 0x20000000u | (uint)table });
                var items = Enumerable.Range(0, n).Select(make).ToList();
                for (int k = 0; k < n; k++)
                {
                    var (desc, ptrOff, data) = items[k];
                    int dAt = Alloc(desc.Length); for (int q = 0; q < desc.Length; q++) ctl[dAt + q] = desc[q];
                    int entry = table + k * 12;
                    fixups.Add(new ResourceFixup { Offset = entry, Address = 0x20000000u | (uint)dAt });
                    fixups.Add(new ResourceFixup { Offset = dAt + ptrOff, Address = 0x40000000u | (uint)Gpu(data) });
                    defs.Add(new ResourceDefinitionFixup { Offset = (int)(0x20000000u | (uint)entry), Type = kind });
                }
                Be32(ctl, root + blockAt, (uint)n);
            }
            Table(24, vbs.Count, 0, k =>
            {
                var vb = vbs[k]; (byte[] data, int stride, int count, int format)? c = null;
                try { if (vb?.Data?.Data != null && vb.Count > 0) c = Vertices(vb, inVer, inPlat); } catch (Exception ex) { log.Add($"geometry {where}: vertex buffer {k} ({vb?.Format}): {ex.Message}"); }
                if (c == null) { dropped++; c = (new byte[16], 16, 1, (int)(vb?.Format ?? VertexBufferFormat.World)); }
                var desc = new byte[0x1C]; void P32(int at, uint v) { desc[at] = (byte)(v >> 24); desc[at + 1] = (byte)(v >> 16); desc[at + 2] = (byte)(v >> 8); desc[at + 3] = (byte)v; }
                P32(0, (uint)c.Value.count); desc[4] = (byte)(c.Value.format >> 8); desc[5] = (byte)c.Value.format; desc[6] = (byte)(c.Value.stride >> 8); desc[7] = (byte)c.Value.stride; P32(8, (uint)c.Value.data.Length);
                return (desc, 0x14, c.Value.data);
            });
            Table(36, ibs.Count, 1, k =>
            {
                var ib = ibs[k]; var d = (byte[])(ib?.Data?.Data ?? new byte[2]).Clone();
                for (int q = 0; q + 1 < d.Length; q += 2) { var t = d[q]; d[q] = d[q + 1]; d[q + 1] = t; }
                var desc = new byte[0x18]; uint prim = (uint)(ib?.Format ?? IndexBufferFormat.TriangleList);
                desc[0] = (byte)(prim >> 24); desc[1] = (byte)(prim >> 16); desc[2] = (byte)(prim >> 8); desc[3] = (byte)prim;
                desc[4] = (byte)(d.Length >> 24); desc[5] = (byte)(d.Length >> 16); desc[6] = (byte)(d.Length >> 8); desc[7] = (byte)d.Length;
                return (desc, 0x10, d);
            });
            var r = new ExtractedResourceInfo(id) { Flags = 0x2, Type = "render_geometry_api_resource_definition", Info = ctl.ToArray(), ResourceBits = raw.Count > 0 ? 1 : 0, BaseDefinitionAddress = (int)(0x20000000u | (uint)root), OriginalParentTagIndex = parent, Location = new ExtractedResourcePointer() };
            r.ResourceFixups.AddRange(fixups); r.DefinitionFixups.AddRange(defs);
            if (raw.Count > 0) { r.Location.OriginalPrimaryPageIndex = sink.Page(raw.ToArray(), true, true); r.Location.PrimaryOffset = 0; }
            sink.Add(r);
            log.Add($"geometry {where}: {vbs.Count} vertex / {ibs.Count} index buffers, {dropped} vertex buffers not converted, {raw.Count} bytes");
            return r;
        }
    }
}
