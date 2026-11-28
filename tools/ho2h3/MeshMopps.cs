// Per-mesh cluster visibility ("Mesh Cluster Visibility"): one entry per render mesh holding two Havok MOPP codes (over
// the mesh's subparts, then its parts; keys = subpart / part index) and the reorder table built from their keys. Stock
// Guardian has one for every mesh; without them Halo 3 leaves meshes undrawn (hall of mirrors). Halo Online leaves most
// entries empty and the rest in a post-Halo 3 encoding, so all are generated here with TagTool's MOPP tool
// ("generate-mesh-mopp", the input TagTool's PerMeshMoppGenerator writes). TagTool's own exporter reads every vertex
// buffer as uncompressed; level meshes are compressed, so positions are decompressed through the mesh's compression
// bounds here (stock: the MOPP's code-info offset is the compression box corner less the tool's margin). The output
// headers are converted to the 360 byte order with TagTool's HavokConverter; the reorder table is TagTool's.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using TagTool.Cache;
using TagTool.Geometry;
using TagTool.Havok;
using TagTool.Tags.Resources;

namespace Ho2H3
{
    public static class MeshMopps
    {
        // meshCompression: mesh index -> compression index (instance definitions); other compressed meshes use the
        // compression entry of the same index when there is one
        public static int Build(GameCache cache, RenderGeometry geo, RenderGeometryApiResourceDefinition def, Dictionary<int, int> meshCompression, List<string> log, string where)
        {
            if (geo?.Meshes == null || def?.VertexBuffers == null) return 0;
            var list = new List<RenderGeometry.PerMeshMoppBlock>(); int made = 0, empty = 0, failed = 0; var reasons = new Dictionary<string, int>();
            for (int mi = 0; mi < geo.Meshes.Count; mi++)
            {
                RenderGeometry.PerMeshMoppBlock block = null;
                try { block = One(cache, geo, def, mi, meshCompression); } catch (Exception ex) { if (failed++ < 3) log.Add($"mesh MOPP: {where} mesh {mi}: {ex.GetType().Name} {ex.Message}"); }
                if (block == null) { block = new RenderGeometry.PerMeshMoppBlock { MoppCode = new byte[0], MoppReorderTable = new List<short>() }; empty++; reasons[Reason ?? "?"] = reasons.TryGetValue(Reason ?? "?", out var rn) ? rn + 1 : 1; Reason = null; } else made++;
                list.Add(block);
            }
            geo.MeshClusterVisibility = list;
            log.Add($"mesh MOPP: {where}: {made} of {geo.Meshes.Count} meshes generated ({empty} empty: {string.Join(", ", reasons.Select(kv => kv.Key + " " + kv.Value))}; {failed} failed)");
            return made;
        }

        static string Reason;
        static RenderGeometry.PerMeshMoppBlock One(GameCache cache, RenderGeometry geo, RenderGeometryApiResourceDefinition def, int mi, Dictionary<int, int> meshCompression)
        {
            var mesh = geo.Meshes[mi];
            int vbi = mesh.VertexBufferIndices[0], ibi = mesh.IndexBufferIndices[0];
            if (mesh.Parts.Count == 0) { Reason = "no parts"; return null; }
            if (vbi == ushort.MaxValue || ibi == ushort.MaxValue || vbi >= def.VertexBuffers.Count || ibi >= def.IndexBuffers.Count) { Reason = "no vertex/index buffer"; return null; }
            var vb = def.VertexBuffers[vbi].Definition; var ib = def.IndexBuffers[ibi].Definition;
            // positions
            var r = VertexStreamFactory.Create(cache.Version, cache.Platform, new MemoryStream(vb.Data.Data));
            var verts = new List<float[]>();
            RenderGeometryCompression comp = null;
            if (meshCompression.TryGetValue(mi, out var ci) && ci >= 0 && ci < geo.Compression.Count) comp = geo.Compression[ci];
            else if (mi < geo.Compression.Count) comp = geo.Compression[mi];
            for (int k = 0; k < vb.Count; k++)
            {
                switch (vb.Format)
                {
                    case VertexBufferFormat.World: { var v = r.ReadWorldVertex(); verts.Add(new[] { v.Position.I, v.Position.J, v.Position.K }); break; }
                    case VertexBufferFormat.Rigid:
                        {
                            var v = r.ReadRigidVertex(); var p = new[] { v.Position.I, v.Position.J, v.Position.K };
                            if (comp != null) p = new[] { comp.X.Lower + p[0] * (comp.X.Upper - comp.X.Lower), comp.Y.Lower + p[1] * (comp.Y.Upper - comp.Y.Lower), comp.Z.Lower + p[2] * (comp.Z.Upper - comp.Z.Lower) };
                            verts.Add(p); break;
                        }
                    case VertexBufferFormat.Skinned: { var v = r.ReadSkinnedVertex(); var p = new[] { v.Position.I, v.Position.J, v.Position.K }; if (comp != null) p = new[] { comp.X.Lower + p[0] * (comp.X.Upper - comp.X.Lower), comp.Y.Lower + p[1] * (comp.Y.Upper - comp.Y.Lower), comp.Z.Lower + p[2] * (comp.Z.Upper - comp.Z.Lower) }; verts.Add(p); break; }
                    default: Reason = "vertex format " + vb.Format; return null;
                }
            }
            // indices per part / subpart
            ushort[] Read(int first, int count)
            {
                var s = new IndexBufferStream(new MemoryStream(ib.Data.Data), cache.Endianness) { Position = (uint)first };
                return ib.Format == IndexBufferFormat.TriangleStrip ? s.ReadTriangleStrip((uint)count) : s.ReadIndices((uint)count);
            }
            var idx = new List<int>(); var parts = new List<(int s, int c, int ss, int sc)>(); var subs = new List<(int s, int c)>();
            foreach (var part in mesh.Parts)
            {
                int ps = idx.Count, pss = subs.Count;
                if (part.SubPartCount > 0)
                    for (int i = part.FirstSubPartIndex; i < part.FirstSubPartIndex + part.SubPartCount; i++)
                    {
                        var sp = mesh.SubParts[i]; int ss = idx.Count; var t = Read(sp.FirstIndex, sp.IndexCount);
                        for (int j = 0; j + 2 < t.Length; j += 3) { idx.Add(t[j]); idx.Add(t[j + 1]); idx.Add(t[j + 2]); }
                        subs.Add((ss, idx.Count - ss));
                    }
                else { var t = Read(part.FirstIndex, part.IndexCount); for (int j = 0; j + 2 < t.Length; j += 3) { idx.Add(t[j]); idx.Add(t[j + 1]); idx.Add(t[j + 2]); } }
                parts.Add((ps, idx.Count - ps, pss, subs.Count - pss));
            }
            if (idx.Count == 0) { Reason = "no indices"; return null; }
            if (idx.Any(i => i >= verts.Count)) { Reason = "index beyond vertices"; return null; }
            var sb = new StringBuilder(); var ic = CultureInfo.InvariantCulture;
            sb.Append(";### vertices ###\n").Append(verts.Count).Append('\n');
            foreach (var v in verts) sb.Append(string.Format(ic, "{0:0.0000000000}\t{1:0.0000000000}\t{2:0.0000000000}\n", v[0], v[1], v[2]));
            sb.Append("\n;### indices ###\n").Append(idx.Count).Append('\n');
            for (int i = 0; i < idx.Count; i += 3) sb.Append(idx[i]).Append('\t').Append(idx[i + 1]).Append('\t').Append(idx[i + 2]).Append('\n');
            sb.Append("\n;### parts ###\n").Append(parts.Count).Append('\n');
            foreach (var p in parts) sb.Append(p.s).Append('\t').Append(p.c).Append('\n').Append(p.ss).Append('\t').Append(p.sc).Append("\n\n");
            sb.Append("\n;### subparts ###\n").Append(subs.Count).Append('\n');
            foreach (var p in subs) sb.Append(p.s).Append('\t').Append(p.c).Append('\n');
            var raw = Run(sb.ToString()); if (raw == null) { Reason = "MOPP tool failed"; return null; }
            var reorder = PerMeshMoppGenerator.BuildReorderTable(cache, raw);
            var data = HeadersToBigEndian(raw);
            return new RenderGeometry.PerMeshMoppBlock { MoppCode = data, MoppReorderTable = reorder.Select(x => (short)x).ToList() };
        }

        // the tool's output: repeated {0x30-byte hkpMoppCode header, code bytes, padding to 16}. Header words (vtable, the
        // two referenced-object shorts, code-info offset xyzw, array pointer / size / capacity, padding) to big-endian;
        // code bytes are a byte stream and stay as they are.
        static byte[] HeadersToBigEndian(byte[] raw)
        {
            var o = (byte[])raw.Clone(); int at = 0;
            while (at + 0x30 <= o.Length)
            {
                int size = BitConverter.ToInt32(raw, at + 0x24);
                foreach (int w in new[] { 0x00, 0x10, 0x14, 0x18, 0x1C, 0x20, 0x24, 0x28, 0x2C }) Array.Reverse(o, at + w, 4);
                Array.Reverse(o, at + 4, 2); Array.Reverse(o, at + 6, 2);
                if (size < 0) break;
                at += (size + 0x3F) & ~0xF;
            }
            return o;
        }

        static byte[] Run(string input)
        {
            var dir = Path.Combine(AppContext.BaseDirectory, "Temp"); Directory.CreateDirectory(dir);
            string id = Guid.NewGuid().ToString("N").Substring(0, 12), inp = Path.Combine(dir, "mmopp_" + id + ".input"), outp = Path.Combine(dir, "mmopp_" + id + ".output");
            try
            {
                File.WriteAllText(inp, input);
                var p = Process.Start(new ProcessStartInfo { FileName = ClusterMopps.MoppExe, Arguments = $"generate-mesh-mopp \"{inp}\" \"{outp}\"", UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true, WindowStyle = ProcessWindowStyle.Hidden });
                p.StandardOutput.ReadToEnd(); p.StandardError.ReadToEnd(); p.WaitForExit();
                return p.ExitCode == 0 && File.Exists(outp) ? File.ReadAllBytes(outp) : null;
            }
            finally { try { File.Delete(inp); } catch { } try { File.Delete(outp); } catch { } }
        }
    }
}
